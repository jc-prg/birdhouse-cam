//--------------------------------------
// jc://birdhouse/weather
//--------------------------------------


/*
* create view with weather information: current weather, weather for the next three days, and if admin weather for 7 days
*/
class BirdhouseWeather {
    constructor(name) {
        this.name = name;
        this.tab = new birdhouse_table();
    }

    /*
    * create view with weather information: current weather, weather for the next three days, and if admin weather for 7 days
    *
    * @param (dict) data: data returned form server API for this view
    */
    create (data) {
        let settings        = app_data["SETTINGS"];
        let status          = app_data["STATUS"];
        let weather	        = data["WEATHER"];

        if (settings["localization"]["weather_active"] === false) {
            setTextById(app_frame.content, "&nbsp;<br/><center>" + lang("NO_WEATHER_CHANGE_SETTINGS") + "</center><br/>&nbsp;");
            return;
        }
        if (!weather["forecast"] || !weather["current"] || !weather["forecast"]["today"] || weather["info_status"]["running"] === "error") {
            setTextById(app_frame.content, "&nbsp;<br/><center><font color='red'><b>" + lang("WEATHER_DATA_ERROR") + "</b></font></center><br/>&nbsp;");
            console.warn("Error with weather data!")
            console.warn(weather);
            return;
        }

        this.tab.style_rows["height"] = "18px";

        let weather_today = weather["current"];
        let weather_3day  = weather["forecast"];
        let html_weather = "";
        let html_temp = "";
        let current_icon;

        if (weather_today["weathercode"]) {
            current_icon = "<center><font style='font-size:80px;'><big>" + weather_today["description_icon"] + "</big></font>"
                + "<br/>" + lang("WEATHER_" + weather_today["weathercode"]) + "</center>";
        } else {
            current_icon = "<center><font style='font-size:80px;'><big>" + weather_today["description_icon"] + "</big></font>"
                + "<br/>" + weather_today["description"] + "</center>";
        }
        let current_weather = this.tab.start();
        if (weather["info_position"].length <= 2) {
            current_weather += this.tab.row(lang("LOCATION") + ":",  settings["devices"]["weather"]["gps_location"]);
        } else {
            current_weather += this.tab.row(lang("GPS_LOCATION")+":", weather["info_position"][2]);
        }
        current_weather += this.tab.row(lang("GPS_POSITION")+":", "("+weather["info_position"][0]+", "+weather["info_position"][1]+")");
        current_weather += this.tab.row(lang("SUNRISE") +":",    weather_3day["today"]["sunrise"]);
        current_weather += this.tab.row(lang("SUNSET")+":",      weather_3day["today"]["sunset"]);
        current_weather += this.tab.row(lang("TEMPERATURE")+":", weather_today["temperature"] +"°C");
        current_weather += this.tab.row(lang("HUMIDITY")+":",    weather_today["humidity"] +"%");
        current_weather += this.tab.row(lang("WIND")+":",        weather_today["wind_speed"] + " km/h");
        current_weather += this.tab.row(lang("STATUS")+":",      weather_today["date"] + " " + weather_today["time"]);
        if (weather["info_module"]["provider_link_required"]) {
            current_weather += this.tab.row(lang("SOURCE")+":",  weather["info_module"]["provider_link"]);
        }
        current_weather += this.tab.end();

        html_temp  = this.tab.start();
        html_temp += this.tab.row(current_icon, current_weather);
        html_temp += this.tab.end();
        html_weather += "&nbsp;<br/>" + html_temp + "<br/>&nbsp;";
        let html = "";

        let d = new Date();
        let current_year   = d.getFullYear();
        let current_month  = d.getMonth()+1;
        let current_day    = d.getDate();
        let current_hour   = d.getHours();

        let last_day       = "";
        let day_count      = 0;
        let chart_data     = {
            "titles" : [lang("TEMPERATURE") + " [°C]", lang("HUMIDITY") + " [%]", lang("WIND") + " [km/h]"],
            "data"   : {}
        }
        let weather_data = {}

        Object.keys(weather_3day).forEach(key=>{ if (key !== "today") {
            let forecast_day = weather_3day[key];
            let forecast_year, forecast_month, forecast_day2;
            let forecast_html = "<br/>&nbsp;<hr style='width:95%;'/>";
            let today = false;
            let forecast_entries = 0;
            [forecast_year, forecast_month, forecast_day2] = key.split("-");
            if ((forecast_year*1) === (current_year*1) && (forecast_month*1) === (current_month*1) && (forecast_day2*1) === (current_day*1)) { today = true; }
            day_count += 1;

            Object.keys(forecast_day["hourly"]).forEach(key2=>{
                let key_hour = key2.split(":")[0];
                let key_minute = key2.split(":")[1];
                let forecast_hour = forecast_day["hourly"][key2];

                if (day_count <= 3) {
                    let chart_key = key.split("-")[2] + "." + key.split("-")[1] + " " + key2;
                    if (key !== last_day) { chart_data["data"][chart_key] = [undefined, undefined, undefined]; last_day = key; }
                    if (key2 === "00:00") { chart_key = chart_key.replace("00:00", "00:01"); }
                    chart_data["data"][chart_key] = [forecast_hour["temperature"], forecast_hour["humidity"], forecast_hour["wind_speed"]];

                    if (key_hour.split(":")[0] > 6) {
                        if (!weather_data[key]) { weather_data[key] = {}; }
                        forecast_hour["key"] = key2;
                        weather_data[key][key2] = forecast_hour;
                    }
                }

                if (!today || (current_hour*1) < (key_hour*1)) {
                    let current_icon = "<center><font  style='font-size:40px;'>" + forecast_hour["description_icon"] + "</font></center>";
                    let current_weather = this.tab.start();

                    current_weather += this.tab.row(lang("TEMPERATURE")+":", forecast_hour["temperature"] +"°C");
                    current_weather += this.tab.row(lang("HUMIDITY")+":",    forecast_hour["humidity"] +"%");
                    current_weather += this.tab.row(lang("WIND")+":",        forecast_hour["wind_speed"] + " km/h");
                    // current_weather += tab.row(lang("PRESSURE")+":",    forecast_hour["pressure"] + " hPa");
                    current_weather += this.tab.end();

                    html_temp = "<div style='width:100%;text-align:right;'><b>"+key_hour+":"+key_minute+"</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div><hr style='width:95%;'/>";
                    html_temp += this.tab.start();
                    html_temp += this.tab.row(current_icon, current_weather);
                    html_temp += this.tab.end();
                    html_temp += "<hr style='width:95%;'/>";

                    forecast_html += html_temp;
                    forecast_entries += 1;
                }
            });
            if (forecast_entries > 0) {
                let title = "";
                if (today) { title = key + "&nbsp;-&nbsp;" + lang("TODAY"); }
                else       { title = key; }
                html += birdhouse_OtherGroup( "weather_forecast_"+key, title, forecast_html, false );
            }
        }});

        html_weather += "<br/>&nbsp;<br/>";

        //console.error(chart_data);
        //console.error(weather_data);

        let chart     = "&nbsp;<br/>";
        chart        += birdhouseChart_create("", chart_data["titles"],chart_data["data"]);
        chart        += "<br/>&nbsp;<br/>";

        Object.keys(weather_data).forEach(date=>{
            chart   += "<div class='weather-3day-overview'>";
            chart   += "<b>" + date + "</b><br/>";
            chart   += "<center>" + this.overviewChart(weather_data[date], "key", false) + "</center>" ;
            chart   += "</div>";
        });

        chart        += "<br/>&nbsp;<br/>";
        html_weather += birdhouse_OtherGroup( "chart", lang("WEATHER") + " (3 " + lang("DAYS") + ")", chart, true );
        if (app_admin_allowed) {
            html_weather += html;
        }

        let title = "<div id='status_error_WEATHER' style='float:left'><div id='black'></div></div>";
        title += "<center><h2>" + lang("WEATHER") + "&nbsp;&nbsp;&nbsp;&nbsp;</h2></center>";
        setTextById(app_frame.header, title);
        setTextById(app_frame.content, html_weather);
    }

    /*
    * create a three days weather overview chart
    *
    * @param (dict) entries: weather entries from server API
    * @param (string) title_key: title key
    * @param (boolean) title_column: show title above the chart
    */
    overviewChart (entries, title_key="time", title_column=true) {
        let html = "";
        let count = 0;
        let weather_data = {};

        Object.keys(entries).forEach( key => {
            weather_data[entries[key][title_key]] = entries[key]["description_icon"];
            /*
            if (key.substring(2,4) == "00" && entries[key]["weather"]) {
                weather_data[key.substring(0,2)+":"+key.substring(2,4)] = entries[key]["weather"]["description_icon"];
            }
            */
        });

        // width -> 8 if small; 16 if middle; 24 if big

        let html_row1, html_row2;
        if (title_column) {
            html_row1 = "<td></td>";
            html_row2 = "<td>"+lang("WEATHER")+": &nbsp;</td>";
        }
        else {
            html_row1 = "";
            html_row2 = "";
        }
        Object.keys(weather_data).sort().forEach(key => {
            let td_class = "weather_hide_if_small";
            if (Math.abs(count % 2) !== 0 || Object.keys(weather_data).length <= 8) {
                td_class = "weather_show";
            }
            if (count < 16) {
                html_row1 += "<td class='"+td_class+"'>"+key+"<td>";
                html_row2 += "<td class='"+td_class+"' style='font-size:14px;'><center>"+weather_data[key]+"<center><td>";
            }
            count += 1;
        });
        if (count === 0) { return ""; }
        html += "<hr/><table border='0'>";
        html += "<tr style='font-size:8px;'>" + html_row1 + "</tr>";
        html += "<tr style='font-size:11px;'>" + html_row2 + "</tr>";
        html +="</table>"
        console.debug(weather_data);
        //html += "&nbsp;<br/>&nbsp;";
        return html;
    }
}


const bhWeather = new BirdhouseWeather("bhWeather");


app_scripts_loaded += 1;