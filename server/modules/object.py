import os
import time
import threading

from modules.presets import *
from modules.bh_class import BirdhouseCameraClass
from modules.image import BirdhouseImageProcessing


class BirdhouseObjectDetection(threading.Thread, BirdhouseCameraClass):

    def __init__(self, camera_id, config):
        """
        create instance of this class for a specific camera
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
        self.last_model = None
        self.image_size_object_detection = self.detect_settings["detection_size"]
        self._processing_percentage = 0

        self.thread_set_priority(4)

    def run(self):
        """
        queue to analyze pictures of archive days
        """
        if not self.detect_active:
            self.logging.info("Do not start OBJECT DETECTION, can be changed in file '.env'.")
            return

        self.logging.info("Starting OBJECT DETECTION for '"+self.id+"' ...")
        self.connect()
        while self._running:

            self._processing_percentage = 0
            if len(self.detect_queue_archive) > 0:
                date = self.detect_queue_archive.pop()
                self.analyze_archive_images(date)

            self.config.object_detection_processing = self._processing
            self.config.object_detection_progress = self._processing_percentage

            self.thread_wait()
            self.thread_control()
        self.logging.info("Stopped OBJECT DETECTION for '"+self.id+"'.")

    def connect(self, first_load=True):
        """
        initialize models for object detection
        """
        if self.detect_active:
            try:
                if first_load or not birdhouse_status["object_detection"]:
                    from modules.detection.detection import DetectionModel, ImageHandling
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
                        self.detect_objects = self.DetectionModel(model_to_load)
                        self.detect_live = self.detect_settings["live"]
                        self.detect_loaded = True
                        self.last_model = self.detect_settings["model"]
                        birdhouse_status["object_detection"] = True
                        self.logging.info(" -> '" + model_to_load + "': OK")
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
        reconnect, e.g., when the model has been changed
        """
        if self.detect_active:
            if self.last_model == self.detect_settings["model"] and self.detect_loaded and not force_reload:
                self.logging.info("Object detection models has not change, don't reload the detection model yet.")
                return

            self.logging.info("Start reconnect of object detection model ...")
            self.detect_objects = None
            self.detect_loaded = False
            self.detect_live = False
            self.detect_settings = self.param["object_detection"]
            self.connect(first_load=False)

    def analyze_image(self, stamp, path_hires, image_hires, image_info):
        """
        analyze image for objects, save in metadata incl. image with labels if detected
        """
        start_time = time.time()
        if self.detect_objects is not None and self.detect_objects.loaded:

            path_hires_temp = path_hires.replace(".jpeg", "_temp.jpeg")
            self.image.write(path_hires_temp, image_hires, scale_percent=self.image_size_object_detection)
            img, detect_info = self.detect_objects.analyze(path_hires_temp, -1, False)
            img = self.detect_visualize.render_detection(image_hires, detect_info, 1, self.detect_settings["threshold"])
            img = self.image.draw_text_raw(img, stamp, (-80, -40), None, 0.5, (255, 255, 255), 1)

            if os.path.exists(path_hires_temp):
                os.remove(path_hires_temp)
            self.logging.debug("Current detection for " + stamp + ": " + str(detect_info))

            if len(detect_info["detections"]) > 0:
                detections_to_save = []
                for detect in detect_info["detections"]:
                    if float(detect["confidence"] * 100) >= float(self.detect_settings["threshold"]):
                        detections_to_save.append(detect.copy())

                if len(detections_to_save) > 0:
                    image_info["detections"] = detections_to_save
                    image_info["hires_detect"] = image_info["hires"].replace(".jpeg", "_detect.jpeg")
                    path_hires_detect = path_hires.replace(".jpeg", "_detect.jpeg")
                    self.image.write(filename=path_hires_detect, image=img)

            image_info["detection_threshold"] = self.detect_settings["threshold"]
            image_info["info"]["duration_2"] = round(time.time() - start_time, 3)

            self.config.queue.entry_add(config="images", date="", key=stamp, entry=image_info)

        else:
            self.logging.debug("Object detection not loaded (" + stamp + ")")

    def analyze_archive_images_start(self, date):
        """
        add analyzing request to the queue
        """
        response = {
            "command": ["archive object detection"],
            "camera": self.id,
            "status": "Added " + date + " to the queue."
        }
        self.detect_queue_archive.append(date)
        return response

    def analyze_archive_images(self, date):
        """
        detect objects for an archived day, replaces  detections if exist
        """
        response = {"command": ["archive object detection"], "camera": self.id}
        self._processing = True
        if self.detect_objects is not None and self.detect_objects.loaded:
            self.logging.info("Starting object detection for " + self.id + " / " + date + " ...")
            archive_data = self.config.db_handler.read(config="backup", date=date)
            archive_entries = archive_data["files"]
            archive_info = archive_data["info"]
            archive_info["detection_"+self.id] = {
                "date":         self.config.local_time().strftime('%d.%m.%Y %H:%M:%S'),
                "threshold":    self.detect_settings["threshold"],
                "model":        self.detect_settings["model"]
            }

            count = 0
            for stamp in archive_entries:
                if archive_entries[stamp]["camera"] == self.id and "hires" in archive_entries[stamp]:

                    if "to_be_deleted" in archive_entries[stamp] and str(archive_entries[stamp]["to_be_deleted"]) == 1:
                        continue

                    path_hires = str(os.path.join(self.config.db_handler.directory("backup", date),
                                                  archive_entries[stamp]["hires"]))
                    path_hires_detect = str(path_hires.replace(".jpeg", "_detect.jpeg"))

                    self.logging.info("- " + date + "/" + stamp + ": " + path_hires_detect)
                    img, detect_info = self.detect_objects.analyze(file_path=path_hires,
                                                                   threshold=self.detect_settings["threshold"],
                                                                   return_image=True, render_detection=True)
                    self.logging.info("- " + date + "/" + stamp + ": " +
                                      str(len(detect_info["detections"])) + " objects detected")
                    if os.path.exists(path_hires_detect):
                        os.remove(path_hires_detect)

                    if len(detect_info["detections"]) > 0:
                        self.image.write(path_hires_detect, img)
                        archive_entries[stamp]["detections"] = detect_info["detections"]
                        archive_entries[stamp]["hires_detect"] = path_hires_detect.split("/")[-1]
                    else:
                        archive_entries[stamp]["detections"] = []
                        archive_entries[stamp]["hires_detect"] = ""

                    self.config.queue.entry_add(config="backup", date=date, key=stamp, entry=archive_entries[stamp])

                count += 1
                self._processing_percentage = round(count / len(archive_entries) * 100, 1)
                self.config.object_detection_processing = self._processing
                self.config.object_detection_progress = self._processing_percentage
                if self._processing_percentage == 100:
                    time.sleep(2)

            archive_detections = self.summarize_detections(archive_entries)
            self.config.queue.set_status_changed(date=date, change="objects")
            self.config.queue.entry_edit(config="backup", date=date, key="info", entry=archive_info)
            self.config.queue.entry_edit(config="backup", date=date, key="detection", entry=archive_detections)
            self.config.queue.add_to_status_queue(config="backup", date=date, key="end",
                                                  change_status="OBJECT_DETECTION_END", status=0)
            msg = "Object detection for " + date + " done, datasets are going to be saved."
            self.logging.info(msg)
            response["status"] = msg
        else:
            msg = "Object detection archive not possible, object detection not loaded."
            response["error"] = msg
            self.logging.info(msg)

        self._processing = False
        return response

    def summarize_detections(self, entries) -> dict:
        """
        check files-section which detected objects are in and summarize for the archive configuration
        """
        self.logging.debug("Summarize detections from entries (" + str(len(entries)) + " entries)")
        detections = {}
        for stamp in entries:
            if "detections" in entries[stamp]:
                camera = entries[stamp]["camera"]
                for detection in entries[stamp]["detections"]:
                    if detection["label"] not in detections:
                        detections[detection["label"]] = {"favorite": [], "default": {}}
                    if camera not in detections[detection["label"]]["default"]:
                        detections[detection["label"]]["default"][camera] = []

                    if "favorit" in entries[stamp] and int(entries[stamp]["favorit"]) == 1:
                        detections[detection["label"]]["favorite"].append(stamp)

                    elif "to_be_deleted" not in entries[stamp] or not int(entries[stamp]["to_be_deleted"]):
                        detections[detection["label"]]["default"][camera].append(stamp)

        return detections
