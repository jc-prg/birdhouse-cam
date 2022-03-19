import RPi.GPIO as GPIO
import modules.dht11 as dht11
import time
import threading
import logging


class mySensor(threading.Thread):

   def __init__(self, id, param, config):
       '''
       Initialize new thread and set inital parameters
       '''
       threading.Thread.__init__(self)
       self.id           = id
       self.param        = param
       self.config       = config
       self.running      = True
       self.error        = False
       self.values       = {}

       GPIO.setmode(GPIO.BCM)
       self.sensor = dht11.DHT11(pin=4)

       logging.info("Starting sensors ("+self.id+") ...")


   def run(self):
       '''
       Start recording from sensors
       '''
       while (self.running and not self.error):
         try:
           indoor = self.sensor.read()
           if indoor.is_valid():
             self.values["temperature"] = indoor.temperature
             self.values["humidity"]    = indoor.humidity
             logging.debug("Temperature: " + str(indoor.temperature))
             logging.debug("Humidity:    " + str(indoor.humidity))
           else:
             logging.warning("Could not read data from sensor '"+self.id+"'")
         except Exception as e:
           logging.warning("Error reading data from sensor '"+self.id+"'")
           
         time.sleep(1)
       
       logging.info("Stopped sensors ("+self.id+").")


   def stop(self):
       '''
       Stop sensors
       '''
       GPIO.cleanup()
       self.running = False


