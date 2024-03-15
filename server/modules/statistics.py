import threading
import time

from modules.bh_class import BirdhouseClass


class BirdhouseStatistics(threading.Thread, BirdhouseClass):
    """
    Class to record data for statistic: usage data, server data, ...
    """

    def __init__(self, config):
        """
        Constructor to initialize class.

        Args:
             config (modules.config.BirdhouseConfig): reference to main configuration handler
        """
        threading.Thread.__init__(self)
        BirdhouseClass.__init__(self, class_id="statistic", config=config)
        self.thread_set_priority(3)

        self._usage_time = time.time() - 60
        self._usage_interval = 60
        self._statistics = {}
        self._statistics_info = {}
        self._statistics_default = {
            "info": {},
            "data": {}
        }
        self._running = True

    def run(self):
        """
        Starting thread
        """
        self.logging.info("Starting statistic handler ...")

        while self._running:
            self.write_statistics()
            self.thread_control()
            self.thread_wait()

        self.logging.info("Stopped statistic handler.")

    def write_statistics(self):
        """
        write statistic data to database
        """
        if time.time() - self._usage_time > self._usage_interval:
            self.logging.info("Write statistic data ...")

            self._usage_time = time.time()
            save_stamp = self.config.local_time().strftime('%H:%M')
            save_time = self.config.local_time().strftime('%d.%m.%Y %H:%M:%S')

            statistics = self.config.db_handler.read(config="statistics")
            if statistics == {} or "data" not in statistics or "info" not in statistics:
                self.config.db_handler.write(config="statistics", date="", data=self._statistics_default, create=True,
                                             save_json=True)

            save_statistic = {}
            for key in self._statistics:
                if "_" in key:
                    parts = key.split("_")
                    key2 = parts[0]
                    key3 = key.replace(key2 + "_", "")
                    if key2 not in save_statistic:
                        save_statistic[key2] = {}
                    save_statistic[key2][key3] = self._statistics[key]
                else:
                    save_statistic[key] = self._statistics[key]

            save_statistic_info = {}
            for key in self._statistics_info:
                if "_" in key:
                    parts = key.split("_")
                    key2 = parts[0]
                    key3 = key.replace(key2 + "_", "")
                    if key2 not in save_statistic_info:
                        save_statistic_info[key2] = {}
                    save_statistic_info[key2][key3] = self._statistics_info[key]
                else:
                    save_statistic_info[key] = self._statistics_info[key]

            if len(self._statistics) > 0:
                self.config.queue.entry_other(config="statistics", date="", key=save_stamp,
                                              entry=save_statistic_info.copy(), command="info")
                self.config.queue.entry_add(config="statistics", date="", key=save_stamp,
                                            entry=save_statistic.copy())

    def register(self, key, description):
        """
        Register keys incl. description for statistics

        Args:
            key (str): statistic key
            description (str): description to be used in charts
        """
        self._statistics_info[key] = description

    def set(self, key, value):
        """
        Set key and value to be saved in next iteration

        Args:
            key (str): statistic key
            value (Any): statistic value
        """
        self._statistics[key] = value

    def get_chart_data(self, category, date=""):
        """
        Create chart input data for statistics view

        Args:
            category (str): statistics category (srv, cam1, cam2)
            date (str): date (default="" for today)
        Returns:
             dict[str, Any]: data formatted for chart.js
        """
        chart = {"data": {}, "titles": []}
        chart_data = self.config.db_handler.read_cache("statistics")

        if category not in chart_data["info"]:
            chart["error"] = "category '" + category + "' not found in statistic data."

        else:
            titles = list(chart_data["info"][category].keys())
            chart["titles"] = list(chart_data["info"][category].values())
            for stamp in chart_data["data"]:
                values = []
                for key in titles:
                    if key in chart_data["data"][stamp][category]:
                        values.append(chart_data["data"][stamp][category][key])
                    else:
                        values.append(key)
                chart["data"][stamp] = values

        return chart
