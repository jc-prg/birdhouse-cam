import threading
import python_weather
import asyncio
import logging
import time
import requests
from geopy.geocoders import Nominatim
from datetime import datetime, timezone, timedelta
from modules.presets import *


class BirdhouseGPS(object):

    def __init__(self):
        return

    @staticmethod
    def look_up_location(location):
        """
        look up location (https://pypi.org/project/geopy/)
        """
        geo_locator = Nominatim(user_agent="Weather App")
        try:
            geo_location = geo_locator.geocode(location)
            return [geo_location.latitude, geo_location.longitude, geo_location.address]
        except Exception as e:
            return [0, 0, "Error location lookup ("+location+") -> " + str(e)]

    @staticmethod
    def look_up_gps(gps_coordinates):
        """
        look up location (https://pypi.org/project/geopy/)
        """
        geo_locator = Nominatim(user_agent="Weather App")
        try:
            geo_location = geo_locator.reverse(str(gps_coordinates[0]) + ", " + str(gps_coordinates[1]))
            return [geo_location.latitude, geo_location.longitude, geo_location.address]
        except Exception as e:
            return [0, 0, "Error GPS lookup ("+str(gps_coordinates)+") -> " + str(e)]


class BirdhouseWeatherPython(threading.Thread):

    def __init__(self, config, location, time_zone):
        """
        get weather data via python weather (in the main class at the moment)
        """
        threading.Thread.__init__(self)
        self._running = True
        self._paused = False
        self.config = config

        self.logging = logging.getLogger("weather-py")
        self.logging.setLevel(birdhouse_loglevel)
        self.logging.addHandler(birdhouse_loghandler)
        self.logging.info("Starting weather process 'python_weather' ...")

        self.weather_location = location
        self.weather_empty = birdhouse_weather.copy()
        self.weather_info = self.weather_empty.copy()
        self.weather_update = 0
        self.weather_update_rhythm = 60 * 60 * 3
        self.weather_raw_data = None

        self.error = False
        self.error_msg = ""
        self.update_interval = self.weather_update_rhythm / 4
        self.update_settings = True
        self.update_wait = 0

        self.link_required = False
        self.link_provider = "<a href='https://pypi.org/project/python-weather/'>Python-Weather</a>"
        self.link_gps_lookup = ""

    def run(self):
        """
        run thread
        """
        last_update = 0
        while self._running:
            if last_update + self.update_interval < time.time() or self.update_settings:
                self.logging.info("Read weather data ...")
                last_update = time.time()
                asyncio.run(self._get_weather())
                if not self.error:
                    self._convert_data()

            self.update_wait = (last_update + self.update_interval) - time.time()
            self.logging.debug("Wait to read weather data (" + str(round(self.update_interval, 1)) + ":" +
                               str(round(self.update_wait, 1)) + "s) ...")
            time.sleep(5)

        self.logging.info("Stopp weather thread.")

    def stop(self):
        """
        stop thread loop
        """
        self._running = False

    @staticmethod
    def _extract_icon(icon_type, icon_object):
        """
        extract icons
        """
        if icon_type != "":
            icon_string = str(icon_object)
            parts = icon_string.split(icon_type + "='")
            if len(parts) > 1:
                parts = parts[1].split("'")
                return parts[0]
            else:
                parts = icon_string.split(icon_type + "=")
                if len(parts) > 1:
                    if " " in parts[1]:
                        parts = parts[1].split(" ")
                        return parts[0]
                    elif ">" in parts[1]:
                        return parts[1].replace(">", "")
                    else:
                        return parts[1]
                else:
                    return "Error extracting icon: " + str(icon_object)

        else:
            return "Error extracting icon: " + str(icon_object)

    async def _get_weather(self):
        """
        get complete weather data set for a specific data
        https://pypi.org/project/python-weather/
        """
        # declare the client. format defaults to the metric system (celcius, km/h, etc.)
        async with python_weather.Client(format=python_weather.METRIC) as client:

            try:
                # fetch a weather forecast from a city
                self.error = False
                self.weather = await client.get(self.weather_location)

            except Exception as e:
                self.error = True
                self.error_msg = "Could not load weather data: " + str(e)
                self.weather_info = self.weather_empty.copy()
                self.weather_info["info_status"]["running"] = "error"
                self.weather_info["info_status"]["error"] = self.error
                self.weather_info["info_status"]["error_msg"] = self.error_msg
                self.weather_info["info_status"]["error_time"] = self.config.local_time().strftime("%d.%m.%Y %H:%M:%S")
                return

    def _convert_data(self):
        """
        convert data to internal format
        """
        self.weather_info = self.weather_empty
        self.weather_info["info_module"] = {
            "name": "Python Weather",
            "provider_link": self.link_provider,
            "provider_link_required": self.link_required
        }
        self.weather_info["info_update"] = self.config.local_time().strftime("%d.%m.%Y %H:%M:%S")
        self.weather_info["info_update_stamp"] = self.config.local_time().strftime("%H%M%S")
        self.weather_info["info_format"] = "metric"
        self.weather_info["info_city"] = self.weather_location
        self.weather_info["info_position"] = self.weather.location
        self.weather_info["info_status"]["running"] = "OK"
        self.weather_info["info_rhythm"] = self.weather_update_rhythm

        current = self.weather.current
        self.weather_info["current"] = {
            "temperature": current.temperature,
            "description": current.description,
            "description_icon": self._extract_icon("type", self.weather.current),
            "wind_speed": current.wind_speed,
            "uv_index": current.uv_index,
            "pressure": current.pressure,
            "humidity": current.humidity,
            "wind_direction": current.wind_direction,
            "precipitation": current.precipitation,
            "time": str(current.local_time.time()),
            "date": str(current.local_time.date())
        }

        self.weather_info["forecast"] = {}

        # get the weather forecast for a few days
        for forecast in self.weather.forecasts:
            info = {
                "sunrise": str(forecast.astronomy.sun_rise),
                "sunset": str(forecast.astronomy.sun_set),
                "moonrise": str(forecast.astronomy.moon_rise),
                "moon_phase": str(forecast.astronomy.moon_phase),
                "moon_phase_icon": self._extract_icon("moon_phase", forecast.astronomy),
                "moon_illumination": str(forecast.astronomy.moon_illumination),
                "hourly": {}
            }
            self.weather_info["forecast"][str(forecast.date)] = info
            for hourly in forecast.hourly:
                hourly_forecast = {
                    "temperature": hourly.temperature,
                    "cloud_cover": hourly.cloud_cover,
                    "description": hourly.description,
                    "description_icon": self._extract_icon("type", hourly),
                    "wind_speed": hourly.wind_speed,
                    "uv_index": hourly.uv_index,
                    "chance_of_sunshine": hourly.chance_of_sunshine,
                    "chance_of_windy": hourly.chance_of_windy,
                    "pressure": hourly.pressure,
                    "wind_direction": hourly.wind_direction,
                    "precipitation": hourly.precipitation
                }
                self.weather_info["forecast"][str(forecast.date)]["hourly"][str(hourly.time)] = hourly_forecast

        today = self.config.local_time().strftime("%Y-%m-%d")
        self.weather_info["forecast"]["today"] = self.weather_info["forecast"][today]

    def get_data(self):
        """
        return weather data from cache
        """
        data = self.weather_info.copy()
        return data


class BirdhouseWeatherOpenMeteo(threading.Thread):

    def __init__(self, config, gps_location, time_zone):
        """
        get weather data using Open Metheo API; API get hourly updated
        * https://open-meteo.com/ (without API key)
        """
        threading.Thread.__init__(self)
        self._running = True
        self._paused = False
        self.config = config

        self.logging = logging.getLogger("weather-om")
        self.logging.setLevel(birdhouse_loglevel)
        self.logging.addHandler(birdhouse_loghandler)
        self.logging.info("Starting weather process 'Open-Metheo.com' for GPS="+str(gps_location)+" ...")

        self.weather_location = gps_location
        self.weather_empty = birdhouse_weather.copy()
        self.weather_info = self.weather_empty.copy()
        self.weather_update = 0
        self.weather_update_rhythm = 60 * 60

        self.error = False
        self.error_msg = ""
        self.update_interval = self.weather_update_rhythm / 4
        self.update_settings = True
        self.update_wait = 0
        self.timezone = time_zone

        self.link_required = True
        self.link_provider = "<a href='https://open-meteo.com/' target='_blank'>Weather by Open-Meteo.com</a>"
        self.link_gps_lookup = "https://open-meteo.com/en/docs"

        self.weather_descriptions = {
            "0": "clear sky",
            "1": "clear",
            "2": "partly cloudy",
            "3": "overcast",
            "45": "fog",
            "48": "depositing rime fog",
            "51": "light drizzle",
            "53": "moderate drizzle",
            "55": "dense intensity drizzle",
            "56": "light freezing drizzle",
            "57": "dense intensity freezing drizzle",
            "61": "slight rain",
            "63": "moderate rain",
            "65": "heavy rain",
            "66": "light freezing rain",
            "67": "heavy freezing rain",
            "71": "slight snow fall",
            "73": "moderate snow fall",
            "75": "heavy snow fall",
            "77": "snow grains",
            "80": "slight rain showers",
            "81": "moderate rain showers",
            "82": "violent rain showers",
            "85": "slight snow showers",
            "86": "heavy snow showers",
            "95": "slight or moderate thunderstorms",
            "96": "thunderstorms with slight hail",
            "99": "thunderstorms with heavy hail"
        }
        self.weather_icons = {
            "0": "☀️",
            "1": "☀️",
            "2": "⛅️",
            "3": "☁️",
            "45": "🌫",
            "48": "🌫",
            "51": "🌦",
            "53": "🌦",
            "55": "🌧",
            "56": "🌨",
            "57": "️❄️",
            "61": "🌦",
            "63": "🌧",
            "65": "🌧",
            "66": "🌨",
            "67": "❄️",
            "71": "🌨",
            "73": "🌨",
            "75": "❄️",
            "77": "❄️",
            "80": "🌦",
            "81": "🌦",
            "82": "🌧",
            "85": "🌨",
            "86": "❄️",
            "95": "🌩",
            "96": "⛈",
            "99": "⛈",
            "100": "✨"
        }

    def run(self):
        """
        regularly request weather data
        """
        last_update = 0
        while self._running:
            if last_update + self.update_interval < time.time() or self.update_settings:
                self.logging.info("Read weather data ...")
                last_update = time.time()
                if self.update_settings:
                    self._create_url()
                    self.update_settings = False
                self._request_data()
                self._convert_data()

            self.update_wait = (last_update + self.update_interval) - time.time()
            self.logging.debug("Wait to read weather data (" + str(round(self.update_interval, 1)) + ":" +
                              str(round(self.update_wait, 1)) + "s) ...")
            time.sleep(5)

        self.logging.info("Stopp weather thread.")

    def stop(self):
        """
        stop thread loop
        """
        self._running = False

    def _weather_descriptions(self, weather_code):
        """
        check if weather code exists and return description
        """
        if str(weather_code) in self.weather_descriptions:
            return self.weather_descriptions[str(weather_code)]
        else:
            return "unknown weather code ("+str(weather_code)+")"

    def _weather_icons(self, weather_code):
        """
        check if weather code exists and return icon
        """
        if str(weather_code) in self.weather_icons:
            return self.weather_icons[str(weather_code)]
        else:
            return self.weather_icons[str(100)]

    def _create_url(self):
        """
        create API url
        """
        url = "https://api.open-meteo.com/v1/forecast?"
        url += "latitude=" + str(self.weather_location[0]) + "&longitude=" + str(self.weather_location[1])
        url += "&timezone=auto"
        url += "&current_weather=true"
        url += "&hourly=temperature_2m,relativehumidity_2m,windspeed_10m,weathercode"
        url += "&daily=sunset,sunrise"
        self.weather_api = url

    def _request_data(self):
        """
        request weather data from API
        """
        try:
            data = requests.get(url=self.weather_api, timeout=5)
            self.weather_raw_data = data.json()
            self.weather_update = self.config.local_time()
            self.error = False
        except Exception as e:
            self.error = True
            self.error_msg = "Could not read weather from open-metheo.com: "+str(e)
            self.logging.warning(self.error_msg)

    def _convert_data(self):
        """
        convert data to own format (see birdhouse_weather in presets.py)
        """
        self.weather_info["info_module"] = {
            "name": "Open Metheo",
            "provider_link": self.link_provider,
            "provider_link_required": self.link_required,
            "gps_lookup": self.link_gps_lookup
        }
        self.weather_info["info_module_link"] = self.link_provider
        self.weather_info["info_module_link_required"] = self.link_required
        self.weather_info["info_format"] = "metric"
        self.weather_info["info_status"] = {
            "running": self._running,
            "paused": self._paused,
            "error": self.error,
            "error_msg": self.error_msg
        }
        self.weather_info["info_update"] = self.weather_update.strftime("%d.%m.%Y %H:%M:%S")
        self.weather_info["info_update_stamp"] = self.weather_update.strftime("%H%M%S")
        self.weather_info["info_position"] = self.weather_location
        self.weather_info["info_rhythm"] = self.weather_update_rhythm
        self.weather_info["info_units"] = {
            "temperature": self.weather_raw_data["hourly_units"]["temperature_2m"],
            "humidity": self.weather_raw_data["hourly_units"]["relativehumidity_2m"],
            "wind_speed": self.weather_raw_data["hourly_units"]["windspeed_10m"]
        }

        self.weather_info["current"] = self.weather_raw_data["current_weather"]
        self.weather_info["current"]["wind_speed"] = self.weather_info["current"]["windspeed"]
        self.weather_info["current"]["description"] = self._weather_descriptions(self.weather_raw_data["current_weather"]["weathercode"])
        self.weather_info["current"]["description_icon"] = self._weather_icons(self.weather_raw_data["current_weather"]["weathercode"])

        today_stamp = self.weather_update.strftime("%Y-%m-%d")
        hourly_data_raw = self.weather_raw_data["hourly"]
        daily_data_raw = self.weather_raw_data["daily"]
        hourly_data = {}
        count = 0
        for key in hourly_data_raw["time"]:
            stamp_date, stamp_time = key.split("T")
            if count == 0:
                today_stamp = stamp_date
            if stamp_date not in hourly_data:
                hourly_data[stamp_date] = {}
                hourly_data[stamp_date]["hourly"] = {}
            hourly_data[stamp_date]["hourly"][stamp_time] = {
                "temperature": hourly_data_raw["temperature_2m"][count],
                "wind_speed": hourly_data_raw["windspeed_10m"][count],
                "humidity": hourly_data_raw["relativehumidity_2m"][count],
                "description": self._weather_descriptions(hourly_data_raw["weathercode"][count]),
                "description_icon": self._weather_icons(hourly_data_raw["weathercode"][count])
            }
            count += 1
        hourly_data["today"] = hourly_data[today_stamp]
        hourly_data["today"]["sunrise"] = daily_data_raw["sunrise"][0].split("T")[1]
        hourly_data["today"]["sunset"] = daily_data_raw["sunset"][0].split("T")[1]

        self.weather_info["forecast"] = hourly_data

        current_date = self.weather_info["current"]["time"].split("T")[0]
        current_time = self.weather_info["current"]["time"].split("T")[1]
        self.weather_info["current"]["time"] = current_time
        self.weather_info["current"]["date"] = current_date
        self.weather_info["current"]["humidity"] = self.weather_info["forecast"][current_date]["hourly"][current_time]["humidity"]

    def set_location(self, settings):
        """
        settings for weather
        """
        self.weather_location = settings["gps_location"]
        self.update_settings = True

    def get_data(self):
        """
        return weather data from cache
        """
        if not self.error:
            data = self.weather_info.copy()
            return data
        else:
            return {"error": self.error, "error_msg": self.error_msg}


class BirdhouseWeather(threading.Thread):

    def __init__(self, config, time_zone=0):
        """
        start weather and sunrise function
        # https://pypi.org/project/python-weather/
        """
        threading.Thread.__init__(self)
        self._running = True
        self._paused = False
        self.config = config
        self.initial_date = self.config.local_time().strftime("%Y%m%d")

        self.logging = logging.getLogger("weather")
        self.logging.setLevel(birdhouse_loglevel)
        self.logging.addHandler(birdhouse_loghandler)
        self.logging.info("Starting weather process ...")

        self.error = False
        self.error_msg = ""

        self.weather = None
        self.weather_source = None
        self.weather_city = None
        self.weather_gps = None
        self.weather_info = {}
        self.weather_active = True
        self.weather_empty = birdhouse_weather.copy()
        self.weather_info = self.weather_empty.copy()
        self.weather_info["info_status"]["running"] = "started"

        self.update = False
        self.update_time = 60 * 15
        self.update_wait = 0

        self.timezone = time_zone
        self.module = None
        self.gps = BirdhouseGPS()
        self.connect(self.config.param["weather"])

    def run(self):
        """
        continuously request fresh data once a minute
        """
        self.logging.info("Starting Weather module ...")
        time.sleep(5)
        last_update = 0
        while self._running:

            # if shutdown
            if self.config.shut_down:
                self.stop()

            # if config update or new day
            self.error = False
            if self.update or self.initial_date != self.config.local_time().strftime("%Y%m%d"):
                self.update = False
                self.connect(self.config.param["weather"])
                self.initial_date = self.config.local_time().strftime("%Y%m%d")

            # if paused
            if self._paused:
                self.weather_info = self.weather_empty.copy()
                self.weather_info["info_status"]["running"] = "paused"
                last_update = 0

            # last update has been a while
            elif last_update + self.update_time < time.time():
                self.logging.info("Read weather data ...")
                last_update = time.time()
                self.weather_info = self.module.get_data()
                # asyncio.run(self.get_weather())
                if not self.error:
                    self.weather_info["info_status"]["running"] = "OK"

            if "current" not in self.weather_info:
                self.error = True
                self.weather_info = self.weather_empty.copy()

            if self.error:
                self.weather_info["info_status"]["running"] = "error"

            if "info_status" in self.weather_info and "running" in self.weather_info["info_status"] \
                    and self.weather_info["info_status"]["running"] == "error":
                time.sleep(10)

            self.update_wait = (last_update + self.update_time) - time.time()
            self.logging.debug("Wait to read weather data (" + str(round(self.update_time, 1)) + ":" +
                               str(round(self.update_wait, 1)) + "s) ...")
            time.sleep(5)

    def stop(self):
        """
        stop weather loop
        """
        self._running = False
        self.module.stop()

    def active(self, active):
        """
        set if active or inactive (used via config.py)
        """
        self.weather_active = active
        if active:
            self._paused = False
        else:
            self._paused = True

    def connect(self, param):
        """
        (re)connect to weather module
        """
        self.weather_source = param["source"]
        self.logging.info("(Re)connect weather module (source="+self.weather_source+")")
        update_gps = False
        if self.update:
            update_gps = True

        if self.weather_source == "Open-Metheo":
            self.weather_city = param["location"]
            if "gps_location" in param and param["gps_location"] != [0, 0] and len(param["gps_location"]) >= 2 \
                    and not update_gps:
                self.weather_gps = param["gps_location"]
            else:
                self.weather_gps = self.gps.look_up_location(self.weather_city)
            self.module = BirdhouseWeatherOpenMeteo(config=self.config,
                                                    gps_location=self.weather_gps,
                                                    time_zone=self.timezone)
            self.module.start()

        else:
            self.weather_city = param["location"]
            if "gps_location" in param and param["gps_location"] != [0, 0] and len(param["gps_location"]) == 2 \
                    and not update_gps:
                self.weather_gps = param["gps_location"]
            else:
                self.weather_gps = self.gps.look_up_location(self.weather_city)
            self.module = BirdhouseWeatherPython(config=self.config,
                                                 location=self.weather_city,
                                                 time_zone=self.timezone)
            self.module.start()

    def get_gps_info(self, param):
        """
        lookup GPS information to be saved in the main configuration
        """
        self.weather_city = param["location"]
        self.weather_gps = self.gps.look_up_location(self.weather_city)
        if self.weather_gps[0] != 0 and self.weather_gps[1] != 0:
            param["gps_location"] = self.weather_gps
            self.logging.info("Found GPS: '" + str(self.weather_gps) + "'.")
        return param

    def get_weather_info(self, info_type="all"):
        """
        return information with different level of detail
        """
        if "current" not in self.weather_info:
            self.error = True
            self.error_msg = "Weather data not correct (get_weather_info)"
            self.logging.error(self.error_msg)
            self.logging.error(str(self.weather_info))
            self.weather_info = self.weather_empty.copy()

        if info_type == "status":
            status = self.weather_info["info_status"].copy()
            status["gps_coordinates"] = self.weather_gps
            status["gps_location"] = self.weather_city
            return status

        if info_type == "current_small":
            weather_data = self.weather_info["current"]
            if "humidity" not in weather_data:
                weather_data["humidity"] = ""
            info = {
                "description_icon": weather_data["description_icon"],
                "description": weather_data["description"],
                "temperature": weather_data["temperature"],
                "humidity": weather_data["humidity"],
                # "pressure": weather_data["pressure"],
                "wind": weather_data["wind_speed"]
            }
            return info

        elif info_type == "current":
            return self.weather_info["current"]

        return self.weather_info
