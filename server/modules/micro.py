import pyaudio
import threading
import time
import wave
import os
from modules.presets import *
from modules.bh_class import BirdhouseClass



class BirdhouseMicrophone(threading.Thread, BirdhouseClass):
    """
    class to control microphones for streaming and recording
    """

    def __init__(self, device_id, config, first_micro=False):
        """
        Constructor method for initializing the class.

        Args:
            device_id (str): id string to identify the microphone from which this class is embedded
            config (modules.config.BirdhouseConfig): reference to main config object
        """
        threading.Thread.__init__(self)
        BirdhouseClass.__init__(self, class_id=device_id + "-main", class_log="mic-main",
                                device_id=device_id, config=config)
        self.thread_set_priority(1)

        self.count = None
        self.param = config.param["devices"]["microphones"][device_id]
        self.config.update["micro_" + self.id] = False
        self.config.update_config["micro_" + self.id] = False
        self.audio = None
        self.device = None
        self.info = None
        self.stream = None
        self.connected = False
        self.chunk = None
        self.first_micro = first_micro

        self.recording = False
        self.recording_start = False
        self.recording_processing = False
        self.recording_processing_start = False
        self.recording_filename = ""
        self.recording_default_path = os.path.join(os.path.dirname(__file__), "../../data",
                                                   birdhouse_directories["audio_temp"])
        self.recording_default_filename = "recording_" + self.id + ".wav"
        self.recording_frames = []
        self.record_start_time = None

        self.last_active = time.time()
        self.last_reload = time.time()
        self.restart_stream = False
        self.timeout = 5

        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        self.CHUNK = 1024
        self.CHUNK_default = 1024
        self.DEVICE = 2
        self.BITS_PER_SAMPLE = 16

        try:
            import lameenc
            self.encode_mp3_available = True
        except Exception as e:
            self.logging.warning("Could not import 'lameenc': encoding audio as MP3 not possible.")
            self.encode_mp3_available = False

    def run(self):
        """
        Start control audio streaming and recording
        """
        self.logging.info("Start microphone handler for '" + self.id + "' ...")
        self.connect()
        self.count = 0

        while self._running:
            self.logging.debug("Micro thread '" + self.id +
                               "' - last_active=" + str(round(time.time() - self.last_active, 2)) + "s; timeout=" +
                               str(round(self.timeout, 2)) + "s - pause=" + str(self._paused) + " - (" + str(self.count) + ")")

            # Pause if not used for a while
            if time.time() - self.last_active > self.timeout:
                self._paused = True

            if self.restart_stream:
                self._paused = False
                self.restart_stream = False

            if self.recording_start:
                self.logging.debug("Request recording for '" + self.id + "' ...")
                time.sleep(self.param["record_audio_delay"])
                self.recording = True
                self.recording_start = False

            if self.recording_processing_start:
                self.logging.debug("Request to stop recording for '" + self.id + "' ...")
                time.sleep(self.param["record_audio_delay"])
                self.recording_processing = True
                self.recording_processing_start = False

            # reconnect if config data were updated
            if self.config.update["micro_" + self.id]:
                self.logging.debug("Request reconnect for '" + self.id + "' ...")
                self.connect()
                self.config.update["micro_" + self.id] = False

            # read data from device and store in a var
            if self.connected and not self.error and not self._paused:
                try:
                    self.chunk = self.stream.read(self.CHUNK, exception_on_overflow=False)
                    self.logging.debug("Read chunk of '" + self.id + "' (" + str(len(self.chunk)) + ") ...")
                    if len(self.chunk) > 0:
                        self.count += 1
                        if self.recording:
                            self.recording_frames.append(self.chunk)

                except Exception as err:
                    self.raise_error("Could not read chunk: " + str(err))
                    self.count = 0

            else:
                self.count = 0
                time.sleep(0.1)

            # start processing if trigger is set
            if self.recording_processing:
                self.record_process()

            self.thread_control()

        try:
            if self.stream is not None:
                if not self.stream.is_stopped():
                    self.stream.stop_stream()
                self.stream.close()

        except Exception as e:
            self.logging.error("Could not stop stream: " + str(e))

        self.logging.info("Stopped microphone '" + self.id + "'.")

    def connect(self):
        """
        connect to microphone
        """
        self.reset_error()
        self.connected = False
        self.param = self.config.param["devices"]["microphones"][self.id]
        self.logging.info("AUDIO device " + self.id + " (" + str(self.param["device_id"]) + "; " +
                          self.param["device_name"] + "; " + str(self.param["sample_rate"]) + ")")

        self.CHUNK = self.CHUNK_default
        self.DEVICE = int(self.param["device_id"])

        if "sample_rate" in self.param:
            self.RATE = self.param["sample_rate"]
        if "chunk_size" in self.param:
            self.CHUNK = self.CHUNK * self.param["chunk_size"]
        if "channels" in self.param:
            self.CHANNELS = self.param["channels"]

        if self.audio is None:
            try:
                self.audio = pyaudio.PyAudio()
            except Exception as e:
                self.raise_error("Could not connect microphone '" + self.id + "': " + str(e))

        elif self.stream is not None and not self.stream.is_stopped():
            try:
                self.stream.stop_stream()
                self.stream.close()
                self.audio.terminate()
                time.sleep(1)
                self.audio = pyaudio.PyAudio()
            except Exception as e:
                self.raise_error("Could not reconnect microphone '" + self.id + "': " + str(e))

        self.info = self.audio.get_host_api_info_by_index(0)
        num_devices = self.info.get('deviceCount')

        if self.first_micro:
            self.logging.info("Identified " + str(num_devices) + " audio devices:")
            for i in range(0, num_devices):
                check = self.audio.get_device_info_by_host_api_device_index(0, i)
                is_micro = ((check.get("input") is not None and check.get("input") > 0) or
                            (check.get("maxInputChannels") is not None and check.get("maxInputChannels") > 0))
                self.logging.info(" - " + str(i).rjust(2) + ": " + check.get("name").ljust(40) + " : micro=" +
                                  str(is_micro))
                self.logging.debug(" - " + str(check))

        if not self.param["active"]:
            self.logging.info("Device '" + self.id + "' is inactive, did not connect.")
            return

        if self.DEVICE not in range(0, num_devices):
            self.raise_error("... AUDIO device '" + str(self.DEVICE) + "' not available (range: 0, " +
                             str(num_devices)+")")
            return

        self.device = self.audio.get_device_info_by_host_api_device_index(0, self.DEVICE)
        is_micro = ((self.device.get("input") is not None and self.device.get("input") > 0) or
                    (self.device.get("maxInputChannels") is not None and self.device.get("maxInputChannels") > 0))
        if not is_micro:
            self.raise_error("... AUDIO device '" + str(self.DEVICE) + "' is not a microphone / has no input (" +
                             self.device.get('name') + ")")
            return

        if self.device.get('name') != self.param["device_name"]:
            self.raise_warning("... AUDIO device '" + str(self.DEVICE) + "' not the same as expected: " +
                               self.device.get('name') + " != " + self.param["device_name"])

        try:
            self.stream = self.audio.open(format=self.FORMAT, channels=int(self.CHANNELS),
                                          rate=int(self.RATE), input=True, input_device_index=int(self.DEVICE),
                                          frames_per_buffer=self.CHUNK)
        except Exception as err:
            self.raise_error("- Could not initialize audio stream (device:" + str(self.DEVICE) + "): " + str(err))
            self.raise_error("- open: channels=" + str(self.CHANNELS) + ", rate=" + str(self.RATE) +
                             ", input_device_index=" + str(self.DEVICE) + ", frames_per_buffer=" + str(self.CHUNK))
            self.raise_error("- device: " + str(self.info))
            return

        self.connected = True
        self.last_reload = time.time()
        self.logging.info("Microphone connected: " + str(self.DEVICE) + ", " + str(self.info))

    def update_config(self):
        """
        update configuration and trigger reconnect
        """
        self.param = self.config.param["devices"]["microphones"][self.id]
        self.connect()

    def file_header(self, size=False, duration=1800):
        """
        create file header for streaming file (duration in seconds, default = 1800s / 30min)
        info: https://docs.fileformat.com/audio/wav/

        Args:
            size (bool): get data size incl. header (True) or complete header (default / False)
            duration (int): duration of audio data in seconds
        Returns:
            Any: data size incl. header or file header
        """
        datasize = duration * self.RATE * self.CHANNELS * self.BITS_PER_SAMPLE // 8
        sample_rate = int(self.RATE)
        bits_per_sample = int(self.BITS_PER_SAMPLE)
        channels = int(self.CHANNELS)

        if size:
            return datasize + 36

        o = bytes("RIFF", 'ascii')  # (4byte) Marks file as RIFF
        o += (datasize + 36).to_bytes(4, 'little')  # (4byte) File size in bytes excluding this and RIFF marker
        o += bytes("WAVE", 'ascii')  # (4byte) File type
        o += bytes("fmt ", 'ascii')  # (4byte) Format Chunk Marker
        o += (16).to_bytes(4, 'little')  # (4byte) Length of above format data
        o += (1).to_bytes(2, 'little')  # (2byte) Format type (1 - PCM)
        o += (channels).to_bytes(2, 'little')  # (2byte)
        o += (sample_rate).to_bytes(4, 'little')  # (4byte)
        o += (sample_rate * channels * bits_per_sample // 8).to_bytes(4, 'little')  # (4byte)
        o += (channels * bits_per_sample // 8).to_bytes(2, 'little')  # (2byte)
        o += (bits_per_sample).to_bytes(2, 'little')  # (2byte)
        o += bytes("data", 'ascii')  # (4byte) Data Chunk Marker
        o += (datasize).to_bytes(4, 'little')  # (4byte) Data size in bytes
        return o

    def get_device_information(self, i=None):
        """
        return device list or single device information

        Args:
            i (int): index for API device info
        Returns:
            dict: device information (id, name, maxInputChannels, maxOutputChannels, defaultSampleRate)
        """
        empty = {
            "id": None,
            "name": "none",
            "maxInputChannels": 0,
            "maxOutputChannels": 0,
            "defaultSampleRate": 0
        }

        if self.audio is None:
            return empty

        if i is None:
            return self.audio.get_host_api_info_by_index(0)
        else:
            info = self.audio.get_host_api_info_by_index(0)
            num_devices = info.get('deviceCount')
            if i in range(0, num_devices):
                return self.audio.get_device_info_by_host_api_device_index(0, i)
            else:
                return empty

    def get_chunk(self):
        """
        get chunk of data from microphone

        Returns:
            bytes: change of audio data from microphone
        """
        data = None
        self.last_active = time.time()
        self.restart_stream = True
        if self.connected and not self.error and len(self.chunk) > 0:
            data = self.chunk
        return data

    def get_first_chunk(self):
        """
        get first chunk from microphone

        Returns:
            bytes: change of audio data from microphone
        """
        self.logging.info("Start new stream ...")
        self.last_active = time.time()
        self.restart_stream = True
        data = self.file_header()
        if self.chunk is not None:
            data += self.chunk
            return data

    def get_device_status(self):
        """
        return status information
        """
        answer = {
            "active": self.param["active"],
            "active_streaming": not self._paused,
            "connected": self.connected,
            "running": self.if_running(),

            "error": self.error,
            "error_msg": self.error_msg,

            "last_reload": time.time() - self.last_reload,
            "last_active": time.time() - self.last_active
        }
        return answer

    def record_start(self, filename):
        """
        empty cache and start recording

        Args:
            filename (str): filename of audio to be recorded
        Return:
            dict: recording information
        """
        if self.recording or self.recording_start:
            self.logging.debug("Recording already ...")
            return {"filename": self.recording_filename}

        self.logging.info("Start recording '" + filename + "' ...")
        self.logging.info(" --- " + self.id + " --> " + str(time.time()) +
                          " + delay=" + str(self.param["record_audio_delay"]) + "s")

        self.restart_stream = True
        self.last_active = time.time()
        self.record_start_time = time.time()
        self.recording_frames = []
        self.recording_filename = os.path.join(str(self.recording_default_path), filename)
        self.recording_start = True
        self.config.record_audio_info = {
            "id": self.id,
            "path": self.recording_default_path,
            "file": filename,
            "sample_rate": self.RATE,
            "channels": self.CHANNELS,
            "chunk_size": self.CHUNK,
            "status": "starting",
            "stamp_start": self.last_active,
        }

        return {"filename": self.recording_filename}

    def record_stop(self):
        """
        stop recording and write to file
        inspired by https://realpython.com/playing-and-recording-sound-python/#pyaudio_1
        """
        self.recording_processing_start = True
        self.last_active = time.time()
        self.restart_stream = False
        self.logging.info("Stopping recording of '" + self.recording_filename + "' with " +
                          str(len(self.recording_frames)) + " chunks ...")

    def record_cancel(self):
        """
        stop recording and clear cache
        """
        self.logging.info("Canceled recording of audio stream (" + self.id + ").")
        self.last_active = time.time()
        self.restart_stream = False
        self.recording = False
        self.recording_processing = False
        self.recording_frames = []
        self.recording_filename = ""
        self.record_start_time = None

    def record_process(self):
        """
        write to file recorded audio data to an audio that can be integrated into the video file creation
        """
        self.recording = False
        self.recording_processing = True
        self.config.record_audio_info["status"] = "processing"

        self.logging.info(" <-- " + self.id + " --- " + str(time.time()) + " ... (" +
                          str(round(time.time() - self.record_start_time, 3)) + ")")

        self.config.record_audio_info["stamp_end"] = time.time()
        self.config.record_audio_info["length_record"] = round(time.time() - self.record_start_time, 3)

        wf = wave.open(self.recording_filename, 'wb')
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(self.audio.get_sample_size(self.FORMAT))
        wf.setframerate(self.RATE)
        wf.writeframes(b''.join(self.recording_frames))
        wf.close()

        self.config.record_audio_info["length"] = len(self.recording_frames) * self.CHUNK / self.BITS_PER_SAMPLE / float(self.RATE)
        self.config.record_audio_info["status"] = "finished"
        self.recording_frames = []
        self.logging.info("Stopped recording of '" + self.recording_filename + "'.")
        self.recording_processing = False

    def encode_mp3(self, frames, quality=7):
        """
        encode a series of frames to MP3 - should be round(RATE / CHUNK) chunks

        Args:
            frames (list): list of chunks - should be round(RATE / CHUNK)
            quality (int): quality (0..9), the higher, the lower the quality
        Returns:
            byte: encoded data
        """
        self.logging.debug("encode_mp3: " + str(len(frames)) + " ... channels=" + str(self.CHANNELS) + "; rate=" + str(self.RATE))

        encoder = lameenc.Encoder()
        encoder.set_channels(self.CHANNELS)
        #encoder.set_bit_rate(128)  # Adjust the bit rate as needed
        encoder.set_bit_rate(32)  # Adjust the bit rate as needed
        encoder.set_in_sample_rate(self.RATE)
        encoder.set_quality(quality)  # Adjust quality (0-9, default is 5)
        mp3_data = bytes()
        for frame in frames:
            mp3_data += encoder.encode(frame)
        mp3_data += encoder.flush()
        return mp3_data
