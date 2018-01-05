import requests
from pprint import pprint
from collections import defaultdict
import configparser
import utils
config = configparser.ConfigParser()
config.read('config.ini')

_BASE_URL = config["DEFAULT"]["base_url"]
_FORMAT = config["DEFAULT"]["format"]

default_params = {"format": _FORMAT, "username": None, "api_key": None}

REQUIRED = ["api_key", "username", "corpname"]


def login(api_key, username):
    global default_params
    default_params.update({"api_key": api_key, "username": username})


def reset_to_default():
    global default_params
    default_params = {"format": _FORMAT, "username": None, "api_key": None}


def _sketch_engine_request(method, params):
    _update_from_default(params)

    _update_from_default(params)
    missing = _missing_params(params)
    if missing:
        raise Exception("Missing parameter(s): {}".format(", ".join(missing)) + ".")

    print("Sending request to Sketch Engine API...")
    response = requests.get(_BASE_URL + method, params=params)
    if response.status_code != requests.codes.ok:
        raise requests.RequestException()
    data = response.json()
    if "error" in data.keys():
        raise requests.RequestException("Server error occured. No data retrieved.")
    print("Data retrieved.")
    return data


def _parse_args(args):
    parsed = {}
    for arg in args:
        if isinstance(arg, Corpus):
            parsed["corpname"] = arg.corpname
        if isinstance(arg, Query):
            parsed.update(arg.parameters)
    return parsed


def _update_from_default(params):
    for key in default_params:
        if key not in params:
            params[key] = default_params[key]
    params.update(default_params)
    return params


def _missing_params(params):
    missing = []
    for key in REQUIRED:
        if key not in params:
            missing.append(key)
        if key in params and not params[key]:
            missing.append(key)
    return missing


def _inverse_dict(d):
    inv = {}
    for key in d:
        inv[d[key]] = key
    return inv


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

    def __init__(self, corpus_name, my_corpus=False):
        self._corpname = corpus_name
        self._params = {"corpname": corpus_name}
        self._info = None
        self._raw_info = None

    def get_info(self):
        if self._info is None:
            data = _sketch_engine_request(self.method, self._params)
            self._info = {"name": data["name"], "description": data["info"], "documentation": data["infohref"],
                "encoding": data["encoding"], "lpos_dict": dict(data["lposlist"]), "size": data["sizes"]}
            self._raw_info = data

    def default(self):
        global default_params
        default_params["corpname"] = self.corpname

    @property
    def corpname(self):
        return self._corpname

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

    def __init__(self, *args, **kwargs):
        self._params = {}

        if kwargs and not args:
            self._params.update(kwargs)

        if args and kwargs:
            self._params.update(_parse_args(args))
            self._params.update(kwargs)

        if args and not kwargs:
            self._params.update(_parse_args(args))

        data = _sketch_engine_request(self.method, self._params)
        self._data = data

    @property
    def lemma(self):
        return self._data["lemma"]

    @property
    def lempos_dict(self):
        return self._data["lpos_dict"]

    @property
    def lempos(self):
        return self._data["lpos"]

    @property
    def pos(self):
        inv = _inverse_dict(self.lempos_dict)
        return inv[self.lempos]

    @property
    def corpus_name(self):
        return self._data["corp_full_name"]

    @property
    def frequency_raw(self):
        return self._data["freq"]

    @property
    def frequency_rel(self):
        return self._data["relfreq"]

    @property
    def gramrels_raw(self):
        return self._data["Gramrels"]

    @property
    def number_of_gramrels(self):
        return len(self.gramrels_raw)

    def __str__(self):
        return ("Lemma: {lemma}.\n"
                "Part of speech: {pos} ('{lempos}').\n"
                "Corpus: {corpus}.\n"
                "Frequency: {freq} ({relfreq} per million).\n"
                "Number of grammatical relations: {num}".format(lemma=self.lemma,
                                                                pos=self.pos,
                                                                lempos=self.lempos,
                                                                corpus=self.corpus_name,
                                                                freq=self.frequency_raw,
                                                                relfreq=round(self.frequency_rel, 2),
                                                                num=self.number_of_gramrels))

    def extract_gramrels(self):
        gramrels = defaultdict(dict)

        for gramrel in self.gramrels_raw:
            name = gramrel["name"].replace("%w", self.lemma)
            for word in gramrel["Words"]:
                collocate = Collocate(word, name)
                gramrels[name][collocate.word] = collocate
        self._gramrels = gramrels

    @property
    def gram_rel_names(self):
        return list(self._gramrels.keys())

    @property
    def gramrels(self):
        return self._gramrels


class Collocate:

    method = "/view"
    basic_params = dict(pagesize=10, viewmode="sen")
    other = dict(gdex_enabled=0, attr="lemma,tag,word", ctxattrs="lemma,tag,word")

    def __init__(self, data, gramrelname):
        self._gram_rel_name = gramrelname
        self._data = data
        self._params = {"q": 'q[ws(2,{})]'.format(data["seek"])}
        # self._params = {"w": data["seek"]} # or 2?
        self._params.update(self.basic_params)

    @property
    def word(self):
        try:
            return self._data["word"]
        except KeyError:
            return self._data["name"]

    @property
    def score(self):
        return self._data["score"]

    @property
    def count(self):
        return self._data["count"]

    @property
    def example(self):
        try:
            return self._data["cm"]
        except KeyError:
            return None

    @property
    def lempos(self):
        try:
            return self._data["lempos"]
        except KeyError:
            return None

    def set_pagesize(self, pagesize):
        self.basic_params["pagesize"] = pagesize

    def set_viewmode(self, viewmode):
        if viewmode not in ["kwic", "sen"]:
            print('Wrong parameters: either "kwic" or "sen".')
            raise Exception()
        self.basic_params["pagesize"] = viewmode

    def get_sentences(self, number_of_pages=5):

        data = _sketch_engine_request(method=self.method, params=self._params)

        sentences = []

        for i in range(number_of_pages):
            for line in data['Lines']:
                left = ''.join(part['str'] for part in line['Left'])
                middle = ''.join(part['str'] for part in line['Kwic'])
                right = ''.join(part['str'] for part in line['Right'])
                sentence = left + middle + right
                sentences.append(sentence)
            pars = self._params
            pars["from"] = data["nextlink"].split("=")[1]
            data = _sketch_engine_request(method=self.method, params=pars)

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



#
# class User:
#
#     def __init__(self, api_key, username, default=True):
#         self._api_key = api_key
#         self._username = username
#         if default:
#             self.default()
#
#     def default(self):
#         global DEFAULT, default_params
#         default_params["api_key"] = self.api_key
#         default_params["username"] = self.username
#
#     @property
#     def api_key(self):
#         return self._api_key
#
#     @property
#     def username(self):
#         return self._username
#
