#!/usr/bin/python

import RPi.GPIO as GPIO
import modules.dht11 as dht11

GPIO.setmode(GPIO.BCM)
sensor = dht11.DHT11(pin=4)

indoor = sensor.read()
if indoor.is_valid():
    print("Temperatur: "  + str(indoor.temperature))
    print("Luftfeuchtigkeit: " + str(indoor.humidity))

GPIO.cleanup()
