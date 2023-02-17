
birdhouse_pages = {
    "live":             ("Live-Stream", "/index.html",       "INDEX"),
    "backup":           ("Archiv",      "/list_backup.html", "ARCHIVE"),
    "today":            ("Heute",       "/list_short.html",  "TODAY"),
    "today_complete":   ("Alle heute",  "/list_new.html",    "TODAY_COMPLETE"),
    "favorit":          ("Favoriten",   "/list_star.html",   "FAVORITES"),
    "cam_info":         ("Kameras",     "/cameras.html",     "CAMERAS"),
    "video_info":       ("Video Info",  "/video-info.html",  ""),
    "videos":           ("Videos",      "/videos.html",      "VIDEOS"),
    "save":             ("Speichern",   "/image.jpg",        "")
}

birdhouse_default_cam_pi = {
    "type": "default",
    "name": "Inside",
    "source": "/dev/video0",
    "active": True,
    "record": True,
    "similarity": {
        "threshold": 95,
        "detection_area": (0.05, 0.1, 0.95, 0.95)
    },
    "image": {
        "black_white": False,
        "crop": (0.1, 0.0, 0.9, 1.0),
        "framerate": 24,
        "show_framerate": True,
        "resolution": "800x600",
        "saturation": -50,
        "rotation": 0,
        "preview_scale": 18,
        "date_time": True,
        "date_time_position": (10, 20),
        "date_time_color": (255, 255, 255),
        "date_time_size": 0.4
    },
    "image_save": {
        "path": "images",
        "color": "GRAY",
        "seconds": ("00", "20", "40"),
        "hours": ("06", "07", "08", "09", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20")
    },
    "video": {
        "allow_recording": True,
        "max_length": 180,
        "stream_port": 8008
    }
}
birdhouse_default_cam_usb = {
    "type": "default",
    "name": "Outside",
    "source": "/dev/video1",
    "active": True,
    "record": True,
    "similarity": {
        "threshold": 90,
        "detection_area": (0.1, 0.1, 0.8, 0.8)
    },
    "image": {
        "crop": (0.1, 0.0, 0.85, 1.0),
        "resolution": "800x600",
        "show_framerate": True,
        "framerate": "not implemented",
        "saturation": "not implemented",
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
    "title": "Our Birdhouse :-)",
    "language": "EN",
    "backup": {
        "preview":   "0700",               # HHMM
        "time":      "2000"
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
        "timezone":         "UTC+1",
        "initial_setup":    True
    },
    "devices": {
        "cameras": {
            "cam1": birdhouse_default_cam_pi,
            "cam2": birdhouse_default_cam_usb
        },
        "microphones": {
            "mic1": birdhouse_default_micro
        },
        "sensors": {
            "sensor1": birdhouse_default_sensor
        }
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
