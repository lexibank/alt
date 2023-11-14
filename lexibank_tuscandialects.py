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



    def cmd_makecldf(self, args):
        # add bib
        args.writer.add_sources()
        args.log.info("added sources")

        # add concept
        concepts = {}
        for concept in self.concepts:
            idx = concept["NUMBER"] + "_" + slug(concept["ITALIAN"])
            args.writer.add_concept(
                    ID=idx,
                    Name=concept["ITALIAN"],
                    Italian_Gloss=concept["ITALIAN"],
                    )
            concepts[concept["ITALIAN"]] = idx
                    
        args.log.info("added concepts")

        # add language
        languages = {}
        for language in self.languages:
            idx = language["ID"] + "_" + slug(language["Name"])
            glottocode = "ital1282" if language["Name"] == "Italiano" else "fior1235"
            isocode = "ita" if language["Name"] == "Italiano" else ""
            args.writer.add_language(
                ID=idx,
                Name=language["Name"],
                Longitude=language["Longitude"],
                Latitude=language["Latitude"],
                Glottocode=glottocode,
                ISO639P3code=isocode
                )
            languages[language["ID"] + " " + language["Name"]] = idx
        args.log.info("added languages")

        # read in data
        #data = self.raw_dir.read_csv(
        #    "ALT-standardized_forms.csv", delimiter=","
        #)

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
                    args.writer.add_form(
                            Language_ID=languages[language],
                            Parameter_ID=concepts[concept],
                            Value=form,
                            Form=form,
                            Source="tuscan")
