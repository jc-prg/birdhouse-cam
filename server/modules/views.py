import os
import time
import threading
from sys import getsizeof
from datetime import datetime, timedelta
import modules.presets as presets
from modules.presets import *
from modules.presets import view_logging
from modules.bh_class import BirdhouseClass


class BirdhouseViewTools(BirdhouseClass):

    def __init__(self, config) -> None:
        BirdhouseClass.__init__(self, class_id="view-arch", config=config)

        self.timeout_living_last = time.time()
        self.timeout_living_signal = 10
        self.progress = {}

        self.logging.info("Connected view tools.")

    def calculate_progress(self, view, number, cam, count, length) -> None:
        """
        show progress information in logging
        """
        if view not in self.progress:
            self.progress[view] = ""

        percentage = round((count / length) * 100, 1)
        self.progress[view] = "#" + str(number) + ": " + str(percentage) + "%"

        if self.timeout_living_last + self.timeout_living_signal < time.time():
            if cam != "":
                self.logging.info("... still calculating " + view + " view - " + cam + " #" + str(number) + ": " +
                                  str(percentage) + "% of " + str(length) + " ...")
            else:
                self.logging.info("... still calculating " + view + " view - #" + str(number) + ": " +
                                  str(percentage) + "% of " + str(length) + " ...")
            self.timeout_living_last = time.time()

    def get_progress(self, view):
        """
        return progress value
        """
        if view in self.progress:
            return self.progress[view]
        else:
            return view

    def get_directories(self, main_directory) -> list[str]:
        """
        grab sub-directories in a directory
        """
        self.logging.debug("Return sub-directories for " + main_directory)
        dir_list = []
        file_list = os.listdir(main_directory)
        for entry in file_list:
            if "." not in entry:
                if os.path.isdir(os.path.join(main_directory, entry)):
                    dir_list.append(entry)
        return dir_list

    def print_links_json(self, link_list, cam="") -> dict:
        """
        create a list of links based on URLs and descriptions defined in preset.py -> for JSON API
        """
        self.logging.debug("Create link list " + str(link_list) + "/" + cam)
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


class BirdhouseViewCharts(BirdhouseClass):

    def __init__(self, config) -> None:
        BirdhouseClass.__init__(self, class_id="view-chart", config=config)
        self.logging.info("Connected chart data creation handler.")

    def chart_data_new(self, data_image, data_sensor=None, data_weather=None, date=None, cameras=None) -> dict:
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

        hours = ["00", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10",
                 "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23"]
        minutes = ["00", "05", "10", "15", "20", "25", "30", "35", "40", "45", "50", "55"]
        chart = {"titles": [], "data": {}}

        activity_dict = {}
        data_activity = {}

        if cameras is None:
            chart["titles"].append("Activity")
            activity_dict["cam1"] = {}
            data_activity["cam1"] = {}
            cameras = ["cam1"]
        else:
            for cam in cameras:
                chart["titles"].append("Activity " + cam.upper())
                data_activity[cam] = {}
                activity_dict[cam] = {}

        self.logging.info("create_chart_data_new: " + datestamp + " / " + date_eu + " / " + date_us +
                          " for cam: " + str(cameras))

        # Calculate image activity
        for cam in cameras:
            for key in data_image:
                if date is not None and "datestamp" in data_image[key] and data_image[key]["datestamp"] != datestamp:
                    continue
                if len(cameras) > 1 and data_image[key]["camera"] != cam:
                    continue
                this_hour = key[0:2]
                this_minute = key[2:4]
                minute_to = str(int(this_minute) + (5 - (int(this_minute) % 5))).zfill(2)
                hour_to = this_hour
                if int(minute_to) > 59:
                    hour_to = str(int(hour_to) + 1).zfill(2)
                if int(hour_to) > 23:
                    hour_to = "00"

                stamp = hour_to + minute_to + "00"
                activity_dict[cam][stamp] = []
                if stamp not in activity_dict:
                    pass
                activity_dict[cam][stamp].append(key)

            # create data structure activity
            for key in activity_dict[cam]:
                activity_sum = 0
                activity_count = 0
                for stamp in activity_dict[cam][key]:
                    if "similarity" in data_image[stamp] and float(data_image[stamp]["similarity"]) > 0:
                        activity_sum += float(data_image[stamp]["similarity"])
                        activity_count += 1
                if activity_count > 0:
                    data_activity[cam][key] = round(100 - (activity_sum / activity_count), 2)

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
                stamp_exists_sensor = False
                stamp_exists_weather = False
                stamp_exists_activity = {}

                # Check if exists and date is correct
                for cam in cameras:
                    if stamp in data_activity[cam]:
                        stamp_exists_activity[cam] = True
                        stamp_exists = True
                    else:
                        stamp_exists_activity[cam] = False

                if stamp in data_sensor_tmp:
                    if date is not None and len(sensor_list) > 0 \
                            and data_sensor_tmp[stamp][sensor_list[0]]["date"] == date_eu:
                        stamp_exists_sensor = True
                        stamp_exists = True
                    elif date is None and len(sensor_list) > 0:
                        stamp_exists_sensor = True
                        stamp_exists = True

                if stamp in data_weather:
                    if date is not None and "date" in data_weather[stamp] and data_weather[stamp]["date"] == date_us:
                        stamp_exists_weather = True
                        stamp_exists = True
                    elif date is None:
                        stamp_exists_weather = True
                        stamp_exists = True

                if stamp_exists:
                    chart["data"][chart_stamp] = []

                # Activity
                for cam in cameras:
                    if stamp_exists_activity[cam]:
                        chart["data"][chart_stamp].append(data_activity[cam][stamp])
                    elif stamp_exists:
                        chart["data"][chart_stamp].append(None)

                # Weather data
                if stamp_exists_weather:
                    for value in weather_data_in_chart:
                        self.logging.debug(" ....: " + value)
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

    def chart_data(self, data) -> dict:
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
            print_key = key[0:2] + ":" + key[2:4]
            if int(print_minute) % weather_data_interval == 0:

                if "camera" in data[key] and data[key]["camera"] not in used_cameras:
                    used_cameras.append(data[key]["camera"])

                if "similarity" in data[key]:
                    if round(float(data[key]["similarity"])) == 0:
                        data[key]["similarity"] = 100
                    chart["data"][print_key] = [100 - float(data[key]["similarity"])]

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

    def weather_data_new(self, data_weather, date=None) -> dict:
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

        weather = {}
        hours = ["00", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10",
                 "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23"]
        sunrise_hour = self.config.weather.get_sunrise()
        sunset_hour = self.config.weather.get_sunset()
        if sunset_hour is not None and sunrise_hour is not None:
            sunset_hour = sunset_hour.split(":")[0]
            sunrise_hour = sunrise_hour.split(":")[0]
        else:
            sunset_hour = 24
            sunrise_hour = 0

        self.logging.debug("... Weather - sunrise=" + str(sunrise_hour) + "; sunset=" + str(sunset_hour))

        for hour in hours:
            if int(sunrise_hour) < int(hour) < int(sunset_hour):
                stamp = hour + "0000"
                if stamp in data_weather:
                    if date is not None and "date" in data_weather[stamp] and data_weather[stamp]["date"] != date_us:
                        continue
                    weather[stamp] = data_weather[stamp]
                    weather[stamp]["time"] = hour + ":00"

        for hour in hours:
            if int(sunrise_hour) < int(hour) < int(sunset_hour):
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

    def weather_data(self, data) -> dict:
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

    def statistic_data(self, data) -> dict:
        """
        create chart format out of statistic data
        ----
        titles - cam1_active, cam1_fps, cam2_active, cam2_fps
        data - {"HHMM": [cam1_active, cam1_fps, cam2_active, cam2_fps], "HHMM": [cam1_active, cam1_fps, cam2_active, cam2_fps], ...}
        """
        self.logging.debug("create_statistic_data")
        chart = {"titles": [], "data": {}}
        main_keys = list(data.keys())
        sub_keys = {"active_streams": "Streams", "stream_framerate": "Framerate"}

        for main_key in main_keys:
            for sub_key in sub_keys:
                chart["titles"].append(main_key + ": " + sub_keys[sub_key])

        for entry_key in data[main_keys[0]]:
            chart["data"][entry_key] = []
            for main_key in main_keys:
                for sub_key in sub_keys:
                    chart["data"][entry_key].append(data[main_key][entry_key][sub_key])

        return chart


class BirdhouseViewFavorite(BirdhouseClass):

    def __init__(self, config, tools) -> None:
        BirdhouseClass.__init__(self, class_id="view-fav", config=config)

        self.tools = tools
        self.views = None
        self.loading = "started"

        self.create = True
        self.create_complete = True
        self.force_reload = False
        self.reload_counter = ""

        self.links_default = ("live", "today", "videos", "backup")
        self.links_admin = ("live", "today", "today_complete", "videos", "backup")

        self.logging.info("Connected archive creation handler.")

    def list(self, param) -> dict:
        """
        Return data for list of favorites from cache
        """
        if not self.views:
            return {}

        camera = param["which_cam"]
        content = self.views
        content["active_cam"] = camera
        content["label"] = ""
        if len(param["parameter"]) >= 3:
            content["label"] = param["parameter"][2]

        if param["admin_allowed"]:
            content["links"] = self.tools.print_links_json(link_list=self.links_admin, cam=camera)
        else:
            content["links"] = self.tools.print_links_json(link_list=self.links_default, cam=camera)

        return content

    def list_update(self, force=False, complete=False) -> None:
        """
        Trigger recreation of the favorit list
        """
        if complete or force:
            self.logging.info("Request update FAVORITE view (complete=" + str(complete) + "; force=" + str(force) +
                              "; count=" + str(self.reload_counter) + ")")
        self.create_complete = complete
        self.create = True
        if force:
            self.force_reload = True

    def list_create(self, complete=False) -> None:
        """
        Page with pictures (and videos) marked as favorites and sorted by date
        """
        start_time = time.time()
        self.logging.info("Create data for favorite view (complete=" + str(complete) + ") ...")
        self.loading = "in progress"

        if self.config.db_handler.exists("favorites", "") and not complete:
            content = self.config.db_handler.read("favorites", "")
        else:
            content = {
                "active_cam": "none",
                "view": "favorites",
                "view_count": ["star"],
                "subtitle": presets.birdhouse_pages["favorit"][0],
                "entries": {},
                "groups": {}
            }

        # check existing directories
        main_directory = self.config.db_handler.directory(config="backup")
        dir_list = self.tools.get_directories(main_directory)
        self.logging.debug(str(dir_list))
        delete_entries = []
        if not complete:
            for stamp in content["entries"]:
                entry = content["entries"][stamp]

                if "_" in stamp:
                    date_stamp = stamp.split("_")[0]
                elif "datestamp" in entry:
                    date_stamp = entry["datestamp"]
                elif "date" in entry and len(entry["date"].split(".")) == 3:
                    day, month, year = entry["date"].split(".")
                    date_stamp = year + month + day
                else:
                    continue

                if date_stamp not in dir_list:
                    delete_entries.append(stamp)

            for stamp in delete_entries:
                del content["entries"][stamp]

        # images from today
        files_images = self._list_create_from_images("", complete)
        if len(files_images) > 0:
            content["groups"]["today"] = []
            for stamp in files_images:
                content["entries"][stamp] = files_images[stamp].copy()
                content["groups"]["today"].append(stamp)

        # videos
        files_videos = self._list_create_from_videos()
        if len(files_videos) > 0:
            for entry in files_videos:
                group = entry[0:4] + "-" + entry[4:6]
                if group not in content["groups"]:
                    content["groups"][group] = []
                content["entries"][entry] = files_videos[entry].copy()
                content["groups"][group].append(entry)

        # archive images
        files_archive = self._list_create_from_archive(complete)
        if len(files_archive) > 0:
            for entry in files_archive:
                group = entry[0:4] + "-" + entry[4:6]
                if group not in content["groups"]:
                    content["groups"][group] = []
                content["entries"][entry] = files_archive[entry].copy()
                content["groups"][group].append(entry)

        self.views = content
        self.create_complete = False
        self.logging.info("Create data for favorite view done (" + str(round(time.time() - start_time, 1)) + "s)")
        self.config.db_handler.write("favorites", "", content, create=True, save_json=True, no_cache=False)
        self.loading = "done"

    def _list_create_from_archive(self, complete=False) -> dict:
        """
        get favorites from archive
        """
        favorites = {}
        main_directory = self.config.db_handler.directory(config="backup")
        dir_list = self.tools.get_directories(main_directory)

        # main_directory = self.config.db_handler.directory(config="backup")
        # dir_list = other_data.keys()
        dir_list = list(reversed(sorted(dir_list)))
        self.logging.info("  -> ARCHIVE Directories: " + str(len(dir_list)))
        self.logging.debug(str(dir_list))

        count_entries = 0
        for archive_directory in dir_list:
            count_entries += 1
            favorites_dir = self._list_create_from_images(archive_directory, complete)
            for key in favorites_dir:
                favorites[key] = favorites_dir[key].copy()
            self.tools.calculate_progress("favorite", "1/1", "", count_entries, len(dir_list))

        return favorites.copy()

    def _list_create_from_images(self, date="", complete=False) -> dict:
        """
        get favorites from current day
        """
        files = {}
        category = "/not_found/"
        files_complete = {}
        fields_not_required = ["similarity", "source", "datestamp"]
        fields_not_required = []
        from_file = False
        save_file = False
        update_mode = " - "

        if date == "":
            today = True
            category = "/current/"
            date = self.config.local_time().strftime("%Y%m%d")
            files = self.config.db_handler.read(config="images")
            files_complete["files"] = files.copy()

        elif self.config.db_handler.exists(config="backup", date=date):
            today = False
            category = "/backup/" + date + "/"
            files_complete = self.config.db_handler.read(config="backup", date=date)
            self.logging.debug("  -> " + category + " ... " + str(files_complete.keys()))

            if "files" in files_complete:
                files = files_complete["files"].copy()
                save_file = True
            else:
                files["error"] = True
        else:
            self.logging.warning("  -> Could not read favorites from " + category + ", no data available.")
            return {}

        if complete:
            from_file = True
            update_mode += " from file (complete)"
        elif self.config.queue.get_status_changed(date=date, change="favorites"):
            from_file = True
            update_mode += " from file (changed="+date+")"
        elif "favorites" not in files_complete:
            from_file = True
            update_mode += " from file (not yet in config-file)"

        if not from_file:
            self.logging.info("  -> Favorites " + category + ": " + str(len(files_complete["favorites"])) + " - keep")
            return files_complete["favorites"]

        if "error" in files or files == {}:
            self.logging.warning("  -> Could not read favorites from " + category + ", wrong data format.")
            return {}

        favorites = {}
        files_today_count = 0
        for stamp in files:
            stamp = str(stamp)
            if "favorit" in files[stamp] and int(files[stamp]["favorit"]) == 1:
                new = date + "_" + stamp
                favorites[new] = {}
                for key in files[stamp]:
                    favorites[new][key] = files[stamp][key]
                # favorites[new] = files[stamp].copy()
                favorites[new]["source"] = ("images", date)
                favorites[new]["time"] = stamp[0:2] + ":" + stamp[2:4] + ":" + stamp[4:6]
                if "type" not in favorites[new]:
                    favorites[new]["type"] = "image"
                favorites[new]["category"] = category + stamp
                favorites[new]["directory"] = "/" + self.config.directories["images"]
                for key in fields_not_required:
                    if key in favorites[new]:
                        del favorites[new][key]
                if not today:
                    favorites[new]["directory"] += "/" + date + "/"
                favorites[new]["directory"] = favorites[new]["directory"].replace("//", "/")
                files_today_count += 1

        if save_file:
            files_complete["favorites"] = favorites.copy()
            self.config.db_handler.write(config="backup", date=date, data=files_complete, create=False,
                                         save_json=True, no_cache=True)

        self.config.queue.set_status_changed(date=date, change="favorites", is_changed=False)
        self.logging.info("  -> Favorites " + category + ": " + str(files_today_count) + "/" + str(len(files)) +
                          " - from file")
        return favorites.copy()

    def _list_create_from_videos(self) -> dict:
        """
        get favorite videos from respective database
        """
        favorites = {}
        files_videos = {}
        files_video_count = 0
        category = "/videos/"

        files_all = self.config.db_handler.read(config="videos")
        if "error" in files_all or files_all == {}:
            self.logging.warning("Could not read favorites from /videos/")
            return favorites

        for file in files_all:
            date = file.split("_")[0]
            if "favorit" in files_all[file] and int(files_all[file]["favorit"]) == 1:
                if date not in files_videos:
                    files_videos[date] = {}
                files_videos[date][file] = files_all[file]
                files_video_count += 1

        for date in files_videos:
            for stamp in files_videos[date]:
                new = date + "_" + stamp
                favorites[new] = files_videos[date][stamp].copy()
                favorites[new]["source"] = ("videos", "")
                favorites[new]["type"] = "video"
                favorites[new]["date"] = date
                favorites[new]["time"] = stamp[0:2] + ":" + stamp[2:4] + ":" + stamp[4:6]
                favorites[new]["category"] = category + date
                favorites[new]["directory"] = "/" + self.config.directories["videos"]

        self.logging.info("  -> VIDEO Favorites: " + str(files_video_count))
        return favorites.copy()

    def request_done(self):
        """
        reset all values that lead to (re)creation of this view
        """
        self.create_complete = False
        self.create = False
        self.force_reload = False


class BirdhouseViewArchive(BirdhouseClass):

    def __init__(self, config, tools, camera) -> None:
        BirdhouseClass.__init__(self, class_id="view-arch", config=config)
        self.tools = tools
        self.camera = camera
        self.views = {}
        self.loading = "started"
        self.dir_size = 0

        self.create = True
        self.create_complete = False
        self.force_reload = False
        self.reload_counter = ""

        # to be validated ....
        self.config_recreate = []
        self.config_recreate_progress = False

        self.links_default = ("live", "today", "videos", "backup")
        self.links_admin = ("live", "favorit", "today", "today_complete", "videos")

        self.logging.info("Connected archive creation handler.")

    def list(self, param) -> dict:
        """
        Return data for list of archive folders (or an empty list if still loading)
        """
        camera = param["which_cam"]
        if camera in self.views:
            content = self.views[camera]
        else:
            content = {}

        content["label"] = ""
        if len(param["parameter"]) >= 3:
            content["label"] = param["parameter"][2]

        if param["admin_allowed"]:
            content["links"] = self.tools.print_links_json(link_list=self.links_admin, cam=camera)
        else:
            content["links"] = self.tools.print_links_json(link_list=self.links_default, cam=camera)
        return content

    def list_update(self, force=False, complete=False) -> None:
        """
        Trigger recreation of the archive list
        """
        if complete or force:
            self.logging.info("Request update ARCHIVE view (complete=" + str(complete) + "; force=" + str(force) +
                              "; count=" + str(self.reload_counter) + ")")
        self.create_complete = complete
        self.create = True
        if force:
            self.force_reload = True

    def list_create(self, complete=False) -> None:
        """
        Page with backup/archive directory
        """
        camera_settings = self.config.param["devices"]["cameras"]
        archive_total_size = 0
        archive_total_count = 0
        start_time = time.time()
        archive_template = {
            "active_cam": "",
            "view": "backup",
            "entries": {},
            "groups": {},
            "view_count": [],
            "max_image_size": {"lowres": [0, 0], "hires": [0, 0]}
        }

        self.loading = "in progress"
        main_directory = self.config.db_handler.directory(config="backup")
        db_type = self.config.db_handler.db_type
        dir_list = self.tools.get_directories(main_directory)

        archive_changed = {}
        archive_info = self.config.db_handler.read("backup_info", "")

        self.logging.info("Create data for archive view from '" + main_directory +
                          "' (complete=" + str(self.create_complete) + ") ...")
        self.logging.info("- Get archive directory information (" + db_type + " | " + main_directory + ") ...")
        self.logging.info("- Found " + str(len(dir_list)) + " archive directories.")
        self.logging.debug("  -> " + str(dir_list))

        # prepare data
        backup_entries = {}
        cam_count = 0
        for cam in self.camera:

            # create new values in archive file if they don't exist
            if cam not in archive_info or archive_info[cam] == {}:
                archive_info[cam] = archive_template.copy()
                archive_info[cam]["active_cam"] = cam

            archive_changed[cam] = archive_template.copy()
            archive_changed[cam]["active_cam"] = cam

            # create list per data (from lists per camera) and check if entries in databases have been changed
            count = 0
            cam_count += 1
            for date in archive_info[cam]["entries"]:
                count += 1
                if date not in backup_entries:
                    backup_entries[date] = {}
                backup_entries[date][cam] = archive_info[cam]["entries"][date].copy()
                if self.config.queue.get_status_changed(date=date, change="archive"):
                    backup_entries[date]["changed"] = True
                    backup_entries[date]["exists"] = True
                if "changed" not in backup_entries[date]:
                    backup_entries[date]["changed"] = False
                if "exists" not in backup_entries[date]:
                    backup_entries[date]["exists"] = False
                self.tools.calculate_progress("archive", str(cam_count)+"/4", cam, count, len(archive_info[cam]["entries"]))

            # check if new directories are available
            count = 0
            for archive_directory in dir_list:
                count += 1
                if ((len(archive_directory) == 8 and archive_directory not in backup_entries)
                        or cam not in backup_entries[archive_directory]):
                    if archive_directory not in backup_entries:
                        backup_entries[archive_directory] = {}
                    if cam not in backup_entries[archive_directory]:
                        backup_entries[archive_directory][cam] = {}
                    backup_entries[archive_directory] = {"changed": True, "exists": False}
                    self.tools.calculate_progress("archive", "2/4", cam, count, len(dir_list))

            # stop if shutdown signal was send
            if self.if_shutdown():
                self.logging.info("Interrupt creating the archive list due to shutdown command ...")
                return

        # update data for those dates where necessary + measure total size
        count_entries = 0
        deleted_dates = []
        for date in backup_entries:

            # check if archive directory still exists
            archive_directory = self.config.db_handler.directory(config="backup", date=date)

            count_entries += 1
            self.tools.calculate_progress("archive", "4/4", "", count_entries, len(backup_entries))

            # if archive directory doesn't exist anymore, remove
            if not os.path.isdir(archive_directory):
                self.logging.warning("Directory '" + archive_directory + "' doesn't exist, remove DB entry.")
                deleted_dates.append(date)

            # if archive directory still exists
            else:
                # check availability of couch db and/or json db
                database_ok = self._list_create_database_ok(date)

                # update for those dates where necessary
                for cam in self.camera:

                    # if directory doesn't exist yet read entries from database of the respective date
                    if ((backup_entries[date]["changed"] and not backup_entries[date]["exists"])
                            or not database_ok or self.create_complete):

                        log_info = ("new [database_ok=" + str(database_ok) + ", complete=" + str(self.create_complete) +
                                    ", exists=" + str(backup_entries[date]["exists"]) +
                                    ", changed=" + str(backup_entries[date]["changed"]) + "]")
                        backup_entries[date][cam] = {
                            "camera": cam,
                            "count": 0,
                            "count_delete": 0,
                            "count_cam": 0,
                            "count_data": 0,
                            "datestamp": date,
                            "date": date[6:8] + "." + date[4:6] + "." + date[0:4],
                            "detection": False,
                            "directory": "images/" + date + "/",
                            "dir_size": 0,
                            "dir_size_cam": 0,
                            "lowres": "",
                            "type": "directory"
                        }

                        # Trigger recreation of config file in date-directory, if config file doesn't exist
                        config_images = self.config.db_handler.read("backup", date)
                        config_images_file = self.config.db_handler.file_path("backup", date)
                        if config_images == {}:
                            start_time = time.time()
                            self.logging.info("     * Start recreation of config file for " + date + " ...")
                            self.config_recreate_progress = True
                            self.config_recreate.append(date)

                            while self.config_recreate_progress or start_time + 20 > time.time():
                                time.sleep(0.2)
                            if self.config_recreate_progress:
                                self.logging.warning("     * Recreation of config file for " + date +
                                                     " takes longer than expected, don't wait longer here.")
                            else:
                                self.logging.info("     * Recreated of config file for " + date + ".")
                        else:
                            self.logging.info("     * DB " + date + " available (" + config_images_file + ")")
                            if "detection" in config_images and len(config_images["detection"]):
                                backup_entries[date][cam]["detection"] = True

                        # Extract data from config file
                        file_data = self._list_create_file_data(date, True)
                        backup_entries[date][cam] = self._list_create_from_database(cam, archive_info[cam],
                                                                                    date, file_data)

                    # if just change re-read entries from database of the respective date
                    elif (backup_entries[date]["changed"] and backup_entries[date]["exists"]) or complete:
                        log_info = "changed"
                        file_data = self._list_create_file_data(date, database_ok)
                        backup_entries[date][cam] = self._list_create_from_database(cam, archive_info[cam],
                                                                                    date, file_data)

                    # else stay with the existing data
                    else:
                        log_info = "keep"
                        pass

                    if cam in backup_entries[date] and "dir_size_cam" in backup_entries[date][cam]:
                        log_info_2 = "    (" + str(backup_entries[date][cam]["dir_size_cam"]).rjust(5) + " MB)"

                    if log_info != "keep" and log_info != "changed":
                        self.logging.info("     * DB " + date + " -> " + log_info)
                    else:
                        log_info_2 = log_info + " " + log_info_2
                    self.logging.info("  -> Archive " + str(count_entries).zfill(4) + ": " +
                                      date + "/" + cam + " ... " + log_info_2)

            # stop if shutdown signal was send
            if self.if_shutdown():
                self.logging.info("Interrupt creating the archive list.")
                return

        # remove unused entries
        for date in deleted_dates:
            del backup_entries[date]

        for cam in archive_changed:
            archive_changed[cam]["entries"] = {}

        # process data to be saved
        for date in backup_entries:
            dir_size_date = 0
            for cam in self.camera:
                if cam in backup_entries[date]:

                    self.logging.debug("........" + str(cam) + "/" + backup_entries[date][cam]["camera"])
                    self.logging.debug("........" + str(backup_entries[date][cam]))

                    backup_entry = backup_entries[date][cam].copy()

                    # copy entries to new dict that will be saved
                    archive_changed[cam]["entries"][date] = backup_entry

                    # calculate total values
                    if "dir_size_cam" in backup_entry and "count_cam" in backup_entry:
                        dir_size_date += backup_entry["dir_size_cam"]
                        archive_total_size += backup_entry["dir_size_cam"]
                        archive_total_count += backup_entry["count_cam"]

                    # create groups
                    backup_group = date[0:4] + "-" + date[4:6]
                    if backup_group not in archive_changed[cam]["groups"]:
                        archive_changed[cam]["groups"][backup_group] = []
                    if date not in archive_changed[cam]["groups"][backup_group]:
                        archive_changed[cam]["groups"][backup_group].append(date)

                    # add additional information
                    archive_changed[cam]["view_count"] = ["all"]
                    archive_changed[cam]["subtitle"] = (presets.birdhouse_pages["backup"][0] + " (" +
                                                        self.camera[cam].name + ")")
                    archive_changed[cam]["chart_data"] = {"data": {}, "titles": ["Activity"], "info": "not implemented"}

                else:
                    archive_changed[cam]["entries"][date] = {}

                self.logging.debug("........" + str(archive_changed[cam]["entries"][date]))
                self.logging.debug("........" + cam + "\n")

            for cam in self.camera:
                if date in archive_changed[cam]["entries"]:
                    archive_changed[cam]["entries"][date]["dir_size"] = dir_size_date

            self.config.queue.set_status_changed(date=date, change="archive", is_changed=False)

            # stop if shutdown signal was send
            if self.if_shutdown():
                self.logging.info("Interrupt creating the archive list.")
                return

        self.logging.debug(":::::::::::" + str(archive_changed))
        self.views = archive_changed.copy()

        # get information what has been changed
        backup_info = self.config.db_handler.read("backup_info", "")
        if "changes" in backup_info:
            changed_values = backup_info["changes"]
        else:
            changed_values = {}
        archive_changed["changes"] = changed_values

        # save data in backup database
        self.dir_size = archive_total_size
        self.config.db_handler.write("backup_info", "", archive_changed)
        self.loading = "done"
        self.create_complete = False

        self.logging.info("  => Total archive size: " + str(round(archive_total_size, 2)) + " MByte in " +
                          str(round(archive_total_count, 2)) + " files and " + str(count_entries) + " directories")
        self.logging.info("     Time required for loading: " + str(round(time.time() - start_time, 1)) + "s")

    def _list_create_preview(self, cam, image_title, archive_directory, file_data):
        """
        select / create preview image for archive (thumbnail for date in archive overview)
        """
        # first favorite as image or ...
        first_img = ""
        first_img_temp = ""
        sorted_file_keys = list(sorted(file_data["files"].keys()))

        if "preview_fav" in self.config.param["backup"] and self.config.param["backup"]["preview_fav"]:
            self.logging.debug(" ......... Preview-FAVORITE: ")
            for file in sorted_file_keys:
                entry = file_data["files"][file]
                if "camera" in entry and entry["camera"] == cam and "favorit" in entry \
                        and int(entry["favorit"]) == 1 and "lowres" in entry:
                    if "type" not in entry or ("type" in entry and entry["type"] == "image"):
                        first_img = file
                        self.logging.debug(" ......... 1=" + first_img)
                        break

            # or take first image with detected image, not full hour
            if first_img == "":
                for file in sorted_file_keys:
                    entry = file_data["files"][file]
                    if "camera" in entry and entry["camera"] == cam and "lowres" in entry \
                            and file[2:4] != "00":
                        if "to_be_deleted" not in entry or int(entry["to_be_deleted"]) != 1:
                            if "type" not in entry or ("type" in entry and entry["type"] == "image"):
                                first_img = file
                                self.logging.debug(" ......... 2=" + first_img)
                                break

            # or take first image with detected image
            if first_img == "":
                for file in sorted_file_keys:
                    entry = file_data["files"][file]
                    if "camera" in entry and entry["camera"] == cam and "lowres" in entry:
                        if "to_be_deleted" not in entry or int(entry["to_be_deleted"]) != 1:
                            if "type" not in entry or ("type" in entry and entry["type"] == "image"):
                                first_img = file
                                self.logging.debug(" ......... 3=" + first_img)
                                break

        # select preview image
        elif "preview_fav" not in self.config.param["backup"] \
                or ("preview_fav" in self.config.param["backup"]
                    and not self.config.param["backup"]["preview_fav"]):
            self.logging.debug(" ......... Preview-TIME=" + image_title[0:4] + ":")

            for file in sorted_file_keys:
                entry = file_data["files"][file]
                if image_title[0:4] == file[0:4] and "camera" in entry and entry["camera"] == cam \
                        and "lowres" in entry:
                    if "to_be_deleted" not in entry or int(entry["to_be_deleted"]) != 1:
                        self.logging.debug(" ......... 4=" + first_img)
                        first_img_temp = file
                        break
            if first_img_temp != "":
                first_img = first_img_temp

        # or take first image as title image
        if first_img == "":
            for file in sorted_file_keys:
                entry = file_data["files"][file]
                if "camera" in entry and entry["camera"] == cam and "lowres" in entry:
                    if "to_be_deleted" not in entry or int(entry["to_be_deleted"]) != 1:
                        self.logging.debug(" ......... 5=" + first_img)
                        first_img = file
                        break

        if first_img in file_data["files"]:
            image_preview = os.path.join(archive_directory, file_data["files"][first_img]["lowres"])
        else:
            image_preview = ""

        return image_preview

    def _list_create_entry(self, cam, content, archive_directory, dir_size, file_data) -> (dict, int):
        """
        create entry per archive directory, measure file sizes
        """
        count = 0
        dir_size_cam = 0
        dir_count_cam = 0
        dir_count_delete = 0
        dir_count_data = 0
        dir_detections = False

        for file in file_data["files"]:
            if self.if_other_prio_process("archive_view"):
                time.sleep(0.1)

            file_info = file_data["files"][file]
            if (("datestamp" in file_info and file_info["datestamp"] == archive_directory)
                    or "datestamp" not in file_info):
                if "type" not in file_info or file_info["type"] == "image":
                    count += 1
                else:
                    dir_count_data += 1

                if "size" in file_info and "lowres" in file_info:
                    dir_size += float(file_info["size"])
                    lowres_file = os.path.join(self.config.db_handler.directory(config="backup"),
                                               archive_directory, file_info["lowres"])
                    if os.path.isfile(lowres_file):
                        dir_size += os.path.getsize(lowres_file)

                if ("camera" in file_info and file_info["camera"] == cam) or "camera" not in file_info:
                    if "size" in file_info and "float" in str(type(file_info["size"])):
                        dir_size_cam += file_info["size"]
                    elif "lowres" in file_info:
                        lowres_file = os.path.join(self.config.db_handler.directory(config="backup"),
                                                   archive_directory, file_info["lowres"])
                        if os.path.isfile(lowres_file):
                            dir_size_cam += os.path.getsize(lowres_file)
                            # self.logging.debug("lowres size: "+str(os.path.getsize(lowres_file)))
                        if "lowres_size" in file_info:
                            if file_info["lowres_size"][0] > content["max_image_size"]["lowres"][0]:
                                content["max_image_size"]["lowres"][0] = file_info["lowres_size"][0]
                            if file_info["lowres_size"][1] > content["max_image_size"]["lowres"][1]:
                                content["max_image_size"]["lowres"][1] = file_info["lowres_size"][1]

                        if "hires" in file_info:
                            hires_file = os.path.join(self.config.db_handler.directory(config="backup"),
                                                      archive_directory, file_info["hires"])
                            if os.path.isfile(hires_file):
                                dir_size_cam += os.path.getsize(hires_file)
                                # self.logging.debug("hires size: " + str(os.path.getsize(hires_file)))
                        if "hires_size" in file_info:
                            if file_info["hires_size"][0] > content["max_image_size"]["hires"][0]:
                                content["max_image_size"]["hires"][0] = file_info["hires_size"][0]
                            if file_info["lowres_size"][1] > content["max_image_size"]["hires"][1]:
                                content["max_image_size"]["hires"][1] = file_info["hires_size"][1]

                    if "to_be_deleted" in file_info and int(file_info["to_be_deleted"]) == 1:
                        dir_count_delete += 1

                    if "type" not in file_info or file_info["type"] == "image":
                        dir_count_cam += 1

        dir_size_cam = round(dir_size_cam / 1024 / 1024, 1)
        dir_size = round(dir_size / 1024 / 1024, 1)

        if "detection_" + cam in file_data["info"] and file_data["info"]["detection_" + cam]:
            dir_detections = True

        content["entries"][archive_directory] = {
            "directory": self.config.directories["backup"] + archive_directory + "/",
            "type": "directory",
            "camera": cam,
            "date": file_data["info"]["date"],
            "datestamp": archive_directory,
            "detection": dir_detections,
            "count": count,
            "count_delete": dir_count_delete,
            "count_cam": dir_count_cam,
            "count_data": dir_count_data,
            "dir_size": 0,
            "dir_size_cam": dir_size_cam,
            "lowres": ""
        }

        return content.copy(), dir_size

    def _list_create_database_ok(self, date) -> bool:
        """
        check availability of couch db and/or json db
        """
        database_ok = False
        database_type = self.config.db_handler.db_type
        database_available = self.config.db_handler.exists(config="backup", date=date)
        self.logging.debug("  -> Check CouchDB: available=" + str(database_available))
        config_available = os.path.isfile(self.config.db_handler.file_path(config="backup", date=date))
        self.logging.debug("  -> Check JSON: config_file=" + str(config_available))
        if database_type == "couch" and database_available:
            database_ok = True
        elif database_type == "both" and database_available or config_available:
            database_ok = True
        elif database_type == "json" and config_available:
            database_ok = True
        if not database_ok:
            self.logging.warning("        -> DB Check for '" + date + "': JSON=" + str(config_available) + ", COUCH=" +
                                 str(database_available) + ", DB-TYPE=" + database_type)
        return database_ok

    def _list_create_file_data(self, archive_directory, database_ok) -> dict:
        """
        get data from existing database or return empty value
        """
        file_data = {}
        config_available = os.path.isfile(self.config.db_handler.file_path(config="backup", date=archive_directory))

        if database_ok:
            self.logging.debug("  -> read from DB")
            file_data = self.config.db_handler.read(config="backup", date=archive_directory)

        elif not database_ok and config_available:
            self.logging.debug("  -> read from file")
            # file_data = self.config.db_handler.json.read(config_file)
            file_data = self.config.db_handler.json.read(config="backup", date=archive_directory)
            if file_data != {}:
                self.logging.debug("  -> write to DB: " + str(file_data.keys()))
                file_data["info"]["changed"] = False
                self.config.db_handler.write(config="backup", date=archive_directory, data=file_data, create=True,
                                             no_cache=True)
            else:
                self.logging.error("  -> got empty data")

        # check if data format is complete
        if "info" not in file_data:
            file_data["info"] = {}
            file_data["info"]["date"] = archive_directory[6:8] + "." + archive_directory[4:6] + "." + archive_directory[
                                                                                                      0:4]
        if "files" not in file_data:
            file_data["files"] = {}
        if "chart_data" not in file_data:
            file_data["chart_data"] = {}
        if "weather_data" not in file_data:
            file_data["weather_data"] = {}

        return file_data.copy()

    def _list_create_from_database(self, cam, content, archive_directory, file_data) -> dict:
        """
        create archive entry from files
        """
        dir_size = 0
        image_preview = self._list_create_preview(cam=cam, image_title=str(self.config.param["backup"]["preview"]),
                                                  archive_directory=archive_directory, file_data=file_data)
        image_preview = os.path.join(str(self.config.directories["backup"]), str(image_preview))
        image_file = image_preview.replace(archive_directory + "/", "")
        image_file = image_file.replace(self.config.directories["backup"], "")

        content, dir_size = self._list_create_entry(cam=cam, content=content.copy(), archive_directory=archive_directory,
                                                    dir_size=dir_size, file_data=file_data)
        content["entries"][archive_directory]["lowres"] = image_file

        files_count = content["entries"][archive_directory]["count_cam"]
        files_size = content["entries"][archive_directory]["dir_size_cam"]

        self.logging.info("     * DB " + archive_directory + "/" + cam + " entries: " +
                          str(files_size) + " MB in " + str(files_count) + " files")

        return content["entries"][archive_directory].copy()

    def request_done(self):
        """
        reset all values that lead to (re)creation of this view
        """
        self.create_complete = False
        self.create = False
        self.force_reload = False


class BirdhouseViewObjects(BirdhouseClass):

    def __init__(self, config, tools, camera) -> None:
        BirdhouseClass.__init__(self, class_id="view-obj", config=config)

        self.tools = tools
        self.views = None
        self.loading = "started"
        self.camera = camera
        self.cameras = list(camera.keys())
        self.detect_active = birdhouse_env["detection_active"]

        self.create = True
        self.create_complete = False
        self.force_reload = False
        self.reload_counter = ""

        self.links_default = ("live", "today", "videos", "backup")
        self.links_admin = ("live", "today", "today_complete", "videos", "backup")

        self.relevant_keys = ["camera", "date", "datestamp", "directory", "hires", "hires_detect",
                              "hires_size", "lowres", "lowres_size", "size", "time", "type"]

        self.logging.info("Connected object view creation handler.")

    def list(self, param) -> dict:
        """
        Return data for list of favorites from cache
        """
        if not self.views or not self.detect_active:
            return {}

        camera = param["which_cam"]
        content = self.views
        content["active_cam"] = camera

        if param["admin_allowed"]:
            content["links"] = self.tools.print_links_json(link_list=self.links_admin, cam=camera)
        else:
            content["links"] = self.tools.print_links_json(link_list=self.links_default, cam=camera)

        return content

    def list_update(self, force=False, complete=False) -> None:
        """
        Trigger recreation of the favorit list
        """
        if not self.detect_active:
            self.logging.debug("Request update OBJECT view but object detection is off")
        else:
            if complete or force:
                self.logging.info("Request update OBJECT view (complete=" + str(complete) + "; force=" + str(force) +
                                  "; count=" + str(self.reload_counter) + ")")
            self.create_complete = complete
            self.create = True
            if force:
                self.force_reload = True

    def list_create(self, complete=False) -> None:
        """
        collect or create data for objects view ...
        """
        if not self.detect_active:
            return

        start_time = time.time()
        self.logging.info("Create data for object detection view (complete=" + str(complete) + ") ...")
        self.loading = "in progress"

        if self.config.db_handler.exists("objects", ""):
            content = self.config.db_handler.read("objects", "")
        else:
            content = {
                "active_cam": "none",
                "view": "objects",
                "view_count": ["star"],
                "subtitle": presets.birdhouse_pages["object"][0],
                "entries": {},
                "groups": {},
                "changes": True
            }

        # in progress: get detection information from archive files
        files_archive = self._list_create_from_archive(complete)
        content["entries"] = files_archive

        self.views = content
        self.create_complete = False
        self.logging.info("Create data for object detection view done (" + str(round(time.time() - start_time, 1)) + "s)")
        self.config.db_handler.write("objects", "", content, create=True, save_json=True, no_cache=False)
        self.loading = "done"

    def _list_get_detection_for_label(self, label, entry, favorite) -> dict:
        """
        get entry, if label inside, and check if its a favorite
        """
        new_entry = {}
        label_exists = False
        coordinates = []

        if favorite and not ("favorit" in entry and int(entry["favorit"]) == 1):
            return {}
        if "type" not in entry or entry["type"] != "image" or "hires" not in entry:
            return {}

        if "directory" in entry:
            img_directory = entry["directory"]
            if img_directory[0:1] == "/":
                img_directory = entry["directory"][1:]
        elif "datestamp" in entry:
            img_directory = "images/" + entry["datestamp"] +"/"
        else:
            return {}
        if not os.path.exists(os.path.join(birdhouse_main_directories["data"], img_directory, entry["hires"])):
            return {}

        if "detections" in entry:
            for detect in entry["detections"]:
                if detect["label"] == label:
                    label_exists = True
                    coordinates = detect["coordinates"]
                    break

        if label_exists:
            for key in self.relevant_keys:
                new_entry[key] = entry[key]
            new_entry["coordinates"] = coordinates
            new_entry["type"] = "label"

        return new_entry

    def _list_create_from_archive(self, complete):
        """
        get information from archive files and return ...
        """
        view_entries = {}
        main_directory = self.config.db_handler.directory(config="backup")
        dir_list = self.tools.get_directories(main_directory)
        dir_list = list(reversed(sorted(dir_list)))

        self.logging.info("  -> ARCHIVE Directories -> Object detection: " +
                          str(len(dir_list)) + " / " + str(self.cameras))
        self.logging.debug(str(dir_list))

        count = 0
        for date in dir_list:

            count += 1
            category = "/objects/" + date + "/"

            if self.config.db_handler.exists(config="backup", date=date):

                archive_entries = self.config.db_handler.read(config="backup", date=date)
                changed = self.config.queue.get_status_changed(date, "objects")
                if changed or complete:
                    if changed:
                        self.logging.info("  * Objects in " + date + " have changed, start update ...")
                    else:
                        self.logging.info("  * Complete update for " + date + " requested ...")
                    changed_detections = self.camera[self.cameras[0]].object.summarize_detections(archive_entries["files"])
                    archive_entries["detection"] = changed_detections
                    self.config.db_handler.write(config="backup", date=date, data=archive_entries)
                    self.config.queue.set_status_changed(date, "objects", False)

                if "detection" in archive_entries:

                    archive_detection_labels = []
                    archive_detect = archive_entries["detection"]

                    # Initial round: identify thumbnails
                    for label in archive_detect:

                        if label not in view_entries:

                            view_entry = {}
                            view_thumbnail = ""

                            for archive_stamp in archive_entries["files"]:
                                archive_entry = archive_entries["files"][archive_stamp]
                                view_entry = self._list_get_detection_for_label(label, archive_entry, True)
                                view_thumbnail = "favorite"
                                if view_entry != {}:
                                    break

                            if view_entry == {}:
                                for archive_stamp in archive_entries["files"]:
                                    archive_entry = archive_entries["files"][archive_stamp]
                                    view_entry = self._list_get_detection_for_label(label, archive_entry, False)
                                    view_thumbnail = "default"
                                    if view_entry != {}:
                                        break

                            if view_entry != {}:
                                view_entries[label] = view_entry
                                view_entries[label]["detections"] = {
                                    "thumbnail": view_thumbnail,
                                    "favorite": 0,
                                    "favorite_dates": [],
                                    "default": 0,
                                    "default_dates": {},
                                    "total": 0
                                }

                    # second round, count detections
                    for label in archive_detect:

                        if "detection" in archive_entries and label in archive_entries["detection"]:
                            detection = archive_entries["detection"][label]
                            if len(detection["favorite"]) > 0:
                                view_entries[label]["detections"]["favorite"] += len(detection["favorite"])
                                view_entries[label]["detections"]["favorite_dates"].append(date)
                                view_entries[label]["detections"]["total"] += len(detection["favorite"])

                            for camera in self.cameras:
                                if camera not in view_entries[label]["detections"]["default_dates"]:
                                    view_entries[label]["detections"]["default_dates"][camera] = []
                                if camera in detection["default"] and len(detection["default"][camera]) > 0:
                                    view_entries[label]["detections"]["default"] += len(detection["default"][camera])
                                    view_entries[label]["detections"]["default_dates"][camera].append(date)
                                    view_entries[label]["detections"]["total"] += len(detection["favorite"])

                            if label not in archive_detection_labels:
                                archive_detection_labels.append(label)

                    self.logging.info("  -> Read objects from " + category + ": " + str(archive_detection_labels))

                else:
                    self.logging.debug("  -> No objects available in " + category + ".")
                    continue

            else:
                self.logging.warning("  -> Could not read objects from " + category + ", no data available.")
                continue

            self.tools.calculate_progress("object", "1/1", "", count, len(dir_list))

        for label in view_entries:
            view_entries[label] = self._list_create_specific_thumbnails(label, view_entries[label])

        return view_entries

    def _list_create_specific_thumbnails(self, label, entry):
        """
        create a thumbnail from the detected object
        """
        detect_position = []
        if entry["directory"][0:1] == "/":
            entry["directory"] = entry["directory"][1:]
        hires_path = os.path.join(birdhouse_main_directories["data"], entry["directory"], entry["hires"])
        lowres_file = "image_" + label + "_lowres.jpg"
        lowres_path = os.path.join(birdhouse_main_directories["data"], entry["directory"], lowres_file)

        if "coordinates" in entry:
            detect_position = entry["coordinates"]

        if detect_position and os.path.exists(hires_path):

            raw = self.camera[self.cameras[0]].image.read(hires_path)
            raw_crop, crop_area = self.camera[self.cameras[0]].image.crop_raw(raw, crop_area=detect_position, crop_type="relative")
            self.camera[self.cameras[0]].image.write(lowres_path, raw_crop)
            entry["lowres"] = lowres_file

            self.logging.debug("Created thumbnail from " + str(hires_path) + ": size=" +
                               str(raw.shape) + "; crop_area=" + str(crop_area))

        elif not os.path.exists(hires_path):
            self.logging.error("Could not find hires file: " + str(hires_path) + " - " + birdhouse_main_directories["data"])

        return entry

    def request_done(self):
        """
        reset all values that lead to (re)creation of this view
        """
        self.create_complete = False
        self.create = False
        self.force_reload = False


class BirdhouseViews(threading.Thread, BirdhouseClass):

    def __init__(self, camera, config):
        """
        Initialize new thread and set initial parameters
        """
        threading.Thread.__init__(self)
        BirdhouseClass.__init__(self, class_id="views", config=config)
        self.thread_set_priority(3)

        self.active_cams = None
        self.camera = camera
        self.which_cam = ""
        self.force_reload = False

        self.today_dir_size = 0  # not implemented yet

        self.timeout_living_last = time.time()
        self.timeout_living_signal = 20

        self.create_archive = True
        self.create_archive_complete = False

        self.tools = BirdhouseViewTools(config)
        self.create = BirdhouseViewCharts(config)
        self.archive = BirdhouseViewArchive(config, self.tools, self.camera)
        self.favorite = BirdhouseViewFavorite(config, self.tools)
        self.object = BirdhouseViewObjects(config, self.tools, self.camera)

    def run(self):
        """
        Do nothing at the moment
        """
        count_rebuild = 60 * 5  # rebuild when triggerd by relevant events already - max once every 5 minutes
        count = count_rebuild + 1

        self.logging.info("Starting HTML views and REST API for GET ...")
        while self._running:

            if self.favorite.force_reload or self.archive.force_reload or self.object.force_reload:
                self.force_reload = True

            # if favorites to be read again (from time to time and depending on user activity)
            if self.favorite.create and (count > count_rebuild or self.force_reload):
                time.sleep(1)
                if not self.if_shutdown():
                    self.favorite.list_create(self.favorite.create_complete)
                    self.favorite.request_done()

            # if archive to be read again (from time to time and depending on user activity)
            if self.archive.create and (count > count_rebuild or self.force_reload):
                time.sleep(1)
                if not self.if_shutdown():
                    self.archive.list_create(self.archive.create_complete)
                    self.archive.request_done()

            # if archive to be read again (from time to time and depending on user activity)
            if self.object.create and (count > count_rebuild or self.force_reload):
                time.sleep(1)
                if not self.if_shutdown():
                    self.object.list_create(self.object.create_complete)
                    self.object.request_done()

            if self.force_reload:
                self.force_reload = False

            if count > count_rebuild:
                count = 0

            if self.config.user_activity():
                count += 1
                self.favorite.reload_counter = str(count)+"/"+str(count_rebuild)
                self.archive.reload_counter = str(count)+"/"+str(count_rebuild)
                self.object.reload_counter = str(count)+"/"+str(count_rebuild)

            self.thread_control()
            self.thread_wait()

        self.logging.info("Stopped HTML views and REST API for GET.")

    def index_view(self, param) -> dict:
        """
        Index page with live-streaming pictures
        """
        self.logging.debug("Create data for Index View.")
        which_cam = param["which_cam"]
        content = {
            "active_cam": which_cam,
            "view": "index"
        }
        if param["admin_allowed"]:
            content["links"] = self.tools.print_links_json(link_list=("favorit", "today", "backup", "cam_info"))
        else:
            content["links"] = self.tools.print_links_json(link_list=("favorit", "today", "backup"))

        return content

    def list(self, param) -> dict:
        """
        Page with pictures (and videos) of a single day
        """
        path = param["path"]
        which_cam = param["which_cam"]
        further_param = param["parameter"]
        date_backup = ""
        if len(further_param) > 0:
            date_backup = param["parameter"][0]

        time_now = self.config.local_time().strftime('%H%M%S')
        check_similarity = True
        backup = False
        category = ""
        subdirectory = ""
        files_today = {}
        files_images = {}
        files_weather = None
        files_sensor = None

        content = {
            "active_cam": which_cam,
            "active_date": date_backup,
            "label": "",
            "view": "list",
            "entries": {},
            "entries_delete": {},
            "entries_yesterday": {},
            "day_back": "",
            "day_forward": "",
            "days_available": [],
            "links": {},
            "subtitle": "",
            "max_image_size": {
                "lowres": [0, 0],
                "hires": [0, 0]
            }
        }
        if len(param["parameter"]) >= 3:
            content["label"] = param["parameter"][2]

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
            content["links"] = self.tools.print_links_json(link_list=("live", "today", "backup", "favorit"), cam=which_cam)

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
            if param["admin_allowed"]:
                content["links"] = self.tools.print_links_json(
                    link_list=("live", "favorit", "today_complete", "videos", "backup"), cam=which_cam)
            else:
                content["links"] = self.tools.print_links_json(link_list=("live", "favorit", "videos", "backup"), cam=which_cam)

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
                if "time" not in files_all[stamp]:
                    files_all[stamp]["time"] = stamp[0:2] + ":" + stamp[2:4] + ":" + stamp[4:6]

                if ((int(stamp) < int(time_now) or time_now == "000000")
                        and files_all[stamp]["datestamp"] == date_today) or backup:

                    show_img = self.camera[which_cam].image_to_select(timestamp=stamp,
                                                                      file_info=files_all[stamp].copy(),
                                                                      check_similarity=check_similarity)
                    if show_img:
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

                        if "type" in files_today[stamp] and files_today[stamp]["type"] == "image":
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
            if not backup and not birdhouse_env["database_cleanup"]:
                for stamp in stamps:
                    if "type" in files_all[stamp] and files_all[stamp]["type"] == "image":
                        if "datestamp" not in files_all[stamp]:
                            self.logging.warning("Wrong entry format [2]:" + str(files_all[stamp]))

                        if (int(stamp) >= int(time_now) and time_now != "000000") and "datestamp" in files_all[
                            stamp] and \
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
            if param["admin_allowed"]:
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

        # add chart and weather data
        if backup:
            if "chart_data" not in content:
                content["chart_data"] = self.create.chart_data(data=files_all.copy())
            if "weather_data" not in content:
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

        # add navigation information for archive (next day, last day)
        if content["entries_total"] > 0:
            if which_cam in self.archive.views and self.archive.views[which_cam] != {} and date_backup != "":

                archived_days = []
                for key in self.archive.views[which_cam]["entries"]:
                    if self.archive.views[which_cam]["entries"][key]["count_cam"] > 0:
                        archived_days.append(key)

                if date_backup in archived_days:
                    if len(archived_days) > 0:
                        archived_days = sorted(archived_days, reverse=True)
                    content["days_available"] = archived_days
                    position_date_backup = archived_days.index(date_backup)
                    if position_date_backup >= 0:
                        if position_date_backup > 0:
                            content["day_forward"] = archived_days[position_date_backup - 1]
                        if position_date_backup < len(archived_days) - 1:
                            content["day_back"] = archived_days[position_date_backup + 1]

            if date_backup != "":
                content["archive_exists"] = {}
                for camera in self.archive.views:
                    if (date_backup in self.archive.views[camera]["entries"]
                            and self.archive.views[camera]["entries"][date_backup]["count_cam"] > 0):
                        content["archive_exists"][camera] = True
                    else:
                        content["archive_exists"][camera] = False

        return content

    def archive_list(self, param) -> dict:
        return self.archive.list(param)

    def camera_list(self, param) -> dict:
        """
        Return data for page with all cameras
        """
        which_cam = param["which_cam"]
        content = {"active_cam": which_cam, "view": "list_cameras", "entries": {}}

        for cam in self.camera:
            content["entries"][cam] = self.camera[cam].param
            content["entries"][cam]["video"]["stream"] = "/stream.mjpg?" + cam
            content["entries"][cam]["video"]["stream_detect"] = "/detection/stream.mjpg?" + cam
            content["entries"][cam]["device"] = "camera"
            content["entries"][cam]["type"] = self.camera[cam].type
            content["entries"][cam]["active"] = self.camera[cam].active

        content["view_count"] = []
        content["subtitle"] = presets.birdhouse_pages["cam_info"][0]
        content["links"] = self.tools.print_links_json(link_list=("live", "favorit", "today", "videos", "backup"), cam=which_cam)

        return content.copy()

    def complete_list_today(self, param) -> dict:
        """
        Page with all pictures of the current day
        """
        self.logging.debug("CompleteListToday: Start - " + self.config.local_time().strftime("%H:%M:%S"))
        which_cam = param["which_cam"]

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
        category = "/current/"
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
                            if "similarity" in files_all[stamp] and float(files_all[stamp]["similarity"]) < float(
                                    threshold):
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
        content["subtitle"] = presets.birdhouse_pages["today_complete"][0] + " (" + self.camera[
            which_cam].name + ", " + str(count) + " Bilder)"
        content["links"] = self.tools.print_links_json(link_list=("live", "favorit", "today", "videos", "backup"),
                                                       cam=which_cam)
        content["chart_data"] = self.create.chart_data_new(data_image=content["entries"].copy(),
                                                           data_sensor=data_sensor,
                                                           data_weather=data_weather,
                                                           date=self.config.local_time().strftime("%Y%m%d"))
        content["weather_data"] = self.create.weather_data_new(data_weather=data_weather,
                                                               date=self.config.local_time().strftime("%Y%m%d"))

        length = getsizeof(content) / 1024
        self.logging.debug("CompleteListToday: End - " + self.config.local_time().strftime("%H:%M:%S") +
                           " (" + str(length) + " kB)")
        return content

    def favorite_list(self, param) -> dict:
        return self.favorite.list(param)

    def video_list(self, param) -> dict:
        """
        Return data for page with all videos
        """
        which_cam = param["which_cam"]
        content = {"active_cam": which_cam, "view": "list_videos"}

        files_delete = {}
        files_show = {}
        content["entries"] = {}

        if self.config.db_handler.exists("videos"):
            files_all = self.config.db_handler.read_cache(config="videos")
            for file in files_all:
                files_all[file]["directory"] = "http://" + birdhouse_env["server_audio"]  ### need for action
                files_all[file]["directory"] += ":" + str(birdhouse_env["port_video"]) + "/"
                files_all[file]["type"] = "video"
                files_all[file]["path"] = self.config.directories["videos"]
                files_all[file]["category"] = "/videos/" + file
                if "to_be_deleted" in files_all[file] and int(files_all[file]["to_be_deleted"]) == 1:
                    files_delete[file] = files_all[file]
                else:
                    files_show[file] = files_all[file]

            if len(files_show) > 0:
                content["entries"] = files_show
            if len(files_delete) > 0 and param["admin_allowed"]:
                content["entries_delete"] = files_delete

        content["view_count"] = ["all", "star", "detect", "recycle"]
        content["subtitle"] = presets.birdhouse_pages["videos"][0]

        if param["admin_allowed"]:
            content["links"] = self.tools.print_links_json(link_list=("live", "favorit", "cam_info", "today", "backup"))
        else:
            content["links"] = self.tools.print_links_json(link_list=("live", "favorit", "today", "backup"))

        return content

    def detail_view_video(self, param) -> dict:
        """
        Show details and edit options for a video file
        """
        which_cam = param["which_cam"]
        video_id = param["parameter"][0]

        content = {"active_cam": which_cam, "view": "detail_video", "entries": {}}
        config_data = self.config.db_handler.read_cache(config="videos")

        if video_id in config_data and "video_file" in config_data[video_id]:
            data = config_data[video_id]
            content["entries"][video_id] = data
            description = ""

            if param["admin_allowed"]:
                if self.config.param["server"]["ip4_stream_video"] != "":
                    video_server = self.config.param["server"]["ip4_stream_video"]
                elif self.config.param["server"]["ip4_address"] != "":
                    video_server = self.config.param["server"]["ip4_address"]
                else:
                    video_server = "<!--CURRENT_SERVER-->"
                files = {
                    "VIDEOFILE": "http://" + video_server + ":" + str(self.config.param["server"]["port_video"]) + "/",
                    "THUMBNAIL": data["thumbnail"],
                    "LENGTH": str(data["length"]),
                    "VIDEOID": video_id,
                    "ACTIVE": which_cam,
                    "JAVASCRIPT": "createShortVideo();"
                }

        content["view_count"] = []
        content["subtitle"] = presets.birdhouse_pages["video_info"][0]
        content["links"] = self.tools.print_links_json(link_list=("live", "favorit", "today", "videos", "backup"))

        return content
