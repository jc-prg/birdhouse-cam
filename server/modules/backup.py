import os
import time
import logging
import cv2
import threading
from tqdm import tqdm
from datetime import datetime
from modules.presets import *


class BirdhouseArchive(threading.Thread):

    def __init__(self, config, camera, views):
        """
        Initialize new thread and set initial parameters
        """
        threading.Thread.__init__(self)

        self.logging = logging.getLogger("backup")
        self.logging.setLevel(birdhouse_loglevel)
        self.logging.addHandler(birdhouse_loghandler)
        self.logging.info("Starting backup handler ...")

        self._running = True
        self.config = config
        self.camera = camera
        self.views = views
        self.name = "Backup"
        self.processing = False
        self.archive_data = False
        self.backup_start = False
        self.backup_running = False

    def run(self):
        """
        start backup in the background
        """
        backup_started = False
        while self._running:
            if self.config.shut_down:
                self.stop()
            stamp = self.config.local_time().strftime('%H%M%S')
            if (stamp[0:4] == self.config.param["backup"]["time"] or self.backup_start) and not backup_started:
                backup_started = True
                self.backup_start = False
                if self.backup_start:
                    self.logging.info("Starting forced backup ...")
                else:
                    self.logging.info("Starting daily backup ...")
                self.backup_files()
                self.views.archive_list_update()
                self.views.favorite_list_update()
                count = 0
                while self._running and count < 60:
                    time.sleep(1)
                    count += 1
                self.logging.info("Backup DONE.")
            else:
                backup_started = False
            time.sleep(0.5)
        self.logging.info("Stopped backup process.")

    def stop(self):
        """
        stop running process
        """
        self._running = False

    def start_backup(self):
        """
        start backup
        """
        self.backup_start = True

    def backup_files(self, other_date=""):
        """
        Backup files with threshold to folder with date ./images/YYMMDD/
        """
        self.backup_running = True
        if other_date == "":
            backup_date = self.config.local_time().strftime('%Y%m%d')
        else:
            backup_date = other_date

        directory = self.config.db_handler.directory(config="images", date=backup_date)
        data_weather = self.config.db_handler.read(config="weather")
        data_sensor = self.config.db_handler.read(config="sensor")

        # if the directory but no config file exists for backup directory create a new one
        if os.path.isdir(directory):
            self.logging.info("Backup files: create a new config file, directory already exists")

            if not os.path.isfile(self.config.db_handler.file_path(config="backup", date=backup_date)):
                files = self.create_image_config(date=backup_date)
                files_backup = {
                    "files": files,
                    "info": {},
                    "chart_data": self.views.create.chart_data_new(data_image=files,
                                                                   data_sensor=data_sensor,
                                                                   data_weather=data_weather,
                                                                   date=backup_date),
                    "weather_data": self.views.create.weather_data_new(data_weather=data_weather)
                }
                files_backup["info"]["count"] = len(files)
                files_backup["info"]["threshold"] = {}
                for cam in self.camera:
                    files_backup["info"]["threshold"][cam] = self.camera[cam].param["similarity"]["threshold"]
                files_backup["info"]["date"] = backup_date[6:8] + "." + backup_date[4:6] + "." + backup_date[0:4]
#                files_backup["info"]["size"] = sum(
#                    os.path.getsize(os.path.join(directory, f)) for f in os.listdir(directory) if
#                    os.path.isfile(os.path.join(directory, f)))
                files_backup["info"]["size"] = sum(
                    os.path.getsize(os.path.join(directory, f)) for f in os.listdir(directory) if
                    f.endswith(".jpeg") or f.endswith(".jpg") or f.endswith(".json"))
                self.config.db_handler.write(config="backup", date=backup_date, data=files_backup, create=True)

        # if no directory exists, create directory, copy files and create a new config file (copy existing information)
        else:
            self.logging.info("Backup files: copy files and create a new config file (copy existing information)")

            self.config.db_handler.directory_create(config="images", date=backup_date)
            files = self.config.db_handler.read_cache(config="images")
            files_backup = {"files": {}, "chart_data": {}, "info": {}}

            file_sensor = self.config.db_handler.file_path(config="sensor")
            file_sensor_copy = os.path.join(self.config.db_handler.directory(config="images", date=backup_date),
                                            self.config.files["sensor"])
            file_weather = self.config.db_handler.file_path(config="weather")
            file_weather_copy = os.path.join(self.config.db_handler.directory(config="weather", date=backup_date),
                                             self.config.files["weather"])

            stamps = list(reversed(sorted(files.keys())))
            dir_source = self.config.db_handler.directory(config="images")
            count = 0
            count_data = 0
            count_other_date = 0
            backup_size = 0

            if os.path.isfile(file_sensor):
                os.popen("cp "+file_sensor+" "+file_sensor_copy)
            if os.path.isfile(file_weather):
                os.popen("cp "+file_weather+" "+file_weather_copy)

            for cam in self.camera:
                for stamp in stamps:
                    save_entry = False

                    # if files are to be archived
                    if "datestamp" not in files[stamp]:
                        self.logging.warning("Wrong entry format:" + str(files[stamp]))

                    if "_" not in stamp and stamp in files and "datestamp" in files[stamp] and \
                            files[stamp]["datestamp"] == backup_date and files[stamp]["camera"] == cam:

                        # create copy of entry (to modify without damage in original data)
                        update_new = files[stamp].copy()

                        # if images are to archived
                        if self.camera[cam].image_to_select(timestamp=stamp, file_info=files[stamp].copy()):

                            count += 1
                            file_lowres = self.config.filename_image(image_type="lowres", timestamp=stamp, camera=cam)
                            file_hires = self.config.filename_image(image_type="hires", timestamp=stamp, camera=cam)

                            if "similarity" not in update_new:
                                update_new["similarity"] = 100
                            if "hires" not in update_new:
                                update_new["hires"] = file_hires
                            if "favorit" not in update_new:
                                update_new["favorit"] = 0
                            if "type" not in update_new:
                                update_new["type"] = "image"

                            update_new["directory"] = os.path.join(self.config.directories["images"], backup_date)

                            if os.path.isfile(os.path.join(dir_source, file_lowres)) and \
                                    os.path.isfile(os.path.join(dir_source, file_hires)):

                                update_new["size"] = (os.path.getsize(os.path.join(dir_source, file_lowres)) +
                                                      os.path.getsize(os.path.join(dir_source, file_hires)))
                                backup_size += update_new["size"]

                                os.popen('cp ' + os.path.join(dir_source, file_lowres) + ' ' +
                                         os.path.join(directory, file_lowres))
                                os.popen('cp ' + os.path.join(dir_source, file_hires) + ' ' +
                                         os.path.join(directory, file_hires))

                                save_entry = True

                        # if data are to be archived
                        elif self.archive_data:
                            count_data += 1
                            update_new["type"] = "data"

                            if "hires" in update_new:
                                del update_new["hires"]
                            if "lowres" in update_new:
                                del update_new["lowres"]
                            if "directory" in update_new:
                                del update_new["directory"]
                            if "compare" in update_new:
                                del update_new["compare"]
                            if "favorit" in update_new:
                                del update_new["favorit"]
                            if "to_be_deleted" in update_new:
                                del update_new["to_be_deleted"]

                            save_entry = True

                        # remove weather and sensor data
                        if "weather" in update_new:
                            del update_new["weather"]
                        if "sensor" in update_new:
                            del update_new["sensor"]

                        if save_entry:
                            files_backup["files"][stamp] = update_new.copy()

                    else:
                        count_other_date += 1

                self.logging.info(cam + ": " + str(count) + " Image entries (" +
                                  str(self.camera[cam].param["similarity"]["threshold"]) + ")")
                self.logging.info(cam + ": " + str(count_data) + " Data entries")
                self.logging.info(cam + ": " + str(count_other_date) + " not saved (other date)")

            # files_backup["chart_data"] = self.views.create.chart_data(data=files_backup["files"], config=self.config)
            files_backup["chart_data"] = self.views.create.chart_data_new(data_image=files_backup["files"],
                                                                          data_sensor=data_sensor,
                                                                          data_weather=data_weather,
                                                                          date=self.config.local_time().strftime(
                                                                              "%Y%m%d"))
            files_backup["weather_data"] = self.views.create.weather_data_new(data_weather=data_weather,
                                                                              date=self.config.local_time().strftime(
                                                                                  "%Y%m%d"))

            files_backup["info"]["date"] = backup_date[6:8] + "." + backup_date[4:6] + "." + backup_date[0:4]
            files_backup["info"]["count"] = count
            files_backup["info"]["size"] = backup_size
            files_backup["info"]["threshold"] = {}
            for cam in self.camera:
                files_backup["info"]["threshold"][cam] = self.camera[cam].param["similarity"]["threshold"]

            self.config.db_handler.write(config="backup", date=directory, data=files_backup, create=True)

        self.backup_running = False

    def create_video_config(self):
        """
        recreate video config file, if not exists
        """
        path = self.config.db_handler.directory(config="videos")
        self.logging.info("Create video list for video directory ...")
        self.logging.debug("Reading files from path: " + path)
        file_list = [f for f in os.listdir(path) if f.endswith(".mp4") and "short" not in f and
                     os.path.isfile(os.path.join(path, f))]
        file_list.sort(reverse=True)
        files = {}
        for file in file_list:

            self.logging.info(" - "+file)
            file_name = file.split(".")
            param = file_name[0].split("_")  # video_cam2_20210428_175551*
            fid = param[2] + "_" + param[3]
            date = param[2][6:8] + "." + param[2][4:6] + "." + param[2][0:4] + " "
            date += param[3][0:2] + ":" + param[3][2:4] + ":" + param[3][4:6]
            file_short = ""
            file_short_length = 0

            # Get Infos from video file
            # https://docs.opencv.org/2.4/modules/highgui/doc/reading_and_writing_images_and_video.html#videocapture-get
            # -------------------------

            cap = cv2.VideoCapture(os.path.join(path, file))
            frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            length = float(frames) / fps
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            file_name_short = param[0] + "_" + param[1] + "_" + param[2] + "_" + param[3] + "_short.mp4"
            if os.path.isfile(os.path.join(path, file_name_short)):
                file_short = file_name_short
                cap = cv2.VideoCapture(os.path.join(path, file_short))
                file_short_length = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)

            streaming_server = self.config.param["server"]["ip4_stream_video"]
            files[fid] = {
                "date_end": fid,
                "stamp_end": 0,
                "stamp_start": 0,
                "start": 0,
                "start_stamp": 0,
                "camera": param[1],
                "camera_name": self.camera[param[1]].name,
                "category": "/videos/" + param[2] + "_" + param[3],
                "date": date,
                "date_start": param[2] + "_" + param[3],
                "directory": streaming_server,
                "image_size": [width, height],
                "image_count": frames,
                "framerate": fps,
                "length": length,
                "path": self.config.directories["videos"],
                "status": "finished",
                "lowres": file_name[0] + "_thumb.jpeg",
                "thumbnail": file_name[0] + "_thumb.jpeg",
                "type": "video",
                "video_file": file,
                "video_file_short": file_short,
                "video_file_short_length": file_short_length,
            }
            self.config.queue.entry_add(config="videos", date="", key=fid, entry=files[fid])
        self.logging.info("Done.")

    def create_image_config(self, date="", recreate=False):
        """
        Initial compare files to create new config file
        """
        time.sleep(1)
        if date == "":
            self.logging.info("(Re)create image config file for main directory ...")
            path = self.config.db_handler.directory(config="images")
        else:
            self.logging.info("(Re)create image config file for  directory "+date+" ...")
            path = self.config.db_handler.directory(config="backup", date=date)
        if recreate and os.path.isfile(path):
            self.logging.info("Remove existing image config file ...")
            os.remove(path)

        # file_list = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)) and "_big" not in f]
        # file_list = [f for f in os.listdir(path) if "_big" not in f and os.path.isfile(os.path.join(path, f))]
        file_list = [f for f in os.listdir(path) if "_big" not in f and (f.endswith(".jpg") or f.endswith("jpeg"))]

        file_list.sort(reverse=True)
        files = self.create_image_config_analyze(file_list=file_list, init=True, subdir=date)
        self.logging.info("Done.")
        return files

    def create_image_config_api(self, path):
        """
        Call (re)creation via API and return JSON answer
        """
        self.logging.debug(path)
        param = path.split("/")
        response = {"command": ["recreate main image config file", param]}

        self.create_image_config(date="", recreate=True)
        return response

    def create_image_config_analyze(self, file_list, init=False, subdir=""):
        """
        Compare image files and write to config file (incl. sensor data if exist)
        """
        if self.processing:
            # this part potentially can be removed again
            self.logging.warning("Compare Files already processing ...")
            return
        self.processing = True

        if os.path.isfile(self.config.db_handler.file_path("images")) and subdir == "":
            files = self.config.db_handler.read_cache(config='images')
        else:
            files = {}
            files = self.create_image_config_get_filelist(file_list=file_list, files=files, subdir=subdir)

            if os.path.isfile(self.config.db_handler.file_path("sensor")):
                sensor_data = self.config.db_handler.read_cache(config="sensor")
                for key in files:
                    if key in sensor_data:
                        if "date" in sensor_data[key]:
                            files[key]["sensor"]["sensor1"] = sensor_data[key]
                        else:
                            files[key]["sensor"] = sensor_data[key]
                            if "activity" in files[key]["sensor"]:
                                del files[key]["sensor"]["activity"]
                            if "date" in files[key]["sensor"]:
                                del files[key]["sensor"]["date"]

        count = 0
        files_new = files.copy()
        files_new_cam = {}
        files_keys = list(files_new.keys())

        for cam in self.config.param["devices"]["cameras"]:
            for key in files_keys:
                if key in files_new and files_new[key]["camera"] == cam:
                    if cam not in files_new_cam:
                        files_new_cam[cam] = {}
                    files_new_cam[cam][key] = files_new[key]

        for cam in self.config.param["devices"]["cameras"]:
            filename_last = ""
            image_current = ""
            image_last = ""
            if cam not in files_new_cam:
                continue
            files_keys = list(files_new_cam[cam].keys())
            keys_count = len(files_keys)

            for i in tqdm(range(0, keys_count), desc="Reloading images "+cam+" ..."):
                key = files_keys[i]
                if key in files_new and files_new[key]["camera"] == cam:
                    filename_current = files_new[key]["lowres"]
                    try:
                        filename = os.path.join(self.config.db_handler.directory(config="images"),
                                                subdir, filename_current)
                        image_current = cv2.imread(filename)
                        image_current = cv2.cvtColor(image_current, cv2.COLOR_BGR2GRAY)
                    except Exception as e:
                        self.logging.error("Could not load image: " + filename + " ... "+str(e))

                    if len(filename_last) > 0:
                        detection_area = self.camera[cam].param["similarity"]["detection_area"]
                        score = self.camera[cam].image.compare_raw(image_current, image_last, detection_area)
                        files_new[key]["compare"] = (filename_current, filename_last)
                        files_new[key]["similarity"] = score
                        count += 1
                    else:
                        files_new[key]["compare"] = filename_current
                        files_new[key]["similarity"] = 0

                    if init:
                        sensor_str = ""
                        if "sensor" in files_new[key]:
                            sensor_str = str(files_new[key]["sensor"])
                        self.logging.debug(" - " + cam + ": " + filename_current + "  " + str(count) + "/" + str(len(files)) +
                                     " - " + str(files_new[key]["similarity"]) + "%  "+sensor_str)

                    filename_last = filename_current
                    image_last = image_current

                    self.config.queue.entry_add(config="images", date=subdir, key=key, entry=files_new[key])

#        if subdir == '':
#            self.config.db_handler.write("images", "", files_new)
        self.processing = False
        return files_new

    def create_image_config_get_filelist(self, file_list, files, subdir=""):
        """
        get image date from file
        """
        for file in file_list:
            if ".jpg" in file:

                analyze = self.config.filename_image_get_param(filename=file)
                if "error" in analyze:
                    continue

                which_cam = analyze["cam"]
                time = analyze["stamp"]
                files[time] = {}
                files[time]["camera"] = which_cam

                if "cam" in file:
                    files[time]["lowres"] = self.config.filename_image(image_type="lowres", timestamp=time, camera=which_cam)
                    files[time]["hires"] = self.config.filename_image(image_type="hires", timestamp=time, camera=which_cam)
                else:
                    files[time]["lowres"] = self.config.filename_image(image_type="lowres", timestamp=time)
                    files[time]["hires"] = self.config.filename_image(image_type="hires", timestamp=time)

                if subdir == "":
                    file_dir = os.path.join(self.config.db_handler.directory(config='images'), file)
                    timestamp = datetime.fromtimestamp(os.path.getmtime(file_dir))

                    files[time]["datestamp"] = timestamp.strftime("%Y%m%d")
                    files[time]["date"] = timestamp.strftime("%d.%m.%Y")
                    files[time]["time"] = timestamp.strftime("%H:%M:%S")

                if "sensor" not in files[time]:
                    files[time]["sensor"] = {}

        return files

    def delete_marked_files_api(self, path):
        """
        set / unset recycling
        """
        self.logging.debug(path)
        date = ""
        config = ""
        param = path.split("/")
        response = {"command": ["delete files that are marked as 'to_be_deleted'", param]}

        if "delete_not_used" in param:
            delete_not_used = True
        else:
            delete_not_used = False

        if param[2] == "backup":
            self.logging.info("Delete marked files: BACKUP ("+path+")")
            date = param[3]
            config = "images"
        elif param[2] == "today":
            self.logging.info("Delete marked files: TODAY ("+path+")")
            date = ""
            config = "images"
        elif param[2] == "video":
            self.logging.info("Delete marked files: VIDEO ("+path+")")
            date = ""
            config = "videos"
        else:
            self.logging.error("Delete marked files: Not clear what to be deleted ("+path+")")
            response["error"] = "not clear, which files shall be deleted"

        if "error" not in response:
            response = self.delete_marked_files_exec(config=config, date=date, delete_not_used=delete_not_used)
            self.config.queue.add_to_status_queue(config=config, date=date, key="end",
                                                  change_status="DELETE_RANGE_END", status=0)
        return response

    def delete_marked_files_exec(self, config="images", date="", delete_not_used=False):
        """
        delete files which are marked to be recycled for a specific date + database entry
        """
        response = {}
        file_types = ["lowres", "hires", "video_file", "thumbnail"]
        files_in_config = []
        delete_keys = []

        # get data from DB
        if config == "images" and date == "":
            files = self.config.db_handler.read_cache(config='images')
            directory = self.config.db_handler.directory(config='images')
        elif config == "images":
            config_file = self.config.db_handler.read_cache(config='backup', date=date)
            directory = self.config.db_handler.directory(config='backup', date=date)
            files = config_file["files"]
            config = "backup"
        elif config == "videos":
            files = self.config.db_handler.read_cache(config='videos')
            directory = self.config.db_handler.directory(config='videos')
        else:
            response["error"] = "file type not supported"
            return response

        # prepare date_stamp
        if date != "":
            check_date = date[6:8] + "." + date[4:6] + "." + date[0:4]
        else:
            check_date = ""

        self.logging.info(" - Prepare DELETE: Start to read data from " + directory)
        start_time = time.time()
        files_in_dir = [f for f in os.listdir(directory) if f.endswith(".jpg") or f.endswith(".jpeg")]
        self.logging.info(" - Prepare DELETE: Read " + str(len(files_in_dir)) + " files (" +
                          str(time.time() - start_time) + "s)")

        for key in files:
            # remove data only entries
            check = False
            if "type" in files[key] and files[key]["type"] != "data":
                check = True
            elif "type" not in files[key]:
                check = True
            elif "to_be_deleted" in files[key] and int(files[key]["to_be_deleted"]) == 1:
                check = True

            # collect stamps where potentially files exist
            if check:
                if date == "" or ("date" in files[key] and check_date in files[key]["date"]):
                    for file_type in file_types:
                        if file_type in files[key]:
                            files_in_config.append(files[key][file_type])

                if "to_be_deleted" in files[key] and int(files[key]["to_be_deleted"]) == 1:
                    delete_keys.append(key)

        self.logging.info(" - Prepare DELETE " + config + ": total_entries="+str(len(files)) + "; " +
                          "total_file_entries=" + str(len(files_in_config)) + "; " +
                          "to_delete=" + str(len(delete_keys)) + "; ")

        # delete identified files if exist (videos and backup)
        count_del_file = 0
        count_del_entry = 0
        for key in delete_keys:
            try:
                if config == "backup" or config == "videos" or config == "images":
                    for file_type in file_types:
                        if file_type in files[key]:
                            if os.path.isfile(os.path.join(directory, files[key][file_type])):
                                os.remove(os.path.join(directory, files[key][file_type]))
                                count_del_file += 1
                                self.logging.debug("Delete - "+str(key)+": "+os.path.join(directory, files[key][file_type]))

                if config == "backup" or config == "images":
                    self.config.queue.entry_keep_data(config=config, date=date, key=key)
                    count_del_entry += 1

                elif config == "videos":
                    self.config.queue.entry_delete(config=config, date=date, key=key)
                    count_del_entry += 1

            except Exception as e:
                self.logging.error(" - Error while deleting file '" + key + "' ... " + str(e))
                response["error"] += "delete file '" + key + "': " + str(e) + "\n"

        self.logging.info(" - Perform DELETE " + config + ": files="+str(count_del_file) + "; " +
                          "entries=" + str(count_del_entry) + "; ")

        count_del_file = 0
        # delete unused files
        if delete_not_used:
            for file in files_in_dir:
                if file not in files_in_config:
                    os.remove(os.path.join(directory, file))
            self.logging.info(" - Perform DELETE 'unused': files="+str(count_del_file) + "; ")

        self.logging.debug(str(len(files_in_dir)) + "/" + str(len(files_in_config)))

        response["deleted_count"] = count_del_entry
        response["deleted_keys"] = delete_keys
        response["files_not_used"] = len(files_in_dir) - len(files_in_config)
        response["files_used"] = len(files_in_config)

        self.logging.info(" -> Deleted " + str(count_del_entry) + " marked files in " + directory + ".")
        return response

