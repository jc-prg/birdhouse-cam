import ffmpeg
import os
from modules.bh_class import BirdhouseClass


class BirdhouseFfmpegTranscoding(BirdhouseClass):

    def __init__(self, camera_id, config):
        BirdhouseClass.__init__(self, class_id="ffmpeg-trc", class_log="cam-ffmpg",
                                device_id=camera_id, config=config)

        self.output_codec = {
            "vcodec": "libx264",
            "acodec": "aac",
            "crf": 18
        }

        self.ffmpeg_create_av = "ffmpeg -f image2 -r {FRAMERATE} -i {INPUT_FILENAMES} " + \
                                "-i {INPUT_AUDIO_FILENAME} " + \
                                "-vcodec " + self.output_codec["vcodec"] + " " + \
                                "-acodec " + self.output_codec["acodec"] + " " + \
                                " -crf " + str(self.output_codec["crf"]) + " {OUTPUT_FILENAME}"

        self.ffmpeg_create = "ffmpeg -f image2 -r {FRAMERATE} -i {INPUT_FILENAMES} " + \
                             "-vcodec " + self.output_codec["vcodec"] + " " + \
                             " -crf " + str(self.output_codec["crf"]) + " {OUTPUT_FILENAME}"

        self.ffmpeg_trim = "ffmpeg -y -i {INPUT_FILENAME} -r {FRAMERATE} " + \
                           "-vcodec " + self.output_codec["vcodec"] + " " + \
                           "-crf " + str(self.output_codec["crf"]) + " " + \
                           "-ss {START_TIME} -to {END_TIME} {OUTPUT_FILENAME}"

        self.ffmpeg_handler_available = ["cmd-line", "python-ffmpeg", "ffmpeg-python"]
        self.ffmpeg_handler = "ffmpeg-python"
        self.ffmpeg_handler = "cmd-line"

    def create_video(self, input_filenames, framerate, output_filename, input_audio_filename=""):
        """
        create video file from images files
        """

        try:
            if self.ffmpeg_handler == "ffmpeg-python":
                (
                    ffmpeg
                    .input(input_filenames)
                    .filter('fps', fps=float(framerate), round='up')
                    .output(output_filename, vcodec=self.output_codec["vcodec"], crf=self.output_codec["crf"])
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=False)
                )
            elif self.ffmpeg_handler == "python-ffmpeg":
                ffmpeg_process = (
                    FFmpeg()
                    .option("y")
                    .input(input_filenames)
                    .output(output_filename,
                            {"codec:v": self.output_codec["vcodec"]},
                            vf="scale=1280:-1",
                            preset="veryslow",
                            crf=self.output_codec["crf"],
                            )
                )

                # @ffmpeg_process.on("progress")
                # def time_to_terminate(progress: Progress):
                #     self.logging.info("FFmpeg: " + str(progress))
                #     if progress.frame > 100:
                #         self.logging.info("FFmpeg: " + str(progress.frame))
                #         ffmpeg_process.terminate()

                @ffmpeg_process.on("progress")
                def document_progress(progress: Progress):
                    self.logging.info("FFmpeg progress = " + str(progress.frame) + " / " + str(progress))

                ffmpeg_process.execute()
            elif self.ffmpeg_handler == "cmd-line":
                if input_audio_filename == "":
                    cmd_ffmpeg = self.ffmpeg_create
                else:
                    cmd_ffmpeg = self.ffmpeg_create_av

                cmd_ffmpeg = cmd_ffmpeg.replace("{INPUT_FILENAMES}", input_filenames)
                cmd_ffmpeg = cmd_ffmpeg.replace("{INPUT_AUDIO_FILENAME}", input_audio_filename)
                cmd_ffmpeg = cmd_ffmpeg.replace("{OUTPUT_FILENAME}", output_filename)
                cmd_ffmpeg = cmd_ffmpeg.replace("{FRAMERATE}", str(round(float(framerate), 1)))

                self.logging.info("Call ffmpeg: " + cmd_ffmpeg)
                message = os.system(cmd_ffmpeg)
            return True

        except Exception as err:
            self.raise_error("Error during ffmpeg video creation (" + self.id + " / " + self.ffmpeg_handler + "): " + str(err))
            return False

    def trim_video(self, input_filename, output_filename, start_timecode, end_timecode, framerate):
        """
        trim a video using ffmpeg
        """

        start_frame = round(float(start_timecode) * float(framerate))
        end_frame = round(float(end_timecode) * float(framerate))

        try:
            if self.ffmpeg_handler == "ffmpeg-python":
                (
                    ffmpeg
                    .input(input_filename)
                    .filter('fps', fps=framerate, round='up')
                    .trim(start_frame=start_frame, end_frame=end_frame)
                    .output(output_filename)
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=False)
                )
            elif self.ffmpeg_handler == "python-ffmpeg":
                self.logging.warning("Trim video not yet implemented for '" + self.ffmpeg_handler + "'!")
                pass
            elif self.ffmpeg_handler == "cmd-line":
                cmd_ffmpeg = self.ffmpeg_trim
                cmd_ffmpeg = cmd_ffmpeg.replace("{START_TIME}", str(start_timecode))
                cmd_ffmpeg = cmd_ffmpeg.replace("{END_TIME}", str(end_timecode))
                cmd_ffmpeg = cmd_ffmpeg.replace("{INPUT_FILENAME}", str(input_filename))
                cmd_ffmpeg = cmd_ffmpeg.replace("{OUTPUT_FILENAME}", str(output_filename))
                cmd_ffmpeg = cmd_ffmpeg.replace("{FRAMERATE}", str(framerate))

                self.logging.info("Call ffmpeg: " + cmd_ffmpeg)
                message = os.system(cmd_ffmpeg)
            return True

        except Exception as err:
            self.raise_error("Error during ffmpeg video trimming (" + self.id + " / " + self.ffmpeg_handler + "): " + str(err))
            return False


class BirdhouseFfmpegProcessingDRAFT(BirdhouseClass):
    """
    draft how to handle ffmpeg incl process - requires python-ffmpeg (instead of ffmpeg-python)
    """

    def __init__(self, camera_id, camera, config):
        BirdhouseClass.__init__(self, class_id=camera_id+"-ffmpg", class_log="cam-ffmpg",
                                device_id=camera_id, config=config)
        self.progess_reset = {
            "running": False,
            "error": False,
            "percentage": 0,
            "estimated_time": 0,
            "estimated_filesize": 0,
            "speed": 0
        }
        self.progress_info = self.progess_reset.copy()

    def handle_progress_info(self, percentage, speed, eta, estimated_file_size):
        if percentage is not None:
            self.logging.info("FFMpeg progress: " + str(round(percentage, 1)) + "%; ...")
            self.progress_info["percentage"] = percentage
        if eta is not None:
            self.logging.info("FFMpeg progress: " + str(round(eta, 1)) + "s; ...")
            self.progress_info["estimated_time"] = eta
        if speed is not None:
            self.progress_info["speed"] = speed
        if estimated_file_size is not None:
            self.progress_info["estimated_filesize"] = estimated_file_size

    def handle_success(self):
        """Code to run if the FFmpeg process completes successfully."""
        self.progress_info = self.progess_reset.copy()

    def handle_error(self):
        """Code to run if the FFmpeg process encounters an error."""
        self.progress_info["error"] = True

    def start_process(self, commands):
        """
        Run FFMpeg process
        process = FfmpegProcess(["ffmpeg", "-i", "input.mp4", "-c:a", "libmp3lame", "output.mp3"])
        """
        self.logging.info("Start rendering: " + str(commands))
        self.progress_info["running"] = True
        process = FfmpegProcess(commands)
        process.run(progress_handler=self.handle_progress_info,
                    success_handler=self.handle_success,
                    error_handler=self.handle_error)

