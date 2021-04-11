#!/usr/bin/python3

# In Progress:
# - ...
# Backlog:
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
from threading        import Condition
from http             import server
from datetime         import datetime, timedelta

from modules.backup   import myBackupRestore
from modules.camera   import myCamera
from modules.config   import myConfig
from modules.commands import myCommands
from modules.presets  import myParameters
from modules.presets  import myPages
from modules.views    import myViews

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


def read_html(directory, filename, content=""):
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
     
     for param in content:
       if "<!--"+param+"-->" in PAGE: PAGE = PAGE.replace("<!--"+param+"-->",str(content[param]))
       
     for param in config.html_replace:
       if "<!--"+param+"-->" in PAGE: PAGE = PAGE.replace("<!--"+param+"-->",str(config.html_replace[param]))
       
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


    def streamFile(self,ftype,content,no_cache=False):
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
           self.streamFile(ftype='application/json', content=json.dumps(response).encode(encoding='utf_8'), no_cache=True);

        
        if self.path.startswith("/favorit/"):            response = commands.setStatusFavorit(self)
        elif self.path.startswith("/recycle/"):          response = commands.setStatusRecycle(self)
        elif self.path.startswith('/remove/'):           response = commands.deleteMarkedFiles(self)
        elif self.path.startswith("/start/recording/"):  response = commands.startRecording(self)
        elif self.path.startswith("/stop/recording/"):   response = commands.stopRecording(self)
        elif self.path.startswith("/restart-cameras/"):  response = commands.restartCameras(self)
        else:
           self.sendError()
           return

        self.streamFile(ftype='application/json', content=json.dumps(response).encode(encoding='utf_8'), no_cache=True);
           

    #-------------------------------------

    def do_GET(self):
        '''
        check path and send requested content
        '''
        logging.debug("GET request with '" + self.path + "'.")
        path, which_cam = views.selectedCamera(self.path)

        config.html_replace["title"]      = config.param["title"]
        config.html_replace["active_cam"] = which_cam

        # index with embedded live stream
        if   self.path == '/': 

          self.redirect("/index.html")


        elif '.html' in self.path:
        
          if   '/index.html' in self.path:       template, content = views.createIndex(server=self)
          elif '/list_star.html' in self.path:   template, content = views.createFavorits(server=self)
          elif '/list_short.html' in self.path:  template, content = views.createList(server=self)
          elif '/list_backup.html' in self.path: template, content = views.createBackupList(server=self)
          elif '/list_new.html' in self.path:    template, content = views.createCompleteListToday(server=self)
          elif '/videos.html' in self.path:      template, content = views.createVideoList(server=self)
          elif '/cameras.html' in self.path:     template, content = views.createCameraList(server=self)
          
          self.streamFile(ftype='text/html', content=read_html(directory='html', filename=template, content=content), no_cache=True)


        # extract and show single image
        elif '/image.jpg' in self.path:
        
            camera[which_cam].setText = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
            camera[which_cam].writeImage('image_'+which_cam+'.jpg',camera[which_cam].convertFrame2Image(camera[which_cam].getFrame()))
            self.streamFile(ftype='image/jpeg', content=read_image(directory="", filename='image_'+which_cam+'.jpg'))


        # show live stream
        elif '/stream.mjpg' in self.path:

            if camera[which_cam].type != "pi" and camera[which_cam].type != "usb":
               logging.warning("Unknown type of camera ("+camera[which_cam].type+"/"+camera[which_cam].name+")")
               stream = False
               self.sendError()
               return
               
            self.streamVideoHeader()
            stream   = True
            
            while stream:
              if camera[which_cam].type == "pi":
                 camera[which_cam].setText(datetime.now().strftime('%d.%m.%Y %H:%M:%S'))

              frame = camera[which_cam].getImage()
                  
              if camera[which_cam].video.recording:                                          
                 length    = str(round(camera[which_cam].video.info_recording()["length"]))
                 framerate = str(round(camera[which_cam].video.info_recording()["framerate"]))
                 frame = camera[which_cam].setText2Image(frame, "Recording", position=(20,40), color=(0,0,255), fontScale=1, thickness=2)
                 frame = camera[which_cam].setText2Image(frame, "("+length+"s/"+framerate+"fps)", position=(200,40), color=(0,0,255), fontScale=0.5, thickness=1)
                 
              if camera[which_cam].video.processing:                                          
                 length    = str(round(camera[which_cam].video.info_recording()["length"]))
                 frame = camera[which_cam].setText2Image(frame, "Processing", position=(20,40), color=(0,255,255), fontScale=1, thickness=2)
                 frame = camera[which_cam].setText2Image(frame, "("+length+"s)", position=(200,40), color=(0,255,255), fontScale=0.5, thickness=1)
                     
              if self.path.startswith("/detection/"):
                 frame = camera[which_cam].drawImageDetectionArea(image=frame)
                     
              try:
                 camera[which_cam].wait()
                 self.streamVideoFrame(frame)

              except Exception as e:
                 stream = False
                 if "Errno 104" in str(e) or "Errno 32" in str(e):  logging.debug('Removed streaming client %s: %s', self.client_address, str(e))
                 else:                                              logging.warning('Removed streaming client %s: %s', self.client_address, str(e))

              for cam in camera:
                if not camera[cam].error:
                  if camera[cam].video.processing:                                          
                    time.sleep(0.3)                     
                    break
                  if camera[cam].video.recording:                                          
                    time.sleep(1)                     
                    break

        # images, css, js
        elif self.path.endswith('.css'):        self.streamFile(ftype='text/css',        content=read_html( directory='',       filename=self.path))
        elif self.path.endswith('.js'):         self.streamFile(ftype='text/javascript', content=read_html( directory='',       filename=self.path))
        elif self.path.endswith('.png'):        self.streamFile(ftype='image/png',       content=read_image(directory='',       filename=self.path))
        elif self.path.endswith('favicon.ico'): self.streamFile(ftype='image/ico',       content=read_image(directory='html',   filename=self.path))

        elif self.path.endswith('.mp4'):        self.streamFile(ftype='video/mp4',       content=read_image(directory="videos", filename=self.path))
        elif self.path.startswith('/videos') and self.path.endswith('.jpeg'):
                                                self.streamFile(ftype='image/jpg',       content=read_image(directory='',       filename=self.path))
       
        elif self.path.endswith(".jpg"):        self.streamFile(ftype='image/jpg',       content=read_image(directory="images", filename=self.path))
        elif self.path.endswith(".jpeg"):       self.streamFile(ftype='image/jpg',       content=read_image(directory="images", filename=self.path))

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

    # start backups
    time.sleep(1)
    backup = myBackupRestore(config, camera)
    backup.start()

    # start views and commands
    views = myViews(config=config, camera=camera)
    views.start()

    commands = myCommands(config=config, camera=camera, backup=backup)
    commands.start()

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
        views.stop()

        logging.info("Stopping WebServer ...")
        server.server_close()

