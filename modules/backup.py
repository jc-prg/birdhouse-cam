#!/usr/bin/python3

import os, time
import logging
import codecs
import string
import cv2

import threading
from datetime        import datetime
from modules.camera  import myCamera
from modules.config  import myConfig

#----------------------------------------------------


class myBackupRestore(threading.Thread):

   def __init__(self, config, camera):
       '''
       Initialize new thread and set inital parameters
       '''
       threading.Thread.__init__(self)
       self.config       = config
       self.camera       = camera
       self.name         = "Backup"
       self._running      = True

   #-----------------------------------

   def run(self):
       '''
       start backup in the background
       '''
       backup_started = False
       while self._running:
         stamp   = datetime.now().strftime('%H%M%S')
         if stamp[0:4] == self.config.param["backup_time"] and not backup_started:
            logging.info("Starting daily backup ...")
            backup_started = True
            self.backup_files()
            logging.info("OK.")
            time.sleep(60)
         else:
            backup_started = False
            
         time.sleep(5)
         
       logging.info("Stopped backup process.")
       

   def stop(self):
       '''
       stop running process
       '''
       self._running=False

   #-----------------------------------

   def compare_files_init(self, date=""):
       '''
       Initial compare files (to create new config file)
       '''

       if date == '': path = self.config.directory(config="images")
       else:          path = self.config.directory(config="backup",date=date)

       file_list = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path,f)) and not "_big" in f]
       file_list.sort(reverse=True)
       files     = self.compare_files(list=file_list, init=True, subdir=date)
       return files


   def compare_files(self, list, init=False, subdir=""):
       '''
       Compare image files and write to config file
       '''

       if os.path.isfile(self.config.file("images")) and subdir == "": files = self.config.read_cache(config='images')
       else:                                                           files = {}

       list = self.update_image_config(list=list, files=files, subdir=subdir)
       if subdir == '': self.config.write(config="images",config_data=files)

       count     = 0
       for cam in self.config.param["cameras"]:
         filenameA = ""
         imageA    = ""
         filenameB = ""
         imageB    = ""

         for time in files:
           if files[time]["camera"] == cam:

              filenameA  = files[time]["lowres"]
              try:
                 filename   = os.path.join(self.config.directory(config="images"), subdir, filenameA)
                 imageA     = cv2.imread(filename)
                 imageA     = cv2.cvtColor(imageA, cv2.COLOR_BGR2GRAY)
              except Exception as e:
                 logging.error("Could not load image: "+filename)
                 logging.error(e)

              if len(filenameB) > 0:
                 score = self.camera[cam].compareRawImages(imageA,imageB)
                 files[time]["compare"]    = (filenameA,filenameB)
                 files[time]["similarity"] = score
                 count += 1
              else:
                 files[time]["compare"]    = (filenameA)
                 files[time]["similarity"] = 0

              if init: logging.info(cam + ": " + filenameA + "  " + str(count) + "/" + str(len(files)) + " - " + str(files[time]["similarity"]) + "%")

              filenameB  = filenameA
              imageB     = imageA

       if subdir == '': self.config.write("images",files)
       return files


   def update_image_config(self, list, files, subdir=""):
       '''
       get image date from file
       '''
       for file in list:
         if ".jpg" in file:

           analyze = self.config.imageName2Param(filename=file)
           if "error" in analyze: continue

           which_cam                  = analyze["cam"]
           time                       = analyze["stamp"]
           files[time]                = {}
           files[time]["camera"]      = which_cam

           if "cam" in file:
              files[time]["lowres"]   = self.config.imageName(type="lowres", timestamp=time, camera=which_cam)
              files[time]["hires"]    = self.config.imageName(type="hires",  timestamp=time, camera=which_cam)
           else:
              files[time]["lowres"]   = self.config.imageName(type="lowres", timestamp=time)
              files[time]["hires"]    = self.config.imageName(type="hires",  timestamp=time)

           if subdir == "":
              file_dir = os.path.join(self.config.directory(config='images'),file)
              timestamp = datetime.fromtimestamp(os.path.getmtime(file_dir))

              files[time]["datestamp"] = timestamp.strftime("%Y%m%d")
              files[time]["date"]      = timestamp.strftime("%d.%m.%Y")
              files[time]["time"]      = timestamp.strftime("%H:%M:%S")

       return files

   #-----------------------------------

   def backup_files(self, other_date=""):
       '''
       Backup files with threshold to folder with date ./images/YYMMDD/
       '''
       if other_date == "": backup_date   = datetime.now().strftime('%Y%m%d')
       else:                backup_date   = other_date
       
       directory = self.config.directory(config="images", date=backup_date)

       if os.path.isdir(directory):
         # if the directory but no config file exists for backup directory create a new one
         if not os.path.isfile(self.config.file(config="backup", date=backup_date)):
            files                             = self.compare_files_init(date=backup_date)
            files_backup                      = { "files" : {}, "info" : {}}
            files_backup["files"]             = files
            files_backup["info"]["count"]     = len(files)
            files_backup["info"]["threshold"] = {}
            for cam in self.camera:
              files_backup["info"]["threshold"][cam] = self.camera[cam].param["similarity"]["threshold"]
            files_backup["info"]["date"]      = backup_date[6:8]+"."+backup_date[4:6]+"."+backup_date[0:4]
            files_backup["info"]["size"]      = sum(os.path.getsize(os.path.join(directory,f)) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory,f)))
            self.config.write(config="backup", config_data=files_backup, date=backup_date)

       # if no directory exists, create directory, copy files and create a new config file (copy existing information)
       else:
         self.config.directory_create(config="images", date=backup_date)
         files        = self.config.read_cache(config="images")
         files_backup = { "files" : {}, "info" : {}}
         stamps       = list(reversed(sorted(files.keys())))
         dir_source   = self.config.directory(config="images")
         count        = 0
         backup_size  = 0

         for cam in self.camera:
           count = 0
           for stamp in stamps:

             if self.camera[cam].selectImage(timestamp=stamp, file_info=files[stamp]) and files[stamp]["datestamp"] == backup_date:
                count      += 1
                update_new  = files[stamp]
                file_lowres = self.config.imageName(type="lowres", timestamp=stamp, camera=cam)
                file_hires  = self.config.imageName(type="hires",  timestamp=stamp, camera=cam)

                if not "similarity" in update_new: update_new["similarity"] = 100
                if not "hires"      in update_new: update_new["hires"]      = file_hires
                if not "favorit"    in update_new: update_new["favorit"]    = 0

                if os.path.isfile(os.path.join(dir_source,file_lowres)):
                   update_new["size"]           = (os.path.getsize(os.path.join(dir_source,file_lowres)) + os.path.getsize(os.path.join(dir_source,file_hires)))
                   backup_size                 += update_new["size"]
                   files_backup["files"][stamp] = update_new

                   os.popen('cp ' + os.path.join(dir_source,file_lowres) + ' ' + os.path.join(directory,file_lowres))
                   os.popen('cp ' + os.path.join(dir_source,file_hires)  + ' ' + os.path.join(directory,file_hires))

           logging.info(cam + ": " +str(count) + " Bilder gesichert (" + str(self.camera[cam].param["similarity"]["threshold"]) + ")")

         files_backup["info"]["date"]      = backup_date[6:8]+"."+backup_date[4:6]+"."+backup_date[0:4]
         files_backup["info"]["count"]     = count
         files_backup["info"]["size"]      = backup_size
         files_backup["info"]["threshold"] = {}
         for cam in self.camera:
           files_backup["info"]["threshold"][cam] = self.camera[cam].param["similarity"]["threshold"]

         self.config.write(config="backup", config_data=files_backup, date=directory)


   #-----------------------------------
   
   def delete_marked_files(self, ftype="image", date="", delete_not_used=False):
       '''
       delete files which are marked to be recycled for a specific date + database entry
       '''       
       response = {}

       if ftype == "image":
         if date == "":  
           files        = self.config.read_cache(config='images')
           directory    = self.config.directory(config='images')
         else:
           config_file  = self.config.read_cache(config='backup', date=date)
           directory    = self.config.directory(config='backup', date=date)
           files        = config_file["files"]
       elif ftype == "video":
         files        = self.config.read_cache(config='videos')
         directory    = self.config.directory(config='videos')
       else:
         response["error"] = "file type not supported"
         
       file_types          = ["lowres","hires","video_file","thumbnail"]
       files_in_dir        = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f)) and not ".json" in f]
       files_in_config     = []
       delete_keys         = []
       
       count = 0
       for key in files:
       
         if date != "": check_date = date[6:8]+"."+date[4:6]+"."+date[0:4]
         if date == "" or ("date" in files[key] and check_date in files[key]["date"]):
           for file_type in file_types:
             if file_type in files[key]: files_in_config.append(files[key][file_type])
                        
         if "to_be_deleted" in files[key] and int(files[key]["to_be_deleted"]) == 1:
            count += 1
            delete_keys.append(key)           
           
       for key in delete_keys:
         try:
           for file_type in file_types:
             if file_type in files[key]: 
               if os.path.isfile(os.path.join(directory, files[key][file_type])):
                 os.remove(os.path.join(directory, files[key][file_type]))
                 logging.debug("Delete - " + str(key) + ": " + os.path.join(directory, files[key][file_type]))
           del files[key]
             
         except Exception as e:
           if not "error" in response: response["error"] = ""
           logging.error("Error while deleting file '" + key + "' ... " + str(e))
           response["error"] += "delete file '" + key + "': " + str(e) + "\n"

       if delete_not_used:
         for file in files_in_dir:
           if file not in files_in_config:
             os.remove(os.path.join(directory, file))
             
       print(str(len(files_in_dir))+"/"+str(len(files_in_config)))           
            
       response["deleted_count"]  = count
       response["deleted_keys"]   = delete_keys
       response["files_not_used"] = len(files_in_dir) - len(files_in_config)
       response["files_used"]     = len(files_in_config)
       
       if ftype == "image":
         if date == "":
           self.config.write(config='images', config_data=files)
         else:
           config_file["files"] = files
           self.config.write(config='backup', config_data=config_file, date=date)
       elif ftype == "video":
         self.config.write(config='videos', config_data=files)

       logging.info("Deleted " + str(count) + " marked files in " + directory + ".")
       return response
