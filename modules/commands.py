#!/usr/bin/python3

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


class myCommands(threading.Thread):

    def __init__(self, camera, config, backup):
        '''
        Initialize new thread and set inital parameters
        '''
        threading.Thread.__init__(self)
        self.camera         = camera
        self.config         = config
        self.backup         = backup
        self.processing     = True
        self.which_cam      = ""
        self.status_queue           = {}
        self.status_queue["images"] = []
        self.status_queue["videos"] = []
        self.status_queue["backup"] = []
        

    #-------------------------------------
    
    def run(self):
        '''
        Do nothing at the moment
        '''
        config_files = ["images","videos"]
        while self.processing:
           time.sleep(10)
           
           for config_file in config_files:
             entries = self.config.read_cache(config_file)
             self.config.lock(config_file)
             
             while len(self.status_queue[config_file]) > 0:
                [ date, key, change_status, status ] = self.status_queue[config_file].pop()

                if key in entries: 
                   test = "yes"
                   entries[key][change_status] = status
                else:
                   test="no"
                   
                logging.info("QUEUE: "+config_file+" // "+key+" - "+change_status+"="+str(status)+" ... "+test)
             
             self.config.unlock(config_file)
             self.config.write(config_file, entries)   
                           
        return
    
    def stop(self):
        '''
        Do nothing at the moment
        '''
        self.processing = False
        return
    
    #-------------------------------------

    def addToQueue( self, config, date, key, change_status, status ):
        '''
        add entry to queue
        '''
        self.status_queue[config].append( [ date, key, change_status, status ] )
    
    #-------------------------------------
    
    def adminAllowed(self):
        '''
        Check if administration is allowed based on the IP4 the request comes from
        '''
        logging.debug("Check if administration is allowed: "+self.address_string()+" / "+str(config.param["ip4_admin_deny"]))
        if self.address_string() in config.param["ip4_admin_deny"]: return False
        else:                                                       return True

    #-------------------------------------
    
    def setStatusFavorit(self, server):
        '''
        set / unset favorit
        '''        
        param    = server.path.split("/")
        response = {}

# config, date, key, change_status, status

        if param[2] == "current":
           config_data         = self.config.read_cache(config="images")
           response["command"] = ["set/unset favorit", param[3], param[4]]
           if param[3] in config_data:

              config_data[param[3]]["favorit"] = param[4]
              self.addToQueue( config="images", date="", key=param[3], change_status="favorit", status=param[4] )

              if int(param[4]) == 1:
                 config_data[param[3]]["to_be_deleted"] = 0
                 self.addToQueue( config="images", date="", key=param[3], change_status="to_be_deleted", status=0 )
                 
#              self.config.write(config="images", config_data=config_data)

           else:
              response["error"] = "no image found with stamp "+str(param[3])


        elif param[2] == "backup":
           config_data         = self.config.read_cache(config="backup", date=param[3])
           response["command"] = ["set/unset favorit (backup)", param[5]]
           if param[4] in config_data["files"]:

              config_data["files"][param[4]]["favorit"] = param[5]
              self.addToQueue( config="backup", date=param[3], key=param[4], change_status="favorit", status=param[5] )
                           
              if int(param[5]) == 1: 
                 config_data["files"][param[4]]["to_be_deleted"] = 0
                 self.addToQueue( config="backup", date=param[3], key=param[4], change_status="to_be_deleted", status=0)
                 
              self.config.write(config="backup",config_data=config_data, date=param[3])

           else:
              response["error"] = "no image found with stamp "+str(param[4])


        elif param[2] == "videos":
           config_data         = self.config.read_cache(config="videos")
           response["command"] = ["set/unset favorit (videos)", param[3], param[4]]
           if param[3] in config_data:

              config_data[param[3]]["favorit"] = param[4]
              self.addToQueue( config="videos", date="", key=param[3], change_status="favorit", status=param[4] )

              if int(param[4]) == 1:
                 config_data[param[3]]["to_be_deleted"] = 0
                 self.addToQueue( config="videos", date="", key=param[3], change_status="to_be_deleted", status=0 )
                 
#              self.config.write(config="videos", config_data=config_data)
              
           else:
              response["error"] = "no video found with stamp "+str(param[3])
    
        return response

    #-------------------------------------
    
    def setStatusRecycle(self, server):
        '''
        set / unset recycling
        '''        
        param    = server.path.split("/")
        response = {}

        if param[2] == "current":
           config_data         = self.config.read_cache(config="images")
           response["command"] = ["mark/unmark for deletion", param[4]]
           if param[3] in config_data:

              config_data[param[3]]["to_be_deleted"] = param[4]
              self.addToQueue( config="images", date="", key=param[3], change_status="to_be_deleted", status=param[4])
              
              if int(param[4]) == 1: 
                 config_data[param[3]]["favorit"] = 0
                 self.addToQueue( config="images", date="", key=param[3], change_status="favorit", status=0 )
                 
#              self.config.write(config="images", config_data=config_data)
           else:
              response["error"] = "no image found with stamp "+str(param[3])


        elif param[2] == "backup":
           config_data         = self.config.read_cache(config="backup", date=param[3])
           response["command"] = ["mark/unmark for deletion (backup)", param[5]]
           if param[4] in config_data["files"]:
           
              config_data["files"][param[4]]["to_be_deleted"] = param[5]
              self.addToQueue( config="backup", date=param[3], key=param[4], change_status="to_be_deleted", status=param[5] )
              
              if int(param[5]) == 1:
                 config_data["files"][param[4]]["favorit"] = 0
                 self.addToQueue( config="backup", date=param[3], key=param[4], change_status="favorit", status=0)
                 
              self.config.write(config="backup",config_data=config_data, date=param[3])
           else:
              response["error"] = "no image found with stamp "+str(param[4])


        elif param[2] == "videos":
           config_data         = self.config.read_cache(config="videos")
           response["command"] = ["mark/unmark for deletion", param[4]]
           if param[3] in config_data:

              config_data[param[3]]["to_be_deleted"] = param[4]
              self.addToQueue( config="videos", date="", key=param[3], change_status="to_be_deleted", status=param[4])

              if int(param[4]) == 1:
                 config_data[param[3]]["favorit"] = 0
                 self.addToQueue( config="videos", date="", key=param[3], change_status="favorit", status=0)
                 
#              self.config.write(config="videos", config_data=config_data)
           else:
              response["error"] = "no video found with stamp "+str(param[3])
           
        return response

    #-------------------------------------
    
    def deleteMarkedFiles(self, server):
        '''
        set / unset recycling
        '''        
        param    = server.path.split("/")
        response = {}

        if "delete_not_used" in param: delete_not_used = True
        else:                          delete_not_used = False
        if param[2] == "backup":       response = self.backup.delete_marked_files(ftype="image", date=param[3], delete_not_used=delete_not_used)
        elif param[2] == "today":      response = self.backup.delete_marked_files(ftype="image", date="",       delete_not_used=delete_not_used)
        elif param[2] == "video":      response = self.backup.delete_marked_files(ftype="video", date="",       delete_not_used=delete_not_used)
        else:                          response["error"] = "not clear, which files shall be deleted"           
        response["command"] = ["delete files that are marked as 'to_be_deleted'" ,param]

        return response

    #-------------------------------------

    def startRecording(self, server):
        '''
        start video recoding
        '''        
        param    = server.path.split("/")
        response = {}

        which_cam = param[3]
        if which_cam in self.camera and not self.camera[which_cam].error and self.camera[which_cam].active:
           if not self.camera[which_cam].video.recording:   self.camera[which_cam].video.start_recording()
           else:                                            response["error"] = "camera is already recording "+str(param[3])       
        elif self.camera[which_cam].error or self.camera[which_cam].active == False:
           response["error"] = "camera is not active "+str(param[3])       
        else:
           response["error"] = "camera doesn't exist "+str(param[3])       
        response["command"]  = ["start recording"]

        return response

    #-------------------------------------
    
    def stopRecording(self, server):
        '''
        stop video recoding
        '''        
        param    = server.path.split("/")
        response = {}
        
        which_cam = param[3]
        if which_cam in self.camera and not self.camera[which_cam].error and self.camera[which_cam].active:
           if self.camera[which_cam].video.recording:  self.camera[which_cam].video.stop_recording()
           else:                                       response["error"] = "camera isn't recording at the moment "+str(param[3])       
        elif self.camera[which_cam].error or self.camera[which_cam].active == False:
           response["error"] = "camera is not active "+str(param[3])       
        else:
           response["error"] = "camera doesn't exist "+str(param[3])       
        response["command"]  = ["start recording"]

        return response

    #-------------------------------------
    
    def createShortVideo(self, server):
        '''
        create a short video and save in DB (not deleting the old video at the moment)
        '''
        param        = server.path.split("/")
        response     = {}
        
        if len(param) < 6:
           response["result"] = "Error: Parameters are missing (/create-short-video/video-id/start-timecode/end-timecode/which-cam/)"
           logging.warning("Create short version of video ... Parameters are missing.")
           
        else:
           logging.info("Create short version of video '"+str(param[2])+"' ["+str(param[3])+":"+str(param[4])+"] ...")
           which_cam    = param[5]
           config_data  = self.config.read_cache(config="videos")
           
           if param[2] not in config_data:
              response["result"] = "Error: video ID '"+str(param[2])+"' doesn't exist."
              logging.warning("VideoID '"+str(param[2])+"' doesn't exist.")
              
           else:
              response            = self.camera[which_cam].trimVideo(video_id=param[2], start=param[3], end=param[4])
              response["command"] = ["Create short version of video"]
              response["video"]   = { "video_id" : param[2], "start" : param[3], "end" : param[4] }
    
        return response
