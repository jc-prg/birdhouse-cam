#!/usr/bin/python3

import io, os, time
import logging
import numpy as np
import string

import imutils, cv2
from imutils.video import WebcamVideoStream
from imutils.video import FPS
from skimage.metrics import structural_similarity as ssim

import threading
from threading       import Condition
from datetime        import datetime


#----------------------------------------------------


class myVideoRecording(threading.Thread):

   def __init__(self, camera, param, directory):
       '''
       Initialize new thread and set inital parameters
       '''
       threading.Thread.__init__(self)
       self.camera       = camera
       self.name         = param["name"]
       self.param        = param
       self.recording    = False
       self.processing   = False
       self.directory    = directory
       self.max_length   = 0.25*60
       self.info         = {}
       self.ffmpeg_cmd   = "ffmpeg -f image2 -r {FRAMERATE} -i {INPUT_FILENAMES} "
       self.ffmpeg_cmd  += "-vcodec libx264 -crf 18"
       
# Other working options:
#       self.ffmpeg_cmd  += "-b 1000k -strict -2 -vcodec libx264 -profile:v main -level 3.1 -preset medium -x264-params ref=4 -movflags +faststart -crf 18"
#       self.ffmpeg_cmd  += "-c:v libx264 -pix_fmt yuv420p"
#       self.ffmpeg_cmd  += "-profile:v baseline -level 3.0 -crf 18"
#       self.ffmpeg_cmd  += "-vcodec libx264 -preset fast -profile:v baseline -lossless 1 -vf \"scale=720:540,setsar=1,pad=720:540:0:0\" -acodec aac -ac 2 -ar 22050 -ab 48k"
       
       self.ffmpeg_cmd  += " {OUTPUT_FILENAME}"
       self.count_length = 8

   #----------------------------------
   
   def run(self):
       '''
       Initialize, set inital values
       '''
       logging.info("Initialize video recording ...")
       self.info = {
         "start"       : 0,
         "start_stamp" : 0,
         "status"      : "ready"
         }
       if "video" in self.param and "max_length" in self.param["video"]:
          self.max_length = self.param["video"]["max_length"]
          logging.debug("Set max video recording length for " + self.camera + " to " + str(self.max_length))
       else:
          logging.debug("Use default max video recording length for " + self.camera + " = " + str(self.max_length))
       return

   
   def start_recording(self):
       '''
       Start recording
       '''
       logging.info("Starting video recording ...")
       self.recording            = True
       self.info["date"]         = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
       self.info["date_start"]   = datetime.now().strftime('%Y%m%d_%H%M%S')
       self.info["stamp_start"]  = datetime.now().timestamp()
       self.info["status"]       = "recording"
       self.info["camera"]       = self.camera
       self.info["camera_name"]  = self.name
       self.info["directory"]    = self.directory
       self.info["image_count"]  = 0
       return

       
   def stop_recording(self):
       '''
       Stop recording and trigger video creation
       '''
       logging.info("Stopping video recording ...")
       self.recording         = False
       self.info["date_end"]  = datetime.now().strftime('%Y%m%d_%H%M%S')
       self.info["stamp_end"] = datetime.now().timestamp()
       self.info["status"]    = "processing"
       self.info["length"]    = round(self.info["stamp_end"] - self.info["stamp_start"],1)
       if float(self.info["length"]) > 1:
          self.info["framerate"] = round(float(self.info["image_count"]) / float(self.info["length"]), 1)
       else:
          self.info["framerate"] = 0
       
       self.create_video()

       self.info["status"]    = "finished"

       if not self.config.exists("videos"):  config_file = {}
       else:                                 config_file = self.config.read_cache("videos")
       config_file[self.info["date_start"]] = self.info
       self.config.write("videos",config_file)           
       
       time.sleep(1)
       self.info = {}
       return
       
      
   def info_recording(self):
       '''
       Get info of recording
       '''
       if self.recording:    self.info["length"] = round(datetime.now().timestamp() - self.info["stamp_start"],1)
       elif self.processing: self.info["length"] = round(self.info["stamp_end"] - self.info["stamp_start"],1)
       
       self.info["image_size"]   = self.image_size

       if float(self.info["length"]) > 1: self.info["framerate"] = round(float(self.info["image_count"]) / float(self.info["length"]), 1)
       else:                              self.info["framerate"] = 0
       
       return self.info


   def autostop(self):
       '''
       Check if maximum length is achieved
       '''
       if self.info["status"] == "recording":
          max_time = float(self.info["stamp_start"] + self.max_length) 
          if max_time < float(datetime.now().timestamp()):
             logging.info("Maximum recording time achieved ...")
             logging.info(str(max_time) + " < " + str(datetime.now().timestamp()))
             return True
       return False


   def status(self):
       '''
       Return recording status
       '''
       return self.record_video_info


   def save_image(self, image):
       '''
       Save image
       '''
       self.info["image_count"] += 1
       self.info["image_files"] = self.filename("vimages")
       self.info["video_file"]  = self.filename("video")
       filename = self.info["image_files"] + str(self.info["image_count"]).zfill(self.count_length) + ".jpg"
       path     = os.path.join(self.directory, filename)
       logging.debug("Save image as: " + path)

       return cv2.imwrite(path, image)

       
   def filename(self, ftype="image"):
       '''
       generate filename for images
       '''
       
       if ftype == "video":     return self.config.imageName(type="video",   timestamp=self.info["date_start"], camera=self.camera)
       elif ftype == "thumb":   return self.config.imageName(type="thumb",   timestamp=self.info["date_start"], camera=self.camera)
       elif ftype == "vimages": return self.config.imageName(type="vimages", timestamp=self.info["date_start"], camera=self.camera)
       else:                    return
       
#       if ftype == "image":   return "video-" + self.camera + "_" + self.info["date_start"] + "_"
#       elif ftype == "video": return "video-" +  self.camera + "_" + self.info["date_start"] + ".mp4"
#       else:                  return


   def create_video(self):
       '''
       Create video from images
       '''
       self.processing = True
       cmd_create = self.ffmpeg_cmd
       cmd_create = cmd_create.replace("{INPUT_FILENAMES}", os.path.join(self.config.directory("videos"), self.filename("vimages") + "%" + str(self.count_length).zfill(2) + "d.jpg"))
       cmd_create = cmd_create.replace("{OUTPUT_FILENAME}", os.path.join(self.config.directory("videos"), self.filename("video")))
       cmd_create = cmd_create.replace("{FRAMERATE}", str(round(self.info["framerate"])))

       self.info["thumbnail"] = self.filename("thumb")
       cmd_thumb  = "cp " + os.path.join(self.config.directory("videos"), self.filename("vimages") + str(1).zfill(self.count_length) + ".jpg ") + os.path.join(self.config.directory("videos"), self.filename("thumb"))
       cmd_delete = "rm " + os.path.join(self.config.directory("videos"), self.filename("vimages") + "*.jpg")
       logging.info("start video creation with ffmpeg ...")
       
       logging.info(cmd_create)       
       message  = os.system(cmd_create)
       logging.debug(message)       


       logging.info(cmd_thumb)       
       message = os.system(cmd_thumb)
       logging.debug(message)       

       logging.info(cmd_delete)       
       message = os.system(cmd_delete)
       logging.debug(message)       

       self.processing = False
       logging.info("OK.")
       return


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
       self.id           = id
       self.param        = param
       self.name         = param["name"]
       self.active       = param["active"]
       self.config       = config
       self.type         = type
       self.record       = record
       self.running      = True
       self.error        = False
       self.image_size   = [0, 0]
       
       logging.info("Starting camera ("+self.type+"/"+self.name+") ...")

       if self.type == "pi":
         try:
            import picamera
         except ImportError:
            self.error  = True
            self.active = False
            logging.error("Python module for PiCamera isn't installed. Try 'pip3 install picamera'.")
         
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
          
       if not self.error:
        if self.param["video"]["allow_recording"]:
          test = self.getImage()
          self.video = myVideoRecording(camera=self.id, param=self.param, directory=self.config.directory("videos"))
          self.video.config = config
          self.video.start()
          self.video.image_size = self.image_size

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
          seconds = datetime.now().strftime('%S')
          hours   = datetime.now().strftime('%H')
          stamp   = datetime.now().strftime('%H%M%S')
          
          # Video Recording
          if self.video.recording:
          
             if self.video.autostop():
                self.video.stop_recording()
                break

             image     = self.getImage()
             image     = self.convertImage2RawImage(image)
             self.video.save_image(image=image)

             logging.debug(".... Video Recording: " + str(self.video.info["stamp_start"]) + " -> " + str(datetime.now().strftime("%H:%M:%S")))

          # Image Recording
          else:
             time.sleep(1)
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
                          "similarity"  : similarity,
                          "size"        : self.image_size
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

       if not self.error and self.active:
         if self.type == "pi":
           self.camera.stop_recording()
           self.camera.close()

         elif self.type == "usb":
           self.camera.stop()
           self.cameraFPS.stop()
          
       logging.info("OK.")

   #----------------------------------

   def setText(self,text):
       '''
       Add / replace text on the image
       '''
       if self.type == "pi":
          self.camera.annotate_text = str(text)


   def setText2RawImage(self, image, text, position=(30,40), font=cv2.FONT_HERSHEY_SIMPLEX, fontScale=0.8, color=(255,255,255), thickness=2):
       '''
       Add text on image
       '''
       image     = cv2.putText(image, text, position, font, fontScale, color, thickness, cv2.LINE_AA)
       return image


   def setText2Image(self, image, text, position=(30,40), font=cv2.FONT_HERSHEY_SIMPLEX, fontScale=0.8, color=(255,255,255), thickness=2):
       '''
       Add text on image
       '''
       image = self.convertImage2RawImage(image)
       image = self.setText2RawImage(image, text, position=position, font=font, fontScale=fontScale, color=color, thickness=thickness)
       image = self.convertRawImage2Image(image)
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

       if self.image_size == [0,0]: 
          self.image_size = self.sizeRawImage(raw)
          self.video.image_size = self.image_size
          
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
   
   def sizeRawImage(self, frame):
       '''
       Return size of raw image
       '''
       try:
         height = frame.shape[0]
         width  = frame.shape[1]
         
       except Exception as e:
         logging.warning("Could not analyze image: "+str(e))
         
       return [width, height]

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
       if len(imageA) == 0 or len(imageB) == 0:
          logging.warning("At least one file has a zero length - A:" + str(len(imageA)) + "/ B:" + str(len(imageB)))
          score = 0
          
       else:
         if detection_area != None:
            logging.debug(self.id +"/compare 1: "+str(detection_area)+" / "+str(imageA.shape))
            imageA, area = self.cropRawImage(frame=imageA, crop_area=detection_area, type="relative")
            imageB, area = self.cropRawImage(frame=imageB, crop_area=detection_area, type="relative")
            logging.debug(self.id +"/compare 2: "+str(area)+" / "+str(imageA.shape))

         try:
            (score, diff) = ssim(imageA, imageB, full=True)

         except Exception as e:
            logging.warning("Error comparing images: " + str(e))
            score = 0

       return round(score*100,1)


   #----------------------------------

   def selectImage(self, timestamp, file_info, check_similarity=True):
       '''
       check image properties to decide if image is a selected one (for backup and view with selected images)
       '''
       if not "similarity" in file_info:                                    return False

       if ("camera" in file_info and file_info["camera"] == self.id) or (not "camera" in file_info and self.id == "cam1"):

          if "to_be_deleted" in file_info:
             delete    = int(file_info["to_be_deleted"])
             if delete == 1:                                                return False

          if "00"+str(self.param["image_save"]["seconds"][0]) in timestamp: return True

          if "favorit" in file_info:
             favorit    = int(file_info["favorit"])
             if favorit == 1:                                               return True

          if check_similarity:
             threshold  = float(self.param["similarity"]["threshold"])
             similarity = float(file_info["similarity"])
             if similarity != 0 and similarity < threshold:                 return True
          else:                                                             return True ### to be checked !!!

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
          files       = self.config.read_cache("images")
          files[time] = data
          self.config.write("images",files)



