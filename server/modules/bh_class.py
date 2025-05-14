import os
import threading
import time
import logging
from random import random
from modules.presets import *
from modules.presets import birdhouse_log_as_file


class BirdhouseClass(object):
    """
    Main class for camera classes: error messaging, logging and global vars
    """

    def __init__(self, class_id, class_log="", device_id="", config=None):
        """
        Constructor for this class

        Args:
            class_id (str): class id
            class_log (str): string for logging message to identify messages from this class (max. 10 characters)
            device_id (str): device id
            config (modules.config.BirdhouseConfig): reference to main config handler
        """
        if class_log == "":
            class_log = class_id
        if device_id == "":
            device_id = class_id
        if config == "":
            config = None

        self.id = device_id
        self.name = class_id
        self.class_id = class_id

        self._running = True
        self._paused = False
        self._processing = False
        self._thread_priority = 3                      # range 0..4 (1..5 via self.threat_set_priority)
        self._thread_waiting_times = [0.2, 0.5, 1, 2, 4, 8, 15, 30, 55, 115]  # to be used depending on priority
        self._thread_slowdown = False
        self._health_check = time.time()

        self.error = False
        self.error_msg = []
        self.error_time = None
        self.error_count = 0
        self.error_connect = False
        self.error_timeout = 60*5

        self.config = None
        if config is not None:
            self.config = config
            self.thread_register(init=True)

        self.logging = set_logging(class_log, device_id)

    def stop(self):
        """
        Stop if thread (set self._running = False)
        """
        self.logging.debug("STOP SIGNAL SEND FROM SOMEWHERE ...")
        self._running = False
        self._processing = False

    def raise_error(self, message, connect=False):
        """
        Report Error, set variables of modules

        Args:
            message (str): error message
            connect (bool): set True if it's a connection error / fatal error
        """
        if connect:
            self.error_connect = True

        message_org = message
        message_repeat = message + " !! repeated"

        time_info = self.config.local_time().strftime('%d.%m.%Y %H:%M:%S')

        message_exists = False
        for error in self.error_msg:
            if message_org in error:
                message_exists = True
        if message_exists:
            message = message_repeat

        self.error_msg.append(time_info + " - " + message)
        self.error_count += 1
        if len(self.error_msg) >= 20:
            self.error_msg.pop(0)

        self.error_time = time.time()
        self.error = True

        message_exists = 0
        for error in self.error_msg:
            if message_repeat in error:
                message_exists += 1

        if message_exists < 2:
            self.logging.error("[" + str(self.error_count).zfill(4) + "] " + self.id + ": " + message)

    def raise_warning(self, message):
        """
        Show warning message

        Args:
            message (str): warning message
        """
        self.logging.warning(self.id + ": " + message)

    def reset_error(self):
        """
        Reset all error variables
        """
        self.error = False
        self.error_msg = []
        self.error_time = 0
        self.error_count = 0
        self.error_connect = False

    def reset_error_check(self, error_timeout=-1):
        """
        Check if last error has been before x seconds and reset error status, if older

        Args:
            error_timeout (float): waiting time until error gets reset, if not set default value is used
        """
        if error_timeout == -1:
            error_timeout = self.error_timeout
        if self.error_time + error_timeout < time.time():
            self.reset_error()

    def health_signal(self):
        """
        Set var that can be requested
        """
        self._health_check = time.time()
        self.thread_register()

    def health_status(self):
        """
        return time sind last heath signal

        Returns:
            float: time since last health signal in seconds
        """
        return round(time.time() - self._health_check, 2)

    def thread_wait(self, wait_time=-1):
        """
        Wait depending on priority or wait_time set in parameters.

        Args:
            wait_time (float): possibility to overwrite waiting time set through priority.
        """
        start = time.time()
        if wait_time == -1:
            wait = self._thread_waiting_times[self._thread_priority]
            if self._thread_slowdown:
                wait = wait * 3

            while start + wait > time.time() and not self.if_shutdown():
                time.sleep(0.05)
        else:
            while start + wait_time > time.time() and not self.if_shutdown():
                time.sleep(0.01)

    def thread_set_priority(self, priority):
        """
        Set priority which results in different waiting times for the thread -> def run(); self.thread_wait()

        Args:
            priority (int): set priority
        """
        priorities = len(self._thread_waiting_times)
        if 0 <= int(priority) < priorities:
            self._thread_priority = priority
        else:
            self.raise_warning("Could not priority, out of range (0.."+str(priorities-1)+"): " + str(priority))

    def thread_prio_process(self, start, pid):
        """
        Set central info that prio process is running

        Args:
            start (bool): starting process
            pid (str): process id
        """
        self.config.thread_ctrl["priority"] = {
            "process": start,
            "pid": pid
        }

    def if_other_prio_process(self, pid):
        """
        check if prio process with other ID

        Args:
            pid (str): process id
        Returns:
            bool: if other process has priority
        """
        priority = self.config.thread_ctrl["priority"]
        if priority["process"] and priority["pid"] != pid:
            return True
        else:
            return False

    def thread_register_process(self, pid, name, status, progress):
        """
        Register progress in config vars (status: start, running, finished, remove; progres 0..1)

        Args:
            pid (str): process id
            name (str): name of the process
            status (str): status of the process
            progress (float): progress of the process
        """
        process_info = {
            "id": pid,
            "name": name,
            "start": time.time(),
            "status": "start",
            "progress": 0
        }
        process_id = pid
        if process_id in self.config.thread_status[self.class_id]["processes"]:
            process_info = self.config.thread_status[self.class_id]["processes"].copy()

        if status != "remove":
            process_info["status"] = status
            process_info["progress"] = progress
            process_info["update"] = time.time()
            self.config.thread_status[self.class_id]["processes"][process_id] = process_info
        else:
            del self.config.thread_status[self.class_id]["processes"][process_id]

    def thread_register(self, init=False):
        """
        Register instance of class in config

        Args:
            init (bool): set to True for first registration of an instance, else update
        """
        if self.config is None:
            return

        elif init:
            self.config.thread_status[self.class_id] = {
                "id": self.class_id,
                "pid_1": "",
                "pid_2": "",
                "device": self.id,
                "thread": False,
                "priority": self._thread_priority,
                "wait_time": self._thread_waiting_times[self._thread_priority],
                "processes": {},
                "status": {
                    "health_signal": time.time(),
                    "running": True,
                    "processing": False,
                    "paused": False,
                    "error": False,
                    "error_msg": []
                },
            }
            try:
                self.config.thread_status[self.class_id]["pid_1"] = threading.get_ident()
                self.config.thread_status[self.class_id]["pid_2"] = threading.get_native_id()
            except Exception as e:
                self.logging.debug("... " +str(e))
        else:
            self.config.thread_status[self.class_id]["thread"] = True
            self.config.thread_status[self.class_id]["priority"] = self._thread_priority
            self.config.thread_status[self.class_id]["wait_time"] = self._thread_waiting_times[self._thread_priority]
            self.config.thread_status[self.class_id]["status"] = {
                "health_signal": time.time(),
                "running": self.if_running(),
                "processing": self.if_processing(),
                "paused": self.if_paused(),
                "error": self.if_error(),
                "error_msg": self.if_error(message=True)
            }

    def thread_control(self):
        """
        Central thread functionality, check if central shutdown signal is available and trigger all threads to stop
        """
        self.health_signal()
        if self.config is not None and self.config.thread_ctrl["shutdown"]:
            self.thread_set_priority(1)
            self.stop()

    def thread_slowdown(self, slowdown=True):
        """
        Set var to increase or decrease waiting time for the thread

        Args:
            slowdown (bool): increase waiting time if True, decrease if False
        """
        self._thread_slowdown = slowdown

    def if_running(self):
        """
        External check if running

        Returns:
            bool: Status if thread is running
        """
        return self._running

    def if_paused(self):
        """
        External check if paused

        Returns:
            bool: Status if thread is paused
        """
        return self._paused

    def if_processing(self):
        """
        External check if paused

        Returns:
            bool: Status if processing is ongoing
        """
        return self._processing

    def if_error(self, message=False, length=False, count=False):
        """
        External check if error

        Args:
            message (bool): return error message(s)
            length (bool): return amount of error messages (if not message=True)
            count (bool): return amount of errors (if not message=True and not length=True)
        Returns:
            Any: requested value
        """
        if message:
            return self.error_msg
        elif length:
            return len(self.error_msg)
        elif count:
            return self.error_count
        else:
            return self.error

    def if_shutdown(self):
        """
        Check if shutdown is requested

        Returns:
            bool: Status if shutdown signal is set
        """
        if self.config is not None:
            return self.config.thread_ctrl["shutdown"]
        else:
            return False


class BirdhouseCameraClass(BirdhouseClass):
    """
    Extension of BirdhouseClass that extracts camera specific parameters to self.param and defines timezone
    """

    def __init__(self, class_id, class_log="", camera_id="", config=None):
        """
        Constructor of this class.

        Args:
            class_id (str): class id
            class_log (str): string for logging message to identify messages from this class (max. 10 characters)
            camera_id (str): device id
            config (modules.config.BirdhouseConfig): reference to main config handler
        """
        BirdhouseClass.__init__(self, class_id, class_log, camera_id, config)
        if "devices" in self.config.param and "cameras" in self.config.param["devices"] \
                and self.id in self.config.param["devices"]["cameras"]:
            self.param = self.config.param["devices"]["cameras"][self.id]

        self.timezone = 0
        if "localization" in self.config.param and "timezone" in self.config.param["localization"]:
            self.timezone = float(self.config.param["localization"]["timezone"].replace("UTC", ""))
            self.logging.debug("Set Timezone: " + self.config.param["localization"]["timezone"] +
                               " (" + str(self.timezone) + " / " + self.config.local_time().strftime("%H:%M") + ")")


class BirdhouseDbClass(BirdhouseClass):
    """
    Main class for database classes.
    """

    def __init__(self, class_id, class_log, config):
        """
        Constructor of this class

        Args:
            class_id (str): class id
            class_log (str): string to identify messages of this class in logging
            config (modules.config.BirdhouseConfig): reference to main config handler
        """
        BirdhouseClass.__init__(self, class_id, class_log, "", config)
        self.locked = {}
        self.waiting_time = 0

    def lock(self, filename):
        """
        lock config file

        Args:
            filename (str): filename / db name of database to be locked
        """
        self.locked[filename] = True

    def unlock(self, filename):
        """
        unlock config file

        Args:
            filename (str): filename / db name of database to be unlocked
        """
        self.locked[filename] = False

    def amount_locked(self):
        """
        Return if a files are locked for writing

        Returns:
            int: amount of locked files
        """
        count = 0
        for key in self.locked:
            if self.locked[key]:
                count += 1
        return count

    def wait_if_locked(self, filename):
        """
        Wait, while a file is locked for writing

        Args:
            filename (str): filename / db name of database - if locked, wait
        """
        wait = 0.05
        count = 0
        self.logging.debug("Start check locked: " + filename + " ...")

        if filename in self.locked and self.locked[filename]:
            while self.locked[filename]:
                self.waiting_time += wait
                time.sleep(wait)
                count += 1
                if count > 100:
                    self.logging.warning("Waiting! File '" + filename + "' is locked (" + str(count) + ")")
                    count = 0

        elif filename == "ALL":
            self.logging.info("Wait until no file is locked ...")
            locked = len(self.locked.keys())
            while locked > 0:
                locked = 0
                for key in self.locked:
                    if self.locked[key]:
                        locked += 1
                self.waiting_time += wait
                time.sleep(wait)

            self.logging.info("OK")

        return "OK"
