#!/usr/bin/python3

import threading
import json
import signal
import sys
import psutil
import subprocess
import os
import socket

import socketserver
from http import server
from datetime import datetime
from urllib.parse import unquote

if len(sys.argv) == 0 or ("--help" not in sys.argv and "--shutdown" not in sys.argv):
    from modules.backup import BirdhouseArchive
    from modules.camera import BirdhouseCamera
    from modules.micro import BirdhouseMicrophone
    from modules.config import BirdhouseConfig
    from modules.presets import srv_logging
    from modules.views import BirdhouseViews
    from modules.sensors import BirdhouseSensor
    from modules.bh_class import BirdhouseClass

from modules.presets import *
from modules.bh_class import BirdhouseClass
from modules.bh_database import BirdhouseTEXT

api_start = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
api_description = {"name": "BirdhouseCAM", "version": "v1.0.8"}
app_framework = "v1.0.8"
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
    srv_logging.exception("Uncaught exception: " + str(value))
    srv_logging.exception("                    " + str(exc_type))
    srv_logging.exception("                    " + str(tb))


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


def read_html(file_directory, filename, content=""):
    """
    read html file, replace placeholders and return for stream via webserver
    """
    if filename.startswith("/"):
        filename = filename[1:len(filename)]
    if file_directory.startswith("/"):
        file_directory = file_directory[1:len(file_directory)]
    file = os.path.join(birdhouse_main_directories["server"], file_directory, filename)

    if not os.path.isfile(file):
        srv_logging.warning("File '" + str(file) + "' does not exist!")
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


def read_image(file_directory, filename):
    """
    read image file and return for stream via webserver
    """
    if filename.startswith("/"):
        filename = filename[1:len(filename)]
    if file_directory.startswith("/"):
        file_directory = file_directory[1:len(file_directory)]

    filename = filename.replace("app/", "")
    file = os.path.join(birdhouse_main_directories["server"], file_directory, filename)
    file = file.replace("backup/", "")

    if not os.path.isfile(file):
        srv_logging.warning("Image '" + str(file) + "' does not exist!")
        return ""

    with open(file, "rb") as image:
        f = image.read()
    return f


def decode_url_string(string):
    string = string.replace("%20", " ")
    string = string.replace("%22", "\"")
    string = string.replace("%5B", "[")
    string = string.replace("%5D", "]")
    string = string.replace("%7B", "{")
    string = string.replace("%7C", "|")
    string = string.replace("%7D", "}")
    return string


class ServerHealthCheck(threading.Thread, BirdhouseClass):

    def __init__(self, maintain=False):
        if not maintain:
            threading.Thread.__init__(self)
            BirdhouseClass.__init__(self, class_id="srv-health", config=config)
            self.thread_set_priority(5)

            self._initial = True
            self._interval_check = 60 * 5
            self._min_live_time = 65
            self._thread_info = {}
            self._health_status = None
            self._shutdown_signal_file = "/tmp/birdhouse-cam-shutdown"
            self._text_files = BirdhouseTEXT()
            self.set_shutdown(False)
            self.set_restart(False)
        else:
            self._shutdown_signal_file = "/tmp/birdhouse-cam-shutdown"
            self._running = False
            self._text_files = BirdhouseTEXT()

    def run(self):
        self.logging.info("Starting Server Health Check ...")
        count = 0
        last_update = time.time()
        while self._running:
            self.thread_wait()
            self.thread_control()

            if last_update + self._interval_check < time.time():
                self.logging.info("Health check ...")
                last_update = time.time()
                count += 1

                self._thread_info = {}
                for key in self.config.thread_status:
                    if self.config.thread_status[key]["thread"]:
                        self._thread_info[key] = time.time() - self.config.thread_status[key]["status"]["health_signal"]

                if self._initial:
                    self._initial = False
                    self.logging.info("... checking the following threads: " + str(self._thread_info.keys()))

                problem = []
                for key in self._thread_info:
                    if self._thread_info[key] > self._min_live_time:
                        problem.append(key + " (" + str(round(self._thread_info[key], 1)) + "s)")

                if len(problem) > 0:
                    self.logging.warning(
                        "... not all threads are running as expected: ")
                    self.logging.warning("  -> " + ", ".join(problem))
                    self._health_status = "NOT RUNNING: " + ", ".join(problem)
                else:
                    self.logging.info("... OK.")
                    self._health_status = "OK"

            if self.check_shutdown():
                self.logging.info("SHUTDOWN SIGNAL send from outside.")
                self.set_shutdown(False)
                config.force_shutdown()

            if self.check_restart():
                self.logging.info("RESTART SIGNAL detected - shutdown and set START signal (requires check via crontab)")
                self.set_start()
                config.force_shutdown()

            if count == 4:
                count = 0
                self.logging.info("Live sign health check!")

        self.logging.info("Stopped Server Health Check.")

    def status(self):
        return self._health_status

    def check_restart(self):
        """
        check if external shutdown signal has been set
        """
        if os.path.exists(self._shutdown_signal_file):
            content = self._text_files.read(self._shutdown_signal_file)
            if "REBOOT" in content:
                return True
        return False

    def set_restart(self, restart=True):
        """
        set external shutdown signal ...
        """
        if restart:
            self._text_files.write(self._shutdown_signal_file, "REBOOT")
        else:
            self._text_files.write(self._shutdown_signal_file, "")

    def check_start(self):
        """
        check if external shutdown signal has been set
        """
        if os.path.exists(self._shutdown_signal_file):
            content = self._text_files.read(self._shutdown_signal_file)
            if "START" in content:
                print("START signal set ... starting birdhouse server.")
                return True
        print("Check: no START signal present (file="+str(os.path.exists(self._shutdown_signal_file))+").")
        return False

    def set_start(self, restart=True):
        """
        set external shutdown signal ...
        """
        if restart:
            self._text_files.write(self._shutdown_signal_file, "START")
        else:
            self._text_files.write(self._shutdown_signal_file, "")

    def check_shutdown(self):
        """
        check if external shutdown signal has been set
        """
        if os.path.exists(self._shutdown_signal_file):
            content = self._text_files.read(self._shutdown_signal_file)
            if "SHUTDOWN" in content:
                return True
        return False

    def set_shutdown(self, shutdown=True):
        """
        set external shutdown signal ...
        """
        if shutdown:
            self._text_files.write(self._shutdown_signal_file, "SHUTDOWN")
        else:
            self._text_files.write(self._shutdown_signal_file, "")


class ServerInformation(threading.Thread, BirdhouseClass):

    def __init__(self, initial_camera_scan):
        threading.Thread.__init__(self)
        BirdhouseClass.__init__(self, class_id="srv-info", config=config)
        self.thread_set_priority(4)

        self._system_status = {}
        self._device_status = {
            "cameras": {},
            "sensors": {},
            "microphones": {},
            "available": {}
        }
        self._srv_info_time = 0
        self.initial_camera_scan = initial_camera_scan

        self.main_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
        self.microphones = None

    def run(self):
        """
        Running thread to continuously update server information in the background.
        """
        self.logging.info("Starting Server Information ...")
        while self._running:
            start_time = time.time()
            self.read_memory_usage()
            self.read_device_status()
            self.read_available_devices()

            self._srv_info_time = round(time.time() - start_time, 2)

            self.thread_control()
            self.thread_wait()

        self.logging.info("Stopped Server Information.")

    def read_memory_usage(self):
        """
        Get data for current memory and HDD usage, to be requested via .get().
        """
        system = {}
        try:
            # cpu information
            system["cpu_usage"] = psutil.cpu_percent(interval=1, percpu=False)
            system["cpu_usage_detail"] = psutil.cpu_percent(interval=1, percpu=True)
            system["mem_total"] = psutil.virtual_memory().total / 1024 / 1024
            system["mem_used"] = psutil.virtual_memory().used / 1024 / 1024

            # diskusage
            hdd = psutil.disk_usage("/")
            system["hdd_used"] = hdd.used / 1024 / 1024 / 1024
            system["hdd_total"] = hdd.total / 1024 / 1024 / 1024

        except Exception as err:
            system = {
                "cpu_usage": -1,
                "cpu_usage_detail": -1,
                "mem_total": -1,
                "mem_used": -1,
                "hdd_used": -1,
                "hdd_total": -1
            }

        system["system_info_interval"] = self._srv_info_time

        # Initialize the result.
        result = -1
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

        try:
            cmd_data = ["du", "-hs", os.path.join(self.main_dir, "data")]
            temp_data = str(subprocess.check_output(cmd_data))
            temp_data = temp_data.replace("b'", "")
            temp_data = temp_data.split("\\t")[0]
            if "k" in temp_data:
                system["hdd_data"] = float(temp_data.replace("k", "")) / 1024 / 1024
            elif "M" in temp_data:
                system["hdd_data"] = float(temp_data.replace("M", "")) / 1024
            elif "G" in temp_data:
                system["hdd_data"] = float(temp_data.replace("G", ""))
        except Exception as e:
            system["hdd_data"] = -1
            self.logging.warning("Was not able to get size of data dir: " + (str(cmd_data)) + " - " + str(e))

        self._system_status = system.copy()

    def read_available_devices(self):
        """
        Identify which video and audio devices are available on the system, to be requested via .get_device_status().
        """
        global srv_audio
        system = {}

        process = subprocess.Popen(["v4l2-ctl --list-devices"], stdout=subprocess.PIPE, shell=True)
        output = process.communicate()[0]
        output = output.decode()
        output_2 = output.split("\n")

        last_key = "none"
        if birdhouse_env["rpi_active"]:
            output_2.append("PiCamera:")
            output_2.append("/dev/picam")

        system["video_devices"] = {}
        system["video_devices_short"] = {}
        system["video_devices_complete"] = self.initial_camera_scan["video_devices_complete"]
        for value in output_2:
            if ":" in value:
                system["video_devices"][value] = []
                last_key = value
            elif value != "":
                value = value.replace("\t", "")
                check_text = "NEW"
                if value in system["video_devices_complete"]:
                    check = system["video_devices_complete"][value]
                    if check["image"]:
                        check_text = "OK"
                    else:
                        check_text = "ERROR"
                system["video_devices"][last_key].append(value)
                info = last_key.split(":")
                system["video_devices_short"][value] = check_text + ": " + value + " (" + info[0] + ")"

        system["audio_devices"] = {}
        if microphones != {}:
            first_mic = list(microphones.keys())[0]
            info = microphones[first_mic].get_device_information()
            srv_logging.debug("... mic-info: " + str(info))

            if 'deviceCount' in info:
                num_devices = info['deviceCount']
                for i in range(0, num_devices):
                    dev_info = microphones["mic1"].get_device_information(i)
                    if (dev_info.get('maxInputChannels')) > 0:
                        name = dev_info.get('name')
                        info = dev_info
                        srv_logging.debug("... mic-info: " + str(info))
                        system["audio_devices"][name] = {
                            "id": i,
                            "input": info.get("maxInputChannels"),
                            "output": info.get("maxOutputChannels"),
                            "sample_rate": info.get("defaultSampleRate")
                        }

        srv_logging.debug("... mic-info: " + str(system["audio_devices"]))
        self._device_status["available"] = system

    def read_device_status(self):
        """
        Get device data ever x seconds for a faster API response
        """
        global microphones, camera, sensor
        # get microphone data and create streaming information
        for key in microphones:
            self._device_status["microphones"][key] = microphones[key].get_device_status()

        # get camera data and create streaming information
        for key in camera:
            self._device_status["cameras"][key] = camera[key].get_camera_status()

        # get sensor data
        for key in sensor:
            self._device_status["sensors"][key] = sensor[key].get_status()

    def get(self):
        """
        Get server data which are updated continuously in the background.
        """
        return self._system_status

    def get_device_status(self):
        """
        Get device data which are updated continuously in the background.
        """
        return self._device_status


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class StreamingServerIPv6(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True
    address_family = socket.AF_INET6

    def server_bind(self):
        # Override server_bind to allow both IPv4 and IPv6 connections
        # Bind to the wildcard address ("::") to enable dual-stack support
        self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        super().server_bind()


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
        #self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Methods", "*")
        self.end_headers()

    def stream_audio_header(self, size):
        """
        send header for video stream
        see https://stackoverflow.com/questions/13275409/playing-a-wav-file-on-ios-safari
        """

        self.send_response(200)

        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        #self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Methods", "*")

        self.send_header("Connection", "Keep-Alive")
        # self.send_header('Age', '0')
        # self.send_header('Cache-Control', 'no-cache, private')
        # self.send_header('Pragma', 'no-cache')

        self.send_header('Content-Range', 'bytes 0-'+str(size)+'/'+str(size))
        # self.send_header('Content-Disposition', 'attachment;filename="audio.WAV"')
        self.send_header('Content-Type', 'audio/x-wav')
        # self.send_header('Content-Type', 'audio/x-wav;codec=PCM')
        self.send_header('Content-Length', str(size))
        self.send_header('Content-Transfer-Encoding', 'binary')
        # self.send_header('Transfer-Encoding', 'binary')
        self.send_header('Accept-Ranges', 'bytes')

        self.end_headers()

    def stream_video_frame(self, frame):
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
            srv_logging.debug("CHECK if " + param["session_id"] + " == " +  admin_pwd + " !!!!!!!! " +
                              str(param["session_id"] == admin_pwd))
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

        elif self.path.startswith("/api/reload"):
            param["command"] = "reload"

        elif "/edit-presets/" in self.path:
            param["session_id"] = elements[2]
            param["command"] = "edit-presets"
            param["which_cam"] = ""
            if len(elements) > 4:
                param["parameter"] = elements[4]
            if len(elements) > 5:
                param["which_cam"] = elements[5]

        elif self.path.startswith("/api"):
            param_no_cam = ["check-pwd", "status", "list", "kill-stream", "force-restart", "force-backup",
                            "last-answer", "favorit", "recycle", "update-views", "update-views-complete",
                            "archive-object-detection", "archive-remove-day", "archive-remove-list",
                            "OBJECTS", "FAVORITES", "bird-names"]

            param["session_id"] = elements[2]
            param["command"] = elements[3]

            # start with hypothesis that the last param is the active cam
            last_is_cam = True
            complete_cam = elements[len(elements) - 1]
            if "+" in complete_cam:
                param["which_cam"] = complete_cam.split("+")[0]
                param["other_cam"] = complete_cam.split("+")[1]
            else:
                param["which_cam"] = complete_cam

            # extra rule for TODAY
            if param["command"] == "TODAY" and len(elements) > 5:
                param["date"] = elements[4]
                param["which_cam"] = elements[5]
                last_is_cam = False

            elif param["command"] not in param_no_cam:
                if param["which_cam"] not in views.camera:
                    srv_logging.warning("Unknown camera requested: " + param["which_cam"] + " (" + self.path + ")")
                    param["which_cam"] = "cam1"
                    last_is_cam = False

            elif "command" in param and param["command"] in param_no_cam:
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
        global camera

        content_length = int(self.headers['Content-Length'])
        if content_length >= 2:
            post_data = self.rfile.read(content_length)
            body_data = json.loads(post_data.decode('utf-8'))
            srv_logging.debug("do_POST body data: " + str(body_data))
        else:
            body_data = None

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

        public_commands = ["check-pwd", "kill-stream"]
        if not self.admin_allowed() and param["command"] not in public_commands:
            response["error"] = "Administration not allowed!"
            srv_logging.error(response["error"] + " - command=" + param["command"] + "; admin=" +
                              str(self.admin_allowed()) + "; param=" + str(param))
            self.stream_file(filetype='application/json', content=json.dumps(response).encode(encoding='utf_8'),
                             no_cache=True)
            return

        # admin commands
        if param["command"] == "favorit":
            srv_logging.info(param["command"] + ": " + str(param))
            response = config.queue.set_status_favorite(param)
        elif param["command"] == "recycle":
            srv_logging.info(param["command"] + ": " + str(param))
            response = config.queue.set_status_recycle(param)
        elif param["command"] == "recycle-threshold":
            # http://localhost:8007/api/1682709071876/recycle-threshold/backup/20230421/95/cam1/
            srv_logging.info("RECYCLE THRESHOLD")
            response = config.queue.set_status_recycle_threshold(param, which_cam)
        elif param["command"] == "recycle-object-detection":
            srv_logging.info("RECYCLE OBJECT")
            response = config.queue.set_status_recycle_object(param, which_cam)
        elif param["command"] == "recycle-range":
            srv_logging.info(param["command"] + ": " + str(param))
            response = config.queue.set_status_recycle_range(param)
        elif param["command"] == "create-short-video":
            srv_logging.info(param["command"] + ": " + str(param))
            response = camera[which_cam].video.create_video_trimmed_queue(param)
        elif param["command"] == "recreate-image-config":
            srv_logging.info(param["command"] + ": " + str(param))
            response = backup.create_image_config_api(param)
        elif param["command"] == "create-day-video":
            srv_logging.info(param["command"] + ": " + str(param))
            response = camera[which_cam].video.create_video_day_queue(param)
        elif param["command"] == "remove":
            srv_logging.info(param["command"] + ": " + str(param))
            response = backup.delete_marked_files_api(param)
        elif param["command"] == "archive-object-detection":
            parameters = param["parameter"]
            cam_id = parameters[0]
            date = parameters[1]
            threshold = -1
            if len(parameters) > 2:
                threshold = parameters[2]
            if "_" in date:
                date_list = date.split("_")
                response = camera[cam_id].object.analyze_archive_several_days_start(date_list, threshold)
            else:
                response = camera[cam_id].object.analyze_archive_day_start(date, threshold)
        elif param["command"] == "archive-remove-day":
            srv_logging.info(param["command"] + ": " + str(param))
            response = backup.delete_archived_day(param)
        elif param["command"] == "archive-download-day":
            srv_logging.info(param["command"] + ": " + str(param))
            response = backup.download_files(param)
        elif param["command"] == "archive-download-list":
            srv_logging.info(param["command"] + ": " + str(param))
            response = backup.download_files(param, body_data)
        elif param["command"] == "reconnect-camera":
            srv_logging.info(param["command"] + ": " + str(param))
            response = camera[which_cam].reconnect()
        elif param["command"] == "camera-settings":
            srv_logging.info(param["command"] + ": " + str(param))
            response = camera[which_cam].get_camera_settings(param)
        elif param["command"] == "start-recording":
            audio_filename = ""
            which_mic = ""
            for key in camera:
                config.set_device_signal(key, "recording", True)
            if "record_micro" in camera[which_cam].param:
                which_mic = camera[which_cam].param["record_micro"]
            else:
                srv_logging.warning("Error in configuration file, 'record_micro' is missing.")
            if which_mic != "" and which_mic in microphones:
                if microphones[which_mic].param["active"] and microphones[which_mic].connected:
                    response = microphones[which_mic].record_start("recording_"+which_cam+"_"+which_mic+".wav")
                    audio_filename = response["filename"]
                else:
                    srv_logging.info("Recording without audio (active=" + str(microphones[which_mic].param["active"]) +
                                     "; connected=" + str(microphones[which_mic].connected) + ")")
                    which_mic = "N/A"
            response = camera[which_cam].video.record_start(which_mic, audio_filename)
        elif param["command"] == "stop-recording":
            for key in camera:
                config.set_device_signal(key, "recording", False)
            which_mic = camera[which_cam].param["record_micro"]
            if which_mic != "" and which_mic in microphones:
                if microphones[which_mic].param["active"] and microphones[which_mic].connected:
                    microphones[which_mic].record_stop()
            response = camera[which_cam].video.record_stop()
        elif param["command"] == "start-recording-audio":
            which_mic = self.path.split("/")[-2]
            srv_logging.info("start-recording-audio: " + which_mic)
            response = microphones[which_mic].record_start("test.wav")
        elif param["command"] == "stop-recording-audio":
            which_mic = self.path.split("/")[-2]
            srv_logging.info("stop-recording-audio: " + which_mic)
            response = microphones[which_mic].record_stop()
        elif param["command"] == "edit-video-title":
            srv_logging.info("edit-video-title: " + str(param["parameter"]))
            entries = config.db_handler.read("videos")
            key = param["parameter"][0]
            if key in entries:
                entry = entries[key]
                if param["parameter"][1] == "EMPTY_TITLE_FIELD":
                    entry["title"] = ""
                else:
                    entry["title"] = decode_url_string(param["parameter"][1])
                config.queue.entry_edit("videos", "", key, entry)
            else:
                srv_logging.error("edit-video-title: key not found ("+key+","+self.path+")")
        elif param["command"] == "clean-data-today":
            config.db_handler.clean_all_data("images")
            config.db_handler.clean_all_data("weather")
            config.db_handler.clean_all_data("sensor")
            response = {"cleanup": "done"}
        elif param["command"] == "update-views":
            views.archive.list_update(force=True)
            views.favorite.list_update(force=True)
            views.object.list_update(force=True)
            response = {"update_views": "started"}
        elif param["command"] == "update-views-complete":
            views.archive.list_update(force=True, complete=True)
            views.favorite.list_update(force=True, complete=True)
            views.object.list_update(force=True, complete=True)
            response = {"update-views-complete": "started"}
        elif param["command"] == "force-backup":
            backup.start_backup()
            response = {"backup": "started"}
        elif param["command"] == "force-restart":
            srv_logging.info("-------------------------------------------")
            srv_logging.info("FORCED SHUT-DOWN OF BIRDHOUSE SERVER .... !")
            srv_logging.info("-------------------------------------------")
            config.force_shutdown()
            health_check.set_start()
            response = {"shutdown": "started"}
        elif param["command"] == "check-timeout":
            time.sleep(30)
            response = {"check": "timeout"}
        elif param["command"] == "edit-presets":
            edit_param = param["parameter"].split("###")
            data = {}
            for entry in edit_param:
                if "==" in entry:
                    key, value = entry.split("==")
                    data[key] = unquote(value)
                    data[key] = decode_url_string(data[key])
            srv_logging.info(str(data))
            config.main_config_edit("main", data)
            for key in camera_list:
                camera[key].config_update = True
        elif param["command"] == "set-temp-threshold":
            srv_logging.info("Set temporary threshold to camera '"+which_cam+"': " + str(param["parameter"]))
            if which_cam in camera:
                camera[which_cam].record_temp_threshold = param["parameter"]
        elif param["command"] == "kill-stream":
            srv_logging.debug(self.path)
            srv_logging.debug(str(param["parameter"]))
            stream_id = param["parameter"][0]
            if "&" in stream_id:
                stream_id_kill = stream_id.split("&")[-1]
                which_cam = stream_id.split("&")[0]
                camera[which_cam].set_stream_kill(stream_id_kill)
                response = {
                    "kill-stream": which_cam,
                    "kill-stream-id": stream_id
                }
        elif param["command"] == "check-pwd":
            admin_pwd = birdhouse_env["admin_password"]
            if admin_pwd == param["parameter"][0]:
                response["check-pwd"] = True
            else:
                response["check-pwd"] = False
        elif param["command"] == "--template-to-implement-new-POST-command--":
            msg = "API CALL '" + param["command"] + "' not implemented yet (" + str(self.path) + ")"
            srv_logging.info(msg)
            srv_logging.info(str(param))
            response = {"info": msg}
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

        if config.thread_ctrl["shutdown"]:
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
            self.do_GET_stream_audio(self.path)
        elif self.path.endswith('favicon.ico'):
            self.stream_file(filetype='image/ico', content=read_image(file_directory=birdhouse_directories["html"], filename=self.path))
        elif self.path.startswith("/app/index.html"):
            self.stream_file(filetype=file_types[".html"], content=read_html(file_directory=birdhouse_directories["html"], filename="index.html"))
        elif file_ending in file_types:
            if "/images/" in self.path or "/videos/" in self.path or "/archive/" in self.path:
                file_path = birdhouse_directories["data"]
            else:
                file_path = birdhouse_directories["html"]

            if "text" in file_types[file_ending]:
                self.stream_file(filetype=file_types[file_ending],
                                 content=read_html(file_directory=file_path, filename=self.path))
            elif "application" in file_types[file_ending]:
                self.stream_file(filetype=file_types[file_ending],
                                 content=read_html(file_directory=file_path, filename=self.path))
            else:
                self.stream_file(filetype=file_types[file_ending],
                                 content=read_image(file_directory=file_path, filename=self.path))
        else:
            self.error_404()

    def do_GET_api(self):
        """
        create API response
        """
        request_start = time.time()
        request_times = {}
        status = "Success"
        version = {}

        param = self.path_split()
        which_cam = param["which_cam"]
        command = param["command"]

        config.user_activity("set", command)

        srv_logging.debug("GET API request with '" + self.path + "'.")
        api_response = {
            "API": api_description,
            "STATUS": {
                "admin_allowed": self.admin_allowed(),
                "api-call": status,
                "check-version": version,
                "current_time": config.local_time().strftime('%d.%m.%Y %H:%M:%S'),
                "start_time": api_start,
                "database": {},
                "devices": {
                    "cameras": {},
                    "sensors": {},
                    "weather": {},
                    "microphones": {}
                },
                "reload": False,
                "server": {
                    "view_archive_loading": views.archive.loading,
                    "view_favorite_loading": views.favorite.loading,
                    "view_object_loading": views.object.loading,
                    "view_archive_progress": views.tools.get_progress("archive"),
                    "view_favorite_progress": views.tools.get_progress("favorite"),
                    "view_object_progress": views.tools.get_progress("object"),
                    "backup_process_running": backup.backup_running,
                    "queue_waiting_time": config.queue.queue_wait,
                    "health_check": health_check.status(),
                    "downloads": backup.download_files_waiting(param),
                    "initial_setup": config.param["server"]["initial_setup"],
                    "last_answer": ""
                },
                "system": {},
                "object_detection": {
                    "active": birdhouse_status["object_detection"],
                    "processing": config.object_detection_processing,
                    "progress": config.object_detection_progress,
                    "waiting": config.object_detection_waiting,
                    "waiting_dates": config.object_detection_waiting_keys,
                    "models_available": detection_models,
                    "models_loaded": {},
                    "models_loaded_status": {},
                },
                "view": {
                    "selected": which_cam,
                    "active_cam": which_cam,
                    "active_date": "",
                    "active_page": command
                }
            },
            "SETTINGS": {
                "backup": {},
                "devices": {
                    "cameras": {},
                    "sensors": {},
                    "weather": {},
                    "microphones": {}
                },
                "info": {},
                "localization": {},
                "server": {},
                "title": "",
                "views": {},
                "weather": {}
            },
            "WEATHER": {},
            "DATA": {}
        }
        srv_logging.debug(str(param))

        # prepare API response

        # prepare DATA section
        api_data = {
            "active": {
                "active_cam": which_cam,
                "active_path": self.path,
                "active_page": command,
                "active_date": ""
            },
            "data": {},
            "view": {}
        }
        if command == "TODAY" and len(param["parameter"]) > 0:
            api_data["active"]["active_date"] = param["parameter"][0]
            api_response["STATUS"]["view"]["active_date"] = param["parameter"][0]

        request_times["0_initial"] = round(time.time() - request_start, 3)

        cmd_views = ["INDEX", "FAVORITES", "TODAY", "TODAY_COMPLETE", "ARCHIVE", "VIDEOS", "VIDEO_DETAIL",
                     "DEVICES", "OBJECTS", "bird-names"]
        cmd_status = ["status", "list", "last-answer"]
        cmd_info = ["camera-param", "version", "reload"]

        # execute API commands
        if command == "INDEX":
            content = views.index_view(param=param)
        elif command == "FAVORITES":
            content = views.favorite.list(param=param)
        elif command == "TODAY":
            content = views.list(param=param)
        elif command == "TODAY_COMPLETE":
            content = views.complete_list_today(param=param)
        elif command == "ARCHIVE":
            content = views.archive.list(param=param)
        elif command == "OBJECTS":
            content = views.object.list(param=param)
        elif command == "VIDEOS":
            content = views.video_list(param=param)
        elif command == "VIDEO_DETAIL":
            content = views.detail_view_video(param=param)
        elif command == "DEVICES":
            content = views.camera_list(param=param)
            api_response["STATUS"]["system"] = sys_info.get()
            api_response["STATUS"]["system"]["hdd_archive"] = views.archive.dir_size / 1024
        elif command == "status" or command == "list":
            content = {"last_answer": ""}
            api_response["STATUS"]["database"] = config.get_db_status()
            api_response["STATUS"]["system"] = sys_info.get()
            api_response["STATUS"]["system"]["hdd_archive"] = views.archive.dir_size / 1024
        elif command == "last-answer":
            content = {"last_answer": ""}
            if len(config.async_answers) > 0:
                content["last_answer"] = config.async_answers.pop()
                content["background_process"] = config.async_running
        elif command == "reload":
            content = {}
            api_response["STATUS"]["reload"] = True
        elif command == "bird-names":
            content = {"birds": config.birds}
        elif command == "version":
            content = {}
            version["Code"] = "800"
            version["Msg"] = "Version OK."
            if app_framework != param["session_id"]:
                version["Code"] = "802"
                version["Msg"] = "Update required."
            api_response["STATUS"]["check-version"] = version
        elif command == "camera-param":
            content = {}
            api_data["data"] = camera[which_cam].get_camera_status("properties")
        else:
            content = {}
            status = "Error: command not found."

        request_times["1_api-commands"] = round(time.time() - request_start, 3)

        # collect data for STATUS section
        weather_status = {}
        if command in cmd_status:
            if config.weather is not None:
                api_response["WEATHER"] = config.weather.get_weather_info("all")
                weather_status = config.weather.get_weather_info("status")

            param_to_publish = ["last_answer", "background_process"]
            for key in param_to_publish:
                if key in content:
                    api_response["STATUS"]["server"][key] = content[key]

            for key in camera:
                api_response["STATUS"]["object_detection"]["models_loaded_status"][key] = camera[key].object.detect_loaded
                api_response["STATUS"]["object_detection"]["models_loaded"][key] = camera[key].object.detect_settings["model"]

            # collect data for new DATA section
            param_to_publish = ["backup", "localization", "title", "views", "info", "weather"]
            for key in param_to_publish:
                if key in config.param:
                    api_response["SETTINGS"][key] = config.param[key]

            # ensure localization data are available
            if "localization" in api_response["SETTINGS"]:
                if "language" not in api_response["SETTINGS"]["localization"]:
                    api_response["SETTINGS"]["localization"]["language"] = "EN"
            else:
                api_response["SETTINGS"]["localization"] = birdhouse_preset["localization"]

            request_times["1_status-commands"] = round(time.time() - request_start, 3)

        # collect data for several lists views TODAY, ARCHIVE, TODAY_COMPLETE, ...
        if command in cmd_views:
            param_to_publish = ["entries", "entries_delete", "entries_yesterday", "groups", "archive_exists", "info",
                                "chart_data", "weather_data", "days_available", "day_back", "day_forward", "birds"]
            for key in param_to_publish:
                if key in content:
                    api_data["data"][key] = content[key]

            param_to_publish = ["view", "view_count", "links", "subtitle", "max_image_size", "label"]
            for key in param_to_publish:
                if key in content:
                    api_data["view"][key] = content[key]

            request_times["2_view-commands"] = round(time.time() - request_start, 3)

        # collect data for STATUS and SETTINGS sections (to be clarified -> goal: only for status request)
        if command not in cmd_info:
            # collect data for "DATA" section  ??????????????????????ßß
            param_to_publish = ["title", "backup", "weather", "views", "info"]
            for key in param_to_publish:
                if key in content:
                    content[key] = config.param[key]
            request_times["5_config"] = round(time.time() - request_start, 3)

            # get device data
            api_response["STATUS"]["devices"] = sys_info.get_device_status()
            request_times["6_devices_status"] = round(time.time() - request_start, 3)

            # get microphone data and create streaming information
            micro_data = config.param["devices"]["microphones"].copy()
            for key in micro_data:
                micro_data[key]["stream_server"] = birdhouse_env["server_audio"]
                micro_data[key]["stream_server"] += ":" + str(micro_data[key]["port"])
            request_times["7_status_micro"] = round(time.time() - request_start, 3)

            # get camera data and create streaming information
            camera_data = config.param["devices"]["cameras"].copy()
            for key in camera_data:
                if key in camera:
                    camera_data[key]["video"]["stream"] = "/stream.mjpg?" + key
                    camera_data[key]["video"]["stream_pip"] = "/pip/stream.mjpg?" + key + \
                                                              "+{2nd-camera-key}:{2nd-camera-pos}"
                    camera_data[key]["video"]["stream_lowres"] = "/lowres/stream.mjpg?" + key
                    camera_data[key]["video"]["stream_detect"] = "/detection/stream.mjpg?" + key
                    camera_data[key]["video"]["stream_object"] = "/object/stream.mjpg?" + key
                    camera_data[key]["device"] = "camera"
                    camera_data[key]["image"]["resolution_max"] = camera[key].max_resolution
                    camera_data[key]["image"]["current_streams"] = camera[key].get_stream_count()
                    camera_data[key]["image"]["current_streams_detail"] = camera[key].image_streams
                    if config.param["server"]["ip4_stream_video"] == "":
                        camera_data[key]["video"]["stream_server"] = config.param["server"]["ip4_address"]
                    else:
                        camera_data[key]["video"]["stream_server"] = config.param["server"]["ip4_stream_video"]
                    camera_data[key]["video"]["stream_server"] += ":" + str(birdhouse_env["port_video"])
            request_times["8_status_camera"] = round(time.time() - request_start, 3)

            # get sensor data
            sensor_data = config.param["devices"]["sensors"].copy()
            for key in sensor_data:
                sensor_data[key]["values"] = {}
                if key in sensor and sensor[key].if_running():
                    sensor_data[key]["values"] = sensor[key].get_values()
            request_times["9_status_sensor"] = round(time.time() - request_start, 3)

            api_response["SETTINGS"]["devices"] = {
                "cameras": camera_data,
                "sensors": sensor_data,
                "microphones": micro_data,
                "weather": weather_status
            }

        api_response["DATA"] = api_data

        if command in cmd_status and command != "last-answer":
            server_config = {
                "port": birdhouse_env["port_http"],
                "port_video": birdhouse_env["port_video"],
                "port_audio": birdhouse_env["port_audio"],
                "server_audio": birdhouse_env["port_audio"],
                "database_type": birdhouse_env["database_type"],
                "database_port": birdhouse_env["couchdb_port"],
                "database_server": birdhouse_env["couchdb_server"],
                "ip4_admin_deny": birdhouse_env["admin_ip4_deny"],
                "ip4_admin_allow": birdhouse_env["admin_ip4_allow"],
                "admin_login": birdhouse_env["admin_login"],
                "rpi_active": birdhouse_env["rpi_active"],
                "detection_active": birdhouse_env["detection_active"]
            }
            api_response["SETTINGS"]["server"] = server_config

        if command not in cmd_status and command not in cmd_info:
            del api_response["WEATHER"]
            del api_response["STATUS"]["system"]
            del api_response["STATUS"]["database"]
            del api_response["STATUS"]["check-version"]

        if command == "last-answer":
            del api_response["STATUS"]["devices"]
            del api_response["DATA"]
            del api_response["SETTINGS"]
            del api_response["WEATHER"]

        api_response["API"]["request_details"] = request_times
        api_response["API"]["request_time"] = round(time.time() - request_start, 3)

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
                             content=read_image(file_directory="../data/images/", filename=filename_diff))

        # extract and show single image (creates images with a longer delay ?)
        elif '/image.jpg' in self.path:
            filename = "_image_temp_" + which_cam + ".jpg"
            img_path = os.path.join(config.db_handler.directory("images"), filename)
            camera[which_cam].write_image(img_path, camera[which_cam].get_stream(stream_id="file",
                                                                                 stream_type="camera",
                                                                                 stream_resolution="hires"))
            time.sleep(2)
            self.stream_file(filetype='image/jpeg',
                             content=read_image(file_directory="../data/images/", filename=filename))

    def do_GET_stream_video(self, which_cam, which_cam2, param):
        """
        create video stream
        """
        srv_logging.debug("VIDEO " + which_cam + ": GET API request '" + self.path + "' - Session-ID: " + param["session_id"])

        if ":" in which_cam and "+" in which_cam:
            pip_cam, cam2_pos = which_cam.split(":")
            which_cam, which_cam2 = pip_cam.split("+")
        else:
            cam2_pos = 4

        if param["app_api"] == "pip":
            srv_logging.info("PIP: 1=" + which_cam + " / 2=" + which_cam2 + "/ pos=" + str(cam2_pos))

        stream_pip = False
        stream_active = True
        stream_object = ("/object/" in self.path)
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

            if camera[which_cam].get_stream_kill(stream_id_ext, stream_id_int) or config.thread_ctrl["shutdown"]:
                stream_active = False

            if config.update["camera_" + which_cam]:
                camera[which_cam].reconnect()

            if frame_id != camera[which_cam].get_stream_image_id() \
                    or camera[which_cam].if_error() or camera[which_cam].camera_stream_raw.if_error():

                if stream_object:
                    frame_raw = camera[which_cam].get_stream_object_detection(stream_id=stream_id_int,
                                                                              stream_type=stream_type,
                                                                              stream_resolution=stream_resolution,
                                                                              system_info=True)
                else:
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
                                                                      system_info=False,
                                                                      wait=False)

                        if frame_raw_pip is not None and len(frame_raw_pip) > 0:
                            frame_raw = camera[which_cam].image.image_in_image_raw(raw=frame_raw, raw2=frame_raw_pip,
                                                                                   position=int(cam2_pos), distance=30)

                if stream_type == "camera" \
                        and not camera[which_cam].if_error() \
                        and not camera[which_cam].image.if_error() \
                        and not camera[which_cam].camera_streams[stream_id].if_error():

                    if camera[which_cam].video.recording:
                        srv_logging.debug("VIDEO RECORDING")
                        record_info = camera[which_cam].video.record_info()
                        length = str(round(record_info["length"], 1)) + "s"
                        framerate = str(round(record_info["framerate"], 1)) + "fps"
                        time_s = int(record_info["length"]) % 60
                        time_m = round((int(record_info["length"]) - time_s) / 60)
                        time_l = str(time_m).zfill(2) + ":" + str(time_s).zfill(2)
                        line1 = "Recording"
                        line2 = time_l + " / " + framerate + " (max " + str(camera[which_cam].video.max_length) + "s)"
                        camera[which_cam].set_system_info(True, line1, line2, (0, 0, 100))

                    elif camera[which_cam].video.processing:
                        srv_logging.debug("VIDEO PROCESSING")
                        record_info = camera[which_cam].video.record_info()
                        length = str(round(record_info["length"], 1)) + "s"
                        framerate = str(round(record_info["framerate"], 1)) + "fps"
                        progress = str(round(float(record_info["percent"]), 1)) + "%"
                        time_s = int(record_info["elapsed"]) % 60
                        time_m = round((int(record_info["elapsed"]) - time_s) / 60)
                        time_e = str(time_m).zfill(2) + ":" + str(time_s).zfill(2)
                        line1 = "Processing"
                        line2 = time_e + " / " + progress
                        camera[which_cam].set_system_info(True, line1, line2, (0, 255, 255))

                    else:
                        camera[which_cam].set_system_info(False)

                if not stream_active:
                    self.stream_video_end()
                    srv_logging.info("Closed streaming client: " + stream_id_ext)

                elif frame_raw is None or len(frame_raw) == 0:
                    srv_logging.warning("Stream: Got an empty frame for '" + which_cam + "' ...")

                else:
                    try:
                        frame = camera[which_cam].image.convert_from_raw(frame_raw)
                        self.stream_video_frame(frame)
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
                    if not camera[key].error and camera[key].video:
                        if camera[key].video.processing:
                            time.sleep(stream_wait_while_recording)
                            break
                        if camera[key].video.recording:
                            time.sleep(stream_wait_while_recording)
                            break

    def do_GET_stream_audio(self, this_path):
        """
        Audio streaming generator function
        """
        param = this_path.split("/")[-2]
        which_cam = param.split("&")[0]
        session_id = param.split("&")[-1]

        srv_logging.debug("AUDIO " + which_cam + ": GET API request '" + self.path + "' - Session-ID: " + session_id)

        if which_cam not in microphones:
            srv_logging.error("AUDIO device '" + which_cam + "' does not exist.")
            return

        if not microphones[which_cam].connected or microphones[which_cam].error:
            srv_logging.error("AUDIO device '" + which_cam + "' not connected or with error.")
            return

        srv_logging.info("Start streaming from '"+which_cam+"' ...")
        size = microphones[which_cam].file_header(size=True)
        self.stream_audio_header(size)
        data = microphones[which_cam].get_first_chunk()
        self.wfile.write(data)
        streaming = True

        last_count = 0
        while streaming:
            while microphones[which_cam].count == last_count and streaming:
                pass
            last_count = microphones[which_cam].count
            data = microphones[which_cam].get_chunk()
            if data != "":
                try:
                    self.wfile.write(data)
                except Exception as err:
                    srv_logging.error("Error during streaming of '"+which_cam+"/"+session_id+"': " + str(err))
                    streaming = False

            if microphones[which_cam].if_error():
                streaming = False
        srv_logging.info("Stopped streaming from '"+which_cam+"'.")

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
        print("--help            Write this information")
        print("--logfile         Write logging output to logfile '"+birdhouse_log_filename+"'")
        print("--backup          Start backup directly (current date, delete directory before)")
        print("--shutdown        Send shutdown signal")
        print("--restart         Send restart signal")
        print("--check-if-start  Start if restart requested (-> request via crontab)")
        exit()

    elif len(sys.argv) > 0 and "--shutdown" in sys.argv:
        shutdown_thread = ServerHealthCheck(maintain=True)
        shutdown_thread.set_shutdown()
        exit()

    elif len(sys.argv) > 0 and "--check-if-start" in sys.argv:
        restart_thread = ServerHealthCheck(maintain=True)
        if not restart_thread.check_start():
            exit()

    elif len(sys.argv) > 0 and "--restart" in sys.argv:
        restart_thread = ServerHealthCheck(maintain=True)
        restart_thread.set_restart()

    set_server_logging(sys.argv)

    srv_logging = set_logging('root')
    ch_logging = set_logging('cam-handl')
    view_logging = set_logging("view-head")

    time.sleep(2)

    srv_logging.info('-------------------------------------------')
    srv_logging.info('Starting ...')
    srv_logging.info('-------------------------------------------')
    srv_logging.info('* Logging into File: ' + str(birdhouse_log_as_file))
    srv_logging.info('* Cache handling: cache=' + str(birdhouse_cache) +
                     ", cache_for_archive=" + str(birdhouse_cache_for_archive))

    check_submodules()
    set_error_images()

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

    # start sensors
    sensor = {}
    for sen in config.param["devices"]["sensors"]:
        settings = config.param["devices"]["sensors"][sen]
        sensor[sen] = BirdhouseSensor(sensor_id=sen, config=config)
        sensor[sen].start()

    # start microphones
    microphones = {}
    for mic in config.param["devices"]["microphones"]:
        microphones[mic] = BirdhouseMicrophone(device_id=mic, config=config)
        microphones[mic].start()

    # start cameras
    camera_first = True
    camera_scan = {}
    camera = {}
    for cam in config.param["devices"]["cameras"]:
        settings = config.param["devices"]["cameras"][cam]
        camera[cam] = BirdhouseCamera(camera_id=cam, config=config, sensor=sensor,
                                      microphones=microphones, first_cam=camera_first)
        if camera_first:
            camera_scan = camera[cam].camera_scan
            camera_first = False
        camera[cam].start()
        camera_list.append(cam)

    # system information
    sys_info = ServerInformation(camera_scan)
    sys_info.start()

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
        views.archive.list_update()

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
        address = ('', int(birdhouse_env["port_api"]))
        server = StreamingServerIPv6(address, StreamingHandler)
        srv_logging.info("Starting WebServer on port " + str(birdhouse_env["port_api"]) + " ...")
        srv_logging.info(" -----------------------------> GO!\n")
        server.serve_forever()
        srv_logging.info("STOPPED SERVER.")

    except Exception as e:
        srv_logging.error("Could not start WebServer: " + str(e))

    # Stop all processes to stop
    finally:
        srv_logging.info("Start stopping threads ...")
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

        count_running_threads = 0
        for thread in threading.enumerate():
            if thread.name != "MainThread":
                count_running_threads += 1
                try:
                    if thread.class_id and thread.id:
                        srv_logging.error("Could not stop correctly: " + thread.name + " = " +
                                          thread.class_id + " (" + thread.id + ")")
                    else:
                        srv_logging.error("Could not stop correctly: " + thread.name)
                except Exception as e:
                    srv_logging.error("Could not stop thread correctly, no further information (" +
                                      str(count_running_threads) + ").")

        if count_running_threads > 0:
            srv_logging.info("-> Killing the " + str(count_running_threads) + " threads that could not be stopped ...")
        srv_logging.info("-------------------------------------------")
        os._exit(os.EX_OK)

