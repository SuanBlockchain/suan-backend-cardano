import requests
from requests.structures import CaseInsensitiveDict
from decouple import config
from configparser import ConfigParser


def config(config_path: str = "./credentials.local.ini", section: str = "") -> dict:
    # create a parser
    parser = ConfigParser()
    # read config file
    parser.read(config_path)

    params = {}
    if parser.has_section(section):
        items = parser.items(section)
        for item in items:
            params[item[0]] = item[1]
    else:
        raise Exception(
            "Section {0} not found in the {1} file".format(section, config_path)
        )

    return params


def kobo_api(URL, params={}):
    kobo_tokens_dict = config(section="kobo")
    headers = CaseInsensitiveDict()
    kobo_token = kobo_tokens_dict["kobo_token"]
    headers["Authorization"] = "Token " + str(kobo_token)

    return requests.get(URL, headers=headers, params=params)
