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
        self.running = True
        self.error = False
        self.pin = self.param["pin"]
        self.values = {}
        self.last_read = 0
        self.interval = 10

        try:
            import RPi.GPIO as GPIO
        except Exception as e:
            logging.error("Sensors: Couldn't load module RPi.GPIO. Requires Raspberry and installation of this module.")
            logging.error("To install module, try 'sudo apt-get -y install rpi.gpio'.")
            self.error = True
            self.running = False
            return
        try:
            import modules.dht11 as dht11
            GPIO.setmode(GPIO.BCM)
            self.sensor = dht11.DHT11(pin=self.pin)
        except Exception as e:
            logging.error("Could not load DHT11 sensor module.")
            self.error = True
            self.running = False
            return

        logging.info("Starting sensors (" + self.id + "/" + str(self.pin) + ") ...")

    def run(self):
        """
        Start recording from sensors
        """
        count = 0
        while self.running and not self.error:

            if self.config.update["sensor_"+self.id]:
                self.param = self.config.param["devices"]["sensors"][self.id]
                self.config.update["sensor_"+self.id] = False

            count += 1
            if count == self.interval:
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
                except Exception as e:
                    logging.warning("Error reading data from sensor '" + self.id + "': "+str(e))
                count = 0
            elif self.running:
                time.sleep(0.5)

        logging.info("Stopped sensors (" + self.id + ").")

    def stop(self):
        """
        Stop sensors
        """
        GPIO.cleanup()
        self.running = False

    def get_values(self):
        """
        get values from all sensors
        """
        return self.values.copy()
