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
        self.name           = "Commands"
        self.camera         = camera
        self.config         = config
        self.backup         = backup
        self._running       = True
        self.which_cam      = ""
        self.status_queue           = {}
        self.status_queue["images"] = []
        self.status_queue["videos"] = []
        self.status_queue["backup"] = {}
        self.create_queue           = []       
        self.create_day_queue       = []       

    #-------------------------------------
    
    def run(self):
        '''
        Do nothing at the moment
        '''
        logging.info("Starting REST API for POST ...")
        config_files = ["images","videos","backup"]
        while self._running:
           time.sleep(10)
           
           # create short videos
           if len(self.create_day_queue) > 0:
             self.config.async_running = True
             [ which_cam, filename, stamp, date ] = self.create_day_queue.pop()
             response = self.camera[which_cam].createDayVideo(filename=filename, stamp=stamp, date=date)
             if response["result"] == "OK":  self.config.async_answers.append(["CREATE_DAY_DONE", date, response["result"]])
             else:                           self.config.async_answers.append(["CREATE_DAY_ERROR", date, response["result"]])
             self.config.async_running = False
             time.sleep(1)
           
           # create short videos
           if len(self.create_queue) > 0:
             self.config.async_running = True
             [ which_cam, video_id, start, end ] = self.create_queue.pop()
             logging.info("Start video creation ("+video_id+"): "+str(start)+" - "+str(end)+")")
             response = self.camera[which_cam].trimVideo(video_id, start, end)
             logging.info(str(response))
             self.config.async_answers.append(["TRIM_DONE", video_id, response["result"]])
             self.config.async_running = True
             time.sleep(1)
           
           # status changes
           for config_file in config_files:
           
             if config_file != "backup": 
                entries = self.config.read_cache(config_file)
                self.config.lock(config_file)
             
                while len(self.status_queue[config_file]) > 0:
                   [ date, key, change_status, status ] = self.status_queue[config_file].pop()
                   if key in entries: 
                      test = "yes"
                      entries[key][change_status] = status
                   else:
                      test="no"
                   logging.debug("QUEUE: "+config_file+" // "+key+" - "+change_status+"="+str(status)+" ... "+test)
                   
                self.config.unlock(config_file)
                self.config.write(config_file, entries)   
                
             else:
                for date in self.status_queue[config_file]:
                   entry_data = self.config.read_cache(config_file,date)
                   entries    = entry_data["files"]
                   self.config.lock(config_file,date)
                   while len(self.status_queue[config_file][date]) > 0:
                      [ date, key, change_status, status ] = self.status_queue[config_file][date].pop()
                      if key in entries: 
                         test = "yes"
                         entries[key][change_status] = status
                      else:
                         test="no"
                      logging.debug("QUEUE: "+config_file+"/"+date+" // "+key+" - "+change_status+"="+str(status)+" ... "+test)
                   
                   entry_data["files"] = entries
                   self.config.unlock(config_file, date)
                   self.config.write(config_file, entry_data, date)   
                           
        logging.info("Stopped REST API for POST.")
    

    def stop(self):
        '''
        Do nothing at the moment
        '''
        self._running = False
    
    #-------------------------------------

    def addToQueue( self, config, date, key, change_status, status ):
        '''
        add entry to queue
        '''
        if config != "backup": 
           self.status_queue[config].append( [ date, key, change_status, status ] )
        elif config == "backup":
           if not date in self.status_queue[config]: self.status_queue[config][date] = []
           self.status_queue[config][date].append( [ date, key, change_status, status ] )
    
    #-------------------------------------
    
    def adminAllowed(self):
        '''
        Check if administration is allowed based on the IP4 the request comes from
        '''
        logging.debug("Check if administration is allowed: "+self.address_string()+" / "+str(config.param["ip4_admin_deny"]))
        if self.address_string() in config.param["ip4_admin_deny"]: return False
        else:                                                       return True

    #-------------------------------------
    
    def setStatusFavoritNew(self, server):
        '''
        set / unset favorit -> redesigned
        '''        
        param    = server.path.split("/")
        response = {}
        category = param[2]
        
        if category == "current": 
           entry_id    = param[3]
           entry_value = param[4]
           entry_date  = ""
           category    = "images"
        elif category == "videos": 
           entry_id    = param[3]
           entry_value = param[4]
           entry_date  = ""
        else:
           entry_date  = param[3]
           entry_id    = param[4]
           entry_value = param[5]
           
        if category == "images":   config_data = self.config.read_cache(config="images")
        elif category == "backup": config_data = self.config.read_cache(config="backup", date=entry_date)["files"]
        elif category == "videos": config_data = self.config.read_cache(config="videos")
        
        response["command"] = ["mark/unmark as favorit", entry_id]
        if entry_id in config_data:
           self.addToQueue( config=category, date=entry_date, key=entry_id, change_status="favorit", status=entry_value)
           if entry_value == 1:
              self.addToQueue( config=category, date=entry_date, key=entry_id, change_status="to_be_deleted", status=1)
        else:
           response["error"]   = "no entry found with stamp "+entry_id

        return response        


    #-------------------------------------
    
    def setStatusRecycleNew(self, server):
        '''
        set / unset recycling -> redesigned
        '''        
        param    = server.path.split("/")
        response = {}
        category = param[2]
        
        if category == "current": 
           entry_id    = param[3]
           entry_value = param[4]
           entry_date  = ""
           category    = "images"
        elif category == "videos": 
           entry_id    = param[3]
           entry_value = param[4]
           entry_date  = ""
        else:
           entry_date  = param[3]
           entry_id    = param[4]
           entry_value = param[5]
           
        if category == "images":   config_data = self.config.read_cache(config="images")
        elif category == "backup": config_data = self.config.read_cache(config="backup", date=entry_date)["files"]
        elif category == "videos": config_data = self.config.read_cache(config="videos")
        
        logging.info("test:"+entry_date)
        
        response["command"] = ["mark/unmark for deletion", entry_id]
        if entry_id in config_data:
           logging.info("OK")
           self.addToQueue( config=category, date=entry_date, key=entry_id, change_status="to_be_deleted", status=entry_value)
           if entry_value == 1:
              self.addToQueue( config=category, date=entry_date, key=entry_id, change_status="favorit", status=1)
        else:
           response["error"]   = "no entry found with stamp "+entry_id

        return response        


    #-------------------------------------
    
    def setStatusRecycleRange(self, server):
        '''
        set / unset recycling -> range from-to
        '''        
        param    = server.path.split("/")
        response = {}
        category = param[2]
        
        if category == "current": 
           entry_from  = param[3]
           entry_to    = param[4]
           entry_value = param[5]
           entry_date  = ""
           category    = "images"
        elif category == "videos": 
           entry_from  = param[3]
           entry_to    = param[4]
           entry_value = param[5]
           entry_date  = ""
        else:
           entry_date  = param[3]
           entry_from  = param[4]
           entry_to    = param[5]
           entry_value = param[6]
           
        if category == "images":   config_data = self.config.read_cache(config="images")
        elif category == "backup": config_data = self.config.read_cache(config="backup", date=entry_date)["files"]
        elif category == "videos": config_data = self.config.read_cache(config="videos")
        
        response["command"] = ["mark/unmark for deletion", entry_from, entry_to]
        if entry_from in config_data and entry_to in config_data:
           relevant = False
           stamps   = list(reversed(sorted(config_data.keys())))
           for entry_id in stamps:
               if entry_id == entry_from: relevant = True
               if relevant:
                  self.addToQueue(config=category, date=entry_date, key=entry_id, change_status="to_be_deleted", status=1)
                  self.addToQueue(config=category, date=entry_date, key=entry_id, change_status="favorit", status=0)
               if entry_id == entry_to:   relevant = False
        else:
           response["error"]   = "no entry found with stamp "+entry_from+"/"+entry_to

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
    
    def createDayVideo(self, server):
        '''
        create a video of all existing images of the day
        '''
        param        = server.path.split("/")
        response     = {}
        logging.info(str(param))
        
        if len(param) < 3:
           response["result"] = "Error: Parameters are missing (/create-short-video/video-id/start-timecode/end-timecode/which-cam/)"
           logging.warning("Create video of daily images ... Parameters are missing.")
           
        else:
           which_cam   = param[2]
           stamp       = datetime.now().strftime('%Y%m%d_%H%M%S')
           date        = datetime.now().strftime('%d.%m.%Y')
           filename    = "image_"+which_cam+"_big_"
           
           self.create_day_queue.append([ which_cam, filename, stamp, date ])

           response["command"] = ["Create video of the day"]
           response["video"]   = { "camera" : which_cam, "date" : date }
           
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
              self.create_queue.append([ which_cam, param[2], param[3], param[4] ])
              #response            = self.camera[which_cam].trimVideo(video_id=param[2], start=param[3], end=param[4])
              response["command"] = ["Create short version of video"]
              response["video"]   = { "video_id" : param[2], "start" : param[3], "end" : param[4] }
    
        return response
