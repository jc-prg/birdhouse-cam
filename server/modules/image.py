import numpy as np
import cv2
import os

from skimage.metrics import structural_similarity as ssim
from modules.bh_class import BirdhouseCameraClass


class BirdhouseImageProcessing(BirdhouseCameraClass):
    """
    modify encoded and raw images
    """

    def __init__(self, camera_id, config):
        BirdhouseCameraClass.__init__(self, class_id=camera_id+"-img", class_log="image",
                                      camera_id=camera_id, config=config)

        self.frame = None

        self.text_default_position = (30, 40)
        self.text_default_scale = 0.8
        self.text_default_font = cv2.FONT_HERSHEY_SIMPLEX
        self.text_default_color = (255, 255, 255)
        self.text_default_thickness = 2

        self.img_camera_error = "camera_na.jpg"
        self.img_camera_error_v2 = "camera_na_v3.jpg"
        self.img_camera_error_v3 = "camera_na_v4.jpg"
        self.img_camara_error_server = "camera_na_server.jpg"

        self.error_camera = False
        self.error_image = {}

        self.logging.info("Connected IMAGE processing ("+self.id+") ...")

    def compare(self, image_1st, image_2nd, detection_area=None):
        """
        calculate structural similarity index (SSIM) of two images
        """
        if self.error_camera:
            return 0

        image_1st = self.convert_to_raw(image_1st)
        image_2nd = self.convert_to_raw(image_2nd)
        similarity = self.compare_raw(image_1st, image_2nd, detection_area)
        return similarity

    def compare_raw(self, image_1st, image_2nd, detection_area=None):
        """
        calculate structural similarity index (SSIM) of two images
        """
        if self.error_camera:
            return 0

        try:
            if len(image_1st) == 0 or len(image_2nd) == 0:
                self.raise_warning("Compare: At least one file has a zero length - A:" +
                                   str(len(image_1st)) + "/ B:" + str(len(image_2nd)))
                score = 0
        except Exception as e:
            self.raise_warning("Compare: At least one file has a zero length: " + str(e))
            score = 0

        if detection_area is not None:
            image_1st, area = self.crop_raw(raw=image_1st, crop_area=detection_area, crop_type="relative")
            image_2nd, area = self.crop_raw(raw=image_2nd, crop_area=detection_area, crop_type="relative")
        else:
            area = [0, 0, 1, 1]

        try:
            self.logging.debug(self.id + "/compare 1: " + str(detection_area) + " / " + str(image_1st.shape))
            self.logging.debug(self.id + "/compare 2: " + str(area) + " / " + str(image_1st.shape))
            (score, diff) = ssim(image_1st, image_2nd, full=True)

        except Exception as e:
            self.raise_warning("Error comparing images (" + str(e) + ")")
            score = 0

        return round(score * 100, 1)

    def compare_raw_show(self, image_1st, image_2nd):
        """
        show in an image where the differences are
        """
        image_diff = cv2.subtract(image_2nd, image_1st)

        # color the mask red
        Conv_hsv_Gray = cv2.cvtColor(image_diff, cv2.COLOR_BGR2GRAY)
        ret, mask = cv2.threshold(Conv_hsv_Gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
        image_diff[mask != 255] = [0, 0, 255]

        image_diff = self.draw_area_raw(raw=image_diff, area=self.param["similarity"]["detection_area"],
                                        color=(0, 255, 255))

        return image_diff

    def convert_from_raw(self, raw):
        """
        convert from raw image to image // untested
        """
        try:
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 100]
            r, buf = cv2.imencode(".jpg", raw, encode_param)
            size = len(buf)
            image = bytearray(buf)
            return image
        except Exception as e:
            self.raise_error("Error convert RAW image -> image (" + str(e) + ")")
            return raw

    def convert_to_raw(self, image):
        """
        convert from device to raw image -> to be modified with CV2
        """
        if self.error_camera:
            return

        try:
            image = np.frombuffer(image, dtype=np.uint8)
            raw = cv2.imdecode(image, 1)
            return raw
        except Exception as e:
            self.raise_error("Error convert image -> RAW image (" + str(e) + ")")
            return

    def convert_to_gray_raw(self, raw):
        """
        convert image from RGB to gray scale image (e.g. for analyzing similarity)
        """
        # error in camera
        if self.error_camera:
            return raw

        # image already seems to be in gray scale
        if len(raw.shape) == 2:
            return raw

        # convert and catch possible errors
        try:
            gray = cv2.cvtColor(raw, cv2.COLOR_BGR2GRAY)
            return gray

        except Exception as e:
            self.raise_error("Could not convert image to gray scale (" + str(e) + ")")
            self.logging.error("Shape " + str(raw.shape))
            return raw

    def convert_from_gray_raw(self, raw):
        """
        convert image from RGB to gray scale image (e.g. for analyzing similarity)
        """
        # error in camera
        if self.error_camera:
            return raw

        # convert and catch possible errors
        try:
            color = cv2.cvtColor(raw, cv2.COLOR_GRAY2BGR)
            return color

        except Exception as e:
            self.raise_error("Could not convert image back from gray scale (" + str(e) + ")")
            self.logging.error("Shape " + str(raw.shape))
            return raw

    def crop(self, image, crop_area, crop_type="relative"):
        """
        crop encoded image
        """
        raw = self.convert_to_raw(image)
        raw = self.crop_raw(raw, crop_area, crop_type)
        image = self.convert_from_raw(raw)
        return image

    def crop_raw(self, raw, crop_area, crop_type="relative"):
        """
        crop image using relative dimensions (0.0 ... 1.0);
        ensure dimension is dividable by 2, which is required to create a video based on this images
        """
        try:
            height = raw.shape[0]
            width = raw.shape[1]

            if crop_type == "relative":
                (w_start, h_start, w_end, h_end) = crop_area
                x_start = int(round(width * w_start, 0))
                y_start = int(round(height * h_start, 0))
                x_end = int(round(width * w_end, 0))
                y_end = int(round(height * h_end, 0))
                crop_area = (x_start, y_start, x_end, y_end)
            else:
                (x_start, y_start, x_end, y_end) = crop_area

            width = x_end - x_start
            height = y_end - y_start
            if round(width / 2) != width / 2:
                x_end -= 1
            if round(height / 2) != height / 2:
                y_end -= 1

            self.logging.debug("H: " + str(y_start) + "-" + str(y_end) + " / W: " + str(x_start) + "-" + str(x_end))
            frame_cropped = raw[y_start:y_end, x_start:x_end]
            #frame_cropped = raw[x_start:x_end, y_start:y_end]
            return frame_cropped, crop_area

        except Exception as e:
            self.raise_error("Could not crop image (" + str(e) + ")")

        return raw, (0, 0, 1, 1)

    def crop_area_pixel(self, resolution, area, dimension=True):
        """
        calculate start & end pixel for relative area
        """
        if "x" in resolution:
            resolution = resolution.split("x")
        width = int(resolution[0])
        height = int(resolution[1])

        (w_start, h_start, w_end, h_end) = area
        x_start = int(round(width * w_start, 0))
        y_start = int(round(height * h_start, 0))
        x_end = int(round(width * w_end, 0))
        y_end = int(round(height * h_end, 0))
        x_width = x_end - x_start
        y_height = y_end - y_start
        if dimension:
            pixel_area = (x_start, y_start, x_end, y_end, x_width, y_height)
        else:
            pixel_area = (x_start, y_start, x_end, y_end)

        self.logging.debug("- Crop area " + self.id + ": " + str(pixel_area))
        return pixel_area

    def draw_text(self, image, text, position=None, font=None, scale=None, color=None, thickness=0):
        """
        Add text on image
        """
        raw = self.convert_to_raw(image)
        raw = self.draw_text_raw(raw, text, position=position, font=font, scale=scale, color=color, thickness=thickness)
        image = self.convert_from_raw(raw)
        return image

    def draw_text_raw(self, raw, text, position=None, font=None, scale=None, color=None, thickness=0):
        """
        Add text on image
        """
        if position is None:
            position = self.text_default_position
        if font is None:
            font = self.text_default_font
        if scale is None:
            scale = self.text_default_scale
        if color is None:
            color = self.text_default_color
        if thickness == 0:
            thickness = self.text_default_thickness

        (x, y) = tuple(position)
        if x < 0 or y < 0:
            if "resolution_cropped" in self.param["image"] and \
                    self.param["image"]["resolution_cropped"] != (0, 0):
                (width, height) = self.param["image"]["resolution_cropped"]
            else:
                height = raw.shape[0]
                width = raw.shape[1]
                self.param["image"]["resolution_cropped"] = (width, height)
            if x < 0:
                x = width + x
            if y < 0:
                y = height + y
            position = (int(x), int(y))

        param = str(text) + ", " + str(position) + ", " + str(font) + ", " + str(scale) + ", " + str(
            color) + ", " + str(thickness)
        self.logging.debug("draw_text_raw: "+param)
        try:
            raw = cv2.putText(raw, text, tuple(position), font, scale, color, thickness, cv2.LINE_AA)
        except Exception as e:
            self.raise_error("Could not draw text into image (" + str(e) + ")")
            self.logging.warning(" ... " + param)

        return raw

    # !!! check if to be moved to EditStream
    def draw_date_raw(self, raw, overwrite_color=None, overwrite_position=None, offset=None):
        date_information = self.config.local_time().strftime('%d.%m.%Y %H:%M:%S')

        font = self.text_default_font
        thickness = 1
        if self.param["image"]["date_time_color"]:
            color = self.param["image"]["date_time_color"]
        else:
            color = None
        if self.param["image"]["date_time_position"]:
            position = self.param["image"]["date_time_position"]
        else:
            position = None
        if offset is None:
            offset = [0, 0]
        position = (int(position[0] + offset[0]), int(position[1] + offset[1]))
        if self.param["image"]["date_time_size"]:
            scale = self.param["image"]["date_time_size"]
        else:
            scale = None

        if overwrite_color is not None:
            color = overwrite_color
        if overwrite_position is not None:
            position = overwrite_position
            thickness = 1
        raw = self.draw_text_raw(raw, date_information, position, font, scale, color, thickness)
        return raw

    def draw_area_raw(self, raw, area=(0, 0, 1, 1), color=(0, 0, 255), thickness=2):
        """
        draw as colored rectangle
        """
        try:
            height = raw.shape[0]
            width = raw.shape[1]
            (x_start, y_start, x_end, y_end, x_width, y_height) = self.crop_area_pixel([width, height], area)
            image = cv2.line(raw, (x_start, y_start), (x_start, y_end), color, thickness)
            image = cv2.line(image, (x_start, y_start), (x_end, y_start), color, thickness)
            image = cv2.line(image, (x_end, y_end), (x_start, y_end), color, thickness)
            image = cv2.line(image, (x_end, y_end), (x_end, y_start), color, thickness)
            return image

        except Exception as e:
            self.raise_warning("Could not draw area into the image (" + str(e) + ")")
            return raw

    def draw_warning_bullet_raw(self, raw, color=None):
        """
        add read circle in raw image (not cropped, depending on lowres position)
        """
        (start_x, start_y, end_x, end_y) = self.param["image"]["crop_area"]
        position = self.config.param["views"]["index"]["lowres_position"]
        if position == 1:
            default_position = (end_x - 25, start_y + 30)
        else:
            default_position = (start_x + 25, start_y + 30)
        self.logging.info(str(default_position))
        default_color = (0, 0, 255)
        if color is None:
            color = default_color
        raw_bullet = cv2.circle(raw, default_position, 4, color, 6)
        if raw_bullet is not None:
            return raw_bullet
        else:
            return raw

    def image_in_image_raw(self, raw, raw2, position=4, distance=10):
        """
        add a smaller image in a larger image,
        inspired by https://answers.opencv.org/question/231069/inserting-logo-in-an-image/
        """
        [w1, h1, ch1] = raw.shape
        [w2, h2, ch2] = raw2.shape
        self.logging.debug("Insert images into image: big="+str(w1)+","+str(h1)+" / small="+str(w2)+","+str(h2))
        # top left
        if position == 1:
            raw[distance:w2+distance, distance:h2+distance] = raw2
        # top right
        if position == 2:
            raw[distance:w2+distance, h1-(distance+h2):h1-distance] = raw2
        # bottom left
        if position == 3:
            raw[w1-(distance+w2):w1-distance, distance:h2+distance] = raw2
        # bottom right
        if position == 4:
            raw[w1-(distance+w2):w1-distance, h1-(distance+h2):h1-distance] = raw2

        return raw

    def rotate_raw(self, raw, degree):
        """
        rotate image
        """
        self.logging.debug("Rotate image " + str(degree) + " ...")
        rotate_degree = "don't rotate"
        if int(degree) == 90:
            rotate_degree = cv2.ROTATE_90_CLOCKWISE
        elif int(degree) == 180:
            rotate_degree = cv2.ROTATE_180
        elif int(degree) == 270:
            rotate_degree = cv2.ROTATE_90_COUNTERCLOCKWISE
        try:
            if rotate_degree != "don't rotate":
                raw = cv2.rotate(raw, rotate_degree)
            return raw
        except Exception as e:
            self.raise_error("Could not rotate image (" + str(e) + ")")
            return raw

    def size(self, image):
        """
        Return size of raw image
        """
        frame = self.convert_to_raw(image)
        try:
            height = frame.shape[0]
            width = frame.shape[1]
            return [width, height]
        except Exception as e:
            self.raise_warning("Could not analyze image (" + str(e) + ")")
            return [0, 0]

    def write(self, filename, image, scale_percent=100):
        """
        Scale image and write to file

        Parameters:
            filename (str): relative path and filename starting from server directory
            image (list): raw image data as list of lists
            scale_percent (int): target size of image in percent
        Returns:
            bool/str: status if successfully
        """
        image_path = os.path.join(self.config.main_directory, filename)
        self.logging.debug("Write image: " + image_path)

        try:
            if scale_percent != 100:
                width = int(image.shape[1] * float(scale_percent) / 100)
                height = int(image.shape[0] * float(scale_percent) / 100)
                image = cv2.resize(image, (width, height))
            return cv2.imwrite(image_path, image)

        except Exception as e:
            error_msg = "Can't save image and/or create thumbnail '" + image_path + "': " + str(e)
            self.raise_error(error_msg)
            return ""

    def read(self, filename: str) -> Any:
        """
        Read image with given filename

        Parameters:
            filename (str): relative path and filename starting from server directory
        Returns:
            list/str: raw image data as list of lists
        """
        image_path = os.path.join(self.config.main_directory, filename)
        self.logging.debug("Read image: " + image_path)

        try:
            image = cv2.imread(image_path)
            self.logging.debug(" --> " + str(image.shape))
            return image

        except Exception as e:
            error_msg = "Can't read image '" + image_path + "': " + str(e)
            self.raise_error(error_msg)
            return ""

    def size_raw(self, raw, scale_percent=100):
        """
        Return size of raw image
        """
        try:
            if scale_percent != 100:
                width = int(raw.shape[1] * float(scale_percent) / 100)
                height = int(raw.shape[0] * float(scale_percent) / 100)
                raw = cv2.resize(raw, (width, height))
            height = raw.shape[0]
            width = raw.shape[1]
            return [width, height]
        except Exception as e:
            self.raise_warning("Could not analyze image (" + str(e) + ")")
            return [0, 0]

    def resize_raw(self, raw, scale_percent=100, scale_size=None):
        """
        resize raw image
        """
        self.logging.debug("Resize image ("+str(scale_percent)+"% / "+str(scale_size)+")")
        if scale_size is not None:
            [width, height] = scale_size
            try:
                raw = cv2.resize(raw, (width, height))
            except Exception as e:
                self.raise_error("Could not resize raw image: " + str(e))
        elif scale_percent != 100:
            [width, height] = self.size_raw(raw, scale_percent=scale_percent)
            try:
                raw = cv2.resize(raw, (width, height))
            except Exception as e:
                self.raise_error("Could not resize raw image: " + str(e))
        return raw

