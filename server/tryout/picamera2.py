import cv2
from picamera2 import Picamera2

stream = Picamera2()
config = stream.create_still_configuration({"size": (1152, 864)})
print(str(config))
config = stream.create_still_configuration(main={"size": (1296, 972)})
print(str(config))
config = stream.create_still_configuration(raw=None)
print(str(config))
config["main"]["size"] = (1292, 972)

stream.configure(config)
stream.still_configuration.main.size = (1292, 972)
stream.start()

image = stream.switch_mode_and_capture_array(config, "main")
image = stream.capture_array()
cv2.imwrite("/tmp/test.jpg", image)

stream.stop()
print(str(image.shape))
print(stream.still_configuration.main.size)
print("OK")
