import cv2
import threading
import time
import os

from modules.presets import *
from modules.bh_class import BirdhouseCameraClass
from modules.bh_ffmpeg import BirdhouseFfmpegTranscoding
from modules.image import BirdhouseImageSupport

from modules.presets import birdhouse_env


class BirdhouseVideoProcessing(threading.Thread, BirdhouseCameraClass):
    """
    Record videos: start and stop; from all pictures of the day
    """

    def __init__(self, camera_id, camera, config):
        """
        Constructor method for initializing the class.

        Args:
            camera_id (str): id string to identify the camera from which this class is embedded
            camera (modules.camera.BirdhouseCamera): reference to camera object
            config (modules.config.BirdhouseConfig): reference to main config object
        """
        threading.Thread.__init__(self)
        BirdhouseCameraClass.__init__(self, class_id=camera_id+"-video", class_log="video",
                                      camera_id=camera_id, config=config)

        self.camera = camera
        self.micro = None
        self.name = self.param["name"]
        self.directory = self.config.db_handler.directory("videos")
        self.queue_create = []
        self.queue_trim = []
        self.queue_thumb = []
        self.queue_wait = 10

        self.record_audio_filename = ""
        self.record_video_info = None
        self.record_start_time = None
        self.record_timestamps_before = []
        self.record_timestamps_after = []
        self.image_size = [0, 0]
        self.recording = False
        self.processing = False
        self.processing_cancel = False
        self.processing_day_video = False
        self.max_length = 60
        self.delete_temp_files = True   # usually set to True, can temporarily be used to keep recorded files for analysis

        self.config.set_processing("video-recording", self.id, False)

        self.img_support = BirdhouseImageSupport(camera_id, config)
        self.ffmpeg = BirdhouseFfmpegTranscoding(self.id, self.config, camera_id)
        self.count_length = 8
        self.info = {
            "start": 0,
            "start_stamp": 0,
            "status": "ready",
            "video_fps": {}
        }
        self._running = False

    def run(self):
        """
        Thread control: start queue to create or trim a video file
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

                # create thumbnail of video
                if len(self.queue_thumb) > 0:
                    [video_id, start, end] = self.queue_thumb.pop()
                    self.logging.info("Start thumbnail extraction (" + video_id + "): " + str(start) + ".")
                    response = self.create_video_thumb(video_id, start)
                    self.config.async_answers.append(["THUMB_DONE", video_id, response["result"]])

            self.thread_control()

        self.logging.info("Stopped VIDEO processing for '"+self.id+"'.")

    def stop(self):
        """
        Stop running process and thread
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

        Returns:
            dict: recording status
        """
        return self.record_video_info.copy()

    def filename(self, file_type="image"):
        """
        generate filename for images

        Args:
            file_type (str): file type to create filename (video, thumb, vimages)
        Returns:
            str: filename
        """
        if file_type == "video":
            return self.img_support.filename(image_type="video", timestamp=self.info["date_start"], camera=self.id)
        elif file_type == "thumb":
            return self.img_support.filename(image_type="thumb", timestamp=self.info["date_start"], camera=self.id)
        elif file_type == "vimages":
            return self.img_support.filename(image_type="vimages", timestamp=self.info["date_start"], camera=self.id)
        else:
            return

    def record_start(self, micro="", audio_filename=""):
        """
        start video recoding

        Args:
            micro (str): id of microphone to get audio from
            audio_filename (str): filename for audio to be recorded
        """
        response = {"command": ["start recording"]}
        self.micro = micro
        self.record_audio_filename = audio_filename
        self.processing_cancel = False
        self.info["status"] = "recording"
        self.record_timestamps_before = []
        self.record_timestamps_after = []

        if self.camera.active and not self.camera.error and not self.recording:
            self.logging.info("Starting video recording (camera=" + self.id + " / micro=" + micro + ") ...")

            self.thread_register_process("recording", self.id + "_" + self.micro, "start", 0)
            self.thread_prio_process(start=True, pid=self.id)
            self.recording = True
            self.config.set_processing("video-recording", self.id, True)

            self.logging.info(" --- " + self.id + " --> " + str(time.time()))
            self.record_start_time = time.time()
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

    def record_cancel(self):
        """
        cancel video recording process

        Returns:
            dict: information for API response
        """
        self.thread_prio_process(start=False, pid=self.id)
        response = {"command": ["cancel recording"]}
        self.record_timestamps_before = []
        self.record_timestamps_after = []

        if self.camera.active and not self.camera.error and self.processing:
            self.logging.info("Cancel video processing (" + self.id + ") ...")
            filename = self.ffmpeg.cancel_process()
            self.processing = False
            self.cleanup(filename)
        if self.camera.active and not self.camera.error and self.recording:
            self.logging.info("Cancel video recording (" + self.id + ") ...")
            self.recording = False
            self.processing = False
            self.processing_cancel = True
            self.config.set_processing("video-recording", self.id, False)
            self.cleanup()
        elif not self.camera.active:
            response["error"] = "camera is not active " + self.camera.id
        elif not self.recording:
            response["error"] = "camera isn't recording " + self.camera.id

        return response

    def record_stop(self):
        """
        stop video recoding

        Returns:
            dict: recording information
        """
        self.thread_prio_process(start=False, pid=self.id)
        response = {"command": ["stop recording"]}
        if self.camera.active and not self.camera.error and self.recording:
            self.logging.info("Stopping video recording (" + self.id + ") ...")
            current_time = self.config.local_time()
            self.info["date_end"] = current_time.strftime('%Y%m%d_%H%M%S')
            self.info["stamp_end"] = current_time.timestamp()
            self.info["status"] = "processing"
            self.info["length"] = round(self.info["stamp_end"] - self.info["stamp_start"], 2)
            self.info["fps"] = self.record_stop_fps_details()

            initial_stamp = self.record_timestamps_after[0]
            if "av_sync" in birdhouse_env and birdhouse_env["av_sync"] == True:
                count = 0
                last_after = last_fps = 0
                self.info["video_fps"] = {
                    "titles": ["fps", "fps_diff", "saving duration"],
                    "data": {}
                }
                for before, after in zip(self.record_timestamps_before, self.record_timestamps_after):
                    duration = after - before
                    fps = 0
                    if last_after != 0:
                        fps = 1 / (after - last_after)
                        fps_diff = fps - last_fps
                    if count > 2:
                        stamp = after - initial_stamp
                        self.info["video_fps"]["data"][str(round(stamp, 2)).zfill(7)] = [round(fps, 5), round(fps_diff, 5), round(duration, 5)]
                    last_after = after
                    last_fps = fps
                    count += 1
            else:
                del self.info["video_fps"]

            if float(self.info["length"]) > 1:
                self.info["framerate"] = round(float(self.info["image_count"]) / float(self.info["length"]), 2)
            else:
                self.info["framerate"] = 0
            self.logging.info("--------------------> Length: "+str(self.info["length"]))
            self.logging.info("--------------------> Count: "+str(self.info["image_count"]))
            self.logging.info("--------------------> FPS: "+str(self.info["framerate"]))
            self.logging.info(" <-- " + self.id + " --- " + str(time.time()) + " ... (" +
                              str(round(time.time() - self.record_start_time, 3)) + ")")
            self.recording = False
            self.config.set_processing("video-recording", self.id, False)
            success = self.create_video()
            if success:
                self.info["audio"] = self.config.record_audio_info

                if "stamp_start" in self.info["audio"]:
                    self.info["audio"]["delay"] = self.info["stamp_start"] - self.info["audio"]["stamp_start"]
                self.info["status"] = "finished"
                self.config.queue.entry_add(config="videos", date="", key=self.info["date_start"], entry=self.info.copy())
                self.config.record_audio_info = {}
            self.thread_register_process("recording", self.id + "_" + self.micro, "stop", 0)
        elif not self.camera.active:
            response["error"] = "camera is not active " + self.camera.id
        elif not self.recording:
            response["error"] = "camera isn't recording " + self.camera.id
        return response

    def record_stop_fps_details(self):
        """
        analyze fps for audio and video during the recording

        Returns:
            dict: details in a format that can be used for chart.js
        """
        fps_details = {"video":{}, "audio":{}}
        if "av_sync" in birdhouse_env and birdhouse_env["av_sync"] == True:
            initial_stamp = self.record_timestamps_after[0]
            count = last_after = last_fps = 0
            fps_details["video"] = {
                "titles": ["video_fps", "video_fps_diff", "img_saving"],
                "data": {}
            }
            for before, after in zip(self.record_timestamps_before, self.record_timestamps_after):
                duration = after - before
                fps = 0
                if last_after != 0:
                    fps = 1 / (after - last_after)
                    fps_diff = fps - last_fps
                    self.logging.debug(" ---> " + str(fps) + " / " + str(after))
                if count > 2:
                    stamp = after - initial_stamp
                    fps_details["video"]["data"][str(round(stamp, 2)).zfill(7)] = [round(fps, 5), round(fps_diff, 5),
                                                                                     round(duration, 5)]
                last_after = after
                last_fps = fps
                count += 1

            initial_stamp = self.config.record_audio_info["audio_fps"][0]
            count = last_timestamp = last_fps = 0
            fps_details["audio"] = {
                "titles": ["audio_fps", "audio_fps_diff"],
                "data": {}
            }
            for timestamp in self.config.record_audio_info["audio_fps"]:
                if last_timestamp != 0:
                    fps = 1 / (timestamp - last_timestamp)
                    fps_diff = fps - last_fps
                    self.logging.debug(" ---> " + str(fps) + " / " + str(timestamp))
                if count > 2:
                    stamp = timestamp - initial_stamp
                    fps_details["audio"]["data"][str(round(stamp, 2)).zfill(7)] = [round(fps, 5), round(fps_diff, 5)]
                last_timestamp = timestamp
                last_fps = fps
                count += 1

        return fps_details

    def record_stop_auto(self):
        """
        Check if maximum length is achieved

        Returns:
            bool: recording to be stopped due to maximum length
        """
        self.thread_prio_process(start=False, pid=self.id)
        if not "stamp_start" in self.info:
            self.info["stamp_start"] = self.config.local_time().timestamp()

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

        Returns:
            dict: recording information
        """
        if self.recording:
            self.info["length"] = round(self.config.local_time().timestamp() - self.info["stamp_start"], 1)
            self.info["process"] = "recording"
        elif self.processing:
            self.info["length"] = round(self.info["stamp_end"] - self.info["stamp_start"], 1)
            self.info["process"] = "processing"
        elif self.processing_day_video:
            self.info["process"] = "video_of_day"
        else:
            self.info["process"] = "none"

        if self.info["process"] != "none":

            self.info["image_size"] = self.image_size

            if "length" in self.info and float(self.info["length"]) > 1:
                self.info["framerate"] = round(float(self.info["image_count"]) / float(self.info["length"]), 1)
            else:
                self.info["framerate"] = 0

            for key in self.ffmpeg.progress_info:
                self.info[key] = self.ffmpeg.progress_info[key]

        return self.info

    def create_video(self):
        """
        Create video from images using ffmpeg

        Returns:
            bool: success status
        """
        if self.processing:
            return

        success = False
        self.processing = True
        self.logging.info("Start video creation with ffmpeg ...")
        self.thread_register_process("recording", self.id + "_" + self.micro, "encoding", 0)
        if self.record_audio_filename != "" and not self.processing_cancel:
            self.logging.info("- including audio '" + str(self.record_audio_filename) + "' ...")
            count = 0
            while not os.path.exists(self.record_audio_filename) and count < 20 and not self.processing_cancel:
                time.sleep(1)
                count += 1
            if os.path.exists(self.record_audio_filename) and not self.processing_cancel:
                last_file_size = 0
                while last_file_size != os.path.getsize(self.record_audio_filename):
                    time.sleep(0.5)
                    last_file_size = os.path.getsize(self.record_audio_filename)
                    time.sleep(0.5)
            elif not os.path.exists(self.record_audio_filename) and not self.processing_cancel:
                self.record_audio_filename = ""
                self.logging.error("- audio file '" + str(self.record_audio_filename) + "' not available yet ...")

        if not self.processing_cancel:
            input_filenames = os.path.join(self.config.db_handler.directory("videos_temp"), self.filename("vimages") + "%" +
                                           str(self.count_length).zfill(2) + "d.jpg")
            output_filename = os.path.join(self.config.db_handler.directory("videos"), self.filename("video"))

            success = self.ffmpeg.create_video(self.id + "_" + self.micro, input_filenames, self.info["framerate"],
                                               output_filename, self.record_audio_filename)
            self.thread_register_process("recording", self.id + "_" + self.micro, "clean-up", 100)

        if not success or self.processing_cancel:
            self.processing = False
            success = False

        else:
            self.info["thumbnail"] = self.filename("thumb")
            cmd_thumb = "cp " + os.path.join(self.config.db_handler.directory("videos_temp"),
                                             self.filename("vimages") + str(1).zfill(self.count_length) + ".jpg "
                                             ) + os.path.join(self.config.db_handler.directory("videos"),
                                                              self.filename("thumb"))

        cmd_delete = "rm " + os.path.join(self.config.db_handler.directory("videos_temp"),
                                          self.filename("vimages") + "*.jpg")
        cmd_delete_audio = "rm " + self.record_audio_filename

        try:
            if success:
                self.logging.info(cmd_thumb)
                message = os.system(cmd_thumb)
                self.logging.debug(message)

            if self.delete_temp_files:
                self.logging.info(cmd_delete)
                message = os.system(cmd_delete)
                self.logging.debug(message)

                self.logging.info(cmd_delete_audio)
                message = os.system(cmd_delete_audio)
                self.logging.debug(message)

        except Exception as err:
            self.raise_error("Error during video creation (thumbnail/cleanup): " + str(err))
            self.processing = False
            success = False

        self.processing = False
        self.thread_register_process("recording", self.id + "_" + self.micro, "remove", 0)
        if not self.processing_cancel:
            self.logging.info("OK.")
        else:
            self.logging.info("Canceled processing.")
            self.processing_cancel = False
            self.record_audio_filename = ""
            success = False
        return success

    def save_video_image(self, image, delay=""):
        """
        Save image with predefined filename in temp directory

        Args:
            image (numpy.ndarray): image data
            delay (float): timestamp when image was created
        """
        timestamp_start = time.time()

        self.info["image_count"] += 1
        self.info["image_files"] = self.filename("vimages")
        self.info["video_file"] = self.filename("video")
        filename = self.info["image_files"] + str(self.info["image_count"]).zfill(self.count_length) + ".jpg"
        #path = os.path.join(self.directory, filename)
        path = os.path.join(self.config.db_handler.directory("videos_temp"), filename)
        self.logging.debug("Save image as: " + path)

        try:
            self.logging.debug("Write  image '" + path + "')")
            result = cv2.imwrite(str(path), image)
            if self.info["image_count"] == 1:
                self.logging.info("--> Record fist image: saved=" + str(time.time()) + " / delay=" + str(delay))
            self.record_timestamps_before.append(timestamp_start)
            self.record_timestamps_after.append(time.time())
            return result
        except Exception as e:
            self.info["image_count"] -= 1
            self.raise_error("Could not save image '" + filename + "': " + str(e))

    def create_video_day(self, filename, stamp, date):
        """
        Create daily video from all single images (of the current day) that are available

        Args:
            filename (str): input filename(s)
            stamp (str): date and time stamp as part of the output files
            date (str): date for the video to be created
        """
        camera = self.id
        cmd_videofile = "video_" + camera + "_" + stamp + ".mp4"
        cmd_thumbfile = "video_" + camera + "_" + stamp + "_thumb.jpeg"
        cmd_tempfiles = "img_" + camera + "_" + stamp + "_"
        framerate = 20

        self.thread_register_process("day_video", self.id, "start", 0)
        self.processing_day_video = True

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
        cmd_rename = "find " + self.config.db_handler.directory("videos_temp") + \
                     "image_* -type f -size 0 -delete; "
        cmd_rename += "i=0; " + \
                      "for fi in " + self.config.db_handler.directory("videos_temp") + \
                      "image_*[0-9][0-9][0-9][0-9][0-9][0-9].jpeg; " + \
                      "do mv \"$fi\" $(printf \"" + cmd_filename + "%05d.jpg\" $i); " + \
                      "i=$((i+1)); done"
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

        self.thread_register_process("day_video", self.id, "encoding", 0)

        self.logging.info("Starting FFMpeg video creation ...")
        input_filenames = cmd_filename + "%05d.jpg"
        output_filename = os.path.join(self.config.db_handler.directory("videos"), cmd_videofile)
        success = self.ffmpeg.create_video(self.id, input_filenames, framerate, output_filename)
        if not success:
            response = {"result": "error", "reason": "create video with ffmpeg", "message": ""}
            return response

        self.thread_register_process("day_video", self.id, "cleanup", 100)

        self.logging.info("Create thumbnail file ...")
        cmd_thumb = "cp " + cmd_filename + "00001.jpg " + self.config.db_handler.directory("videos") + cmd_thumbfile
        self.logging.debug(cmd_thumb)
        try:
            message = os.system(cmd_thumb)
            if message != 0:
                response = {"result": "error", "reason": "create thumbnail", "message": message}
                self.raise_error("Error during day video creation: create thumbnails.")
                return response

            if self.delete_temp_files:
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

        self.processing_day_video = False
        self.thread_register_process("day_video", self.id, "remove", 0)
        return response

    def create_video_day_queue(self, param):
        """
        create a video of all existing images of the day

        Args:
            param (dict): parameters from the API request (not used at the moment)
        Returns:
            dict: information for the API response
        """
        response = {}
        which_cam = self.id
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

        Args:
            video_id (str): id of the video to be trimmed
            start (float): start timecode
            end (float): end timecode
        Returns:
            str: success state (OK, Error)
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

    def create_video_thumb(self, video_id, start):
        """
        create thumbnail

        Args:
            video_id (str): id of the video to be trimmed
            start (float): image timecode

        Returns:
            str: success state (OK, Error)
        """
        config_file = self.config.db_handler.read_cache("videos")
        if video_id in config_file:
            input_file = config_file[video_id]["video_file"]
            output_file = config_file[video_id]["thumbnail"]
            output_file = output_file.replace(".jpeg", "_selected.jpeg")
            framerate = config_file[video_id]["framerate"]
            result = self.create_video_thumb_exec(input_file=input_file,
                                                  output_file=output_file,
                                                  start_timecode=start)
            if result == "OK":
                config_file[video_id]["thumbnail_selected"] = output_file

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

        Args:
            input_file (str): filename of input file
            output_file (str): filename for output file
            start_timecode (float): start timecode
            end_timecode (float): end timecode
            framerate (float): framerate in frames per seconds
        Returns:
            str: success state (OK, Error)
         """
        input_file = os.path.join(self.config.db_handler.directory("videos"), input_file)
        output_file = os.path.join(self.config.db_handler.directory("videos"), output_file)

        success = self.ffmpeg.trim_video(input_file, output_file, start_timecode, end_timecode, framerate)

        if success and os.path.isfile(output_file):
            return "OK"
        else:
            return "Error"

    def create_video_thumb_exec(self, input_file, output_file, start_timecode):
        """
        creates a thumbnail of the video

        Args:
            input_file (str): filename of input file
            output_file (str): filename for output thumbnail file
            start_timecode (float): timecode for video
        Returns:
            str: success state (OK, Error)
         """
        input_file = os.path.join(self.config.db_handler.directory("videos"), input_file)
        output_file = os.path.join(self.config.db_handler.directory("videos"), output_file)

        success = self.ffmpeg.create_thumbnail(input_file, output_file, start_timecode)

        if success and os.path.isfile(output_file):
            return "OK"
        else:
            return "Error"

    def create_video_trimmed_queue(self, param):
        """
        create a short video and save in DB (not deleting the old video at the moment)

        Args:
            param (dict): input from API request
        Returns:
            dict: information for API response
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

    def create_video_thumb_queue(self, param):
        """
        create a thumb video and save in DB (not deleting the old video at the moment)

        Args:
            param (dict): input from API request
        Returns:
            dict: information for API response
        """
        response = {}
        parameter = param["parameter"]

        self.logging.info("Create short version of video: " + str(parameter) + " ...")
        config_data = self.config.db_handler.read_cache(config="videos")

        if parameter[0] not in config_data:
            response["result"] = "Error: video ID '" + str(parameter[0]) + "' doesn't exist."
            self.logging.warning("VideoID '" + str(parameter[0]) + "' doesn't exist.")
        else:
            self.queue_thumb.append([parameter[0], parameter[1], parameter[2]])
            response["command"] = ["Create thumbnail of video"]
            response["video"] = {"video_id": parameter[0], "start": parameter[1], "end": parameter[2]}

        return response

    def create_video_audio_correction_queue(self, param):
        """
        Ideas
        * work with queue as done for video trimming (as it takes a while)
        * +/- offset
        * create from main file
        * save in DB entry as "video_file_audio_correction"
        """
        pass

    def replace_video_with_audio_correction(self, param):
        """
        * add function, to replace main video file with the corrected one
          (no option to recreate short version, has to be done before or manually)
        """
        pass

    def delete_shortened_video(self, param):
        """
        delete shortened video and remove references from db entry
        Args:
            param (dict): parameter from API request
        Returns:
            dict: information for API response
        """
        parameter = param["parameter"]
        video_id = parameter[0]
        response = {
            "video_id": video_id,
            "command": "Delete shortened video",
            }

        self.logging.info("Delete short version of video: " + str(parameter) + " ...")
        config_file = self.config.db_handler.read_cache("videos")

        if video_id in config_file:
            video = config_file[video_id].copy()
            file = video["video_file_short"]
            video["video_file_short"] = ""
            video["video_file_short_length"] = 0
            config_file[video_id] = video
            self.config.db_handler.write("videos", "", config_file)

            cmd_delete = "rm " + str(os.path.join(self.config.db_handler.directory("videos"), file))
            self.logging.info(cmd_delete)
            message = os.system(cmd_delete)
            self.logging.debug(message)
            response["message"] = message
        else:
            response["error"] = "Video ID " + video_id + " not found."

        return response

    def delete_thumbnail(self, param):
        """
        delete shortened video and remove references from db entry
        Args:
            param (dict): parameter from API request
        Returns:
            dict: information for API response
        """
        parameter = param["parameter"]
        video_id = parameter[0]
        response = {
            "video_id": video_id,
            "command": "Delete thumbnail",
            }

        self.logging.info("Delete thumbnail of video: " + str(parameter) + " ...")
        config_file = self.config.db_handler.read_cache("videos")

        if video_id in config_file:
            video = config_file[video_id].copy()
            file = video["thumbnail_selected"]
            video["thumbnail_selected"] = ""
            config_file[video_id] = video
            self.config.db_handler.write("videos", "", config_file)

            cmd_delete = "rm " + str(os.path.join(self.config.db_handler.directory("videos"), file))
            self.logging.info(cmd_delete)
            message = os.system(cmd_delete)
            self.logging.debug(message)
            response["message"] = message
        else:
            response["error"] = "Video ID " + video_id + " not found."

        return response

    def cleanup(self, output_file=""):
        """
        remove all files from last recording

        Args:
            output_file (str): in case the video creation has started the started file can be deleted also
        """
        cmd_delete = "rm " + os.path.join(self.config.db_handler.directory("videos_temp"),
                                          self.filename("vimages") + "*.jpg")
        self.logging.info(cmd_delete)
        message = os.system(cmd_delete)
        self.logging.debug(message)

        cmd_delete = "rm " + os.path.join(self.config.db_handler.directory("videos_temp"), "*.wav")
        self.logging.info(cmd_delete)
        message = os.system(cmd_delete)
        self.logging.debug(message)

        if output_file != "":
            cmd_delete = "rm " + output_file
            self.logging.info(cmd_delete)
            message = os.system(cmd_delete)
            self.logging.debug(message)
