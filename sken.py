import requests
from pprint import pprint
import configparser
config = configparser.ConfigParser()
config.read('config.ini')

DEFAULT = {"DEFAULT_USER": None,
           "DEFAULT_CORPUS": None}

_BASE_URL = config["DEFAULT"]["base_url"]
_FORMAT = config["DEFAULT"]["format"]

query_params = {"base_url": _BASE_URL, "format": _FORMAT}

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


def default_parameters():
    print(parse_args(list(DEFAULT.values())))
    return parse_args(list(DEFAULT.values()))


def reset_default_parameters():
    global DEFAULT
    DEFAULT = {"DEFAULT_USER": None,
               "DEFAULT_CORPUS": None}


def update_from_default(params):
    default = parse_args(list(DEFAULT.values()))
    for key in default:
        if key not in params:
            params[key] = default[key]
    params["format"] = _FORMAT
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

    def __init__(self, api_key, username):

        self._api_key = api_key
        self._username = username

    def default(self):
        global DEFAULT
        DEFAULT["DEFAULT_USER"] = self

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

    def __init__(self, corpus_name, my_corpus=False):
        self._corpname = corpus_name
        self._info = None

    @property
    def corpname(self):
        return self._corpname

    def get_info(self):
        #TODO
        if not self._info:
            #make request
            #self._info = request
            return "DEFINE Query"
        else:
            return self._info

    def default(self):
        global DEFAULT
        DEFAULT["DEFAULT_CORPUS"] = self

    @property
    def lempos(self):
        #TODO
        return {"KEY": "VALUE"}


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
        self._gram_rels = data["gramrels"]

    def params_from_kwargs(self, kwargs):
        if set(self._params.keys()).issubset(set(REQUIRED)):
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
        return ("URL: {}.\nLemma: {}.\nPart of speech: {} ('{}').\n"
                "Corpus: {}.\nFrequency: {} ({} per million).\n".format(self.url, self.lemma, self.pos, self.lpos,
                                                                        self.corpus_name, self.frequency_raw,
                                                                        round(self.frequency_rel, 2)))


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





