#!/usr/bin/python3

import os
import sys
import time
import logging
import json
import codecs
import threading
from datetime import datetime


class BirdhouseConfig(threading.Thread):

    def __init__(self, param_init, main_directory):
        """
        Initialize new thread and set inital parameters
        """
        threading.Thread.__init__(self)
        self.update = {}
        self.param_init = param_init
        self.name = "Config"
        self.async_answers = []
        self.async_running = False
        self.locked = {}
        self.config_cache = {}
        self.html_replace = {
            "start_date": datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        }
        self.directories = {
            "html": "../app/",
            "data": "../data/",
            "main": "",
            "sensor": "",
            "images": "images/",
            "backup": "images/",
            "videos": "videos/",
            "videos_temp": "videos/images2video/"
        }
        self.files = {
            "main": "config.json",
            "backup": "config_images.json",
            "images": "config_images.json",
            "sensor": "config_sensor.json",
            "videos": "config_videos.json"
        }

        self.main_directory = main_directory

        if not self.exists("main"):
            directory = os.path.join(self.main_directory, self.directories["data"])
            filename = os.path.join(directory, self.files["main"])
            logging.info("Create main config file (" + filename + ") ...")
            self.write("main", self.param_init)
            if not self.exists("main"):
                logging.info("OK.")
            else:
                logging.error("Could not create main config file, check if directory '"+directory+"' is writable.")
                sys.exit()

        logging.info("Read configuration from '"+self.file("main")+"' ...")
        self.param = self.read("main")
        self.param["path"] = main_directory
        self._running = True

    def run(self):
        """
        Core function (not clear what to do yet)
        """
        logging.info("Starting config handler ...")
        while self._running:
            time.sleep(1)
        logging.info("Stopped config handler.")

    def stop(self):
        """
        Core function (not clear what to do yet)
        """
        self._running = False

        return

    def reload(self):
        """
        Reload main configuration
        """
        self.param = self.read("main")

    def lock(self, config, date=""):
        """
        lock config file
        """
        filename = os.path.join(self.directory(config), date, self.files[config])
        self.locked[filename] = True

    def unlock(self, config, date=""):
        """
        unlock config file
        """
        filename = os.path.join(self.directory(config), date, self.files[config])
        self.locked[filename] = False

    def check_locked(self, filename):
        """
        wait, while a file is locked for writing
        """
        count = 0
        if filename in self.locked and self.locked[filename]:
            while self.locked[filename]:
                time.sleep(0.2)
                count += 1
                if count > 10:
                    logging.warning("Waiting! File '" + filename + "' is locked (" + str(count) + ")")
                    time.sleep(1)
        if count > 10:
            logging.warning("File '" + filename + "' is not locked any more (" + str(count) + ")")
        return "OK"

    def directory(self, config, date=""):
        """
        return directory of config file
        """
        return os.path.join(self.main_directory, self.directories["data"], self.directories[config], date)

    def directory_create(self, config, date=""):
        """
        return directory of config file
        """
        if not os.path.isdir(self.directory(config)):
            logging.info("Creating directory for " + config + " ...")
            os.mkdir(self.directory(config))
            logging.info("OK.")

        if date != "" and not os.path.isdir(os.path.join(self.directory(config), date)):
            logging.info("Creating directory for " + config + " ...")
            os.mkdir(os.path.join(self.directory(config), date))
            logging.info("OK.")

    def file(self, config, date=""):
        """
        return complete path of config file
        """
        return os.path.join(self.directory(config, date), self.files[config])

    def read(self, config, date=""):
        """
        read dict from json config file
        """
        config_file = self.file(config, date)
        config_data = self.read_json(config_file)
        logging.debug("Read JSON file " + config_file)
        return config_data.copy()

    def read_json(self, filename):
        """
        read json file including check if locked
        """
        try:
            with open(filename) as json_file:
                data = json.load(json_file)
            return data

        except Exception as e:
            logging.error("Could not read JSON file: " + filename)
            logging.error(str(e))
            return {}

    def read_cache(self, config, date=""):
        """
        return from cache, read file and fill cache if not in cache already
        """
        if config not in self.config_cache and date == "":
            self.config_cache[config] = self.read(config=config, date="")
        elif config not in self.config_cache and date != "":
            self.config_cache[config] = {}
            self.config_cache[config][date] = self.read(config=config, date=date)
        elif date not in self.config_cache[config] and date != "":
            self.config_cache[config][date] = self.read(config=config, date=date)

        if date == "":
            return self.config_cache[config].copy()
        else:
            return self.config_cache[config][date].copy()

    def write(self, config, config_data, date=""):
        """
        write dict to json config file and update cache
        """
        config_file = self.file(config, date)
        self.write_json(config_file, config_data)

        if date == "":
            self.config_cache[config] = config_data
        elif config in self.config_cache:
            self.config_cache[config][date] = config_data
        else:
            self.config_cache[config] = {}
            self.config_cache[config][date] = config_data

    def write_json(self, filename, data):
        """
        write json file including locking mechanism
        """
        try:
            self.check_locked(filename)
            self.locked[filename] = True
            with open(filename, 'wb') as json_file:
                json.dump(data, codecs.getwriter('utf-8')(json_file), ensure_ascii=False, sort_keys=True, indent=4)
            self.locked[filename] = False
            logging.debug("Write JSON file: "+filename)

        except Exception as e:
            logging.error("Could not write JSON file: " + filename)
            logging.error(str(e))

    def write_image(self, config, file_data, date="", time=''):
        """
        write dict for single file to json config file
        """
        logging.info("Write image: " + config_file)
        config_data = self.read_cache(config=config, date=date)
        config_data[time] = file_data
        self.write(config=config, config_data=config_data, date=date)

    def create_copy(self, config, date="", add="copy"):
        config_file = self.file(config, date)
        content = self.read_json(config_file)
        self.write_json(config_file+"."+add, content)

    def exists(self, config, date=""):
        """
        check if config file exists
        """
        config_file = os.path.join(self.directory(config), date, self.files[config])
        return os.path.isfile(config_file)

    def imageName(self, image_type, timestamp, camera=""):
        """
        set image name
        """
        if camera != "":
            camera += '_'

        if image_type == "lowres":
            return "image_" + camera + timestamp + ".jpg"
        elif image_type == "hires":
            return "image_" + camera + "big_" + timestamp + ".jpeg"
        elif image_type == "thumb":
            return "video_" + camera + timestamp + "_thumb.jpeg"
        elif image_type == "video":
            return "video_" + camera + timestamp + ".mp4"
        elif image_type == "vimages":
            return "video_" + camera + timestamp + "_"
        else:
            return "image_" + camera + timestamp + ".jpg"

    def imageName2Param(self, filename):
        """
        Analyze image name ...
        """
        if filename.endswith(".jpg"):
            filename = filename.replace(".jpg", "")
        elif filename.endswith(".jpeg"):
            filename = filename.replace(".jpeg", "")
        else:
            return {"error": "not an image"}

        parts = filename.split("_")
        info = {"stamp": '', "type": 'lowres', "cam": 'cam1'}
        if len(parts) == 2:
            info["stamp"] = parts[1]
        if len(parts) == 3 and parts[1] == "big":
            info["stamp"] = parts[2]
            info["type"] = "hires"
        if len(parts) == 3:
            info["cam"] = parts[1]
            info["stamp"] = parts[2]
        if len(parts) == 4:
            info["cam"] = parts[1]
            info["type"] = "hires"
            info["stamp"] = parts[3]
        return info

    def change_config(self, config, config_data, date=""):
        """
        change configuration base on dict in form
        dict["key1:ey2:key3"] = "value"
        """
        logging.info("Change configuration ... "+config+"/"+date+" ... "+str(config_data))
        param = self.read(config, date)
        data_type = ""
        for key in config_data:
            keys = key.split(":")
            if "||" in config_data[key]:
                value_type = config_data[key].split("||")
                value = value_type[0]
                data_type = value_type[1]
            else:
                value = config_data[key]

            if data_type == "boolean" and value == "false":
                value = False
            elif data_type == "boolean" and value == "true":
                value = True
            elif data_type == "float":
                value = float(value)
            elif data_type == "integer":
                value = int(value)
            elif data_type == "json":
                try:
                    value = json.loads(value)
                except Exception as e:
                    logging.error("Could not load as JSON: "+str(e))

            if ":" not in key:
                param[key] = value
            elif len(keys) == 2:
                param[keys[0]][keys[1]] = value
            elif len(keys) == 3:
                param[keys[0]][keys[1]][keys[2]] = value
            elif len(keys) == 4:
                param[keys[0]][keys[1]][keys[2]][keys[3]] = value
            elif len(keys) == 5:
                param[keys[0]][keys[1]][keys[2]][keys[3]][keys[4]] = value
            elif len(keys) == 6:
                param[keys[0]][keys[1]][keys[2]][keys[3]][keys[4]][keys[5]] = value
        self.write(config, param, date)

        if config == "main":
            self.param = self.read(config, date)
            for key in self.update:
                self.update[key] = True
