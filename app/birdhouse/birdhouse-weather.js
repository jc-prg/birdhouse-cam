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
	var weather	= data["WEATHER"];
	var weather_today = weather["current"];
	var weather_3day  = weather["forecast"];

	var tab     = new birdhouse_table();
	//tab.style_rows["height"] = "150px";

    var html_weather = "";
    var html_temp = "";
    var html_entry = "";

    var current_icon = "<center><font style='font-size:80px;'><big>" + weather_today["description_icon"] + "</big></font></center>";
    var current_weather = tab.start();
    current_weather += tab.row("Location:", weather["info_city"]);
    current_weather += tab.row("Sunrise / Sunset:", weather_3day["today"]["sunrise"] + " / " + weather_3day["today"]["sunset"]);
    current_weather += tab.row("Weather:", weather_today["description"]);
    current_weather += tab.row("Temperature:", weather_today["temperature"] +"°C");
    current_weather += tab.row("Wind:", weather_today["wind_speed"] + " km/h - " + weather_today["wind_direction"]);
    current_weather += tab.row("Pressure:", weather_today["pressure"] + " hPa");
    current_weather += tab.row("UV Index:", weather_today["uv_index"]);
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
            current_weather += tab.row("Temperature:", forcast_hour["temperature"] +"°C");
            current_weather += tab.row("Wind:", forcast_hour["wind_speed"] + " km/h - " + forcast_hour["wind_direction"]);
            current_weather += tab.row("Pressure:", forcast_hour["pressure"] + " hPa");
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
