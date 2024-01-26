import os
import sys
import time
import json
import threading

from datetime import datetime, timezone, timedelta
from modules.presets import *
from modules.presets import birdhouse_cache_for_archive, birdhouse_cache
from modules.weather import BirdhouseWeather
from modules.bh_database import BirdhouseCouchDB, BirdhouseJSON, BirdhouseTEXT
from modules.bh_class import BirdhouseClass


class BirdhouseConfigDBHandler(threading.Thread, BirdhouseClass):

    def __init__(self, config, db_type="json", main_directory=""):
        threading.Thread.__init__(self)
        BirdhouseClass.__init__(self, class_id="DB-handler", config=config)
        self.thread_set_priority(1)

        self.db = birdhouse_couchdb
        self.backup_interval = 60 * 15
        self.directories = birdhouse_directories
        self.files = birdhouse_files
        self.main_directory = main_directory

        self.json = None
        self.couch = None
        self.db_type = None
        self.set_db_type(db_type)
        self.config_cache = {}
        self.config_cache_changed = {}

    def run(self):
        """
        if db_type == json, create a backup regularly
        """
        update_time = time.time()
        self.logging.info("Starting DB handler (" + self.db_type + "|" + self.main_directory + ") ...")
        while self._running:
            if self.db_type == "couch" and update_time + self.backup_interval < time.time():
                self.logging.info("Write cache to JSON ... " + str(self.backup_interval))
                update_time = time.time()
                self.write_cache_to_json()
            else:
                wait = round(update_time + self.backup_interval - time.time())
                self.logging.debug("Wait to write cache to JSON ... " +
                                   str(wait) + "s")
                if wait > 20:
                    time.sleep(10)

            self.thread_control()
            self.thread_wait()

        self.logging.info("Stopped DB handler (" + self.db_type + ").")

    def connect(self, db_type=None):
        """
        (re)connect database
        """
        if db_type is None:
            db_type = self.db_type
        self.logging.info(" -> (Re)Connecting to database(s) '" + db_type + "' ...")
        self.reset_error()
        self._processing = False
        self.set_db_type(db_type)

    def set_db_type(self, db_type):
        """
        set DB type: JSON, CouchDB, BOTH
        """
        self.logging.info("  -> database handler set database type (" + db_type + ")")
        self.db_type = db_type
        if self.json is None:
            self.json = BirdhouseJSON(self.config)
        if self.db_type == "json":
            self.logging.info("  -> database handler - db_type=" + self.db_type + ".")
            return True
        elif self.db_type == "couch" or self.db_type == "both":
            if self.couch is None or not self.couch.connected:
                #self.couch = BirdhouseCouchDB(self.config, self.db_usr, self.db_pwd, self.db_server,
                #                              self.db_port_internal, self.db_basedir)
                self.couch = BirdhouseCouchDB(self.config, self.db)
            if not self.couch.connected:
                self.db_type = "json"
            self.logging.info("  -> database handler - db_type=" + self.db_type + ".")
            return True
        else:
            self.logging.error("  -> Unknown DB type (" + str(self.db_type) + ")")
            return False

    def get_db_status(self):
        """
        return db status
        """
        db_info = {}
        if self.db_type == "json":
            db_info = {
                "type": self.db_type,
                "db_connected": self.json.connected,
                "db_error": self.json.error,
                "db_error_msg": self.json.error_msg,
                "handler_error": self.error,
                "handler_error_msg": self.error_msg
            }
        elif self.db_type == "couch":
            db_info = {
                "type": self.db_type,
                "db_connected": self.couch.connected,
                "db_error": self.couch.error,
                "db_error_msg": self.couch.error_msg,
                "handler_error": self.error,
                "handler_error_msg": self.error_msg
            }
        elif self.db_type == "both":
            db_info = {
                "type": self.db_type,
                "db_connected": "couch=" + str(self.couch.connected) + " / json=" + str(self.json.connected),
                "db_connected_couch": self.couch.connected,
                "db_connected_json": self.json.connected,
                "db_error": "couch=" + str(self.couch.error) + " / json=" + str(self.json.error),
                "db_error_msg": [*self.couch.error_msg, *self.json.error_msg],
                "handler_error": self.error,
                "handler_error_msg": self.error_msg
            }
        return db_info

    def wait_if_paused(self):
        """
        wait if paused to avoid loss of data
        """
        while self._paused:
            time.sleep(0.2)

    def wait_if_process_running(self):
        """
        wait if paused to avoid loss of data
        """
        while self._processing:
            time.sleep(0.2)

    def file_path(self, config, date=""):
        """
        return complete path of config file
        """
        return os.path.join(self.directory(config, date), self.files[config])

    def directory(self, config, date=""):
        """
        return directory of config file
        """
        dir_path = os.path.join(self.main_directory, self.directories["data"], self.directories[config], date)
        if ".." in dir_path:
            elements = dir_path.split("/")
            path_new = []
            for element in elements:
                if element == ".." and len(path_new) > 0:
                    path_new.pop(-1)
                else:
                    path_new.append(element)
            dir_path = ""
            for element in path_new:
                dir_path += "/" + element
            dir_path = dir_path.replace("//", "/")
        return dir_path

    def directory_create(self, config, date=""):
        """
        return directory of config file
        """
        if not os.path.isdir(self.directory(config)):
            self.logging.info("Creating directory for " + config + " ...")
            os.mkdir(self.directory(config))
            self.logging.info("OK.")

        if date != "" and not os.path.isdir(os.path.join(self.directory(config), date)):
            self.logging.info("Creating directory for " + config + " ...")
            os.mkdir(os.path.join(self.directory(config), date))
            self.logging.info("OK.")

    def exists(self, config, date=""):
        """
        check if file or DB exists
        """
        if_exists = False
        filename = self.file_path(config, date)
        self.logging.debug(filename)

        if self.db_type == "json":
            if_exists = os.path.isfile(filename)
        elif self.db_type == "couch":
            if_exists = self.couch.exists(filename)
        elif self.db_type == "both":
            if_exists = self.couch.exists(filename)
            if not if_exists:
                if_exists = os.path.isfile(filename)

        self.logging.debug("-----> Check DB exists: " + str(if_exists) + " (" + self.db_type + " | " + filename + ")")
        return if_exists

    def exists_in_cache(self, config, date=""):
        """
        check if data are available in the cache
        """
        if config in self.config_cache:
            if date == "":
                return True
            if date in self.config_cache[config]:
                return True
        return False

    def read(self, config, date=""):
        """
        read data from DB
        """
        result = {}
        filename = self.file_path(config, date)

        if self.db_type == "json":
            result = self.json.read(filename)

        elif "config.json" in filename:
            result = self.json.read(filename)

        elif self.db_type == "couch" or self.db_type == "both":

            if not self.couch.exists(filename) and self.json.exists(filename):
                result = self.json.read(filename)
                self.couch.write(filename, result, create=True)

            elif self.couch.exists(filename) and not self.json.exists(filename) and self.db_type == "both":
                result = self.couch.read(filename)
                self.json.write(filename, result)

            elif self.couch.exists(filename):
                result = self.couch.read(filename)

            if result == {}:
                result = self.json.read(filename)

        else:
            self.raise_error("Unknown DB type (" + str(self.db_type) + ")")

        return result.copy()

    def read_cache(self, config, date=""):
        """
        get date from cache, if available (else read from source)
        """
        if not birdhouse_cache_for_archive and not birdhouse_cache:
            if not birdhouse_cache:
                return self.read(config, date)
            elif (config == "backup" or config == "images") and date != "":
                return self.read(config, date)

        if config not in self.config_cache and date == "":
            self.config_cache[config] = self.read(config=config, date="")
            self.config_cache_changed[config] = False

        elif config not in self.config_cache and date != "":
            self.config_cache[config] = {}
            self.config_cache[config][date] = self.read(config=config, date=date)
            self.config_cache_changed[config + "_" + date] = False

        elif date not in self.config_cache[config] and date != "":
            self.config_cache[config][date] = self.read(config=config, date=date)
            self.config_cache_changed[config + "_" + date] = False

        if date == "":
            return self.config_cache[config].copy()
        else:
            return self.config_cache[config][date].copy()

    def write(self, config, date="", data=None, create=False, save_json=False, no_cache=False):
        """
        write data to DB
        """
        filename = ""
        try:
            self.logging.debug("Write: " + config + " / " + date + " / " + self.db_type)
            self.wait_if_paused()
            if data is None:
                self.logging.error("Write: No data given (" + str(config) + "/" + str(date) + ")")
                return
            if create:
                self.directory(config, date)
            filename = self.file_path(config, date)
            if self.db_type == "json":
                self.json.write(filename, data)
            elif self.db_type == "couch" and "config.json" in filename:
                self.couch.write(filename, data, create)
                self.json.write(filename, data)
            elif self.db_type == "couch":
                self.couch.write(filename, data, create)
                if save_json:
                    self.json.write(filename, data)
            elif self.db_type == "both":
                self.couch.write(filename, data, create)
                self.json.write(filename, data)
            else:
                self.raise_error("Unknown DB type (" + str(self.db_type) + ")")

            if birdhouse_cache and ((no_cache and self.exists_in_cache(config, date)) or not no_cache):
                self.logging.debug("Write to cache: " + config + " / " + date + " / " + self.db_type)
                self.write_cache(config, date, data)

        except Exception as e:
            self.logging.error("Error writing file " + filename + " - " + str(e))

    def write_org(self, config, date="", data=None, create=False, save_json=False, no_cache=False):
        """
        write data to DB
        """
        filename = ""
        try:
            self.logging.debug("Write: " + config + " / " + date + " / " + self.db_type)
            self.wait_if_paused()
            if data is None:
                self.logging.error("Write: No data given (" + str(config) + "/" + str(date) + ")")
                return
            if create:
                self.directory(config, date)
            filename = self.file_path(config, date)
            if self.db_type == "json":
                self.json.write(filename, data)
                self.write_cache(config, date, data)
            elif self.db_type == "couch" and "config.json" in filename:
                self.couch.write(filename, data, create)
                self.json.write(filename, data)
                self.write_cache(config, date, data)
            elif self.db_type == "couch":
                self.couch.write(filename, data, create)
                if save_json:
                    self.json.write(filename, data)
                self.write_cache(config, date, data)
            elif self.db_type == "both":
                self.couch.write(filename, data, create)
                self.json.write(filename, data)
                self.write_cache(config, date, data)
            else:
                self.raise_error("Unknown DB type (" + str(self.db_type) + ")")
        except Exception as e:
            self.logging.error("Error writing file " + filename + " - " + str(e))

    def write_copy(self, config, date="", add="copy"):
        """
        create a copy of a complete config file
        """
        if self.db_type == "json" or self.db_type == "both":
            config_file = self.file_path(config, date)
            content = self.read(config_file)
            self.write(config_file + "." + add, content)

    def write_cache(self, config, date="", data=None):
        """
        add / update date in cache
        """
        if data is None:
            return
        if date == "":
            self.config_cache[config] = data
            self.config_cache_changed[config] = True
        elif config in self.config_cache:
            self.config_cache[config][date] = data
            self.config_cache_changed[config + "_" + date] = True
        else:
            self.config_cache[config] = {}
            self.config_cache[config][date] = data
            self.config_cache_changed[config + "_" + date] = True

    def write_cache_to_json(self):
        """
        create a backup of all data in the cache to JSON files (backup if db_type == couch)
        """
        self.wait_if_process_running()
        self._processing = True

        start_time = time.time()
        self.logging.info("Create backup from cached data ...")
        for config in self.config_cache:
            if config != "backup":
                if self.config_cache_changed[config]:
                    filename = self.file_path(config=config, date="")
                    self.json.write(filename=filename, data=self.config_cache[config])
                    self.logging.info("   -> backup2json: " + config + " (" + str(round(time.time() - start_time, 1)) + "s)")
                    self.config_cache_changed[config] = False
            else:
                for date in self.config_cache[config]:
                    if config + "_" + date in self.config_cache_changed \
                            and self.config_cache_changed[config + "_" + date]:
                        filename = self.file_path(config=config, date=date)
                        self.json.write(filename=filename, data=self.config_cache[config][date])
                        self.logging.info("   -> backup2json: " + config + " / " + date +
                                          " (" + str(round(time.time() - start_time, 1)) + "s)")
                        self.config_cache_changed[config + "_" + date] = False
        self._processing = False

    def clean_all_data(self, config, date=""):
        """
        remove all entries from a database
        """
        self.wait_if_process_running()
        self._processing = True

        self.logging.info("Clean all data from database " + config + " " + date)
        self.write(config=config, date=date, data={})
        self.write_cache(config=config, date=date, data={})

        if config == "images" and date == "":

            jpg_files_01 = os.path.join(self.config.db_handler.directory(config=config, date=date), "*.jpg")
            jpg_files_02 = os.path.join(self.config.db_handler.directory(config=config, date=date), "*.jpeg")

            try:
                self.logging.info("- delete images: " + jpg_files_01)
                message = os.system("rm " + jpg_files_01)
                self.logging.debug(message)
            except Exception as e:
                self.raise_error("Could not delete image files from " +
                                 self.config.db_handler.directory(config=config, date=date) + " (" + str(e) + ")")

            try:
                self.logging.info("- delete images: " + jpg_files_02)
                message = os.system("rm " + jpg_files_02)
                self.logging.debug(message)
            except Exception as e:
                self.raise_error("Could not delete image files from " +
                                 self.config.db_handler.directory(config=config, date=date) + " (" + str(e) + ")")

        if config == "downloads":
            self.logging.info(" - delete all files in download folder ...")
            try:
                download_directory = str(birdhouse_main_directories["download"])
                command = "rm -rf " + download_directory
                os.system(command)
            except Exception as e:
                self.logging.error("Couldn't delete all downloads: " + str(e))

        self._processing = False

    def clean_up_cache(self, config, date=""):
        """remove data from cache"""
        if config != "" and config != "all":
            if date != "":
                del self.config_cache[config][date]
            else:
                del self.config_cache[config]
        elif config == "all":
            keys = list(self.config_cache.keys())
            for conf_key in keys:
                del self.config_cache[conf_key]
            self.logging.info("Removed all data from cache.")

    def lock(self, config, date=""):
        """
        lock file if JSON
        """
        filename = self.file_path(config, date)
        if self.db_type == "json":
            return self.json.lock(filename)

    def unlock(self, config, date=""):
        """
        lock file if JSON
        """
        filename = self.file_path(config, date)
        if self.db_type == "json":
            return self.json.unlock(filename)


class BirdhouseConfigQueue(threading.Thread, BirdhouseClass):

    def __init__(self, config, db_handler):
        """
        Initialize new thread and set inital parameters
        """
        threading.Thread.__init__(self)
        BirdhouseClass.__init__(self, class_id="config-Q", config=config)
        self.thread_set_priority(1)

        self.queue_count = None
        self.views = None
        self.db_handler = db_handler
        self.edit_queue = {"images": [], "videos": [], "backup": {}, "sensor": [], "weather": [], "statistics": []}
        self.edit_queue_in_progress = False
        self.range_queue = {"images": [], "videos": [], "backup": {}, "sensor": [], "weather": [], "statistics": []}
        self.range_queue_in_progress = False
        self.status_queue = {"images": [], "videos": [], "backup": {}, "sensor": [], "weather": [], "statistics": []}
        self.status_queue_in_progress = False
        self.queue_timeout = 25
        self.queue_wait = 5
        self.queue_wait_max = 30
        self.queue_wait_min = 5
        self.queue_wait_duration = 0

    def run(self):
        """
        create videos and process queue.
        """
        self.logging.info("Starting config queue ...")

        config_files = ["images", "videos", "backup", "sensor", "weather", "statistics"]
        start_time = time.time()
        start_time_2 = time.time()
        check_count_entries = 0
        while self._running:
            update_views = False
            count_entries = 0
            count_files = 0
            active_files = []

            if start_time + self.queue_wait < time.time():
                self.logging.debug("... Check Queue (" + str(self.queue_wait) + "s)")
                self.logging.debug("    ... edit:   " + str(len(self.edit_queue)))
                self.logging.debug("    ... range:  " + str(len(self.range_queue)))
                self.logging.debug("    ... status: " + str(len(self.status_queue)))

                start_time = time.time()

                # check first if entries are available
                entries_available = False
                for config_file in config_files:
                    if config_file != "backup" and not entries_available:
                        if (config_file in self.edit_queue and len(self.edit_queue[config_file]) > 0) or \
                                (config_file in self.status_queue and len(self.status_queue[config_file]) > 0):
                            entries_available = True
                    elif not entries_available:
                        for date in self.edit_queue["backup"]:
                            if len(self.edit_queue["backup"][date]) > 0:
                                entries_available = True
                        for date in self.status_queue["backup"]:
                            if len(self.status_queue["backup"][date]) > 0:
                                entries_available = True

                if entries_available:
                    self.logging.debug("... Entries available in the queue (" +
                                       str(round(time.time() - start_time, 2)) + "s)")

                    # Check if DB connection
                    wait_for_db = 0
                    while not self.db_handler.get_db_status()["db_connected"]:
                        self.logging.warning("Waiting for DB Connection ...")
                        wait_for_db += 1
                        if wait_for_db > 6:
                            self.db_handler.connect(self.db_handler.db_type)
                        time.sleep(5)

                    if self.execute_edit_queue():
                        update_views = True
                    if self.execute_status_queue():
                        update_views = True

                    check_count_entries += count_entries
                    self.logging.debug("Queue execution: wrote " + str(count_entries) + " entries to " +
                                       str(count_files) + " config files (" + str(round(time.time() - start_time, 2)) +
                                       "s)")

                    self.queue_wait_duration = time.time() - start_time
                    if self.queue_wait < self.queue_wait_duration:
                        if self.queue_wait < self.queue_wait_max:
                            self.queue_wait += 3
                            self.logging.warning("Writing entries from queue takes longer than expected: " +
                                                 str(self.queue_wait_duration) + "s. Check DB configuration!")
                            self.logging.warning("-> extended waiting time: " + str(self.queue_wait) + "s")
                        else:
                            self.logging.error("Writing entries from queue takes MUCH longer than expected. " +
                                               "The queue may be is blocked and server is slowed down!")

                    elif self.queue_wait - 3 > self.queue_wait_duration:
                        if self.queue_wait + 3 < self.queue_wait_min:
                            self.queue_wait -= 3

                        time.sleep(1)

            if start_time_2 + self.queue_wait_max * 6 < time.time():
                self.logging.info("Queue: wrote " + str(check_count_entries) + " entries since the last " +
                                  str(self.queue_wait_max * 6) + "s.")
                check_count_entries = 0
                start_time_2 = time.time()

            if update_views:
                self.views.archive.list_update()
                self.views.favorite.list_update()
                self.views.object.list_update()

            self.thread_control()
            self.thread_wait()

        self.logging.info("Stopped Config Queue.")

    def execute_edit_queue(self):
        """
        execute entries in edit_queue if exist
        """
        config_files = ["images", "videos", "backup", "sensor", "weather", "statistics"]
        count_files = 0
        count_entries = 0
        update_views = False

        self.edit_queue_in_progress = True
        for config_file in config_files:

            if len(self.edit_queue[config_file]) == 0:
                continue
            else:
                self.logging.debug("    -> Execute edit queue: " + config_file + " ... (" +
                                   str(len(self.edit_queue[config_file])) + " entries)")

            # EDIT QUEUE: today, video (without date)
            if config_file != "backup" and len(self.edit_queue[config_file]) > 0:

                entries = self.db_handler.read_cache(config_file)
                self.db_handler.lock(config_file)

                count_files += 1
                count_edit = 0

                entries_in_queue = len(self.edit_queue[config_file]) > 0
                while entries_in_queue:
                    entries_in_queue = len(self.edit_queue[config_file]) > 0
                    if entries_in_queue:
                        self.logging.debug("Edit queue POP (1): " + str(self.edit_queue[config_file][-1]))
                        [key, entry, command] = self.edit_queue[config_file].pop()
                        count_entries += 1
                        if command == "add" or command == "edit":
                            entries[key] = entry
                            count_edit += 1
                        elif command == "delete" and key in entries:
                            del entries[key]
                            count_edit += 1
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

                self.db_handler.unlock(config_file)
                self.db_handler.write(config_file, "", entries)

            # EDIT QUEUE: backup (with date)
            elif config_file == "backup":

                for date in self.edit_queue[config_file]:

                    entry_data = self.db_handler.read_cache(config_file, date)
                    self.db_handler.lock(config_file, date)
                    entries = entry_data["files"]
                    file_info = entry_data["info"]
                    if "detection" in entry_data:
                        detection_info = entry_data["detection"]
                    else:
                        detection_info = {}

                    if date in self.edit_queue[config_file] and len(self.edit_queue[config_file][date]) > 0:
                        count_files += 1

                    count_edit = 0
                    entries_in_queue = len(self.edit_queue[config_file][date]) > 0
                    while entries_in_queue:
                        entries_in_queue = len(self.edit_queue[config_file][date]) > 0
                        if entries_in_queue:
                            self.logging.debug("Edit queue POP (2): " + str(self.edit_queue[config_file][date][-1]))
                            [key, entry, command] = self.edit_queue[config_file][date].pop()
                            count_entries += 1

                            if key == "info":
                                self.logging.info(" +++> " + command + " +++ " + key)
                                file_info = entry.copy()

                            elif key == "detection":
                                self.logging.info(" +++> " + command + " +++ " + key)
                                detection_info = entry.copy()

                            else:
                                self.logging.info(" +++> " + command + " +++ " + key)

                                if command == "add" or command == "edit":
                                    entries[key] = entry
                                    count_edit += 1
                                elif command == "delete" and key in entries:  # !!! check, if also for keep_data?!
                                    del entries[key]
                                    count_edit += 1
                                elif command == "keep_data":
                                    entries[key]["type"] = "data"
                                    if "hires" in entries[key]:
                                        del entries[key]["hires"]
                                    if "hires_size" in entries[key]:
                                        del entries[key]["hires_size"]
                                    if "lowres" in entries[key]:
                                        del entries[key]["lowres"]
                                    if "lowres_size" in entries[key]:
                                        del entries[key]["lowres_size"]
                                    if "directory" in entries[key]:
                                        del entries[key]["directory"]
                                    if "compare" in entries[key]:
                                        del entries[key]["compare"]
                                    if "favorit" in entries[key]:
                                        del entries[key]["favorit"]
                                    if "to_be_deleted" in entries[key]:
                                        del entries[key]["to_be_deleted"]

                    entry_data["files"] = entries
                    entry_data["info"] = file_info
                    entry_data["detection"] = detection_info
                    self.db_handler.unlock(config_file, date)
                    self.db_handler.write(config_file, date, entry_data)
                    if count_edit > 0 and self.views is not None:
                        self.set_status_changed(date=date, change="all")

                    update_views = True

        self.logging.debug("    -> Edit queue: " + config_file + " done.)")

        self.edit_queue_in_progress = False
        return update_views

    def execute_status_queue(self):
        """
        execute entries in status_queue if exist
        """
        config_files = ["images", "videos", "backup", "sensor", "weather", "statistics"]
        count_files = 0
        count_entries = 0
        update_views = False

        self.status_queue_in_progress = True
        for config_file in config_files:

            # STATUS QUEUE: today, video (without date)
            if config_file != "backup" and len(self.status_queue[config_file]) > 0:

                entries = self.db_handler.read_cache(config_file)
                self.db_handler.lock(config_file)

                count_files += 1
                entries_in_queue = len(self.status_queue[config_file]) > 0
                while entries_in_queue:
                    entries_in_queue = len(self.status_queue[config_file]) > 0
                    if entries_in_queue:
                        self.logging.debug("Status queue POP (1): " + str(self.status_queue[config_file][-1]))
                        [date, key, change_status, status] = self.status_queue[config_file].pop()
                        count_entries += 1

                        if change_status == "RANGE_END":
                            self.config.async_answers.append(["RANGE_DONE"])
                        elif change_status == "DELETE_RANGE_END":
                            self.config.async_answers.append(["DELETE_RANGE_DONE"])
                        elif change_status == "OBJECT_DETECTION_END":
                            self.config.async_answers.append(["OBJECT_DETECTION_DONE"])
                        elif key in entries:
                            entries[key][change_status] = status

                self.db_handler.unlock(config_file)
                self.db_handler.write(config_file, "", entries)

            # STATUS QUEUE: backup (with date)
            elif config_file == "backup":
                for date in self.status_queue[config_file]:

                    entry_data = self.db_handler.read_cache(config_file, date)
                    entries = entry_data["files"]
                    self.db_handler.lock(config_file, date)

                    if len(self.status_queue[config_file][date]) > 0:
                        count_files += 1

                    entries_in_queue = len(self.status_queue[config_file][date]) > 0
                    while entries_in_queue:
                        entries_in_queue = len(self.status_queue[config_file][date]) > 0
                        if entries_in_queue:
                            self.logging.debug("Queue POP (3): " + str(self.status_queue[config_file][date][-1]))
                            [date, key, change_status, status] = self.status_queue[config_file][date].pop()
                            count_entries += 1

                            if change_status == "RANGE_END":
                                self.config.async_answers.append(["RANGE_DONE"])
                            elif change_status == "DELETE_RANGE_END":
                                self.config.async_answers.append(["DELETE_RANGE_DONE"])
                            elif change_status == "OBJECT_DETECTION_END":
                                self.config.async_answers.append(["OBJECT_DETECTION_DONE"])
                            elif key in entries:
                                entries[key][change_status] = status

                    entry_data["files"] = entries
                    self.db_handler.unlock(config_file, date)
                    self.db_handler.write(config_file, date, entry_data)
                    self.set_status_changed(date=date, change="all")

                    update_views = True

            self.logging.debug("    -> Status queue: " + config_file + " done.)")

        self.status_queue_in_progress = False
        return update_views

    def execute_range_queue(self):
        pass

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
        #start = time.time()
        #while self.edit_queue_in_progress:  # and start + self.queue_timeout > time.time():
        #    time.sleep(0.2)
        #if time.time() - start > 1:
        #    self.logging.info("WAIT add_to_edit_queue: " + config + "|" + date + "|" + key + "|" + command +
        #                      " ... " + str(time.time() - start))

        if config != "backup":
            self.edit_queue[config].append([key, entry, command])
        elif config == "backup":
            if date not in self.edit_queue[config]:
                self.edit_queue[config][date] = []
            self.edit_queue[config][date].append([key, entry, command])

    def add_to_range_queue(self, config, date, key, entry, command):
        """
        add, remove or edit complete entry using a queue
        """
        #start = time.time()
        #while self.range_queue_in_progress:  # and start + self.queue_timeout > time.time():
        #    time.sleep(0.2)
        #if time.time() - start > 1:
        #    self.logging.info("WAIT add_to_range_queue: " + config + "|" + date + "|" + key + "|" + command +
        #                      " ... " + str(time.time() - start))

        if config != "backup":
            self.range_queue[config].append([key, entry, command])
        elif config == "backup":
            if date not in self.range_queue[config]:
                self.range_queue[config][date] = []
            self.range_queue[config][date].append([key, entry, command])

    def set_status_favorite(self, param):
        """
        set / unset favorite -> redesigned
        """
        self.logging.debug("Status favorite: " + str(param))

        response = {}
        config_data = {}
        category = param["parameter"][0]

        if category == "current":
            entry_id = param["parameter"][1]
            entry_value = param["parameter"][2]
            entry_date = ""
            category = "images"
        elif category == "videos":
            entry_id = param["parameter"][1]
            entry_value = param["parameter"][2]
            entry_date = ""
        else:
            entry_date = param["parameter"][1]
            entry_id = param["parameter"][2]
            entry_value = param["parameter"][3]

        if category == "images":
            config_data = self.db_handler.read_cache(config="images")
        elif category == "backup":
            config_data = self.db_handler.read_cache(config="backup", date=entry_date)["files"]
        elif category == "videos":
            config_data = self.db_handler.read_cache(config="videos")

        response["command"] = ["mark/unmark as favorite", entry_id]
        if entry_id in config_data:
            self.add_to_status_queue(config=category, date=entry_date, key=entry_id, change_status="favorit",
                                     status=entry_value)
            if entry_value == 1:
                self.add_to_status_queue(config=category, date=entry_date, key=entry_id, change_status="to_be_deleted",
                                         status=1)
        else:
            response["error"] = "no entry found with stamp " + entry_id

        return response

    def set_status_recycle(self, param):
        """
        set / unset recycling -> redesigned
        """
        self.logging.info("Status recycle: " + str(param))

        response = {}
        config_data = {}
        category = param["parameter"][0]

        if category == "current":
            entry_id = param["parameter"][1]
            entry_value = param["parameter"][2]
            entry_date = ""
            category = "images"
        elif category == "videos":
            entry_id = param["parameter"][1]
            entry_value = param["parameter"][2]
            entry_date = ""
        else:
            entry_date = param["parameter"][1]
            entry_id = param["parameter"][2]
            entry_value = param["parameter"][3]

        if category == "images":
            config_data = self.db_handler.read_cache(config="images")
        elif category == "backup":
            config_data = self.db_handler.read_cache(config="backup", date=entry_date)["files"]
        elif category == "videos":
            config_data = self.db_handler.read_cache(config="videos")

        response["command"] = ["mark/unmark for deletion", entry_id]
        if entry_id in config_data:
            self.logging.debug("- OK " + entry_id)
            self.add_to_status_queue(config=category, date=entry_date, key=entry_id, change_status="to_be_deleted",
                                     status=entry_value)
            if entry_value == 1:
                self.add_to_status_queue(config=category, date=entry_date, key=entry_id, change_status="favorit",
                                         status=0)
        else:
            self.logging.debug("- NOT OK " + entry_id)
            response["error"] = "no entry found with stamp " + entry_id

        return response

    def set_status_recycle_threshold(self, param, which_cam):
        """
        set / unset recycling based on given threshold
        """
        self.logging.info("Start to identify RECYCLE images based on threshold ...")
        self.logging.info("- recycle threshold: " + str(param) + " / " + which_cam)

        response = {}
        category = param["parameter"][0]
        entry_date = param["parameter"][1]
        threshold = float(param["parameter"][2])
        delete = int(param["parameter"][3])

        if category == "images":
            config_data = self.db_handler.read_cache(config="images")
        elif category == "backup":
            config_data = self.db_handler.read_cache(config="backup", date=entry_date)["files"]
        else:
            config_data = {}

        self.logging.info("- category: " + str(len(config_data.keys())))

        count = 0
        for entry_id in config_data:
            entry_threshold = float(config_data[entry_id]["similarity"])
            if "camera" not in config_data[entry_id] or config_data[entry_id]["camera"] == which_cam:
                if threshold > entry_threshold:
                    self.add_to_status_queue(config=category, date=entry_date, key=entry_id,
                                             change_status="to_be_deleted", status=0)
                    count += 1
                elif "favorit" in config_data[entry_id] and int(config_data[entry_id]["favorit"]) != 1:
                    self.add_to_status_queue(config=category, date=entry_date, key=entry_id,
                                             change_status="to_be_deleted", status=1)

        self.logging.info("- threshold=" + str(threshold) + "% -> " + str(count) + " entries.")
        return response

    def set_status_recycle_range(self, param):
        """
        set / unset recycling -> range from-to
        """
        self.logging.info("Start to identify RECYCLE range ...")
        self.logging.info("Status recycle range: " + str(param))

        response = {}
        config_data = {}
        category = param["parameter"][0]

        if category == "current":
            entry_from = param["parameter"][1]
            entry_to = param["parameter"][2]
            entry_value = param["parameter"][3]
            entry_date = ""
            category = "images"
        elif category == "videos":
            entry_from = param["parameter"][1]
            entry_to = param["parameter"][2]
            entry_value = param["parameter"][3]
            entry_date = ""
        else:
            entry_date = param["parameter"][1]
            entry_from = param["parameter"][2]
            entry_to = param["parameter"][3]
            entry_value = param["parameter"][4]

        if category == "images":
            config_data = self.db_handler.read_cache(config="images")
        elif category == "backup":
            config_data = self.db_handler.read_cache(config="backup", date=entry_date)["files"]
        elif category == "videos":
            config_data = self.db_handler.read_cache(config="videos")

        last_stamp = ""
        response["command"] = ["mark/unmark for deletion", entry_from, entry_to]
        if entry_from in config_data and entry_to in config_data:

            relevant = False
            stamps = list(reversed(sorted(config_data.keys())))
            camera = config_data[entry_from]["camera"]
            for entry_id in stamps:
                if entry_id == entry_from:
                    relevant = True

                if entry_id[2:4] == "00" and entry_id[0:4] != last_stamp[0:4]:
                    last_stamp = entry_id
                    dont_delete = True
                else:
                    dont_delete = False

                if relevant and not dont_delete:
                    if config_data[entry_id]["camera"] == camera and \
                            ("type" not in config_data[entry_id] or config_data[entry_id]["type"] != "data") and \
                            ("to_be_deleted" not in config_data[entry_id] or
                             int(config_data[entry_id]["to_be_deleted"]) != 1):
                        self.logging.debug("   ... add to queue: " + entry_id)

                        self.add_to_status_queue(config=category, date=entry_date, key=entry_id,
                                                 change_status="to_be_deleted", status=1)
                        self.add_to_status_queue(config=category, date=entry_date, key=entry_id,
                                                 change_status="favorit", status=0)
                if entry_id == entry_to:
                    relevant = False
        else:
            response["error"] = "no entry found with stamp " + entry_from + "/" + entry_to

        self.add_to_status_queue(config=category, date=entry_date, key=entry_id,
                                 change_status="RANGE_END", status=0)

        self.logging.info("Send RECYCLE range to queue ...")
        return response

    def set_status_changed(self, date, change="archive", is_changed=True):
        """
        set status of an archive entry to changed - in central file and in date specific backup file
        """
        allowed_status = ["favorites", "archive", "objects"]
        if change == "all":
            status_keys = allowed_status
        elif change in allowed_status:
            status_keys = [change]
        else:
            self.logging.error("Key '"+str(change)+"' not allowed for 'set_status_changed()'.")
            return

        backup_info = self.db_handler.read("backup_info", "")
        backup_file = self.db_handler.read("backup", date)
        if "changes" not in backup_info:
            backup_info["changes"] = {}
        if "info" not in backup_file:
            backup_file["info"] = {}

        for status_key in status_keys:
            if status_key not in backup_info["changes"]:
                backup_info["changes"][status_key] = {}
            if is_changed:
                backup_info["changes"][status_key][date] = True
                backup_file["info"]["changed_"+change] = True
            elif status_key in backup_info["changes"] and date in backup_info["changes"][status_key]:
                del backup_info["changes"][status_key][date]
            if not is_changed and "info" in backup_file:
                backup_file["info"]["changed_"+change] = False
        self.db_handler.write("backup_info", "", backup_info, create=False, save_json=True, no_cache=True)

    def get_status_changed(self, date, change="archive"):
        """
        get status, if changed - from central file and from date specific backup file
        """
        return_value = False
        backup_info = self.db_handler.read("backup_info", "")
        backup_file = self.db_handler.read("backup", date)
        if "changes" in backup_info:
            if (change in backup_info["changes"] and date in backup_info["changes"][change]
                    and backup_info["changes"][change]):
                return_value = True
        if ("info" in backup_file and "changed_"+change in backup_file["info"]
                and backup_file["info"]["changed_"+change]):
            return_value = True
        self.logging.debug("get_status_changed: " + change + "/" + date + "/" + str(return_value))
        return return_value

    def entry_add(self, config, date, key, entry):
        """
        add entry to config file using the queue
        """
        self.add_to_edit_queue(config, date, key, entry, "add")

    def entry_edit(self, config, date, key, entry):
        """
        edit entry in config file using the queue
        """
        self.logging.debug("Request to edit data (" + config + "/" + date + "/" + key + ").")
        self.add_to_edit_queue(config, date, key, entry, "edit")

    def entry_delete(self, config, date, key):
        """
        delete entry from config file using the queue
        """
        self.logging.debug("Request to delete data (" + config + "/" + date + "/" + key + ").")
        self.add_to_edit_queue(config, date, key, {}, "delete")

    def entry_keep_data(self, config, date, key):
        """
        cleaning image entry keeping activity and sensor data for charts using the queue
        """
        self.logging.debug("Request to keep data and delete image reference (" + config + "/" + date + "/" + key + ").")
        self.add_to_edit_queue(config, date, key, {}, "keep_data")


class BirdhouseConfig(threading.Thread, BirdhouseClass):

    def __init__(self, param_init, main_directory):
        """
        Constructor to initialize class

        Parameters:
            param_init (dict): initial parameters
            main_directory (str): main directory (location of main script)
        """
        threading.Thread.__init__(self)
        BirdhouseClass.__init__(self, class_id="config", config=None)
        self.thread_set_priority(1)

        self.param = None
        self.config = None
        self.config_cache = {}
        self.device_signal = {}
        self.views = None
        self.queue = None
        self.db_handler = None
        self.birds = None

        self.thread_status = {}
        self.thread_ctrl = {
            "shutdown": False,
            "priority": {
                "process": False,
                "pid": ""
            }
        }

        self.update = {}
        self.update_views = {"favorite": False, "archive": False}
        self.async_answers = []
        self.async_running = False
        self.locked = {}
        self.param_init = param_init
        self.param_default = birdhouse_preset
        self.timezone = 0
        self.html_replace = {"start_date": datetime.now().strftime("%d.%m.%Y %H:%M:%S")}
        self.directories = birdhouse_directories
        self.files = birdhouse_files
        self.weather = None
        self.user_active = False
        self.user_activity_last = 0
        self.record_audio_info = {}
        self.object_detection_processing = None
        self.object_detection_progress = None
        self.object_detection_waiting = None
        self.object_detection_waiting_keys = None
        self.object_detection_build_views = False

        self.last_start = ""
        self.last_activity_cache = time.time()
        self.last_activity_empty_cache = 15 * 60

        # read or create main config file
        self.db_handler = BirdhouseConfigDBHandler(self, "json", main_directory)
        self.db_handler.start()
        self.main_directory = main_directory
        if self.db_handler.exists("main"):
            self.param = self.db_handler.read("main")
        if not self.db_handler.exists("main") or self.param == {}:
            self.main_config_create()

        # read main config, modify status info
        self.param = self.db_handler.read(config="main")
        self.timezone = float(self.param["localization"]["timezone"].replace("UTC", ""))
        self.current_day = self.local_time().strftime("%Y%m%d")
        self.html_replace = {"start_date": self.local_time().strftime("%d.%m.%Y %H:%M:%S")}
        self.logging.info("Read configuration from '" + self.db_handler.file_path("main") +
                          "' (timezone=" + str(self.timezone) + ") ...")

        # check main status information
        if "info" in self.param and "last_day_running" in self.param["info"]:
            self.last_day_running = self.param["info"]["last_day_running"]
        elif "info" not in self.param:
            self.param["info"] = {}
        if "last_day_running" not in self.param["info"]:
            self.last_day_running = self.local_time().strftime("%Y-%m-%d")
            self.param["info"]["last_day_running"] = self.last_day_running
        self.param["info"]["last_start_date"] = self.local_time().strftime("%Y-%m-%d")
        self.param["info"]["last_start_time"] = self.local_time().strftime("%H:%M:%S")
        self.db_handler.write(config="main", data=self.param)

        # read birdhouse dictionary
        self.birds = self.db_handler.json.read(os.path.join(birdhouse_main_directories["data"], birdhouse_files["birds"]))
        self.logging.debug(str(self.birds))

        # set database type if not JSON
        self.db_type = birdhouse_env["database_type"]
        if self.db_type != "json" and ("db_type" not in self.param_init or self.param_init["db_type"] != "json"):
            if self.db_handler is not None:
                self.db_handler.stop()
            self.db_handler = BirdhouseConfigDBHandler(self, self.db_type, main_directory)
            self.db_handler.start()

        self.queue = BirdhouseConfigQueue(config=self, db_handler=self.db_handler)
        self.queue.start()

        # text file handler
        self.txt_handler = BirdhouseTEXT(config=self)
        self.main_config_app()

    def run(self):
        """
        Core function (not clear what to do yet)
        """
        self.logging.info("Starting config handler (" + self.main_directory + ") ...")

        count = 0
        self.param = self.db_handler.read("main")
        self.param["path"] = self.main_directory

        if "weather" not in self.param_init or self.param_init["weather"] is not False:
            self.weather = BirdhouseWeather(config=self)
            self.weather.start()
        elif not self.weather and self.weather is not None:
            self.weather.stop()
            self.weather = False
        else:
            self.weather = False

        while self._running:

            # check if data has change and old data shall be removed
            if birdhouse_env["database_cleanup"]:
                date_today = self.local_time().strftime("%Y-%m-%d")
                if date_today != self.last_day_running:
                    self.logging.info("-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.")
                    self.logging.info("Date changed: " + self.last_day_running + " -> " + date_today)
                    self.logging.info("-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.")
                    self.db_handler.clean_all_data(config="images")
                    self.db_handler.clean_all_data(config="sensor")
                    self.db_handler.clean_all_data(config="weather")
                    self.db_handler.clean_all_data(config="downloads")
                    self.param["info"]["last_day_running"] = date_today
                    self.last_day_running = date_today
                    self.db_handler.write(config="main", date="", data=self.param)
                    time.sleep(2)

            # check when last active access via app has been done -> delete cache from time to time
            if self.last_activity_cache + self.last_activity_empty_cache < time.time():
                self.db_handler.clean_up_cache("all")
                self.last_activity_cache = time.time()

            # check if DB reconnect ist required
            connected = self.db_handler.get_db_status()["db_connected"]
            messages = len(self.db_handler.get_db_status()["db_error_msg"])
            if not connected or messages >= 5:
                time.sleep(5)
                self.db_handler.connect()

            # check if system is paused
            if self._paused and count == 0:
                if count == 0:
                    self.logging.info("Writing config files is paused ...")
                    count += 1
            elif not self._paused:
                count = 0
                if self.weather is not False:
                    self.weather.active(self.param["localization"]["weather_active"])

            self.thread_control()
            self.thread_wait()

        self.logging.info("Stopped config handler.")

    def stop(self):
        """
        Core function (not clear what to do yet)
        """
        self.queue.stop()
        self.db_handler.stop()
        self._running = False

    def pause(self, command):
        """
        pause all writing processes (under construction)
        """
        self._paused = command

    def reload(self):
        """
        Reload main configuration
        """
        self.param = self.db_handler.read("main")

    def main_config_edit(self, config, config_data, date=""):
        """
        change configuration base on dict in form
        dict["key1:ey2:key3"] = "value"
        """
        self.logging.info("Change configuration ... " + config + "/" + date + " ... " + str(config_data))
        param = self.db_handler.read(config, date)
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
            elif data_type == "string":
                value = value
            elif data_type == "json":
                try:
                    value = json.loads(value)
                except Exception as e:
                    self.logging.error("Could not load as JSON: " + str(e))

            if "-dev-" in str(value):
                value = value.replace("-dev-", "/dev/")

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
        self.db_handler.write(config, date, param)

        if config == "main":
            self.param = self.db_handler.read(config, date)
            # self.db_handler.set_db_type(db_type=self.param["server"]["database_type"])
            self.db_handler.set_db_type(db_type=birdhouse_env["database_type"])

            for key in self.update:
                self.update[key] = True

            if self.weather is not False and "weather:location" in config_data:
                self.logging.info(
                    "Update weather config and lookup GPS data: '" + self.param["weather"]["location"] + "'.")
                self.weather.update = True
                self.param["weather"] = self.weather.get_gps_info(self.param["weather"])
                self.db_handler.write(config, date, self.param)

        self.timezone = float(self.param["localization"]["timezone"].replace("UTC", ""))

    def main_config_create(self):
        """
        create a new main config file if not exists
        """
        directory = os.path.join(self.main_directory, self.directories["data"])
        filename = os.path.join(directory, self.files["main"])

        self.logging.info("Create main config file (" + filename + ") ...")
        self.db_handler.unlock("main")
        self.db_handler.write("main", "", self.param_default)

        time.sleep(1)
        self.param = self.db_handler.read("main")
        if self.param != {}:
            self.logging.info("OK.")
        else:
            self.logging.error("Could not create main config file, check if directory '" +
                               directory + "' is writable.")
            sys.exit('Error creating main config file')

    def main_config_app(self):
        """
        create / overwrite configuration file of app
        """
        filename = os.path.join(birdhouse_client_presets["directory"], birdhouse_client_presets["filename"])
        self.txt_handler.write(filename, birdhouse_client_presets["content"])
        self.logging.info("Write App config file: " + filename)
        self.logging.debug(birdhouse_client_presets["content"])

    def local_time(self):
        """
        return time that includes the current timezone
        """
        date_tz_info = timezone(timedelta(hours=self.timezone))
        return datetime.now(date_tz_info)

    def force_shutdown(self):
        """
        shut down main services and then exit -> if docker, then restart will follow
        Final kill is done in the server component -> StreamingHandler.do_GET
        """
        if self._running:
            self.logging.info("STOPPING THE RUNNING THREADS ...")
            self.thread_ctrl["shutdown"] = True
            self.stop()

    def if_new_day(self) -> bool:
        """
        check if it's a new day
        """
        check_day = self.local_time().strftime("%Y%m%d")
        if check_day != self.current_day:
            self.logging.info("-----------------------------------------------------------")
            self.logging.info(" NEW DAY STARTED: " + self.current_day + " -> " + check_day)
            self.logging.info("-----------------------------------------------------------")
            self.current_day = self.local_time().strftime("%Y%m%d")
            return True
        else:
            return False

    def user_activity(self, cmd="get", param=""):
        """
        set user activity
        """
        if cmd == "get" and param != "" and param not in ["status", "last_answer"]:
            self.last_activity_cache = time.time()

        if cmd == "set":
            self.user_activity_last = self.local_time().timestamp()
            self.user_active = True
            self.last_activity_cache = time.time()
            return True

        elif cmd == "get" and self.user_activity_last + 60 > self.local_time().timestamp():
            return True


        self.user_active = False
        return False

    def set_views(self, views):
        """
        set handler for views
        """
        self.views = views
        self.queue.views = views

    def set_device_signal(self, device, key, value):
        """
        set device signal
        """
        if device not in self.device_signal:
            self.device_signal[device] = {}
        self.device_signal[device][key] = value

    def get_device_signal(self, device, key):
        """
        check device signal
        """
        if device in self.device_signal and key in self.device_signal[device]:
            return self.device_signal[device][key]
        else:
            return False

    def get_db_status(self):
        """
        return DB status
        """
        return self.db_handler.get_db_status()

    # !!! leads to an error ?!
    def get_changes(self, category=""):
        """
        get changes documented in backup_info
        """
        if self.db_handler.exists("backup_info", ""):
            entries = self.db_handler.read("back_info", "")
            if "changes" in entries and category != "" and category in entries["changes"]:
                return entries["changes"][category]
            else:
                return entries["changes"]
        return {}

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
