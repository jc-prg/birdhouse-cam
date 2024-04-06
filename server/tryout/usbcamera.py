import cv2

source = "/dev/video0"

stream = cv2.VideoCapture(source, cv2.CAP_V4L)
stream.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))

if not stream.isOpened():
    print("- Can't connect to camera '" + source + "': not isOpen()")
    exit()

ref, image = stream.read()
check = str(type(image))
if "NoneType" in check or len(image) == 0:
    print("Connected, but returned empty image.")

cv2.imwrite("/tmp/test.jpg", image)

print(str(image.shape))
print("OK")


