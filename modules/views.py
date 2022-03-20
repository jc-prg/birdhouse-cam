import os, time
import logging
import threading

from datetime import datetime, timedelta
from modules.presets import myPages

dir_app_v1 = "/app"


def read_html(filename, content=""):
    """
    read html file, replace placeholders and return for stream via webserver
    """
    if not os.path.isfile(filename):
        logging.warning("File '" + filename + "' does not exist!")
        return ""

    with open(filename, "r") as page:
        PAGE = page.read()

    if content != "":
        for param in content:
            if "<!--" + param + "-->" in PAGE:
                PAGE = PAGE.replace("<!--" + param + "-->", content[param])

    # PAGE = PAGE.encode('utf-8')
    return PAGE


class myViews(threading.Thread):

    def __init__(self, camera, config):
        """
        Initialize new thread and set inital parameters
        """
        threading.Thread.__init__(self)
        self.server = None
        self.active_cams = None
        self._running = True
        self.name = "Views"
        self.camera = camera
        self.config = config
        self.which_cam = ""

    def run(self):
        """
        Do nothing at the moment
        """
        logging.info("Starting HTML views and REST API for GET ...")
        while self._running:
            time.sleep(1)
        logging.info("Stopped HTML views and REST API for GET.")

    def stop(self):
        """
        Do nothing at the moment
        """
        self._running = False

    def admin_allowed(self):
        """
        Check if administration is allowed based on the IP4 the request comes from
        """
        logging.debug("Check if administration is allowed: " + self.server.address_string() + " / " + str(
            self.config.param["ip4_admin_deny"]))
        if self.server.address_string() in self.config.param["ip4_admin_deny"]:
            return False
        else:
            return True

    def selectedCamera(self, check_path=""):
        """
        Check path, which cam has been selected
        """
        which_cam = "cam1"
        if check_path == "":
            path = self.server.path
        else:
            path = check_path

        if "/api" in path and "/api/status" not in path and "/api/version" not in path:
            param = path.split("/")
            if len(param) > 3:
                which_cam = param[3]
            if which_cam not in self.camera or len(param) <= 3:
                logging.warning("Unknown camera requested (%s).", path)
                which_cam = "cam1"

        self.active_cams = []
        for key in self.camera:
            if self.camera[key].active:
                self.active_cams.append(key)

        if not self.camera[which_cam].active and self.active_cams:
            which_cam = self.active_cams[0]

        if check_path == "":
            logging.debug("Selected CAM = " + which_cam + " (" + self.server.path + ")")
        else:
            logging.debug("Selected CAM = " + which_cam + " (" + check_path + ")")

        self.which_cam = which_cam
        return path, which_cam

    def printLinksJSON(self, link_list, cam=""):
        """
        create a list of links based on URLs and descriptions defined in preset.py -> for JSON API
        """
        json = {}
        count = 0
        if cam != "":
            cam_link = cam
        else:
            cam_link = ""

        for link in link_list:
            json[link] = {
                "link": myPages[link][2],
                "camera": cam_link,
                "description": myPages[link][0],
                "position": count
            }
            count += 1
        return json

    def createIndex(self, server):
        """
        Index page with live streaming pictures
        """
        self.server = server
        path, which_cam = self.selectedCamera()
        content = {
            "active_cam": which_cam,
            "view": "index"
        }
        if self.admin_allowed():
            content["links"] = self.printLinksJSON(link_list=("favorit", "today", "backup", "cam_info"))
        else:
            content["links"] = self.printLinksJSON(link_list=("favorit", "today", "backup"))

        return content

    def createFavorits(self, server):
        """
        Page with pictures (and videos) marked as favorits and sorted by date
        """
        self.server = server
        path, which_cam = self.selectedCamera()
        content = {
            "active_cam": which_cam,
            "view": "favorits",
            "entries": {},
            "groups": {}
        }
        favorits = {}

        # videos
        files_videos = {}
        if self.config.exists("videos"):
            files_all = self.config.read_cache(config="videos")
            for file in files_all:
                date = file.split("_")[0]
                if "favorit" in files_all[file] and int(files_all[file]["favorit"]) == 1:
                    if date not in files_videos: files_videos[date] = {}
                    files_videos[date][file] = files_all[file]

        # today
        date_today = datetime.now().strftime("%Y%m%d")
        files = self.config.read_cache(config="images")
        category = "/current/"

        for stamp in files:
            if date_today == files[stamp]["datestamp"] and "favorit" in files[stamp] and int(
                    files[stamp]["favorit"]) == 1:
                new = datetime.now().strftime("%Y%m%d") + "_" + stamp
                favorits[new] = files[stamp]
                favorits[new]["source"] = ("images", "")
                favorits[new]["date"] = "Aktuell"
                favorits[new]["time"] = stamp[0:2] + ":" + stamp[2:4] + ":" + stamp[4:6]
                if "type" not in favorits[new]:
                    favorits[new]["type"] = "image"
                favorits[new]["category"] = category + stamp
                favorits[new]["directory"] = "/" + self.config.directories["images"]

        if date_today in files_videos:
            for stamp in files_videos[date_today]:
                new = stamp
                favorits[new] = files_videos[date_today][stamp]
                favorits[new]["source"] = ("videos", "")
                favorits[new]["date"] = "Aktuell"
                favorits[new]["time"] = stamp[0:2] + ":" + stamp[2:4] + ":" + stamp[4:6]
                favorits[new]["type"] = "video"
                favorits[new]["category"] = category + stamp
                favorits[new]["directory"] = "/" + self.config.directories["videos"]

        if len(favorits) > 0:
            content["view_count"] = ["star"]
            content["groups"]["today"] = []
            for entry in favorits:
                content["entries"][entry] = favorits[entry]
                content["groups"]["today"].append(entry)

        # other days
        main_directory = self.config.directory(config="backup")
        dir_list = [f for f in os.listdir(main_directory) if os.path.isdir(os.path.join(main_directory, f))]
        dir_list = list(reversed(sorted(dir_list)))

        video_list = []
        for file_date in files_videos:
            if file_date not in dir_list:
                dir_list.append(file_date)
                video_list.append(file_date)

        dir_list = list(reversed(sorted(dir_list)))

        for directory in dir_list:
            category = "/backup/" + directory + "/"
            favorits[directory] = {}

            if self.config.exists(config="backup", date=directory):
                files_data = self.config.read_cache(config="backup", date=directory)
                if "info" in files_data and "files" in files_data:
                    files = files_data["files"]
                    date = directory[6:8] + "." + directory[4:6] + "." + directory[0:4]

                    if directory not in video_list:
                        for stamp in files:
                            if "datestamp" in files[stamp] and files[stamp]["datestamp"] == directory:
                                if "favorit" in files[stamp] and int(files[stamp]["favorit"]) == 1:
                                    new = directory + "_" + stamp
                                    favorits[directory][new] = files[stamp]
                                    favorits[directory][new]["source"] = ("backup", directory)
                                    favorits[directory][new]["date"] = date
                                    favorits[directory][new]["time"] = stamp[0:2] + ":" + stamp[2:4] + ":" + stamp[4:6]
                                    favorits[directory][new]["date2"] = favorits[directory][new]["date"]
                                    if "type" not in favorits[directory][new]:
                                        favorits[directory][new]["type"] = "image"
                                    favorits[directory][new]["category"] = category + stamp
                                    favorits[directory][new]["directory"] = "/" + self.config.directories[
                                        "backup"] + directory + "/"

            if directory in files_videos:
                for stamp in files_videos[directory]:
                    new = stamp
                    date = directory[6:8] + "." + directory[4:6] + "." + directory[0:4]
                    favorits[directory][new] = files_videos[directory][stamp]
                    favorits[directory][new]["source"] = ("videos", "")
                    favorits[directory][new]["date"] = date  # ?????
                    favorits[directory][new]["time"] = stamp[0:2] + ":" + stamp[2:4] + ":" + stamp[4:6]
                    favorits[directory][new]["type"] = "video"
                    favorits[directory][new]["category"] = "/videos/" + stamp
                    favorits[directory][new]["directory"] = "/" + self.config.directories["videos"]

            if len(favorits[directory]) > 0:
                content["groups"][date] = []
                for entry in favorits[directory]:
                    content["entries"][entry] = favorits[directory][entry]
                    content["groups"][date].append(entry)

        content["view_count"] = ["star"]
        content["subtitle"] = myPages["favorit"][0]
        content["links"] = self.printLinksJSON(link_list=("live", "today", "videos", "backup"), cam=which_cam)

        return content

    def createList(self, server):
        """
        Page with pictures (and videos) of a single day
        """
        self.server = server
        param = server.path.split("/")
        path, which_cam = self.selectedCamera()
        time_now = datetime.now().strftime('%H%M%S')

        if param[1] != "api":
            if len(param) > 2:
                date_backup = param[2]
            else:
                date_backup = ""
        else:
            if len(param) > 4:
                date_backup = param[4]
            else:
                date_backup = ""

        content = {
            "active_cam": which_cam,
            "active_date": date_backup,
            "view": "list",
            "entries": {},
            "entries_delete": {},
            "entries_yesterday": {}
        }
        files_all = {}
        count = 0

        date_today = datetime.now().strftime("%Y%m%d")
        date_yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y%m%d")

        if date_backup != "":
            backup = True
            path = self.config.directory(config="backup", date=date_backup)
            files_data = self.config.read_cache(config="backup", date=date_backup)
            files_all = files_data["files"]
            check_similarity = False
            category = "/backup/" + date_backup + "/"
            subdirectory = date_backup + "/"
            time_now = "000000"
            first_title = ""

            content["subtitle"] = myPages["backup"][0] + " " + files_data["info"]["date"]
            content["links"] = self.printLinksJSON(link_list=("live", "today", "backup", "favorit"), cam=which_cam)

        elif os.path.isfile(self.config.file(config="images")):
            backup = False
            files_all = self.config.read_cache(config="images")
            time_now = datetime.now().strftime('%H%M%S')
            check_similarity = True
            category = "/current/"
            subdirectory = ""
            first_title = "Heute &nbsp; "

            content["subtitle"] = myPages["today"][0]
            if self.admin_allowed():
                content["links"] = self.printLinksJSON(
                    link_list=("live", "favorit", "today_complete", "videos", "backup"), cam=which_cam)
            else:
                content["links"] = self.printLinksJSON(link_list=("live", "favorit", "videos", "backup"), cam=which_cam)

        if files_all != {}:

            # Today or backup
            files_today = {}
            stamps = list(reversed(sorted(files_all.keys())))

            for stamp in stamps:
                if not "datestamp" in files_all[stamp]:
                    files_all[stamp]["datestamp"] = date_backup
                if not "date" in files_all[stamp]:
                    files_all[stamp]["date"] = date_backup[6:8] + "." + date_backup[4:6] + "." + date_backup[0:4]

                if ((int(stamp) < int(time_now) or time_now == "000000")
                        and files_all[stamp]["datestamp"] == date_today) or files_all[stamp]["datestamp"] == date_backup:
                    if "camera" not in files_all[stamp] or self.camera[which_cam].selectImage(timestamp=stamp, file_info=files_all[stamp], check_similarity=check_similarity):
                        if files_all[stamp]["datestamp"] == date_today or backup:
                            files_today[stamp] = files_all[stamp]
                            if "type" not in files_today[stamp]:
                                files_today[stamp]["type"] = "image"
                            files_today[stamp]["category"] = category + stamp
                            files_today[stamp]["detect"] = self.camera[which_cam].detectImage(
                                file_info=files_today[stamp])
                            files_today[stamp]["directory"] = "/" + self.config.directories["images"] + subdirectory
                            count += 1

            if first_title == "":
                first_title = files_all[stamp]["date"]

            elif not backup:
                files_today["999999"] = {
                    "lowres": "stream.mjpg?" + which_cam,
                    "hires": "index.html?" + which_cam,
                    "camera": which_cam,
                    "type": "addon",
                    "title": "Live-Stream"
                }

            if self.admin_allowed():
                header = True
            else:
                header = False

            content["entries"] = files_today

            # Yesterday
            files_yesterday = {}
            stamps = list(reversed(sorted(files_all.keys())))
            if not backup:
                for stamp in stamps:
                    if (int(stamp) >= int(time_now) and time_now != "000000") and "datestamp" in files_all[stamp] and \
                            files_all[stamp]["datestamp"] == date_yesterday:
                        if self.camera[which_cam].selectImage(timestamp=stamp, file_info=files_all[stamp],
                                                              check_similarity=check_similarity):
                            files_yesterday[stamp] = files_all[stamp]
                            if not "type" in files_yesterday[stamp]:
                                files_yesterday[stamp]["type"] = "image"
                            files_yesterday[stamp]["category"] = category + stamp
                            files_yesterday[stamp]["detect"] = self.camera[which_cam].detectImage(
                                file_info=files_yesterday[stamp])
                            files_yesterday[stamp]["directory"] = "/" + self.config.directories["images"]
                            count += 1

            if len(files_yesterday) > 0:
                content["entries_yesterday"] = files_yesterday

            # To be deleted
            files_recycle = {}
            if self.admin_allowed():
                for stamp in stamps:
                    if "to_be_deleted" in files_all[stamp] and int(files_all[stamp]["to_be_deleted"]) == 1:
                        if files_all[stamp]["camera"] == which_cam:
                            files_recycle[stamp] = files_all[stamp]
                            if not "type" in files_recycle[stamp]:
                                files_recycle[stamp]["type"] = "image"
                            files_recycle[stamp]["category"] = category + stamp
                            files_recycle[stamp]["directory"] = "/" + self.config.directories["images"] + subdirectory
                            count += 1

            if len(files_recycle) > 0:
                if backup:
                    url = "/remove/backup/" + date_backup
                else:
                    url = "/remove/today"

                intro = "<a onclick='removeFiles(\"" + url + "\");' style='cursor:pointer;'>Delete all files marked for recycling ...</a>"
                content["entries_delete"] = files_recycle

        content["subtitle"] += " (" + self.camera[which_cam].name + ", " + str(count) + " Bilder)"
        content["view_count"] = ["all", "star", "detect"]

        return content

    def createBackupList(self, server):
        '''
        Page with backup/archive directory
        '''
        self.server = server
        path, which_cam = self.selectedCamera()
        content = {
            "active_cam": which_cam,
            "view": "backup",
            "entries": {},
            "groups": {}
        }
        param = server.path.split("/")
        if "app-v1" in param: del param[1]
        files_all = {}

        main_directory = self.config.directory(config="backup")
        dir_list = [f for f in os.listdir(main_directory) if os.path.isdir(os.path.join(main_directory, f))]
        dir_list.sort(reverse=True)
        dir_total_size = 0
        files_total = 0

        imageTitle = str(self.config.param["preview_backup"]) + str(
            self.camera[which_cam].param["image_save"]["seconds"][0])
        imageToday = self.config.imageName(type="lowres", timestamp=imageTitle, camera=which_cam)
        image = os.path.join(self.config.directory(config="images"), imageToday)

        for directory in dir_list:

            group_name = directory[0:4] + "-" + directory[4:6]
            if "groups" not in content:
                content["groups"] = {}
            if group_name not in content["groups"]:
                content["groups"][group_name] = []

            if os.path.isfile(self.config.file(config="backup", date=directory)):

                file_data = self.config.read_cache(config="backup", date=directory)
                content["groups"][group_name].append(directory)

                if "info" not in file_data or not "files" in file_data:
                    if directory not in content["entries"]:
                        content["entries"][directory] = {}
                    content["entries"][directory]["error"] = True

                else:
                    count = 0  # file_data["info"]["count"]
                    first_img = ""
                    dir_size_cam = 0
                    dir_size = 0
                    dir_count_cam = 0
                    dir_count_delete = 0

                    if imageTitle in file_data["files"]:
                        image = os.path.join(directory, file_data["files"][imageTitle]["lowres"])
                    else:
                        for file in list(sorted(file_data["files"].keys())):
                            if "camera" in file_data["files"][file] and file_data["files"][file]["camera"] == which_cam:
                                first_img = file
                                break
                        if first_img != "" and "lowres" in file_data["files"][first_img]:
                            image = os.path.join(directory, file_data["files"][first_img]["lowres"])

                for file in file_data["files"]:
                    file_info = file_data["files"][file]
                    if ("datestamp" in file_info and file_info[
                        "datestamp"] == directory) or not "datestamp" in file_info:
                        count += 1
                        if "size" in file_info:
                            dir_size += file_info["size"]

                        if ("camera" in file_info and file_info["camera"] == which_cam) or not "camera" in file_info:
                            if "size" in file_info:
                                dir_size_cam += file_info["size"]
                            elif "lowres" in file_info:
                                lowres_file = os.path.join(self.config.directory(config="backup"), directory,
                                                           file_info["lowres"])
                                if os.path.isfile(lowres_file):    dir_size_cam += os.path.getsize(lowres_file)
                                if "hires" in file_info:
                                    hires_file = os.path.join(self.config.directory(config="backup"), directory,
                                                              file_info["hires"])
                                    if os.path.isfile(hires_file): dir_size_cam += os.path.getsize(hires_file)
                            if "to_be_deleted" in file_info and int(file_info["to_be_deleted"]) == 1:
                                dir_count_delete += 1
                            dir_count_cam += 1

                dir_size = round(dir_size / 1024 / 1024, 1)
                dir_size_cam = round(dir_size_cam / 1024 / 1024, 1)
                dir_total_size += dir_size
                files_total += count

                image = os.path.join(self.config.directories["backup"], image)
                image_file = image.replace(directory + "/", "")
                image_file = image_file.replace(self.config.directories["backup"], "")

                content["entries"][directory] = {
                    "directory": "/" + self.config.directories["backup"] + directory + "/",
                    "type": "directory",
                    "camera": which_cam,
                    "date": file_data["info"]["date"],
                    "datestamp": directory,
                    "count": count,
                    "count_delete": dir_count_delete,
                    "count_cam": dir_count_cam,
                    "dir_size": dir_size,
                    "dir_size_cam": dir_size_cam,
                    "lowres": image_file
                }


            else:
                logging.error("Archive: no config file available: /backup/" + directory)
                # self.sendError()

        content["view_count"] = []
        content["subtitle"] = myPages["backup"][0] + " (" + self.camera[which_cam].name + ")"
        if self.admin_allowed():
            content["links"] = self.printLinksJSON(link_list=("live", "favorit", "today", "today_complete", "videos"),
                                                   cam=which_cam)
        else:
            content["links"] = self.printLinksJSON(link_list=("live", "favorit", "today", "videos"), cam=which_cam)

        return content

    def createCompleteListToday(self, server):
        """
        Page with all pictures of the current day
        """
        self.server = server
        path, which_cam = self.selectedCamera()
        content = {
            "active_cam": which_cam,
            "view": "list_complete",
            "entries": {},
            "groups": {}
        }

        count = 0
        param = server.path.split("/")
        if "app-v1" in param:
            del param[1]

        category = "/current/"
        path = self.config.directory(config="images")
        files_all = self.config.read_cache(config="images")

        time_now = datetime.now().strftime('%H%M%S')
        date_today = datetime.now().strftime("%Y%m%d")
        date_yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y%m%d")

        hours = list(self.camera[which_cam].param["image_save"]["hours"])
        hours.sort(reverse=True)

        # Today
        for hour in hours:
            hour_min = hour + "0000"
            hour_max = str(int(hour) + 1) + "0000"
            files_part = {}
            count_diff = 0
            stamps = list(reversed(sorted(files_all.keys())))
            for stamp in stamps:
                if int(stamp) <= int(time_now) and int(stamp) >= int(hour_min) and int(stamp) < int(hour_max):
                    if "datestamp" in files_all[stamp] and files_all[stamp]["datestamp"] == date_today:
                        if "camera" in files_all[stamp] and files_all[stamp]["camera"] == which_cam:
                            threshold = self.camera[which_cam].param["similarity"]["threshold"]
                            if float(files_all[stamp]["similarity"]) < float(threshold):
                                if float(files_all[stamp]["similarity"]) > 0:
                                    count_diff += 1
                            files_part[stamp] = files_all[stamp]
                            if not "type" in files_part[stamp]:
                                files_part[stamp]["type"] = "image"
                            files_part[stamp]["detect"] = self.camera[which_cam].detectImage(
                                file_info=files_part[stamp])
                            files_part[stamp]["category"] = category + stamp
                            files_part[stamp]["directory"] = "/" + self.config.directories["images"]
                            count += 1

            if len(files_part) > 0:
                content["groups"][hour + ":00"] = []
                for entry in files_part:
                    content["entries"][entry] = files_part[entry]
                    content["groups"][hour + ":00"].append(entry)

        content["view_count"] = ["all", "star", "detect", "recycle"]
        content["subtitle"] = myPages["today_complete"][0] + " (" + self.camera[which_cam].name + ", " + str(
            count) + " Bilder)"
        content["links"] = self.printLinksJSON(link_list=("live", "favorit", "today", "videos", "backup"),
                                               cam=which_cam)

        return content

    def createVideoList(self, server):
        '''
        Page with all videos 
        '''
        self.server = server
        path, which_cam = self.selectedCamera()
        content = {}
        content["active_cam"] = which_cam
        content["view"] = "list_videos"
        param = server.path.split("/")
        if "app-v1" in param: del param[1]

        directory = self.config.directory(config="videos")
        category = "/videos/"  # self.config.directories["videos"]

        files_all = {}
        files_delete = {}
        files_show = {}
        content["entries"] = {}

        if self.config.exists("videos"):
            files_all = self.config.read_cache(config="videos")
            for file in files_all:
                files_all[file]["directory"] = self.camera[which_cam].param["video"]["streaming_server"]
                files_all[file]["type"] = "video"
                files_all[file]["path"] = self.config.directories["videos"]
                files_all[file]["category"] = "/videos/" + file
                if "to_be_deleted" in files_all[file] and int(files_all[file]["to_be_deleted"]) == 1:
                    files_delete[file] = files_all[file]
                else:
                    files_show[file] = files_all[file]

            if len(files_show) > 0:                           content["entries"] = files_show
            if len(files_delete) > 0 and self.admin_allowed(): content["entries_delete"] = files_delete

        content["view_count"] = ["all", "star", "detect", "recycle"]
        content["subtitle"] = myPages["videos"][
            0]  # + " (" + self.camera[which_cam].name +", " + str(len(files_all)) + " Videos)"

        if self.admin_allowed():
            content["links"] = self.printLinksJSON(link_list=("live", "favorit", "cam_info", "today", "backup"))
        else:
            content["links"] = self.printLinksJSON(link_list=("live", "favorit", "today", "backup"))

        return content

    def createCameraList(self, server):
        '''
        Page with all videos 
        '''
        self.server = server
        path, which_cam = self.selectedCamera()
        content = {}
        content["active_cam"] = which_cam
        content["view"] = "list_cameras"
        content["entries"] = {}
        param = server.path.split("/")
        if "app-v1" in param: del param[1]
        count = 0

        for cam in self.camera:
            info = self.camera[cam].param
            content["entries"][cam] = self.camera[cam].param
            content["entries"][cam]["lowres"] = "/detection/stream.mjpg?" + cam
            content["entries"][cam]["hires"] = "/detection/stream.mjpg?" + cam
            content["entries"][cam]["type"] = "camera"
            content["entries"][cam]["camera_type"] = self.camera[cam].type
            content["entries"][cam]["active"] = self.camera[cam].active

        content["view_count"] = []
        content["subtitle"] = myPages["cam_info"][0]
        content["links"] = self.printLinksJSON(link_list=("live", "favorit", "today", "videos", "backup"),
                                               cam=which_cam)

        return content

    def detailViewVideo(self, server):
        '''
        Show details and edit options for a video file
        '''
        self.server = server
        path, which_cam = self.selectedCamera()
        content = {}
        content["active_cam"] = which_cam
        content["view"] = "detail_video"
        content["entries"] = {}
        param = server.path.split("/")
        if "app-v1" in param: del param[1]
        count = 0

        if "api" in param:
            video_id = param[4]
        else:
            video_id = param[1]

        config_data = self.config.read_cache(config="videos")
        if video_id in config_data and "video_file" in config_data[video_id]:

            data = config_data[video_id]
            content["entries"][video_id] = data
            description = ""

            if self.admin_allowed():
                files = {
                    "VIDEOFILE": self.camera[which_cam].param["video"]["streaming_server"] + data["video_file"],
                    "THUMBNAIL": data["thumbnail"],
                    "LENGTH": str(data["length"]),
                    "VIDEOID": video_id,
                    "ACTIVE": which_cam,
                    "JAVASCRIPT": "createShortVideo();"
                }

        content["view_count"] = []
        content["subtitle"] = myPages["video_info"][0]
        content["links"] = self.printLinksJSON(link_list=("live", "favorit", "today", "videos", "backup"))

        return content
