//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// weather view
//--------------------------------------


/*
* create view with weather information: current weather, weather for the next three days, and if admin weather for 7 days
*
* @param (dict) data: data returned form server API for this view
*/
function birdhouseWeather( data ) {
    var settings        = app_data["SETTINGS"];
    var admin_allowed   = app_data["STATUS"]["admin_allowed"];
    var status          = app_data["STATUS"];
	var weather	        = data["WEATHER"];

    if (settings["localization"]["weather_active"] == false) {
        setTextById(app_frame_content, "&nbsp;<br/><center>" + lang("NO_WEATHER_CHANGE_SETTINGS") + "</center><br/>&nbsp;");
        return;
    }
    if (!weather["forecast"] || !weather["current"] || !weather["forecast"]["today"] || weather["info_status"]["running"] == "error") {
        setTextById(app_frame_content, "&nbsp;<br/><center><font color='red'><b>" + lang("WEATHER_DATA_ERROR") + "</b></font></center><br/>&nbsp;");
        console.warn("Error with weather data!")
        console.warn(weather);
        return;
    }

	var tab     = new birdhouse_table();
	tab.style_rows["height"] = "18px";

	var weather_today = weather["current"];
	var weather_3day  = weather["forecast"];
    var html_weather = "";
    var html_temp = "";
    var html_entry = "";

    if (weather_today["weathercode"]) {
        var current_icon = "<center><font style='font-size:80px;'><big>" + weather_today["description_icon"] + "</big></font>"
                           + "<br/>" + lang("WEATHER_" + weather_today["weathercode"]) + "</center>";
    }
    else {
        var current_icon = "<center><font style='font-size:80px;'><big>" + weather_today["description_icon"] + "</big></font>"
                           + "<br/>" + weather_today["description"] + "</center>";
    }
    var current_weather = tab.start();
    if (weather["info_position"].length <= 2) {
        current_weather += tab.row(lang("LOCATION") + ":",  settings["devices"]["weather"]["gps_location"]);
        }
    else {
        current_weather += tab.row(lang("GPS_LOCATION")+":", weather["info_position"][2]);
        }
    current_weather += tab.row(lang("GPS_POSITION")+":", "("+weather["info_position"][0]+", "+weather["info_position"][1]+")");
    current_weather += tab.row(lang("SUNRISE") +":",    weather_3day["today"]["sunrise"]);
    current_weather += tab.row(lang("SUNSET")+":",      weather_3day["today"]["sunset"]);
    current_weather += tab.row(lang("TEMPERATURE")+":", weather_today["temperature"] +"°C");
    current_weather += tab.row(lang("HUMIDITY")+":",    weather_today["humidity"] +"%");
    current_weather += tab.row(lang("WIND")+":",        weather_today["wind_speed"] + " km/h");
    current_weather += tab.row(lang("STATUS")+":",      weather_today["date"] + " " + weather_today["time"]);
    // current_weather += tab.row(lang("PRESSURE")+":",    weather_today["pressure"] + " hPa");
    //current_weather += tab.row(lang("UV_INDEX")+":",    weather_today["uv_index"]);
    if (weather["info_module"]["provider_link_required"]) {
        current_weather += tab.row(lang("SOURCE")+":",  weather["info_module"]["provider_link"]);
    }
    current_weather += tab.end();

    html_temp = tab.start();
    html_temp += tab.row(current_icon, current_weather);
    html_temp += tab.end();
    html_weather += "&nbsp;<br/>" + html_temp + "<br/>&nbsp;";
    html = "";

    var d = new Date();
    var current_year   = d.getFullYear();
    var current_month  = d.getMonth()+1;
    var current_day    = d.getDate();
    var current_hour   = d.getHours();

    var last_day       = "";
    var day_count      = 0;
    var chart_data     = {
        "titles" : [lang("TEMPERATURE") + " [°C]", lang("HUMIDITY") + " [%]", lang("WIND") + " [km/h]"],
        "data"   : {}
    }
    var weather_data = {}

    Object.keys(weather_3day).forEach(key=>{ if (key != "today") {
        var forecast_day = weather_3day[key];
        var forecast_html = "<br/>&nbsp;<hr style='width:95%;'/>";
        var today = false;
        var forecast_entries = 0;
        var [forcast_year, forcast_month, forcast_day] = key.split("-");
        if ((forcast_year*1) == (current_year*1) && (forcast_month*1) == (current_month*1) && (forcast_day*1) == (current_day*1)) { today = true; }
        day_count += 1;

        Object.keys(forecast_day["hourly"]).forEach(key2=>{
            var key_hour = key2.split(":")[0];
            var key_minute = key2.split(":")[1];
            var forcast_hour = forecast_day["hourly"][key2];

            if (day_count <= 3) {
                var chart_key = key.split("-")[2] + "." + key.split("-")[1] + " " + key2;
                if (key != last_day) { chart_data["data"][chart_key] = [undefined, undefined, undefined]; last_day = key; }
                if (key2 == "00:00") { chart_key = chart_key.replace("00:00", "00:01"); }
                chart_data["data"][chart_key] = [forcast_hour["temperature"], forcast_hour["humidity"], forcast_hour["wind_speed"]];

                if (key_hour.split(":")[0] > 6) {
                    if (!weather_data[key]) { weather_data[key] = {}; }
                    forcast_hour["key"] = key2;
                    weather_data[key][key2] = forcast_hour;
                    }
            }

            if (!today || (current_hour*1) < (key_hour*1)) {
                var current_icon = "<center><font  style='font-size:40px;'>" + forcast_hour["description_icon"] + "</font></center>";
                var current_weather = tab.start();

                current_weather += tab.row(lang("TEMPERATURE")+":", forcast_hour["temperature"] +"°C");
                current_weather += tab.row(lang("HUMIDITY")+":",    forcast_hour["humidity"] +"%");
                current_weather += tab.row(lang("WIND")+":",        forcast_hour["wind_speed"] + " km/h");
                // current_weather += tab.row(lang("PRESSURE")+":",    forcast_hour["pressure"] + " hPa");
                current_weather += tab.end();

                html_temp = "<div style='width:100%;text-align:right;'><b>"+key_hour+":"+key_minute+"</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div><hr style='width:95%;'/>";
                html_temp += tab.start();
                html_temp += tab.row(current_icon, current_weather);
                html_temp += tab.end();
                html_temp += "<hr style='width:95%;'/>";

                forecast_html += html_temp;
                forecast_entries += 1;
            }
        });
        if (forecast_entries > 0) {
            var title = "";
            if (today) { title = key + "&nbsp;-&nbsp;" + lang("TODAY"); }
            else       { title = key; }
            html += birdhouse_OtherGroup( "weather_forecast_"+key, title, forecast_html, false );
        }
    }});

    html_weather += "<br/>&nbsp;<br/>";

    //console.error(chart_data);
    //console.error(weather_data);

    var chart     = "&nbsp;<br/>";
    chart        += birdhouseChart_create(label="", titles=chart_data["titles"],data=chart_data["data"]);
    chart        += "<br/>&nbsp;<br/>";

    Object.keys(weather_data).forEach(date=>{
        chart   += "<b>" + date + "</b><br/>";
        chart   += "<center>" + birdhouseWeather_OverviewChart(weather_data[date], "key", false) + "</center>" ;
        });

    chart        += "<br/>&nbsp;<br/>";
    html_weather += birdhouse_OtherGroup( "chart", lang("WEATHER") + " (3 " + lang("DAYS") + ")", chart, true );
    if (admin_allowed) {
        html_weather += html;
        }

    var title = "<div id='status_error_WEATHER' style='float:left'><div id='black'></div></div>";
    title += "<center><h2>" + lang("WEATHER") + "&nbsp;&nbsp;&nbsp;&nbsp;</h2></center>";
    setTextById(app_frame_header, title);
	setTextById(app_frame_content, html_weather);
}

/*
* create a three days weather overview chart
*
* @param (dict) entries: weather entries from server API
* @param (string) title_key: title key
* @param (boolean) title_column: show title above the chart
*/
function birdhouseWeather_OverviewChart (entries, title_key="time", title_column=true) {
    var html = "";
    var count = 0;
    var weather_data = {};

    Object.keys(entries).forEach( key => {
        weather_data[entries[key][title_key]] = entries[key]["description_icon"];
        /*
        if (key.substring(2,4) == "00" && entries[key]["weather"]) {
            weather_data[key.substring(0,2)+":"+key.substring(2,4)] = entries[key]["weather"]["description_icon"];
        }
        */
    });

    // width -> 8 if small; 16 if middle; 24 if big

    if (title_column) {
        html_row1 = "<td></td>";
        html_row2 = "<td>"+lang("WEATHER")+": &nbsp;</td>";
    }
    else {
        html_row1 = "";
        html_row2 = "";
    }
    Object.keys(weather_data).sort().forEach(key => {
        var td_class = "weather_hide_if_small";
        if (Math.abs(count % 2) != 0 || Object.keys(weather_data).length <= 8) {
             td_class = "weather_show";
        }
        if (count < 16) {
            html_row1 += "<td class='"+td_class+"'>"+key+"<td>";
            html_row2 += "<td class='"+td_class+"' style='font-size:14px;'><center>"+weather_data[key]+"<center><td>";
        }
        count += 1;
    });
    if (count == 0) { return ""; }
    html += "<hr/><table border='0'>";
    html += "<tr style='font-size:8px;'>" + html_row1 + "</tr>";
    html += "<tr style='font-size:11px;'>" + html_row2 + "</tr>";
    html +="</table>"
    console.debug(weather_data);
    //html += "&nbsp;<br/>&nbsp;";
    return html;
}


app_scripts_loaded += 1;