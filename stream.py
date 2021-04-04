#!/usr/bin/python3

# In Progress:
# - ...
# Backlog:
# - In progress (error!): Restart camera threads via API, Shutdown all services via API, Trigger RPi halt/reboot via API
# - delete files with to_be_deleted == 1 in archive folders
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
from datetime        import datetime

from modules.backup  import myBackupRestore
from modules.camera  import myCamera
from modules.config  import myConfig
from modules.presets import myParameters
from modules.presets import myPages

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

    def printYesterday(self):
        return "<div class='separator'><hr/>Gestern<hr/></div>"


    def printLinks(self, link_list, current="", cam=""):
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
          html  += " / <a href='"+myPages[current][1]+"?"+self.active_cams[selected]+"'>"+self.active_cams[selected].upper()+"</a>"

        return html


    def printStar(self,file="",favorit=0,cam=""):
       stamp = file.split("/")
       stamp = stamp[len(stamp)-1]
       if int(favorit) == 1:
          star    = "/html/star1.png"
          value   = "0"
       else:
          star    = "/html/star0.png"
          value   = "1"
       if self.adminAllowed():
          onclick = "setFavorit(\""+file+"\",document.getElementById(\"s_"+file+"_value\").innerHTML,\""+config.imageName("lowres", stamp, cam)+"\");"
          return "<div class='star'><div id='s_"+file+"_value' style='display:none;'>"+value+"</div><img class='star_img' id='s_"+file+"' src='" + star + "' onclick='"+onclick+"'/></div>\n"
       else:
          onclick = ""
          if int(favorit) == 1:
            return "<div class='star'><div id='s_"+file+"_value' style='display:none;'>"+value+"</div><img class='star_img' id='s_"+file+"' src='" + star + "' onclick='"+onclick+"'/></div>\n"
          else:
            return "<div class='star'></div>\n"


    def printTrash(self,file="",delete=0,cam=""):
       stamp = file.split("/")
       stamp = stamp[len(stamp)-1]
       if int(delete) == 1:
          trash   = "/html/recycle1.png"
          value   = "0"
       else:
          trash   = "/html/recycle0.png"
          value   = "1"
       if self.adminAllowed():
          onclick = "setRecycle(\""+file+"\",document.getElementById(\"d_"+file+"_value\").innerHTML,\""+config.imageName("lowres", stamp, cam)+"\");"
          return "<div class='trash'><div id='d_"+file+"_value' style='display:none;'>"+value+"</div><img class='trash_img' id='d_"+file+"' src='" + trash + "' onclick='"+onclick+"'/></div>\n"
       else:
          return "<div class='trash'></div>\n"


    def printImageContainer(self, description, lowres, hires='', javascript='' ,star='', trash='', window='self', lazzy='', border='black'):
        html = "<div class='image_container'>\n"
        if star  != '':      html += star
        else:                html += "<div class='star'></div>"
        if trash  != '':     html += trash
        else:                html += "<div class='trash'></div>"
        if lazzy == 'lazzy': lazzy = "data-"
        else:                lazzy = ""
        
        lowres_file = lowres.split("/")
        lowres_file = lowres_file[len(lowres_file)-1]
        
        html += "<div class='thumbnail_container'>\n"
        if lowres == "EMPTY":
          html += "<div class='thumbnail' style='background-color:#222222;'><br/><br/><small>"+description+"</small></div>"
        else:
          if hires != '':        html += "<a href='"+hires+"' target='_"+window+"'><img "+lazzy+"src='"+lowres+"' id='"+lowres_file+"' class='thumbnail' style='border:1px solid "+border+";'/></a><br/><small>"+description+"</small>"
          elif javascript != '': html += "<div onclick='javascript:"+javascript+"' style='cursor:pointer;'><img "+lazzy+"src='"+lowres+"' id='"+lowres_file+"' class='thumbnail' style='border:1px solid "+border+";'/></div><br/><small>"+description+"</small>"
          else:                  html += "<img "+lazzy+"src='"+lowres+"' id='"+lowres_file+"' class='thumbnail' style='border:1px solid "+border+";'/><br/><small>"+description+"</small>"
        html += "\n</div>\n"
        html += "</div>\n"
        return html


    def printImageGroup(self, title, group_id, image_group, index, header=True, header_open=False, header_count=['all','star','detect','recycle'], cam=''):
           '''
           create html for a list of images including all checks
           '''
           id_list     = images     = display     = ""
           count       = { 'all' : 0, 'star' : 0, 'detect' : 0, 'recycle' : 0 }
           color       = { 'all' : 'white', 'star' : 'lime', 'detect' : 'aqua', 'recycle' : 'red' }

           stamps = list(reversed(sorted(image_group.keys())))
           for stamp in stamps:
              border     = "black"
              
              if "type" in image_group[stamp] and image_group[stamp]["type"] == "addon":
                 entry       = image_group[stamp]
                 description = entry["title"]
                 lowres      = entry["lowres"]
                 hires       = entry["hires"]
                 javascript  = star = trash = lazzy = ""

              else:              
                if "_" in stamp: 
                   stamp_date, stamp_time = stamp.split("_")
                   time       = stamp_date[6:8] + "." + stamp_date[4:6] + "." + stamp_date[0:4] + " " + stamp_time[0:2] + ":" + stamp_time[2:4]
                   time      += "<br/>"
                else:
                   stamp_time = stamp
                   time       = stamp_time[0:2] + ":" + stamp_time[2:4] + ":" + stamp_time[4:6]
                   
                similarity = str(image_group[stamp]["similarity"])+'%'
                threshold  = camera[cam].param["similarity"]["threshold"]
                
                if "favorit" in image_group[stamp]:
                  star   = self.printStar(file=index+stamp_time, favorit=image_group[stamp]["favorit"], cam=cam)
                  if int(image_group[stamp]["favorit"]) == 1: 
                    border      = "lime"
                    count["star"] += 1
                else:
                  star   = self.printStar(file=index+stamp_time, favorit=0, cam=cam)
                
                if "to_be_deleted" in image_group[stamp]:
                  trash  = self.printTrash(file=index+stamp_time, delete=image_group[stamp]["to_be_deleted"], cam=cam)
                  if int(image_group[stamp]["to_be_deleted"]) == 1:
                    border       = "red"
                    count["recycle"] += 1
                else:
                  trash  = self.printTrash(file=index+stamp_time, delete=0, cam=cam)

                if float(image_group[stamp]["similarity"]) < float(threshold) and float(image_group[stamp]["similarity"]) > 0:
                  if border == "black":
                   border      = "aqua"
                   count["detect"] += 1

                if "backup" in index: url_dir = index
                else:                 url_dir = ""

                hires       = ""
                description = time + " ("+similarity+")"
                lowres      = url_dir + image_group[stamp]["lowres"]
                if "hires" in image_group[stamp]:
                   hires      = "" # image_group[stamp]["hires"]
                   javascript ="imageOverlay(\"" + url_dir + image_group[stamp]["hires"] + "\",\"" + description + "\");"

                if header and not header_open:
                   display    = "style='display:none;'"
                   id_list   += lowres + " "
                   lazzy      = "lazzy"
                else:
                   lazzy      = ""

              images    += self.printImageContainer(description=description, lowres=lowres, hires=hires, star=star, trash=trash, javascript=javascript, lazzy=lazzy, border=border)

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

           html   += "<div id='group_ids_" + group_id + "' style='display:none;'>"+id_list+"</div>\n"             
           html   += "<div id='group_" + group_id + "' " + display + "><div class='separator'>&nbsp;</div>"+images+"</div>\n"
           return html

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
        if self.path.startswith("/favorit/current/"):
           param = self.path.split("/")
           config_data = config.read(config="images")
           if param[3] in config_data:
             config_data[param[3]]["favorit"] = param[4]
             if int(param[4]) == 1: config_data[param[3]]["to_be_deleted"] = 0
             config.write(config="images", config_data=config_data)
           else:
             response["error"] = "no image found with stamp "+str(param[3])
  
           response["command"] = ["set/unset favorit", param[3], param[4]]
           self.streamFile(type='application/json', content=json.dumps(response).encode(encoding='utf_8'), no_cache=True);

        # set / unset favorit
        elif self.path.startswith("/favorit/backup/"):
           param = self.path.split("/")
           config_data = config.read(config="backup", date=param[3])
           if param[4] in config_data["files"]:
             config_data["files"][param[4]]["favorit"] = param[5]
             if int(param[5]) == 1: config_data["files"][param[4]]["to_be_deleted"] = 0
             config.write(config="backup",config_data=config_data, date=param[3])
           else:
             response["error"] = "no image found with stamp "+str(param[4])

           response["command"] = ["set/unset favorit (backup)", param[5]]
           self.streamFile(type='application/json', content=json.dumps(response).encode(encoding='utf_8'), no_cache=True);

        # mark / unmark for deletion
        elif self.path.startswith("/delete/current/"):
           param = self.path.split("/")
           config_data = config.read(config="images")
           if param[3] in config_data:
             config_data[param[3]]["to_be_deleted"] = param[4]
             if int(param[4]) == 1: config_data[param[3]]["favorit"] = 0
             config.write(config="images", config_data=config_data)
           else:
             response["error"] = "no image found with stamp "+str(param[3])

           response["command"] = ["mark/unmark for deletion", param[4]]
           self.streamFile(type='application/json', content=json.dumps(response).encode(encoding='utf_8'), no_cache=True);

        # mark / unmark for deletion
        elif self.path.startswith("/delete/backup/"):
           param = self.path.split("/")
           config_data = config.read(config="backup", date=param[3])
           if param[4] in config_data["files"]:
              config_data["files"][param[4]]["to_be_deleted"] = param[5]
              if int(param[5]) == 1: config_data["files"][param[4]]["favorit"] = 0
              config.write(config="backup",config_data=config_data, date=param[3])
           else:
              response["error"] = "no image found with stamp "+str(param[4])

           response["command"] = ["mark/unmark for deletion (backup)", param[5]]
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
        if   self.path == '/': self.redirect("/index.html")
        elif self.path == '/index.html':

            if camera["cam1"].active and camera["cam2"].active:
               if which_cam == "cam1":   index_file = "index_cam1+cam2.html"
               elif which_cam == "cam2": index_file = "index_cam2+cam1.html"
               else:                     index_file = "index.html"
            else:
               index_file = "index.html"

            config.html_replace["active_cam"] = which_cam
            if adminAllowed(): config.html_replace["links"] = self.printLinks(link_list=("today","backup","favorit","cam_info"),cam=which_cam)
            else:              config.html_replace["links"] = self.printLinks(link_list=("today","backup","favorit"),cam=which_cam)
            self.streamFile(type='text/html', content=read_html('html',index_file), no_cache=True)

        # List favorit images (marked with star)
        elif '/list_star.html' in self.path:

            html                             = ""
            favorits                         = {}
            config.html_replace["subtitle"]  = myPages["favorit"][0] + " (" + camera[which_cam].name + ")"
            config.html_replace["links"]     = self.printLinks(link_list=("live","today","backup"), cam=which_cam)

            # today
            files = config.read(config="images")
            index = "/current/"
            for stamp in files:
              if "favorit" in files[stamp] and int(files[stamp]["favorit"]) == 1:
                new = datetime.now().strftime("%Y%m%d")+"_"+stamp
                favorits[new]           = files[stamp]
                favorits[new]["source"] = ("images","")
                favorits[new]["date"]   = "Aktuell"
                favorits[new]["time"]   = stamp[0:2]+":"+stamp[2:4]+":"+stamp[4:6]

            html += self.printImageGroup(title="Heute &nbsp; &nbsp; &nbsp; &nbsp;", group_id="today", image_group=favorits, index=index, header=True, header_open=True, header_count=['star'], cam=which_cam)

            path           = config.directory(config="backup")
            dir_list       = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
            dir_list       = list(reversed(sorted(dir_list)))
            for directory in dir_list:
              index    = "/backup/"+directory+"/"
              if config.exists(config="backup", date=directory):
                files_data = config.read(config="backup", date=directory)
                files      = files_data["files"]
                date       = directory[6:8]+"."+directory[4:6]+"."+directory[0:4]
                favorits[directory] = {}
                for stamp in files:
                  if "favorit" in files[stamp] and int(files[stamp]["favorit"]) == 1:
                    new = directory+"_"+stamp
                    favorits[directory][new]           = files[stamp]
                    favorits[directory][new]["source"] = ("backup",directory)
                    favorits[directory][new]["date"]   = date
                    favorits[directory][new]["time"]   = stamp[0:2]+":"+stamp[2:4]+":"+stamp[4:6]
                    favorits[directory][new]["date2"]  = favorits[directory][new]["date"]

                if len(favorits[directory]) > 0:
                   html += self.printImageGroup(title=date, group_id=directory, image_group=favorits[directory], index=index, header=True, header_open=True, header_count=['star'], cam=which_cam)

            config.html_replace["file_list"] = html
            self.streamFile(type='text/html',content=read_html('html','list.html'), no_cache=True)

        # List only if threshold ...
        elif '/list_short.html' in self.path:

           html          = ""
           files         = {}
           count         = 0
           file_dir      = self.path.split("/")
           backup_config = config.files["images"]
           today         = datetime.now().strftime("%Y%m%d")

           if file_dir[1] == "backup":
               path       = config.directory(config="backup", date=file_dir[2])
               files_data = config.read(config="backup", date=file_dir[2])
               files      = files_data["files"]
               index      = self.path.replace("list_short.html","")
               time_now   = "000000"

               config.html_replace["subtitle"]  = myPages["backup"][0] + " " + files_data["info"]["date"] + " (" + camera[which_cam].name + ", " + str(files_data["info"]["count"]) + " Bilder)"
               config.html_replace["links"]     = self.printLinks(link_list=("live","today","backup","favorit"), current='backup', cam=which_cam)

           elif os.path.isfile(config.file(config="images")):
               path     = config.directory(config="images")
               files    = config.read(config="images")
               time_now = datetime.now().strftime('%H%M%S')
               index    = "/current/"

               config.html_replace["subtitle"]    = myPages["today"][0] + " (" + camera[which_cam].name + ")"
               if self.adminAllowed():
                 config.html_replace["links"]     = self.printLinks(link_list=("live","today_complete","backup","favorit"), current='today', cam=which_cam)
               else:
                 config.html_replace["links"]     = self.printLinks(link_list=("live","backup","favorit"), current='today', cam=which_cam)

           if files != {}:
               stamps   = list(reversed(sorted(files.keys())))

               # Today
               html_today  = ""
               files_today = {}
               for stamp in stamps:
                 if int(stamp) < int(time_now) or time_now == "000000":
                   if camera[which_cam].selectImage(timestamp=stamp, file_info=files[stamp]):
                     if not "datestamp" in files[stamp] or files[stamp]["datestamp"] == today or file_dir[1] == "backup":
                        files_today[stamp] = files[stamp]

               files_today["999999"] = {
                       "lowres" : "stream.mjpg?"+which_cam,
                       "hires"  : "/index.html?"+which_cam,
                       "camera" : which_cam,
                       "type"   : "addon",
                       "title"  : "Live-Stream"
               	}
               	
               if self.adminAllowed(): header = True
               else:                   header = False

               html_today += self.printImageGroup(title="Heute &nbsp; ", group_id="today", image_group=files_today, index=index, header=header, header_open=True, header_count=['all','star','detect'], cam=which_cam)

               # Yesterday
               html_yesterday  = ""
               files_yesterday = {}
               for stamp in stamps:
                 if int(stamp) >= int(time_now) and time_now != "000000":
                   if camera[which_cam].selectImage(timestamp=stamp, file_info=files[stamp]):
                      files_yesterday[stamp] = files[stamp]

               if file_dir[1] != "backup":
                  html_yesterday += self.printImageGroup(title="Gestern", group_id="yesterday", image_group=files_yesterday, index=index, header=True, header_open=False, header_count=['all','star','detect'],  cam=which_cam)

               # To be deleted
               html_recycle  = ""
               files_recycle = {}
               if self.adminAllowed():
                 for stamp in stamps:
                   if "to_be_deleted" in files[stamp] and int(files[stamp]["to_be_deleted"]) == 1:
                     if files[stamp]["camera"] == which_cam:
                       files_recycle[stamp] = files[stamp]
                       
                 if len(files_recycle) > 0:      
                   html_recycle += self.printImageGroup(title="Recycle", group_id="recycle", image_group=files_recycle, index=index, header=True, header_open=False, header_count=['recycle'],  cam=which_cam)

               html += html_today
               html += html_yesterday               
               html += html_recycle
               html += "<div class='separator'>&nbsp;<br/>&nbsp;</div>"
               
               html += "<div style='padding:2px;float:left;width:100%'><hr/>"+str(count)+" Bilder / &Auml;hnlichkeit &lt; "+str(camera[which_cam].param["similarity"]["threshold"])+"%</div>"
               config.html_replace["file_list"] = html
               self.streamFile(type='text/html',content=read_html('html','list.html'), no_cache=True)

           else:
             logging.error("list_short 05 "+str(len(files)))
             self.redirect("/list_new.html")

        # List all backup directories
        elif self.path == '/list_backup.html':

           config.html_replace["subtitle"] = myPages["backup"][0] + " (" + camera[which_cam].name + ")"
           if self.adminAllowed():
             config.html_replace["links"]    = self.printLinks(link_list=("live","today","today_complete","favorit"), current="backup", cam=which_cam)
           else:
             config.html_replace["links"]    = self.printLinks(link_list=("live","today","favorit"), current="backup", cam=which_cam)

           path           = config.directory(config="backup")
           backup_config  = config.files["backup"]
           dir_list       = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
           dir_list.sort(reverse=True)
           dir_total_size = 0
           files_total    = 0
           html           = ""

           imageTitle     = str(config.param["preview_backup"]) + str(camera[which_cam].param["image_save"]["seconds"][0])
           imageToday     = config.imageName(type="lowres", timestamp=imageTitle, camera=which_cam)
           image          = os.path.join(config.directory(config="images"), imageToday)
           
           if os.path.isfile(image):
              html        += self.printImageContainer(description=myPages["today"][0], lowres=imageToday, hires=myPages["today"][1]+"?"+which_cam, star='' ,window="self")
           elif which_cam == "cam1":
              imageToday  = "image_"+imageTitle+".jpg" # older archives
              image       = os.path.join(config.directory(config="images"), imageToday)
              html       += self.printImageContainer(description=myPages["today"][0], lowres=imageToday, hires=myPages["today"][1]+"?"+which_cam, star='' ,window="self")

           for directory in dir_list:

              if os.path.isfile(config.file(config="backup",date=directory)):
                 file_data        = config.read(config="backup", date=directory)
                 date             = file_data["info"]["date"]
                 count            = file_data["info"]["count"]
                 dir_size_cam     = 0
                 dir_count_cam    = 0
                 dir_count_delete = 0

                 if imageTitle in file_data["files"]:
                    image = os.path.join(directory, file_data["files"][imageTitle]["lowres"])

                 for file in file_data["files"]:
                   file_info    = file_data["files"][file]
                   if ("camera" in file_info and file_info["camera"] == which_cam) or (which_cam == "cam1" and not "camera" in file_info):

                      if "size" in file_info: dir_size_cam  += file_info["size"]
                      else:
                        lowres_file = os.path.join(config.directory(config="backup"), directory, file_info["lowres"])
                        if os.path.isfile(lowres_file):    dir_size_cam  += os.path.getsize(lowres_file)
                        if "hires" in file_info:
                           hires_file = os.path.join(config.directory(config="backup"), directory, file_info["hires"])
                           if os.path.isfile(hires_file): dir_size_cam  += os.path.getsize(hires_file)
                      if "to_be_deleted" in file_info and int(file_info["to_be_deleted"]) == 1:
                        dir_count_delete += 1
                      dir_count_cam += 1

                 dir_size        = round(file_data["info"]["size"]/1024/1024,1)
                 dir_size_cam    = round(dir_size_cam/1024/1024,1)
                 dir_total_size += dir_size
                 files_total    += count
                 
                 if dir_count_delete > 0: delete_info = "<br/>(Recycle: " + str(dir_count_delete) + ")"
                 else:                    delete_info = ""
                 if dir_count_cam > 0:    html  += self.printImageContainer(description="<b>"+date+"</b><br/>"+str(dir_count_cam)+" / "+str(dir_size_cam)+" MB" + delete_info, lowres=image, hires="/backup/"+directory+"/list_short.html?"+which_cam, window="self") + "\n"
                 else:                    html  += self.printImageContainer(description="<b>"+date+"</b><br/>Leer für "+which_cam, lowres="EMPTY") + "\n"

              ### >>> should not be necesarry any more ...
              else:
                 logging.warning("Archive: no config file available!"+directory)
                 date            = directory[6:8] + "." + directory[4:6] + "." + directory[0:4]
                 file_list       = [f for f in os.listdir(os.path.join(path,directory)) if os.path.isfile(os.path.join(path,directory,f)) and "_big" not in f]
                 dir_size        = sum(os.path.getsize(os.path.join(path,directory,f)) for f in os.listdir(os.path.join(path,directory)) if os.path.isfile(os.path.join(path,directory,f)))
                 dir_size        = round(dir_size/1024/1024,1)
                 dir_total_size += dir_size
                 files_total    += len(file_list)
                 html           += self.printImageContainer(description="*<b>"+date+"</b><br/>"+str(len(file_list))+" / "+str(dir_size)+" MB*",lowres="/backup/"+image,hires="/backup/"+directory+"/list.html",window="self")

           html += "<div style='padding:2px;float:left;width:100%'><hr/>Gesamt: " + str(round(dir_total_size,1)) + " MB / " + str(files_total) + " Bilder</div>"
           config.html_replace["file_list"] = html
           self.streamFile(type='text/html', content=read_html('html','list.html'), no_cache=True)

        # List all files NEW
        elif self.path.endswith('/list_new.html'):

           html         = ""
           files        = self.path.split("/")

           if files[1] == "backup":
              redirect(self.path.replace("/list_new.html","/list_short.html"))

           else:
              index     = "/current/"
              path      = config.directory(config="images")
              files_all = config.read(config="images")
              files     = config.read(config="images")
              time_now  = datetime.now().strftime('%H%M%S')
              today     = datetime.now().strftime('%Y%m%d')

              config.html_replace["subtitle"] = myPages["today_complete"][0] + " (" + camera[which_cam].name +", " + str(len(files_all)) + " Bilder)"
              config.html_replace["links"]    = self.printLinks(link_list=("live","today","favorit","backup"), current="today_complete", cam=which_cam)

           hours = list(camera[which_cam].param["image_save"]["hours"])
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
                    if not "datestamp" in files_all[stamp] or files_all[stamp]["datestamp"] == today:
                       if "camera" in files_all[stamp] and files_all[stamp]["camera"] == which_cam:
                          threshold = camera[which_cam].param["similarity"]["threshold"]
                          if float(files_all[stamp]["similarity"]) < float(threshold) and float(files_all[stamp]["similarity"]) > 0: count_diff += 1
                          files_part[stamp] = files_all[stamp]

              if len(files_part) > 0:
                 html += self.printImageGroup(title="Bilder "+hour+":00", group_id=hour_min, image_group=files_part, index=index, header=True, header_open=False, cam=which_cam)

           # Yesterday
           files_part = {}
           html_yesterday   = ""
           header_yesterday = True
           for hour in hours:
              hour_min    = hour + "0000"
              hour_max    = str(int(hour)+1) + "0000"
              files_part  = {}
              count_diff  = 0
              stamps      = list(reversed(sorted(files_all.keys())))
              for stamp in stamps:
                if int(stamp) > int(time_now) and int(stamp) >= int(hour_min) and int(stamp) < int(hour_max):
                  if "camera" in files_all[stamp] and files_all[stamp]["camera"] == which_cam:
                    threshold = camera[which_cam].param["similarity"]["threshold"]
                    if float(files_all[stamp]["similarity"]) < float(threshold) and float(files_all[stamp]["similarity"]) > 0: count_diff += 1
                    files_part[stamp] = files_all[stamp]

              if len(files_part) > 0:
                 if header_yesterday: 
                    html_yesterday += self.printYesterday()
                    header_yesterday = False
                 html_yesterday += self.printImageGroup(title="Bilder "+hour+":00", group_id=hour_min, image_group=files_part, index=index, header=True, header_open=False, cam=which_cam)

           html += html_yesterday
           html += "<div class='separator'>&nbsp;<br/>&nbsp;</div>"

           config.html_replace["file_list"] = html
           self.streamFile(type='text/html', content=read_html('html','list.html'), no_cache=True)


        # List all video files
        elif '/videos.html' in self.path:
        
           html      = ""
           files_all = {}
           path      = config.directory(config="videos")

           if config.exists("videos"):
             files_all = config.read(config="videos")
           
             if len(files_all) > 0:
               html  += "<div class='separator' style='width:100%'>"
               html  += "<b>Liste vorhandener Videos</b>"
               html  += "</div>\n"
               
               html  += "<div>\n"
               
               for video in files_all:
                  description = files_all[video]["date"].replace(" ","<br/>") + "<br/>" + files_all[video]["camera"].upper() + ": " + files_all[video]["camera_name"]
                  video_link  = camera[which_cam].param["video"]["streaming_server"] + files_all[video]["video_file"]
                  javascript  = "videoOverlay(\"" + video_link + "\",\"" + description + "\");"
                  html       += self.printImageContainer(description=description, lowres="videos/"+files_all[video]["thumbnail"], javascript=javascript, star='', window='self', border='white')
                  
               html += "</div>\n"
               
             else: html  += "<div class='separator' style='width:100%;text-color:lightred;'>Keine Videos vorhanden</div>"
           else:   html  += "<div class='separator' style='width:100%;text-color:lightred;'>Keine Videos vorhanden</div>"
           
           config.html_replace["subtitle"]  = myPages["videos"][0] + " (" + camera[which_cam].name +", " + str(len(files_all)) + " Videos)"
           config.html_replace["links"]     = self.printLinks(link_list=("live","cam_info","today","favorit"), current="today_complete", cam=which_cam)
           config.html_replace["file_list"] = html
           self.streamFile(type='text/html', content=read_html('html','list.html'), no_cache=True)
           
           
        # List all files
        elif '/list.html' in self.path:

           files     = self.path.split("/")
           if files[1] == "backup":  path = config.directory(config="backup",date=files[2])
           else:                     path = config.directory(config="images")

           file_list = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)) and "big" not in f]
           file_list.sort(reverse=True)

           if files[1] == "backup":
             config.html_replace["subtitle"] = myPages["backup"][0] + " "+files[2][6:8] + "." + files[2][4:6] + "." + files[2][0:4]+" ("+camera[which_cam].name+", "+str(len(file_list))+" Bilder)"
             if self.adminAllowed():
               config.html_replace["links"]    = self.printLinks(link_list=("live","today_complete","backup"), cam=which_cam)
             else:
               config.html_replace["links"]    = self.printLinks(link_list=("live","backup"), cam=which_cam)
             index     = "/backup/"
             time_now  = "000000"

           else:
             config.html_replace["subtitle"] = myPages["today_complete"][0] + " ("+camera[which_cam].name+", "+str(len(file_list))+" Bilder)"
             config.html_replace["links"]    = self.printLinks(link_list=("live","today","backup"), cam=which_cam)
             time_now  = datetime.now().strftime('%H%M%S')
             index     = "/current/"
             files     = config.read(config="images")

           html = ""
           # Today
           for file in file_list:
             if ".jpg" in file:
                stamp     = file[6:12]
                if int(stamp) < int(time_now) or time_now == "000000":
                   description = file[6:8]+":"+file[8:10]+":"+file[10:12]
                   file_big    = config.imageName(type="hires",timestamp=stamp)

                   if index == "/current/":
                     if "favorit" in files[stamp]:                   star  = self.printStar(file=index+stamp, favorit=files[stamp]["favorit"],             cam=which_cam)
                     else:                                           star  = self.printStar(file=index+stamp, favorit=0,                                   cam=which_cam)
                     if "to_be_deleted" in image_group[stamp]:       trash = self.printTrash(file=index+stamp, delete=image_group[stamp]["to_be_deleted"], cam=which_cam)
                     else:                                           trash = self.printTrash(file=index+stamp, delete=0,                                   cam=which_cam)
                   else: star = ""

                   if os.path.isfile(os.path.join(path,file_big)): html += self.printImageContainer(description=description, lowres=file, hires=file_big, star=star)
                   else:                                           html += self.printImageContainer(description=description, lowres=file, hires="", star=star)

           # Yesterday
           html_yesterday = ""
           for file in file_list:
             if ".jpg" in file:
                stamp     = file[6:12]
                if int(stamp) >= int(time_now) and time_now != "000000":
                   description     = file[6:8]+":"+file[8:10]+":"+file[10:12]
                   file_big = config.imageName(type="hires",timestamp=stamp)

                   if index == "/current/":
                     if "favorit" in files[stamp]:                   star  = self.printStar(file=index+stamp, favorit=files[stamp]["favorit"],             cam=which_cam)
                     else:                                           star  = self.printStar(file=index+stamp, favorit=0,                                   cam=which_cam)
                     if "to_be_deleted" in image_group[stamp]:       trash = self.printTrash(file=index+stamp, delete=image_group[stamp]["to_be_deleted"], cam=which_cam)
                     else:                                           trash = self.printTrash(file=index+stamp, delete=0,                                    cam=which_cam)
                   else: star = ""

                   if os.path.isfile(os.path.join(path,file_big)): html_yesterday += self.printImageContainer(description=description, lowres=file, hires=file_big, star=star)
                   else:                                           html_yesterday += self.printImageContainer(description=description, lowres=file, hires="", star=star)

           if html_yesterday != "":
              html += self.printYesterday()
              html += html_yesterday

           config.html_replace["file_list"] = html
           self.streamFile(type='text/html', content=read_html('html','list.html'), no_cache=True)

        # extract and show single image
        elif self.path == '/image.jpg':
            camera[which_cam].setText = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
            camera[which_cam].writeImage('image_'+which_cam+'.jpg',camera[which_cam].convertFrame2Image(camera[which_cam].getFrame()))
            self.streamFile(type='image/jpeg', content=read_image("",'image_'+which_cam+'.jpg'))

        # show live stream
        elif self.path.endswith('/cameras.html'):
            html  = ""
            count = 0
            for cam in camera:
              info = camera[cam].param
              html += "<div class='camera_info'>"
              html += "<div class='camera_info_image'>"

              description = cam.upper() + ": " + info["name"]
              if camera[cam].active:  html   += "<center>"  + self.printImageContainer(description=description, lowres="/detection/stream.mjpg?"+cam, javascript="imageOverlay(\""+"/detection/stream.mjpg?"+cam+"\",\""+description+"\");", star='', window='self', border='white') + "<br/></center>"
              else:                   html   += "<i>Camera "+ cam.upper() + "<br/>not available<br/>at the moment.</i>"
              html += "</div>"
              html += "<div class='camera_info_text'><big><b>" + cam.upper() + ": " + info["name"] + "</b></big>"
              html   += "<ul>"
              html   += "<li>Type: "   + info["type"] + "</li>"
              html   += "<li>Active: " + str(camera[cam].active) + "</li>"
              html   += "<li>Record: " + str(info["record"]) + "</li>"
              html   += "<li>Crop: "   + str(info["image"]["crop"]) + "</li>"
              html   += "<li>Detection (red rectangle): <ul>"
              html     += "<li>Threshold: " + str(info["similarity"]["threshold"]) + "%</li>"
              html     += "<li>Area: "      + str(info["similarity"]["detection_area"]) + "</li>"
              html   += "</ul></li>"
              html   += "</ul>"
              if self.adminAllowed():
                if camera[cam].active and camera[cam].param["video"]["allow_recording"]:
                  html   += "<hr width='100%'/>"
                  html   += "<center><button onclick='requestAPI(\"/start/recording/"+cam+"\");'>Record</button> &nbsp;"
                  html   += "<button onclick='requestAPI(\"/stop/recording/"+cam+"\");'>Stop</button></center>"
              html  += "</div>"
              html  += "</div>"
              count += 1
              if count < len(camera):
               html += "<div class='separator'><hr/>"
              
#            if self.adminAllowed():
#              html += "<div class='separator'><hr/>"
#              html += "<button onclick='requestAPI(\"/restart-cameras\");'>Kameras neu starten</button>"
#              html += "</div>"

            config.html_replace["subtitle"]  = myPages["cam_info"][0]
            config.html_replace["links"]     = self.printLinks(link_list=("live","today","videos","favorit"), cam=which_cam)
            config.html_replace["file_list"] = html
            self.streamFile(type='text/html',  content=read_html('html','list.html'), no_cache=True)


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
            
            try:
                while stream:
                  if camera[which_cam].type == "pi":
                     camera[which_cam].setText(datetime.now().strftime('%d.%m.%Y %H:%M:%S'))

                  frame = camera[which_cam].getImage()
                  
                  if camera[which_cam].video.recording:                                          
                     frame = camera[which_cam].setText2Image(frame, "Recording", position=(100,100), color=(0,0,255), fontScale=1, thickness=1)
                     time.sleep(1)                     
                     
                  if self.path.startswith("/detection/"):
                     frame = camera[which_cam].drawImageDetectionArea(image=frame)
                     
                  camera[which_cam].wait()
                  self.streamVideoFrame(frame)

            except Exception as e:
                logging.warning('Removed streaming client %s: %s', self.client_address, str(e))
                stream = False

        # images, css, js
        elif self.path.startswith('/videos') and self.path.endswith('.jpeg'):
                                                self.streamFile(type='image/jpg', content=read_image('',self.path))
        elif self.path.endswith('.css'):        self.streamFile(type='text/css',  content=read_html('html',self.path))
        elif self.path.endswith('.js'):         self.streamFile(type='text/javascript',  content=read_html('html',self.path))
        elif self.path.endswith('icon.png'):    self.streamFile(type='image/png', content=read_image('html','icon.png'))
        elif self.path.endswith('favicon.ico'): self.streamFile(type='image/ico', content=read_image('html','favicon.ico'))
        elif self.path.endswith(".png"):        self.streamFile(type='image/png', content=read_image("",self.path))
        elif self.path.endswith(".jpg"):        self.streamFile(type='image/jpg', content=read_image("images",self.path))
        elif self.path.endswith(".jpeg"):       self.streamFile(type='image/jpg', content=read_image("images",self.path))
        elif self.path.endswith(".mp4"):        self.streamFile(type='video/mp4', content=read_image("videos",self.path))

        # unknown
        else:
            self.sendError()


#----------------------------------------------------


# execute only if run as a script
if __name__ == "__main__":

    logging.basicConfig(format='%(levelname)s: %(message)s',level=logging.INFO)
    #logging.basicConfig(format='%(levelname)s: %(message)s',level=logging.DEBUG)
    signal.signal(signal.SIGINT,  onexit)
    signal.signal(signal.SIGTERM, onkill)
    
    config   = myConfig(param_init=myParameters, main_directory=os.path.dirname(os.path.abspath(__file__)))
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

    time.sleep(1)

    backup = myBackupRestore(config, camera)
    backup.start()

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

