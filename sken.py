import requests
from pprint import pprint
from collections import defaultdict
import configparser
config = configparser.ConfigParser()
config.read('config.ini')

_BASE_URL = config["DEFAULT"]["base_url"]
_FORMAT = config["DEFAULT"]["format"]

default_params = {"format": _FORMAT, "username": None, "api_key": None}

REQUIRED = ["api_key", "username", "corpname"]


def parse_args(args):
    parsed = {}
    for arg in args:
        if isinstance(arg, User):
            parsed["api_key"] = arg.api_key
            parsed["username"] = arg.username
        if isinstance(arg, Corpus):
            parsed["corpname"] = arg.corpname
        if isinstance(arg, Query):
            parsed.update(arg.parameters)
    return parsed


def reset_default_parameters():
    global default_params
    default_params = {"format": _FORMAT, "username": None, "api_key": None}


def update_from_default(params):
    for key in default_params:
        if key not in params:
            params[key] = default_params[key]
    params.update(default_params)
    return params


def missing_params(params):
    missing = []
    for key in REQUIRED:
        if key not in params:
            missing.append(key)
        if key in params and not params[key]:
            missing.append(key)
    return missing


class User:

    def __init__(self, api_key, username, default=True):
        self._api_key = api_key
        self._username = username
        if default:
            self.default()

    def default(self):
        global DEFAULT, default_params
        default_params["api_key"] = self.api_key
        default_params["username"] = self.username

    @property
    def api_key(self):
        return self._api_key

    @property
    def username(self):
        return self._username




class Query:

    def __init__(self, **parameters):
        for key in parameters:
            if not parameters[key]:
                raise Exception("Non-empty string expected.")
            if type(parameters[key]) != str:
                raise Exception("String <str> expected.")
        self._params = parameters


    @property
    def parameters(self):
        return self._params

    def __str__(self):
        string = ""
        for key in self.parameters:
            string += key + ":" + self.parameters[key] + "\n"
        return string

    #TODO определить метод для сохранения запроса
    #TODO определить метод для импортирования сохраненных запросов


class Corpus:

    method = "/corp_info"

    def __init__(self, corpus_name, my_corpus=False, default=False):
        self._corpname = corpus_name
        self._params = {"corpname": corpus_name}
        self._url = None
        self._info = None
        self._raw_info = None

        if default:
            self.default()

    @property
    def corpname(self):
        return self._corpname

    @property
    def info(self):
        return self._info

    def default(self):
        global default_params
        default_params["corpname"] = self.corpname

    def __str__(self):
        return self.description

    def get_info(self):
        if self.info is not None:
            return self.info

        update_from_default(self._params)
        response = requests.get(_BASE_URL + self.method, params=self._params)
        self._url = response.url
        data = response.json()

        self._info = {"name": data["name"], "description": data["info"], "documentation": data["infohref"],
                "encoding": data["encoding"], "lpos_dict": dict(data["lposlist"]), "size": data["sizes"]}
        self._raw_info = data

        return self.info

    @property
    def info(self):
        return self._info

    @property
    def info_raw(self):
        return self._raw_info

    @property
    def name(self):
        return self.info["name"]

    @property
    def description(self):
        return self.info["description"]

    @property
    def documentation(self):
        return self.info["documentation"]

    @property
    def encoding(self):
        return self.info["encoding"]

    @property
    def lempos(self):
        return self.info["lpos_dict"]

    @property
    def size(self):
        return self.info["size"]


class WordSketch:

    method = "/wsketch"
    method_url = _BASE_URL + method

    def __init__(self, *args, **kwargs):
        self._params = {}

        if args and kwargs:
            self._params.update(parse_args(args))
            self._params.update(kwargs)

        if kwargs and not args:
            self.params_from_kwargs(kwargs)

        if args and not kwargs:
            self.params_from_args(args)

        update_from_default(self._params)
        missing = missing_params(self._params)
        if missing:
            raise Exception("Missing parameter(s): {}".format(", ".join(missing)) + ".")

        print("Sending request to Sketch Engine API...")

        response = requests.get(self.method_url, params=self._params)
        if response.status_code != requests.codes.ok:
            response.raise_for_status()

        data = response.json()
        print("Data retrieved.")

        self._url = response.url
        self._lemma = data["lemma"]
        self._corpus_name = data["corp_full_name"]
        self._frequency_raw = data["freq"]
        self._frequency_rel = data["relfreq"]
        self._lpos_dict = data["lpos_dict"]
        self._lpos = data["lpos"]
        self._gram_rels = data["Gramrels"]

    def params_from_kwargs(self, kwargs):
        if set(kwargs).issubset(set(REQUIRED)):
            raise Exception("Not enough arguments to make a Sketch Engine request.")
        self._params.update(kwargs)

    def params_from_args(self, args):

        types = [type(o) for o in args]
        if Query not in types:
            raise Exception("Please specify your query.")
        else:
            self._params.update(parse_args(args))

    @property
    def parameters(self):
        return self._params

    @property
    def lemma(self):
        return self._lemma


    @property
    def lpos_dict(self):
        return self._lpos_dict

    @property
    def lpos(self):
        return self._lpos

    @property
    def pos(self):
        inv = dict()
        for key in self.lpos_dict:
            inv[self.lpos_dict[key]] = key
        return inv[self.lpos]

    @property
    def corpus_name(self):
        return self._corpus_name

    @property
    def frequency_raw(self):
        return self._frequency_raw

    @property
    def frequency_rel(self):
        return self._frequency_rel

    @property
    def gram_rel(self):
        return self._gram_rels

    @property
    def url(self):
        return self._url

    def __str__(self):
        return ("Lemma: {}.\nPart of speech: {} ('{}').\n"
                "Corpus: {}.\nFrequency: {} ({} per million).".format(self.lemma, self.pos, self.lpos,
                                                                      self.corpus_name, self.frequency_raw,
                                                                      round(self.frequency_rel, 2)))

    def extract_gramrels(self):
        gram_rels = defaultdict(dict)

        for gramrel in self._gram_rels:
            name = gramrel["name"].replace("%w", self.lemma)
            for word in gramrel["Words"]:
                collocate = Collocate(word, name)
                gram_rels[name][collocate.word] = collocate
        self._gram_rels = gram_rels

    @property
    def gram_rel_names(self):
        return list(self._gram_rels.keys())

    @property
    def gram_rels(self):
        return self._gram_rels


class Collocate:

    method_url = _BASE_URL + "/view"
    basic_params = {"pagesize": 5, "viewmode": "sen"}

    def __init__(self, data, gramrelname):
        self._gram_rel_name = gramrelname
        try:
            self._word = data["word"]
        except KeyError:
            self._word = data["name"]

        # self._lempos = data["lempos"]
        self._score = data["score"]
        self._seek = 'q[ws(2,{})]'.format(data["seek"])
        self._count = data["count"]
        # self._example = data["cm"]
        self._params = {"q": self._seek}
        self._params.update(self.basic_params)
        self._params.update(default_params)

    @property
    def word(self):
        return self._word

    def get_sentences(self):

        data = requests.get(self.method_url, params=self._params).json()

        sentences = []

        for i in range(3):
            for line in data['Lines']:
                left = ''.join(part['str'] for part in line['Left'])
                middle = ''.join(part['str'] for part in line['Kwic'])
                right = ''.join(part['str'] for part in line['Right'])
                sentence = left + middle + right
                sentences.append(sentence)
            pars = self._params
            pars["from"] = data["nextlink"].split("=")[1]
            response = requests.get(self.method_url, params=pars).json()

        return sentences


class WordList:

    method = "/wordlist"
    method_url = _BASE_URL + method

    def __init__(self, **parameters):
        self._data = ""
        self._url = ""
        self._query = ""
        self.lemma = ""

class Thesaurus:

    method = "/thes"
    method_url = _BASE_URL + method

    def __init__(self, **parameters):
        self._data = ""
        self._url = ""
        self._query = ""
        self.lemma = ""


class SketchDiff:

    method = "/wsdiff"
    method_url = _BASE_URL + method

    def __init__(self, **parameters):
        self._data = ""
        self._url = ""
        self._query = ""
        self.lemma = ""
