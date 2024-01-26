import os.path
import time

import numpy as np
import cv2
import psutil
import threading
import subprocess

from datetime import datetime

from modules.presets import *
from modules.bh_class import BirdhouseCameraClass
from modules.image import BirdhouseImageProcessing
from modules.video import BirdhouseVideoProcessing
from modules.object import BirdhouseObjectDetection
from modules.camera_handler import BirdhousePiCameraHandler, BirdhouseCameraHandler, CameraInformation
# https://pyimagesearch.com/2016/01/04/unifying-picamera-and-cv2-videocapture-into-a-single-class-with-opencv/


class BirdhouseCameraStreamRaw(threading.Thread, BirdhouseCameraClass):
    """
    creates a continuous stream while active requests
    """

    def __init__(self, camera_id, config):
        threading.Thread.__init__(self)
        BirdhouseCameraClass.__init__(self, class_id=camera_id+"-sRaw", class_log="cam-stream",
                                      camera_id=camera_id, config=config)

        self.camera = None
        self.image = BirdhouseImageProcessing(camera_id=self.id, config=self.config)
        self.image.resolution = self.param["image"]["resolution"]
        self.active = False

        self.fps = None
        self.fps_max = 12
        self.fps_max_lowres = 3
        self.fps_slow = 2
        self.fps_average = []
        self.duration_max = 1 / self.fps_max
        self.duration_max_lowres = 1 / self.fps_max_lowres
        self.duration_slow = 1 / self.fps_slow

        self.slow_stream = False
        self.maintenance_mode = False

        self._active_streams = 0
        self._recording = False
        self._stream = None
        self._stream_last = None
        self._stream_last_time = None
        self._stream_image_id = 0
        self._timeout = 5

        self._last_activity = 0
        self._last_activity_count = 0
        self._last_activity_per_stream = {}
        self._start_time = None
        self._start_delay_stream = 1
        self._connected = False

    def run(self) -> None:
        """
        create a continuous stream while active; use buffer if empty answer
        """
        circle_in_cache = False
        while not self.if_ready():
            time.sleep(0.1)

        self.reset_error()
        self._connected = True
        self.logging.info("Starting CAMERA raw stream for '"+self.id+"' ...")

        while self._running:
            self._start_time = time.time()

            #if self.maintenance_mode:
            #    pass

            if self.param["active"] \
                    and self.camera is not None and self.camera.if_connected() \
                    and self._last_activity > 0 and self._last_activity + self._timeout > self._start_time:
                try:
                    raw = self.read_from_camera()
                    if raw is None or len(raw) == 0:
                        raise Exception("Error with 'read_from_camera()': empty image.")

                    self.active = True
                    self._stream = raw.copy()
                    self._stream_last = raw.copy()
                    self._stream_last_time = time.time()
                    self._stream_image_id += 1
                    circle_in_cache = False

                except Exception as e:
                    self.raise_error("Error reading RAW stream for '" + self.id + "': " + str(e))
                    if self._stream_last is not None:
                        if not circle_in_cache:
                            try:
                                self._stream_last = self.image.draw_warning_bullet_raw(self._stream_last)
                                circle_in_cache = True
                            except cv2.error as e:
                                self.raise_warning("Could not mark image as 'from cache due to error'.")
                        self._stream = self._stream_last.copy()

            else:
                self.active = False
                self._stream = None
                self._stream_last = None
                self._stream_image_id = 0
                self._last_activity = 0
                self._last_activity_count = 0
                self._last_activity_per_stream = {}

            self.stream_count()
            self.stream_framerate_check()
            self.thread_control()

        self.logging.info("Stopped CAMERA raw stream for '"+self.id+"'.")

    def read_from_camera(self):
        """
        extract image from stream
        """
        raw = self.camera.read("stream_raw")

        if raw is not None and self.param["image"]["rotation"] != 0:
            raw = self.image.rotate_raw(raw, self.param["image"]["rotation"])
        if raw is not None and len(raw) > 0:
            return raw.copy()
        else:
            self.raise_warning("Could not read image from camera.")

    def read_image(self):
        """
        read single raw image (extract from stream, if exists)
        """
        if self.active:
            return self._stream
        else:
            return self.read_from_camera()

    def read_stream(self, stream_id="default", wait=True):
        """
        return stream image considering the max fps
        """
        duration = time.time() - self._last_activity
        self._last_activity = time.time()
        self._last_activity_count += 1
        self._last_activity_per_stream[stream_id] = time.time()

        if wait:
            wait_time = 0
            while self._stream_image_id == 0 and wait_time <= self._timeout:
                time.sleep(0.2)
                wait_time += 0.2

        if self._stream_image_id == 0:
            self.raise_error("sRaw: read_stream: got no image from source '" + self.id + "' yet!")

        return self._stream

    def read_stream_image_id(self):
        """
        return current image id
        """
        return self._stream_image_id

    def get_active_streams(self, stream_id=""):
        """
        return amount of active streams
        """
        if stream_id == "":
            return int(self._active_streams)
        else:
            if stream_id in self._last_activity_per_stream:
                return True
            else:
                return False

    def get_framerate(self):
        """
        return rounded framerate
        """
        if len(self.fps_average) > 0:
            return round(sum(self.fps_average) / len(self.fps_average), 1)
        elif self.fps is not None:
            return round(self.fps, 1)
        else:
            return 0

    def set_framerate(self, fps):
        """
        add framerate to array to calculate average rate -> get_framerate
        """
        self.fps_average.append(fps)
        if len(self.fps_average) > 10:
            self.fps_average.pop(0)

    def set_camera_handler(self, camera_handler):
        """
        set camera handler for internal purposes
        """
        self.camera = camera_handler

    def stream_count(self):
        """
        check active streams and delete old ones
        """
        old_streams_to_delete = []
        for stream_id in self._last_activity_per_stream:
            if self._last_activity_per_stream[stream_id] + self._timeout < self._start_time:
                old_streams_to_delete.append(stream_id)
        for stream_id in old_streams_to_delete:
            if stream_id in self._last_activity_per_stream:
                del self._last_activity_per_stream[stream_id]
        self._active_streams = len(self._last_activity_per_stream.keys())

    def stream_framerate_check(self):
        """
        calculate framerate and ensure max. framerate
        """
        duration = time.time() - self._start_time
        duration_max = self.duration_max

        if self.slow_stream:
            duration_max = self.duration_slow

        if duration < duration_max:
            time.sleep(duration_max - duration)

        duration = time.time() - self._start_time
        if self.active:
            self.fps = 1 / duration
            self.set_framerate(self.fps)
        else:
            self.fps = 0

    def slow_down(self, slow_down=True):
        """
        slow down streaming framerate
        """
        self.slow_stream = slow_down

    def if_ready(self):
        """
        check if stream is ready to deliver images, connection to camera exists
        """
        if self.camera is None:
            return False
        elif not self.camera.if_connected() or not self.param["active"]:
            return False
        else:
            return True

    def if_connected(self):
        return self._connected

    def kill(self, stream_id="default"):
        """
        kill continuous stream creation
        """
        if stream_id == "default":
            self._last_activity = 0
            self.camera = None

        if stream_id in self._last_activity_per_stream:
            self.logging.info(".... killing stream: " + str(stream_id))
            del self._last_activity_per_stream[stream_id]

        self.logging.debug(".... active "+str(list(self._last_activity_per_stream.keys())))

    def stop(self):
        """
        stop basic stream
        """
        self._running = False


class BirdhouseCameraStreamEdit(threading.Thread, BirdhouseCameraClass):
    """
    creates a continuous stream while active requests
    """

    def __init__(self, camera_id, config, stream_raw, stream_type, stream_resolution):
        threading.Thread.__init__(self)
        BirdhouseCameraClass.__init__(self, class_id=camera_id+"-sEdit", class_log="cam-stream",
                                      camera_id=camera_id, config=config)

        self.type = stream_type
        self.type_available = ["raw", "normalized", "camera", "setting"]
        self.resolution = stream_resolution
        self.resolution_available = ["lowres", "hires"]
        self.active = False

        if self.type not in self.type_available:
            self.raise_error("Could not initialize: " + self.type + " not available (" + str(self.type_available) + ")")
            self.stop()
            return

        if self.resolution not in self.resolution_available:
            self.raise_error("Could not initialize: " + self.resolution + " not available (" +
                             str(self.resolution_available) + ")")
            self.stop()
            return

        self.stream_raw = stream_raw
        self.image = self.stream_raw.image

        self.img_error_files = {
            "setting": "camera_error_settings.jpg",
            "camera": "camera_error_hires.jpg",
            "lowres": "camera_error_lowres.png"
            }
        self.img_error_raw = {
            "setting": None,
            "lowres": None,
            "camera": None
            }

        self._active_streams = 0
        self._recording = False
        self._timeout = 6
        self._last_activity = 0
        self._last_activity_count = 0
        self._last_activity_per_stream = {}
        self._start_time = 0
        self._stream = None
        self._stream_last = None
        self._stream_last_id = None
        self._stream_last_time = 0
        self._stream_id_base = self.type + "_" + self.resolution + "_"
        self._stream_image_id = 0
        self._size_lowres = None
        self._start_delay_stream = 2
        self._error_wait = True
        self._connected = False

        self.fps = None
        self.fps_max = 12
        self.fps_max_lowres = 3
        self.fps_slow = 2
        self.fps_object_detection = None
        if self.resolution == "lowres":
            self.fps_max = self.fps_max_lowres
        self.duration_max = 1 / (self.fps_max + 1)
        self.duration_slow = 1 / self.fps_slow
        self.slow_stream = False
        self.system_status = {
            "active": False,
            "color": "default",
            "line1": "",
            "line2": ""
        }
        self.maintenance_mode = False
        self.reload_time = 0
        self.reload_tried = 0
        self.reload_success = 0
        self.initial_connect_msg = {}

        self._init_error_images()

    def _init_error_images(self):
        """
        create error images for settings and camera
        """
        if "resolution_current" in self.param["image"]:
            resolution = self.param["image"]["resolution_current"]
        elif self.param["image"]["resolution"] and "x" in self.param["image"]["resolution"]:
            resolution = self.param["image"]["resolution"].split("x")
        else:
            resolution = [800, 600]
        area = (0, 0, int(resolution[0]), int(resolution[1]))

        try:
            for image in self.img_error_files:
                filename = os.path.join(self.config.main_directory, self.config.directories["data"],
                                        self.img_error_files[image])
                if not os.path.exists(filename):
                    raise Exception("File '" + filename + "' not found.")

                raw = birdhouse_error_images_raw[image].copy()
                raw, area = self.image.crop_raw(raw=raw, crop_area=area, crop_type="absolute")
                self.img_error_raw[image] = raw.copy()
            return True

        except Exception as e:
            self.raise_error("Error reading images: " + str(e))
            return False

    def run(self) -> None:
        self.reset_error()
        while not self.stream_raw.if_connected():
            time.sleep(0.1)

        self._connected = True
        self.logging.info("Starting CAMERA edited stream for '"+self.id+"/"+self.type+"/"+self.resolution+"' ...")
        while self._running:
            self._start_time = time.time()

            if self.maintenance_mode:
                raw = self.read_maintenance_image()
                self._stream = raw.copy()
                self._stream_last = raw.copy()
                self._stream_image_id += 1
                self._stream_last_time = time.time()
                time.sleep(1)

            elif self.active and self.stream_raw is not None \
                    and self._last_activity > 0 and self._last_activity + self._timeout > self._start_time:
                try:
                    raw = self.read_raw_and_edit(stream=True, stream_id=self._stream_id_base, return_error_image=True)
                    if raw is None or len(raw) == 0:
                        raise Exception("Error with 'read_raw_and_edit()': empty image.")

                    self._stream = raw.copy()
                    self._stream_last = raw.copy()
                    self._stream_image_id += 1
                    self._stream_last_time = time.time()

                except Exception as e:
                    self.raise_error("Error reading EDIT stream for '" + self.id + "/" + self.type + "': " + str(e))

            else:
                self._stream = None
                self._last_activity = 0
                self._last_activity_count = 0
                self._last_activity_per_stream = {}
                self._stream_image_id += 0
                self._error_wait = True

            self.stream_count()
            self.stream_framerate_check()
            self.thread_control()

        self.logging.info("Stopped CAMERA edited stream for '"+self.id+"/"+self.type+"/"+self.resolution+"'.")

    def read_raw_and_edit(self, stream=False, stream_id="default", return_error_image=True):
        """
        read image from raw stream and edit depending on streaming type and resolution
        """
        if self.maintenance_mode:
            raw = self.img_error_raw["camera"].copy()
            if self.type == "camera":
                raw = self.edit_crop_area(raw, start_zero=True)
            if self.resolution != "lowres":
                raw = self.edit_add_system_info(raw)

            if raw is not None:
                return raw.copy()
            else:
                return raw

        if stream:
            raw = self.stream_raw.read_stream(self._stream_id_base + stream_id, self._error_wait)
            raw = self.edit_check_error(raw, "Error reading 'self.stream_raw.read_stream()' in read_raw_and_edit()",
                                        return_error_image)
        else:
            raw = self.stream_raw.read_image()
            raw = self.edit_check_error(raw, "Error reading 'self.stream_raw.read_image()' in read_raw_and_edit()",
                                        return_error_image)

        if self.type == "raw":
            if self.resolution == "lowres":
                raw = self.edit_create_lowres(raw)
                raw = self.edit_check_error(raw, "Error reading 'self.stream_raw.edit_create_lowres(raw)' " +
                                            "in read_raw_and_edit()", return_error_image)
            if raw is not None:
                return raw.copy()
            else:
                return raw

        elif self.type == "normalized":
            normalized = self.edit_normalize(raw)
            normalized = self.edit_check_error(normalized, "Error reading 'self.stream_raw.edit_normalize" +
                                               "(raw)' in read_raw_and_edit()", return_error_image)
            if self.resolution == "lowres":
                normalized = self.edit_create_lowres(normalized)
                normalized = self.edit_check_error(normalized, "Error reading 'self.stream_raw.edit_create_lowres" +
                                                   "(normalized)' in read_raw_and_edit()", return_error_image)

            if normalized is not None:
                return normalized.copy()
            else:
                return normalized

        elif self.type == "camera":
            normalized = self.edit_normalize(raw)
            normalized = self.edit_check_error(normalized, "Error reading 'self.stream_raw.edit_normalize" +
                                               "(raw)' in read_raw_and_edit()", return_error_image)
            camera = self.edit_crop_area(normalized)
            camera = self.edit_check_error(camera, "Error reading 'self.stream_raw.edit_crop_area" +
                                           "(camera)' in read_raw_and_edit()", return_error_image)
            if self.resolution != "lowres":
                camera = self.edit_add_datetime(camera)
                camera = self.edit_add_framerate(camera)
                camera = self.edit_check_error(camera, "Error reading 'self.stream_raw.edit_add_*text" +
                                               "(camera)' in read_raw_and_edit()", return_error_image)
            if self.resolution == "lowres":
                camera = self.edit_create_lowres(camera)
                camera = self.edit_check_error(camera, "Error reading 'self.stream_raw.edit_create_lowres" +
                                               "(camera)' in read_raw_and_edit()", return_error_image)
            if camera is not None:
                return camera.copy()
            else:
                return camera

        elif self.type == "setting":
            normalized = self.edit_normalize(raw)
            normalized = self.edit_check_error(normalized, "Error reading 'self.stream_raw.edit_normalize" +
                                               "(raw)' in read_raw_and_edit()", return_error_image)
            setting = self.edit_add_areas(normalized)
            setting = self.edit_check_error(setting, "Error reading 'self.stream_raw.edit_add_areas" +
                                            "(setting)' in read_raw_and_edit()", return_error_image)
            if self.resolution != "lowres":
                setting = self.edit_add_datetime(setting)
                setting = self.edit_add_framerate(setting)
                setting = self.edit_check_error(setting, "Error reading 'self.stream_raw.edit_add_*text" +
                                                "(setting)' in read_raw_and_edit()", return_error_image)
            if self.resolution == "lowres":
                setting = self.edit_create_lowres(setting)
                setting = self.edit_check_error(setting, "Error reading 'self.stream_raw.edit_create_lowres" +
                                                "(setting)' in read_raw_and_edit()", return_error_image)
            if setting is not None:
                return setting.copy()
            else:
                return setting

    def read_image(self, return_error_image=True):
        """
        read single image from stream
        """
        return self.read_raw_and_edit(stream=False, stream_id="default", return_error_image=return_error_image)

    def read_stream(self, stream_id, system_info=False, wait=True):
        """
        read stream image considering the max fps
        """
        if not wait:
            self._error_wait = False

        duration = time.time() - self._last_activity
        self._last_activity = time.time()
        self._last_activity_count += 1
        self._last_activity_per_stream[stream_id] = time.time()

        if wait:
            wait_time = 0
            while self._stream_image_id == 0 and wait_time <= self._timeout:
                time.sleep(1)
                wait_time += 1
            if self._stream_image_id == 0:
                self.logging.debug("WAIT .... !!!")

        if self._stream_image_id == 0:
            self.raise_error("sEdit: read_stream: got no image from raw stream '" + self.id + "' yet!")

        if self._stream is not None and len(self._stream) > 0:
            stream_img = self._stream.copy()
            if system_info:
                stream_img = self.edit_add_system_info(stream_img)
            return stream_img
        else:
            return

    def read_stream_image_id(self):
        """
        return current image number
        """
        return self.stream_raw.read_stream_image_id()

    def read_error_image(self, error_msg="", error_trigger=""):
        """
        return error image, depending on settings
        """
        if error_msg == "":
            error_msg = self.if_error(message=True)
            if len(error_msg) == 0:
                error_msg = "no error :-)"
            else:
                error_msg = error_msg[-1]

        if self.type == "setting":
            image = self.img_error_raw["setting"]
            image = self.edit_error_add_info(image, [error_msg], reload_time=0, info_type="setting",
                                             error_trigger=error_trigger)
        elif self.resolution == "lowres":
            image = self.img_error_raw["lowres"]
            image = self.edit_create_lowres(image)
            image = self.edit_error_add_info(image, error_msg, reload_time=0, info_type="lowres",
                                             error_trigger=error_trigger)
        else:
            image = self.img_error_raw["camera"]
            image = self.edit_error_add_info(image, error_msg, reload_time=0, info_type="camera",
                                             error_trigger=error_trigger)

        if image is None:
            for err_img in self.img_error_raw:
                self.logging.error(".... " + self.resolution + " - " + str(error_msg) + " - " +
                                   str(type(self.img_error_raw[err_img])))
        else:
            return image.copy()

    def edit_error_add_info(self, raw, error_msg, reload_time=0, info_type="empty", error_trigger=""):
        """
        edit information to error image
        """
        if raw is None or len(raw) == 0:
            self.logging.error("edit_error_add_info: empty image")
            return raw

        font_scale_headline = 1
        font_scale_text = 0.5
        font_color = (0, 0, 255)
        line_scale = 8

        #raw = raw.copy()
        lowres_position = self.config.param["views"]["index"]["lowres_position"]

        if info_type == "setting":
            line_position = 160

            msg = self.id + ": " + self.param["name"]
            raw = self.image.draw_text_raw(raw=raw, text=msg, position=(20, line_position), font=None,
                                           scale=font_scale_headline, color=font_color, thickness=2)

            if self.param["active"]:
                line_position += 4 * line_scale
                source = self.param["source"]
                if source == "":
                    source = "!!! not set !!!"
                msg = "Device: active=" + str(self.param["active"]) + \
                      ", source=" + str(source) + ", resolution=" + self.param["image"]["resolution"]
                raw = self.image.draw_text_raw(raw=raw, text=msg, position=(20, line_position), font=None,
                                               scale=font_scale_text, color=font_color, thickness=1)
                self.logging.debug(str(self.initial_connect_msg) + ".............")

                if source in self.initial_connect_msg:
                    line_position += 3 * line_scale
                    msg = self.initial_connect_msg[source]
                    raw = self.image.draw_text_raw(raw=raw, text=msg, position=(85, line_position),
                                                   font=None, scale=font_scale_text, color=font_color, thickness=1)
                line_position += 1 * line_scale

                if error_trigger != "":
                    line_position += 3 * line_scale
                    msg = "Error Trigger: " + error_trigger
                    raw = self.image.draw_text_raw(raw=raw, text=msg, position=(20, line_position), font=None,
                                                   scale=font_scale_text, color=font_color, thickness=1)

                if self.stream_raw.camera is None:
                    line_position += 3 * line_scale
                    msg = "Error Camera: Not yet connected!"
                    raw = self.image.draw_text_raw(raw=raw, text=msg, position=(20, line_position), font=None,
                                                   scale=font_scale_text, color=font_color, thickness=1)

                elif len(self.stream_raw.camera.error_msg) > 0:
                    line_position += 3 * line_scale
                    msg = "Error Camera: " + self.stream_raw.camera.error_msg[-1] + \
                          " [#" + str(len(self.stream_raw.camera.error_msg)) + "]"
                    raw = self.image.draw_text_raw(raw=raw, text=msg, position=(20, line_position), font=None,
                                                   scale=font_scale_text, color=font_color, thickness=1)

                if len(self.stream_raw.error_msg) > 0:
                    line_position += 3 * line_scale
                    msg = "Error Raw-Stream: " + self.stream_raw.error_msg[-1] + \
                          " [#" + str(len(self.stream_raw.error_msg)) + "]"
                    raw = self.image.draw_text_raw(raw=raw, text=msg, position=(20, line_position), font=None,
                                                   scale=font_scale_text, color=font_color, thickness=1)

                if len(self.error_msg) > 0:
                    line_position += 3 * line_scale
                    msg = "Error Edit-Stream: " + self.error_msg[-1] + " [#" + str(len(self.error_msg)) + "]"
                    raw = self.image.draw_text_raw(raw=raw, text=msg, position=(20, line_position), font=None,
                                                   scale=font_scale_text, color=font_color, thickness=1)

                line_position += 4 * line_scale
                msg = "Last tried reconnect: " + str(round(time.time() - self.reload_tried)) + "s "
                raw = self.image.draw_text_raw(raw=raw, text=msg, position=(20, line_position), font=None,
                                               scale=font_scale_text, color=font_color, thickness=1)

                line_position += 3 * line_scale
                reload_success = round(time.time() - self.reload_success)
                if reload_success > 1000000000:
                    msg = "Last successful reconnect: not since server started!"
                else:
                    msg = "Last successful reconnect: " + str(reload_success) + "s"
                raw = self.image.draw_text_raw(raw=raw, text=msg, position=(20, line_position), font=None,
                                               scale=font_scale_text, color=font_color, thickness=1)

            else:
                line_position += 4 * line_scale
                msg = "Device '"+self.id+"' is not activated, change settings."
                raw = self.image.draw_text_raw(raw=raw, text=msg, position=(20, line_position), font=None,
                                               scale=font_scale_text, color=font_color, thickness=1)

            details = True
            if details:
                line_position += 4 * line_scale
                msg = "CPU Usage: " + str(psutil.cpu_percent(interval=1, percpu=False)) + "% "
                msg += "(" + str(psutil.cpu_count()) + " CPU)"
                raw = self.image.draw_text_raw(raw=raw, text=msg, position=(20, line_position), font=None,
                                               scale=font_scale_text, color=font_color, thickness=1)

                line_position += 3 * line_scale
                total = psutil.virtual_memory().total
                total = round(total / 1024 / 1024)
                used = psutil.virtual_memory().used
                used = round(used / 1024 / 1024)
                percentage = psutil.virtual_memory().percent
                msg = "Memory: total=" + str(total) + "MB, used=" + str(used) + "MB (" + str(percentage) + "%)"
                raw = self.image.draw_text_raw(raw=raw, text=msg, position=(20, line_position), font=None,
                                               scale=font_scale_text, color=font_color, thickness=1)

            line_position += 4 * line_scale
            raw = self.image.draw_date_raw(raw=raw, overwrite_color=font_color, overwrite_position=(20, line_position))

        elif info_type == "camera":
            if int(lowres_position) != 1:
                line_position = 40
            else:
                line_position = -70

            raw = self.image.draw_text_raw(raw=raw, text=self.id.upper() + ": " + self.param["name"],
                                           position=(20, line_position), color=(255, 255, 255), thickness=2)
            raw = self.image.draw_date_raw(raw=raw, overwrite_color=(255, 255, 255),
                                           overwrite_position=(20, line_position + 30))

        return raw

    def read_maintenance_image(self, error_msg=""):
        """
        return error image, depending on settings
        """
        if error_msg == "":
            error_msg = self.if_error(message=True)
            if len(error_msg) == 0:
                error_msg = "no error :-)"
            else:
                error_msg = error_msg[-1]

        if self.type == "setting":
            image = self.img_error_raw["setting"]
            image = self.edit_maintenance_add_info(image, [error_msg], reload_time=0, info_type="setting")
        elif self.resolution == "lowres":
            image = self.img_error_raw["lowres"]
            image = self.edit_create_lowres(image)
            image = self.edit_maintenance_add_info(image, error_msg, reload_time=0, info_type="lowres")
        else:
            image = self.img_error_raw["camera"]
            image = self.edit_maintenance_add_info(image, error_msg, reload_time=0, info_type="camera")

        if image is None:
            for err_img in self.img_error_raw:
                self.logging.error(".... " + self.resolution + " - " + str(error_msg) + " - " +
                                   str(type(self.img_error_raw[err_img])))
        else:
            return image.copy()

    def edit_maintenance_add_info(self, raw, error_msg, reload_time=0, info_type="empty"):
        """
        edit information to error image
        """
        if raw is None or len(raw) == 0:
            self.logging.error("edit_error_add_info: empty image")
            return raw

        font_scale_headline = 1
        font_scale_text = 0.5
        font_color = (255, 0, 0)
        line_scale = 8

        #raw = raw.copy()
        lowres_position = self.config.param["views"]["index"]["lowres_position"]

        if info_type == "setting":
            line_position = 160

            msg = self.id + ": " + self.param["name"]
            raw = self.image.draw_text_raw(raw=raw, text=msg, position=(20, line_position), font=None,
                                           scale=font_scale_headline, color=font_color, thickness=2)

            line_position += 4 * line_scale
            msg = "Camera is in maintenance mode at the moment and will restart shortly..."
            raw = self.image.draw_text_raw(raw=raw, text=msg, position=(85, line_position),
                                           font=None, scale=font_scale_text, color=font_color, thickness=1)

        elif info_type == "camera":
            if int(lowres_position) != 1:
                line_position = 40
            else:
                line_position = -70

            raw = self.image.draw_text_raw(raw=raw, text=self.id.upper() + ": " + self.param["name"] + " / " +
                                           "Maintenance Mode",
                                           position=(20, line_position), color=(255, 255, 255), thickness=2)
            raw = self.image.draw_date_raw(raw=raw, overwrite_color=(255, 255, 255),
                                           overwrite_position=(20, line_position + 30))

        return raw

    def edit_normalize(self, raw):
        """
        create normalized image
        """
        if "black_white" in self.param["image"] and self.param["image"]["black_white"] is True:
            normalized = self.image.convert_to_gray_raw(raw)
            normalized = self.image.convert_from_gray_raw(normalized)
            return normalized.copy()
        elif raw is not None:
            return raw.copy()

    def edit_crop_area(self, raw, start_zero=False):
        """
        crop image to area defined in the settings
        """
        if raw is None or len(raw) == 0:
            return raw

        crop_area = self.param["image"]["crop"]
        if start_zero:
            crop_area = [0, 0, crop_area[2]-crop_area[0], crop_area[3]-crop_area[1]]
        cropped, area = self.image.crop_raw(raw=raw, crop_area=crop_area, crop_type="relative")
        self.param["image"]["crop_area"] = area
        self.param["image"]["resolution_cropped"] = [area[2] - area[0], area[3] - area[1]]
        if cropped is not None:
            return cropped.copy()
        elif raw is not None:
            return raw.copy()
        else:
            return raw

    def edit_create_lowres(self, raw):
        """
        scale image to create lowres
        """
        if self._size_lowres is None:
            self._size_lowres = self.image.size_raw(raw=raw, scale_percent=self.param["image"]["preview_scale"])
        lowres = self.image.resize_raw(raw=raw, scale_percent=100, scale_size=self._size_lowres)

        if lowres is not None:
            return lowres.copy()
        else:
            return lowres

    def edit_add_areas(self, raw):
        """
        Draw a red rectangle into the image to show detection area / and a yellow to show the crop area
        """
        if raw is None:
            return raw

        color_detect = (0, 255, 255)
        color_crop = (0, 0, 255)
        frame_thickness = 4

        self.logging.debug("-----------------" + self.id + "------- show area")
        outer_area = self.param["image"]["crop"]
        inner_area = self.param["similarity"]["detection_area"]
        area_image = self.image.draw_area_raw(raw=raw, area=outer_area, color=color_crop, thickness=frame_thickness)

        w_start = outer_area[0] + ((outer_area[2] - outer_area[0]) * inner_area[0])
        h_start = outer_area[1] + ((outer_area[3] - outer_area[1]) * inner_area[1])
        w_end = outer_area[2] - ((outer_area[2] - outer_area[0]) * (1 - inner_area[2]))
        h_end = outer_area[3] - ((outer_area[3] - outer_area[1]) * (1 - inner_area[3]))

        inner_area = (w_start, h_start, w_end, h_end)
        area_image = self.image.draw_area_raw(raw=area_image, area=inner_area, color=color_detect, thickness=frame_thickness)
        return area_image.copy()

    def edit_check_error(self, image, error_message="", return_error_image=True):
        """
        check: if error then show error image
        """
        if return_error_image:
            check = str(type(image))
            if "NoneType" in check or len(image) == 0:
                self.raise_error("edit_check_error:  " + error_message)
            else:
                return image
        else:
            return image

    def edit_add_datetime(self, raw):
        """
        add date and time
        """
        if raw is None or len(raw) <= 0:
            self.logging.error("edit_add_datetime: empty image")
            return raw

        offset = None
        if self.type == "setting":
            offset = self.param["image"]["crop_area"]
        if self.param["image"]["date_time"] and self.resolution != "lowres":
            raw = self.image.draw_date_raw(raw, offset=offset)

        return raw.copy()

    def edit_add_framerate(self, raw):
        """
        add framerate into the image (bottom left)
        """
        if raw is None or len(raw) <= 0:
            self.logging.error("edit_add_framerate: empty image")
            return raw

        if "show_framerate" in self.param["image"] and self.param["image"]["show_framerate"] \
                and self.resolution != "lowres":
            framerate = round(self.stream_raw.fps, 1)
            if self.fps and framerate and self.fps < framerate:
                framerate = self.fps
            if framerate:
                raw = self.image.draw_text_raw(raw=raw, text=str(round(framerate, 1)) + "fps",
                                               font=cv2.QT_FONT_NORMAL,
                                               position=(10, -20), scale=0.4, thickness=1)
        return raw.copy()

    def edit_add_system_info(self, raw):
        """
        add information if recording or processing to image
        """
        if raw is None or len(raw) <= 0:
            self.logging.error("edit_add_system_info: empty image")
            return raw

        image = raw.copy()

        if self.system_status["active"]:
            lowres_position = self.config.param["views"]["index"]["lowres_position"]
            size = self.config.param["devices"]["cameras"][self.id]["image"]["resolution_cropped"]
            self.logging.debug("...... " + self.name + " " + str(size))

            [width, height] = [float(size[0]), float(size[1])]
            if int(lowres_position) != 3:
                pos_line1 = (15, -70)
                pos_line2 = (15, -50)
                size = [0.0, height-105.0, 400.0, height-35.0]
            else:
                pos_line1 = (-385, -70)
                pos_line2 = (-385, -50)
                size = [width-400.0, height-105.0, width, height-35.0]

            self.logging.debug(".............. " + str(size))
            [x1, y1, x2, y2] = map(int, size)

            cv2.rectangle(image, (x1, y1), (x2, y2), (130, 130, 130), -1)
            cv2.rectangle(image, (x1, y1), (x2, y2), (230, 230, 230), 1)
            image = self.image.draw_text_raw(raw=image, text=self.system_status["line1"],
                                             font=cv2.QT_FONT_NORMAL, color=self.system_status["color"],
                                             position=pos_line1, scale=1, thickness=2)
            image = self.image.draw_text_raw(raw=image, text=self.system_status["line2"],
                                             font=cv2.QT_FONT_NORMAL, color=self.system_status["color"],
                                             position=pos_line2, scale=0.4, thickness=1)
        return image.copy()

    def stream_count(self):
        """
        check active streams and delete old ones
        """
        old_streams_to_delete = []
        for stream_id in self._last_activity_per_stream:
            if self._last_activity_per_stream[stream_id] + self._timeout < self._start_time:
                old_streams_to_delete.append(stream_id)
        for stream_id in old_streams_to_delete:
            if stream_id in self._last_activity_per_stream:
                del self._last_activity_per_stream[stream_id]
        self._active_streams = len(self._last_activity_per_stream.keys())

    def stream_framerate_check(self):
        """
        calculate framerate and ensure max. framerate
        """
        duration = time.time() - self._start_time
        duration_max = self.duration_max

        if self.slow_stream:
            duration_max = self.duration_slow

        if duration < duration_max:
            time.sleep(duration_max - duration)

        duration = time.time() - self._start_time
        if self.active:
            self.fps = 1 / duration
        else:
            self.fps = 0

    def get_active_streams(self, stream_id=""):
        """
        return amount of active streams
        """
        if stream_id == "":
            return int(self._active_streams)
        else:
            if stream_id in self._last_activity_per_stream:
                return True
            else:
                return False

    def slow_down(self, slow_down=True):
        """
        slow down streaming framerate
        """
        self.slow_stream = slow_down

    def set_maintenance_mode(self, active, line1="", line2="", silent=False):
        """
        set maintenance mode -> image plus text, no streaming image (e.g. for camera restart)
        """
        maintenance_color = (0, 0, 0)
        if active and not silent:
            self.logging.info("Start maintenance mode for '"+self.id+"/"+self.type+"/"+self.resolution+"' (" +
                              line1 + ") ... ")
        self.maintenance_mode = active
        self.stream_raw.maintenance_mode = active
        self.set_system_info(active, line1, line2, color=maintenance_color)
        if not active:
            self.reset_error()
            if not silent:
                self.logging.info("Stopped maintenance mode for '"+self.id+"/"+self.type+"/"+self.resolution+"'.")

    def set_system_info(self, active, line1="", line2="", color=None):
        """
        format message -> added via edit_add_system_info
        """
        default_color = (0, 0, 255)
        self.system_status = {
            "active": active,
            "line1": line1,
            "line2": line2,
            "color": color,
        }
        if color is None:
            self.system_status["color"] = default_color

    def kill(self):
        self._last_activity = 0

    def stop(self):
        self._running = False

    def if_connected(self):
        return self._connected


class BirdhouseCamera(threading.Thread, BirdhouseCameraClass):

    def __init__(self, camera_id, config, sensor, microphones, first_cam=False):
        """
        Create instance of this class and set initial parameters
        """
        threading.Thread.__init__(self)
        BirdhouseCameraClass.__init__(self, class_id=camera_id + "-main", class_log="cam-main",
                                      camera_id=camera_id, config=config)

        self.config_cache = {}
        self.config_cache_size = 5
        self.config_update = None
        self.config.update["camera_" + self.id] = False

        self.name = self.param["name"]
        self.active = self.param["active"]
        self.source = self.param["source"]
        self.type = self.param["type"]

        self.image = None
        self.video = None
        self.camera = None
        self.object = None

        self.cam_param = None
        self.cam_param_image = None
        self.sensor = sensor
        self.microphones = microphones
        self.micro = None
        self.weather_active = self.config.param["weather"]["active"]
        self.weather_sunrise = None
        self.weather_sunset = None

        self.detect_objects = None
        self.detect_birds = None
        self.detect_visualize = None
        self.detect_live = False
        self.detect_settings = self.param["object_detection"]
        self.detect_active = birdhouse_env["detection_active"]
        self.detect_fps = None
        self.detect_fps_last = {}
        self.detect_frame_last = None
        self.detect_frame_id_last = None
        self.first_cam = first_cam
        self.initialized = False

        self._interval = 0.2
        self._interval_reload_if_error = 60*3
        self._stream_errors_max_accepted = 25
        self._stream_errors_restart = False
        self._stream_errors = 0

        self.error_reload_time = 60
        self.error_no_reconnect = False

        self.reload_camera = False
        self.reload_time = 0
        self.reload_tried = 0
        self.reload_success = 0

        self.image_size = [0, 0]
        self.image_size_lowres = [0, 0]
        self.image_last_raw = None
        self.image_last_raw_time = 0
        self.image_last_id = 0
        self.image_last_edited = None
        self.image_last_edited_lowres = None
        self.image_last_size_lowres = None
        self.image_count_empty = 0
        self.image_time_last = {}
        self.image_time_current = {}
        self.image_time_rotate = {}
        self.image_fps = {}
        self.image_streams = {}
        self.image_streams_to_kill = {}
        self.image_to_select_last = "xxxxxx"
        self.image_size_object_detection = self.detect_settings["detection_size"]
        self.max_resolution = None

        self.previous_image = None
        self.previous_stamp = "000000"

        self.record = self.param["record"]
        self.record_seconds = []
        self.record_image_last = time.time()
        self.record_image_reload = time.time()
        self.record_image_last_string = ""
        self.record_image_last_compare = ""
        self.record_image_start = ""
        self.record_image_end = ""
        self.record_image_error = False
        self.record_image_error_msg = []
        self.record_temp_threshold = None
        self.recording = False

        self.camera_stream_raw = None
        self.camera_streams = {}
        self.available_devices = {}

        self.date_last = self.config.local_time().strftime("%Y-%m-%d")
        self.usage_time = time.time()
        self.usage_interval = 60
        self.initial_connect_msg = {}
        self.maintenance_mode = False

        self.camera_scan = {}
        self.camera_info = CameraInformation()
        if first_cam:
            self.camera_scan = self.get_available_devices()

        self.connect()

    def _init_image_processing(self):
        """
        start image processing
        """
        self.image = BirdhouseImageProcessing(camera_id=self.id, config=self.config)
        self.image.resolution = self.param["image"]["resolution"]

    def _init_video_processing(self):
        """
        start or restart video processing
        """

        if self.video is not None and self.video.if_running():
            self.video.stop()
            time.sleep(1)

        self.video = BirdhouseVideoProcessing(camera_id=self.id, camera=self, config=self.config)

        if not self.error and self.param["video"]["allow_recording"]:
            self.camera_enable_recording()

    def _init_stream_raw(self):
        """
        start or restart video processing
        """
        if self.camera_stream_raw is not None and self.camera_stream_raw.if_running():
            self.camera_stream_raw.kill()
            self.camera_stream_raw.stop()
            time.sleep(1)

        self.camera_stream_raw = BirdhouseCameraStreamRaw(camera_id=self.id, config=self.config)
        self.camera_stream_raw.start()

    def _init_streams(self):
        """
        init streams
        """
        available_streams = ["raw", "normalized_hires", "normalized_lowres", "camera_hires", "camera_lowres",
                             "setting_hires", "setting_lowres"]

        count = 0
        while self.camera_stream_raw is None or not self.camera_stream_raw.if_running():
            time.sleep(1)
            count += 1
            if count > 9:
                self.raise_error("Could not start video streaming!")
                return

        count = 0
        for stream in available_streams:
            if stream in self.camera_streams:
                if self.camera_streams[stream].if_running():
                    count += 1
                    self.camera_streams[stream].kill()
                    self.camera_streams[stream].stop()
            if count > 0:
                time.sleep(1)

        self.camera_streams = {
            "raw": BirdhouseCameraStreamEdit(camera_id=self.id, config=self.config,
                                             stream_raw=self.camera_stream_raw,
                                             stream_type="raw", stream_resolution="hires"),
            "normalized_hires": BirdhouseCameraStreamEdit(camera_id=self.id, config=self.config,
                                                          stream_raw=self.camera_stream_raw,
                                                          stream_type="normalized", stream_resolution="hires"),
            "normalized_lowres": BirdhouseCameraStreamEdit(camera_id=self.id, config=self.config,
                                                           stream_raw=self.camera_stream_raw,
                                                           stream_type="normalized", stream_resolution="lowres"),
            "camera_hires": BirdhouseCameraStreamEdit(camera_id=self.id, config=self.config,
                                                      stream_raw=self.camera_stream_raw,
                                                      stream_type="camera", stream_resolution="hires"),
            "camera_lowres": BirdhouseCameraStreamEdit(camera_id=self.id, config=self.config,
                                                       stream_raw=self.camera_stream_raw,
                                                       stream_type="camera", stream_resolution="lowres"),
            "setting_hires": BirdhouseCameraStreamEdit(camera_id=self.id, config=self.config,
                                                       stream_raw=self.camera_stream_raw,
                                                       stream_type="setting", stream_resolution="hires"),
            "setting_lowres": BirdhouseCameraStreamEdit(camera_id=self.id, config=self.config,
                                                        stream_raw=self.camera_stream_raw,
                                                        stream_type="setting", stream_resolution="lowres")
        }
        for stream in self.camera_streams:
            self.camera_streams[stream].start()
            self.camera_streams[stream].reload_success = self.reload_success
            self.camera_streams[stream].reload_tried = self.reload_tried
            self.camera_streams[stream].reload_time = self.reload_time
            self.camera_streams[stream].initial_connect_msg = birdhouse_initial_connect_msg

    def _init_camera(self, init=False):
        """
        Try out new
        """
        self.reload_time = time.time()

        if not init:
            self.set_maintenance_mode(True, "Restarting camera", self.id)
            self.logging.info("Restarting CAMERA (" + self.id + ":" + self.source + ") ...")
            time.sleep(1)
        else:
            self.set_maintenance_mode(True, "Starting camera", self.id)
            self.logging.info("Starting CAMERA (" + self.id + ":" + self.source + ") ...")

        self.reset_error_all()
        if init:
            if self.camera is not None:
                self.camera.disconnect()
            if "/dev/picam" in self.source:
                self.camera = BirdhousePiCameraHandler(camera_id=self.id, source=self.source, config=self.config)
            else:
                self.camera = BirdhouseCameraHandler(camera_id=self.id, source=self.source, config=self.config)
            self.connected = self.camera.connect()
        else:
            self.connected = self.camera.reconnect()

        self.reload_tried = time.time()
        if self.connected:
            self.camera_stream_raw.set_camera_handler(self.camera)
            self.reload_success = time.time()
            self.record_image_reload = time.time()

            self._init_camera_settings()
            self.camera_stream_raw.set_camera_handler(self.camera)
            self.reset_error_all()
        else:
            self.raise_error("Could not connect camera, check error msg of camera handler.")

        if not init:
            self.logging.error(" ........ " + str(self.camera_streams.keys()))

        self.set_maintenance_mode(False)
        for stream in self.camera_streams:
            self.camera_streams[stream].reload_success = self.reload_success
            self.camera_streams[stream].reload_tried = self.reload_tried
            self.camera_streams[stream].reload_time = self.reload_time

    def _init_camera_settings(self):
        """
        set resolution for USB
        """
        if self.camera is None or not self.camera.if_connected():
            return

        # set saturation, contrast, brightness
        available_settings = self.camera.get_properties_available()
        for key in available_settings:
            if key in self.param["image"] and float(self.param["image"][key]) != -1:
                self.camera.set_properties(key, float(self.param["image"][key]))

        # set resolutions, define grop area
        current = self.camera.get_resolution()
        self.logging.info("- Current resolution: " + str(current))

        self.max_resolution = self.camera.get_resolution(maximum=True)
        self.logging.debug("- Maximum resolution: " + str(self.max_resolution))

        if "x" in self.param["image"]["resolution"]:
            dimensions = self.param["image"]["resolution"].split("x")
            self.logging.debug(self.id + " Set resolution: " + str(dimensions))
            self.camera.set_resolution(width=float(dimensions[0]), height=float(dimensions[1]))
            current = self.camera.get_resolution()

            if current == [0, 0]:
                current = [int(dimensions[0]), int(dimensions[1])]

            self.param["image"]["resolution_max"] = self.max_resolution
            self.param["image"]["resolution_current"] = current
            self.param["image"]["crop_area"] = self.image.crop_area_pixel(resolution=current,
                                                                          area=self.param["image"]["crop"],
                                                                          dimension=False)
            self.logging.info("- New resolution: " + str(current))
            self.logging.debug("- New crop area:  " + str(self.param["image"]["crop"]) + " -> " +
                               str(self.param["image"]["crop_area"]))
        else:
            self.logging.info("- Resolution definition not supported (e.g. '800x600'): " +
                              str(self.param["image"]["resolution"]))

        # return properties as values
        self.param["camera"] = self.camera.get_properties()

    def _init_microphone(self):
        """
        connect with the correct microphone
        """
        if "record_micro" in self.param:
            which_mic = self.param["record_micro"]
            if which_mic != "" and which_mic in self.microphones:
                self.micro = self.microphones[which_mic]
                micro_id = self.micro.id
                self.logging.info("- Connected microphone '" + micro_id + "' and camera '" + self.id + "'.")
                return
        self.micro = None
        self.logging.warning("- Could not connect a microphone to camera '" + self.id + "'!")

    def run(self):
        """
        Start recording for livestream and save images every x seconds
        """
        similarity = 0
        count_paused = 0
        reload_time = time.time()
        sensor_last = ""

        self.logging.info("Starting CAMERA control for '"+self.id+"' ...")
        self.logging.info("Initializing camera (id=" + self.id + ", type=" + self.type +
                          ", source=" + str(self.source) + ") ...")

        while self._running:
            current_time = self.config.local_time()
            stamp = current_time.strftime('%H%M%S')
            self.config_update = self.config.update["camera_" + self.id]

            if self.active:

                # reset some settings end of the day
                if self.date_last != self.config.local_time().strftime("%Y-%m-%d"):
                    self.record_temp_threshold = None
                    self.date_last = self.config.local_time().strftime("%Y-%m-%d")

                if self._stream_errors > self._stream_errors_max_accepted and self._stream_errors_restart:
                    self.logging.warning("....... Reload CAMERA '" + self.id + "' due to stream errors: " +
                                         str(self._stream_errors) + " errors.")

                # if error reload from time to time
                if self.if_error() and (reload_time + self._interval_reload_if_error) < time.time():
                    self.logging.warning("....... Reload CAMERA '" + self.id + "' due to errors --> " +
                                         str(round(reload_time, 1)) + " + " +
                                         str(round(self._interval_reload_if_error, 1)) + " > " +
                                         str(round(time.time(), 1)))
                    self.logging.warning("        " + self.if_error(details=True))
                    reload_time = time.time()
                    self.config_update = True
                    self.reload_camera = True

                # check if camera is paused, wait with all processes ...
                if not self._paused:
                    count_paused = 0
                while self._paused and self._running:
                    if count_paused == 0:
                        self.logging.info("Recording images with " + self.id + " paused ...")
                        count_paused += 1
                    time.sleep(1)

                # Video recording
                if self.video.recording:
                    self.video_recording(current_time)

                # Check and record active streams
                self.measure_usage(current_time, stamp)

                # Video Recording
                if self.if_other_prio_process(self.id) or self.if_only_lowres() or self.video.processing \
                        or self.error or not self.active:

                    self.logging.debug("prio=" + str(self.if_other_prio_process(self.id)) + "; " +
                                       "lowres=" + str(self.if_only_lowres()) + "; " +
                                       "processing=" + str(self.video.processing) + "; " +
                                       "error=" + str(self.error) + "; " +
                                       "active=" + str(self.active))

                    self.slow_down_streams(True)
                else:
                    self.slow_down_streams(False)

            # start or reload camera connection
            if self.config_update or self.reload_camera:
                self.logging.info("Updating CAMERA configuration (" + self.id + "/" +
                                  self.param["name"] + "/" + str(self.param["active"]) + "/" +
                                  ") ...")
                self.update_main_config()
                self.set_streams_active(active=True)
                self.reconnect(directly=True)

            # Image Recording (if not video recording)
            if self.active and self.record and not self.video.recording and not self.error:
                self.thread_set_priority(2)
                self.image_recording(current_time, stamp, similarity, sensor_last)

            elif not self.active or self.error:
                self.thread_set_priority(7)

            self.thread_wait()
            self.thread_control()

        self.logging.info("Stopped camera (" + self.id + "/" + self.type + ").")

    def stop(self):
        """
        Stop recording
        """
        if self.video:
            self.video.stop()

        self.camera_stream_raw.stop()
        for stream in self.camera_streams:
            self.camera_streams[stream].kill()
            self.camera_streams[stream].stop()

        self._running = False

    def pause(self, command):
        """
        pause image recording and reconnect try
        """
        self._paused = command

    def if_error(self, message=False, length=False, details=False):
        """
        check for camera error and errors in streams
        """
        if message:
            return self.error_msg
        elif length:
            return len(self.error_msg)
        elif details:
            error_list = "Errors: " + self.id + "=" + str(self.error) + " (" + str(len(self.error_msg)) + "); "
            error_list += self.id + "-img=" + str(self.image.if_error()) + " ("
            error_list += str(self.image.if_error(length=True)) + "); "
            error_list += self.id + "-sRaw=" + str(self.camera_stream_raw.if_error()) + " ("
            error_list += str(self.camera_stream_raw.if_error(length=True)) + "); "
            for stream in self.camera_streams:
                error_list += self.id + "-sEdit-" + stream + "=" + str(self.camera_streams[stream].if_error()) + " ("
                error_list += str(self.camera_streams[stream].if_error(length=True)) + "); "
            error_list += "\n"
            return error_list

        if self.error:
            return self.error

        for stream in self.camera_streams:
            if self.camera_streams[stream].if_error(message=False, length=True) > self._stream_errors_max_accepted:
                self.raise_warning("Camera doesn't work correctly: More than " + str(self._stream_errors_max_accepted) +
                                   " errors in EDIT stream '" + stream + "'...")
                self._stream_errors += 1

        return False

    def reset_error_all(self):
        """
        reset errors for all relevant classes
        """
        self.reset_error()
        self._stream_errors = 0
        if self.image is not None:
            self.image.reset_error()
        if self.video is not None:
            self.video.reset_error()
        if self.camera is not None:
            self.camera.reset_error()
        if self.camera_stream_raw is not None:
            self.camera_stream_raw.reset_error()
        for stream_id in self.camera_streams:
            if self.camera_streams[stream_id] is not None:
                self.camera_streams[stream_id].reset_error()
        self.record_image_error = False

    def connect(self):
        """
        initial connect of all relevant streams and devices
        """
        self._init_image_processing()
        self._init_video_processing()
        self._init_stream_raw()
        self._init_streams()
        if self.active:
            self.set_streams_active(active=True)
            time.sleep(1)
            self._init_camera(init=True)
        self._init_microphone()

        self.object = BirdhouseObjectDetection(self.id, self.config)
        self.object.start()
        self.initialized = True

    def reconnect(self, directly=False):
        """
        Reconnect after API call.
        """
        if directly and self.camera is not None:
            if self.active:
                self.set_streams_active(active=True)
                time.sleep(1)
                self._init_camera(init=True)
            self.object.reconnect()
            self.reload_camera = False
        elif directly:
            if self.active:
                self.set_streams_active(active=True)
                time.sleep(1)
                self._init_camera(init=True)
            self._init_microphone()
            self.object.reconnect()
            self.reload_camera = False
        else:
            self.reload_camera = True
            self.config_update = True
        response = {"command": ["reconnect camera"], "camera": self.id}
        return response

    def camera_enable_recording(self):
        """
        start recording and set current image size
        """
        if not self.video.if_running():
            self.video.start()
            self.video.image_size = self.image_size

    def video_recording(self, current_time):
        """
        record video
        """
        if self.error:
            return

        if self.video.record_stop_auto():
            if "record_micro" in self.param:
                mic = self.param["record_micro"]
                self.logging.info("- Try to stop micro '" + mic + "' ...")
                if mic in self.microphones:
                    self.logging.info("- Automatically stop AUDIO recording ...")
                    self.microphones[mic].record_stop()

            self.logging.info("- Automatically stop VIDEO recording ...")
            self.video.record_stop()

        else:
            image_id = self.camera_streams["camera_hires"].read_stream_image_id()

            if self.image_last_id == 0 or self.image_last_id != image_id:
                image = self.camera_streams["camera_hires"].read_stream("record")
                self.image_last_id = image_id
            else:
                return

            self.video.image_size = self.image_size
            self.video.create_video_image(image=image)

            if self.image_size == [0, 0]:
                self.image_size = self.image.size_raw(image)
                self.video.image_size = self.image_size

            self.logging.debug(".... Video Recording: " + str(self.video.info["stamp_start"]) + " -> " + str(
                current_time.strftime("%H:%M:%S")))

    def measure_usage(self, current_time, stamp):
        """
        measure usage from time to time
        """
        if time.time() - self.usage_time > self.usage_interval:
            self.logging.debug("... check usage!")

            self.usage_time = time.time()
            this_stamp = stamp[0:4]
            statistics = self.config.db_handler.read(config="statistics")

            if statistics == {}:
                statistics[self.id] = {}
                self.config.db_handler.write(config="statistics", date="", data=statistics, create=True, save_json=True)
            elif self.id not in statistics:
                statistics[self.id] = {}
                self.config.db_handler.write(config="statistics", date="", data=statistics, create=True, save_json=True)

            count = 0
            for stream_id in self.camera_streams:
                count += self.camera_streams[stream_id].get_active_streams()

            statistics[self.id][this_stamp] = {
                #"active_streams_raw": self.camera_stream_raw.get_active_streams(),
                "active_streams": count,
                "stream_framerate": self.camera_stream_raw.get_framerate(),
                "camera_error": self.if_error(),
                "camera_raw_error": self.camera_stream_raw.if_error()
            }

            self.config.queue.entry_add(config="statistics", date="", key=self.id, entry=statistics[self.id].copy())

    def image_recording(self, current_time, stamp, similarity, sensor_last):
        """
        record images as defined in settings
        """
        if self.error:
            return

        self.logging.debug(" ...... check if recording")
        start_time = time.time()
        if self.image_recording_active(current_time=current_time):

            self.logging.debug(" ...... record now!")
            image_hires = self.camera_streams["camera_hires"].read_image()

            # retry once if image could not be read
            if image_hires is None or self.image.error or len(image_hires) == 0:
                self.image.error = False
                image_hires = self.camera_streams["camera_hires"].read_image(return_error_image=False)

            # if no error format and analyze image
            if image_hires is not None and not self.image.error and len(image_hires) > 0:
                image_compare = self.image.convert_to_gray_raw(image_hires)
                height, width, color = image_hires.shape
                preview_scale = self.param["image"]["preview_scale"]

                if self.previous_image is not None:
                    similarity = self.image.compare_raw(image_1st=image_compare,
                                                        image_2nd=self.previous_image,
                                                        detection_area=self.param["similarity"]["detection_area"])
                    similarity = str(similarity)

                image_info = {
                    "camera": self.id,
                    "compare": (stamp, self.previous_stamp),
                    "date": current_time.strftime("%d.%m.%Y"),
                    "datestamp": current_time.strftime("%Y%m%d"),
                    "detections": [],
                    "hires": self.config.filename_image("hires", stamp, self.id),
                    "hires_size": [width, height],
                    "info": {},
                    "lowres": self.config.filename_image("lowres", stamp, self.id),
                    "lowres_size": [round(width * preview_scale / 100), round(height * preview_scale / 100)],
                    "similarity": similarity,
                    "sensor": {},
                    "time": current_time.strftime("%H:%M:%S"),
                    "type": "image",
                    "weather": {}
                }
                self.previous_image = image_compare
                sensor_data = {"activity": round(100 - float(similarity), 1)}

            # else if error save at least sensor data
            else:
                self.record_image_error = True
                if image_hires is None:
                    self.record_image_error_msg = ["img_error='empty image from camera, but no camera error' (None)"]
                else:
                    self.record_image_error_msg = ["img_error=" + str(self.image.error) + "; img_len=" + str(len(image_hires))]
                sensor_data = {}
                image_info = {}
                self.previous_stamp = stamp
                return

            # get data from dht-sensors
            for key in self.sensor:
                if self.sensor[key].if_running():
                    sensor_data[key] = self.sensor[key].get_values()
                    sensor_data[key]["date"] = current_time.strftime("%d.%m.%Y")
                    # image_info["sensor"][key] = sensor_data[key]

            sensor_stamp = current_time.strftime("%H%M") + "00"
            image_info["info"]["duration_1"] = round(time.time() - start_time, 3)
            self.config.queue.entry_add(config="images", date="", key=stamp, entry=image_info)

            if int(self.config.local_time().strftime("%M")) % 5 == 0 and sensor_stamp != sensor_last:
                sensor_last = sensor_stamp
                self.logging.debug("Write sensor data to file ...")
                self.config.queue.entry_add(config="sensor", date="", key=sensor_stamp, entry=sensor_data)

            # if no error save image files
            if not self.error and not self.image.error:
                path_lowres = os.path.join(self.config.db_handler.directory("images"),
                                           self.config.filename_image("lowres", stamp, self.id))
                path_hires = os.path.join(self.config.db_handler.directory("images"),
                                          self.config.filename_image("hires", stamp, self.id))
                self.logging.debug("WRITE:" + path_lowres)
                self.write_image(filename=path_hires, image=image_hires)
                self.write_image(filename=path_lowres, image=image_hires,
                                 scale_percent=self.param["image"]["preview_scale"])

                if self.detect_active and self.detect_settings["active"] and os.path.exists(path_hires):
                    self.object.analyze_image(stamp, path_hires, image_hires, image_info)

                self.record_image_error = False
                self.record_image_error_msg = []
                self.record_image_last = time.time()
                self.record_image_last_string = self.config.local_time().strftime('%d.%m.%Y %H:%M:%S')

            time.sleep(self._interval)
            self.previous_stamp = stamp

    def image_recording_active(self, current_time=-1, check_in_general=False):
        """
        check if image recording is currently active depending on settings (start and end time incl. sunset or sunrise)
        """
        is_active = False
        if check_in_general:
            self.record_image_last_compare = ""

        if current_time == -1:
            current_time = self.config.local_time()
        second = current_time.strftime('%S')
        minute = current_time.strftime('%M')
        hour = current_time.strftime('%H')
        current_time_string = current_time.strftime("%Y-%m-%d_%H:%M:%S")

        self.logging.debug("Check if record ... " + str(hour) + "/" + str(minute) + "/" + str(second) + " ...")

        record_from_hour = -1
        record_from_minute = -1
        record_to_hour = -1
        record_to_minute = -1
        record_to_hour_compare = -1
        record_to_minute_compare = -1

        if self.record and not self.error:
            # old detection
            if "record_from" not in self.param["image_save"] or "record_to" not in self.param["image_save"]:
                if (second in self.param["image_save"]["seconds"]) and (hour in self.param["image_save"]["hours"]):
                    self.logging.info(
                        " -> RECORD TRUE "+self.id+" (" + str(record_from_hour) + ":" + str(record_from_minute) + "-" +
                        str(record_to_hour) + ":" + str(record_to_minute) + ") " +
                        str(hour) + "/" + str(minute) + "/" + str(second))
                    if check_in_general:
                        self.record_image_last_compare = "OLD|"
                    is_active = True

            # new detection
            elif "record_from" in self.param["image_save"] and "record_to" in self.param["image_save"]:

                self.weather_sunrise = self.config.weather.get_sunrise()
                self.weather_sunset = self.config.weather.get_sunset()

                record_from = self.param["image_save"]["record_from"]
                record_to = self.param["image_save"]["record_to"]
                record_rhythm = self.param["image_save"]["rhythm"]
                record_rhythm_offset = self.param["image_save"]["rhythm_offset"]
                record_seconds = []

                start = int(record_rhythm_offset)
                while start < 60:
                    self.record_seconds.append(start)
                    start += int(record_rhythm)

                if "sun" in record_from and self.weather_active and self.weather_sunrise is not None:
                    if "sunrise-1" in record_from:
                        record_from_hour = int(self.weather_sunrise.split(":")[0]) - 1
                        record_from_minute = int(self.weather_sunrise.split(":")[1])
                    elif "sunrise+0" in record_from:
                        record_from_hour = int(self.weather_sunrise.split(":")[0])
                        record_from_minute = int(self.weather_sunrise.split(":")[1])
                    elif "sunrise+1" in record_from:
                        record_from_hour = int(self.weather_sunrise.split(":")[0]) + 1
                        record_from_minute = int(self.weather_sunrise.split(":")[1])
                elif "sun" in record_from:
                    record_from_hour = 8
                    record_from_minute = 0
                else:
                    record_from_hour = record_from
                    record_from_minute = 0

                if "sun" in record_to and self.weather_active and self.weather_sunrise is not None:
                    if "sunset-1" in record_to:
                        record_to_hour = int(self.weather_sunset.split(":")[0]) - 1
                        record_to_minute = self.weather_sunset.split(":")[1]
                    elif "sunset+0" in record_to:
                        record_to_hour = int(self.weather_sunset.split(":")[0])
                        record_to_minute = self.weather_sunset.split(":")[1]
                    elif "sunset+1" in record_to:
                        record_to_hour = int(self.weather_sunset.split(":")[0]) + 1
                        record_to_minute = self.weather_sunset.split(":")[1]
                elif "sun" in record_to:
                    record_to_hour = 20
                    record_to_minute = 0
                else:
                    record_to_hour = record_to
                    record_to_minute = 0

                record_to_minute_compare = record_to_minute
                record_to_hour_compare = record_to_hour
                if int(record_to_minute) == 0:
                    record_to_minute_compare = "59"
                    record_to_hour_compare = str(int(record_to_hour_compare) - 1).zfill(2)

                self.logging.debug(" -> RECORD check " + self.id + "  (" + str(record_from_hour) + ":" +
                                   str(record_from_minute) + "-" + str(record_to_hour_compare) + ":" +
                                   str(record_to_minute_compare) + ") " + str(int(hour)) + "/" + str(int(minute)) + "/" +
                                   str(int(second)) + " ... " + str(self.record_seconds))

                if int(second) in self.record_seconds or check_in_general:
                    if ((int(record_from_hour)*60)+int(record_from_minute)) <= ((int(hour)*60)+int(minute)) <= \
                            ((int(record_to_hour_compare)*60)+int(record_to_minute_compare)):
                        self.logging.debug(
                            " -> RECORD TRUE "+self.id+"  (" + str(record_from_hour) + ":" + str(record_from_minute) + "-" +
                            str(record_to_hour_compare) + ":" + str(record_to_minute_compare) + ") " +
                            str(hour) + "/" + str(minute) + "/" + str(second) + "  < -----")
                        is_active = True

        self.logging.debug(" -> RECORD FALSE "+self.id+" (" + str(record_from_hour) + ":" + str(record_from_minute) +
                           "-" + str(record_to_hour_compare) + ":" + str(record_to_minute_compare) + ")")

        if check_in_general:
            self.record_image_last_compare += "[" + str(is_active) + " | " + current_time_string + "] [from " + \
                                              str(int(record_from_hour)) + ":" + str(int(record_from_minute)) + \
                                              " | to " + str(int(record_to_hour)) + ":" + str(int(record_to_minute)) + \
                                              "]"
            self.record_image_start = str(int(record_from_hour)).zfill(2) + ":" + str(int(record_from_minute)).zfill(2)
            self.record_image_end = str(int(record_to_hour)).zfill(2) + ":" + str(int(record_to_minute)).zfill(2)

        return is_active

    def image_differs(self, file_info):
        """
        check if similarity is under threshold
        """
        threshold = float(self.param["similarity"]["threshold"])
        similarity = float(file_info["similarity"])
        if similarity != 0 and similarity < threshold:
            return 1
        else:
            return 0

    def image_to_select(self, timestamp, file_info, check_similarity=True):
        """
        check image properties to decide if image is a selected one (for backup and view with selected images)
        """
        threshold = float(self.param["similarity"]["threshold"])
        if self.record_temp_threshold is not None:
            threshold = self.record_temp_threshold

        select = False
        if "similarity" not in file_info:
            select = False

        elif "to_be_deleted" in file_info and float(file_info["to_be_deleted"]) == 1:
            select = False

        elif ("camera" in file_info and file_info["camera"] == self.id) or (
                "camera" not in file_info and self.id == "cam1"):

            if timestamp[2:4] == "00" and timestamp[0:4] != self.image_to_select_last[0:4]:
                self.image_to_select_last = timestamp
                select = True

            elif "favorit" in file_info and float(file_info["favorit"]) == 1:
                select = True

            elif "detections" in file_info and len(file_info["detections"]) > 0:
                select = True

            elif check_similarity:
                similarity = float(file_info["similarity"])
                if similarity != 0 and similarity < threshold:
                    select = True

            else:
                select = True  # to be checked !!!

        info = file_info.copy()
        for value in ["camera", "to_be_deleted", "favorit", "similarity"]:
            if value not in info:
                info[value] = -1
        self.logging.debug("Image to select: delete=" + str(float(info["to_be_deleted"])) +
                           "; cam=" + str(info["camera"]) + "|" + self.id +
                           "; favorite=" + str(float(info["favorit"])) +
                           "; stamp=" + timestamp + "|" + self.image_to_select_last +
                           "; similarity=" + str(float(info["similarity"])) + "<" +
                           str(self.param["similarity"]["threshold"]) +
                           " -> " + str(select))
        return select

    def get_image_raw(self):
        """
        get image and convert to raw
        """
        if self.error:
            return ""

        try:
            raw = self.camera_streams["raw"].read_image()
            check = str(type(raw))
            if "NoneType" in check or len(raw) == 0:
                raise Exception("Got an empty image from 'self.camera_stream_raw.read_image()'")
            elif self.camera_stream_raw.if_error():
                raise Exception("Other error requesting 'self.camera_stream_raw.read_image()' - see log.")
            else:
                return raw.copy()
        except Exception as e:
            error_msg = "Can't grab image from camera '" + self.id + "': " + str(e)
            self.image.raise_error(error_msg)
            return ""

    def get_stream(self, stream_id, stream_type, stream_resolution="", system_info=False, wait=True):
        """
        get image from new streams
        """
        stream = stream_type
        if stream_resolution != "":
            stream += "_" + stream_resolution

        if stream not in self.camera_streams:
            error_msg = "Stream '" + stream + "' does not exist."
            image = self.camera_streams[stream].read_error_image(error_msg, error_trigger="get_stream: stream '" +
                                                                 stream + "' not in self.camera_streams")
            self.raise_error(error_msg)
            return image
        else:
            image = self.camera_streams[stream].read_stream(stream_id, system_info, wait)

        if self.camera_streams[stream].if_error():
            image = self.camera_streams[stream].read_error_image(error_msg="",
                                                                 error_trigger="get_stream: self.camera_streams['" +
                                                                 stream + "'].if_error()")
        elif self.if_error():
            image = self.camera_streams[stream].read_error_image(error_msg="", error_trigger="get_stream: if_error()")
        return image

    def get_stream_object_detection(self, stream_id, stream_type, stream_resolution="", system_info=False, wait=True):
        """
        get image with rendered labels of detected objects
        """
        current_frame_id = self.get_stream_image_id()
        if stream_id in self.detect_fps_last:
            self.detect_fps = round((1 / (time.time() - self.detect_fps_last[stream_id])), 1)
            self.logging.debug("--> " + str(self.detect_fps) + "fps / " +
                               str(round((time.time() - self.detect_fps_last[stream_id]), 2))+"s / " +
                               str(current_frame_id-self.detect_frame_id_last) + " frames difference / " +
                               str(self.image_size_object_detection) + "%")

        self.detect_fps_last[stream_id] = time.time()
        if self.detect_frame_id_last == current_frame_id and self.detect_frame_last is not None:
            return self.detect_frame_last

        image = self.get_stream(stream_id, stream_type, stream_resolution, system_info, wait)
        self.detect_frame_last = image
        self.detect_frame_id_last = self.get_stream_image_id()

        if self.detect_objects and self.detect_objects.loaded and not self.if_error():
            path_hires = str(os.path.join(self.config.db_handler.directory("images"),
                                          "_temp_"+str(self.id)+"_"+str(stream_id)+".jpg"))
            try:
                self.write_image(path_hires, image, scale_percent=self.image_size_object_detection)
                img, detect_info = self.detect_objects.analyze(path_hires, -1, False)
                img = self.detect_visualize.render_detection(image, detect_info, 1, self.detect_settings["threshold"])
                if os.path.exists(path_hires):
                    os.remove(path_hires)
                return img
            except Exception as e:
                msg = "Object detection error: " + str(e)
                self.logging.error(msg)
                image = self.image.draw_text_raw(raw=image, text=msg, position=(20, -40), font=None, scale=0.6,
                                                 color=(255, 255, 255), thickness=1)

        elif not self.detect_objects or not self.detect_objects.loaded:
            msg = "Object detection not loaded."
            image = self.image.draw_text_raw(raw=image, text=msg, position=(20, -40), font=None, scale=0.6,
                                             color=(255, 255, 255), thickness=1)

        return image

    def get_stream_image_id(self):
        """
        return current image id from stream raw
        """
        return self.camera_stream_raw.read_stream_image_id()

    def get_stream_count(self):
        """
        identify amount of currently running streams
        """
        count = 0
        for stream_id in self.camera_streams:
            if self.camera_streams[stream_id].if_running():
                count += self.camera_streams[stream_id].get_active_streams()
        return count

    def get_stream_kill(self, ext_stream_id, int_stream_id):
        """
        check if stream has to be killed
        """
        self.logging.debug("get_image_stream_kill: " + str(ext_stream_id))
        if ext_stream_id in self.image_streams_to_kill:
            self.logging.debug("get_image_stream_kill - True: " + str(ext_stream_id))
            del self.image_streams_to_kill[ext_stream_id]
            self.camera_stream_raw.kill(int_stream_id)
            return True
        else:
            return False

    def set_stream_kill(self, ext_stream_id):
        """
        mark streams to be killed
        """
        self.logging.debug("set_image_stream_kill: " + ext_stream_id)
        self.image_streams_to_kill[ext_stream_id] = datetime.now().timestamp()

    def set_streams_active(self, active=True):
        """
        set all streams active or inactive
        """
        for stream_id in self.camera_streams:
            self.camera_streams[stream_id].active = active

    def get_camera_status(self, info="all"):
        """
        return all status and error information
        """
        if not self.initialized:
            return {}

        recording_active = self.image_recording_active(current_time=-1, check_in_general=True)
        if self.record and time.time() - self.record_image_last > 120 \
                and not self.video.recording and not self.video.processing \
                and self.param["active"] and recording_active:
            self.record_image_error = True
            self.record_image_error_msg = ["No image recorded for >120s (" +
                                           str(round(time.time() - self.record_image_last, 1)) + ")"]

        status = {
            "active": self.param["active"],
            "active_streams": self.get_stream_count(),
            "running": self.if_running(),
            "recording": self.video.recording,
            "processing": self.video.processing,
            "last_reload": time.time() - self.record_image_reload,

            "error_details": {},
            "error_details_msg": {},
            "error_details_health": {},
            "error": self.error,
            "error_msg": ",\n".join(self.error_msg),

            "image_cache_size": self.config_cache_size,
            "record_image": self.record,
            "record_image_error": self.record_image_error,
            "record_image_last": time.time() - self.record_image_last,
            "record_image_active": recording_active,
            "record_image_last_compare": self.record_image_last_compare,
            "record_image_start": self.record_image_start,
            "record_image_end": self.record_image_end,
            "stream_raw_fps": self.camera_stream_raw.get_framerate(),
            "stream_object_fps": self.detect_fps,

            "properties": {},
            "properties_image": {}
            }

        if info == "all":
            error_details = {
                "camera": self.error,
                "camera_handler": None,
                "image": self.image.error,
                "image_record": self.record_image_error,
                "video": self.video.error,
                "stream_raw": self.camera_stream_raw.error
            }

            error_details_msg = {
                "camera": self.error_msg,
                "camera_handler": [],
                "image": self.image.error_msg,
                "image_record": self.record_image_error_msg,
                "video": self.video.error_msg,
                "stream_raw": self.camera_stream_raw.error_msg
            }

            error_details_health = {
                "camera": self.health_status(),
                "video": self.video.health_status(),
                "stream_raw": self.camera_stream_raw.health_status()
            }

            if self.camera is not None:
                error_details["camera_handler"] = self.camera.error
                error_details_msg["camera_handler"] = self.camera.error_msg

            for stream_id in self.camera_streams:
                error_details[stream_id] = self.camera_streams[stream_id].error
                error_details_msg[stream_id] = self.camera_streams[stream_id].error_msg
                error_details_health[stream_id] = self.camera_streams[stream_id].health_status()

            status["error_details"] = error_details
            status["error_details_msg"] = error_details_msg
            status["error_details_health"] = error_details_health

        if info == "properties" or self.cam_param is None:
            if self.camera is not None and self.camera.if_connected():
                status["properties"] = self.camera.get_properties()
                status["properties_image"] = self.camera.get_properties_image()
                self.cam_param = status["properties"]
                self.cam_param_image = status["properties_image"]
        elif self.cam_param is not None:
            status["properties"] = self.cam_param
            status["properties_image"] = self.cam_param_image

        return status

    def get_camera_settings(self, param):
        """
        change camera settings
        """
        response = {}
        parameters = param["parameter"]
        setting_key = parameters[0]
        setting_value = parameters[1]
        available_settings = self.camera.get_properties_available("set")

        if setting_key in available_settings:
            self.camera.set_properties(key=setting_key, value=setting_value)
        else:
            self.raise_error("Error during change of camera settings: given key '" + setting_key + "' is not supported.")

        self.logging.info("Camera settings: " + str(parameters))
        self.logging.info("   -> available: " + str(available_settings))
        return response

    def set_system_info(self, active, line1="", line2="", color=""):
        """
        show system info in specific streams
        """
        self.camera_streams["camera_hires"].set_system_info(active, line1, line2, color)

    def get_available_devices(self):
        """
        identify available video devices
        """
        self.logging.info("Identify available video devices ...")
        devices = self.camera_info.get_available_cameras()
        system = {
            "video_devices": devices["list"],
            "video_devices_short": devices["short"],
            "video_devices_complete": devices["complete"],
        }

        camera_cv = BirdhouseCameraHandler(self.id, self.source, self.config)
        camera_pi = BirdhousePiCameraHandler(self.id, self.source, self.config)

        camera_count = 0
        self.logging.info("Identified " + str(len(system["video_devices_short"])) + " video devices:")
        for key in system["video_devices_short"]:
            camera_count += 1
            device_info = system["video_devices_complete"][key]["info"]

            if key == "/dev/picam" and birdhouse_env["rpi_64bit"]:
                system["video_devices_complete"][key] = camera_pi.camera_status(source=key, name=device_info)
            else:
                system["video_devices_complete"][key] = camera_cv.camera_status(source=key, name=device_info)

            birdhouse_initial_connect_msg[key] = "initial_connect=" + str(system["video_devices_complete"][key]["image"]) + \
                                                 ", info=" + system["video_devices_complete"][key]["info"] + \
                                                 ", shape=" + str(system["video_devices_complete"][key]["shape"])

            camera_string = " - " + str(camera_count).rjust(2) + ": " + str(key).ljust(12) + " ("
            camera_string += system["video_devices_complete"][key]["info"].split(" (")[0].split(":")[0] + ") "

            if "error" in system["video_devices_complete"][key]:
                self.logging.warning(camera_string + " - ERROR: " + str(system["video_devices_complete"][key]["error"]))
                birdhouse_initial_connect_msg[key] += ", error='" + str(system["video_devices_complete"][key]["error"]) + "'"
            else:
                self.logging.warning(camera_string + " - OK")

        self.available_devices = system
        return system

    def set_maintenance_mode(self, active=True, line1="", line2=""):
        """
        set maintenance_mode in all streams
        """
        if active:
            self.logging.info("Starting maintenance mode for CAMERA '" + self.id + " ... ")
        for stream in self.camera_streams:
            self.camera_streams[stream].set_maintenance_mode(active, line1, line2, True)
        if not active:
            self.logging.info("Stopped maintenance mode for CAMERA '" + self.id + ". ")

    def write_image(self, filename, image, scale_percent=100):
        """
        Scale image and write to file
        """
        image_path = os.path.join(self.config.main_directory, filename)
        self.logging.debug("Write image: " + image_path)

        try:
            if scale_percent != 100:
                width = int(image.shape[1] * float(scale_percent) / 100)
                height = int(image.shape[0] * float(scale_percent) / 100)
                image = cv2.resize(image, (width, height))
            return cv2.imwrite(image_path, image)

        except Exception as e:
            error_msg = "Can't save image and/or create thumbnail '" + image_path + "': " + str(e)
            self.image.raise_error(error_msg)
            return ""

    def read_image(self, filename):
        """
        read image with given filename
        """
        image_path = os.path.join(self.config.main_directory, filename)
        self.logging.info("Read image: " + image_path)

        try:
            image = cv2.imread(image_path)
            self.logging.debug(" --> " + str(image.shape))
            return image

        except Exception as e:
            error_msg = "Can't read image '" + image_path + "': " + str(e)
            self.image.raise_error(error_msg)
            return ""

    def slow_down_streams(self, slow_down=True):
        """
        slow down video streams, e.g. while recording
        """
        self.camera_stream_raw.slow_down(slow_down)
        for stream in self.camera_streams:
            self.camera_streams[stream].slow_down(slow_down)

    def if_only_lowres(self):
        """
        check if only lowres is requested
        """
        count_lowres = 0
        count_other = 0
        for stream in self.camera_streams:
            if self.camera_streams[stream] is not None:
                if self.camera_streams[stream].get_active_streams() > 0 and "lowres" in stream:
                    count_lowres += 1
                elif self.camera_streams[stream].get_active_streams() > 0:
                    count_other += 1

        self.logging.debug(" ... lowres=" + str(count_lowres) + "; other=" + str(count_other))
        if count_other > 0:
            return False
        else:
            return True

    def update_main_config(self):
        self.logging.info("- Update data from main configuration file for camera " + self.id)
        temp_data = self.config.db_handler.read("main")

        self.config_update = False
        self.reload_camera = False

        self.param = temp_data["devices"]["cameras"][self.id]
        self.name = self.param["name"]
        self.active = self.param["active"]
        self.source = self.param["source"]
        self.type = self.param["type"]
        self.record = self.param["record"]
        self.detect_settings = self.param["object_detection"]

        self.image_size = [0, 0]
        self.image_size_lowres = [0, 0]
        self.image_last_raw = None
        self.image_last_raw_time = 0
        self.image_last_edited = None
        self.image_count_empty = 0
        self.image_time_last = {}
        self.image_time_current = {}
        self.image_time_rotate = {}
        self.image_fps = {}
        self.image_streams = {}
        self.image_streams_to_kill = {}
        self.image_size_object_detection = self.detect_settings["detection_size"]

        self.previous_image = None
        self.previous_stamp = "000000"

        if "video" in self.param and "max_length" in self.param["video"]:
            self.video.max_length = self.param["video"]["max_length"]

        self.camera.source = self.param["source"]
        self.camera_stream_raw.param = self.param
        self.camera_stream_raw.source = self.param["source"]
        for stream in self.camera_streams:
            self.camera_streams[stream].param = self.param
            self.camera_streams[stream].image.param = self.param
            self.camera_streams[stream].source = self.param["source"]
            self.camera_streams[stream].initial_connect_msg = self.initial_connect_msg
        self.image.param = self.param
        self.video.param = self.param
        self.object.param = self.param

        self.config.update["camera_" + self.id] = False
        self.reload_camera = True
