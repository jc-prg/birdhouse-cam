#!/usr/bin/python3

import os
import time
import logging
import json
import signal
import sys

import socketserver
from http import server
from datetime import datetime

from modules.backup import BirdhouseArchive
from modules.camera import BirdhouseCamera
from modules.config import BirdhouseConfig
from modules.commands import BirdhouseCommands
from modules.presets import birdhouse_preset
from modules.presets import file_types
from modules.views import BirdhouseViews

api_description = {
    "name": "BirdhouseCAM",
    "version": "v0.9.0"
}
api_start = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
app_framework = "v0.9.1"


def on_exit(signum, handler):
    """
    Clean exit on Strg+C
    All shutdown functions are defined in the "finally:" section in the end of this script
    """
    time.sleep(1)
    print('\nSTRG+C pressed! (Signal: %s)' % (signum,))
    while True:
        confirm = input('Enter "yes" to cancel program now or "no" to keep running [yes/no]: ').strip().lower()
        if confirm == 'yes':
            print("Cancel!\n")
            sys.exit()
        elif confirm == 'no':
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
    sys.exit()


def read_html(directory, filename, content=""):
    """
    read html file, replace placeholders and return for stream via webserver
    """
    if filename.startswith("/"):
        filename = filename[1:len(filename)]
    if directory.startswith("/"):
        directory = directory[1:len(directory)]
    file = os.path.join(config.param["path"], directory, filename)

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
    file = os.path.join(config.param["path"], directory, filename)
    file = file.replace("backup/", "")

    if not os.path.isfile(file):
        logging.warning("Image '" + file + "' does not exist!")
        return ""

    with open(file, "rb") as image:
        f = image.read()
    return f


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
        self.send_header('Age', 0)
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
        self.send_header('Content-Length', len(str(frame)))
        self.end_headers()
        self.wfile.write(frame)
        self.wfile.write(b'\r\n')

    def admin_allowed(self):
        """
        Check if administration is allowed based on the IP4 the request comes from
        """
        logging.debug("Check if administration is allowed: " + self.address_string() + " / " + str(
            config.param["ip4_admin_deny"]))
        if self.address_string() in config.param["ip4_admin_deny"]:
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
        global config, camera, backup

        logging.info("POST API request with '" + self.path + "'.")
        response = {}

        if not self.admin_allowed():
            response["error"] = "Administration not allowed for this IP-Address!"
            self.stream_file(filetype='application/json', content=json.dumps(response).encode(encoding='utf_8'),
                             no_cache=True)

        if self.path.startswith("/api"):
            self.path = self.path.replace("/api", "")

        if self.path.startswith("/favorit/"):
            response = commands.setStatusFavoritNew(self)
        elif self.path.startswith("/recycle/"):
            response = commands.setStatusRecycleNew(self)
        elif self.path.startswith("/recycle-range/"):
            response = commands.setStatusRecycleRange(self)
        elif self.path.startswith('/remove/'):
            response = commands.deleteMarkedFiles(self)
        elif self.path.startswith("/start/recording/"):
            response = commands.startRecording(self)
        elif self.path.startswith("/stop/recording/"):
            response = commands.stopRecording(self)
        elif self.path.startswith("/create-short-video/"):
            response = commands.createShortVideo(self)
        elif self.path.startswith("/create-day-video/"):
            response = commands.createDayVideo(self)
        else:
            self.error_404()
            return

        self.stream_file(filetype='application/json', content=json.dumps(response).encode(encoding='utf_8'),
                         no_cache=True)

    def do_GET(self):
        """
        check path and send requested content
        """
        path, which_cam = views.selected_camera(self.path)
        file_ending = self.path.split(".")
        file_ending = "." + file_ending[len(file_ending) - 1].lower()

        config.html_replace["title"] = config.param["title"]
        config.html_replace["active_cam"] = which_cam

        # index 
        if self.path == '/':
            self.redirect("/app/index.html")
        elif self.path == '/index.html':
            self.redirect("/")
        elif self.path == '/index.html?cam1':
            self.redirect("/")
        elif self.path == '/app':
            self.redirect("/app/index.html")
        elif self.path == '/app/':
            self.redirect("/app/index.html")

        # REST API call :  /api/<cmd>/<camera>/param1>/<param2>
        elif self.path.startswith("/api/"):

            logging.info("GET API request with '" + self.path + "'.")
            param = self.path.split("/")
            command = param[2]
            status = "Success"
            version = {}

            if len(param) > 3:
                which_cam = param[3]

            if command == "INDEX":
                content = views.index(server=self)
            elif command == "FAVORITS":
                content = views.favorites(server=self)
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
            content["ip4_address"] = config.param["ip4_address"]
            content["backup_time"] = config.param["backup_time"]
            content["preview_backup"] = config.param["preview_backup"]
            content["rpi_active"] = config.param["rpi_active"]

            cameras = {}
            for key in camera:
                if camera[key].active:
                    cameras[key] = {
                        "name": camera[key].name,
                        "camera_type": camera[key].type,
                        "record": camera[key].record,
                        "image": camera[key].image_size,
                        "stream": "/stream.mjpg?" + key,
                        "streaming_server": camera[key].param["video"]["streaming_server"],
                        "server_port": config.param["port"],
                        "similarity": camera[key].param["similarity"],
                        "status": {
                            "error": camera[key].error,
                            "running": camera[key].running,
                            "img_error": camera[key].error_image,
                            "img_msg": camera[key].error_image_msg
                        }
                    }

            sensor_data = config.param["sensors"]
            for key in sensor_data:
                sensor_data[key]["values"] = {}
                if key in sensor and not sensor[key].error and sensor[key].running:
                    sensor_data[key]["values"] = sensor[key].get_values()
                elif key in sensor:
                    logging.info("Sensor not available: "+key+"/error:"+str(sensor[key].error)+"/run:"+str(sensor[key].running))
                else:
                    logging.info("Sensor not available: "+key)

            micro_data = config.param["microphones"]

            api_response = {
                "STATUS": {
                    "start_time": api_start,
                    "current_time": datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
                    "admin_allowed": self.admin_allowed(),
                    "check-version": version,
                    "api-call": status,
                    "reload": False
                },
                "API": api_description,
                "DATA": content
            }
            api_response["DATA"]["cameras"] = cameras
            api_response["DATA"]["sensors"] = sensor_data
            api_response["DATA"]["microphones"] = micro_data
            api_response["DATA"]["selected"] = which_cam
            api_response["DATA"]["active_page"] = command

            self.stream_file(filetype='application/json', content=json.dumps(api_response).encode(encoding='utf_8'),
                             no_cache=True)

        # extract and show single image
        elif '/image.jpg' in self.path:
            # camera[which_cam].setText = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
            camera[which_cam].writeImage('image_' + which_cam + '.jpg',
                                         camera[which_cam].convertFrame2Image(camera[which_cam].getFrame()))
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
                frame = camera[which_cam].getRawImage()
                frame_raw = frame.copy()

                if self.path.startswith("/detection/"):
                    frame_raw = camera[which_cam].drawRawImageDetectionArea(image=frame_raw)
                    frame = camera[which_cam].convertRawImage2Image(frame_raw)

                else:
                    frame = camera[which_cam].normalizeRawImage(frame)
                    if camera[which_cam].param["image"]["date_time"]:
                        frame = camera[which_cam].setDateTime2RawImage(frame)

                    if camera[which_cam].video.recording:
                        logging.debug("VIDEO RECORDING")
                        length = str(round(camera[which_cam].video.info_recording()["length"]))
                        framerate = str(round(camera[which_cam].video.info_recording()["framerate"]))
                        y_position = camera[which_cam].image_size[1] - 40
                        frame = camera[which_cam].setText2RawImage(frame, "Recording", position=(20, y_position),
                                                                color=(0, 0, 255), scale=1, thickness=2)
                        frame = camera[which_cam].setText2RawImage(frame, "(" + length + "s/" + framerate + "fps)",
                                                                position=(200, y_position), color=(0, 0, 255),
                                                                scale=0.5, thickness=1)

                    if camera[which_cam].video.processing:
                        logging.debug("VIDEO PROCESSING")
                        length = str(round(camera[which_cam].video.info_recording()["length"]))
                        image_size = str(camera[which_cam].video.info_recording()["image_size"])
                        y_position = camera[which_cam].image_size[1] - 40
                        frame = camera[which_cam].setText2RawImage(frame, "Processing", position=(20, y_position),
                                                                color=(0, 255, 255), scale=1, thickness=2)
                        frame = camera[which_cam].setText2RawImage(frame, "(" + length + "s/" + image_size + ")",
                                                                position=(200, y_position), color=(0, 255, 255),
                                                                scale=0.5, thickness=1)

                    frame = camera[which_cam].convertRawImage2Image(frame)

                try:
                    camera[which_cam].wait()
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
            self.stream_file(filetype='image/ico', content=read_image(directory='app-v1', filename=self.path))

        # images, js, css, ...
        elif file_ending in file_types:

            if "/videos" in self.path and "/app-v1" in self.path:
                self.path = self.path.replace("/app-v1", "")
            if "/images" in self.path and "/app-v1" in self.path:
                self.path = self.path.replace("/app-v1", "")

            if "text" in file_types[file_ending]:
                self.stream_file(filetype=file_types[file_ending], content=read_html(directory='', filename=self.path))
            elif "application" in file_types[file_ending]:
                self.stream_file(filetype=file_types[file_ending], content=read_html(directory='', filename=self.path))
            else:
                self.stream_file(filetype=file_types[file_ending],
                                 content=read_image(directory='', filename=self.path))

        # request unknown
        else:
            self.error_404()


if __name__ == "__main__":

    # help
    if len(sys.argv) > 0 and "--logfile" in sys.argv:
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
        logging.basicConfig(format='%(levelname)s: %(message)s',
                            level=logging.INFO)

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

    # start sensors
    sensor = {}
    if "rpi_active" in config.param and config.param["rpi_active"]:
        from server.modules.sensors import BirdhouseSensor

        for sen in config.param["sensors"]:
            settings = config.param["sensors"][sen]
            sensor[sen] = BirdhouseSensor(sensor_id=sen, param=settings, config=config)
            if not sensor[sen].error:
                sensor[sen].start()
    if sensor == {}:
        logging.info("No sensor added.")

    # start cameras
    camera = {}
    for cam in config.param["cameras"]:
        settings = config.param["cameras"][cam]
        camera[cam] = BirdhouseCamera(thread_id=cam, config=config, sensor=sensor)
        camera[cam].start()
        camera[cam].param["path"] = config.param["path"]

    # start views and commands
    views = BirdhouseViews(config=config, camera=camera)
    views.start()
    views.create_archive_list()

    # start backups
    time.sleep(1)
    backup = BirdhouseArchive(config, camera)
    backup.start()
    if len(sys.argv) > 0 and "--backup" in sys.argv:
        backup.backup_files()

    commands = BirdhouseCommands(config=config, camera=camera, backup=backup)
    commands.start()

    # check if config files for main image directory exists and create if not exists
    if not os.path.isfile(config.file("images")):
        for cam in camera:
            camera[cam].pause = True
        logging.info("Create image list for main directory ...")
        backup.compare_files_init()
        for cam in camera:
            camera[cam].pause = False
        logging.info("OK.")
    else:
        test_config = config.read(config="images")
        if test_config == {}:
            logging.info("Create image list for main directory ...")
            backup.compare_files_init()
            logging.info("OK.")

    if not os.path.isfile(config.file("videos")):
        logging.info("Create video list for video directory ...")
        backup.create_video_config()
        logging.info("OK.")
    else:
        test_config = config.read(config="videos")
        if test_config == {}:
            logging.info("Create video list for video directory ...")
            backup.create_video_config()
            logging.info("OK.")

    # Start Webserver
    try:
        address = ('', config.param["port"])
        server = StreamingServer(address, StreamingHandler)
        logging.info("Starting WebServer ...")
        server.serve_forever()
        logging.info("OK.")

    # Stop all processes to stop
    finally:
        config.stop()
        backup.stop()
        for cam in camera:
            if camera[cam].active:
                camera[cam].stop()
        for sen in sensor:
            if sensor[sen].running:
                sensor[sen].stop()
        commands.stop()
        views.stop()

        server.server_close()
        server.shutdown()
        logging.info("Stopped WebServer.")