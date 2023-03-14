#!/usr/bin/python3

import os
import threading
import time
import json
import signal
import sys
import psutil
import subprocess

import logging
from logging.handlers import RotatingFileHandler

import socketserver
from http import server
from datetime import datetime
from urllib.parse import unquote

from modules.backup import BirdhouseArchive
from modules.camera import BirdhouseCamera
from modules.config import BirdhouseConfig
from modules.presets import *
from modules.views import BirdhouseViews
from modules.sensors import BirdhouseSensor


api_start = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
api_description = {"name": "BirdhouseCAM", "version": "v0.9.5"}
app_framework = "v0.9.5"


def on_exit(signum, handler):
    """
    Clean exit on Strg+C
    All shutdown functions are defined in the "finally:" section in the end of this script
    """
    print('\nSTRG+C pressed! (Signal: %s)' % (signum,))
    config.pause(True)
    for key in camera:
        camera[key].pause(True)
    for key in sensor:
        sensor[key].pause(True)
    time.sleep(1)
    confirm = "yes"

    while True:
        if confirm == "":
            confirm = input('Enter "yes" to cancel program now or "no" to keep running [yes/no]: ').strip().lower()

        if confirm == 'yes':
            print("Cancel!\n")
            config.pause(False)
            for key in camera:
                camera[key].pause(False)
            for key in sensor:
                sensor[key].pause(False)
            config.force_shutdown()
            time.sleep(5)
            sys.exit()
        elif confirm == 'no':
            config.pause(False)
            for key in camera:
                camera[key].pause(False)
            for key in sensor:
                sensor[key].pause(False)
            print("Keep running!\n")
            break
        else:
            confirm = ""
            print('Sorry, no valid answer...\n')
        pass


def on_kill(signum, handler):
    """
    Clean exit on kill command
    All shutdown functions are defined in the "finally:" section in the end of this script
    """
    print('\nKILL command detected! (Signal: %s)' % (signum,))
    srv_logging.warning('KILL command detected! (Signal: %s)' % (signum,))
    srv_logging.info("Starting shutdown ...")
    config.pause(True)
    config.force_shutdown()
    time.sleep(5)
    sys.exit()


def read_html(directory, filename, content=""):
    """
    read html file, replace placeholders and return for stream via webserver
    """
    if filename.startswith("/"):
        filename = filename[1:len(filename)]
    if directory.startswith("/"):
        directory = directory[1:len(directory)]
    file = os.path.join(config.main_directory, directory, filename)

    if not os.path.isfile(file):
        srv_logging.warning("File '" + file + "' does not exist!")
        return ""

    with open(file, "r") as page:
        page = page.read()

        for param in content:
            if "<!--" + param + "-->" in page:
                page = page.replace("<!--" + param + "-->", str(content[param]))
        for param in config.html_replace:
            if "<!--" + param + "-->" in page:
                page = page.replace("<!--" + param + "-->", str(config.html_replace[param]))

        page = page.encode('utf-8')
    return page


def read_image(directory, filename):
    """
    read image file and return for stream via webserver
    """
    if filename.startswith("/"):  filename = filename[1:len(filename)]
    if directory.startswith("/"): directory = directory[1:len(directory)]
    file = os.path.join(config.main_directory, directory, filename)
    file = file.replace("backup/", "")

    if not os.path.isfile(file):
        srv_logging.warning("Image '" + file + "' does not exist!")
        return ""

    with open(file, "rb") as image:
        f = image.read()
    return f


class ServerCheckThreads(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self._running = True
        self._interval = 60*5
        self._initial = True
        self._min_live_time = 65
        self._thread_info = {}

        self.logging = logging.getLogger("srv-check")
        self.logging.setLevel(birdhouse_loglevel)
        self.logging.addHandler(birdhouse_loghandler)
        self.logging.info("Starting Server Health Check ...")

    def run(self):
        last_update = time.time()
        count = 0
        while self._running:
            if last_update + self._interval < time.time():
                self.logging.info("Health check ...")
                last_update = time.time()
                count += 1

                self._thread_info = {
                    "views": time.time() - views.health_check,
                    "weather": time.time() - config.weather.health_check,
                    "weather-module": time.time() - config.weather.module.health_check,
                    "srv-info": time.time() - sys_info.health_check,
                    "config": time.time() - config.health_check,
                    "config-Q": time.time() - config.queue.health_check,
                    "DB-handler": time.time() - config.db_handler.health_check,
                    "backup": time.time() - backup.health_check
                }
                for sensor_id in sensor:
                    self._thread_info["sensor_"+sensor_id] = time.time() - sensor[sensor_id].health_check
                for camera_id in camera:
                    self._thread_info["camera_"+camera_id] = time.time() - camera[camera_id].health_check

                if self._initial:
                    self._initial = False
                    self.logging.info("... checking the following threads: " + str(self._thread_info.keys()))

                problem = []
                for key in self._thread_info:
                    if self._thread_info[key] > self._min_live_time:
                        problem.append(key + " (" + str(round(self._thread_info[key],1)) + "s)")

                if len(problem) > 0:
                    self.logging.warning("Not all threads are running as expected (<" + str(self._interval) + "s): ")
                    self.logging.warning("  -> " + ", ".join(problem))

            if count == 4:
                count = 0
                self.logging.info("Live sign health check!")

        self.logging.info("Stopped Server Health Check.")

    def stop(self):
        self._running = False


class ServerInformation(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self._running = True
        self._system_status = {}
        self._interval = 5
        self.health_check = time.time()

        self.logging = logging.getLogger("srv-info")
        self.logging.setLevel(birdhouse_loglevel)
        self.logging.addHandler(birdhouse_loghandler)
        self.logging.info("Starting Server Information ...")

    def run(self) -> None:
        while self._running:
            self.read()
            self.health_check = time.time()
            time.sleep(self._interval)

    def stop(self):
        self._running = False

    def read(self):
        system = {}
        # Initialize the result.
        result = 0.0
        # The first line in this file holds the CPU temperature as an integer times 1000.
        # Read the first line and remove the newline character at the end of the string.
        if os.path.isfile('/sys/class/thermal/thermal_zone0/temp'):
            with open('/sys/class/thermal/thermal_zone0/temp') as f:
                line = f.readline().strip()
            # Test if the string is an integer as expected.
            if line.isdigit():
                # Convert the string with the CPU temperature to a float in degrees Celsius.
                result = float(line) / 1000
        # Give the result back to the caller.
        system["cpu_temperature"] = result

        # cpu information
        system["cpu_usage"] = psutil.cpu_percent(interval=1, percpu=False)
        system["cpu_usage_detail"] = psutil.cpu_percent(interval=1, percpu=True)
        system["mem_total"] = psutil.virtual_memory().total / 1024 / 1024
        system["mem_used"] = psutil.virtual_memory().used / 1024 / 1024

        # diskusage
        hdd = psutil.disk_usage("/")
        system["hdd_used"] = hdd.used / 1024 / 1024 / 1024
        system["hdd_total"] = hdd.total / 1024 / 1024 / 1024

        # threading information
        # system["threads_active"] = str(threading.active_count())
        # system["threads_info"] = str(threading.enumerate())

        # read camera information
        process = subprocess.Popen(["v4l2-ctl --list-devices"], stdout=subprocess.PIPE, shell=True)
        output = process.communicate()[0]
        output = output.decode()
        output_2 = output.split("\n")
        last_key = "none"
        system["video_devices"] = {}
        system["video_devices_02"] = {}
        for value in output_2:
            if ":" in value:
                system["video_devices"][value] = []
                last_key = value
            elif value != "":
                value = value.replace("\t", "")
                system["video_devices"][last_key].append(value)
                info = last_key.split(":")
                system["video_devices_02"][value] = value + " (" + info[0] + ")"

        self._system_status = system.copy()

    def get(self):
        return self._system_status


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class StreamingHandler(server.BaseHTTPRequestHandler):

    def redirect(self, file):
        """
        Redirect to other file / URL
        """
        srv_logging.debug("Redirect: " + file)
        self.send_response(301)
        self.send_header('Location', file)
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()

    def error_404(self):
        """
        Send file not found
        """
        self.send_error(404)
        self.end_headers()

    def stream_file(self, filetype, content, no_cache=False):
        """
        send file content (HTML, image, ...)
        """
        if len(content) > 0:
            self.send_response(200)
            self.send_header('Access-Control-Allow-Credentials', 'true')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-type', filetype)
            self.send_header('Content-length', str(len(content)))
            if no_cache:
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")
            self.end_headers()
            self.wfile.write(content)
        else:
            self.error_404()

    def stream_video_header(self):
        """
        send header for video stream
        """
        self.send_response(200)
        self.send_header('Age', '0')
        self.send_header('Cache-Control', 'no-cache, private')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def stream_video_frame(self, frame):
        """
        send header and frame inside a MJPEG video stream
        """
        self.wfile.write(b'--FRAME\r\n')
        self.send_header('Content-Type', 'image/jpeg')
        self.send_header('Content-Length', str(len(str(frame))))
        self.end_headers()
        self.wfile.write(frame)
        self.wfile.write(b'\r\n')

    def stream_video_end(self):
        """
        send end header to close stream
        """
        self.end_headers()

    def admin_allowed(self):
        """
        Check if administration is allowed based on the IP4 the request comes from
        """
        srv_logging.debug("Check if administration is allowed: " + self.address_string() + " / " + str(
            config.param["server"]["ip4_admin_deny"]))
        if self.address_string() in config.param["server"]["ip4_admin_deny"]:
            return False
        else:
            return True

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', '*')
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_POST(self):
        """
        REST API for javascript commands e.g. to change values in runtime
        """
        srv_logging.debug("POST API request with '" + self.path + "'.")
        config.user_activity("set")
        response = {}

        if not self.admin_allowed():
            response["error"] = "Administration not allowed for this IP-Address!"
            self.stream_file(filetype='application/json', content=json.dumps(response).encode(encoding='utf_8'),
                             no_cache=True)

        if self.path.startswith("/api"):
            self.path = self.path.replace("/api", "")

        param = self.path.split("/")
        if self.path.endswith("/"):
            which_cam = param[len(param)-2]
        else:
            which_cam = param[len(param)-1]

        if self.path.startswith("/favorit/"):
            response = config.queue.set_status_favorite(self.path)
        elif self.path.startswith("/recycle/"):
            response = config.queue.set_status_recycle(self.path)
        elif self.path.startswith("/recycle-range/"):
            response = config.queue.set_status_recycle_range(self.path)
        elif self.path.startswith("/start/recording/"):
            response = camera[which_cam].video.record_start()
        elif self.path.startswith("/stop/recording/"):
            response = camera[which_cam].video.record_stop()
        elif self.path.startswith("/create-short-video/"):
            response = camera[which_cam].video.create_video_trimmed_queue(self.path)
        elif self.path.startswith("/create-day-video/"):
            response = camera[which_cam].video.create_video_day_queue(self.path)
        elif self.path.startswith('/recreate-image-config/'):
            response = backup.create_image_config_api(self.path)
        elif self.path.startswith('/reconnect_camera/'):
            response = camera[which_cam].camera_reconnect()
        elif self.path.startswith('/remove/'):
            response = backup.delete_marked_files_api(self.path)
        elif self.path.startswith('/clean_data_today/'):
            config.db_handler.clean_all_data("images")
            config.db_handler.clean_all_data("weather")
            config.db_handler.clean_all_data("sensor")
            response = {"cleanup": "done"}
        elif self.path.startswith('/force_backup/'):
            response = {}
            backup.start_backup()
        elif self.path.startswith('/force_restart/'):
            response = {}
            srv_logging.info("-------------------------------------------")
            srv_logging.info("FORCED SHUT-DOWN OF BIRDHOUSE SERVER .... !")
            srv_logging.info("-------------------------------------------")
            config.force_shutdown()
        elif self.path.startswith('/kill_stream/'):
            if "&" in which_cam:
                stream_id_kill = which_cam
                further_param = which_cam.split("&")
                which_cam = further_param[0]
                response = camera[which_cam].set_stream_kill(stream_id_kill)

        elif self.path.startswith("/edit_presets/"):
            param_string = self.path.replace("/edit_presets/", "")
            param = param_string.split("///")
            data = {}
            for entry in param:
                if "==" in entry:
                    key, value = entry.split("==")
                    data[key] = unquote(value)
                    data[key] = data[key].replace("%20", " ")
                    data[key] = data[key].replace("%22", "\"")
                    data[key] = data[key].replace("%5B", "[")
                    data[key] = data[key].replace("%5D", "]")
                    data[key] = data[key].replace("%7B", "{")
                    data[key] = data[key].replace("%7C", "|")
                    data[key] = data[key].replace("%7D", "}")
            config.main_config_edit("main", data)
            for key in camera:
                camera[key].config_update = True

        elif self.path.startswith("/check-timeout/"):
            time.sleep(30)
            response = {"check": "timeout"}
        else:
            self.error_404()
            return

        self.stream_file(filetype='application/json', content=json.dumps(response).encode(encoding='utf_8'),
                         no_cache=True)

    def do_GET(self):
        """
        check path and send requested content
        """
        global camera, sensor, config

        if config.shut_down:
            time.sleep(5)
            config.shut_down = False
            srv_logging.info("FINALLY KILLING ALL PROCESSES NOW!")
            server.server_close()
            server.shutdown()
            return

        config.user_activity("set")
        path, which_cam, further_param = views.selected_camera(self.path)
        file_ending = self.path.split(".")
        file_ending = "." + file_ending[len(file_ending) - 1].lower()

        if "+" in which_cam:
            which_cam2 = which_cam.split("+")[1]
            which_cam = which_cam.split("+")[0]
        else:
            which_cam2 = ""

        config.html_replace["title"] = config.param["title"]
        config.html_replace["active_cam"] = which_cam

        # get param
        param = ""
        redirect_app = "/app/index.html"
        if "?" in self.path:
            param = self.path.split("?")[1]
            redirect_app = "/app/index.html?"+param

        # index
        if self.path == "/":
            self.redirect(redirect_app)
        elif self.path.startswith("/index.html"):
            self.redirect(redirect_app)
        elif self.path == "/app" or self.path == "/app/":
            self.redirect(redirect_app)
        elif self.path.startswith("/api/"):
            self.do_GET_api(self.path, which_cam)
        elif '/image.jpg' in self.path:
            self.do_GET_image(self.path, which_cam)
        elif '/stream.mjpg' in self.path:
            self.do_GET_stream(self.path, which_cam, which_cam2, further_param)
        elif self.path.endswith('favicon.ico'):
            self.stream_file(filetype='image/ico', content=read_image(directory='../app', filename=self.path))
        elif self.path.startswith("/app/index.html"):
            self.stream_file(filetype=file_types[".html"], content=read_html(directory="../app", filename="index.html"))
        elif file_ending in file_types:
            if "/images/" in self.path or "/videos/" in self.path or "/archive/" in self.path:
                file_path = config.directories["data"]
            else:
                file_path = "../"
            if "text" in file_types[file_ending]:
                self.stream_file(filetype=file_types[file_ending], content=read_html(directory=file_path, filename=self.path))
            elif "application" in file_types[file_ending]:
                self.stream_file(filetype=file_types[file_ending], content=read_html(directory=file_path, filename=self.path))
            else:
                self.stream_file(filetype=file_types[file_ending], content=read_image(directory=file_path, filename=self.path))
        else:
            self.error_404()

    def do_GET_api(self, path, which_cam):
        """
        create API response
        """
        srv_logging.debug("GET API request with '" + path + "'.")
        request_start = time.time()
        param = path.split("/")
        command = param[2]
        status = "Success"
        version = {}

        if len(param) > 3:
            which_cam = param[3]

        # prepare API response
        api_response = {
            "STATUS": {
                "start_time": api_start,
                "current_time": config.local_time().strftime('%d.%m.%Y %H:%M:%S'),
                "admin_allowed": self.admin_allowed(),
                "check-version": version,
                "api-call": status,
                "reload": False,
                "system": {},
                "server": {
                    "view_archive_loading": views.archive_loading,
                    "view_favorite_loading": views.favorite_loading,
                    "backup_process_running": backup.backup_running,
                    "last_answer": ""
                },
                "devices": {
                    "cameras": {},
                    "sensors": {},
                    "weather": {},
                    "microphones": {}
                },
                "view": {
                    "selected": which_cam,
                    "active_cam": which_cam,
                    "active_date": "",
                    "active_page": command
                },
                "database": {}
            },
            "API": api_description,
            "WEATHER": {},
            "DATA": {}
        }

        # prepare DATA section
        api_data = {
            "active": {
                "active_cam": which_cam,
                "active_path": path,
                "active_page": command,
                "active_date": ""
            },
            "data": {},
            "settings": {},
            "view": {}
        }
        if len(param) >= 5 and command == "TODAY":
            api_data["active"]["active_date"] = param[4]

        # execute API commands
        if command == "INDEX":
            content = views.index(server=self)
        elif command == "FAVORITES":
            content = views.favorite_list(camera=which_cam)
        elif command == "TODAY":
            content = views.list(server=self)
        elif command == "TODAY_COMPLETE":
            content = views.complete_list_today(server=self)
        elif command == "ARCHIVE":
            content = views.archive_list(camera=which_cam)
        elif command == "VIDEOS":
            content = views.video_list(server=self)
        elif command == "VIDEO_DETAIL":
            content = views.detail_view_video(server=self)
        elif command == "DEVICES":
            content = views.camera_list(server=self)
            api_response["STATUS"]["system"] = sys_info.get()
            api_response["STATUS"]["system"]["hdd_archive"] = views.archive_dir_size / 1024

        elif command == "status" or command == "version" or command == "list":
            content = views.index(server=self)

            if len(param) > 3 and param[2] == "version":
                version["Code"] = "800"
                version["Msg"] = "Version OK."
                if param[3] != app_framework:
                    version["Code"] = "802"
                    version["Msg"] = "Update required."
            content["last_answer"] = ""

            if len(config.async_answers) > 0:
                content["last_answer"] = config.async_answers.pop()
                content["background_process"] = config.async_running

            if config.weather is not None:
                api_response["WEATHER"] = config.weather.get_weather_info("all")
                api_response["STATUS"]["devices"]["weather"] = config.weather.get_weather_info("status")

            api_response["STATUS"]["database"] = config.db_status()
            api_response["STATUS"]["system"] = sys_info.get()
            api_response["STATUS"]["system"]["hdd_archive"] = views.archive_dir_size / 1024

        else:
            content = {}
            status = "Error: command not found."

        # collect data for new DATA section
        param_to_publish = ["backup", "devices", "info", "localization", "server", "title", "views", "weather"]
        for key in param_to_publish:
            if key in config.param:
                api_data["settings"][key] = config.param[key]

        param_to_publish = ["entries", "entries_delete", "entries_yesterday", "groups", "chart_data", "weather_data"]
        for key in param_to_publish:
            if key in content:
                api_data["data"][key] = content[key]

        param_to_publish = ["view", "view_count", "links", "subtitle", "max_image_size"]
        for key in param_to_publish:
            if key in content:
                api_data["view"][key] = content[key]

        # collect data for "DATA" section
        param_to_publish = ["title", "backup", "weather", "views", "info"]
        for key in param_to_publish:
            if key in content:
                content[key] = config.param[key]

        # collect data for STATUS section
        param_to_publish = ["last_answer", "background_process"]
        for key in param_to_publish:
            if key in content:
                api_response["STATUS"]["server"][key] = content[key]

        # ensure localization data are available
        if "localization" in api_data["settings"]:
            if "language" not in api_data["settings"]["localization"]:
                api_data["settings"]["localization"]["language"] = "EN"
        else:
            api_data["settings"]["localization"] = birdhouse_preset["localization"]

        # get microphone data and create streaming information
        micro_data = config.param["devices"]["microphones"].copy()
        for key in micro_data:
            api_response["STATUS"]["devices"]["microphones"][key] = {"status": "not implemented yet"}
            if config.param["server"]["ip4_stream_audio"] == "":
                micro_data[key]["stream_server"] = config.param["server"]["ip4_address"]
            else:
                micro_data[key]["stream_server"] = config.param["server"]["ip4_stream_audio"]
            micro_data[key]["stream_server"] += ":" + str(micro_data[key]["port"])

        # get camera data and create streaming information
        camera_data = config.param["devices"]["cameras"].copy()
        for key in camera_data:
            if key in camera:
                api_response["STATUS"]["devices"]["cameras"][key] = camera[key].get_camera_status()
                camera_data[key]["video"]["stream"] = "/stream.mjpg?" + key
                camera_data[key]["video"]["stream_pip"] = "/pip/stream.mjpg?" + key + "+{2nd-camera-key}"
                camera_data[key]["video"]["stream_lowres"] = "/lowres/stream.mjpg?" + key
                camera_data[key]["video"]["stream_detect"] = "/detection/stream.mjpg?" + key
                camera_data[key]["device"] = "camera"
                camera_data[key]["image"]["resolution_max"] = camera[key].max_resolution
                camera_data[key]["image"]["current_streams"] = camera[key].get_stream_count()
                camera_data[key]["image"]["current_streams_detail"] = camera[key].image_streams
                #camera_data[key]["status"] = camera[key].get_camera_status()
                if config.param["server"]["ip4_stream_video"] == "":
                    camera_data[key]["video"]["stream_server"] = config.param["server"]["ip4_address"]
                else:
                    camera_data[key]["video"]["stream_server"] = config.param["server"]["ip4_stream_video"]
                camera_data[key]["video"]["stream_server"] += ":" + str(config.param["server"]["port_video"])

        # get sensor data
        sensor_data = config.param["devices"]["sensors"].copy()
        for key in sensor_data:
            api_response["STATUS"]["devices"]["sensors"][key] = sensor[key].get_status()
            sensor_data[key]["values"] = {}
            if key in sensor and sensor[key].running:
                sensor_data[key]["values"] = sensor[key].get_values()

        api_data["settings"]["devices"] = {
            "cameras": camera_data,
            "sensors": sensor_data,
            "microphones": micro_data
        }

        api_response["DATA"] = api_data
        api_response["API"]["request_time"] = round(time.time() - request_start, 2)

        if command != "status" and command != "list":
            del api_response["WEATHER"]
            # del api_response["STATUS"]

        self.stream_file(filetype='application/json', content=json.dumps(api_response).encode(encoding='utf_8'),
                         no_cache=True)

    def do_GET_image(self, path, which_cam):
        """
        create images as response
        """
        # show compared images
        if '/compare/' in path and '/image.jpg' in path:
            srv_logging.debug("Compare: Create and return image that shows differences to the former image ...")
            filename = os.path.join(config.db_handler.directory("images"), "_image_diff_" + which_cam + ".jpg")
            param = path.split("?")
            param = param[0].split("/")
            srv_logging.debug("---->" + param[2])
            srv_logging.debug("---->" + param[3])

            filename_1st = "image_" + which_cam + "_big_"+param[2]+".jpeg"
            filename_2nd = "image_" + which_cam + "_big_"+param[3]+".jpeg"
            filename_diff = "_image_diff_" + which_cam + ".jpg"
            path_1st = os.path.join(config.db_handler.directory("images"), filename_1st)
            path_2nd = os.path.join(config.db_handler.directory("images"), filename_2nd)
            path_diff = os.path.join(config.db_handler.directory("images"), filename_diff)

            image_1st = camera[which_cam].read_image(path_1st)
            image_2nd = camera[which_cam].read_image(path_2nd)
            image_diff = camera[which_cam].image.compare_raw_show(image_1st, image_2nd)
            image_diff = camera[which_cam].image.draw_text_raw(image_diff, "-> " + param[2] + ":" + param[3] + ":" +
                                                               param[4], position=(10, 20), scale=0.5, thickness=1)
            camera[which_cam].write_image(path_diff, image_diff)

            time.sleep(0.5)
            self.stream_file(filetype='image/jpeg',
                             content=read_image(directory="../data/images/", filename=filename_diff))

        # extract and show single image (creates images with a longer delay ?)
        elif '/image.jpg' in self.path:
            filename = "_image_temp_" + which_cam + ".jpg"
            path = os.path.join(config.db_handler.directory("images"), filename)
            camera[which_cam].write_image(path, camera[which_cam].get_stream_raw())
            time.sleep(2)
            self.stream_file(filetype='image/jpeg',
                             content=read_image(directory="../data/images/", filename=filename))

    def do_GET_stream(self, path, which_cam, which_cam2, further_param):
        """
        create stream
        """
        if camera[which_cam].type != "pi" and camera[which_cam].type != "usb" and \
                camera[which_cam].type != "default":
            srv_logging.warning("Unknown type of camera (" + camera[which_cam].type + "/" +
                                camera[which_cam].name + ")")
            self.error_404()
            return

        self.stream_video_header()

        stream_lowres = False
        stream_pip = False
        stream_active = True
        stream_id_int = datetime.now().timestamp()
        stream_id_ext = "&".join(further_param)

        stream_wait_while_error = 0.5
        stream_wait_while_recording = 1
        stream_wait_while_streaming = 0.01

        if '/lowres/stream.mjpg' in path:
            stream_lowres = True
        if '/pip/stream.mjpg' in path:
            stream_pip = True

        while stream_active:

            if camera[which_cam].get_stream_kill(stream_id_ext):
                stream_active = False
            if config.update["camera_" + which_cam]:
                camera[which_cam].update_main_config()

            if path.startswith("/detection/"):
                frame_raw = camera[which_cam].get_stream_raw(normalize=False, stream_id=stream_id_int,
                                                             lowres=stream_lowres)
            elif stream_pip and which_cam2 != "":
                frame_raw = camera[which_cam].get_stream_raw(normalize=True, stream_id=stream_id_int,
                                                             lowres=False)
                if which_cam2 in camera:
                    frame_raw2 = camera[which_cam2].get_stream_raw(normalize=True, stream_id=stream_id_int,
                                                                   lowres=True)
                    frame_raw = camera[which_cam].image.image_in_image_raw(frame_raw, frame_raw2)

            else:
                frame_raw = camera[which_cam].get_stream_raw(normalize=True, stream_id=stream_id_int,
                                                             lowres=stream_lowres)

            if not camera[which_cam].error and not camera[which_cam].image.error:
                if path.startswith("/detection/"):
                    if "black_white" in camera[which_cam].param["image"] and \
                            camera[which_cam].param["image"]["black_white"]:
                        frame_raw = camera[which_cam].image.convert_to_gray_raw(frame_raw)
                        frame_raw = camera[which_cam].image.convert_from_gray_raw(frame_raw)
                    if camera[which_cam].param["image"]["date_time"]:
                        frame_raw = camera[which_cam].image.draw_date_raw(raw=frame_raw,
                                                                          offset=camera[which_cam].param["image"][
                                                                              "crop_area"])
                    frame_raw = camera[which_cam].show_areas_raw(image=frame_raw)

                else:
                    if camera[which_cam].param["image"]["date_time"] and not stream_lowres:
                        frame_raw = camera[which_cam].image.draw_date_raw(frame_raw)

                    if camera[which_cam].video.recording and not stream_lowres:
                        srv_logging.debug("VIDEO RECORDING")
                        length = str(round(camera[which_cam].video.record_info()["length"]))
                        framerate = str(round(camera[which_cam].video.record_info()["framerate"]))
                        y_position = camera[which_cam].image_size[1] - 40
                        frame_raw = camera[which_cam].image.draw_text_raw(frame_raw, "Recording",
                                                                          position=(20, y_position),
                                                                          color=(0, 0, 255), scale=1, thickness=2)
                        frame_raw = camera[which_cam].image.draw_text_raw(frame_raw,
                                                                          "(" + length + "s/" + framerate + "fps)",
                                                                          position=(200, y_position), color=(0, 0, 255),
                                                                          scale=0.5, thickness=1)

                    if camera[which_cam].video.processing and not stream_lowres:
                        srv_logging.debug("VIDEO PROCESSING")
                        length = str(round(camera[which_cam].video.record_info()["length"]))
                        image_size = str(camera[which_cam].video.record_info()["image_size"])
                        y_position = camera[which_cam].image_size[1] - 40
                        frame_raw = camera[which_cam].image.draw_text_raw(frame_raw, "Processing",
                                                                          position=(20, y_position),
                                                                          color=(0, 255, 255), scale=1, thickness=2)
                        frame_raw = camera[which_cam].image.draw_text_raw(frame_raw,
                                                                          "(" + length + "s/" + image_size + ")",
                                                                          position=(200, y_position),
                                                                          color=(0, 255, 255),
                                                                          scale=0.5, thickness=1)

            try:
                frame = camera[which_cam].image.convert_from_raw(frame_raw)
                camera[which_cam].camera_wait_recording()
                self.stream_video_frame(frame)
                if not stream_active:
                    self.stream_video_end()
                    srv_logging.info("Closed streaming client: " + stream_id_ext)

            except Exception as e:
                stream_active = False
                if "Errno 104" in str(e) or "Errno 32" in str(e):
                    srv_logging.debug('Removed streaming client %s: %s', self.client_address, str(e))
                else:
                    srv_logging.warning('Removed streaming client %s: %s', self.client_address, str(e))

            if camera[which_cam].error or camera[which_cam].image.error:
                time.sleep(stream_wait_while_error)
            else:
                time.sleep(stream_wait_while_streaming)
                for key in camera:
                    if not camera[key].error:
                        if camera[key].video.processing:
                            time.sleep(stream_wait_while_recording)
                            break
                        if camera[key].video.recording:
                            time.sleep(stream_wait_while_recording)
                            break

    def do_GET_files(self):
        """
        create API response
        """
        return


if __name__ == "__main__":

    # help
    if len(sys.argv) > 0 and "--help" in sys.argv:
        print("jc://birdhouse/\n\nArguments:")
        print("--logfile    Write logging output to logfile 'stream.log'")
        print("--backup     Start backup directly (current date, delete directory before)")
        exit()

    log_into_file = True

    # set logging
    if len(sys.argv) > 0 and "--logfile" in sys.argv or birdhouse_log_into_file:

        srv_logging = logging.getLogger('root')
        srv_logging.setLevel(birdhouse_loglevel)
        srv_logging.addHandler(birdhouse_loghandler)
    else:
        logging.basicConfig(format='%(asctime)s | %(levelname)-8s %(name)-10s | %(message)s',
                            datefmt='%m/%d %H:%M:%S',
                            level=birdhouse_loglevel)
        srv_logging = logging.getLogger('root')

    srv_logging.info('-------------------------------------------')
    srv_logging.info('Starting ...')
    srv_logging.info('-------------------------------------------')

    # set system signal handler
    signal.signal(signal.SIGINT, on_exit)
    signal.signal(signal.SIGTERM, on_kill)

    # system information
    sys_info = ServerInformation()
    sys_info.start()

    # start config    
    config = BirdhouseConfig(param_init=birdhouse_preset, main_directory=os.path.dirname(os.path.abspath(__file__)))
    config.start()
    config.db_handler.directory_create("data")
    config.db_handler.directory_create("images")
    config.db_handler.directory_create("videos")
    config.db_handler.directory_create("videos_temp")
    time.sleep(0.5)

    # start sensors
    sensor = {}
    for sen in config.param["devices"]["sensors"]:
        settings = config.param["devices"]["sensors"][sen]
        sensor[sen] = BirdhouseSensor(sensor_id=sen, param=settings, config=config)
        sensor[sen].start()

    # start cameras
    camera = {}
    for cam in config.param["devices"]["cameras"]:
        settings = config.param["devices"]["cameras"][cam]
        camera[cam] = BirdhouseCamera(thread_id=cam, config=config, sensor=sensor)
        camera[cam].start()

    # start views and commands
    views = BirdhouseViews(config=config, camera=camera)
    views.start()
    config.set_views(views)

    # start backups
    time.sleep(1)
    backup = BirdhouseArchive(config, camera, views)
    backup.start()
    if len(sys.argv) > 0 and "--backup" in sys.argv:
        backup.backup_files()
        views.archive_list_update()

    # check if config files for main image directory exists and create if not exists
    if not os.path.isfile(config.db_handler.file_path("images")):
        for cam in camera:
            camera[cam].pause(True)
        backup.create_image_config()
        for cam in camera:
            camera[cam].pause(False)
    else:
        test_config = config.db_handler.read(config="images")
        if test_config == {}:
            backup.create_image_config()

    if not os.path.isfile(config.db_handler.file_path("videos")):
        backup.create_video_config()
    else:
        test_config = config.db_handler.read(config="videos")
        if test_config == {}:
            backup.create_video_config()

    # start health check
    health_check = ServerCheckThreads()
    health_check.start()

    # Start Webserver
    try:
        address = ('0.0.0.0', config.param["server"]["port"])
        server = StreamingServer(address, StreamingHandler)
        srv_logging.info("Starting WebServer on port "+str(config.param["server"]["port"])+" ...")
        server.serve_forever()
        srv_logging.info("STOPPED SERVER.")

    except Exception as e:
        srv_logging.error("Could not start WebServer: "+str(e))

    # Stop all processes to stop
    finally:
        health_check.stop()
        config.stop()
        sys_info.stop()
        backup.stop()
        for cam in camera:
            camera[cam].stop()
        for sen in sensor:
            sensor[sen].stop()
        views.stop()

        server.server_close()
        server.shutdown()
        time.sleep(5)
        srv_logging.info("Stopped WebServer.")
        srv_logging.info("-------------------------------------------")
