import pathlib
import attr
from clldutils.misc import slug
from pylexibank import Dataset as BaseDataset
from pylexibank import progressbar as pb
from pylexibank import Language, Concept
from pylexibank import FormSpec
import re
import codecs


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
            args.writer.add_language(
                    ID=idx,
                    Name=language["Name"]
                    )
            languages[language["ID"] + " "+ language["Name"]] = idx 
        args.log.info("added languages")

        # read in data
        data = self.raw_dir.read_csv(
            "ALT-standardized_forms.csv", delimiter=","
        )
        # add data
        for row in pb(data[1:], desc="cldfify"):
            concept = row[0]
            for language, form in list(zip(data[0], row))[1:]:
                if form.strip():
                    args.writer.add_form(
                            Language_ID=languages[language],
                            Parameter_ID=concepts[concept],
                            Value=form,
                            Form=form,
                            Source="tuscan")

