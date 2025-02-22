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
from modules.image import BirdhouseImageProcessing, BirdhouseImageSupport
from modules.video import BirdhouseVideoProcessing
from modules.object import BirdhouseObjectDetection
from modules.camera_handler import BirdhousePiCameraHandler, BirdhouseCameraHandler, CameraInformation
# https://pyimagesearch.com/2016/01/04/unifying-picamera-and-cv2-videocapture-into-a-single-class-with-opencv/


class BirdhouseCameraStreamRaw(threading.Thread, BirdhouseCameraClass):
    """
    creates a continuous stream while active requests
    """

    def __init__(self, camera_id, config):
        """
        Constructor to initialize camera class.

        Args:
            camera_id (str): camera ID
            config (modules.config.BirdhouseConfig): reference to main config handler
        """
        threading.Thread.__init__(self)
        BirdhouseCameraClass.__init__(self, class_id=camera_id+"-sRaw", class_log="cam-stream",
                                      camera_id=camera_id, config=config)

        self.camera = None
        self.image = BirdhouseImageProcessing(camera_id=self.id, config=self.config)
        self.image.resolution = self.param["image"]["resolution"]
        self.active = False

        self.fps = None
        self.fps_max = self.param["image"]["framerate"]
        self.fps_max_lowres = 3
        self.fps_slow = 2
        self.fps_average = []
        self.duration_max = None
        self.duration_max_lowres = None
        self.duration_slow = None
        self.set_duration_from_framerate()

        self.slow_stream = False
        self.maintenance_mode = False
        self.connected = False

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
        self._last_image = None
        self._start_time = None
        self._start_delay_stream = 1
        self._connected = False

    def run(self):
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

            if self.param["active"] \
                    and not self.maintenance_mode \
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

            elif self.maintenance_mode:
                pass

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
        extract image from stream (rotated if defined in settings)

        Returns:
            numpy.ndarray: raw image
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

        Returns:
            numpy.ndarray: raw image from cache or camera
        """
        if self.active:
            return self._stream
        else:
            return self.read_from_camera()

    def read_stream(self, stream_id="default", wait=True):
        """
        return stream image considering the max fps

        Args:
            stream_id (str): stream id
            wait (bool): wait for first image
        Returns:
            numpy.ndarray: raw image
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

        Returns:
            int: stream image id
        """
        return self._stream_image_id

    def read_stream_image_time(self):
        """
        return current image creation time

        Returns:
            float: stream image image create time
        """
        return self._stream_last_time

    def get_active_streams(self, stream_id=""):
        """
        return amount of active streams

        Args:
            stream_id (int): stream id
        Returns:
            (int|bool): if stream id not set, amount of active streams, else status of stream
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

        Returns:
            float: current frame rate
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

        Args:
            fps (float): current fps
        """
        self.fps_average.append(fps)
        if len(self.fps_average) > 10:
            self.fps_average.pop(0)

    def set_camera_handler(self, camera_handler):
        """
        connect camera handler for internal purposes

        Args:
            camera_handler (modules.camera_handler.BirdhouseCameraHandler|modules.camera_handler.BirdhousePiCameraHandler):
                reference to camera handler
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

        Args:
            slow_down (bool): set True to slow down thread
        """
        self.slow_stream = slow_down

    def set_duration_from_framerate(self):
        """
        set durations based on given frame rates
        """
        self.duration_max = 1 / self.fps_max
        self.duration_max_lowres = 1 / self.fps_max_lowres
        self.duration_slow = 1 / self.fps_slow

    def set_maintenance_mode(self, mode=True):
        """
        set raw stream to maintenance mode, in this mode reading is paused

        Args:
            mode (bool): activate or deactivate maintenance mode
        """
        self.maintenance_mode = mode

    def if_ready(self):
        """
        check if stream is ready to deliver images, connection to camera exists

        Returns:
            bool: True if active and connected
        """
        if self.camera is None:
            return False
        elif not self.camera.if_connected() or not self.param["active"]:
            return False
        else:
            return True

    def if_connected(self):
        """
        get status if camera is connected

        Returns:
            bool: status if connected
        """
        return self._connected

    def kill(self, stream_id="default"):
        """
        kill continuous stream creation

        Args:
            stream_id (int): stream id of stream to kill
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
    Class to create a continuous stream with specific format while active requests incl. error handling.
    """

    def __init__(self, camera_id, config, stream_raw, stream_type, stream_resolution):
        """
        Constructor to initialize camera class.

        Args:
            camera_id (str): camera ID
            config (modules.config.BirdhouseConfig): reference to main config handler
            stream_raw (BirdhouseCameraStreamRaw): reference to raw stream handler
            stream_type (str): options: "raw", "normalized", "camera", "setting"
            stream_resolution (str): options: "lowres", "hires"
        """
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
        self.fps_max = self.param["image"]["framerate"]
        self.fps_max_lowres = 3
        self.fps_slow = 2
        self.duration_max = None
        self.duration_slow = None
        self.set_duration_from_framerate()
        self.fps_object_detection = None
        self.slow_stream = False
        self.system_status = {
            "active": False,
            "color": [],
            "line1": "",
            "line2": ""
        }
        self.connected = False
        self.maintenance_mode = False
        self.reload_time = 0
        self.reload_tried = 0
        self.reload_success = 0
        self.initial_connect_msg = {}

        self._init_error_images()

    def _init_error_images(self):
        """
        create error images for settings and camera

        Returns:
            bool: status if loaded images correctly
        """
        if "resolution_cropped" in self.param["image"] and (self.type == "camera" or self.type == "normalized"):
            resolution = self.param["image"]["resolution_cropped"]
        elif "resolution_current" in self.param["image"]:
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

    def run(self):
        """
        start thread for edited streams
        """
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
                    raw = self.read_raw_and_edit(stream=True, stream_id=self._stream_id_base,
                                                 return_error_image=True)
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

        Args:
            stream (bool): stream image (True) or single image (False)
            stream_id (int|str): stream id ("default" if not stream_id is set)
            return_error_image (bool): return error image if error
        Returns:
            numpy.ndarray: edited image
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

        Args:
            return_error_image (bool): return error image if error
        Returns:
            numpy.ndarray: single edited image
        """
        return self.read_raw_and_edit(stream=False, stream_id="default", return_error_image=return_error_image)

    def read_stream(self, stream_id, system_info=False, wait=True):
        """
        read stream image considering the max fps

        Args:
            stream_id (int): stream id
            system_info (bool): add system_info if set
            wait (bool): wait for first image if required
        Returns:
            numpy.ndarray: edited image for stream
        """
        if not wait:
            self._error_wait = False

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

        Returns:
            int: current image number
        """
        return self.stream_raw.read_stream_image_id()

    def read_stream_image_time(self):
        """
        return current image creation time

        Returns:
            float: stream image image create time
        """
        return self.stream_raw.read_stream_image_time()

    def read_error_image(self, error_msg="", error_trigger=""):
        """
        return error image, depending on settings

        Args:
            error_msg (str): error message to be added to the image
            error_trigger (str): trigger for error
        """
        if error_msg == "":
            error_msg = self.if_error(message=True)
            if len(error_msg) == 0:
                error_msg = "no error :-)"
            else:
                error_msg = error_msg[-1]

        if self.type == "setting":
            image = self.img_error_raw["setting"].copy()
            image = self.edit_error_add_info(image, [error_msg], reload_time=0, info_type="setting",
                                             error_trigger=error_trigger)
        elif self.resolution == "lowres":
            image = self.img_error_raw["lowres"].copy()
            image = self.edit_create_lowres(image)
            image = self.edit_error_add_info(image, error_msg, reload_time=0, info_type="lowres",
                                             error_trigger=error_trigger)
        else:
            image = self.img_error_raw["camera"].copy()
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

        Args:
            raw (numpy.ndarray): raw image
            error_msg (str): error message to be added to the image
            reload_time (int): reload time
            info_type (str): type of infos to be added: empty, setting, camera
            error_trigger (str): trigger for the error
        Returns:
            numpy.ndarray: raw image with error infos
        """
        if raw is None or len(raw) == 0:
            self.logging.error("edit_error_add_info: empty image")
            return raw

        font_scale_headline = 1
        font_scale_text = 0.5
        font_color = (0, 0, 255)
        line_scale = 8

        lowres_position = self.config.param["views"]["index"]["lowres_pos_"+self.id]

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

        Args:
            error_msg (str): error message to be added to the image
        Returns:
            numpy.ndarray: raw image with maintenance infos
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

        Args:
            raw (numpy.ndarray): raw image
            error_msg (str): error message to be added to the image
            reload_time (int): reload time
            info_type (str): type of infos to be added: empty, setting, camera
        Returns:
            numpy.ndarray: raw image with error infos
        """
        if raw is None or len(raw) == 0:
            self.logging.error("edit_error_add_info: empty image")
            return raw

        font_scale_headline = 1
        font_scale_text = 0.5
        font_color = (255, 0, 0)
        line_scale = 8

        #raw = raw.copy()
        #lowres_position = self.config.param["views"]["index"]["lowres_position"]
        lowres_position = self.config.param["views"]["index"]["lowres_pos_"+self.id]

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

        Args:
            raw (numpy.ndarray): raw image
        Returns:
            numpy.ndarray: normalized raw image
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

        Args:
            raw (numpy.ndarray): raw image
            start_zero (bool): start crop area at [0, 0]
        Returns:
            numpy.ndarray: cropped image
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

        Args:
            raw (numpy.ndarray): raw image
        Returns:
            numpy.ndarray: lowres image
        """
        self.logging.debug(" ... size:" + str(self.image.size_raw(raw)) +
                           " ... scale: " + str(self.param["image"]["preview_scale"]) + " ... lowres: " +
                           str(self.image.size_raw(raw=raw, scale_percent=self.param["image"]["preview_scale"])))

        self._size_lowres = list(self.image.size_raw(raw=raw, scale_percent=self.param["image"]["preview_scale"]))
        lowres = self.image.resize_raw(raw=raw, scale_percent=100, scale_size=self._size_lowres)

        if lowres is not None:
            return lowres.copy()
        else:
            return lowres

    def edit_add_areas(self, raw):
        """
        Draw a red rectangle into the image to show detection area / and a yellow to show the crop area

        Args:
            raw (numpy.ndarray): raw image
        Returns:
            numpy.ndarray: image with rectangles for detection and crop areas
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
        area_image = self.image.draw_area_raw(raw=area_image, area=inner_area, color=color_detect,
                                              thickness=frame_thickness)
        return area_image.copy()

    def edit_check_error(self, image, error_message="", return_error_image=True):
        """
        check: if error then show error image

        Args:
            image (numpy.ndarray): image to check
            error_message (str): error message to raise in case of error
            return_error_image (bool): return error image
        Returns:
            numpy.ndarray: image if no error
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
        Add date and time to the image (top left).

        Args:
            raw (numpy.ndarray): input raw image
        Returns:
            numpy.ndarray: raw image with date and time information
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
        Add framerate into the image (bottom left)

        Args:
            raw (numpy.ndarray): input raw image
        Returns:
            numpy.ndarray: raw image with framerate information
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
        Add information if recording or processing to image (if activated).
        Use self.set_system_info() to set values and activate.

        Args:
            raw (numpy.ndarray): input raw image
        Returns:
            numpy.ndarray: raw image with system information added (if set activated)
        """
        if raw is None or len(raw) <= 0:
            self.logging.error("edit_add_system_info: empty image")
            return raw

        image = raw.copy()

        if self.system_status["active"] and self.resolution == "hires":
            lowres_position = self.config.param["views"]["index"]["lowres_pos_"+self.id]
            size = self.config.param["devices"]["cameras"][self.id]["image"]["resolution_cropped"]
            self.logging.debug("...... " + self.name + " " + str(size))

            [width, height] = [float(size[0]), float(size[1])]
            if int(lowres_position) != 3:
                pos_line1 = (25, -70)
                pos_line2 = (25, -50)
                size = [10.0, height-105.0, 400.0, height-35.0]
            else:
                pos_line1 = (-375, -70)
                pos_line2 = (-375, -50)
                size = [width-400.0, height-105.0, width-10, height-35.0]

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
        elif self.system_status["active"] and self.resolution == "lowres":
            [x1, y1, x2, y2] = [10, 10, 36, 36]
            pos_line1 = [15, 31]

            cv2.rectangle(image, (x1, y1), (x2, y2), self.system_status["color"], 1)
            image = self.image.draw_text_raw(raw=image, text=self.system_status["line1"],
                                             font=cv2.QT_FONT_NORMAL, color=self.system_status["color"],
                                             position=pos_line1, scale=0.8, thickness=2)

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

        Args:
            stream_id (int): stream id
        Returns:
            (int|bool): if stream id not set, amount of active streams, else status of stream
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

        Args:
            slow_down (bool): set True to slow down thread
        """
        self.slow_stream = slow_down

    def set_maintenance_mode(self, active, line1="", line2="", silent=False):
        """
        set maintenance mode -> image plus text, no streaming image (e.g. for camera restart)

        Args:
            active (bool): if active
            line1 (str): text for first line in big letters
            line2 (str): text for second line in small letters
            silent (bool): show logging information
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
            else:
                self.logging.debug("Stopped maintenance mode for '"+self.id+"/"+self.type+"/"+self.resolution+"'.")

    def set_system_info(self, active, line1="", line2="", color=None):
        """
        format message -> added via edit_add_system_info

        Args:
            active (bool): if active
            line1 (str): text for first line in big letters
            line2 (str): text for second line in small letters
            color ((int,int,int)): text color as (r,g,b)
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

    def set_duration_from_framerate(self):
        """
        set duration values based on given framerate
        """
        if self.resolution == "lowres":
            self.fps_max = self.fps_max_lowres
        self.duration_max = 1 / (self.fps_max + 1)
        self.duration_slow = 1 / self.fps_slow

    def kill(self):
        """
        kill continuous stream creation for a specific stream
        """
        self._last_activity = 0

    def stop(self):
        """
        stop edited streams
        """
        self._running = False

    def if_connected(self):
        """
        get status if camera is connected

        Returns:
            bool: status if connected
        """
        return self._connected


class BirdhouseCamera(threading.Thread, BirdhouseCameraClass):
    """
    Camera handler to control camera, record images, coordinate sensor and microphone and save data to database.
    """

    def __init__(self, camera_id, config, sensor, microphones, relays, statistics, first_cam=False):
        """
        Constructor to initialize camera class.

        Args:
            camera_id (str): camera ID
            config (modules.config.BirdhouseConfig): reference to main config handler
            sensor (dict[str, modules.sensors.BirdhouseSensor]): reference to sensor handler
            microphones (dict[str, modules.micro.BirdhouseMicrophone]): reference to microphone handler
            first_cam (bool): set True for the first camera to load relevant Python modules only once
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
        self.brightness = 100

        self.cam_param = None
        self.cam_param_image = None
        self.sensor = sensor
        self.relays = relays
        self.statistics = statistics
        self.microphones = microphones
        self.micro = None
        self.weather_active = self.config.param["weather"]["active"]
        self.weather_sunrise = None
        self.weather_sunset = None

        self.detect_objects = None
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
        self._interval_reload_if_error = 60*5
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
        self.image_streams = {}
        self.image_streams_to_kill = {}
        self.image_size_object_detection = self.detect_settings["detection_size"]
        self.max_resolution = None

        self.previous_image = None
        self.previous_stamp = "000000"

        self.record = self.param["record"]
        self.record_seconds = []
        self.record_image_last = time.time()
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

        self.connected = False
        self.camera_scan = {}
        self.camera_scan_source = None
        self.camera_info = CameraInformation()
        self.img_support = BirdhouseImageSupport(self.id, self.config)
        if first_cam:
            self.camera_scan = self.get_available_devices()
            self.config.camera_scan = self.camera_scan
        else:
            self.camera_scan = self.config.camera_scan

        self.connect()
        self.measure_usage(init=True)

    def _init_image_processing(self):
        """
        connect and start image processing
        """
        self.image = BirdhouseImageProcessing(camera_id=self.id, config=self.config)
        self.image.resolution = self.param["image"]["resolution"]

    def _init_video_processing(self):
        """
        connect and start or restart video processing
        """

        if self.video is not None and self.video.if_running():
            self.video.stop()
            time.sleep(1)

        self.video = BirdhouseVideoProcessing(camera_id=self.id, camera=self, config=self.config)

        if not self.error and self.param["video"]["allow_recording"]:
            self.video_recording_start()

    def _init_stream_raw(self):
        """
        connect and start or restart raw camera stream
        """
        if self.camera_stream_raw is not None and self.camera_stream_raw.if_running():
            self.camera_stream_raw.kill()
            self.camera_stream_raw.stop()
            time.sleep(1)

        self.camera_stream_raw = BirdhouseCameraStreamRaw(camera_id=self.id, config=self.config)
        self.camera_stream_raw.start()

    def _init_streams(self):
        """
        init and connect edited streams
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
        start or restart camera handler

        Args:
            init (bool): set True for initial start and False if restarting
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
                if self.camera_scan_source is None:
                    self.camera = BirdhouseCameraHandler(camera_id=self.id, source=self.source, config=self.config)
                else:
                    self.camera = BirdhouseCameraHandler(camera_id=self.id, source=self.camera_scan_source,
                                                         config=self.config)
            self.connected = self.camera.connect()
        else:
            self.connected = self.camera.reconnect()

        self.set_connection_status(self.connected)
        self.reload_tried = time.time()
        if self.connected:
            self.logging.debug("Camera '" + self.id + "' connected, initialize settings ...")
            self.camera_stream_raw.set_camera_handler(self.camera)

            self._init_camera_settings()
            self.camera_stream_raw.set_camera_handler(self.camera)

            self.reload_success = time.time()
            self.reset_error_all()
        else:
            self.raise_error("Could not connect camera, check error msg of camera handler.")

        if not init:
            self.logging.error(" ........ " + str(self.camera_streams.keys()))

        self.logging.debug("Camera connect done: " + str(self.connected))

        self.set_maintenance_mode(False)
        for stream in self.camera_streams:
            self.camera_streams[stream].reload_success = self.reload_success
            self.camera_streams[stream].reload_tried = self.reload_tried
            self.camera_streams[stream].reload_time = self.reload_time

    def _init_camera_validate(self):
        """
        check if camera works or device assignment has changed
        """
        if not birdhouse_env["test_video_devices"]:
            self.logging.debug("No validation")

        elif "/dev/picam" in self.source:
            self.logging.debug("No validation for /dev/picam")

        else:
            if ("video_devices_complete" in self.camera_scan and
                    self.source in self.camera_scan["video_devices_complete"]):
                camera_scans = self.camera_scan["video_devices_complete"]
                self.logging.debug(str(camera_scans[self.source]))
                if (self.source in camera_scans and "image" in camera_scans[self.source]
                        and camera_scans[self.source]["image"]):

                    if "source_id" in self.param and self.param["source_id"] is not None:
                        camera_id = self.param["source_id"]
                    else:
                        camera_id = camera_scans[self.source]["bus"]

                    camera_info = self.source + " (" + camera_id + ")"
                    self.logging.info("Camera validation: OK - " + camera_info)

                else:
                    if "source_id" in self.param and self.param["source_id"] is not None:
                        camera_id = self.param["source_id"]
                    else:
                        camera_id = camera_scans[self.source]["bus"]

                    camera_info = self.source + " (" + camera_id + ")"
                    self.logging.warning("Camera validation: FAILED - " + camera_info)
                    for device in camera_scans:
                        if camera_scans[device]["bus"] == camera_id and camera_scans[device]["image"]:
                            self.logging.warning("                 : looks like device assignment changed to " + device)
                            self.logging.warning("                 : use temporarily " + device + " as video device")
                            self.camera_scan_source = device
            else:
                self.logging.warning("Camera validation for " + self.source + " not possible. Camera scan:")
                self.logging.warning(str(self.camera_scan))

    def _init_camera_settings(self):
        """
        set resolution and identify max. resolution for USB cameras
        """
        self.logging.debug("Initialize camera settings ...")
        if self.camera is None or not self.camera.if_connected():
            return

        # set saturation, contrast, brightness
        self.camera.camera_create_test_image("set initial properties")
        available_settings = self.camera.get_properties_available()
        for key in available_settings:
            if key in self.param["image_presets"] and float(self.param["image_presets"][key]) != -1:
                self.logging.debug("Set properties: " + key + "=" + str(self.param["image_presets"][key]))
                self.camera.set_properties(key, float(self.param["image_presets"][key]))

        # set resolutions, define grop area
        self.camera.camera_create_test_image("get resolutions")
        current = self.camera.get_resolution()
        self.logging.info("- Current resolution: " + str(current))

        self.max_resolution = self.camera.get_resolution(maximum=True)
        self.logging.debug("- Maximum resolution: " + str(self.max_resolution))

        if "x" in self.param["image"]["resolution"]:
            self.camera.camera_create_test_image("set resolution")
            dimensions = self.param["image"]["resolution"].split("x")
            self.logging.debug("Set resolution for '" + self.id + "': " + str(dimensions))
            self.camera.set_resolution(width=float(dimensions[0]), height=float(dimensions[1]))

            self.camera.camera_create_test_image("get resolution")
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
            self.logging.info("- Resolution definition not supported (required format: '800x600'): " +
                              str(self.param["image"]["resolution"]))

        # return properties as values
        self.camera.camera_create_test_image("get properties")
        self.param["camera"] = self.camera.get_properties()
        self.logging.debug("Initialized camera settings for '" + self.id + "'.")

    def _init_microphone(self):
        """
        connect with the correct microphone
        """
        if "record_micro" in self.param:
            which_mic = self.param["record_micro"]
            if which_mic != "" and which_mic in self.microphones:
                self.micro = self.microphones[which_mic]
                micro_id = self.micro.id
                self.logging.info("Connected microphone '" + micro_id + "' to camera '" + self.id + "'.")
                return

            elif which_mic == "":
                self.micro = None
                self.logging.info("No microphone defined for '" + self.id + "'.")

        self.micro = None
        self.logging.warning("Could not connect a microphone to camera '" + self.id + "', check configuration!")

    def run(self):
        """
        Start recording for livestream, save images every x seconds, reload camera and connected devices.
        """
        similarity = 0
        count_paused = 0
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

                # if error reload from time to time
                if self.if_reconnect_on_error():
                    self.reconnect(directly=False)

                # check if camera is paused, wait with all processes ...
                if not self._paused:
                    count_paused = 0

                while self._paused and self._running:
                    if count_paused == 0:
                        self.logging.info("Recording images with " + self.id + " paused ...")
                        count_paused += 1
                    time.sleep(1)

                # Recording ...
                if not self.error and not self.config_update and not self.reload_camera:

                    # Video recording
                    if self.video.recording:
                        self.video_recording(current_time)

                    # Image recording (only while not recording video)
                    elif self.record:
                        self.image_recording(current_time, stamp, similarity, sensor_last)
                        self.image_recording_auto_light()

                    # Check and record active streams
                    self.measure_usage()

                # Slow down if other process with higher priority is running or error
                if (self.if_other_prio_process(self.id)
                        or self.if_only_lowres()
                        or self.video.processing
                        or self.error or not self.active):

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

                self.logging.info("Updating configuration and reconnecting CAMERA '" + self.id + "' (" +
                                  self.param["name"] + "/" + str(self.param["active"]) + ") ...")
                self.update_main_config()
                self.set_streams_active(active=True)
                self.reconnect(directly=True)

            # Define thread priority and waiting time depending on running tasks
            if self.active and self.record and not self.video.recording and not self.error:
                self.thread_set_priority(2)
                self.thread_wait()
            elif not self.active or self.error:
                self.thread_set_priority(7)
                if self.video.recording:
                    self.thread_wait(wait_time=0.04)

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

        Args:
            command (bool): if start or stop pause
        """
        self._paused = command

    def connect(self):
        """
        initial connect of all relevant streams and devices
        """
        self.logging.debug("Initial connect of all camera components for '" + self.id + "' ...")
        self._init_image_processing()
        self._init_video_processing()
        self._init_stream_raw()
        self._init_streams()
        if self.active:
            self.set_streams_active(active=True)
            time.sleep(1)
            self._init_camera_validate()
            self._init_camera(init=True)
        self._init_microphone()

        self.object = BirdhouseObjectDetection(self.id, self.config)
        self.object.start()
        self.initialized = True

    def reconnect(self, directly=False):
        """
        Reconnect from inside the thread or via API call

        Args:
            directly (bool): don't wait for next iteration
        Return:
            dict: information for API response
        """
        if directly:
            if self.active:
                self.set_streams_active(active=True)
                time.sleep(1)
                self._init_camera_validate()
                self._init_camera(init=True)
                if self.camera is None:
                    self._init_microphone()
                self.object.reconnect()
            self.reload_camera = False

        else:
            self.reload_camera = True
            self.config_update = True

        response = {"command": ["reconnect camera"], "camera": self.id}
        return response

    def video_recording(self, current_time):
        """
        Record video image for video, trigger video and audio creation when recording is stopped.

        Args:
            current_time (datetime): current time for logging
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
            image_time = self.camera_streams["camera_hires"].read_stream_image_time()
            image_delay = time.time() - image_time

            if self.image_last_id == 0 or self.image_last_id != image_id:
                image = self.camera_streams["camera_hires"].read_stream("record")
                self.image_last_id = image_id
            else:
                return

            self.video.image_size = self.image_size
            self.video.create_video_image(image=image, delay=image_delay)

            if self.image_size == [0, 0]:
                self.image_size = self.image.size_raw(image)
                self.video.image_size = self.image_size

            self.logging.debug(".... Video Recording: " + str(self.video.info["stamp_start"]) + " -> " + str(
                current_time.strftime("%H:%M:%S")))

    def video_recording_start(self):
        """
        start recording and set current image size
        """
        if not self.video.if_running():
            self.video.start()
            self.video.image_size = self.image_size

    def video_recording_cancel(self):
        """
        cancel video recording

        Returns:
            dict: information for API response
        """
        return self.video.record_cancel()

    def image_recording(self, current_time, stamp, similarity, sensor_last):
        """
        record images as defined in settings

        Args:
            current_time (datetime): current time in datetime format
            stamp (str): time stamp of measurement
            similarity (float): similarity value (not used at the moment)
            sensor_last (str): last time stamp of sensor measurement
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
            if image_hires is not None and not self.image.error and image_hires is not None and len(image_hires) > 0:
                image_compare = self.image.convert_to_gray_raw(image_hires)
                self.brightness = self.image.get_brightness_raw(image_hires)
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
                    "hires": self.img_support.filename("hires", stamp, self.id),
                    "hires_size": [width, height],
                    "hires_brightness": self.brightness,
                    "info": {},
                    "lowres": self.img_support.filename("lowres", stamp, self.id),
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
                    self.record_image_error_msg = ["img_error=" + str(self.image.error) +
                                                   "; img_len=" + str(len(image_hires))]
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
                self.logging.debug("Write sensor data to file ...")
                self.config.queue.entry_add(config="sensor", date="", key=sensor_stamp, entry=sensor_data)

            # if no error save image files
            if not self.error and not self.image.error and image_hires is not None:
                path_lowres = os.path.join(self.config.db_handler.directory("images"),
                                           self.img_support.filename("lowres", stamp, self.id))
                path_hires = os.path.join(self.config.db_handler.directory("images"),
                                          self.img_support.filename("hires", stamp, self.id))
                self.logging.debug("WRITE:" + path_lowres)
                self.image.write(filename=path_hires, image=image_hires)
                self.image.write(filename=path_lowres, image=image_hires,
                                 scale_percent=self.param["image"]["preview_scale"])

                if (self.detect_active and self.detect_settings["active"]
                        and image_hires is not None and os.path.exists(path_hires)):
                    self.object.add2queue_analyze_image(stamp, path_hires, image_hires, image_info)

                # !!! unclear what happens with this analyze image?

                self.record_image_error = False
                self.record_image_error_msg = []
                self.record_image_last = time.time()
                self.record_image_last_string = self.config.local_time().strftime('%d.%m.%Y %H:%M:%S')

            time.sleep(self._interval)
            self.previous_stamp = stamp

    def image_recording_active(self, current_time=-1, check_in_general=False):
        """
        check if image recording is currently active depending on settings (start and end time incl. sunset or sunrise)

        Args:
            current_time (datetime|int): current time, if not set get time fresh from the system
            check_in_general (bool): create recording time information for API
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

                self.logging.debug(" -> RECORD TIMES: from=" + record_from + "; to=" + record_to +
                                   "; sunrise=" + str(self.weather_sunrise) + "; sunset=" + str(self.weather_sunset) +
                                   "; weather_active=" + str(self.weather_active))

                start = int(record_rhythm_offset)
                while start < 60:
                    if start not in self.record_seconds:
                        self.record_seconds.append(start)  # !!! gets longer and longer! reset?
                    start += int(record_rhythm)

                if "sun" in record_from and self.weather_active and self.weather_sunrise is not None:
                    if "sunrise-1" in record_from:
                        record_from_hour = int(self.weather_sunrise.split(":")[0]) - 1
                        record_from_minute = int(self.weather_sunrise.split(":")[1])
                    elif record_from == "sunrise-0" or "sunrise+0" or "sunrise":
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
                                   str(record_from_minute) + "|" + str(record_to_hour_compare) + ":" +
                                   str(record_to_minute_compare) + ") " + str(int(hour)) + "/" +
                                   str(int(minute)) + "/" +
                                   str(int(second)) + " ... " + str(self.record_seconds))

                if int(second) in self.record_seconds or check_in_general:
                    if ((int(record_from_hour)*60)+int(record_from_minute)) <= ((int(hour)*60)+int(minute)) <= \
                            ((int(record_to_hour_compare)*60)+int(record_to_minute_compare)):
                        self.logging.debug(
                            " -> RECORD TRUE "+self.id+"  (" + str(record_from_hour) + ":" +
                            str(record_from_minute) + "-" +
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

    def image_recording_auto_light(self):
        """
        check brightness and switch on the light, if to dark and auto light is defined
        """
        if "camera_light" in self.param and "switch" in self.param["camera_light"]:
            light_relay = self.param["camera_light"]["switch"]

            if light_relay in self.relays:
                sunrise = self.config.weather.get_sunrise().split(":")
                sunset = self.config.weather.get_sunset().split(":")
                local_time = self.config.local_time()
                threshold = self.param["camera_light"]["threshold"]

                if self.brightness < threshold and not self.relays[light_relay].is_on():
                    self.relays[light_relay].switch_on()
                self.logging.info("Check brightness: " + str(self.brightness) + " / " + str(threshold))
                self.logging.info("Check timing:     sunrise=" + str(sunrise) +
                                  "; sunset=" + str(sunset) + "; time=" + str(local_time))
        else:
            self.logging.debug("Config file is not up-to-date, value 'camera_light' is missing.")

    def measure_usage(self, init=False):
        """
        measure usage from time to time

        Args:
            init (bool): initialize usage
        """
        if init:
            self.statistics.register(self.id.lower() + "_streams", "Streams " + self.id.upper())
            self.statistics.register(self.id.lower() + "_framerate", "Framerate " + self.id.upper())
            self.statistics.register(self.id.lower() + "_error", "Camera Error " + self.id.upper())
            self.statistics.register(self.id.lower() + "_raw_error", "Stream Error " + self.id.upper())

        else:
            self.logging.debug("Measure stream usage ...")

            count = 0
            for stream_id in self.camera_streams:
                count += self.camera_streams[stream_id].get_active_streams()

            self.statistics.set(self.id.lower() + "_streams", count)
            self.statistics.set(self.id.lower() + "_framerate", self.camera_stream_raw.get_framerate())
            self.statistics.set(self.id.lower() + "_error", self.if_error())
            self.statistics.set(self.id.lower() + "_raw_error", self.camera_stream_raw.if_error())

    def get_image_raw(self):
        """
        get raw image from respective stream

        Returns:
            numpy.ndarray: raw image
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
        get image for video stream, if camera is not connected or an error occurred, return an error image

        Args:
            stream_id (str): unique stream ID give from app
            stream_type (str): stream type: camera, normalized, setting
            stream_resolution (str): resolution: hires, lowres
            system_info (bool): add system info to the image
            wait (bool): wait a while for first image (defined in timeout)
        Returns:
            numpy.ndarray: image for stream
        """
        image = None
        stream = stream_type
        if stream_resolution != "":
            stream += "_" + stream_resolution

        if stream not in self.camera_streams:
            error_msg = "Stream '" + stream + "' does not exist."
            image = self.camera_streams[stream].read_error_image(error_msg, error_trigger="get_stream: stream '" +
                                                                 stream + "' not in self.camera_streams")
            self.raise_error(error_msg)
            return image

        elif self.camera_streams[stream].if_connected() and not self.camera_streams[stream].if_error():
            image = self.camera_streams[stream].read_stream(stream_id, system_info, wait)

        if self.camera_streams[stream].if_error() or not self.camera_streams[stream].if_connected():
            image = self.camera_streams[stream].read_error_image(error_msg="",
                                                                 error_trigger="get_stream: self.camera_streams['" +
                                                                 stream + "'].if_error()")
        elif self.if_error():
            image = self.camera_streams[stream].read_error_image(error_msg="", error_trigger="get_stream: if_error()")

        return image

    def get_stream_object_detection(self, stream_id, stream_type, stream_resolution="", system_info=False, wait=True):
        """
        get image with rendered labels of detected objects

        Args:
            stream_id (str): unique stream ID give from app
            stream_type (str): stream type: camera, normalized, setting
            stream_resolution (str): resolution: hires, lowres
            system_info (bool): add system info to the image
            wait (bool): wait a while for first image (defined in timeout)
        Returns:
            numpy.ndarray: image for stream incl. rendered object detections
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

        if self.object and self.object.detect_loaded and not self.if_error():
            path_hires = str(os.path.join(self.config.db_handler.directory("images"),
                                          "_temp_"+str(self.id)+"_"+str(stream_id)+".jpg"))
            try:
                self.image.write(path_hires, image, scale_percent=self.image_size_object_detection)
                img, detect_info = self.object.detect_objects.analyze(path_hires, self.detect_settings["threshold"],
                                                                      False)
                img = self.object.detect_visualize.render_detection(image, detect_info, 1,
                                                                    self.detect_settings["threshold"])
                if os.path.exists(path_hires):
                    os.remove(path_hires)
                return img
            except Exception as e:
                msg = "Object detection error: " + str(e)
                self.logging.error(msg)
                image = self.image.draw_text_raw(raw=image, text=msg, position=(20, -40), font=None, scale=0.6,
                                                 color=(255, 255, 255), thickness=1)

        elif not self.object or not self.object.detect_loaded:
            msg = "Object detection not loaded." + str(self.object.detect_loaded)
            image = self.image.draw_text_raw(raw=image, text=msg, position=(20, -40), font=None, scale=0.6,
                                             color=(255, 255, 255), thickness=1)

        return image

    def get_stream_image_id(self):
        """
        return current image id from stream raw

        Returns:
            int: current image id
        """
        return self.camera_stream_raw.read_stream_image_id()

    def get_stream_count(self):
        """
        identify amount of currently running streams

        Returns:
            int: amount of currently running streams
        """
        count = 0
        for stream_id in self.camera_streams:
            if self.camera_streams[stream_id].if_running():
                count += self.camera_streams[stream_id].get_active_streams()
        return count

    def get_stream_kill(self, ext_stream_id, int_stream_id):
        """
        check if stream has to be killed

        Args:
            ext_stream_id (str): external stream id defined by app
            int_stream_id (float): internal stream id defined by server
        Returns:
            bool: status if killed stream
        """
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

        Args:
            ext_stream_id (str): stream id defined by app
        """
        self.logging.debug("set_image_stream_kill: " + ext_stream_id)
        self.image_streams_to_kill[ext_stream_id] = datetime.now().timestamp()

    def set_streams_active(self, active=True):
        """
        set all streams active or inactive

        Args:
            active (bool): True for active and False for inactive
        """
        for stream_id in self.camera_streams:
            self.camera_streams[stream_id].active = active

    def get_camera_status(self, info="all"):
        """
        return all status and error information

        Args:
            info (str): define which information to get: all, properties
        Returns:
            dict: camera status information
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
            "active_device": self.camera_scan_source,
            "running": self.if_running(),
            "recording": self.video.recording,
            "processing": self.video.processing,
            "last_reload": time.time() - self.reload_success,

            "error_details": {},
            "error_details_msg": {},
            "error_details_health": {},
            "error": self.error,
            "error_msg": ",\n".join(self.error_msg),

            "image_cache_size": self.config_cache_size,
            "record_image": self.record,
            "record_image_error": self.record_image_error,
            "record_image_last": time.time() - self.record_image_last,
            "record_image_last_string": self.record_image_last_string,
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

        Args:
            param (dict): parameters given via API
        Returns:
            dict: API response
        """
        response = {}
        parameters = param["parameter"]
        setting_key = parameters[0]
        setting_value = parameters[1]
        available_settings = self.camera.get_properties_available("set")

        if setting_key in available_settings:
            self.camera.set_properties(key=setting_key, value=setting_value)
        else:
            self.raise_error("Error during change of camera settings: given key '"+setting_key+"' is not supported.")

        self.logging.info("Camera settings: " + str(parameters))
        self.logging.info("   -> available: " + str(available_settings))
        return response

    def set_system_info(self, active, line1="", line2="", color=""):
        """
        show system info in specific streams

        Args:
            active (bool): if active
            line1 (str): text for first line in big letters
            line2 (str): text for second line in small letters
            color ((int,int,int)): text color as (r,g,b)
        """
        self.camera_streams["camera_hires"].set_system_info(active, line1, line2, color)

    def set_system_info_lowres(self, active, sign="", color=""):
        """
        show system info in specific streams

        Args:
            active (bool): if active
            sign (str): sign to be displayed, should be a single character
            color ((int,int,int)): text color as (r,g,b)
        """
        self.camera_streams["camera_lowres"].set_system_info(active, sign, "", color)

    def get_available_devices(self):
        """
        identify available video devices

        Returns:
            dict: definition of available devices in different levels of detail:
                  video_devices_short, video_devices_complete
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

            birdhouse_initial_connect_msg[key] = ("initial_connect=" +
                                                  str(system["video_devices_complete"][key]["image"]) +
                                                  ", info=" + system["video_devices_complete"][key]["info"] +
                                                  ", shape=" + str(system["video_devices_complete"][key]["shape"]))

            camera_string = " - " + str(camera_count).rjust(2) + ": " + str(key).ljust(12) + " ("
            camera_string += system["video_devices_complete"][key]["info"].split(" (")[0].split(":")[0] + ") "

            just_value = 52
            if "error" in system["video_devices_complete"][key]:
                self.logging.info(camera_string.ljust(just_value) + " - ERROR: " +
                                  str(system["video_devices_complete"][key]["error"]))
                birdhouse_initial_connect_msg[key] += (", error='" + str(system["video_devices_complete"][key]["error"])
                                                       + "'")
            elif not birdhouse_env["test_video_devices"]:
                self.logging.info(camera_string.ljust(just_value) + " (w/o test)")
            else:
                self.logging.info(camera_string.ljust(just_value) + " - OK")

        self.available_devices = system
        return system

    def set_maintenance_mode(self, active=True, line1="", line2=""):
        """
        set maintenance_mode in all streams

        Args:
            active (bool): if active
            line1 (str): text for first line in big letters
            line2 (str): text for second line in small letters
        """
        if active:
            self.logging.info("Starting maintenance mode for CAMERA '" + self.id + " ... ")

        self.camera_stream_raw.set_maintenance_mode(active)
        for stream in self.camera_streams:
            self.camera_streams[stream].set_maintenance_mode(active, line1, line2, True)

        if not active:
            self.logging.info("Stopped maintenance mode for CAMERA '" + self.id + ". ")

    def set_connection_status(self, status):
        """
        spread connection status to all streams

        Args:
            status (bool): connection status
        """
        self.connected = status
        self.camera_stream_raw.connected = status
        for stream in self.camera_streams:
            self.camera_streams[stream].connected = status

    def slow_down_streams(self, slow_down=True):
        """
        slow down all video streams for this camera, e.g. while recording

        Args:
            slow_down (bool): slow down status to be set
        """
        self.camera_stream_raw.slow_down(slow_down)
        for stream in self.camera_streams:
            self.camera_streams[stream].slow_down(slow_down)

    def reset_image_presets(self):
        """
        reset image presets to default (delete configuration from main config file)

        Returns:
            dict: information for API response
        """
        self.logging.info("Resetting image presets for camera '" + self.id + "' ...")
        response = {"command": "reset-image-presets"}
        main_config = self.config.db_handler.read("main")
        camera_settings = main_config["devices"]["cameras"][self.id].copy()
        try:
            for key in camera_settings["image_presets"]:
                if key in camera_settings["camera"]:
                    camera_settings["image_presets"][key] = camera_settings["camera"][key][0]
                else:
                    del camera_settings["image_presets"][key]
            main_config["devices"]["cameras"][self.id] = camera_settings.copy()

            self.config.db_handler.write("main", "", main_config)
            self.update_main_config()
            self.reconnect()
            self.logging.info("Reset done.")

        except Exception as e:
            response["error"] = "Error while removing image presets: " + str(e)
            self.raise_error(response["error"])

        return response

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

    def if_error(self, message=False, length=False, details=False):
        """
        check for camera error and errors in streams

        Args:
            message (bool): if True return error messages
            length (bool): if True return amount of error messages
            details (bool): if True return details as string
        Returns:
            Any: error information
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

    def if_only_lowres(self):
        """
        check if only lowres is requested

        Returns:
            bool: status if currently requested streams are only lowres
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

    def if_reconnect_on_error(self):
        """
        check if reconnect is required (error, time since last reconnect, ...)

        Returns:
            bool: status if to be reconnected
        """
        reload = False
        self.logging.debug("Check if reload on errors is required ...")
        if time.time() > self.reload_tried + self._interval_reload_if_error:
            if self.error:
                reload = True
            if self.camera_stream_raw.error:
                reload = True

        if reload:
            self.logging.info("....... Reload CAMERA '" + self.id + "' due to errors --> " +
                              str(round(self.reload_tried, 1)) + " + " +
                              str(round(self._interval_reload_if_error, 1)) + " > " +
                              str(round(time.time(), 1)))
            self.logging.info("        " + self.if_error(details=True))

        return reload

    def update_main_config(self):
        """
        reread all relevant settings after update of the main configuration
        """
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
        self.camera_scan_source = None

        self.image_size = [0, 0]
        self.image_size_lowres = [0, 0]
        self.image_last_raw = None
        self.image_last_raw_time = 0
        self.image_last_edited = None
        self.image_count_empty = 0
        self.image_time_last = {}
        self.image_time_current = {}
        self.image_time_rotate = {}
        self.image_streams = {}
        self.image_streams_to_kill = {}
        self.image_size_object_detection = self.detect_settings["detection_size"]

        self.previous_image = None
        self.previous_stamp = "000000"

        if "video" in self.param and "max_length" in self.param["video"]:
            self.video.max_length = self.param["video"]["max_length"]

        if self.camera:
            self.camera.source = self.param["source"]
            self.camera_stream_raw.param = self.param
            self.camera_stream_raw.source = self.param["source"]
            self.camera_stream_raw.fps_max = self.param["image"]["framerate"]
            self.camera_stream_raw.set_duration_from_framerate()

            for stream in self.camera_streams:
                self.camera_streams[stream].param = self.param
                self.camera_streams[stream].image.param = self.param
                self.camera_streams[stream].source = self.param["source"]
                self.camera_streams[stream].initial_connect_msg = self.initial_connect_msg
                self.camera_streams[stream].fps_max = self.param["image"]["framerate"]
                self.camera_streams[stream].set_duration_from_framerate()

        self.image.param = self.param
        self.img_support.param = self.param
        self.video.param = self.param
        self.object.param = self.param

        self.config.update["camera_" + self.id] = False
        self.reload_camera = True
