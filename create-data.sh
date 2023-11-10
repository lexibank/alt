# pip install csvkit
# get the concepts
csvcut -l raw/ALT-standardized_forms.csv -c 1 | sed 's/line_number,/NUMBER,ITALIAN/g' | tr ',' '\t' > etc/concepts.tsv

# get the locations 
# use sed for replacements
# last cmd removes empty lines: https://recoverit.wondershare.com/linux-recovery/bash-remove-empty-lines.html
head raw/ALT-standardized_forms.csv -n 1 | sed 's/,/\n/g' | sed 's/^\([0-9]*\) /\1,/g' | sort -nu | sed 's/^7,/ID,Name\n7,/g' | sed '/^[[:space:]]*$/d'  > etc/languages.csv
# create empty citation
echo "@book{tuscan, author={+++}, year={+++}}" > raw/sources.bib

# run catconfig (installing glottolog, concepticon, etc. in one place)
#
pip install -e .
cldfbench catconfig 

# map concepts to concepticon 
concepticon map_concepts etc/concepts.tsv --language=it

# run cldf bench
cldfbench lexibank.makecldf lexibank_tuscandialects.py

# run orthography profile 
cldfbench lexibank.init_profile lexibank_tuscandialects.py 

# convert to edictor
pip install pyedictor
edictor wordlist --name=alt --preprocessing=edictor/prep.py
