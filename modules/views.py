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


#----------------------------------------------------

dir_app_v1 = "/app-v1"

#----------------------------------------------------

def read_html(filename, content=""):
   '''
   read html file, replace placeholders and return for stream via webserver
   '''
   if not os.path.isfile(filename):
     logging.warning("File '"+filename+"' does not exist!")
     return ""

   with open(filename, "r") as page:
     PAGE = page.read()
     
   if content != "":
     for param in content:
       if "<!--"+param+"-->" in PAGE: PAGE = PAGE.replace("<!--"+param+"-->",content[param])
       
   #PAGE = PAGE.encode('utf-8')
   return PAGE

#----------------------------------------------------


class myViews(threading.Thread):

    def __init__(self, camera, config):
        '''
        Initialize new thread and set inital parameters
        '''
        threading.Thread.__init__(self)
        self._running  = True
        self.name      = "Views"
        self.camera    = camera
        self.config    = config
        self.which_cam = ""

    #-------------------------------------
    
    def run(self):
        '''
        Do nothing at the moment
        '''
        logging.info("Starting HTML views and REST API for GET ...")
        while self._running:
           time.sleep(1)
        logging.info("Stopped HTML views and REST API for GET.")
        
            
    def stop(self):
        '''
        Do nothing at the moment
        '''
        self._running = False
    
    #-------------------------------------
    
    def adminAllowed(self):
        '''
        Check if administration is allowed based on the IP4 the request comes from
        '''
        logging.debug("Check if administration is allowed: " + self.server.address_string() + " / " + str(self.config.param["ip4_admin_deny"]))
        if self.server.address_string() in self.config.param["ip4_admin_deny"]: return False
        else:                                                                   return True


    def selectedCamera(self, check_path=""):
        '''
        Check path, which cam has been selected
        '''
        if check_path == "": path = self.server.path
        else:                path = check_path
        
        if "?" in path:
           param       = path.split("?")
           path        = param[0]
           which_cam   = param[1]
           if not which_cam in self.camera:
              logging.warning("Unknown camera requested.")
              return path, ""
              
        elif "/api" in path and not "/api/status" in path:
           param        = path.split("/")
           if len(param) > 3:
              which_cam = param[3]
           if not which_cam in self.camera or len(param) <= 3:
              logging.warning("Unknown camera requested.")
              return path, ""
        
        else:
           which_cam = "cam1"
               
        self.active_cams = []
        for key in self.camera:
          if self.camera[key].active: self.active_cams.append(key)
        if self.camera[which_cam].active == False:
          which_cam = self.active_cams[0]
        
        if check_path == "": logging.debug("Selected CAM = " + which_cam + " (" + self.server.path + ")")
        else:                logging.debug("Selected CAM = " + which_cam + " (" + check_path + ")")
        
        self.which_cam  = which_cam
        return path, which_cam

    #-------------------------------------

    def printLinks(self, link_list, current="", cam=""):
        '''
        create a list of links based on URLs and descriptions defined in preset.py
        '''
        html  = ""
        count = 0
        if cam != "": cam_link = '?' + cam
        else:         cam_link = ""
        
        for link in link_list:
            count += 1
            html  += "<a href='"+myPages[link][1]+cam_link+"'>"+myPages[link][0]+"</a>"
            if count < len(link_list): html += " / "

        if current != "" and len(self.active_cams) > 1:
           selected   = self.active_cams.index(cam) + 1 
           if selected >= len(self.active_cams): selected = 0
           html  += " / <a href='"+dir_app_v1+"/"+myPages[current][1]+"?"+self.active_cams[selected]+"'>"+self.active_cams[selected].upper()+"</a>"

        return html


    def printLinksJSON(self, link_list, cam=""):
        '''
        create a list of links based on URLs and descriptions defined in preset.py -> for JSON API
        '''
        json  = {}
        count = 0
        if cam != "": cam_link = cam
        else:         cam_link = ""
        
        for link in link_list:
            json[link] = {}
            json[link]["link"]        = myPages[link][2]
            json[link]["camera"]      = cam_link
            json[link]["description"] = myPages[link][0]
            json[link]["position"]    = count
            count += 1
            
        return json


    def printStar(self,file="",favorit=0,cam=""):
        '''
        check if the image is marked as favorit and create html/javascript elements to show and change the favorit status
        '''
        stamp = file.split("/")
        if "app-v1" in stamp: del stamp[1]
        stamp = stamp[len(stamp)-1]
        if int(favorit) == 1:
           star    = dir_app_v1+"/star1.png"
           value   = "0"
        else:
           star    = dir_app_v1+"/star0.png"
           value   = "1"
           
        if "/videos/" in file: img_id = self.config.imageName(type="thumb",  timestamp=stamp, camera=cam)
        else:                  img_id = self.config.imageName(type="lowres", timestamp=stamp, camera=cam)
        
        if self.adminAllowed():
           onclick = "setFavorit(\"" + file + "\",document.getElementById(\"s_" + file + "_value\").innerHTML,\"" + img_id + "\");"
           return "<div class='star'><div id='s_" + file + "_value' style='display:none;'>" + value + "</div><img class='star_img' id='s_" + file + "' src='" + star + "' onclick='" + onclick + "'/></div>\n"
        else:
           onclick = ""
           if int(favorit) == 1:
              return "<div class='star'><div id='s_" + file + "_value' style='display:none;'>" + value + "</div><img class='star_img' id='s_" + file + "' src='" + star + "' onclick='" + onclick + "'/></div>\n"
           else:
              return "<div class='star'></div>\n"


    def printRecycle(self,file="",recycle=0,cam=""):
        '''
        check if the image is marked as to be recycled and create html/javascript elements to show and change the favorit status
        '''
        stamp = file.split("/")
        if "app-v1" in stamp: del stamp[1]
        stamp = stamp[len(stamp)-1]
        if int(recycle) == 1:
           trash   = dir_app_v1+"/recycle1.png"
           value   = "0"
        else:
           trash   = dir_app_v1+"/recycle0.png"
           value   = "1"
           
        if "/videos/" in file: img_id = self.config.imageName(type="thumb",  timestamp=stamp, camera=cam)
        else:                  img_id = self.config.imageName(type="lowres", timestamp=stamp, camera=cam)
        
        if self.adminAllowed():
           onclick = "setRecycle(\"" + file + "\",document.getElementById(\"d_" + file + "_value\").innerHTML,\"" + img_id + "\");"
           return "<div class='trash'><div id='d_" + file + "_value' style='display:none;'>" + value + "</div><img class='trash_img' id='d_" + file + "' src='" + trash + "' onclick='" + onclick + "'/></div>\n"
        else:
           return "<div class='trash'></div>\n"


    def printImageContainer(self, description, lowres, hires='', javascript='' ,star='', trash='', window='self', lazzy='', border='black'):
        '''
        create an image container include elements to change favorit and recycle status
        '''
        html = "<div class='image_container'>\n"
        if star  != '':      html += star
        else:                html += "<div class='star'></div>"
        if trash  != '':     html += trash
        else:                html += "<div class='trash'></div>"
        if lazzy == 'lazzy': lazzy = "data-"
        else:                lazzy = ""
        
        lowres_file = lowres.split("/")
        lowres_file = lowres_file[len(lowres_file)-1]
        
        if ".mp4" in javascript: play = "<img src=\""+dir_app_v1+"/play.png\" class=\"play_button\" onclick='javascript:" + javascript + "'/>\n"
        else:                    play = ""
        
        html += "<div class='thumbnail_container'>\n"
        if lowres == "EMPTY":
          html += "<div class='thumbnail' style='background-color:#222222;'><br/><br/><small>"+description+"</small></div>"
        else:
          if hires != '':        html += "<a href='" + hires + "' target='_" + window + "'><img " + lazzy + "src='" + lowres + "' id='" + lowres_file + "' class='thumbnail' style='border:1px solid " + border + ";'/></a><br/><small>" + description + "</small>"
          elif javascript != '': html += "<a onclick='javascript:" + javascript + "' style='cursor:pointer;'><img " + lazzy + "src='" + lowres + "' id='" + lowres_file + "' class='thumbnail' style='border:1px solid " + border + ";'/></a><br/>" + play + "<small>"+description+"</small>"
          else:                  html += "<img " + lazzy + "src='" + lowres + "' id='" + lowres_file + "' class='thumbnail' style='border:1px solid " + border + ";'/><br/><small>" + description + "</small>"


        html += "\n</div>\n"
        html += "</div>\n"
        return html


    def printImageGroup(self, title, group_id, image_group, category, header=True, header_open=False, header_count=['all','star','detect','recycle'], cam='', intro=''):
        '''
        create html for a list of images including all checks
        '''
        id_list     = images     = display     = ""
        count       = { 'all' : 0, 'star' : 0, 'detect' : 0, 'recycle' : 0 }
        color       = { 'all' : 'white', 'star' : 'lime', 'detect' : 'aqua', 'recycle' : 'red' }

        stamps = list(reversed(sorted(image_group.keys())))
        for stamp in stamps:
           border      = "black"
           description = lowres = hires = javascript = lazzy = ""
           
### <<<<>>>> Check, why those vars are not initialized before self.printImageContainer ~line 300
# >>> compare config_videos.json!
# >>> sth went wrong during recording (video and thumb doesn't exist any more, record with "autostop")

           if "_" in stamp: 
              stamp_date, stamp_time = stamp.split("_")
              time       = stamp_date[6:8] + "." + stamp_date[4:6] + "." + stamp_date[0:4] + " " + stamp_time[0:2] + ":" + stamp_time[2:4]
              time      += "<br/>"
           else:
              if "datestamp" in image_group[stamp]:  stamp_date = image_group[stamp]["datestamp"]
              else:                                  stamp_date = ""
              stamp_time = stamp
              time       = stamp_time[0:2] + ":" + stamp_time[2:4] + ":" + stamp_time[4:6]
           
           if "backup" in category:  url_dir = os.path.join(self.config.directories["backup"], stamp_date)
           elif "video" in category: url_dir = self.config.directories["videos"]
           else:                     url_dir = self.config.directories["images"]
           
           # addons, e.g. small live stream with special links
           if "type" in image_group[stamp] and image_group[stamp]["type"] == "addon":
              entry       = image_group[stamp]
              description = entry["title"]
              lowres      = entry["lowres"]
              hires       = entry["hires"]
              javascript  = star = trash = lazzy = ""

           # images and videos
           else:
             
             if "video_file" in image_group[stamp]:  stamp_file = stamp
             else:                                   stamp_file = stamp_time
           
             if "favorit" in image_group[stamp]:
                if "camera" in image_group[stamp]: selected_cam = image_group[stamp]["camera"]
                else:                              selected_cam = cam
                star   = self.printStar(file=category+stamp_file, favorit=image_group[stamp]["favorit"], cam=selected_cam)
                if int(image_group[stamp]["favorit"]) == 1: 
                   border         = "lime"
                   count["star"] += 1
             else:
                star   = self.printStar(file=category+stamp_file, favorit=0, cam=cam)
                
             if "to_be_deleted" in image_group[stamp]:
                if "camera" in image_group[stamp]: selected_cam = image_group[stamp]["camera"]
                else:                              selected_cam = cam
                trash  = self.printRecycle(file=category+stamp_file, recycle=image_group[stamp]["to_be_deleted"], cam=selected_cam)
                if int(image_group[stamp]["to_be_deleted"]) == 1:
                   border            = "red"
                   count["recycle"] += 1
             else:
                trash  = self.printRecycle(file=category+stamp_file, recycle=0, cam=cam)

             # if image
             if "lowres" in image_group[stamp] and "similarity" in image_group[stamp]:
             
                threshold  = self.camera[cam].param["similarity"]["threshold"]
                similarity = str(image_group[stamp]["similarity"])+'%'                
                if float(image_group[stamp]["similarity"]) < float(threshold) and float(image_group[stamp]["similarity"]) > 0:
                   if border == "black":
                      border           = "aqua"
                      count["detect"] += 1

                hires        = ""
                description  = time + " ("+similarity+")"
                lowres       = os.path.join("/", url_dir, image_group[stamp]["lowres"])
                if "hires" in image_group[stamp]:
                   hires      = "" # image_group[stamp]["hires"]
                   javascript ="imageOverlay(\"" + os.path.join("/", url_dir, image_group[stamp]["hires"]) + "\",\"" + description + "\");"
                   
             # if video
             elif "video_file_short" in image_group[stamp]:
                description = image_group[stamp]["date"].replace(" ","<br/>") + "<br/>" + image_group[stamp]["camera"].upper() + ": " + image_group[stamp]["camera_name"] + "*"
                #description = "<a href=\"/"+stamp+"/video-info.html\">" + description + "</a>"
                description = "<a href=/"+stamp+"/video-info.html>" + description + "</a>"
                lowres      = "videos/" + image_group[stamp]["thumbnail"]
                hires       = ""
                video_link  = self.camera[cam].param["video"]["streaming_server"] + image_group[stamp]["video_file_short"]
                javascript  = "videoOverlay(\"" + video_link + "\",\"" + description + "\");"
                image_group[stamp]["lowres"] = image_group[stamp]["thumbnail"]

             elif "video_file" in image_group[stamp]:
                description = image_group[stamp]["date"].replace(" ","<br/>") + "<br/>" + image_group[stamp]["camera"].upper() + ": " + image_group[stamp]["camera_name"]
                #description = "<a href=\"/"+stamp+"/video-info.html\">" + description + "</a>"
                description = "<a href=/"+stamp+"/video-info.html>" + description + "</a>"
                lowres      = "videos/" + image_group[stamp]["thumbnail"]
                hires       = ""
                video_link  = self.camera[cam].param["video"]["streaming_server"] + image_group[stamp]["video_file"]
                javascript  = "videoOverlay(\"" + video_link + "\",\"" + description + "\");"
                image_group[stamp]["lowres"] = image_group[stamp]["thumbnail"]

             if header and not header_open:
                display    = "style='display:none;'"
                id_list   += image_group[stamp]["lowres"] + " "
                lazzy      = "lazzy"
             else:
                lazzy      = ""

           images += self.printImageContainer(description=description, lowres=lowres, hires=hires, star=star, trash=trash, javascript=javascript, lazzy=lazzy, border=border)

        html = ""
        if header:
          if header_open: sign = "−"
          else:           sign = "+"
          count["all"]         = len(image_group)

          onclick = "onclick='showHideGroup(\"" + group_id + "\")'"
          html   += "\n\n<div class='separator_group' "+onclick+">"
          html   += "<a id='group_link_" + group_id + "' style='cursor:pointer;'>(" + sign + ")</a> "
          html   += title
          html   += "<font color='gray'> &nbsp; &nbsp; [";
          i = 0
          for c in header_count:
            if c in count:
              color_p = "gray"
              fill    = 2
              if count[c] > 0: color_p = color[c]
              if c == "all"  : fill    = 3
              html += c + ": <font color='"+color_p+"'>"+str(count[c]).zfill(fill) + "</font>"
              i    += 1
              if i < len(header_count): html += " | "
            else:
              logging.warning("imageGroup: header_count="+str(c)+" value doesn't exist")
              html += "all: <font color='white'>"+str(count['all']).zfill(3) + "</font> "
              break
          html   += "]</font>";
          html   += "</div>\n"

        if intro != "": html += "<div  id='group_intro_" + group_id + "' class='separator' style='display:none;'>"+intro+"</div>"
        html   += "<div id='group_ids_" + group_id + "' style='display:none;'>"+id_list+"</div>\n"             
        html   += "<div id='group_" + group_id + "' " + display + "><div class='separator'>&nbsp;</div>"+images+"</div>\n"
        return html

    #-------------------------------------
    #--------------------------------------
    
    def createIndex(self, server):
        '''
        Index page with live streaming pictures
        '''        
        self.server           = server
        path, which_cam       = self.selectedCamera()
        content               = {}
        content["active_cam"] = which_cam
        content["view"]       = "index"
        
        if self.camera["cam1"].active and self.camera["cam2"].active:
           if which_cam == "cam1":        template = dir_app_v1+"/index_cam1+cam2.html"
           elif which_cam == "cam2":      template = dir_app_v1+"/index_cam2+cam1.html"
           else:                          template = dir_app_v1+"/index.html"
           
        else:
           template = dir_app_v1+"/index.html"
           
        if self.adminAllowed():
           content["links"]       = self.printLinks(link_list=("favorit","today","backup","cam_info"), cam=which_cam)
           content["links_json"]  = self.printLinksJSON(link_list=("favorit","today","backup","cam_info"), cam=which_cam)
           content["record"]      = "<br/>" + which_cam.upper() + ": <button onclick='requestAPI(\"/start/recording/" + which_cam + "\");'>Record</button> &nbsp;"
           content["record"]      += "<button onclick='requestAPI(\"/stop/recording/" + which_cam + "\");'>Stop</button>"
        else:
           content["links"]       = self.printLinks(link_list=("favorit","today","backup"), cam=which_cam)
           content["links_json"]  = self.printLinksJSON(link_list=("favorit","today","backup"), cam=which_cam)
        

        return template, content

    #--------------------------------------

    def createFavorits(self, server):
        '''
        Page with pictures (and videos) marked as favorits and sorted by date
        '''
        self.server           = server
        path, which_cam       = self.selectedCamera()
        content               = {
            "active_cam"        : which_cam,
            "view"              : "favorits",
            "entries"           : {},
            "groups"            : {}
            }
        template              = "list.html"
        html                  = ""
        favorits              = {}

        # videos
        directory       = self.config.directory(config="videos")
        category        = "/videos/"
        files_all       = {}
        files_videos    = {}
                  
        if self.config.exists("videos"):
           files_all = self.config.read_cache(config="videos")
           for file in files_all:
               date = file.split("_")[0]
               if "favorit" in files_all[file] and int(files_all[file]["favorit"]) == 1: 
                  if not date in files_videos: files_videos[date] = {}
                  files_videos[date][file] = files_all[file]
          
        # today
        date_today = datetime.now().strftime("%Y%m%d")
        files      = self.config.read_cache(config="images")
        category   = "/current/"
        
        for stamp in files:
            if date_today == files[stamp]["datestamp"] and "favorit" in files[stamp] and int(files[stamp]["favorit"]) == 1:
               new = datetime.now().strftime("%Y%m%d")+"_"+stamp
               favorits[new]              = files[stamp]
               favorits[new]["source"]    = ("images","")
               favorits[new]["date"]      = "Aktuell"
               favorits[new]["time"]      = stamp[0:2]+":"+stamp[2:4]+":"+stamp[4:6]
               favorits[new]["type"]      = "image"
               favorits[new]["category"]  = category+stamp
               favorits[new]["directory"] = "/"+self.config.directories["images"]

        if date_today in files_videos:
          for stamp in files_videos[date_today]:
               new = stamp
               favorits[new]              = files_videos[date_today][stamp]
               favorits[new]["source"]    = ("videos","")
               favorits[new]["date"]      = "Aktuell"
               favorits[new]["time"]      = stamp[0:2]+":"+stamp[2:4]+":"+stamp[4:6]
               favorits[new]["type"]      = "video"
               favorits[new]["category"]  = category+stamp
               favorits[new]["directory"] = "/"+self.config.directories["videos"]

        if len(favorits) > 0:
           html += self.printImageGroup(title="Heute &nbsp; &nbsp; &nbsp; &nbsp;", group_id="today", image_group=favorits, category=category, header=True, header_open=True, header_count=['star'], cam=which_cam)

           content["view_count"]      = ["star"]           
           content["groups"]["today"] = []
           for entry in favorits: 
             content["entries"][entry] = favorits[entry]
             content["groups"]["today"].append(entry)
             
        # other days
        main_directory = self.config.directory(config="backup")
        dir_list       = [f for f in os.listdir(main_directory) if os.path.isdir(os.path.join(main_directory, f))]
        dir_list       = list(reversed(sorted(dir_list)))
        
        video_list = []
        for file_date in files_videos:
          if file_date not in dir_list:
            dir_list.append(file_date)
            video_list.append(file_date)
        
        dir_list       = list(reversed(sorted(dir_list)))

        logging.error("---")
        logging.error(str(dir_list))
        logging.error(str(video_list))
                
        for directory in dir_list:
            category            = "/backup/"+directory+"/"
            favorits[directory] = {}
            
            if self.config.exists(config="backup", date=directory):
               files_data = self.config.read_cache(config="backup", date=directory)
               if "info" in files_data and "files" in files_data:
                 files      = files_data["files"]
                 date       = directory[6:8]+"."+directory[4:6]+"."+directory[0:4]
                 
                 if directory not in video_list:
                   for stamp in files:
                    if "datestamp" in files[stamp] and files[stamp]["datestamp"] == directory:
                      if "favorit" in files[stamp] and int(files[stamp]["favorit"]) == 1:
                        new = directory+"_"+stamp
                        favorits[directory][new]              = files[stamp]
                        favorits[directory][new]["source"]    = ("backup",directory)
                        favorits[directory][new]["date"]      = date
                        favorits[directory][new]["time"]      = stamp[0:2]+":"+stamp[2:4]+":"+stamp[4:6]
                        favorits[directory][new]["date2"]     = favorits[directory][new]["date"]
                        favorits[directory][new]["type"]      = "image"
                        favorits[directory][new]["category"]  = category+stamp
                        favorits[directory][new]["directory"] = "/"+self.config.directories["backup"]+directory+"/"

            if directory in files_videos:
                   for stamp in files_videos[directory]:
                     new   = stamp
                     date  = directory[6:8]+"."+directory[4:6]+"."+directory[0:4]
                     favorits[directory][new]              = files_videos[directory][stamp]
                     favorits[directory][new]["source"]    = ("videos","")
                     favorits[directory][new]["date"]      = date  #?????
                     favorits[directory][new]["time"]      = stamp[0:2]+":"+stamp[2:4]+":"+stamp[4:6]
                     favorits[directory][new]["type"]      = "video"
                     favorits[directory][new]["category"]  = "/videos/"+stamp
                     favorits[directory][new]["directory"] = "/"+self.config.directories["videos"]
                     
            if len(favorits[directory]) > 0:
                    html += self.printImageGroup(title=date, group_id=directory, image_group=favorits[directory], category=category, header=True, header_open=True, header_count=['star'], cam=which_cam)
                    
                    content["groups"][date] = []
                    for entry in favorits[directory]:
                      content["entries"][entry] = favorits[directory][entry]
                      content["groups"][date].append(entry)


        content["view_count"]  = ["star"]           
        content["subtitle"]    = myPages["favorit"][0]
        content["links"]       = self.printLinks(link_list=("live","today","videos","backup"), cam=which_cam)
        content["links_json"]  = self.printLinksJSON(link_list=("live","today","videos","backup"), cam=which_cam)
        content["file_list"]   = html
        
        return template, content

    #--------------------------------------

    def createList(self, server):
        '''
        Page with pictures (and videos) of a single day
        '''
        self.server           = server
        param                 = server.path.split("/")
        if "app-v1" in param: del param[1]
        path, which_cam       = self.selectedCamera()

        if param[1] != "api":
           if len(param) > 2: date_backup = param[2]
           else:              date_backup = ""
        else:
           if len(param) > 4: date_backup = param[4]
           else:              date_backup = ""

        content               = {
            "active_cam"        : which_cam,
            "active_date"       : date_backup,
            "view"              : "list",
            "entries"           : {},
            "entries_delete"    : {},
            "entries_yesterday" : {}
            }
        template              = "list.html"
        html                  = ""
        files_all             = {}
        count                 = 0

        date_today      = datetime.now().strftime("%Y%m%d")
        date_yesterday  = (datetime.today() - timedelta(days=1)).strftime("%Y%m%d")   
        
        if date_backup != "":
           backup           = True
           path             = self.config.directory(config="backup", date=date_backup)
           files_data       = self.config.read_cache(config="backup", date=date_backup)
           files_all        = files_data["files"]
           check_similarity = False
           category         = "/backup/" + date_backup + "/"
           subdirectory     = date_backup + "/"
           time_now         = "000000"
           first_title      = ""

           content["subtitle"]    = myPages["backup"][0] + " " + files_data["info"]["date"] + " (" + self.camera[which_cam].name + ", " + str(files_data["info"]["count"]) + " Bilder)"
           content["links"]       = self.printLinks(link_list=("live","today","backup","favorit"), current='backup', cam=which_cam)
           content["links_json"]  = self.printLinksJSON(link_list=("live","today","backup","favorit"), cam=which_cam)

        elif os.path.isfile(self.config.file(config="images")):
           backup           = False
           path             = self.config.directory(config="images")
           files_all        = self.config.read_cache(config="images")
           time_now         = datetime.now().strftime('%H%M%S')
           check_similarity = True
           category         = "/current/"
           subdirectory     = ""
           first_title      = "Heute &nbsp; "

           content["subtitle"]    = myPages["today"][0] + " (" + self.camera[which_cam].name + ")"
           if self.adminAllowed():
              content["links"]      = self.printLinks(link_list=("live","favorit","today_complete","videos","backup"), current='today', cam=which_cam)
              content["links_json"] = self.printLinksJSON(link_list=("live","favorit","today_complete","videos","backup"), cam=which_cam)
           else:
              content["links"]      = self.printLinks(link_list=("live","favorit","videos","backup"), current='today', cam=which_cam)
              content["links_json"] = self.printLinksJSON(link_list=("live","favorit","videos","backup"), cam=which_cam)

        if files_all != {}:

           # Today or backup
           files_today     = {}
           html_today      = ""              
           stamps          = list(reversed(sorted(files_all.keys())))
           
           for stamp in stamps:
           
             if not "datestamp" in files_all[stamp]: files_all[stamp]["datestamp"] = date_backup
             if not "date" in files_all[stamp]:      files_all[stamp]["date"]      = date_backup[6:8]+"."+date_backup[4:6]+"."+date_backup[0:4]
             
             if ((int(stamp) < int(time_now) or time_now == "000000") and files_all[stamp]["datestamp"] == date_today) or files_all[stamp]["datestamp"] == date_backup:
               if not "camera" in files_all[stamp] or self.camera[which_cam].selectImage(timestamp=stamp, file_info=files_all[stamp], check_similarity=check_similarity):
                 if files_all[stamp]["datestamp"] == date_today or backup:
                    files_today[stamp]              = files_all[stamp]
                    files_today[stamp]["type"]      = "image"
                    files_today[stamp]["category"]  = category+stamp
                    files_today[stamp]["detect"]    = self.camera[which_cam].detectImage(file_info=files_today[stamp])
                    files_today[stamp]["directory"] = "/" + self.config.directories["images"] + subdirectory
                    count += 1
                    
           if first_title == "":
              first_title = files_all[stamp]["date"]
              
           elif not backup:
              files_today["999999"] = {
                       "lowres" : "stream.mjpg?"+which_cam,
                       "hires"  : "index.html?"+which_cam,
                       "camera" : which_cam,
                       "type"   : "addon",
                       "title"  : "Live-Stream"
               	}
               	
           if self.adminAllowed(): header = True
           else:                   header = False

           html_today           += self.printImageGroup(title=first_title, group_id="today", image_group=files_today, category=category, header=header, header_open=True, header_count=['all','star','detect'], cam=which_cam)
           content["entries"]    = files_today

           # Yesterday
           html_yesterday  = ""
           files_yesterday = {}
           stamps          = list(reversed(sorted(files_all.keys())))
           if not backup:
             for stamp in stamps: 
               if (int(stamp) >= int(time_now) and time_now != "000000") and "datestamp" in files_all[stamp] and files_all[stamp]["datestamp"] == date_yesterday:
                 if self.camera[which_cam].selectImage(timestamp=stamp, file_info=files_all[stamp], check_similarity=check_similarity):
                    files_yesterday[stamp]              = files_all[stamp]
                    files_yesterday[stamp]["type"]      = "image"
                    files_yesterday[stamp]["category"]  = category+stamp
                    files_yesterday[stamp]["detect"]    = self.camera[which_cam].detectImage(file_info=files_yesterday[stamp])
                    files_yesterday[stamp]["directory"] = "/" + self.config.directories["images"]
                    count += 1
                         
           if len(files_yesterday) > 0:
              html_yesterday              += self.printImageGroup(title="Gestern", group_id="yesterday", image_group=files_yesterday, category=category, header=True, header_open=False, header_count=['all','star','detect'],  cam=which_cam)
              content["entries_yesterday"] = files_yesterday


           # To be deleted
           html_recycle  = ""
           files_recycle = {}
           if self.adminAllowed():
             for stamp in stamps:
               if "to_be_deleted" in files_all[stamp] and int(files_all[stamp]["to_be_deleted"]) == 1:
                 if files_all[stamp]["camera"] == which_cam:
                    files_recycle[stamp]              = files_all[stamp]
                    files_recycle[stamp]["type"]      = "image"
                    files_recycle[stamp]["category"]  = category+stamp
                    files_recycle[stamp]["directory"] = "/" + self.config.directories["images"] + subdirectory
                    count += 1
                       
           if len(files_recycle) > 0:
              if backup: url = "/remove/backup/" + date_backup
              else:      url = "/remove/today"
                   
              intro          = "<a onclick='removeFiles(\"" + url + "\");' style='cursor:pointer;'>Delete all files marked for recycling ...</a>"
              html_recycle             += self.printImageGroup(title="Recycle", group_id="recycle", image_group=files_recycle, category=category, header=True, header_open=False, header_count=['recycle'], cam=which_cam, intro=intro)
              content["entries_delete"] = files_recycle

           html += html_today
           html += html_yesterday               
           html += html_recycle
           html += "<div class='separator'>&nbsp;<br/>&nbsp;</div>"
           html += "<div style='padding:2px;float:left;width:100%'><hr/>" + str(count) + " Bilder / &Auml;hnlichkeit &lt; "+str(self.camera[which_cam].param["similarity"]["threshold"])+"%</div>"
               
        else:
           html += "<div class='separator'>Keine Bilder vorhanden.</div>"

        content["view_count"] = ["all","star","detect"]
        content["file_list"]  = html
        return template, content

    #--------------------------------------

    def createBackupList(self, server):
        '''
        Page with backup/archive directory
        '''
        self.server           = server
        path, which_cam       = self.selectedCamera()
        content               = {
           "active_cam" : which_cam,
           "view"       : "backup",
           "entries"    : {}
           }
        param                 = server.path.split("/")
        if "app-v1" in param: del param[1]
        template              = "list.html"
        html                  = ""
        files_all             = {}

        main_directory  = self.config.directory(config="backup")
        dir_list        = [f for f in os.listdir(main_directory) if os.path.isdir(os.path.join(main_directory, f))]
        dir_list.sort(reverse=True)
        dir_total_size  = 0
        files_total     = 0

        imageTitle     = str(self.config.param["preview_backup"]) + str(self.camera[which_cam].param["image_save"]["seconds"][0])
        imageToday     = self.config.imageName(type="lowres", timestamp=imageTitle, camera=which_cam)
        image          = os.path.join(self.config.directory(config="images"), imageToday)
           
        if os.path.isfile(image):
           html        += self.printImageContainer(description=myPages["today"][0], lowres=imageToday, hires=myPages["today"][1]+"?"+which_cam, star='' ,window="self")
           
        elif which_cam == "cam1":
           imageToday  = "image_"+imageTitle+".jpg" # older archives
           image       = os.path.join(self.config.directory(config="images"), imageToday)
           html       += self.printImageContainer(description=myPages["today"][0], lowres=imageToday, hires=myPages["today"][1]+"?"+which_cam, star='' ,window="self")

        for directory in dir_list:
        
          if os.path.isfile(self.config.file(config="backup", date=directory)):
             file_data = self.config.read_cache(config="backup", date=directory)
             
             if not "info" in file_data or not "files" in file_data:
               html  += self.printImageContainer(description="<b>"+directory+"</b><br/>Fehler in Config-Datei!", lowres="EMPTY") + "\n"
               content["entries"][directory]["error"] = True
               
             else:
               date             = file_data["info"]["date"]
               count            = file_data["info"]["count"]
               first_img        = ""
               dir_size_cam     = 0
               dir_count_cam    = 0
               dir_count_delete = 0

               if imageTitle in file_data["files"]:
                  image = os.path.join(directory, file_data["files"][imageTitle]["lowres"])
               else:
                  for file in list(sorted(file_data["files"].keys())):
                     if ("camera" in file_data["files"][file] and file_data["files"][file]["camera"] == which_cam):
                        first_img = file
                        break
                  if first_img != "":           
                    image = os.path.join(directory, file_data["files"][first_img]["lowres"])

               for file in file_data["files"]:
                  file_info    = file_data["files"][file]
                  if ("camera" in file_info and file_info["camera"] == which_cam) or not "camera" in file_info:
                    if ("datestamp" in file_info and file_info["datestamp"] == directory) or not "datestamp" in file_info:

                      if "size" in file_info: dir_size_cam  += file_info["size"]
                      else:
                        lowres_file = os.path.join(self.config.directory(config="backup"), directory, file_info["lowres"])
                        if os.path.isfile(lowres_file):    dir_size_cam  += os.path.getsize(lowres_file)
                        if "hires" in file_info:
                           hires_file = os.path.join(self.config.directory(config="backup"), directory, file_info["hires"])
                           if os.path.isfile(hires_file): dir_size_cam  += os.path.getsize(hires_file)
                      if "to_be_deleted" in file_info and int(file_info["to_be_deleted"]) == 1:
                        dir_count_delete += 1
                      dir_count_cam += 1

               dir_size        = round(file_data["info"]["size"]/1024/1024,1)
               dir_size_cam    = round(dir_size_cam/1024/1024,1)
               dir_total_size += dir_size
               files_total    += count
               image           = os.path.join(self.config.directories["backup"],image)
                 
               if dir_count_delete > 0: delete_info = "<br/>(Recycle: " + str(dir_count_delete) + ")"
               else:                    delete_info = ""
               if dir_count_cam > 0:    html  += self.printImageContainer(description="<b>"+date+"</b><br/>"+str(dir_count_cam)+" / "+str(dir_size_cam)+" MB" + delete_info, lowres=image, hires="/backup/"+directory+"/list_short.html?"+which_cam, window="self") + "\n"
               #else:                    html  += self.printImageContainer(description="<b>"+date+"</b><br/>Leer für "+which_cam, lowres="EMPTY") + "\n"

               image_file = image.replace(directory+"/","")
               image_file = image_file.replace(self.config.directories["backup"],"")
               content["entries"][directory] = {
                  "directory"    : "/" + self.config.directories["backup"] + directory + "/",
                  "type"         : "directory",
                  "camera"       : which_cam,
                  "date"         : file_data["info"]["date"],
                  "datestamp"    : directory,
                  "count"        : file_data["info"]["count"],
                  "count_delete" : dir_count_delete,
                  "count_cam"    : dir_count_cam,
                  "dir_size"     : dir_size,
                  "dir_size_cam" : dir_size_cam,
                  "lowres"       : image_file
                  }


          else:
             logging.error("Archive: no config file available: /backup/" + directory)
             #self.sendError()

        html += "<div style='padding:2px;float:left;width:100%'><hr/>Gesamt: " + str(round(dir_total_size,1)) + " MB / " + str(files_total) + " Bilder</div>"

        content["view_count"] = []           
        content["file_list"]  = html
        content["subtitle"]   = myPages["backup"][0] + " (" + self.camera[which_cam].name + ")"
        if self.adminAllowed():
           content["links"]      = self.printLinks(link_list=("live","favorit","today","today_complete","videos"), current="backup", cam=which_cam)
           content["links_json"] = self.printLinksJSON(link_list=("live","favorit","today","today_complete","videos"), cam=which_cam)
        else:
           content["links"]      = self.printLinks(link_list=("live","favorit","today","videos"), current="backup", cam=which_cam)
           content["links_json"] = self.printLinksJSON(link_list=("live","favorit","today","videos"), cam=which_cam)

        return template, content

    #--------------------------------------

    def createCompleteListToday(self, server):
        '''
        Page with all pictures of the current day
        '''
        self.server           = server
        path, which_cam       = self.selectedCamera()
        content               = {
            "active_cam" :  which_cam,
            "view"       : "list_complete",
            "entries"    : {},
            "groups"     : {}
            }
            
        param                 = server.path.split("/")
        if "app-v1" in param: del param[1]
        template              = "list.html"
        html                  = ""

        category       = "/current/"
        path           = self.config.directory(config="images")
        files_all      = self.config.read_cache(config="images")

        time_now       = datetime.now().strftime('%H%M%S')
        date_today     = datetime.now().strftime("%Y%m%d")
        date_yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y%m%d")

        hours = list(self.camera[which_cam].param["image_save"]["hours"])
        hours.sort(reverse=True)

        # Today
        for hour in hours:
            hour_min    = hour + "0000"
            hour_max    = str(int(hour)+1) + "0000"
            files_part  = {}
            count_diff  = 0
            stamps      = list(reversed(sorted(files_all.keys())))
            for stamp in stamps:
                if int(stamp) <= int(time_now) and int(stamp) >= int(hour_min) and int(stamp) < int(hour_max):
                   if "datestamp" in files_all[stamp] and files_all[stamp]["datestamp"] == date_today:
                      if "camera" in files_all[stamp] and files_all[stamp]["camera"] == which_cam:
                         threshold = self.camera[which_cam].param["similarity"]["threshold"]
                         if float(files_all[stamp]["similarity"]) < float(threshold) and float(files_all[stamp]["similarity"]) > 0: count_diff += 1
                         files_part[stamp]              = files_all[stamp]
                         files_part[stamp]["type"]      = "image"
                         files_part[stamp]["detect"]    = self.camera[which_cam].detectImage(file_info=files_part[stamp])
                         files_part[stamp]["category"]  = category+stamp
                         files_part[stamp]["directory"] = "/" + self.config.directories["images"]

            if len(files_part) > 0:
               html += self.printImageGroup(title="Bilder "+hour+":00", group_id=hour_min, image_group=files_part, category=category, header=True, header_open=False, cam=which_cam)
               
               content["groups"][hour+":00"] = []
               for entry in files_part:
                  content["entries"][entry] = files_part[entry]
                  content["groups"][hour+":00"].append(entry)
                  
        html += "<div class='separator'>&nbsp;<br/>&nbsp;</div>"

        content["view_count"]  = ["all","star","detect","recycle"]
        content["file_list"]   = html
        content["subtitle"]    = myPages["today_complete"][0] + " (" + self.camera[which_cam].name +", " + str(len(files_all)) + " Bilder)"
        content["links"]       = self.printLinks(link_list=("live","favorit","today","videos","backup"), current="today_complete", cam=which_cam)
        content["links_json"]  = self.printLinksJSON(link_list=("live","favorit","today","videos","backup"), cam=which_cam)

        return template, content

    #--------------------------------------

    def createVideoList(self, server):
        '''
        Page with all videos 
        '''
        self.server           = server
        path, which_cam       = self.selectedCamera()
        content               = {}
        content["active_cam"] = which_cam
        content["view"]       = "list_videos"
        param                 = server.path.split("/")
        if "app-v1" in param: del param[1]
        template              = "list.html"
        html                  = ""

        directory       = self.config.directory(config="videos")
        category        = "/videos/"
        
        files_all       = {}
        files_delete    = {}
        files_show      = {}
           
        if self.config.exists("videos"):
           files_all = self.config.read_cache(config="videos")
           for file in files_all:
               files_all[file]["directory"] = self.camera[which_cam].param["video"]["streaming_server"]
               files_all[file]["type"]      = "video"
               files_all[file]["category"]  = category+file
               if "to_be_deleted" in files_all[file] and int(files_all[file]["to_be_deleted"]) == 1: files_delete[file] = files_all[file]
               else:                                                                                 files_show[file]   = files_all[file]
                  
           if self.adminAllowed():            
              if len(files_show) > 0:   
                 html  += self.printImageGroup(title="Aufgezeichnete Videos", group_id="videos", image_group=files_show, category=category, header=True, header_open=True, header_count=['all','star'], cam=which_cam)
                 content["entries"] = files_show
                 
              if len(files_delete) > 0:
                 url    = "/remove/video"
                 intro  = "<a onclick='removeFiles(\"" + url + "\");' style='cursor:pointer;'>Delete all files marked for recycling ...</a>"
                 html  += self.printImageGroup(title="Zu recycelnde Videos", group_id="videos_recylce", image_group=files_delete, category=category, header=True, header_open=False, header_count=['recycle'], cam=which_cam, intro=intro)
                 content["entries_delete"] = files_delete
                 
           else:
              if len(files_show) > 0:
                 html  += self.printImageGroup(title="Aufgezeichnete Videos", group_id="videos", image_group=files_show, category=category, header=False, header_open=True, header_count=['all','star'], cam=which_cam)
                 content["entries"] = files_show

           if len(files_show) > 0 or len(files_delete) > 0: html += "<div class='separator'>&nbsp;<br/>&nbsp;</div>"
           
             
        if html == "": 
           html             += "<div class='separator' style='width:100%;text-color:lightred;'>Keine Videos vorhanden</div>"
           content["entries"]  = {}

        content["view_count"] = ["all","star","detect","recycle"]
        content["file_list"]  = html
        content["subtitle"]   = myPages["videos"][0] # + " (" + self.camera[which_cam].name +", " + str(len(files_all)) + " Videos)"
        
        if self.adminAllowed():  
           content["links"]       = self.printLinks(link_list=("live","favorit","cam_info","today","backup"), current="today_complete", cam=which_cam)
           content["links_json"]  = self.printLinksJSON(link_list=("live","favorit","cam_info","today","backup"), cam=which_cam)
        else:                    
           content["links"]       = self.printLinks(link_list=("live","favorit","today","backup"), current="today_complete", cam=which_cam)
           content["links_json"]  = self.printLinksJSON(link_list=("live","favorit","today","backup"), cam=which_cam)

        return template, content

    #--------------------------------------

    def createCameraList(self, server):
        '''
        Page with all videos 
        '''
        self.server           = server
        path, which_cam       = self.selectedCamera()
        content               = {}
        content["active_cam"] = which_cam
        content["view"]       = "list_cameras"
        content["entries"]    = {}
        param                 = server.path.split("/")
        if "app-v1" in param: del param[1]
        template              = "list.html"
        html                  = ""
        count                 = 0
            
        for cam in self.camera:
            info                                   = self.camera[cam].param
            content["entries"][cam]                = self.camera[cam].param
            content["entries"][cam]["lowres"]      = "/detection/stream.mjpg?"+cam
            content["entries"][cam]["hires"]       = "/detection/stream.mjpg?"+cam
            content["entries"][cam]["type"]        = "camera"
            content["entries"][cam]["camera_type"] = self.camera[cam].type
            content["entries"][cam]["active"]      = self.camera[cam].active
            
            html += "<div class='camera_info'>"
            html += "<div class='camera_info_image'>"

            description = cam.upper() + ": " + info["name"]
            if self.camera[cam].active:  html   += "<center>"  + self.printImageContainer(description=description, lowres="/detection/stream.mjpg?"+cam, javascript="imageOverlay(\""+"/detection/stream.mjpg?"+cam+"\",\""+description+"\");", star='', window='self', border='white') + "<br/></center>"
            else:                        html   += "<i>Camera "+ cam.upper() + "<br/>not available<br/>at the moment.</i>"
            html += "</div>"
            html += "<div class='camera_info_text'><big><b>" + cam.upper() + ": " + info["name"] + "</b></big>"
            html   += "<ul>"
            html   += "<li>Type: "   + content["entries"][cam]["camera_type"] + "</li>"
            html   += "<li>Active: " + str(self.camera[cam].active) + "</li>"
            html   += "<li>Record: " + str(info["record"]) + "</li>"
            html   += "<li>Crop: "   + str(info["image"]["crop"]) + "</li>"
            html   += "<li>Detection (red rectangle): <ul>"
            html     += "<li>Threshold: " + str(info["similarity"]["threshold"]) + "%</li>"
            html     += "<li>Area: "      + str(info["similarity"]["detection_area"]) + "</li>"
            html   += "</ul></li>"
            html   += "</ul>"
            if self.adminAllowed():
               if self.camera[cam].active and self.camera[cam].param["video"]["allow_recording"]:
                  html   += "<hr width='100%'/>"
                  html   += "<center><button onclick='requestAPI(\"/start/recording/"+cam+"\");'>Record</button> &nbsp;"
                  html   += "<button onclick='requestAPI(\"/stop/recording/"+cam+"\");'>Stop</button></center>"
            html  += "</div>"
            html  += "</div>"
            count += 1
            if count < len(self.camera):
               html += "<div class='separator'><hr/>"
              
        content["view_count"]  = []
        content["subtitle"]    = myPages["cam_info"][0]
        content["links"]       = self.printLinks(link_list=("live","favorit","today","videos","backup"), cam=which_cam)
        content["links_json"]  = self.printLinksJSON(link_list=("live","favorit","today","videos","backup"), cam=which_cam)
        content["file_list"]   = html

        return template, content

    #-------------------------------------
    
    def detailViewVideo(self, server):
        '''
        Show details and edit options for a video file
        '''
        self.server           = server
        path, which_cam       = self.selectedCamera()
        content               = {}
        content["active_cam"] = which_cam
        content["view"]       = "detail_video"
        content["entries"]    = {}
        param                 = server.path.split("/")
        if "app-v1" in param: del param[1]
        template              = "list.html"
        html                  = ""
        count                 = 0
        
        if "api" in param:    video_id = param[4]
        else:                 video_id = param[1]
        
        config_data           = self.config.read_cache(config="videos")
        if video_id in config_data and "video_file" in config_data[video_id]:
        
            data                         = config_data[video_id]
            content["entries"][video_id] = data
            description                  = ""
            
            html += "<div class='camera_info'>\n"
            html += "<div class='camera_info_image'>"
            
            if "video_file" in data:
               description = "<b>Vollst&auml;ndiges Video</b>"
               lowres      = "/videos/"+data["thumbnail"]
               video_link  = self.camera[which_cam].param["video"]["streaming_server"] + data["video_file"]
               javascript  = "videoOverlay(\"" + video_link + "\",\"" + description + "\");"           
               html += self.printImageContainer(description=description, lowres=lowres, javascript=javascript, star='', window='self', border='white') 
               
            if "video_file_short" in data:
               description  = "<b>Gek&uuml;rztes Video</b>"
               description2 = description + "<br/>Start: "+str(round(data["video_file_short_start"],1))+"s / Ende: "+str(round(data["video_file_short_end"],1))+"s"
               lowres       = "/videos/"+data["thumbnail"]
               video_link   = self.camera[which_cam].param["video"]["streaming_server"] + data["video_file_short"]
               javascript   = "videoOverlay(\"" + video_link + "\",\"" + description2 + "\");"           
               html += self.printImageContainer(description=description, lowres=lowres, javascript=javascript, star='', window='self', border='white') 
               
            if description == "":
               html += "<center>"
               html += "Kein Videofile vorhanden."
               html += "</center>"
                        
            html += "</div>\n"
            html += "<div class='camera_info_text'>"

            html += "<b>" + data["date"] + "</b><br/>&nbsp;<br/>"
            html += "Kamera: " + data["camera"].upper() + " - " + data["camera_name"] + "<br/>"
            html += "L&auml;nge: " + str(round(data["length"],1)) + " s<br/>"
            html += "Framerate: " + str(data["framerate"]) + " fps<br/>"
            if "image_size" in data:
               html += "Bildgr&ouml;&szlig;e: " + str(data["image_size"]) + "<br/>"
            
            if "video_file_short" in data: html += "Kurzversion: "+str(round(data["video_file_short_length"],1))+" s<br/>"
            else:                          html += "Kurzversion: nicht vorhanden <br/>"

            if self.adminAllowed():
               html += "&nbsp;<br/>"
               html += "Bearbeiten: &nbsp;  <button onclick=\"toggleVideoEdit();\" class=\"button-video-edit\">&nbsp;K&uuml;rzen&nbsp;</button>"
               
            html += "&nbsp;<br/>"
            html += "</div>\n"
            html += "</div>\n"
            
            if self.adminAllowed():

               files = {}
               files["VIDEOFILE"]  = self.camera[which_cam].param["video"]["streaming_server"] + data["video_file"]
               files["THUMBNAIL"]  = data["thumbnail"]
               files["LENGTH"]     = str(data["length"])
               files["VIDEOID"]    = video_id
               files["ACTIVE" ]    = which_cam
               files["JAVASCRIPT"] = "createShortVideo();"
            
               filename = os.path.join(self.config.param["path"],self.config.directory(config="html"),"video-player.html")
               logging.info(filename)
            
               html += "<div id='camera_video_edit' class='camera_video_edit'>\n"
               html += read_html(filename=filename, content=files)
               html += "<br/>&nbsp;</div>\n"

        elif param[1] in config_data:
           html += "<div class='separator'>Keine Videodatei f&uuml;r die ID &quot;" + param[1] + "&quot; verf&uuml;gbar.</div>"        
        
        else:
           html += "<div class='separator'>Kein Video mit dieser ID &quot;" + param[1] + "&quot; verf&uuml;gbar.</div>"        

        content["view_count"] = []
        content["subtitle"]   = myPages["video_info"][0]
        content["links"]      = self.printLinks(link_list=("live","favorit","videos"), cam=which_cam)
        content["links_json"] = self.printLinksJSON(link_list=("live","favorit","today","videos","backup"), cam=which_cam)
        content["file_list"]  = html

        return template, content

