import os
import time
import logging
import cv2
import threading
from tqdm import tqdm
from datetime import datetime


class BirdhouseArchive(threading.Thread):

    def __init__(self, config, camera, views):
        """
        Initialize new thread and set initial parameters
        """
        threading.Thread.__init__(self)
        logging.info("Starting backup process ...")
        self.config = config
        self.camera = camera
        self.views = views
        self.name = "Backup"
        self.processing = False
        self._running = True

    def run(self):
        """
        start backup in the background
        """
        backup_started = False
        while self._running:
            stamp = self.config.local_time().strftime('%H%M%S')
            if stamp[0:4] == self.config.param["backup"]["time"] and not backup_started:
                logging.info("Starting daily backup ...")
                backup_started = True
                self.backup_files()
                logging.info("OK.")
                self.views.archive_list_create()
                count = 0
                while self._running and count < 60:
                    time.sleep(1)
                    count += 1
            else:
                backup_started = False
            time.sleep(0.5)
        logging.info("Stopped backup process.")

    def stop(self):
        """
        stop running process
        """
        self._running = False

    def create_video_config(self):
        """
        recreate video config file, if not exists
        """
        path = self.config.directory(config="videos")
        logging.info("Create video list for video directory ...")
        logging.debug("Reading files from path: " + path)

        file_list = [f for f in os.listdir(path) if
                     os.path.isfile(os.path.join(path, f)) and ".mp4" in f and not "short" in f]
        file_list.sort(reverse=True)
        files = {}
        for file in file_list:

            logging.info(" - "+file)
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
                "directory": self.camera[param[1]].param["video"]["streaming_server"],
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
        logging.info("Done.")

    def create_image_config(self, date="", recreate=False):
        """
        Initial compare files to create new config file
        """
        time.sleep(1)
        if date == "":
            logging.info("(Re)create image config file for main directory ...")
            path = self.config.directory(config="images")
        else:
            logging.info("(Re)create image config file for  directory "+date+" ...")
            path = self.config.directory(config="backup", date=date)
        if recreate and os.path.isfile(path):
            logging.info("Remove existing image config file ...")
            os.remove(path)
        file_list = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)) and "_big" not in f]
        file_list.sort(reverse=True)
        files = self.create_image_config_analyze(file_list=file_list, init=True, subdir=date)
        logging.info("Done.")
        return files

    def create_image_config_api(self, path):
        """
        Call (re)creation via API and return JSON answer
        """
        logging.debug(path)
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
            logging.warning("Compare Files already processing ...")
            return
        self.processing = True

        if os.path.isfile(self.config.file_path("images")) and subdir == "":
            files = self.config.read_cache(config='images')
        else:
            files = {}
            files = self.create_image_config_get_filelist(file_list=file_list, files=files, subdir=subdir)

            if os.path.isfile(self.config.file_path("sensor")):
                sensor_data = self.config.read_cache(config="sensor")
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
                        filename = os.path.join(self.config.directory(config="images"), subdir, filename_current)
                        image_current = cv2.imread(filename)
                        image_current = cv2.cvtColor(image_current, cv2.COLOR_BGR2GRAY)
                    except Exception as e:
                        logging.error("Could not load image: " + filename + " ... "+str(e))

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
                        logging.debug(" - " + cam + ": " + filename_current + "  " + str(count) + "/" + str(len(files)) +
                                     " - " + str(files_new[key]["similarity"]) + "%  "+sensor_str)

                    filename_last = filename_current
                    image_last = image_current

                    self.config.queue.entry_add(config="images", date=subdir, key=key, entry=files_new[key])

#        if subdir == '':
#            self.config.write("images", files_new)
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
                    file_dir = os.path.join(self.config.directory(config='images'), file)
                    timestamp = datetime.fromtimestamp(os.path.getmtime(file_dir))

                    files[time]["datestamp"] = timestamp.strftime("%Y%m%d")
                    files[time]["date"] = timestamp.strftime("%d.%m.%Y")
                    files[time]["time"] = timestamp.strftime("%H:%M:%S")

                if "sensor" not in files[time]:
                    files[time]["sensor"] = {}

        return files

    def backup_files(self, other_date=""):
        """
       Backup files with threshold to folder with date ./images/YYMMDD/
       """
        if other_date == "":
            backup_date = self.config.local_time().strftime('%Y%m%d')
        else:
            backup_date = other_date

        directory = self.config.directory(config="images", date=backup_date)

        # if the directory but no config file exists for backup directory create a new one
        if os.path.isdir(directory):
            logging.info("Backup files: create a new config file, directory already exists")

            if not os.path.isfile(self.config.file_path(config="backup", date=backup_date)):
                files = self.create_image_config(date=backup_date)
                files_backup = {"files": files, "info": {}}
                files_backup["info"]["count"] = len(files)
                files_backup["info"]["threshold"] = {}
                for cam in self.camera:
                    files_backup["info"]["threshold"][cam] = self.camera[cam].param["similarity"]["threshold"]
                files_backup["info"]["date"] = backup_date[6:8] + "." + backup_date[4:6] + "." + backup_date[0:4]
                files_backup["info"]["size"] = sum(
                    os.path.getsize(os.path.join(directory, f)) for f in os.listdir(directory) if
                    os.path.isfile(os.path.join(directory, f)))
                self.config.write(config="backup", config_data=files_backup, date=backup_date)

        # if no directory exists, create directory, copy files and create a new config file (copy existing information)
        else:
            logging.info("Backup files: copy files and create a new config file (copy existing information)")

            self.config.directory_create(config="images", date=backup_date)
            files = self.config.read_cache(config="images")
            files_backup = {"files": {}, "info": {}}
            file_sensor = self.config.file_path(config="sensor")
            file_sensor_copy = os.path.join(self.config.directory(config="images", date=backup_date), self.config.files["sensor"])
            stamps = list(reversed(sorted(files.keys())))
            dir_source = self.config.directory(config="images")
            count = 0
            count_data = 0
            count_other_date = 0
            backup_size = 0

            if os.path.isfile(file_sensor):
                os.popen("cp "+file_sensor+" "+file_sensor_copy)

            for cam in self.camera:
                for stamp in stamps:
                    # if files are to be archived
                    if files[stamp]["datestamp"] == backup_date and files[stamp]["camera"] == cam:
                        update_new = files[stamp].copy()

                        # if images are to archived
                        if self.camera[cam].image_to_select(timestamp=stamp, file_info=files[stamp]):
                            count += 1
                            file_lowres = self.config.filename_image(image_type="lowres", timestamp=stamp, camera=cam)
                            file_hires = self.config.filename_image(image_type="hires", timestamp=stamp, camera=cam)

                            if "similarity" not in update_new:
                                update_new["similarity"] = 100
                            if "hires" not in update_new:
                                update_new["hires"] = file_hires
                            if "favorit" not in update_new:
                                update_new["favorit"] = 0

                            update_new["type"] = "image"
                            update_new["directory"] = os.path.join(self.config.directories["images"], backup_date)

                            if os.path.isfile(os.path.join(dir_source, file_lowres)):
                                update_new["size"] = (
                                        os.path.getsize(os.path.join(dir_source, file_lowres)) + os.path.getsize(
                                    os.path.join(dir_source, file_hires)))
                                backup_size += update_new["size"]
                                os.popen('cp ' + os.path.join(dir_source, file_lowres) + ' ' + os.path.join(directory,
                                                                                                            file_lowres))
                                os.popen('cp ' + os.path.join(dir_source, file_hires) + ' ' + os.path.join(directory,
                                                                                                           file_hires))

                        # if data are to be archived
                        else:
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

                        files_backup["files"][stamp] = update_new.copy()

                    else:
                        count_other_date += 1

                logging.info(cam + ": " + str(count) + " Image entries (" + str(
                    self.camera[cam].param["similarity"]["threshold"]) + ")")
                logging.info(cam + ": " + str(count_data) + " Data entries")
                logging.info(cam + ": " + str(count_other_date) + " not saved (other date)")

            files_backup["info"]["date"] = backup_date[6:8] + "." + backup_date[4:6] + "." + backup_date[0:4]
            files_backup["info"]["count"] = count
            files_backup["info"]["size"] = backup_size
            files_backup["info"]["threshold"] = {}
            for cam in self.camera:
                files_backup["info"]["threshold"][cam] = self.camera[cam].param["similarity"]["threshold"]

            self.config.write(config="backup", config_data=files_backup, date=directory)

    def delete_marked_files_api(self, path):
        """
        set / unset recycling
        """
        logging.debug(path)
        param = path.split("/")
        response = {"command": ["delete files that are marked as 'to_be_deleted'", param]}

        if "delete_not_used" in param:
            delete_not_used = True
        else:
            delete_not_used = False

        if param[2] == "backup":
            response = self.delete_marked_files_exec(config="images", date=param[3], delete_not_used=delete_not_used)
        elif param[2] == "today":
            response = self.delete_marked_files_exec(config="images", date="", delete_not_used=delete_not_used)
        elif param[2] == "video":
            response = self.delete_marked_files_exec(config="videos", date="", delete_not_used=delete_not_used)
        else:
            response["error"] = "not clear, which files shall be deleted"

        return response

    def delete_marked_files_exec(self, config="images", date="", delete_not_used=False):
        """
        delete files which are marked to be recycled for a specific date + database entry
        """
        response = {}
        file_types = ["lowres", "hires", "video_file", "thumbnail"]
        files_in_config = []
        delete_keys = []

        if config == "images" and date == "":
            files = self.config.read_cache(config='images')
            directory = self.config.directory(config='images')
        elif config == "images":
            config_file = self.config.read_cache(config='backup', date=date)
            directory = self.config.directory(config='backup', date=date)
            files = config_file["files"]
        elif config == "videos":
            files = self.config.read_cache(config='videos')
            directory = self.config.directory(config='videos')
        else:
            response["error"] = "file type not supported"
            return response

        files_in_dir = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f)) and ".json" not in f]
        count = 0
        for key in files:
            if date != "":
                check_date = date[6:8] + "." + date[4:6] + "." + date[0:4]
            else:
                check_date = ""

            if date == "" or ("date" in files[key] and check_date in files[key]["date"]):
                for file_type in file_types:
                    if file_type in files[key]:
                        files_in_config.append(files[key][file_type])

            if "to_be_deleted" in files[key] and int(files[key]["to_be_deleted"]) == 1:
                count += 1
                delete_keys.append(key)

        for key in delete_keys:
            try:
                for file_type in file_types:
                    if file_type in files[key]:
                        if os.path.isfile(os.path.join(directory, files[key][file_type])):
                            os.remove(os.path.join(directory, files[key][file_type]))
                            logging.debug("Delete - "+str(key)+": "+os.path.join(directory, files[key][file_type]))

                self.config.queue.entry_keep_data(config="backup", date=date, key=key)

            except Exception as e:
                logging.error("Error while deleting file '" + key + "' ... " + str(e))
                response["error"] += "delete file '" + key + "': " + str(e) + "\n"

        if delete_not_used:
            for file in files_in_dir:
                if file not in files_in_config:
                    os.remove(os.path.join(directory, file))

        print(str(len(files_in_dir)) + "/" + str(len(files_in_config)))

        response["deleted_count"] = count
        response["deleted_keys"] = delete_keys
        response["files_not_used"] = len(files_in_dir) - len(files_in_config)
        response["files_used"] = len(files_in_config)
        logging.info("Deleted " + str(count) + " marked files in " + directory + ".")
        return response

