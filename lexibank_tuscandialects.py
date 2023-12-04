import pathlib
import attr
from clldutils.misc import slug
from pylexibank import Dataset as BaseDataset
from pylexibank import progressbar as pb
from pylexibank import Language, Concept
from pylexibank import FormSpec
import re
import codecs
from collections import defaultdict, Counter
from cldfbench import CLDFSpec
from pyclts import CLTS
import pylexibank


@attr.s
class CustomLanguage(Language):
    Location = attr.ib(default=None)
    #Remark = attr.ib(default=None)


@attr.s
class CustomConcept(Concept):
    Italian_Gloss = attr.ib(default=None)


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "tuscandialects"
    language_class = CustomLanguage
    concept_class = CustomConcept
    #form_spec = FormSpec(separators="~;,/", missing_data=["∅"], first_form_only=True)

    def cmd_download(self, args):
        """
        Download basic data.
        """
        self.raw_dir.download(
                "http://dbtvm1.ilc.cnr.it/altweb/ISAPI_AltWeb.dll?AZIONE=ALL&PARAM=P",
                "concepts.html")
        with codecs.open(self.raw_dir / "concepts.html", "r", encoding="windows-1250") as f:
            text = ""
            for row in f:
                text += row
        concepts = re.findall(
                r'target="principale">([^<]*)\. \(n\. ([0-9]*[a-zA-Z]*)\)</', text)
        alt_concepts = re.findall(
                r'target="principale">([^<]*)<', text)
        with codecs.open(self.raw_dir / "concepts-in-source.tsv", "w", "utf-8") as f:
            for concept, num in concepts:
                f.write(num + "\t" + concept + "\n")
        args.log.info("wrote concepts in source to raw directory")

        self.raw_dir.download(
            "http://dbtvm1.ilc.cnr.it/altweb/ISAPI_AltWeb.dll?AZIONE=ALL&PARAM=P2&LUOGHI=&NUMSAVE=",
            "concepts2.html")
        with codecs.open(self.raw_dir / "concepts2.html", "r", encoding="windows-1250") as f:
            text = ""
            for row in f:
                text += row
        concepts = re.findall(
            r'target="principale">([^<]*)\. \(n\. ([0-9]*[a-zA-Z]*)\)</', text)
        alt_concepts = re.findall(
            r'target="principale">([^<]*)<', text)
        with codecs.open(self.raw_dir / "concepts-in-source.tsv", "a", "utf-8") as f:
            for concept, num in concepts:
                f.write(num + "\t" + concept + "\n")
        args.log.info("wrote concepts in source to raw directory")

    def cldf_specs(self):
        return {
            None: pylexibank.Dataset.cldf_specs(self),
            "structure": CLDFSpec(
                module="StructureDataset",
                dir=self.cldf_dir,
                data_fnames={"ParameterTable": "features.csv"},
            ),
        }

    def cmd_makecldf(self, args):
        
        sounds = defaultdict(
                lambda : {
                    "concept": defaultdict(int), 
                    "variety": defaultdict(int), 
                    "total": 0})
        # add lexical data
        with self.cldf_writer(args) as writer:
            # add bib
            writer.add_sources()
            args.log.info("added sources")

            # add concept
            concepts = {}
            for concept in self.concepts:
                idx = concept["NUMBER"] + "_" + slug(concept["ITALIAN"])
                writer.add_concept(
                        ID=idx,
                        Name=concept["ITALIAN"],
                        Italian_Gloss=concept["ITALIAN"],
                        )
                concepts[concept["ITALIAN"]] = idx
                        
            args.log.info("added concepts")

            # add languages
            with open(self.raw_dir / "Tuscany-subset.kml") as f:
                geodata = f.read()
            pattern = re.compile(
                    r'<Placemark>.*?<name>([0-9]+.*?)</name>.*?'
                    '<LookAt>.*?<longitude>(.*?)</longitude>.*?'
                    '<latitude>(.*?)</latitude>.*?</LookAt>.*?'
                    '</Placemark>', re.DOTALL)
            datapoints = re.findall(pattern, geodata)
            # manually add coordinates for Standard Italian (from Glottolog)
            datapoints.append(
                    ("225 Italiano", "12.65", "43.05")
                    )  
            id_to_site_data = {}
            
            for site, long, lat in datapoints:
                site_info = site.split()
                site_id = site_info[0]
                site_name = " ".join(site_info[1:]).replace("&apos;", "'")
            
                id_to_site_data[site_id] = {
                    "name": site_name,
                    "longitude": long,
                    "latitude": lat
                }
            languages = {}
            cldf_languages = []
            for language in self.languages:
                idx = language["ID"] + "_" + slug(language["Name"])
                glottocode = "ital1282" if language["Name"] == "Italiano" else "fior1235"
                isocode = "ita" if language["Name"] == "Italiano" else ""
                lng = writer.add_language(
                    ID=idx,
                    Name=language["Name"],
                    Longitude=id_to_site_data[language["ID"]]["longitude"],
                    Latitude=id_to_site_data[language["ID"]]["latitude"],
                    Glottocode=glottocode,
                    ISO639P3code=isocode
                    )
                languages[language["ID"] + " " + language["Name"]] = idx
                cldf_languages += [lng]
            args.log.info("added languages")

            readings = defaultdict(lambda: defaultdict(list))
            for path in self.raw_dir.glob("alt_notosc_IPA/*.fon"):
                concept, language = "", ""
                for row in self.raw_dir.read_csv(path):
                    line = row[0]
                    if line.startswith("%"):
                        continue
                    elif line.startswith("#"):
                        concept = line[2:].replace(" ", "_").replace("'", "_")
                    elif line.startswith(":"):
                        language = line[2:]
                    elif line.startswith('-'):
                        form = line[2:]
                        readings[concept][language] += [form]

            standardized_data = defaultdict(lambda: defaultdict(str))
            for concept, langdict in readings.items():
                for language, forms in langdict.items():
                    if not forms:
                        continue
                    most_common_form = Counter(forms).most_common(1)[0][0]
                    standardized_data[concept][language] = most_common_form
            
            # add data
            for concept, langdict in pb(standardized_data.items(), desc="cldfify"):
                for language, form in langdict.items():
                    if form.strip():
                        lexeme = writer.add_form(
                                Language_ID=languages[language],
                                Parameter_ID=concepts[concept],
                                Value=form,
                                Form=form,
                                Source="tuscan")
                        for sound in lexeme["Segments"]:
                            sounds[sound]["variety"][languages[language]] += 1
                            sounds[sound]["concept"][concepts[concept]] += 1
                            sounds[sound]["total"] += 1
            language_table = writer.cldf["LanguageTable"]            

        with self.cldf_writer(args, cldf_spec="structure", clean=False) as writer:
            # We share the language table across both CLDF datasets:
            writer.cldf.add_component(language_table)
            writer.objects["LanguageTable"] = cldf_languages
            
            # columns for the features table
            writer.cldf.add_columns(
                "ParameterTable",
                {"name": "CLTS_BIPA", "datatype": "string"},
                {"name": "CLTS_Name", "datatype": "string"},
                {"name": "Lexibank_BIPA", "datatype": "string"},
                {"name": "Frequency", "datatype": "integer"},
                {"name": "OccurrencePerVariety", "datatype": "integer"},
                {"name": "OccurrencePerConcept", "datatype": "integer"}
            )
            writer.cldf.add_columns(
                    "ValueTable", 
                    {"name": "Context", "datatype": "string"})
            writer.cldf.add_columns(
                    "ValueTable", {"name": "Frequency", "datatype": "integer"})
            clts = CLTS(args.clts.dir)
            bipa = clts.transcriptionsystem_dict["bipa"]
            for sound_, values in pb(sounds.items(), desc="add sounds"):
                sound = bipa[sound_]
                pidx = "-".join(
                        [s[2:] for s in sound.codepoints.split()])

                writer.objects["ParameterTable"].append(
                        {
                            "ID": pidx,
                            "Name": str(sound),
                            "Description": sound.name,
                            "CLTS_BIPA": str(sound),
                            "CLTS_Name": sound.name,
                            "Lexibank_BIPA": sound_,
                            "Frequency": values["total"],
                            "OccurrencePerVariety": len(values["variety"]),
                            "OccurrencePerConcept": len(values["concept"])
                        }
                    )
                for language, frequency in values["variety"].items():
                    writer.objects["ValueTable"].append(
                            {
                                "ID": language + "_" + pidx,
                                "Language_ID": language,
                                "Parameter_ID": pidx,
                                "Value": str(sound),
                                "Frequency": frequency,
                                "Source": ["tuscan"],
                            }
                        )
                args.log.info("added sounds")
