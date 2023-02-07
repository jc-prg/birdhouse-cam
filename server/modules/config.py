import os
import sys
import time
import logging
import json
import codecs
import threading
from datetime import datetime


class BirdhouseConfigJSON(object):

    def __init__(self):
        self.locked = {}
        logging.info("Starting config JSON handler ...")

    def lock(self, filename):
        """
        lock config file
        """
        self.locked[filename] = True

    def unlock(self, filename):
        """
        unlock config file
        """
        self.locked[filename] = False

    def wait_if_locked(self, filename):
        """
        wait, while a file is locked for writing
        """
        wait = 0.2
        count = 0
        logging.debug("Start check locked: " + filename + " ...")

        if filename in self.locked and self.locked[filename]:
            while self.locked[filename]:
                time.sleep(wait)
                count += 1
                if count > 10:
                    logging.warning("Waiting! File '" + filename + "' is locked (" + str(count) + ")")
                    time.sleep(1)

        elif filename == "ALL":
            logging.info("Wait until no file is locked ...")
            locked = len(self.locked.keys())
            while locked > 0:
                locked = 0
                for key in self.locked:
                    if self.locked[key]:
                        locked += 1
                time.sleep(wait)
            logging.info("OK")
        if count > 10:
            logging.warning("File '" + filename + "' is not locked any more (" + str(count) + ")")
        return "OK"

    def read(self, filename):
        """
        read json file including check if locked
        """
        try:
            self.wait_if_locked(filename)
            with open(filename) as json_file:
                data = json.load(json_file)
            return data

        except Exception as e:
            logging.error("Could not read JSON file: " + filename)
            logging.error(str(e))
            return {}

    def write(self, filename, data):
        """
        write json file including locking mechanism
        """
        self.wait_if_locked(filename)
        try:
            self.locked[filename] = True
            with open(filename, 'wb') as json_file:
                json.dump(data, codecs.getwriter('utf-8')(json_file), ensure_ascii=False, sort_keys=True, indent=4)
                json_file.close()
            self.locked[filename] = False
            logging.debug("Write JSON file: " + filename)

        except Exception as e:
            self.locked[filename] = False
            logging.error("Could not write JSON file: " + filename)
            logging.error(str(e))


class BirdhouseConfigQueue(threading.Thread):

    def __init__(self, config):
        """
        Initialize new thread and set inital parameters
        """
        threading.Thread.__init__(self)
        self.queue_count = None
        self.config = config
        self._running = True
        self.edit_queue = {"images": [], "videos": [], "backup": {}, "sensor": []}
        self.status_queue = {"images": [], "videos": [], "backup": {}, "sensor": []}
        self.queue_wait = 10

    def run(self):
        """
        create videos and process queue
        """
        logging.info("Starting config queue ...")
        config_files = ["images", "videos", "backup", "sensor"]
        start_time = time.time()
        while self._running:
            if start_time + self.queue_wait < time.time():
                start_time = time.time()

                count_entries = 0
                count_files = 0
                for config_file in config_files:

                    # EDIT QUEUE: today, video (without date)
                    if config_file != "backup" and len(self.edit_queue[config_file]) > 0:
                        entries = self.config.read_cache(config_file)
                        self.config.lock(config_file)

                        count_files += 1
                        while len(self.edit_queue[config_file]) > 0:
                            [key, entry, command] = self.edit_queue[config_file].pop()
                            count_entries += 1
                            if command == "add" or command == "edit":
                                entries[key] = entry
                            elif command == "delete" and key in entries:
                                del entries[key]
                            elif command == "keep_data":
                                entries[key]["type"] = "data"
                                if "hires" in entries[key]:
                                    del entries[key]["hires"]
                                if "lowres" in entries[key]:
                                    del entries[key]["lowres"]
                                if "directory" in entries[key]:
                                    del entries[key]["directory"]
                                if "compare" in entries[key]:
                                    del entries[key]["compare"]
                                if "favorit" in entries[key]:
                                    del entries[key]["favorit"]
                                if "to_be_deleted" in entries[key]:
                                    del entries[key]["to_be_deleted"]

                        self.config.unlock(config_file)
                        self.config.write(config_file, entries)

                    # EDIT QUEUE: backup (with date)
                    elif config_file == "backup":
                        for date in self.edit_queue[config_file]:
                            entry_data = self.config.read_cache(config_file, date)
                            entries = entry_data["files"]
                            self.config.lock(config_file, date)

                            if date in self.edit_queue[config_file] and len(self.edit_queue[config_file][date]) > 0:
                                count_files += 1
                            elif date not in self.edit_queue[config_file]:
                                self.edit_queue[config_file][date] = []

                            while len(self.edit_queue[config_file][date]) > 0:
                                [key, entry, command] = self.edit_queue[config_file][date].pop()
                                count_entries += 1

                                if command == "add" or command == "edit":
                                    entries[key] = entry
                                elif command == "delete" and key in entries:
                                    del entries[key]
                                elif command == "keep_data":
                                    entries[key]["type"] = "data"
                                    if "hires" in entries[key]:
                                        del entries[key]["hires"]
                                    if "lowres" in entries[key]:
                                        del entries[key]["lowres"]
                                    if "directory" in entries[key]:
                                        del entries[key]["directory"]
                                    if "compare" in entries[key]:
                                        del entries[key]["compare"]
                                    if "favorit" in entries[key]:
                                        del entries[key]["favorit"]
                                    if "to_be_deleted" in entries[key]:
                                        del entries[key]["to_be_deleted"]

                            entry_data["files"] = entries
                            self.config.unlock(config_file, date)
                            self.config.write(config_file, entry_data, date)

                    # STATUS QUEUE: today, video (without date)
                    if config_file != "backup" and len(self.status_queue[config_file]) > 0:
                        entries = self.config.read_cache(config_file)
                        self.config.lock(config_file)

                        count_files += 1
                        while len(self.status_queue[config_file]) > 0:
                            [date, key, change_status, status] = self.status_queue[config_file].pop()
                            count_entries += 1

                            if change_status == "RANGE_END":
                                self.config.async_answers.append(["RANGE_DONE"])
                            elif key in entries:
                                entries[key][change_status] = status

                        self.config.unlock(config_file)
                        self.config.write(config_file, entries)

                    # STATUS QUEUE: backup (with date)
                    elif config_file == "backup":
                        for date in self.status_queue[config_file]:
                            entry_data = self.config.read_cache(config_file, date)
                            entries = entry_data["files"]
                            self.config.lock(config_file, date)

                            if date in self.status_queue[config_file] and len(self.status_queue[config_file][date]) > 0:
                                count_files += 1
                            else:
                                self.status_queue[config_file][date] = []

                            while len(self.status_queue[config_file][date]) > 0:
                                [date, key, change_status, status] = self.status_queue[config_file][date].pop()
                                count_entries += 1

                                if change_status == "RANGE_END":
                                    self.config.async_answers.append(["RANGE_DONE"])
                                elif key in entries:
                                    entries[key][change_status] = status

                            entry_data["files"] = entries
                            self.config.unlock(config_file, date)
                            self.config.write(config_file, entry_data, date)

                if count_entries > 0:
                    logging.info("Queue: wrote "+str(count_entries)+" entries to "+str(count_files)+" config files (" +
                                 str(round(time.time()-start_time, 2))+"s/"+str(round(time.time()))+")")

            time.sleep(1)

        logging.info("Stopped Config Queue.")

    def stop(self):
        """
        Do nothing at the moment
        """
        self._running = False

    def add_to_status_queue(self, config, date, key, change_status, status):
        """
        add status change to queue
        """
        if config != "backup":
            self.status_queue[config].append([date, key, change_status, status])
        elif config == "backup":
            if date not in self.status_queue[config]:
                self.status_queue[config][date] = []
            self.status_queue[config][date].append([date, key, change_status, status])

    def add_to_edit_queue(self, config, date, key, entry, command):
        """
        add, remove or edit complete entry using a queue
        """
        if config != "backup":
            self.edit_queue[config].append([key, entry, command])
        elif config == "backup":
            if date not in self.edit_queue[config]:
                self.edit_queue[config][date] = []
            self.edit_queue[config][date].append([key, entry, command])

    def set_status_favorite(self, path):
        """
        set / unset favorite -> redesigned
        """
        param = path.split("/")
        response = {}
        category = param[2]
        config_data = {}
        self.config.update_views["favorite"] = True

        if category == "current":
            entry_id = param[3]
            entry_value = param[4]
            entry_date = ""
            category = "images"
        elif category == "videos":
            entry_id = param[3]
            entry_value = param[4]
            entry_date = ""
        else:
            entry_date = param[3]
            entry_id = param[4]
            entry_value = param[5]

        if category == "images":
            config_data = self.config.read_cache(config="images")
        elif category == "backup":
            config_data = self.config.read_cache(config="backup", date=entry_date)["files"]
        elif category == "videos":
            config_data = self.config.read_cache(config="videos")

        response["command"] = ["mark/unmark as favorit", entry_id]
        if entry_id in config_data:
            self.add_to_status_queue(config=category, date=entry_date, key=entry_id, change_status="favorit",
                                     status=entry_value)
            if entry_value == 1:
                self.add_to_status_queue(config=category, date=entry_date, key=entry_id, change_status="to_be_deleted",
                                         status=1)
        else:
            response["error"] = "no entry found with stamp " + entry_id

        return response

    def set_status_recycle(self, path):
        """
        set / unset recycling -> redesigned
        """
        param = path.split("/")
        response = {}
        category = param[2]
        config_data = {}
        self.config.update_views["favorite"] = True

        if category == "current":
            entry_id = param[3]
            entry_value = param[4]
            entry_date = ""
            category = "images"
        elif category == "videos":
            entry_id = param[3]
            entry_value = param[4]
            entry_date = ""
        else:
            entry_date = param[3]
            entry_id = param[4]
            entry_value = param[5]

        if category == "images":
            config_data = self.config.read_cache(config="images")
        elif category == "backup":
            config_data = self.config.read_cache(config="backup", date=entry_date)["files"]
        elif category == "videos":
            config_data = self.config.read_cache(config="videos")

        logging.info("test:" + entry_date)

        response["command"] = ["mark/unmark for deletion", entry_id]
        if entry_id in config_data:
            logging.info("OK")
            self.add_to_status_queue(config=category, date=entry_date, key=entry_id, change_status="to_be_deleted",
                                     status=entry_value)
            if entry_value == 1:
                self.add_to_status_queue(config=category, date=entry_date, key=entry_id, change_status="favorit", status=0)
        else:
            response["error"] = "no entry found with stamp " + entry_id

        return response

    def set_status_recycle_range(self, path):
        """
        set / unset recycling -> range from-to
        """
        param = path.split("/")
        response = {}
        category = param[2]
        config_data = {}
        self.config.update_views["favorite"] = True

        if category == "current":
            entry_from = param[3]
            entry_to = param[4]
            entry_value = param[5]
            entry_date = ""
            category = "images"
        elif category == "videos":
            entry_from = param[3]
            entry_to = param[4]
            entry_value = param[5]
            entry_date = ""
        else:
            entry_date = param[3]
            entry_from = param[4]
            entry_to = param[5]
            entry_value = param[6]

        if category == "images":
            config_data = self.config.read_cache(config="images")
        elif category == "backup":
            config_data = self.config.read_cache(config="backup", date=entry_date)["files"]
        elif category == "videos":
            config_data = self.config.read_cache(config="videos")

        response["command"] = ["mark/unmark for deletion", entry_from, entry_to]
        if entry_from in config_data and entry_to in config_data:
            relevant = False
            stamps = list(reversed(sorted(config_data.keys())))
            camera = config_data[entry_from]["camera"]
            for entry_id in stamps:
                if entry_id == entry_from:
                    relevant = True
                if relevant and config_data[entry_id]["camera"] == camera and \
                        ("type" not in config_data[entry_id] or config_data[entry_id]["type"] != "data"):
                    self.add_to_status_queue(config=category, date=entry_date, key=entry_id,
                                             change_status="to_be_deleted", status=1)
                    self.add_to_status_queue(config=category, date=entry_date, key=entry_id,
                                             change_status="favorit", status=0)
                if entry_id == entry_to:
                    relevant = False
        else:
            response["error"] = "no entry found with stamp " + entry_from + "/" + entry_to

        self.add_to_status_queue(config=category, date=entry_date, key=entry_id, change_status="RANGE_END", status=0)
        return response

    def entry_add(self, config, date, key, entry):
        """
        add entry to config file using the queue
        """
        self.add_to_edit_queue(config, date, key, entry, "add")

    def entry_edit(self, config, date, key, entry):
        """
        edit entry in config file using the queue
        """
        self.add_to_edit_queue(config, date, key, entry, "edit")

    def entry_delete(self, config, date, key):
        """
        delete entry from config file using the queue
        """
        self.add_to_edit_queue(config, date, key, {}, "delete")

    def entry_keep_data(self, config, date, key):
        """
        cleaning image entry keeping activity and sensor data for charts using the queue
        """
        self.add_to_edit_queue(config, date, key, {}, "keep_data")


class BirdhouseConfig(threading.Thread):

    def __init__(self, param_init, main_directory):
        """
        Initialize new thread and set inital parameters
        """
        threading.Thread.__init__(self)
        self.name = "Config"
        self.param = None
        self.queue = None
        self.json = None

        self._running = True
        self._paused = False
        self.update = {}
        self.update_views = {"favorite": False, "archive": False}
        self.async_answers = []
        self.async_running = False
        self.locked = {}
        self.param_init = param_init
        self.config_cache = {}
        self.html_replace = {
            "start_date": datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        }
        self.directories = {
            "html": "../app/",
            "data": "../data/",
            "main": "",
            "sensor": "images/",
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
                logging.error("Could not create main config file, check if directory '" + directory + "' is writable.")
                sys.exit()

        logging.info("Read configuration from '" + self.file_path("main") + "' ...")

    def run(self):
        """
        Core function (not clear what to do yet)
        """
        count = 0
        logging.info("Starting config handler ...")
        self.json = BirdhouseConfigJSON()
        self.queue = BirdhouseConfigQueue(config=self)
        self.queue.start()
        self.param = self.read("main")
        self.param["path"] = self.main_directory
        self.param["swap"] = self.read_swap_info()

        while self._running:
            time.sleep(1)
            if self._paused and count == 0:
                if count == 0:
                    logging.info("Writing config files is paused ...")
                    count += 1
            elif not self._paused:
                count = 0
        logging.info("Stopped config handler.")

    def stop(self):
        """
        Core function (not clear what to do yet)
        """
        self.queue.stop()
        self._running = False

        return

    def pause(self, command):
        """
        pause all writing processes (under construction)
        """
        self._paused = command

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
        self.json.lock(filename)

    def unlock(self, config, date=""):
        """
        unlock config file
        """
        filename = os.path.join(self.directory(config), date, self.files[config])
        self.json.unlock(filename)

    def wait_if_locked(self, filename):
        """
        wait, while a file is locked for writing
        """
        wait = 0.2
        count = 0
        logging.debug("Start check locked: " + filename + " ...")

        if filename in self.locked and self.locked[filename]:
            while self.locked[filename]:
                time.sleep(wait)
                count += 1
                if count > 10:
                    logging.warning("Waiting! File '" + filename + "' is locked (" + str(count) + ")")
                    time.sleep(1)

        elif filename == "ALL":
            logging.info("Wait until no file is locked ...")
            locked = len(self.locked.keys())
            while locked > 0:
                locked = 0
                for key in self.locked:
                    if self.locked[key]:
                        locked += 1
                time.sleep(wait)
            logging.info("OK")
        if count > 10:
            logging.warning("File '" + filename + "' is not locked any more (" + str(count) + ")")
        return "OK"

    def wait_if_paused(self):
        """
        wait if paused to avoid loss of data
        """
        while self._paused:
            time.sleep(0.2)

    def exists(self, config, date=""):
        """
        check if config file exists
        """
        config_file = os.path.join(self.directory(config), date, self.files[config])
        return os.path.isfile(config_file)

    def file_path(self, config, date=""):
        """
        return complete path of config file
        """
        return os.path.join(self.directory(config, date), self.files[config])

    def directory(self, config, date=""):
        """
        return directory of config file
        """
        path = os.path.join(self.main_directory, self.directories["data"], self.directories[config], date)
        if ".." in path:
            elements = path.split("/")
            path_new = []
            for element in elements:
                if element == "..":
                    path_new.pop(-1)
                else:
                    path_new.append(element)
            path = ""
            for element in path_new:
                path += "/" + element
            path = path.replace("//", "/")
        return path

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

    def read(self, config, date=""):
        """
        read dict from json config file
        """
        config_data = {}
        if self.exists(config, date):
            config_file = self.file_path(config, date)
            config_data = self.json.read(config_file)
        return config_data.copy()

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
        self.wait_if_paused()
        config_file = self.file_path(config, date)
        self.json.write(config_file, config_data)

        if date == "":
            self.config_cache[config] = config_data
        elif config in self.config_cache:
            self.config_cache[config][date] = config_data
        else:
            self.config_cache[config] = {}
            self.config_cache[config][date] = config_data

    def write_copy(self, config, date="", add="copy"):
        """
        create a copy of a complete config file
        """
        config_file = self.file_path(config, date)
        content = self.json.read(config_file)
        self.json.write(config_file + "." + add, content)

    def main_config_edit(self, config, config_data, date=""):
        """
        change configuration base on dict in form
        dict["key1:ey2:key3"] = "value"
        """
        logging.info("Change configuration ... " + config + "/" + date + " ... " + str(config_data))
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
                    logging.error("Could not load as JSON: " + str(e))

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

    @staticmethod
    def read_swap_info():
        """
        read swap info, if raspberry pi
        """
        cmd = "cat /etc/dphys-swapfile | grep CONF_SWAPSIZE"
        message = os.system(cmd)
        logging.info(message)
        return message

    @staticmethod
    def filename_image(image_type, timestamp, camera=""):
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

    @staticmethod
    def filename_image_get_param(filename):
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

