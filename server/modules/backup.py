import os
import time
import shutil
import cv2
import threading
from tqdm import tqdm
from datetime import datetime
from modules.presets import *
from modules.bh_class import *
from modules.bh_database import BirdhouseTEXT
from modules.image import BirdhouseImageSupport


class BirdhouseArchiveDownloads(threading.Thread, BirdhouseClass):
    """
    create tar gz archives incl. YOLOv5 files to be downloaded
    """

    def __init__(self, config):
        """
        thread to create tar archives from archived data and return download link

        Args:
            config (modules.config.BirdhouseConfig): reference to main config handler
        """
        threading.Thread.__init__(self)
        BirdhouseClass.__init__(self, class_id="bu-dwnld", config=config)

        self.downloads = {}
        self.download_keep_time = 10 * 60
        self.img_support = BirdhouseImageSupport("", config)
        self.text = BirdhouseTEXT()

    def run(self):
        """
        Control thread to create and delete downloads
        """
        self.logging.info("Starting backup download handler ...")
        while self._running:

            downloads_in_queue = list(self.downloads.keys())
            for download_id in downloads_in_queue:
                if not self.downloads[download_id]["created"]:
                    self.create(download_id)
                elif self.downloads[download_id]["time"] + self.download_keep_time < time.time():
                    self.delete(download_id)

            self.thread_control()
            self.thread_wait()

        self.logging.info("Stopped backup download handler.")

    def stop(self):
        """
        stop if thread (set self._running = False)
        """
        self.logging.debug("STOP SIGNAL SEND FROM SOMEWHERE ...")
        self._running = False
        self._processing = False
        self.delete_all_downloads()

    def add2queue(self, param, file_list=None):
        """
        add download to queue

        Args:
            param (dict): parameters from API request
            file_list (list): optional, list of files - entry format YYYYMMDD_HHMMSS
        """
        if file_list is None:
            file_list = []
        if len(param["parameter"]) == 0:
            param["parameter"].append("")
        stamp = str(time.time())
        self.downloads[stamp] = {
            "camera": param["which_cam"],
            "date": param["parameter"][0],
            "entry_list": file_list,
            "package": "default",
            "time": time.time(),
            "created": False,
            "file_path": "",
            "download_path": "... in progress ...",
            "request_session": param["session_id"]
        }
        # self.add2queue_test(stamp)

    def waiting(self, param):
        """
        return downloads waiting for a specific session id

        Args:
            param (dict): parameters from API request (not used yet)
        """
        downloads = {}
        for download_id in self.downloads:
            # if self.downloads[download_id]["request_session"] == param["session_id"]:
            download_info = self.downloads[download_id]
            downloads[download_info["date"]] = download_info["download_path"]
        return downloads

    def create(self, download_id):
        """
        start download preparation: create a zip package to be downloaded

        Args:
            download_id (str): download id to identify download
        """
        camera = self.downloads[download_id]["camera"]
        date = self.downloads[download_id]["date"]
        entry_list = self.downloads[download_id]["entry_list"]
        package = self.downloads[download_id]["package"]
        self.logging.info("Create download: " + camera + " / " + date + " / " + package)

        # archive files of a day
        if len(entry_list) == 0:
            time_string = "[0-9][0-9][0-9][0-9][0-9][0-9]"
            archive_path = str(os.path.join(birdhouse_main_directories["data"], birdhouse_directories["backup"]))
            archive_files = {
                "images": self.img_support.filename(image_type="hires", timestamp=time_string, camera=camera),
                "config": "*.json",
                "yolov5": "yolov5/*.txt"
            }
            archive_zip_file = "birdhouse-archive_" + date + "_" + camera + ".tar.gz"
            archive_zip_path = str(os.path.join(birdhouse_main_directories["download"], archive_zip_file))
            archive_zip_download = os.path.join("downloads", archive_zip_file)

            self.create_YOLOv5(download_id)

            if os.path.exists(archive_zip_path):
                os.remove(archive_zip_path)

            for key in archive_files:
                self.create_tar_gz(archive_path, date, archive_files[key], archive_zip_path)

        # archive files from a list (format <cam_id>_<date:YYYYMMDD>_<time:HHMMSS>)
        else:
            archive_path = str(os.path.join(birdhouse_main_directories["data"], birdhouse_directories["backup"]))
            archive_zip_file = "birdhouse-archive_list_"+self.config.local_time().strftime('%Y%m%d-%H%M%S')+".tar.gz"
            archive_zip_path = str(os.path.join(birdhouse_main_directories["download"], archive_zip_file))
            archive_zip_download = os.path.join("downloads", archive_zip_file)

            archive_files = {}
            archive_entries = {}

            for entry in entry_list:
                camera, datestamp, timestamp = entry.split("_")
                if datestamp not in archive_entries:
                    archive_entries[datestamp] = {}
                if camera not in archive_entries[datestamp]:
                    archive_entries[datestamp][camera] = []
                archive_entries[datestamp][camera].append(timestamp)

            self.logging.info(str(archive_entries))

            self.create_YOLOv5(download_id, archive_entries)

            for datestamp in archive_entries:
                if datestamp not in archive_files:
                    archive_files[datestamp] = {}
                archive_files[datestamp] = {
                    "config": "*.json",
                    "yolov5": "yolov5/*.txt"
                }
                for camera in archive_entries[datestamp]:
                    for timestamp in archive_entries[datestamp][camera]:
                        archive_key = "image_"+timestamp+"_"+camera
                        archive_files[datestamp][archive_key] = self.img_support.filename(image_type="hires",
                                                                                          timestamp=timestamp,
                                                                                          camera=camera)
            for datestamp in archive_files:
                for key in archive_files[datestamp]:
                    self.create_tar_gz(archive_path, datestamp, archive_files[datestamp][key], archive_zip_path)

        self.downloads[download_id]["created"] = True
        self.downloads[download_id]["file_path"] = archive_zip_path
        self.downloads[download_id]["download_path"] = archive_zip_download

    def create_tar_gz(self, archive_path, archive_date, archive_files, archive_destination_path):
        """
        Create tar archive or add files ...

        Args:
            archive_path (str): path to archive files
            archive_date (str): date (sub-path) to archive files
            archive_files (str): filenames to be archived
            archive_destination_path (str): path to destination file
        """
        filename = archive_files.split("/")[-1]
        archive_path_plus = str(os.path.join(archive_path, archive_date, "/".join(archive_files.split("/")[:-1])))
        command = "find " + archive_path_plus + " -name " + filename
        command += " -exec tar "
        command += " --transform='s,data/images/" + archive_date + "/yolov5/,labels_,' "
        command += " --transform='s,data/images/" + archive_date + "/," + archive_date + "/,' "
        command += " --transform='s,_big_,_" + archive_date + "_,' "
        command += " -rvf " + str(archive_destination_path) + " {} \;"
        self.logging.info("Create download for archive " + archive_date + " - " + archive_files + " ... ")
        self.logging.info(command)
        os.system(command)
        self.logging.info("-> done.")

    def create_YOLOv5(self, download_id, archive_entries=None):
        """
        create YOLOv5 files

        Args:
            download_id (str): download id to identify download
            archive_entries (dict): prepared list of files to be downloaded
        """
        self.logging.debug("Start YOLOv5 creation for download ID " + str(download_id) +
                           " (" + str(archive_entries) + ") ...")

        camera = self.downloads[download_id]["camera"]
        date = self.downloads[download_id]["date"]
        entry_list = self.downloads[download_id]["entry_list"]
        package = self.downloads[download_id]["package"]

        # if requested for a single date only
        if len(entry_list) == 0:
            self.logging.debug("* for single date: " + str(date) + "/" + camera)
            archive_path = str(os.path.join(birdhouse_main_directories["data"], birdhouse_directories["backup"], date))
            archive_path_info = str(os.path.join(archive_path, "yolov5"))
            entries = self.config.db_handler.read("backup", date)

            if ("info" in entries and "detection_" + camera in entries["info"]
                    and "detected" in entries["info"]["detection_"+camera]
                    and entries["info"]["detection_"+camera]["detected"]):
                if "labels" in entries["info"]["detection_"+camera]:
                    labels = entries["info"]["detection_"+camera]["labels"]
                    model = entries["info"]["detection_" + camera]["model"]
                    model = model.replace(".pt", "")
                    self.logging.debug("* model: " + str(model) + " / labels: " + str(labels))
                else:
                    labels = {}
                    model = "no-model"
                    self.logging.debug("* no model defined")
            else:
                self.logging.debug("* no detection found")
                return

            if os.path.exists(archive_path_info):
                shutil.rmtree(archive_path_info)
            os.makedirs(archive_path_info)
            archive_path_info_model = os.path.join(archive_path_info, model)
            os.makedirs(archive_path_info_model)

            classes = {}
            for stamp in entries["files"]:
                classes = self.create_YOLOv5_file(entries["files"][stamp], archive_path_info_model, classes)

            self.create_YOLOv5_classes(classes, labels, archive_path_info_model)

        # if requested for a list of files
        else:
            model_saved = []
            self.logging.debug("* for " + str(len(archive_entries)) + " dates ...")
            for datestamp in archive_entries:
                archive_path = str(os.path.join(birdhouse_main_directories["data"],
                                                birdhouse_directories["backup"], datestamp))
                archive_path_info = str(os.path.join(archive_path, "yolov5"))
                entries = self.config.db_handler.read("backup", datestamp)

                for camera in archive_entries[datestamp]:
                    if ("info" in entries and "detection_" + camera in entries["info"]
                            and "detected" in entries["info"]["detection_"+camera]
                            and entries["info"]["detection_"+camera]["detected"]):
                        if "labels" in entries["info"]["detection_"+camera]:
                            labels = entries["info"]["detection_"+camera]["labels"]
                            model = entries["info"]["detection_"+camera]["model"]
                            model = model.replace(".pt", "")
                            self.logging.debug("* model: " + str(model) + " / labels: " + str(labels))
                        else:
                            labels = {}
                            model = "no-model"
                            self.logging.debug("* no model defined")
                    else:
                        self.logging.debug("* no detection found")
                        continue

                    if os.path.exists(archive_path_info):
                        shutil.rmtree(archive_path_info)
                    os.makedirs(archive_path_info)
                    archive_path_info_model = os.path.join(archive_path_info, model)
                    os.makedirs(archive_path_info_model)

                    classes = {}
                    for timestamp in archive_entries[datestamp][camera]:
                        if timestamp in entries["files"]:
                            classes = self.create_YOLOv5_file(entries["files"][timestamp], archive_path_info_model, classes)

                    self.create_YOLOv5_classes(classes, labels, archive_path_info_model, datestamp+"-"+camera)
                    if model not in model_saved:
                        self.create_YOLOv5_classes(classes, labels, archive_path_info_model)
                        model_saved.append(model)

    def create_YOLOv5_file(self, entry, archive_path_info, classes):
        """
        create YOLOv5 file for an entry

        Args:
            entry (dict): db entry for file
            archive_path_info (str): destination path for the YOLOv5 file to be stored
            classes (dict): growing list of used classes as input
        Returns:
            dict: growing list of classes
        """
        if "detections" in entry:
            filename = entry["hires"].replace(".jpeg", ".txt")
            file_string = ""
            for detection in entry["detections"]:
                if str(detection["class"]) not in classes:
                    classes[detection["class"]] = detection["label"]
                file_string += str(detection["class"]) + " "
                [start_x, start_y, end_x, end_y] = detection["coordinates"]
                width = end_x - start_x
                height = end_y - start_y
                pos_x = start_x + (width / 2)
                pos_y = start_y + (height / 2)
                file_string += str(round(pos_x, 6)) + " " + str(round(pos_y, 6)) + " "
                file_string += str(round(width, 6)) + " " + str(round(height, 6)) + "\n"
            file_path = str(os.path.join(archive_path_info, filename))
            self.text.write(file_path, file_string)
            self.logging.debug(" * write file " + file_path)
        return classes

    def create_YOLOv5_classes(self, classes, labels, archive_path_info, extension=""):
        """
        Create file with used classes as classes.txt

        Args:
            classes (dict): class definition from detections
            labels (dict): label definition from detection model
            archive_path_info (str): destination path for the YOLOv5 file to be stored
            extension (str): string to be added into the filename (e.g. date or camera id)
        """
        if extension != "":
            extension = "_" + extension
        file_string = ""
        file_path = str(os.path.join(archive_path_info, "classes"+extension+".txt"))
        if labels == {}:
            for class_id in classes:
                file_string += str(classes[class_id]) + "\n"
        else:
            for label in labels:
                file_string += labels[label] + "\n"
        self.text.write(file_path, file_string)
        self.logging.debug(" * write file " + file_path)

    def delete(self, download_id):
        """
        delete download files that are older than ...

        Args:
            download_id (str): download id to identify download
        """
        self.logging.info("Delete file from download folder: " + self.downloads[download_id]["file_path"])
        if self.downloads[download_id]["created"]:
            if os.path.exists(self.downloads[download_id]["file_path"]):
                os.remove(self.downloads[download_id]["file_path"])
        del self.downloads[download_id]

    def delete_all_downloads(self):
        """
        clean up download directory and internal dict
        """
        self.logging.info("Delete all files in download folder ...")
        try:
            download_directory = str(birdhouse_main_directories["download"])
            command = "rm -rf " + download_directory
            os.system(command)
            self.downloads = {}
        except Exception as e:
            self.logging.error("Couldn't delete all downloads: " + str(e))


class BirdhouseArchive(threading.Thread, BirdhouseClass):
    """
    class to archive and download images files
    """

    def __init__(self, config, camera, views):
        """
        Initialize new thread and set initial parameters

        Args:
            config (modules.config.BirdhouseConfig): reference to config handler
            camera (dict[str, modules.config.BirdhouseCamera]): reference to camera handler
            views (dict[str, modules.views.BirdhouseViews]): reference to view handler
        """
        threading.Thread.__init__(self)
        BirdhouseClass.__init__(self, class_id="backup", config=config)
        self.thread_set_priority(5)

        self.camera = camera
        self.views = views
        self.archive_data = False
        self.backup_start = False
        self.backup_running = False
        self.recreate_config = False

        self.img_support = BirdhouseImageSupport("", config)
        self.download = BirdhouseArchiveDownloads(config)
        self.download.start()

    def run(self):
        """
        start backup handler
        """
        backup_started = False
        self.logging.info("Starting backup handler ...")
        while self._running:
            stamp = self.config.local_time().strftime('%H%M%S')
            check_stamp = str(int(stamp[0:4]) - 1)

            if (int(check_stamp) == int(self.config.param["backup"]["time"])
                    or self.backup_start) and not backup_started:
                backup_started = True
                if self.backup_start:
                    self.logging.info("Starting forced backup ...")
                else:
                    self.logging.info("Starting daily backup ...")
                self.backup_files()
                self.views.archive.list_update(force=True)
                self.views.favorite.list_update(force=True)
                self.views.object.list_update(force=True)
                count = 0
                while self._running and count < 60:
                    time.sleep(1)
                    count += 1
                if self.backup_start:
                    self.config.async_answers.append(["BACKUP_DONE"])
                    self.backup_start = False
                self.logging.info("Backup DONE.")
            else:
                backup_started = False

            if len(self.views.archive.config_recreate) > 0:
                self.views.archive.config_recreate_progress = True
                date = self.views.archive.config_recreate.pop()
                self._create_image_config_save(date)
                self.views.archive.config_recreate_progress = False

            if self.recreate_config:
                files = self.create_image_config(date="", recreate=True)
                if files is not None:
                    self.config.db_handler.write(config="images", date="", data=files, create=True, save_json=True)
                self.config.async_answers.append(["CREATE_IMG_CONFIG_DONE"])
                self.recreate_config = False

            self.thread_control()
            self.thread_wait()

        self.logging.info("Stopped backup handler.")

    def start_backup(self):
        """
        start backup
        """
        self.backup_start = True

    def backup_files(self, other_date=""):
        """
        Backup files with threshold to folder with date ./images/YYMMDD/

        Args:
            other_date (str): other date if not today
        """
        self.backup_running = True
        if other_date == "":
            backup_date = self.config.local_time().strftime('%Y%m%d')
        else:
            backup_date = other_date

        backup_camera_list = []
        for cam in self.camera:
            backup_camera_list.append(cam)

        backup_directory = self.config.db_handler.directory(config="backup", date=backup_date)
        data_weather = self.config.db_handler.read(config="weather")
        data_sensor = self.config.db_handler.read(config="sensor")

        # if the directory but no config file exists for backup directory create a new one
        if os.path.isdir(backup_directory):
            self.logging.info("Backup files: create a new config file, directory already exists")

            if not os.path.isfile(self.config.db_handler.file_path(config="backup", date=backup_date)):
                files = self.create_image_config(date=backup_date)
                files_backup = {
                    "files": files,
                    "info": {},
                    "favorite": {},
                    "chart_data": self.views.create.chart_data_new(data_image=files,
                                                                   data_sensor=data_sensor,
                                                                   data_weather=data_weather,
                                                                   date=backup_date,
                                                                   cameras=backup_camera_list),
                    "weather_data": self.views.create.weather_data_new(data_weather=data_weather)
                }
                files_backup["info"]["count"] = len(files)
                files_backup["info"]["threshold"] = {}
                for cam in self.camera:
                    files_backup["info"]["threshold"][cam] = self.camera[cam].param["similarity"]["threshold"]
                files_backup["info"]["date"] = backup_date[6:8] + "." + backup_date[4:6] + "." + backup_date[0:4]
                files_backup["info"]["size"] = sum(
                    os.path.getsize(os.path.join(backup_directory, f)) for f in os.listdir(backup_directory) if
                    f.endswith(".jpeg") or f.endswith(".jpg") or f.endswith(".json"))
                self.config.db_handler.write(config="backup", date=backup_date, data=files_backup,
                                             create=True, save_json=True)

        # if no directory exists, create directory, copy files and create a new config file (copy existing information)
        else:
            self.logging.info("Backup files: copy files and create a new config file (copy existing information)")

            self.config.db_handler.directory_create(config="images", date=backup_date)
            files = self.config.db_handler.read_cache(config="images")
            files_chart = files.copy()
            files_backup = {"files": {}, "chart_data": {}, "info": {}, "weather_data": {}, "detection": {}}

            file_sensor = self.config.db_handler.file_path(config="sensor")
            file_sensor_copy = os.path.join(self.config.db_handler.directory(config="images", date=backup_date),
                                            self.config.files["sensor"])
            file_weather = self.config.db_handler.file_path(config="weather")
            file_weather_copy = os.path.join(self.config.db_handler.directory(config="images", date=backup_date),
                                             self.config.files["weather"])
            file_stats = self.config.db_handler.file_path(config="statistics")
            file_stats_copy = os.path.join(self.config.db_handler.directory(config="images", date=backup_date),
                                           self.config.files["statistics"])

            stamps = list(reversed(sorted(files.keys())))
            dir_source = self.config.db_handler.directory(config="images")
            count = 0
            count_data = 0
            count_other_date = 0
            backup_size = 0

            if os.path.isfile(file_sensor):
                os.popen("cp " + file_sensor + " " + str(file_sensor_copy))
            if os.path.isfile(file_weather):
                os.popen("cp " + file_weather + " " + str(file_weather_copy))
            if os.path.isfile(file_stats):
                os.popen("cp " + file_stats + " " + str(file_stats_copy))

            info = True
            for cam in self.camera:
                for stamp in stamps:
                    save_entry = False

                    if self.if_shutdown() and info:
                        self.logging.info("Backup process is running, shut down may take a bit longer ...")
                        info = False

                    # if recording slow down this process
                    if self.if_other_prio_process("backup"):
                        time.sleep(0.2)

                    # if files are to be archived
                    if "datestamp" not in files[stamp]:
                        self.logging.warning("Wrong entry format [1]:" + str(files[stamp]))

                    if "_" not in stamp and stamp in files and "datestamp" in files[stamp] and \
                            files[stamp]["datestamp"] == backup_date and files[stamp]["camera"] == cam:

                        # create copy of entry (to modify without damage in original data)
                        update_new = files[stamp].copy()

                        # if images are to be archived
                        if self.camera[cam].img_support.select(timestamp=stamp, file_info=files[stamp].copy()):

                            count += 1
                            file_lowres = self.img_support.filename(image_type="lowres", timestamp=stamp, camera=cam)
                            file_hires = self.img_support.filename(image_type="hires", timestamp=stamp, camera=cam)
                            file_hires_detect = file_hires.replace(".jpeg", "_detect.jpeg")

                            if "similarity" not in update_new:
                                update_new["similarity"] = 100
                            if "hires" not in update_new:
                                update_new["hires"] = file_hires
                            if "favorit" not in update_new:
                                update_new["favorit"] = 0
                            if "type" not in update_new:
                                update_new["type"] = "image"
                            if "detections" in update_new and len(update_new["detections"]) > 0:
                                files_backup["info"]["detection_" + cam] = True

                            update_new["directory"] = "/" + self.config.db_handler.directory("images", backup_date)+"/"

                            if os.path.isfile(os.path.join(dir_source, file_lowres)) and \
                                    os.path.isfile(os.path.join(dir_source, file_hires)):

                                update_new["size"] = (os.path.getsize(os.path.join(dir_source, file_lowres)) +
                                                      os.path.getsize(os.path.join(dir_source, file_hires)))
                                backup_size += update_new["size"]

                                os.popen('cp ' + os.path.join(str(dir_source), file_lowres) + ' ' +
                                         os.path.join(str(backup_directory), file_lowres))
                                os.popen('cp ' + os.path.join(str(dir_source), file_hires) + ' ' +
                                         os.path.join(str(backup_directory), file_hires))

                                if os.path.isfile(os.path.join(dir_source, file_hires_detect)):
                                    os.popen('cp ' + os.path.join(str(dir_source), file_hires_detect) + ' ' +
                                             os.path.join(str(backup_directory), file_hires_detect))

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

                # add detection information
                camera_settings = self.config.param["devices"]["cameras"][cam]
                if "object_detection" in camera_settings and camera_settings["object_detection"]["active"]:
                    files_backup["info"]["detection_" + cam] = {
                        "date": self.config.local_time().strftime('%d.%m.%Y %H:%M:%S'),
                        "threshold": camera_settings["object_detection"]["threshold"],
                        "model": camera_settings["object_detection"]["model"],
                        "detected": False
                    }
                else:
                    files_backup["info"]["detection_" + cam] = {
                        "date": self.config.local_time().strftime('%d.%m.%Y %H:%M:%S'),
                        "threshold": 0,
                        "model": "N/A",
                        "detected": False
                    }
                detections = self.camera[cam].object.summarize_detections(files_backup["files"])
                if len(detections) > 0 and self.camera[cam].object.detect_objects is not None:
                    labels = self.camera[cam].object.detect_objects.get_labels()
                    files_backup["info"]["detection_" + cam]["detected"] = True
                    files_backup["info"]["detection_" + cam]["labels"] = labels
                elif len(detections) > 0:
                    files_backup["info"]["detection_" + cam]["detected"] = True
                    files_backup["info"]["detection_" + cam]["labels"] = []

            # create chart data from sensor and weather data vor archive
            files_backup["chart_data"] = self.views.create.chart_data_new(data_image=files_chart,
                                                                          data_sensor=data_sensor,
                                                                          data_weather=data_weather,
                                                                          date=backup_date,
                                                                          cameras=backup_camera_list)
            # extract relevant weather data for archive
            files_backup["weather_data"] = self.views.create.weather_data_new(data_weather=data_weather,
                                                                              date=backup_date)
            files_backup["detection"] = self.camera[backup_camera_list[0]].object.summarize_detections(
                files_backup["files"])
            files_backup["info"]["date"] = backup_date[6:8] + "." + backup_date[4:6] + "." + backup_date[0:4]
            files_backup["info"]["count"] = count
            files_backup["info"]["size"] = backup_size
            files_backup["info"]["threshold"] = {}
            for cam in self.camera:
                files_backup["info"]["threshold"][cam] = self.camera[cam].param["similarity"]["threshold"]

            self.config.db_handler.write(config="backup", date=backup_directory, data=files_backup,
                                         create=True, save_json=True)
            self.config.queue.set_status_changed(date=backup_directory, change="archive")

        self.backup_running = False

    def download_files(self, param, file_list=None):
        """
        add download requests to queue

        Args:
            param (dict): parameter from API request
            file_list (list): optional, list of files - entry format YYYYMMDD_HHMMSS
        Returns:
            dict: API response
        """
        self.download.add2queue(param, file_list)
        return {
            "command": "requested download files: " + param["parameter"][0] + "/" + param["which_cam"],
            "date": param["parameter"][0]
        }

    def download_files_waiting(self, param):
        """
        check if downloads waiting for a specific session id

        Returns:
            status if downloads are waiting
        """
        return self.download.waiting(param)

    def create_video_config(self):
        """
        recreate video config file, if not exists
        """
        video_path = self.config.db_handler.directory(config="videos")
        self.logging.info("Create video list for video directory ...")
        self.logging.debug("Reading files from path: " + video_path)
        file_list = [f for f in os.listdir(video_path) if f.endswith(".mp4") and "short" not in f and
                     os.path.isfile(os.path.join(video_path, f))]
        file_list.sort(reverse=True)
        files = {}
        for file in file_list:

            self.logging.info(" - " + file)
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

            cap = cv2.VideoCapture(os.path.join(video_path, file))
            frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps == 0:
                fps = 1
            length = float(frames) / fps
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            file_name_short = param[0] + "_" + param[1] + "_" + param[2] + "_" + param[3] + "_short.mp4"
            if os.path.isfile(os.path.join(video_path, file_name_short)):
                file_short = file_name_short
                cap = cv2.VideoCapture(os.path.join(video_path, file_short))
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

        Args:
            date (str): create config file for this date
            recreate (bool): recreate config file completely
        """
        time.sleep(1)
        if date == "":
            self.logging.info("(Re)create image config file for main directory ...")
            path = self.config.db_handler.directory(config="images")
        else:
            self.logging.info("(Re)create image config file for  directory " + date + " ...")
            path = self.config.db_handler.directory(config="backup", date=date)
        if recreate and os.path.isfile(path):
            self.logging.info("Remove existing image config file ...")
            os.remove(path)

        # file_list = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)) and "_big" not in f]
        # file_list = [f for f in os.listdir(path) if "_big" not in f and os.path.isfile(os.path.join(path, f))]
        file_list = [f for f in os.listdir(path) if "_big" and "_diff" not in f and (f.endswith(".jpg") or f.endswith("jpeg"))]

        file_list.sort(reverse=True)
        files = self._create_image_config_analyze(file_list=file_list, init=True, subdir=date)
        self.logging.info("Done.")
        return files

    def create_image_config_api(self, param):
        """
        Call (re)creation via API and return JSON answer

        Args:
            param (dict): parameters from API request
        Returns:
            dict: information for API response
        """
        response = {"command": ["recreate main image config file", param["parameter"]]}
        self.recreate_config = True
        return response

    def _create_image_config_save(self, date=""):
        """
        create and save image config

        Args:
            date (str): date of config file to be saved
        """
        camera_list = []
        for cam in self.camera:
            camera_list.append(cam)

        directory = self.config.db_handler.directory(config="images", date=date)
        if not os.path.isdir(directory):
            self.logging.warning("Directory '" + directory + "' doesn't exist.")
            return

        if self.config.db_handler.exists(config="weather", date=date):
            data_weather = self.config.db_handler.read(config="weather", date=date)
        else:
            data_weather = {}

        if self.config.db_handler.exists(config="sensor", date=date):
            data_sensor = self.config.db_handler.read(config="sensor", date=date)
        else:
            data_sensor = {}

        # !!! Recreation of chart_data and weather_data seems not to work correctly
        files = self.create_image_config(date, True)
        files_backup = {
            "files": files,
            "info": {},
            "chart_data": self.views.create.chart_data_new(data_image=files,
                                                           data_sensor=data_sensor, data_weather=data_weather,
                                                           date=date, cameras=camera_list),
            "weather_data": self.views.create.weather_data_new(data_weather=data_weather)
        }
        files_backup["info"]["count"] = len(files)
        files_backup["info"]["threshold"] = {}
        for cam in self.camera:
            files_backup["info"]["threshold"][cam] = self.camera[cam].param["similarity"]["threshold"]
        files_backup["info"]["date"] = date[6:8] + "." + date[4:6] + "." + date[0:4]
        files_backup["info"]["size"] = sum(
            os.path.getsize(os.path.join(directory, f)) for f in os.listdir(directory) if
            f.endswith(".jpeg") or f.endswith(".jpg") or f.endswith(".json"))
        self.config.db_handler.write(config="backup", date=date, data=files_backup,
                                     create=True, save_json=True)

    def _create_image_config_analyze(self, file_list, init=False, subdir=""):
        """
        Compare image files and write to config file (incl. sensor data if exist)

        Args:
            file_list (list): list of files to be analyzed
            init (bool): initialize
            subdir (str): subdirectory
        """
        if self._processing:
            # this part potentially can be removed again
            self.logging.warning("Compare Files already processing ...")
            return

        self._processing = True
        self.logging.info("Start recreation for " + str(len(file_list)) + " image files ...")

        if os.path.isfile(self.config.db_handler.file_path("images")) and subdir == "" and not init:
            files = self.config.db_handler.read_cache(config='images')
            self.logging.debug("Use existing config file.")

        else:
            files = {}
            self.logging.debug("Start with a fresh config file.")
            files = self._create_image_config_get_filelist(file_list=file_list, files=files, subdir=subdir)

            self.logging.debug("Integrate sensor data ...")
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

            self.logging.debug("Integration of sensor data done.")

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
            key_last = ""
            image_current = ""
            image_hires = ""
            image_last = ""
            if cam not in files_new_cam:
                continue
            files_keys = list(files_new_cam[cam].keys())
            keys_count = len(files_keys)

            for i in tqdm(range(0, keys_count), desc="Reloading images " + cam + " ..."):
                key = files_keys[i]
                if key in files_new and files_new[key]["camera"] == cam:
                    height_h = 0
                    height_l = 0
                    width_h = 0
                    width_l = 0
                    filename = ""
                    filename_hires = files_new[key]["hires"]
                    filename_lowres = files_new[key]["lowres"]

                    if subdir != "":
                        files_new[key]["datestamp"] = subdir
                        files_new[key]["date"] = subdir[6:8] + "." + subdir[4:6] + "." + subdir[0:4]
                        files_new[key]["time"] = key[0:2] + ":" + key[2:4] + ":" + key[4:6]
                        files_new[key]["directory"] = self.config.db_handler.directory("images", subdir, False)

                    files_new[key]["to_be_deleted"] = 0
                    files_new[key]["favorit"] = 0
                    files_new[key]["type"] = "image"
                    files_new[key]["compare"] = [key]
                    files_new[key]["similarity"] = 0

                    self.logging.debug("- Identify image data: " + key + "/" + cam + "/" + filename_lowres + "/" +
                                       filename_hires)
                    try:
                        filename = os.path.join(self.config.db_handler.directory(config="images"),
                                                subdir, filename_lowres)
                        image_current = cv2.imread(str(filename))
                        image_current = cv2.cvtColor(image_current, cv2.COLOR_BGR2GRAY)
                        height_l, width_l = image_current.shape[:2]

                        filename = os.path.join(self.config.db_handler.directory(config="images"),
                                                subdir, filename_hires)
                        image_hires = cv2.imread(str(filename))
                        height_h, width_h = image_hires.shape[:2]
                        self.logging.debug("  OK.")

                    except Exception as e:
                        self.config.queue.entry_add(config="images", date=subdir, key=key, entry=files_new[key])
                        self.raise_error("Could not load image: " + str(filename) + " ... " + str(e))
                        continue

                    files_new[key]["size"] = len(image_hires)
                    files_new[key]["hires_size"] = [width_h, height_h]
                    files_new[key]["lowres_size"] = [width_l, height_l]

                    self.logging.debug("- compare image " + filename_lowres + " with last image " + filename_last)
                    if len(filename_last) > 0:
                        detection_area = self.camera[cam].param["similarity"]["detection_area"]
                        score = self.camera[cam].image.compare_raw(image_current, image_last, detection_area)
                        files_new[key]["compare"] = (key, key_last)
                        files_new[key]["similarity"] = score
                        count += 1

                    if init:
                        sensor_str = ""
                        if "sensor" in files_new[key]:
                            sensor_str = str(files_new[key]["sensor"])
                        self.logging.debug(
                            " - " + cam + ": " + filename_lowres + "  " + str(count) + "/" + str(len(files)) +
                            " - " + str(files_new[key]["similarity"]) + "%  " + sensor_str)

                    filename_last = filename_lowres
                    key_last = key
                    image_last = image_current

                    self.config.queue.entry_add(config="images", date=subdir, key=key, entry=files_new[key])

        #        if subdir == '':
        #            self.config.db_handler.write("images", "", files_new)
        self._processing = False
        return files_new

    def _create_image_config_get_filelist(self, file_list, files, subdir=""):
        """
        Get image date from files and add to database entries

        Args:
            file_list (list): list of filenames (without path)
            files (dict): database with file entries
            subdir (str): not used yet ... ?!
        """
        count = 0
        for file in file_list:
            if ".jpg" in file:

                analyze = self.img_support.param_from_filename(filename=file)
                if "error" in analyze:
                    continue

                count += 1
                which_cam = analyze["cam"]
                timestamp = analyze["stamp"]
                files[timestamp] = {}
                files[timestamp]["camera"] = which_cam
                files[timestamp]["recreate"] = 1

                if "cam" in file:
                    files[timestamp]["lowres"] = self.img_support.filename(image_type="lowres", timestamp=timestamp,
                                                                           camera=which_cam)
                    files[timestamp]["hires"] = self.img_support.filename(image_type="hires", timestamp=timestamp,
                                                                          camera=which_cam)
                else:
                    files[timestamp]["lowres"] = self.img_support.filename(image_type="lowres", timestamp=timestamp)
                    files[timestamp]["hires"] = self.img_support.filename(image_type="hires", timestamp=timestamp)

                if subdir == "":
                    file_dir = os.path.join(self.config.db_handler.directory(config='images'), file)
                    timestamp2 = datetime.fromtimestamp(os.path.getmtime(file_dir))

                    files[timestamp]["datestamp"] = timestamp2.strftime("%Y%m%d")
                    files[timestamp]["date"] = timestamp2.strftime("%d.%m.%Y")
                    files[timestamp]["time"] = timestamp2.strftime("%H:%M:%S")

                else:
                    files[timestamp]["datestamp"] = subdir
                    files[timestamp]["date"] = subdir[6:8] + "." + subdir[4:6] + "." + subdir[0:4]
                    files[timestamp]["time"] = timestamp[0:2] + ":" + timestamp[2:4] + "." + timestamp[4:6]

                if "sensor" not in files[timestamp]:
                    files[timestamp]["sensor"] = {}

        self.logging.debug("Extracted infos for " + str(count) + " out of " + str(len(file_list)) + " files ...")
        return files

    def delete_marked_files_api(self, param):
        """
        set / unset recycling

        Args:
            param (dict): parameters from API request
        Returns:
            dict: information for API response
        """
        date = ""
        config = ""
        category = param["parameter"][0]
        response = {"command": ["delete files that are marked as 'to_be_deleted'", param]}

        if "delete_not_used" in param["parameter"]:
            delete_not_used = True
        else:
            delete_not_used = False

        if category == "backup":
            self.logging.info("Delete marked files: BACKUP (" + str(param["parameter"]) + ")")
            date = param["parameter"][1]
            config = "images"
        elif category == "today":
            self.logging.info("Delete marked files: TODAY (" + str(param["parameter"]) + ")")
            date = ""
            config = "images"
        elif category == "video":
            self.logging.info("Delete marked files: VIDEO (" + str(param["parameter"]) + ")")
            date = ""
            config = "videos"
        else:
            self.raise_error("Delete marked files: Not clear what to be deleted (" + str(param["parameter"]) + ")")
            response["error"] = "not clear, which files shall be deleted"

        if "error" not in response:
            response = self._delete_marked_files_exec(config=config, date=date, delete_not_used=delete_not_used)
            self.config.queue.add_to_status_queue(config=config, date=date, key="end",
                                                  change_status="DELETE_RANGE_END", status=0)
        return response

    def _delete_marked_files_exec(self, config="images", date="", delete_not_used=False):
        """
        delete files which are marked to be recycled for a specific date + database entry

        Args:
            config (str): type of configuration (images, backup, videos)
            date (str): date of archive where files shall be deleted
            delete_not_used (bool): delete unused files
        Returns:
            dict: information for API response
        """
        response = {}
        del_file_types = ["lowres", "hires", "video_file", "thumbnail"]
        files_in_config = []
        delete_keys = []

        # get data from DB
        if config == "images" and date == "":
            files = self.config.db_handler.read_cache(config='images')
            del_directory = self.config.db_handler.directory(config='images')
        elif config == "images":
            config_file = self.config.db_handler.read_cache(config='backup', date=date)
            del_directory = self.config.db_handler.directory(config='backup', date=date)
            files = config_file["files"]
            config = "backup"
        elif config == "videos":
            files = self.config.db_handler.read_cache(config='videos')
            del_directory = self.config.db_handler.directory(config='videos')
        else:
            response["error"] = "file type not supported"
            return response

        # prepare date_stamp
        if date != "":
            check_date = date[6:8] + "." + date[4:6] + "." + date[0:4]
        else:
            check_date = ""

        self.logging.info(" - Prepare DELETE: Start to read data from " + del_directory)
        start_time = time.time()
        files_in_dir = [f for f in os.listdir(del_directory) if f.endswith(".jpg") or f.endswith(".jpeg")]
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
                    for file_type in del_file_types:
                        if file_type in files[key]:
                            files_in_config.append(files[key][file_type])

                if "to_be_deleted" in files[key] and int(files[key]["to_be_deleted"]) == 1:
                    delete_keys.append(key)

        self.logging.info(" - Prepare DELETE " + config + ": total_entries=" + str(len(files)) + "; " +
                          "total_file_entries=" + str(len(files_in_config)) + "; " +
                          "to_delete=" + str(len(delete_keys)) + "; ")

        # delete identified files if exist (videos and backup)
        count_del_file = 0
        count_del_entry = 0
        for key in delete_keys:
            try:
                if config == "backup" or config == "videos" or config == "images":
                    for file_type in del_file_types:
                        if file_type in files[key]:
                            if os.path.isfile(os.path.join(del_directory, files[key][file_type])):
                                os.remove(os.path.join(del_directory, files[key][file_type]))
                                count_del_file += 1
                                self.logging.debug(
                                    "Delete - " + str(key) + ": " + str(os.path.join(del_directory, files[key][file_type])))

                if config == "backup" or config == "images":
                    self.config.queue.entry_keep_data(config=config, date=date, key=key)
                    count_del_entry += 1

                elif config == "videos":
                    self.config.queue.entry_delete(config=config, date=date, key=key)
                    count_del_entry += 1

            except Exception as e:
                self.raise_error(" - Error while deleting file '" + key + "' ... " + str(e))
                response["error"] += "delete file '" + key + "': " + str(e) + "\n"

        self.logging.info(" - Perform DELETE " + config + ": files=" + str(count_del_file) + "; " +
                          "entries=" + str(count_del_entry) + "; ")

        count_del_file = 0
        # delete unused files
        if delete_not_used:
            for file in files_in_dir:
                if file not in files_in_config:
                    os.remove(os.path.join(del_directory, file))
            self.logging.info(" - Perform DELETE 'unused': files=" + str(count_del_file) + "; ")

        self.logging.debug(str(len(files_in_dir)) + "/" + str(len(files_in_config)))

        response["deleted_count"] = count_del_entry
        response["deleted_keys"] = delete_keys
        response["files_not_used"] = len(files_in_dir) - len(files_in_config)
        response["files_used"] = len(files_in_config)

        self.logging.info(" -> Deleted " + str(count_del_entry) + " marked files in " + del_directory + ".")
        return response

    def delete_archived_day(self, param):
        """
        delete complete directory incl. files in it and trigger recreation of archive and favorite view

        Args:
            param (dict): parameters from API request
        Returns:
            dict: information for API response
        """
        date = param["parameter"][0]
        response = {"command": ["delete archived date '" + date + "'"]}

        try:
            archive_directory = str(
                os.path.join(birdhouse_main_directories["data"], birdhouse_directories["backup"], date))
            command = "rm -rf " + archive_directory
            os.system(command)
            self.views.archive.list_update(force=True)
            self.views.favorite.list_update(force=True)
            self.views.object.list_update(force=True)
            self.logging.info(
                "Deleted archived day '" + date + "' and triggered recreation of archive and favorite view")
        except Exception as e:
            self.logging.error("Error while trying to delete data from '" + date + "': " + str(e))

        return response
