import os
import time
import threading

from modules.presets import *
from modules.bh_class import BirdhouseCameraClass
from modules.image import BirdhouseImageProcessing


class BirdhouseObjectDetection(threading.Thread, BirdhouseCameraClass):
    """
    Class to control the object detection for a camera.
    """

    def __init__(self, camera_id, config):
        """
        Constructor method for initializing the class.

        Args:
            camera_id (str): id string to identify the camera from which this class is embedded
            config (modules.config.BirdhouseConfig): reference to main config object
        """
        threading.Thread.__init__(self)
        BirdhouseCameraClass.__init__(self, class_id=camera_id + "-object", class_log="cam-object",
                                      camera_id=camera_id, config=config)

        self.image = BirdhouseImageProcessing(camera_id=self.id, config=self.config)
        self.image.resolution = self.param["image"]["resolution"]

        self.DetectionModel = None
        self.detect_active = birdhouse_env["detection_active"]
        self.detect_settings = self.param["object_detection"]
        self.detect_live = False
        self.detect_loaded = False
        self.detect_objects = None
        self.detect_visualize = None
        self.detect_queue_archive = []
        self.detect_queue_image = []
        self.last_model = None
        self.image_size_object_detection = self.detect_settings["detection_size"]
        self._processing_percentage = 0

        self.thread_set_priority(4)

    def run(self):
        """
        Manage queue to analyze pictures of archive days and single images

        Returns:
            None
        """
        if not self.detect_active:
            self.logging.info("Do not start OBJECT DETECTION, can be changed in file '.env'.")
            return

        self.logging.info("Starting OBJECT DETECTION for '" + self.id + "' ...")
        self.connect()
        while self._running:

            self.logging.debug("Object detection queues: image=" + str(len(self.detect_queue_image)) +
                               ", day=" + str(len(self.detect_queue_archive)) +
                               " (prio=" + str(self.priority_processing()) + ")")

            if not self.priority_processing() and len(self.detect_queue_image) > 0:
                [stamp, path_hires, image_hires, image_info] = self.detect_queue_image.pop()
                self.analyze_image(stamp, path_hires, image_hires, image_info)

            elif not self.priority_processing() and len(self.detect_queue_archive) > 0:
                [date, threshold] = self.detect_queue_archive.pop()
                self.analyze_archive_day(date, threshold)

            self.config.object_detection_processing = self._processing
            self.config.object_detection_progress = self._processing_percentage

            # !!! update unclear ?!
            if self.id != "":
                self.detect_settings = self.config.param["devices"]["cameras"][self.id]["object_detection"]

            self.thread_wait()
            self.thread_control()
        self.logging.info("Stopped OBJECT DETECTION for '" + self.id + "'.")

    def connect(self, first_load=True):
        """
        initialize models for object detection

        Args:
            first_load (bool): set True when initializing the first object of this class to import required modules
        Returns:
            None
        """
        if self.detect_active:
            try:
                if first_load or not birdhouse_status["object_detection"]:
                    from modules.detection.detection_v8 import DetectionModel, ImageHandling
                    self.DetectionModel = DetectionModel
                    self.detect_visualize = ImageHandling()

                if self.detect_settings["active"]:

                    if self.detect_settings["model"] is None or self.detect_settings["model"] == "":
                        self.logging.warning("No detection model defined. Check device configuration in the app.")

                    else:
                        model_to_load = self.detect_settings["model"]
                        if model_to_load.endswith(".pt"):
                            model_to_load = os.path.join(detection_custom_model_path, model_to_load)
                        self.logging.info("Initialize object detection model (" + self.name + ") ...")
                        self.logging.info(" -> '" + model_to_load + "'")
                        if "/" not in model_to_load or os.path.exists(model_to_load):
                            self.detect_objects = self.DetectionModel(model_to_load)
                            if self.detect_objects.loaded:
                                self.detect_live = self.detect_settings["live"]
                                self.detect_loaded = True
                                self.last_model = self.detect_settings["model"]
                                birdhouse_status["object_detection"] = True
                                self.logging.info(" -> '" + model_to_load + "': OK")
                            else:
                                self.detect_loaded = False
                                self.logging.info(" -> '" + model_to_load + "': ERROR LOADING MODEL")
                        else:
                            self.detect_loaded = False
                            self.logging.info(" -> '" + model_to_load + "': NOT FOUND")
                else:
                    self.logging.info(" -> Object detection inactive (" + self.name + "), see settings.")

            except Exception as e:
                self.logging.error(" -> Could not load 'modules.detection': " + str(e))
                self.detect_loaded = False
                birdhouse_status["object_detection"] = False
        else:
            self.detect_loaded = False
            self.logging.info(" -> Object detection inactive (" + self.name + "), see .env-file.")

    def reconnect(self, force_reload=False):
        """
        Reconnect, e.g., when connect didn't work due to an error or the model has been changed

        Args:
            force_reload (bool): force a reconnect even if already a model is set
        Returns:
            None
        """
        if self.detect_active:
            if self.last_model == self.detect_settings["model"] and self.detect_loaded and not force_reload:
                self.logging.info("Object detection model has not changed, don't reload the detection model yet.")
                return

            self.logging.info("Start reconnect of object detection model ...")
            self.detect_objects = None
            self.detect_loaded = False
            self.detect_live = False
            self.detect_settings = self.param["object_detection"]
            self.connect(first_load=False)

    def add2queue_analyze_image(self, stamp, path_hires, image_hires, image_info):
        """
        Add 2 Queue: Analyze an image for objects.

        Analyze an image for objects. Changes will be saved in metadata incl. image with labels if detected
        using the config queue.

        Args:
            stamp (str): entry key which is the recording time in the format HHMMSS
            path_hires (str): complete path to the hires image file
            image_hires (numpy.ndarray): hires images, e.g., directly from the camera or read via cv2.imread()
            image_info (dict): complete entry for the image
        Returns:
            None
        """
        self.logging.debug("Add entry to detection queue: " + str(stamp) + " / " + str(path_hires))
        self.detect_queue_image.append([stamp, path_hires, image_hires, image_info])

    def add2queue_analyze_archive_day(self, date, threshold=-1):
        """
        Add object detection request for one date.

        Add object detection analyzing request to the queue for a specific date and camera.
        The camera is defined when an object for a camera is build based on this class.

        Args:
            date (str): archived date that shall be analyzed
            threshold (float): threshold for analyzing
        Returns:
            dict: response for API
        """
        if not self.detect_active:
            response = {
                "command": ["archive object detection"],
                "camera": self.id,
                "error": "Object detections is inactive",
                "status": "Object detections is inactive"
            }
        else:
            response = {
                "command": ["archive object detection"],
                "camera": self.id,
                "status": "Added " + date + " to the queue."
            }
            self.detect_queue_archive.append([date, threshold])
        self.logging.info("Added object detection request for " + date + " to the queue ...")
        return response

    def add2queue_analyze_archive_several_days(self, dates, threshold=-1):
        """
        Add object detection request for a list of dates.

        Add object detection analyzing request to the queue for a list of dates and a specific camera.
        The camera is defined when an object for a camera is build based on this class.

        Args:
            dates (list): list of archived dates that shall be analyzed
            threshold (float): threshold for analyzing
        Returns:
            dict: response for API
        """
        if not self.detect_active:
            response = {
                "command": ["archive object detection - list of dates"],
                "camera": self.id,
                "error": "Object detections is inactive",
                "status": "Object detections is inactive"
            }
        else:
            response = {
                "command": ["archive object detection"],
                "camera": self.id,
                "status": "Added " + str(dates) + " to the queue."
            }
            self.logging.info("Got a bundle of " + str(len(dates)) + " object detection requests ...")
            for date in dates:
                self.add2queue_analyze_archive_day(date, threshold)
        return response

    def analyze_image(self, stamp, path_hires, image_hires, image_info):
        """
        Analyze an image for objects.

        Analyze an image for objects. Changes will be saved in metadata incl. image with labels if detected
        using the config queue.

        Args:
            stamp (str): entry key which is the recording time in the format HHMMSS
            path_hires (str): complete path to the hires image file
            image_hires (numpy.ndarray): hires images, e.g., directly from the camera or read via cv2.imread()
            image_info (dict): complete entry for the image
        Returns:
            None
        """
        if not self.detect_active:
            return

        start_time = time.time()
        if self.detect_objects is not None and self.detect_objects.loaded:
            self.logging.debug("Analyze image: path=" + path_hires + "; model=" +
                               self.detect_settings["model"] + "; threshold=" + str(self.detect_settings["threshold"]))

            path_hires_temp = path_hires.replace(".jpeg", "_temp.jpeg")
            if os.path.exists(path_hires_temp):
                os.remove(path_hires_temp)
            self.image.write(path_hires_temp, image_hires, scale_percent=self.image_size_object_detection)
            img, detect_info = self.detect_objects.analyze(file_path=path_hires_temp,
                                                           threshold=self.detect_settings["threshold"],
                                                           return_image=False)
            if "error" in detect_info:
                self.logging.error("Couldn't detect objects: " + detect_info["error"])
                return

            img = self.detect_visualize.render_detection(img=image_hires, detection_info=detect_info,
                                                         label_position=1, threshold=self.detect_settings["threshold"])

            img = self.image.draw_text_raw(img, stamp, (-80, -40), None, 0.5, (255, 255, 255), 1)

            self.logging.debug("Current detection for " + stamp + ": " + str(detect_info))

            if len(detect_info["detections"]) > 0:
                image_info["detections"] = detect_info["detections"]
                image_info["hires_detect"] = image_info["hires"].replace(".jpeg", "_detect.jpeg")
                path_hires_detect = path_hires.replace(".jpeg", "_detect.jpeg")
                if os.path.exists(path_hires_detect):
                    os.remove(path_hires_detect)
                self.image.write(filename=path_hires_detect, image=img)

            else:
                image_info["detections"] = []
                image_info["hires_detect"] = ""
                path_hires_detect = path_hires.replace(".jpeg", "_detect.jpeg")
                if os.path.exists(path_hires_detect):
                    os.remove(path_hires_detect)

            image_info["detection_threshold"] = self.detect_settings["threshold"]
            image_info["info"]["duration_2"] = round(time.time() - start_time, 3)

            self.config.queue.entry_add(config="images", date="", key=stamp, entry=image_info)

        else:
            self.logging.debug("Object detection not loaded (" + stamp + ")")

    def analyze_archive_day(self, date, threshold):
        """
        Execute detection request for one day.

        Detects objects for an archived day and replace detections if existing.

        Args:
            date (str): date of day to be analyzed
            threshold (float): threshold for analyzing
        Returns:
            dict: in case of direct call from API it returns an API response
        """
        if not self.detect_active:
            response = {
                "command": ["archive object detection"],
                "camera": self.id,
                "error": "Object detections is inactive",
                "status": "Object detections is inactive"
            }
            return response

        if threshold == -1:
            threshold = float(self.detect_settings["threshold"])
        else:
            threshold = float(threshold)

        response = {"command": ["archive object detection"], "camera": self.id}
        self._processing = True
        if self.detect_objects is not None and self.detect_objects.loaded:
            self.logging.info("Starting object detection for " + self.id + " / " + date +
                              " / " + str(threshold) + "% ...")
            archive_data = self.config.db_handler.read(config="backup", date=date)
            archive_entries = archive_data["files"]
            archive_info = archive_data["info"]
            archive_info["detection_" + self.id] = {
                "date": self.config.local_time().strftime('%d.%m.%Y %H:%M:%S'),
                "detected": False,
                "threshold": threshold,
                "model": self.detect_settings["model"]
            }

            count = 0
            found = False
            for stamp in archive_entries:
                if archive_entries[stamp]["camera"] == self.id and "hires" in archive_entries[stamp]:

                    if "to_be_deleted" in archive_entries[stamp] and int(archive_entries[stamp]["to_be_deleted"]) == 1:
                        continue

                    path_hires = str(os.path.join(self.config.db_handler.directory("backup", date),
                                                  archive_entries[stamp]["hires"]))
                    path_hires_detect = str(path_hires.replace(".jpeg", "_detect.jpeg"))

                    self.logging.debug("- " + date + "/" + stamp + ": " + path_hires_detect)
                    img, detect_info = self.detect_objects.analyze(file_path=path_hires,
                                                                   threshold=threshold,
                                                                   return_image=True, render_detection=True)
                    if "error" in detect_info:
                        self.logging.error("Could not detect objects: " + detect_info["error"])
                        continue

                    self.logging.info("- " + date + "/" + stamp + "/" + self.id + ": " +
                                      str(len(detect_info["detections"])) + " objects detected")

                    if len(detect_info["detections"]) > 0:
                        if os.path.exists(path_hires_detect):
                            os.remove(path_hires_detect)
                        self.image.write(path_hires_detect, img)
                        archive_entries[stamp]["detections"] = detect_info["detections"]
                        archive_entries[stamp]["hires_detect"] = path_hires_detect.split("/")[-1]
                        self.config.queue.entry_add(config="backup", date=date, key=stamp, entry=archive_entries[stamp])
                    else:
                        if os.path.exists(path_hires_detect):
                            os.remove(path_hires_detect)
                        archive_entries[stamp]["detections"] = []
                        archive_entries[stamp]["hires_detect"] = ""
                        self.config.queue.entry_add(config="backup", date=date, key=stamp, entry=archive_entries[stamp])

                count += 1
                self._processing_percentage = round(count / len(archive_entries) * 100, 1)
                self.config.object_detection_processing = self._processing
                self.config.object_detection_progress = self._processing_percentage
                self.config.object_detection_waiting = len(self.detect_queue_archive)
                self.config.object_detection_waiting_keys = self.detect_queue_archive
                if self._processing_percentage == 100:
                    time.sleep(2)

            archive_info["detection_" + self.id]["detected"] = True
            archive_info["detection_" + self.id]["labels"] = self.detect_objects.get_labels()

            archive_detections = self.summarize_detections(archive_entries, threshold)
            self.config.queue.set_status_changed(date=date, change="objects")
            self.config.queue.entry_edit(config="backup", date=date, key="info", entry=archive_info)
            self.config.queue.entry_edit(config="backup", date=date, key="detection", entry=archive_detections)
            if len(self.detect_queue_archive) == 0:
                self.config.queue.add_to_status_queue(config="backup", date=date, key="end",
                                                      change_status="OBJECT_DETECTION_END", status=0)
                self.config.object_detection_build_views = True
            msg = "Object detection for " + date + " done, datasets are going to be saved."
            self.logging.info(msg)
            response["status"] = msg
        else:
            msg = "Object detection archive not possible, object detection not loaded."
            response["error"] = msg
            self.logging.info(msg)

        time.sleep(3)
        self._processing = False
        self._processing_percentage = 0
        return response

    def remove_detection_day(self, date):
        """
        remove all object detection information from the data

        Args:
            date (str): date in format YYYYMMDD
        Returns:
            dict: information for API response
        """
        response = {
            "command": ["archive remove object detection"],
            "camera": self.id,
            "status": "Remove object detection data from " + date + " (use queue)."
        }

        archive_data = self.config.db_handler.read(config="backup", date=date)
        archive_entries = archive_data["files"]
        archive_info = archive_data["info"]
        if "detection_" + self.id in archive_data["info"]:
            del archive_data["info"]["detection_" + self.id]

        keys = archive_entries.keys()
        for entry_id in keys:
            entry = archive_entries[entry_id]
            if entry["camera"] == self.id and "detections" in entry:
                archive_entries[entry_id]["detections"] = []
                self.config.queue.entry_edit(config="backup", date=date, key=entry_id, entry=archive_entries[entry_id])

        archive_detections = self.summarize_detections(archive_entries)
        self.config.queue.entry_edit(config="backup", date=date, key="info", entry=archive_info)
        self.config.queue.entry_edit(config="backup", date=date, key="detection", entry=archive_detections)
        return response

    def summarize_detections(self, entries, threshold=-1):
        """
        Check entries from files-section which detected objects are in and summarize for the archive configuration

        Args:
            entries (dict): entries from "files" section of a config file for images
        Returns:
            dict: entry for summarizing "detection" section in config file for images
        """
        if threshold == -1:
            threshold = self.detect_settings["threshold"]
        if not self.detect_active:
            return {}

        self.logging.debug("Summarize detections from entries (" + str(len(entries)) + " entries)")
        detections = {}
        for stamp in entries:
            if "detections" in entries[stamp]:
                camera = entries[stamp]["camera"]
                for detection in entries[stamp]["detections"]:
                    is_favorite = False

                    if detection["label"] not in detections:
                        detections[detection["label"]] = {"favorite": [], "default": {}}

                    if camera not in detections[detection["label"]]["default"]:
                        detections[detection["label"]]["default"][camera] = []

                    if "favorit" in entries[stamp] and int(entries[stamp]["favorit"]) == 1:
                        detections[detection["label"]]["favorite"].append(stamp)
                        detections[detection["label"]]["default"][camera].append(stamp)
                        is_favorite = True

                    elif "to_be_deleted" not in entries[stamp] or not int(entries[stamp]["to_be_deleted"]):
                        detections[detection["label"]]["default"][camera].append(stamp)

                    if "thumbnail" not in detections[detection["label"]] and "confidence" in detection:
                        detections[detection["label"]]["thumbnail"] = {
                            "stamp": stamp,
                            "confidence": detection["confidence"],
                            "threshold": threshold
                        }
                    elif is_favorite or len(detections[detection["label"]]["favorite"]) == 0:
                        detections[detection["label"]]["thumbnail"] = {
                            "stamp": stamp,
                            "confidence": detection["confidence"],
                            "threshold": threshold
                        }

                    elif (len(detections[detection["label"]]["favorite"]) == 0 and "confidence" in detection and
                          detections[detection["label"]]["thumbnail"]["confidence"] < detection["confidence"]):

                        detections[detection["label"]]["thumbnail"] = {
                            "stamp": stamp,
                            "confidence": detection["confidence"],
                            "threshold": threshold
                        }

        return detections

    def priority_processing(self):
        """
        check if processes with higher priorities are running

        Return:
            bool: processing status
        """
        priority_processes = False
        check = self.config.get_processing("video-recording", "all")
        if check is not None:
            for key in check:
                if check[key]:
                    priority_processes = True
        self.logging.debug("PrioProcess: " + str(priority_processes) + " / " + str(check))
        return priority_processes
