import threading
import datetime
import python_weather
import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
import time
import logging


class BirdhouseWeather(threading.Thread):

    def __init__(self, city, time_zone=0):
        """
        start weather and sunrise function
        # https://pypi.org/project/python-weather/
        """
        threading.Thread.__init__(self)
        logging.info("Starting weather process ...")

        self._running = True
        self._paused = False

        self.error = False
        self.error_msg = ""

        self.weather = None
        self.weather_city = city
        self.weather_info = {}
        self.update_time = 60 * 5
        self.timezone = time_zone
        self.weather_empty = {
            "info_update": "none",
            "info_city": "",
            "info_format": "",
            "info_position": "",
            "info_status": {},
            "current": {
                "temperature": None,
                "description": "",
                "description_icon": "",
                "wind_speed": None,
                "uv_index": None,
                "pressure": None,
                "humidity": None,
                "wind_direction": "",
                "precipitation": None
            },
            "forecast": {
                "today": {}
            }
        }

    def run(self):
        """
        continuously request fresh data once a minute
        """
        logging.info("Starting Weather module ...")
        while self._running:
            if not self._paused:
                asyncio.run(self.get_weather())
            else:
                info = self.weather_empty.copy()
                info["info_status"]["running"] = "paused"
                self.weather_info = info.copy()

            if self.weather_info["info_status"]["running"] == "error":
                time.sleep(10)
            else:
                time.sleep(self.update_time)

    @staticmethod
    def _extract(icon_type, icon_object):
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

    def _local_time(self):
        """
        return time that includes the current timezone
        """
        date_tz_info = timezone(timedelta(hours=self.timezone))
        return datetime.now(date_tz_info)

    def active(self, active):
        """
        set if active or inactive
        """
        if active:
            self._paused = False
        else:
            self._paused = True

    async def get_weather(self):
        """
        get complete weather data set for a specific data
        https://pypi.org/project/python-weather/
        """
        # declare the client. format defaults to the metric system (celcius, km/h, etc.)
        async with python_weather.Client(format=python_weather.METRIC) as client:

            try:
                # fetch a weather forecast from a city
                self.error = False
                self.weather = await client.get(self.weather_city)

            except Exception as e:
                self.error = True
                self.error_msg = "Could not load weather data: " + str(e)
                self.weather_info = self.weather_empty
                self.weather_info["info_status"]["running"] = "error"
                self.weather_info["info_status"]["error"] = self.error
                self.weather_info["info_status"]["error_msg"] = self.error_msg
                self.weather_info["info_status"]["error_time"] = self._local_time().strftime("%d.%m.%Y %H:%M:%S")
                return

            self.weather_info = self.weather_empty
            self.weather_info["info_update"] = self._local_time().strftime("%d.%m.%Y %H:%M:%S")
            self.weather_info["info_update_stamp"] = self._local_time().strftime("%H%M%S")
            self.weather_info["info_format"] = "metric"
            self.weather_info["info_city"] = self.weather_city
            self.weather_info["info_position"] = self.weather.location
            self.weather_info["info_status"]["running"] = "OK"

            current = self.weather.current
            self.weather_info["current"] = {
                "temperature": current.temperature,
                "description": current.description,
                "description_icon": self._extract("type", self.weather.current),
                "wind_speed": current.wind_speed,
                "uv_index": current.uv_index,
                "pressure": current.pressure,
                "humidity": current.humidity,
                "wind_direction": current.wind_direction,
                "precipitation": current.precipitation

            }
            self.weather_info["forecast"] = {}

            # get the weather forecast for a few days
            for forecast in self.weather.forecasts:
                info = {
                    "sunrise": str(forecast.astronomy.sun_rise),
                    "sunset": str(forecast.astronomy.sun_set),
                    "moonrise": str(forecast.astronomy.moon_rise),
                    "moon_phase": str(forecast.astronomy.moon_phase),
                    "moon_phase_icon": self._extract("moon_phase", forecast.astronomy),
                    "moon_illumination": str(forecast.astronomy.moon_illumination),
                    "hourly": {}
                }
                self.weather_info["forecast"][str(forecast.date)] = info
                for hourly in forecast.hourly:
                    hourly_forecast = {
                        "temperature": hourly.temperature,
                        "cloud_cover": hourly.cloud_cover,
                        "description": hourly.description,
                        "description_icon": self._extract("type", hourly),
                        "wind_speed": hourly.wind_speed,
                        "uv_index": hourly.uv_index,
                        "chance_of_sunshine": hourly.chance_of_sunshine,
                        "chance_of_windy": hourly.chance_of_windy,
                        "pressure": hourly.pressure,
                        "wind_direction": hourly.wind_direction,
                        "precipitation": hourly.precipitation
                    }
                    self.weather_info["forecast"][str(forecast.date)]["hourly"][str(hourly.time)] = hourly_forecast

            today = self._local_time().strftime("%Y-%m-%d")
            self.weather_info["forecast"]["today"] = self.weather_info["forecast"][today]

    def get_weather_info(self, info_type="all"):
        """
        return information with different level of detail
        """
        if info_type == "current_small":
            weather_data = self.weather_info["current"]
            info = {
                "description_icon": weather_data["description_icon"],
                "description": weather_data["description"],
                "temperature": weather_data["temperature"],
                "humidity": weather_data["humidity"],
                "pressure": weather_data["pressure"],
                "wind": weather_data["wind_speed"]
            }
            return info
        elif info_type == "current":
            return self.weather_info["current"]
        return self.weather_info
