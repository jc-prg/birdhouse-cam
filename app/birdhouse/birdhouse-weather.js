//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// show and edit device information
//--------------------------------------


function birdhouseWeather( title, data ) {
	commands = ["status"];
	appFW.requestAPI('GET', commands, '', birdhouseWeather_exec,'','birdhouseWeather');
}

function birdhouseWeather_exec( data ) {
    if (data["DATA"]["localization"]["weather_active"] == false) {
        setTextById(app_frame_content, "&nbsp;<br/><center>" + lang("NO_WEATHER_CHANGE_SETTINGS") + "</center><br/>&nbsp;");
        return;
    }

	var weather	= data["WEATHER"];
	var weather_today = weather["current"];
	var weather_3day  = weather["forecast"];

    if (!weather["forecast"] || !weather["current"] || !weather["forecast"]["today"]) {
        setTextById(app_frame_content, "&nbsp;<br/><center>" + lang("WEATHER_DATA_ERROR") + "</center><br/>&nbsp;");
        console.warn("Error with weather data!")
        console.warn(weather);
        return;
    }

	var tab     = new birdhouse_table();
	tab.style_rows["height"] = "18px";

    var html_weather = "";
    var html_temp = "";
    var html_entry = "";

    var current_icon = "<center><font style='font-size:80px;'><big>" + weather_today["description_icon"] + "</big></font>"
                       + "<br/>" + weather_today["description"] + "</center>";
    var current_weather = tab.start();
    if (weather["info_position"].length <= 2) {
        current_weather += tab.row(lang("LOCATION") + ":",  data["STATUS"]["devices"]["weather"]["gps_location"]);
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

    var d = new Date();
    var current_year   = d.getFullYear();
    var current_month  = d.getMonth()+1;
    var current_day    = d.getDate();
    var current_hour   = d.getHours();

    Object.keys(weather_3day).forEach(key=>{ if (key != "today") {
        var forecast_day = weather_3day[key];
        var forecast_html = "<br/>&nbsp;<hr style='width:95%;'/>";
        var today = false;
        var forecast_entries = 0;
        var [forcast_year, forcast_month, forcast_day] = key.split("-");
        if ((forcast_year*1) == (current_year*1) && (forcast_month*1) == (current_month*1) && (forcast_day*1) == (current_day*1)) { today = true; }

        Object.keys(forecast_day["hourly"]).forEach(key2=>{
            var key_hour = key2.split(":")[0];
            var key_minute = key2.split(":")[1];

            if (!today || (current_hour*1) < (key_hour*1)) {
                var forcast_hour = forecast_day["hourly"][key2];
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
            html_weather += birdhouse_OtherGroup( "weather_forecast_"+key, title, forecast_html, false );
        }
    }});

    html_weather += "<br/>&nbsp;<br/>";

    var title = "<div id='status_error_WEATHER' style='float:left'><div id='black'></div></div>";
    title += "<center><h2>" + lang("WEATHER") + "&nbsp;&nbsp;&nbsp;&nbsp;</h2></center>";
    setTextById(app_frame_header, title);
	setTextById(app_frame_content, html_weather);
}
