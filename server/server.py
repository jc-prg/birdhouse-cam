#!/usr/bin/python3

import os
import time
import logging
import json
import signal
import sys
import psutil

import socketserver
from http import server
from datetime import datetime
from urllib.parse import unquote

from modules.backup import BirdhouseArchive
from modules.camera import BirdhouseCamera
from modules.config import BirdhouseConfig
from modules.presets import birdhouse_preset, file_types
from modules.views import BirdhouseViews
from modules.sensors import BirdhouseSensor

api_start = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
api_description = {
    "name": "BirdhouseCAM",
    "version": "v0.9.0"
}
app_framework = "v0.9.1"


def on_exit(signum, handler):
    """
    Clean exit on Strg+C
    All shutdown functions are defined in the "finally:" section in the end of this script
    """
    print('\nSTRG+C pressed! (Signal: %s)' % (signum,))
    config.wait_if_locked("ALL")
    config.pause(True)
    for key in camera:
        camera[key].pause(True)
    for key in sensor:
        sensor[key].pause(True)
    time.sleep(1)

    while True:
        confirm = input('Enter "yes" to cancel program now or "no" to keep running [yes/no]: ').strip().lower()
        if confirm == 'yes':
            print("Cancel!\n")
            config.pause(False)
            for key in camera:
                camera[key].pause(False)
            for key in sensor:
                sensor[key].pause(False)
            config.wait_if_locked("ALL")
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
            print('Sorry, no valid answer...\n')
        pass


def on_kill(signum, handler):
    """
    Clean exit on kill command
    All shutdown functions are defined in the "finally:" section in the end of this script
    """
    print('\nKILL command detected! (Signal: %s)' % (signum,))
    logging.warning('KILL command detected! (Signal: %s)' % (signum,))
    logging.info("Starting shutdown ...")
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
        logging.warning("File '" + file + "' does not exist!")
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
        logging.warning("Image '" + file + "' does not exist!")
        return ""

    with open(file, "rb") as image:
        f = image.read()
    return f


def get_system_data():
    """
    """
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

    # ----> Einheit passt noch nicht?! Lt. Anleitung -> in Bytes?!
    hdd = psutil.disk_usage("/")
    system["hdd_used"] = hdd.used / 8 / 1024 / 1024
    system["hdd_total"] = hdd.total / 8 / 1024 / 1024

    return system



class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class StreamingHandler(server.BaseHTTPRequestHandler):

    def redirect(self, file):
        """
        Redirect to other file / URL
        """
        logging.debug("Redirect: " + file)
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

    def admin_allowed(self):
        """
        Check if administration is allowed based on the IP4 the request comes from
        """
        logging.debug("Check if administration is allowed: " + self.address_string() + " / " + str(
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
        logging.debug("POST API request with '" + self.path + "'.")
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
            views.favorite_list_update()
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
        elif self.path.startswith('/remove/'):
            response = backup.delete_marked_files_api(self.path)

        elif self.path.startswith("/edit_presets/"):
            param_string = self.path.replace("/edit_presets/", "")
            param = param_string.split("/")
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
        elif self.path.startswith("/check-timeout/"):
            time.sleep(30)
            response = {"check": "timeout"}
        else:
            self.error_404()
            return

        self.stream_file(filetype='application/json', content=json.dumps(response).encode(encoding='utf_8'), no_cache=True)

    def do_GET(self):
        """
        check path and send requested content
        """
        global camera, sensor, config

        path, which_cam = views.selected_camera(self.path)
        file_ending = self.path.split(".")
        file_ending = "." + file_ending[len(file_ending) - 1].lower()

        config.html_replace["title"] = config.param["title"]
        config.html_replace["active_cam"] = which_cam

        # index
        if self.path == "/":
            self.redirect("/app/index.html")
        elif self.path == "/index.html":
            self.redirect("/app/index.html")
        elif self.path == "/index.html?cam1":
            self.redirect("/app/index.html")
        elif self.path == "/app":
            self.redirect("/app/index.html")
        elif self.path == "/app/":
            self.redirect("/app/index.html")

        # REST API call :  /api/<cmd>/<camera>/param1>/<param2>
        elif self.path.startswith("/api/"):

            logging.debug("GET API request with '" + self.path + "'.")
            param = self.path.split("/")
            command = param[2]
            status = "Success"
            version = {}

            if len(param) > 3:
                which_cam = param[3]

            if command == "INDEX":
                content = views.index(server=self)
            elif command == "FAVORITS":
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
            elif command == "CAMERAS":
                content = views.camera_list(server=self)
            elif command == "status" or command == "version":
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
            else:
                content = {}
                status = "Error: command not found."

            if "links_json" in content:
                content["links"] = content["links_json"]
            if "links_json" in content:
                del content["links_json"]
            if "file_list" in content:
                del content["file_list"]

            content["title"] = config.param["title"]
            content["server"] = config.param["server"]
            content["backup"] = config.param["backup"]

            micro_data = config.param["devices"]["microphones"].copy()
            for key in micro_data:
                if config.param["server"]["ip4_stream_audio"] == "":
                    micro_data[key]["stream_server"] = config.param["server"]["ip4_address"]
                else:
                    micro_data[key]["stream_server"] = config.param["server"]["ip4_stream_audio"]
                micro_data[key]["stream_server"] += ":" + str(micro_data[key]["port"])

            camera_data = config.param["devices"]["cameras"].copy()
            for key in camera_data:
                if key in camera:
                    camera_data[key]["video"]["stream"] = "/stream.mjpg?" + key
                    camera_data[key]["video"]["stream_detect"] = "/detection/stream.mjpg?" + key
                    camera_data[key]["device"] = "camera"
                    camera_data[key]["image"]["resolution_max"] = str(camera[key].max_resolution)
                    camera_data[key]["status"] = {
                        "error": camera[key].error,
                        "error_warn": camera[key].error_image,
                        "error_msg": camera[key].error_msg,
                        "image_error": camera[key].image.error,
                        "image_error_msg": camera[key].image.error_msg,
                        "image_cache_size": camera[key].config_cache_size,
                        "video_error": camera[key].video.error,
                        "video_error_msg": camera[key].video.error_msg,
                        "running": camera[key].running,
                    }
                    if config.param["server"]["ip4_stream_video"] == "":
                        camera_data[key]["video"]["stream_server"] = config.param["server"]["ip4_address"]
                    else:
                        camera_data[key]["video"]["stream_server"] = config.param["server"]["ip4_stream_video"]
                    camera_data[key]["video"]["stream_server"] += ":" + str(config.param["server"]["port_video"])

            sensor_data = config.param["devices"]["sensors"].copy()
            for key in sensor_data:
                sensor_data[key]["values"] = {}
                sensor_data[key]["status"] = {"error": False}
                if key in sensor and sensor[key].error:
                    sensor_data[key]["status"] = {
                        "error": sensor[key].error,
                        "error_msg": sensor[key].error_msg,
                    }
                if key in sensor and sensor[key].running:
                    sensor_data[key]["values"] = sensor[key].get_values()
                else:
                    logging.debug("Sensor not available: "+key)
                    sensor_data[key]["status"] = {
                        "error": True,
                        "error_msg": "Sensor not available: "+key
                    }

            content["devices"] = {
                "cameras": camera_data,
                "sensors": sensor_data,
                "microphones": micro_data
            }
            api_response = {
                "STATUS": {
                    "start_time": api_start,
                    "current_time": datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
                    "admin_allowed": self.admin_allowed(),
                    "check-version": version,
                    "api-call": status,
                    "system": get_system_data(),
                    "reload": False
                },
                "API": api_description,
                "DATA": content
            }
            api_response["DATA"]["selected"] = which_cam
            api_response["DATA"]["active_page"] = command

            self.stream_file(filetype='application/json', content=json.dumps(api_response).encode(encoding='utf_8'),
                             no_cache=True)

        # extract and show single image
        elif '/image.jpg' in self.path:
            # camera[which_cam].setText = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
            camera[which_cam].write_image('image_' + which_cam + '.jpg', camera[which_cam].get_image())
            self.stream_file(filetype='image/jpeg',
                             content=read_image(directory="", filename='image_' + which_cam + '.jpg'))

        # show live stream
        elif '/stream.mjpg' in self.path:
            if camera[which_cam].type != "pi" and camera[which_cam].type != "usb":
                logging.warning(
                    "Unknown type of camera (" + camera[which_cam].type + "/" + camera[which_cam].name + ")")
                self.error_404()
                return

            self.stream_video_header()
            stream = True

            while stream:
                frame = camera[which_cam].get_image_raw()
                frame_raw = frame

                if config.update["camera_"+which_cam]:
                    camera[which_cam].update_main_config()

                if not camera[which_cam].error and not camera[which_cam].error_image:

                    if self.path.startswith("/detection/"):
                        frame_raw = camera[which_cam].show_areas_raw(image=frame_raw)
                        frame = camera[which_cam].image.convert_from_raw(frame_raw)

                    else:
                        frame = camera[which_cam].image.normalize_raw(frame)
                        if camera[which_cam].param["image"]["date_time"]:
                            frame = camera[which_cam].image.draw_date_raw(frame)

                        if camera[which_cam].video.recording:
                            logging.debug("VIDEO RECORDING")
                            length = str(round(camera[which_cam].video.record_info()["length"]))
                            framerate = str(round(camera[which_cam].video.record_info()["framerate"]))
                            y_position = camera[which_cam].image_size[1] - 40
                            frame = camera[which_cam].image.draw_text_raw(frame, "Recording", position=(20, y_position),
                                                                          color=(0, 0, 255), scale=1, thickness=2)
                            frame = camera[which_cam].image.draw_text_raw(frame, "(" + length + "s/" + framerate + "fps)",
                                                                          position=(200, y_position), color=(0, 0, 255),
                                                                          scale=0.5, thickness=1)

                        if camera[which_cam].video.processing:
                            logging.debug("VIDEO PROCESSING")
                            length = str(round(camera[which_cam].video.record_info()["length"]))
                            image_size = str(camera[which_cam].video.record_info()["image_size"])
                            y_position = camera[which_cam].image_size[1] - 40
                            frame = camera[which_cam].image.draw_text_raw(frame, "Processing", position=(20, y_position),
                                                                          color=(0, 255, 255), scale=1, thickness=2)
                            frame = camera[which_cam].image.draw_text_raw(frame, "(" + length + "s/" + image_size + ")",
                                                                          position=(200, y_position), color=(0, 255, 255),
                                                                          scale=0.5, thickness=1)

                        frame = camera[which_cam].image.convert_from_raw(frame)
                else:
                    frame = camera[which_cam].image.convert_from_raw(frame)

                try:
                    camera[which_cam].camera_wait_recording()
                    self.stream_video_frame(frame)
                except Exception as e:
                    stream = False
                    if "Errno 104" in str(e) or "Errno 32" in str(e):
                        logging.debug('Removed streaming client %s: %s', self.client_address, str(e))
                    else:
                        logging.warning('Removed streaming client %s: %s', self.client_address, str(e))

                for key in camera:
                    if not camera[key].error:
                        if camera[key].video.processing:
                            time.sleep(0.3)
                            break
                        if camera[key].video.recording:
                            time.sleep(1)
                            break

        # favicon
        elif self.path.endswith('favicon.ico'):
            self.stream_file(filetype='image/ico', content=read_image(directory='../app', filename=self.path))

        # images, js, css, ...
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

        # request unknown
        else:
            self.error_404()


if __name__ == "__main__":

    # help
    if len(sys.argv) > 0 and "--help" in sys.argv:
        print("jc://birdhouse/\n\nArguments:")
        print("--logfile    Write logging output to logfile 'stream.log'")
        print("--backup     Start backup directly (current date, delete directory before)")
        exit()

    # set logging
    if len(sys.argv) > 0 and "--logfile" in sys.argv:
        logging.basicConfig(filename=os.path.join(os.path.dirname(__file__), "stream.log"),
                            filemode='a',
                            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                            datefmt='%d.%m.%y %H:%M:%S',
                            level=logging.INFO)
        logging.info('-------------------------------------------')
        logging.info('Started ...')
        logging.info('-------------------------------------------')
    else:
        logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)
        logging.info('Starting ...')

    # set system signal handler
    signal.signal(signal.SIGINT, on_exit)
    signal.signal(signal.SIGTERM, on_kill)

    # start config    
    config = BirdhouseConfig(param_init=birdhouse_preset, main_directory=os.path.dirname(os.path.abspath(__file__)))
    config.start()
    config.directory_create("data")
    config.directory_create("images")
    config.directory_create("videos")
    config.directory_create("videos_temp")
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

    # start backups
    time.sleep(1)
    backup = BirdhouseArchive(config, camera, views)
    backup.start()
    if len(sys.argv) > 0 and "--backup" in sys.argv:
        backup.backup_files()
        views.archive_list_update()

    # check if config files for main image directory exists and create if not exists
    if not os.path.isfile(config.file_path("images")):
        for cam in camera:
            camera[cam].pause(True)
        backup.create_image_config()
        for cam in camera:
            camera[cam].pause(False)
    else:
        test_config = config.read(config="images")
        if test_config == {}:
            backup.create_image_config()

    if not os.path.isfile(config.file_path("videos")):
        backup.create_video_config()
    else:
        test_config = config.read(config="videos")
        if test_config == {}:
            backup.create_video_config()

    # Start Webserver
    try:
        address = ('0.0.0.0', config.param["server"]["port"])
        server = StreamingServer(address, StreamingHandler)
        logging.info("Starting WebServer on port "+str(config.param["server"]["port"])+" ...")
        server.serve_forever()

    except Exception as e:
        logging.error("Could not start WebServer: "+str(e))

    # Stop all processes to stop
    finally:
        config.stop()
        backup.stop()
        for cam in camera:
            camera[cam].stop()
        for sen in sensor:
            sensor[sen].stop()
        views.stop()

        server.server_close()
        server.shutdown()
        logging.info("Stopped WebServer.")
