#!/usr/bin/python3

import io, os, time
import logging
import numpy as np
import string

import picamera
import imutils, cv2
from imutils.video import WebcamVideoStream
from imutils.video import FPS
from skimage.metrics import structural_similarity as ssim

import threading
from threading       import Condition
from datetime        import datetime


#----------------------------------------------------

class myCameraOutput(object):

    def __init__(self):
        self.frame     = None
        self.buffer    = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # New frame, copy the existing buffer's content and notify all
            # clients it's available
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)

#----------------------------------------------------


class myCamera(threading.Thread):

   def __init__(self, id, type, record, param, config):
       '''
       Initialize new thread and set inital parameters
       '''
       threading.Thread.__init__(self)
       self.id        = id
       self.param     = param
       self.name      = param["name"]
       self.active    = param["active"]
       self.config    = config
       self.type      = type
       self.record    = record
       self.running   = True
       self.error     = False

       logging.info("Starting camera ("+self.type+"/"+self.name+") ...")

       if self.type == "pi":
         try:
            self.camera            = picamera.PiCamera()
            self.output            = myCameraOutput()
            self.camera.resolution = param["image"]["resolution"]
            self.camera.framerate  = param["image"]["framerate"]
            self.camera.rotation   = param["image"]["rotation"]
            self.camera.saturation = param["image"]["saturation"]
            self.camera.zoom       = param["image"]["crop"]
            self.camera.annotate_background = picamera.Color('black')
            self.camera.start_recording(self.output, format='mjpeg')
            logging.info("OK.")

         except Exception as e:
            self.error  = True
            self.active = False
            logging.error("Starting PiCamera doesn't work!")

       elif type == "usb":
         try:
            #cap                    = cv2.VideoCapture(0) # check if camera is available
            #if cap is None or not cap.isOpened(): raise
            self.camera            = WebcamVideoStream(src=0).start()
            self.cameraFPS         = FPS().start()

            #self.camera.stream.set(cv2.CAP_PROP_FRAME_WIDTH, cvsettings.CAMERA_WIDTH)

            logging.info("OK.")

         except Exception as e:
            self.error  = True
            self.active = False
            logging.error("Starting USB camera doesn't work!\n" +str(e))

       else:
          self.error  = True
          self.active = False
          logging.error("Unknown type of camera!")

       self.previous_image    = None
       self.previous_stamp    = "000000"

   #----------------------------------

   def run(self):
       '''
       Start recording for livestream and save images every x seconds
       '''
       similarity = 0
       logging.debug("HOURS:   "+str(self.param["image_save"]["hours"]))
       logging.debug("SECONDS: "+str(self.param["image_save"]["seconds"]))

       while (self.running and not self.error):
          time.sleep(1)
          seconds = datetime.now().strftime('%S')
          hours   = datetime.now().strftime('%H')
          stamp   = datetime.now().strftime('%H%M%S')

          if self.record:

            if (seconds in self.param["image_save"]["seconds"]) and (hours in self.param["image_save"]["hours"]):
               text  = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
               self.setText(text)

               image         = self.getImage()
               image         = self.convertImage2RawImage(image)
               image_compare = self.convertRawImage2Gray(image)

               if self.previous_image is not None:
                  similarity = str(self.compareRawImages(imageA=image_compare, imageB=self.previous_image, detection_area=self.param["similarity"]["detection_area"]))

               image_info = {
                          "camera"      : self.id,
                          "hires"       : self.config.imageName("hires",  stamp, self.id),
                          "lowres"      : self.config.imageName("lowres", stamp, self.id),
                          "compare"     : (stamp,self.previous_stamp),
                          "datestamp"   : datetime.now().strftime("%Y%m%d"),
                          "date"        : datetime.now().strftime("%d.%m.%Y"),
                          "time"        : datetime.now().strftime("%H:%M:%S"),
                          "similarity"  : similarity
                          }

               pathLowres = os.path.join(self.config.param["path"], self.param["image_save"]["path"], self.config.imageName("lowres", stamp, self.id))
               pathHires  = os.path.join(self.config.param["path"], self.param["image_save"]["path"], self.config.imageName("hires",  stamp, self.id))

               logging.debug("WRITE:" +pathLowres)

               self.writeImageInfo(time=stamp, data=image_info)
               self.writeImage(filename=pathHires,  image=image)
               self.writeImage(filename=pathLowres, image=image, scale_percent=self.param["preview_scale"])

               self.previous_image = image_compare
               self.previous_stamp = stamp


   def wait(self):
       '''
       Wait with recording between two pictures
       '''
       if self.type == "pi":  self.camera.wait_recording(0.1)
       if self.type == "usb": time.sleep(0.1)


   def stop(self):
       '''
       Stop recording
       '''
       logging.info("Stopping camera ("+self.type+") ...")
       self.running = False
       time.sleep(1)

       if self.type == "pi":
          self.camera.stop_recording()
          self.camera.close()

       elif self.type == "usb":
          self.camera.stop()
          self.cameraFPS.stop()


   #----------------------------------

   def setText(self,text):
       '''
       Add / replace text on the image
       '''
       if self.type == "pi":
          self.camera.annotate_text = str(text)


   def setText2Image(self,image,text):
       '''
       Add text on image
       '''
       font      = cv2.FONT_HERSHEY_SIMPLEX
       fontScale = 0.8
       org       = (30,40)
       color     = (120,120,120)
       thickness = 2
       image     = cv2.putText(image, text, org, font, fontScale, color, thickness, cv2.LINE_AA)
       return image

   #----------------------------------

   def getImage(self):
       '''
       read image from device
       '''
       if self.type == "pi":
         with self.output.condition:
           self.output.condition.wait()
           raw = self.output.frame

       elif self.type == "usb":
           raw = self.camera.read()   ## potentially not the same RAW as fram PI
           raw = self.normalizeImage(raw)
           r, buf = cv2.imencode(".jpg",raw)
           size   = len(buf)
           raw    = bytearray(buf)

       else:
           logging.error("Camera type not supported ("+str(self.type)+").")

       return raw


   def normalizeImage(self, image, color="", compare=False):
       '''
       apply presets per camera to image
       '''
       if self.type == "usb":
          # crop image
          if not "crop_area" in self.param["image"]:  normalized, self.param["image"]["crop_area"] = self.cropRawImage(frame=image, crop_area=self.param["image"]["crop"],      type="relative")
          else:                                       normalized, self.param["image"]["crop_area"] = self.cropRawImage(frame=image, crop_area=self.param["image"]["crop_area"], type="pixel")
          # rotate     - not implemented yet
          # resize     - not implemented yet
          # saturation - not implemented yet
       else:
          normalized = image

       return normalized


   def convertRawImage2Image(self, raw):
       '''
       convert from raw image to image // untested
       '''
       try:
         r, buf = cv2.imencode(".jpg", raw)
         size   = len(buf)
         image  = bytearray(buf)

       except Exception as e:
         logging.error("Error convert RAW image -> image: "+str(e))

       return image


   def convertImage2RawImage(self, image):
       '''
       convert from device to raw image -> to be modifeid with CV2
       '''
       try:
         image = np.frombuffer(image, dtype=np.uint8)
         image = cv2.imdecode(image, 1)
         return image

       except Exception as e:
         logging.error("Error convert image -> RAW image: "+str(e))


   def convertRawImage2Gray(self, image):
       '''
       convert image from RGB to gray scale image (e.g. for analyzing similarity)
       '''
       return cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)

   #----------------------------------

   def drawImageDetectionArea(self, image):
       '''
       Draw a red rectangle into the image to show detection area
       '''
       image = self.convertImage2RawImage(image)
       image = self.drawRawImageDetectionArea(image)
       image = self.convertRawImage2Image(image)
       return image


   def drawRawImageDetectionArea(self, image):
       '''
       Draw a red rectangle into the image to show detection area
       '''
       color     = (0, 0, 255) # color in BGR
       thickness = 5
       height    = image.shape[0]
       width     = image.shape[1]

       (w_start, h_start, w_end, h_end) = self.param["similarity"]["detection_area"]
       x_start   = int(round(width  * w_start, 0))
       y_start   = int(round(height * h_start, 0))
       x_end     = int(round(width  * w_end,   0))
       y_end     = int(round(height * h_end,   0))

       logging.debug(self.id +": show detection area ... "+str(self.param["similarity"]["detection_area"]))

       image     = cv2.line(image, (x_start,y_start), (x_start, x_end), color, thickness)
       image     = cv2.line(image, (x_start,y_start), (x_end, y_start), color, thickness)
       image     = cv2.line(image, (x_end,y_end),     (x_start, y_end), color, thickness)
       image     = cv2.line(image, (x_end,y_end),     (x_end, y_start), color, thickness)

       return image

   #----------------------------------

   def cropRawImage(self, frame, crop_area, type="relative"):
       '''
       crop image using relative dimensions (0.0 ... 1.0)
       '''
       try:
         height = frame.shape[0]
         width  = frame.shape[1]

         if type == "relative":
           (w_start, h_start, w_end, h_end) = crop_area
           x_start   = int(round(width  * w_start, 0))
           y_start   = int(round(height * h_start, 0))
           x_end     = int(round(width  * w_end,   0))
           y_end     = int(round(height * h_end,   0))
           crop_area = (x_start,y_start,x_end,y_end)
         else:
           (x_start,y_start,x_end,y_end) = crop_area

         logging.debug("H: "+str(y_start)+"-"+str(y_end)+" / W: "+str(x_start)+"-"+str(x_end))
         frame_cropped  = frame[y_start:y_end, x_start:x_end]
         return frame_cropped, crop_area

       except Exception as e:
         logging.warning("Could not crop image: "+str(e))

       return frame, (0,0,1,1)


   #----------------------------------

   def compareImages(self, imageA, imageB, detection_area=None):
       '''
       calculate structual similarity index (SSIM) of two images
       '''
       imageA     = self.convertImage2RawImage(imageA)
       imageB     = self.convertImage2RawImage(imageB)
       similarity = self.compareRawImages(imageA, imageB, detection_area)
       return similarity


   def compareRawImages(self, imageA, imageB, detection_area=None):
       '''
       calculate structual similarity index (SSIM) of two images
       '''
       if detection_area != None:
          logging.debug(self.id +"/compare 1: "+str(detection_area)+" / "+str(imageA.shape))
          imageA, area = self.cropRawImage(frame=imageA, crop_area=detection_area, type="relative")
          imageB, area = self.cropRawImage(frame=imageB, crop_area=detection_area, type="relative")
          logging.debug(self.id +"/compare 2: "+str(area)+" / "+str(imageA.shape))

       try:
          (score, diff) = ssim(imageA, imageB, full=True)

       except Exception as e:
          logging.warning("Error comparing images: ", str(e))
          score = 0

       return round(score*100,1)


   #----------------------------------

   def selectImage(self, timestamp, file_info):
       '''
       check image properties to decide if image is a selected one (for backup and view with selected images)
       '''
       if not "similarity" in file_info:                                    return False

       if ("camera" in file_info and file_info["camera"] == self.id) or (not "camera" in file_info and self.id == "cam1"):

          if "to_be_deleted" in file_info:
             delete    = int(file_info["to_be_deleted"])
             if delete == 1:                                                return False

          threshold  = float(self.param["similarity"]["threshold"])
          similarity = float(file_info["similarity"])

          if "00"+str(self.param["image_save"]["seconds"][0]) in timestamp: return True
          if similarity != 0 and similarity < threshold:                    return True

          if "favorit" in file_info:
             favorit    = int(file_info["favorit"])
             if favorit == 1:                                               return True

       return False


   def writeImage(self,filename,image,scale_percent=100):
       '''
       Scale image and write to file
       '''
       if scale_percent != 100:
          width  = int(image.shape[1] * scale_percent / 100)
          height = int(image.shape[0] * scale_percent / 100)
          image  = cv2.resize(image, (width,height))

       return cv2.imwrite(os.path.join(self.config.param["path"],filename),image)


   def writeImageInfo(self, time, data):
       '''
       Write image information to file
       '''
       if os.path.isfile(self.config.file("images")):
          files = self.config.read("images")
          files[time] = data
          self.config.write("images",files)


#----------------------------------------------------
