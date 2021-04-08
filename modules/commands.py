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


class myCommands(threading.Thread):

    def __init__(self, camera, config, backup):
        '''
        Initialize new thread and set inital parameters
        '''
        threading.Thread.__init__(self)
        self.camera    = camera
        self.config    = config
        self.backup    = backup
        self.which_cam = ""

    #-------------------------------------
    
    def run(self):
        '''
        Do nothing at the moment
        '''
        return
    
    def stop(self):
        '''
        Do nothing at the moment
        '''
        return
    
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

        if param[2] == "current":
           config_data         = self.config.read_cache(config="images")
           response["command"] = ["set/unset favorit", param[3], param[4]]
           if param[3] in config_data:
              config_data[param[3]]["favorit"] = param[4]
              if int(param[4]) == 1: config_data[param[3]]["to_be_deleted"] = 0
              self.config.write(config="images", config_data=config_data)
           else:
              response["error"] = "no image found with stamp "+str(param[3])

        elif param[2] == "backup":
           config_data         = self.config.read_cache(config="backup", date=param[3])
           response["command"] = ["set/unset favorit (backup)", param[5]]
           if param[4] in config_data["files"]:
              config_data["files"][param[4]]["favorit"] = param[5]
              if int(param[5]) == 1: config_data["files"][param[4]]["to_be_deleted"] = 0
              self.config.write(config="backup",config_data=config_data, date=param[3])
           else:
              response["error"] = "no image found with stamp "+str(param[4])

        elif param[2] == "videos":
           config_data         = self.config.read_cache(config="videos")
           response["command"] = ["set/unset favorit (videos)", param[3], param[4]]
           if param[3] in config_data:
              config_data[param[3]]["favorit"] = param[4]
              if int(param[4]) == 1: config_data[param[3]]["to_be_deleted"] = 0
              self.config.write(config="videos", config_data=config_data)
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
              if int(param[4]) == 1: config_data[param[3]]["favorit"] = 0
              self.config.write(config="images", config_data=config_data)
           else:
              response["error"] = "no image found with stamp "+str(param[3])

        elif param[2] == "backup":
           config_data         = self.config.read_cache(config="backup", date=param[3])
           response["command"] = ["mark/unmark for deletion (backup)", param[5]]
           if param[4] in config_data["files"]:
              config_data["files"][param[4]]["to_be_deleted"] = param[5]
              if int(param[5]) == 1: config_data["files"][param[4]]["favorit"] = 0
              self.config.write(config="backup",config_data=config_data, date=param[3])
           else:
              response["error"] = "no image found with stamp "+str(param[4])

        elif param[2] == "videos":
           config_data         = self.config.read_cache(config="videos")
           response["command"] = ["mark/unmark for deletion", param[4]]
           if param[3] in config_data:
              config_data[param[3]]["to_be_deleted"] = param[4]
              if int(param[4]) == 1: config_data[param[3]]["favorit"] = 0
              self.config.write(config="videos", config_data=config_data)
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
        if param[2] == "backup":       response = self.backup.delete_marked_files(date=param[3], delete_not_used=delete_not_used)
        elif param[2] == "today":      response = self.backup.delete_marked_files(date="",       delete_not_used=delete_not_used)
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
    
    def restartCameras(self, server):
        '''
        restart cameras -> not ready yet
        '''        
        param    = server.path.split("/")
        response = {}
        
        logging.info("Restart of camera threads requested ...")
        for cam in self.camera:
           self.camera[cam].stop()

        self.camera = {}
        self.config.reload()
        for cam in self.config.param["cameras"]:
          settings = self.config.param["cameras"][cam]
          self.camera[cam] = myCamera(id=cam, type=settings["type"], record=settings["record"], param=settings, config=config)
          if not camera[cam].error:
             self.camera[cam].start()
             self.camera[cam].param["path"] = config.param["path"]
             self.camera[cam].setText("Restarting ...")
          response["command"] = ["Restart cameras"]

        return response
        
    #-------------------------------------
    
