#!/usr/bin/python3

# In Progress:
# - ...
# Backlog:
# -> GET to myViews
# -> POST to myAPI
#
# - show videos in favorits section
# - show videos in day views (with play icon on it)
# - Optimize data handling
#   -> Queue for writing into JSON (e.g. for status changes)
#   -> using a CouchDB instead of JSON files
# - In progress (error!): Restart camera threads via API, Shutdown all services via API, Trigger RPi halt/reboot via API
# - password for external access (to enable admin from outside)
# - Idea: set to_be_deleted when below threshold; don't show / backup those files


import io, os, time
import logging
import json, codecs
import numpy as np
import signal, sys, string

import threading
import socketserver
from threading       import Condition
from http            import server
from datetime        import datetime, timedelta

from modules.backup  import myBackupRestore
from modules.camera  import myCamera
from modules.config  import myConfig
from modules.presets import myParameters
from modules.presets import myPages
from modules.views   import myViews

#----------------------------------------------------

def onexit(signum, handler):
    '''
    Clean exit on Strg+C
    All shutdown functions are defined in the "finally:" section in the end of this script
    '''
    time.sleep(1)
    print ('\nSTRG+C pressed! (Signal: %s)' % (signum,))
    while True:
        confirm = input('Enter "yes" to cancel programm now or "no" to keep running [yes/no]: ').strip().lower()
        if confirm == 'yes':
            print ("Cancel!\n")
            sys.exit()
        elif confirm == 'no':
            print ("Keep runnning!\n")
            break
        else:
            print ('Sorry, no valid answer...\n')
        pass


def onkill(signum, handler):
    '''
    Clean exit on kill command
    All shutdown functions are defined in the "finally:" section in the end of this script
    '''
    print('\nKILL command detected! (Signal: %s)' % (signum,))
    sys.exit()


#----------------------------------------------------


def read_html(directory,filename):
   '''
   read html file, replace placeholders and return for stream via webserver
   '''
   if filename.startswith("/"):  filename = filename[1:len(filename)]
   if directory.startswith("/"): directory = directroy[1:len(directory)]
   file = os.path.join(config.param["path"], directory, filename)

   if not os.path.isfile(file):
     logging.warning("File '"+file+"' does not exist!")
     return ""

   with open(file, "r") as page:
     PAGE = page.read()
     for param in config.html_replace:
       if "<!--"+param+"-->" in PAGE:
         PAGE = PAGE.replace("<!--"+param+"-->",str(config.html_replace[param]))
     PAGE = PAGE.encode('utf-8')
   return PAGE


def read_image(directory,filename):
   '''
   read image file and return for stream via webserver
   '''
   if filename.startswith("/"):  filename = filename[1:len(filename)]
   if directory.startswith("/"): directory = directroy[1:len(directory)]
   file = os.path.join(config.param["path"], directory, filename)
   file = file.replace("backup/","")

   if not os.path.isfile(file):
      logging.warning("Image '"+file+"' does not exist!")
      return ""

   with open(file, "rb") as image: f = image.read()
   return f


#----------------------------------------------------


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):

    allow_reuse_address = True
    daemon_threads      = True


class StreamingHandler(server.BaseHTTPRequestHandler):

    def redirect(self,file):
        '''
        Redirect to other file / URL
        '''
        self.send_response(301)
        self.send_header('Location', '/index.html')
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()	


    def sendError(self):
        '''
        Send file not found
        '''
        self.send_error(404)
        self.end_headers()


    def streamFile(self,type,content,no_cache=False):
        '''
        send file content (HTML, image, ...)
        '''
        if len(content) > 0:
           self.send_response(200)
           self.send_header('Content-Type', type)
           self.send_header('Content-Length', len(content))
           if no_cache:
             self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
             self.send_header("Pragma", "no-cache")
             self.send_header("Expires", "0")
           self.end_headers()
           self.wfile.write(content)
        else:
           self.sendError()


    def streamVideoHeader(self):
        '''
        send header for video stream
        '''
        self.send_response(200)
        self.send_header('Age', 0)
        self.send_header('Cache-Control', 'no-cache, private')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
        self.end_headers()


    def streamVideoFrame(self,frame):
        '''
        send header and frame inside a MJPEG video stream
        '''
        self.wfile.write(b'--FRAME\r\n')
        self.send_header('Content-Type', 'image/jpeg')
        self.send_header('Content-Length', len(frame))
        self.end_headers()
        self.wfile.write(frame)
        self.wfile.write(b'\r\n')

    #-------------------------------------
    
    def adminAllowed(self):
        '''
        Check if administration is allowed based on the IP4 the request comes from
        '''
        logging.debug("Check if administration is allowed: "+self.address_string()+" / "+str(config.param["ip4_admin_deny"]))
        if self.address_string() in config.param["ip4_admin_deny"]: return False
        else:                                                       return True

    #-------------------------------------

    def do_POST(self):
        '''
        REST API for javascript commands e.g. to change values in runtime
        '''
        global config, camera, backup
        
        response = {}
        if not self.adminAllowed():
           response["error"] = "Administration not allowed for this IP-Address!"
           self.streamFile(type='application/json', content=json.dumps(response).encode(encoding='utf_8'), no_cache=True);
        
        # set / unset favorit
        if self.path.startswith("/favorit/"):
           param = self.path.split("/")

           if param[2] == "current":
              config_data         = config.read_cache(config="images")
              response["command"] = ["set/unset favorit", param[3], param[4]]
              if param[3] in config_data:
                 config_data[param[3]]["favorit"] = param[4]
                 if int(param[4]) == 1: config_data[param[3]]["to_be_deleted"] = 0
                 config.write(config="images", config_data=config_data)
              else:
                 response["error"] = "no image found with stamp "+str(param[3])

           elif param[2] == "backup":
              config_data         = config.read_cache(config="backup", date=param[3])
              response["command"] = ["set/unset favorit (backup)", param[5]]
              if param[4] in config_data["files"]:
                 config_data["files"][param[4]]["favorit"] = param[5]
                 if int(param[5]) == 1: config_data["files"][param[4]]["to_be_deleted"] = 0
                 config.write(config="backup",config_data=config_data, date=param[3])
              else:
                 response["error"] = "no image found with stamp "+str(param[4])

           elif param[2] == "videos":
              config_data         = config.read_cache(config="videos")
              response["command"] = ["set/unset favorit (videos)", param[3], param[4]]
              if param[3] in config_data:
                 config_data[param[3]]["favorit"] = param[4]
                 if int(param[4]) == 1: config_data[param[3]]["to_be_deleted"] = 0
                 config.write(config="videos", config_data=config_data)
              else:
                 response["error"] = "no video found with stamp "+str(param[3])

           self.streamFile(type='application/json', content=json.dumps(response).encode(encoding='utf_8'), no_cache=True);


        # mark / unmark for deletion
        elif self.path.startswith("/recycle/"):
           param = self.path.split("/")

           if param[2] == "current":
              config_data         = config.read_cache(config="images")
              response["command"] = ["mark/unmark for deletion", param[4]]
              if param[3] in config_data:
                 config_data[param[3]]["to_be_deleted"] = param[4]
                 if int(param[4]) == 1: config_data[param[3]]["favorit"] = 0
                 config.write(config="images", config_data=config_data)
              else:
                 response["error"] = "no image found with stamp "+str(param[3])

           elif param[2] == "backup":
              config_data         = config.read_cache(config="backup", date=param[3])
              response["command"] = ["mark/unmark for deletion (backup)", param[5]]
              if param[4] in config_data["files"]:
                 config_data["files"][param[4]]["to_be_deleted"] = param[5]
                 if int(param[5]) == 1: config_data["files"][param[4]]["favorit"] = 0
                 config.write(config="backup",config_data=config_data, date=param[3])
              else:
                 response["error"] = "no image found with stamp "+str(param[4])

           elif param[2] == "videos":
              config_data         = config.read_cache(config="videos")
              response["command"] = ["mark/unmark for deletion", param[4]]
              if param[3] in config_data:
                 config_data[param[3]]["to_be_deleted"] = param[4]
                 if int(param[4]) == 1: config_data[param[3]]["favorit"] = 0
                 config.write(config="videos", config_data=config_data)
              else:
                 response["error"] = "no video found with stamp "+str(param[3])
           
           self.streamFile(type='application/json', content=json.dumps(response).encode(encoding='utf_8'), no_cache=True);


        # remove marked files           
        elif self.path.startswith('/remove/'):
           param = self.path.split("/")
           if "delete_not_used" in param: delete_not_used = True
           else:                          delete_not_used = False
           if param[2] == "backup":       response = backup.delete_marked_files(date=param[3], delete_not_used=delete_not_used)
           elif param[2] == "today":      response = backup.delete_marked_files(date="",       delete_not_used=delete_not_used)
           else:                          response["error"] = "not clear, which files shall be deleted"
           
           response["command"] = ["delete files that are marked as 'to_be_deleted'" ,param]
           self.streamFile(type='application/json', content=json.dumps(response).encode(encoding='utf_8'), no_cache=True);
           
        # start video recording
        elif self.path.startswith("/start/recording/"):
           param     = self.path.split("/")
           which_cam = param[3]
           if which_cam in camera and not camera[which_cam].error and camera[which_cam].active:
              if not camera[which_cam].video.recording:   camera[which_cam].video.start_recording()
              else:                                       response["error"] = "camera is already recording "+str(param[3])       
           elif camera[which_cam].error or camera[which_cam].active == False:
              response["error"] = "camera is not active "+str(param[3])       
           else:
              response["error"] = "camera doesn't exist "+str(param[3])       

           response["command"] = ["start recording"]
           self.streamFile(type='application/json', content=json.dumps(response).encode(encoding='utf_8'), no_cache=True);

        # end video recording
        elif self.path.startswith("/stop/recording/"):
           param     = self.path.split("/")
           which_cam = param[3]
           if which_cam in camera and not camera[which_cam].error and camera[which_cam].active:
              if camera[which_cam].video.recording:  camera[which_cam].video.stop_recording()
              else:                                  response["error"] = "camera isn't recording at the moment "+str(param[3])       
           elif camera[which_cam].error or camera[which_cam].active == False:
              response["error"] = "camera is not active "+str(param[3])       
           else:
              response["error"] = "camera doesn't exist "+str(param[3])       

           response["command"] = ["start recording"]
           self.streamFile(type='application/json', content=json.dumps(response).encode(encoding='utf_8'), no_cache=True);


        # restart camera // doesn't close the camera correctly at the moment
        elif self.path.startswith("/restart-cameras/"):
           logging.info("Restart of camera threads requested ...")
           for cam in camera:
             camera[cam].stop()

           camera = {}
           config.reload()
           for cam in config.param["cameras"]:
             settings = config.param["cameras"][cam]
             camera[cam] = myCamera(id=cam, type=settings["type"], record=settings["record"], param=settings, config=config)
             if not camera[cam].error:
               camera[cam].start()
               camera[cam].param["path"] = config.param["path"]
               camera[cam].setText("Restarting ...")
             response["command"] = ["Restart cameras"]

        else:
           self.sendError()
           return
           

    #-------------------------------------

    def do_GET(self):
        '''
        check path and send requested content
        '''
        logging.debug("GET request with '" + self.path + "'.")
        config.html_replace["title"] = config.param["title"]

        # check which camera has bin requested
        if "?" in self.path:
           param = self.path.split("?")
           self.path = param[0]
           which_cam = param[1]
           if not which_cam in camera:
              logging.warning("Unknown camera requested.")
              self.sendError()
              return
        else:
           which_cam = "cam1"

        self.active_cams = []
        for key in camera:
          if camera[key].active: self.active_cams.append(key)
        if camera[which_cam].active == False:
          which_cam = self.active_cams[0]
        config.html_replace["active_cam"] = which_cam


        # index with embedded live stream
        if   self.path == '/':

          self.redirect("/index.html")


        elif self.path.endswith('.html'):
        
          if   self.path.endswith('/index.html'):       template = views.createIndex(server=self)
          elif self.path.endswith('/list_star.html'):   template = views.createFavorits(server=self)
          elif self.path.endswith('/list_short.html'):  template = views.createList(server=self)
          elif self.path.endswith('/list_backup.html'): template = views.createBackupList(server=self)
          elif self.path.endswith('/list_new.html'):    template = views.createCompleteListToday(server=self)
          elif self.path.endswith('/videos.html'):      template = views.createVideoList(server=self)
          elif self.path.endswith('/cameras.html'):     template = views.createCameraList(server=self)
          
          self.streamFile(type='text/html', content=read_html('html',template), no_cache=True)

         
        # extract and show single image
        elif self.path == '/image.jpg':
        
            camera[which_cam].setText = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
            camera[which_cam].writeImage('image_'+which_cam+'.jpg',camera[which_cam].convertFrame2Image(camera[which_cam].getFrame()))
            self.streamFile(type='image/jpeg', content=read_image("",'image_'+which_cam+'.jpg'))


        # show live stream
        elif self.path.endswith('/stream.mjpg'):

            if camera[which_cam].type != "pi" and camera[which_cam].type != "usb":
               logging.warning("Unknown type of camera ("+camera[which_cam].type+"/"+camera[which_cam].name+")")
               stream = False
               self.sendError()
               return
               
            self.streamVideoHeader()
            count    = 0
            addText  = ""
            imageOld = []
            stream   = True
            
            while stream:
              if camera[which_cam].type == "pi":
                 camera[which_cam].setText(datetime.now().strftime('%d.%m.%Y %H:%M:%S'))

              frame = camera[which_cam].getImage()
                  
              if camera[which_cam].video.recording:                                          
                 frame = camera[which_cam].setText2Image(frame, "Recording", position=(100,100), color=(0,0,255), fontScale=1, thickness=1)
                 time.sleep(1)                     
                     
              if self.path.startswith("/detection/"):
                 frame = camera[which_cam].drawImageDetectionArea(image=frame)
                     
              try:
                  camera[which_cam].wait()
                  self.streamVideoFrame(frame)

              except Exception as e:
                  stream = False
                  if "Errno 104" in str(e) or "Errno 32" in str(e):  logging.debug('Removed streaming client %s: %s', self.client_address, str(e))
                  else:                                              logging.warning('Removed streaming client %s: %s', self.client_address, str(e))


        # images, css, js
        elif self.path.endswith('.png'):        self.streamFile(type='image/png',       content=read_image('',self.path))
        elif self.path.endswith('.css'):        self.streamFile(type='text/css',        content=read_html( '',self.path))
        elif self.path.endswith('.js'):         self.streamFile(type='text/javascript', content=read_html( '',self.path))
        elif self.path.endswith('favicon.ico'): self.streamFile(type='image/ico', content=read_image('html','favicon.ico'))

        elif self.path.endswith('.mp4'):        self.streamFile(type='video/mp4', content=read_image("videos",self.path))
        elif self.path.startswith('/videos') and self.path.endswith('.jpeg'):
                                                self.streamFile(type='image/jpg', content=read_image('',self.path))
       
        elif self.path.endswith(".jpg"):        self.streamFile(type='image/jpg', content=read_image("images",self.path))
        elif self.path.endswith(".jpeg"):       self.streamFile(type='image/jpg', content=read_image("images",self.path))

        # unknown
        else:
            self.sendError()

#----------------------------------------------------

# execute only if run as a script
if __name__ == "__main__":

    # set logging
    if len(sys.argv) > 0 and "--logfile" in sys.argv:
       logging.basicConfig(filename=os.path.join(os.path.dirname(__file__),"stream.log"),
                           filemode='a',
                           format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                           datefmt='%d.%m.%y %H:%M:%S',
                           level=logging.INFO)
       logging.info('-------------------------------------------')
       logging.info('Started ...')
       logging.info('-------------------------------------------')
    else:
       logging.basicConfig(format='%(levelname)s: %(message)s',level=logging.INFO)
       #logging.basicConfig(format='%(levelname)s: %(message)s',level=logging.DEBUG)
       
    # set system signal handler
    signal.signal(signal.SIGINT,  onexit)
    signal.signal(signal.SIGTERM, onkill)

    # start config    
    config = myConfig(param_init=myParameters, main_directory=os.path.dirname(os.path.abspath(__file__)))
    config.start()    
    config.directory_create("images")
    config.directory_create("videos")

    # start cameras
    camera = {}
    for cam in config.param["cameras"]:
        settings = config.param["cameras"][cam]
        camera[cam] = myCamera(id=cam, type=settings["type"], record=settings["record"], param=settings, config=config)
        if not camera[cam].error:
           camera[cam].start()
           camera[cam].param["path"] = config.param["path"]
           camera[cam].setText("Starting ...")

    # start views           
    views = myViews(config=config, camera=camera)
    views.start()

    # start backups
    time.sleep(1)
    backup = myBackupRestore(config, camera)
    backup.start()

    # check if config files for main image directory exists and create if not exists
    if not os.path.isfile(config.file("images")):
        logging.info("Create image list for main directory ...")
        backup.compare_files_init()
        logging.info("OK.")



#----------------------------------------------------
# manual start to be implemented into UI

    #backup.backup_files()
    #backup.backup_files("20210402")

#----------------------------------------------------

    try:
        address = ('', config.param["port"])
        server  = StreamingServer(address, StreamingHandler)

        logging.info("Starting WebServer ...")
        server.serve_forever()
        logging.info("OK.")


    finally:
        for cam in camera:
          if camera[cam].active:
             camera[cam].stop()
        backup.stop()

        logging.info("Stopping WebServer ...")
        server.server_close()

