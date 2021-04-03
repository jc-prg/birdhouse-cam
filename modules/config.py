#!/usr/bin/python3

import os, time
import logging
import json, codecs

import threading
from threading       import Condition
from datetime        import datetime

from modules.presets import myParameters
from modules.presets import myPages

#----------------------------------------------------

class myConfig(threading.Thread):

   def __init__(self, param_init, main_directory):
       '''
       Initialize new thread and set inital parameters
       '''
       threading.Thread.__init__(self)
       self.param_init     = param_init
       self.locked         = {}
       self.config_cache   = {}
       self.html_replace   = {}
       self.html_replace["start_date"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
       self.directories    = {
           "main"   : "",
           "images" : "images/",
           "backup" : "images/",
           "videos" : "videos/"
           }
       self.files          = {
           "main"   : "config.json",
           "images" : "config_images.json",
           "backup" : "config_images.json"
           }
           
       self.main_directory = main_directory

       if not self.exists("main"):
         logging.info("Create main config file (" + os.path.join(self.main_directory, self.files["main"]) + ") ...")
         self.write("main", self.param_init)
         logging.info("OK.")
         
       self.param          = self.read("main")
       self.main_directory = self.param["path"]
       


   def run(self):
       '''
       Core function (not clear what to do yet)
       '''
       time.sleep(1)
       return       
          
   def reload(self):
       '''
       Reload main configuration
       '''
       self.param = self.read("main")


   def check_locked(self, filename):
       '''
       wait, while a file is locked for writing
       '''
       count = 0
       if filename in self.locked and self.locked[filename]:
         while self.locked[filename]:
            time.sleep(0.2)
            count += 1
            if count > 10:
               logging.warning("Waiting! File '"+filename+"' is locked ("+str(count)+")")
               time.sleep(1)
       return "OK"


   def read_json(self, filename):
       '''
       read json file including check if locked
       '''
       self.check_locked(filename)
       with open(filename) as json_file:
         data = json.load(json_file)
       return data


   def write_json(self, filename, data):
       '''
       write json file including locking mechanism
       '''
       self.check_locked(filename)
       self.locked[filename] = True
       with open(filename, 'wb') as json_file:
            json.dump(data, codecs.getwriter('utf-8')(json_file), ensure_ascii=False, sort_keys=True, indent=4)
       self.locked[filename] = False


   def directory(self, config, date=""):
       '''
       return directory of config file
       '''
       return os.path.join(self.main_directory, self.directories[config], date)


   def directory_create(self, config, date=""):
       '''
       return directory of config file
       '''
       if not os.path.isdir(os.path.join(self.main_directory,self.directory(config))):
          logging.info("Creating directory for " + config + " ...")
          os.mkdir(os.path.join(self.main_directory,self.directory(config)))
          logging.info("OK.")
       
       if date != "" and not os.path.isdir(os.path.join(self.main_directory,self.directory(config),date)):
          logging.info("Creating directory for " + config + " ...")
          os.mkdir(os.path.join(self.main_directory,self.directory(config), date))
          logging.info("OK.")
       

   def file(self, config, date=""):
       '''
       return complete path of config file
       '''
       return os.path.join(self.main_directory, self.directories[config], date, self.files[config])


   def read(self, config, date=""):
       '''
       read dict from json config file
       '''
       config_file = os.path.join(self.main_directory, self.directories[config], date, self.files[config])
       config_data = self.read_json(config_file)
       self.config_cache[config] = config_data
       return config_data


   def write(self, config, config_data, date=""):
       '''
       write dict to json config file
       '''
       config_file = os.path.join(self.main_directory, self.directories[config], date, self.files[config])
       self.write_json(config_file, config_data)
       self.config_cache[config] = config_data


   def write_image(self, config, file_data, date="", time=''):
       '''
       write dict for single file to json config file
       '''
       config_file = os.path.join(self.main_directory, self.directories[config], date, self.files[config])
       config_data = self.read(config=config, date=date)
       config_data[time] = file_data
       self.write(config=config,config_data=config_data,date=date)


   def exists(self, config, date=""):
       '''
       check if config file exists
       '''
       config_file = os.path.join(self.main_directory ,self.directories[config], date, self.files[config])
       return os.path.isfile(config_file)


   def cache(self, config, date=""):
       '''
       return from cache, read file if not in cache already
       '''
       if config in self.config_cache and date == "":
          return self.config_cache[config]

       elif date == "":
          self.config_cache[config] = self.read(config)
          return self.config_cache[config]

       elif config in self.config_cache and date in self.config_cache[config]:
          return self.config_cache[config][date]

       else:
          if not config in self.config_cache: self.config_cache[config] = {}
          self.config_cache[config][date] = self.read(config,date=date)
          return self.config_cache[config][date]

   #------------------------------------

   def imageName(self, type, timestamp, camera=""):
       '''
       set image name
       '''
       if camera != "": camera += '_'
       #camera = "" #>>> im moment noch keine CAM im namen !!!

       if type == "lowres":   return "image_" + camera + timestamp + ".jpg"
       elif type == "hires":  return "image_" + camera + "big_" + timestamp + ".jpeg"
       else:                  return "image_" + camera + timestamp + ".jpg"


   def imageName2Param(self, filename):
       '''
       Analyze image name ...
       '''
       if  filename.endswith(".jpg"):   filename = filename.replace(".jpg","")
       elif filename.endswith(".jpeg"): filename = filename.replace(".jpeg","")
       else:                            return { "error" : "not an image" }

       parts = filename.split("_")
       info  = { "stamp" : '', "type" : 'lowres', "cam" : 'cam1' }
       if len(parts) == 2:
          info["stamp"] = parts[1]
       if len(parts) == 3 and  parts[1] == "big":
          info["stamp"] = parts[2]
          info["type"]  = "hires"
       if len(parts) == 3:
          info["cam"]   = parts[1]
          info["stamp"] = parts[2]
       if len(parts) == 4:
          info["cam"]   = parts[1]
          info["type"]  = "hires"
          info["stamp"] = parts[3]
       return info


#----------------------------------------------------

