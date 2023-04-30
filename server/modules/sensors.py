import time
import threading
import logging
from modules.presets import *
from modules.bh_class import BirdhouseClass

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    error_module = False
    error_module_msg = ""
except Exception as e:
    error_module = True
    error_module_msg = "Couldn't load module RPi.GPIO: "+str(e)


class BirdhouseSensor(threading.Thread, BirdhouseClass):

    def __init__(self, sensor_id, config):
        """
        Initialize new thread and set inital parameters
        """
        threading.Thread.__init__(self)
        BirdhouseClass.__init__(self, "SENSORS", "sensors", sensor_id, config)

        self.config.update["sensor_"+self.id] = False
        self.param = self.config.param["devices"]["sensors"][sensor_id]
        self.active = self.param["active"]

        self._running = True
        self._paused = False

        self.GPIO = None
        self.sensor = None

        self.error_module = error_module
        self.error_connect = False

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

        self.logging.info("Starting sensor control for '"+sensor_id+"' ...")

    def run(self):
        """
        Start recording from sensors
        """
        count = 0
        retry = 0
        retry_wait = 20
        self.logging.info("- Starting sensor loop (" + self.id + "/" + str(self.pin) + "/"+self.param["type"]+") ...")
        while self._running:
            p_count = 0
            count += 1

            # if shutdown
            if self.config.shut_down:
                self.stop()

            # wait if paused
            while self._paused and self._running:
                if p_count == 0:
                    self.logging.info("Pause sensor "+self.id+" ...")
                    p_count += 1
                time.sleep(1)

            # check if configuration update
            if self.config.update["sensor_"+self.id]:
                self.logging.info("....... Reload SENSOR '"+self.id+"' after update: Reread configuration.")
                self.param = self.config.param["devices"]["sensors"][self.id]
                self.config.update["sensor_"+self.id] = False
                self.active = self.param["active"]

            # reconnect if error and active
            if self.error_connect and self.param["active"]:
                self.logging.info("....... Reload SENSOR '"+self.id+"' due to errors.")
                self.connect()
                self.error_connect = False

            # if longer time no correct data read, reconnect
            if self.last_read_time + self.interval_reconnect < time.time():
                self.error_connect = True
                self.last_read_time = time.time()

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

                    self.reset_error()

                except Exception as e:
                    if self.last_read_time + self.interval_reconnect < time.time():
                        self.raise_error(connect=False, message="Error reading data from sensor: " + str(e))

                if self.values == {}:
                    self.raise_error(connect=False, message="Returned empty values.")

                if not self.error:
                    self.last_read = self.config.local_time().strftime('%d.%m.%Y %H:%M:%S')
                    self.last_read_time = time.time()

            self.health_signal()
            time.sleep(1)

        # GPIO.cleanup()
        self.logging.info("Stopped sensor (" + self.id + "/"+self.param["type"]+").")

    def stop(self):
        """
        Stop sensors
        """
        self._running = False

    def connect(self):
        """
        connect with sensor
        """
        temp = ""
        self.reset_error()
        self.error_connect = False

        if birdhouse_env["rpi_active"]:
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
                self.raise_error(message="Could not load " + self.param["type"] + " sensor module: " + str(e),
                                 connect=True)
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

                self.reset_error()

            except Exception as e:
                self.raise_error(message="Initial load " + self.param["type"] + " not OK: " + str(e),
                                 connect=False)
                return

            if not self.error:
                self.logging.info("Loaded Sensor: "+self.id)
                self.logging.info("- Initial values: "+str(temp))
            self.raise_error(message="No sensor available: requires Raspberry Pi / activate" +
                                     " 'rpi_active' in config file.", connect=True)

        else:
            pass

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
            "running": self._running,
            "rpi_active": birdhouse_env["rpi_active"],
            "last_read": time.time() - self.last_read_time,
            "error": self.error,
            "error_msg": self.error_msg,
            "error_module": self.error_module,
            "error_connect": self.error_connect
            }
        return error
