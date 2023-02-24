//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// show and edit device information
//--------------------------------------
/* INDEX:
function birdhouseDevices( title, data )
*/
//--------------------------------------

function birdhouseWeather( title, data ) {

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
    current_weather += tab.row(lang("LOCATION") + ":",  weather["info_city"]);
    current_weather += tab.row(lang("SUNRISE") +":",    weather_3day["today"]["sunrise"]);
    current_weather += tab.row(lang("SUNSET")+":",      weather_3day["today"]["sunset"]);
    current_weather += tab.row(lang("TEMPERATURE")+":", weather_today["temperature"] +"°C");
    current_weather += tab.row(lang("HUMIDITY")+":",    weather_today["humidity"] +"%");
    current_weather += tab.row(lang("WIND")+":",        weather_today["wind_speed"] + " km/h - " + weather_today["wind_direction"]);
    current_weather += tab.row(lang("PRESSURE")+":",    weather_today["pressure"] + " hPa");
    current_weather += tab.row(lang("UV_INDEX")+":",    weather_today["uv_index"]);
    current_weather += tab.end();

    html_temp = tab.start();
    html_temp += tab.row(current_icon, current_weather);
    html_temp += tab.end();
    html_weather += "&nbsp;<br/>" + html_temp + "<br/>&nbsp;";

    Object.keys(weather_3day).forEach(key=>{ if (key != "today") {
        var forecast_day = weather_3day[key];
        var forecast_html = "<br/>&nbsp;<hr style='width:95%;'/>";

        Object.keys(forecast_day["hourly"]).forEach(key2=>{
            var forcast_hour = forecast_day["hourly"][key2];
            var current_icon = "<center><font  style='font-size:40px;'>" + forcast_hour["description_icon"] + "</font></center>";
            var current_weather = tab.start();
            current_weather += tab.row(lang("TEMPERATURE")+":", forcast_hour["temperature"] +"°C");
            current_weather += tab.row(lang("WIND")+":",        forcast_hour["wind_speed"] + " km/h - " + forcast_hour["wind_direction"]);
            current_weather += tab.row(lang("PRESSURE")+":",    forcast_hour["pressure"] + " hPa");
            current_weather += tab.end();

            html_temp = "<div style='width:100%;text-align:right;'><b>"+key2+"</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div><hr style='width:95%;'/>";
            html_temp += tab.start();
            html_temp += tab.row(current_icon, current_weather);
            html_temp += tab.end();
            html_temp += "<hr style='width:95%;'/>";

            forecast_html += html_temp;
        });
        html_entry += forecast_html;
        html_weather += birdhouse_OtherGroup( "weather_forecast_"+key, key, html_entry, false );
    }});

    html_weather += "<br/>&nbsp;<br/>";

	setTextById(app_frame_content, html_weather);
}
