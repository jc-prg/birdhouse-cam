import io
import os
import time
import logging
import numpy as np
import ffmpeg
import cv2
import psutil
import threading

from imutils.video import FPS, WebcamVideoStream
from skimage.metrics import structural_similarity as ssim
from threading import Condition
from datetime import datetime, timezone, timedelta
from modules.presets import *


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
        self.id = camera_id
        self.camera = camera
        self.name = param["name"]
        self.param = param
        self.config = config
        self.directory = directory
        self.timezone = time_zone

        self.logging = logging.getLogger(self.id + "-video")
        self.logging.setLevel(birdhouse_loglevel_module["cam-video"])
        self.logging.addHandler(birdhouse_loghandler)
        self.logging.info("Starting VIDEO processing for '"+self.id+"' ...")

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

    def raise_error(self, message, warning=False):
        """
        Report Error, set variables of modules, collect last 3 messages in var self.error_msg
        """
        if warning:
            self.raise_warning(message)
            return
        self.logging.error("Video Processing (" + self.id + "): " + message)
        self.error = True
        time_info = self.config.local_time().strftime('%d.%m.%Y %H:%M:%S')
        self.error_msg.append(time_info + " - " + message)
        if len(self.error_msg) >= 5:
            self.error_msg.pop()

    def raise_warning(self, message):
        """
        Report Error, set variables of modules
        """
        self.logging.warning("Video Processing (" + self.id + "): " + message)

    def reset_error(self):
        """
        reset all error values
        """
        self.error = False
        self.error_msg = []

    def run(self):
        """
        Initialize, set initial values
        """
        self.logging.info("Initialize video recording ...")
        if "video" in self.param and "max_length" in self.param["video"]:
            self.max_length = self.param["video"]["max_length"]
            self.logging.debug("Set max video recording length for " + self.id + " to " + str(self.max_length))
        else:
            self.logging.debug("Use default max video recording length for " + self.id + " = " + str(self.max_length))

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

        self.logging.info("Stopped video recording.")

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
            self.recording = False
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
        Create video from images
        """
        self.processing = True
        self.logging.info("Start video creation with ffmpeg ...")

        input_filenames = os.path.join(self.config.db_handler.directory("videos"), self.filename("vimages") + "%" +
                                       str(self.count_length).zfill(2) + "d.jpg")
        output_filename = os.path.join(self.config.db_handler.directory("videos"), self.filename("video"))

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
            self.raise_error("Error during ffmpeg video creation: " + str(e))
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

        except Exception as e:
            self.raise_error("Error during video creation (thumbnail/cleanup): " + str(e))
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

        try:
            cmd_rm = "rm " + self.config.db_handler.directory("videos_temp") + "*"
            self.logging.debug(cmd_rm)
            message = os.system(cmd_rm)
            if message != 0:
                response = {"result": "error", "reason": "remove temp image files", "message": message}
                self.raise_error("Error during day video creation: remove old temp image files.", warning=True)
                # return response
        except Exception as e:
            self.raise_error("Error during day video creation: " + str(e), warning=True)

        try:
            cmd_copy = "cp " + self.config.db_handler.directory("images") + filename + "* " + \
                       self.config.db_handler.directory("videos_temp")
            self.logging.debug(cmd_copy)
            message = os.system(cmd_copy)
            if message != 0:
                response = {"result": "error", "reason": "copy temp image files", "message": message}
                self.raise_error("Error during day video creation: copy temp image files.")
                return response
        except Exception as e:
            self.raise_error("Error during day video creation: " + str(e))

        cmd_filename = self.config.db_handler.directory("videos_temp") + cmd_tempfiles
        cmd_rename = "i=0; for fi in " + self.config.db_handler.directory("videos_temp") + "image_*; do mv \"$fi\" $(printf \""
        cmd_rename += cmd_filename + "%05d.jpg\" $i); i=$((i+1)); done"
        try:
            self.logging.info(cmd_rename)
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

        input_filenames = cmd_filename + "%05d.jpg"
        output_filename = os.path.join(self.config.db_handler.directory("videos"), cmd_videofile)
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
            self.raise_error("Error during ffmpeg video creation: " + str(e))
            response = {"result": "error", "reason": "create video with ffmpeg", "message": str(e)}
            return response

        try:
            cmd_thumb = "cp " + cmd_filename + "00001.jpg " + self.config.db_handler.directory("videos") + cmd_thumbfile
            self.logging.info(cmd_thumb)
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
            self.logging.warning("Create video of daily images ... Parameters are missing.")
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
            self.raise_error("Error during video trimming: " + str(e))
            return "Error"

        # try:
        #    self.logging.debug(cmd)
        #    message = os.system(cmd)
        #    self.logging.debug(message)
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
            self.logging.warning("Create short version of video ... Parameters are missing.")

        else:
            self.logging.info("Create short version of video '" + str(param[2]) + "' [" + str(param[3]) + ":" +
                         str(param[4]) + "] ...")
            which_cam = param[5]
            config_data = self.config.db_handler.read_cache(config="videos")

            if param[2] not in config_data:
                response["result"] = "Error: video ID '" + str(param[2]) + "' doesn't exist."
                self.logging.warning("VideoID '" + str(param[2]) + "' doesn't exist.")
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
        self.frame = None
        self.id = camera_id
        self.config = config
        self.param = param

        self.logging = logging.getLogger(self.id + "-img")
        self.logging.setLevel(birdhouse_loglevel_module["cam-img"])
        self.logging.addHandler(birdhouse_loghandler)
        self.logging.info("Starting IMAGE processing for '"+self.id+"' ...")

        self.text_default_position = (30, 40)
        self.text_default_scale = 0.8
        self.text_default_font = cv2.FONT_HERSHEY_SIMPLEX
        self.text_default_color = (255, 255, 255)
        self.text_default_thickness = 2

        self.img_camera_error = "camera_na.jpg"
        self.img_camera_error_v2 = "camera_na_v3.jpg"
        self.img_camera_error_v3 = "camera_na_v4.jpg"
        self.img_camara_error_server = "camera_na_server.jpg"

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
            self.logging.error("Image Processing (" + self.id + "): " + message)
            self.error = True
            time_info = self.config.local_time().strftime('%d.%m.%Y %H:%M:%S')
            self.error_msg.append(time_info + " - " + message)
            self.error_count += 1
            if self.error_time == 0:
                self.error_time = time.time()
            if len(self.error_msg) >= 10:
                self.error_msg.pop()
        else:
            self.logging.warning("Image Processing (" + self.id + "): " + message)

    def reset_error(self):
        """
        reset error vars
        """
        self.error = False
        self.error_msg = []
        self.error_count = 0
        self.error_time = 0
        self.error_camera = False

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
            self.logging.debug(self.id + "/compare 1: " + str(detection_area) + " / " + str(image_1st.shape))
            self.logging.debug(self.id + "/compare 2: " + str(area) + " / " + str(image_1st.shape))
            (score, diff) = ssim(image_1st, image_2nd, full=True)

        except Exception as e:
            self.raise_error("Error comparing images (" + str(e) + ")", warning=True)
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

    def draw_date_raw(self, raw, overwrite_color=None, overwrite_position=None, offset=[0, 0], timezone_info=+1):
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
            self.raise_error("Could not draw area into the image (" + str(e) + ")", warning=True)
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

        elif info_type == "empty":
            raw = self.image_error_raw(image=self.img_camera_error_v3)

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
            normalized = self.convert_from_gray_raw(normalized)

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
            self.raise_error("Could not analyze image (" + str(e) + ")", warning=True)
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
            self.raise_error("Could not analyze image (" + str(e) + ")", warning=True)
            return [0, 0]

    def resize_raw(self, raw, scale_percent=100, scale_size=None):
        """
        resize raw image
        """
        self.logging.debug("Resize image ("+str(scale_percent)+"% / "+str(scale_size)+")")
        if scale_size is not None:
            [width, height] = scale_size
            raw = cv2.resize(raw, (width, height))
        elif scale_percent != 100:
            [width, height] = self.size_raw(raw, scale_percent=scale_percent)
            raw = cv2.resize(raw, (width, height))
        return raw


class BirdhouseCameraOutput(object):
    """
    Create camera output
    """

    def __init__(self, camera):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

        self.logging = logging.getLogger(camera + "-out")
        self.logging.setLevel(birdhouse_loglevel_module["cam-out"])
        self.logging.addHandler(birdhouse_loghandler)
        self.logging.info("Starting CAMERA output for '"+camera+"' ...")

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

        self.logging = logging.getLogger(name + "-other")
        self.logging.setLevel(birdhouse_loglevel_module["cam-other"])
        self.logging.addHandler(birdhouse_loghandler)
        self.logging.info("Starting CAMERA support for '"+name+"/"+source+"' ...")

        if "/dev/" not in str(source):
            source = "/dev/video" + str(source)

        self.stream = cv2.VideoCapture(source, cv2.CAP_V4L)
        try:
            ref, raw = self.stream.read()
        except cv2.error as e:
            self.error = True
            self.error_msg = str(e)
            self.logging.warning("- Error connecting to camera '" + source + "' and reading first image")

    def read(self):
        try:
            ref, raw = self.stream.read()
            self.error = False
            return raw
        except cv2.error as e:
            self.logging.warning("- Error connecting to camera '" + source + "' and reading first image")
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
        self.health_check = time.time()

        self.logging = logging.getLogger(self.id+"-main")
        self.logging.setLevel(birdhouse_loglevel_module["cam-main"])
        self.logging.addHandler(birdhouse_loghandler)
        self.logging.info("Starting CAMERA control for '"+self.id+"' ...")

        self.sensor = sensor
        self.param = self.config.param["devices"]["cameras"][self.id]
        self.weather_active = self.config.param["weather"]["active"]
        # ------------------
        self.weather_sunrise = None
        self.weather_sunset = None

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
        self.record_seconds = []

        self.timezone = 0
        if "localization" in self.config.param and "timezone" in self.config.param["localization"]:
            self.timezone = float(self.config.param["localization"]["timezone"].replace("UTC", ""))
            self.logging.info("Set Timezone: " + self.config.param["localization"]["timezone"] +
                              " (" + str(self.timezone) + " / " + self.config.local_time().strftime("%H:%M") + ")")

        self.image_size = [0, 0]
        self.image_size_lowres = [0, 0]
        self.image_last_raw = None
        self.image_last_raw_time = 0
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
        self.image_to_select_last = "000000"
        self.previous_image = None
        self.previous_stamp = "000000"
        self.record_image_last = time.time()
        self.record_image_reload = time.time()
        self.record_image_last_string = ""
        self.record_image_last_compare = ""
        self.record_image_error = False

        self.logging.info("Initializing camera (" + self.id + "/" + self.type + "/" + str(self.source) + ") ...")

        self.image = BirdhouseImageProcessing(camera_id=self.id, camera=self, config=self.config, param=self.param,
                                              time_zone=self.timezone)
        self.image.resolution = self.param["image"]["resolution"]
        self.video = BirdhouseVideoProcessing(camera_id=self.id, camera=self, config=self.config, param=self.param,
                                              directory=self.config.db_handler.directory("videos"),
                                              time_zone=self.timezone)
        self.video.output = BirdhouseCameraOutput(self.id)
        self.camera = None
        self.cameraFPS = None

    def run(self):
        """
        Start recording for livestream and save images every x seconds
        """
        similarity = 0
        count_paused = 0
        reload_time = time.time()
        reload_time_error = 60*3
        reload_time_error_record = 60*3
        sensor_last = ""

        while self.running:
            current_time = self.config.local_time()
            stamp = current_time.strftime('%H%M%S')
            self.config_update = self.config.update["camera_" + self.id]

            # if shutdown
            if self.config.shut_down:
                self.stop()

            # if error reload from time to time
            if self.active and self.error and (reload_time + reload_time_error) < time.time():
                self.logging.info("....... RELOAD Error: " + self.id + " - " +
                                  str(reload_time + reload_time_error) + " > " + str(time.time()))
                reload_time = time.time()
                self.config_update = True
                self.reload_camera = True

            # if record and images not recorded for while reload
            if self.record and self.record_image_error and \
                    (self.record_image_reload + reload_time_error_record) < time.time():

                self.logging.info("....... RELOAD Record Error: " + self.id + " - " +
                                  str(self.record_image_last + reload_time_error_record) + " < " +
                                  str(time.time()))
                self.record_image_reload = time.time()
                self.config_update = True
                self.reload_camera = True

            # check if configuration shall be updated
            if self.config_update:
                self.logging.info("....... RELOAD Update: " + self.id + " - " +
                                  str(reload_time + reload_time_error) + " > " + str(time.time()))
                self.update_main_config()
                self.reload_camera = True

            # start or reload camera connection
            if self.reload_camera and self.active:
                self.logging.info("- (Re)starting Camera (" + self.id + ") ...")
                self.camera_start_default()
                if not self.error and self.param["video"]["allow_recording"]:
                    self.camera_start_recording()
                self.reload_camera = False

            # check if camera is paused, wait with all processes ...
            if not self._paused:
                count_paused = 0
            while self._paused and self.running:
                if count_paused == 0:
                    self.logging.info("Recording images with " + self.id + " paused ...")
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

                    self.logging.debug(".... Video Recording: " + str(self.video.info["stamp_start"]) + " -> " + str(
                        current_time.strftime("%H:%M:%S")))

            # Image Recording (if not video recording)
            elif not self.error and self.param["active"] and self.param["active"] != "False":
                time.sleep(0.3)
                if self.record:
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
                            sensor_data = {}
                            image_info = {
                                "camera": self.id,
                                "compare": (stamp, self.previous_stamp),
                                "date": current_time.strftime("%d.%m.%Y"),
                                "datestamp": current_time.strftime("%Y%m%d"),
                                "error": self.error_msg[len(self.error_msg) - 1],
                                "hires": "",
                                "lowres": "",
                                "similarity": 0,
                                "sensor": {},
                                "size": self.image_size,
                                "time": current_time.strftime("%H:%M:%S"),
                                "type": "data",
                                "weather": {}
                            }

                        if self.weather_active:
                            image_info["weather"] = self.config.weather.get_weather_info("current_small")

                        for key in self.sensor:
                            if self.sensor[key].running:
                                sensor_data[key] = self.sensor[key].get_values()
                                sensor_data[key]["date"] = current_time.strftime("%d.%m.%Y")
                                image_info["sensor"][key] = sensor_data[key]

                        sensor_stamp = current_time.strftime("%H%M") + "00"
                        self.config.queue.entry_add(config="images", date="", key=stamp, entry=image_info)

                        if int(self.config.local_time().strftime("%M")) % 5 == 0 and sensor_stamp != sensor_last:
                            sensor_last = sensor_stamp
                            self.logging.info("Write sensor data to file ...")
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
                            self.record_image_last = time.time()
                            self.record_image_reload = time.time()
                            self.record_image_last_string = self.config.local_time().strftime('%d.%m.%Y %H:%M:%S')

                        time.sleep(0.7)
                        self.previous_stamp = stamp

            self.health_check = time.time()

        self.logging.info("Stopped camera (" + self.id + "/" + self.type + ").")

    def stop(self):
        """
        Stop recording
        """
        if not self.error and self.active:
            self.cameraFPS.stop()

            if self.video:
                self.video.stop()

        self.running = False

    def pause(self, command):
        """
        pause image recording and reconnect try
        """
        self._paused = command

    def _raise_error(self, cam_error, message):
        """
        Report Error, set variables of modules
        """
        if cam_error:
            self.error = True
            self.image.error_camera = True
        else:
            self.image.raise_error(message)
        time_info = self.config.local_time().strftime('%d.%m.%Y %H:%M:%S')
        self.error_msg.append(time_info + " - " + message)
        if len(self.error_msg) >= 10:
            self.error_msg.pop()
        self.error_time = time.time()
        self.logging.error(self.id + ": " + message + " (" + str(self.error_time) + ")")

    def _reset_error(self):
        """
        remove all errors
        """
        self.error = False
        self.error_msg = []
        self.error_time = 0
        self.video.reset_error()
        self.image.reset_error()
        self.image_last_raw = None
        self.image_last_edited = None
        self.image_last_edited_lowres = None
        self.image_last_size_lowres = None

    def camera_start_default(self):
        """
        Try out new
        """
        self._reset_error()
        self.reload_time = time.time()
        try:
            self.camera.stream.release()
        except Exception as e:
            self.logging.info("Ensure Stream is released ...")

        try:
            self.camera = BirdhouseCameraOther(self.source, self.id)

            if self.camera.error:
                self._raise_error(True, "Can't connect to camera, check if '" + str(
                    self.source) + "' is a valid source (" + self.camera.error_msg + ").")
                self.camera.stream.release()
            elif not self.camera.stream.isOpened():
                self._raise_error(True, "Can't connect to camera, check if '" + str(
                    self.source) + "' is a valid source (could not open).")
                self.camera.stream.release()
            elif self.camera.stream is None:
                self._raise_error(True, "Can't connect to camera, check if '" + str(
                    self.source) + "' is a valid source (empty image).")
                self.camera.stream.release()
            else:
                raw = self.get_image_raw()
                check = str(type(raw))
                if "NoneType" in check:
                    self._raise_error(True,
                                     "Source " + str(self.source) + " returned empty image, try type 'pi' or 'usb'.")
                else:
                    self.camera_resolution_usb(self.param["image"]["resolution"])
                    self.cameraFPS = FPS().start()
                    self.logging.info(self.id + ": OK (Source=" + str(self.source) + ")")

        except Exception as e:
            self._raise_error(True, "Starting camera '" + self.source + "' doesn't work: " + str(e))

        return

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
            self.logging.info("USB Current resolution: " + str(current))
        except Exception as e:
            self.logging.warning("Could not get current resolution: " + self.id)

        high_value = 10000
        self.camera.stream.set(cv2.CAP_PROP_FRAME_WIDTH, high_value)
        self.camera.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, high_value)
        self.max_resolution = [self.camera.stream.get(cv2.CAP_PROP_FRAME_WIDTH),
                               self.camera.stream.get(cv2.CAP_PROP_FRAME_HEIGHT)]
        self.logging.debug(self.id + " Maximum resolution: " + str(self.max_resolution))

        if "x" in resolution:
            dimensions = resolution.split("x")
            self.logging.debug(self.id + " Set resolution: " + str(dimensions))
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
            self.logging.info(self.id + " New resolution: " + str(current))
            self.logging.debug(self.id + " New crop area:  " + str(self.param["image"]["crop"]) + " -> " +
                               str(self.param["image"]["crop_area"]))
        else:
            self.logging.info("Resolution definition not supported: " + str(resolution))

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

        raw = self.get_image_raw()
        encoded = self.image.convert_from_raw(raw)
        return encoded

    def get_image_raw(self):
        """
        get image and convert to raw
        """
        if self.error:
            return ""

        self.image.reset_error()
        try:
            raw = self.camera.read()
            check = str(type(raw))
            if self.camera.error:
                self._raise_error(False, "Error reading image (source=" + str(self.source) + ", " +
                                  self.camera.error_msg + ")")
                return ""
            elif "NoneType" in check or len(raw) == 0:
                self._raise_error(False, "Got an empty image (source=" + str(self.source) + ")")
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
            self._raise_error(False, error_msg)
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

    def image_recording_active(self, current_time=-1, check_in_general=False):
        """
        check if image recording is active
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

                if ("sunrise" in record_from or "sunset" in record_to) and \
                        self.weather_active and self.weather_sunrise is not None:
                    if "sunrise-1" in record_from:
                        record_from_hour = int(self.weather_sunrise.split(":")[0]) - 1
                        record_from_minute = self.weather_sunrise.split(":")[1]
                    elif "sunrise+0" in record_from:
                        record_from_hour = int(self.weather_sunrise.split(":")[0])
                        record_from_minute = self.weather_sunrise.split(":")[1]
                    elif "sunrise+1" in record_from:
                        record_from_hour = int(self.weather_sunrise.split(":")[0]) + 1
                        record_from_minute = self.weather_sunrise.split(":")[1]
                    if "sunset-1" in record_to:
                        record_to_hour = int(self.weather_sunset.split(":")[0]) - 1
                        record_to_minute = self.weather_sunset.split(":")[1]
                    elif "sunset+0" in record_to:
                        record_to_hour = int(self.weather_sunset.split(":")[0])
                        record_to_minute = self.weather_sunset.split(":")[1]
                    elif "sunset+1" in record_to:
                        record_to_hour = int(self.weather_sunset.split(":")[0]) + 1
                        record_to_minute = self.weather_sunset.split(":")[1]
                else:
                    if "sunrise" in record_from:
                        record_from_hour = 7
                        record_from_minute = 0
                    if "sunset" in record_to:
                        record_to_hour = 20
                        record_to_minute = 0

                if record_from_hour == -1:
                    record_from_hour = record_from
                    record_from_minute = 0
                if record_to_hour == -1:
                    record_to_hour = record_to
                    record_to_minute = 59

                self.logging.debug(" -> RECORD check " + self.id + "  (" + str(record_from_hour) + ":" +
                                   str(record_from_minute) + "-" + str(record_to_hour) + ":" +
                                   str(record_to_minute) + ") " + str(int(hour)) + "/" + str(int(minute)) + "/" +
                                   str(int(second)) + " ... " + str(self.record_seconds))

                if int(second) in self.record_seconds or check_in_general:
                    if ((int(record_from_hour)*60)+int(record_from_minute)) <= ((int(hour)*60)+int(minute)) <= \
                            ((int(record_to_hour)*60)+int(record_to_minute)):
                        self.logging.debug(
                            " -> RECORD TRUE "+self.id+"  (" + str(record_from_hour) + ":" + str(record_from_minute) + "-" +
                            str(record_to_hour) + ":" + str(record_to_minute) + ") " +
                            str(hour) + "/" + str(minute) + "/" + str(second) + "  < -----")
                        is_active = True

        self.logging.debug(" -> RECORD FALSE "+self.id+" (" + str(record_from_hour) + ":" + str(record_from_minute) +
                           "-" + str(record_to_hour) + ":" + str(record_to_minute) + ")")

        if check_in_general:
            self.record_image_last_compare += "[" + str(is_active) + " | " + current_time_string + "] [from " + \
                                              str(int(record_from_hour)) + ":" + str(int(record_from_minute)) + \
                                              " | to " + str(int(record_to_hour)) + ":" + str(int(record_to_minute)) + \
                                              "]"

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
        if "similarity" not in file_info:
            return False

        elif "to_be_deleted" in file_info and int(file_info["to_be_deleted"]) == 1:
            return False

        elif ("camera" in file_info and file_info["camera"] == self.id) or (
                "camera" not in file_info and self.id == "cam1"):

            if "favorit" in file_info and int(file_info["favorit"]) == 1:
                return True

            elif timestamp[2:4] == "00" and timestamp[0:4] != self.image_to_select_last[0:4]:
                self.image_to_select_last = timestamp
                return True

            elif check_similarity:
                threshold = float(self.param["similarity"]["threshold"])
                similarity = float(file_info["similarity"])
                if similarity != 0 and similarity < threshold:
                    return True

            else:
                return True  # to be checked !!!

        return False

    def get_stream_raw(self, normalize=False, stream_id="", lowres=False):
        """
        get image, if error return error message on image
        -> IMPROVE: reuse images, if multiple streams ... (define primary stream, others use copies ...)
                    check if in device mode there are two streams of each camera?!
        -> IMPROVE: reuse error images (lower frame rate required)
        """

        image = self.get_image_raw()
        fps_rotate = self.get_stream_fps(stream_id=stream_id)

        # grab existing images if less than 10 image errors
        if not self.error and self.image.error and self.image.error_count < 10:
            if not lowres and self.image_last_edited is not None:
                image = self.image_last_edited
                image = cv2.circle(image, (25, 50), 4, (0, 0, 255), 6)
                return image
            elif lowres and self.image_last_edited_lowres is not None:
                image = self.image_last_edited_lowres
                image = cv2.circle(image, (25, 50), 4, (0, 0, 255), 6)
                return image

        # if 10 or more image errors or a camera error return error msg as image
        elif self.error or self.image.error:
            if lowres:
                image_error = self.image.image_error_info_raw(self.error_msg, self.reload_time, "empty")
                image_error = self.image.normalize_error_raw(image_error)
            elif normalize:
                image_error = self.image.image_error_info_raw(self.error_msg, self.reload_time, "reduced")
                image_error = self.image.normalize_error_raw(image_error)
            else:
                image_error = self.image.image_error_info_raw(self.error_msg, self.reload_time, "complete")

            if "show_framerate" in self.param["image"] and self.param["image"]["show_framerate"] \
                    and stream_id in self.image_fps and not lowres:
                image_error = self.image.draw_text_raw(raw=image_error,
                                                       text=str(round(self.image_fps[stream_id], 1)) + "fps   " +
                                                            fps_rotate, font=cv2.QT_FONT_NORMAL, color=(0, 0, 0),
                                                       position=(20, -20), scale=0.4, thickness=1)
            if lowres:
                if self.image_last_size_lowres is None:
                    self.image_last_size_lowres = self.image.size_raw(raw=image_error, scale_percent=self.param["image"]["preview_scale"])
                image_error = self.image.resize_raw(raw=image_error, scale_percent=100, scale_size=self.image_last_size_lowres)

            return image_error

        # if no error create image for stream
        else:
            if normalize:
                image = self.image.normalize_raw(image)

            if not self.video.recording and not self.video.processing and not lowres:
                if "show_framerate" in self.param["image"] and self.param["image"]["show_framerate"]:
                    image = self.image.draw_text_raw(raw=image,
                                                     text=str(round(self.image_fps[stream_id], 1)) + "fps   "
                                                          + fps_rotate, font=cv2.QT_FONT_NORMAL,
                                                     position=(10, -20), scale=0.4, thickness=1)
            if lowres:
                if self.image_last_size_lowres is None:
                    self.image_last_size_lowres = self.image.size_raw(raw=image, scale_percent=self.param["image"]["preview_scale"])
                image = self.image.resize_raw(raw=image, scale_percent=100, scale_size=self.image_last_size_lowres)
                self.image_last_edited_lowres = image
            else:
                self.image_last_edited = image

            return image

    def get_stream_count(self):
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

    def get_stream_fps(self, stream_id):
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

    def get_stream_kill(self, stream_id):
        """
        check if stream has to be killed
        """
        self.logging.debug("get_image_stream_kill: " + str(stream_id))
        if stream_id in self.image_streams_to_kill:
            self.logging.info("get_image_stream_kill - True: " + str(stream_id))
            del self.image_streams_to_kill[stream_id]
            return True
        else:
            return False

    def set_stream_kill(self, stream_id):
        """
        mark streams to be killed
        """
        self.logging.info("set_image_stream_kill: " + stream_id)
        self.image_streams_to_kill[stream_id] = datetime.now().timestamp()

    def get_camera_status(self):
        """
        return all status and error information
        """
        status = {
            "active_streams": self.get_stream_count(),
            "error": self.error,
            "error_warn": self.error_msg,
            "error_msg": ",\n".join(self.error_msg),
            "image_error": self.image.error,
            "image_error_msg": ",\n".join(self.image.error_msg),
            "image_cache_size": self.config_cache_size,
            "record_image_error": self.record_image_error,
            "record_image_last": time.time() - self.record_image_last,
            "record_image_reload": time.time() - self.record_image_reload,
            "record_image_active": self.image_recording_active(current_time=-1, check_in_general=True),
            "record_image_last_compare": self.record_image_last_compare,
            "video_error": self.video.error,
            "video_error_msg": ",\n".join(self.video.error_msg),
            "running": self.running
            }
        return status

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
        self.logging.debug("-----------------" + self.id + "------- show area")
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
        self.logging.debug("Write image: " + image_path)

        try:
            if scale_percent != 100:
                width = int(image.shape[1] * float(scale_percent) / 100)
                height = int(image.shape[0] * float(scale_percent) / 100)
                image = cv2.resize(image, (width, height))
            return cv2.imwrite(image_path, image)

        except Exception as e:
            error_msg = "Can't save image and/or create thumbnail '" + image_path + "': " + str(e)
            self._raise_error(False, error_msg)
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
            self._raise_error(False, error_msg)
            return ""

    def update_main_config(self):
        self.logging.info("Update data from main configuration file for camera " + self.id)
        temp_data = self.config.db_handler.read("main")
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

        self.camera_resolution_usb(self.param["image"]["resolution"])
