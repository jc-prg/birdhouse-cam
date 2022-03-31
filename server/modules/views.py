import os
import time
import logging
import threading
from sys import getsizeof
from datetime import datetime, timedelta
from modules.presets import birdhouse_pages


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


def print_links_json(link_list, cam=""):
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
            "link": birdhouse_pages[link][2],
            "camera": cam_link,
            "description": birdhouse_pages[link][0],
            "position": count
        }
        count += 1
    return json


def create_chart_data(data):
    chart = {
        "titles": ["Activity"],
        "data": {}
    }
    used_keys = []
    used_cameras = []

    for key in data:
        print_key = key[0:2]+":"+key[2:4]
        if data[key]["camera"] not in used_cameras:
            used_cameras.append(data[key]["camera"])
        if "similarity" in data[key]:
            if round(float(data[key]["similarity"])) == 0:
                data[key]["similarity"] = 100
            chart["data"][print_key] = [100-float(data[key]["similarity"])]
        if "sensor" in data[key]:
            for sensor in data[key]["sensor"]:
                for sensor_key in data[key]["sensor"][sensor]:
                    sensor_title = sensor + ":" + sensor_key
                    if sensor_title not in chart["titles"]:
                        chart["titles"].append(sensor_title)

    for key in data:
        print_key = key[0:2] + ":" + key[2:4]
        if print_key not in used_keys and used_cameras[0] == data[key]["camera"]:
            used_keys.append(print_key)
            for sensor_title in chart["titles"]:
                if sensor_title != "Activity":
                    sensor = sensor_title.split(":")
                    if "sensor" in data[key] and sensor[0] in data[key]["sensor"] and sensor[1] in data[key]["sensor"][sensor[0]]:
                        chart["data"][print_key].append(data[key]["sensor"][sensor[0]][sensor[1]])

    return chart


class BirdhouseViews(threading.Thread):

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
        self.archive_views = {}

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
            self.config.param["server"]["ip4_admin_deny"]))
        if self.server.address_string() in self.config.param["server"]["ip4_admin_deny"]:
            return False
        else:
            return True

    def selected_camera(self, check_path=""):
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
        elif "?" in path:
            param = path.split("?")
            which_cam = param[1]

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

    def index(self, server):
        """
        Index page with live streaming pictures
        """
        self.server = server
        path, which_cam = self.selected_camera()
        content = {
            "active_cam": which_cam,
            "view": "index"
        }
        if self.admin_allowed():
            content["links"] = print_links_json(link_list=("favorit", "today", "backup", "cam_info"))
        else:
            content["links"] = print_links_json(link_list=("favorit", "today", "backup"))

        return content

    def favorites(self, server):
        """
        Page with pictures (and videos) marked as favorits and sorted by date
        """
        self.server = server
        path, which_cam = self.selected_camera()
        content = {
            "active_cam": which_cam,
            "view": "favorits",
            "entries": {},
            "groups": {}
        }
        favorites = {}

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
                favorites[new] = files[stamp]
                favorites[new]["source"] = ("images", "")
                favorites[new]["date"] = "Aktuell"
                favorites[new]["time"] = stamp[0:2] + ":" + stamp[2:4] + ":" + stamp[4:6]
                if "type" not in favorites[new]:
                    favorites[new]["type"] = "image"
                favorites[new]["category"] = category + stamp
                favorites[new]["directory"] = "/" + self.config.directories["images"]

        if date_today in files_videos:
            for stamp in files_videos[date_today]:
                new = stamp
                favorites[new] = files_videos[date_today][stamp]
                favorites[new]["source"] = ("videos", "")
                favorites[new]["date"] = "Aktuell"
                favorites[new]["time"] = stamp[0:2] + ":" + stamp[2:4] + ":" + stamp[4:6]
                favorites[new]["type"] = "video"
                favorites[new]["category"] = category + stamp
                favorites[new]["directory"] = "/" + self.config.directories["videos"]

        if len(favorites) > 0:
            content["view_count"] = ["star"]
            content["groups"]["today"] = []
            for entry in favorites:
                content["entries"][entry] = favorites[entry]
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
            favorites[directory] = {}

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
                                    favorites[directory][new] = files[stamp]
                                    favorites[directory][new]["source"] = ("backup", directory)
                                    favorites[directory][new]["date"] = date
                                    favorites[directory][new]["time"] = stamp[0:2] + ":" + stamp[2:4] + ":" + stamp[4:6]
                                    favorites[directory][new]["date2"] = favorites[directory][new]["date"]
                                    if "type" not in favorites[directory][new]:
                                        favorites[directory][new]["type"] = "image"
                                    favorites[directory][new]["category"] = category + stamp
                                    favorites[directory][new]["directory"] = "/" + self.config.directories[
                                        "backup"] + directory + "/"

            if directory in files_videos:
                for stamp in files_videos[directory]:
                    new = stamp
                    date = directory[6:8] + "." + directory[4:6] + "." + directory[0:4]
                    favorites[directory][new] = files_videos[directory][stamp]
                    favorites[directory][new]["source"] = ("videos", "")
                    favorites[directory][new]["date"] = date  # ?????
                    favorites[directory][new]["time"] = stamp[0:2] + ":" + stamp[2:4] + ":" + stamp[4:6]
                    favorites[directory][new]["type"] = "video"
                    favorites[directory][new]["category"] = "/videos/" + stamp
                    favorites[directory][new]["directory"] = "/" + self.config.directories["videos"]

            if len(favorites[directory]) > 0:
                content["groups"][date] = []
                for entry in favorites[directory]:
                    content["entries"][entry] = favorites[directory][entry]
                    content["groups"][date].append(entry)

        content["view_count"] = ["star"]
        content["subtitle"] = birdhouse_pages["favorit"][0]
        content["links"] = print_links_json(link_list=("live", "today", "videos", "backup"), cam=which_cam)

        return content

    def list(self, server):
        """
        Page with pictures (and videos) of a single day
        """
        self.server = server
        param = server.path.split("/")
        path, which_cam = self.selected_camera()
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

            content["subtitle"] = birdhouse_pages["backup"][0] + " " + files_data["info"]["date"]
            content["links"] = print_links_json(link_list=("live", "today", "backup", "favorit"), cam=which_cam)

        elif os.path.isfile(self.config.file(config="images")):
            backup = False
            files_all = self.config.read_cache(config="images")
            time_now = datetime.now().strftime('%H%M%S')
            check_similarity = True
            category = "/current/"
            subdirectory = ""
            first_title = "Heute &nbsp; "

            content["subtitle"] = birdhouse_pages["today"][0]
            if self.admin_allowed():
                content["links"] = print_links_json(
                    link_list=("live", "favorit", "today_complete", "videos", "backup"), cam=which_cam)
            else:
                content["links"] = print_links_json(link_list=("live", "favorit", "videos", "backup"), cam=which_cam)

        if files_all != {}:

            # Today or backup
            files_today = {}
            stamps = list(reversed(sorted(files_all.keys())))

            for stamp in stamps:
                if "datestamp" not in files_all[stamp]:
                    files_all[stamp]["datestamp"] = date_backup
                if "date" not in files_all[stamp]:
                    files_all[stamp]["date"] = date_backup[6:8] + "." + date_backup[4:6] + "." + date_backup[0:4]

                # GROSSE BAUSTELLE

                select_image = self.camera[which_cam].image_to_select(timestamp=stamp, file_info=files_all[stamp], check_similarity=check_similarity)
                if ((int(stamp) < int(time_now) or time_now == "000000") and files_all[stamp]["datestamp"] == date_today) or files_all[stamp]["datestamp"] == date_backup:
                    if "camera" not in files_all[stamp] or select_image or (backup and files_all[stamp]["camera"] == which_cam):
                        if files_all[stamp]["datestamp"] == date_today or backup:
                            files_today[stamp] = files_all[stamp].copy()
                            if "type" not in files_today[stamp]:
                                files_today[stamp]["type"] = "image"
                            files_today[stamp]["category"] = category + stamp
                            files_today[stamp]["detect"] = self.camera[which_cam].image_differs(file_info=files_today[stamp])
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
                        if self.camera[which_cam].image_to_select(timestamp=stamp, file_info=files_all[stamp],
                                                                  check_similarity=check_similarity):
                            files_yesterday[stamp] = files_all[stamp]
                            if not "type" in files_yesterday[stamp]:
                                files_yesterday[stamp]["type"] = "image"
                            files_yesterday[stamp]["category"] = category + stamp
                            files_yesterday[stamp]["detect"] = self.camera[which_cam].image_differs(
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
        content["chart_data"] = create_chart_data(content["entries"].copy())
        return content

    def archive_list(self, camera):
        content = self.archive_views[camera]
        if self.admin_allowed():
            content["links"] = print_links_json(link_list=("live", "favorit", "today", "today_complete", "videos"), cam=camera)
        else:
            content["links"] = print_links_json(link_list=("live", "favorit", "today", "videos"), cam=camera)
        return content

    def create_archive_list(self):
        """
        Page with backup/archive directory
        """
        logging.info("Create data for archive view from '"+self.config.directory(config="backup")+"' ...")
        for cam in self.camera:
            content = {
                "active_cam": cam,
                "view": "backup",
                "entries": {},
                "groups": {}
            }

            main_directory = self.config.directory(config="backup")
            dir_list = [f for f in os.listdir(main_directory) if os.path.isdir(os.path.join(main_directory, f))]
            dir_list.sort(reverse=True)
            dir_total_size = 0
            files_total = 0

            image_title = str(self.config.param["backup"]["time"]) + str(self.camera[cam].param["image_save"]["seconds"][0])
            image_today = self.config.imageName(image_type="lowres", timestamp=image_title, camera=cam)
            image = os.path.join(self.config.directory(config="images"), image_today)

            for directory in dir_list:
                group_name = directory[0:4] + "-" + directory[4:6]
                if "groups" not in content:
                    content["groups"] = {}
                if group_name not in content["groups"]:
                    content["groups"][group_name] = []

                if os.path.isfile(self.config.file(config="backup", date=directory)):

                    file_data = self.config.read_cache(config="backup", date=directory)
                    content["groups"][group_name].append(directory)

                    if "info" not in file_data or "files" not in file_data:
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
                        dir_count_data = 0

                        if image_title in file_data["files"] and "lowres" in file_data["files"]:
                            image = os.path.join(directory, file_data["files"][image_title]["lowres"])
                        else:
                            for file in list(sorted(file_data["files"].keys())):
                                if "camera" in file_data["files"][file] and file_data["files"][file]["camera"] == cam \
                                        and file_data["files"][file]["type"] == "image":
                                    first_img = file
                                    break
                            if first_img != "" and "lowres" in file_data["files"][first_img]:
                                image = os.path.join(directory, file_data["files"][first_img]["lowres"])

                    for file in file_data["files"]:
                        file_info = file_data["files"][file]
                        if ("datestamp" in file_info and file_info["datestamp"] == directory) or "datestamp" not in file_info:
                            if file_info["type"] == "image":
                                count += 1
                            else:
                                dir_count_data += 1

                            if "size" in file_info and "float" in str(type(file_info["size"])):
                                dir_size += file_info["size"]

                            if ("camera" in file_info and file_info["camera"] == cam) or "camera" not in file_info:
                                if "size" in file_info and "float" in str(type(file_info["size"])):
                                    dir_size_cam += file_info["size"]
                                elif "lowres" in file_info:
                                    lowres_file = os.path.join(self.config.directory(config="backup"), directory, file_info["lowres"])
                                    if os.path.isfile(lowres_file):
                                        dir_size_cam += os.path.getsize(lowres_file)
                                        logging.debug("lowres size: "+str(os.path.getsize(lowres_file)))
                                    if "hires" in file_info:
                                        hires_file = os.path.join(self.config.directory(config="backup"), directory, file_info["hires"])
                                        if os.path.isfile(hires_file):
                                            dir_size_cam += os.path.getsize(hires_file)
                                            logging.debug("hires size: " + str(os.path.getsize(hires_file)))
                                if "to_be_deleted" in file_info and int(file_info["to_be_deleted"]) == 1:
                                    dir_count_delete += 1

                                if file_info["type"] == "image":
                                    dir_count_cam += 1

                    dir_size += dir_size_cam
                    dir_size = round(dir_size / 1024 / 1024, 1)
                    dir_size_cam = round(dir_size_cam / 1024 / 1024, 1)
                    dir_total_size += dir_size
                    files_total += count

                    logging.info("- directory: "+str(dir_size)+" / cam: "+str(dir_size_cam)+" / "+str(dir_total_size)+" ("+directory+"/"+cam+")")

                    image = os.path.join(self.config.directories["backup"], image)
                    image_file = image.replace(directory + "/", "")
                    image_file = image_file.replace(self.config.directories["backup"], "")

                    content["entries"][directory] = {
                        "directory": "/" + self.config.directories["backup"] + directory + "/",
                        "type": "directory",
                        "camera": cam,
                        "date": file_data["info"]["date"],
                        "datestamp": directory,
                        "count": count,
                        "count_delete": dir_count_delete,
                        "count_cam": dir_count_cam,
                        "count_data": dir_count_data,
                        "dir_size": dir_size,
                        "dir_size_cam": dir_size_cam,
                        "lowres": image_file
                    }

                else:
                    logging.error("Archive: no config file available: /backup/" + directory)
                    # self.sendError()

            content["view_count"] = []
            content["subtitle"] = birdhouse_pages["backup"][0] + " (" + self.camera[cam].name + ")"
            content["chart_data"] = create_chart_data(content["entries"].copy())
            self.archive_views[cam] = content

    def complete_list_today(self, server):
        """
        Page with all pictures of the current day
        """
        logging.debug("CompleteListToday: Start - "+datetime.now().strftime("%H:%M:%S"))
        self.server = server
        path, which_cam = self.selected_camera()
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
                logging.info(str(stamp)+"/"+str(time_now)+"/"+str(hour_min)+"/"+str(hour_max))
                if int(stamp) <= int(time_now) and int(stamp) >= int(hour_min) and int(stamp) < int(hour_max):
                    if "datestamp" in files_all[stamp] and files_all[stamp]["datestamp"] == date_today:
                        if "camera" in files_all[stamp] and files_all[stamp]["camera"] == which_cam:
                            threshold = self.camera[which_cam].param["similarity"]["threshold"]
                            if "similarity" in files_all[stamp] and float(files_all[stamp]["similarity"]) < float(threshold):
                                if float(files_all[stamp]["similarity"]) > 0:
                                    count_diff += 1
                            files_part[stamp] = files_all[stamp]
                            if not "type" in files_part[stamp]:
                                files_part[stamp]["type"] = "image"
                            files_part[stamp]["detect"] = self.camera[which_cam].image_differs(
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
        content["subtitle"] = birdhouse_pages["today_complete"][0] + " (" + self.camera[which_cam].name + ", " + str(count) + " Bilder)"
        content["links"] = print_links_json(link_list=("live", "favorit", "today", "videos", "backup"), cam=which_cam)
        content["chart_data"] = create_chart_data(content["entries"].copy())

        length = getsizeof(content)/1024
        logging.debug("CompleteListToday: End - "+datetime.now().strftime("%H:%M:%S")+" ("+str(length)+" kB)")
        return content

    def video_list(self, server):
        '''
        Page with all videos 
        '''
        self.server = server
        path, which_cam = self.selected_camera()
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
                #files_all[file]["directory"] = self.camera[which_cam].param["video"]["streaming_server"]
                files_all[file]["directory"] = "http://"+self.config.param["server"]["ip4_stream_video"]
                files_all[file]["directory"] += ":"+str(self.config.param["server"]["port_video"])+"/"
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
        content["subtitle"] = birdhouse_pages["videos"][
            0]  # + " (" + self.camera[which_cam].name +", " + str(len(files_all)) + " Videos)"

        if self.admin_allowed():
            content["links"] = print_links_json(link_list=("live", "favorit", "cam_info", "today", "backup"))
        else:
            content["links"] = print_links_json(link_list=("live", "favorit", "today", "backup"))

        return content

    def camera_list(self, server):
        '''
        Page with all videos 
        '''
        self.server = server
        path, which_cam = self.selected_camera()
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
            content["entries"][cam]["video"]["stream"] = "/stream.mjpg?" + cam
            content["entries"][cam]["video"]["stream_detect"] = "/detection/stream.mjpg?" + cam
            content["entries"][cam]["device"] = "camera"
            content["entries"][cam]["type"] = self.camera[cam].type
            content["entries"][cam]["active"] = self.camera[cam].active

        content["view_count"] = []
        content["subtitle"] = birdhouse_pages["cam_info"][0]
        content["links"] = print_links_json(link_list=("live", "favorit", "today", "videos", "backup"), cam=which_cam)

        return content.copy()

    def detail_view_video(self, server):
        """
        Show details and edit options for a video file
        """
        self.server = server
        path, which_cam = self.selected_camera()
        content = {"active_cam": which_cam, "view": "detail_video", "entries": {}}
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
                    # "VIDEOFILE": self.camera[which_cam].param["video"]["streaming_server"] + data["video_file"],
                    "VIDEOFILE": "http://"+self.config.param["server"]["ip4_stream_video"]+":"+str(self.config.param["server"]["port_video"])+"/",
                    "THUMBNAIL": data["thumbnail"],
                    "LENGTH": str(data["length"]),
                    "VIDEOID": video_id,
                    "ACTIVE": which_cam,
                    "JAVASCRIPT": "createShortVideo();"
                }

        content["view_count"] = []
        content["subtitle"] = birdhouse_pages["video_info"][0]
        content["links"] = print_links_json(link_list=("live", "favorit", "today", "videos", "backup"))

        return content
