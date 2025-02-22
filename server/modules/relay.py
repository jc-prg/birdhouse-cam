import time

from modules.bh_class import BirdhouseClass

try:
    import RPi.GPIO as GPIO
    loaded_gpio = True
except Exception as e:
    loaded_gpio = False
    error_module = True
    error_module_msg = "Couldn't load module RPi.GPIO: " + str(e)


class BirdhouseRelay(BirdhouseClass):

    def __init__(self, relay_id, config):
        """
        Constructor method for initializing a relay, e.g. to switch on and off IR light for the camera.

        Args:
            relay_id (str): id string to identify the relay
            config (modules.config.BirdhouseConfig): reference to main config object
        """
        BirdhouseClass.__init__(self, "RELAY", "relay", relay_id, config)

        self.relay = None
        self.gpio_loaded = loaded_gpio
        self.state = "STARTED"

        self.param = self.config.param["devices"]["relays"][relay_id]
        self.active = self.param["active"]
        self.pin = self.param["pin"]

    def start(self):
        """
        setup GPIO (use BCM GPIO numbering)
        """
        self.logging.info("Initializing relay control ...")
        if self.gpio_loaded and self.active:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.pin, GPIO.OUT, initial=GPIO.LOW)
            self.logging.info("... Loaded GPIO")
        elif not self.active:
            self.logging.warning("... GPIO module not loaded: relay " + self.id + " is inactive.")
        else:
            self.logging.warning("... GPIO module not loaded: " + error_module_msg)

    def stop(self):
        """
        cleanup / unload GPIO
        """
        if self.gpio_loaded and self.active:
            GPIO.cleanup()
            self.logging.info("Stopped GPIO for relay control.")

    def switch_on(self):
        """
        use relay to switch connected device on
        """
        if self.gpio_loaded and self.active:
            GPIO.output(self.pin, GPIO.HIGH)
            self.state = "ON"
            self.logging.info("Switch ON: " + str(self.pin))

    def switch_off(self):
        """
        use relay to switch connected device of
        """
        if self.gpio_loaded and self.active:
            GPIO.output(self.pin, GPIO.LOW)
            self.state = "OFF"
            self.logging.info("Switch OFF: " + str(self.pin))

    def is_started(self):
        """
        check if relay is set to STARTED

        Returns:
            boolean: relay state
        """
        return self.state == "STARTED"

    def is_on(self):
        """
        check if relay is set to ON

        Returns:
            boolean: relay state
        """
        return self.state == "ON"

    def test(self):
        """
        test by switching on and off
        """
        if self.gpio_loaded and self.active:
            time_wait = 2
            self.switch_on()
            time.sleep(time_wait)
            self.switch_off()
            self.logging.info("Relay test done.")
        else:
            self.logging.warning("GPIO not loaded")
