import sken
import configparser
config = configparser.ConfigParser()
config.read('config.ini')

noam = sken.User(api_key=config["NOAM"]["api_key"],
                 username=config["NOAM"]["username"])
noam.default()

corpus = sken.Corpus(corpus_name=config["NOAM"]["corpname"])
corpus.default()

query = sken.Query(lemma="large", lpos="-j")

ws = sken.WordSketch(query)
print(ws)