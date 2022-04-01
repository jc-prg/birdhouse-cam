import time
import threading
import logging
from datetime import datetime


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
        self.config.update["sensor_"+self.id] = False
        self.param = self.config.param["devices"]["sensors"][sensor_id]
        self.active = self.param["active"]
        self.running = True

        self.GPIO = None
        self.sensor = None

        self.error = False
        self.error_connect = False
        self.error_msg = ""
        self.pin = self.param["pin"]
        self.values = {}
        self.last_read = 0
        self.interval = 10

        if not error_module:
            self.connect()
        else:
            logging.error(error_module_msg)
            logging.error("- Requires Raspberry and installation of this module.")
            logging.error("- To install module, try 'sudo apt-get -y install rpi.gpio'.")
            self.error_connect = True
            self.error_msg = error_module_msg
            self.running = False

    def run(self):
        """
        Start recording from sensors
        """
        count = 0
        retry = 0
        retry_wait = 120
        logging.info("- Starting sensor loop (" + self.id + "/" + str(self.pin) + ") ...")
        while self.running:
            time.sleep(1)

            if self.config.update["sensor_"+self.id]:
                self.param = self.config.param["devices"]["sensors"][self.id]
                self.config.update["sensor_"+self.id] = False
                self.active = self.param["active"]

            count += 1
            if self.error_connect and self.param["active"]:
                retry += 1
                if retry > retry_wait:
                    logging.info("Retry starting sensor: "+self.id)
                    self.connect()
                    retry = 0
            elif count >= self.interval and self.param["active"]:
                try:
                    indoor = self.sensor.read()
                    if indoor.is_valid():
                        self.values["temperature"] = indoor.temperature
                        self.values["humidity"] = indoor.humidity
                        self.last_read = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
                        logging.debug("Temperature: " + str(indoor.temperature))
                        logging.debug("Humidity:    " + str(indoor.humidity))
                    else:
                        raise Exception("Not valid ("+str(indoor.is_valid())+")")
                    self.error = False
                    self.error_msg = ""
                except Exception as e:
                    self.error = True
                    self.error_msg = "Error reading data from sensor: "+str(e)
                    logging.warning("Error reading data from sensor '" + self.id + "': "+str(e))
                count = 0

        # GPIO.cleanup()
        logging.info("Stopped sensor (" + self.id + ").")

    def connect(self):
        """
        connect with sensor
        """
        temp = ""
        if "rpi_active" in self.config.param["server"] and self.config.param["server"]["rpi_active"]:
            try:
                import modules.dht11 as dht11
                self.sensor = dht11.DHT11(pin=self.pin)
                indoor = self.sensor.read()
                if indoor.is_valid():
                    temp = indoor.temperature
                else:
                    temp = "error"
                self.error = False
                self.error_connect = False
                self.error_msg = ""
            except Exception as e:
                self.error = True
                self.error_connect = True
                self.error_msg = "Could not load DHT11 sensor module: "+str(e)
                logging.error(self.error_msg)
            if not self.error:
                logging.info("Loaded Sensor: "+self.id)
                logging.info("- Initial temperature: "+str(temp))
        else:
            self.error = True
            self.error_connect = True
            self.error_msg = "No sensor available: requires Raspberry Pi / activate 'rpi_active' in config file."
            logging.info(self.error_msg)

    def stop(self):
        """
        Stop sensors
        """
        self.running = False

    def get_values(self):
        """
        get values from all sensors
        """
        return self.values.copy()
