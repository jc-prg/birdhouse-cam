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
        self.thread_set_priority(6)

        self._usage_time = time.time()
        self._usage_interval = 60
        self._write_interval = 4 * 60

        self._statistics = {}
        self._statistics_array = {}
        self._statistics_info = {}
        self._statistics_default = {
            "info": {},
            "data": {}
        }
        self._statistics_3days = {}
        self._running = True

    def run(self):
        """
        Starting thread
        """
        self.logging.info("Starting statistic handler ("+self.config.local_time().strftime('%H:%M')+"|"+str(self._write_interval)+"s) ...")

        while self._running:

            if time.time() - self._usage_time > self._write_interval:
                self.logging.debug("... write statistics in next "+str(time.time() - self._usage_time)+"s > "+str(self._write_interval)+"s ...")
                self._usage_time = time.time()
                self.write_statistics()

            self.thread_control()
            self.thread_wait()

        self.logging.info("Stopped statistic handler.")

    def write_statistics(self):
        """
        write statistic data to database depending on self._write_interval.
        """
        save_stamp = self.config.local_time().strftime('%H:%M')
        #save_time = self.config.local_time().strftime('%d.%m.%Y %H:%M:%S')

        statistics = self.config.db_handler.read(config="statistics")
        if statistics == {} or "data" not in statistics or "info" not in statistics:
            self.config.db_handler.write(config="statistics", date="", data=self._statistics_default, create=True,
                                         save_json=True)

        save_statistic = {}
        for key in self._statistics_array:
            if "_" in key:
                parts = key.split("_")
                key2 = parts[0]
                key3 = key.replace(key2 + "_", "")
                if key2 not in save_statistic:
                    save_statistic[key2] = {}

                #save_statistic[key2][key3] = self._statistics[key]
                save_statistic[key2][key3] = sum(self._statistics_array[key]) / len(self._statistics_array[key])
                self._statistics_array[key] = []
            else:
                #save_statistic[key] = self._statistics[key]
                save_statistic[key] = sum(self._statistics_array[key]) / len(self._statistics_array[key])
                self._statistics_array[key] = []

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

        if len(self._statistics_array) > 0:
            self.logging.info("Add statistic data ("+str(len(self._statistics_array))+") to queue ...")

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
        if key not in self._statistics_array:
            self._statistics_array[key] = []
        self._statistics_array[key].append(value)

    def get_chart_data(self, categories, date="", values=False):
        """
        Create chart input data for statistics view

        Args:
            categories (list): statistics category (srv, cam1, cam2)
            date (str): date (default="" for today)
            values (bool): devices (default) or values
        Returns:
             dict[str, Any]: data formatted for chart.js
        """
        chart = {}
        db_name = "statistics"
        if date != "":
            db_name = "statistics_archive"
        chart_data = self.config.db_handler.read_cache(db_name, date)
        chart_value = {}
        chart_values = {"data": {}, "info": {}}

        values = True
        # reformat values if requested
        if values and "info" in chart_data and "data" in chart_data:
            for key in chart_data["info"]:
                for value in chart_data["info"][key]:
                    if "error" == value:
                        chart_value["error:" + key] = key + ":" + value
                    elif "raw_error" == value:
                        chart_value["error:raw-" + key] = key + ":" + value
                    elif "_" in value:
                        cat = value.split("_")[0]
                        val = value.replace(cat + "_", "")
                        chart_value[cat + ":" + val + "-" + key] = key + ":" + value
                    else:
                        chart_value[value + ":" + key] = key + ":" + value

            for key in chart_value:
                k_cat, k_val = key.split(":")
                v_cat, v_val = chart_value[key].split(":")
                if k_cat not in chart_values["info"]:
                    chart_values["info"][k_cat] = {}
                chart_values["info"][k_cat][k_val] = chart_data["info"][v_cat][v_val]

            for stamp in chart_data["data"]:
                chart_values["data"][stamp] = {}
                for key in chart_value:
                    k_cat, k_val = key.split(":")
                    v_cat, v_val = chart_value[key].split(":")
                    if k_cat not in chart_values["data"][stamp]:
                        chart_values["data"][stamp][k_cat] = {}
                    if v_cat in chart_data["data"][stamp] and v_val in chart_data["data"][stamp][v_cat]:
                        chart_values["data"][stamp][k_cat][k_val] = chart_data["data"][stamp][v_cat][v_val]
        else:
            return {}

        # create chart data
        if len(categories) == 0:
            categories = list(chart_values["info"].keys())
            chart_data = chart_values

        for category in categories:
            chart[category] = {"titles": [], "data": {}}

            if category not in chart_data["info"]:
                chart[category]["error"] = "category '" + category + "' not found in statistic data."

            else:
                titles = list(chart_data["info"][category].keys())
                chart[category]["titles"] = list(chart_data["info"][category].values())
                for stamp in chart_data["data"]:
                    values = []
                    for key in titles:
                        if category in chart_data["data"][stamp]:
                            if key in chart_data["data"][stamp][category]:
                                values.append(chart_data["data"][stamp][category][key])
                            else:
                                values.append(key)
                    chart[category]["data"][stamp] = values

                if category == "streams":
                    chart[category]["info"] = {"max": 0, "views": 0}
                    for stamp in chart[category]["data"]:
                        for value in chart[category]["data"][stamp]:
                            if "int" in str(type(value)):
                                if value > chart[category]["info"]["max"]:
                                    chart[category]["info"]["max"] = value
                                chart[category]["info"]["views"] += value

        return chart

    def get_chart_data_view(self):
        """
        create chart data for statistics view in the app for today, yesterday, 3days

        Returns:
            dict: chart data for statistics view to be used with chart.js
        """
        today = self.config.local_date()
        yesterday = self.config.local_date(days=1)
        day_minus_2days = self.config.local_date(days=2)
        day_minus_3days = self.config.local_date(days=3)
        day_minus_4days = self.config.local_date(days=4)
        day_minus_5days = self.config.local_date(days=5)
        days_3 = [day_minus_3days, day_minus_2days, yesterday]
        days_5 = [day_minus_5days, day_minus_4days, day_minus_3days, day_minus_2days, yesterday]
        chart = {
            "today" : self.get_chart_data([]),
            "yesterday": self.get_chart_data([], yesterday),
            "3days": self._statistics_3days
        }
        if chart["3days"] == {}:

            for key in days_3:
                short_date = key[6:8]+"."+key[4:6]+"."
                day_data = self.get_chart_data([], key)

                for category in day_data:
                    if category not in chart["3days"]:
                        chart["3days"][category] = {}
                        chart["3days"][category]["data"] = {}
                    chart["3days"][category]["titles"] = day_data[category]["titles"]

                    for stamp in day_data[category]["data"]:
                        chart["3days"][category]["data"][short_date + " " + stamp] = day_data[category]["data"][stamp]

            self._statistics_3days = chart["3days"]

        return chart
