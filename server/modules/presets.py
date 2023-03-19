import os
import logging
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler


def get_env(var_name):
    return os.environ.get(var_name)


path = os.path.join(os.path.dirname(__file__), "../../.env")
load_dotenv(path)


birdhouse_env = {
    "couchdb_user": get_env("COUCHDB_USER"),
    "couchdb_password": get_env("COUCHDB_PASSWORD"),
    "couchdb_port": get_env("COUCHDB_PORT"),
    "port_http": get_env("BIRDHOUSE_HTTP_PORT"),
    "port_video": get_env("BIRDHOUSE_VIDEO_PORT"),
    "port_audio": get_env("BIRDHOUSE_AUDIO_PORT"),
    "dir_project": get_env("BIRDHOUSE_DIR_PROJECT"),
    "dir_logging": get_env("BIRDHOUSE_DIR_LOGGING")
}


birdhouse_log_into_file = True
birdhouse_loglevel = logging.INFO
birdhouse_loglevel_module = {
    "backup": birdhouse_loglevel,
    "cam-main": birdhouse_loglevel,
    "cam-img": birdhouse_loglevel,
    "cam-video": birdhouse_loglevel,
    "cam-out": birdhouse_loglevel,
    "cam-other": birdhouse_loglevel,
    "config": birdhouse_loglevel,
    "config-Q": birdhouse_loglevel,
    "DB-json": birdhouse_loglevel,
    "DB-couch": birdhouse_loglevel,
    "DB-handler": birdhouse_loglevel,
    "sensors": birdhouse_loglevel,
    "server": birdhouse_loglevel,
    "srv-info": birdhouse_loglevel,
    "srv-health": birdhouse_loglevel,
    "video-srv": birdhouse_loglevel,
    "views": birdhouse_loglevel,
    "view-head": birdhouse_loglevel,
    "view-creat": birdhouse_loglevel,
    "weather": birdhouse_loglevel,
    "weather-py": birdhouse_loglevel,
    "weather-om": birdhouse_loglevel,
}
birdhouse_log_format = logging.Formatter(fmt='%(asctime)s | %(levelname)-8s %(name)-10s | %(message)s',
                                         datefmt='%m/%d %H:%M:%S')
birdhouse_log_filename = str(os.path.join(os.path.dirname(__file__), "../../log", "server.log"))
birdhouse_loghandler = RotatingFileHandler(filename=birdhouse_log_filename, mode='a',
                                           maxBytes=int(2.5 * 1024 * 1024),
                                           backupCount=2, encoding=None, delay=False)
birdhouse_loghandler.setFormatter(birdhouse_log_format)


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
    "archive_images": {},
    "archive_sensors": {},
    "archive_weather": {},
    "archive_videos": {}
}
birdhouse_directories = {
    "html": "../app/",
    "data": "../data/",
    "main": "",
    "sensor": "images/",
    "images": "images/",
    "weather": "images/",
    "backup": "images/",
    "backup_info": "images/",
    "favorites": "images/",
    "videos": "videos/",
    "videos_temp": "videos/images2video/"
}
birdhouse_files = {
    "main": "config.json",
    "backup": "config_images.json",
    "backup_info": "config_backup.json",
    "favorites": "config_favorites.json",
    "images": "config_images.json",
    "videos": "config_videos.json",
    "sensor": "config_sensor.json",
    "weather": "config_weather.json"
}
birdhouse_dir_to_database = {
    "config":                       "config",
    "images/config_images":         "today_images",
    "images/config_sensor":         "today_sensors",
    "images/config_weather":        "today_weather",
    "images/config_backup":         "archive_images",
    "images/config_favorites":      "favorites",
    "videos/config_videos":         "archive_videos",
    "images/<DATE>/config_images":  "archive_images",
    "images/<DATE>/config_sensors": "archive_sensors",
    "images/<DATE>/config_weather": "archive_weather"
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
birdhouse_default_cam1 = {
    "type": "default",
    "name": "Inside",
    "source": "/dev/video0",
    "active": True,
    "record": True,
    "similarity": {
        "threshold": 90,
        "detection_type": "max_quarter",
        "detection_area": (0.1, 0.1, 0.8, 0.8)
    },
    "image": {
        "crop": (0.1, 0.0, 0.85, 1.0),
        "resolution": "800x600",
        "show_framerate": True,
        "framerate": "not implemented",
        "saturation": "not implemented",
        "rotation": 0,
        "reconnect_to_calibrate": False,
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
        "rhythm_offset": "3",
        "record_from": "06",
        "record_to": "22",
        "seconds": ("00", "20", "40"),
        "hours": ("06", "07", "08", "09", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20")
    },
    "video": {
        "allow_recording": True,
        "max_length": 180,
        "stream_port": 8008
    }
}
birdhouse_default_cam2 = {
    "type": "default",
    "name": "Outside",
    "source": "/dev/video1",
    "active": True,
    "record": True,
    "similarity": {
        "threshold": 90,
        "detection_type": "average",
        "detection_area": (0.1, 0.1, 0.8, 0.8)
    },
    "image": {
        "crop": (0.1, 0.0, 0.85, 1.0),
        "resolution": "800x600",
        "show_framerate": True,
        "framerate": "not implemented",
        "saturation": "not implemented",
        "reconnect_to_calibrate": False,
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
        "rhythm": "10",
        "rhythm_offset": "0",
        "record_from": "sunrise-1",
        "record_to": "sunset+1",
        "seconds": ("10", "30", "50"),
        "hours": ("06", "07", "08", "09", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20")
    },
    "video": {
        "allow_recording": True,
        "max_length": 180,
        "stream_port": 8008
    }
}
birdhouse_default_micro = {
    "active": True,
    "name": "Inside",
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
    "server": {
        "ip4_admin_deny":   ["192.168.1.31"],  # put in the IP address of your proxy or router if you don't want to allow edits from outside
        "ip4_address":      "192.168.1.20",
        "ip4_stream_audio": "",
        "ip4_stream_video": "",
        "rpi_active":       False,
        "port":             8000,              # http-port
        "port_video":       8008,
        "database_type":    "json",             # can be "json" or "couchdb"
        "database_port":    5100,
        "database_server":  "",
        "daily_clean_up":   True,
        "initial_setup":    True
    },
    "title": "jc://birdhouse/",
    "views": {
        "index": {
            "type": "default",
            "lowres_position": 1
        }
    },
    "weather": {
        "active": True,
        "location": "Munich",
        "gps_location": [48.14, 11.58],
        "source": "Open-Metheo",
        "available_sources": ["Python-Weather", "Open-Metheo"]
    }
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
