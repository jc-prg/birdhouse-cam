import time
from datetime import datetime
import threading
import logging


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
        self.error = False
        self.error_connect = False
        self.error_msg = ""
        self.pin = self.param["pin"]
        self.values = {}
        self.last_read = 0
        self.interval = 10
        self.connect()

    def run(self):
        """
        Start recording from sensors
        """
        count = 0
        retry = 0
        retry_wait = 120
        logging.info("Starting sensors (" + self.id + "/" + str(self.pin) + ") ...")
        while self.running:

            if self.config.update["sensor_"+self.id]:
                self.param = self.config.param["devices"]["sensors"][self.id]
                self.config.update["sensor_"+self.id] = False
                self.active = self.param["active"]

            count += 1
            if not self.error and self.active and count >= self.interval and self.param["active"]:
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
            elif self.error:
                retry += 1
                if retry > retry_wait:
                    logging.info("Retry starting sensor: "+self.id)
                    self.connect()
                    retry = 0
            elif self.running:
                time.sleep(0.5)

        logging.info("Stopped sensors (" + self.id + ").")

    def connect(self):
        """
        connect with sensor
        """
        try:
            import RPi.GPIO as GPIO
            self.error = False
            self.error_connect = False
            self.error_msg = ""
            logging.info("Load GPIO for Sensor:"+self.id)
        except Exception as e:
            logging.error("Sensors: Couldn't load module RPi.GPIO. Requires Raspberry and installation of this module.")
            logging.error("To install module, try 'sudo apt-get -y install rpi.gpio'.")
            logging.error(str(e))
            self.error = True
            self.error_connect = True
            self.error_msg = "Couldn't load module RPi.GPIO: "+str(e)
            self.running = False
            return
        try:
            import modules.dht11 as dht11
            GPIO.setmode(GPIO.BCM)
            self.sensor = dht11.DHT11(pin=self.pin)
            self.error = False
            self.error_connect = False
            self.error_msg = ""
            logging.info("Load Sensor:"+self.id)
        except Exception as e:
            logging.error("Could not load DHT11 sensor module: "+str(e))
            self.error = True
            self.error_connect = True
            self.error_msg = "Could not load DHT11 sensor module: "+str(e)
            self.running = False

    def stop(self):
        """
        Stop sensors
        """
        if not self.error and GPIO:
            GPIO.cleanup()
        self.running = False

    def get_values(self):
        """
        get values from all sensors
        """
        return self.values.copy()
