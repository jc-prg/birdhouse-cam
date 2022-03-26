import io
import os
import time
import logging
import numpy as np

import cv2
from imutils.video import WebcamVideoStream
from imutils.video import FPS
from skimage.metrics import structural_similarity as ssim

import threading
from threading import Condition
from datetime import datetime


class BirdhouseVideoProcessing(threading.Thread):
    """
    Record videos: start and stop; from all pictures of the day
    """

    def __init__(self, camera, config, param, directory):
        """
        Initialize new thread and set inital parameters
        """
        threading.Thread.__init__(self)
        self.camera = camera
        self.name = param["name"]
        self.param = param
        self.config = config
        self.directory = directory

        self.recording = False
        self.processing = False
        self.max_length = 0.25 * 60
        self.info = {}
        self.ffmpeg_cmd = "ffmpeg -f image2 -r {FRAMERATE} -i {INPUT_FILENAMES} "
        self.ffmpeg_cmd += "-vcodec libx264 -crf 18"

        # Other working options:
        # self.ffmpeg_cmd  += "-b 1000k -strict -2 -vcodec libx264 -profile:v main -level 3.1 -preset medium - \
        #                      x264-params ref=4 -movflags +faststart -crf 18"
        # self.ffmpeg_cmd  += "-c:v libx264 -pix_fmt yuv420p"
        # self.ffmpeg_cmd  += "-profile:v baseline -level 3.0 -crf 18"
        # self.ffmpeg_cmd  += "-vcodec libx264 -preset fast -profile:v baseline -lossless 1 -vf \
        #                     \"scale=720:540,setsar=1,pad=720:540:0:0\" -acodec aac -ac 2 -ar 22050 -ab 48k"

        self.ffmpeg_cmd += " {OUTPUT_FILENAME}"
        self.ffmpeg_trim = "ffmpeg -y -i {INPUT_FILENAME} -r {FRAMERATE} -vcodec libx264 -crf 18 -ss {START_TIME} -to {END_TIME} {OUTPUT_FILENAME}"
        #       self.ffmpeg_trim  = "ffmpeg -y -i {INPUT_FILENAME} -c copy -ss {START_TIME} -to {END_TIME} {OUTPUT_FILENAME}"
        self.count_length = 8
        self.running = True

    def run(self):
        """
        Initialize, set inital values
        """
        logging.info("Initialize video recording ...")
        self.info = {
            "start": 0,
            "start_stamp": 0,
            "status": "ready"
        }
        if "video" in self.param and "max_length" in self.param["video"]:
            self.max_length = self.param["video"]["max_length"]
            logging.debug("Set max video recording length for " + self.camera + " to " + str(self.max_length))
        else:
            logging.debug("Use default max video recording length for " + self.camera + " = " + str(self.max_length))

        while self.running:
            time.sleep(1)

    def stop(self):
        """
        ending functions (nothing at the moment)
        """
        self.running = False
        return

    def start_recording(self):
        """
        Start recording
        """
        logging.info("Starting video recording ...")
        self.recording = True
        self.info["date"] = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        self.info["date_start"] = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.info["stamp_start"] = datetime.now().timestamp()
        self.info["status"] = "recording"
        self.info["camera"] = self.camera
        self.info["camera_name"] = self.name
        self.info["directory"] = self.directory
        self.info["image_count"] = 0
        return

    def stop_recording(self):
        """
        Stop recording and trigger video creation
        """
        logging.info("Stopping video recording ...")
        self.recording = False
        self.info["date_end"] = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.info["stamp_end"] = datetime.now().timestamp()
        self.info["status"] = "processing"
        self.info["length"] = round(self.info["stamp_end"] - self.info["stamp_start"], 1)

        if float(self.info["length"]) > 1:
            self.info["framerate"] = round(float(self.info["image_count"]) / float(self.info["length"]), 1)
        else:
            self.info["framerate"] = 0

        self.create_video()

        self.info["status"] = "finished"
        if not self.config.exists("videos"):
            config_file = {}
        else:
            config_file = self.config.read_cache("videos")
        config_file[self.info["date_start"]] = self.info
        self.config.write("videos", config_file)

        time.sleep(1)
        self.info = {}
        return

    def info_recording(self):
        """
        Get info of recording
        """
        if self.recording:
            self.info["length"] = round(datetime.now().timestamp() - self.info["stamp_start"], 1)
        elif self.processing:
            self.info["length"] = round(self.info["stamp_end"] - self.info["stamp_start"], 1)

        self.info["image_size"] = self.image_size

        if float(self.info["length"]) > 1:
            self.info["framerate"] = round(float(self.info["image_count"]) / float(self.info["length"]), 1)
        else:
            self.info["framerate"] = 0

        return self.info

    def auto_stop(self):
        """
        Check if maximum length is achieved
        """
        if self.info["status"] == "recording":
            max_time = float(self.info["stamp_start"] + self.max_length)
            if max_time < float(datetime.now().timestamp()):
                logging.info("Maximum recording time achieved ...")
                logging.info(str(max_time) + " < " + str(datetime.now().timestamp()))
                return True
        return False

    def status(self):
        """
        Return recording status
        """
        return self.record_video_info

    def save_image(self, image):
        """
       Save image
       """
        self.info["image_count"] += 1
        self.info["image_files"] = self.filename("vimages")
        self.info["video_file"] = self.filename("video")
        filename = self.info["image_files"] + str(self.info["image_count"]).zfill(self.count_length) + ".jpg"
        path = os.path.join(self.directory, filename)
        logging.debug("Save image as: " + path)

        return cv2.imwrite(path, image)

    def filename(self, ftype="image"):
        """
        generate filename for images
        """
        if ftype == "video":
            return self.config.imageName(image_type="video", timestamp=self.info["date_start"], camera=self.camera)
        elif ftype == "thumb":
            return self.config.imageName(image_type="thumb", timestamp=self.info["date_start"], camera=self.camera)
        elif ftype == "vimages":
            return self.config.imageName(image_type="vimages", timestamp=self.info["date_start"], camera=self.camera)
        else:
            return

    def create_video(self):
        """
        Create video from images
        """
        self.processing = True
        cmd_create = self.ffmpeg_cmd
        cmd_create = cmd_create.replace("{INPUT_FILENAMES}", os.path.join(self.config.directory("videos"),
                                                                          self.filename("vimages") + "%" + str(
                                                                              self.count_length).zfill(2) + "d.jpg"))
        cmd_create = cmd_create.replace("{OUTPUT_FILENAME}",
                                        os.path.join(self.config.directory("videos"), self.filename("video")))
        cmd_create = cmd_create.replace("{FRAMERATE}", str(round(self.info["framerate"])))

        self.info["thumbnail"] = self.filename("thumb")
        cmd_thumb = "cp " + os.path.join(self.config.directory("videos"), self.filename("vimages") + str(1).zfill(
            self.count_length) + ".jpg ") + os.path.join(self.config.directory("videos"), self.filename("thumb"))
        cmd_delete = "rm " + os.path.join(self.config.directory("videos"), self.filename("vimages") + "*.jpg")
        logging.info("start video creation with ffmpeg ...")

        logging.info(cmd_create)
        message = os.system(cmd_create)
        logging.debug(message)

        logging.info(cmd_thumb)
        message = os.system(cmd_thumb)
        logging.debug(message)

        logging.info(cmd_delete)
        message = os.system(cmd_delete)
        logging.debug(message)

        self.processing = False
        logging.info("OK.")
        return

    def trim_video(self, input_file, output_file, start_timecode, end_timecode, framerate):
        """
        creates a shortend version of the video
        """
        input_file = os.path.join(self.config.directory("videos"), input_file)
        output_file = os.path.join(self.config.directory("videos"), output_file)

        cmd = self.ffmpeg_trim
        cmd = cmd.replace("{START_TIME}", str(start_timecode))
        cmd = cmd.replace("{END_TIME}", str(end_timecode))
        cmd = cmd.replace("{INPUT_FILENAME}", str(input_file))
        cmd = cmd.replace("{OUTPUT_FILENAME}", str(output_file))
        cmd = cmd.replace("{FRAMERATE}", str(framerate))

        logging.info(cmd)
        message = os.system(cmd)
        logging.debug(message)

        if os.path.isfile(output_file):
            return "OK"
        else:
            return "Error"


class BirdhouseImageProcessing(object):
    """
    modify encoded and raw images
    """
    def __init__(self, camera, config, param):
        self.frame = None
        self.camera = camera
        self.config = config
        self.param = param


class BirdhouseCameraOutput(object):
    """
    Create camera output
    """

    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # New frame, copy the existing buffer's content and notify all
            # clients it's available
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)


class BirdhouseCamera(threading.Thread):

    def __init__(self, thread_id, config, sensor):
        """
        Initialize new thread and set initial parameters
        """
        threading.Thread.__init__(self)
        self.id = thread_id
        self.config = config
        self.sensor = sensor

        self.param = self.config.param["cameras"][self.id]
        self.name = self.param["name"]
        self.active = self.param["active"]
        self.source = self.param["source"]
        self.type = self.param["type"]
        self.record = self.param["record"]

        self.video = BirdhouseVideoProcessing(camera=self.id, config=self.config, param=self.param, directory=self.config.directory("videos"))
        self.image = BirdhouseImageProcessing(camera=self.id, config=self.config, param=self.param)

        self.running = True
        self.pause = False
        self.error = False
        self.error_time = 0
        self.error_image = False
        self.error_image_msg = []

        self.text_default_position = (30, 40)
        self.text_default_scale = 0.8
        self.text_default_font = cv2.FONT_HERSHEY_SIMPLEX
        self.text_default_color = (255, 255, 255)
        self.text_default_thickness = 2
        self.image_size = [0, 0]
        self.previous_image = None
        self.previous_stamp = "000000"
        self.camera_NA = os.path.join(self.config.main_directory, self.config.directories["data"], "camera_na.jpg")
        self.image_NA_raw = cv2.imread(self.camera_NA)
        self.image_NA = self.convertRawImage2Image(self.image_NA_raw)

        logging.info("Starting camera (" + self.id + "/" + self.type + "/" + self.name + ") ...")

        if self.type == "pi":
            self.camera_start_pi()
        elif self.type == "usb":
            self.camera_start_usb()
        else:
            self.camera_error(True, False, "Unknown type of camera!")
        if not self.error and self.param["video"]["allow_recording"]:
            self.video_start_recording()

        logging.debug("Length " + self.camera_NA + " - File:" + str(len(self.image_NA)) + "/Img:" + str(len(self.image_NA_raw)))
        logging.debug("HOURS:   " + str(self.param["image_save"]["hours"]))
        logging.debug("SECONDS: " + str(self.param["image_save"]["seconds"]))

    def run(self):
        """
        Start recording for livestream and save images every x seconds
        """
        similarity = 0
        while self.running:
            seconds = datetime.now().strftime('%S')
            hours = datetime.now().strftime('%H')
            stamp = datetime.now().strftime('%H%M%S')

            i = 0
            while self.pause and self.running:
                logging.debug("Paused ...")
                time.sleep(0.1)

            # Error with camera - try to restart from time to time
            if self.error:
                retry_time = 60
                if self.error_time + retry_time < time.time():
                    logging.info("Try to restart camera ...")
                    self.active = True
                    if self.type == "pi":
                        self.camera_start_pi()
                    elif self.type == "usb":
                        self.camera_start_usb()
                    self.error_time = time.time()
                    time.sleep(1)

            # Video Recording
            elif self.video.recording:

                if self.video.auto_stop():
                    self.video.stop_recording()

                else:
                    image = self.getImage()
                    image = self.convertImage2RawImage(image)
                    self.video.image_size = self.image_size
                    self.video.save_image(image=image)

                    if self.image_size == [0, 0]:
                        self.image_size = self.sizeRawImage(image)
                        self.video.image_size = self.image_size

                    logging.debug(".... Video Recording: " + str(self.video.info["stamp_start"]) + " -> " + str(
                        datetime.now().strftime("%H:%M:%S")))

            # Image Recording (if not video recording)
            else:
                time.sleep(1)
                if self.record:
                    if (seconds in self.param["image_save"]["seconds"]) and (
                            hours in self.param["image_save"]["hours"]):

                        image = self.getRawImage()
                        image = self.normalizeRawImage(image)
                        image_compare = self.convertRawImage2Gray(image)

                        if self.param["image"]["date_time"]:
                            image = self.setDateTime2RawImage(image)

                        if self.image_size == [0, 0]:
                            self.image_size = self.sizeRawImage(image)
                            self.video.image_size = self.image_size

                        if self.previous_image is not None:
                            similarity = str(self.compareRawImages(imageA=image_compare, imageB=self.previous_image,
                                                                   detection_area=self.param["similarity"][
                                                                       "detection_area"]))

                        image_info = {
                            "camera": self.id,
                            "hires": self.config.imageName("hires", stamp, self.id),
                            "lowres": self.config.imageName("lowres", stamp, self.id),
                            "compare": (stamp, self.previous_stamp),
                            "datestamp": datetime.now().strftime("%Y%m%d"),
                            "date": datetime.now().strftime("%d.%m.%Y"),
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "similarity": similarity,
                            "sensor": {},
                            "size": self.image_size
                        }
                        for key in self.sensor:
                            if self.sensor[key].running and not self.sensor[key].error:
                                image_info["sensor"][key] = self.sensor[key].get_values()
                                self.writeSensorInfo(stamp=stamp, data=self.sensor[key].get_values())

                        path_lowres = os.path.join(self.config.directory("images"), self.config.imageName("lowres", stamp, self.id))
                        path_hires = os.path.join(self.config.directory("images"), self.config.imageName("hires", stamp, self.id))

                        logging.debug("WRITE:" + path_lowres)

                        self.writeImageInfo(timestamp=stamp, data=image_info)
                        self.writeImage(filename=path_hires, image=image)
                        self.writeImage(filename=path_lowres, image=image, scale_percent=self.param["preview_scale"])

                        self.previous_image = image_compare
                        self.previous_stamp = stamp

        logging.info("Stopped camera (" + self.id + "/" + self.type + ").")

    def wait(self):
        """
        Wait with recording between two pictures
        """
        if self.type == "pi":
            self.camera.wait_recording(0.1)
        if self.type == "usb":
            time.sleep(0.1)

    def stop(self):
        """
        Stop recording
        """
        if not self.error and self.active:
            if self.type == "pi":
                self.camera.stop_recording()
                self.camera.close()

            elif self.type == "usb":
                self.camera.stop()
                self.cameraFPS.stop()

            if self.video:
                self.video.stop()

        self.running = False

    def camera_start_pi(self):
        try:
            import picamera
        except ImportError:
            self.camera_error(True, False, "Module for PiCamera isn't installed. Try 'pip3 install picamera'.")
        try:
            self.camera = picamera.PiCamera()
            self.output = BirdhouseCameraOutput()
            self.camera.resolution = self.param["image"]["resolution"]
            self.camera.framerate = self.param["image"]["framerate"]
            self.camera.rotation = self.param["image"]["rotation"]
            self.camera.saturation = self.param["image"]["saturation"]
            # self.camera.zoom = self.param["image"]["crop"]
            # self.camera.annotate_background = picamera.Color('black')
            self.camera.start_recording(self.output, format='mjpeg')
            logging.info(self.id + ": OK.")
        except Exception as e:
            self.camera_error(True, False, "Starting PiCamera doesn't work!\n" + str(e))

    def camera_start_usb(self):
        try:
            # cap                    = cv2.VideoCapture(0) # check if camera is available
            # if cap is None or not cap.isOpened(): raise
            self.camera = WebcamVideoStream(src=self.source).start()
            self.cameraFPS = FPS().start()
            if self.getImage() == "":
                raise Exception("Error during first image capturing.")
            logging.info(self.id + ": OK (Source=" + str(self.source) + ")")
        except Exception as e:
            self.camera_error(True, False, "Starting USB camera doesn't work: " + str(e))

    def camera_error(self, cam_error, active, message, image_error=False):
        """
        Report Error, set variables of modules
        """
        self.error = cam_error
        self.error_time = time.time()
        self.active = active
        if image_error:
            self.error_image = True
            self.error_image_msg.append(exception)

        logging.error(self.id + ": "+message+" ("+str(self.error_time)+")")

    def video_start_recording(self):
        self.video.start()
        self.video.image_size = self.image_size

    def setText(self, text):
        """
        Add / replace text on the image
        """
        if self.type == "pi":
            self.camera.annotate_text = str(text)

    def setText2RawImage(self, image, text, position="", font="", scale="", color="", thickness=0):
        """
        Add text on image
        """
        if position == "":
            position = self.text_default_position
        if font == "":
            font = self.text_default_font
        if scale == "":
            scale = self.text_default_scale
        if color == "":
            color = self.text_default_color
        if thickness == 0:
            thickness = self.text_default_thickness

        image = cv2.putText(image, text, position, font, scale, color, thickness, cv2.LINE_AA)
        return image

    def setText2Image(self, image, text, position="", font="", scale="", color="", thickness=0):
        """
       Add text on image
       """
        image = self.convertImage2RawImage(image)
        image = self.setText2RawImage(image, text, position=position, font=font, scale=scale, color=color,
                                      thickness=thickness)
        image = self.convertRawImage2Image(image)
        return image

    def setDateTime2Image(self, image):
        date_information = datetime.now().strftime('%d.%m.%Y %H:%M:%S')

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
        if self.param["image"]["date_time_size"]:
            scale = self.param["image"]["date_time_size"]
        else:
            scale = ""

        image = self.setText2Image(image, date_information, position, font, scale, color, thickness)
        return image

    def setDateTime2RawImage(self, image):
        date_information = datetime.now().strftime('%d.%m.%Y %H:%M:%S')

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
        if self.param["image"]["date_time_size"]:
            scale = self.param["image"]["date_time_size"]
        else:
            scale = ""

        image = self.setText2RawImage(image, date_information, position, font, scale, color, thickness)
        return image

    def getImage(self):
        """
        read image from device
        """
        if self.error_image:
            return self.image_NA

        elif self.type == "pi":
            with self.output.condition:
                self.output.condition.wait()
                encoded = self.output.frame
            return encoded.copy()

        elif self.type == "usb":
            try:
                raw = self.camera.read()  ## potentially not the same RAW as fram PI
                encoded = self.convertRawImage2Image(raw)
                return encoded.copy()

            except Exception as e:
                error_msg = "Can't encode image from camera: " + str(e)
                self.camera_error(False, True, error_msg, True)
                return ""

        else:
            error_msg = "Camera type not supported (" + str(self.type) + ")."
            self.camera_error(True, False, error_msg, True)
            return ""

    def getRawImage(self):
        """
        get image and convert to raw
        """
        if self.error_image:
            return self.image_NA_raw

        if self.type == "pi":
            with self.output.condition:
                self.output.condition.wait()
                encoded = self.output.frame
            raw = self.convertImage2RawImage(encoded)
            return raw.copy()

        elif self.type == "usb":
            try:
                raw = self.camera.read()  ## potentially not the same RAW as fram PI
                return raw.copy()

            except Exception as e:
                error_msg = "Cant encode image from camera: " + str(e)
                self.camera_error(False, True, error_msg, True)
                return ""
        else:
            error_msg = "Camera type not supported (" + str(self.type) + ")."
            self.camera_error(True, False, error_msg, True)
            return ""

    def normalizeRawImage(self, image, color="", compare=False):
        """
        apply presets per camera to image
        """
        if self.error_image:
            return self.image_NA_raw

        if self.type == "usb":
            # crop image
            if not "crop_area" in self.param["image"]:
                normalized, self.param["image"]["crop_area"] = self.cropRawImage(frame=image, crop_area=self.param["image"]["crop"], crop_type="relative")
            else:
                normalized, self.param["image"]["crop_area"] = self.cropRawImage(frame=image, crop_area=self.param["image"]["crop_area"], crop_type="pixel")
            # rotate     - not implemented yet
            # resize     - not implemented yet
            # saturation - not implemented yet
        else:
            normalized = image

        return normalized

    def convertRawImage2Image(self, raw):
        """
        convert from raw image to image // untested
        """
        if self.error_image:
            return self.image_NA

        try:
            r, buf = cv2.imencode(".jpg", raw)
            size = len(buf)
            image = bytearray(buf)
            return image

        except Exception as e:
            error_msg = self.id + ": Error convert RAW image -> image: " + str(e)
            logging.error(error_msg)
            self.error_image_msg.append(error_msg)
            self.error_image = True

    def convertImage2RawImage(self, image):
        """
        convert from device to raw image -> to be modifeid with CV2
        """
        if self.error_image:
            return self.image_NA_raw

        try:
            image = np.frombuffer(image, dtype=np.uint8)
            image = cv2.imdecode(image, 1)
            return image

        except Exception as e:
            error_msg = self.id + ": Error convert image -> RAW image: " + str(e)
            logging.error(error_msg)
            self.error_image_msg.append(error_msg)
            self.error_image = True

    def convertRawImage2Gray(self, image):
        """
        convert image from RGB to gray scale image (e.g. for analyzing similarity)
        """
        try:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        except Exception as e:
            error_msg = self.id + ": Error convert image to gray scale: " + str(e)
            logging.error(error_msg)
            self.error_image_msg.append(error_msg)
            self.error_image = True

    def drawImageDetectionArea(self, image):
        """
        Draw a red rectangle into the image to show detection area
        """
        image = self.convertImage2RawImage(image)
        image = self.drawRawImageDetectionArea(image)
        image = self.convertRawImage2Image(image)
        return image

    def drawRawImageDetectionArea(self, image):
        """
        Draw a red rectangle into the image to show detection area
        """
        # draw yellow rectangle for crop area
        color = (0, 255, 255)  # color in BGR
        thickness = 4
        height = image.shape[0]
        width = image.shape[1]

        (w_start, h_start, w_end, h_end) = self.param["image"]["crop"]
        x_start = int(round(width * w_start, 0))
        y_start = int(round(height * h_start, 0))
        x_end = int(round(width * w_end, 0))
        y_end = int(round(height * h_end, 0))

        logging.debug(self.id + ": show crop area ... " + str(self.param["image"]["crop"]))
        try:
            image = cv2.line(image, (x_start, y_start), (x_start, y_end), color, thickness)
            image = cv2.line(image, (x_start, y_start), (x_end, y_start), color, thickness)
            image = cv2.line(image, (x_end, y_end), (x_start, y_end), color, thickness)
            image = cv2.line(image, (x_end, y_end), (x_end, y_start), color, thickness)
            logging.debug("... top XY: " + str(x_start) + "/" + str(y_start) + " - bottom XY: " + str(x_end) + "/" + str(y_end))

        except Exception as e:
            error_msg = self.id + ": Error convert image to gray scale: " + str(e)
            logging.error(error_msg)
            self.error_image_msg.append(error_msg)
            self.error_image = True
            return ""

        # draw red rectangle for detection area
        color = (0, 0, 255)  # color in BGR
        thickness = 4
        d_height = x_end - x_start
        d_width = y_end - y_start
        y_offset = round((height - d_height)/2)
        x_offset = round((width - d_width)/2)

        logging.debug(self.id+": calculate image ... h/w: "+str(height)+"/"+str(width)+" dh/dw: "+str(d_height)+"/"+str(d_width))
        logging.debug(self.id+": calculate image ... w/h_offset: "+str(y_offset)+"/"+str(y_offset))

        (w_start, h_start, w_end, h_end) = self.param["similarity"]["detection_area"]
        x_start = int(round(d_width * w_start, 0)) + x_offset
        y_start = int(round(d_height * h_start, 0)) + y_offset
        x_end = int(round(d_width * w_end, 0)) + x_offset
        y_end = int(round(d_height * h_end, 0)) + y_offset

        logging.debug(self.id + ": show detection area ... " + str(self.param["similarity"]["detection_area"]))
        try:
            image = cv2.line(image, (x_start, y_start), (x_start, y_end), color, thickness)
            image = cv2.line(image, (x_start, y_start), (x_end, y_start), color, thickness)
            image = cv2.line(image, (x_end, y_end), (x_start, y_end), color, thickness)
            image = cv2.line(image, (x_end, y_end), (x_end, y_start), color, thickness)
            logging.debug("... top XY: " + str(x_start) + "/" + str(y_start) + " - bottom XY: " + str(x_end) + "/" + str(y_end))
            return image

        except Exception as e:
            error_msg = self.id + ": Error convert image to gray scale: " + str(e)
            logging.error(error_msg)
            self.error_image_msg.append(error_msg)
            self.error_image = True

    def sizeRawImage(self, frame):
        """
        Return size of raw image
        """
        try:
            height = frame.shape[0]
            width = frame.shape[1]
            return [width, height]

        except Exception as e:
            logging.warning(self.id + ": Could not analyze image: " + str(e))
            return [0, 0]

    def cropImage(self, frame, crop_area, crop_type="relative"):
        """
        crop encoded image
        """
        raw = self.convertImage2RawImage(frame)
        raw = self.cropRawImage(raw, crop_area, crop_type)
        crop = self.convertRawImage2Image(raw)
        return crop

    def cropRawImage(self, frame, crop_area, crop_type="relative"):
        """
        crop image using relative dimensions (0.0 ... 1.0)
        """
        try:
            height = frame.shape[0]
            width = frame.shape[1]

            if crop_type == "relative":
                (w_start, h_start, w_end, h_end) = crop_area
                x_start = int(round(width * w_start, 0))
                y_start = int(round(height * h_start, 0))
                x_end = int(round(width * w_end, 0))
                y_end = int(round(height * h_end, 0))
                crop_area = (x_start, y_start, x_end, y_end)
            else:
                (x_start, y_start, x_end, y_end) = crop_area

            logging.debug("H: " + str(y_start) + "-" + str(y_end) + " / W: " + str(x_start) + "-" + str(x_end))
            frame_cropped = frame[y_start:y_end, x_start:x_end]
            return frame_cropped, crop_area

        except Exception as e:
            logging.warning(self.id + ": Could not crop image: " + str(e))

        return frame, (0, 0, 1, 1)

    def compareImages(self, imageA, imageB, detection_area=None):
        """
        calculate structual similarity index (SSIM) of two images
        """
        imageA = self.convertImage2RawImage(imageA)
        imageB = self.convertImage2RawImage(imageB)
        similarity = self.compareRawImages(imageA, imageB, detection_area)
        return similarity

    def compareRawImages(self, imageA, imageB, detection_area=None):
        """
        calculate structual similarity index (SSIM) of two images
        """
        if len(imageA) == 0 or len(imageB) == 0:
            logging.warning(
                self.id + ": At least one file has a zero length - A:" + str(len(imageA)) + "/ B:" + str(len(imageB)))
            score = 0

        else:
            if detection_area != None:
                logging.debug(self.id + "/compare 1: " + str(detection_area) + " / " + str(imageA.shape))
                imageA, area = self.cropRawImage(frame=imageA, crop_area=detection_area, crop_type="relative")
                imageB, area = self.cropRawImage(frame=imageB, crop_area=detection_area, crop_type="relative")
                logging.debug(self.id + "/compare 2: " + str(area) + " / " + str(imageA.shape))

            try:
                (score, diff) = ssim(imageA, imageB, full=True)

            except Exception as e:
                logging.warning(self.id + ": Error comparing images: " + str(e))
                score = 0

        return round(score * 100, 1)

    def detectImage(self, file_info):
        """
       check if similarity is under threshold
       """
        threshold = float(self.param["similarity"]["threshold"])
        similarity = float(file_info["similarity"])
        if similarity != 0 and similarity < threshold:
            return 1
        else:
            return 0

    def selectImage(self, timestamp, file_info, check_similarity=True):
        """
        check image properties to decide if image is a selected one (for backup and view with selected images)
        """
        if "similarity" not in file_info:
            return False

        elif ("camera" in file_info and file_info["camera"] == self.id) or ("camera" not in file_info and self.id == "cam1"):

            if "to_be_deleted" in file_info and int(file_info["to_be_deleted"]) == 1:
                return False

            elif "favorit" in file_info and int(file_info["favorit"]) == 1:
                return True

            elif "00" + str(self.param["image_save"]["seconds"][0]) in timestamp:
                return True

            elif check_similarity:
                threshold = float(self.param["similarity"]["threshold"])
                similarity = float(file_info["similarity"])
                if similarity != 0 and similarity < threshold:
                    return True

            else:
                return True  ### to be checked !!!

        return False

    def writeImage(self, filename, image, scale_percent=100):
        """
       Scale image and write to file
       """
        image_path = os.path.join(self.config.param["path"], filename)
        logging.debug("Write image: " + image_path)

        if scale_percent != 100:
            width = int(image.shape[1] * scale_percent / 100)
            height = int(image.shape[0] * scale_percent / 100)
            image = cv2.resize(image, (width, height))

        return cv2.imwrite(image_path, image)

    def writeImageInfo(self, timestamp, data):
        """
        Write image information to file
        """
        logging.debug(self.id+": Write image info: " + self.config.file("images"))
        if os.path.isfile(self.config.file("images")):
            files = self.config.read_cache("images")
            files[timestamp] = data.copy()
            self.config.write("images", files)

    def writeVideoInfo(self, stamp, data):
        """
        Write image information to file
        """
        logging.debug(self.id + ": Write video info: " + self.config.file("images"))
        if os.path.isfile(self.config.file("videos")):
            files = self.config.read_cache("videos")
            files[stamp] = data
            self.config.write("videos", files)

    def writeSensorInfo(self, stamp, data):
        """
        Write Sensor information to separate config file (for recovery purposes)
        """
        logging.debug(self.id + ": Write video info: " + self.config.file("images"))
        if os.path.isfile(self.config.file("sensor")):
            files = self.config.read_cache("sensor")
        else:
            files = {}
        files[stamp] = data
        self.config.write("sensor", files)

    def createDayVideo(self, filename, stamp, date):
        """
        Create daily video from all single images available
        """
        camera = self.id
        cmd_videofile = "video_" + camera + "_" + stamp + ".mp4"
        cmd_thumbfile = "video_" + camera + "_" + stamp + "_thumb.jpeg"
        cmd_tempfiles = "img_" + camera + "_" + stamp + "_"
        framerate = 20

        cmd_rm = "rm " + self.config.directory("videos_temp") + "*"
        logging.info(cmd_rm)
        message = os.system(cmd_rm)

        cmd_copy = "cp " + self.config.directory("images") + filename + "* " + self.config.directory("videos_temp")
        logging.info(cmd_copy)
        message = os.system(cmd_copy)
        if message != 0:
            response = {
                "result": "error",
                "reason": "copy temp image files",
                "message": message
            }
            return response

        cmd_filename = self.config.directory("videos_temp") + cmd_tempfiles
        cmd_rename = "i=0; for fi in " + self.config.directory(
            "videos_temp") + "image_*; do mv \"$fi\" $(printf \"" + cmd_filename + "%05d.jpg\" $i); i=$((i+1)); done"
        logging.info(cmd_rename)
        message = os.system(cmd_rename)
        if message != 0:
            response = {
                "result": "error",
                "reason": "rename temp image files",
                "message": message
            }
            return response

        amount = 0
        for root, dirs, files in os.walk(self.config.directory("videos_temp")):
            for filename in files:
                if cmd_tempfiles in filename:
                    amount += 1

        cmd_create = self.video.ffmpeg_cmd
        cmd_create = cmd_create.replace("{INPUT_FILENAMES}", cmd_filename + "%05d.jpg")
        cmd_create = cmd_create.replace("{OUTPUT_FILENAME}",
                                        os.path.join(self.config.directory("videos"), cmd_videofile))
        cmd_create = cmd_create.replace("{FRAMERATE}", str(framerate))
        logging.info(cmd_create)
        message = os.system(cmd_create)
        if message != 0:
            response = {
                "result": "error",
                "reason": "create video with ffmpeg",
                "message": message
            }
            return response

        cmd_thumb = "cp " + cmd_filename + "00001.jpg " + self.config.directory("videos") + cmd_thumbfile
        logging.info(cmd_thumb)
        message = os.system(cmd_thumb)
        if message != 0:
            response = {
                "result": "error",
                "reason": "create thumbnail",
                "message": message
            }
            return response

        cmd_rm2 = "rm " + self.config.directory("videos_temp") + "*.jpg"
        logging.info(cmd_rm2)
        message = os.system(cmd_rm2)
        if message != 0:
            response = {
                "result": "error",
                "reason": "remove temp image files",
                "message": message
            }
            return response

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

        self.writeVideoInfo(stamp=stamp, data=video_data)

        return {"result": "OK"}

    def trimVideo(self, video_id, start, end):
        """
        create a shorter video based on date and time
        """
        config_file = self.config.read_cache("videos")
        if video_id in config_file:
            input_file = config_file[video_id]["video_file"]
            output_file = input_file.replace(".mp4", "_short.mp4")
            framerate = config_file[video_id]["framerate"]
            result = self.video.trim_video(input_file=input_file, output_file=output_file, start_timecode=start,
                                           end_timecode=end, framerate=framerate)
            if result == "OK":
                config_file[video_id]["video_file_short"] = output_file
                config_file[video_id]["video_file_short_start"] = float(start)
                config_file[video_id]["video_file_short_end"] = float(end)
                config_file[video_id]["video_file_short_length"] = float(end) - float(start)

                self.config.write("videos", config_file)
                return {"result": "OK"}
            else:
                return {"result": "Error while creating shorter video."}

        else:
            logging.warning("No video with the ID " + str(video_id) + " available.")
            return {"result": "No video with the ID " + str(video_id) + " available."}
