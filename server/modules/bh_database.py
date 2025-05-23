import os.path
import sys
import time
import json
import codecs
import couchdb
import requests

from modules.presets import *
from modules.bh_class import BirdhouseClass, BirdhouseDbClass


class BirdhouseTEXT(BirdhouseDbClass):
    """
    class to read and write text files
    """

    def __init__(self, config=""):
        """
        Constructor to initialize class

        Args:
            config (str|modules.config.BirdhouseConfig): reference to config handler or empty string
        """
        if config != "":
            BirdhouseDbClass.__init__(self, "TEXT", "DB-text", config)
        else:
            self.logging = set_logging("DB-text")
            self.logging.setLevel(logging.ERROR)
        self.locked = {}
        self.logging.info("Connected TEXT handler.")

    def read(self, filename):
        """
        read json file including check if locked

        Args:
            filename (str): file incl. path to read
        Returns:
            str: file content
        """
        try:
            self.wait_if_locked(filename)
            with open(filename) as text_file:
                data = text_file.read()
            text_file.close()
            return str(data)

        except Exception as e:
            self.raise_error("Could not read TEXT file: " + filename + " - " + str(e))
            return {}

    def write(self, filename, data):
        """
        write json file including locking mechanism

        Args:
            filename (str): file incl. path to write
            data (str): text data to write into the file
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
    """
    class to read and write json data in text files
    """

    def __init__(self, config) -> None:
        """
        Constructor to initialize class

        Args:
            config (modules.config.BirdhouseConfig): reference to config handler
        """
        BirdhouseDbClass.__init__(self, "JSON", "DB-json", config)
        self.locked = {}
        self.sort_keys = True
        self.connected = True
        self.db_list = []
        self.get_db_list()

        self.logging.info("Connected JSON handler.")

    def read(self, filename) -> dict:
        """
        read json file including check if locked

        Args:
            filename (str): file incl. path to read
        Returns:
            dict: file content
        """
        try:
            self.wait_if_locked(filename)
            with open(filename) as json_file:
                data = json.load(json_file)
            self.logging.debug("Read JSON file: " + filename)
            self.logging.debug("                " + str(list(data.keys()))[:80])
            return data

        except Exception as e:
            self.raise_error("Could not read JSON file: " + filename + " - " + str(e))
            return {}

    def write(self, filename, data, create=False):
        """
        write json file including locking mechanism

        Args:
            filename (str): file incl. path to write
            data (dict): json data to write into the file
            create (bool): create directory from path if not exists
        """
        self.wait_if_locked(filename)
        try:
            start_write_time = time.time()
            file_path = filename.split("/")
            file = file_path[-1]
            path = filename.replace(file, "")
            if not os.path.exists(path) and not create:
                raise "Path '" + path + "' doesn't exist."
            elif not os.path.exists(path):
                os.makedirs(path)

            self.locked[filename] = True
            with open(filename, 'w', encoding='utf-8') as json_file:
                json.dump(data, json_file, ensure_ascii=False, sort_keys=self.sort_keys, indent=4)
                json_file.close()
            self.config.set_processing_performance("db_write_file", "write_file", start_write_time)
            self.locked[filename] = False
            self.logging.debug("Write JSON file: " + filename)
            self.logging.debug("                 " + str(list(data.keys()))[:80])

        except Exception as e:
            self.locked[filename] = False
            self.raise_error("Could not write JSON file: " + filename + " - " + str(e))

    def get_db_list(self):
        """
        get list of all json databases in data directory

        Returns:
            list: list of all json databases
        """
        self.logging.debug(" - Get JSON DB list ... ")
        json_files = []
        directory = birdhouse_main_directories["data"]
        count = 0

        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.json'):
                    parts = file.split(".")
                    if len(parts) == 2:
                        count += 1
                        path = os.path.join(root, file).replace(birdhouse_main_directories["data"], "")
                        self.logging.debug(str(count) + ". " + str(path))
                        json_files.append(path)
        self.db_list = json_files.copy()
        return json_files

    def delete_db(self, filename):
        """
        delete json database file

        Args:
            filename: file to be deleted
        """
        if os.path.exists(filename):
            os.remove(filename)
            self.logging.info("The file "+filename+" has been deleted.")
        else:
            self.logging.warning("The file "+filename+" does not exist.")
        pass

    def exists(self, filename) -> bool:
        """
        check if file exists

        Args:
            filename (str): file incl. path to check
        Returns:
            bool: status if file exists
        """
        result = os.path.exists(filename)
        self.logging.debug("File exists=" + str(result) + "; File=" + filename)
        return result


class BirdhouseCouchDB(BirdhouseDbClass):
    """
    class to read and write date from CouchDB
    """

    def __init__(self, config, db):
        """
        Constructor to initialize class

        Args:
            config (modules.config.BirdhouseConfig): reference to config handler
            db (dict): database configuration (db_usr, db_pwd, db_server, db_port)
        """
        BirdhouseDbClass.__init__(self, "COUCH", "DB-couch", config)
        self.locked = {}
        self.changed_data = False
        self.database = None
        self.timeout = 10

        self.basic_directory = db["db_basedir"]
        self.db_url = "http://" + db["db_usr"] + ":" + db["db_pwd"] + "@" + db["db_server"] + \
                      ":" + str(db["db_port"]) + "/"
        self.db_list = []

        self.create_revisions = False

        self.database_definition = birdhouse_databases
        self.database_translation = birdhouse_dir_to_database

        self.connected = self.connect()
        self.logging.info("Connected CouchDB handler (" + self.db_url + ").")

    def connect(self):
        """
        connect to database incl. retry

        Returns:
            bool: connection status
        """
        connects2db = 0
        max_connects = 5
        self.reset_error()
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

        try:
            self.database = couchdb.Server(self.db_url)
        except Exception as e:
            self.raise_error("  -> Could not connect to DB " + self.db_url + "! " + str(e))
            return False

        check = self.check_db()
        if check:
            self.logging.info("Connected.")
            self.get_db_list()
            return True
        else:
            self.logging.warning("Error CouchDB database check.")
            return False

    def check_db(self):
        """
        check if required DB exists or create (under construction)

        Returns:
            bool: status if db exists
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
                    if "104" in str(e):
                        self.raise_error("  -> Increase or remove memory limits in .env to avoid this error.\n" +
                                         "     And ensure that a swap file is available and used (see README.md).")
                    return False
        return True

    def get_db_list(self):
        """
        get list of all databases in couch_db

        Returns:
            list: list of all databases in couch_db
        """
        self.logging.debug(" - Get Couch DB list ... ")
        count = 0
        for db_key in self.database:
            count += 1
            self.logging.debug(str(count) + ". " + db_key)
            self.db_list.append(db_key)
        return self.db_list

    def delete_db(self, filename, db_key=""):
        """
        delete a database from couch_db

        Args:
            db_key: db_key of the database to be deleted (if empty, db_key will be translated from filename)
            filename: filename to be translated into db_key and date (if empty, db_key will be translated from filename)
        """
        if db_key == "":
            [db_key, date] = self.filename2keys(filename, "couch delete")
            self.logging.debug("-----> DELETE DB: " + db_key + "/" + date + " - " + filename)
        else:
            self.logging.debug("-----> DELETE DB: " + db_key)

        try:
            if db_key in self.database:
                self.database.delete(db_key)
                self.logging.info("Database '"+db_key+"' deleted successfully.")
            else:
                self.logging.warning("Database '"+db_key+"' doesn't exist. Nothing to delete.")
        except couchdb.http.ServerError as e:
            self.logging.error("Error deleting database: " + str(e))

    def create(self, db_key):
        """
        create a database in couch_db

        Args:
            db_key (str): database name
        """
        self.logging.debug("   -> create DB " + db_key)
        try:
            if db_key in self.database:
                self.logging.warning("   -> DB " + db_key + " exists.")
                db = self.database[db_key]
            else:
                try:
                    db = self.database.create(db_key)
                except Exception as e:
                    self.raise_error("   -> Could not create DB " + db_key + "! " + str(e))
                    return
        except Exception as e:
            self.logging.error("CouchDB error create: " + str(e))

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
        self.logging.info("   -> DB created: " + db_key + " " + str(time.time()))
        return

    def filename2keys(self, filename, call=""):
        """
        translate filename to keys

        Args:
            filename (str): filename to be translated into database key
        Returns:
            str: db_key
        """
        date = ""
        database = ""
        filename = filename.replace(self.basic_directory, "")
        filename = filename.replace(".json", "")
        if filename.startswith("/"):
            filename = filename[1:]
        self.logging.debug("filename2keys: " + filename)

        if filename in self.database_translation:
            database = self.database_translation[filename]
            date = ""
            self.logging.debug("  -> " + database)
        else:
            parts1 = filename.split("/")
            if len(parts1) >= 3:
                parts2 = parts1[0] + "/<DATE>/" + parts1[2]
                if parts2 in self.database_translation:
                    database = self.database_translation[parts2]
                    date = parts1[1]
                    self.logging.debug("  -> " + database + " / " + date)
                else:
                    database = filename.replace("/","_")
                    database = filename.replace(".._","_")
                    self.logging.warning("  -> " + filename + " not found in database_translation #1 ("+call+").")
                    self.logging.debug("  -> basic directory: " + self.basic_directory)
                    self.logging.warning("  -> use the following DB name instead: " + database)
            else:
                database = filename.replace("/", "_")
                self.logging.warning("  -> " + filename + " not found in database_translation #2 ("+call+").")
                self.logging.debug("  -> basic directory: " + self.basic_directory)
                self.logging.warning("  -> use the following DB name instead: " + database)

        # experiment
        if date != "":
            database += "_" + date
            date = ""

        return [database, date]

    def read(self, filename, retry=True):
        """
        read data from DB

        Args:
            filename (str): filename to be translated into db_key
            retry (bool): retry after error
        Returns:
            dict: data from database
        """
        data = {}
        [db_key, date] = self.filename2keys(filename, "couch read")
        self.logging.debug("-----> READ DB: " + db_key + "/" + date + " - " + filename)

        if db_key == "":
            self.raise_error("CouchDB ERROR read, could not get db_key from filename ("+filename+")")
            return {}
        try:
            if db_key in self.database:
                database = self.database[db_key]
                doc = database.get("main")
                doc_data = doc["data"]
                if date != "":
                    if date in doc_data:
                        return doc_data[date]
                    else:
                        self.raise_error("CouchDB ERROR read (date): " + filename + " - " +
                                         db_key + "/" + date)
                        return {}
                else:
                    return doc_data
            else:
                self.raise_error("CouchDB ERROR read (db_key): " + filename + " - " + db_key + "/" + date)
                return {}
        except Exception as e:
            if retry:
                self.logging.warning("CouchDB ERROR read: " + filename + " - " + db_key + "/" + date +
                                     " - " + str(e) + " -> RETRY")
                return self.read(filename, retry=False)
            else:
                self.raise_error("CouchDB ERROR read: " + filename + " - " + db_key + "/" + date + " - " + str(e))
                return {}

    def write(self, filename, data, create=False, retry=True):
        """
        read data from DB

        Args:
            filename (str): filename to be translated into db_key
            data (dict): data to be saved in the database
            create (bool): create database if not exists
            retry (bool): retry after error
        """
        [db_key, date] = self.filename2keys(filename, "couch write")
        self.logging.debug("-----> WRITE: " + filename + " (" + self.basic_directory + ")")
        self.logging.debug("-----> WRITE DB: " + db_key + "/" + date)

        if db_key not in self.database and create:
            self.create(db_key)

        if db_key not in self.database:
            self.raise_error("CouchDB ERROR save: '" + db_key + "' not found, could not write data.")
            return

        try:
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
        except Exception as e:
            if retry:
                self.logging.warning("CouchDB ERROR save (prepare data): " + db_key + " " + str(e) + " -> RETRY")
                time.sleep(self.timeout)
                self.write(filename, data, create, retry=False)
                return
            else:
                self.logging.error("CouchDB ERROR save (prepare data): " + db_key + " " + str(e))
                return

        try:
            database.save(doc)
            database.compact()

        except Exception as e:
            if retry:
                self.logging.error("CouchDB ERROR save: " + db_key + " " + str(e) + " -> RETRY")
                time.sleep(self.timeout)
                self.write(filename, data, create, retry=False)
            else:
                self.logging.error("CouchDB ERROR save: " + db_key + " " + str(e))
                self.logging.error("  -> dict entries: " + str(len(doc["data"])))
                self.logging.error("  -> dict size: " + str(sys.getsizeof(doc["data"])))
                self.logging.debug("  -> dict keys: " + str(doc["data"].keys()))
                return

        self.changed_data = True
        return

    def exists(self, filename):
        """
        check if db exists

        Args:
            filename (str): filename to be translated into db_key
        Returns:
            bool: status if database exists
        """
        [db_key, date] = self.filename2keys(filename, "couch exists")
        self.logging.debug("-----> CHECK DB: " + db_key + "/" + date)

        if db_key == "":
            return False
        try:
            if db_key in self.database:
                #time.sleep(0.01)
                database = self.database[db_key]
                #time.sleep(0.01)
                doc = database.get("main")
                #time.sleep(0.01)
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
        except Exception as e:
            self.logging.error("'exists()' - DB connection error: " + str(e))


