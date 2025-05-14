import time
import ffmpeg
import os
import logging
import subprocess as sp

from modules.presets import *
from modules.bh_class import BirdhouseClass
from ffmpeg_progress import start


class BirdhouseFfmpegTranscoding(BirdhouseClass):
    """
    class to control ffmpeg transcoding
    """

    def __init__(self, camera_id, config, device_id):
        """
        Constructor method for initializing the class.

        Args:
            camera_id (str): id string to identify the camera from which this class is embedded
            config (modules.config.BirdhouseConfig): reference to main config object
        """
        BirdhouseClass.__init__(self, class_id="ffmpeg-trc", class_log="cam-ffmpg",
                                device_id=camera_id, config=config)

        self.audio_filename = ""
        self.audio_framerate = 12
        self.audio_samplerate = 0

        self.camera_id = device_id
        self.camera_config = config.param["devices"]["cameras"][self.camera_id]
        self.micro_id = config.param["devices"]["cameras"][self.camera_id]["record_micro"]
        self.micro_config = {}
        if self.micro_id != "" and self.micro_id in config.param["devices"]["microphones"]:
            self.micro_config = config.param["devices"]["microphones"][self.micro_id]
            self.audio_samplerate = str(self.micro_config["sample_rate"])

        self.logging.info("Connect ffmpeg for '" + self.camera_id + "' / '" + self.micro_id + "'")

        self.progress_info = {"percent": 0, "frame_count": 0, "frames": 0, "elapsed": 0}
        self.output_codec = {
            "video-codec": "libx264",
            "audio-codec": "aac",
            "sample-rate": "441000",
            "crf": 18
        }
        self.process_id = ""
        self.process = None

        self.ffmpeg_handler_available = ["cmd-line", "python-ffmpeg", "ffmpeg-python", "ffmpeg-progress"]
        self.ffmpeg_handler = "ffmpeg-progress"
        self.ffmpeg_running = False

        self.ffmpeg_command = "/usr/bin/ffmpeg -y -threads 1 "
        self.ffmpeg_progress = "-nostats -loglevel 0 -vstats_file {VSTATS_PATH} "

        if self.ffmpeg_handler == "ffmpeg-progress":
            self.ffmpeg_command = self.ffmpeg_command + self.ffmpeg_progress

        self.ffmpeg_create_av_test = self.ffmpeg_command + \
                                "-f image2 -r {FRAMERATE} -i {INPUT_FILENAMES} " + \
                                "-ar {SAMPLERATE} -i {INPUT_AUDIO_FILENAME} " + \
                                 "-filter_complex \"[1:a]adeclick[aud]\"  -map 0:v -map \"[aud]\" " + \
                                 "-c:v " + self.output_codec["video-codec"] + " " + \
                                "-c:a " + self.output_codec["audio-codec"] + " " + \
                                "-crf " + str(self.output_codec["crf"]) + " " + \
                                "{OUTPUT_FILENAME}"

        self.ffmpeg_create_av = self.ffmpeg_command + \
                                "-f image2 -r {FRAMERATE} -i {INPUT_FILENAMES} " + \
                                "-i {INPUT_AUDIO_FILENAME} " + \
                                "-af adeclick " + \
                                "-c:v " + self.output_codec["video-codec"] + " " + \
                                "-c:a " + self.output_codec["audio-codec"] + " " + \
                                "-crf " + str(self.output_codec["crf"]) + " " + \
                                "{OUTPUT_FILENAME}"

        self.ffmpeg_create = self.ffmpeg_command + \
                             "-f image2 -r {FRAMERATE} -i {INPUT_FILENAMES} " + \
                             "-c:v " + self.output_codec["video-codec"] + " " + \
                             "-crf " + str(self.output_codec["crf"]) + " " + \
                             "{OUTPUT_FILENAME}"

        self.ffmpeg_trim = self.ffmpeg_command + " " + \
                           "-i {INPUT_FILENAME} -r {FRAMERATE} " + \
                           "-c:v " + self.output_codec["video-codec"] + " " + \
                           "-crf " + str(self.output_codec["crf"]) + " " + \
                           "-ss {START_TIME} -to {END_TIME} " + \
                           "{OUTPUT_FILENAME}"
        self.current_output_file = ""

    def ffmpeg_callback(self, infile, outfile, vstats_path):
        """
        callback function to get transcoding progress information - to be validated / experimental and not in use

        Args:
            infile (str): filename of input file
            outfile (str): filename for output file
            vstats_path (str): filename for progress information
        Returns:
            Any: to be validated
        """
        if self.audio_filename == "":
            cmd_ffmpeg = self.ffmpeg_create
        else:
            cmd_ffmpeg = self.ffmpeg_create_av

        cmd_ffmpeg = cmd_ffmpeg.replace("{INPUT_FILENAMES}", infile)
        cmd_ffmpeg = cmd_ffmpeg.replace("{VSTATS_PATH}", vstats_path)
        cmd_ffmpeg = cmd_ffmpeg.replace("{INPUT_AUDIO_FILENAME}", self.audio_filename)
        cmd_ffmpeg = cmd_ffmpeg.replace("{SAMPLERATE}", self.audio_samplerate)
        cmd_ffmpeg = cmd_ffmpeg.replace("{OUTPUT_FILENAME}", outfile)
        cmd_ffmpeg = cmd_ffmpeg.replace("{FRAMERATE}", str(round(float(self.audio_framerate), 1)))
        cmd_ffmpeg = cmd_ffmpeg.replace("   ", " ")
        cmd_ffmpeg = cmd_ffmpeg.replace("  ", " ")
        cmd_parts = cmd_ffmpeg.split(" ")
        self.logging.info('ffmpeg-progress: START ' + str(cmd_parts))
        self.process = sp.Popen(cmd_parts)
        return self.process.pid

    def on_message_handler(self, percent: float, fr_cnt: int, total_frames: int, elapsed: float):
        """
        get progress information and safe in a central dict - to be validated / experimental not in use

        Args:
            percent (float): progress in percent
            fr_cnt (int): frame count
            total_frames (int): total frames of the video
            elapsed (float): time elapsed sind start of progress
        """
        self.progress_info = {
            "percent": percent,
            "frame_count": fr_cnt,
            "frames": total_frames,
            "elapsed": elapsed
        }
        self.logging.debug("ffmpeg-progress: " + str(round(percent, 2)) + "%, " +
                           str(fr_cnt) + "/" + str(total_frames) + ", " + str(round(elapsed, 2)))

    def on_done_handler(self):
        """
        reset progress information when done
        """
        self.progress_info = {"percent": 0, "frame_count": 0, "frames": 0, "elapsed": 0}
        self.logging.info('ffmpeg-progress: DONE')

    def create_video(self, process_id, input_filenames, framerate, output_filename, input_audio_filename=""):
        """
        create video file from images files

        Args:
            process_id (str): process identifier
            input_filenames (str): input filename
            framerate (str): framerate in frames per second
            output_filename (str): output filename
            input_audio_filename (str): input audio filename if available (otherwise create video without audio)
        Returns:
            booL: success state
        """
        self.process_id = process_id
        self.current_output_file = output_filename
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
            elif self.ffmpeg_handler == "ffmpeg-progress":
                # for details see https://github.com/Tatsh/ffmpeg-progress
                self.audio_filename = input_audio_filename
                self.audio_framerate = framerate
                start(input_filenames,
                      output_filename,
                      self.ffmpeg_callback,
                      on_message=self.on_message_handler,
                      on_done=self.on_done_handler,
                      wait_time=1)  # seconds

            return True

        except Exception as err:
            self.raise_error(
                "Error during ffmpeg video creation (" + self.id + " / " + self.ffmpeg_handler + "): " + str(err))
            return False

    def trim_video(self, input_filename, output_filename, start_timecode, end_timecode, framerate):
        """
        trim a video using ffmpeg

        Args:
            input_filename (str): input filename
            output_filename (str): output filename for trimmed video
            start_timecode (float): start timecode for trimmed video
            end_timecode (float): end timecode for trimmed video
            framerate (float): framerate in frames per second
        Returns:
            bool: success state
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
            elif self.ffmpeg_handler == "cmd-line" or self.ffmpeg_handler == "ffmpeg-progress":
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
            self.raise_error(
                "Error during ffmpeg video trimming (" + self.id + " / " + self.ffmpeg_handler + "): " + str(err))
            return False

    def cancel_process(self):
        """
        cancel running process

        Returns:
            str: output filename
        """
        if self.process:
            self.process.terminate()
            self.logging.info("Terminate running ffmpeg process.")
            return self.current_output_file
        else:
            self.logging.warning("No ffmpeg process running to terminate.")
            return ""
