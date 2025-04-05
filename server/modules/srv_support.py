import threading
import time
import psutil
import subprocess
import os
import gc

from modules.bh_class import BirdhouseClass
from modules.bh_database import BirdhouseTEXT
from modules.presets import *


class ServerHealthCheck(threading.Thread, BirdhouseClass):

    def __init__(self, config, server, maintain=False):
        self.server = server
        self._shutdown_signal_file = "/tmp/birdhouse-cam-shutdown"
        self._wait_till_start = 60
        if not maintain:
            threading.Thread.__init__(self)
            BirdhouseClass.__init__(self, class_id="srv-health", config=config)
            self.thread_set_priority(5)

            self._initial = True
            self._interval_check = 60 * 5
            self._min_live_time = 65
            self._thread_info = {}
            self._health_status = None
            self._text_files = BirdhouseTEXT()
            self.set_shutdown(False)
            self.set_restart(False)
        else:
            self._running = False
            self._text_files = BirdhouseTEXT()

    def run(self):
        self.logging.info("Starting Server Health Check ...")
        count = 0
        last_update = time.time()
        while self._running:
            self.thread_wait()
            self.thread_control()

            if self.config.thread_ctrl["shutdown"]:
                time.sleep(5)
                self.config.shut_down = False
                self.logging.info("FINALLY KILLING ALL PROCESSES NOW!")
                self.server.server_close()
                self.server.shutdown()
                return

            if last_update + self._interval_check < time.time():
                self.logging.info("Health check ...")
                last_update = time.time()
                count += 1

                self._thread_info = {}
                for key in self.config.thread_status:
                    if self.config.thread_status[key]["thread"]:
                        self._thread_info[key] = time.time() - self.config.thread_status[key]["status"]["health_signal"]

                if self._initial:
                    self._initial = False
                    self.logging.info("... checking the following threads: " + str(self._thread_info.keys()))

                problem = []
                for key in self._thread_info:
                    if self._thread_info[key] > self._min_live_time:
                        problem.append(key + " (" + str(round(self._thread_info[key], 1)) + "s)")

                if len(problem) > 0:
                    self.logging.warning(
                        "... not all threads are running as expected: ")
                    self.logging.warning("  -> " + ", ".join(problem))
                    self._health_status = "NOT RUNNING: " + ", ".join(problem)
                else:
                    self.logging.info("... OK.")
                    self._health_status = "OK"

            if self.check_shutdown():
                self.logging.info("SHUTDOWN SIGNAL send from outside.")
                self.set_shutdown(False)
                self.config.force_shutdown()

            if self.check_restart():
                self.logging.info("RESTART SIGNAL detected - shutdown and set START signal (requires check via crontab)")
                self.set_start()
                self.config.force_shutdown()

            if count == 4:
                count = 0
                self.logging.info("Live sign health check!")

        self.logging.info("Stopped Server Health Check.")

    def status(self):
        return self._health_status

    def check_restart(self):
        """
        check if external shutdown signal has been set
        """
        if os.path.exists(self._shutdown_signal_file):
            content = self._text_files.read(self._shutdown_signal_file)
            if "REBOOT" in content:
                return True
        return False

    def set_restart(self, restart=True):
        """
        set external shutdown signal ...
        """
        if restart:
            self._text_files.write(self._shutdown_signal_file, "REBOOT")
            print("Restart requested ...")
        else:
            self._text_files.write(self._shutdown_signal_file, "")

    def check_start(self):
        """
        check if external shutdown signal has been set
        """
        if os.path.exists(self._shutdown_signal_file):
            content = self._text_files.read(self._shutdown_signal_file)
            if "START" in content:
                print("START signal received ... waiting " + str(self._wait_till_start) + "s before starting birdhouse server.")
                self._text_files.write(self._shutdown_signal_file, "")
                time.sleep(self._wait_till_start)
                print("Starting ...")
                return True
        print("Check: no START signal present (file="+str(os.path.exists(self._shutdown_signal_file))+").")
        return False

    def set_start(self, restart=True):
        """
        set external shutdown signal ...
        """
        if restart:
            self._text_files.write(self._shutdown_signal_file, "START")
        else:
            self._text_files.write(self._shutdown_signal_file, "")

    def check_shutdown(self):
        """
        check if external shutdown signal has been set
        """
        if os.path.exists(self._shutdown_signal_file):
            content = self._text_files.read(self._shutdown_signal_file)
            if "SHUTDOWN" in content:
                return True
        return False

    def set_shutdown(self, shutdown=True):
        """
        set external shutdown signal ...
        """
        if shutdown:
            self._text_files.write(self._shutdown_signal_file, "SHUTDOWN")
        else:
            self._text_files.write(self._shutdown_signal_file, "")


class ServerInformation(threading.Thread, BirdhouseClass):

    def __init__(self, initial_camera_scan, config_handler, camera_handler, sensor_handler,
                 microphone_handler, relay_handler, statistics):
        """
        Constructor of the class

        Args:
            initial_camera_scan (dict): information of camera scan
            config_handler (modules.config.BirdhouseConfig): reference to config handler
            camera_handler (dict): list of camera handlers
            sensor_handler (dict): list of sensor handlers
            microphone_handler (dict): list of microphone handlers
            statistics (modules.statistics.BirdhouseStatistics): reference to statistic handler
        """
        threading.Thread.__init__(self)
        BirdhouseClass.__init__(self, class_id="srv-info", config=config_handler)
        self.thread_set_priority(4)

        self._system_status = {}
        self._device_status = {
            "cameras": {},
            "sensors": {},
            "microphones": {},
            "relays": {},
            "available": {}
        }
        self._srv_info_time = 0
        self.initial_camera_scan = initial_camera_scan

        self.camera = camera_handler
        self.microphone = microphone_handler
        self.sensor = sensor_handler
        self.statistics = statistics
        self.relays = relay_handler
        self.main_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
        self.main_dir = birdhouse_main_directories["project"]

        self.disk_usage_interval = 10 * 60
        self.disk_usage_cache = {}
        self.disk_usage_last = 0

        self.statistics.register("srv_cpu", "CPU Usage")
        self.statistics.register("srv_cpu_temp", "CPU Temperature")
        self.statistics.register("srv_hdd_percentage", "HDD Used [%]")
        self.statistics.register("srv_hdd_used", "HDD Used [GB]")
        self.statistics.register("srv_hdd_data", "HDD Data [GB]")

    def run(self):
        """
        Running thread to continuously update server information in the background and
        trigger a garbage collection from time to time.
        """
        count = 0
        self.logging.info("Starting Server Information ...")
        while self._running:
            start_time = time.time()
            self.read_memory_usage()
            self.read_disk_usage()
            self.read_device_status()
            self.read_available_devices()

            self._srv_info_time = round(time.time() - start_time, 2)
            self.config.set_processing_performance("server", "srv_support", start_time)

            count += 1
            if count == 10:
                self.logging.info("Garbage collection ...")
                count = 0
                gc.collect()

            self.thread_control()
            self.thread_wait()

        self.logging.info("Stopped Server Information.")

    def read_memory_usage(self):
        """
        Get data for current memory , to be requested via .get().
        """
        system = {}
        try:
            # cpu information
            system["cpu_usage"] = psutil.cpu_percent(interval=1, percpu=False)
            system["cpu_usage_detail"] = psutil.cpu_percent(interval=1, percpu=True)
            system["mem_total"] = psutil.virtual_memory().total / 1024 / 1024
            system["mem_used"] = psutil.virtual_memory().used / 1024 / 1024
            mem_process = psutil.Process(os.getpid()).memory_info()
            system["mem_process"] = mem_process.rss / 1024 / 1024

        except Exception as err:
            system = {
                "cpu_usage": -1,
                "cpu_usage_detail": -1,
                "mem_total": -1,
                "mem_used": -1,
            }

        system["system_info_interval"] = self._srv_info_time

        # Initialize the result.
        result = -1
        # The first line in this file holds the CPU temperature as an integer times 1000.
        # Read the first line and remove the newline character at the end of the string.
        if os.path.isfile('/sys/class/thermal/thermal_zone0/temp'):
            with open('/sys/class/thermal/thermal_zone0/temp') as f:
                line = f.readline().strip()
            # Test if the string is an integer as expected.
            if line.isdigit():
                # Convert the string with the CPU temperature to a float in degrees Celsius.
                result = float(line) / 1000
        # Give the result back to the caller.
        system["cpu_temperature"] = result

        self.statistics.set(key="srv_cpu", value=system["cpu_usage"])
        self.statistics.set(key="srv_cpu_temp", value=system["cpu_temperature"])

        for key in system:
            self._system_status[key] = system[key]

    def read_disk_usage(self):
        """
        read disk usage from linux command from time to time, interval defined in self.disk_usage_interval,
        and write data to statistics module
        """
        if self.disk_usage_cache == {} or self.disk_usage_last + self.disk_usage_interval < time.time():
            self.logging.debug("... disk usage cache expired ...")
            self.disk_usage_last = time.time()

            system = {}
            try:
                # diskusage
                hdd = psutil.disk_usage("/")
                system["hdd_used"] = hdd.used / 1024 / 1024 / 1024
                system["hdd_total"] = hdd.total / 1024 / 1024 / 1024
            except Exception as err:
                system = {"hdd_used": -1, "hdd_total": -1}

            try:
                cmd_data = ["du", "-hs", os.path.join(self.main_dir, "data")]
                temp_data = str(subprocess.check_output(cmd_data))
                temp_data = temp_data.replace("b'", "")
                temp_data = temp_data.split("\\t")[0]
                if "k" in temp_data:
                    system["hdd_data"] = float(temp_data.replace("k", "")) / 1024 / 1024
                elif "M" in temp_data:
                    system["hdd_data"] = float(temp_data.replace("M", "")) / 1024
                elif "G" in temp_data:
                    system["hdd_data"] = float(temp_data.replace("G", ""))
            except Exception as e:
                system["hdd_data"] = -1
                self.logging.warning("Was not able to get size of data dir: " + (str(cmd_data)) + " - " + str(e))
            self.disk_usage_cache = system.copy()
        else:
            self.logging.debug("... disk usage cache still valid ...")
            system = self.disk_usage_cache.copy()

        for key in system:
            self._system_status[key] = system[key]

        self.statistics.set(key="srv_hdd_percentage", value=round((system["hdd_used"]/system["hdd_total"]), 3))
        self.statistics.set(key="srv_hdd_used", value=round(system["hdd_used"], 3))
        self.statistics.set(key="srv_hdd_data", value=round(system["hdd_data"], 3))

    def read_available_devices(self):
        """
        Identify which video and audio devices are available on the system, to be requested via .get_device_status().
        """
        system = {}

        process = subprocess.Popen(["v4l2-ctl --list-devices"], stdout=subprocess.PIPE, shell=True)
        output = process.communicate()[0]
        output = output.decode()
        output_2 = output.split("\n")

        last_key = "none"
        if birdhouse_env["rpi_active"]:
            output_2.append("PiCamera:")
            output_2.append("/dev/picam")

        system["video_devices"] = {}
        system["video_devices_short"] = {}
        system["video_devices_complete"] = self.initial_camera_scan["video_devices_complete"]

#       -> use values from self.initial_camera_scan!

        for value in self.initial_camera_scan["video_devices_complete"]:

            check = self.initial_camera_scan["video_devices_complete"][value]
            check_text = ""
            if birdhouse_env["test_video_devices"]:
                if check["image"]:
                    check_text = "OK: "
                else:
                    check_text = "ERROR: "

            system["video_devices_short"][value] = check_text + value + " (" + check["info"] + " | " + check["bus"] + ")"

        system["audio_devices"] = {}
        if self.microphone != {}:
            first_mic = list(self.microphone.keys())[0]
            info = self.microphone[first_mic].get_device_information()
            self.logging.debug("... mic-info: " + str(info))

            if 'deviceCount' in info:
                num_devices = info['deviceCount']
                for i in range(0, num_devices):
                    dev_info = self.microphone["mic1"].get_device_information(i)
                    if (dev_info.get('maxInputChannels')) > 0:
                        name = dev_info.get('name')
                        info = dev_info
                        self.logging.debug("... mic-info: " + str(info))
                        system["audio_devices"][name] = {
                            "id": i,
                            "input": info.get("maxInputChannels"),
                            "output": info.get("maxOutputChannels"),
                            "sample_rate": info.get("defaultSampleRate")
                        }

        self.logging.debug("... mic-info: " + str(system["audio_devices"]))
        self._device_status["available"] = system

    def read_device_status(self):
        """
        Get device data ever x seconds for a faster API response
        """
        # get microphone data and create streaming information
        for key in self.microphone:
            self._device_status["microphones"][key] = self.microphone[key].get_device_status()

        for key in self.relays:
            self._device_status["relays"][key] = self.relays[key].is_on()

        # get camera data and create streaming information
        for key in self.camera:
            self._device_status["cameras"][key] = self.camera[key].get_camera_status()

        # get sensor data
        for key in self.sensor:
            self._device_status["sensors"][key] = self.sensor[key].get_status()

    def get(self):
        """
        Get server data which are updated continuously in the background.
        """
        return self._system_status

    def get_device_status(self):
        """
        Get device data which are updated continuously in the background.
        """
        return self._device_status

