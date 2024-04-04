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
    """
    Class to get camera information from the OS
    """

    def __init__(self):
        """
        init logging instance
        """
        self.logging = set_logging("cam-info")

    def get_available_cameras(self):
        """
        use v4l2_ctl to identify available cameras

        Returns:
            dict: different level of device definitions in a dict: 'list', 'short', 'complete'
        """
        try:
            process = subprocess.Popen(["v4l2-ctl --list-devices"], stdout=subprocess.PIPE, shell=True)
            output = process.communicate()[0]
            output = output.decode()
            output = output.split("\n")
        except Exception as e:
            ch_logging.error("Could not grab video devices. Check, if v4l2-ctl is installed. " + str(e))
            return system

        try:
            process = subprocess.Popen(["lsusb"], stdout=subprocess.PIPE, shell=True)
            ls_usb = process.communicate()[0]
            ls_usb = ls_usb.decode()
            ls_usb = ls_usb.split("\n")
        except Exception as e:
            ch_logging.warning("Could not video device bus information. Check, if lsusb is installed. " + str(e))
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
                devices["complete"][value] = {"dev": value, "info": last_key, "image": False, "shape": [], "bus": ""}

                for line in ls_usb:
                    if info[0] in line:
                        usb_values = line.split(":")
                        usb_values = usb_values[0].split(" ")
                        devices["complete"][value]["bus"] = usb_values[1] + "/" + usb_values[3]

        self.logging.debug("Found "+str(len(devices["list"]))+" devices.")
        self.logging.debug(str(devices))

        return devices.copy()

    def get_available_camera_resolutions(self, source):
        """
        use v4l2_ctl to identify available camera resolutions

        Args:
            source (string): device definition, e.g. /dev/video0
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
    """
    class to control PiCamera using PiCamera2
    """

    def __init__(self, camera_id, source, config):
        """
        create instance for PiCamera2
        documentation: https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf

        Args:
            camera_id (str): camera identifier
            source (str): source, e.g., /dev/video0
            config (modules.config.BirdhouseConfig): reference to main config handler
        """
        BirdhouseCameraClass.__init__(self, class_id=camera_id+"-pi", class_log="cam-pi",
                                      camera_id=camera_id, config=config)
        self.source = source
        self.stream = None
        self.transform = None
        self.configuration = {}
        self.property_keys = None
        self.properties_get = {}
        self.properties_not_used = None
        self.properties_set = None
        self.connected = False
        self.available_devices = {}
        self.first_connect = True
        self.create_test_images = False

        self.picamera_controls = {
            "saturation":       ["Saturation",          "rwm", 0.0, 32.0, "float"],
            "brightness":       ["Brightness",          "rwm", -1.0, 1.0, "float"],
            "contrast":         ["Contrast",            "rwm", 0.0, 32.0, "float"],
            "sharpness":        ["Sharpness",           "rw",  0.0, 16.0, "float"],
            "auto_wb":          ["AwbEnable",           "r",   -1, -1],
        }
        self.picamera_image = {
            "temperature":      ["ColourTemperature",   "r",   -1, -1],
            "exposure":         ["ExposureTime",        "r",   -1, -1],
            "focus":            ["FocusFoM",            "r",   -1, -1],
            "gain_digital":     ["DigitalGain",         "r",   0.0, 32.0],
            "gain_analogue":    ["AnalogueGain",        "r",   0.0, 32.0],
            "lux":              ["Lux",                 "r",   -1, -1]
        }
        self.picamera_cam = {
            "camera_model":         ["Model", "r"],
            "color_filter":         ["ColorFilterArrangement", "r"],
            "pixel_size":           ["PixelArraySize", "r"],
            "rotation":             ["Rotation", "r"],
            "sensor_sensitivity":   ["SensorSensitivity", "r"]
        }
        self.picamera_streams = ["raw", "main", "lores"]
        self.picamera_stream = ["size", "format", "stride", "framesize"]

        self.camera_info = CameraInformation()
        self.logging.info("Starting PiCamera2 support for '"+self.id+":"+source+"' ...")

    def connect(self):
        """
        connect with PiCamera

        Returns:
            bool | str: True, False or 'WARNING' depending on connection status
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

            self.get_properties()
            self.set_properties_init()
            if self.first_connect:
                self.logging.debug("------------------")
                self.logging.debug(" PiCamera2 initial config: " + str(self.configuration))
                self.logging.debug(" PiCamera2 GET: " + str(self.properties_get))
                self.logging.debug("------------------")

            self.first_connect = False
            self.connected = True

        try:
            self.logging.debug("Switch mode and capture first image")
            image = self.stream.switch_mode_and_capture_array(self.configuration, "main")
            if image is None or len(image) == 0:
                raise Exception("Returned empty image.")
            else:
                self.camera_create_test_image("switch mode and capture first image", image)
                self.logging.debug("- Done.")
            return True

        except Exception as err:
            self.raise_warning("- Error reading first image from PiCamera '"+self.source+"': " + str(err))
            return "WARNING"

    def reconnect(self):
        """
        reconnect camera

        Returns:
            bool | str: True, False or 'WARNING' depending on connection status
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
        self.logging.debug("Read image from PiCamera")
        try:
            raw = self.stream.capture_array("main")
            if raw is None or len(raw) == 0:
                raise Exception("Returned empty image.")
            else:
                self.logging.debug("- Done.")
            return raw
        except Exception as err:
            self.raise_error("- Error reading image from PiCamera2 '" + self.source +
                             "' by stream '" + stream + "': " + str(err))
            return

    def set_properties_init(self):
        """
        set properties based on configuration file
        """
        self.logging.debug("Set initial properties for '" + self.id + "' ...")
        self.properties_set = []
        for p_key in self.picamera_controls:
            if "w" in self.picamera_controls[p_key][1]:
                self.properties_set.append(p_key)

        if self.param["image"]["black_white"]:
            self.param["image_presets"]["saturation"] = 0

        self.stream.stop()
        for c_key in self.param["image_presets"]:
            if c_key in self.properties_get and "w" in self.properties_get[c_key][1]:
                result = self.set_properties(c_key, self.param["image_presets"][c_key], True)
                self.logging.debug("... set " + c_key + "=" + str(self.param["image_presets"][c_key]) + " - " +
                                   str(result))
        self.stream.start()
        self.camera_create_test_image("set properties init")

    def set_properties(self, key, value="", init=False):
        """
        set properties / controls for picamera2

        Args:
            key (str): internal key
            value (str): value to be set
            init (bool): initialization
        Return:
            bool: status if set property
        """
        self.logging.debug("Set property for '" + self.id + "': " + key + "=" + str(value) + " (" + str(init) + ")")

        if key in self.picamera_controls and "w" in self.picamera_controls[key][1]:
            full_key = self.picamera_controls[key][0]
            try:
                if not init:
                    self.stream.stop()
                self.configuration["controls"][full_key] = value
                self.stream.configure(self.configuration)
                if not init:
                    self.stream.start()
                return True
            except Exception as err:
                self.raise_error("Could not set to value for '" + str(full_key) + "': " + str(err))
                return False

        elif key in self.picamera_controls:
            full_key = self.picamera_controls[key][0]
            self.raise_error("Could not set to value for '" + str(full_key) +
                             "': property is classified as read only.")
            return False

        elif key in self.picamera_image:
            full_key = self.picamera_image[key][0]
            self.raise_error("Could not set to value for '" + str(full_key) + "': not implemented yet.")
            return False

        elif key in self.picamera_cam:
            full_key = self.picamera_cam[key][0]
            self.raise_error("Could not set to value for '" + str(full_key) + "': not implemented yet.")
            return False

        else:
            self.raise_error("Key '" + str(key) + "' is unknown!")
            return False

    def get_properties_available(self, keys="get"):
        """
        get available properties from Picamera2 using different methods; for more details see the full
        documentation: https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf; not all available properties
        are implemented.

        picamera2.capture_metadata() ... 'SensorTimestamp', 'ColourCorrectionMatrix', 'FocusFoM', 'ColourTemperature',
        'ColourGains', 'AeLocked', 'Lux', 'FrameDuration', 'SensorBlackLevels', 'DigitalGain', 'AnalogueGain',
        'ScalerCrop', 'ExposureTime'

        picamera2.camera_properties{} ... 'Model', 'UnitCellSize', 'Location', 'Rotation', 'PixelArraySize',
        'PixelArrayActiveAreas', 'ColorFilterArrangement', 'ScalerCropMaximum', 'SystemDevices', 'SensorSensitivity'

        picamera2.sensor_modes[] ... 'bit_depth', 'crop_limits', 'exposure_limits', 'format', 'fps', 'size','unpacked'

        Returns:
            list: keys for all properties that are implemented at the moment
        """
        if keys == "get":
            return list(self.properties_get.keys())
        elif keys == "set":
            return self.properties_set
        return self.property_keys

    def get_properties(self, key=""):
        """
        get properties from camera (camera_controls, image_properties, and camera properties);

        uses picamera2.camera_controls[<full_key>], picamera2.still_configuration.<full_key>, picamera2.capture_metadata(), and picamera2.camera_properties[..]

        Args:
            key (str): available keys: saturation, brightness, contrast, gain, sharpness, temperature, exposure,
                       auto_wb; if not set return complete list of properties
        Returns:
            dict | float: complete list of properties in format [current_value, "rwm", min_value, max_value]
                          or current value if key is set
        """
        self.logging.debug("(1) Get camera and stream properties for '" + self.id + "' (PiCamera2)")
        for c_key in self.picamera_controls:
            self.properties_get[c_key] = self.picamera_controls[c_key].copy()
            c_key_full = self.picamera_controls[c_key][0]
            try:
                min_exp, max_exp, default_exp = self.stream.camera_controls[c_key_full]
                self.properties_get[c_key][0] = default_exp
                self.properties_get[c_key][2] = min_exp
                self.properties_get[c_key][3] = max_exp
            except Exception as e:
                msg = "Could not get data for '" + c_key_full + "': " + str(e)
                self.properties_get[c_key][0] = -1
                self.properties_get[c_key].append(msg)
                self.logging.warning(msg)

            if c_key_full in self.configuration["controls"]:
                self.properties_get[c_key][0] = self.configuration["controls"][c_key_full]

        self.logging.debug("(2) Get camera and stream properties for '" + self.id + "' (PiCamera2)")
        for i_key in self.picamera_image:
            self.properties_get[i_key] = self.picamera_image[i_key].copy()
            i_key_full = self.picamera_image[i_key][0]
            self.logging.debug("- " + str(i_key))
            try:
                # the following command breaks complete server after an update / upgrade of the OS in 04-2024
                #image_properties = self.stream.capture_metadata()
                image_properties = {}
                if i_key_full in image_properties:
                    self.properties_get[i_key][0] = image_properties[i_key_full]
                else:
                    self.properties_get[i_key][0] = -1
            except Exception as e:
                self.logging.error("Could not capture metadata from stream: " + str(e))

        self.logging.debug("(3) Get camera and stream properties for '" + self.id + "' (PiCamera2)")
        for p_key in self.picamera_cam:
            self.properties_get[p_key] = self.picamera_cam[p_key].copy()
            p_key_full = self.picamera_cam[p_key][0]
            if p_key_full in self.stream.camera_properties:
                self.properties_get[p_key][0] = self.stream.camera_properties[p_key_full]

        self.logging.debug("(4) Get camera and stream properties for '" + self.id + "' (PiCamera2)")
        if key in self.properties_get:
            return self.properties_get[key][0]
        else:
            return self.properties_get

    def get_properties_image(self):
        """
        read image and get properties - not implemented yet

        Returns:
            dict: list image properties brightness, contrast, saturation (calculated from image)
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
        set saturation to 0 (black and white)

        Returns:
            bool: status setting camera to black and white mode
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

        Args:
            width (int): new image width
            height (int): new image height
        Returns:
            bool: status setting camera resolution
        """
        try:
            #self.configuration["main"]["size"] = (int(width), int(height))
            self.configuration["raw"]["size"] = (int(width), int(height))
            self.logging.debug("Set resolution: " + str(self.configuration["main"]["size"]))
            self.stream.stop()
            self.stream.configure(self.configuration)
            self.stream.start()
            time.sleep(1)
            self.logging.debug("Set resolution: Done.")
            return True
        except Exception as err:
            self.raise_error("Could not set resolution: " + str(err))
            return False

    def get_resolution(self, maximum=False):
        """
        get resolution of the device

        Args:
            maximum (bool): get maximum resolution (True) or current resolution (False)
        Returns:
            [int, int]: width, height
        """
        if maximum:
            (width, height) = self.stream.camera_properties['PixelArraySize']
        else:
            (width, height) = self.stream.still_configuration.main.size
        return [width, height]

    def camera_create_test_image(self, context="", image=None):
        """
        create test image incl. date and context information

        Args:
            image (numpy.ndarray): image to be saved
            context (str): name the context here
        """
        if not self.create_test_images:
            return

        try:
            if image is None:
                image = self.stream.capture_array("main")

            text = str(self.config.local_time()) + " - " + context
            image = cv2.putText(image, str(text), (30, 40), int(cv2.FONT_HERSHEY_SIMPLEX), 1, (0, 0, 0),
                                2, cv2.LINE_AA)
            image = cv2.putText(image, str(text), (30, 80), int(cv2.FONT_HERSHEY_SIMPLEX), 1, (255, 255, 255),
                                2, cv2.LINE_AA)

            image_path = os.path.join(birdhouse_main_directories["data"], "test_connect_" + self.id + ".jpg")
            cv2.imwrite(image_path, image)

            self.logging.debug("Save test image: " + context)
            self.logging.debug("               : " + image_path)

        except Exception as e:
            self.logging.warning("Could not save test image: " + image_path + " / " + str(e))

    def camera_status(self, source, name):
        """
        check if given source can be connected as PiCamera and returns an image

        Args:
            source (str): device string, should be "/dev/picam"
            name (str): description for the camera
        Returns:
            dict: camera information: 'dev', 'info', 'image', 'shape'
        """
        self.logging.debug("Camera status: " + str(source) + " / " + str(name))

        camera_info = {"dev": source, "info": name, "image": False, "shape": []}
        devices = self.camera_info.get_available_cameras()["complete"]
        for key in devices:
            if devices[key]["dev"] == source:
                camera_info["bus"] = devices[key]["bus"]

        if birdhouse_env["test_video_devices"] is not None and not birdhouse_env["test_video_devices"]:
            camera_info["image"] = True
            return camera_info

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

        Returns:
            bool: connection status
        """
        return self.connected


class BirdhouseCameraHandler(BirdhouseCameraClass):
    """
    class to control USB camera and PiCamera using Open-CV2
    """

    def __init__(self, camera_id, source, config):
        """
        create instance of USB camera or PiCamera

        Args:
            camera_id (str): camera identifier
            source (str): source, e.g., /dev/video0
            config (modules.config.BirdhouseConfig): reference to main config handler
        """
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

        Returns:
            bool: connection status
        """
        self.reset_error()
        self.connected = False

        time.sleep(1)
        self.reset_usb()
        time.sleep(3)

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

        Returns:
            bool: connection status
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

    def reset_usb(self):
        """
        Reset USB camera if bus information available
        """
        camera_info = self.camera_status(self.source, self.id)
        if camera_info["bus"] != "":
            try:
                process = subprocess.Popen(["usbreset "+camera_info["bus"]], stdout=subprocess.PIPE, shell=True)
                output = process.communicate()[0]
                output = output.decode()
                if " ok" not in output:
                    raise ("Could not reset USB device " + self.source + " bus " + camera_info["bus"])
                else:
                    self.logging.info("Reset of USB camera " + self.source + " done (Bus " + camera_info["bus"] + ").")
            except Exception as e:
                self.logging.error("Reset of USB camera failed: " + str(e))
        else:
            self.logging.warning("Reset of USB camera not possible, not bus information for " + self.source)

    def read(self, stream="not set"):
        """
        read image from camera

        Args:
            stream (str): stream name
        Returns:
            numpy.ndarray: raw image
        """
        self.logging.debug("Read image from '" + self.id + "' ...")
        try:
            ref, raw = self.stream.read()
            check = str(type(raw))
            if not ref:
                raise Exception("Error reading image.")
            if "NoneType" in check or len(raw) == 0:
                raise Exception("Returned empty image.")
            else:
                self.logging.debug("- Done.")
            return raw
        except Exception as err:
            self.raise_error("- Error reading image from camera '" + self.source +
                             "' by stream '" + stream + "': " + str(err))
            return

    def set_properties(self, key, value=""):
        """
        set camera parameter ...

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

        Args:
            key (str): key
            value (float): value
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

        Args:
            keys (str): get keys: 'get' or 'set'
        Returns:
            list: list of keys
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
        read image and get properties - not implemented yet

        Returns:
            dict: list image properties brightness, contrast, saturation (calculated from image)
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

        Returns:
            bool: black and white or not?
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

        Args:
            width (int): image width
            height (int): image height
        Returns:
            bool: setting status
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

        Args:
            maximum (bool): return maximum or current size
        Returns:
            (int, int): (width, height)
        """
        if maximum:
            high_value = 10000
            self.set_resolution(width=high_value, height=high_value)
        width = self.stream.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = self.stream.get(cv2.CAP_PROP_FRAME_HEIGHT)
        return [width, height]

    def camera_create_test_image(self, context="", image=None):
        """
        not implemented for USB cameras
        """
        return

    def camera_status(self, source, name):
        """
        check if given source can be connected as PiCamera and returns an image

        Args:
            source (str): device string, should be "/dev/picam"
            name (str): description for the camera
        Returns:
            dict: camera status
        """
        self.logging.debug("Camera status: " + str(source) + " / " + str(name))

        camera_info = {"dev": source, "info": name, "image": False, "shape": []}
        devices = self.camera_info.get_available_cameras()["complete"]
        for key in devices:
            if devices[key]["dev"] == source:
                camera_info["bus"] = devices[key]["bus"]

        if birdhouse_env["test_video_devices"] is not None and not birdhouse_env["test_video_devices"]:
            camera_info["image"] = True
            return camera_info

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

        Returns:
            bool: connection status
        """
        return self.connected

