import RPi.GPIO as GPIO
import modules.dht11 as dht11
import time
from datetime import datetime
import threading
import logging


class mySensor(threading.Thread):

    def __init__(self, sensor_id, param, config):
        """
        Initialize new thread and set inital parameters
        """
        threading.Thread.__init__(self)
        self.id = sensor_id
        self.param = param
        self.config = config
        self.running = True
        self.error = False
        self.pin = self.param["pin"]
        self.values = {}
        self.last_read = 0

        GPIO.setmode(GPIO.BCM)
        self.sensor = dht11.DHT11(pin=self.pin)

        logging.info("Starting sensors (" + self.id + "/" + str(self.pin) + ") ...")

    def run(self):
        """
        Start recording from sensors
        """
        while self.running and not self.error:
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

            time.sleep(10)

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
