import os
import glob
import sys
import logging
import time
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler


def get_env(var_name):
    return os.environ.get(var_name)


def read_error_images():
    global birdhouse_error_images_raw, birdhouse_error_images
    import cv2
    for key in birdhouse_error_images:
        image_path = os.path.join(os.getcwd(), "data", birdhouse_error_images[key])
        if os.path.exists(image_path):
            birdhouse_error_images_raw[key] = cv2.imread(image_path)
        else:
            print("Could not load error image " + image_path)
            sys.exit()


def check_submodules():
    global birdhouse_git_submodules, birdhouse_git_submodules_installed

    for key in birdhouse_git_submodules:
        module_path = os.path.join(os.getcwd(), birdhouse_git_submodules[key], "README.md")
        if not os.path.exists(module_path):
            print("ERROR: Submodule from git not installed: https://github.com/" + key + " in directory " +
                  birdhouse_git_submodules[key])
            print("-> Try: 'sudo git submodule update --init --recursive' in the root directory.")
            sys.exit()
    birdhouse_git_submodules_installed = True


path = os.path.join(os.path.dirname(__file__), "../../.env")
load_dotenv(path)

logger_list = []
loggers = {}
logger_exists = {}

birdhouse_error_images_raw = {}
birdhouse_error_images = {
    "setting": "camera_error_settings.jpg",
    "camera": "camera_error_hires.jpg",
    "lowres": "camera_error_lowres.png"
}

birdhouse_git_submodules_installed = False
birdhouse_git_submodules = {
    "jc-prg/bird-detection": "server/modules/detection",
    "jc-prg/modules": "app/modules",
    "jc-prg/app-framework": "app/framework"
}

birdhouse_env = {
    "database_type": get_env("DATABASE_TYPE"),
    "database_cleanup": get_env("DATABASE_DAILY_CLEANUP").lower() in ("true", "1", 1, "yes", "on"),

    "rpi_active": get_env("RPI_ACTIVE").lower() in ("true", "1", 1, "yes", "on"),
    "rpi_64bit": get_env("RPI_64BIT").lower() in ("yes", "1", 1, "true", "on"),

    "couchdb_server": get_env("COUCHDB_SERVER"),
    "couchdb_user": get_env("COUCHDB_USER"),
    "couchdb_password": get_env("COUCHDB_PASSWORD"),
    "couchdb_port": get_env("COUCHDB_PORT"),

    "http_server": get_env("BIRDHOUSE_HTTP_SERVER"),
    "port_http": get_env("BIRDHOUSE_HTTP_PORT"),
    "port_api": get_env("BIRDHOUSE_API_PORT"),
    "port_video": get_env("BIRDHOUSE_VIDEO_PORT"),

    "server_audio": get_env("BIRDHOUSE_AUDIO_SERVER"),
    "port_audio": get_env("BIRDHOUSE_AUDIO_PORT"),

    "dir_project": get_env("BIRDHOUSE_DIR_PROJECT"),
    "dir_logging": get_env("BIRDHOUSE_DIR_LOGGING"),

    "admin_ip4_deny": get_env("ADMIN_IP4_DENY"),
    "admin_ip4_allow": get_env("ADMIN_IP4_ALLOW"),
    "admin_password": get_env("ADMIN_PASSWORD"),
    "admin_login": get_env("ADMIN_LOGIN"),

    "detection_active": (get_env("OBJECT_DETECTION").upper() in ("ON", "1", 1, "TRUE", "YES"))
}

birdhouse_log_into_file = True
birdhouse_loglevel = logging.INFO
birdhouse_loglevel_modules_info = ["mic-main", "server"]
birdhouse_loglevel_modules_debug = []
birdhouse_loglevel_modules_warning = []
birdhouse_loglevel_modules_error = []
birdhouse_loglevel_module = {
    "root": birdhouse_loglevel,
    "backup": birdhouse_loglevel,
    "cam-main": birdhouse_loglevel,
    "cam-img": birdhouse_loglevel,
    "cam-ffmpg": birdhouse_loglevel,
    "cam-video": birdhouse_loglevel,
    "cam-out": birdhouse_loglevel,
    "cam-other": birdhouse_loglevel,
    "cam-stream": birdhouse_loglevel,
    "config": birdhouse_loglevel,
    "config-Q": birdhouse_loglevel,
    "DB-text": birdhouse_loglevel,
    "DB-json": birdhouse_loglevel,
    "DB-couch": birdhouse_loglevel,
    "DB-handler": birdhouse_loglevel,
    "image": birdhouse_loglevel,
    "mic-main": birdhouse_loglevel,
    "sensors": birdhouse_loglevel,
    "server": birdhouse_loglevel,
    "srv-info": birdhouse_loglevel,
    "srv-health": birdhouse_loglevel,
    "video": birdhouse_loglevel,
    "video-srv": birdhouse_loglevel,
    "views": birdhouse_loglevel,
    "view-head": birdhouse_loglevel,
    "view-creat": birdhouse_loglevel,
    "weather": birdhouse_loglevel,
    "weather-py": birdhouse_loglevel,
    "weather-om": birdhouse_loglevel,
}

for module in birdhouse_loglevel_modules_info:
    birdhouse_loglevel_module[module] = logging.INFO
for module in birdhouse_loglevel_modules_debug:
    birdhouse_loglevel_module[module] = logging.DEBUG
for module in birdhouse_loglevel_modules_warning:
    birdhouse_loglevel_module[module] = logging.WARNING
for module in birdhouse_loglevel_modules_error:
    birdhouse_loglevel_module[module] = logging.ERROR

birdhouse_log_format = logging.Formatter(fmt='%(asctime)s | %(levelname)-8s %(name)-10s | %(message)s',
                                         datefmt='%m/%d %H:%M:%S')
birdhouse_log_filename = str(os.path.join(os.path.dirname(__file__), "../../log", "server.log"))
birdhouse_log_as_file = True

# birdhouse_loghandler = RotatingFileHandler(filename=birdhouse_log_filename, mode='a',
#                                            maxBytes=int(2.5 * 1024 * 1024),
#                                            backupCount=2, encoding=None, delay=False)
# birdhouse_loghandler.setFormatter(birdhouse_log_format)


birdhouse_couchdb = {
    "db_usr": birdhouse_env["couchdb_user"],
    "db_pwd": birdhouse_env["couchdb_password"],
    "db_server_ip": "192.168.202.3",
    "db_server": "birdhouse_db",
    "db_port": 5984,
    "db_basedir": "/usr/src/app/data/"
}
birdhouse_pages = {
    "live":             ("Live-Stream", "/index.html",       "INDEX"),
    "backup":           ("Archiv",      "/list_backup.html", "ARCHIVE"),
    "today":            ("Heute",       "/list_short.html",  "TODAY"),
    "today_complete":   ("Alle heute",  "/list_new.html",    "TODAY_COMPLETE"),
    "favorit":          ("Favoriten",   "/list_star.html",   "FAVORITES"),
    "cam_info":         ("Ger&auml;te", "/cameras.html",     "DEVICES"),
    "video_info":       ("Video Info",  "/video-info.html",  ""),
    "videos":           ("Videos",      "/videos.html",      "VIDEOS"),
    "save":             ("Speichern",   "/image.jpg",        "")
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
    "videos": "videos/",
    "videos_temp": "videos/images2video/",
    "audio_temp": "videos/images2video/",
    "weather": "images/"
}
birdhouse_files = {
    "main": "config.json",
    "backup": "config_images.json",
    "backup_info": "config_backup.json",
    "favorites": "config_favorites.json",
    "images": "config_images.json",
    "videos": "config_videos.json",
    "sensor": "config_sensor.json",
    "statistics": "config_statistics.json",
    "weather": "config_weather.json"
}
birdhouse_dir_to_database = {
    "config":                       "config",
    "images/config_images":         "today_images",
    "images/config_sensor":         "today_sensors",
    "images/config_weather":        "today_weather",
    "images/config_statistics":     "today_statistics",
    "images/config_backup":         "archive_images",
    "images/config_favorites":      "favorites",
    "videos/config_videos":         "archive_videos",
    "images/<DATE>/config_statistics": "archive_statistics",
    "images/<DATE>/config_images":     "archive_images",
    "images/<DATE>/config_sensors":    "archive_sensors",
    "images/<DATE>/config_weather":    "archive_weather"
}


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
    "record": True,
    "record_micro": "",
    "image": {
        "crop": (0.1, 0.0, 0.85, 1.0),
        "resolution": "800x600",
        "show_framerate": True,
        "framerate": 15,
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
        "live": False,
        "model": "yolov5m",
        "classes": [],
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
birdhouse_default_cam2["image_save"]["record_from"] = "sunrise-0"
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
        "preview": "0700",               # HHMM
        "preview_fav": True,               # HHMM
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
    "server": {                     # set vars in the .env file
        "ip4_admin_deny":   [""],
        "ip4_address":      "",
        "ip4_stream_audio": "",
        "ip4_stream_video": "",
        "initial_setup":    True
    },
    "title": "jc://birdhouse/",
    "views": {
        "index": {
            "type": "overlay",
            "lowres_position": 1
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
               "var test		= false;\n" +
               "var server_port = '" + birdhouse_env["port_api"] + "';\n\n"
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

detection_default_models = ["yolov5n", "yolov5s", "yolov5m", "yolov5l", "yolov5x",
                            "yolov5n6", "yolov5s6", "yolov5m6", "yolov5l6", "yolov5x6"]
detection_custom_model_path = "server/modules/detection/custom_models/"
detection_custom_models = glob.glob(detection_custom_model_path + "*.pt")
detection_models = detection_default_models
for directory in detection_custom_models:
    directory = directory.replace(detection_custom_model_path, "")
    detection_models.append(directory)

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
    "clock": "🕐 🕒 🕓 🕔 🕕 🕖 🕗 🕘 🕙 🕚 🕛 🕜 🕝 🕞 🕟 🕠 🕡 🕢 🕣 🕤 🕥 🕦 🕧"
}
