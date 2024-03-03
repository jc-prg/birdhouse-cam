import os
import glob
import sys
import logging
import time
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler


def get_env(var_name):
    """
    get value from .env-file if exists

    Args:
        var_name (str): key in .env file
    Returns:
        Any: value from .env file
    """
    try:
        value = os.environ.get(var_name)
    except Exception as e:
        value = None
    return value


def set_global_configuration():
    """
    read global vars from .env file
    """
    global birdhouse_env, birdhouse_loglevel_modules_debug, birdhouse_loglevel_modules_info, \
        birdhouse_loglevel_modules_error, birdhouse_loglevel_modules_warning, birdhouse_loglevel_modules_all

    path = os.path.join(os.path.dirname(__file__), "../../.env")
    load_dotenv(path)
    birdhouse_env_keys = {
        "admin_ip4_deny": "ADMIN_IP4_DENY",
        "admin_ip4_allow": "ADMIN_IP4_ALLOW",
        "admin_password": "ADMIN_PASSWORD",
        "admin_login": "ADMIN_LOGIN",
        "couchdb_server": "COUCHDB_SERVER",
        "couchdb_user": "COUCHDB_USER",
        "couchdb_password": "COUCHDB_PASSWORD",
        "couchdb_port": "COUCHDB_PORT",
        "database_type": "DATABASE_TYPE",
        "database_cleanup": "DATABASE_DAILY_CLEANUP",
        "detection_active": "OBJECT_DETECTION",
        "dir_project": "BIRDHOUSE_DIR_PROJECT",
        "dir_logging": "BIRDHOUSE_DIR_LOGGING",
        "http_server": "BIRDHOUSE_HTTP_SERVER",
        "installation_type": "BIRDHOUSE_INSTALLATION_TYPE",
        "log_level": "BIRDHOUSE_LOG_LEVEL",
        "log_level_debug": "BIRDHOUSE_LOG_DEBUG",
        "log_level_info": "BIRDHOUSE_LOG_INFO",
        "log_level_warning": "BIRDHOUSE_LOG_WARNING",
        "log_level_error": "BIRDHOUSE_LOG_ERROR",
        "log_to_file": "BIRDHOUSE_LOG2FILE",
        "port_http": "BIRDHOUSE_HTTP_PORT",
        "port_api": "BIRDHOUSE_API_PORT",
        "port_audio": "BIRDHOUSE_AUDIO_PORT",
        "port_video": "BIRDHOUSE_VIDEO_PORT",
        "rpi_active": "RPI_ACTIVE",
        "rpi_64bit": "RPI_64BIT",
        "server_audio": "BIRDHOUSE_AUDIO_SERVER",
        "test_instance": "BIRDHOUSE_INSTANCE",
        "test_video_devices": "BIRDHOUSE_VIDEO_DEVICE_TEST",
        "which_instance": "BIRDHOUSE_INSTANCE",
    }

    birdhouse_env = {}
    for key in birdhouse_env_keys:
        birdhouse_env[key] = get_env(birdhouse_env_keys[key])
        if birdhouse_env[key] is None:
            print('Value in .env not found: ' + str(birdhouse_env_keys[key]))

    for key in ["database_cleanup", "rpi_active", "rpi_64bit", "detection_active", "log_to_file",
                "test_video_devices"]:
        if birdhouse_env[key] is not None:
            birdhouse_env[key] = str(birdhouse_env[key]).lower() in ("true", "1", "yes", "on")

    birdhouse_env["test_instance"] = str(birdhouse_env["test_instance"].upper() == "TEST").lower()

    try:
        for key in ["log_level"]:
            if birdhouse_env[key].upper() in ["INFO", "DEBUG", "WARNING", "ERROR"]:
                try:
                    birdhouse_env[key] = eval("logging." + str(birdhouse_env[key]).upper())
                except Exception as e:
                    log_level = birdhouse_env[key]
                    birdhouse_env[key] = None
                    raise ValueError("Couldn't set log level logging." + str(log_level) + ": " + str(e))
            else:
                birdhouse_env[key] = None

    except Exception as e:
        print("Error reading configuration defined in the file '.env': " + str(e))
        print("Check or rebuild your configuration file based on the file 'sample.env'.")
        os._exit(os.EX_CONFIG)

    for key in ["log_level_debug", "log_level_info", "log_level_warning", "log_level_error"]:
        try:
            level = ""
            if birdhouse_env[key] is not None and birdhouse_env[key] != "":
                level = key.split("_")[2]
                modules = birdhouse_env[key].split(",")
                if level == "debug":
                    birdhouse_loglevel_modules_debug = []
                if level == "info":
                    birdhouse_loglevel_modules_info = []
                if level == "warning":
                    birdhouse_loglevel_modules_warning = []
                if level == "error":
                    birdhouse_loglevel_modules_error = []

                for module in modules:
                    if module in birdhouse_loglevel_modules_all:
                        eval("birdhouse_loglevel_modules_" + level + ".append('" + module + "')")
                if level != "":
                    print(level.upper() + ": " + str(eval("birdhouse_loglevel_modules_" + level)))

        except Exception as e:
            print("Error reading list of log levels ("+key+"|"+level+"|"+str(birdhouse_env[key])+"): " + str(e))


def set_error_images():
    """
    read error images from disk into vars
    """
    global birdhouse_error_images_raw, birdhouse_error_images
    import cv2
    for key in birdhouse_error_images:
        image_path = os.path.join(birdhouse_main_directories["data"], birdhouse_error_images[key])
        if os.path.exists(image_path):
            birdhouse_error_images_raw[key] = cv2.imread(image_path)
        else:
            print("Could not load error image " + image_path)
            sys.exit()


def check_submodules():
    """
    check if required submodules from git are installed otherwise show error message and quit
    """
    global birdhouse_git_submodules, birdhouse_git_submodules_installed

    for key in birdhouse_git_submodules:
        module_path = os.path.join(birdhouse_main_directories["project"], birdhouse_git_submodules[key], "README.md")
        if not os.path.exists(module_path):
            print("ERROR: Submodule from git not installed: https://github.com/" + key + " in directory " +
                  birdhouse_git_submodules[key])
            print("-> Try: 'sudo git submodule update --init --recursive' in the root directory.")
            sys.exit()
    birdhouse_git_submodules_installed = True


def set_log_directory():
    """
    set logging directory and try to create if it doesn't exist
    """
    global birdhouse_main_directories, birdhouse_env, birdhouse_log_as_file, \
        birdhouse_log_directory, birdhouse_log_filename

    if birdhouse_env["dir_logging"] != "" and birdhouse_env["dir_logging"][0:1] == "/":
        birdhouse_log_directory = birdhouse_env["dir_logging"]
    elif birdhouse_env["dir_logging"] != "":
        birdhouse_log_directory = str(os.path.join(birdhouse_main_directories["project"], birdhouse_env["dir_logging"]))
    else:
        birdhouse_log_directory = birdhouse_main_directories["log"]

    try:
        if not os.path.exists(birdhouse_log_directory):
            print("Log directory doesn't exist yet. Created directory: " + birdhouse_log_directory)
            os.makedirs(birdhouse_log_directory)
    except Exception as e:
        print("Could not create log directory: " + str(e))
        print("Switch back to console logging.")
        birdhouse_log_as_file = False
    if not os.path.exists(birdhouse_log_directory):
        print("Could not create log directory: " + str(e))
        print("Switch back to console logging.")
        birdhouse_log_as_file = False

    birdhouse_log_filename = str(os.path.join(birdhouse_log_directory, "server.log"))


def set_loglevel():
    """
    set log level per module or class
    """
    global birdhouse_loglevel_default, birdhouse_loglevel_modules_all, birdhouse_loglevel_module, \
        birdhouse_loglevel_modules_error, birdhouse_loglevel_modules_warning, birdhouse_loglevel_modules_info, \
        birdhouse_loglevel_modules_debug

    if birdhouse_env["log_level"] is not None:
        birdhouse_loglevel_default = birdhouse_env["log_level"]

    for module in birdhouse_loglevel_modules_all:
        birdhouse_loglevel_module[module] = birdhouse_loglevel_default
    for module in birdhouse_loglevel_modules_info:
        birdhouse_loglevel_module[module] = logging.INFO
    for module in birdhouse_loglevel_modules_debug:
        birdhouse_loglevel_module[module] = logging.DEBUG
    for module in birdhouse_loglevel_modules_warning:
        birdhouse_loglevel_module[module] = logging.WARNING
    for module in birdhouse_loglevel_modules_error:
        birdhouse_loglevel_module[module] = logging.ERROR


def set_logging(name):
    """
    set logger and ensure it exists only once

    Args:
        name (str): logger name
    """
    global logger_exists, logger_list, loggers, birdhouse_loglevel_module

    init_time = time.time()
    log_as_file = birdhouse_log_as_file

    if loggers.get(name) or name in logger_list:
        # print("... logger already exists: " + name)
        return loggers.get(name)

    else:
        logger_exists[name] = init_time
        logger_list.append(name)

        if log_as_file:
            logger = logging.getLogger(name + str(init_time))
        else:
            logger = logging.getLogger(name)

        if name not in birdhouse_loglevel_module:
            log_level = birdhouse_loglevel_default
            logger.setLevel(log_level)
            print("Key '" + name + "' is not defined in preset.py in 'birdhouse_loglevel_module'.")
        else:
            log_level = birdhouse_loglevel_module[name]
            logger.setLevel(log_level)

        if log_as_file and os.access(birdhouse_log_filename, os.W_OK):
            # log_format = logging.Formatter(fmt='%(asctime)s |' + str(len(logger_list)).zfill(
            #    3) + '| %(levelname)-8s '+name.ljust(10)+' | %(message)s', # + "\n" + str(logger_list),
            #                               datefmt='%m/%d %H:%M:%S')

            log_format = logging.Formatter(fmt='%(asctime)s | %(levelname)-8s ' + name.ljust(10) + ' | %(message)s',
                                           datefmt='%m/%d %H:%M:%S')
            handler = RotatingFileHandler(filename=birdhouse_log_filename, mode='a',
                                          maxBytes=int(2.5 * 1024 * 1024),
                                          backupCount=2, encoding=None, delay=False)
            handler.setFormatter(log_format)
            logger.addHandler(handler)

        else:
            logging.basicConfig(format='%(asctime)s | %(levelname)-8s %(name)-10s | %(message)s',
                                datefmt='%m/%d %H:%M:%S',
                                level=log_level)

        logger.debug("___ Init logger '" + name + "', into_file=" + str(log_as_file))

        if log_as_file and not os.access(birdhouse_log_filename, os.W_OK):
            logger.warning("Could not write to log file " + birdhouse_log_filename)

        loggers[name] = logger
        return logger


def set_server_logging(system_arguments):
    """
    set function for global logging

    Args:
        system_arguments (str): depending on system arguments and settings in .env file set if logging into file
    """
    global srv_logging, ch_logging, birdhouse_log_as_file, birdhouse_env, view_logging

    # set logging
    if (len(system_arguments) > 0 and "--logfile" in system_arguments) or birdhouse_env["log_to_file"]:
        print('-------------------------------------------')
        print('Starting ...')
        print('-------------------------------------------')
        print("Using logfile " + birdhouse_log_filename + " ...")
        birdhouse_log_as_file = True


# ------------------------------------
# absolute paths
# ------------------------------------

birdhouse_main_directories = {
    "modules": os.path.dirname(os.path.abspath(__file__)),
    "working": os.path.dirname(os.path.abspath(__name__)),
    "server": os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."),
    "project": os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."),
    "app": os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "app"),
    "log": os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "log"),
    "data": os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data"),
    "download": os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data/downloads")
}

# ------------------------------------
# error handling
# ------------------------------------
birdhouse_initial_connect_msg = {}
birdhouse_error_images_raw = {}
birdhouse_error_images = {
    "setting": "camera_error_settings.jpg",
    "camera": "camera_error_hires.jpg",
    "lowres": "camera_error_lowres.png"
}

# ------------------------------------
# git sub modules
# ------------------------------------
birdhouse_git_submodules_installed = False
birdhouse_git_submodules = {
    "jc-prg/bird-detection": "server/modules/detection",
    "jc-prg/modules": "app/modules",
    "jc-prg/app-framework": "app/framework"
}


# ------------------------------------
# logging default settings
# ------------------------------------
birdhouse_loglevel_default = logging.INFO
birdhouse_loglevel_module = {}
birdhouse_loglevel_modules_all = [
    'root', 'backup', 'bu-dwnld', 'server', 'srv-info', 'srv-health',
    'cam-main', 'cam-img', 'cam-pi', 'cam-ffmpg', 'cam-video', 'cam-out', 'cam-other', 'cam-object', 'cam-stream',
    'cam-handl', 'cam-info',
    'config', 'config-Q',
    'DB-text', 'DB-json', 'DB-couch', 'DB-handler', 'image', 'mic-main', 'sensors',
    'video', 'video-srv', "img-eval",
    'views', 'view-head', 'view-chart', 'view-fav', 'view-arch', 'view-obj',
    'weather', 'weather-py', 'weather-om']

# add modules to the following lists to change their log_level
birdhouse_loglevel_modules_info = ["server"]
birdhouse_loglevel_modules_debug = []
birdhouse_loglevel_modules_warning = []
birdhouse_loglevel_modules_error = []


# ------------------------------------
# global configuration
# ------------------------------------
camera_list = []
birdhouse_env = {}
birdhouse_status = {"object_detection": False}
birdhouse_picamera = False
birdhouse_cache = True
birdhouse_cache_for_archive = False

set_global_configuration()

# ------------------------------------
# database configuration
# ------------------------------------

birdhouse_couchdb = {
    "db_usr": birdhouse_env["couchdb_user"],
    "db_pwd": birdhouse_env["couchdb_password"],
    "db_server_ip": "192.168.202.3",
    "db_server": "birdhouse_db",
    "db_port": 5984,
    "db_basedir": "/usr/src/app/data/"
}
if birdhouse_env["installation_type"].upper() != "DOCKER":
    birdhouse_couchdb["db_port"] = birdhouse_env["couchdb_port"]
    birdhouse_couchdb["db_server"] = birdhouse_env["couchdb_server"]
    birdhouse_couchdb["db_basedir"] = birdhouse_env["dir_project"] + "data/"

birdhouse_pages = {
    "live":             ("Live-Stream", "/index.html", "INDEX"),
    "backup":           ("Archiv", "/list_backup.html", "ARCHIVE"),
    "today":            ("Heute", "/list_short.html", "TODAY"),
    "today_complete":   ("Alle heute", "/list_new.html", "TODAY_COMPLETE"),
    "favorit":          ("Favoriten", "/list_star.html", "FAVORITES"),
    "cam_info":         ("Ger&auml;te", "/cameras.html", "DEVICES"),
    "video_info":       ("Video Info", "/video-info.html", ""),
    "videos":           ("Videos", "/videos.html", "VIDEOS"),
    "object":           ("Birds", "/birds.html", "BIRDS"),
    "save":             ("Speichern", "/image.jpg", "")
}
birdhouse_databases = {
    "config": {},
    "favorites": {},
    "today_images": {},
    "today_weather": {},
    "today_sensors": {},
    "today_statistics": {},
    "archive_images": {},
    "archive_sensors": {},
    "archive_weather": {},
    "archive_videos": {}
}
birdhouse_directories = {
    "backup": "images/",
    "backup_info": "images/",
    "html": "../app/",
    "data": "../data/",
    "main": "",
    "images": "images/",
    "favorites": "images/",
    "sensor": "images/",
    "statistics": "images/",
    "today": "00_today/",
    "objects": "images/",
    "custom_models": "custom_models/",
    "videos": "videos/",
    "videos_temp": "videos/images2video/",
    "audio_temp": "videos/images2video/",
    "weather": "images/"
}
birdhouse_files = {
    "main": "config.json",
    "birds": "birds.json",
    "backup": "config_images.json",
    "backup_info": "config_backup.json",
    "favorites": "config_favorites.json",
    "objects": "config_objects.json",
    "images": "config_images.json",
    "videos": "config_videos.json",
    "sensor": "config_sensor.json",
    "statistics": "config_statistics.json",
    "weather": "config_weather.json"
}
birdhouse_dir_to_database = {
    "config": "config",
    "birds": "birds",
    "images/config_sensor": "today_sensors",
    "images/config_weather": "today_weather",
    "images/config_statistics": "today_statistics",
    "images/config_backup": "archive_images",
    "images/config_favorites": "favorites",
    "images/config_objects": "objects",
    "videos/config_videos": "archive_videos",
    "images/00_today/config_images": "today_images",
    "images/<DATE>/config_images": "archive_images",
    "images/<DATE>/config_statistics": "archive_statistics",
    "images/<DATE>/config_sensors": "archive_sensors",
    "images/<DATE>/config_weather": "archive_weather"
}

# ------------------------------------
# set logging
# ------------------------------------
logger_list = []
loggers = {}
logger_exists = {}

birdhouse_log_as_file = False
birdhouse_log_directory = ""
birdhouse_log_filename = ""
birdhouse_log_format = logging.Formatter(fmt='%(asctime)s | %(levelname)-8s %(name)-10s | %(message)s',
                                         datefmt='%m/%d %H:%M:%S')

srv_logging = None
ch_logging = None
view_logging = None

set_loglevel()
set_log_directory()

# ------------------------------------
# device configuration
# ------------------------------------
birdhouse_weather = {
    "info_update": "none",
    "info_update_stamp": "none",
    "info_city": "",
    "info_format": "",
    "info_position": "",
    "info_status": {"running": ""},
    "current": {
        "temperature": None,
        "description": "",
        "description_icon": "",
        "wind_speed": None,
        "uv_index": None,
        "pressure": None,
        "humidity": None,
        "wind_direction": "",
        "precipitation": None
    },
    "forecast": {
        "today": {}
    }
}
birdhouse_default_cam = {
    "type": "default",
    "name": "NAME",
    "source": "/dev/video0",
    "active": True,
    "detection_mode": "similarity",
    "record": True,
    "record_micro": "",
    "image": {
        "crop": (0.1, 0.0, 0.85, 1.0),
        "resolution": "800x600",
        "show_framerate": True,
        "framerate": 12,
        "saturation": 50,
        "brightness": -1,
        "contrast": -1,
        "exposure": -1,
        "rotation": 0,
        "preview_scale": 18,
        "date_time": True,
        "date_time_position": (10, 20),
        "date_time_color": (255, 255, 255),
        "date_time_size": 0.4
    },
    "image_presets": {},
    "image_save": {
        "path": "images",
        "color": "ORIGINAL",
        "rhythm": "20",
        "rhythm_offset": "0",
        "record_from": "06",
        "record_to": "20",
        "seconds": ("00", "20", "40"),
        "hours": ("06", "07", "08", "09", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20")
    },
    "similarity": {
        "threshold": 95,
        "detection_area": (0.1, 0.1, 0.8, 0.8)
    },
    "object_detection": {
        "active": False,
        "classes": [],
        "detection_size": 40,
        "live": False,
        "model": "yolov5m",
        "threshold": 50
    },
    "video": {
        "allow_recording": True,
        "max_length": 180,
        "stream_port": 8008
    }
}

birdhouse_default_cam1 = birdhouse_default_cam.copy()
birdhouse_default_cam1["name"] = "Inside"
birdhouse_default_cam1["source"] = "/dev/video0"
birdhouse_default_cam1["record_micro"] = "mic1"

birdhouse_default_cam2 = birdhouse_default_cam.copy()
birdhouse_default_cam2["name"] = "Outside"
birdhouse_default_cam2["source"] = "/dev/video1"
birdhouse_default_cam2["image_save"]["offset"] = "5"
birdhouse_default_cam2["image_save"]["record_from"] = "sunrise+0"
birdhouse_default_cam2["image_save"]["record_to"] = "sunset+0"

birdhouse_default_micro = {
    "active": True,
    "name": "Inside",
    "device_id": 0,
    "device_name": "none",
    "sample_rate": 16000,
    "chunk_size": 1,
    "channels": 1,
    "type": "usb",
    "port": 5002
}

birdhouse_default_sensor = {
    "active": True,
    "name": "Inside",
    "type": "dht22",
    "pin": 10,
    "units": {
        "temperature": "°C",
        "humidity": "%"
    }
}
birdhouse_preset = {
    "backup": {
        "preview": "0700",  # HHMM
        "preview_fav": True,  # HHMM
        "time": "2000"
    },
    "devices": {
        "cameras": {
            "cam1": birdhouse_default_cam1,
            "cam2": birdhouse_default_cam2
        },
        "microphones": {
            "mic1": birdhouse_default_micro
        },
        "sensors": {
            "sensor1": birdhouse_default_sensor
        }
    },
    "info": {},
    "localization": {
        "language": "EN",
        "timezone": "UTC+1",
        "weather_active": True
    },
    "server": {  # set vars in the .env file
        "ip4_admin_deny": [""],
        "ip4_address": "",
        "ip4_stream_audio": "",
        "ip4_stream_video": "",
        "initial_setup": True
    },
    "title": "jc://birdhouse/",
    "views": {
        "index": {
            "type": "overlay",
            "lowres_pos_cam1": 1,
            "lowres_pos_cam2": 1
        }
    },
    "weather": {
        "active": True,
        "location": "Munich",
        "gps_location": [48.14, 11.58, "Munich"],
        "source": "Open-Metheo",
        "available_sources": ["Python-Weather", "Open-Metheo"]
    }
}

birdhouse_client_presets = {
    "filename": "config_stage.js",
    "directory": os.path.join(os.path.dirname(__file__), "../../app/birdhouse/"),
    "content": "//--------------------------------\n" +
               "// Configure stage details (" + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()) + ")\n" +
               "//---------------------------------\n" +
               "// Please edit not here, but in .env-File\n" +
               "var test		= " + birdhouse_env["test_instance"] + ";\n" +
               "var instance	= '" + birdhouse_env["which_instance"] + "';\n" +
               "var server_port = '" + birdhouse_env["port_api"] + "';\n\n" +
               "app_scripts_loaded += 1;\n\n"
}

file_types = {
    '.css': 'text/css',
    '.html': 'text/html',
    '.js': 'application/javascript',
    '.json': 'application/json',
    '.png': 'image/png',
    '.ico': 'image/ico',
    '.mp4': 'video/mp4',
    '.gif': 'image/gif',
    '.jpg': 'image/jpg',
    '.jpeg': 'image/jpg',
}

detection_default_models = ["yolov8n", "yolov8s", "yolov8m", "yolov8l", "yolov8x"]
detection_custom_model_path = os.path.join(birdhouse_main_directories["data"],
                                           birdhouse_directories["custom_models"])
detection_custom_models = glob.glob(os.path.join(detection_custom_model_path, "*.pt"))
detection_models = []
for directory in detection_custom_models:
    directory = directory.replace(str(detection_custom_model_path), "")
    detection_models.append(directory)
detection_models.extend(detection_default_models)

# http://codes.wmo.int/bufr4/codeflag/_0-20-003 (parts used by open-meteo.com)
birdhouse_weather_descriptions = {
    "0": "clear sky",
    "1": "clear",
    "2": "partly cloudy",
    "3": "overcast",
    "45": "fog",
    "48": "depositing rime fog",
    "51": "light drizzle",
    "53": "moderate drizzle",
    "55": "dense intensity drizzle",
    "56": "light freezing drizzle",
    "57": "dense intensity freezing drizzle",
    "61": "slight rain",
    "63": "moderate rain",
    "65": "heavy rain",
    "66": "light freezing rain",
    "67": "heavy freezing rain",
    "71": "slight snow fall",
    "73": "moderate snow fall",
    "75": "heavy snow fall",
    "77": "snow grains",
    "80": "slight rain showers",
    "81": "moderate rain showers",
    "82": "violent rain showers",
    "85": "slight snow showers",
    "86": "heavy snow showers",
    "95": "slight or moderate thunderstorms",
    "96": "thunderstorms with slight hail",
    "99": "thunderstorms with heavy hail"
}
birdhouse_weather_icons = {
    "0": "☀️",
    "1": "☀️",
    "2": "⛅️",
    "3": "☁️",
    "45": "🌫",
    "48": "🌫",
    "51": "🌦",
    "53": "🌦",
    "55": "🌧",
    "56": "🌨",
    "57": "️❄️",
    "61": "🌦",
    "63": "🌧",
    "65": "🌧",
    "66": "🌨",
    "67": "❄️",
    "71": "🌨",
    "73": "🌨",
    "75": "❄️",
    "77": "❄️",
    "80": "🌦",
    "81": "🌦",
    "82": "🌧",
    "85": "🌨",
    "86": "❄️",
    "95": "🌩",
    "96": "⛈",
    "99": "⛈",
    "100": "✨"
}

interesting_icons = {
    "other": "🌂 ☔ ❄ 🌈 🌬 🌡 ⚡ 🌞 ✨ ⭐ 🌟 💫 💦 🔅 🔆 ⛷ 🌍 🌎 🌏 🌐",
    "moons": "🌑 🌒 🌓 🌔 🌕 🌖 🌗 🌘",
    "weather": "🌤 🌦 🌧 🌨 🌩 🌪 ",
    "clock": "🕐 🕒 🕓 🕔 🕕 🕖 🕗 🕘 🕙 🕚 🕛 🕜 🕝 🕞 🕟 🕠 🕡 🕢 🕣 🕤 🕥 🕦 🕧",
    "calendar": "🗓️ 📅 📆 ⌚ ⏰ 🔔 🗒️ 📜 ⏳ ⌛"
}
