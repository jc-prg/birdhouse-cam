import os
import time
import logging
import numpy as np
import ffmpeg
import cv2
import psutil
import threading

from skimage.metrics import structural_similarity as ssim
from datetime import datetime

from modules.presets import *
from modules.bh_class import BirdhouseCameraClass, BirdhouseClass
from modules.bh_ffmpeg import BirdhouseFfmpegTranscoding

#from better_ffmpeg_progress import FfmpegProcess
#from ffmpeg import FFmpeg, Progress


class BirdhouseCameraHandler(BirdhouseCameraClass):

    def __init__(self, camera_id, source, config, param):
        BirdhouseCameraClass.__init__(self, class_id=camera_id+"-ctrl", class_log="cam-other",
                                      camera_id=camera_id, config=config)

        if "/dev/" not in str(source):
            source = "/dev/video" + str(source)

        self.source = source
        self.stream = None
        self.property_keys = None
        self.properties_get = None
        self.properties_not_used = None
        self.properties_set = None

        self.logging.info("Starting CAMERA support for '"+self.id+":"+source+"' ...")

        self.connect()
        self.get_properties(key="init")
        self.set_properties(key="init")

    def read(self):
        if self.if_error():
            return
        try:
            ref, raw = self.stream.read()
            return raw
        except Exception as err:
            self.raise_error("- Error reading first image from camera '"+self.source+"': " + str(err))
            return

    def connect(self):
        self.reset_error()
        try:
            self.stream = cv2.VideoCapture(self.source, cv2.CAP_V4L)
            time.sleep(1)
        except Exception as err:
            self.raise_error("- Error connecting to camera '" + self.source + "': " + str(err))
            return
        self.read()

    def reconnect(self):
        self.disconnect()
        self.connect()

    def disconnect(self):
        if self.stream is not None:
            try:
                self.stream.release()
            except cv2.error as err:
                self.logging.debug("- Release of camera did not work: " + str(err))
        else:
            self.logging.debug("- Camera not yet connected.")

    def set_properties(self, key, value=""):
        """
        set camera parameter ...
        -----------------------------
        0. CV_CAP_PROP_POS_MSEC Current position of the video file in milliseconds.
        1. CV_CAP_PROP_POS_FRAMES 0-based index of the frame to be decoded/captured next.
        2. CV_CAP_PROP_POS_AVI_RATIO Relative position of the video file
        3. CV_CAP_PROP_FRAME_WIDTH Width of the frames in the video stream.
        4. CV_CAP_PROP_FRAME_HEIGHT Height of the frames in the video stream.
        5. CV_CAP_PROP_FPS Frame rate.
        6. CV_CAP_PROP_FOURCC 4-character code of codec.
        7. CV_CAP_PROP_FRAME_COUNT Number of frames in the video file.
        8. CV_CAP_PROP_FORMAT Format of the Mat objects returned by retrieve() .
        9. CV_CAP_PROP_MODE Backend-specific value indicating the current capture mode.
        10. CV_CAP_PROP_BRIGHTNESS Brightness of the image (only for cameras). [0..255]
        11. CV_CAP_PROP_CONTRAST Contrast of the image (only for cameras). [0..255]
        12. CV_CAP_PROP_SATURATION Saturation of the image (only for cameras). [0..255]
        13. CV_CAP_PROP_HUE Hue of the image (only for cameras).
        14. CV_CAP_PROP_GAIN Gain of the image (only for cameras). [0..127]
        15. CV_CAP_PROP_EXPOSURE Exposure (only for cameras). [-7..-1] ... tbc.
        16. CV_CAP_PROP_CONVERT_RGB Boolean flags indicating whether images should be converted to RGB.
        17. CV_CAP_PROP_WHITE_BALANCE Currently unsupported [4000..7000]
        """
        self.properties_set = ["saturation", "brightness", "contrast", "framerate", "exposure",
                               "hue", "auto_white_balance", "auto_exposure", "gamma", "gain"]
        if key == "init":
            return

        try:
            if key == "auto_exposure":
                self.stream.set(cv2.CAP_PROP_AUTO_EXPOSURE, float(value))
            elif key == "auto_white_balance":
                self.stream.set(cv2.CAP_PROP_AUTO_WB, float(value))
            elif key == "brightness":
                self.stream.set(cv2.CAP_PROP_BRIGHTNESS, float(value))
            elif key == "contrast":
                self.stream.set(cv2.CAP_PROP_CONTRAST, float(value))
            elif key == "exposure":
                self.stream.set(cv2.CAP_PROP_EXPOSURE, float(value))
            elif key == "fps":
                self.stream.set(cv2.CAP_PROP_FPS, float(value))
            elif key == "gain":
                self.stream.set(cv2.CAP_PROP_GAIN, float(value))
            elif key == "gamma":
                self.stream.set(cv2.CAP_PROP_GAMMA, float(value))
            elif key == "hue":
                self.stream.set(cv2.CAP_PROP_HUE, float(value))
            elif key == "saturation":
                self.stream.set(cv2.CAP_PROP_SATURATION, float(value))
        except cv2.error as err:
            self.raise_error("Could not change camera setting '" + key + "': " + str(err))

    def get_properties_available(self, keys="get"):
        """
        return keys for all properties that are implemented at the moment
        """
        if keys == "get":
            return list(self.properties_get.keys())
        elif keys == "set":
            return self.properties_set
        return self.property_keys

    def get_properties(self, key=""):
        """
        get properties from camera
        """
        properties_not_used = ["pos_msec", "pos_frames", "pos_avi_ratio", "convert_rgb", "fourcc", "format", "mode",
                               "frame_count", "frame_width", "frame_height"]
        properties_get_array = ["brightness", "saturation", "contrast", "hue", "gain", "gamma",
                                "exposure", "auto_exposure", "auto_wb", "wb_temperature", "temperature",
                                "fps", "focus", "autofocus", "zoom"]

        if key == "init":
            self.properties_get = {}

        for prop_key in properties_get_array:
            command = "self.stream.get(cv2.CAP_PROP_" + prop_key.upper() + ")"
            value = self.stream.get(eval("cv2.CAP_PROP_" + prop_key.upper()))
            if prop_key not in self.properties_get:
                self.properties_get[prop_key] = [value, -1, -1]
            else:
                self.properties_get[prop_key][0] = value

        if key == "init":
            for prop_key in properties_get_array:
                # evaluate minimum
                if not prop_key.startswith("frame_"):
                    self.stream.set(eval("cv2.CAP_PROP_" + prop_key.upper()), -100000.0)
                    value = self.stream.get(eval("cv2.CAP_PROP_" + prop_key.upper()))
                    if value > 0:
                        self.stream.set(eval("cv2.CAP_PROP_" + prop_key.upper()), 0.0)
                        value = self.stream.get(eval("cv2.CAP_PROP_" + prop_key.upper()))
                    self.properties_get[prop_key][1] = value

                # evaluate maximum
                self.stream.set(eval("cv2.CAP_PROP_" + prop_key.upper()), 100000.0)
                value = self.stream.get(eval("cv2.CAP_PROP_" + prop_key.upper()))
                self.properties_get[prop_key][2] = value

                # set again current value
                self.stream.set(eval("cv2.CAP_PROP_" + prop_key.upper()), self.properties_get[prop_key][0])

        return self.properties_get

    def get_properties_image(self):
        """
        read image and get properties (-> fuer Regelkreislauf)
        """
        image_properties = {}
        raw = self.read()

        if raw is None:
            return image_properties

        if len(raw.shape) > 2:
            gray = cv2.cvtColor(raw, cv2.COLOR_BGR2GRAY)
        else:
            gray = raw

        try:
            cols, rows = gray.shape
            image_properties["brightness"] = np.sum(gray) / (255 * cols * rows)
        except cv2.error as err:
            self.raise_error("Could not measure brightness: " + str(err))

        try:
            image_properties["contrast"] = gray.std()
        except cv2.error as err:
            self.raise_error("Could not measure contrast: " + str(err))

        try:
            img_hsv = cv2.cvtColor(raw, cv2.COLOR_BGR2HSV)
            image_properties["saturation"] = img_hsv[:, :, 1].mean()
        except cv2.error as err:
            self.raise_error("Could not measure saturation: " + str(err))

        return image_properties

    def set_black_white(self):
        """
        set saturation to 0
        """
        try:
            self.stream.set(cv2.CAP_PROP_SATURATION, 0)
            return True
        except cv2.error as err:
            self.raise_error("Could not set to black and white: " + str(err))
            return False

    def set_resolution(self, width, height):
        """
        set camera resolution
        """
        try:
            self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            return True
        except cv2.error as err:
            self.raise_error("Could not set resolution: " + str(err))
            return False

    def get_resolution(self, maximum=False):
        """
        get camera resolution
        """
        if maximum:
            high_value = 10000
            self.set_resolution(width=high_value, height=high_value)
        width = self.stream.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = self.stream.get(cv2.CAP_PROP_FRAME_HEIGHT)
        return [width, height]


class BirdhouseImageProcessing(BirdhouseCameraClass):
    """
    modify encoded and raw images
    """

    def __init__(self, camera_id, config):
        BirdhouseCameraClass.__init__(self, class_id=camera_id+"-img", class_log="cam-img",
                                      camera_id=camera_id, config=config)

        self.frame = None

        self.text_default_position = (30, 40)
        self.text_default_scale = 0.8
        self.text_default_font = cv2.FONT_HERSHEY_SIMPLEX
        self.text_default_color = (255, 255, 255)
        self.text_default_thickness = 2

        self.img_camera_error = "camera_na.jpg"
        self.img_camera_error_v2 = "camera_na_v3.jpg"
        self.img_camera_error_v3 = "camera_na_v4.jpg"
        self.img_camara_error_server = "camera_na_server.jpg"

        self.error_camera = False
        self.error_image = {}

        self.logging.info("Connected IMAGE processing ("+self.id+") ...")

    def compare(self, image_1st, image_2nd, detection_area=None):
        """
        calculate structural similarity index (SSIM) of two images
        """
        if self.error_camera:
            return 0

        image_1st = self.convert_to_raw(image_1st)
        image_2nd = self.convert_to_raw(image_2nd)
        similarity = self.compare_raw(image_1st, image_2nd, detection_area)
        return similarity

    def compare_raw(self, image_1st, image_2nd, detection_area=None):
        """
        calculate structural similarity index (SSIM) of two images
        """
        if self.error_camera:
            return 0

        try:
            if len(image_1st) == 0 or len(image_2nd) == 0:
                self.raise_warning("Compare: At least one file has a zero length - A:" +
                                   str(len(image_1st)) + "/ B:" + str(len(image_2nd)))
                score = 0
        except Exception as e:
            self.raise_warning("Compare: At least one file has a zero length.")
            score = 0

        if detection_area is not None:
            image_1st, area = self.crop_raw(raw=image_1st, crop_area=detection_area, crop_type="relative")
            image_2nd, area = self.crop_raw(raw=image_2nd, crop_area=detection_area, crop_type="relative")
        else:
            area = [0, 0, 1, 1]

        try:
            self.logging.debug(self.id + "/compare 1: " + str(detection_area) + " / " + str(image_1st.shape))
            self.logging.debug(self.id + "/compare 2: " + str(area) + " / " + str(image_1st.shape))
            (score, diff) = ssim(image_1st, image_2nd, full=True)

        except Exception as e:
            self.raise_warning("Error comparing images (" + str(e) + ")")
            score = 0

        return round(score * 100, 1)

    def compare_raw_show(self, image_1st, image_2nd):
        """
        show in an image where the differences are
        """
        #image_1st = cv2.cvtColor(image_1st, cv2.COLOR_BGR2GRAY)
        #image_2nd = cv2.cvtColor(image_2nd, cv2.COLOR_BGR2GRAY)
        image_diff = cv2.subtract(image_2nd, image_1st)

        # color the mask red
        Conv_hsv_Gray = cv2.cvtColor(image_diff, cv2.COLOR_BGR2GRAY)
        ret, mask = cv2.threshold(Conv_hsv_Gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
        image_diff[mask != 255] = [0, 0, 255]

        image_diff = self.draw_area_raw(raw=image_diff, area=self.param["similarity"]["detection_area"],
                                        color=(0, 255, 255))

        return image_diff

    def convert_from_raw(self, raw):
        """
        convert from raw image to image // untested
        """
        try:
            r, buf = cv2.imencode(".jpg", raw)
            size = len(buf)
            image = bytearray(buf)
            return image
        except Exception as e:
            self.raise_error("Error convert RAW image -> image (" + str(e) + ")")
            return raw

    def convert_to_raw(self, image):
        """
        convert from device to raw image -> to be modifeid with CV2
        """
        if self.error_camera:
            return

        try:
            image = np.frombuffer(image, dtype=np.uint8)
            raw = cv2.imdecode(image, 1)
            return raw
        except Exception as e:
            self.raise_error("Error convert image -> RAW image (" + str(e) + ")")
            return

    def convert_to_gray_raw(self, raw):
        """
        convert image from RGB to gray scale image (e.g. for analyzing similarity)
        """
        # error in camera
        if self.error_camera:
            return raw

        # image already seems to be in gray scale
        if len(raw.shape) == 2:
            return raw

        # convert and catch possible errors
        try:
            gray = cv2.cvtColor(raw, cv2.COLOR_BGR2GRAY)
            return gray

        except Exception as e:
            self.raise_error("Could not convert image to gray scale (" + str(e) + ")")
            self.logging.error("Shape " + str(raw.shape))
            return raw

    def convert_from_gray_raw(self, raw):
        """
        convert image from RGB to gray scale image (e.g. for analyzing similarity)
        """
        # error in camera
        if self.error_camera:
            return raw

        # convert and catch possible errors
        try:
            color = cv2.cvtColor(raw, cv2.COLOR_GRAY2BGR)
            return color

        except Exception as e:
            self.raise_error("Could not convert image back from gray scale (" + str(e) + ")")
            self.logging.error("Shape " + str(raw.shape))
            return raw

    def crop(self, image, crop_area, crop_type="relative"):
        """
        crop encoded image
        """
        raw = self.convert_to_raw(image)
        raw = self.crop_raw(raw, crop_area, crop_type)
        image = self.convert_from_raw(raw)
        return image

    def crop_raw(self, raw, crop_area, crop_type="relative"):
        """
        crop image using relative dimensions (0.0 ... 1.0);
        ensure dimension is dividable by 2, which is required to create a video based on this images
        """
        try:
            height = raw.shape[0]
            width = raw.shape[1]

            if crop_type == "relative":
                (w_start, h_start, w_end, h_end) = crop_area
                x_start = int(round(width * w_start, 0))
                y_start = int(round(height * h_start, 0))
                x_end = int(round(width * w_end, 0))
                y_end = int(round(height * h_end, 0))
                crop_area = (x_start, y_start, x_end, y_end)
            else:
                (x_start, y_start, x_end, y_end) = crop_area

            width = x_end - x_start
            height = y_end - y_start
            if round(width / 2) != width / 2:
                x_end -= 1
            if round(height / 2) != height / 2:
                y_end -= 1

            self.logging.debug("H: " + str(y_start) + "-" + str(y_end) + " / W: " + str(x_start) + "-" + str(x_end))
            frame_cropped = raw[y_start:y_end, x_start:x_end]
            return frame_cropped, crop_area

        except Exception as e:
            self.raise_error("Could not crop image (" + str(e) + ")")

        return raw, (0, 0, 1, 1)

    @staticmethod
    def crop_area_pixel(resolution, area, dimension=True):
        """
        calculate start & end pixel for relative area
        """
        if "x" in resolution:
            resolution = resolution.split("x")
        width = int(resolution[0])
        height = int(resolution[1])

        (w_start, h_start, w_end, h_end) = area
        x_start = int(round(width * w_start, 0))
        y_start = int(round(height * h_start, 0))
        x_end = int(round(width * w_end, 0))
        y_end = int(round(height * h_end, 0))
        x_width = x_end - x_start
        y_height = y_end - y_start
        if dimension:
            pixel_area = (x_start, y_start, x_end, y_end, x_width, y_height)
        else:
            pixel_area = (x_start, y_start, x_end, y_end)

        return pixel_area

    def draw_text(self, image, text, position=None, font=None, scale=None, color=None, thickness=0):
        """
        Add text on image
        """
        raw = self.convert_to_raw(image)
        raw = self.draw_text_raw(raw, text, position=position, font=font, scale=scale, color=color, thickness=thickness)
        image = self.convert_from_raw(raw)
        return image

    def draw_text_raw(self, raw, text, position=None, font=None, scale=None, color=None, thickness=0):
        """
        Add text on image
        """
        if position is None:
            position = self.text_default_position
        if font is None:
            font = self.text_default_font
        if scale is None:
            scale = self.text_default_scale
        if color is None:
            color = self.text_default_color
        if thickness == 0:
            thickness = self.text_default_thickness

        (x, y) = tuple(position)
        if x < 0 or y < 0:
            if "resolution_cropped" in self.param["image"] and \
                    self.param["image"]["resolution_cropped"] != (0, 0):
                (width, height) = self.param["image"]["resolution_cropped"]
            else:
                height = raw.shape[0]
                width = raw.shape[1]
                self.param["image"]["resolution_cropped"] = (width, height)
            if x < 0:
                x = width + x
            if y < 0:
                y = height + y
            position = (int(x), int(y))

        param = str(text) + ", " + str(position) + ", " + str(font) + ", " + str(scale) + ", " + str(
            color) + ", " + str(thickness)
        self.logging.debug("draw_text_raw: "+param)
        try:
            raw = cv2.putText(raw, text, tuple(position), font, scale, color, thickness, cv2.LINE_AA)
        except Exception as e:
            self.raise_error("Could not draw text into image (" + str(e) + ")")
            self.logging.warning(" ... " + param)

        return raw

    # !!! check if to be moved to EditStream
    def draw_date(self, image, offset=None):
        date_information = self.config.local_time().strftime('%d.%m.%Y %H:%M:%S')

        font = self.text_default_font
        thickness = 1
        if self.param["image"]["date_time_color"]:
            color = self.param["image"]["date_time_color"]
        else:
            color = ""
        if self.param["image"]["date_time_position"]:
            position = self.param["image"]["date_time_position"]
        else:
            position = ""
        if offset is not None:
            position = (int(position[0] + offset[0]), int(position[1] + offset[1]))
        if self.param["image"]["date_time_size"]:
            scale = self.param["image"]["date_time_size"]
        else:
            scale = ""

        image = self.draw_text(image, date_information, position, font, scale, color, thickness)
        return image

    # !!! check if to be moved to EditStream
    def draw_date_raw(self, raw, overwrite_color=None, overwrite_position=None, offset=[0, 0]):
        date_information = self.config.local_time().strftime('%d.%m.%Y %H:%M:%S')

        font = self.text_default_font
        thickness = 1
        if self.param["image"]["date_time_color"]:
            color = self.param["image"]["date_time_color"]
        else:
            color = None
        if self.param["image"]["date_time_position"]:
            position = self.param["image"]["date_time_position"]
        else:
            position = None
        if offset is not None:
            position = (int(position[0] + offset[0]), int(position[1] + offset[1]))
        if self.param["image"]["date_time_size"]:
            scale = self.param["image"]["date_time_size"]
        else:
            scale = None

        if overwrite_color is not None:
            color = overwrite_color
        if overwrite_position is not None:
            position = overwrite_position
            thickness = 1
        raw = self.draw_text_raw(raw, date_information, position, font, scale, color, thickness)
        return raw

    def draw_area_raw(self, raw, area=(0, 0, 1, 1), color=(0, 0, 255), thickness=2):
        """
        draw as colored rectangle
        """
        try:
            height = raw.shape[0]
            width = raw.shape[1]
            (x_start, y_start, x_end, y_end, x_width, y_height) = self.crop_area_pixel([width, height], area)
            image = cv2.line(raw, (x_start, y_start), (x_start, y_end), color, thickness)
            image = cv2.line(image, (x_start, y_start), (x_end, y_start), color, thickness)
            image = cv2.line(image, (x_end, y_end), (x_start, y_end), color, thickness)
            image = cv2.line(image, (x_end, y_end), (x_end, y_start), color, thickness)
            return image

        except Exception as e:
            self.raise_warning("Could not draw area into the image (" + str(e) + ")")
            return raw

    def image_in_image_raw(self, raw, raw2, position=4, distance=10):
        """
        add a smaller image in a larger image,
        inspired by https://answers.opencv.org/question/231069/inserting-logo-in-an-image/
        """
        [w1, h1, ch1] = raw.shape
        [w2, h2, ch2] = raw2.shape
        self.logging.debug("Insert images into image: big="+str(w1)+","+str(h1)+" / small="+str(w2)+","+str(h2))
        # top left
        if position == 1:
            raw[distance:w2+distance, distance:h2+distance] = raw2
        # top right
        if position == 2:
            raw[distance:w2+distance, h1-(distance+h2):h1-distance] = raw2
        # bottom left
        if position == 3:
            raw[w1-(distance+w2):w1-distance, distance:h2+distance] = raw2
        # bottom right
        if position == 4:
            raw[w1-(distance+w2):w1-distance, h1-(distance+h2):h1-distance] = raw2

        return raw

    # !!! Check if still required ....
    def image_error_info_raw(self, error_msg, reload_time, info_type="complete"):
        """
        add error information to image
        """
        if info_type == "complete":
            raw = self.image_error_raw(image=self.img_camera_error_v2)

            line_position = 160
            msg = self.id + ": " + self.param["name"]
            raw = self.draw_text_raw(raw=raw, text=msg, position=(20, line_position), font=None, scale=1,
                                     color=(0, 0, 255), thickness=2)

            line_position += 40
            msg = "Device: type=" + self.param["type"] + ", active=" + str(self.param["active"]) + ", source=" + str(
                self.param["source"])
            msg += ", resolution=" + self.param["image"]["resolution"]
            raw = self.draw_text_raw(raw=raw, text=msg, position=(20, line_position), font=None, scale=0.6,
                                     color=(0, 0, 255), thickness=1)

            if len(error_msg) > 0:
                line_position += 30
                msg = "Last Cam Error: " + error_msg[len(error_msg) - 1] + " [#" + str(len(error_msg)) + "]"
                raw = self.draw_text_raw(raw=raw, text=msg, position=(20, line_position), font=None, scale=0.6,
                                         color=(0, 0, 255), thickness=1)

            if len(self.error_msg) > 0:
                line_position += 30
                msg = "Last Img Error: " + self.error_msg[len(self.error_msg) - 1] + " [#" + str(len(error_msg)) + "]"
                raw = self.draw_text_raw(raw=raw, text=msg, position=(20, line_position), font=None, scale=0.6,
                                         color=(0, 0, 255), thickness=1)

            line_position += 30
            msg = "Last Reconnect: " + str(round(time.time() - reload_time)) + "s"
            raw = self.draw_text_raw(raw=raw, text=msg, position=(20, line_position), font=None, scale=0.6,
                                     color=(0, 0, 255), thickness=1)

            details = True
            if details:
                line_position += 30
                msg = "CPU Usage: " + str(psutil.cpu_percent(interval=1, percpu=False)) + "% "
                msg += "(" + str(psutil.cpu_count()) + " CPU)"
                raw = self.draw_text_raw(raw=raw, text=msg, position=(20, line_position), font=None, scale=0.6,
                                         color=(0, 0, 255), thickness=1)

                line_position += 30
                total = psutil.virtual_memory().total
                total = round(total / 1024 / 1024)
                used = psutil.virtual_memory().used
                used = round(used / 1024 / 1024)
                percentage = psutil.virtual_memory().percent
                msg = "Memory: total=" + str(total) + "MB, used=" + str(used) + "MB (" + str(percentage) + "%)"
                raw = self.draw_text_raw(raw=raw, text=msg, position=(20, line_position), font=None, scale=0.6,
                                         color=(0, 0, 255), thickness=1)

            line_position += 40
            raw = self.draw_date_raw(raw=raw, overwrite_color=(0, 0, 255), overwrite_position=(20, line_position))

        elif info_type == "empty":
            raw = self.image_error_raw(image=self.img_camera_error_v3)

        else:
            raw = self.image_error_raw(image=self.img_camera_error_v3)
            raw = self.draw_text_raw(raw=raw, text=self.id + ": " + self.param["name"],
                                     position=(20, 40), color=(255, 255, 255), thickness=2)
            raw = self.draw_date_raw(raw=raw, overwrite_color=(255, 255, 255), overwrite_position=(20, 80))

        return raw

    # !!! Check if still required ....
    def image_error_raw(self, reload=False, image=""):
        """
        return image with error message
        """
        if len(image) == 0:
            image = self.img_camera_error_v2

        if self.param["image"]["resolution"] and "x" in self.param["image"]["resolution"]:
            resolution = self.param["image"]["resolution"].split("x")
        else:
            resolution = [800, 600]
        area = (0, 0, int(resolution[0]), int(resolution[1]))

        if image not in self.error_image or self.error_image[image] is None or reload:
            filename = os.path.join(self.config.main_directory, self.config.directories["data"], image)
            raw = cv2.imread(filename)
            raw, area = self.crop_raw(raw=raw, crop_area=area, crop_type="absolute")
            self.error_image[image] = raw.copy()
            return raw.copy()
        else:
            return self.error_image[image].copy()

    # !!! Check if still required ....
    def normalize_raw(self, raw):
        """
        apply presets per camera to image -> implemented = crop to given values
        """
        if self.error_camera:
            return

        normalized, area = self.crop_raw(raw=raw, crop_area=self.param["image"]["crop"], crop_type="relative")
        self.param["image"]["crop_area"] = area
        self.param["image"]["resolution_cropped"] = [area[2] - area[0], area[3] - area[1]]

        # --> the following part doesn't work at the moment, self.param["image"]["crop_area"] somewhere is set wrong
        #
        #        if "crop_area" not in self.param["image"]:
        #            normalized, self.param["image"]["crop_area"] = self.crop_raw(raw=raw, crop_area=self.param["image"]["crop"],
        #                                                                         crop_type="relative")
        #        else:
        #            normalized, self.param["image"]["crop_area"] = self.crop_raw(raw=raw,
        #                                                                         crop_area=self.param["image"]["crop_area"],
        #                                                                         crop_type="pixel")

        if "black_white" in self.param["image"] and self.param["image"]["black_white"] is True:
            normalized = self.convert_to_gray_raw(normalized)
            normalized = self.convert_from_gray_raw(normalized)

        # rotate     - not implemented yet
        # resize     - not implemented yet
        # saturation - not implemented yet

        # see https://www.programmerall.com/article/5684321533/

        return normalized

    # !!! Check if still required ....
    def normalize_error_raw(self, raw):
        """
        apply presets per camera to image -> implemented = crop to given values
        """
        if "crop_area" not in self.param["image"] or self.param["image"]["crop_area"] == (0, 0, 0, 0):
            [start_x, start_y, end_x, end_y] = self.param["image"]["crop"]
            end_x = start_x + end_x
            start_x = 0
            area = [start_x, start_y, end_x, end_y]
            normalized, self.param["image"]["crop_area"] = self.crop_raw(raw=raw, crop_area=area,
                                                                         crop_type="relative")
        else:
            [start_x, start_y, end_x, end_y] = self.param["image"]["crop_area"]
            end_x = start_x + end_x
            start_x = 0
            area = [start_x, start_y, end_x, end_y]
            normalized, self.param["image"]["crop_area"] = self.crop_raw(raw=raw,
                                                                         crop_area=area,
                                                                         crop_type="pixel")

        # rotate     - not implemented yet
        # resize     - not implemented yet
        # saturation - not implemented yet
        return normalized

    def rotate_raw(self, raw, degree):
        """
        rotate image
        """
        self.logging.debug("Rotate image " + str(degree) + " ...")
        rotate_degree = "don't rotate"
        if int(degree) == 90:
            rotate_degree = cv2.ROTATE_90_CLOCKWISE
        elif int(degree) == 180:
            rotate_degree = cv2.ROTATE_180
        elif int(degree) == 270:
            rotate_degree = cv2.ROTATE_90_COUNTERCLOCKWISE
        try:
            if rotate_degree != "don't rotate":
                raw = cv2.rotate(raw, rotate_degree)
            return raw
        except Exception as e:
            self.raise_error("Could not rotate image (" + str(e) + ")")
            return raw

    def size(self, image):
        """
        Return size of raw image
        """
        frame = self.convert_to_raw(image)
        try:
            height = frame.shape[0]
            width = frame.shape[1]
            return [width, height]
        except Exception as e:
            self.raise_warning("Could not analyze image (" + str(e) + ")")
            return [0, 0]

    def size_raw(self, raw, scale_percent=100):
        """
        Return size of raw image
        """
        try:
            if scale_percent != 100:
                width = int(raw.shape[1] * float(scale_percent) / 100)
                height = int(raw.shape[0] * float(scale_percent) / 100)
                raw = cv2.resize(raw, (width, height))
            height = raw.shape[0]
            width = raw.shape[1]
            return [width, height]
        except Exception as e:
            self.raise_warning("Could not analyze image (" + str(e) + ")")
            return [0, 0]

    def resize_raw(self, raw, scale_percent=100, scale_size=None):
        """
        resize raw image
        """
        self.logging.debug("Resize image ("+str(scale_percent)+"% / "+str(scale_size)+")")
        if scale_size is not None:
            [width, height] = scale_size
            try:
                raw = cv2.resize(raw, (width, height))
            except Exception as e:
                self.raise_error("Could not resize raw image: " + str(e))
        elif scale_percent != 100:
            [width, height] = self.size_raw(raw, scale_percent=scale_percent)
            try:
                raw = cv2.resize(raw, (width, height))
            except Exception as e:
                self.raise_error("Could not resize raw image: " + str(e))
        return raw


class BirdhouseVideoProcessing(threading.Thread, BirdhouseCameraClass):
    """
    Record videos: start and stop; from all pictures of the day
    """

    def __init__(self, camera_id, camera, config):
        """
        Initialize new thread and set inital parameters
        """
        threading.Thread.__init__(self)
        BirdhouseCameraClass.__init__(self, class_id=camera_id+"-video", class_log="cam-video",
                                      camera_id=camera_id, config=config)

        self.camera = camera
        self.name = self.param["name"]
        self.directory = self.config.db_handler.directory("videos")
        self.queue_create = []
        self.queue_trim = []
        self.queue_wait = 10

        self.record_video_info = None
        self.image_size = [0, 0]
        self.recording = False
        self.processing = False
        self.max_length = 60

        self.output_codec = {"vcodec": "libx264", "crf": 18}
        self.ffmpeg_cmd = "ffmpeg -f image2 -r {FRAMERATE} -i {INPUT_FILENAMES} " + \
                          "-vcodec libx264 -crf 18 {OUTPUT_FILENAME}"
        self.ffmpeg_trim = "ffmpeg -y -i {INPUT_FILENAME} -r {FRAMERATE} -vcodec libx264 -crf 18 " + \
                           "-ss {START_TIME} -to {END_TIME} {OUTPUT_FILENAME}"
        # self.ffmpeg = BirdhouseFfmpegProcessing(camera_id, camera, config)

        self.ffmpeg = BirdhouseFfmpegTranscoding(self.id, self.config)

        # Other working options:
        # self.ffmpeg_cmd  += "-b 1000k -strict -2 -vcodec libx264 -profile:v main -level 3.1 -preset medium - \
        #                      x264-params ref=4 -movflags +faststart -crf 18"
        # self.ffmpeg_cmd  += "-c:v libx264 -pix_fmt yuv420p"
        # self.ffmpeg_cmd  += "-profile:v baseline -level 3.0 -crf 18"
        # self.ffmpeg_cmd  += "-vcodec libx264 -preset fast -profile:v baseline -lossless 1 -vf \
        #                     \"scale=720:540,setsar=1,pad=720:540:0:0\" -acodec aac -ac 2 -ar 22050 -ab 48k"

        # self.ffmpeg_trim  = "ffmpeg -y -i {INPUT_FILENAME} -c copy -ss {START_TIME} -to {END_TIME} {OUTPUT_FILENAME}"
        self.count_length = 8
        self.info = {
            "start": 0,
            "start_stamp": 0,
            "status": "ready"
        }
        self._running = False

    def run(self):
        """
        Initialize, set initial values
        """
        self._running = True
        self.logging.info("Starting VIDEO processing for '"+self.id+"' ...")
        if "video" in self.param and "max_length" in self.param["video"]:
            self.max_length = self.param["video"]["max_length"]
            self.logging.debug("Set max video recording length for " + self.id + " to " + str(self.max_length))
        else:
            self.logging.debug("Use default max video recording length for " + self.id + " = " + str(self.max_length))

        count = 0
        while self._running:
            time.sleep(1)
            count += 1
            if count >= self.queue_wait:
                count = 0

                # create short videos
                if len(self.queue_create) > 0:
                    self.config.async_running = True
                    [filename, stamp, date] = self.queue_create.pop()

                    self.logging.info("Start day video creation (" + filename + "): " + stamp + " - " + date + ")")
                    response = self.create_video_day(filename=filename, stamp=stamp, date=date)

                    if response["result"] == "OK":
                        self.config.queue.entry_add(config="videos", date="", key=stamp, entry=response["data"])
                        self.config.async_answers.append(["CREATE_DAY_DONE", date, response["result"]])
                    else:
                        self.config.async_answers.append(["CREATE_DAY_ERROR", date, response["result"]])
                    self.config.async_running = False

                # create short videos
                if len(self.queue_trim) > 0:
                    self.config.async_running = True
                    [video_id, start, end] = self.queue_trim.pop()

                    self.logging.info("Start video trimming (" + video_id + "): " + str(start) + " - " + str(end) + ")")
                    response = self.create_video_trimmed(video_id, start, end)
                    self.config.async_answers.append(["TRIM_DONE", video_id, response["result"]])
                    self.config.async_running = True

            self.health_signal()

        self.logging.info("Stopped VIDEO processing for '"+self.id+"'.")

    def stop(self):
        """
        ending functions (nothing at the moment)
        """
        if self.recording:
            self.record_stop()
            while self.recording:
                self.logging.info("Stopped recording for shut down. Please wait ...")
                time.sleep(1)

        self._running = False

    def status(self):
        """
        Return recording status
        """
        return self.record_video_info.copy()

    def filename(self, file_type="image"):
        """
        generate filename for images
        """
        if file_type == "video":
            return self.config.filename_image(image_type="video", timestamp=self.info["date_start"], camera=self.id)
        elif file_type == "thumb":
            return self.config.filename_image(image_type="thumb", timestamp=self.info["date_start"], camera=self.id)
        elif file_type == "vimages":
            return self.config.filename_image(image_type="vimages", timestamp=self.info["date_start"], camera=self.id)
        else:
            return

    def record_start(self):
        """
        start video recoding
        """
        response = {"command": ["start recording"]}

        if self.camera.active and not self.camera.error and not self.recording:
            self.logging.info("Starting video recording (" + self.id + ") ...")
            self.recording = True
            current_time = self.config.local_time()
            self.info = {
                "date": current_time.strftime('%d.%m.%Y %H:%M:%S'),
                "date_start": current_time.strftime('%Y%m%d_%H%M%S'),
                "stamp_start": current_time.timestamp(),
                "status": "recording",
                "camera": self.id,
                "camera_name": self.name,
                "directory": self.directory,
                "image_count": 0
            }
        elif not self.camera.active:
            response["error"] = "camera is not active " + self.camera.id
        elif self.recording:
            response["error"] = "camera is already recording " + self.camera.id
        return response

    def record_stop(self):
        """
        stop video recoding
        """
        response = {"command": ["stop recording"]}
        if self.camera.active and not self.camera.error and self.recording:
            self.logging.info("Stopping video recording (" + self.id + ") ...")
            current_time = self.config.local_time()
            self.info["date_end"] = current_time.strftime('%Y%m%d_%H%M%S')
            self.info["stamp_end"] = current_time.timestamp()
            self.info["status"] = "processing"
            self.info["length"] = round(self.info["stamp_end"] - self.info["stamp_start"], 2)
            if float(self.info["length"]) > 1:
                self.info["framerate"] = round(float(self.info["image_count"]) / float(self.info["length"]), 2)
            else:
                self.info["framerate"] = 0
            self.logging.info("---------------------> Length: "+str(self.info["length"]))
            self.logging.info("---------------------> Count: "+str(self.info["image_count"]))
            self.logging.info("---------------------> FPS: "+str(self.info["framerate"]))
            self.recording = False
            self.create_video()
            self.info["status"] = "finished"
            self.config.queue.entry_add(config="videos", date="", key=self.info["date_start"], entry=self.info.copy())
        elif not self.camera.active:
            response["error"] = "camera is not active " + self.camera.id
        elif not self.recording:
            response["error"] = "camera isn't recording " + self.camera.id
        return response

    def record_stop_auto(self):
        """
        Check if maximum length is achieved
        """
        if self.info["status"] == "recording":
            max_time = float(self.info["stamp_start"] + self.max_length)
            if max_time < float(self.config.local_time().timestamp()):
                self.logging.info("Maximum recording time achieved ...")
                self.logging.info(str(max_time) + " < " + str(self.config.local_time().timestamp()))
                return True
        return False

    def record_info(self):
        """
        Get info of recording
        """
        if self.recording:
            self.info["length"] = round(self.config.local_time().timestamp() - self.info["stamp_start"], 1)
        elif self.processing:
            self.info["length"] = round(self.info["stamp_end"] - self.info["stamp_start"], 1)

        self.info["image_size"] = self.image_size

        if float(self.info["length"]) > 1:
            self.info["framerate"] = round(float(self.info["image_count"]) / float(self.info["length"]), 1)
        else:
            self.info["framerate"] = 0

        return self.info

    def create_video(self):
        """
        Create video from images using ffmpeg
        """
        self.processing = True
        self.logging.info("Start video creation with ffmpeg ...")

        input_filenames = os.path.join(self.config.db_handler.directory("videos"), self.filename("vimages") + "%" +
                                       str(self.count_length).zfill(2) + "d.jpg")
        output_filename = os.path.join(self.config.db_handler.directory("videos"), self.filename("video"))

        success = self.ffmpeg.create_video(input_filenames, self.info["framerate"], output_filename)
        if not success:
            self.processing = False
            return

        self.info["thumbnail"] = self.filename("thumb")
        cmd_thumb = "cp " + os.path.join(self.config.db_handler.directory("videos"),
                                         self.filename("vimages") + str(1).zfill(self.count_length) + ".jpg "
                                         ) + os.path.join(self.config.db_handler.directory("videos"),
                                                          self.filename("thumb"))
        cmd_delete = "rm " + os.path.join(self.config.db_handler.directory("videos"),
                                          self.filename("vimages") + "*.jpg")
        try:
            self.logging.info(cmd_thumb)
            message = os.system(cmd_thumb)
            self.logging.debug(message)

            self.logging.info(cmd_delete)
            message = os.system(cmd_delete)
            self.logging.debug(message)

        except Exception as err:
            self.raise_error("Error during video creation (thumbnail/cleanup): " + str(err))
            self.processing = False
            return

        self.processing = False
        self.logging.info("OK.")
        return

    def create_video_image(self, image):
        """
        Save image
        """
        self.info["image_count"] += 1
        self.info["image_files"] = self.filename("vimages")
        self.info["video_file"] = self.filename("video")
        filename = self.info["image_files"] + str(self.info["image_count"]).zfill(self.count_length) + ".jpg"
        path = os.path.join(self.directory, filename)
        self.logging.debug("Save image as: " + path)

        try:
            self.logging.debug("Write  image '" + path + "')")
            return cv2.imwrite(path, image)
        except Exception as e:
            self.info["image_count"] -= 1
            self.raise_error("Could not save image '" + filename + "': " + str(e))

    def create_video_day(self, filename, stamp, date):
        """
        Create daily video from all single images available
        """
        camera = self.id
        cmd_videofile = "video_" + camera + "_" + stamp + ".mp4"
        cmd_thumbfile = "video_" + camera + "_" + stamp + "_thumb.jpeg"
        cmd_tempfiles = "img_" + camera + "_" + stamp + "_"
        framerate = 20

        self.logging.info("Remove old files from '" + self.config.db_handler.directory("videos_temp") + "' ...")
        cmd_rm = "rm " + self.config.db_handler.directory("videos_temp") + "*"
        self.logging.debug(cmd_rm)
        try:
            message = os.system(cmd_rm)
            if message != 0:
                self.raise_warning("Error during day video creation: remove old temp image files.")
        except Exception as e:
            self.raise_warning("Error during day video creation: " + str(e))

        self.logging.info("Copy files to temp directory '" + self.config.db_handler.directory("videos_temp") + "' ...")
        cmd_copy = "cp " + self.config.db_handler.directory("images") + filename + "* " + \
                   self.config.db_handler.directory("videos_temp")
        self.logging.debug(cmd_copy)
        try:
            message = os.system(cmd_copy)
            if message != 0:
                response = {"result": "error", "reason": "copy temp image files", "message": message}
                self.raise_error("Error during day video creation: copy temp image files.")
                return response
        except Exception as e:
            self.raise_error("Error during day video creation: " + str(e))

        self.logging.info("Rename files to prepare the video creation ...")
        cmd_filename = self.config.db_handler.directory("videos_temp") + cmd_tempfiles
        cmd_rename = "i=0; for fi in " + self.config.db_handler.directory("videos_temp") + \
                     "image_*; do mv \"$fi\" $(printf \""
        cmd_rename += cmd_filename + "%05d.jpg\" $i); i=$((i+1)); done"
        self.logging.debug(cmd_rename)
        try:
            message = os.system(cmd_rename)
            if message != 0:
                response = {"result": "error", "reason": "rename temp image files", "message": message}
                self.raise_error("Error during day video creation: rename temp image files.")
                return response
        except Exception as e:
            self.raise_error("Error during day video creation: " + str(e))

        amount = 0
        for root, dirs, files in os.walk(self.config.db_handler.directory("videos_temp")):
            for filename in files:
                if cmd_tempfiles in filename:
                    amount += 1

        self.logging.info("Starting FFMpeg video creation ...")
        input_filenames = cmd_filename + "%05d.jpg"
        output_filename = os.path.join(self.config.db_handler.directory("videos"), cmd_videofile)
        success = self.ffmpeg.create_video(input_filenames, framerate, output_filename)
        if not success:
            response = {"result": "error", "reason": "create video with ffmpeg", "message": ""}
            return response

        self.logging.info("Create thumbnail file ...")
        cmd_thumb = "cp " + cmd_filename + "00001.jpg " + self.config.db_handler.directory("videos") + cmd_thumbfile
        self.logging.debug(cmd_thumb)
        try:
            message = os.system(cmd_thumb)
            if message != 0:
                response = {"result": "error", "reason": "create thumbnail", "message": message}
                self.raise_error("Error during day video creation: create thumbnails.")
                return response

            cmd_rm2 = "rm " + self.config.db_handler.directory("videos_temp") + "*.jpg"
            self.logging.info(cmd_rm2)
            message = os.system(cmd_rm2)
            if message != 0:
                response = {"result": "error", "reason": "remove temp image files", "message": message}
                self.raise_error("Error during day video creation: remove temp image files.")
                return response
        except Exception as e:
            self.raise_error("Error during day video creation: " + str(e))

        self.logging.info("Create database entry ...")
        length = (amount / framerate)
        video_data = {
            "camera": self.id,
            "camera_name": self.name,
            "date": date,
            "date_start": stamp,
            "framerate": framerate,
            "image_count": amount,
            "image_size": self.image_size,
            "length": length,
            "time": "complete day",
            "type": "video",
            "thumbnail": cmd_thumbfile,
            "video_file": cmd_videofile,
        }
        response = {
            "result": "OK",
            "data": video_data
        }
        return response

    def create_video_day_queue(self, param):
        """
        create a video of all existing images of the day
        """
        response = {}
        which_cam = param["which_cam"]
        current_time = self.config.local_time()
        stamp = current_time.strftime('%Y%m%d_%H%M%S')
        date = current_time.strftime('%d.%m.%Y')
        filename = "image_" + which_cam + "_big_"

        self.queue_create.append([filename, stamp, date])

        response["command"] = ["Create video of the day"]
        response["video"] = {"camera": which_cam, "date": date}
        return response

    def create_video_trimmed(self, video_id, start, end):
        """
        create a shorter video based on date and time
        """
        config_file = self.config.db_handler.read_cache("videos")
        if video_id in config_file:
            input_file = config_file[video_id]["video_file"]
            output_file = input_file.replace(".mp4", "_short.mp4")
            framerate = config_file[video_id]["framerate"]
            result = self.create_video_trimmed_exec(input_file=input_file, output_file=output_file,
                                                    start_timecode=start,
                                                    end_timecode=end, framerate=framerate)
            if result == "OK":
                config_file[video_id]["video_file_short"] = output_file
                config_file[video_id]["video_file_short_start"] = float(start)
                config_file[video_id]["video_file_short_end"] = float(end)
                config_file[video_id]["video_file_short_length"] = float(end) - float(start)

                self.config.db_handler.write("videos", "", config_file)
                return {"result": "OK"}
            else:
                return {"result": "Error while creating shorter video."}

        else:
            self.logging.warning("No video with the ID " + str(video_id) + " available.")
            return {"result": "No video with the ID " + str(video_id) + " available."}

    def create_video_trimmed_exec(self, input_file, output_file, start_timecode, end_timecode, framerate):
        """
        creates a shortened version of the video
        """
        input_file = os.path.join(self.config.db_handler.directory("videos"), input_file)
        output_file = os.path.join(self.config.db_handler.directory("videos"), output_file)

        success = self.ffmpeg.trim_video(input_file, output_file, start_timecode, end_timecode, framerate)

        if success and os.path.isfile(output_file):
            return "OK"
        else:
            return "Error"

    def create_video_trimmed_queue(self, param):
        """
        create a short video and save in DB (not deleting the old video at the moment)
        """
        response = {}
        parameter = param["parameter"]

        self.logging.info("Create short version of video: " + str(parameter) + " ...")
        config_data = self.config.db_handler.read_cache(config="videos")

        if parameter[0] not in config_data:
            response["result"] = "Error: video ID '" + str(parameter[0]) + "' doesn't exist."
            self.logging.warning("VideoID '" + str(parameter[0]) + "' doesn't exist.")
        else:
            self.queue_trim.append([parameter[0], parameter[1], parameter[2]])
            response["command"] = ["Create short version of video"]
            response["video"] = {"video_id": parameter[0], "start": parameter[1], "end": parameter[2]}

        return response


class BirdhouseCameraStreamRaw(threading.Thread, BirdhouseCameraClass):
    """
    creates a continuous stream while active requests
    """

    def __init__(self, camera_id, config):
        threading.Thread.__init__(self)
        BirdhouseCameraClass.__init__(self, class_id=camera_id+"-sRaw", class_log="cam-stream",
                                      camera_id=camera_id, config=config)

        self.stream_handler = None
        self.image = BirdhouseImageProcessing(camera_id=self.id, config=self.config)
        self.image.resolution = self.param["image"]["resolution"]

        self.fps = None
        self.fps_max = 12
        self.fps_max_lowres = 3
        self.fps_slow = 2
        self.fps_average = []
        self.duration_max = 1 / self.fps_max
        self.duration_max_lowres = 1 / self.fps_max_lowres
        self.duration_slow = 1 / self.fps_slow

        self.active = False
        self.slow_stream = False
        self.maintenance_mode = False

        self._active_streams = 0
        self._recording = False
        self._stream = None
        self._stream_last = None
        self._stream_last_time = None
        self._stream_image_id = 0
        self._timeout = 3

        self._last_activity = 0
        self._last_activity_count = 0
        self._last_activity_per_stream = {}
        self._start_time = None
        self._start_delay_stream = 1

    def run(self) -> None:
        """
        create a continuous stream while active; use buffer if empty answer
        """
        circle_in_cache = False
        circle_color = (0, 0, 255)
        time.sleep(2)

        self.reset_error()
        self.logging.info("Starting CAMERA raw stream for '"+self.id+"' ...")

        while self._running:
            self._start_time = time.time()

            if self.stream_handler is not None and not self.maintenance_mode \
                    and self._last_activity > 0 and self._last_activity + self._timeout > self._start_time:
                self.active = True
                try:
                    raw = self.read_from_camera()
                    if raw is None or len(raw) == 0:
                        raise Exception("Error with 'read_from_camera()': empty image.")

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
                                self._stream_last = cv2.circle(self._stream_last, (25, 50), 4, circle_color, 6)
                                circle_in_cache = True
                            except cv2.error as e:
                                self.raise_warning("Could not mark image as 'from cache due to error'.")
                        self._stream = self._stream_last.copy()

            else:
                self.active = False
                self._stream = None
                self._stream_image_id = 0
                self._last_activity = 0
                self._last_activity_count = 0
                self._last_activity_per_stream = {}

            self.stream_count()
            self.stream_framerate_check()
            self.health_signal()

        self.logging.info("Stopped CAMERA raw stream for '"+self.id+"'.")

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
                time.sleep(1)
                wait_time += 1

        if self._stream_image_id == 0:
            self.raise_error("sRaw: read_stream: got no image from source '" + self.id + "' yet!")

        return self._stream

    def read_stream_image_id(self):
        """
        return current image id
        """
        return self._stream_image_id

    def read_from_camera(self):
        """
        extract image from stream
        """
        try:
            retrieve, raw = self.stream_handler.read()
            if not retrieve:
                self.raise_error("Could not grab an image from source '" + str(self.id) + "'.")
                return

        except Exception as err:
            self.raise_error("Error while grabbing image from source '" + self.id + "': " + str(err))
            return

        if self.param["image"]["rotation"] != 0:
            raw = self.image.rotate_raw(raw, self.param["image"]["rotation"])

        if raw is not None and len(raw) > 0:
            return raw.copy()

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
        add framerate to array to calculate avarage rate -> get_framerate
        """
        self.fps_average.append(fps)
        if len(self.fps_average) > 10:
            self.fps_average.pop(0)

    def set_stream_handler(self, stream_handler):
        """
        set or reset camera handler
        """
        self.stream_handler = stream_handler

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
        if self.stream_handler is None or not self.param["active"]:
            return False
        else:
            return True

    def kill(self, stream_id="default"):
        """
        kill continuous stream creation
        """
        if stream_id == "default":
            self._last_activity = 0
            self.stream_handler = None

        if stream_id in self._last_activity_per_stream:
            self.logging.info(".... kill: " + str(stream_id))
            del self._last_activity_per_stream[stream_id]

        self.logging.info(".... "+str(list(self._last_activity_per_stream.keys())))

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
        self.image = None

        self.img_error_files = {
            "setting": "camera_na_v3.jpg",
            "camera": "camera_na_v4.jpg"
            }
        self.img_error_raw = {
            "setting": None,
            "camera": None
            }

        self._active_streams = 0
        self._recording = False
        self._timeout = 3
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

        self.fps = None
        self.fps_max = 12
        self.fps_max_lowres = 3
        self.fps_slow = 2
        if self.resolution == "lowres":
            self.fps_max = self.fps_max_lowres
        self.duration_max = 1 / (self.fps_max + 1)
        self.duration_slow = 1 / self.fps_slow
        self.slow_stream = False
        self.active = False
        self.system_status = {
            "active": False,
            "color": "default",
            "line1": "",
            "line2": ""
        }
        self.maintenance_mode = False
        self.reload_time = 0

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
                raw = cv2.imread(filename)
                raw, area = self.image.crop_raw(raw=raw, crop_area=area, crop_type="absolute")
                self.img_error_raw[image] = raw.copy()
            return True

        except Exception as e:
            self.raise_error("Error reading images: " + str(e))
            return False

    def run(self) -> None:
        self.reset_error()
        #while not self.stream_raw.if_ready() and not self.param["active"]:
        while not self.stream_raw.if_running():
            time.sleep(0.1)

        self.image = self.stream_raw.image
        if not self._init_error_images():
            self.raise_error("Could not initialize, error images not found in ./data/: " + str(self.img_error_files))
            self.stop()
            return

        self.logging.info("Starting CAMERA edited stream for '"+self.id+"/"+self.type+"/"+self.resolution+"' ...")
        while self._running:
            self._start_time = time.time()

            if self.stream_raw is not None and self.param["active"] \
                    and self._last_activity > 0 and self._last_activity + self._timeout > self._start_time:
                self.active = True
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
                    #if self._stream_last is not None:
                    #    if not circle_in_cache:
                    #        try:
                    #            #self._stream_last = cv2.circle(self._stream_last, (25, 50), 4, circle_color, 6)
                    #            self._stream_last = self.edit_add_warning_bullet(self._stream_last.copy())
                    #            circle_in_cache = True
                    #        except cv2.error as e:
                    #            self._stream = self._stream_last.copy()

            else:
                self.active = False
                self._stream = None
                self._last_activity = 0
                self._last_activity_count = 0
                self._last_activity_per_stream = {}
                self._stream_image_id += 0
                self._error_wait = True

            if self.param["active"]:
                self.stream_count()
                self.stream_framerate_check()

            self.health_signal()

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
            return raw.copy()

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
            return raw.copy()

        elif self.type == "normalized":
            normalized = self.edit_normalize(raw)
            normalized = self.edit_check_error(normalized, "Error reading 'self.stream_raw.edit_normalize" +
                                               "(raw)' in read_raw_and_edit()", return_error_image)
            if self.resolution == "lowres":
                normalized = self.edit_create_lowres(normalized)
                normalized = self.edit_check_error(normalized, "Error reading 'self.stream_raw.edit_create_lowres" +
                                                   "(normalized)' in read_raw_and_edit()", return_error_image)
            return normalized.copy()

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
            return camera.copy()

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
            return setting.copy()

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
            self.raise_error("sRaw: read_stream: got no image from source '" + self.id + "' yet!")

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

    def read_error_image(self, error_msg=""):
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
            image = self.edit_error_add_info(image, error_msg, reload_time=0, info_type="setting")
        elif self.resolution == "lowres":
            image = self.img_error_raw["camera"]
            image = self.edit_create_lowres(image)
            image = self.edit_error_add_info(image, error_msg, reload_time=0, info_type="lowres")
        else:
            image = self.img_error_raw["camera"]
            image = self.edit_error_add_info(image, error_msg, reload_time=0, info_type="camera")

        return image.copy()

    def edit_error_add_info(self, raw, error_msg, reload_time=0, info_type="empty"):
        """
        edit information to error image
        """
        raw = raw.copy()
        if info_type == "setting":
            line_position = 160
            msg = self.id + ": " + self.param["name"]
            raw = self.image.draw_text_raw(raw=raw, text=msg, position=(20, line_position), font=None, scale=1,
                                           color=(0, 0, 255), thickness=2)

            line_position += 40
            msg = "Device: type=" + self.param["type"] + ", active=" + str(self.param["active"]) + ", source=" + str(
                self.param["source"])
            msg += ", resolution=" + self.param["image"]["resolution"]
            raw = self.image.draw_text_raw(raw=raw, text=msg, position=(20, line_position), font=None, scale=0.6,
                                           color=(0, 0, 255), thickness=1)

            if len(error_msg) > 0:
                line_position += 30
                msg = "Last Cam Error: " + error_msg[len(error_msg) - 1] + " [#" + str(len(error_msg)) + "]"
                raw = self.image.draw_text_raw(raw=raw, text=msg, position=(20, line_position), font=None, scale=0.6,
                                               color=(0, 0, 255), thickness=1)

            if len(self.error_msg) > 0:
                line_position += 30
                msg = "Last Img Error: " + self.error_msg[len(self.error_msg) - 1] + " [#" + str(len(error_msg)) + "]"
                raw = self.image.draw_text_raw(raw=raw, text=msg, position=(20, line_position), font=None, scale=0.6,
                                               color=(0, 0, 255), thickness=1)

            line_position += 30
            msg = "Last Reconnect: " + str(round(time.time() - self.reload_time)) + "s"
            raw = self.image.draw_text_raw(raw=raw, text=msg, position=(20, line_position), font=None, scale=0.6,
                                           color=(0, 0, 255), thickness=1)

            details = True
            if details:
                line_position += 30
                msg = "CPU Usage: " + str(psutil.cpu_percent(interval=1, percpu=False)) + "% "
                msg += "(" + str(psutil.cpu_count()) + " CPU)"
                raw = self.image.draw_text_raw(raw=raw, text=msg, position=(20, line_position), font=None, scale=0.6,
                                               color=(0, 0, 255), thickness=1)

                line_position += 30
                total = psutil.virtual_memory().total
                total = round(total / 1024 / 1024)
                used = psutil.virtual_memory().used
                used = round(used / 1024 / 1024)
                percentage = psutil.virtual_memory().percent
                msg = "Memory: total=" + str(total) + "MB, used=" + str(used) + "MB (" + str(percentage) + "%)"
                raw = self.image.draw_text_raw(raw=raw, text=msg, position=(20, line_position), font=None, scale=0.6,
                                               color=(0, 0, 255), thickness=1)

            line_position += 40
            raw = self.image.draw_date_raw(raw=raw, overwrite_color=(0, 0, 255), overwrite_position=(20, line_position))

        elif info_type == "camera":
            raw = self.image.draw_text_raw(raw=raw, text=self.id + ": " + self.param["name"],
                                           position=(20, 40), color=(255, 255, 255), thickness=2)
            raw = self.image.draw_date_raw(raw=raw, overwrite_color=(255, 255, 255), overwrite_position=(20, 80))

        return raw

    def edit_normalize(self, raw):
        """
        create normalized image
        """
        if "black_white" in self.param["image"] and self.param["image"]["black_white"] is True:
            normalized = self.image.convert_to_gray_raw(raw)
            normalized = self.image.convert_from_gray_raw(normalized)
            return normalized.copy()
        else:
            return raw.copy()

    def edit_crop_area(self, raw, start_zero=False):
        """
        crop image to area defined in the settings
        """
        crop_area = self.param["image"]["crop"]
        if start_zero:
            crop_area = [0, 0, crop_area[2]-crop_area[0], crop_area[3]-crop_area[1]]
        cropped, area = self.image.crop_raw(raw=raw, crop_area=crop_area, crop_type="relative")
        self.param["image"]["crop_area"] = area
        self.param["image"]["resolution_cropped"] = [area[2] - area[0], area[3] - area[1]]
        return cropped.copy()

    def edit_create_lowres(self, raw):
        """
        scale image to create lowres
        """
        if self._size_lowres is None:
            self._size_lowres = self.image.size_raw(raw=raw, scale_percent=self.param["image"]["preview_scale"])
        lowres = self.image.resize_raw(raw=raw, scale_percent=100, scale_size=self._size_lowres)
        return lowres.copy()

    def edit_add_areas(self, raw):
        """
        Draw a red rectangle into the image to show detection area / and a yellow to show the crop area
        """
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
        if "show_framerate" in self.param["image"] and self.param["image"]["show_framerate"] \
                and self.resolution != "lowres":
            framerate = round(self.stream_raw.fps, 1)
            if self.fps < framerate:
                framerate = self.fps
            raw = self.image.draw_text_raw(raw=raw, text=str(round(framerate, 1)) + "fps",
                                           font=cv2.QT_FONT_NORMAL,
                                           position=(10, -20), scale=0.4, thickness=1)
        return raw.copy()

    def edit_add_system_info(self, raw):
        """
        add information if recording or processing to image
        """
        image = raw.copy()
        if self.system_status["active"]:
            image = self.image.draw_text_raw(raw=image, text=self.system_status["line1"],
                                           font=cv2.QT_FONT_NORMAL, color=self.system_status["color"],
                                           position=(10, -70), scale=1, thickness=2)
            image = self.image.draw_text_raw(raw=image, text=self.system_status["line2"],
                                           font=cv2.QT_FONT_NORMAL, color=self.system_status["color"],
                                           position=(10, -50), scale=0.4, thickness=1)
        return image.copy()

    @staticmethod
    def edit_add_warning_bullet(raw, color=None):
        """
        add read circle (depending on lowres position)
        """
        default_color = (0, 0, 255)
        default_position = (25, -25)
        if color is None:
            color = default_color
        raw = cv2.circle(raw.copy(), default_position, 4, color, 6)
        return raw

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

    def set_maintenance_mode(self, active, line1="", line2=""):
        """
        set maintenance mode -> image plus text, no streaming image (e.g. for camera restart)
        """
        maintenance_color = (0, 0, 0)
        if active:
            self.logging.info("Start maintenance mode ("+self.type+"/"+self.resolution+"): " + line1 + " ... ")
        self.maintenance_mode = active
        self.stream_raw.maintenance_mode = active
        self.set_system_info(active, line1, line2, color=maintenance_color)
        if not active:
            self.reset_error()
            self.logging.debug("Stopped maintenance mode ("+self.type+"/"+self.resolution+").")

    def set_system_info(self, active, line1="", line2="", color=""):
        """
        format message
        """
        default_color = (0, 0, 255)
        self.system_status = {
            "active": active,
            "line1": line1,
            "line2": line2,
            "color": color,
        }
        if color == "":
            self.system_status["color"] = default_color

    def kill(self):
        self._last_activity = 0

    def stop(self):
        self._running = False


class BirdhouseCamera(threading.Thread, BirdhouseCameraClass):

    def __init__(self, camera_id, config, sensor):
        """
        Initialize new thread and set initial parameters
        """
        threading.Thread.__init__(self)
        BirdhouseCameraClass.__init__(self, class_id=camera_id + "-main", class_log="cam-main",
                                      camera_id=camera_id, config=config)

        self.config_cache = {}
        self.config_cache_size = 5
        self.config_update = None
        self.config.update["camera_" + self.id] = False

        self.image = None
        self.video = None
        self.camera = None
        self.sensor = sensor
        self.weather_active = self.config.param["weather"]["active"]
        self.weather_sunrise = None
        self.weather_sunset = None

        self.name = self.param["name"]
        self.active = self.param["active"]
        self.source = self.param["source"]
        self.type = self.param["type"]
        self.max_resolution = None

        self._interval = 0.2
        self._interval_reload_if_error = 60*3
        self._stream_errors_max_accepted = 25
        self._stream_errors_restart = False
        self._stream_errors = 0

        self.error_reload_time = 60
        self.error_no_reconnect = False

        self.reload_camera = False
        self.reload_time = 0

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

        self.camera_stream_raw = None
        self.camera_streams = {}

        self.date_last = self.config.local_time().strftime("%Y-%m-%d")
        self.usage_time = time.time()
        self.usage_interval = 60

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
            self.camera_streams[stream].reload_time = self.reload_time

    def _init_camera(self, init=False):
        """
        Try out new
        """
        relevant_streams = ["camera_hires", "camera_lowres", "setting_hires", "setting_lowres"]
        self.reload_time = time.time()
        for stream in self.camera_streams:
            self.camera_streams[stream].reload_time = self.reload_time

        if not init:
            self.logging.info("- Restarting CAMERA (" + self.id + ") ...")
            for stream in relevant_streams:
                if stream in self.camera_streams:
                    self.camera_streams[stream].set_maintenance_mode(True, "Restart camera", self.id)
            time.sleep(1)
        else:
            self.logging.info("Starting CAMERA (" + self.id + ") ...")

        self.reset_error_all()
        try:
            if init:
                self.camera = BirdhouseCameraHandler(camera_id=self.id, source=self.source,
                                                     config=self.config, param=self.param)
                self.camera_stream_raw.set_stream_handler(self.camera.stream)
            else:
                self.camera.reconnect()
                self.camera_stream_raw.set_stream_handler(self.camera.stream)

            if self.camera.error:
                self.raise_error("Can't connect to camera, check if '" + str(
                    self.source) + "' is a valid source (" + self.camera.error_msg + ").")
                self.camera.disconnect()
            elif not self.camera.stream.isOpened():
                self.raise_error("Can't connect to camera, check if '" + str(
                    self.source) + "' is a valid source (could not open).")
                self.camera.disconnect()
            elif self.camera.stream is None:
                self.raise_error("Can't connect to camera, check if '" + str(
                    self.source) + "' is a valid source (empty image).")
                self.camera.disconnect()
            else:
                raw = self.camera.read()
                check = str(type(raw))
                if "NoneType" in check:
                    self.raise_error("Check after (re)connect: Source " + str(self.source) + " returned empty image.")
                else:
                    self._init_camera_settings()
                    self.camera_stream_raw.set_stream_handler(self.camera.stream)
                    self.logging.info("Check after (re)connect: OK (Source=" + str(self.source) + ")")

            self.record_image_reload = time.time()

        except Exception as e:
            self.raise_error("Starting camera '" + self.source + "' doesn't work: " + str(e))

        if not init:
            self.logging.error(" ........ " + str(self.camera_streams.keys()))
            for stream in relevant_streams:
                if stream in self.camera_streams:
                    self.camera_streams[stream].set_maintenance_mode(False)
        return

    def _init_camera_settings(self):
        """
        set resolution for USB
        """
        if self.camera is None:
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
            self.logging.info("- Resolution definition not supported (e.g. '800x600'): " + str(self.param["image"]["resolution"]))

        # return properties as values
        self.param["camera"] = self.camera.get_properties()

    def run(self):
        """
        Start recording for livestream and save images every x seconds
        """
        self._init_image_processing()
        self._init_video_processing()
        self._init_stream_raw()
        self._init_streams()
        if self.active:
            self._init_camera(init=True)

        similarity = 0
        count_paused = 0
        reload_time = time.time()
        sensor_last = ""

        self.logging.info("Starting CAMERA control for '"+self.id+"' ...")
        self.logging.info("Initializing camera (" + self.id + "/" + self.type + "/" + str(self.source) + ") ...")

        while self._running:
            current_time = self.config.local_time()
            stamp = current_time.strftime('%H%M%S')
            self.config_update = self.config.update["camera_" + self.id]

            # reset some settings end of the day
            if self.date_last != self.config.local_time().strftime("%Y-%m-%d"):
                self.record_temp_threshold = None
                self.date_last = self.config.local_time().strftime("%Y-%m-%d")

            # if shutdown
            if self.config.shut_down:
                self.stop()

            if self._stream_errors > self._stream_errors_max_accepted and self._stream_errors_restart:
                self.logging.warning("....... Reload CAMERA '" + self.id + "' due to stream errors: " +
                                     str(self._stream_errors) + " errors.")

            # if error reload from time to time
            if self.active and self.if_error() and (reload_time + self._interval_reload_if_error) < time.time():
                self.logging.warning("....... Reload CAMERA '" + self.id + "' due to errors --> " +
                                     str(round(reload_time, 1)) + " + " +
                                     str(round(self._interval_reload_if_error, 1)) + " > " +
                                     str(round(time.time(), 1)))
                self.logging.warning("        " + self.if_error(details=True))
                reload_time = time.time()
                self.config_update = True
                self.reload_camera = True

            # start or reload camera connection
            if (self.config_update or self.reload_camera) and self.active:
                self.logging.info("Updating CAMERA configuration (" + self.id + ") ...")
                self.update_main_config()
                if self.active:
                    self.camera_reconnect(directly=True)
                else:
                    self.logging.info(" - CAMERA is set inactive, no restart (" + self.id + ") ...")

            # check if camera is paused, wait with all processes ...
            if not self._paused:
                count_paused = 0
            while self._paused and self._running:
                if count_paused == 0:
                    self.logging.info("Recording images with " + self.id + " paused ...")
                    count_paused += 1
                time.sleep(1)

            # Video Recording
            if self.active:
                if self.video.recording:
                    self.slow_down_streams(False)
                    self.video_recording(current_time)

                elif self.config.get_device_signal(self.id, "recording") and not self.video.processing:
                    self.slow_down_streams(True)
                else:
                    self.slow_down_streams(False)

            # Image Recording (if not video recording)
            if self.active and self.record and not self.video.recording:
                time.sleep(self._interval)
                self.image_recording(current_time, stamp, similarity, sensor_last)

            # Check and record active streams
            if self.active:
                self.measure_usage(current_time, stamp)

            # reconnect from time to time, to foster re-calibrate by camera
            #if self.active and "reconnect_to_calibrate" in self.param["image"] \
            #        and self.param["image"]["reconnect_to_calibrate"] \
            #        and self.get_stream_count() == 0:
            #    count_reconnect += 1
            #    if count_reconnect > 9:
            #        self.camera_reconnect(directly=True)
            #        count_reconnect = 0

            self.health_signal()

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

        #if self.image.if_error(message=False, length=True) > self._max_accepted_stream_errors:
        #    self.raise_error("Camera doesn't work correctly: More than " + str(self._max_accepted_stream_errors) +
        #                     " errors in IMAGE processing ...")
        #    return self.error

        #if self.camera_stream_raw.if_error(message=False, length=True) > self._max_accepted_stream_errors:
        #    self.raise_error("Camera doesn't work correctly: More than " + str(self._max_accepted_stream_errors) +
        #                     " errors in RAW stream ...")
        #    return self.error

        for stream in self.camera_streams:
            if self.camera_streams[stream].if_error(message=False, length=True) > self._stream_errors_max_accepted:
                self.raise_warning("Camera doesn't work correctly: More than " + str(self._stream_errors_max_accepted) +
                                   " errors in EDIT stream '" + stream + "'...")
                self._stream_errors += 1
        #        return self.error

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

    def camera_reconnect(self, directly=False):
        """
        Reconnect after API call
        """
        if directly and self.camera is not None:
            self._init_camera()
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
            self.logging.info("... check usage!")

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
        if self.image_recording_active(current_time=current_time):

            self.logging.debug(" ...... record now!")
            image = self.get_image_raw()

            # retry once if image could not be read
            if self.image.error or len(image) == 0:
                self.image.error = False
                image = self.get_image_raw()

            # if no error format and analyze image
            if not self.image.error and len(image) > 0:
                image = self.image.normalize_raw(image)
                image_compare = self.image.convert_to_gray_raw(image)

                if self.param["image"]["date_time"]:
                    image = self.image.draw_date_raw(image)

                if self.image_size == [0, 0]:
                    self.image_size = self.image.size_raw(image)
                    self.video.image_size = self.image_size

                if self.image_size_lowres == [0, 0]:
                    scale = self.param["image"]["preview_scale"]
                    self.image_size_lowres = self.image.size_raw(image, scale)
                    self.video.image_size = self.image_size

                if self.previous_image is not None:
                    similarity = self.image.compare_raw(image_1st=image_compare,
                                                        image_2nd=self.previous_image,
                                                        detection_area=self.param["similarity"][
                                                            "detection_area"])
                    similarity = str(similarity)

                image_info = {
                    "camera": self.id,
                    "compare": (stamp, self.previous_stamp),
                    "date": current_time.strftime("%d.%m.%Y"),
                    "datestamp": current_time.strftime("%Y%m%d"),
                    "hires": self.config.filename_image("hires", stamp, self.id),
                    "hires_size": self.image_size,
                    "lowres": self.config.filename_image("lowres", stamp, self.id),
                    "lowres_size": self.image_size_lowres,
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
                self.record_image_error_msg = ["img_error=" + str(self.image.error) + "; img_len=" + str(len(image))]
                sensor_data = {}
                image_info = {}

            for key in self.sensor:
                if self.sensor[key].if_running():
                    sensor_data[key] = self.sensor[key].get_values()
                    sensor_data[key]["date"] = current_time.strftime("%d.%m.%Y")
                    # image_info["sensor"][key] = sensor_data[key]

            sensor_stamp = current_time.strftime("%H%M") + "00"
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
                self.write_image(filename=path_hires, image=image)
                self.write_image(filename=path_lowres, image=image,
                                 scale_percent=self.param["image"]["preview_scale"])

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

    def get_stream(self, stream_id, stream_type, stream_resolution="", system_info=False,
                   return_error_image=True, wait=True):
        """
        get image from new streams
        """
        stream = stream_type
        if stream_resolution != "":
            stream += "_" + stream_resolution

        if stream not in self.camera_streams:
            error_msg = "Stream '" + stream + "' does not exist."
            image = self.camera_streams[stream].read_error_image(error_msg)
            self.raise_error(error_msg)
            return image
        else:
            image = self.camera_streams[stream].read_stream(stream_id, system_info, wait)

        if self.if_error() or self.camera_streams[stream].if_error():
            image = self.camera_streams[stream].read_error_image()
        return image

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
            self.logging.info("get_image_stream_kill - True: " + str(ext_stream_id))
            del self.image_streams_to_kill[ext_stream_id]
            self.camera_stream_raw.kill(int_stream_id)
            return True
        else:
            return False

    def set_stream_kill(self, ext_stream_id):
        """
        mark streams to be killed
        """
        self.logging.info("set_image_stream_kill: " + ext_stream_id)
        self.image_streams_to_kill[ext_stream_id] = datetime.now().timestamp()

    def get_camera_status(self):
        """
        return all status and error information
        """
        if self.record and time.time() - self.record_image_last > 120 \
                and not self.video.recording and not self.video.processing and self.param["active"]:
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
            "record_image_active": self.image_recording_active(current_time=-1, check_in_general=True),
            "record_image_last_compare": self.record_image_last_compare,
            "record_image_start": self.record_image_start,
            "record_image_end": self.record_image_end,
            "stream_raw_fps": self.camera_stream_raw.get_framerate(),

            "properties": {},
            "properties_image": {}
            }

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

        if self.camera is not None:
            status["properties"] = self.camera.get_properties()
            status["properties_image"] = self.camera.get_properties_image()
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

    def update_main_config(self):
        self.logging.info("- Update data from main configuration file for camera " + self.id)
        temp_data = self.config.db_handler.read("main")

        self.param = temp_data["devices"]["cameras"][self.id]
        self.name = self.param["name"]
        self.active = self.param["active"]
        self.source = self.param["source"]
        self.type = self.param["type"]
        self.record = self.param["record"]

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
        self.previous_image = None
        self.previous_stamp = "000000"

        self.camera_stream_raw.param = self.param
        for stream in self.camera_streams:
            self.camera_streams[stream].param = self.param
        self.image.param = self.param
        self.video.param = self.param

        self.config.update["camera_" + self.id] = False
        self.reload_camera = True
