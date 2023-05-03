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
# from modules.micro import BirdhouseMicrophone
from modules.config import BirdhouseConfig
from modules.presets import *
from modules.views import BirdhouseViews
from modules.sensors import BirdhouseSensor

import pyaudio

api_start = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
api_description = {"name": "BirdhouseCAM", "version": "v0.9.8"}
app_framework = "v0.9.8"
srv_audio_stream = None
srv_audio = None

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


def on_exception(exc_type, value, tb):
    """
    grab all exceptions and write them to the logfile (if active)
    """
    srv_logging.exception("Uncaught exception: {0}".format(str(value)))
    srv_logging.exception("                    {0}".format(str(exc_type)))
    srv_logging.exception("                    {0}".format(str(tb)))


def on_exception_setting():
    """
    Workaround for `sys.excepthook` thread bug from:
    http://bugs.python.org/issue1230540

    Call once from the main thread before creating any threads.
    """
    init_original = threading.Thread.__init__

    def init(self, *args, **kwargs):

        init_original(self, *args, **kwargs)
        run_original = self.run

        def run_with_except_hook(*args2, **kwargs2):
            try:
                run_original(*args2, **kwargs2)
            except Exception:
                sys.excepthook(*sys.exc_info())

        self.run = run_with_except_hook

    threading.Thread.__init__ = init


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


class ServerHealthCheck(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self._running = True
        self._interval = 5
        self._interval_check = 60 * 5
        self._initial = True
        self._min_live_time = 65
        self._thread_info = {}
        self._health_status = None

        self.logging = logging.getLogger("srv-health")
        self.logging.setLevel(birdhouse_loglevel_module["srv-health"])
        self.logging.addHandler(birdhouse_loghandler)
        self.logging.info("Starting Server Health Check ...")

    def run(self):
        last_update = time.time()
        count = 0
        while self._running:
            time.sleep(self._interval)
            if last_update + self._interval_check < time.time():
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
                    self._thread_info["sensor_" + sensor_id] = time.time() - sensor[sensor_id].health_check

#                for mic_id in microphones:
#                    self._thread_info["mic_" + mic_id] = time.time() - microphones[mic_id].health_check

                for camera_id in camera:
                    self._thread_info["camera_" + camera_id] = time.time() - camera[camera_id].health_check
                    health_state = camera[camera_id].camera_stream_raw.health_check
                    self._thread_info["camera_" + camera_id + "_raw"] = time.time() - health_state
                    health_state = camera[camera_id].video.health_check
                    self._thread_info["camera_" + camera_id + "_video"] = time.time() - health_state
                    for stream_id in camera[camera_id].camera_streams:
                        health_state = camera[camera_id].camera_streams[stream_id].health_check
                        self._thread_info["camera_" + camera_id + "_edit_" + stream_id] = time.time() - health_state

                if self._initial:
                    self._initial = False
                    self.logging.info("... checking the following threads: " + str(self._thread_info.keys()))

                problem = []
                for key in self._thread_info:
                    if self._thread_info[key] > self._min_live_time:
                        problem.append(key + " (" + str(round(self._thread_info[key], 1)) + "s)")

                if len(problem) > 0:
                    self.logging.warning(
                        "... not all threads are running as expected (<" + str(self._interval) + "s): ")
                    self.logging.warning("  -> " + ", ".join(problem))
                    self._health_status = "NOT RUNNING: " + ", ".join(problem)
                else:
                    self.logging.info("... OK.")
                    self._health_status = "OK"

            if count == 4:
                count = 0
                self.logging.info("Live sign health check!")

        self.logging.info("Stopped Server Health Check.")

    def status(self):
        return self._health_status

    def stop(self):
        self._running = False


class ServerInformation(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self._running = True
        self._system_status = {}
        self._interval = 5
        self.health_check = time.time()
        self.main_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

        self.logging = logging.getLogger("srv-info")
        self.logging.setLevel(birdhouse_loglevel_module["srv-info"])
        self.logging.addHandler(birdhouse_loghandler)

        self.microphones = None

    def run(self) -> None:
        self.logging.info("Starting Server Information ...")
        while self._running:
            self.read()
            self.health_check = time.time()
            if config.shut_down:
                self.stop()
            time.sleep(self._interval)
        self.logging.info("Stopped Server Information.")

    def stop(self):
        self._running = False

    def read(self):
        global srv_audio

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

        try:
            cmd_data = ["du", "-hs", os.path.join(self.main_dir, "data")]
            system["hdd_data"] = str(subprocess.check_output(cmd_data))
            system["hdd_data"] = system["hdd_data"].replace("b'", "")
            system["hdd_data"] = system["hdd_data"].split("\\t")[0]
            if "k" in system["hdd_data"]:
                system["hdd_data"] = float(system["hdd_data"].replace("k", "")) / 1024 / 1024
            elif "M" in system["hdd_data"]:
                system["hdd_data"] = float(system["hdd_data"].replace("M", "")) / 1024
            elif "G" in system["hdd_data"]:
                system["hdd_data"] = float(system["hdd_data"].replace("G", ""))
        except Exception as e:
            self.logging.warning("Was not able to get size of data dir: " + (str(cmd_data)) + " - " + str(e))

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
        system["audio_devices"] = {}

        test = True
        if test:
            if self.microphones is None:
                srv_audio = pyaudio.PyAudio()
                info = srv_audio.get_host_api_info_by_index(0)
                num_devices = info.get('deviceCount')
                for i in range(0, num_devices):
                    if (audio1.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                        name = audio1.get_device_info_by_host_api_device_index(0, i).get('name')
                        info = audio1.get_device_info_by_host_api_device_index(0, i)
                        system["audio_devices"][name] = {
                            "id": i,
                            "input": info.get("maxInputChannels"),
                            "output": info.get("maxOutputChannels"),
                            "sample_rate": info.get("defaultSampleRate")

                        }
                self.microphones = system["audio_devices"]
            else:
                system["audio_devices"] = self.microphones

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
            try:
                self.wfile.write(content)
            except Exception as err:
                srv_logging.error("Error streaming file (" + filetype + "): " + str(err))
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

    def stream_audio_header(self):
        """
        send header for video stream
        """
        self.send_response(200)
        self.send_header('Age', '0')
        self.send_header('Cache-Control', 'no-cache, private')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Content-Type', 'audio/x-wav; codec=PCM')
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def stream_video_frame(self, frame, which_cam):
        """
        send header and frame inside a MJPEG video stream
        """
        # try:
        self.wfile.write(b'--FRAME\r\n')
        self.send_header('Content-Type', 'image/jpeg')
        self.send_header('Content-Length', str(len(str(frame))))
        self.end_headers()
        self.wfile.write(frame)
        self.wfile.write(b'\r\n')
        # except Exception as err:
        #    srv_logging.error("Error streaming video frame (" + which_cam + "): " + str(err))

    def stream_video_end(self):
        """
        send end header to close stream
        """
        self.end_headers()

    def admin_allowed(self):
        """
        Check if administration is allowed based on the IP4 the request comes from
        """
        admin_type = birdhouse_env["admin_login"]
        admin_deny = birdhouse_env["admin_ip4_deny"]
        admin_allow = birdhouse_env["admin_ip4_allow"]
        admin_pwd = birdhouse_env["admin_password"]

        srv_logging.debug("Check if administration is allowed: " +
                          admin_type + " / " + self.address_string() + " / " +
                          "DENY=" + str(admin_deny) + "; ALLOW=" + str(admin_allow))

        if admin_type == "DENY":
            if self.address_string() in admin_deny:
                return False
            else:
                return True
        elif admin_type == "ALLOW":
            if self.address_string() in admin_allow:
                return True
            else:
                return False
        elif admin_type == "LOGIN":
            # initial implementation, later with session ID
            param = self.path_split(check_allowed=False)
            if param["session_id"] == admin_pwd:
                return True
            else:
                return False
        else:
            return False

    def path_split(self, check_allowed=True):
        """
        split path into parameters
        -> /app/index.html?<PARAMETER>
        -> /api/<command>/<param1>/<param2>/<param3>/<which_cam+other_cam>
        -> /<other-path>/<filename>.<ending>?parameter1&parameter2
        """
        this_path = self.path.replace("///", "###")
        elements = this_path.split("/")
        param = {
            "app_api": elements[1],
            "command": "NONE",
            "session_id": "",
            "which_cam": "cam1",
            "other_cam": "",
            "parameter": [],
            "path": self.path,
            "path_short": "",
            "file_ending": "",
            "admin_allowed": False
        }
        if check_allowed:
            param["admin_allowed"] = self.admin_allowed()

        if elements[-1] == "":
            del elements[-1]

        if len(elements) > 2:
            param["command"] = elements[2]

        if self.path.startswith("/api/status") or self.path.startswith("/api/version"):
            if "version" in self.path:
                param["session_id"] = elements[3]

        elif "/edit-presets/" in self.path:
            param["session_id"] = elements[2]
            param["command"] = "edit-presets"
            param["which_cam"] = ""
            if len(elements) > 4:
                param["parameter"] = elements[4]
            if len(elements) > 5:
                param["which_cam"] = elements[5]

        elif self.path.startswith("/api"):
            param["session_id"] = elements[2]
            param["command"] = elements[3]
            last_is_cam = True

            complete_cam = elements[len(elements) - 1]
            if "+" in complete_cam:
                param["which_cam"] = complete_cam.split("+")[0]
                param["other_cam"] = complete_cam.split("+")[1]
            else:
                param["which_cam"] = complete_cam

            if param["command"]:
                if param["which_cam"] not in views.camera:
                    srv_logging.warning("Unknown camera requested: " + param["which_cam"] + " (" + self.path + ")")
                    param["which_cam"] = "cam1"
                    last_is_cam = False

            count = 0
            amount = len(elements)
            if last_is_cam:
                amount -= 1
            while count < len(elements):
                if 3 < count < amount:
                    param["parameter"].append(elements[count])
                count += 1

            param["path_short"] = self.path.replace("/api", "")

        elif self.path.startswith("/app/index.html"):
            if "?" in self.path:
                html_param = self.path.split("?")
                param["command"] = html_param[1]
            else:
                param["command"] = "INDEX"

        else:
            if "." in self.path:
                param["file_ending"] = self.path.split(".")
                param["file_ending"] = "." + param["file_ending"][len(param["file_ending"]) - 1].lower()

            if "?" in self.path:
                temp = self.path.split("?")[1]
                temp = temp.split("&")
                param["which_cam"] = temp[0]
                if len(temp) > 2:
                    param["parameter"] = [temp[1]]
                    param["session_id"] = temp[2]

        return param

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
        config.user_activity("set")
        param = self.path_split()
        which_cam = param["which_cam"]

        srv_logging.debug("POST API request with '" + self.path + "'.")
        srv_logging.debug(str(param))

        api_response = {
            "API": api_description,
            "STATUS": {},
            "WEATHER": {},
            "DATA": {}
        }
        response = {}

        if not self.admin_allowed() and param["command"] != "check-pwd":
            response["error"] = "Administration not allowed!"
            self.stream_file(filetype='application/json', content=json.dumps(response).encode(encoding='utf_8'),
                             no_cache=True)
            return

        if param["command"] == "favorit":
            response = config.queue.set_status_favorite(param)
        elif param["command"] == "recycle":
            response = config.queue.set_status_recycle(param)
        elif param["command"] == "recycle-threshold":
            # http://localhost:8007/api/1682709071876/recycle-threshold/backup/20230421/95/cam1/
            srv_logging.info("RECYCLE THRESHOLD")
            response = config.queue.set_status_recycle_threshold(param)
        elif param["command"] == "recycle-range":
            response = config.queue.set_status_recycle_range(param)
        elif param["command"] == "create-short-video":
            response = camera[which_cam].video.create_video_trimmed_queue(param)
        elif param["command"] == "recreate-image-config":
            response = backup.create_image_config_api(param)
        elif param["command"] == "create-day-video":
            response = camera[which_cam].video.create_video_day_queue(param)
        elif param["command"] == "remove":
            response = backup.delete_marked_files_api(param)
        elif param["command"] == "reconnect-camera":
            response = camera[which_cam].camera_reconnect()
        elif param["command"] == "camera-settings":
            response = camera[which_cam].get_camera_settings(param)
        elif param["command"] == "start-recording":
            response = camera[which_cam].video.record_start()
        elif param["command"] == "stop-recording":
            response = camera[which_cam].video.record_stop()
        elif param["command"] == "clean-data-today":
            config.db_handler.clean_all_data("images")
            config.db_handler.clean_all_data("weather")
            config.db_handler.clean_all_data("sensor")
            response = {"cleanup": "done"}
        elif param["command"] == "update-views":
            views.archive_list_update(force=True)
            views.favorite_list_update(force=True)
            response = {"update_views": "started"}
        elif param["command"] == "force-backup":
            backup.start_backup()
            response = {"backup": "started"}
        elif param["command"] == "force-restart":
            srv_logging.info("-------------------------------------------")
            srv_logging.info("FORCED SHUT-DOWN OF BIRDHOUSE SERVER .... !")
            srv_logging.info("-------------------------------------------")
            config.force_shutdown()
            response = {"shutdown": "started"}
        elif param["command"] == "check-timeout":
            time.sleep(30)
            response = {"check": "timeout"}
        elif param["command"] == "kill-stream":
            stream_id = param["parameter"][0]
            if "&" in stream_id:
                stream_id_kill = stream_id.split("&")[-1]
                camera[which_cam].set_stream_kill(stream_id_kill)
                response = {
                    "kill-stream": which_cam,
                    "kill-stream-id": stream_id
                }
        elif param["command"] == "edit-presets":
            edit_param = param["parameter"].split("###")
            data = {}
            for entry in edit_param:
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
                    data[key] = data[key].replace("-dev-", "/dev/")
            srv_logging.info(str(data))
            config.main_config_edit("main", data)
            if which_cam in camera:
                camera[which_cam].config_update = True
        elif param["command"] == "set-temp-threshold":
            srv_logging.info("Set temporary threshold to camera '"+which_cam+"': " + str(param["parameter"]))
            if which_cam in camera:
                camera[which_cam].record_temp_threshold = param["parameter"]
        elif param["command"] == "check-pwd":
            admin_pwd = birdhouse_env["admin_password"]
            if admin_pwd == param["parameter"][0]:
                response["check-pwd"] = True
            else:
                response["check-pwd"] = False
        else:
            self.error_404()
            return

        api_response["STATUS"] = response

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
        param = self.path_split()
        which_cam = param["which_cam"]
        which_cam2 = param["other_cam"]
        further_param = param["parameter"]
        file_ending = param["file_ending"]

        config.html_replace["title"] = config.param["title"]
        config.html_replace["active_cam"] = param["which_cam"]

        # get param
        redirect_app = "/app/index.html"
        if "?" in self.path:
            redirect_app += "?" + self.path.split("?")[1]

        # index
        if self.path == "/":
            self.redirect(redirect_app)
        elif self.path.startswith("/index.html"):
            self.redirect(redirect_app)
        elif self.path == "/app" or self.path == "/app/":
            self.redirect(redirect_app)
        elif self.path.startswith("/api/"):
            self.do_GET_api()
        elif '/image.jpg' in self.path:
            self.do_GET_image(which_cam)
        elif '/stream.mjpg' in self.path:
            self.do_GET_stream_video(which_cam, which_cam2, param)
        elif '/audio.wav' in self.path:
            self.do_GET_stream_audio(which_cam, param)
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
                self.stream_file(filetype=file_types[file_ending],
                                 content=read_html(directory=file_path, filename=self.path))
            elif "application" in file_types[file_ending]:
                self.stream_file(filetype=file_types[file_ending],
                                 content=read_html(directory=file_path, filename=self.path))
            else:
                self.stream_file(filetype=file_types[file_ending],
                                 content=read_image(directory=file_path, filename=self.path))
        else:
            self.error_404()

    def do_GET_api(self):
        """
        create API response
        """
        request_start = time.time()
        status = "Success"
        version = {}

        param = self.path_split()
        which_cam = param["which_cam"]
        command = param["command"]

        srv_logging.debug("GET API request with '" + self.path + "'.")
        srv_logging.debug(str(param))

        # prepare API response
        api_response = {
            "API": api_description,
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
                    "queue_waiting_time": config.queue.queue_wait,
                    "health_check": health_check.status(),
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
            "WEATHER": {},
            "DATA": {}
        }

        # prepare DATA section
        api_data = {
            "active": {
                "active_cam": which_cam,
                "active_path": self.path,
                "active_page": command,
                "active_date": ""
            },
            "data": {},
            "settings": {},
            "view": {}
        }
        if command == "TODAY" and len(param["parameter"]) > 0:
            api_data["active"]["active_date"] = param["parameter"][0]
            api_response["STATUS"]["view"]["active_date"] = param["parameter"][0]

        # execute API commands
        if command == "INDEX":
            content = views.index_view(param=param)
        elif command == "FAVORITES":
            content = views.favorite_list(param=param)
        elif command == "TODAY":
            content = views.list(param=param)
        elif command == "TODAY_COMPLETE":
            content = views.complete_list_today(param=param)
        elif command == "ARCHIVE":
            content = views.archive_list(param=param)
        elif command == "VIDEOS":
            content = views.video_list(param=param)
        elif command == "VIDEO_DETAIL":
            content = views.detail_view_video(param=param)
        elif command == "DEVICES":
            content = views.camera_list(param=param)
            api_response["STATUS"]["system"] = sys_info.get()
            api_response["STATUS"]["system"]["hdd_archive"] = views.archive_dir_size / 1024
        elif command == "status" or command == "version" or command == "list" or command == "reload":
            content = views.index_view(param=param)

            if command == "version":
                version["Code"] = "800"
                version["Msg"] = "Version OK."
                if app_framework != param["session_id"]:
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

            if command == "reload":
                api_response["STATUS"]["reload"] = True
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
            micro_data[key]["stream_server"] = birdhouse_env["server_audio"]
            micro_data[key]["stream_server"] += ":" + str(micro_data[key]["port"])

        # get camera data and create streaming information
        camera_data = config.param["devices"]["cameras"].copy()
        for key in camera_data:
            if key in camera:
                api_response["STATUS"]["devices"]["cameras"][key] = camera[key].get_camera_status()
                camera_data[key]["video"]["stream"] = "/stream.mjpg?" + key
                camera_data[key]["video"]["stream_pip"] = "/pip/stream.mjpg?" + key + \
                                                          "+{2nd-camera-key}:{2nd-camera-pos}"
                camera_data[key]["video"]["stream_lowres"] = "/lowres/stream.mjpg?" + key
                camera_data[key]["video"]["stream_detect"] = "/detection/stream.mjpg?" + key
                camera_data[key]["device"] = "camera"
                camera_data[key]["image"]["resolution_max"] = camera[key].max_resolution
                camera_data[key]["image"]["current_streams"] = camera[key].get_stream_count()
                camera_data[key]["image"]["current_streams_detail"] = camera[key].image_streams
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
            if key in sensor and sensor[key].if_running():
                sensor_data[key]["values"] = sensor[key].get_values()

        api_data["settings"]["devices"] = {
            "cameras": camera_data,
            "sensors": sensor_data,
            "microphones": micro_data
        }

        api_response["DATA"] = api_data
        api_response["DATA"]["settings"]["server"]["port"] = birdhouse_env["port_http"]
        api_response["DATA"]["settings"]["server"]["port_video"] = birdhouse_env["port_video"]
        api_response["DATA"]["settings"]["server"]["port_audio"] = birdhouse_env["port_audio"]
        api_response["DATA"]["settings"]["server"]["server_audio"] = birdhouse_env["port_audio"]
        api_response["DATA"]["settings"]["server"]["database_port"] = birdhouse_env["couchdb_port"]
        api_response["DATA"]["settings"]["server"]["database_server"] = birdhouse_env["couchdb_server"]
        api_response["DATA"]["settings"]["server"]["ip4_admin_deny"] = birdhouse_env["admin_ip4_deny"]
        api_response["DATA"]["settings"]["server"]["ip4_admin_allow"] = birdhouse_env["admin_ip4_allow"]
        api_response["DATA"]["settings"]["server"]["admin_login"] = birdhouse_env["admin_login"]
        api_response["API"]["request_time"] = round(time.time() - request_start, 2)

        if command != "status" and command != "list" and command != "version":
            del api_response["WEATHER"]
            del api_response["STATUS"]["system"]
            del api_response["STATUS"]["database"]
            del api_response["STATUS"]["check-version"]

        self.stream_file(filetype='application/json', content=json.dumps(api_response).encode(encoding='utf_8'),
                         no_cache=True)

    def do_GET_image(self, which_cam):
        """
        create images as response
        """
        # show compared images
        if '/compare/' in self.path and '/image.jpg' in self.path:
            srv_logging.debug("Compare: Create and return image that shows differences to the former image ...")
            filename = os.path.join(config.db_handler.directory("images"), "_image_diff_" + which_cam + ".jpg")
            param = self.path.split("?")
            param = param[0].split("/")
            srv_logging.debug("---->" + param[2])
            srv_logging.debug("---->" + param[3])

            filename_1st = "image_" + which_cam + "_big_" + param[2] + ".jpeg"
            filename_2nd = "image_" + which_cam + "_big_" + param[3] + ".jpeg"
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
            img_path = os.path.join(config.db_handler.directory("images"), filename)
            camera[which_cam].write_image(img_path, camera[which_cam].get_stream(stream_id="file",
                                                                                 stream_type="camera",
                                                                                 stream_resolution="hires"))
            time.sleep(2)
            self.stream_file(filetype='image/jpeg',
                             content=read_image(directory="../data/images/", filename=filename))

    def do_GET_stream_video(self, which_cam, which_cam2, param):
        """
        create video stream
        """
        srv_logging.info("VIDEO " + which_cam + ": GET API request '" + self.path + "' - Session-ID: " + param["session_id"])

        if ":" in which_cam and "+" in which_cam:
            pip_cam, cam2_pos = which_cam.split(":")
            which_cam, which_cam2 = pip_cam.split("+")
        else:
            cam2_pos = 4

        if param["app_api"] == "pip":
            srv_logging.info("PIP: 1=" + which_cam + " / 2=" + which_cam2 + "/ pos=" + str(cam2_pos))

        stream_pip = False
        stream_active = True
        stream_id_int = datetime.now().timestamp()
        stream_id_ext = param["session_id"]

        stream_wait_while_error = 0.5
        stream_wait_while_recording = 1
        stream_wait_while_streaming = 0.01

        if '/pip/stream.mjpg' in self.path:
            stream_pip = True

        if "/detection/" in self.path:
            stream_type = "setting"
        else:
            stream_type = "camera"

        if '/lowres/' in self.path:
            stream_resolution = "lowres"
        else:
            stream_resolution = "hires"

        stream_id = stream_type + "_" + stream_resolution
        frame_id = None

        self.stream_video_header()
        while stream_active:

            if camera[which_cam].get_stream_kill(stream_id_ext, stream_id_int) or config.shut_down:
                stream_active = False

            if config.update["camera_" + which_cam]:
                camera[which_cam].camera_reconnect()

            if frame_id != camera[which_cam].get_stream_image_id() \
                    or camera[which_cam].if_error() or camera[which_cam].camera_stream_raw.if_error():

                frame_raw = camera[which_cam].get_stream(stream_id=stream_id_int,
                                                         stream_type=stream_type,
                                                         stream_resolution=stream_resolution,
                                                         system_info=True)
                frame_id = camera[which_cam].get_stream_image_id()

                if frame_raw is not None and len(frame_raw) > 0:
                    if stream_pip and which_cam2 != "" and which_cam2 in camera:
                        frame_raw_pip = camera[which_cam2].get_stream(stream_id=stream_id_int,
                                                                      stream_type=stream_type,
                                                                      stream_resolution="lowres",
                                                                      wait=False)

                        if frame_raw_pip is not None and len(frame_raw_pip) > 0:
                            frame_raw = camera[which_cam].image.image_in_image_raw(raw=frame_raw, raw2=frame_raw_pip,
                                                                                   position=int(cam2_pos))

                if stream_type == "camera" \
                        and not camera[which_cam].if_error() \
                        and not camera[which_cam].image.if_error() \
                        and not camera[which_cam].camera_streams[stream_id].if_error():

                    if camera[which_cam].video.recording:
                        srv_logging.debug("VIDEO RECORDING")
                        length = str(round(camera[which_cam].video.record_info()["length"]))
                        framerate = str(round(camera[which_cam].video.record_info()["framerate"]))
                        line1 = "Recording"
                        line2 = "(" + length + "s/" + framerate + "fps)"
                        camera[which_cam].set_system_info(True, line1, line2, (0, 0, 255))

                    elif camera[which_cam].video.processing:
                        srv_logging.debug("VIDEO PROCESSING")
                        length = str(round(camera[which_cam].video.record_info()["length"]))
                        framerate = str(round(camera[which_cam].video.record_info()["framerate"]))
                        line1 = "Processing"
                        line2 = "(" + length + "s/" + framerate + "fps)"
                        camera[which_cam].set_system_info(True, line1, line2, (0, 255, 255))

                    else:
                        camera[which_cam].set_system_info(False)

                if not stream_active:
                    self.stream_video_end()
                    srv_logging.info("Closed streaming client: " + stream_id_ext)

                elif frame_raw is None or len(frame_raw) == 0:
                    srv_logging.warning("Stream: Got an empty frame ...")

                else:
                    try:
                        frame = camera[which_cam].image.convert_from_raw(frame_raw)
                        self.stream_video_frame(frame, which_cam)
                    except Exception as error_msg:
                        stream_active = False
                        if "Errno 104" in str(error_msg) or "Errno 32" in str(error_msg):
                            srv_logging.debug('Removed streaming client %s: %s', self.client_address, str(error_msg))
                        else:
                            srv_logging.warning('Removed streaming client %s: %s', self.client_address, str(error_msg))

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

    @staticmethod
    def do_GET_stream_audio_header(self, sample_rate, bits_per_sample, channels):
        """.."""
        datasize = 2000 * 10 ** 6
        #datasize = samples * channels * bits_per_sample // 8
        o = bytes("RIFF", 'ascii')  # (4byte) Marks file as RIFF
        o += (datasize + 36).to_bytes(4, 'little')  # (4byte) File size in bytes excluding this and RIFF marker
        o += bytes("WAVE", 'ascii')  # (4byte) File type
        o += bytes("fmt ", 'ascii')  # (4byte) Format Chunk Marker
        o += (16).to_bytes(4, 'little')  # (4byte) Length of above format data
        o += (1).to_bytes(2, 'little')  # (2byte) Format type (1 - PCM)
        o += (channels).to_bytes(2, 'little')  # (2byte)
        o += (sample_rate).to_bytes(4, 'little')  # (4byte)
        o += (sample_rate * channels * bits_per_sample // 8).to_bytes(4, 'little')  # (4byte)
        o += (channels * bits_per_sample // 8).to_bytes(2, 'little')  # (2byte)
        o += (bits_per_sample).to_bytes(2, 'little')  # (2byte)
        o += bytes("data", 'ascii')  # (4byte) Data Chunk Marker
        o += (datasize).to_bytes(4, 'little')  # (4byte) Data size in bytes
        return o

    def do_GET_stream_audio(self, which_cam, param):
        """Audio streaming generator function."""
        global srv_audio_stream, srv_audio
        srv_logging.debug("AUDIO " + which_cam + ": GET API request '" + self.path + "' - Session-ID: " + param["session_id"])

        CHANNELS = 1
        RATE = 16000
        CHUNK = 1024
        DEVICE = 2
        BITS_PER_SAMPLE = 16

        micros = config.param["devices"]["microphones"]
        if which_cam in micros:
            micro = micros[which_cam]
            srv_logging.info("AUDIO device " + which_cam + " (" + str(micro["device_id"]) + "; " +
                             micro["device_name"] + "; " + str(micro["sample_rate"]) + ")")

            DEVICE = micro["device_id"]
            RATE = micro["sample_rate"]

            if srv_audio is None:
                srv_audio = pyaudio.PyAudio()

            info = srv_audio.get_host_api_info_by_index(0)
            num_devices = info.get('deviceCount')
            if DEVICE not in range(0, num_devices):
                srv_logging.error("... AUDIO device '"+str(DEVICE)+"' not available (range: 0, "+str(num_devices)+")")
                return
            device = srv_audio.get_device_info_by_host_api_device_index(0, DEVICE)
            if device.get('input') == 0:
                srv_logging.error("... AUDIO device '"+str(DEVICE)+"' is not a microphone / has no input (" +
                                  device.get('name') + ")")
                return
            if device.get('name') != micro["device_name"]:
                srv_logging.warning("... AUDIO device '" + str(DEVICE) + "' not the same as expected: " +
                                    device.get('name') + " != " + micro["device_name"])
        else:
            srv_logging.error("AUDIO device '" + which_cam + "' is not defined.")
            return

        try:
            if srv_audio_stream is None:
                srv_audio_stream = srv_audio.open(format=pyaudio.paInt16, channels=CHANNELS,
                                                  rate=RATE, input=True, input_device_index=DEVICE,
                                                  frames_per_buffer=CHUNK)
        except Exception as err:
            srv_logging.error("- Could not initialize audio stream (" + str(DEVICE) + "): " + str(err))
            srv_logging.error("- open: channels=" + str(CHANNELS) + ", rate=" + str(RATE) +
                              ", input_device_index=" + str(DEVICE) + ", frames_per_buffer=" + str(CHUNK))
            srv_logging.error("- device: " + str(device))
            return

        srv_logging.info("Start streaming ...")
        self.stream_audio_header()
        # frames = []

        wav_header = self.do_GET_stream_audio_header(RATE, BITS_PER_SAMPLE, CHANNELS)
        first_run = True
        streaming = True
        while streaming:
            if srv_audio_stream.is_stopped():
                srv_audio_stream.start_stream()
            if first_run:
                data = wav_header + srv_audio_stream.read(CHUNK)
                try:
                    first_run = False
                except Exception as err:
                    streaming = False
                    srv_logging.error("Error while grabbing audio from device: " + str(err))
            else:
                try:
                    data = srv_audio_stream.read(CHUNK)
                except Exception as err:
                    streaming = False
                    srv_logging.error("Error while grabbing audio from device: " + str(err))

            self.wfile.write(data)
        srv_audio_stream.stop_stream()

    def do_GET_stream_audio_tryout(self, which_cam, param):
        """Audio streaming generator function."""
        srv_logging.info("AUDIO " + which_cam + ": GET API request '" + self.path + "' - Session-ID: " + param["session_id"])

        if which_cam not in microphones:
            srv_logging.error("AUDIO device '" + which_cam + "' does not exist.")
            return

        if not microphones[which_cam].connected or microphones[which_cam].error:
            srv_logging.error("AUDIO device '" + which_cam + "' not connected or with error.")
            return

        srv_logging.info("Start streaming ...")
        self.stream_audio_header()
        first_run = True
        streaming = True
        count = 0
        last_count
        while streaming:
            if first_run:
                data = microphones[which_cam].get_first_chunk()
                first_run = True
                last_count = microphones[which_cam].count
            else:
                while microphones[which_cam].count != last_count and streaming:
                    pass
                last_count = microphones[which_cam].count
                data = microphones[which_cam].get_chunk()

            if data != "":
                self.wfile.write(data)
                count = 0
            elif count < 5:
                count += 1
            else:
                srv_logging.error("Got no data from microphone, stop streaming.")
                streaming = False

    def do_GET_files(self):
        """
        create API response
        """
        return


on_exception_setting()
sys.excepthook = on_exception

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
        srv_logging.setLevel(birdhouse_loglevel_module["server"])
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

    # start config
    config = BirdhouseConfig(param_init=birdhouse_preset, main_directory=os.path.dirname(os.path.abspath(__file__)))
    config.start()
    config.db_handler.directory_create("data")
    config.db_handler.directory_create("images")
    config.db_handler.directory_create("videos")
    config.db_handler.directory_create("videos_temp")
    time.sleep(0.5)

    # system information
    sys_info = ServerInformation()
    sys_info.start()

    # start sensors
    sensor = {}
    for sen in config.param["devices"]["sensors"]:
        settings = config.param["devices"]["sensors"][sen]
        sensor[sen] = BirdhouseSensor(sensor_id=sen, config=config)
        sensor[sen].start()

    # start cameras
    camera = {}
    for cam in config.param["devices"]["cameras"]:
        settings = config.param["devices"]["cameras"][cam]
        camera[cam] = BirdhouseCamera(camera_id=cam, config=config, sensor=sensor)
        camera[cam].start()

    # start microphones
    microphones = {}
#    for mic in config.param["devices"]["microphones"]:
#        microphones[mic] = BirdhouseMicrophone(device_id=mic, config=config)
#        microphones[mic].start()

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
    health_check = ServerHealthCheck()
    health_check.start()

    # Start Webserver
    try:
        address = ('0.0.0.0', int(birdhouse_env["port_api"]))
        server = StreamingServer(address, StreamingHandler)
        srv_logging.info("Starting WebServer on port " + str(birdhouse_env["port_api"]) + " ...")
        server.serve_forever()
        srv_logging.info("STOPPED SERVER.")

    except Exception as e:
        srv_logging.error("Could not start WebServer: " + str(e))

    # Stop all processes to stop
    finally:
        health_check.stop()
        sys_info.stop()
        config.stop()
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

        for thread in threading.enumerate():
            if thread.name != "MainThread":
                srv_logging.error("Could not stop: " + thread.name)
                thread.stop()
