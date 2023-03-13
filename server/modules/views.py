import os
import time
import logging
import threading
from sys import getsizeof
from datetime import datetime, timedelta
import modules.presets as presets
from modules.presets import *


view_logging = logging.getLogger("view-header")
view_logging.setLevel(birdhouse_loglevel)
view_logging.addHandler(birdhouse_loghandler)


def read_html(filename, content=None):
    """
    read html file, replace placeholders and return for stream via webserver
    """
    if content is None:
        content = {}

    if not os.path.isfile(filename):
        view_logging.warning("File '" + filename + "' does not exist!")
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
            "link": presets.birdhouse_pages[link][2],
            "camera": cam_link,
            "description": presets.birdhouse_pages[link][0],
            "position": count
        }
        count += 1
    return json


class BirdhouseViewCreate(object):

    def __init__(self, config):
        self.config = config
        self.logging = logging.getLogger("view-creat")
        self.logging.setLevel(birdhouse_loglevel)
        self.logging.addHandler(birdhouse_loghandler)
        self.logging.info("Starting backup handler ...")

    def chart_data_new(self, data_image, data_sensor=None, data_weather=None, date=None):
        """
        create chart data based on sensor, weather and activity data
        """
        if date is not None:
            datestamp = date
            date_us = date[0:4] + "-" + date[4:6] + "-" + date[6:8]
            date_eu = date[6:8] + "." + date[4:6] + "." + date[0:4]
        else:
            datestamp = ""
            date_eu = ""
            date_us = ""

        self.logging.info("create_chart_data_new: " + datestamp + " / " + date_eu + " / " + date_us)
        hours = ["00", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10",
                 "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23"]
        minutes = ["00", "05", "10", "15", "20", "25", "30", "35", "40", "45", "50", "55"]
        chart = {"titles": ["Activity"], "data": {}}

        # Calculate image activity
        activity_dict = {}
        for key in data_image:
            if date is not None and "datestamp" in data_image[key] and data_image[key]["datestamp"] != datestamp:
                continue
            this_hour = key[0:2]
            this_minute = key[2:4]
            minute_to = str(int(this_minute) + (5 - (int(this_minute) % 5))).zfill(2)
            hour_to = this_hour
            if int(minute_to) > 59:
                hour_to = str(int(hour_to)+1).zfill(2)
            if int(hour_to) > 23:
                hour_to = "00"

            stamp = hour_to + minute_to + "00"
            if stamp not in activity_dict:
                activity_dict[stamp] = []
            activity_dict[stamp].append(key)

        data_activity = {}
        for key in activity_dict:
            activity_sum = 0
            activity_count = 0
            for stamp in activity_dict[key]:
                if "similarity" in data_image[stamp]:
                    activity_sum += float(data_image[stamp]["similarity"])
                    activity_count += 1
            data_activity[key] = round(100 - (activity_sum / activity_count), 2)

        # get categories weather
        weather_data_in_chart = ["temperature", "humidity", "wind_speed"]
        weather_location = self.config.param["weather"]["location"]
        if data_weather is not None:
            for weather_category in weather_data_in_chart:
                weather_title = "WEATHER/" + weather_location + ":" + weather_category
                if weather_title not in chart["titles"]:
                    chart["titles"].append(weather_title)

        # get categories sensor
        sensor_list = []
        sensor_key_list = []
        data_sensor_keys = []
        data_sensor_tmp = {}

        self.logging.info("Chart - Sensor-Input:" + str(len(data_sensor)))

        if data_sensor is not None:
            for stamp in data_sensor:
                for sensor in data_sensor[stamp]:
                    # add date check ... here
                    if sensor != "activity" and sensor != "date":
                        if sensor not in sensor_list:
                            sensor_list.append(sensor)
                        for sensor_key in data_sensor[stamp][sensor]:
                            if sensor_key != "date" and sensor_key != "activity":
                                sensor_title = sensor + ":" + sensor_key
                                if sensor_key not in sensor_key_list:
                                    sensor_key_list.append(sensor_key)
                                if sensor_title not in chart["titles"]:
                                    chart["titles"].append(sensor_title)
                                    data_sensor_keys.append(sensor_title)

                if date is not None and len(sensor_list) > 0 and data_sensor[stamp][sensor_list[0]]["date"] != date_eu:
                    continue

                reduced_stamp = stamp[0:2] + str(int(stamp[2:4]) - (int(stamp[2:4]) % 5)).zfill(2) + "00"
                if reduced_stamp not in data_sensor_tmp:
                    data_sensor_tmp[reduced_stamp] = data_sensor[stamp]

        self.logging.debug("Chart - Sensor-Output:" + str(len(data_sensor_tmp)))
        self.logging.debug("Chart - Sensor-Output:" + str(data_sensor_tmp.keys()))

        # create chart data
        for hour in hours:
            for minute in minutes:
                chart_stamp = hour + ":" + minute
                stamp = hour + minute + "00"

                # check if a value exists
                stamp_exists = False
                stamp_exists_activity = False
                stamp_exists_sensor = False
                stamp_exists_weather = False

                # Check if exists and date is correct
                if stamp in data_activity:
                    stamp_exists_activity = True

                if stamp in data_sensor_tmp:
                    if date is not None and len(sensor_list) > 0 \
                            and data_sensor_tmp[stamp][sensor_list[0]]["date"] == date_eu:
                        stamp_exists_sensor = True
                    elif date is None and len(sensor_list) > 0:
                        stamp_exists_sensor = True

                if stamp in data_weather:
                    if date is not None and data_weather[stamp]["date"] == date_us:
                        stamp_exists_weather = True
                    elif date is None:
                        stamp_exists_weather = True

                if stamp_exists_weather or stamp_exists_sensor or stamp_exists_activity:
                    stamp_exists = True
                    chart["data"][chart_stamp] = []

                # Activity
                if stamp_exists_activity:
                    chart["data"][chart_stamp].append(data_activity[stamp])
                elif stamp_exists:
                    chart["data"][chart_stamp].append(None)

                # Weather data
                if stamp_exists_weather:
                    for value in weather_data_in_chart:
                        if value in data_weather[stamp]:
                            chart["data"][chart_stamp].append(data_weather[stamp][value])
                        else:
                            chart["data"][chart_stamp].append(None)
                elif stamp_exists:
                    for value in weather_data_in_chart:
                        chart["data"][chart_stamp].append(None)

                # Sensor data
                if stamp_exists_sensor:
                    for key in data_sensor_keys:
                        sensor, sensor_key = key.split(":")
                        if sensor in data_sensor_tmp[stamp] and sensor_key in data_sensor_tmp[stamp][sensor]:
                            chart["data"][chart_stamp].append(data_sensor_tmp[stamp][sensor][sensor_key])
                        else:
                            chart["data"][chart_stamp].append(None)
                elif stamp_exists:
                    for value in data_sensor_keys:
                        chart["data"][chart_stamp].append(None)

                self.logging.debug(stamp + ": activity=" + str(stamp_exists_activity) + "; " +
                                   "weather=" + str(stamp_exists_weather) + "; " +
                                   "sensor=" + str(stamp_exists_sensor) + "; " +
                                   "all=" + str(stamp_exists))

        return chart

    def chart_data(self, data):
        self.logging.debug("create_chart_data")
        chart = {
            "titles": ["Activity"],
            "data": {}
        }
        used_keys = []
        used_cameras = []
        weather_data_in_chart = ["temperature", "humidity", "wind"]
        weather_data_interval = 5

        if data == {} or "dict" not in str(type(data)):
            self.logging.error("Could not create chart data (empty)!")

        # get categories / titles
        for key in data:
            print_minute = key[2:4]
            print_key = key[0:2]+":"+key[2:4]
            if int(print_minute) % weather_data_interval == 0:

                if "camera" in data[key] and data[key]["camera"] not in used_cameras:
                    used_cameras.append(data[key]["camera"])

                if "similarity" in data[key]:
                    if round(float(data[key]["similarity"])) == 0:
                        data[key]["similarity"] = 100
                    chart["data"][print_key] = [100-float(data[key]["similarity"])]

                if "sensor" in data[key]:
                    for sensor in data[key]["sensor"]:
                        for sensor_key in data[key]["sensor"][sensor]:
                            if sensor_key != "date":
                                sensor_title = sensor + ":" + sensor_key
                                if sensor_title not in chart["titles"]:
                                    chart["titles"].append(sensor_title)

                if "weather" in data[key]:
                    if "location" in data[key]["weather"]:
                        location = data[key]["weather"]["location"]
                    elif self.config is not None:
                        location = self.config.param["localization"]["weather_location"]
                    else:
                        location = ""
                    for weather_category in weather_data_in_chart:
                        weather_title = "WEATHER/" + location + ":" + weather_category
                        if weather_title not in chart["titles"]:
                            chart["titles"].append(weather_title)

        # get data
        for key in data:
            print_minute = key[2:4]
            print_key = key[0:2] + ":" + key[2:4]
            if int(print_minute) % weather_data_interval == 0:
                if print_key not in used_keys and used_cameras[0] == data[key]["camera"]:
                    used_keys.append(print_key)
                    for title in chart["titles"]:

                        if title != "Activity" and print_key in chart["data"]:
                            sensor = title.split(":")

                            if "sensor" in data[key] and sensor[0] in data[key]["sensor"] and \
                                    sensor[1] in data[key]["sensor"][sensor[0]]:
                                chart["data"][print_key].append(data[key]["sensor"][sensor[0]][sensor[1]])

                            elif "weather" in data[key] and sensor[1] in data[key]["weather"]:
                                chart["data"][print_key].append(data[key]["weather"][sensor[1]])

                            else:
                                chart["data"][print_key].append("")

        return chart

    def weather_data_new(self, data_weather, date=None):
        """
        create hourly weather data for API
        """
        if date is not None:
            date_us = date[0:4] + "-" + date[4:6] + "-" + date[6:8]
        else:
            date_us = ""

        self.logging.debug("create_weather_data_new")
        if data_weather is None:
            return {}

        hours = ["00", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10",
                 "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23"]
        weather = {}

        for hour in hours:
            stamp = hour + "0000"
            if stamp in data_weather:
                if date is not None and data_weather[stamp]["date"] != date_us:
                    continue
                weather[stamp] = data_weather[stamp]
                weather[stamp]["time"] = hour + ":00"

        for hour in hours:
            stamp = hour + "0000"
            if stamp not in weather:
                for key in data_weather:
                    if key == "none" or "date" not in data_weather[key]:
                        continue
                    if date is not None and data_weather[key]["date"] != date_us:
                        continue
                    this_hour = key[0:2]
                    if this_hour == hour:
                        if this_hour + ":00" == data_weather[key]["time"]:
                            weather[stamp] = data_weather[key]
                            weather[stamp]["time"] = this_hour + ":00"
                            continue

        return weather

    def weather_data(self, data):
        """
        create hourly weather data for API
        """
        self.logging.debug("create_weather_data")
        if data is None:
            return {}

        data_weather = {}
        for stamp in data:
            if "weather" in data[stamp]:
                data_weather[stamp] = data[stamp]["weather"]

        hours = ["00", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10",
                 "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23"]
        weather = {}

        for hour in hours:
            stamp = hour + "0000"
            if stamp in data_weather:
                weather[stamp] = data_weather[stamp]
                weather[stamp]["time"] = hour + ":00"

        for hour in hours:
            stamp = hour + "0000"
            if stamp not in weather:
                for key in data_weather:
                    this_time = key[0:4]
                    if this_time == hour + "00":
                        weather[stamp] = data_weather[key]
                        weather[stamp]["time"] = key[0:2] + ":00"
                        continue

        return weather


class BirdhouseViews(threading.Thread):

    def __init__(self, camera, config):
        """
        Initialize new thread and set initial parameters
        """
        threading.Thread.__init__(self)

        self.logging = logging.getLogger("views")
        self.logging.setLevel(birdhouse_loglevel)
        self.logging.addHandler(birdhouse_loghandler)
        self.logging.info("Starting views thread ...")

        self.server = None
        self.active_cams = None
        self._running = True
        self.name = "Views"
        self.camera = camera
        self.config = config
        self.which_cam = ""
        self.archive_views = {}
        self.archive_loading = "started"
        self.archive_dir_size = 0
        self.today_dir_size = 0             # not implemented yet
        self.favorite_views = {}
        self.favorite_loading = "started"
        self.create_archive = True
        self.create_favorites = True
        self.create = BirdhouseViewCreate(config)

    def run(self):
        """
        Do nothing at the moment
        """
        count_rebuild = 60*5   # rebuild when triggerd by relevant events already - max once every 5 minutes
        count = count_rebuild + 1

        self.logging.info("Starting HTML views and REST API for GET ...")
        while self._running:
            # if shutdown
            if self.config.shut_down:
                self.stop()

            # if archive to be read again (from time to time and depending on user activity)
            if self.create_archive and count > count_rebuild:
                time.sleep(10)
                self.archive_list_create()
                self.create_archive = False

            # if favorites to be read again (from time to time and depending on user activity)
            if self.create_favorites and count > count_rebuild:
                time.sleep(10)
                self.favorite_list_create()
                self.create_favorites = False

            if count > count_rebuild:
                count = 0

            if self.config.user_activity():
                count += 1

            time.sleep(1)
        self.logging.info("Stopped HTML views and REST API for GET.")

    def stop(self):
        """
        Do nothing at the moment
        """
        self._running = False

    def admin_allowed(self):
        """
        Check if administration is allowed based on the IP4 the request comes from
        """
        if self.server is None:
            return False

        self.logging.debug("Check if administration is allowed: " + self.server.address_string() + " / " + str(
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
        further_param = ""
        complete_cam = ""

        if check_path == "":
            path = self.server.path
        else:
            path = check_path

        if "/api" in path and "/api/status" not in path and "/api/version" not in path:
            param = path.split("/")
            if len(param) > 3:
                complete_cam = param[3]
                which_cam = param[3]
            if "+" in complete_cam:
                which_cam = complete_cam.split("+")[0]
            if which_cam not in self.camera or len(param) <= 3:
                self.logging.warning("Unknown camera requested (%s).", path)
                which_cam = "cam1"
        elif "?" in path and "index.html" not in path:
            param = path.split("?")
            param = param[1].split("&")
            which_cam = param[0]
            complete_cam = param[0]
            if "+" in complete_cam:
                which_cam = complete_cam.split("+")[0]
            further_param = param

        self.active_cams = []
        for key in self.camera:
            if self.camera[key].active:
                self.active_cams.append(key)

        if not self.camera[which_cam].active and self.active_cams:
            which_cam = self.active_cams[0]

        if check_path == "":
            self.logging.debug("Selected CAM = " + which_cam + " (" + self.server.path + ")")
        else:
            self.logging.debug("Selected CAM = " + which_cam + " (" + check_path + ")")

        self.which_cam = which_cam
        return path, complete_cam, further_param

    def index(self, server):
        """
        Index page with live-streaming pictures
        """
        self.server = server
        path, which_cam, further_param = self.selected_camera()
        content = {
            "active_cam": which_cam,
            "view": "index"
        }
        if self.admin_allowed():
            content["links"] = print_links_json(link_list=("favorit", "today", "backup", "cam_info"))
        else:
            content["links"] = print_links_json(link_list=("favorit", "today", "backup"))

        return content

    def list(self, server):
        """
        Page with pictures (and videos) of a single day
        """
        self.server = server
        param = server.path.split("/")
        path, which_cam, further_param = self.selected_camera()
        time_now = self.config.local_time().strftime('%H%M%S')
        check_similarity = True
        backup = False
        category = ""
        subdirectory = ""
        files_today = {}
        files_images = {}
        files_weather = None
        files_sensor = None

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
            "entries_yesterday": {},
            "links": {},
            "subtitle": "",
            "max_image_size": {
                "lowres": [0, 0],
                "hires": [0, 0]
            }
        }
        files_all = {}
        count = 0

        date_today = self.config.local_time().strftime("%Y%m%d")
        date_yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y%m%d")

        # if backup entry read from respective DB and create vars, links ...
        if date_backup != "":
            backup = True
            path = self.config.db_handler.directory(config="backup", date=date_backup)
            files_data = self.config.db_handler.read_cache(config="backup", date=date_backup)
            if "files" in files_data:
                files_all = files_data["files"].copy()
                self.logging.info("BACKUP/" + date_backup + ": found " + str(len(files_all)) + " entries")
            else:
                self.logging.info("BACKUP/" + date_backup + ": no data found")
                return content

            if "chart_data" in files_data:
                content["chart_data"] = files_data["chart_data"].copy()
            if "weather_data" in files_data:
                content["weather_data"] = files_data["weather_data"].copy()

            check_similarity = False
            category = "/backup/" + date_backup + "/"
            subdirectory = date_backup + "/"
            time_now = "000000"

            content["subtitle"] = presets.birdhouse_pages["backup"][0] + " " + files_data["info"]["date"]
            content["links"] = print_links_json(link_list=("live", "today", "backup", "favorit"), cam=which_cam)

        # else read files from current day and create vars, links ...
        elif self.config.db_handler.exists(config="images"):
            backup = False
            files_all = self.config.db_handler.read_cache(config="images")
            files_weather = self.config.db_handler.read_cache(config="weather")
            files_sensor = self.config.db_handler.read_cache(config="sensor")
            self.logging.info("TODAY: found " + str(len(files_all)) + " entries; " +
                              str(len(files_weather)) + " weather entries; " +
                              str(len(files_sensor)) + " sensor entries")

            time_now = self.config.local_time().strftime('%H%M%S')
            category = "/current/"
            subdirectory = ""

            content["subtitle"] = presets.birdhouse_pages["today"][0]
            if self.admin_allowed():
                content["links"] = print_links_json(
                    link_list=("live", "favorit", "today_complete", "videos", "backup"), cam=which_cam)
            else:
                content["links"] = print_links_json(link_list=("live", "favorit", "videos", "backup"), cam=which_cam)

        # else something went wrong ... ?
        else:
            self.logging.warning("LIST: Could not read data ... " + str(param) + " date=" + date_backup +
                                 "; path=" + path + "; cam=" + which_cam + "; further_param=" + further_param)

        if files_all != {}:

            # Today or backup
            stamps = list(reversed(sorted(files_all.keys())))

            for stamp in stamps:
                if "datestamp" not in files_all[stamp]:
                    files_all[stamp]["datestamp"] = date_backup
                if "date" not in files_all[stamp]:
                    files_all[stamp]["date"] = date_backup[6:8] + "." + date_backup[4:6] + "." + date_backup[0:4]

                if ((int(stamp) < int(time_now) or time_now == "000000")
                        and files_all[stamp]["datestamp"] == date_today) or backup:

                    show_image = self.camera[which_cam].image_to_select(timestamp=stamp, file_info=files_all[stamp],
                                                                        check_similarity=check_similarity)

                    if show_image and ("camera" not in files_all[stamp] or files_all[stamp]["camera"] == which_cam):
                        if "to_be_deleted" not in files_all[stamp] or int(files_all[stamp]["to_be_deleted"]) != 1:

                            # check maximum image size
                            if "lowres_size" in files_all[stamp]:
                                if files_all[stamp]["lowres_size"][0] > content["max_image_size"]["lowres"][0]:
                                    content["max_image_size"]["lowres"][0] = files_all[stamp]["lowres_size"][0]
                                if files_all[stamp]["lowres_size"][1] > content["max_image_size"]["lowres"][1]:
                                    content["max_image_size"]["lowres"][1] = files_all[stamp]["lowres_size"][1]
                            if "hires_size" in files_all[stamp]:
                                if files_all[stamp]["hires_size"][0] > content["max_image_size"]["hires"][0]:
                                    content["max_image_size"]["hires"][0] = files_all[stamp]["hires_size"][0]
                                if files_all[stamp]["lowres_size"][1] > content["max_image_size"]["hires"][1]:
                                    content["max_image_size"]["hires"][1] = files_all[stamp]["hires_size"][1]

                            # copy data to new dict (select relevant data only)
                            files_today[stamp] = files_all[stamp].copy()

                            # prepare further metadata
                            if "type" not in files_today[stamp]:
                                files_today[stamp]["type"] = "image"
                            files_today[stamp]["category"] = category + stamp
                            files_today[stamp]["detect"] = self.camera[which_cam].image_differs(files_today[stamp])
                            files_today[stamp]["directory"] = "/" + self.config.directories["images"] + subdirectory

                            if "type" in files_today[stamp] and files_today[stamp]["type"] != "data":
                                count += 1

                            if "type" in files_all[stamp] and files_all[stamp]["type"] == "image":
                                files_images[stamp] = files_today[stamp].copy()
                                if "weather" in files_images[stamp]:
                                    del files_images[stamp]["weather"]
                                if "sensor" in files_images[stamp]:
                                    del files_images[stamp]["sensor"]

            if not backup:
                files_images["999999"] = {
                    "stream": "lowres/stream.mjpg?" + which_cam,
                    "lowres": "lowres/stream.mjpg?" + which_cam,
                    "hires": "index.html?" + which_cam,
                    "camera": which_cam,
                    "type": "addon",
                    "title": "Live-Stream"
                }

            content["entries"] = files_images

            # Yesterday
            files_yesterday = {}
            stamps = list(reversed(sorted(files_all.keys())))
            if not backup and not self.config.param["server"]["daily_clean_up"]:
                for stamp in stamps:
                    if "type" in files_all[stamp] and files_all[stamp]["type"] == "image":
                        if "datestamp" not in files_all[stamp]:
                            self.logging.warning("Wrong entry format:" + str(files_all[stamp]))

                        if (int(stamp) >= int(time_now) and time_now != "000000") and "datestamp" in files_all[stamp] and \
                                files_all[stamp]["datestamp"] == date_yesterday:

                            if self.camera[which_cam].image_to_select(timestamp=stamp, file_info=files_all[stamp],
                                                                      check_similarity=check_similarity):
                                files_yesterday[stamp] = files_all[stamp]
                                if "type" not in files_yesterday[stamp]:
                                    files_yesterday[stamp]["type"] = "image"
                                files_yesterday[stamp]["category"] = category + stamp
                                files_yesterday[stamp]["detect"] = self.camera[which_cam].image_differs(
                                    file_info=files_yesterday[stamp])
                                files_yesterday[stamp]["directory"] = "/" + self.config.directories["images"]
                                if "type" in files_yesterday[stamp] and files_yesterday[stamp]["type"] != "data":
                                    count += 1

            if len(files_yesterday) > 0:
                content["entries_yesterday"] = files_yesterday

            # To be deleted
            files_recycle = {}
            if self.admin_allowed():
                for stamp in stamps:
                    if "type" in files_all[stamp] and files_all[stamp]["type"] == "image":
                        if "to_be_deleted" in files_all[stamp] and int(files_all[stamp]["to_be_deleted"]) == 1:
                            if files_all[stamp]["camera"] == which_cam:
                                files_recycle[stamp] = files_all[stamp]
                                if "type" not in files_recycle[stamp]:
                                    files_recycle[stamp]["type"] = "image"
                                files_recycle[stamp]["category"] = category + stamp
                                files_recycle[stamp]["directory"] = "/" + self.config.directories["images"] + \
                                                                    subdirectory
                                if "type" in files_recycle[stamp] and files_recycle[stamp]["type"] != "data":
                                    count += 1

                if len(files_recycle) > 0:
                    content["entries_delete"] = files_recycle

        content["subtitle"] += " (" + self.camera[which_cam].name + ", " + str(count) + " Bilder)"
        content["entries_total"] = len(files_today)
        content["view_count"] = ["all", "star", "detect", "data"]

        if backup:
            if "chart_data" not in content:
                content["chart_data"] = self.create.chart_data(data=files_all.copy())
            content["weather_data"] = self.create.weather_data(data=files_all.copy())
            if "weather_data" not in content:
                pass

        else:
            if "chart_data" not in content:
                content["chart_data"] = self.create.chart_data_new(data_image=files_today.copy(),
                                                                   data_sensor=files_sensor.copy(),
                                                                   data_weather=files_weather.copy(),
                                                                   date=self.config.local_time().strftime("%Y%m%d"))
            if "weather_data" not in content:
                content["weather_data"] = self.create.weather_data_new(data_weather=files_weather.copy(),
                                                                       date=self.config.local_time().strftime("%Y%m%d"))

        return content

    def archive_list(self, camera):
        """
        Return data for list of archive folders (or an empty list if still loading)
        """
        if camera in self.archive_views:
            content = self.archive_views[camera]
        else:
            content = {}
        if self.admin_allowed():
            content["links"] = print_links_json(link_list=("live", "favorit", "today", "today_complete", "videos"), cam=camera)
        else:
            content["links"] = print_links_json(link_list=("live", "favorit", "today", "videos"), cam=camera)
        return content

    def archive_list_create(self):
        """
        Page with backup/archive directory
        """
        count = 0
        dir_size = 0
        dir_size_cam = 0
        dir_size_total = 0
        dir_count_cam = 0
        dir_count_data = 0
        dir_count_delete = 0
        archive_info = {}
        start_time = time.time()

        self.archive_loading = "in progress"
        self.logging.info("Create data for archive view from '" +
                          self.config.db_handler.directory(config="backup")+"' ...")

        main_directory = self.config.db_handler.directory(config="backup")
        self.logging.info("- Get archive directory information (" + self.config.db_handler.db_type + " | " +
                          main_directory + ") ...")

        dir_list = []
        file_list = os.listdir(main_directory)
        for entry in file_list:
            if "." not in entry:
                if os.path.isdir(os.path.join(main_directory, entry)):
                    dir_list.append(entry)
        self.logging.info("- Found " + str(len(dir_list)) + " archive directories: " + str(dir_list))

        # dir_list = [f for f in os.listdir(main_directory) if os.path.isdir(os.path.join(main_directory, f))]
        # dir_list.sort(reverse=True)

        for cam in self.camera:
            content = {
                "active_cam": cam,
                "view": "backup",
                "entries": {},
                "groups": {},
                "max_image_size": {
                    "lowres": [0, 0],
                    "hires": [0, 0]
                }
            }

            dir_total_size = 0
            files_total = 0

            image_title = str(self.config.param["backup"]["preview"])
            # + str(self.camera[cam].param["image_save"]["seconds"][0])
            image_today = self.config.filename_image(image_type="lowres", timestamp=image_title, camera=cam)
            image = os.path.join(self.config.db_handler.directory(config="images"), image_today)

            self.logging.info("- Scan " + str(len(dir_list)) + " directories for " + cam + " ...")
            for directory in dir_list:
                group_name = directory[0:4] + "-" + directory[4:6]
                self.logging.debug("  -> Directory: " + directory + " | " + group_name)

                if "groups" not in content:
                    content["groups"] = {}
                if group_name not in content["groups"]:
                    content["groups"][group_name] = []

                available = False
                config_file = ""
                config_available = False
                if self.config.db_handler.db_type == "couch" or self.config.db_handler.db_type == "both":
                    available = self.config.db_handler.exists(config="backup", date=directory)
                    config_file = self.config.db_handler.file_path(config="backup", date=directory)
                    config_available = os.path.isfile(config_file)
                    if not available or not config_available:
                        self.logging.warning("  -> Check CouchDB: available=" + str(available))
                        self.logging.warning("  -> Check JSON: config_file=" + str(config_available))

                elif self.config.db_handler.db_type == "json":
                    available = self.config.db_handler.exists(config="backup", date=directory)
                    if not available:
                        self.logging.error("  -> Check JSON: config_file=" + str(config_available))

                file_data = {}
                if available:
                    self.logging.debug("  -> read from DB")
                    file_data = self.config.db_handler.read_cache(config="backup", date=directory)

                elif not available and config_available:
                    self.logging.debug("  -> read from file")
                    file_data = self.config.db_handler.json.read(config_file)
                    if file_data != {}:
                        self.logging.debug("  -> write to DB: " + str(file_data.keys()))
                        self.config.db_handler.write(config="backup", date=directory, data=file_data, create=True)
                        available = True
                    else:
                        self.logging.error("  -> got empty data")

                if available:
                    self.logging.debug("  -> Check CONFIG")
                    content["groups"][group_name].append(directory)

                    # check if config file in correct format
                    if "info" not in file_data or "files" not in file_data:
                        if directory not in content["entries"]:
                            content["entries"][directory] = {}
                        content["entries"][directory]["error"] = True
                        self.logging.error("  -> Read JSON: Wrong file format - " + config_file)

                    else:
                        count = 0  # file_data["info"]["count"]
                        first_img = ""
                        dir_size_cam = 0
                        dir_size = 0
                        dir_count_cam = 0
                        dir_count_delete = 0
                        dir_count_data = 0

                        # select preview image
                        if image_title in file_data["files"] and "lowres" in file_data["files"][image_title]:
                            image = os.path.join(directory, file_data["files"][image_title]["lowres"])

                        # or take first image as title image
                        else:
                            for file in list(sorted(file_data["files"].keys())):
                                if "camera" in file_data["files"][file] and file_data["files"][file]["camera"] == cam \
                                        and ("type" not in file_data["files"][file] or
                                             file_data["files"][file]["type"] == "image"):
                                    first_img = file
                                    break
                            if first_img != "" and "lowres" in file_data["files"][first_img]:
                                image = os.path.join(directory, file_data["files"][first_img]["lowres"])

                    if "files" in file_data:
                        for file in file_data["files"]:
                            file_info = file_data["files"][file]
                            if ("datestamp" in file_info and file_info["datestamp"] == directory) or "datestamp" not in file_info:
                                if "type" not in file_info or file_info["type"] == "image":
                                    count += 1
                                else:
                                    dir_count_data += 1

                                if "size" in file_info and "float" in str(type(file_info["size"])):
                                    dir_size += file_info["size"]

                                if ("camera" in file_info and file_info["camera"] == cam) or "camera" not in file_info:
                                    if "size" in file_info and "float" in str(type(file_info["size"])):
                                        dir_size_cam += file_info["size"]
                                    elif "lowres" in file_info:
                                        lowres_file = os.path.join(self.config.db_handler.directory(config="backup"),
                                                                   directory, file_info["lowres"])
                                        if os.path.isfile(lowres_file):
                                            dir_size_cam += os.path.getsize(lowres_file)
                                            self.logging.debug("lowres size: "+str(os.path.getsize(lowres_file)))
                                        if "lowres_size" in file_info:
                                            if file_info["lowres_size"][0] > content["max_image_size"]["lowres"][0]:
                                                content["max_image_size"]["lowres"][0] = file_info["lowres_size"][0]
                                            if file_info["lowres_size"][1] > content["max_image_size"]["lowres"][1]:
                                                content["max_image_size"]["lowres"][1] = file_info["lowres_size"][1]

                                        if "hires" in file_info:
                                            hires_file = os.path.join(self.config.db_handler.directory(config="backup"),
                                                                      directory, file_info["hires"])
                                            if os.path.isfile(hires_file):
                                                dir_size_cam += os.path.getsize(hires_file)
                                                self.logging.debug("hires size: " + str(os.path.getsize(hires_file)))
                                        if "hires_size" in file_info:
                                            if file_info["hires_size"][0] > content["max_image_size"]["hires"][0]:
                                                content["max_image_size"]["hires"][0] = file_info["hires_size"][0]
                                            if file_info["lowres_size"][1] > content["max_image_size"]["hires"][1]:
                                                content["max_image_size"]["hires"][1] = file_info["hires_size"][1]

                                    if "to_be_deleted" in file_info and int(file_info["to_be_deleted"]) == 1:
                                        dir_count_delete += 1

                                    if "type" not in file_info or file_info["type"] == "image":
                                        dir_count_cam += 1

                        dir_size += dir_size_cam
                        dir_size = round(dir_size / 1024 / 1024, 1)
                        dir_size_cam = round(dir_size_cam / 1024 / 1024, 1)
                        dir_total_size += dir_size
                        files_total += count

                        self.logging.info("  -> Archive " + directory + ": " + str(round(dir_total_size, 1)) +
                                          " MB / " + cam + ": " + str(dir_size_cam) + " MB in " + str(count) + " files")

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
                        self.logging.error("  -> Archive: config file available but empty/in wrong format: /backup/" + directory)

                elif available:
                    self.logging.info("  -> Archive available in CouchDB")
                else:
                    self.logging.error("  -> No config file available: /backup/" + directory)

            content["view_count"] = []
            content["subtitle"] = presets.birdhouse_pages["backup"][0] + " (" + self.camera[cam].name + ")"
            content["chart_data"] = self.create.chart_data(content["entries"].copy())
            self.archive_views[cam] = content.copy()

            if self.config.db_handler.db_type == "couch":
                del content["entries"]
                archive_info[cam] = content.copy()

            dir_size_total += dir_total_size

        self.archive_dir_size = dir_size_total
        self.config.db_handler.write("backup_info", "", archive_info)
        self.archive_loading = "done"
        self.logging.info("Create data for archive view done ("+str(round(time.time()-start_time, 1))+"s)")

    def archive_list_update(self):
        """
        Trigger recreation of the archive list
        """
        self.create_archive = True

    def complete_list_today(self, server):
        """
        Page with all pictures of the current day
        """
        self.logging.debug("CompleteListToday: Start - "+self.config.local_time().strftime("%H:%M:%S"))
        self.server = server
        path, which_cam, further_param = self.selected_camera()
        content = {
            "active_cam": which_cam,
            "view": "list_complete",
            "entries": {},
            "groups": {},
            "max_image_size": {
                "lowres": [0, 0],
                "hires": [0, 0]
            }
        }

        count = 0
        param = server.path.split("/")
        if "app-v1" in param:
            del param[1]

        category = "/current/"
        path = self.config.db_handler.directory(config="images")
        files_all = self.config.db_handler.read_cache(config="images")
        data_weather = self.config.db_handler.read_cache(config="weather")
        data_sensor = self.config.db_handler.read_cache(config="sensor")

        self.logging.info("TODAY_COMPLETE: found " + str(len(files_all)) + " entries")

        time_now = self.config.local_time().strftime('%H%M%S')
        date_today = self.config.local_time().strftime("%Y%m%d")
        date_yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y%m%d")

        hours = list(["00", "01", "02", "03", "04", "05", "06", "07", "08", "09",
                      "10", "11", "12", "13", "14", "15", "16", "17", "18", "19",
                      "20", "21", "22", "23"])
        hours.sort(reverse=True)

        # Today
        for hour in hours:
            hour_min = hour + "0000"
            hour_max = str(int(hour) + 1) + "0000"
            files_part = {}
            count_diff = 0
            stamps = list(reversed(sorted(files_all.keys())))
            for stamp in stamps:
                if int(time_now) >= int(stamp) >= int(hour_min) and int(stamp) < int(hour_max):
                    if "datestamp" in files_all[stamp] and files_all[stamp]["datestamp"] == date_today:
                        if "camera" in files_all[stamp] and files_all[stamp]["camera"] == which_cam:
                            threshold = self.camera[which_cam].param["similarity"]["threshold"]
                            if "similarity" in files_all[stamp] and float(files_all[stamp]["similarity"]) < float(threshold):
                                if float(files_all[stamp]["similarity"]) > 0:
                                    count_diff += 1
                            files_part[stamp] = files_all[stamp]
                            if "type" not in files_part[stamp]:
                                files_part[stamp]["type"] = "image"
                            files_part[stamp]["detect"] = self.camera[which_cam].image_differs(
                                file_info=files_part[stamp])
                            files_part[stamp]["category"] = category + stamp
                            files_part[stamp]["directory"] = "/" + self.config.directories["images"]
                            count += 1

                            if "lowres_size" in files_part[stamp]:
                                if files_part[stamp]["lowres_size"][0] > content["max_image_size"]["lowres"][0]:
                                    content["max_image_size"]["lowres"][0] = files_part[stamp]["lowres_size"][0]
                                if files_part[stamp]["lowres_size"][1] > content["max_image_size"]["lowres"][1]:
                                    content["max_image_size"]["lowres"][1] = files_part[stamp]["lowres_size"][1]

                            if "hires_size" in files_part[stamp]:
                                if files_part[stamp]["hires_size"][0] > content["max_image_size"]["hires"][0]:
                                    content["max_image_size"]["hires"][0] = files_part[stamp]["hires_size"][0]
                                if files_part[stamp]["lowres_size"][1] > content["max_image_size"]["hires"][1]:
                                    content["max_image_size"]["hires"][1] = files_all[stamp]["hires_size"][1]

            if len(files_part) > 0:
                content["groups"][hour + ":00"] = []
                for entry in files_part:
                    content["entries"][entry] = files_part[entry]
                    content["groups"][hour + ":00"].append(entry)

        content["view_count"] = ["all", "star", "detect", "recycle", "data"]
        content["subtitle"] = presets.birdhouse_pages["today_complete"][0] + " (" + self.camera[which_cam].name + ", " + str(count) + " Bilder)"
        content["links"] = print_links_json(link_list=("live", "favorit", "today", "videos", "backup"), cam=which_cam)
        # content["chart_data"] = self.create.chart_data(content["entries"].copy(), self.config)
        content["chart_data"] = self.create.chart_data_new(data_image=content["entries"].copy(),
                                                           data_sensor=data_sensor,
                                                           data_weather=data_weather,
                                                           date=self.config.local_time().strftime("%Y%m%d"))
        content["weather_data"] = self.create.weather_data_new(data_weather=data_weather,
                                                               date=self.config.local_time().strftime("%Y%m%d"))

        length = getsizeof(content)/1024
        self.logging.debug("CompleteListToday: End - " + self.config.local_time().strftime("%H:%M:%S") +
                           " (" + str(length) + " kB)")
        return content

    def favorite_list(self, camera):
        """
        Return data for list of favorites from cache
        """
        content = self.favorite_views
        content["active_cam"] = camera

        if self.admin_allowed():
            content["links"] = print_links_json(link_list=("live", "today", "today_complete", "videos", "backup"), cam=camera)
        else:
            content["links"] = print_links_json(link_list=("live", "today", "videos", "backup"), cam=camera)
        return content

    def favorite_list_create(self):
        """
        Page with pictures (and videos) marked as favorites and sorted by date
        """
        start_time = time.time()
        self.logging.info("Create data for favorite view  ...")
        self.favorite_loading = "in Progress"
        content = {
            "active_cam": "none",
            "view": "favorits",
            "entries": {},
            "groups": {}
        }
        favorites = {}

        # videos
        files_videos = {}
        files_video_count = 0
        if self.config.db_handler.exists("videos"):
            files_all = self.config.db_handler.read_cache(config="videos")
            for file in files_all:
                date = file.split("_")[0]
                if "favorit" in files_all[file] and int(files_all[file]["favorit"]) == 1:
                    if date not in files_videos:
                        files_videos[date] = {}
                    files_videos[date][file] = files_all[file]
                    files_video_count += 1
        self.logging.info("  -> VIDEO Favorites: " + str(files_video_count))

        # today
        date_today = self.config.local_time().strftime("%Y%m%d")
        files = self.config.db_handler.read_cache(config="images")
        category = "/current/"
        files_today_count = 0

        for stamp in files:
            stamp = str(stamp)
            if "_" not in stamp and stamp in files and "datestamp" in files[stamp] and \
                    date_today == files[stamp]["datestamp"] and \
                    "favorit" in files[stamp] and int(files[stamp]["favorit"]) == 1:
                new = self.config.local_time().strftime("%Y%m%d") + "_" + stamp
                favorites[new] = files[stamp]
                favorites[new]["source"] = ("images", "")
                favorites[new]["date"] = "Aktuell"
                favorites[new]["time"] = stamp[0:2] + ":" + stamp[2:4] + ":" + stamp[4:6]
                if "type" not in favorites[new]:
                    favorites[new]["type"] = "image"
                favorites[new]["category"] = category + stamp
                favorites[new]["directory"] = "/" + self.config.directories["images"]
                files_today_count += 1

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

        self.logging.info("  -> TODAY Favorites: " + str(files_video_count))

        # other days
        file_other_count = 0
        other_data = self.config.db_handler.read_cache(config="backup")
        dir_list = other_data.keys()
        dir_list = list(reversed(sorted(dir_list)))
        self.logging.info("  -> OTHER Directories: " + str(len(dir_list)))

        # main_directory = self.config.db_handler.directory(config="backup")
        # dir_list = [f for f in os.listdir(main_directory) if os.path.isdir(os.path.join(main_directory, f))]

        video_list = []
        for file_date in files_videos:
            if file_date not in dir_list:
                dir_list.append(file_date)
                video_list.append(file_date)

        dir_list = list(reversed(sorted(dir_list)))

        for directory in dir_list:
            date = ""
            category = "/backup/" + directory + "/"
            favorites[directory] = {}

            if self.config.db_handler.exists(config="backup", date=directory):
                files_data = self.config.db_handler.read_cache(config="backup", date=directory)
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
                                    file_other_count += 1

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

        self.logging.info("  -> OTHER Favorites: " + str(file_other_count))

        content["view_count"] = ["star"]
        content["subtitle"] = presets.birdhouse_pages["favorit"][0]

        self.favorite_views = content
        self.logging.info("Create data for favorite view done ("+str(round(time.time()-start_time, 1))+"s)")
        self.config.db_handler.write("favorites", "", content)
        self.favorite_loading = "done"

    def favorite_list_update(self):
        """
        Trigger recreation of the favorit list
        """
        self.create_favorites = True

    def video_list(self, server):
        """
        Page with all videos
        """
        self.server = server
        path, which_cam, further_param = self.selected_camera()
        content = {"active_cam": which_cam, "view": "list_videos"}
        param = server.path.split("/")
        if "app-v1" in param:
            del param[1]

        directory = self.config.db_handler.directory(config="videos")
        category = "/videos/"  # self.config.directories["videos"]

        files_all = {}
        files_delete = {}
        files_show = {}
        content["entries"] = {}

        if self.config.db_handler.exists("videos"):
            files_all = self.config.db_handler.read_cache(config="videos")
            for file in files_all:
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
        content["subtitle"] = presets.birdhouse_pages["videos"][
            0]  # + " (" + self.camera[which_cam].name +", " + str(len(files_all)) + " Videos)"

        if self.admin_allowed():
            content["links"] = print_links_json(link_list=("live", "favorit", "cam_info", "today", "backup"))
        else:
            content["links"] = print_links_json(link_list=("live", "favorit", "today", "backup"))

        return content

    def camera_list(self, server):
        """
        Page with all videos
        """
        self.server = server
        path, which_cam, further_param = self.selected_camera()
        content = {"active_cam": which_cam, "view": "list_cameras", "entries": {}}
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
        content["subtitle"] = presets.birdhouse_pages["cam_info"][0]
        content["links"] = print_links_json(link_list=("live", "favorit", "today", "videos", "backup"), cam=which_cam)

        return content.copy()

    def detail_view_video(self, server):
        """
        Show details and edit options for a video file
        """
        self.server = server
        path, which_cam, further_param = self.selected_camera()
        content = {"active_cam": which_cam, "view": "detail_video", "entries": {}}
        param = server.path.split("/")
        if "app-v1" in param:
            del param[1]
        count = 0

        if "api" in param:
            video_id = param[4]
        else:
            video_id = param[1]

        config_data = self.config.db_handler.read_cache(config="videos")
        if video_id in config_data and "video_file" in config_data[video_id]:

            data = config_data[video_id]
            content["entries"][video_id] = data
            description = ""

            if self.admin_allowed():
                if self.config.param["server"]["ip4_stream_video"] != "":
                    video_server = self.config.param["server"]["ip4_stream_video"]
                elif self.config.param["server"]["ip4_server"] != "":
                    video_server = self.config.param["server"]["ip4_server"]
                else:
                    video_server = "<!--CURRENT_SERVER-->"
                files = {
                    # "VIDEOFILE": self.camera[which_cam].param["video"]["streaming_server"] + data["video_file"],
                    "VIDEOFILE": "http://"+video_server+":"+str(self.config.param["server"]["port_video"])+"/",
                    "THUMBNAIL": data["thumbnail"],
                    "LENGTH": str(data["length"]),
                    "VIDEOID": video_id,
                    "ACTIVE": which_cam,
                    "JAVASCRIPT": "createShortVideo();"
                }

        content["view_count"] = []
        content["subtitle"] = presets.birdhouse_pages["video_info"][0]
        content["links"] = print_links_json(link_list=("live", "favorit", "today", "videos", "backup"))

        return content
