import sys
import time
import logging
import json
import codecs
import couchdb
import requests

from modules.presets import *
from modules.bh_class import BirdhouseClass, BirdhouseDbClass


class BirdhouseCouchDB_org(object):

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

        self.database_definition = birdhouse_databases
        self.database_translation = birdhouse_dir_to_database

        self.connected = self.connect()
        self.error = False
        self.error_msg = []

        self.logging.info("Connected CouchDB handler ("+self.db_url+").")

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


class BirdhouseJSON_org(object):

    def __init__(self, config):
        self.locked = {}
        self.config = config
        self.connected = True
        self.error = False
        self.error_msg = []

        self.logging = logging.getLogger("DB-json")
        self.logging.setLevel(birdhouse_loglevel_module["DB-json"])
        self.logging.addHandler(birdhouse_loghandler)
        self.logging.info("Connected JSON handler.")

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


# ----------------------
class BirdhouseTEXT(BirdhouseDbClass):

    def __init__(self, config):
        BirdhouseDbClass.__init__(self, "TEXT", "DB-text", config)
        self.locked = {}

        self.logging.info("Connected TEXT handler.")

    def read(self, filename):
        """
        read json file including check if locked
        """
        try:
            self.wait_if_locked(filename)
            with open(filename) as text_file:
                data = text_file
            return data

        except Exception as e:
            self.raise_error("Could not read TEXT file: " + filename + " - " + str(e))
            return {}

    def write(self, filename, data):
        """
        write json file including locking mechanism
        """
        self.wait_if_locked(filename)
        try:
            self.locked[filename] = True
            with open(filename, 'w') as text_file:
                text_file.write(data)
                text_file.close()
            self.locked[filename] = False
            self.logging.debug("Write TEXT file: " + filename)

        except Exception as e:
            self.locked[filename] = False
            self.raise_error("Could not write TEXT file: " + filename + " - " + str(e))


class BirdhouseJSON(BirdhouseDbClass):

    def __init__(self, config):
        BirdhouseDbClass.__init__(self, "JSON", "DB-json", config)
        self.locked = {}
        self.connected = True

        self.logging.info("Connected JSON handler.")

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
            self.raise_error("Could not write JSON file: " + filename + " - " + str(e))


class BirdhouseCouchDB(BirdhouseDbClass):

    def __init__(self, config, db_usr, db_pwd, db_server, db_port, base_dir):
        """
        initialize
        """
        BirdhouseDbClass.__init__(self, "COUCH", "DB-couch", config)
        self.locked = {}
        self.changed_data = False
        self.database = None
        self.basic_directory = base_dir
        self.db_url = "http://" + db_usr + ":" + db_pwd + "@" + db_server + ":" + str(db_port) + "/"
        self.create_revisions = False

        self.database_definition = birdhouse_databases
        self.database_translation = birdhouse_dir_to_database

        self.connected = self.connect()
        self.logging.info("Connected CouchDB handler (" + self.db_url + ").")

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
                self.logging.warning(
                    " - Waiting 5s for next connect to CouchDB: " + str(connects2db) + "/" + str(max_connects))
                self.logging.warning("   -> " + str(e))
                time.sleep(5)

            if connects2db == max_connects:
                self.raise_error("Error connecting to CouchDB, give up.")
                return False

        self.database = couchdb.Server(self.db_url)
        self.check_db()
        self.logging.info("Connected.")
        return True

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
            parts2 = parts1[0] + "/<DATE>/" + parts1[2]
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


