#!/usr/bin/python3

# Ideen:
# - Videos aufzeichnen, z.B. wenn Bewegung detektiert wird
# - Favoriten -> eindeutigen Timestamp (date + time)
# - BACKUP auf mehrere Kameras anpassen!
# - Similarity Threshold je Kamera separat!

import io, os, time
import logging
import json, codecs
import numpy as np
import signal, sys, string

import picamera
import imutils, cv2
from imutils.video import WebcamVideoStream
from imutils.video import FPS
from skimage.metrics import structural_similarity as ssim

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
        self.end_headers()

    def sendError(self):
        '''
        Send file not found
        '''
        self.send_error(404)
        self.end_headers()

    def streamFile(self,type,content):
        '''
        send file content (HTML, image, ...)
        '''
        if len(content) > 0:
           self.send_response(200)
           self.send_header('Content-Type', type)
           self.send_header('Content-Length', len(content))
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

    def printYesterday(self):
        return "<div class='separator'><hr/>Gestern<hr/></div>"


    def printStar(self,file="",favorit=0,check_ip=""):
       if int(favorit) == 1:
          star    = "/html/star1.png"
          value   = "0"
       else:
          star    = "/html/star0.png"
          value   = "1"
       if check_ip != config.param["ip_deny_favorit"]:  onclick = "setFavorit(\""+file+"\",document.getElementById(\"s_"+file+"_value\").innerHTML);"
       else:                                            onclick = ""
       return "<div class='star'><div id='s_"+file+"_value' style='display:none;'>"+value+"</div><img class='star_img' id='s_"+file+"' src='" + star + "' onclick='"+onclick+"'/></div>\n"


    def printTrash(self,file="",delete=0,check_ip=""):
       if int(delete) == 1:
          trash   = "/html/recycle1.png"
          value   = "0"
       else:
          trash   = "/html/recycle0.png"
          value   = "1"
       if check_ip != config.param["ip_deny_favorit"]:  onclick = "setTrash(\""+file+"\",document.getElementById(\"d_"+file+"_value\").innerHTML);"
       else:                                            onclick = ""
       return "<div class='trash'><div id='d_"+file+"_value' style='display:none;'>"+value+"</div><img class='trash_img' id='d_"+file+"' src='" + trash + "' onclick='"+onclick+"'/></div>\n"


    def printImageContainer(self, description, lowres, hires='',star='', trash='', window='blank', lazzy=''):
        html = "<div class='image_container'>"
        if star  != '':      html += star
        else:                html += "<div class='star'></div>"
        if trash  != '':     html += trash
        else:                html += "<div class='trash'></div>"
        if lazzy == 'lazzy': lazzy = "data-"
        else:                lazzy = ""
        if lowres == "EMPTY":
          html += "<div class='thumbnail_container'><div class='thumbnail' style='background-color:#222222;'><br/><br/><small>"+description+"</small></div></div>"
        else:
          if hires != '':      html += "<div class='thumbnail_container'><a href='"+hires+"' target='_"+window+"'><img "+lazzy+"src='"+lowres+"' id='"+lowres+"' class='thumbnail'/></a><br/><small>"+description+"</small></div>"
          else:                html += "<div class='thumbnail_container'><img "+lazzy+"src='"+lowres+"' id='"+lowres+"' class='thumbnail'/><br/><small>"+description+"</small></div>"
        html += "</div>"
        return html


    def printLinks(self, link_list, camera=""):
        html  = ""
        count = 0
        if camera != "": camera = '?' + camera
        for link in link_list:
            count += 1
            html  += "<a href='"+myPages[link][1]+camera+"'>"+myPages[link][0]+"</a>"
            if count < len(link_list): html += " / "
        return html


    def printImageGroup(self, title, id, image_group, index, diff, check_ip="", cam=''):
           onclick = "onclick='showHideGroup(\""+id+"\")'"
           html    = "<div class='separator' style='align:left;background-color:#111111;' align='left' "+onclick+">"
           html   += "<a id='group_link_"+id+"' style='cursor:pointer;'>(+)</a> "
           html   += title + " ... " + str(len(image_group))
           if diff > 0: html += " -&gt; " + str(diff)
           html += "</div><div class='separator'><hr/></div>\n"
           id_list = ""
           images  = ""

           for stamp in image_group:
              time       = stamp[0:2]+":"+stamp[2:4]+":"+stamp[4:6]
              if "favorit" in image_group[stamp]:        star   = self.printStar(file=index+stamp, favorit=image_group[stamp]["favorit"], check_ip=check_ip)
              else:                                      star   = self.printStar(file=index+stamp, favorit=0, check_ip=check_ip)
              if "to_be_deleted" in image_group[stamp]:  trash  = self.printTrash(file=index+stamp, delete=image_group[stamp]["to_be_deleted"], check_ip=check_ip)
              else:                                      trash  = self.printTrash(file=index+stamp, delete=0, check_ip=check_ip)

              similarity = str(image_group[stamp]["similarity"])+'%'
              threshold  = camera[cam].param["similarity"]["threshold"]
              if float(image_group[stamp]["similarity"]) < float(threshold) and float(image_group[stamp]["similarity"]) > 0:
                 similarity = "<u>"+similarity+"</u>"

              hires    = ""
              lowres   = image_group[stamp]["lowres"]
              if "hires" in image_group[stamp]:
                 hires = image_group[stamp]["hires"]

              id_list   += lowres + " "
              images    += self.printImageContainer(description=time + " ("+similarity+")", lowres=lowres, hires=hires, star=star, trash=trash, lazzy='lazzy')

           html += "<div id='group_"+id+"' style='display:none;'>"+images+"</div>\n"
           html += "<div id='group_ids_"+id+"' style='display:none;'>"+id_list+"</div>\n"
           return html

    #-------------------------------------

    def do_POST(self):
        '''
        REST API for javascript commands e.g. to change values in runtime
        '''
        # set / unset favorit
        if self.path.startswith("/favorit/current/"):
           param = self.path.split("/")
           config_data = config.read(config="images")
           config_data[param[3]]["favorit"] = param[4]
           config.write(config="images", config_data=config_data)
           self.streamFile('application/json', json.dumps({ "path" : self.path }).encode(encoding='utf_8'));

        # set / unset favorit
        elif self.path.startswith("/favorit/backup/"):
           param = self.path.split("/")
           config_data = config.read(config="backup", date=param[3])
           config_data["files"][param[4]]["favorit"] = param[5]
           config.write(config="backup",config_data=config_data, date=param[3])
           self.streamFile('application/json', json.dumps({ "path" : self.path }).encode(encoding='utf_8'));

        # set / unset favorit
        if self.path.startswith("/delete/current/"):
           param = self.path.split("/")
           config_data = config.read(config="images")
           config_data[param[3]]["to_be_deleted"] = param[4]
           config.write(config="images", config_data=config_data)
           self.streamFile('application/json', json.dumps({ "path" : self.path }).encode(encoding='utf_8'));

        # set / unset favorit
        elif self.path.startswith("/delete/backup/"):
           param = self.path.split("/")
           config_data = config.read(config="backup", date=param[3])
           config_data["files"][param[4]]["to_be_deleted"] = param[5]
           config.write(config="backup",config_data=config_data, date=param[3])
           self.streamFile('application/json', json.dumps({ "path" : self.path }).encode(encoding='utf_8'));

        else:
           self.sendError()

    #-------------------------------------

    def do_GET(self):
        '''
        check path and send requested content
        '''
        logging.debug("GET request with '" + self.path + "'.")

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

        # index with embedded live stream
        if   self.path == '/': self.redirect("/index.html")
        elif self.path == '/index.html':

            if camera["cam1"].active and camera["cam2"].active:
               if which_cam == "cam1":   index_file = "index_cam1+cam2.html"
               elif which_cam == "cam2": index_file = "index_cam2+cam1.html"
               else:                     index_file = "index.html"
            else:
               index_file = "index.html"

            config.html_replace["links"] = self.printLinks(("today","backup","favorit","cam_info"),which_cam)
            self.streamFile('text/html',read_html('html',index_file))

        # List favorit images (marked with star)
        elif '/list_star.html' in self.path:

            html                             = ""
            favorits                         = {}
            config.html_replace["subtitle"]  = myPages["favorit"][0] + " (" + camera[which_cam].name + ")"
            config.html_replace["links"]     = self.printLinks(link_list=("live","today","backup"), camera=which_cam)

            files = config.cache(config="images")
            for stamp in files:
              if "favorit" in files[stamp] and int(files[stamp]["favorit"]) == 1:
                new = datetime.now().strftime("%Y%m%d")+"_"+stamp
                favorits[new]           = files[stamp]
                favorits[new]["source"] = ("images","")
                favorits[new]["date"]   = "Aktuell"
                favorits[new]["time"]   = stamp[0:2]+":"+stamp[2:4]+":"+stamp[4:6]

            path           = config.directory(config="backup")
            dir_list       = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
            for directory in dir_list:
              files = config.cache(config="backup",date=directory)["files"]
              for stamp in files:
                if "favorit" in files[stamp] and int(files[stamp]["favorit"]) == 1:
                  new = directory+"_"+stamp
                  favorits[new]           = files[stamp]
                  favorits[new]["source"] = ("backup",directory)
                  favorits[new]["date"]   = directory[6:8]+"."+directory[4:6]+"."+directory[0:4]
                  favorits[new]["time"]   = stamp[0:2]+":"+stamp[2:4]+":"+stamp[4:6]

            favorit_sort = list(reversed(sorted(favorits.keys())))
            for stamp in favorit_sort:
              info  = favorits[stamp]["source"][0] + "/" + favorits[stamp]["source"][1]
              info += " - " + favorits[stamp]["lowres"] + "<br/>"
              logging.debug(info)
              stamp1,stamp2 = stamp.split("_")

              entry = favorits[stamp]
              if entry["source"][0] == "backup":
                 dir            = os.path.join(entry["source"][0],entry["source"][1])
                 index          = "/backup/"+entry["source"][1]+"/"
                 entry["date"]  = "<a href='/backup/"+entry["source"][1]+"/list_short.html'>"+entry["date"]+"</a>"
              else:
                 dir   = ""
                 index = "/current/"
                 entry["date"]  = "<a href='/list_short.html'>"+entry["date"]+"</a>"

              if "favorit" in entry:                     star  = self.printStar(file=index+stamp2, favorit=entry["favorit"], check_ip=self.address_string())
              else:                                      star  = self.printStar(file=index+stamp2, favorit=0, check_ip=self.address_string())
              if "to_be_deleted" in entry:               trash = self.printTrash(file=index+stamp, delete=entry["to_be_deleted"], check_ip=self.address_string())
              else:                                      trash = self.printTrash(file=index+stamp, delete=0, check_ip=self.address_string())

              html += self.printImageContainer(description="<b>"+entry["date"]+"</b><br/>"+entry["time"], lowres=os.path.join(dir,entry["lowres"]), hires=os.path.join(dir,entry["hires"]), star=star, window="blank")

            config.html_replace["file_list"] = html
            self.streamFile('text/html',read_html('html','list.html'))

        # List only if threshold ...
        elif '/list_short.html' in self.path:

           html          = ""
           files         = {}
           count         = 0
           file_dir      = self.path.split("/")
           backup_config = config.files["images"]
           today         = datetime.now().strftime("%Y%m%d")

           logging.error("list_short")

           if file_dir[1] == "backup":
               path       = config.directory(config="backup", date=file_dir[2])
               files_data = config.read(config="backup", date=file_dir[2])
               files      = files_data["files"]
               index      = self.path.replace("list_short.html","")
               time_now   = "000000"

               config.html_replace["subtitle"]  = myPages["backup"][0] + " " + files_data["info"]["date"] + " (" + camera[which_cam].name + ", " + str(files_data["info"]["count"]) + " Bilder)"
               config.html_replace["links"]     = self.printLinks(link_list=("live","today","backup","favorit"), camera=which_cam)

           elif os.path.isfile(config.file(config="images")):
               path     = config.directory(config="images")
               files    = config.read(config="images")
               time_now = datetime.now().strftime('%H%M%S')
               index    = "/current/"
               html     = self.printImageContainer(description="Live-Stream", lowres="stream.mjpg?"+which_cam, hires="/index.html",star="",window="self")

               config.html_replace["subtitle"]  = myPages["today"][0] + " (" + camera[which_cam].name + ")"
               config.html_replace["links"]     = self.printLinks(link_list=("live","today_complete","backup","favorit"), camera=which_cam)

           if files != {}:
               stamps   = list(reversed(sorted(files.keys())))

               # Today
               for stamp in stamps:
                 if int(stamp) < int(time_now) or time_now == "000000":
#                   if config.selectImage(timestamp=stamp, file_info=files[stamp], camera=which_cam):
                   if camera[which_cam].selectImage(timestamp=stamp, file_info=files[stamp]):
                     if not "datestamp" in files[stamp] or files[stamp]["datestamp"] == today or file_dir[1] == "backup":
                       count   += 1
                       time     = stamp[0:2]+":"+stamp[2:4]+":"+stamp[4:6]
                       file     = files[stamp]["lowres"]
                       file_big = files[stamp]["hires"]

                       if "favorit" in files[stamp]:                   star   = self.printStar(file=index+stamp, favorit=files[stamp]["favorit"], check_ip=self.address_string())
                       else:                                           star   = self.printStar(file=index+stamp, favorit=0, check_ip=self.address_string())
                       if "to_be_deleted" in files[stamp]:             trash  = self.printTrash(file=index+stamp, delete=files[stamp]["to_be_deleted"], check_ip=self.address_string())
                       else:                                           trash  = self.printTrash(file=index+stamp, delete=0, check_ip=self.address_string())
                       if os.path.isfile(os.path.join(path,file_big)): html += self.printImageContainer(description=time+" ("+str(files[stamp]["similarity"])+"%)", lowres=file, hires=file_big, star=star, trash=trash)
                       else:                                           html += self.printImageContainer(description=time+" ("+str(files[stamp]["similarity"])+"%)", lowres=file, hires="",       star=star, trash=trash)

               # Yesterday
               html_yesterday = ""
               for stamp in stamps:
                 if int(stamp) >= int(time_now) and time_now != "000000":
#                   if config.selectImage(timestamp=stamp, file_info=files[stamp], camera=which_cam):
                   if camera[which_cam].selectImage(timestamp=stamp, file_info=files[stamp]):
                     count   += 1
                     time     = stamp[0:2]+":"+stamp[2:4]+":"+stamp[4:6]
                     file     = files[stamp]["lowres"]
                     file_big = files[stamp]["hires"]

                     if "favorit" in files[stamp]:                   star  = self.printStar(file=index+stamp, favorit=files[stamp]["favorit"], check_ip=self.address_string())
                     else:                                           star  = self.printStar(file=index+stamp, favorit=0, check_ip=self.address_string())
                     if "to_be_deleted" in files[stamp]:             trash = self.printTrash(file=index+stamp, delete=files[stamp]["to_be_deleted"], check_ip=self.address_string())
                     else:                                           trash = self.printTrash(file=index+stamp, delete=0, check_ip=self.address_string())
                     if os.path.isfile(os.path.join(path,file_big)): html_yesterday += self.printImageContainer(description=time+" ("+str(files[stamp]["similarity"])+"%)", lowres=file, hires=file_big, star=star, trash=trash)
                     else:                                           html_yesterday += self.printImageContainer(description=time+" ("+str(files[stamp]["similarity"])+"%)", lowres=file, hires="",       star=star, trash=trash)

               if html_yesterday != "":
                  html += self.printYesterday()
                  html += html_yesterday

               html += "<div style='padding:2px;float:left;width:100%'><hr/>"+str(count)+" Bilder / &Auml;hnlichkeit &lt; "+str(camera[which_cam].param["similarity"]["threshold"])+"%</div>"
               config.html_replace["file_list"] = html
               self.streamFile('text/html',read_html('html','list.html'))

           else:
             self.redirect("/list_new.html")

        # List all backup directories
        elif self.path == '/list_backup.html':

           config.html_replace["subtitle"] = myPages["backup"][0] + " (" + camera[which_cam].name + ")"
           config.html_replace["links"]    = self.printLinks(("live","today","today_complete","favorit"), which_cam)

           path           = config.directory(config="backup")
           backup_config  = config.files["backup"]
           dir_list       = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
           dir_list.sort(reverse=True)
           dir_total_size = 0
           files_total    = 0
           html           = ""

           imageTitle     = config.param["preview_backup"]
           imageToday     = config.imageName(type="lowres", timestamp=imageTitle, camera=which_cam)
           image          = os.path.join(config.directory(config="images"), imageToday)

           if os.path.isfile(image):
              html        += self.printImageContainer(description=myPages["today"][0], lowres=imageToday, hires=myPages["today"][1]+"?"+which_cam, star='' ,window="self")
           elif which_cam == "cam1":
              imageToday  = "image_"+imageTitle+".jpg"
              image       = os.path.join(config.directory(config="images"), imageToday)
              html       += self.printImageContainer(description=myPages["today"][0], lowres=imageToday, hires=myPages["today"][1]+"?"+which_cam, star='' ,window="self")

           for directory in dir_list:

              if os.path.isfile(config.file(config="backup",date=directory)):
                 file_data       = config.read(config="backup", date=directory)
                 date            = file_data["info"]["date"]
                 count           = file_data["info"]["count"]
                 dir_size_cam    = 0
                 dir_count_cam   = 0

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
                      dir_count_cam += 1

                 dir_size        = round(file_data["info"]["size"]/1024/1024,1)
                 dir_size_cam    = round(dir_size_cam/1024/1024,1)
                 dir_total_size += dir_size
                 files_total    += count

                 if dir_count_cam > 0:  html  += self.printImageContainer(description="<b>"+date+"</b><br/>"+str(dir_count_cam)+" / "+str(dir_size_cam)+" MB", lowres=image, hires="/backup/"+directory+"/list_short.html", window="self") + "\n"
                 else:                  html  += self.printImageContainer(description="<b>"+date+"</b><br/>Leer für "+which_cam, lowres="EMPTY") + "\n"

              ### >>> should not be necesarry any more ...
              else:
                 logging.warning("Archive: no config file available!"+stamp)
                 date            = directory[6:8] + "." + directory[4:6] + "." + directory[0:4]
                 file_list       = [f for f in os.listdir(os.path.join(path,directory)) if os.path.isfile(os.path.join(path,directory,f)) and "_big" not in f]
                 dir_size        = sum(os.path.getsize(os.path.join(path,directory,f)) for f in os.listdir(os.path.join(path,directory)) if os.path.isfile(os.path.join(path,directory,f)))
                 dir_size        = round(dir_size/1024/1024,1)
                 dir_total_size += dir_size
                 files_total    += len(file_list)
                 html           += self.printImageContainer(description="*<b>"+date+"</b><br/>"+str(len(file_list))+" / "+str(dir_size)+" MB*",lowres="/backup/"+image,hires="/backup/"+directory+"/list.html",window="self")

           html += "<div style='padding:2px;float:left;width:100%'><hr/>Gesamt: " + str(round(dir_total_size,1)) + " MB / " + str(files_total) + " Bilder</div>"
           config.html_replace["file_list"] = html
           self.streamFile('text/html',read_html('html','list.html'))

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
              config.html_replace["links"]    = self.printLinks(link_list=("live","today","backup"), camera=which_cam)

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
                 html += self.printImageGroup(title="Bilder "+hour+":00", id=hour_min, image_group=files_part, index=index, diff=count_diff, cam=which_cam)

           # Yesterday
           files_part = {}
           html_yesterday = ""
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
                 html_yesterday += self.printImageGroup(title="Bilder "+hour+":00", id=hour_min, image_group=files_part, index=index, diff=count_diff, cam=which_cam)

           if html_yesterday != "":
              html += self.printYesterday()
              html += html_yesterday

           #if int(stamp) < int(time_now) or time_now == "000000":

           config.html_replace["file_list"] = html
           self.streamFile('text/html',read_html('html','list.html'))


        # List all files
        elif '/list.html' in self.path:

           files     = self.path.split("/")
           if files[1] == "backup":  path = config.directory(config="backup",date=files[2])
           else:                     path = config.directory(config="images")

           file_list = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)) and "big" not in f]
           file_list.sort(reverse=True)

           if files[1] == "backup":
             config.html_replace["subtitle"] = myPages["backup"][0] + " "+files[2][6:8] + "." + files[2][4:6] + "." + files[2][0:4]+" ("+camera[which_cam].name+", "+str(len(file_list))+" Bilder)"
             config.html_replace["links"]    = self.printLinks(link_list=("live","today_complete","backup"), camera=which_cam)
             index     = "/backup/"
             time_now  = "000000"

           else:
             config.html_replace["subtitle"] = myPages["today_complete"][0] + " ("+camera[which_cam].name+", "+str(len(file_list))+" Bilder)"
             config.html_replace["links"]    = self.printLinks(link_list=("live","today","backup"), camera=which_cam)
             time_now  = datetime.now().strftime('%H%M%S')
             index     = "/current/"
             files     = config.read(config="images")

           html = ""
           # Today
           for file in file_list:
             if ".jpg" in file:
                stamp     = file[6:12]
                if int(stamp) < int(time_now) or time_now == "000000":
                   time     = file[6:8]+":"+file[8:10]+":"+file[10:12]
                   file_big = config.imageName(type="hires",timestamp=stamp)

                   if index == "/current/":
                     if "favorit" in files[stamp]:                   star  = self.printStar(file=index+stamp, favorit=files[stamp]["favorit"], check_ip=self.address_string())
                     else:                                           star  = self.printStar(file=index+stamp, favorit=0, check_ip=address_string())
                     if "to_be_deleted" in image_group[stamp]:       trash = self.printStar(file=index+stamp, delete=image_group[stamp]["to_be_deleted"], check_ip=check_ip)
                     else:                                           trash = self.printStar(file=index+stamp, delete=0, check_ip=check_ip)
                   else: star = ""

                   if os.path.isfile(os.path.join(path,file_big)): html += self.printImageContainer(description=time, lowres=file, hires=file_big, star=star)
                   else:                                           html += self.printImageContainer(description=time, lowres=file, hires="", star=star)

           # Yesterday
           html_yesterday = ""
           for file in file_list:
             if ".jpg" in file:
                stamp     = file[6:12]
                if int(stamp) >= int(time_now) and time_now != "000000":
                   time     = file[6:8]+":"+file[8:10]+":"+file[10:12]
                   file_big = config.imageName(type="hires",timestamp=stamp)

                   if index == "/current/":
                     if "favorit" in files[stamp]:                   star  = self.printStar(file=index+stamp, favorit=files[stamp]["favorit"], check_ip=address_string())
                     else:                                           star  = self.printStar(file=index+stamp, favorit=0, check_ip=addess_string())
                     if "to_be_deleted" in image_group[stamp]:       trash = self.printStar(file=index+stamp, delete=image_group[stamp]["to_be_deleted"], check_ip=check_ip)
                     else:                                           trash = self.printStar(file=index+stamp, delete=0, check_ip=check_ip)
                   else: star = ""

                   if os.path.isfile(os.path.join(path,file_big)): html_yesterday += self.printImageContainer(description=time, lowres=file, hires=file_big, star=star)
                   else:                                           html_yesterday += self.printImageContainer(description=time, lowres=file, hires="", star=star)

           if html_yesterday != "":
              html += self.printYesterday()
              html += html_yesterday

           config.html_replace["file_list"] = html
           self.streamFile('text/html',read_html('html','list.html'))

        # extract and show single image
        elif self.path == '/image.jpg':
            camera[which_cam].setText = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
            camera[which_cam].writeImage('image_'+which_cam+'.jpg',camera[which_cam].convertFrame2Image(camera[which_cam].getFrame()))
            self.streamFile('image/jpeg',read_image("",'image_'+which_cam+'.jpg'))

        # show live stream
        elif self.path.endswith('/cameras.html'):
            html = ""
            for cam in camera:
              info = camera[cam].param
              html += "<div class='camera_info'>"
              html += "<div class='camera_info_image'>"
              html   += self.printImageContainer(description=cam, lowres="/detection/stream.mjpg?"+cam, hires="/index.html?"+cam, star='', window='self') + "<br/>"
              html += "</div>"
              html += "<div class='camera_info_text'><big><b>"+cam+": "+info["name"]+"</b></big>"
              html   += "<ul>"
              html   += "<li>Type: "+info["type"] + "</li>"
              html   += "<li>Active: "+str(info["active"]) + "</li>"
              html   += "<li>Record: "+str(info["record"]) + "</li>"
              html   += "<li>Crop: "+str(info["image"]["crop"]) + "</li>"
              html   += "<li>Detection (red rectangle): <ul>"
              html     += "<li>Threshold: "+str(info["similarity"]["threshold"]) + "%</li>"
              html     += "<li>Area: "+str(info["similarity"]["detection_area"]) + "</li>"
              html   += "</ul></li>"
              html   += "</ul>"
              html += "</div>"
              html += "</div>"

            config.html_replace["links"]     = self.printLinks(link_list=("live","today","backup","favorit"), camera=which_cam)
            config.html_replace["file_list"] = html
            self.streamFile('text/html',read_html('html','list.html'))


        # show live stream
        elif self.path.endswith('/stream.mjpg'):

            self.streamVideoHeader()
            count    = 0
            addText  = ""
            imageOld = []
            stream   = True
            try:
                while stream:

                  if camera[which_cam].type == "pi":
                     camera[which_cam].setText(datetime.now().strftime('%d.%m.%Y %H:%M:%S'))
                     frame = camera[which_cam].getImage() # .getFrame()
                     if self.path.startswith("/detection/"):
                       frame = camera[which_cam].drawImageDetectionArea(image=frame)
                     camera[which_cam].wait()
                     self.streamVideoFrame(frame)

                  elif camera[which_cam].type == "usb":
                     frame = camera[which_cam].getImage()
                     if self.path.startswith("/detection/"):
                       frame = camera[which_cam].drawImageDetectionArea(image=frame)
                     camera[which_cam].wait()
                     self.streamVideoFrame(frame)

                  else:
                     logging.warning("Unknown type of camera ("+camera[which_cam].type+"/"+camera[which_cam].name+")")
                     stream = False

            except Exception as e:
                logging.warning('Removed streaming client %s: %s', self.client_address, str(e))
                stream = False

        # images, css, js
        elif self.path.endswith('.css'):        self.streamFile('text/css' ,read_html('html',self.path))
        elif self.path.endswith('.js'):         self.streamFile('text/javascript' ,read_html('html',self.path))
        elif self.path.endswith('icon.png'):    self.streamFile('image/png',read_image('html','icon.png'))
        elif self.path.endswith('favicon.ico'): self.streamFile('image/ico',read_image('html','favicon.ico'))
        elif self.path.endswith(".png"):        self.streamFile('image/png',read_image("",self.path))
        elif self.path.endswith(".jpg"):        self.streamFile('image/jpg',read_image("images",self.path))
        elif self.path.endswith(".jpeg"):       self.streamFile('image/jpg',read_image("images",self.path))

        # unknown
        else:
            self.sendError()


#----------------------------------------------------


# execute only if run as a script
if __name__ == "__main__":

    logging.basicConfig(format='%(levelname)s: %(message)s',level=logging.INFO)
    #logging.basicConfig(format='%(levelname)s: %(message)s',level=logging.DEBUG)
    signal.signal(signal.SIGINT, onexit)

    config = myConfig(myParameters)
    config.start()

    time.sleep(1)

    if not os.path.isdir(config.directory("images")):
        logging.info("Create image directory...")
        os.mkdir(config.directory("images"))
        logging.info("OK.")

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
    #backup.backup_files("20210331")

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

