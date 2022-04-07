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
        logging.info("- Loading Video Processing for " + camera + "... ")
        self.id = camera
        self.camera = camera
        self.name = param["name"]
        self.param = param
        self.config = config
        self.directory = directory

        self.record_video_info = None
        self.image_size = [0, 0]
        self.recording = False
        self.processing = False
        self.max_length = 0.25 * 60
        self.info = {}
        self.output = None
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
        # self.ffmpeg_trim  = "ffmpeg -y -i {INPUT_FILENAME} -c copy -ss {START_TIME} -to {END_TIME} {OUTPUT_FILENAME}"
        self.count_length = 8
        self.running = True
        self.error = False
        self.error_msg = []

    def _msg_error(self, message):
        """
        Report Error, set variables of modules, collect last 3 messages in var self.error_msg
        """
        logging.error("Video Processing (" + self.id + "): " + message)
        self.error = True
        self.error_msg.append(message)
        if len(self.error_msg) >= 3:
            self.error_msg.pop()

    def _msg_warning(self, message):
        """
        Report Error, set variables of modules
        """
        logging.warning("Video Processing (" + self.id + "): " + message)

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
            return self.config.imageName(image_type="video", timestamp=self.info["date_start"], camera=self.camera)
        elif file_type == "thumb":
            return self.config.imageName(image_type="thumb", timestamp=self.info["date_start"], camera=self.camera)
        elif file_type == "vimages":
            return self.config.imageName(image_type="vimages", timestamp=self.info["date_start"], camera=self.camera)
        else:
            return

    def record_start(self):
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

    def record_stop(self):
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

    def record_stop_auto(self):
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

    def record_info(self):
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
        logging.info("Start video creation with ffmpeg ...")

        try:
            logging.info(cmd_create)
            message = os.system(cmd_create)
            logging.debug(message)

            logging.info(cmd_thumb)
            message = os.system(cmd_thumb)
            logging.debug(message)

            logging.info(cmd_delete)
            message = os.system(cmd_delete)
            logging.debug(message)

        except Exception as e:
            self._msg_error("Error during video creation: " + str(e))

        self.processing = False
        logging.info("OK.")
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
        logging.debug("Save image as: " + path)

        try:
            logging.debug("Write  image '" + path + "')")
            return cv2.imwrite(path, image)
        except Exception as e:
            self._msg_error("Could not save image '" + filename + "': " + str(e))

    def create_video_day(self, filename, stamp, date):
        """
        Create daily video from all single images available
        """
        camera = self.id
        cmd_videofile = "video_" + camera + "_" + stamp + ".mp4"
        cmd_thumbfile = "video_" + camera + "_" + stamp + "_thumb.jpeg"
        cmd_tempfiles = "img_" + camera + "_" + stamp + "_"
        framerate = 20
        message = ""

        try:
            cmd_rm = "rm " + self.config.directory("videos_temp") + "*"
            logging.debug(cmd_rm)
            message = os.system(cmd_rm)
            if message != 0:
                response = {
                    "result": "error",
                    "reason": "copy temp image files",
                    "message": message
                }
                self._msg_error("Error during day video creation: copy temp image files.")
                return response
        except Exception as e:
            self._msg_error("Error during day video creation: " + str(e))

        try:
            cmd_copy = "cp " + self.config.directory("images") + filename + "* " + self.config.directory("videos_temp")
            logging.debug(cmd_copy)
            message = os.system(cmd_copy)
            if message != 0:
                response = {
                    "result": "error",
                    "reason": "copy temp image files",
                    "message": message
                }
                self._msg_error("Error during day video creation: copy temp image files.")
                return response
        except Exception as e:
            self._msg_error("Error during day video creation: " + str(e))

        cmd_filename = self.config.directory("videos_temp") + cmd_tempfiles
        cmd_rename = "i=0; for fi in " + self.config.directory(
            "videos_temp") + "image_*; do mv \"$fi\" $(printf \"" + cmd_filename + "%05d.jpg\" $i); i=$((i+1)); done"

        try:
            logging.info(cmd_rename)
            message = os.system(cmd_rename)
            if message != 0:
                response = {
                    "result": "error",
                    "reason": "rename temp image files",
                    "message": message
                }
                self._msg_error("Error during day video creation: rename temp image files.")
                return response
        except Exception as e:
            self._msg_error("Error during day video creation: " + str(e))

        amount = 0
        for root, dirs, files in os.walk(self.config.directory("videos_temp")):
            for filename in files:
                if cmd_tempfiles in filename:
                    amount += 1

        cmd_create = self.ffmpeg_cmd
        cmd_create = cmd_create.replace("{INPUT_FILENAMES}", cmd_filename + "%05d.jpg")
        cmd_create = cmd_create.replace("{OUTPUT_FILENAME}",
                                        os.path.join(self.config.directory("videos"), cmd_videofile))
        cmd_create = cmd_create.replace("{FRAMERATE}", str(framerate))

        try:
            logging.debug(cmd_create)
            message = os.system(cmd_create)
            if message != 0:
                response = {
                    "result": "error",
                    "reason": "create video with ffmpeg",
                    "message": message
                }
                self._msg_error("Error during day video creation: create video with ffmpeg.")
                return response
        except Exception as e:
            self._msg_error("Error during day video creation: " + str(e))

        cmd_thumb = "cp " + cmd_filename + "00001.jpg " + self.config.directory("videos") + cmd_thumbfile
        logging.info(cmd_thumb)
        message = os.system(cmd_thumb)
        try:
            if message != 0:
                response = {
                    "result": "error",
                    "reason": "create thumbnail",
                    "message": message
                }
                self._msg_error("Error during day video creation: create thumbnails.")
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
                self._msg_error("Error during day video creation: remove temp image files.")
                return response
        except Exception as e:
            self._msg_error("Error during day video creation: " + str(e))

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

    def create_video_trimmed(self, video_id, start, end):
        """
        create a shorter video based on date and time
        """
        config_file = self.config.read_cache("videos")
        if video_id in config_file:
            input_file = config_file[video_id]["video_file"]
            output_file = input_file.replace(".mp4", "_short.mp4")
            framerate = config_file[video_id]["framerate"]
            result = self.trim_video(input_file=input_file, output_file=output_file, start_timecode=start,
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

    def trim_video(self, input_file, output_file, start_timecode, end_timecode, framerate):
        """
        creates a shortened version of the video
        """
        input_file = os.path.join(self.config.directory("videos"), input_file)
        output_file = os.path.join(self.config.directory("videos"), output_file)

        cmd = self.ffmpeg_trim
        cmd = cmd.replace("{START_TIME}", str(start_timecode))
        cmd = cmd.replace("{END_TIME}", str(end_timecode))
        cmd = cmd.replace("{INPUT_FILENAME}", str(input_file))
        cmd = cmd.replace("{OUTPUT_FILENAME}", str(output_file))
        cmd = cmd.replace("{FRAMERATE}", str(framerate))

        try:
            logging.debug(cmd)
            message = os.system(cmd)
            logging.debug(message)
        except Exception as e:
            self._msg_error("Error during video trimming: " + str(e))

        if os.path.isfile(output_file):
            return "OK"
        else:
            return "Error"


class BirdhouseImageProcessing(object):
    """
    modify encoded and raw images
    """

    def __init__(self, camera, config, param):
        logging.info("- Loading Image Processing for " + camera + "... ")
        self.frame = None
        self.id = camera
        self.config = config
        self.param = param

        self.text_default_position = (30, 40)
        self.text_default_scale = 0.8
        self.text_default_font = cv2.FONT_HERSHEY_SIMPLEX
        self.text_default_color = (255, 255, 255)
        self.text_default_thickness = 2

        self.img_camera_error = "camera_na.jpg"
        self.error = False
        self.error_msg = []
        self.error_camera = False
        self.error_image = None
        self.error_image_raw = None

    def _msg_error(self, message):
        """
        Report Error, set variables of modules; collect last 3 messages in central var  self.error_msg
        """
        logging.error("Image Processing (" + self.id + "): " + message)
        self.error = True
        self.error_msg.append(message)
        if len(self.error_msg) >= 3:
            self.error_msg.pop()

    def _msg_warning(self, message):
        """
        Report Error, set variables of modules
        """
        logging.warning("Image Processing (" + self.id + "): " + message)

    def compare(self, image_1st, image_2nd, detection_area=None):
        """
        calculate structural similarity index (SSIM) of two images
        """
        image_1st = self.convert_to_raw(image_1st)
        image_2nd = self.convert_to_raw(image_2nd)
        similarity = self.compare_raw(image_1st, image_2nd, detection_area)
        return similarity

    def compare_raw(self, image_1st, image_2nd, detection_area=None):
        """
        calculate structural similarity index (SSIM) of two images
        """
        try:
            if len(image_1st) == 0 or len(image_2nd) == 0:
                self._msg_warning(
                    "Compare: At least one file has a zero length - A:" + str(len(image_1st)) + "/ B:" + str(
                        len(image_2nd)))
                score = 0
        except Exception as e:
            self._msg_warning("Compare: At least one file has a zero length.")

        if detection_area is not None:
            image_1st, area = self.crop_raw(raw=image_1st, crop_area=detection_area, crop_type="relative")
            image_2nd, area = self.crop_raw(raw=image_2nd, crop_area=detection_area, crop_type="relative")

        try:
            logging.debug(self.id + "/compare 1: " + str(detection_area) + " / " + str(image_1st.shape))
            logging.debug(self.id + "/compare 2: " + str(area) + " / " + str(image_1st.shape))
            (score, diff) = ssim(image_1st, image_2nd, full=True)

        except Exception as e:
            self._msg_warning("Error comparing images (" + str(e) + ")")
            score = 0

        return round(score * 100, 1)

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
            self._msg_error("Error convert RAW image -> image (" + str(e) + ")")
            return self.image_error()

    def convert_to_raw(self, image):
        """
        convert from device to raw image -> to be modifeid with CV2
        """
        try:
            image = np.frombuffer(image, dtype=np.uint8)
            raw = cv2.imdecode(image, 1)
            return raw
        except Exception as e:
            self._msg_error("Error convert image -> RAW image (" + str(e) + ")")
            return self.image_error_raw()

    def convert_to_gray_raw(self, raw):
        """
        convert image from RGB to gray scale image (e.g. for analyzing similarity)
        """
        try:
            return cv2.cvtColor(raw, cv2.COLOR_BGR2GRAY)

        except Exception as e:
            self._msg_error("Could not convert image to gray scale " + str(e) + ")")
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
        crop image using relative dimensions (0.0 ... 1.0)
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

            logging.debug("H: " + str(y_start) + "-" + str(y_end) + " / W: " + str(x_start) + "-" + str(x_end))
            frame_cropped = raw[y_start:y_end, x_start:x_end]
            return frame_cropped, crop_area

        except Exception as e:
            self._msg_error("Could not crop image (" + str(e) + ")")

        return raw, (0, 0, 1, 1)

    def crop_area_pixel(self, raw, area):
        """
        calculate start & end pixel for relative area
        """
        height = raw.shape[0]
        width = raw.shape[1]

        (w_start, h_start, w_end, h_end) = area
        x_start = int(round(width * w_start, 0))
        y_start = int(round(height * h_start, 0))
        x_end = int(round(width * w_end, 0))
        y_end = int(round(height * h_end, 0))
        x_width = x_end - x_start
        y_height = y_end - y_start
        pixel_area = (x_start, y_start, x_end, y_end, x_width, y_height)

        return pixel_area

    def draw_text(self, image, text, position="", font="", scale="", color="", thickness=0):
        """
        Add text on image
        """
        raw = self.convert_to_raw(image)
        raw = self.draw_text_raw(raw, text, position=position, font=font, scale=scale, color=color, thickness=thickness)
        image = self.convert_from_raw(raw)
        return image

    def draw_text_raw(self, raw, text, position="", font="", scale="", color="", thickness=0):
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

        try:
            raw = cv2.putText(raw, text, position, font, scale, color, thickness, cv2.LINE_AA)
        except Exception as e:
            self._msg_warning("Could not draw text into image (" + str(e) + ")")

        return raw

    def draw_date(self, image):
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

        image = self.draw_text(image, date_information, position, font, scale, color, thickness)
        return image

    def draw_date_raw(self, raw):
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

        raw = self.draw_text_raw(raw, date_information, position, font, scale, color, thickness)
        return raw

    def draw_area_raw(self, raw, area=(0, 0, 1, 1), color=(0, 0, 255), thickness=2):
        """
        draw as colored rectangle
        """
        try:
            height = raw.shape[0]
            width = raw.shape[1]
            (x_start, y_start, x_end, y_end, x_width, y_height) = self.crop_area_pixel(raw, area)
            image = cv2.line(raw, (x_start, y_start), (x_start, y_end), color, thickness)
            image = cv2.line(image, (x_start, y_start), (x_end, y_start), color, thickness)
            image = cv2.line(image, (x_end, y_end), (x_start, y_end), color, thickness)
            image = cv2.line(image, (x_end, y_end), (x_end, y_start), color, thickness)
            return image

        except Exception as e:
            self._msg_warning("Could not draw area into the image (" + str(e) + ")")
            return raw

    def image_error(self):
        """
        return image with error message
        """
        if self.error_image is None:
            raw = self.image_error_raw()
            image = self.convert_from_raw(raw)
            self.error_image = image
            return image
        else:
            return self.error_image

    def image_error_raw(self):
        """
        return image with error message
        """
        if self.error_image_raw is None:
            filename = os.path.join(self.config.main_directory, self.config.directories["data"], self.img_camera_error)
            raw = cv2.imread(filename)
            self.error_image_raw = raw
            return raw
        else:
            return self.error_image_raw

    def normalize_raw(self, raw):
        """
        apply presets per camera to image -> implemented = crop to given values
        """
        if "crop_area" not in self.param["image"]:
            normalized, self.param["image"]["crop_area"] = self.crop_raw(raw=raw, crop_area=self.param["image"]["crop"],
                                                                         crop_type="relative")
        else:
            normalized, self.param["image"]["crop_area"] = self.crop_raw(raw=raw,
                                                                         crop_area=self.param["image"]["crop_area"],
                                                                         crop_type="pixel")
        # rotate     - not implemented yet
        # resize     - not implemented yet
        # saturation - not implemented yet
        return normalized

    def rotate_raw(self, raw, degree):
        """
        rotate image
        """
        logging.debug("Rotate image "+str(degree)+" ...")
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
            self._msg_error("Could not rotate image (" + str(e) + ")")

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
            self._msg_warning("Could not analyze image (" + str(e) + ")")
            return [0, 0]

    def size_raw(self, raw):
        """
        Return size of raw image
        """
        try:
            height = raw.shape[0]
            width = raw.shape[1]
            return [width, height]
        except Exception as e:
            self._msg_warning("Could not analyze image (" + str(e) + ")")
            return [0, 0]


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
        self.config_cache = {}
        self.config_cache_size = 5
        self.config.update["camera_" + self.id] = False

        self.sensor = sensor
        self.param = self.config.param["devices"]["cameras"][self.id]

        self.name = self.param["name"]
        self.active = self.param["active"]
        self.source = self.param["source"]
        self.type = self.param["type"]
        self.record = self.param["record"]

        self.video = None
        self.image = None
        self.running = True
        self._paused = False
        self.error = False
        self.error_msg = ""
        self.error_time = 0
        self.error_image = False
        self.error_image_count = 0
        self.error_no_reconnect = False

        self.param = self.config.param["devices"]["cameras"][self.id]
        self.name = self.param["name"]
        self.active = self.param["active"]
        self.source = self.param["source"]
        self.type = self.param["type"]
        self.record = self.param["record"]

        self.image_size = [0, 0]
        self.previous_image = None
        self.previous_stamp = "000000"

        logging.info("Starting camera (" + self.id + "/" + self.type + "/" + str(self.source) + ") ...")

        self.image = BirdhouseImageProcessing(camera=self.id, config=self.config, param=self.param)
        self.video = BirdhouseVideoProcessing(camera=self.id, config=self.config, param=self.param, directory=self.config.directory("videos"))
        self.video.output = BirdhouseCameraOutput()
        self.camera = None
        self.cameraFPS = None

        if self.type == "pi":
            self.camera_start_pi()
        elif self.type == "usb":
            self.camera_start_usb()
        else:
            self.camera_error(True, "Unknown type of camera!")

        if not self.error and self.param["video"]["allow_recording"]:
            self.camera_start_recording()

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
            config_update = self.config.update["camera_" + self.id]

            while self._paused and self.running:
                logging.info(self.id + " = paused ...")
                time.sleep(0.5)

            if config_update:
                self.update_main_config()

            # Error with camera / or update main config - try to restart from time to time
            if self.running and self.error and not self.error_no_reconnect:
                retry_time = 60
                if self.error_time + retry_time < time.time():
                    self.update_main_config()
                    logging.info("Try to restart camera ...")
                    if self.type == "pi":
                        self.camera_start_pi()
                    elif self.type == "usb":
                        self.camera_start_usb()
                    self.error_time = time.time()
                    if not self.error and self.param["video"]["allow_recording"]:
                        self.camera_start_recording()

            # [image2 @ 0x561e328229c0] Could find no file
            # with path '/home/jean/Projekte/test/birdhouse-cam/server/../data/videos/video_cam2_20220405_221441_%08d.jpg' and index in the range 0-4

            # Video Recording
            elif self.video.recording:

                if self.video.record_stop_auto():
                    self.video.record_stop()
                else:
                    image = self.get_image_raw()
                    image = self.image.normalize_raw(image)
                    self.video.image_size = self.image_size
                    self.video.create_video_image(image=image)

                    if self.image_size == [0, 0]:
                        self.image_size = self.image.size_raw(image)
                        self.video.image_size = self.image_size

                    logging.debug(".... Video Recording: " + str(self.video.info["stamp_start"]) + " -> " + str(
                        datetime.now().strftime("%H:%M:%S")))

            # Image Recording (if not video recording)
            elif self.param["active"]:
                time.sleep(1)
                if self.record:
                    if (seconds in self.param["image_save"]["seconds"]) and (
                            hours in self.param["image_save"]["hours"]):

                        image = self.get_image_raw()
                        image = self.image.normalize_raw(image)
                        image_compare = self.image.convert_to_gray_raw(image)

                        if self.param["image"]["date_time"]:
                            image = self.image.draw_date_raw(image)

                        if self.image_size == [0, 0]:
                            self.image_size = self.image.size_raw(image)
                            self.video.image_size = self.image_size

                        if self.previous_image is not None:
                            similarity = self.image.compare_raw(image_1st=image_compare, image_2nd=self.previous_image,
                                                                detection_area=self.param["similarity"][
                                                                    "detection_area"])
                            similarity = str(similarity)

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
                            if self.sensor[key].running:
                                sensor_data = self.sensor[key].get_values()
                                sensor_data["date"] = datetime.now().strftime("%d.%m.%Y")
                                image_info["sensor"][key] = self.sensor[key].get_values()
                                # self.write_sensor_info(timestamp=stamp, data=self.sensor[key].get_values())
                                self.write_cache(data_type="sensor", timestamp=stamp, data=sensor_data)

                        path_lowres = os.path.join(self.config.directory("images"),
                                                   self.config.imageName("lowres", stamp, self.id))
                        path_hires = os.path.join(self.config.directory("images"),
                                                  self.config.imageName("hires", stamp, self.id))

                        logging.debug("WRITE:" + path_lowres)

                        # self.write_image_info(timestamp=stamp, data=image_info)
                        self.write_cache(data_type="images", timestamp=stamp, data=image_info)
                        self.write_image(filename=path_hires, image=image)
                        self.write_image(filename=path_lowres, image=image,
                                         scale_percent=self.param["image"]["preview_scale"])

                        self.previous_image = image_compare
                        self.previous_stamp = stamp

        logging.info("Stopped camera (" + self.id + "/" + self.type + ").")

    def stop(self):
        """
        Stop recording
        """
        if not self.error and self.active:
            if self.type == "pi":
                self.camera.record_stop()
                self.camera.close()

            elif self.type == "usb":
                self.camera.stop()
                self.cameraFPS.stop()

            if self.video:
                self.video.stop()

        self.running = False

    def pause(self, command):
        """
        pause image recording and reconnect try
        """
        self._paused = command

    def camera_start_pi(self):
        """
        Initialize picamera incl. initial settings
        """
        self.error = False
        self.error_msg = ""
        self.error_image = False
        try:
            import picamera
        except ImportError:
            self.camera_error(True, "Module for PiCamera isn't installed. Try 'pip3 install picamera'.")
            self.error_no_reconnect = True
        try:
            if not self.error:
                self.camera = picamera.PiCamera()
                self.camera.resolution = self.param["image"]["resolution"]
                self.camera.framerate = self.param["image"]["framerate"]
                self.camera.rotation = self.param["image"]["rotation"]
                self.camera.saturation = self.param["image"]["saturation"]
                # self.camera.zoom = self.param["image"]["crop"]
                # self.camera.annotate_background = picamera.Color('black')
                self.camera.start_recording(self.video.output, format='mjpeg')
                logging.info(self.id + ": OK.")
        except Exception as e:
            self.camera_error(True, "Starting PiCamera doesn't work: " + str(e))

    def camera_start_usb(self):
        """
        Initialize USB Camera
        """
        self.error = False
        self.error_msg = ""
        self.error_image = False
        try:
            self.camera.stream.release()
        except Exception as e:
            logging.info("Ensure Stream is released ...")
        try:
            self.camera = WebcamVideoStream(src=self.source).start()
            if not self.camera.stream.isOpened():
                self.camera_error(True, "Can't connect to camera, check if source is "+str(self.source)+" ("+str(self.camera.stream.isOpened())+").")
                self.camera.stream.release()
            elif self.camera.stream is None:
                self.camera_error(True, "Can't connect to camera, check if source is " + str(self.source) + ".)")
            else:
                raw = self.get_image_raw()
                check = str(type(raw))
                if "NoneType" in check:
                    self.camera_error(True, "Images are empty, cv2 doesn't work for source " + str(self.source) + ", try picamera.")
                else:
                    if "x" in self.param["image"]["resolution"]:
                        resolution = self.param["image"]["resolution"].split("x")
                        logging.debug(str(resolution))
                        self.camera.stream.set(3, int(resolution[0]))
                        self.camera.stream.set(4, int(resolution[1]))
                        # self.camera.stream.set(cv2.CAP_PROP_FRAME_WIDTH, 1280);
                        # self.camera.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, 720);
                        # potential source for errors ... errno=16 / device or resource is busy
                    self.cameraFPS = FPS().start()
                    logging.info(self.id + ": OK (Source=" + str(self.source) + ")")
        except Exception as e:
            self.camera_error(True, "Starting USB camera doesn't work: " + str(e))

    def camera_error(self, cam_error, message):
        """
        Report Error, set variables of modules
        """
        if cam_error:
            self.error = True
        elif self.error_image_count > 20:
            self.error = True
            self.error_image_count = 0
            message = "Too much image errors, connection to camera seems to be lost."
        else:
            self.error_image = True
            self.error_image_count += 1
        self.error_msg = message
        self.error_time = time.time()
        logging.error(self.id + ": " + message + " (" + str(self.error_time) + ")")

    def camera_start_recording(self):
        """
        start recording and set current image size
        """
        self.video.start()
        self.video.image_size = self.image_size

    def camera_wait_recording(self):
        """
        Wait with recording between two pictures
        """
        if self.type == "pi":
            self.camera.wait_recording(0.1)
        if self.type == "usb":
            time.sleep(0.1)

    def get_image(self):
        """
        read image from device
        """
        if self.error:
            return self.image.image_error()

        if self.type == "pi":
            try:
                with self.video.output.condition:
                    self.video.output.condition.wait()
                    encoded = self.video.output.frame
                return encoded
            except Exception as e:
                error_msg = "Can't grab image from camera '" + self.id + "': " + str(e)
                self.camera_error(False, error_msg)
                return ""

        elif self.type == "usb":
            raw = self.get_image_raw()
            encoded = self.image.convert_from_raw(raw)
            return encoded

        else:
            error_msg = "Camera type not supported (" + str(self.type) + ")."
            self.camera_error(True, error_msg)
            return ""

    def get_image_raw(self):
        """
        get image and convert to raw
        """
        if self.error:
            return self.image.image_error_raw()

        if self.type == "pi":
            try:
                with self.video.output.condition:
                    self.video.output.condition.wait()
                    encoded = self.video.output.frame
                raw = self.image.convert_to_raw(encoded)
                return raw
            except Exception as e:
                error_msg = "Can't grab image from camera '" + self.id + "': " + str(e)
                self.camera_error(False, error_msg)
                return ""

        elif self.type == "usb":
            try:
                raw = self.camera.read()
                check = str(type(raw))
                if "NoneType" in check:
                    self.camera_error(False, "Got an empty image (source=" + str(self.source) + ")")
                    return ""
                else:
                    if self.param["image"]["rotation"] != 0:
                        raw = self.image.rotate_raw(raw, self.param["image"]["rotation"])
                    return raw.copy()
            except Exception as e:
                error_msg = "Can't grab image from camera '" + self.id + "': " + str(e)
                self.camera_error(False, error_msg)
                return ""

        else:
            error_msg = "Camera type not supported (" + str(self.type) + ")."
            self.camera_error(True, error_msg)
            return ""

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
        if "similarity" not in file_info:
            return False

        elif "to_be_deleted" in file_info and int(file_info["to_be_deleted"]) == 1:
            return False

        elif ("camera" in file_info and file_info["camera"] == self.id) or ("camera" not in file_info and self.id == "cam1"):

            if "favorit" in file_info and int(file_info["favorit"]) == 1:
                return True

            elif "00" + str(self.param["image_save"]["seconds"][0]) in timestamp:
                return True

            elif check_similarity:
                threshold = float(self.param["similarity"]["threshold"])
                similarity = float(file_info["similarity"])
                if similarity != 0 and similarity < threshold:
                    return True

            else:
                return True  # to be checked !!!

        return False

    def show_areas(self, image):
        """
        Draw a red rectangle into the image to show detection area
        """
        image = self.image.convert_to_raw(image)
        image = self.show_areas_raw(image)
        image = self.image.convert_from_raw(image)
        return image

    def show_areas_raw(self, image):
        """
        Draw a red rectangle into the image to show detection area / and a yellow to show the crop area
        """
        outer_area = self.param["image"]["crop"]
        inner_area = self.param["similarity"]["detection_area"]
        image = self.image.draw_area_raw(raw=image, area=outer_area, color=(0, 255, 255), thickness=4)

        w_start = outer_area[0] + ((outer_area[2] - outer_area[0]) * inner_area[0])
        h_start = outer_area[1] + ((outer_area[3] - outer_area[1]) * inner_area[1])
        w_end = outer_area[2] - ((outer_area[2] - outer_area[0]) * (1 - inner_area[2]))
        h_end = outer_area[3] - ((outer_area[3] - outer_area[1]) * (1 - inner_area[3]))

        inner_area = (w_start, h_start, w_end, h_end)
        image = self.image.draw_area_raw(raw=image, area=inner_area, color=(0, 0, 255), thickness=4)
        return image

    def write_cache(self, data_type, timestamp, data, force_write=False):
        """
        store entries in a cache and write packages of entries to reduce file write access
        """
        if data_type in self.config_cache and len(self.config_cache[data_type].keys()) >= self.config_cache_size:
            files = self.config.read_cache(data_type)
            for key in self.config_cache[data_type]:
                files[key] = self.config_cache[data_type][key]
            if timestamp != "":
                files[timestamp] = data.copy()
            self.config.write(data_type, files)
            logging.debug("Wrote " + str(len(self.config_cache[data_type].keys())) + " entries from cache: " + data_type)
            self.config_cache[data_type] = {}
        else:
            if data_type not in self.config_cache:
                self.config_cache[data_type] = {}
            self.config_cache[data_type][timestamp] = data.copy()
            logging.debug("Stored in cache: " + timestamp + "/" + data_type + " ... " + str(len(self.config_cache[data_type].keys())))

    def write_image(self, filename, image, scale_percent=100):
        """
        Scale image and write to file
        """
        image_path = os.path.join(self.config.main_directory, filename)
        logging.debug("Write image: " + image_path)

        try:
            if scale_percent != 100:
                width = int(image.shape[1] * scale_percent / 100)
                height = int(image.shape[0] * scale_percent / 100)
                image = cv2.resize(image, (width, height))
            return cv2.imwrite(image_path, image)

        except Exception as e:
            error_msg = "Can't save image and/or create thumbnail '" + image_path + "': " + str(e)
            self.camera_error(False, error_msg)
            return ""

    def write_image_info(self, timestamp, data):
        """
        Write image information to file
        """
        logging.debug(self.id + ": Write image info: " + self.config.file("images"))
        if os.path.isfile(self.config.file("images")):
            files = self.config.read_cache("images")
            files[timestamp] = data.copy()
            self.config.write("images", files)
        else:
            logging.error("Could not find file: " + self.config.file("images"))

    def write_video_info(self, timestamp, data):
        """
        Write image information to file
        """
        logging.debug(self.id + ": Write video info: " + self.config.file("images"))
        if os.path.isfile(self.config.file("videos")):
            files = self.config.read_cache("videos")
            files[timestamp] = data
            self.config.write("videos", files)

    def write_sensor_info(self, timestamp, data):
        """
        Write Sensor information to separate config file (for recovery purposes)
        """
        logging.debug(self.id + ": Write video info: " + self.config.file("sensor"))
        if os.path.isfile(self.config.file("sensor")):
            files = self.config.read_cache("sensor")
        else:
            files = {}
        files[timestamp] = data
        self.config.write("sensor", files)

    def update_main_config(self):
        logging.info("Update data from main configuration file for camera " + self.id)
        temp_data = self.config.read("main")
        self.param = temp_data["devices"]["cameras"][self.id]
        self.video.param = self.param
        self.image.param = self.param
        self.config.update["camera_" + self.id] = False
