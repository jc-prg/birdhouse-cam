import io
import os
import time
import logging
import numpy as np
import ffmpeg
import cv2
import psutil

from imutils.video import WebcamVideoStream
from imutils.video import FPS
from skimage.metrics import structural_similarity as ssim

import threading
from threading import Condition
from datetime import datetime, timezone, timedelta


# https://learn.circuit.rocks/introduction-to-opencv-using-the-raspberry-pi


class BirdhouseVideoProcessing(threading.Thread):
    """
    Record videos: start and stop; from all pictures of the day
    """

    def __init__(self, camera_id, camera, config, param, directory, time_zone):
        """
        Initialize new thread and set inital parameters
        """
        threading.Thread.__init__(self)
        logging.info("- Loading Video Processing for " + camera_id + "... ")
        self.id = camera_id
        self.camera = camera
        self.name = param["name"]
        self.param = param
        self.config = config
        self.directory = directory
        self.timezone = time_zone

        self.queue_create = []
        self.queue_trim = []
        self.queue_wait = 10

        self.record_video_info = None
        self.image_size = [0, 0]
        self.recording = False
        self.processing = False
        self.max_length = 0.25 * 60
        self.output = None
        self.output_codec = {"vcodec": "libx264", "crf": 18}
        self.ffmpeg_cmd = "ffmpeg -f image2 -r {FRAMERATE} -i {INPUT_FILENAMES} "
        self.ffmpeg_cmd += "-vcodec libx264 -crf 18"
        self.ffmpeg_cmd += " {OUTPUT_FILENAME}"

        self.ffmpeg_trim = "ffmpeg -y -i {INPUT_FILENAME} -r {FRAMERATE} -vcodec libx264 -crf 18 " + \
                           "-ss {START_TIME} -to {END_TIME} {OUTPUT_FILENAME}"

        # Other working options:
        # self.ffmpeg_cmd  += "-b 1000k -strict -2 -vcodec libx264 -profile:v main -level 3.1 -preset medium - \
        #                      x264-params ref=4 -movflags +faststart -crf 18"
        # self.ffmpeg_cmd  += "-c:v libx264 -pix_fmt yuv420p"
        # self.ffmpeg_cmd  += "-profile:v baseline -level 3.0 -crf 18"
        # self.ffmpeg_cmd  += "-vcodec libx264 -preset fast -profile:v baseline -lossless 1 -vf \
        #                     \"scale=720:540,setsar=1,pad=720:540:0:0\" -acodec aac -ac 2 -ar 22050 -ab 48k"

        # self.ffmpeg_trim  = "ffmpeg -y -i {INPUT_FILENAME} -c copy -ss {START_TIME} -to {END_TIME} {OUTPUT_FILENAME}"
        self.count_length = 8
        self.running = False
        self.error = False
        self.error_msg = []
        self.info = {
            "start": 0,
            "start_stamp": 0,
            "status": "ready"
        }

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
        Initialize, set initial values
        """
        logging.info("Initialize video recording ...")
        if "video" in self.param and "max_length" in self.param["video"]:
            self.max_length = self.param["video"]["max_length"]
            logging.debug("Set max video recording length for " + self.id + " to " + str(self.max_length))
        else:
            logging.debug("Use default max video recording length for " + self.id + " = " + str(self.max_length))

        count = 0
        self.running = True
        while self.running:
            time.sleep(1)
            count += 1
            if count >= self.queue_wait:
                count = 0

                # create short videos
                if len(self.queue_create) > 0:
                    self.config.async_running = True
                    [filename, stamp, date] = self.queue_create.pop()

                    logging.info("Start day video creation (" + filename + "): " + stamp + " - " + date + ")")
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

                    logging.info("Start video trimming (" + video_id + "): " + str(start) + " - " + str(end) + ")")
                    response = self.create_video_trimmed(video_id, start, end)
                    self.config.async_answers.append(["TRIM_DONE", video_id, response["result"]])
                    self.config.async_running = True

        logging.info("Stopped video recording.")

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
            logging.info("Starting video recording (" + self.id + ") ...")
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
            logging.info("Stopping video recording (" + self.id + ") ...")
            current_time = self.config.local_time()
            self.recording = False
            self.info["date_end"] = current_time.strftime('%Y%m%d_%H%M%S')
            self.info["stamp_end"] = current_time.timestamp()
            self.info["status"] = "processing"
            self.info["length"] = round(self.info["stamp_end"] - self.info["stamp_start"], 1)
            if float(self.info["length"]) > 1:
                self.info["framerate"] = round(float(self.info["image_count"]) / float(self.info["length"]), 1)
            else:
                self.info["framerate"] = 0
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
                logging.info("Maximum recording time achieved ...")
                logging.info(str(max_time) + " < " + str(self.config.local_time().timestamp()))
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
        Create video from images
        """
        self.processing = True
        logging.info("Start video creation with ffmpeg ...")

        input_filenames = os.path.join(self.config.directory("videos"), self.filename("vimages") + "%" +
                                       str(self.count_length).zfill(2) + "d.jpg")
        output_filename = os.path.join(self.config.directory("videos"), self.filename("video"))

        try:
            (
                ffmpeg
                .input(input_filenames)
                .filter('fps', fps=self.info["framerate"], round='up')
                .output(output_filename, vcodec=self.output_codec["vcodec"], crf=self.output_codec["crf"])
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=False)
            )
        except ffmpeg.Error as e:
            self._msg_error("Error during ffmpeg video creation: " + str(e))
            self.processing = False
            return

        self.info["thumbnail"] = self.filename("thumb")
        cmd_thumb = "cp " + os.path.join(self.config.directory("videos"), self.filename("vimages") + str(1).zfill(
            self.count_length) + ".jpg ") + os.path.join(self.config.directory("videos"), self.filename("thumb"))
        cmd_delete = "rm " + os.path.join(self.config.directory("videos"), self.filename("vimages") + "*.jpg")
        try:
            logging.info(cmd_thumb)
            message = os.system(cmd_thumb)
            logging.debug(message)

            logging.info(cmd_delete)
            message = os.system(cmd_delete)
            logging.debug(message)

        except Exception as e:
            self._msg_error("Error during video creation (thumbnail/cleanup): " + str(e))
            self.processing = False
            return

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

        try:
            cmd_rm = "rm " + self.config.directory("videos_temp") + "*"
            logging.debug(cmd_rm)
            message = os.system(cmd_rm)
            if message != 0:
                response = {"result": "error", "reason": "remove temp image files", "message": message}
                self._msg_error("Error during day video creation: remove old temp image files.", warning=True)
                # return response
        except Exception as e:
            self._msg_error("Error during day video creation: " + str(e), warning=True)

        try:
            cmd_copy = "cp " + self.config.directory("images") + filename + "* " + self.config.directory("videos_temp")
            logging.debug(cmd_copy)
            message = os.system(cmd_copy)
            if message != 0:
                response = {"result": "error", "reason": "copy temp image files", "message": message}
                self._msg_error("Error during day video creation: copy temp image files.")
                return response
        except Exception as e:
            self._msg_error("Error during day video creation: " + str(e))

        cmd_filename = self.config.directory("videos_temp") + cmd_tempfiles
        cmd_rename = "i=0; for fi in " + self.config.directory("videos_temp") + "image_*; do mv \"$fi\" $(printf \""
        cmd_rename += cmd_filename + "%05d.jpg\" $i); i=$((i+1)); done"
        try:
            logging.info(cmd_rename)
            message = os.system(cmd_rename)
            if message != 0:
                response = {"result": "error", "reason": "rename temp image files", "message": message}
                self._msg_error("Error during day video creation: rename temp image files.")
                return response
        except Exception as e:
            self._msg_error("Error during day video creation: " + str(e))

        amount = 0
        for root, dirs, files in os.walk(self.config.directory("videos_temp")):
            for filename in files:
                if cmd_tempfiles in filename:
                    amount += 1

        input_filenames = cmd_filename + "%05d.jpg"
        output_filename = os.path.join(self.config.directory("videos"), cmd_videofile)
        try:
            (
                ffmpeg
                .input(input_filenames)
                .filter('fps', fps=framerate, round='up')
                .output(output_filename, vcodec=self.output_codec["vcodec"], crf=self.output_codec["crf"])
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=False)
            )
        except ffmpeg.Error as e:
            self._msg_error("Error during ffmpeg video creation: " + str(e))
            response = {"result": "error", "reason": "create video with ffmpeg", "message": str(e)}
            return response

        try:
            cmd_thumb = "cp " + cmd_filename + "00001.jpg " + self.config.directory("videos") + cmd_thumbfile
            logging.info(cmd_thumb)
            message = os.system(cmd_thumb)
            if message != 0:
                response = {"result": "error", "reason": "create thumbnail", "message": message}
                self._msg_error("Error during day video creation: create thumbnails.")
                return response

            cmd_rm2 = "rm " + self.config.directory("videos_temp") + "*.jpg"
            logging.info(cmd_rm2)
            message = os.system(cmd_rm2)
            if message != 0:
                response = {"result": "error", "reason": "remove temp image files", "message": message}
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

    def create_video_day_queue(self, path):
        """
        create a video of all existing images of the day
        """
        param = path.split("/")
        response = {}
        if len(param) < 3:
            response["result"] = "Error: Parameters are missing "
            response["result"] += "(/create-day-video/which-cam/)"
            logging.warning("Create video of daily images ... Parameters are missing.")
        else:
            which_cam = param[2]
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
        config_file = self.config.read_cache("videos")
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

                self.config.write("videos", config_file)
                return {"result": "OK"}
            else:
                return {"result": "Error while creating shorter video."}

        else:
            logging.warning("No video with the ID " + str(video_id) + " available.")
            return {"result": "No video with the ID " + str(video_id) + " available."}

    def create_video_trimmed_exec(self, input_file, output_file, start_timecode, end_timecode, framerate):
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

        start_frame = round(float(start_timecode) * float(framerate))
        end_frame = round(float(end_timecode) * float(framerate))

        try:
            (
                ffmpeg
                .input(input_file)
                .filter('fps', fps=framerate, round='up')
                .trim(start_frame=start_frame, end_frame=end_frame)
                .output(output_file)
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=False)
            )
        except ffmpeg.Error as e:
            self._msg_error("Error during video trimming: " + str(e))
            return "Error"

        # try:
        #    logging.debug(cmd)
        #    message = os.system(cmd)
        #    logging.debug(message)
        # except Exception as e:
        #    self._msg_error("Error during video trimming: " + str(e))

        if os.path.isfile(output_file):
            return "OK"
        else:
            return "Error"

    def create_video_trimmed_queue(self, path):
        """
        create a short video and save in DB (not deleting the old video at the moment)
        """
        param = path.split("/")
        response = {}

        if len(param) < 6:
            response["result"] = "Error: Parameters are missing"
            response["result"] += " (/create-short-video/video-id/start-timecode/end-timecode/which-cam/)"
            logging.warning("Create short version of video ... Parameters are missing.")

        else:
            logging.info("Create short version of video '" + str(param[2]) + "' [" + str(param[3]) + ":" +
                         str(param[4]) + "] ...")
            which_cam = param[5]
            config_data = self.config.read_cache(config="videos")

            if param[2] not in config_data:
                response["result"] = "Error: video ID '" + str(param[2]) + "' doesn't exist."
                logging.warning("VideoID '" + str(param[2]) + "' doesn't exist.")
            else:
                self.queue_trim.append([param[2], param[3], param[4]])
                response["command"] = ["Create short version of video"]
                response["video"] = {"video_id": param[2], "start": param[3], "end": param[4]}

        return response


class BirdhouseImageProcessing(object):
    """
    modify encoded and raw images
    """

    def __init__(self, camera_id, camera, config, param, time_zone):
        logging.info("- Loading Image Processing for " + camera_id + "... ")
        self.frame = None
        self.id = camera_id
        self.config = config
        self.param = param

        self.text_default_position = (30, 40)
        self.text_default_scale = 0.8
        self.text_default_font = cv2.FONT_HERSHEY_SIMPLEX
        self.text_default_color = (255, 255, 255)
        self.text_default_thickness = 2

        self.img_camera_error = "camera_na.jpg"
        self.img_camera_error_v2 = "camera_na_v3.jpg"
        self.img_camera_error_v3 = "camera_na_v4.jpg"

        self.error = False
        self.error_msg = []
        self.error_time = 0
        self.error_count = 0
        self.error_camera = False
        self.error_image = {}

        self.timezone = time_zone

    def raise_error(self, message, warning=False):
        """
        Report Error, set variables of modules; collect last 3 messages in central var  self.error_msg
        """
        if not warning:
            logging.error("Image Processing (" + self.id + "): " + message)
            self.error = True
            self.error_msg.append(message)
            self.error_count += 1
            if self.error_time == 0:
                self.error_time = time.time()
            if len(self.error_msg) >= 10:
                self.error_msg.pop()
        else:
            logging.warning("Image Processing (" + self.id + "): " + message)

    def reset_error(self):
        """
        reset error vars
        """
        self.error = False
        self.error_msg = []
        self.error_count = 0
        self.error_time = 0

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
                self.raise_error("Compare: At least one file has a zero length - A:" +
                                 str(len(image_1st)) + "/ B:" + str(len(image_2nd)), warning=True)
                score = 0
        except Exception as e:
            self.raise_error("Compare: At least one file has a zero length.", warning=True)
            score = 0

        if detection_area is not None:
            image_1st, area = self.crop_raw(raw=image_1st, crop_area=detection_area, crop_type="relative")
            image_2nd, area = self.crop_raw(raw=image_2nd, crop_area=detection_area, crop_type="relative")
        else:
            area = [0, 0, 1, 1]

        try:
            logging.debug(self.id + "/compare 1: " + str(detection_area) + " / " + str(image_1st.shape))
            logging.debug(self.id + "/compare 2: " + str(area) + " / " + str(image_1st.shape))
            (score, diff) = ssim(image_1st, image_2nd, full=True)

        except Exception as e:
            self.raise_error("Error comparing images (" + str(e) + ")", warning=True)
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
            logging.error("Shape " + str(raw.shape))
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

            logging.debug("H: " + str(y_start) + "-" + str(y_end) + " / W: " + str(x_start) + "-" + str(x_end))
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
        logging.debug("draw_text_raw: "+param)
        try:
            raw = cv2.putText(raw, text, tuple(position), font, scale, color, thickness, cv2.LINE_AA)
        except Exception as e:
            self.raise_error("Could not draw text into image (" + str(e) + ")", warning=True)
            logging.warning(" ... " + param)

        return raw

    def draw_date(self, image):
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
        if self.param["image"]["date_time_size"]:
            scale = self.param["image"]["date_time_size"]
        else:
            scale = ""

        image = self.draw_text(image, date_information, position, font, scale, color, thickness)
        return image

    def draw_date_raw(self, raw, overwrite_color=None, overwrite_position=None, timezone_info=+1):
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
            self.raise_error("Could not draw area into the image (" + str(e) + ")", warning=True)
            return raw

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
            raw = self.draw_date_raw(raw=raw, overwrite_color=(0, 0, 255),
                                     overwrite_position=(20, line_position), timezone_info=self.timezone)

        else:
            raw = self.image_error_raw(image=self.img_camera_error_v3)
            raw = self.draw_text_raw(raw=raw, text=self.id + ": " + self.param["name"],
                                     position=(20, 40), color=(255, 255, 255), thickness=2)
            raw = self.draw_date_raw(raw=raw, overwrite_color=(255, 255, 255), overwrite_position=(20, 80))

        return raw

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

    def normalize_raw(self, raw):
        """
        apply presets per camera to image -> implemented = crop to given values
        """
        if self.error_camera:
            return

        normalized, area = self.crop_raw(raw=raw, crop_area=self.param["image"]["crop"],
                                                                     crop_type="relative")
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

        # rotate     - not implemented yet
        # resize     - not implemented yet
        # saturation - not implemented yet

        # see https://www.programmerall.com/article/5684321533/

        return normalized

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
        logging.debug("Rotate image " + str(degree) + " ...")
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
            self.raise_error("Could not analyze image (" + str(e) + ")", warning=True)
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
            self.raise_error("Could not analyze image (" + str(e) + ")", warning=True)
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


class BirdhouseCameraOther(object):

    def __init__(self, source, name):
        self.error = False
        self.error_msg = ""

        if "/dev/" not in str(source):
            source = "/dev/video" + str(source)

        logging.info("Initialize Camera Thread for " + name + ", source=" + source + " ...")
        self.stream = cv2.VideoCapture(source, cv2.CAP_V4L)
        try:
            ref, raw = self.stream.read()
        except cv2.error as e:
            self.error = True
            self.error_msg = str(e)
            logging.warning("- Error connecting to camera '" + source + "' and reading first image")

    def read(self):
        try:
            ref, raw = self.stream.read()
            self.error = False
            return raw
        except cv2.error as e:
            logging.warning("- Error connecting to camera '" + source + "' and reading first image")
            self.error = True
            self.error_msg = str(e)
            return


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
        self.max_resolution = None

        self.video = None
        self.image = None
        self.running = True
        self._paused = False
        self.error = False
        self.error_msg = []
        self.error_time = 0
        self.error_reload_time = 60
        self.error_no_reconnect = False

        self.reload_camera = True
        self.reload_time = 0
        self.config_update = None

        self.param = self.config.param["devices"]["cameras"][self.id]
        self.name = self.param["name"]
        self.active = self.param["active"]
        self.source = self.param["source"]
        self.type = self.param["type"]
        self.record = self.param["record"]

        self.timezone = 0
        if "timezone" in self.config.param["server"]:
            self.timezone = float(self.config.param["server"]["timezone"].replace("UTC", ""))
            logging.info("Set Timezone: " + self.config.param["server"]["timezone"] + " (" + str(self.timezone) + ")")

        self.image_size = [0, 0]
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

        logging.info("Initializing camera (" + self.id + "/" + self.type + "/" + str(self.source) + ") ...")

        self.image = BirdhouseImageProcessing(camera_id=self.id, camera=self, config=self.config, param=self.param,
                                              time_zone=self.timezone)
        self.image.resolution = self.param["image"]["resolution"]
        self.video = BirdhouseVideoProcessing(camera_id=self.id, camera=self, config=self.config, param=self.param,
                                              directory=self.config.directory("videos"), time_zone=self.timezone)
        self.video.output = BirdhouseCameraOutput()
        self.camera = None
        self.cameraFPS = None

        logging.debug("HOURS:   " + str(self.param["image_save"]["hours"]))
        logging.debug("SECONDS: " + str(self.param["image_save"]["seconds"]))

    def run(self):
        """
        Start recording for livestream and save images every x seconds
        """
        similarity = 0
        count_paused = 0
        reload_time = time.time()
        reload_time_error = 60

        while self.running:
            current_time = self.config.local_time()
            seconds = current_time.strftime('%S')
            hours = current_time.strftime('%H')
            stamp = current_time.strftime('%H%M%S')
            self.config_update = self.config.update["camera_" + self.id]

            # if error reload from time to time
            if self.active and self.error and (reload_time + reload_time_error) < time.time():
                logging.info("....... RELOAD Error: " + self.id + " - " +
                             str(reload_time + reload_time_error) + " > " + str(time.time()))
                reload_time = time.time()
                self.config_update = True
                self.reload_camera = True

            # check if configuration shall be updated
            if self.config_update:
                logging.info("....... RELOAD Update: " + self.id + " - " +
                             str(reload_time + reload_time_error) + " > " + str(time.time()))
                self.update_main_config()
                self.reload_camera = True

            # start or reload camera connection
            if self.reload_camera and self.active:
                logging.info("- (Re)starting Camera (" + self.id + ") ...")
                if self.type == "pi":
                    self.camera_start_pi()
                elif self.type == "default":
                    self.camera_start_default()
                elif self.type == "usb":
                    self.camera_start_usb()
                else:
                    self.raise_error(True, "Unknown type of camera!")
                if not self.error and self.param["video"]["allow_recording"]:
                    self.camera_start_recording()
                self.reload_camera = False

            # check if camera is paused, wait with all processes ...
            if not self._paused:
                count_paused = 0
            while self._paused and self.running:
                if count_paused == 0:
                    logging.info("Recording images with " + self.id + " paused ...")
                    count_paused += 1
                time.sleep(0.5)

            # Video Recording
            if not self.error and self.video.recording:

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
                        current_time.strftime("%H:%M:%S")))

            # Image Recording (if not video recording)
            elif not self.error and self.param["active"] and self.param["active"] != "False":
                time.sleep(0.3)
                if self.record:
                    logging.debug("Check if record ... " + str(hours) + "/*/" + str(seconds) + " ...")
                    if (seconds in self.param["image_save"]["seconds"]) and \
                            (hours in self.param["image_save"]["hours"]):

                        logging.debug(" ...... record now!")
                        # image = self.get_image_raw_buffered(max_age_seconds=1)    # does not work at the moment
                        image = self.get_image_raw()

                        if not self.image.error and len(image) > 0:
                            image = self.image.normalize_raw(image)
                            image_compare = self.image.convert_to_gray_raw(image)

                            if self.param["image"]["date_time"]:
                                image = self.image.draw_date_raw(image)

                            if self.image_size == [0, 0]:
                                self.image_size = self.image.size_raw(image)
                                self.video.image_size = self.image_size

                            if self.previous_image is not None:
                                similarity = self.image.compare_raw(image_1st=image_compare,
                                                                    image_2nd=self.previous_image,
                                                                    detection_area=self.param["similarity"][
                                                                        "detection_area"])
                                similarity = str(similarity)

                            image_info = {
                                "camera": self.id,
                                "hires": self.config.filename_image("hires", stamp, self.id),
                                "lowres": self.config.filename_image("lowres", stamp, self.id),
                                "compare": (stamp, self.previous_stamp),
                                "datestamp": current_time.strftime("%Y%m%d"),
                                "date": current_time.strftime("%d.%m.%Y"),
                                "time": current_time.strftime("%H:%M:%S"),
                                "similarity": similarity,
                                "sensor": {},
                                "size": self.image_size
                            }
                            self.previous_image = image_compare
                        else:
                            image_info = {
                                "camera": self.id,
                                "hires": "",
                                "lowres": "",
                                "compare": (stamp, self.previous_stamp),
                                "datestamp": current_time.strftime("%Y%m%d"),
                                "date": current_time.strftime("%d.%m.%Y"),
                                "time": current_time.strftime("%H:%M:%S"),
                                "similarity": 0,
                                "sensor": {},
                                "size": self.image_size,
                                "error": self.error_msg[len(self.error_msg) - 1]
                            }

                        sensor_data = {"activity": round(100 - float(similarity), 1)}
                        for key in self.sensor:
                            if self.sensor[key].running:
                                sensor_data[key] = self.sensor[key].get_values()
                                sensor_data[key]["date"] = current_time.strftime("%d.%m.%Y")
                                image_info["sensor"][key] = self.sensor[key].get_values()

                        self.config.queue.entry_add(config="sensor", date="", key=stamp, entry=sensor_data)
                        self.config.queue.entry_add(config="images", date="", key=stamp, entry=image_info)

                        if not self.error:
                            path_lowres = os.path.join(self.config.directory("images"),
                                                       self.config.filename_image("lowres", stamp, self.id))
                            path_hires = os.path.join(self.config.directory("images"),
                                                      self.config.filename_image("hires", stamp, self.id))
                            logging.debug("WRITE:" + path_lowres)
                            self.write_image(filename=path_hires, image=image)
                            self.write_image(filename=path_lowres, image=image,
                                             scale_percent=self.param["image"]["preview_scale"])

                        time.sleep(0.7)
                        self.previous_stamp = stamp

        logging.info("Stopped camera (" + self.id + "/" + self.type + ").")

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

    def pause(self, command):
        """
        pause image recording and reconnect try
        """
        self._paused = command

    def raise_error(self, cam_error, message):
        """
        Report Error, set variables of modules
        """
        if cam_error:
            self.error = True
            self.image.error_camera = True
        else:
            self.image.raise_error(message)
        self.error_msg.append(message)
        self.error_time = time.time()
        logging.error(self.id + ": " + message + " (" + str(self.error_time) + ")")

    def reset_error(self):
        """
        remove all errors
        """
        self.error = False
        self.error_msg = []
        self.error_time = 0
        self.image.error_camera = False
        self.image.reset_error()
        self.image_last_raw = None
        self.image_last_edited = None

    def camera_start_pi(self):
        """
        Initialize picamera incl. initial settings
        """
        self.reset_error()
        self.reload_time = time.time()
        try:
            import picamera
            # https://raspberrypi.stackexchange.com/questions/114035/picamera-and-ubuntu-20-04-arm64
        except ImportError:
            self.raise_error(True, "Module for PiCamera isn't installed. Try 'pip3 install picamera'.")
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
            self.raise_error(True, "Starting PiCamera doesn't work: " + str(e))

    def camera_start_default(self):
        """
        Try out new
        """
        self.reset_error()
        self.reload_time = time.time()
        try:
            self.camera.stream.release()
        except Exception as e:
            logging.info("Ensure Stream is released ...")

        try:
            self.camera = BirdhouseCameraOther(self.source, self.id)

            if self.camera.error:
                self.raise_error(True, "Can't connect to camera, check if '" + str(
                    self.source) + "' is a valid source (" + self.camera.error_msg + ").")
                self.camera.stream.release()
            elif not self.camera.stream.isOpened():
                self.raise_error(True, "Can't connect to camera, check if '" + str(
                    self.source) + "' is a valid source (could not open).")
                self.camera.stream.release()
            elif self.camera.stream is None:
                self.raise_error(True, "Can't connect to camera, check if '" + str(
                    self.source) + "' is a valid source (empty image).")
                self.camera.stream.release()
            else:
                raw = self.get_image_raw()
                check = str(type(raw))
                if "NoneType" in check:
                    self.raise_error(True,
                                     "Source " + str(self.source) + " returned empty image, try type 'pi' or 'usb'.")
                else:
                    self.camera_resolution_usb(self.param["image"]["resolution"])
                    self.cameraFPS = FPS().start()
                    logging.info(self.id + ": OK (Source=" + str(self.source) + ")")

        except Exception as e:
            self.raise_error(True, "Starting camera '" + self.source + "' doesn't work: " + str(e))

        return

    def camera_start_usb(self):
        """
        Initialize USB Camera
        """
        self.reset_error()
        self.reload_time = time.time()
        try:
            self.camera.stream.release()
        except Exception as e:
            logging.info("Ensure Stream is released ...")
        try:
            self.camera = WebcamVideoStream(src=self.source).start()
            if not self.camera.stream.isOpened():
                self.raise_error(True, "Can't connect to camera, check if source is " + str(self.source) + " (" + str(
                    self.camera.stream.isOpened()) + ").")
                self.camera.stream.release()
            elif self.camera.stream is None:
                self.raise_error(True, "Can't connect to camera, check if source is " + str(self.source) + ".)")
            else:
                raw = self.get_image_raw()
                check = str(type(raw))
                if "NoneType" in check:
                    self.raise_error(True, "Images are empty, cv2 doesn't work for source " + str(
                        self.source) + ", try picamera.")
                else:
                    self.camera_resolution_usb(self.param["image"]["resolution"])
                    self.cameraFPS = FPS().start()
                    logging.info(self.id + ": OK (Source=" + str(self.source) + ")")
        except Exception as e:
            self.raise_error(True, "Starting USB camera doesn't work: " + str(e))

    def camera_reconnect(self):
        """
        Reconnect after API call
        """
        response = {"command": ["reconnect camera"], "camera": self.id}
        self.reload_camera = True
        self.config_update = True
        return response

    def camera_resolution_usb(self, resolution):
        """
        set resolution for USB
        """
        if self.type != "usb" and self.type != "default":
            return
        if self.camera is None:
            return

        try:
            current = [self.camera.stream.get(cv2.CAP_PROP_FRAME_WIDTH),
                       self.camera.stream.get(cv2.CAP_PROP_FRAME_HEIGHT)]
            logging.info("USB Current resolution: " + str(current))
        except Exception as e:
            logging.warning("Could not get current resolution: " + self.id)

        high_value = 10000
        self.camera.stream.set(cv2.CAP_PROP_FRAME_WIDTH, high_value)
        self.camera.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, high_value)
        self.max_resolution = [self.camera.stream.get(cv2.CAP_PROP_FRAME_WIDTH),
                               self.camera.stream.get(cv2.CAP_PROP_FRAME_HEIGHT)]
        logging.info(self.id + " Maximum resolution: " + str(self.max_resolution))

        if "x" in resolution:
            dimensions = resolution.split("x")
            logging.info(self.id + " Set resolution: " + str(dimensions))
            # self.camera.stream.set(3, int(resolution[0]))
            # self.camera.stream.set(4, int(resolution[1]))
            self.camera.stream.set(cv2.CAP_PROP_FRAME_WIDTH, float(dimensions[0]))
            self.camera.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, float(dimensions[1]))
            current = [self.camera.stream.get(cv2.CAP_PROP_FRAME_WIDTH),
                       self.camera.stream.get(cv2.CAP_PROP_FRAME_HEIGHT)]

            if current == [0, 0]:
                current = [int(dimensions[0]), int(dimensions[1])]

            self.param["image"]["resolution_current"] = current
            self.param["image"]["crop_area"] = self.image.crop_area_pixel(resolution=current,
                                                                          area=self.param["image"]["crop"],
                                                                          dimension=False)
            logging.info(self.id + " New resolution: " + str(current))
            logging.info(self.id + " New crop area:  " + str(self.param["image"]["crop"]) + " -> " +
                         str(self.param["image"]["crop_area"]))
        else:
            logging.info("Resolution definition not supported: " + str(resolution))

        # potential source for errors ... errno=16 / device or resource is busy === >>
        # [ WARN:0@3.021] global /tmp/pip-wheel-8dvnqe62/opencv-python_7949e8065e824f1480edaa2d75fce534
        # /opencv/modules/videoio/src/cap_v4l.cpp (801) requestBuffers VIDEOIO(V4L2:/dev/video1):
        # failed VIDIOC_REQBUFS: errno=16 (Device or resource busy)
        # ---
        # cale OpenCV(4.5.5) :-1: error: (-5:Bad argument) in function 'cvtColor'
        # > Overload resolution failed:
        # >  - src is not a numpy array, neither a scalar
        # >  - Expected Ptr<cv::UMat> for argument 'src'
        # )

    def camera_start_recording(self):
        """
        start recording and set current image size
        """
        if not self.video.running:
            self.video.start()
        self.video.image_size = self.image_size

    def camera_wait_recording(self):
        """
        Wait with recording between two pictures
        """
        if self.type == "pi":
            self.camera.wait_recording(0.1)
        if self.type == "usb" or self.type == "default":
            return

    def get_image(self):
        """
        read image from device
        """
        if self.error:
            return

        if self.type == "pi":
            try:
                with self.video.output.condition:
                    self.video.output.condition.wait()
                    encoded = self.video.output.frame
                self.image.reset_error()
                return encoded
            except Exception as e:
                error_msg = "Can't grab image from piCamera '" + self.id + "': " + str(e)
                self.raise_error(False, error_msg)
                return ""

        elif self.type == "usb" or self.type == "default":
            raw = self.get_image_raw()
            encoded = self.image.convert_from_raw(raw)
            return encoded

        else:
            error_msg = "Camera type not supported (" + str(self.type) + ")."
            self.raise_error(True, error_msg)
            return ""

    def get_image_raw(self):
        """
        get image and convert to raw
        """
        if self.error:
            return ""

        if self.type == "pi":
            try:
                with self.video.output.condition:
                    self.video.output.condition.wait()
                    encoded = self.video.output.frame
                self.image.reset_error()
                raw = self.image.convert_to_raw(encoded)
                self.image_last_raw = raw
                self.image_last_raw_time = datetime.now().timestamp()
                return raw
            except Exception as e:
                error_msg = "Can't grab image from piCamera '" + self.id + "': " + str(e)
                self.raise_error(False, error_msg)
                return ""

        elif self.type == "usb" or self.type == "default":
            self.image.reset_error()
            try:
                raw = self.camera.read()
                check = str(type(raw))
                if self.camera.error:
                    self.raise_error(False, "Error reading image (source=" + str(self.source) + ", " +
                                     self.camera.error_msg + ")")
                    return ""
                elif "NoneType" in check or len(raw) == 0:
                    self.raise_error(False, "Got an empty image (source=" + str(self.source) + ")")
                    return ""
                else:
                    if self.param["image"]["rotation"] != 0:
                        raw = self.image.rotate_raw(raw, self.param["image"]["rotation"])
                if len(raw) > 0 and not self.image.error:
                    self.image_last_raw = raw.copy()
                    self.image_last_raw_time = datetime.now().timestamp()
                    return raw.copy()
                else:
                    return ""
            except Exception as e:
                error_msg = "Can't grab image from camera '" + self.id + "': " + str(e)
                self.raise_error(False, error_msg)
                return ""

        else:
            error_msg = "Camera type not supported (" + str(self.type) + ")."
            self.raise_error(True, error_msg)
            return ""

    def get_image_raw_buffered(self, max_age_seconds=1):
        """
        get image from buffer if not to old
        """
        if self.image_last_raw_time == 0:
            self.image_last_raw_time = datetime.now().timestamp()

        if self.image_last_raw is not None and len(self.image_last_raw) > 0:
            if self.image_last_raw_time + max_age_seconds < datetime.now().timestamp():
                return self.image_last_raw

        return self.get_image_raw()

    def get_image_stream_count(self):
        """
        identify amount of currently running streams
        """
        current_time = datetime.now().timestamp()
        count_streams = 0
        del_key = ""
        for key in self.image_streams:
            if self.image_streams[key] + 1 > current_time:
                count_streams += 1
            else:
                del_key = key
        if del_key != "":
            del self.image_streams[del_key]
        return count_streams

    def get_image_stream_fps(self, stream_id):
        """
        calculate fps for a specific stream
        """
        self.image_streams[stream_id] = datetime.now().timestamp()
        if stream_id not in self.image_time_current:
            self.image_time_current[stream_id] = 0
        if stream_id not in self.image_time_rotate:
            self.image_time_rotate[stream_id] = 0
        if stream_id not in self.image_fps:
            self.image_fps[stream_id] = 0

        time_rotate = ["-", "/", "|", "\\"]
        self.image_time_last[stream_id] = self.image_time_current[stream_id]
        self.image_time_current[stream_id] = datetime.now().timestamp()
        if self.image_time_last[stream_id] > 0:
            self.image_fps[stream_id] = 1 / (self.image_time_current[stream_id] - self.image_time_last[stream_id])
            self.image_time_rotate[stream_id] += 1
            if self.image_time_rotate[stream_id] > len(time_rotate) - 1:
                self.image_time_rotate[stream_id] = 0
        return time_rotate[self.image_time_rotate[stream_id]]

    def get_image_stream_raw(self, normalize=False, stream_id=""):
        """
        get image, if error show error message
        -> IMPROVE: create possibility to stop stream via API Command (Cam-ID + external Stream-ID)
        -> IMPROVE: reuse images, if multiple streams ... (define primary stream, others use copies ...)
        ->          check if in device mode there are two streams of each camera?!
        """

        image = self.get_image_raw()
        fps_rotate = self.get_image_stream_fps(stream_id=stream_id)

        if not self.error and self.image.error and self.image.error_count < 10 and self.image_last_edited is not None:
            image = self.image_last_edited
            image = cv2.circle(image, (25, 50), 4, (0, 0, 255), 6)
            return image

        elif self.error or self.image.error:
            if normalize:
                image_error = self.image.image_error_info_raw(self.error_msg, self.reload_time, "reduced")
                image_error = self.image.normalize_error_raw(image_error)  # ---> causes error after a while?
            else:
                image_error = self.image.image_error_info_raw(self.error_msg, self.reload_time, "complete")

            if "show_framerate" in self.param["image"] and self.param["image"]["show_framerate"]:
                image_error = self.image.draw_text_raw(raw=image_error,
                                                       text=str(
                                                           round(self.image_fps[stream_id], 1)) + "fps   " + fps_rotate,
                                                       font=cv2.QT_FONT_NORMAL, color=(0, 0, 0),
                                                       position=(20, -20), scale=0.4, thickness=1)
            return image_error

        else:
            if normalize:
                image = self.image.normalize_raw(image)

            if not self.video.recording and not self.video.processing:
                if "show_framerate" in self.param["image"] and self.param["image"]["show_framerate"]:
                    image = self.image.draw_text_raw(raw=image,
                                                     text=str(round(self.image_fps[stream_id], 1)) + "fps   "
                                                          + fps_rotate, font=cv2.QT_FONT_NORMAL,
                                                     position=(10, -20), scale=0.4, thickness=1)
            self.image_last_edited = image
            return image

    def get_image_stream_kill(self, stream_id):
        """
        check if stream has to be killed
        """
        logging.debug("get_image_stream_kill: " + str(stream_id))
        if stream_id in self.image_streams_to_kill:
            logging.info("get_image_stream_kill - True: " + str(stream_id))
            del self.image_streams_to_kill[stream_id]
            return True
        else:
            return False

    def set_image_stream_kill(self, stream_id):
        """
        mark streams to be killed
        """
        logging.info("set_image_stream_kill: " + stream_id)
        self.image_streams_to_kill[stream_id] = datetime.now().timestamp()

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

        elif ("camera" in file_info and file_info["camera"] == self.id) or (
                "camera" not in file_info and self.id == "cam1"):

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
        logging.debug("-----------------" + self.id + "------- show area")
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
            self.raise_error(False, error_msg)
            return ""

    def update_main_config(self):
        logging.info("Update data from main configuration file for camera " + self.id)
        temp_data = self.config.read("main")
        self.param = temp_data["devices"]["cameras"][self.id]
        self.name = self.param["name"]
        self.active = self.param["active"]
        self.source = self.param["source"]
        self.type = self.param["type"]
        self.record = self.param["record"]
        self.video.param = self.param
        self.image.param = self.param
        self.config.update["camera_" + self.id] = False
        self.reload_camera = True
        self.camera_resolution_usb(self.param["image"]["resolution"])
