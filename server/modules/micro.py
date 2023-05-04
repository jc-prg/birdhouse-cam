import pyaudio
import threading
import time
from modules.presets import *
from modules.bh_class import BirdhouseClass


class BirdhouseMicrophone(threading.Thread, BirdhouseClass):

    def __init__(self, device_id, config):
        """
        Initialize new thread and set initial parameters
        """
        threading.Thread.__init__(self)
        BirdhouseClass.__init__(self, class_id=device_id + "-main", class_log="mic-main",
                                device_id=device_id, config=config)

        self.count = None
        self.param = config.param["devices"]["microphones"][device_id]
        self.audio = None
        self.device = None
        self.info = None
        self.stream = None
        self.connected = False
        self.chunk = None

        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        self.CHUNK = 1024
        self.DEVICE = 2
        self.BITS_PER_SAMPLE = 16

    def run(self):
        """
        Stream
        """
        self.logging.info("Start microphone handler for '" + self.id + "' ...")
        self.connect()
        self.count = 0

        while self._running:
            self.health_signal()

            if not self.error and self.connected:
                try:
                    self.chunk = self.stream.read(self.CHUNK, exception_on_overflow=False)
                    if len(self.chunk) > 0:
                        self.count += 1

                except Exception as err:
                    self.raise_error("Could not read chunk: " + str(err))
                    self.count = 0

            else:
                self.count = 0
                time.sleep(1)

        if not self.stream.is_stopped():
            self.stream.stop_stream()
        self.stream.close()
        self.logging.info("Stopped microphone '" + self.id + "'.")

    def stop(self):
        """
        stop thread by stopping loop
        """
        self._running = False

    def connect(self):
        """
        connect to microphone
        """
        self.reset_error()
        self.logging.info("AUDIO device " + self.id + " (" + str(self.param["device_id"]) + "; " +
                          self.param["device_name"] + "; " + str(self.param["sample_rate"]) + ")")

        self.DEVICE = int(self.param["device_id"])
        self.RATE = self.param["sample_rate"]
        self.CHUNK = self.CHUNK * self.param["chunk_size"]

        if self.audio is None:
            self.audio = pyaudio.PyAudio()
        elif not self.stream.is_stopped():
            self.stream.stop_stream()

        self.info = self.audio.get_host_api_info_by_index(0)
        num_devices = self.info.get('deviceCount')
        for i in range(0, num_devices):
            self.logging.info(" - " + str(i) + " - " +
                              str(self.audio.get_device_info_by_host_api_device_index(0, i).get('name')))

        if self.DEVICE not in range(0, num_devices):
            self.raise_error("... AUDIO device '" + str(self.DEVICE) + "' not available (range: 0, " +
                             str(num_devices)+")")
            return

        self.device = self.audio.get_device_info_by_host_api_device_index(0, self.DEVICE)
        if self.device.get('input') == 0:
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
        self.logging.info("Microphone connected.")

    def file_header(self):
        """
        create file header for streaming file
        """
        datasize = 2000 * 10 ** 6
        sample_rate = int(self.RATE)
        bits_per_sample = int(self.BITS_PER_SAMPLE)
        channels = int(self.CHANNELS)

        #datasize = samples * channels * bits_per_sample // 8
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
        """
        if i is None:
            return self.audio.get_host_api_info_by_index(0)
        else:
            return self.audio.get_device_info_by_host_api_device_index(0, i)

    def get_chunk(self):
        data = None
        if self.connected and not self.error and len(self.chunk) > 0:
            data = self.chunk
        return data

    def get_first_chunk(self):
        self.logging.info("Start new stream ...")
        data = self.file_header()
        data += self.chunk
        return data
