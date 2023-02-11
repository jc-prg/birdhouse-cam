import json
import codecs
import logging
from os import path


jsonAppDir = path.dirname(path.abspath(__file__))
jsonSettingsPath = ""


def init(json_path):
    """global settings"""

    global jsonPath, jsonAppDir, jsonSettings, jsonSettingsFile, jsonSettingsPath
    jsonPath = json_path
    jsonSettingsPath = path.join(jsonAppDir, jsonPath)


def read(file):
    """read data from json file"""

    d = {}
    file1 = file + ".json"
    file2 = path.join(jsonAppDir, jsonPath, file1)
    logging.debug("Reading JSON file (" + file2 + ")")

    if path.exists(file2):
        try:
            with open(file2) as json_data:
                d = json.load(json_data)
        except Exception as e:
            logging.error("Error reading JSON file (" + file2 + "): " + str(e))
            d = {"error": str(e)}
    else:
        logging.error("JSON file does not exist (" + file2 + ") ")
        d = {"error": "File does not exist (" + file2 + ")!"}

    return d


def write(file, data):
    """write data to readable json file"""

    d = {}
    file1 = file + ".json"
    file2 = path.join(jsonAppDir, jsonPath, file1)

    try:
        with open(file2, 'wb') as outfile:
            json.dump(data, codecs.getwriter('utf-8')(outfile), ensure_ascii=False, sort_keys=True, indent=4)
            # json.dump(data, outfile, ensure_ascii=False, sort_keys=True, indent=4)
        logging.debug("Wrote JSON file (" + file2 + ")")
        return "ok"

    except Exception as e:
        logging.error("Error writing JSON file (" + file2 + "): " + str(e))
        return "error"