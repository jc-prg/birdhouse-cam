import os
import sys
import time
import json
import threading
from pympler import asizeof

from datetime import datetime, timezone, timedelta
from shutil import which

from modules.presets import *
from modules.weather import BirdhouseWeather
from modules.bh_database import BirdhouseCouchDB, BirdhouseJSON, BirdhouseTEXT
from modules.bh_class import BirdhouseClass
from modules.image import BirdhouseImageSupport


class BirdhouseConfigDBHandler(threading.Thread, BirdhouseClass):
    """
    Class to handle DB connect, to read, write, and cache data
    """

    def __init__(self, config, db_type="json", main_directory=""):
        """
        Constructor to initialize class.

        Args:
             config (modules.config.BirdhouseConfig): reference to main configuration handler
             db_type (str): database type (json, couch, both)
             main_directory (str): root directory of the server
        """
        threading.Thread.__init__(self)
        BirdhouseClass.__init__(self, class_id="DB-handler", config=config)
        self.thread_set_priority(1)

        self.db = birdhouse_couchdb
        self.backup_interval = 60 * 15
        self.directories = birdhouse_directories
        self.directories_complete = birdhouse_dir_to_database
        self.files = birdhouse_files
        self.main_directory = main_directory

        self.json = None
        self.couch = None
        self.db_type = None
        self.db_status_cache = {}
        self.db_status_interval = 15
        self.set_db_type(db_type)

        self.cache_active = birdhouse_env["database_cache"]
        self.cache_archive_active = birdhouse_env["database_cache_archive"]
        self.config_cache = {}
        self.config_cache_changed = {}
        self.config_cache_size = {"all": 0.0, "images": 0.0}
        self.config_cache_size_max = 20 * 1024 * 1024
        self.config_cache_size_update = time.time()

    def run(self):
        """
        if db_type == json, create a backup regularly
        """
        time_cache2json = time.time()
        time_cache_update = time.time()

        self.logging.info("Starting DB handler (" + self.db_type + "|" + self.main_directory + ") ...")
        while self._running:

            if self.db_type == "couch" and time_cache2json + self.backup_interval < time.time():
                self.logging.info("Write cache to JSON ... " + str(self.backup_interval))
                time_cache2json = time.time()
                self.write_cache_to_json()

            if time_cache_update + self.db_status_interval < time.time():
                time_cache_update = time.time()
                self.get_db_status(cache=False)

            if self.config_cache_size["all"] > self.config_cache_size_max:
                self.logging.info("Clean up cache ...")
                self.clean_up_cache("all")

            self.thread_control()
            self.thread_wait()

        self.logging.info("Stopped DB handler (" + self.db_type + ").")

    def connect(self, db_type=None):
        """
        (re)connect database

        Args:
            db_type (str): database type (json, couch, both)
        """
        if db_type is None:
            db_type = self.db_type
        self.logging.info(" -> (Re)Connecting to database(s) '" + db_type + "' ...")
        self.reset_error()
        self._processing = False
        self.set_db_type(db_type)

    def get_cache_size(self, part="all"):
        """
        get size of cache in Byte (updated every 20 seconds)

        Returns:
            float: size of cache in Byte
        """
        if self.config_cache_size_update + 20 < time.time():
            self.config_cache_size["all"] = asizeof.asizeof(self.config_cache)

            if "images" in self.config_cache:
                self.config_cache_size["images"] = asizeof.asizeof(self.config_cache["images"])
            if "backup" in self.config_cache:
                self.config_cache_size["backup"] = asizeof.asizeof(self.config_cache["backup"])
            self.config_cache_size_update = time.time()

        self.logging.debug("Cache keys: " + str(self.config_cache.keys()))

        if part in self.config_cache_size:
            return self.config_cache_size[part]
        else:
            return 0.0

    def get_db_list(self):
        """
        get list of available databases

        Returns:
            list: list of available databases (json, couch - depending on db type)
        """
        db_list = {"json": [], "couch": []}
        if self.db_type == "json":
            db_list["json"] = self.json.get_db_list()
        elif self.db_type == "couch":
            db_list["json"] = self.json.get_db_list()
            db_list["couch"] = self.couch.get_db_list()
        elif self.db_type == "both":
            db_list["json"] = self.json.get_db_list()
            db_list["couch"] = self.couch.get_db_list()
        return db_list

    def set_db_type(self, db_type):
        """
        set DB type: JSON, CouchDB, BOTH

        Args:
            db_type (str): database type (json, couch, both)
        """
        self.logging.info("  -> database handler set database type (" + db_type + ")")
        self.db_type = db_type
        if self.json is None:
            self.json = BirdhouseJSON(self.config)
        if self.db_type == "json":
            self.logging.info("  -> database handler - db_type=" + self.db_type + ".")
            return True
        elif self.db_type == "couch" or self.db_type == "both":
            if self.couch is None or not self.couch.connected or self.couch.error:
                self.couch = BirdhouseCouchDB(self.config, self.db)
            if not self.couch.connected:
                self.db_type = "json"
            self.logging.info("  -> database handler - db_type=" + self.db_type + ".")
            return True
        else:
            self.logging.error("  -> Unknown DB type (" + str(self.db_type) + ")")
            return False

    def get_db_status(self, cache=True):
        """
        return db status

        Returns:
            dict: database status (type, db_connected, db_error, db_error_msg, handler_error, handler_error_msg)
        """
        update_start = time.time()
        if cache and self.db_status_cache != {}:
            return self.db_status_cache
        else:
            db_info = {}
            if self.db_type == "json":
                db_info = {
                    "type": self.db_type,
                    "cache_size": self.get_cache_size(),
                    "cache_active": self.cache_active,
                    "cache_archive_active": self.cache_archive_active,
                    "db_connected": self.json.connected,
                    "db_error": self.json.error,
                    "db_error_msg": self.json.error_msg,
                    "db_locked_json": self.json.amount_locked(),
                    "db_waiting_json": self.json.waiting_time,
                    "handler_error": self.error,
                    "handler_error_msg": self.error_msg
                }
            elif self.db_type == "couch":
                db_info = {
                    "type": self.db_type,
                    "cache_size": self.get_cache_size(),
                    "cache_active": self.cache_active,
                    "cache_archive_active": self.cache_archive_active,
                    "db_connected": self.couch.connected,
                    "db_error": self.couch.error,
                    "db_error_msg": self.couch.error_msg,
                    "handler_error": self.error,
                    "handler_error_msg": self.error_msg
                }
            elif self.db_type == "both":
                connected = (self.couch.connected and self.json.connected)
                db_info = {
                    "type": self.db_type,
                    "cache_size": self.get_cache_size(),
                    "cache_active": self.cache_active,
                    "cache_archive_active": self.cache_archive_active,
                    "db_connected": connected,
                    "db_connected_info": "couch=" + str(self.couch.connected) + " / json=" + str(self.json.connected),
                    "db_connected_couch": self.couch.connected,
                    "db_connected_json": self.json.connected,
                    "db_locked_json": self.json.amount_locked(),
                    "db_error": "couch=" + str(self.couch.error) + " / json=" + str(self.json.error),
                    "db_error_msg": [self.couch.error_msg, self.json.error_msg],
                    "handler_error": self.error,
                    "handler_error_msg": self.error_msg
                }
            self.db_status_cache = db_info.copy()
            self.config.set_processing_performance("config", "db_status", update_start)
            return db_info

    def get_db_config_date(self, filename="", db_key=""):
        """
        get config and date from database by given filename or db_key

        Args:
            filename: filename of JSON database file
            db_key: database key of couch db (if filename is not given)

        Returns:
            [str, str]: config and date of database
        """
        if filename == "" and db_key != "":
            pass

        elif filename != "" and db_key == "":
            [db_key, date] = self.couch.filename2keys(filename)

        return ["", ""]

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

        Args:
            config (str): database name
            date (str): date of database if required (format: YYYYMMDD)
        Returns:
            str: path of database file
        """
        if config in self.files:
            return os.path.join(self.directory(config, date), self.files[config])
        else:
            self.logging.warning("Could not find a path for '" + config + "/" + date + "'.")
            return ""

    def directory(self, config, date="", include_main=True):
        """
        return directory of config file

        Args:
            config (str): database name
            date (str): date of database if required (format: YYYYMMDD)
            include_main (bool): include main directory for an absolute path
        Returns:
            str: directory of database file
        """
        if config == "images" and date == "" and date != "EMPTY":
            date = self.directories["today"]
        elif config == "today":
            config = "images"
            date = self.directories["today"]
        elif date == "EMPTY":
            date = ""

        if config in self.directories:
            if include_main:
                dir_path = os.path.join(self.main_directory, self.directories["data"], self.directories[config], date)
            else:
                dir_path = os.path.join(self.directories[config], date)
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
        else:
            self.logging.error("Directory doesn't exist in self.directories: " + config)
            if include_main:
                return os.path.join(self.main_directory, self.directories["data"])
            else:
                return ""

    def directory_create(self, config, date=""):
        """
        create directory for database file if not exists

        Args:
            config (str): database name
            date (str): date of database if required (format: YYYYMMDD)
        """
        if not os.path.isdir(self.directory(config, "EMPTY")):
            self.logging.info("Creating directory for " + config + " ...")
            os.mkdir(self.directory(config, "EMPTY"))
            self.logging.info("OK.")

        if config == "images" and not os.path.isdir(self.directory(config)):
            self.logging.info("Creating directory for " + config + "/" + birdhouse_directories["today"] + " ...")
            os.mkdir(self.directory(config))
            self.logging.info("OK.")

        if date != "" and not os.path.isdir(self.directory(config, date)):
            self.logging.info("Creating directory for " + config + " ...")
            os.mkdir(self.directory(config, date))
            self.logging.info("OK.")

    def exists(self, config, date="", db_type=""):
        """
        check if file or DB exists

        Args:
            config (str): database name
            date (str): date of database if required (format: YYYYMMDD)
            db_type (str): type of database if not current settings (couch, json, both)
        Returns:
            bool: status if database exists
        """
        if_exists = False
        filename = self.file_path(config, date)
        self.logging.debug("-----> Check DB exists: " + filename)

        if db_type == "":
            db_type = self.db_type
        if self.couch is None and db_type != "json":
            self.logging.debug("DB type '" + db_type + "' is currently not available, switch to 'json'.")
            db_type = "json"

        if db_type == "json":
            if_exists = os.path.isfile(filename)
        elif db_type == "couch":
            if_exists = self.couch.exists(filename)
        elif db_type == "both":
            if_exists = self.couch.exists(filename)
            if not if_exists:
                if_exists = os.path.isfile(filename)

        self.logging.debug("-----> Check DB exists: " + str(if_exists) + " (" + db_type + " | " + filename + ")")
        return if_exists

    def exists_in_cache(self, config, date=""):
        """
        check if data are available in the cache

        Args:
            config (str): database name
            date (str): date of database if required (format: YYYYMMDD)
        Returns:
            bool: status if database is available in the cache already
        """
        if config in self.config_cache:
            if date == "":
                return True
            if date in self.config_cache[config]:
                return True
        return False

    def read(self, config="", date="", filename="", write_other=True, db_type=""):
        """
        read data from database (for all db types)

        Args:
            config (str): database name
            date (str): date of database if required (format: YYYYMMDD)
            filename (str): filename of database file (if not specified, use config name)
            write_other (bool): write other data to other DB type if type is couch or both
            db_type (str): type of database if not current settings (couch, json, both)
        Returns:
            dict: complete data from database
        """
        result = {}
        if db_type == "":
            db_type = self.db_type
        if self.couch is None and db_type != "json":
            self.logging.debug("DB type '" + db_type + "' is currently not available, switch to 'json'.")
            db_type = "json"

        if filename == "" and config != "":
            self.logging.debug("Reading data from database " + config + " / " + date + " (config) ...")
            filename = self.file_path(config, date)
        elif filename != "" and config == "":
            self.logging.debug("Reading data from database " + filename + " (filename) ...")
        elif filename != "" and config != "":
            self.logging.warning("No DB specified to read data from!")
            return result

        if db_type == "json":
            result = self.json.read(filename)

        elif "config.json" in filename:
            result = self.json.read(filename)

        elif write_other and db_type == "couch" or db_type == "both":

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

        elif db_type == "couch":
            result = self.couch.read(filename)

        else:
            self.raise_error("Unknown DB type (" + str(db_type) + "|" + self.db_type + ")")

        return result.copy()

    def read_cache(self, config, date=""):
        """
        get date from cache, if available (else read from source)

        Args:
            config (str): database name
            date (str): date of database if required (format: YYYYMMDD)
        Returns:
            dict: complete data from database in cache
        """
        if not self.cache_active:
            return self.read(config, date)

        elif not self.cache_active and date != "" and config == "images":
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
        write data to database (for all types)

        Args:
            config (str): database name
            date (str): date of database if required (format: YYYYMMDD)
            data (dict): complete data for database
            create (bool): if true create database if doesn't exists
            save_json (bool): if true write data into JSON database (even if type is couch)
            no_cache (bool): if true don't update data in the cache
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
                self.json.write(filename, data, create)
                self.logging.debug("   -> write2json: " + config + " | " + filename)
            elif self.db_type == "couch" and "config.json" in filename:
                self.couch.write(filename, data, create)
                self.json.write(filename, data, create)
                self.logging.debug("   -> write2both: " + config + " | " + filename)
            elif self.db_type == "couch":
                self.couch.write(filename, data, create)
                self.logging.debug("   -> write2couch: " + config + " | " + filename)
                if save_json:
                    self.json.write(filename, data, create)
            elif self.db_type == "both":
                self.couch.write(filename, data, create)
                self.json.write(filename, data, create)
                self.logging.debug("   -> write2both: " + config + " | " + filename)
            else:
                self.raise_error("Unknown DB type (" + str(self.db_type) + ")")

            if birdhouse_cache and ((no_cache and self.exists_in_cache(config, date)) or not no_cache):
                self.logging.debug("Write to cache: " + config + " / " + date + " / " + self.db_type)
                self.write_cache(config, date, data)

        except Exception as e:
            self.logging.error("Error writing file " + filename + " - " + str(e))

    def write_copy(self, config, date="", add="copy"):
        """
        create a copy of a complete of the JSON database file if type is json or both

        Args:
            config (str): database name
            date (str): date of database if required (format: YYYYMMDD)
            add (dict): string to be added to the filename (default = "copy")
        """
        if self.db_type == "json" or self.db_type == "both":
            config_file = self.file_path(config, date)
            content = self.read(config_file)
            self.write(config_file + "." + add, content)

    def write_cache(self, config, date="", data=None):
        """
        add / update date in cache

        Args:
            config (str): database name
            date (str): date of database if required (format: YYYYMMDD)
            data (dict): complete data for database
        """
        if data is None or not self.cache_active:
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

        count = 0
        start_time = time.time()
        self.logging.debug("Create backup from cached data ...")
        for config in self.config_cache:
            count += 1
            if config != "backup" and config in self.config_cache_changed:
                filename = self.file_path(config=config, date="")
                self.json.write(filename=filename, data=self.config_cache[config])
                self.logging.debug("   -> backup2json: " + config + " (" + str(round(time.time() - start_time, 1)) + "s)")
                self.config_cache_changed[config] = False
            elif config in self.config_cache_changed:
                for date in self.config_cache[config]:
                    if config + "_" + date in self.config_cache_changed \
                            and self.config_cache_changed[config + "_" + date]:
                        filename = self.file_path(config=config, date=date)
                        self.json.write(filename=filename, data=self.config_cache[config][date])
                        self.logging.debug("   -> backup2json: " + config + " / " + date +
                                          " (" + str(round(time.time() - start_time, 1)) + "s)")
                        self.config_cache_changed[config + "_" + date] = False
        self.logging.info(f"Wrote {count} databases as backup to JSON files.")
        self._processing = False

    def clean_all_data(self, config, date=""):
        """
        remove all entries from a database

        Args:
            config (str): database name
            date (str): date of database if required (format: YYYYMMDD)
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
        """
        remove data from cache

        Args:
            config (str): database name
            date (str): date of database if required (format: YYYYMMDD)
        """
        self.logging.debug("Clean up cache for " + config + " " + date)
        if config != "" and config != "all":
            if date != "":
                del self.config_cache[config][date]
            else:
                del self.config_cache[config]
        elif config == "all":
            for key in self.config_cache_size:
                self.config_cache_size[key] = 0
            self.config_cache = {}
            self.config_cache_changed = {}
            self.config_cache_size_update = time.time()
            self.logging.info("Removed all data from cache.")

    def lock(self, config, date=""):
        """
        lock file if JSON

        Args:
            config (str): database name
            date (str): date of database if required (format: YYYYMMDD)
        Returns:
            bool: look status
        """
        filename = self.file_path(config, date)
        if self.db_type == "json":
            return self.json.lock(filename)

    def unlock(self, config, date=""):
        """
        lock file if JSON

        Args:
            config (str): database name
            date (str): date of database if required (format: YYYYMMDD)
        Returns:
            bool: lock status
        """
        filename = self.file_path(config, date)
        if self.db_type == "json":
            return self.json.unlock(filename)


class BirdhouseConfigQueue(threading.Thread, BirdhouseClass):
    """
    Class to manage queue for database access (json, couch, both)
    """

    def __init__(self, config, db_handler):
        """
        Constructor to initialize class.

        Args:
             config (modules.config.BirdhouseConfig): reference to main configuration handler
             db_handler (modules.config.BirdhouseConfigDBHandler): reference to db handler
        """
        threading.Thread.__init__(self)
        BirdhouseClass.__init__(self, class_id="config-Q", config=config)
        self.thread_set_priority(1)

        self.queue_count = None
        self.views = None
        self.db_handler = db_handler
        self.edit_queue = {"images": [], "videos": [], "backup": {}, "sensor": [], "weather": [], "statistics": [], "favorites": []}
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
        self.img_support = BirdhouseImageSupport(camera_id="", config=config)

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
                start_time = time.time()
                self.config.set_processing_performance("config", "queue", self.queue_wait + time.time())
                self.logging.debug("... Check Queue (" + str(self.queue_wait) + "s)")
                self.logging.debug("    ... edit:   " + str(len(self.edit_queue)))
                self.logging.debug("    ... range:  " + str(len(self.range_queue)))
                self.logging.debug("    ... status: " + str(len(self.status_queue)))

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
                    start_time_available = time.time()
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

                    # Check queues and write existing entries to db
                    start_time_exec = time.time()
                    if self.execute_edit_queue():
                        update_views = True
                    self.config.set_processing_performance("config", "write_1", start_time_exec)
                    if self.execute_status_queue():
                        update_views = True
                    self.config.set_processing_performance("config", "write", start_time_exec)

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

                    self.config.set_processing_performance("config", "available", start_time_available)

            if start_time_2 + self.queue_wait_max * 6 < time.time():
                self.logging.info("Queue: wrote " + str(check_count_entries) + " entries since the last " +
                                  str(self.queue_wait_max * 6) + "s.")
                check_count_entries = 0
                start_time_2 = time.time()

            if update_views:
                start_time_update = time.time()
                self.views.archive.list_update()
                self.views.favorite.list_update()
                self.views.object.list_update()
                self.config.set_processing_performance("views", "update_all", start_time_update)

            self.thread_control()
            self.thread_wait()

        self.logging.info("Stopped Config Queue.")

    def execute_edit_queue(self):
        """
        execute entries in edit_queue if exist, add/edit/keep_data/delete complete existing entries

        Returns:
            booL: view update required
        """
        config_files = ["images", "videos", "backup", "sensor", "weather", "statistics", "favorites"]
        count_files = 0
        count_entries = 0
        update_views = False

        self.edit_queue_in_progress = True
        for config_file in config_files:

            start_time = time.time()
            if len(self.edit_queue[config_file]) == 0:
                continue
            else:
                self.logging.debug("    -> Execute edit queue: " + config_file + " ... (" +
                                   str(len(self.edit_queue[config_file])) + " entries)")

            # statistic file
            if config_file == "statistics":

                entries = self.db_handler.read_cache(config_file)
                if "data" not in entries:
                    entries["data"] = {}
                if "info" not in entries:
                    entries["info"] = {}
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
                            entries["data"][key] = entry
                            count_edit += 1
                        elif command == "delete" and key in entries:
                            del entries["data"][key]
                            count_edit += 1
                        elif command == "info":
                            entries["info"] = entry
                            count_edit += 1

                self.db_handler.unlock(config_file)
                self.db_handler.write(config_file, "", entries)

            # EDIT QUEUE: favorite view
            elif config_file == "favorites":

                file_content = self.db_handler.read_cache(config_file)

                if "entries" and "groups" in file_content:
                    entries = file_content["entries"].copy()
                    groups = file_content["groups"].copy()
                    self.db_handler.lock(config_file)

                    count_files += 1
                    count_edit = 0

                    entries_in_queue = len(self.edit_queue[config_file]) > 0
                    while entries_in_queue:
                        entries_in_queue = len(self.edit_queue[config_file]) > 0
                        if entries_in_queue:
                            self.logging.debug("Edit queue POP (1): " + str(self.edit_queue[config_file][-1]))
                            [key, entry, command] = self.edit_queue[config_file].pop()
                            count_edit += 1
                            if command == "add":
                                if key not in entries:
                                    [key_date, key_time] = key.split("_")
                                    entry["category"] = "/backup/" + key_date + "/" + key_time
                                    entry["source"] = ["images", key_date]
                                    entries[key] = entry
                                group = key[0:4] + "-" + key[4:6]
                                if group not in groups:
                                    groups[group] = []
                                if key not in groups[group]:
                                    groups[group].append(key)
                            elif command == "delete":
                                if key in entries:
                                    del entries[key]
                                group = key[0:4] + "-" + key[4:6]

                                if group in groups and key in groups[group]:
                                    index = groups[group].index(key)
                                    del groups[group][index]
                                if len(groups[group]) == 0:
                                    del groups[group]

                    file_content["entries"] = entries.copy()
                    file_content["groups"] = groups.copy()

                self.db_handler.unlock(config_file)
                self.db_handler.write(config_file, "", file_content)

            # EDIT QUEUE: today, video (without date)
            elif config_file != "backup" and len(self.edit_queue[config_file]) > 0:

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
                self.config.set_processing_performance("config_queue_write", config_file, start_time)

            # EDIT QUEUE: backup (with date)
            elif config_file == "backup":

                dates_in_queue = list(self.edit_queue[config_file].keys())
                for date in dates_in_queue:

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
                                self.logging.debug(" +++> " + command + " +++ " + key)
                                file_info = entry.copy()

                            elif key == "detection":
                                self.logging.debug(" +++> " + command + " +++ " + key)
                                detection_info = entry.copy()

                            else:
                                self.logging.debug(" +++> " + command + " +++ " + key)

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

            self.config.set_processing_performance("config_queue_edit", config_file, start_time)
            self.logging.debug("    -> Edit queue: " + config_file + " done.")

        self.edit_queue_in_progress = False
        return update_views

    def execute_status_queue(self):
        """
        execute entries in status_queue if exist; change single values of existing entries

        Returns:
            booL: view update required
        """
        config_files = ["images", "videos", "backup", "sensor", "weather", "statistics"]
        count_files = 0
        count_entries = 0
        update_views = False

        self.status_queue_in_progress = True
        for config_file in config_files:

            start_time = time.time()

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
                dates_from_queue = list(self.status_queue[config_file])
                for date in dates_from_queue:

                    entry_data = self.db_handler.read_cache(config_file, date)
                    entries = entry_data["files"]
                    self.db_handler.lock(config_file, date)

                    if len(self.status_queue[config_file][date]) > 0:
                        count_files += 1

                    changes_other_than_favorite_and_delete = False
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
                                if change_status == "favorit":
                                    if "_" in key:
                                        favorite_key = key
                                    else:
                                        favorite_key = date + "_" + key
                                    if int(status) == 1:
                                        self.add_to_edit_queue("favorites", "", favorite_key, entries[key], "add")
                                    elif int(status) == 0:
                                        self.add_to_edit_queue("favorites", "", favorite_key, entries[key], "delete")

                                if change_status != "favorit" and change_status != "delete":
                                    changes_other_than_favorite_and_delete = True

                    entry_data["files"] = entries
                    self.db_handler.unlock(config_file, date)
                    self.db_handler.write(config_file, date, entry_data)

                    if changes_other_than_favorite_and_delete:
                        self.set_status_changed(date=date, change="all")
                    else:
                        self.set_status_changed(date=date, change="archive")
                        self.set_status_changed(date=date, change="objects")

                    update_views = True

            self.config.set_processing_performance("config_queue_status", config_file, start_time)
            self.logging.debug("    -> Status queue: " + config_file + " done.)")

        self.status_queue_in_progress = False
        return update_views

    def add_to_status_queue(self, config, date, key, change_status, status):
        """
        add status change to queue, e.g., used to change to_be_deleted or favorite status

        Args:
            config (str): database key
            date (str): date if image archive database (YYYYMMDD)
            key (str): key of entry to be edited
            change_status (str): parameter to be edited or specific process signals:
                                 "RANGE_END", "DELETE_RANGE_DONE", "OBJECT_DETECTION_DONE"
            status (Any): value to be set
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

        Args:
            config (str): database key
            date (str): date if image archive database (YYYYMMDD)
            key (str): key of entry to be edited
            entry (dict): modified data of the entry
            command (str): command how to deal with the entry: add, edit, delete, keep_data
        """
        if config != "backup":
            self.edit_queue[config].append([key, entry, command])
        elif config == "backup":
            if date not in self.edit_queue[config]:
                self.edit_queue[config][date] = []
            self.edit_queue[config][date].append([key, entry, command])

    def set_status_favorite(self, param):
        """
        set / unset favorite status - transform API request to queue entry

        Args:
             param (dict): parameters from API request
        Returns:
            dict: information for API response
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
            if int(entry_value) == 1:
                self.add_to_status_queue(config=category, date=entry_date, key=entry_id, change_status="to_be_deleted",
                                         status=0)
        else:
            response["error"] = "no entry found with stamp " + entry_id

        return response

    def set_status_recycle(self, param):
        """
        Set / unset recycling for single image - transform API request to queue entry

        Args:
            param (dict): parameters given via API
        Returns:
            dict: API response
        """
        self.logging.debug("Status recycle: " + str(param))

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
            if int(entry_value) == 1:
                self.add_to_status_queue(config=category, date=entry_date, key=entry_id, change_status="favorit",
                                         status=0)
        else:
            self.logging.debug("- NO ENTRY " + entry_id)
            response["error"] = "no entry found with stamp " + entry_id

        return response

    def set_status_recycle_object(self, param, which_cam):
        """
        identify RECYCLE images based on detected objects

        Args:
            param (dict): parameters given via API
            which_cam (str): id of selected camera
        Returns:
            dict: API response
        """
        response = {}
        config_data = {}
        category = param["parameter"][0]
        entry_date = param["parameter"][1]

        self.logging.info("Start to identify RECYCLE images based on detected objects ...")
        self.logging.info("- recycle object: " + category + "/" + entry_date + " / " + which_cam)
        self.logging.debug("- recycle object: " + str(param))

        if category == "images":
            config_data = self.db_handler.read_cache(config="images")
        elif category == "backup":
            config_data = self.db_handler.read_cache(config="backup", date=entry_date)["files"]

        count = 0
        for entry_id in config_data:
            self.logging.debug("..." + entry_id + " from " + category + "/" + entry_date)
            select = self.img_support.select(timestamp=entry_id, file_info=config_data[entry_id], check_detection=True,
                                             overwrite_threshold=-1, overwrite_detection_mode="object",
                                             overwrite_camera=which_cam)
            self.logging.debug("   ..." + str(select))
            if select:
                self.add_to_status_queue(config=category, date=entry_date, key=entry_id,
                                         change_status="to_be_deleted", status=0)
                count += 1
            else:
                self.add_to_status_queue(config=category, date=entry_date, key=entry_id,
                                         change_status="to_be_deleted", status=1)

        self.logging.info("- object=" + str(count) + "/" + str(len(config_data.keys())) + " entries.")
        return response

    def set_status_recycle_threshold(self, param, which_cam):
        """
        Set / unset recycling based on given threshold

        Args:
            param (dict): parameters given via API
            which_cam (str): id of selected camera
        Returns:
            dict: API response
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
            self.logging.debug("..." + entry_id)
            select = self.img_support.select(timestamp=entry_id, file_info=config_data[entry_id], check_detection=True,
                                             overwrite_detection_mode="similarity", overwrite_camera=which_cam,
                                             overwrite_threshold=threshold)
            #if select:
            #    self.add_to_status_queue(config=category, date=entry_date, key=entry_id,
            #                             change_status="to_be_deleted", status=0)
            #    count += 1
            #else:
            #    self.add_to_status_queue(config=category, date=entry_date, key=entry_id,
            #                             change_status="to_be_deleted", status=1)

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

        Args:
            param (dict): parameters given via API
        Returns:
            dict: API response
        """
        self.logging.debug("Start to identify RECYCLE range ...")
        self.logging.debug("Status recycle range: " + str(param))

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

        Args:
            date (str): date of changed database
            change (str): view that has to be recreated: archive, favorite, object
            is_changed (bool): status - True if change and False if recreation has be done
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

    def get_status_changed(self, date, change="archive", both=True):
        """
        get status, if changed - from central file and from date specific backup file

        Args:
            date (str): date of changed database
            change (str): view that has to be recreated: archive, favorite, object
            both (bool): check backup_info and individual backup file (True) or only backup_info (False)
        Returns:
            bool: change status - True if change and False if recreation has be done
        """
        return_value = False
        backup_info = self.db_handler.read_cache("backup_info", "")
        if "changes" in backup_info:
            if (change in backup_info["changes"] and date in backup_info["changes"][change]
                    and backup_info["changes"][change]):
                return_value = True
        if both:
            backup_file = self.db_handler.read("backup", date)
            if ("info" in backup_file and "changed_"+change in backup_file["info"]
                    and backup_file["info"]["changed_"+change]):
                return_value = True
        self.logging.debug("get_status_changed: " + change + "/" + date + "/" + str(return_value))
        return return_value

    def entry_add(self, config, date, key, entry):
        """
        add entry to config file using the queue

        Args:
            config (str): database key
            date (str): date of database if archive image database
            key (str): entry key of entry to be added
            entry (dict): modified entry data
        """
        self.add_to_edit_queue(config, date, key, entry, "add")

    def entry_other(self, config, date, key, entry, command):
        """
        add entry to config file using the queue

        Args:
            config (str): database key
            date (str): date of database if archive image database
            key (str): entry key of entry to be added
            entry (dict): modified entry data
            command (str): command to be executed
        """
        self.add_to_edit_queue(config, date, key, entry, command)

    def entry_edit(self, config, date, key, entry):
        """
        edit entry in config file using the queue

        Args:
            config (str): database key
            date (str): date of database if archive image database
            key (str): entry key of entry to be changed
            entry (dict): modified entry data
        """
        self.logging.debug("Request to edit data (" + config + "/" + date + "/" + key + ").")
        self.add_to_edit_queue(config, date, key, entry, "edit")

    def entry_edit_object_labels(self, command, date, key, data=""):
        """
        edit or delete labels for image entry (today or archive)

        Args:
            command (str): use "edit" (no further commands implemented yet)
            date (str): date of archived day, empty for today
            key (str): time key of image entry
            data (Any): data in the format "0::object1,1::object2,2::object3"

        Returns:
            dict: API response
        """
        entry = {}
        response = {}
        self.logging.info("Edit detection labels for '" + date + "_" + key + "': " + data)

        if date == "TODAY":
            date = ""
        entries = self.db_handler.read_cache("images", date)
        if date != "" and key in entries["files"]:
            self.logging.debug("Archive - FOUND ("+key+")")
            entry = entries["files"][key]
        elif key in entries:
            self.logging.debug("Today - FOUND ("+key+")")
            entry = entries[key]
        else:
            error_msg = "Edit labels - entry NOT FOUND ("+date+"_"+key+")"
            self.logging.warning()
            self.logging.debug(str(entries))
            response = {"result": "ERROR: " + error_msg}
            return response

        label_object_list = []
        data_list = data.split(",")
        for item in data_list:
            if not "::" in item:
                continue
            number, value = item.split("::")
            number = int(number)
            if number >= len(entry["detections"]):
                continue
            label_object = entry["detections"][number]
            if value != "DELETE":
                if value != label_object["label"]:
                    if not "label_org" in label_object:
                        label_object["label_org"] = label_object["label"]
                    label_object["label"] = value
                    label_object["confidence_org"] = label_object["confidence"]
                    label_object["confidence"] = 1.0
                label_object_list.append(label_object)
        entry["detections"] = label_object_list

        self.logging.debug("---> entry_edit_object_labels: " + str(entry))

        if date == "":
            self.add_to_edit_queue("images", date, key, entry, "edit")
        else:
            self.add_to_edit_queue("backup", date, key, entry, "edit")

        response = {"result": "OK"}
        return response

    def entry_delete(self, config, date, key):
        """
        delete entry from config file using the queue

        Args:
            config (str): database key
            date (str): date of database if archive image database
            key (str): entry key of entry to be deleted
        """
        self.logging.debug("Request to delete data (" + config + "/" + date + "/" + key + ").")
        self.add_to_edit_queue(config, date, key, {}, "delete")

    def entry_keep_data(self, config, date, key):
        """
        cleaning image entry keeping activity and sensor data for charts using the queue

        Args:
            config (str): database key
            date (str): date of database if archive image database
            key (str): entry key of entry to be changed
        """
        self.logging.debug("Request to keep data and delete image reference (" + config + "/" + date + "/" + key + ").")
        self.add_to_edit_queue(config, date, key, {}, "keep_data")


class BirdhouseConfig(threading.Thread, BirdhouseClass):

    def __init__(self, param_init, main_directory):
        """
        Constructor to initialize class

        Args:
            param_init (dict): initial parameters
            main_directory (str): main directory (location of main script)
        """
        threading.Thread.__init__(self)
        BirdhouseClass.__init__(self, class_id="config")
        self.thread_set_priority(1)

        self.birds = None
        self.config = None
        self.db_handler = None
        self.views = None
        self.weather = None
        self.queue = None
        self.statistics = None

        self.thread_status = {}
        self.thread_ctrl = {
            "shutdown": False,
            "priority": {
                "process": False,
                "pid": ""
            }
        }
        self.thread_ids = {}

        self.directories = birdhouse_directories
        self.directories_complete = birdhouse_dir_to_database
        self.directories_main = birdhouse_main_directories
        self.files = birdhouse_files

        self.config_cache = {}
        self.device_signal = {}
        self.locked = {}
        self.update = {}
        self.update_config = {}
        self.update_views = {"favorite": False, "archive": False}
        self.async_answers = []
        self.async_running = False
        self.video_frame_count = 0

        self.param = None
        self.param_init = param_init
        self.param_default = birdhouse_preset

        self.timezone = 0
        self.html_replace = {"start_date": datetime.now().strftime("%d.%m.%Y %H:%M:%S")}
        self.user_active = False
        self.user_activity_last = 0
        self.record_audio_info = {}
        self.camera_scan = {}
        self.camera_capture_active = False

        self.processing_information = {}
        self.processing_performance = {}

        self.object_detection_processing = None
        self.object_detection_progress = None
        self.object_detection_info = {}

        self.object_detection_waiting = None
        self.object_detection_waiting_keys = None
        self.object_detection_build_views = False

        self.last_start = ""
        self.measure_time = 30
        self.measure_last = time.time()
        self.last_wrote_statistics = 0

        # read or create main config file
        self.db_handler = BirdhouseConfigDBHandler(self, "json", main_directory)
        self.db_handler.start()
        self.main_directory = main_directory
        if self.db_handler.exists("main"):
            self.param = self.db_handler.read("main")
        if not self.db_handler.exists("main", "", "json") or self.param == {}:
            self.logging.warning("Main configuration doesn't exist yet (data/config.json).")
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

        # read birdhouse dictionary
        self.birds = self.db_handler.json.read(os.path.join(self.directories_main["data"], birdhouse_files["birds"]))
        self.logging.debug(str(self.birds))

        # set database type if not JSON
        self.db_type = birdhouse_env["database_type"]
        self.last_db_type = None
        if "info" in self.param and "last_db_type" in self.param["info"]:
            self.last_db_type = self.param["info"]["last_db_type"]
        self.param["info"]["last_db_type"] = self.db_type
        self.db_handler.write(config="main", data=self.param)

        if self.db_type != "json" and ("db_type" not in self.param_init or self.param_init["db_type"] != "json"):
            if self.db_handler is not None:
                self.db_handler.stop()
            self.db_handler = BirdhouseConfigDBHandler(self, self.db_type, self.main_directory)
            self.db_handler.start()

        self.queue = BirdhouseConfigQueue(config=self, db_handler=self.db_handler)
        self.queue.start()

        # text file handler
        self.txt_handler = BirdhouseTEXT(config=self)
        self.main_config_app()
        self.set_thread_id(self.id, threading.get_native_id())

    def run(self):
        """
        Run thread with core function: ensure reconnect, delete data when date changes
        """
        self.logging.info("Starting config handler (" + self.main_directory + ") ...")
        self.main_config_create_dirs()

        count = 0
        self.param = self.db_handler.read("main")
        self.param["path"] = self.main_directory
        self.main_config_db_changed()

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
                    self.db_handler.clean_all_data(config="statistics")
                    self.param["info"]["last_day_running"] = date_today
                    self.last_day_running = date_today
                    self.db_handler.write(config="main", date="", data=self.param)
                    for key in self.update_config:
                        self.update_config[key] = True
                    time.sleep(2)

            # check if DB reconnect ist required
            connected = self.db_handler.get_db_status()["db_connected"]
            messages = len(self.db_handler.get_db_status()["db_error_msg"])
            if not connected or messages >= 5:
                self.logging.info("... DB Connection: " + self.db_handler.db_type + " - " + str(connected))
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

            self.measure_status()
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

    def main_config_create_dirs(self):
        """
        create main data directories
        """
        self.logging.info("Check if data directories exist ...")
        for key in birdhouse_directories:
            path = self.db_handler.directory(key, date="", include_main=True)
            self.logging.debug("============ " + key + " = " + path)
            if not os.path.exists(path):
                self.logging.info("Create data directory: " + path)
                os.makedirs(path)

    def main_config_decompose(self, config_data, param=None):
        """
        decompose config data into a list of dictionaries

        Args:
            config_data (dict): selected vars to be changed in the format dict["key1:key2:key3"] = "value"
            param (dict): parameter to be changed

        Returns:
            dict: config data transformed to dict["key1"]["key2"]["key3"] = "value"
        """
        if param is None:
            param = {}

        data_type = ""
        difference = []
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
                value = value.replace("-dev-v4l-by-id-", "/dev/v4l/by-id/")
                value = value.replace("-dev-", "/dev/")

            try:
                if ":" not in key:
                    if param[key] != value:
                        param[key] = value
                        difference.append(key)
                elif len(keys) == 2:
                    if param[keys[0]][keys[1]] != value:
                        param[keys[0]][keys[1]] = value
                        difference.append(keys[0]+":"+keys[1])
                elif len(keys) == 3:
                    if param[keys[0]][keys[1]][keys[2]] != value:
                        param[keys[0]][keys[1]][keys[2]] = value
                        difference.append(keys[0]+":"+keys[1]+":"+keys[2])
                elif len(keys) == 4:
                    if param[keys[0]][keys[1]][keys[2]][keys[3]] != value:
                        param[keys[0]][keys[1]][keys[2]][keys[3]] = value
                        difference.append(keys[0] + ":" + keys[1] + ":" + keys[2] + ":" + keys[3])
                elif len(keys) == 5:
                    if param[keys[0]][keys[1]][keys[2]][keys[3]][keys[4]] != value:
                        param[keys[0]][keys[1]][keys[2]][keys[3]][keys[4]] = value
                        difference.append(keys[0] + ":" + keys[1] + ":" + keys[2] + ":" + keys[3] + ":" + keys[4])
                elif len(keys) == 6:
                    if param[keys[0]][keys[1]][keys[2]][keys[3]][keys[4]][keys[5]] != value:
                        param[keys[0]][keys[1]][keys[2]][keys[3]][keys[4]][keys[5]] = value
                        difference.append(keys[0] + ":" + keys[1] + ":" + keys[2] + ":" + keys[3] + ":" + keys[4] + ":" + keys[5])

            except Exception as e:
                self.logging.warning("Could not decompose keys (" + str(keys) + "): " + str(e))
                self.logging.warning("Check and add missing keys in your config file or start with a new config file.")

        return param, difference

    def main_config_edit(self, config, config_data, date="", camera=""):
        """
        change configuration base on dict in form

        Args:
            camera (str): camera id
            config (str): database name
            config_data (dict): selected vars to be changed in the format dict["key1:key2:key3"] = "value"
            date (str): date of database if required (format: YYYYMMDD)
        """
        self.logging.info("Change configuration ... " + config + "/" + date + " ... " + str(config_data))

        param = self.db_handler.read(config, date)
        param, difference = self.main_config_decompose(config_data, param.copy())

        difference_update = False
        difference_update_fields = ["devices:cameras:" + camera + ":source",
                                    "devices:cameras:" + camera + ":active",
                                    "devices:microphones:mic1:device_id",
                                    "devices:microphones:mic2:device_id"]

        self.db_handler.write(config, date, param)

        if not difference:
            self.logging.info("main-config-edit: No changes detected.")
        else:
            self.logging.info("main-config-edit: Detected changes: " + str(difference))
            for value in difference:
                if value in difference_update_fields:
                    difference_update = True
                    self.logging.info("main-config-edit: Force device reconnect (" + value + ")")
            if not difference_update:
                self.logging.info("main-config-edit: No device reconnect required (" + camera + ").")


        if config == "main":
            self.param = self.db_handler.read(config, date)
            self.db_handler.set_db_type(db_type=birdhouse_env["database_type"])

            if difference_update:
                for key in self.update:
                    self.update[key] = True
            if camera != "" and difference:
                self.update_config["camera_" + camera] = True

            for camera in self.param["devices"]["cameras"]:
                source = self.param["devices"]["cameras"][camera]["source"]
                if "video_devices_complete" in self.camera_scan and source in self.camera_scan["video_devices_complete"]:
                    source_id = self.camera_scan["video_devices_complete"][source]["bus"]
                    self.param["devices"]["cameras"][camera]["source_id"] = source_id

            self.db_handler.write("main", "", self.param)

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

    def main_config_db_changed(self):
        """
        check if db_type has changed since last start and ensure that the data
        are migrated from the old type to the new one

        JSON -> BOTH/COUCH
        - for each DB in couch, delete
        - for each DB in json migrate to couch db
        ?? maybe reload date somehow ??

        COUCH -> JSON (not implemented yet)
        - initially connect to couch (as usually not yet loaded)
        - check if JSON DB exists rewrite, if not create from couch
        - keep JSON file (as usually they are used as backup)
        """
        backup_date = self.local_time().strftime("%Y%m%d-%H%M%S")
        line = "-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-."
        if self.last_db_type != self.db_type and self.last_db_type is not None:
            self.logging.info(line)
            self.logging.info("DB type has changed: " + str(self.last_db_type) + " -> " + self.db_type)
            self.logging.debug("(data path: " + str(self.directories_main["data"]) + ")")
            self.logging.info(line)

            if self.last_db_type == "json" and self.db_type == "couch" or self.db_type == "both":
                available_databases = self.db_handler.get_db_list()
                self.logging.info("Delete all "+str(len(available_databases["couch"]))+" couch databases ...")
                for database in available_databases["couch"]:
                    if not database.startswith("_"):
                        self.logging.info("Delete old couch DB: " + database)
                        self.db_handler.couch.delete_db("", database)

                self.logging.info("Migrate all "+str(len(available_databases["json"]))+" json databases to couch databases...")
                for database in available_databases["json"]:
                    path_to_db = self.directories_main["data"] + database
                    self.logging.info("Migrate from JSON to couch DB: " + self.directories_main["data"] + "|" + database)
                    data = self.db_handler.json.read(path_to_db)
                    self.db_handler.couch.write(filename=database, data=data, create=True)
                self.logging.info(line)

            elif (self.last_db_type == "both" or self.last_db_type == "couch") and self.db_type == "json":
                couch_db_handler = BirdhouseConfigDBHandler(self, "couch", self.main_directory)
                couch_db_handler.couch.basic_directory = self.directories_main["data"]
                available_couch_db = couch_db_handler.get_db_list()
                for database in available_couch_db["couch"]:
                    for key in self.directories_complete:
                        if database.startswith(self.directories_complete[key]):
                            filename = key + ".json"
                            match = False
                            if "<DATE>" in key and database[-1].isdigit():
                                date = database.replace(self.directories_complete[key]+"_", "")
                                filename = filename.replace("<DATE>", date)
                                match = True
                            elif not "<DATE>" in key and not database[-1].isdigit():
                                date = ""
                                match = True
                            filename = self.directories_main["data"] + "/" + filename
                            if match:
                                self.logging.info("(Re)write JSON DB: " + database + " -> " + filename)
                                self.logging.info("  -> data path: " + str(self.directories_main["data"]))

                                # 1. read from couch
                                data = couch_db_handler.read(filename=filename, write_other=False).copy()
                                self.logging.debug("Read JSON DB: " + str(data))
                                # 2. write to json (rewrite / create file)
                                data_bu = self.db_handler.json.read(filename=filename).copy()
                                if filename.endswith("data/config.json"):
                                    data_bu["info"]["backup_time"] = backup_date
                                    data_bu["info"]["migration_time"] = ""
                                    data["info"]["migration_time"] = backup_date
                                    self.param = data
                                #self.db_handler.json.write(filename=filename.replace(".json", "." + backup_date + "_C.json"), data=data, create=True)
                                #self.db_handler.json.write(filename=filename.replace(".json", "." + backup_date + "_B.json"), data=data_bu, create=True)
                                self.db_handler.json.write(filename=filename, data=data, create=True)

                self.logging.warning("NOT FULLY IMPLEMENTED YET: change from " + str(self.last_db_type) + " to " + str(self.db_type))
            else:
                self.logging.debug("No migration required.")

    def local_time(self, day="today"):
        """
        return time that includes the current timezone (day="today")
        other values: yesterday,

        Returns:
            datetime: local time for the current timezone
        """
        date_tz_info = datetime.now(timezone(timedelta(hours=self.timezone)))
        date_tz_info_1 = datetime.now(timezone(timedelta(hours=self.timezone) - timedelta(days=1)))
        self.logging.debug("Local time: " + str(date_tz_info) + " / " + str(date_tz_info_1))

        if day == "yesterday":
            return date_tz_info_1
        else:
            return date_tz_info

    def local_date(self, days=0):
        """
        get current date in format YYYYMMDD with an offset of days (1 = yesterday, 2 = 2 days ago, ...)

        Returns:
            str: date in format YYYYMMDD
        """
        today = datetime.now()
        target_date = today - timedelta(days=days)
        self.logging.debug("Target date: " + str(target_date))
        return target_date.strftime('%Y%m%d')

    def force_shutdown(self):
        """
        shut down main services and then exit -> if docker, then restart will follow
        Final kill is done in the server component -> StreamingHandler.do_GET
        """
        if self._running:
            self.logging.info("STOPPING THE RUNNING THREADS ...")
            self.thread_ctrl["shutdown"] = True
            self.stop()

    def is_new_day(self):
        """
        check if it's a new day

        Returns:
            bool: status if a new date has started
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

    def is_sunrise(self, hour_offset=0, mode="exact"):
        """
        check if current time is sunrise; if weather is not available, try from cache in config file or return False

        Args:
            hour_offset (int): hour offset for sunrise, e.g., +1 or -1
            mode (str): mode how to check - available modes: "exact", "before", "after"
        Returns:
            boolean: True if weather data available and current time is sunrise time (incl. hour offset)
        """
        if self.weather is None:
            if "last_sunrise" in self.param["weather"]:
                sunrise = self.param["weather"]["last_sunrise"]
            else:
                self.logging.debug("No weather data available to check sunrise time.")
                return False
        else:
            sunrise = str(self.weather.get_sunrise())

        sunrise = sunrise.split(":")
        sunrise = str(int(sunrise[0]) + int(hour_offset)).zfill(2) + ":" + str(sunrise[1])
        local_time = str(self.local_time()).split(" ")[1].split(".")[0]
        local_time = local_time.split(":")[0] + ":" + local_time.split(":")[1]

        sunrise = int(sunrise.replace(":", ""))
        local_time = int(local_time.replace(":", ""))

        if sunrise == local_time and mode == "exact":
            self.logging.debug("It's time for sunrise (True): " + str(local_time) + " / " + str(sunrise))
            return True
        elif mode == "exact":
            self.logging.debug("No sunrise at the moment (False): " + str(local_time) + " / " + str(sunrise))
            return False
        elif sunrise > local_time and mode == "before":
            self.logging.debug("It's before sunrise (True): " + str(local_time) + " / " + str(sunrise))
            return True
        elif mode == "before":
            self.logging.debug("It's after sunrise (False): " + str(local_time) + " / " + str(sunrise))
            return False
        elif sunrise < local_time and mode == "after":
            self.logging.debug("It's after sunrise (True): " + str(local_time) + " / " + str(sunrise))
            return True
        elif mode == "after":
            self.logging.debug("It's before sunrise (False): " + str(local_time) + " / " + str(sunrise))
            return False
        else:
            self.logging.warning("Error:  " + str(mode) + " / " + str(local_time) + " / " + str(sunrise))
            return False

    def is_sunset(self, hour_offset=0, mode="exact"):
        """
        check if current time is sunset; if weather is not available try from cache in config file or return False

        Args:
            hour_offset (int): hour offset for sunset, e.g., +1 or -1
            mode (str): mode how to check - available modes: "exact", "before", "after"
        Returns:
            boolean: True if weather data available and current time is sunset time (incl. hour offset)
        """
        if self.weather is None:
            if "sunset" in self.param["weather"]:
                sunset = self.param["weather"]["sunset"]
            else:
                self.logging.debug("No weather data available to check sunset time.")
                return False
        else:
            sunset = str(self.weather.get_sunset())

        sunset = sunset.split(":")
        sunset = str(int(sunset[0]) + int(hour_offset)).zfill(2) + ":" + str(sunset[1])
        local_time = str(self.local_time()).split(" ")[1].split(".")[0]
        local_time = local_time.split(":")[0] + ":" + local_time.split(":")[1]

        sunset = int(sunset.replace(":", ""))
        local_time = int(local_time.replace(":", ""))

        if mode == "exact" and sunset == local_time:
            self.logging.debug("It's time for sunset (True):  " + str(local_time) + " / " + str(sunset))
            return True
        elif mode == "exact":
            self.logging.debug("No sunset at the moment (False):  " + str(local_time) + " / " + str(sunset))
            return False
        elif mode == "after" and local_time > sunset:
            self.logging.debug("It's after sunset (True):  " + str(local_time) + " / " + str(sunset))
            return True
        elif mode == "after":
            self.logging.debug("It's before sunset (False):  " + str(local_time) + " / " + str(sunset))
            return False
        elif mode == "before" and local_time > sunset:
            self.logging.debug("It's before sunset (True):  " + str(local_time) + " / " + str(sunset))
            return True
        elif mode == "before":
            self.logging.debug("It's after sunset (False):  " + str(local_time) + " / " + str(sunset))
            return False
        else:
            self.logging.warning("Error:  " + str(mode) + " / " + str(local_time) + " / " + str(sunset))
            return False

    def user_activity(self, cmd="get", param=""):
        """
        set user activity

        Args:
            cmd (str): options are 'get' or 'set'
            param (str): options are empty, 'status' or 'last_answer'
        Returns:
            bool: activity status
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

    def set_statistics(self, statistics):
        """
        set statistics handler to self.statistics

        Args:
            statistics: statistics handler
        """
        self.statistics = statistics
        self.measure_status(True)

    def set_views(self, views):
        """
        set handler for views

        Args:
            views (modules.views.BirdhouseViews): reference to view handler
        """
        self.views = views
        self.queue.views = views

    def set_device_signal(self, device, key, value):
        """
        set device signal

        Args:
            device (str): device id
            key (str): parameter key
            value (Any): parameter value
        """
        if device not in self.device_signal:
            self.device_signal[device] = {}
        self.device_signal[device][key] = value

    def get_device_signal(self, device, key):
        """
        check device signal

        Args:
            device (str): device id
            key (str): parameter key
        Returns:
            Any: parameter value
        """
        if device in self.device_signal and key in self.device_signal[device]:
            return self.device_signal[device][key]
        else:
            return False

    def get_db_status(self):
        """
        return DB status

        Returns:
            bool: db status
        """
        return self.db_handler.get_db_status()

    def get_changes(self, category=""):
        """
        get changes documented in backup_info

        Args:
            category (str): category of changes (favorite, archive, object)
        Returns:
            dict: list of dates where changes in the respective category have happend
        """
        if self.db_handler.exists("backup_info", ""):
            entries = self.db_handler.read("back_info", "")
            if "changes" in entries and category != "" and category in entries["changes"]:
                return entries["changes"][category]
            else:
                return entries["changes"]
        return {}

    def set_processing(self, category, subcategory, value):
        """
        set processing info to be centrally available

        Args:
            category (str): set a category
            subcategory (str): set a subcategory; use an empty string if there is none
            value (Any): set a value
        """
        if category not in self.processing_information:
            self.processing_information[category] = {}
        if subcategory == "":
            subcategory = "default"
        self.processing_information[category][subcategory] = value

    def get_processing(self, category, subcategory):
        """
        get centrally available processing information

        Args:
            category (str): use a specific category or "all" to get the bunch of processing information
            subcategory (str): use a specific subcategory or "all" to get the bunch of processing information
        Return:
            Any: values
        """
        if category == "all":
            return self.processing_information
        elif category in self.processing_information:
            if subcategory == "all":
                return self.processing_information[category]
            elif subcategory in self.processing_information[category]:
                return self.processing_information[category][subcategory]
            elif subcategory == "" and "default" in self.processing_information[category]:
                return self.processing_information[category]["default"]
            else:
                return None
        else:
            return None
        
    def set_processing_performance(self, category, object_id, start, end=None):
        """
        save performance information in a central place

        Args:
            category (str): category of performance information
            id (str): id of the object
            start (float): start time of the process
            end (float): end time of the process
        """
        if not end:
            end = time.time()
        value = end - start
        if object_id == "":
            object_id = "default"
        if category not in self.processing_performance:
            self.processing_performance[category] = {}
        if not object_id in self.processing_performance[category]:
            self.processing_performance[category][object_id] = []

        self.processing_performance[category][object_id].append(value)
        if len(self.processing_performance[category][object_id]) > 20:
            self.processing_performance[category][object_id].pop(0)
        self.processing_performance[category]["last_update"] = str(self.local_time()).split(".")[0]

    def get_processing_performance(self, category=""):
        """
        Returns average processing performance information of the last 20 or all existing values

        Args:
            category (str): category of performance information

        Returns:
            dict: list of performance information
        """
        round_digits = 4
        averaged_processing_performance = {}

        for key in self.processing_performance:
            if key not in averaged_processing_performance:
                averaged_processing_performance[key] = {}

            for object_id in self.processing_performance[key]:
                if object_id != "last_update":
                    averaged_processing_performance[key][object_id] = round(sum(self.processing_performance[key][object_id]) / len(self.processing_performance[key][object_id]), round_digits)
                else:
                    averaged_processing_performance[key][object_id] = self.processing_performance[key][object_id]

        if category == "":
            return averaged_processing_performance

        elif category in self.processing_performance:
            return averaged_processing_performance[category]

        else:
            self.logging.debug("get_processing_performance: category '" + str(category) + "' not found.")
            return -1

    def get_queue_size(self):
        """
        Calculate the size of the config queues

        Returns:
            dict: size of the config queues
        """
        queue_size = {"status" : 0, "edit" : 0, "range" : 0}
        for key in self.queue.edit_queue:
            queue_size["edit"] += len(self.queue.edit_queue[key])
        for key in self.queue.range_queue:
            queue_size["range"] += len(self.queue.range_queue[key])
        for key in self.queue.status_queue:
            queue_size["status"] += len(self.queue.status_queue[key])
        return queue_size

    def measure_status(self, init=False):
        """
        add db queue and db cache size to statistics

        Args:
            init (bool): initialize the statistics
        """
        if init:
            self.statistics.register("config_queue_db", "DB Queue")
            self.statistics.register("config_queue_wait", "Queue Wait [s]")
            self.statistics.register("config_queue_write", "Queue Write [s]")
            self.statistics.register("config_cache_size", "Cache [MB]")
            self.statistics.register("config_cache_size_images", "Cache images [MB]")
            self.statistics.register("config_cache_size_backup", "Cache archive [MB]")
            self.statistics.register("srv_api_status", "API Response Status [s]")
            self.statistics.register("config_img_video", "Video frames [fps]")

        else:
            if self.statistics and self.measure_last + self.measure_time < time.time():
                self.measure_last = time.time()
                queues = self.get_queue_size()
                queue_size = 0
                for key in queues:
                    queue_size += queues[key]
                self.statistics.set("config_queue_db", queue_size)
                config_queue_write = self.get_processing_performance("config_queue_write")
                if config_queue_write != -1 and "images" in config_queue_write:
                    self.statistics.set("config_queue_write", config_queue_write["images"])
                self.statistics.set("config_queue_wait", self.queue.queue_wait)
                self.statistics.set("config_cache_size", self.db_handler.get_cache_size("all") / 1024 / 1024)
                self.statistics.set("config_cache_size_images", self.db_handler.get_cache_size("images") / 1024 / 1024)
                self.statistics.set("config_cache_size_backup", self.db_handler.get_cache_size("backup") / 1024 / 1024)
                if self.get_processing_performance("api_GET") != -1 and "status" in self.get_processing_performance("api_GET"):
                    self.statistics.set("srv_api_status", self.get_processing_performance("api_GET")["status"])
                self.statistics.set("config_img_video", self.video_frame_count / self.statistics.get_interval())
                self.video_frame_count = 0

    def set_thread_id(self, id, name):
        self.thread_ids[id] = name
