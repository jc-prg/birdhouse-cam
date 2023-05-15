import time
import logging

from modules.presets import *


class BirdhouseClass(object):
    """
    Main class for camera classes: error messaging, logging and global vars
    """

    def __init__(self, class_id, class_log="", device_id="", config=""):

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
        self._thread_priority = 3  # range 0..3
        self._thread_waiting_times = [1, 2, 4, 8, 16]  # to be used depending priority
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

        self.logging = logging.getLogger(class_id)
        if class_log not in birdhouse_loglevel_module:
            self.logging.setLevel(logging.INFO)
            self.logging.error("Key '" + class_id + "' is not defined in preset.py in 'birdhouse_loglevel_module'.")
        else:
            self.logging.setLevel(birdhouse_loglevel_module[class_log])
        self.logging.addHandler(birdhouse_loghandler)

    def stop(self):
        """
        stop if thread (set self._running = False)
        """
        self._running = False
        self._processing = False

    def raise_error(self, message, connect=False):
        """
        Report Error, set variables of modules
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
        show warning message
        """
        self.logging.warning(self.id + ": " + message)

    def reset_error(self):
        """
        remove all errors
        """
        self.error = False
        self.error_msg = []
        self.error_time = 0
        self.error_count = 0
        self.error_connect = False

    def reset_error_check(self, error_timeout=-1):
        """
        check if last error has been before x seconds and reset error status, if older
        """
        if error_timeout == -1:
            error_timeout = self.error_timeout
        if self.error_time + error_timeout < time.time():
            self.reset_error()

    def health_signal(self):
        """
        set var that can be requested
        """
        self._health_check = time.time()
        self.thread_register()

    def health_status(self):
        """
        return time sind last heath signal
        """
        return round(time.time() - self._health_check, 2)

    def thread_wait(self):
        """
        wait depending on priority
        """
        time.sleep(self._thread_waiting_times[self._thread_priority])

    def thread_set_priority(self, priority):
        """
        set priority
        """
        if 1 <= int(priority) <= 5:
            self._thread_priority = priority - 1
        else:
            self.raise_warning("Could not priority, out of range (0..5): " + str(priority))

    def thread_register(self, init=False):
        """
        register class in config
        """
        if self.config is None:
            return

        elif init:
            self.config.thread_status[self.class_id] = {
                "id": self.class_id,
                "device": self.id,
                "thread": False,
                "priority": self._thread_priority,
                "wait_time": self._thread_waiting_times[self._thread_priority],
                "status": {
                    "health_signal": time.time(),
                    "running": self.if_running(),
                    "processing": self.if_processing(),
                    "paused": self.if_paused(),
                    "error": self.if_error(),
                    "error_msg": self.if_error(message=True)
                },
            }
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

    def if_running(self):
        """
        external check if running
        """
        return self._running

    def if_paused(self):
        """
        external check if paused
        """
        return self._paused

    def if_processing(self):
        """
        external check if paused
        """
        return self._processing

    def if_error(self, message=False, length=False, count=False):
        """
        external check if error
        """
        if message:
            return self.error_msg
        elif length:
            return len(self.error_msg)
        elif count:
            return self.error_count
        else:
            return self.error


class BirdhouseCameraClass(BirdhouseClass):

    def __init__(self, class_id, class_log, camera_id, config):
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

    def __init__(self, class_id, class_log, config):
        BirdhouseClass.__init__(self, class_id, class_log, "", config)
        self.locked = {}

    def lock(self, filename):
        """
        lock config file
        """
        self.locked[filename] = True

    def unlock(self, filename):
        """
        unlock config file
        """
        self.locked[filename] = False

    def wait_if_locked(self, filename):
        """
        wait, while a file is locked for writing
        """
        wait = 0.2
        count = 0
        self.logging.debug("Start check locked: " + filename + " ...")

        if filename in self.locked and self.locked[filename]:
            while self.locked[filename]:
                time.sleep(wait)
                count += 1
                if count > 10:
                    self.logging.warning("Waiting! File '" + filename + "' is locked (" + str(count) + ")")
                    time.sleep(1)

        elif filename == "ALL":
            self.logging.info("Wait until no file is locked ...")
            locked = len(self.locked.keys())
            while locked > 0:
                locked = 0
                for key in self.locked:
                    if self.locked[key]:
                        locked += 1
                time.sleep(wait)
            self.logging.info("OK")
        if count > 10:
            self.logging.warning("File '" + filename + "' is not locked any more (" + str(count) + ")")
        return "OK"
