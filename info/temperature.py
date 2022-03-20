#!/usr/bin/python

import RPi.GPIO as GPIO
import modules.dht11 as dht11
import time

GPIO.setmode(GPIO.BCM)
sensor = dht11.DHT11(pin=4)

while True:
  indoor = sensor.read()
  if indoor.is_valid():
    print("Temperatur: "  + str(indoor.temperature))
    print("Luftfeuchtigkeit: " + str(indoor.humidity))
  time.sleep(1)

GPIO.cleanup()
