#!/usr/bin/python3

import RPi.GPIO as GPIO
import dht22.dht22 as dht22
import time
import datetime

# initialize GPIO
GPIO.setwarnings(True)
GPIO.setmode(GPIO.BCM)

# read data using pin 14
instance = dht22.DHT22(pin=10)

print("Start DHT22 Check ...")

try:
    while True:
        print(".")
        result = instance.read()
        if result.is_valid():
            print("Last valid input: " + str(datetime.datetime.now()))
            print("Temperature: %-3.1f C" % result.temperature)
            print("Humidity: %-3.1f %%" % result.humidity)
            time.sleep(5)

except KeyboardInterrupt:
    print("Cleanup")
    GPIO.cleanup()

