//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// show status functions
//--------------------------------------

var header_color_error = "#993333";
var header_color_warning = "#666633";
var header_color_default = "";

function setHeaderColor(header_id, header_color) {
    header = document.getElementById("group_header_" + header_id);
    if (header) {
        header.style.background = header_color;
        }
}

function setStatusColor(status_id, status_color) {
    var status = "<div id='" + status_color + "'></div>";
    setTextById(status_id, status);
}

function birdhouseStatus_print(data) {
    console.debug("Update Status ...");

    // add database information
    var db_info = "type=" + data["DATA"]["server"]["database_type"]+"; ";
    if (data["DATA"]["server"]["database_type"] == "couch") {
        db_info += "connected=" + data["DATA"]["server"]["database_couch_connect"];
    }
    setTextById("system_info_database",         db_info);

    // add system information
    percentage = (data["STATUS"]["system"]["mem_used"]/data["STATUS"]["system"]["mem_total"])*100
    setTextById("system_info_mem_total",        (Math.round(data["STATUS"]["system"]["mem_total"]*10)/10)+" MB")
    setTextById("system_info_mem_used",         (Math.round(data["STATUS"]["system"]["mem_used"]*10)/10)+" MB (" + Math.round(percentage) + "%)")

    setTextById("system_info_cpu_usage",        (Math.round(data["STATUS"]["system"]["cpu_usage"]*10)/10)+"%")
    setTextById("system_info_cpu_temperature",  (Math.round(data["STATUS"]["system"]["cpu_temperature"]*10)/10)+"°C")

    var cpu_details = "";
    for (var i=0;i<data["STATUS"]["system"]["cpu_usage_detail"].length;i++) {
        cpu_details += "cpu"+i+"="+Math.round(data["STATUS"]["system"]["cpu_usage_detail"][i])+"%, ";
        }
    setTextById("system_info_cpu_usage_detail", cpu_details);

    // add camera information
    var cameras = data["DATA"]["devices"]["cameras"];
    var camera_streams = 0;
    for (let camera in cameras) {
        setTextById("show_stream_count_"+camera, cameras[camera]["image"]["current_streams"]);
        camera_streams += cameras[camera]["image"]["current_streams"];
        setTextById("error_cam_"+camera, cameras[camera]["status"]["error_msg"]);
        setTextById("error_img_"+camera, cameras[camera]["status"]["image_error_msg"]);
        setTextById("last_image_recorded_"+camera, Math.round(cameras[camera]["status"]["record_image_last"]*10)/10 +
                    "s (error=" + cameras[camera]["status"]["record_image_error"] + ")");

        if (cameras[camera]["status"]["error"] || cameras[camera]["status"]["image_error"]) {
            setHeaderColor(header_id=camera+"_error", header_color=header_color_error);
            setHeaderColor(header_id=camera, header_color=header_color_error);
            setStatusColor(status_id="status_error_"+camera, "red");
        }
        else {
            setHeaderColor(header_id=camera+"_error", header_color="");
            setHeaderColor(header_id=camera, header_color="");
            setStatusColor(status_id="status_error_"+camera, "green");
        }
        if (cameras[camera]["active"]) {
            setStatusColor(status_id="status_active_"+camera, "white");
            }
        else {
            setStatusColor(status_id="status_active_"+camera, "black");
            setStatusColor(status_id="status_error_"+camera, "black");
            }

        if (cameras[camera]["image"]["crop_area"]) {
            crop = "[" + cameras[camera]["image"]["crop_area"][0] + ", " + cameras[camera]["image"]["crop_area"][1] + ", ";
            crop += cameras[camera]["image"]["crop_area"][2] + ", " + cameras[camera]["image"]["crop_area"][2] + "] ";
            setTextById("get_crop_area_"+camera, crop);
            }
        }
    setTextById("system_active_streams", camera_streams);

    // weather information
    var weather_footer = [];
    var entry = "";
    var weather_icon = "<small>N/A</small>";
    var weather_update = "N/A";
    var weather_error = "";
    if (data["WEATHER"]["current"] && data["WEATHER"]["current"]["description_icon"]) {
        if (data["DATA"]["localization"]["weather_active"]) {
            entry = data["WEATHER"]["info_city"] + ": " + data["WEATHER"]["current"]["temperature"] + "°C";
            entry = "<big>" + data["WEATHER"]["current"]["description_icon"] + "</big> &nbsp; " + entry;
            weather_icon = data["WEATHER"]["current"]["description_icon"];
            weather_update = data["WEATHER"]["info_update"];
        }
        weather_error = "Running: " + data["WEATHER"]["info_status"]["running"] + "\n";
        if (data["WEATHER"]["info_status"]["error"]) {
            weather_error += "Error: " + data["WEATHER"]["info_status"]["error"].toString() + "\n";
            weather_error += "Message: " + data["WEATHER"]["info_status"]["error_msg"];
            setHeaderColor(header_id="weather_error", header_color=header_color_error);
            setHeaderColor(header_id="weather_settings", header_color=header_color_error);
            setStatusColor(status_id="status_error_WEATHER", "red");
        }
        else if (data["WEATHER"]["info_status"]["running"].indexOf("paused") > -1) {
            setHeaderColor(header_id="weather_error", header_color=header_color_warning);
            setStatusColor(status_id="status_error_WEATHER", "black");
        }
        else {
            setHeaderColor(header_id="weather_settings", header_color="");
            setHeaderColor(header_id="weather_error", header_color="");
            setStatusColor(status_id="status_error_WEATHER", "green");
        }
        if (data["DATA"]["localization"]["weather_active"] == true) {
            setStatusColor(status_id="status_active_WEATHER", "white");
            }
        else{
            setStatusColor(status_id="status_active_WEATHER", "black");
            setStatusColor(status_id="status_error_WEATHER", "black");
        }
    }
    weather_footer.push(entry);
    setTextById("weather_info_icon", weather_icon);
    setTextById("weather_info_update", weather_update);
    setTextById("weather_info_error", weather_error);

    // add sensor information
    var sensors = data["DATA"]["devices"]["sensors"];
    var keys = Object.keys(sensors);
    for (let sensor in sensors) {
        if (sensors[sensor]["status"]) {
            var status = sensors[sensor]["status"];
            var sensor_error_01 = status["error_msg"];
            var sensor_error_02 = "Error: " + status["error"].toString() + "\n\n";
            if (status["error_connect"]) {
                sensor_error_02    += "Error Connect: " + status["error_connect"].toString() + "\n\n";
                }
            if (status["error_module"]) {
                sensor_error_02    += "Error Module: " + status["error_module"].toString();
                }
            setTextById("error_sensor1_"+sensor, sensor_error_01);
            setTextById("error_sensor2_"+sensor, sensor_error_02);
            setTextById("status_sensor_"+sensor, status["running"]);
            setTextById("status_sensor_last_"+sensor, Math.round(status["last_read"]*10)/10) +"s");
            if (status["error"] || status["error_module"] || status["connect"]) {
                setHeaderColor(header_id=sensor+"_error", header_color=header_color_error);
                setHeaderColor(header_id=sensor, header_color=header_color_error);
                setStatusColor(status_id="status_error_"+sensor, "red");
            }
            else {
                setHeaderColor(header_id=sensor+"_error", header_color="");
                setHeaderColor(header_id=sensor, header_color="");
                setStatusColor(status_id="status_error_"+sensor, "green");
            }
        }

        if (sensors[sensor]["active"]) {
            setStatusColor(status_id="status_active_"+sensor, "white");
            var entry = "";
            if (typeof(sensors[sensor]["values"]["temperature"]) != "undefined" && sensors[sensor]["values"]["temperature"] != null) {
                entry += sensors[sensor]["name"] + ": ";
                entry += "<font id='temp"+sensor+"'>"+sensors[sensor]["values"]["temperature"];
                entry += sensors[sensor]["units"]["temperature"]+"</font>";
                weather_footer.push(entry);
                }

            var summary = "";
            for (let key in sensors[sensor]["values"]) {
                summary += sensors[sensor]["values"][key] + sensors[sensor]["units"][key] + "<br/>";
            }
            setTextById("sensor_info_"+sensor, summary);
        }
        else {
            setStatusColor(status_id="status_active_"+sensor, "black");
            setStatusColor(status_id="status_error_"+sensor, "black");
        }
    }

    // add micro information
    var microphones = data["DATA"]["devices"]["microphones"];
    var keys = Object.keys(microphones);
    for (let micro in microphones) {
        if (microphones[micro]["active"]) {
            setStatusColor(status_id="status_active_"+micro, "white");
        }
        else {
            setStatusColor(status_id="status_active_"+micro, "black");
        }
    }

    document.getElementById(app_frame_info).style.display = "block";
    html = "<center><i><font color='gray'>";
    html += weather_footer.join(" / ");
    html += "</font></i></center>";
    setTextById(app_frame_info, html);
}

