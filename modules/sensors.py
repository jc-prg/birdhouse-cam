import RPi.GPIO as GPIO
import modules.dht11 as dht11
import time
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
        self.pin = 4
        self.values = {}

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
                    logging.debug("Temperature: " + str(indoor.temperature))
                    logging.debug("Humidity:    " + str(indoor.humidity))
                else:
                    logging.warning("Could not read data from sensor '" + self.id + "': " + str(indoor.error_code))
            except Exception as e:
                logging.warning("Error reading data from sensor '" + self.id + "'")

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
        return self.values
