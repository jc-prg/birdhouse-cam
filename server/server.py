#!/usr/bin/python3
import subprocess
import threading
import json
import signal
import sys
import traceback
import secrets
import string

import socket
import math
import urllib.parse
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
from modules.relay import BirdhouseRelay
from modules.bh_class import BirdhouseClass
from modules.bh_database import BirdhouseTEXT
from modules.srv_support import ServerInformation, ServerHealthCheck
from modules.statistics import BirdhouseStatistics
import faulthandler
faulthandler.enable()

api_description = {"name": "BirdhouseCAM", "version": "v1.8.1"}
app_framework = "v1.8.1"


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


def on_exception(exc_type, value, trace_back):
    """
    grab all exceptions and write them to the logfile (if active)
    """
    tb_str = ''.join(traceback.format_exception(exc_type, value, trace_back))
    srv_logging.error("Exception:\n\n" + tb_str + "\n")


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
    read html or text file, replace placeholders and return for stream via webserver
    """
    if filename.startswith("/"):
        filename = filename[1:len(filename)]
    if file_directory.startswith("/"):
        file_directory = file_directory[1:len(file_directory)]
    file = os.path.join(birdhouse_main_directories["server"], file_directory, filename)

    if "?" in file:
        file = file.split("?")[0]

    if not os.path.isfile(file):
        srv_logging.warning("HTML/text file '" + str(file) + "' does not exist!")
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
    """
    decode URL path

    Args:
        string: encoded URI path

    Returns:
        str: decoded URI path
    """
    decoded_path = urllib.parse.unquote(string)
    return decoded_path


def check_pwd(password):
    """
    check if password is correct and return a session ID, if correct

    Args:
        password: password from login dialog
    Returns:
        Any: True if password is correct
    """
    timeout = 5 * 60
    if password == birdhouse_env["admin_password"]:
        characters = string.ascii_letters + string.digits  # Letters and digits
        session_id = ''.join(secrets.choice(characters) for _ in range(32))
        birdhouse_sessions[session_id] = time.time()
        srv_logging.info("Login successful: " + str(session_id))
        return session_id

    elif password in birdhouse_sessions and birdhouse_sessions[password] + timeout > time.time():
        birdhouse_sessions[password] = time.time()
        return password

    else:
        srv_logging.debug("Login failed: " + password)
        return False


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    """
    configure server.HTTPServer
    """
    allow_reuse_address = True
    daemon_threads = True


class StreamingServerIPv6(socketserver.ThreadingMixIn, server.HTTPServer):
    """
    enable IPv6 support
    """
    allow_reuse_address = True
    daemon_threads = True
    address_family = socket.AF_INET6

    def server_bind(self):
        """
        Override server_bind to allow both IPv4 and IPv6 connections
        Bind to the wildcard address ("::") to enable dual-stack support
        """
        self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        super().server_bind()


class StreamingHandler(server.BaseHTTPRequestHandler):
    """
    stream requested files or create API response
    """

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

        Args:
            filetype (str): file type for http header
            content (Any): content to calculate the content size
            no_cache (bool): info if cache-control shall be set in the header
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

    def stream_audio_header(self, size, content_type='audio/x-wav'):
        """
        send header for video stream
        see https://stackoverflow.com/questions/13275409/playing-a-wav-file-on-ios-safari

        Args:
            size (Any): not used at the moment
            content_type (str): content type of audio to be streamed, default is 'audio/x-wav'
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

        ###self.send_header('Content-Range', 'bytes 0-'+str(size)+'/'+str(size))
        # self.send_header('Content-Disposition', 'attachment;filename="audio.WAV"')
        self.send_header('Content-Type', content_type)
        # self.send_header('Content-Type', 'audio/x-wav;codec=PCM')
        ###self.send_header('Content-Length', str(size))
        self.send_header('Content-Transfer-Encoding', 'binary')
        # self.send_header('Transfer-Encoding', 'binary')
        self.send_header('Accept-Ranges', 'bytes')

        self.end_headers()

    def stream_video_frame(self, frame):
        """
        send header and frame inside a MJPEG video stream

        Args:
            frame (Any): video frame content to calculate its length
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

        Returns:
            bool: if authentication has taken place
        """
        admin_type = birdhouse_env["admin_login"]
        admin_deny = birdhouse_env["admin_ip4_deny"]
        admin_allow = birdhouse_env["admin_ip4_allow"]
        admin_pwd = birdhouse_env["admin_password"]
        current_ip = self.address_string().replace("::ffff:","")

        srv_logging.debug("Check if administration is allowed: " +
                          admin_type + " / " + self.address_string() + " / " +
                          "DENY=" + str(admin_deny) + "; ALLOW=" + str(admin_allow))

        if admin_type == "DENY":
            if current_ip in admin_deny:
                return False
            else:
                return True
        elif admin_type == "ALLOW":
            if current_ip in admin_allow:
                return True
            else:
                return False
        elif admin_type == "LOGIN":
            if current_ip in admin_allow:
                return True
            else:
                # initial implementation, later with session ID
                param = self.path_split(check_allowed=False)
                srv_logging.debug("CHECK if " + param["session_id"] + " == " +  admin_pwd + " !!!!!!!! " +
                                  str(param["session_id"] == admin_pwd))
                return check_pwd(param["session_id"])
        else:
            return False

    def path_split(self, check_allowed=True):
        """
        split path into parameters
        -> /app/index.html?<PARAMETER>
        -> /api/<command>/<param1>/<param2>/<param3>/<which_cam+other_cam>
        -> /<other-path>/<filename>.<ending>?parameter1&parameter2

        Args:
            check_allowed (bool): if True, check if logged in
        Returns:
            dict: parameters from URI of API request
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
                            "archive-object-detection", "archive-remove-day", "archive-remove-list", "recreate-image-config",
                            "OBJECTS", "FAVORITES", "bird-names", "recycle-range", "WEATHER", "relay-on", "relay-off",
                            "SETTINGS", "IMAGE_SETTINGS", "DEVICE_SETTINGS", "CAMERA_SETTINGS", "SETTINGS_STATISTICS", "STATISTICS",
                            "python-pkg", "reconnect-microphone", "edit-labels", "delete-labels",
                            "DIARY", "diary-edit-milestone", "diary-delete-milestone", "diary-edit-brood", "diary-delete-brood",
                            "delete-short-video", "delete-thumb-video"]

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
                if param["which_cam"] not in views.camera and param["which_cam"] != "INDEX":
                    srv_logging.warning("Unknown camera requested: " + param["which_cam"] + " (" + self.path + ")")
                    param["which_cam"] = "cam1"
                    last_is_cam = False
                elif param["which_cam"] == "INDEX":
                    srv_logging.debug("Invalid API request due to logout.")
                    param["which_cam"] = "cam1"
                    last_is_cam = False
            elif "command" in param and param["command"] in param_no_cam:
                param["which_cam"] = ""
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

                path = self.path
                if "?" in self.path:
                    path = self.path.split("?")[0]

                param["file_ending"] = path.split(".")
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
        """
        create http response if asked for OPTIONS
        """
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', '*')
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_POST(self):
        """
        Handles HTTP POST requests for a variety of operations including managing camera and server
        settings, executing tasks, and updating views. This method processes the incoming data,
        validates commands and parameters, and executes the corresponding action based on command.

        Returns:
            None
        """
        global camera

        request_start = time.time()
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
        srv_logging.debug("POST//" + param["command"] + ": " + str(param))

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

        if param["command"] == "favorit":
            response = config.queue.set_status_favorite(param)
        elif param["command"] == "recycle":
            response = config.queue.set_status_recycle(param)
        elif param["command"] == "recycle-threshold":
            response = config.queue.set_status_recycle_threshold(param, which_cam)
        elif param["command"] == "recycle-object-detection":
            response = config.queue.set_status_recycle_object(param, which_cam)
        elif param["command"] == "recycle-range":
            response = config.queue.set_status_recycle_range(param)
        elif param["command"] == "create-short-video":
            response = camera[which_cam].video.create_video_trimmed_queue(param)
        elif param["command"] == "delete-short-video":
            response = camera[which_cam].video.delete_shortened_video(param)
        elif param["command"] == "create-thumb-video":
            response = camera[which_cam].video.create_video_thumb_queue(param)
        elif param["command"] == "delete-thumb-video":
            response = camera[which_cam].video.delete_thumbnail(param)
        elif param["command"] == "recreate-image-config":
            response = backup.create_image_config_api(param)
        elif param["command"] == "create-day-video":
            response = camera[which_cam].video.create_video_day_queue(param)
        elif param["command"] == "relay-on":
            response = relays[param["parameter"][0]].switch_on()
        elif param["command"] == "relay-off":
            response = relays[param["parameter"][0]].switch_off()
        elif param["command"] == "remove":
            response = backup.delete_marked_files_api(param)
        elif param["command"] == "remove-archive-object-detection":
            parameters = param["parameter"]
            cam_id = parameters[0]
            date = parameters[1]
            response = camera[cam_id].object.remove_detection_day(date)
        elif param["command"] == "archive-object-detection":
            parameters = param["parameter"]
            cam_id = parameters[0]
            date = parameters[1]
            threshold = -1
            if len(parameters) > 2:
                threshold = parameters[2]
            if "_" in date:
                date_list = date.split("_")
                response = camera[cam_id].object.add2queue_analyze_archive_several_days(date_list, threshold)
            else:
                response = camera[cam_id].object.add2queue_analyze_archive_day(date, threshold)
        elif param["command"] == "archive-remove-day":
            response = backup.delete_archived_day(param)
        elif param["command"] == "archive-download-day":
            response = backup.download_files(param)
        elif param["command"] == "archive-download-list":
            response = backup.download_files(param, body_data)
        elif param["command"] == "diary-edit-brood":
            if len(param["parameter"]) < 2:
                param["parameter"].append("")
            response = views.diary.edit_brood(param["parameter"][0], param["parameter"][1], body_data)
        elif param["command"] == "diary-delete-brood":
            response = views.diary.delete_brood(param["parameter"][0])
        elif param["command"] == "diary-edit-milestone":
            if len(param["parameter"]) < 2:
                param["parameter"].append("")
            response = views.diary.edit_milestone(param["parameter"][0], param["parameter"][1], body_data)
        elif param["command"] == "diary-delete-milestone":
            if len(param["parameter"]) < 2:
                param["parameter"].append("")
            response = views.diary.delete_milestone(param["parameter"][0], param["parameter"][1])
        elif param["command"] == "reconnect-camera":
            response = camera[which_cam].reconnect()
        elif param["command"] == "reconnect-microphone":
            which_mic = param["parameter"][0]
            if which_mic in microphones:
                response = microphones[which_mic].reconnect()
            else:
                response = {}
                srv_logging.warning("reconnect-microphone: " + which_mic + " not found.")
        elif param["command"] == "camera-settings":
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
        elif param["command"] == "cancel-recording":
            for key in camera:
                response = camera[key].video_recording_cancel()
            for key in microphones:
                microphones[key].record_cancel()
            response["command"] = param["command"]
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
            srv_logging.info(str(param["parameter"]))
            if "all" in param["parameter"] or "archive" in param["parameter"]:
                views.archive.list_update(force=True)
            if "all" in param["parameter"] or "favorite" in param["parameter"]:
                views.favorite.list_update(force=True)
            if "all" in param["parameter"] or "object" in param["parameter"]:
                views.object.list_update(force=True)
            response = {"update_views": "started"}
        elif param["command"] == "update-views-complete":
            srv_logging.info(str(param["parameter"]))
            if "all" in param["parameter"] or "archive" in param["parameter"]:
                views.archive.list_update(force=True, complete=True)
            if "all" in param["parameter"] or "favorite" in param["parameter"]:
                views.favorite.list_update(force=True, complete=True)
            if "all" in param["parameter"] or "object" in param["parameter"]:
                views.object.list_update(force=True, complete=True)
            response = {"update-views-complete": "started"}
        elif param["command"] == "force-backup":
            backup.start_backup()
            response = {"backup": "started"}
        elif param["command"] == "force-restart":
            srv_logging.info("---------------------------------------------")
            srv_logging.info("FORCE RESTART OF BIRDHOUSE SERVER ...")
            srv_logging.info("---------------------------------------------")
            config.force_shutdown()
            health_check.set_start(True)
            response = {"shutdown": "started", "mode": "restart"}
        elif param["command"] == "force-shutdown":
            srv_logging.info("---------------------------------------------")
            srv_logging.info("FORCE SHUTDOWN OF BIRDHOUSE SERVER ...")
            srv_logging.info("---------------------------------------------")
            config.force_shutdown()
            health_check.set_start(False)
            response = {"shutdown": "started", "mode": "shutdown"}
        elif param["command"] == "check-timeout":
            time.sleep(30)
            response = {"check": "timeout"}
        elif param["command"] == "edit-presets":
            edit_param = str(param["parameter"]).split("###")
            data = {}
            for entry in edit_param:
                if "==" in entry:
                    key, value = entry.split("==")
                    data[key] = unquote(value)
                    data[key] = decode_url_string(data[key])

            srv_logging.info("edit-presets: " + str(which_cam))
            srv_logging.info(str(data))

            config.main_config_edit("main", data, "", which_cam)
        elif param["command"] == "edit-labels":
            msg = "API CALL '" + param["command"] + "' not implemented yet (" + str(self.path) + ")"
            srv_logging.info(msg)
            srv_logging.info(str(param))
            response = config.queue.entry_edit_object_labels("edit", param["parameter"][0], param["parameter"][1], param["parameter"][2])
        elif param["command"] == "set-temp-threshold":
            srv_logging.debug("Set temporary threshold to camera '"+which_cam+"': " + str(param["parameter"]))
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
            check = check_pwd(param["parameter"][0])
            if check == False:
                response["check-pwd"] = False
                response["session-id"] = ""
            else:
                response["check-pwd"] = True
                response["return-page"] = param["parameter"][1]
                response["session-id"] = check
        elif param["command"] == "reset-image-presets":
            response = camera[which_cam].reset_image_presets()
            srv_logging.info(str(param))
        elif param["command"] == "create-max-resolution-image":
            camera[which_cam].image_recording_max()
            response = {"info": "create-max-resolution-image"}
        elif param["command"] == "--template-to-implement-new-POST-command--":
            msg = "API CALL '" + param["command"] + "' not implemented yet (" + str(self.path) + ")"
            srv_logging.info(msg)
            srv_logging.info(str(param))
            response = {"info": msg}
        else:
            self.error_404()
            return

        api_response["STATUS"] = response
        config.set_processing_performance("api_POST", param["command"], request_start)

        self.stream_file(filetype='application/json', content=json.dumps(response).encode(encoding='utf_8'),
                         no_cache=True)

    def do_GET(self):
        """
        check path and send requested content, forwards to other functions depending on the requested content
        """
        global camera, sensor, config

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
        elif '/audio.wav' in self.path or '/audio.mp3' in self.path:
            self.do_GET_stream_audio(self.path)
        elif self.path.endswith('favicon.ico'):
            self.stream_file(filetype='image/ico',
                             content=read_image(file_directory=birdhouse_directories["html"], filename=self.path))
        elif self.path.startswith("/app/index.html"):
            self.stream_file(filetype=file_types[".html"],
                             content=read_html(file_directory=birdhouse_directories["html"], filename="index.html"))
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
        Handles API GET requests by processing and responding with structured data based
        on the provided command and parameters.

        This method parses the incoming API request, determines the appropriate course
        of action based on the defined commands, and generates a response with detailed
        status, settings, and data information. The response structure is defined based
        on the command and the parameters specified in the request.

        Returns:
            None: The method sends a response back to the client with relevant data and
                does not explicitly return any value.
        """
        global camera, sensor, config

        request_start = time.time()
        request_times = {}
        status = "Success"
        version = {}

        param = self.path_split()
        which_cam = param["which_cam"]
        command = param["command"]
        config.user_activity("set", command)

        srv_logging.debug("GET API request with '" + self.path + "'.")
        srv_logging.debug("GET//" + command + ": " + str(param))

        api_data = {}
        api_response = {
            "API": api_description,
            "DATA": {},
            "SETTINGS": {},
            "STATUS": {},
            "WEATHER": {}
        }
        api_response["API"]["request_url"] = self.path
        api_response["API"]["request_param"] = param
        api_response["API"]["request_command"] = command
        api_response["API"]["request_ip"] = self.address_string().replace("::ffff:","")
        api_commands = {
            "data"     : ["INDEX", "FAVORITES", "TODAY", "TODAY_COMPLETE", "ARCHIVE", "VIDEOS", "VIDEO_DETAIL",
                          "DEVICES", "OBJECTS", "STATISTICS", "bird-names", "WEATHER",
                          "SETTINGS", "CAMERA_SETTINGS", "IMAGE_SETTINGS", "DEVICE_SETTINGS",
                          "SETTINGS_CAMERAS", "SETTINGS_DEVICES", "SETTINGS_IMAGE", "SETTINGS_INFORMATION", "SETTINGS_STATISTICS",
                          "status", "list","DIARY"],
            "info"     : ["camera-param", "version", "reload","python-pkg"],
            "status"   : ["status", "list", "WEATHER", "INDEX", "STATISTICS"],
            "status_small" : ["last-answer"],
            "settings" : ["status", "list", "INDEX", "STATISTICS"],
            "weather"  : ["WEATHER"]
        }
        no_extra_command = ["WEATHER", "SETTINGS", "CAMERA_SETTINGS","IMAGE_SETTINGS","DEVICE_SETTINGS"]
        weather_status = {}

        # prepare data structure and set some initial values
        if command in api_commands["status"]: # or command in api_commands["data"]:
            api_response["STATUS"] = {
                "admin_allowed": self.admin_allowed(),
                "api-call": status,
                "check-version": version,
                "current_time": config.local_time().strftime('%d.%m.%Y %H:%M:%S'),
                "start_time": api_start,
                "up_time": round(time.time() - api_start_tc),
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
                    "video_frame_count": config.video_frame_count,
                    "backup_process_running": backup.backup_running,
                    "queue_waiting_time": config.queue.queue_wait,
                    "health_check": health_check.status(),
                    "downloads": backup.download_files_waiting(param),
                    "initial_setup": config.param["server"]["initial_setup"],
                    "last_answer": ""
                },
                "server_performance": config.get_processing_performance(),
                "server_config_queues": config.get_queue_size(),
                "server_object_queues": {},
                "system": {},
                "video_recording": {},
                "video_creation_day": {},
                "object_detection": {
                    "active": birdhouse_status["object_detection"],
                    "processing": config.object_detection_processing,
                    "processing_info": config.object_detection_info,
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
                },
                "brood": views.diary.get_current_state()
            }
            # grab recording infos for defined cameras
            for cam_id in camera:
                active = camera[cam_id].active
                api_response["STATUS"]["video_recording"][cam_id] = {}
                api_response["STATUS"]["video_creation_day"][cam_id] = {}
                api_response["STATUS"]["server_object_queues"]["archive_"+cam_id] = len(camera[cam_id].object.detect_queue_archive)
                if camera[cam_id].if_error():
                    active = False
                if camera[cam_id].video.recording or camera[cam_id].video.processing:
                    api_response["STATUS"]["video_recording"][cam_id] = {
                        "active":     active,
                        "processing": camera[cam_id].video.processing,
                        "recording":  camera[cam_id].video.recording,
                        "error":      camera[cam_id].if_error(),
                        "info":       camera[cam_id].video.record_info()
                    }
                else:
                    api_response["STATUS"]["video_recording"][cam_id] = {
                        "active":     active,
                        "processing": camera[cam_id].video.processing,
                        "recording":  camera[cam_id].video.recording,
                        "error":      camera[cam_id].if_error(),
                        "info":       {}
                    }
                if camera[cam_id].video.processing_day_video:
                    api_response["STATUS"]["video_creation_day"][cam_id] = {
                        "active":     active,
                        "processing": camera[cam_id].video.processing_day_video,
                        "error":      camera[cam_id].if_error(),
                        "info":       camera[cam_id].video.record_info()
                    }
                else:
                    api_response["STATUS"]["video_creation_day"][cam_id] = {
                        "active":     active,
                        "processing": camera[cam_id].video.processing_day_video,
                        "error":      camera[cam_id].if_error(),
                        "info":       {}
                    }
                api_response["STATUS"]["server_object_queues"]["image_"+cam_id] = len(camera[cam_id].object.detect_queue_image)
        if command in api_commands["status_small"]:
            api_response["STATUS"] = {
                "admin_allowed": self.admin_allowed(),
                "api-call": status,
                "check-version": version,
                "current_time": config.local_time().strftime('%d.%m.%Y %H:%M:%S'),
                "start_time": api_start,
                "server": {
                    "view_archive_loading": views.archive.loading,
                    "view_favorite_loading": views.favorite.loading,
                    "view_object_loading": views.object.loading,
                    "view_archive_progress": views.tools.get_progress("archive"),
                    "view_favorite_progress": views.tools.get_progress("favorite"),
                    "view_object_progress": views.tools.get_progress("object"),
                    "last_answer": ""
                },
                "object_detection": {
                    "active": birdhouse_status["object_detection"],
                    "processing": config.object_detection_processing,
                    "progress": config.object_detection_progress,
                    "waiting": config.object_detection_waiting,
                },
                "view": {
                    "selected": which_cam,
                    "active_cam": which_cam,
                    "active_date": "",
                    "active_page": command
                }
            }
        if command in api_commands["settings"]:
            api_response["SETTINGS"] = {
                "backup": {},
                "devices": {
                    "cameras": {},
                    "sensors": {},
                    "weather": {},
                    "microphones": {},
                    "relays": {}
                },
                "info": {},
                "localization": {},
                "server": {},
                "title": "",
                "views": {},
                "weather": {}
                }
        if command in api_commands["data"]:
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
                #api_response["STATUS"]["view"]["active_date"] = param["parameter"][0]

        request_times["0_initial"] = round(time.time() - request_start, 4)

        if command == "INDEX":
            content = views.index_view(param=param)
        elif command == "DIARY":
            content = views.diary_view(param=param)
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
        elif command == "STATISTICS":
            content = views.statistic_list(param=param)
        elif command == "SETTINGS_STATISTICS":
            content = views.statistic_list(param=param)
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
            content = {
                "active_cam" : which_cam,
                "camera_properties" : camera[which_cam].get_camera_status("properties")
            }
        elif command == "python-pkg":
            pkg_string = ""
            content = {"packages": {}}
            #for dst in pkg_resources.working_set:
            #    content["packages"][dst.project_name] = dst.version
            #    pkg_string += dst.project_name + "==" + dst.version + "\n"
            try:
                cmd_data = "/usr/local/bin/pip3"
                cmd_data += " list --format=freeze"
                pkg_string = str(subprocess.check_output(cmd_data))
            except Exception as e:
                pkg_string = "Could not get Python packages list: " + str(e)
            content["packages"] = pkg_string
        elif command in no_extra_command:
            content = {}
        else:
            content = {}
            status = "Error: command not found."
            srv_logging.warning("API CALL: " + status + " (" + self.path + ")")
        # execute API commands

        request_times["1_api-commands"] = round(time.time() - request_start, 4)

        # add maintenance information
        if "maintenance" in config.param:
            api_response["API"]["maintenance"] = config.param["maintenance"]
            if command in api_commands["settings"]:
                api_response["SETTINGS"]["maintenance"] = config.param["maintenance"]

        # collect data for WEATHER section
        if command in api_commands["weather"]:
            if config.weather is not None:
                api_response["WEATHER"] = config.weather.get_weather_info("all")

        # collect data for STATUS section
        if command in api_commands["status"]: # or command in api_commands["data"]:
            weather_status = config.weather.get_weather_info("status")
            weather_current = config.weather.get_weather_info("current_extended")

            param_to_publish = ["last_answer", "background_process"]
            for key in param_to_publish:
                if key in content:
                    api_response["STATUS"]["server"][key] = content[key]

            for key in camera:
                api_response["STATUS"]["object_detection"]["models_loaded_status"][key] = camera[key].object.detect_loaded
                api_response["STATUS"]["object_detection"]["models_loaded"][key] = camera[key].object.detect_settings["model"]

            api_response["STATUS"]["object_detection"]["status"] = birdhouse_status["object_detection"]
            api_response["STATUS"]["object_detection"]["status_details"] = birdhouse_status["object_detection_details"]
            api_response["STATUS"]["weather"] = weather_current

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

            request_times["1_status-commands"] = round(time.time() - request_start, 4)

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
                "server_mode": birdhouse_env["installation_type"],
                "server_restart": birdhouse_env["restart_server"],
                "detection_active": birdhouse_env["detection_active"]
            }
            api_response["SETTINGS"]["server"] = server_config

            if self.admin_allowed():
                api_response["SETTINGS"]["webdav"] = {
                    "active": sys_info.webdav_available,
                    "show": birdhouse_env["webdav_show"],
                    "port": birdhouse_env["webdav_port"],
                    "user": birdhouse_env["webdav_user"],
                    "pwd": birdhouse_env["webdav_pwd"],
                }
            else:
                api_response["SETTINGS"]["webdav"] = {
                    "active": sys_info.webdav_available,
                    "port": birdhouse_env["webdav_port"],
                    "show": birdhouse_env["webdav_show"],
                    "user": "",
                    "pwd": "",
                }

        # collect data for several lists views TODAY, ARCHIVE, TODAY_COMPLETE, ...
        if command in api_commands["data"]:# or command in api_commands["status"]:
            param_to_publish = ["entries", "entries_delete", "entries_yesterday", "entries_favorites", "groups",
                                "archive_exists", "info", "chart_data", "weather_data", "days_available",
                                "day_back", "day_forward", "birds","diary"]
            for key in param_to_publish:
                if key in content:
                    api_data["data"][key] = content[key]

            param_to_publish = ["view", "view_count", "links", "max_image_size", "label"]
            for key in param_to_publish:
                if key in content:
                    api_data["view"][key] = content[key]

            api_response["DATA"] = api_data
            request_times["2_view-commands"] = round(time.time() - request_start, 3)

        # collect data for STATUS and SETTINGS sections (to be clarified -> goal: only for status request)
        if command not in api_commands["info"] and command not in api_commands["status_small"]:
            # collect data for "DATA" section
            param_to_publish = ["title", "backup", "weather", "views", "info"]
            for key in param_to_publish:
                if key in content:
                    content[key] = config.param[key]
            request_times["5_config"] = round(time.time() - request_start, 4)

            # get device data
            if command in api_commands["status"]:
                api_response["STATUS"]["devices"] = sys_info.get_device_status()
                request_times["6_devices_status"] = round(time.time() - request_start, 4)

            # get microphone data and create streaming information
            micro_data = config.param["devices"]["microphones"].copy()
            for key in micro_data:
                micro_data[key]["stream_server"] = birdhouse_env["server_audio"]
                micro_data[key]["stream_server"] += ":" + str(micro_data[key]["port"])
            request_times["7_status_micro"] = round(time.time() - request_start, 4)

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
            request_times["8_status_camera"] = round(time.time() - request_start, 4)

            # get sensor data
            sensor_data = config.param["devices"]["sensors"].copy()
            for key in sensor_data:
                sensor_data[key]["values"] = {}
                if key in sensor and sensor[key].if_running():
                    sensor_data[key]["values"] = sensor[key].get_values()
            request_times["9_status_sensor"] = round(time.time() - request_start, 4)

            if command in api_commands["settings"]:
                api_response["SETTINGS"]["devices"] = {
                "cameras": camera_data,
                "sensors": sensor_data,
                "microphones": micro_data,
                "weather": weather_status,
                "relays": config.param["devices"]["relays"]
            }

        # info
        if command in api_commands["info"]:
            for key in content:
                api_response["DATA"][key] = content[key]

        # cleanup data structure, remove unused elements
        if command == "last-answer":
            del api_response["DATA"]
            del api_response["SETTINGS"]
            for key in content:
                api_response["STATUS"]["server"][key] = content[key]
        elif command == "WEATHER":
            del api_response["SETTINGS"]
        elif command == "python-pkg":
            api_response["DATA"] = content

        if command not in api_commands["status"] and command not in api_commands["info"]:
            if "STATUS" in api_response:
                if "system" in api_response["STATUS"]:
                    del api_response["STATUS"]["system"]
                if "database" in api_response["STATUS"]:
                    del api_response["STATUS"]["database"]
                if "check-version" in api_response["STATUS"]:
                    del api_response["STATUS"]["check-version"]
        if command not in api_commands["weather"] and "WEATHER" in api_response:
            del api_response["WEATHER"]

        # add API request information
        #if param["session_id"] in request_times and param["session_id"] != "":
        api_response["API"]["request_details"] = request_times
        api_response["API"]["request_time"] = round(time.time() - request_start, 3)
        config.set_processing_performance("api_GET", command, request_start)

        self.stream_file(filetype='application/json', content=json.dumps(api_response).encode(encoding='utf_8'),
                         no_cache=True)

    def do_GET_image(self, which_cam):
        """
        Handles GET requests to provide image-related operations, including comparing images and extracting a single
        image. This function supports serving different variations of images, such as images showing differences between
        two images and images extracted directly from the camera stream.

        Args:
            which_cam: The identifier for selecting the camera used to perform image operations.
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

            image_1st = camera[which_cam].image.read(path_1st)
            image_2nd = camera[which_cam].image.read(path_2nd)
            image_diff = camera[which_cam].image.compare_raw_show(image_1st, image_2nd)
            image_diff = camera[which_cam].image.draw_text_raw(image_diff, "-> " + param[2] + ":" + param[3] + ":" +
                                                               param[4], position=(10, 20), scale=0.5, thickness=1)
            camera[which_cam].image.write(path_diff, image_diff)
            srv_logging.debug("---->" + str(path_diff))
            srv_logging.debug("---->" + str(config.db_handler.directory("images", "", False)))

            time.sleep(0.5)
            self.stream_file(filetype='image/jpeg',
                             content=read_image(file_directory="../data/"+config.db_handler.directory("images", "", False),
                                                filename=filename_diff))

        # extract and show single image (creates images with a longer delay ?)
        elif '/image.jpg' in self.path:
            filename = "_image_temp_" + which_cam + ".jpg"
            img_path = os.path.join(config.db_handler.directory("images"), filename)
            camera[which_cam].image.write(img_path, camera[which_cam].get_stream(stream_id="file",
                                                                                 stream_type="camera",
                                                                                 stream_resolution="hires"))
            time.sleep(2)
            self.stream_file(filetype='image/jpeg',
                             content=read_image(file_directory="../data/images/", filename=filename))

    def do_GET_stream_video(self, which_cam, which_cam2, param):
        """
        Handles video streaming for a specified camera or set of cameras, managing configurations,
        stream properties, and error handling during streaming operations.

        Args:
            which_cam: Identifier of the primary camera to stream video from.
            which_cam2: Identifier of the secondary camera to be used in Picture-in-Picture (PiP) mode, if applicable.
            param: Dictionary containing additional configuration parameters for the streaming session.
                Includes session metadata and API request details.
        """
        global config

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
        frame_id = frame_raw = frame_raw_pip = None

        self.stream_video_header()
        config.camera_capture_active = False
        while stream_active:

            config.video_frame_count += 1

            if camera[which_cam].get_stream_kill(stream_id_ext, stream_id_int) or config.thread_ctrl["shutdown"]:
                stream_active = False

            while config.camera_capture_active:
                time.sleep(0.1)

            if config.update["camera_" + which_cam]:
                camera[which_cam].reconnect()

            if config.update_config["camera_" + which_cam]:
                camera[which_cam].update_main_config(reload=False)

            if frame_id != camera[which_cam].get_stream_image_id() \
                    or camera[which_cam].if_error() or camera[which_cam].camera_stream_raw.if_error():

                if stream_object:
                    frame_raw = camera[which_cam].get_stream_object_detection(stream_id=str(stream_id_int),
                                                                              stream_type=stream_type,
                                                                              stream_resolution=stream_resolution,
                                                                              system_info=True)
                else:
                    frame_raw = camera[which_cam].get_stream(stream_id=str(stream_id_int),
                                                             stream_type=stream_type,
                                                             stream_resolution=stream_resolution,
                                                             system_info=True)
                frame_id = camera[which_cam].get_stream_image_id()

                if frame_raw is not None and len(frame_raw) > 0:
                    if stream_pip and which_cam2 != "" and which_cam2 in camera:
                        frame_raw_pip = camera[which_cam2].get_stream(stream_id=str(stream_id_int),
                                                                      stream_type=stream_type,
                                                                      stream_resolution="hires",  # hires
                                                                      system_info=False,
                                                                      wait=False)

                        if frame_raw_pip is not None and len(frame_raw_pip) > 0:

                            total_pixels_cam1 = frame_raw.shape[0] * frame_raw.shape[1]
                            total_pixels_cam2 = frame_raw_pip.shape[0] * frame_raw_pip.shape[1]
                            desired_total_pixels_cam2 = total_pixels_cam1 / 9
                            scale_factor = math.sqrt(desired_total_pixels_cam2 / total_pixels_cam2) * 100
                            if frame_raw.shape[1] > 1000:
                                distance = 50
                            else:
                                distance = 30
                            srv_logging.debug(" PiP ... size %: " + str(scale_factor) + " / distance: " + str(distance))

                            frame_raw_pip = camera[which_cam2].image.resize_raw(frame_raw_pip, scale_factor)
                            frame_raw = camera[which_cam].image.image_in_image_raw(raw=frame_raw,
                                                                                   raw2=frame_raw_pip,
                                                                                   position=int(cam2_pos),
                                                                                   distance=distance)

                # burn addition information onto the video image if recording or processing
                if stream_type == "camera" \
                        and not camera[which_cam].if_error() \
                        and not camera[which_cam].image.if_error() \
                        and not camera[which_cam].camera_streams[stream_id].if_error():

                    if camera[which_cam].video.recording:
                        srv_logging.debug("VIDEO RECORDING")
                        record_info = camera[which_cam].video.record_info()
                        #length = str(round(record_info["length"], 1)) + "s"
                        framerate = str(round(record_info["framerate"], 1)) + "fps"
                        time_s = int(record_info["length"]) % 60
                        time_m = round((int(record_info["length"]) - time_s) / 60)
                        time_l = str(time_m).zfill(2) + ":" + str(time_s).zfill(2)
                        line1 = "Recording"
                        line2 = time_l + " / " + framerate + " (max " + str(camera[which_cam].video.max_length) + "s)"
                        camera[which_cam].set_system_info(True, line1, line2, (0, 0, 100))
                        camera[which_cam].set_system_info_lowres(True, "R", (0, 0, 100))

                    elif camera[which_cam].video.processing:
                        srv_logging.debug("VIDEO PROCESSING")
                        record_info = camera[which_cam].video.record_info()
                        #length = str(round(record_info["length"], 1)) + "s"
                        #framerate = str(round(record_info["framerate"], 1)) + "fps"
                        progress = str(round(float(record_info["percent"]), 1)) + "%"
                        time_s = int(record_info["elapsed"]) % 60
                        time_m = round((int(record_info["elapsed"]) - time_s) / 60)
                        time_e = str(time_m).zfill(2) + ":" + str(time_s).zfill(2)
                        line1 = "Processing"
                        line2 = time_e + " / " + progress
                        camera[which_cam].set_system_info(True, line1, line2, (0, 255, 255))
                        camera[which_cam].set_system_info_lowres(True, "P", (0, 255, 255))

                    else:
                        camera[which_cam].set_system_info(False)
                        camera[which_cam].set_system_info_lowres(False)

                if not stream_active:
                    srv_logging.info("Closed streaming client: " + stream_id_ext)
                    self.stream_video_end()
                    frame_id = frame_raw = frame_raw_pip = None
                    break

                elif frame_raw is None or len(frame_raw) == 0:
                    srv_logging.warning("Stream: Got an empty frame for '" + which_cam + "' ...")

                else:
                    try:
                        frame = camera[which_cam].image.convert_from_raw(frame_raw)
                        self.stream_video_frame(frame)
                    except Exception as error_msg:
                        stream_active = False
                        frame_id = frame_raw = frame_raw_pip = None
                        if "Errno 104" in str(error_msg) or "Errno 32" in str(error_msg):
                            srv_logging.debug('Removed streaming client %s: %s', self.client_address, str(error_msg))
                        else:
                            srv_logging.warning('Removed streaming client %s: %s', self.client_address, str(error_msg))
                        break

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
        super().finish()

    def do_GET_stream_audio(self, this_path):
        """
        Handles the GET request for streaming audio data from a specified microphone. This function
        streams audio in either WAV or MP3 format, depending on the API request URL, provided
        the microphone is connected, error-free, and MP3 encoding (if required) is available.

        Args:
            this_path (str): The requested API path containing the microphone identifier and session ID.
        """
        param = this_path.split("/")[-2]
        which_cam = param.split("&")[0]
        session_id = param.split("&")[-1]

        srv_logging.debug("AUDIO " + which_cam + ": GET API request '" + self.path + "' - Session-ID: " + session_id)

        if which_cam not in microphones:
            srv_logging.error("AUDIO device '" + which_cam + "' does not exist.")
            return

        if not microphones[which_cam].encode_mp3_available:
            srv_logging.error("MP3 Encoding '" + which_cam + "' not activated.")
            return

        if not microphones[which_cam].connected or microphones[which_cam].error:
            srv_logging.error("AUDIO device '" + which_cam + "' not connected or with error.")
            return

        srv_logging.info("Start streaming from '"+which_cam+"' ("+self.path+") ...")
        size = microphones[which_cam].file_header(size=True)
        streaming = True
        data = ""

        if ".wav" in self.path:
            self.stream_audio_header(size)
            data = microphones[which_cam].get_first_chunk()
            self.wfile.write(data)

        elif ".mp3" in self.path:
            self.stream_audio_header(size, "audio/mp3")
            data = microphones[which_cam].get_first_chunk()

        srv_logging.debug("... got first chunk (" + str(len(data)) + ")")
        last_count = 0
        count = 0
        while streaming:
            count += 1
            srv_logging.debug("...A... " + str(count))
            if ".wav" in self.path:
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

            elif ".mp3" in self.path:
                frames = []
                srv_logging.debug("Collect frames: " + str(microphones[which_cam].RATE) + "/" +
                                  str(microphones[which_cam].CHUNK) + "=" +
                                  str(int(microphones[which_cam].RATE/microphones[which_cam].CHUNK)))

                i = 0
                while i < int(microphones[which_cam].RATE / microphones[which_cam].CHUNK):
                    while microphones[which_cam].count == last_count and streaming:
                        pass
                    last_count = microphones[which_cam].count
                    data = microphones[which_cam].get_chunk()
                    frames.append(data)
                    i += 1

                if frames != "":
                    try:
                        mp3_data = microphones[which_cam].encode_mp3(frames, 7)
                        self.wfile.write(mp3_data)

                    except Exception as err:
                        srv_logging.error("Error during streaming of '"+which_cam+"/"+session_id+"': " + str(err))
                        streaming = False

            if microphones[which_cam].if_error():
                streaming = False

        srv_logging.info("Stopped streaming from '"+which_cam+"'.")


on_exception_setting()
sys.excepthook = on_exception


if __name__ == "__main__":
    api_start = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
    api_start_tc = time.time()

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
        shutdown_thread = ServerHealthCheck("", None, maintain=True)
        shutdown_thread.set_shutdown()
        exit()

    elif len(sys.argv) > 0 and "--check-if-start" in sys.argv:
        restart_thread = ServerHealthCheck("", None, maintain=True)
        if not restart_thread.check_start():
            exit()

    elif len(sys.argv) > 0 and "--restart" in sys.argv:
        restart_thread = ServerHealthCheck("", None, maintain=True)
        restart_thread.set_restart()
        exit()

    elif len(sys.argv) > 0 and "--rpi" in sys.argv:
        # when rpi wait a minute, as RPI have to connect to the internet first to get the correct time
        time.sleep(60)
        api_start = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        api_start_tc = time.time()

    set_server_logging(sys.argv)
    srv_logging = set_logging('root')
    ch_logging = set_logging('cam-handl')
    view_logging = set_logging("view-head")

    time.sleep(1)

    if birdhouse_loglevel_default == logging.WARNING:
        srv_logging.warning('---------------------------------------------')
        srv_logging.warning('Starting ... log level WARNING')
        srv_logging.warning('---------------------------------------------')

    elif birdhouse_loglevel_default == logging.ERROR:
        srv_logging.error('---------------------------------------------')
        srv_logging.error('Starting ... log level ERROR')
        srv_logging.error('---------------------------------------------')

    else:
        srv_logging.info('---------------------------------------------')
        srv_logging.info('Starting ...')
        srv_logging.info('---------------------------------------------')
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

    # start statistics
    statistics = BirdhouseStatistics(config=config)
    statistics.start()
    config.set_statistics(statistics)

    # start relays
    relays = {}
    if "relays" in config.param["devices"]:
        for relay in config.param["devices"]["relays"]:
            relays[relay] = BirdhouseRelay(relay_id=relay, config=config)
            relays[relay].start()
            #time.sleep(2)
            #relays[relay].test()

    # start sensors
    sensor = {}
    for sen in config.param["devices"]["sensors"]:
        settings = config.param["devices"]["sensors"][sen]
        sensor[sen] = BirdhouseSensor(sensor_id=sen, config=config)
        sensor[sen].start()

    # start microphones
    first_micro = True
    microphones = {}
    for mic in config.param["devices"]["microphones"]:
        microphones[mic] = BirdhouseMicrophone(device_id=mic, config=config, first_micro=first_micro)
        microphones[mic].start()
        first_micro = False

    # start cameras
    camera_first = True
    camera_scan = {}
    camera = {}
    for cam in config.param["devices"]["cameras"]:
        settings = config.param["devices"]["cameras"][cam]
        camera[cam] = BirdhouseCamera(camera_id=cam, config=config, sensor=sensor, relays=relays,
                                      microphones=microphones, statistics=statistics, first_cam=camera_first)
        if camera_first:
            camera_scan = camera[cam].camera_scan
            camera_first = False
        camera[cam].start()
        camera_list.append(cam)

    # system information
    sys_info = ServerInformation(camera_scan, config, camera, sensor, microphones, relays, statistics)
    sys_info.start()

    # start views and commands
    views = BirdhouseViews(config=config, camera=camera, statistic=statistics)
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



    # Start Webserver
    try:
        # start API
        address = ('', int(birdhouse_env["port_api"]))
        server = StreamingServerIPv6(address, StreamingHandler)

        # start health check
        health_check = ServerHealthCheck(config, server)
        health_check.start()

        srv_logging.info("Starting REST API on port " + str(birdhouse_env["port_api"]) + " ...")
        srv_logging.info("WebServer running on port " + str(birdhouse_env["port_http"]) + " ...")
        srv_logging.info(" -----------------------------> GO!\n")
        config.set_processing_performance("server", "boot", api_start_tc)

        server.serve_forever()
        srv_logging.info("STOPPED SERVER.")

    except Exception as e:
        srv_logging.error("Could not start WebServer: " + str(e))
        srv_logging.error("Stopping!")
        os._exit()

    # Stop all processes to stop
    finally:
        server.server_close()
        server.shutdown()
        srv_logging.info("Stopped WebServer.")
        srv_logging.info("---------------------------------------------")
        srv_logging.info("Looking for left over threads ...")

        time.sleep(5)
        count_running_threads = 0
        for thread in threading.enumerate():
            if thread.name != "MainThread":
                count_running_threads += 1
                try:
                    if thread.class_id and thread.id:
                        srv_logging.warning("Could not stop correctly: " + thread.name + " = " +
                                            thread.class_id + " (" + thread.id + ")")
                    else:
                        srv_logging.warning("Could not stop correctly: " + thread.name)
                except Exception as e:
                    srv_logging.warning("Could not stop thread correctly, no further information (" +
                                        str(count_running_threads) + "): " + str(e))

        if count_running_threads > 0:
            srv_logging.info("-> Killing the " + str(count_running_threads) + " threads that could not be stopped ...")
        srv_logging.info("---------------------------------------------\n")
        os._exit(os.EX_OK)

