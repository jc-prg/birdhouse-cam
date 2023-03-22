import os
import sys
import time
import logging
import json
import codecs
import threading
import couchdb
import requests

from datetime import datetime, timezone, timedelta
from modules.weather import BirdhouseWeather
from modules.presets import *


class BirdhouseConfigCouchDB(object):

    def __init__(self, config, db_usr, db_pwd, db_server, db_port, base_dir):
        """
        initialize
        """
        self.locked = {}
        self.config = config
        self.connected = False
        self.changed_data = False
        self.database = None
        self.basic_directory = base_dir
        self.db_url = "http://"+db_usr+":"+db_pwd+"@"+db_server+":"+str(db_port)+"/"
        self.create_revisions = False

        self.logging = logging.getLogger("DB-couch")
        self.logging.setLevel(birdhouse_loglevel_module["DB-couch"])
        self.logging.addHandler(birdhouse_loghandler)
        self.logging.info("Starting DB handler CouchDB ("+self.db_url+") ...")

        self.database_definition = birdhouse_databases
        self.database_translation = birdhouse_dir_to_database

        self.connected = self.connect()
        self.error = False
        self.error_msg = []

    def connect(self):
        """
        connect to database incl. retry
        """
        connects2db = 0
        max_connects = 5
        while connects2db < max_connects + 1:

            if connects2db == 8 or connects2db == 15 or connects2db == 25:
                self.logging.info("Waiting for DB ...")

            try:
                self.logging.info(" - Try to connect to CouchDB: " + self.db_url)
                response = requests.get(self.db_url)
                connects2db = max_connects + 1

            except requests.exceptions.RequestException as e:
                connects2db += 1
                self.logging.warning(" - Waiting 5s for next connect to CouchDB: " + str(connects2db) + "/" + str(max_connects))
                self.logging.warning("   -> " + str(e))
                time.sleep(5)

            if connects2db == max_connects:
                self.raise_error("Error connecting to CouchDB, give up.")
                return False

        self.database = couchdb.Server(self.db_url)
        self.check_db()
        self.logging.info("Connected.")
        return True

    def raise_error(self, message):
        """
        Report Error, set variables of modules, collect last 3 messages in var self.error_msg
        """
        self.logging.error(message)
        self.error = True
        time_info = self.config.local_time().strftime('%d.%m.%Y %H:%M:%S')
        self.error_msg.append(time_info + " - " + message)
        if len(self.error_msg) >= 5:
            self.error_msg.pop()
        if "Connection refused" in message:
            self.connected = False

    def reset_error(self):
        """
        reset all error values
        """
        self.error = False
        self.error_msg = []

    def check_db(self):
        """
        check if required DB exists or create (under construction)
        """
        self.logging.info(" - Check if DB exist ... ")
        self.logging.debug(str(self.database_definition))
        for db_key in self.database_definition:
            if db_key in self.database and "main" in self.database[db_key]:
                self.logging.info("  -> OK: DB " + db_key + " exists.")
            else:
                self.logging.info("  -> DB " + db_key + " have to be created ...")
                try:
                    self.create(db_key)
                except Exception as e:
                    self.raise_error("  -> Could not create DB " + db_key + "! " + str(e))

    def create(self, db_key):
        """
        create a database in couch_db
        """
        self.logging.info("   -> create DB " + db_key)
        if db_key in self.database:
            self.logging.warning("   -> DB " + db_key + " exists.")
            db = self.database[db_key]
        else:
            try:
                db = self.database.create(db_key)
            except Exception as e:
                self.raise_error("   -> Could not create DB " + db_key + "! " + str(e))
                return

        # create initial data
        if "main" in self.database[db_key]:
            self.logging.warning("CouchDB - Already data in " + db_key + "!")
            return
        else:
            doc = db.get("main")
            if doc is None:
                doc = {
                    '_id': 'main',
                    'type': db_key,
                    'time': time.time(),
                    'change': 'new',
                    'data': {}
                }
            try:
                db.save(doc)
            except Exception as e:
                self.raise_error("CouchDB - Could not save after create: " + db_key + "  " + str(e))
                return

        # success
        self.logging.info("  -> DB created: " + db_key + " " + str(time.time()))
        return

    def filename2keys(self, filename):
        """
        translate filename to keys
        """
        date = ""
        database = ""
        filename = filename.replace(self.basic_directory, "")
        filename = filename.replace(".json", "")
        self.logging.debug("filename2keys: " + filename)

        if filename in self.database_translation:
            database = self.database_translation[filename]
            date = ""
            self.logging.debug("  -> " + database)
        else:
            parts1 = filename.split("/")
            parts2 = parts1[0]+"/<DATE>/"+parts1[2]
            if parts2 in self.database_translation:
                database = self.database_translation[parts2]
                date = parts1[1]
                self.logging.debug("  -> " + database + " / " + date)

        # experiment
        if date != "":
            database += "_" + date
            date = ""

        return [database, date]

    def read(self, filename):
        """
        read data from DB
        """
        data = {}
        [db_key, date] = self.filename2keys(filename)
        self.logging.debug("-----> READ DB: " + db_key + "/" + date)

        if db_key in self.database:
            database = self.database[db_key]
            doc = database.get("main")
            doc_data = doc["data"]
            if date != "":
                if date in doc_data:
                    return doc_data[date]
                else:
                    self.raise_error("CouchDB ERROR read (date): " + filename + " - " + db_key + "/" + date)
                    return {}
            else:
                return doc_data
        else:
            self.raise_error("CouchDB ERROR read (db_key): " + filename + " - " + db_key + "/" + date)
            return {}

    def write(self, filename, data, create=False):
        """
        read data from DB
        """
        [db_key, date] = self.filename2keys(filename)
        self.logging.debug("-----> WRITE: " + filename + " (" + self.basic_directory + ")")
        self.logging.debug("-----> WRITE DB: " + db_key + "/" + date)

        if db_key not in self.database and create:
            self.create(db_key)

        if db_key not in self.database:
            self.raise_error("CouchDB ERROR save: '" + db_key + "' not found, could not write data.")
            return

        database = self.database[db_key]
        doc = database.get("main")
        doc_data = doc["data"]
        if date != "":
            doc_data[date] = data
        else:
            doc_data = data

        if doc is None:
            doc = {
                '_id': 'main',
                'type': db_key,
                'time': time.time(),
                'change': 'new',
                'data': doc_data
            }
        else:
            doc['data'] = doc_data
            doc['time'] = time.time()
            doc['change'] = 'save changes'

        try:
            database.save(doc)
            database.compact()

        except Exception as e:
            self.logging.error("CouchDB ERROR save: " + db_key + " " + str(e))
            self.logging.error("  -> dict entries: " + str(len(doc["data"])))
            self.logging.error("  -> dict size: " + str(sys.getsizeof(doc["data"])))
            return

        self.changed_data = True
        return

    def exists(self, filename):
        """
        check if db exists
        """
        [db_key, date] = self.filename2keys(filename)
        self.logging.debug("-----> CHECK DB: " + db_key + "/" + date)

        if db_key in self.database:
            database = self.database[db_key]
            doc = database.get("main")
            doc_data = doc["data"]
            if date != "":
                if date in doc_data:
                    return True
                else:
                    return False
            else:
                return True
        else:
            return False


class BirdhouseConfigJSON(object):

    def __init__(self, config):
        self.locked = {}
        self.config = config
        self.connected = True
        self.error = False
        self.error_msg = []

        self.logging = logging.getLogger("DB-json")
        self.logging.setLevel(birdhouse_loglevel_module["DB-json"])
        self.logging.addHandler(birdhouse_loghandler)
        self.logging.info("Starting DB handler JSON ...")

    def raise_error(self, message):
        """
        Report Error, set variables of modules, collect last 3 messages in var self.error_msg
        """
        self.logging.error(message)
        self.error = True
        time_info = self.config.local_time().strftime('%d.%m.%Y %H:%M:%S')
        self.error_msg.append(time_info + " - " + message)
        if len(self.error_msg) >= 5:
            self.error_msg.pop()
        if "Connection refused" in message:
            self.connected = False

    def reset_error(self):
        """
        reset all error values
        """
        self.error = False
        self.error_msg = []

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
        self.logging.debug("Start check locked: " + filename + " ...")

        if filename in self.locked and self.locked[filename]:
            while self.locked[filename]:
                time.sleep(wait)
                count += 1
                if count > 10:
                    self.logging.warning("Waiting! File '" + filename + "' is locked (" + str(count) + ")")
                    time.sleep(1)

        elif filename == "ALL":
            self.logging.info("Wait until no file is locked ...")
            locked = len(self.locked.keys())
            while locked > 0:
                locked = 0
                for key in self.locked:
                    if self.locked[key]:
                        locked += 1
                time.sleep(wait)
            self.logging.info("OK")
        if count > 10:
            self.logging.warning("File '" + filename + "' is not locked any more (" + str(count) + ")")
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
            self.raise_error("Could not read JSON file: " + filename + " - " + str(e))
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
            self.logging.debug("Write JSON file: " + filename)

        except Exception as e:
            self.locked[filename] = False
            self.raise_error("Could not write JSON file: " + filename + " - " +str(e))


class BirdhouseConfigDBHandler(threading.Thread):

    def __init__(self, config, db_type="json", main_directory=""):
        threading.Thread.__init__(self)
        self._running = True
        self._paused = False
        self._process_running = False
        self.health_check = time.time()

        self.config = config
        self.error = False
        self.error_msg = []

        self.logging = logging.getLogger("DB-handler")
        self.logging.setLevel(birdhouse_loglevel_module["DB-handler"])
        self.logging.addHandler(birdhouse_loghandler)
        self.logging.info("Starting DB handler ("+db_type+"|"+main_directory+") ...")

        self.db_usr = birdhouse_env["couchdb_user"]
        self.db_pwd = birdhouse_env["couchdb_password"]
        self.db_server = "192.168.202.3"
        self.db_server = "birdhouse_db"
        self.db_port_internal = 5984
        self.db_basedir = "/usr/src/app/data/"

        self.backup_interval = 60*15
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
            if self.config.shut_down:
                self.stop()
            self.health_check = time.time()
            time.sleep(1)
        self.logging.info("Stopped DB handler.")

    def stop(self):
        self._running = False
        self._process_running = False

    def connect(self, db_type=None):
        """
        (re)connect database
        """
        if db_type is None:
            db_type = self.db_type
        self.logging.info(" -> (Re)Connecting to database(s) '"+db_type+"' ...")
        self.reset_error()
        self._process_running = False
        self.set_db_type(db_type)

    def set_db_type(self, db_type):
        """
        set DB type: JSON, CouchDB, BOTH
        """
        self.logging.info("  -> database handler set database type ("+db_type+")")
        self.db_type = db_type
        if self.json is None:
            self.json = BirdhouseConfigJSON(self.config)
        if self.db_type == "json":
            self.logging.info("  -> database handler - db_type=" + self.db_type + ".")
            return True
        elif self.db_type == "couch" or self.db_type == "both":
            if self.couch is None or not self.couch.connected:
                self.couch = BirdhouseConfigCouchDB(self.config, self.db_usr, self.db_pwd, self.db_server,
                                                    self.db_port_internal, self.db_basedir)
            if not self.couch.connected:
                self.db_type = "json"
            self.logging.info("  -> database handler - db_type=" + self.db_type + ".")
            return True
        else:
            self.logging.error("  -> Unknown DB type ("+str(self.db_type)+")")
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

    def raise_error(self, message):
        """
        Report Error, set variables of modules, collect last 3 messages in var self.error_msg
        """
        self.logging.error(message)
        self.error = True
        time_info = self.config.local_time().strftime('%d.%m.%Y %H:%M:%S')
        self.error_msg.append(time_info + " - " + message)
        if len(self.error_msg) >= 5:
            self.error_msg.pop()

    def reset_error(self):
        """
        reset all error values
        """
        self.error = False
        self.error_msg = []
        if self.db_type == "json":
            self.json.reset_error()
        if self.db_type == "couch":
            self.json.reset_error()
            self.couch.reset_error()

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
        while self._process_running:
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
        path = os.path.join(self.main_directory, self.directories["data"], self.directories[config], date)
        if ".." in path:
            elements = path.split("/")
            path_new = []
            for element in elements:
                if element == ".." and len(path_new) > 0:
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
            result = self.couch.read(filename)
            if result == {}:
                result = self.json.read(filename)

        else:
            self.raise_error("Unknown DB type ("+str(self.db_type)+")")

        return result.copy()

    def read_cache(self, config, date=""):
        """
        get date from cache, if available (else read from source)
        """
        if config not in self.config_cache and date == "":
            self.config_cache[config] = self.read(config=config, date="")
            self.config_cache_changed[config] = False

        elif config not in self.config_cache and date != "":
            self.config_cache[config] = {}
            self.config_cache[config][date] = self.read(config=config, date=date)
            self.config_cache_changed[config+"_"+date] = False

        elif date not in self.config_cache[config] and date != "":
            self.config_cache[config][date] = self.read(config=config, date=date)
            self.config_cache_changed[config+"_"+date] = False

        if date == "":
            return self.config_cache[config].copy()
        else:
            return self.config_cache[config][date].copy()

    def write(self, config, date="", data=None, create=False, save_json=False):
        """
        write data to DB
        """
        self.logging.debug("Write: " + config + " / " + date + " / " + self.db_type)
        self.wait_if_paused()
        if data is None:
            self.logging.error("Write: No data given ("+str(config)+"/"+str(date)+")")
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
            self.raise_error("Unknown DB type ("+str(self.db_type)+")")

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
            self.config_cache_changed[config+"_"+date] = True
        else:
            self.config_cache[config] = {}
            self.config_cache[config][date] = data
            self.config_cache_changed[config+"_"+date] = True

    def write_cache_to_json(self):
        """
        create a backup of all data in the cache to JSON files (backup if db_type == couch)
        """
        self.wait_if_process_running()
        self._process_running = True

        start_time = time.time()
        self.logging.info("Create backup from cached data ...")
        for config in self.config_cache:
            if config != "backup":
                if self.config_cache_changed[config]:
                    filename = self.file_path(config=config, date="")
                    self.json.write(filename=filename, data=self.config_cache[config])
                    self.logging.info("   -> backup: " + config + " (" + str(round(time.time()-start_time, 1)) + "s)")
                    self.config_cache_changed[config] = False
            else:
                for date in self.config_cache[config]:
                    if self.config_cache_changed[config+"_"+date]:
                        filename = self.file_path(config=config, date=date)
                        self.json.write(filename=filename, data=self.config_cache[config][date])
                        self.logging.info("   -> backup: " + config + " / " + date +
                                          " (" + str(round(time.time()-start_time, 1)) + "s)")
                        self.config_cache_changed[config + "_" + date] = False
        self._process_running = False

    def clean_all_data(self, config, date=""):
        """
        remove all entries from a database
        """
        self.wait_if_process_running()
        self._process_running = True

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

        self._process_running = False

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


class BirdhouseConfigQueue(threading.Thread):

    def __init__(self, config, db_handler):
        """
        Initialize new thread and set inital parameters
        """
        threading.Thread.__init__(self)
        self.health_check = time.time()

        self.logging = logging.getLogger("config-Q")
        self.logging.setLevel(birdhouse_loglevel_module["config-Q"])
        self.logging.addHandler(birdhouse_loghandler)
        self.logging.info("Starting config queue ...")

        self.queue_count = None
        self.config = config
        self.views = None
        self.db_handler = db_handler
        self._running = True
        self.edit_queue = {"images": [], "videos": [], "backup": {}, "sensor": [], "weather": []}
        self.status_queue = {"images": [], "videos": [], "backup": {}, "sensor": [], "weather": []}
        self.queue_wait = 5
        self.queue_wait_max = 30
        self.queue_wait_min = 5
        self.queue_wait_duration = 0

    def run(self):
        """
        create videos and process queue.
        """
        config_files = ["images", "videos", "backup", "sensor", "weather"]
        start_time = time.time()
        start_time_2 = time.time()
        check_count_entries = 0
        while self._running:
            if start_time + self.queue_wait < time.time():
                self.logging.debug("... Check Queue")

                count_entries = 0
                count_files = 0
                active_files = []

                # check first if entries are available
                entries_available = False
                for config_file in config_files:
                    if config_file != "backup" and not entries_available:
                        if config_file in self.edit_queue and len(self.edit_queue[config_file]) > 0:
                            entries_available = True
                    elif not entries_available:
                        for date in self.edit_queue["backup"]:
                            if len(self.edit_queue["backup"][date]) > 0:
                                entries_available = True

                if entries_available:
                    start_time = time.time()
                    self.logging.debug("... Entries available in the queue (" +
                                       str(round(time.time()-start_time, 2)) + "s)")
                    for config_file in config_files:
                        file_start_time = time.time()
                        self.logging.debug("    -> Queue: "+config_file+" ... (" +
                                           str(len(self.edit_queue[config_file])) + " entries / " +
                                           str(round(time.time()-start_time, 2)) + "s)")

                        # Check if DB connection
                        wait_for_db = 0
                        while not self.db_handler.get_db_status()["db_connected"]:
                            self.logging.warning("Waiting for DB Connection (" +
                                                 str(len(self.edit_queue[config_file])) + " entries in the Queue)")
                            wait_for_db += 1
                            if wait_for_db > 6:
                                self.db_handler.connect(self.db_handler.db_type)
                            time.sleep(5)

                        # EDIT QUEUE: today, video (without date)
                        if config_file != "backup" and len(self.edit_queue[config_file]) > 0:
                            self.logging.debug("       .start (" + str(round(time.time()-file_start_time, 2)) + "s)")
                            active_files.append(config_file)
                            entries = self.db_handler.read_cache(config_file)
                            self.db_handler.lock(config_file)
                            self.logging.debug("       .read (" + str(round(time.time()-file_start_time, 2)) + "s)")

                            count_files += 1
                            count_edit = 0
                            while len(self.edit_queue[config_file]) > 0:
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

                            self.logging.debug("       .edit (" + str(round(time.time()-file_start_time, 2)) + "s)")
                            self.db_handler.unlock(config_file)
                            self.db_handler.write(config_file, "", entries)
                            self.logging.debug("       .write (" + str(round(time.time()-file_start_time, 2)) + "s / " +
                                               str(round(sys.getsizeof(entries)/1024, 1)) + "kB)")

                            if count_edit > 0 and self.views is not None:
                                self.views.favorite_list_update()

                        # EDIT QUEUE: backup (with date)
                        elif config_file == "backup":
                            for date in self.edit_queue[config_file]:
                                if "backup" not in active_files:
                                    active_files.append(config_file)
                                entry_data = self.db_handler.read_cache(config_file, date)
                                entries = entry_data["files"]
                                self.db_handler.lock(config_file, date)

                                if date in self.edit_queue[config_file] and len(self.edit_queue[config_file][date]) > 0:
                                    count_files += 1
                                elif date not in self.edit_queue[config_file]:
                                    self.edit_queue[config_file][date] = []

                                count_edit = 0
                                while len(self.edit_queue[config_file][date]) > 0:
                                    [key, entry, command] = self.edit_queue[config_file][date].pop()
                                    count_entries += 1

                                    self.logging.info(" +++> "+command+" +++ "+key)

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

                                if count_edit > 0 and self.views is not None:
                                    self.views.favorite_list_update()

                                entry_data["files"] = entries
                                self.db_handler.unlock(config_file, date)
                                self.db_handler.write(config_file, date, entry_data)

                        # STATUS QUEUE: today, video (without date)
                        if config_file != "backup" and len(self.status_queue[config_file]) > 0:
                            entries = self.db_handler.read_cache(config_file)
                            self.db_handler.lock(config_file)

                            count_files += 1
                            while len(self.status_queue[config_file]) > 0:
                                [date, key, change_status, status] = self.status_queue[config_file].pop()
                                count_entries += 1

                                if change_status == "RANGE_END":
                                    self.config.async_answers.append(["RANGE_DONE"])
                                elif change_status == "DELETE_RANGE_END":
                                    self.config.async_answers.append(["DELETE_RANGE_DONE"])
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
                                self.db_handler.unlock(config_file, date)
                                self.db_handler.write(config_file, date, entry_data)

                        self.logging.debug("    -> Queue: " + config_file + " done. " +
                                           " (" + str(round(time.time() - start_time, 2)) + "s)")

                    check_count_entries += count_entries
                    self.logging.debug("Queue: wrote " + str(count_entries) + " entries to " + str(count_files) +
                                       " config files (" + str(round(time.time()-start_time, 2)) + "s/" +
                                       ",".join(active_files) + ")")

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

            if start_time_2 + self.queue_wait_max*6 < time.time():
                self.logging.info("Queue: wrote " + str(check_count_entries) + " entries since the last " +
                                  str(self.queue_wait_max*6) + "s.")
                check_count_entries = 0
                start_time_2 = time.time()

            self.health_check = time.time()
            time.sleep(1)

        self.logging.info("Stopped Config Queue.")

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
            config_data = self.db_handler.read_cache(config="images")
        elif category == "backup":
            config_data = self.db_handler.read_cache(config="backup", date=entry_date)["files"]
        elif category == "videos":
            config_data = self.db_handler.read_cache(config="videos")

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
        self.logging.debug("Status recycle: "+str(path))
        param = path.split("/")
        response = {}
        category = param[2]
        config_data = {}

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
            config_data = self.db_handler.read_cache(config="images")
        elif category == "backup":
            config_data = self.db_handler.read_cache(config="backup", date=entry_date)["files"]
        elif category == "videos":
            config_data = self.db_handler.read_cache(config="videos")

        response["command"] = ["mark/unmark for deletion", entry_id]
        if entry_id in config_data:
            self.logging.debug("- OK "+entry_id)
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

                if relevant and config_data[entry_id]["camera"] == camera and \
                        ("type" not in config_data[entry_id] or config_data[entry_id]["type"] != "data") and \
                        ("to_be_deleted" not in config_data[entry_id] or
                         int(config_data[entry_id]["to_be_deleted"]) != 1) and not dont_delete:

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
        self.logging.debug("Request to edit data ("+config+"/"+date+"/"+key+").")
        self.add_to_edit_queue(config, date, key, entry, "edit")

    def entry_delete(self, config, date, key):
        """
        delete entry from config file using the queue
        """
        self.logging.debug("Request to delete data ("+config+"/"+date+"/"+key+").")
        self.add_to_edit_queue(config, date, key, {}, "delete")

    def entry_keep_data(self, config, date, key):
        """
        cleaning image entry keeping activity and sensor data for charts using the queue
        """
        self.logging.debug("Request to keep data and delete image reference ("+config+"/"+date+"/"+key+").")
        self.add_to_edit_queue(config, date, key, {}, "keep_data")


class BirdhouseConfig(threading.Thread):

    def __init__(self, param_init, main_directory):
        """
        Initialize new thread and set inital parameters
        """
        threading.Thread.__init__(self)
        self.name = "Config"
        self._running = True
        self._paused = False
        self.shut_down = False
        self.health_check = time.time()
        self.param = None
        self.config = None
        self.config_cache = {}
        self.views = None
        self.queue = None
        self.db_handler = None

        self.logging = logging.getLogger("config")
        self.logging.setLevel(birdhouse_loglevel_module["config"])
        self.logging.addHandler(birdhouse_loghandler)
        self.logging.info("Starting configuration handler ("+main_directory+") ...")

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
        self.last_start = ""

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
                          "' (timezone="+str(self.timezone)+") ...")

        # check main status information
        if "info" in self.param and "last_day_running" in self.param["info"]:
            self.last_day_running = self.param["info"]["last_day_running"]
        elif "info" not in self.param:
            self.param["info"] = {}
        if "last_day_running" not in self.param:
            self.last_day_running = self.local_time().strftime("%Y-%m-%d")
            self.param["info"]["last_day_running"] = self.last_day_running
        self.param["info"]["last_start_date"] = self.local_time().strftime("%Y-%m-%d")
        self.param["info"]["last_start_time"] = self.local_time().strftime("%H:%M:%S")
        self.db_handler.write(config="main", data=self.param)

        # set database type if not JSON
        self.db_type = self.param["server"]["database_type"]
        if self.db_type != "json" and ("db_type" not in self.param_init or self.param_init["db_type"] != "json"):
            if self.db_handler is not None:
                self.db_handler.stop()
            self.db_handler = BirdhouseConfigDBHandler(self, self.db_type, main_directory)
            self.db_handler.start()

        self.queue = BirdhouseConfigQueue(config=self, db_handler=self.db_handler)
        self.queue.start()

    def run(self):
        """
        Core function (not clear what to do yet)
        """
        count = 0
        self.param = self.db_handler.read("main")
        self.param["path"] = self.main_directory

        if "weather" not in self.param_init or self.param_init["weather"] is not False:
            self.weather = BirdhouseWeather(config=self, time_zone=self.timezone)
            self.weather.start()
        elif not self.weather and self.weather is not None:
            self.weather.stop()
            self.weather = False
        else:
            self.weather = False

        while self._running:
            time.sleep(1)

            # check if data has change and old data shall be removed
            if self.param["server"]["daily_clean_up"]:
                date_today = self.local_time().strftime("%Y-%m-%d")
                if date_today != self.last_day_running:
                    self.logging.info("-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.")
                    self.logging.info("Date changed: " + self.last_day_running + " -> " + date_today)
                    self.logging.info("-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.")
                    self.db_handler.clean_all_data(config="images")
                    self.db_handler.clean_all_data(config="sensor")
                    self.db_handler.clean_all_data(config="weather")
                    self.param["info"]["last_day_running"] = date_today
                    self.last_day_running = date_today
                    self.db_handler.write(config="main", date="", data=self.param)
                    time.sleep(2)

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

            self.health_check = time.time()

        self.logging.info("Stopped config handler.")

    def stop(self):
        """
        Core function (not clear what to do yet)
        """
        self.queue.stop()
        self.db_handler.stop()
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
            self.db_handler.set_db_type(db_type=self.param["server"]["database_type"])

            for key in self.update:
                self.update[key] = True

            if self.weather is not False and "weather:location" in config_data:
                self.logging.info("Update weather config and lookup GPS data: '"+self.param["weather"]["location"]+"'.")
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
            self.shut_down = True
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

    def user_activity(self, cmd="get"):
        """
        set user activity
        """
        if cmd == "set":
            self.user_activity_last = self.local_time().timestamp()
            self.user_active = True
            return True

        elif cmd == "get" and self.user_activity_last + 60 > self.local_time().timestamp():
            return True

        self.user_active = False
        return False

    def db_status(self):
        """
        return DB status
        """
        return self.db_handler.get_db_status()

    def set_views(self, views):
        """
        set handler for views
        """
        self.views = views
        self.queue.views = views

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
