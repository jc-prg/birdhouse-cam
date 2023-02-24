//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// show status functions
//--------------------------------------

function birdhouseStatus_print(data) {
    console.debug("Update Status ...");

    // add system information
    percentage = (data["STATUS"]["system"]["mem_used"]/data["STATUS"]["system"]["mem_total"])*100
    setTextById("system_info_mem_total",        (Math.round(data["STATUS"]["system"]["mem_total"]*10)/10)+" MB")
    setTextById("system_info_mem_used",         (Math.round(data["STATUS"]["system"]["mem_used"]*10)/10)+" MB ("
            + Math.round(percentage) + "%)")

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
        if (cameras[camera]["status"]["error"] || cameras[camera]["status"]["image_error"]) {
            header = document.getElementById("group_header_"+camera+"_error");
            if (header) { header.style.background = "#993333"; }
            }
        if (cameras[camera]["image"]["crop_area"]) {
            crop = "[" + cameras[camera]["image"]["crop_area"][0] + ", " + cameras[camera]["image"]["crop_area"][1] + ", ";
            crop += cameras[camera]["image"]["crop_area"][2] + ", " + cameras[camera]["image"]["crop_area"][2] + "] ";
            setTextById("get_crop_area_"+camera, crop);
            }
        }
    setTextById("system_active_streams", camera_streams);

    // add sensor information
    var sensors = data["DATA"]["devices"]["sensors"];
    html = "<center><i><font color='gray'>";
    html_entry = "";
    var count = 0;
    var keys = Object.keys(sensors);
    for (let sensor in sensors) {
        if (sensors[sensor]["status"]) {
            status = sensors[sensor]["status"];
            var sensor_error_01 = status["error_msg"];
            var sensor_error_02 = "Error:" + status["error"];
            sensor_error_02    += "Error Connect:" + status["error_connect"];
            sensor_error_02    += "Error Module:" + status["error_module"];
            setTextById("error_sensor1_"+sensor, sensor_error_01);
            setTextById("error_sensor2_"+sensor, sensor_error_02);
            if (status["error"] || status["error_module"] || status["connect"]) {
                header = document.getElementById("group_header_"+sensor+"_error");
                if (header) { header.style.background = "#993333"; }
            }
        }
        if (sensors[sensor]["active"]) {

            if (typeof(sensors[sensor]["values"]["temperature"]) != "undefined" && sensors[sensor]["values"]["temperature"] != null) {
                html_entry += sensors[sensor]["name"] + ": ";
                html_entry += "<font id='temp"+sensor+"'>"+sensors[sensor]["values"]["temperature"]+"</font>";
                html_entry += sensors[sensor]["units"]["temperature"];
                count += 1;
                if (count < keys.length) { html_entry += " / "; }
                }

            var summary = "";
            for (let key in sensors[sensor]["values"]) {
                summary += sensors[sensor]["values"][key] + sensors[sensor]["units"][key] + "<br/>";
            }
            setTextById("sensor_info_"+sensor, summary);
        }
    }

    /*
            if (sensors[sensor]["status"] && sensors[sensor]["status"]["error"] == true) {
    		html_entry += tab.row("<hr/>");
            html_entry += tab.row("Error-Msg:", sensors[sensor]["status"]["error_msg"]);
        }

    */

    document.getElementById(app_frame_info).style.display = "block";
    if (data["DATA"]["localization"]["weather_active"] && data["WEATHER"]["current"] && data["WEATHER"]["current"]["description_icon"]) {
        if (html_entry != "") { html_entry += " / "; }
        html_entry += data["WEATHER"]["info_city"] + ": " + data["WEATHER"]["current"]["temperature"] + "°C";
        html_entry = "<big>" + data["WEATHER"]["current"]["description_icon"] + "</big> &nbsp; " + html_entry;
    }
    else if (count > 0) {
        html_entry = lang("TEMPERATURE") + ": " + html_entry;
    }
    html += html_entry;
    html += "</font></i></center>";
    setTextById(app_frame_info, html);
}

