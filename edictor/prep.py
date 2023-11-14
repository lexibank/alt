from lingpy import *

def run(wordlist):

    wordlist.renumber('concept', 'cogid')
    alms = Alignments(wordlist, ref='cogid', transcription="form")
    alms.align()
    return alms
