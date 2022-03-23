#!/usr/bin/python3

import os

#----------------------------------------------------

initial_path = os.path.dirname(os.path.abspath(__file__)).replace("/modules", "")


myPages = {
    "live":             ("Live-Stream", "/index.html",       "INDEX"),
    "backup":           ("Archiv",      "/list_backup.html", "ARCHIVE"),
    "today":            ("Heute",       "/list_short.html",  "TODAY"),
    "today_complete":   ("Alle heute",  "/list_new.html",    "TODAY_COMPLETE"),
    "favorit":          ("Favoriten",   "/list_star.html",   "FAVORITS"),
    "cam_info":         ("Kameras",     "/cameras.html",     "CAMERAS"),
    "video_info":       ("Video Info",  "/video-info.html",  ""),
    "videos":           ("Videos",      "/videos.html",      "VIDEOS"),
    "save":             ("Speichern",   "/image.jpg",        "")
}
myParameters = {
    "title":            "Unser Nistkasten :-)",
    "path":             initial_path,      # initially start from the working dir
    "port":             8000,              # http-port
    "preview_backup":   "0700",            # HHMM
    "ip4_admin_deny":   ["192.168.1.31"],  # put in the IP address of your proxy or router if you don't want to allow edits from outside
    "ip4_address":      "192.168.1.20",
    "backup_time":      "2000",            # HHMM
    "rpi_active":       False,

    "cameras": {
        "cam1": {
            "type":     "pi",
            "name":     "Innen",
            "source":   1,
            "active":   True,
            "record":   True,
            "similarity": {
                "threshold":        95,
                "detection_area":   (0.05,0.1,0.95,0.95)
            },
            "image": {
                "crop": (0.1, 0.0, 0.9, 1.0),
                "framerate": 24,
                "resolution": "900x1080",
                "saturation": -50,
                "rotation": 180,
                "date_time": True,
                "date_time_position": (10, 20),
                "date_time_color": (255, 255, 255),
                "date_time_size": 0.4
            },
            "image_save": {
                "path":     "images",
                "color":    "GRAY",
                "seconds":  ("00", "20", "40"),
                "hours":    ("06", "07", "08", "09", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20")
            },
            "video": {
                "allow_recording":  True,
                "max_length":       180,
                "streaming_server": "http://192.168.1.20:8008/"
            },
            "preview_scale": 18
       },
        "cam2"  : {
            "type":     "usb",
            "name":     "Au&szlig;en",
            "source":   1,
            "active":   True,
            "record":   True,
            "similarity" : {
                "threshold":        90,
                "detection_area":   (0.1, 0.1, 0.8, 0.8)
            },
            "image": {
                "crop":         (0.1, 0.0, 0.85, 1.0),
                "resolution":   "not implemented (640x480)",
                "framerate":    "not implemented",
                "saturation":   "not implemented",
                "rotation":     "not implemented",
                "date_time": True,
                "date_time_position": (10, 20),
                "date_time_color": (255, 255, 255),
                "date_time_size": 0.4
},
            "image_save": {
                "path":     "images",
                "color":    "ORIGINAL",
                "seconds":  ("10", "30", "50"),
                "hours":    ("06", "07", "08", "09", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20")
            },
            "video": {
                "allow_recording":      True,
                "max_length":           180,
                "streaming_server": "http://192.168.1.20:8008/"
            },
            "preview_scale": 18
        }
    },
    "microphones": {
        "mic1": {
            "active": True,
            "name": "Innen",
            "type": "usb",
            "port": 5002
        },
        "mic2" : {
            "active": False,
            "name": "Außen",
            "type": "usb",
            "port": 5001
        }
    },
    "sensors": {
        "sensor1": {
            "active": True,
            "name": "Innen-Thermometer",
            "type": "dht11",
            "pin": 4
        }
    }
}

myMIMEtypes = {
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
