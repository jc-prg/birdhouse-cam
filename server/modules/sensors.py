import time
import threading
import logging
from datetime import datetime
from modules.presets import *


try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    error_module = False
    error_module_msg = ""
except Exception as e:
    error_module = True
    error_module_msg = "Couldn't load module RPi.GPIO: "+str(e)


class BirdhouseSensor(threading.Thread):

    def __init__(self, sensor_id, param, config):
        """
        Initialize new thread and set inital parameters
        """
        threading.Thread.__init__(self)
        self.id = sensor_id
        self.config = config

        self.logging = logging.getLogger("sensors")
        self.logging.setLevel(birdhouse_loglevel_module["sensors"])
        self.logging.addHandler(birdhouse_loghandler)
        self.logging.info("Starting sensor control for '"+sensor_id+"' ...")

        self.config.update["sensor_"+self.id] = False
        self.param = self.config.param["devices"]["sensors"][sensor_id]
        self.active = self.param["active"]
        self.running = True
        self._paused = False
        self.health_check = time.time()

        self.GPIO = None
        self.sensor = None

        self.error = False
        self.error_module = error_module
        self.error_connect = False
        self.error_msg = []
        self.pin = self.param["pin"]
        self.values = {}
        self.last_read = 0
        self.last_read_time = time.time()
        self.interval = 10
        self.interval_reconnect = 60
        self.initial_load = True

        if not error_module:
            self.connect()

        else:
            self.logging.error(error_module_msg)
            self.logging.error("- Requires Raspberry and installation of this module.")
            self.logging.error("- To install module, try 'sudo apt-get -y install rpi.gpio'.")
            self.error_connect = True
            self.error_msg = self.config.local_time().strftime('%d.%m.%Y %H:%M:%S')
            self.error_msg += " - " + error_module_msg
            self.running = False

    def run(self):
        """
        Start recording from sensors
        """
        count = 0
        retry = 0
        retry_wait = 10
        self.logging.info("- Starting sensor loop (" + self.id + "/" + str(self.pin) + "/"+self.param["type"]+") ...")
        while self.running:
            p_count = 0
            count += 1

            # if shutdown
            if self.config.shut_down:
                self.stop()

            # wait if paused
            while self._paused:
                if p_count == 0:
                    self.logging.info("Pause sensor "+self.id+" ...")
                    p_count += 1
                time.sleep(1)

            # check if configuration update
            if self.config.update["sensor_"+self.id]:
                self.logging.info("....... RELOAD Update: Reread coonfiguration sensor: " + self.id)
                self.param = self.config.param["devices"]["sensors"][self.id]
                self.config.update["sensor_"+self.id] = False
                self.active = self.param["active"]

            # reconnect if error and active
            if self.error_connect and self.param["active"]:
                retry += 1
                if retry > retry_wait:
                    self.logging.info("....... RELOAD Error: Retry starting sensor: "+self.id)
                    self.connect()
                    retry = 0

            # if longer time no correct data read, reconnect
            if self.last_read_time + self.interval_reconnect < time.time():
                retry = retry_wait
                self.error_connect = True

            # read data
            if count >= self.interval and self.param["active"]:
                count = 0
                try:
                    if self.param["type"] == "dht11":
                        indoor = self.sensor.read()
                        if indoor.is_valid():
                            self.values["temperature"] = indoor.temperature
                            self.values["humidity"] = indoor.humidity
                            self.last_read = self.config.local_time().strftime('%d.%m.%Y %H:%M:%S')
                            self.last_read_time = time.time()
                            self.logging.debug("Temperature: " + str(indoor.temperature))
                            self.logging.debug("Humidity:    " + str(indoor.humidity))
                        else:
                            raise Exception("Not valid ("+str(indoor.is_valid())+")")
                        if self.values == {}:
                            raise Exception("Returned empty values.")

                    elif self.param["type"] == "dht22":
                        self.values["temperature"] = self.sensor.temperature
                        self.values["humidity"] = self.sensor.humidity
                        self.last_read = self.config.local_time().strftime('%d.%m.%Y %H:%M:%S')
                        self.last_read_time = time.time()
                        self.logging.debug("Temperature: " + str(self.sensor.temperature))
                        self.logging.debug("Humidity:    " + str(self.sensor.humidity))

                    self._reset_error()

                except Exception as e:
                    if self.last_read_time + self.interval_reconnect < time.time():
                        self._raise_error(connect=False, message="Error reading data from sensor: " + str(e))

                if self.values == {}:
                    self._raise_error(connect=False, message="Returned empty values.")

                if not self.error:
                    self.last_read = self.config.local_time().strftime('%d.%m.%Y %H:%M:%S')
                    self.last_read_time = time.time()

            self.health_check = time.time()
            time.sleep(1)

        # GPIO.cleanup()
        self.logging.info("Stopped sensor (" + self.id + "/"+self.param["type"]+").")

    def stop(self):
        """
        Stop sensors
        """
        self.running = False

    def _raise_error(self, connect, message):
        """
        raise error
        """
        if connect:
            self.error_connect = True
        self.error = True
        error_message = self.config.local_time().strftime('%d.%m.%Y %H:%M:%S')
        error_message += " - " + message
        self.error_msg.append(error_message)
        if len(self.error_msg) >= 5:
            self.error_msg.pop()
        self.logging.error(message)

    def _reset_error(self):
        """
        reset error values
        """
        self.error = False
        self.error_connect = False
        self.error_msg = []

    def connect(self):
        """
        connect with sensor
        """
        temp = ""
        self.error = False
        self.error_connect = False
        if "rpi_active" in self.config.param["server"] and self.config.param["server"]["rpi_active"]:
            try:
                if self.param["type"] == "dht11":
                    if self.initial_load:
                        import modules.dht11 as dht11
                        self.initial_load = False
                    self.sensor = dht11.DHT11(pin=self.pin)
                elif self.param["type"] == "dht22":
                    if self.initial_load:
                        import board
                        import adafruit_dht
                        self.initial_load = False
                    ada_pin = eval("board.D"+str(self.pin))
                    self.sensor = adafruit_dht.DHT22(ada_pin, use_pulseio=False)
                else:
                    raise "Sensor type not supported"
            except Exception as e:
                self._raise_error(connect=True, message="Could not load " + self.param["type"] +
                                                        " sensor module: " + str(e))
                return

            try:
                if self.param["type"] == "dht11":
                    indoor = self.sensor.read()
                    if indoor.is_valid():
                        temp = "Temp: {:.1f} C; Humidity: {}% ".format(indoor.temperature, indoor.humidity)
                    else:
                        temp = "error"

                elif self.param["type"] == "dht22":
                    temperature_c = self.sensor.temperature
                    temperature_f = temperature_c * (9 / 5) + 32
                    humidity = self.sensor.humidity
                    temp = "Temp: {:.1f} F / {:.1f} C; Humidity: {}% ".format(temperature_f, temperature_c, humidity)

                self._reset_error()

            except Exception as e:
                self._raise_error(connect=False, message="Initial load "+self.param["type"]+" not OK: "+str(e))
                return

            if not self.error:
                self.logging.info("Loaded Sensor: "+self.id)
                self.logging.info("- Initial values: "+str(temp))

        else:
            self._raise_error(connect=True, message="No sensor available: requires Raspberry Pi / activate" +
                                                    " 'rpi_active' in config file.")

    def pause(self, value):
        """
        pause sensor measurement
        """
        self._paused = value

    def get_values(self):
        """
        get values from all sensors
        """
        return self.values.copy()

    def get_status(self):
        """
        return all error status information
        """
        error = {
            "running": self.running,
            "last_read": time.time() - self.last_read_time,
            "error": self.error,
            "error_msg": self.error_msg,
            "error_module": self.error_module,
            "error_connect": self.error_connect
            }
        return error

