import os.path
import time

import numpy as np
import cv2
import psutil
import threading
import subprocess

from modules.presets import *
from modules.presets import ch_logging
from modules.bh_class import BirdhouseCameraClass

# https://pyimagesearch.com/2016/01/04/unifying-picamera-and-cv2-videocapture-into-a-single-class-with-opencv/


class CameraInformation:

    def __init__(self):

        self.logging = set_logging("cam-info")

    def get_available_cameras(self):
        """
        use v4l2_ctl to identify available cameras
        """
        try:
            process = subprocess.Popen(["v4l2-ctl --list-devices"], stdout=subprocess.PIPE, shell=True)
            output = process.communicate()[0]
            output = output.decode()
            output = output.split("\n")
        except Exception as e:
            ch_logging.error("Could not grab video devices. Check, if v4l2-ctl is installed. " + str(e))
            return system

        last_key = "none"
        if birdhouse_env["rpi_active"]:
            output.append("PiCamera:")
            output.append("/dev/picam")

        devices = {"list": {}, "short": {}, "complete": {}}
        for value in output:
            if ":" in value:
                last_key = value

            elif value != "":
                value = value.replace("\t", "")
                info = last_key.split(":")

                if last_key not in devices["list"]:
                    devices["list"][last_key] = []
                devices["list"][last_key].append(value)
                devices["short"][value] = value + " (" + info[0] + ")"
                devices["complete"][value] = {"dev": value, "info": last_key, "image": False, "shape": []}

        self.logging.info("Found "+str(len(devices["list"]))+" devices.")
        self.logging.debug(str(devices))

        return devices.copy()

    def get_available_camera_resolutions(self, source):
        """
        use v4l2_ctl to identify available camera resolutions
        """
        try:
            process = subprocess.Popen(["v4l2-ctl -d " + source + " --list-formats-ext"],
                                       stdout=subprocess.PIPE, shell=True)
            output = process.communicate()[0]
            output = output.decode()
            output = output.split("\n")

            output_dict = {}
            resolution_key = "0"
            for line in output:
                if "[" in line:
                    resolution_key = line.replace("\t", "")
                    resolution_key = resolution_key.split(": ")[1]
                    resolution_key = resolution_key.split("'")[1]
                    output_dict[resolution_key] = []
                elif "Size: Discrete " in line:
                    value_size = line.split("Size: Discrete ")[1]
                    output_dict[resolution_key].append(value_size)
            return output_dict

        except Exception as e:
            self.logging.error("Could not grab video device resolutions for '" + source +
                          "'. Check, if v4l2-ctl is installed. " + str(e))
            return {}


class BirdhousePiCameraHandler(BirdhouseCameraClass):

    def __init__(self, camera_id, source, config):
        """
        create instance for PiCamera2
        documentation: https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf
        """
        BirdhouseCameraClass.__init__(self, class_id=camera_id+"-pi", class_log="cam-pi",
                                      camera_id=camera_id, config=config)
        self.source = source
        self.stream = None
        self.transform = None
        self.configuration = {}
        self.property_keys = None
        self.properties_get = None
        self.properties_not_used = None
        self.properties_set = None
        self.connected = False
        self.available_devices = {}
        self.first_connect = True

        self.logging.info("Starting PiCamera2 support for '"+self.id+":"+source+"' ...")

    def connect(self):
        """
        connect with PiCamera
        """
        self.reset_error()
        self.connected = False

        self.logging.info("Try to connect PiCamera2 '" + self.id + "/" + self.source + "' ...")
        try:
            if self.first_connect:
                from picamera2 import Picamera2
                self.stream = Picamera2()
                self.configuration = self.stream.create_still_configuration()
                self.stream.configure(self.configuration)

                self.logging.info("------------------")
                self.logging.info(str(self.configuration))
                self.logging.info("------------------")

            self.stream.start()
            time.sleep(0.5)

        except Exception as err:
            self.raise_error("Can't connect to PiCamera2 '" + self.source + "': " + str(err))
            return False

        if self.stream is None:
            self.raise_error("Can't connect to PiCamera2 '" + self.source + "': Unknown error.")
            return False
        else:
            self.logging.info("- Connected.")
            self.get_properties(key="init")
            self.set_properties(key="init")
            self.first_connect = False
            self.connected = True

        try:
            image = self.stream.switch_mode_and_capture_array(self.configuration, "main")
            #image = self.stream.capture_array()
            if image is None or len(image) == 0:
                raise Exception("Returned empty image.")
            return True

        except Exception as err:
            self.raise_warning("- Error reading first image from PiCamera '"+self.source+"': " + str(err))
            return "WARNING"

    def reconnect(self):
        """
        reconnect camera
        """
        self.disconnect()
        return self.connect()

    def disconnect(self):
        """
        disconnect camera
        """
        self.connected = False
        if self.stream is not None:
            try:
                self.stream.close()
            except Exception as err:
                self.logging.debug("- Release of PiCamera2 did not work: " + str(err))
        else:
            self.logging.debug("- PiCamera2 not yet connected.")

    def read(self, stream="not set"):
        """
        read image from camera
        """
        try:
            #raw = self.stream.switch_mode_and_capture_array(self.configuration, "main")
            raw = self.stream.capture_array("main")
            if raw is None or len(raw) == 0:
                raise Exception("Returned empty image.")
            return raw
        except Exception as err:
            self.raise_error("- Error reading image from PiCamera2 '" + self.source +
                             "' by stream '" + stream + "': " + str(err))
            return

    def set_properties(self, key, value=""):
        """
        set configuration for picamera2 using "Picamera2.create_still_configuration"
        """
        self.properties_set = []
        if key == "init":
            for prop_key in self.properties_get:
                if "w" in self.properties_get[prop_key][1]:
                    self.properties_set.append(prop_key)
            return

        if key in self.properties_get:
            picam_key = self.properties_get[key][0]
            try:
                self.stream.set_controls({picam_key: value})
                return True
            except Exception as err:
                self.raise_error("Could not set to value for '" + str(picam_key) + "': " + str(err))
                return False
        else:
            self.raise_error("Key '" + str(key) + "' is unknown!")

    def get_properties_available(self, keys="get"):
        """
        get properties from Picamera,

        picam2.set_controls({"ExposureTime": 10000, "AnalogueGain": 1.0})
        print(picam.controls)

        metadata = picam2.capture_metadata()
        {
        'SensorTimestamp': 9784996188000,
        'ColourCorrectionMatrix': (1.88217031955719, -0.26385337114334106, -0.6183169484138489, -0.6379863619804382,
                                   2.1166977882385254, -0.47871148586273193, -0.13631515204906464, -0.9951226711273193,
                                   2.1314477920532227),
        'FocusFoM': 859,
        'ColourTemperature': 2585,
        'ColourGains': (1.0264559984207153, 2.126723289489746),
        'AeLocked': False,
        'Lux': 54.87057876586914,
        'FrameDuration': 66773,
        'SensorBlackLevels': (1024, 1024, 1024, 1024),
        'DigitalGain': 1.000415325164795,
        'AnalogueGain': 8.0,
        'ScalerCrop': (16, 0, 2560, 1920),
        'ExposureTime': 66638
        }

        ----
        sample output from 'self.stream.camera_properties'
        {
            'Model': 'ov5647',
            'UnitCellSize': (1400, 1400),
            'Location': 2,
            'Rotation': 0,
            'PixelArraySize': (2592, 1944),
            'PixelArrayActiveAreas': [(16, 6, 2592, 1944)],
            'ColorFilterArrangement': 2,
            'ScalerCropMaximum': (16, 0, 2560, 1920),
            'SystemDevices': (20754, 20741, 20743, 20744),
            'SensorSensitivity': 1.0
        }
        picam2.camera_configuration()
        picam2.sensor_modes example
        [
            {'bit_depth': 10, 'crop_limits': (696, 528, 2664, 1980), 'exposure_limits': (31, 66512892),
            'format': SRGGB10_CSI2P, 'fps': 120.05, 'size': (1332, 990), 'unpacked': 'SRGGB10'},
            {'bit_depth': 12, 'crop_limits': (0, 440, 4056, 2160), 'exposure_limits': (60, 127156999),
            'format': SRGGB12_CSI2P, 'fps': 50.03, 'size': (2028, 1080), 'unpacked': 'SRGGB12'}, ...
        ]
        picam2.create_preview_configuration()
        picam2.create_still_configuration()
        picam2.create_video_configuration()
        picam2.preview_configuration.main.size = (800, 600)
        picam2.configure("preview")
        configuration_object.enable_lores()
        configuration_object.enable_raw()

        self.configuration = {
            {"size": (808, 606)},
            raw={'format': 'SRGGB12'},
            sensor={'output_size': mode['size'], 'bit_depth': mode['bit_depth']},
            lores={"size": (320, 240)},
            encode="lores",
            colour_space=ColorSpace.Sycc()
        }
        stream: 'main', 'raw', 'lores', 'video', ...

        ----
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
        ---
        "saturation": "Saturation", [0.0 .. 32.0]
        "brightness": "Brightness", [-1.0 .. 1.0]
        "temperature": "ColourTemperature", [integer]
        "gain": "ColourGains", [0.0 .. 32.0]
        "contrast": "Contrast", [0.0 .. 32.0]
        "sharpness": "Sharpness", [0.0 .. 16.0]
        "exposure": "ExposureTime",
        "noise_reduction": "NoiseReductionMode" [Off, Fast, HighQuality]
        ---
        """
        picamera_properties = {
            "saturation":       ["Saturation",          "rwm", 0.0, 32.],
            "brightness":       ["Brightness",          "rwm", -1.0, 1.0],
            "contrast":         ["Contrast",            "rwm", 0.0, 32.0],
            "gain":             ["ColourGains",         "rw",  0.0, 32.0],
            "sharpness":        ["Sharpness",           "rw",  0.0, 16.0],
            "temperature":      ["ColourTemperature",   "r",   -1, -1],
            "exposure":         ["ExposureTime",        "r",   -1, -1],
            "noise_reduction":  ["NoiseReductionMode",  "r",   -1, -1, ["Off", "Fast", "HighQuality"]],
            "auto_wb":          ["AwbEnable",           "r",   -1, -1]
        }
        properties_not_used = ["exposure", "auto_wb", "temperature", "noise_reduction"]
        properties_get_array = ["brightness", "saturation", "contrast", "gain", "sharpness"]

        if key == "init":
            self.properties_get = picamera_properties.copy()

        for picam_key in picamera_properties:
            picam_key_full = picamera_properties[picam_key][0]

            if key == "init":
                try:
                    min_exp, max_exp, default_exp = self.stream.camera_controls[picam_key_full]
                    self.properties_get[picam_key][0] = default_exp
                    if self.properties_get[picam_key][2] == -1:
                        self.properties_get[picam_key][2] = min_exp
                    if self.properties_get[picam_key][3] == -1:
                        self.properties_get[picam_key][3] = max_exp

                except Exception as e:
                    msg = "Could not get data for '" + picam_key_full + "': " + str(e)
                    self.properties_get[picam_key][0] = -1
                    self.properties_get[picam_key].append(msg)
                    self.logging.warning(msg)

            else:
                try:
                    value = eval("self.stream.still_configuration." + picam_key_full)
                    self.properties_get[picam_key][0] = value
                except Exception as e:
                    self.logging.debug("Value not set yet, stays on default for '" + picam_key + "'. (" + str(e) + ")")

        # !!! Assumption: start with default value, to be changed by configuration
        #     -> if set the value is, what has been set?! until there is a way to request data

        return self.properties_get

    def get_properties_image(self):
        """
        read image and get properties - not implemented yet
        """
        image_properties = {}
        return image_properties

    def set_black_white(self):
        """
        set saturation to 0
        """
        try:
            self.stream.set_controls({"Saturation": 0})
            return True
        except Exception as err:
            self.raise_error("Could not set to black and white: " + str(err))
            return False

    def set_resolution(self, width, height):
        """
        set camera resolution
        """
        try:
            config = self.stream.create_still_configuration({"size": (int(width), int(height))})
            self.stream.stop()
            self.stream.configure(config)
            self.stream.start()
            return True
        except Exception as err:
            self.raise_error("Could not set resolution: " + str(err))
            return False

    def get_resolution(self, maximum=False):
        """
        get resolution of the device
        """
        if maximum:
            (width, height) = self.stream.camera_properties['PixelArraySize']
        else:
            (width, height) = self.stream.still_configuration.main.size
        return [width, height]

    def camera_status(self, source, name):
        """
        check if given source can be connected as PiCamera and returns an image
        Args:
        * source = device string, should be "/dev/picam"
        * name   = description for the camera
        """
        camera_info = {"dev": source, "info": name, "image": False, "shape": []}
        if source == "/dev/picam" and birdhouse_env["rpi_64bit"]:
            try:
                from picamera2 import Picamera2
                picam2_test = Picamera2()
                picam2_test.start()
                time.sleep(0.5)
                image = picam2_test.capture_array()

                if image is None or len(image) == 0:
                    camera_info["error"] = "Returned empty image."
                else:
                    path_raw = str(os.path.join(self.config.db_handler.directory(config="images"),
                                                "..", "test_connect_" + source.replace("/", "_") + ".jpeg"))
                    cv2.imwrite(path_raw, image)
                    if "error" in camera_info:
                        del camera_info["error"]
                    camera_info["image"] = True
                    camera_info["shape"] = image.shape
                    picam2_test.stop()
                    picam2_test.close()

            except Exception as e:
                camera_info["error"] = "Error connecting camera:" + str(e)
        elif not birdhouse_env["rpi_64bit"]:
            camera_info["error"] = "PiCamera2 is only supported on 64bit OS, check configuration in .env-file."
        else:
            camera_info["error"] = "Given source '" + source + "' is not a PiCamera."
        return camera_info

    def if_connected(self):
        """
        check if camera is connected
        """
        return self.connected


class BirdhouseCameraHandler(BirdhouseCameraClass):

    def __init__(self, camera_id, source, config):
        BirdhouseCameraClass.__init__(self, class_id=camera_id+"-ctrl", class_log="cam-other",
                                      camera_id=camera_id, config=config)
        self.source = source
        self.stream = None
        self.property_keys = None
        self.properties_get = None
        self.properties_not_used = None
        self.properties_set = None
        self.connected = False
        self.available_devices = {}
        self.camera_info = CameraInformation()

        self.logging.info("Starting CAMERA support for '"+self.id+":"+source+"' ...")

    def connect(self):
        """
        connect with camera
        """
        self.reset_error()
        self.connected = False

        self.logging.info("Try to connect camera '" + self.id + "/" + self.source + "' ...")
        try:
            if self.stream is not None and self.stream.isOpened():
                self.raise_error("- Seems to be open ... try to release.")
                self.stream.release()
            self.stream = cv2.VideoCapture(self.source, cv2.CAP_V4L)
            self.stream.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))

            if not self.stream.isOpened():
                self.raise_error("- Can't connect to camera '" + self.source + "': not isOpen()")
                return False
            time.sleep(0.5)
        except Exception as err:
            self.raise_error("- Can't connect to camera '" + self.source + "': " + str(err))
            return False

        if self.stream is None:
            self.raise_error("- Can't connect to camera '" + self.source + "': Unknown error.")
            return False
        elif not self.stream.isOpened():
            self.raise_error("- Can't connect to camera '" + self.source + "': Could not open.")
            return False
        else:
            self.logging.info("- Connected.")
            self.reset_error()
            self.get_properties(key="init")
            self.set_properties(key="init")
            self.connected = True

        try:
            ref, raw = self.stream.read()
            check = str(type(raw))
            if "NoneType" in check or len(raw) == 0:
                raise Exception("Returned empty image.")
            return True
        except Exception as err:
            self.raise_warning("- Error reading first image from camera '"+self.source+"': " + str(err))
            return "WARNING"

    def reconnect(self):
        """
        reconnect camera
        """
        self.disconnect()
        return self.connect()

    def disconnect(self):
        """
        disconnect camera
        """
        self.connected = False
        if self.stream is not None:
            try:
                self.stream.release()
            except cv2.error as err:
                self.logging.debug("- Release of camera did not work: " + str(err))
        else:
            self.logging.debug("- Camera not yet connected.")

    def read(self, stream="not set"):
        """
        read image from camera
        """
        try:
            ref, raw = self.stream.read()
            check = str(type(raw))
            if not ref:
                raise Exception("Error reading image.")
            if "NoneType" in check or len(raw) == 0:
                raise Exception("Returned empty image.")
            return raw
        except Exception as err:
            self.raise_error("- Error reading image from camera '" + self.source +
                             "' by stream '" + stream + "': " + str(err))
            return

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
        camera_properties = {
            "saturation":     [-1, "rwm", -1, -1],
            "brightness":     [-1, "rwm", -1, -1],
            "contrast":       [-1, "rwm", -1, -1],
            "gain":           [-1, "rw",  -1, -1],
            "gamma":          [-1, "rw",  -1, -1],
            "hue":            [-1, "rw",  -1, -1],
            "fps":            [-1, "rw",  -1, -1],
            "exposure":       [-1, "rw",  -1, -1],
            "auto_exposure":  [-1, "r",   -1, -1],
            "wb_temperature": [-1, "r",   -1, -1],
            "auto_wb":        [-1, "r",   -1, -1]
        }

        if key == "init":
            self.properties_get = camera_properties.copy()

        for prop_key in self.properties_get:
            value = self.stream.get(eval("cv2.CAP_PROP_" + prop_key.upper()))
            self.properties_get[prop_key][0] = value

            if key == "init":
                try:
                    self.stream.set(eval("cv2.CAP_PROP_" + prop_key.upper()), -100000.0)
                    value = self.stream.get(eval("cv2.CAP_PROP_" + prop_key.upper()))
                    if value > 0:
                        self.stream.set(eval("cv2.CAP_PROP_" + prop_key.upper()), 0.0)
                        value = self.stream.get(eval("cv2.CAP_PROP_" + prop_key.upper()))
                    self.properties_get[prop_key][2] = value

                    self.stream.set(eval("cv2.CAP_PROP_" + prop_key.upper()), 100000.0)
                    value = self.stream.get(eval("cv2.CAP_PROP_" + prop_key.upper()))
                    self.properties_get[prop_key][3] = value

                    self.stream.set(eval("cv2.CAP_PROP_" + prop_key.upper()), self.properties_get[prop_key][0])

                except Exception as e:
                    msg = "Could not get data for key '"+prop_key+"': " + str(e)
                    self.logging.error(msg)
                    self.properties_get[prop_key].append(msg)

        return self.properties_get

    def get_properties_image(self):
        """
        read image and get properties
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

    def camera_status(self, source, name):
        """
        check if given source can be connected as PiCamera and returns an image
        Args:
        * source = device string, should be "/dev/picam"
        * name   = description for the camera
        """
        camera_info = {"dev": source, "info": name, "image": False, "shape": []}
        if source != "/dev/picam":
            try:
                camera = cv2.VideoCapture(source, cv2.CAP_V4L)
                time.sleep(0.1)

                if not camera.isOpened():
                    camera_info["error"] = "Error opening video."

                time.sleep(0.5)
                ref, raw = camera.read()
                camera.release()
                check = str(type(raw))
                if not ref:
                    if "error" not in camera_info:
                        camera_info["error"] = "Error reading image."

                elif "NoneType" in check or len(raw) == 0:
                    if "error" not in camera_info:
                        camera_info["error"] = "Returned empty image."
                else:
                    camera_info["image"] = True
                    camera_info["shape"] = raw.shape
                    camera_info["resolutions"] = self.camera_info.get_available_camera_resolutions(source)
                    birdhouse_picamera = True

                    path_raw = str(os.path.join(self.config.db_handler.directory(config="images"),
                                                "..", "test_connect_" + source.replace("/", "_") + ".jpeg"))
                    cv2.imwrite(path_raw, raw)

                    if "error" in camera_info:
                        del camera_info["error"]

            except cv2.error as e:
                camera_info["error"] = str(e)
        else:
            camera_info["error"] = "CV2 doesn't work with PiCamera under 64bit OS, us other camera handler instead."

        return camera_info

    def if_connected(self):
        """
        check if camera is connected
        """
        return self.connected

