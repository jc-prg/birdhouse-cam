//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// show status functions
//--------------------------------------

var header_color_error = "#993333";
var header_color_warning = "#666633";
var header_color_default = "";
var weather_footer = [];
var loading_dots_red   = '<span class="loading-dots"><span class="dot red"></span><span class="dot red"></span><span class="dot red"></span></span>';
var loading_dots_green = '<span class="loading-dots"><span class="dot green"></span><span class="dot green"></span><span class="dot green"></span></span>';
var app_processing_active = false;
var app_server_error = false;

/*
* change the color of a group header, e.g., to visualize an error
*
* @param (string) header_id: id of the header to be colored
* @param (string) header_color: html code or name of the color to be used, keep empty to get back to default
*/
function setHeaderColor(header_id, header_color="") {
    header = document.getElementById("group_header_" + header_id);
    if (header) {
        header.style.background = header_color;
        }
}

/*
* change the color of an status bullet
*
* @param (string) status_id: id of status element
* @param (string) status_color: color to be used, available: red, blue, green, yellow, black, white
*/
function setStatusColor(status_id, status_color) {
    var status = "<div id='" + status_color + "'></div>";
    setTextById(status_id, status);
}

/*
* Check if app is connected to the server. If error visualize in several places ...
*/
function birdhouseStatus_connectionError() {
    var cameras     = app_data["SETTINGS"]["devices"]["cameras"];
    var microphones = app_data["SETTINGS"]["devices"]["microphones"];
    var sensors     = app_data["SETTINGS"]["devices"]["sensors"];

    setTextById("system_info_connection", "<font color='red'><b>Connection lost!</b></font>");

    for (let camera in cameras) {
        setStatusColor(status_id="status_active_"+camera, "red");
        setStatusColor(status_id="status_error_"+camera, "black");
        setStatusColor(status_id="status_error_record_"+camera, "black");

        setStatusColor(status_id="status_"+camera+"_detection_active", "red");
        setStatusColor(status_id="status_"+camera+"_detection_loaded", "black");
    }
    for (let sensor in sensors) {
        setStatusColor(status_id="status_active_"+sensor, "red");
        setStatusColor(status_id="status_error_"+sensor, "black");
    }
    for (let micro in microphones) {
        setStatusColor(status_id="status_active_"+micro, "red");
        setStatusColor(status_id="status_error_"+micro, "black");
    }
    setStatusColor(status_id="status_active_WEATHER", "red");
    setStatusColor(status_id="status_error_WEATHER", "black");
}

/*
* Orchestration of all status functions
*
* @param (dict) data: response from API status request
*/
function birdhouseStatus_print(data) {
    //if (!data["STATUS"]) { data["STATUS"] = app_data["STATUS"]; }
    console.debug("Update Status ...");

    // set latest status data to var app_data
    app_data       = data;
    weather_footer = [];
    app_processing_active = false;
    app_server_error = false;

    // check page length vs. screen height
    var body = document.body, html = document.documentElement;
    var height = Math.max( body.scrollHeight, body.offsetHeight, html.clientHeight, html.scrollHeight, html.offsetHeight );
    if (height > 1.5 * document.body.clientHeight) { elementVisible("move_up"); }
    else { elementHidden("move_up"); }
    //if (appSettings.active) { setTextById("device_status_short", birdhouseDevices("", data, "short")); } // !!!! Quelle des Problems? Zu oft aufgerufen?
                                                                                                         // bezieht sich auf die Settings
    birdhouseStatus_system(data);
    birdhouseStatus_cameras(data);
    birdhouseStatus_weather(data);
    birdhouseStatus_sensors(data);
    birdhouseStatus_microphones(data);

    birdhouseStatus_loadingViews(data);
    birdhouseStatus_detection(data);
    birdhouseStatus_downloads(data);
    birdhouseStatus_processing(data);
    birdhouseStatus_recordButtons(data);

    if (!appSettings.active) {
        document.getElementById(app_frame_info).style.display = "block";
        html = "<center><i><font color='gray'>";
        html += weather_footer.join(" / ");
        html += "</font></i></center>";
        setTextById(app_frame_info, html);
        }

}

/*
* read latest camera status information and fill respective placeholders with information if exist
*
* @param (dict) data: response from API status request
*/
function birdhouseStatus_cameras(data) {
    // add camera information
    var cameras         = data["SETTINGS"]["devices"]["cameras"];
    var camera_status   = data["STATUS"]["devices"]["cameras"];
    var camera_streams  = 0;

    for (let camera in cameras) {
        if (camera_status[camera]) {
            //console.error(camera_status);
            if (camera_status[camera]["active_streams"] == 1) { stream = lang("STREAM"); } else { stream = lang("STREAMS"); }
            setTextById("show_stream_count_"+camera, camera_status[camera]["active_streams"] + " " + stream);
            setTextById("show_stream_fps_"+camera,   "("+camera_status[camera]["stream_raw_fps"]+" fps)");
            setTextById("show_stream_info_"+camera,   "("+camera_status[camera]["active_streams"] + ": " + camera_status[camera]["stream_raw_fps"]+"fps)");
            setTextById("show_stream_object_fps_"+camera,   "("+camera_status[camera]["stream_object_fps"]+" fps)");
            camera_streams += cameras[camera]["image"]["current_streams"];

            // consolidate error messages
            error_stream_info = "";
            for (stream_id in camera_status[camera]["error_details"]) {
                error_stream_info += "<b>" + stream_id + ":</b><br/>";
                if (camera_status[camera]["error_details"][stream_id]) { error_stream_info += "<font color='red'>"; }
                else                                                   { error_stream_info += "<font>"; } //  color='lightgray'

                var no_error = true;
                if (camera_status[camera]["error_details"][stream_id])                  { no_error = false; error_stream_info += "ERROR: "; }
                if (camera_status[camera]["error_details_msg"][stream_id].length > 0)   { no_error = false; error_stream_info += "messages=" + camera_status[camera]["error_details_msg"][stream_id].length + "; "; }
                if (no_error)                                                           { error_stream_info += "OK: "; }
                if (stream_id != "image" && stream_id != "image_record" && stream_id != "camera_handler") { error_stream_info += "last_active=" + camera_status[camera]["error_details_health"][stream_id] + "s"; }

                if (camera_status[camera]["error_details"][stream_id] && camera_status[camera]["error_details_msg"][stream_id].length > 0) {
                    last_msg = camera_status[camera]["error_details_msg"][stream_id].length - 1;
                    error_stream_info += "<br/><i>" + camera_status[camera]["error_details_msg"][stream_id][last_msg] + ";</i> ";
                }
                error_stream_info += "</font><br/>";
            }

            setTextById("error_streams_"+camera, error_stream_info);
            setTextById("error_rec_"+camera, camera_status[camera]["record_image_error"]);

            // recording time
            record_time_info = "from <u>" + camera_status[camera]["record_image_start"] + "</u> to <u>" + camera_status[camera]["record_image_end"] + "</u>";
            if (camera_status[camera]["record_image_start"] == "-1:-1") { record_time_info = "<i>N/A (camera not active)</i>"; }
            setTextById("get_record_image_time_"+camera, record_time_info);

            //birdhouseStatus_cameraParam(data, camera);

            // error recording images
            if (camera_status[camera]["error"]) {
                setTextById("last_image_recorded_"+camera, "Recording inactive due to camera error.");
            }
            else {
                if (!camera_status[camera]["record_image_active"]) { var record_image_reload = "INACTIVE"; }
                else                                               { var record_image_reload = Math.round(camera_status[camera]["last_reload"]*10)/10 + "s"; }
                setTextById("last_image_recorded_" + camera,
                            "last_recorded=" + Math.round(camera_status[camera]["record_image_last"]*10)/10 + "s" + "; last_reload=" + record_image_reload +
                            "<br/>active=" + camera_status[camera]["record_image_active"] + "; " + "error=" + camera_status[camera]["record_image_error"]);
            }

            // camera stream working correctly
            var error_count = 0;
            for (let stream_id in camera_status[camera]["error_details"]) {
                if (camera_status[camera]["error_details"][stream_id]) { error_count += 1; }
            }
            if (camera_status[camera]["active"] && (camera_status[camera]["error"] || camera_status[camera]["error_details"]["stream_raw"])) {
                setHeaderColor(header_id=camera+"_error", header_color=header_color_error);
                setHeaderColor(header_id=camera, header_color=header_color_error);
                setStatusColor(status_id="status_error_"+camera, "red");
                setStatusColor(status_id="status_error2_"+camera, "red");
            }
            else if (camera_status[camera]["active"] && error_count > 0) {
                setHeaderColor(header_id=camera+"_error", header_color=header_color_warning);
                setHeaderColor(header_id=camera, header_color=header_color_warning);
                setStatusColor(status_id="status_error_"+camera, "yellow");
                setStatusColor(status_id="status_error2_"+camera, "yellow");
            }
            else {
                setHeaderColor(header_id=camera+"_error", header_color="");
                setHeaderColor(header_id=camera, header_color="");
                setStatusColor(status_id="status_error_"+camera, "green");
                setStatusColor(status_id="status_error2_"+camera, "green");
            }

            // image recording working correctly
            if (camera_status[camera]["record_image_active"] && camera_status[camera]["record_image_error"]) {
                setStatusColor(status_id="status_error_record_"+camera, "red");
            }
            else if (camera_status[camera]["record_image_active"]) {
                setStatusColor(status_id="status_error_record_"+camera, "green");
                setStatusColor(status_id="status_error2_record_"+camera, "green");
            }
            else {
                setStatusColor(status_id="status_error_record_"+camera, "black");
                setStatusColor(status_id="status_error2_record_"+camera, "black");
            }

            // camera activated
            if (cameras[camera]["active"]) {
                setStatusColor(status_id="status_active_"+camera, "white");
                }
            else {
                setStatusColor(status_id="status_active_"+camera, "black");
                setStatusColor(status_id="status_error_"+camera, "black");
                setStatusColor(status_id="status_error2_"+camera, "black");
                setStatusColor(status_id="status_error_record_"+camera, "black");
                setStatusColor(status_id="status_error2_record_"+camera, "black");
                }

            if (cameras[camera]["image"]["crop_area"]) {
                crop = "[" + cameras[camera]["image"]["crop_area"][0] + ", " + cameras[camera]["image"]["crop_area"][1] + ", ";
                crop += cameras[camera]["image"]["crop_area"][2] + ", " + cameras[camera]["image"]["crop_area"][2] + "] ";
                setTextById("get_crop_area_"+camera, crop);
                }
            }
        }

    // client stream information
    count_client_streams = birdhouse_CountActiveStreams();
    if (count_client_streams == 1) { stream = lang("STREAM"); } else { stream = lang("STREAMS"); }
    setTextById("show_stream_count_client", count_client_streams + " " + stream);
    setTextById("system_active_streams", camera_streams);
}

/*
* read latest camera settings and fill respective placeholders with information if exist
*
* @param (dict) data: response from API status request
*/
function birdhouseStatus_cameraParam(data, camera) {
    // camera parameter (image settings)
    //var camera_status   = data["STATUS"]["devices"]["cameras"];
    var camera_status   = data["DATA"]["data"];
    if (camera_status["properties"]) {
        for (let key in camera_status["properties"]) {
            var prop_text = camera_status["properties"][key][0];
            setTextById("prop_" + key + "_" + camera, prop_text);
            if (document.activeElement != document.getElementById("set_" + key + "_" + camera) && document.activeElement != document.getElementById("set_" + key + "_" + camera + "_range")) {
                setValueById("set_" + key + "_" + camera, camera_status["properties"][key][0]);
                setValueById("set_" + key + "_" + camera + "_range", camera_status["properties"][key][0]);
                }
            //console.error(key + ":" + camera_status[camera]["properties"][key].toString());
        }
        for (let key in camera_status["properties_image"]) {
            setTextById("img_" + key + "_" + camera, Math.round(camera_status["properties_image"][key]*100)/100);
            //console.error(key + ":" + camera_status[camera]["properties"][key].toString());
        }
    }
}

/*
* read latest weather information and fill respective placeholders with weather information if exist
*
* @param (dict) data: response from API status request
*/
function birdhouseStatus_weather(data) {
    // weather information
    var weather         = data["WEATHER"];
    var settings        = data["SETTINGS"]["devices"]["weather"];

    var entry           = "";
    var weather_icon    = "<small>N/A</small>";
    var weather_update  = "N/A";
    var weather_error   = "";

    if (weather["current"] && weather["current"]["description_icon"]) {
        if (settings["active"]) {
            if (weather["info_city"] != "") {
                entry = weather["info_city"] + ": " + weather["current"]["temperature"] + "°C";
                }
            else if (weather["info_module"]["name"]) {
                entry = weather["info_module"]["name"] + ": " + weather["current"]["temperature"] + "°C";
            }
            else  {
                entry = "Internet: " + weather["current"]["temperature"] + "°C";
            }
            entry = "<big>" + weather["current"]["description_icon"] + "</big> &nbsp; " + entry;
            weather_icon = weather["current"]["description_icon"];
            weather_update = weather["info_update"];
        }
        weather_error = "Running: " + weather["info_status"]["running"] + "\n";
        if (weather["info_status"]["error"] || weather["info_status"]["running"] == "error") {
            weather_error += "Error: " + weather["info_status"]["error"].toString() + "\n";
            weather_error += "Message: " + weather["info_status"]["error_msg"];
            setHeaderColor(header_id="weather_error", header_color=header_color_error);
            setHeaderColor(header_id="weather_settings", header_color=header_color_error);
            setStatusColor(status_id="status_error_WEATHER", "red");
        }
        else if (weather["info_status"]["running"].indexOf("paused") > -1) {
            setHeaderColor(header_id="weather_error", header_color=header_color_warning);
            setStatusColor(status_id="status_error_WEATHER", "black");
        }
        else {
            setHeaderColor(header_id="weather_settings", header_color="");
            setHeaderColor(header_id="weather_error", header_color="");
            setStatusColor(status_id="status_error_WEATHER", "green");
        }
        if (settings["active"] == true) {
            setStatusColor(status_id="status_active_WEATHER", "white");
            }
        else{
            setStatusColor(status_id="status_active_WEATHER", "black");
            setStatusColor(status_id="status_error_WEATHER", "black");
        }
    }
    if (entry != "") { weather_footer.push(entry); }
    setTextById("weather_info_icon", weather_icon);
    setTextById("weather_info_update", weather_update);
    setTextById("weather_info_error", weather_error);

    coordinates = "(" + settings["gps_coordinates"].toString().replaceAll(",", ", ") + ")";
    setTextById("gps_coordinates", coordinates);
}

/*
* read latest sensor status information and fill respective placeholders with information if exist
*
* @param (dict) data: response from API status request
*/
function birdhouseStatus_sensors(data) {
    // add sensor information
    var sensors         = data["SETTINGS"]["devices"]["sensors"];
    var status_dev      = data["STATUS"]["devices"];

    var sensor_status   = status_dev["sensors"];
    var keys            = Object.keys(sensors);
    for (let sensor in sensors) {
        if (sensor_status[sensor]) {
            //var status = sensors[sensor]["status"];
            var status = sensor_status[sensor];
            var sensor_error_01 = status["error_msg"]; //.join(",\n");
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
            setTextById("status_sensor_last_"+sensor, Math.round(status["last_read"]*10)/10 +"s");
            if (status["running"] == "OK") {
                setStatusColor(status_id="status_active_"+sensor, "white");
            }
            else {
                setStatusColor(status_id="status_active_"+sensor, "black");
            }
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
}

/*
* read latest microphone status information and fill respective placeholders with information if exist
*
* @param (dict) data: response from API status request
*/
function birdhouseStatus_microphones(data) {
    // add micro information
    var microphones  = app_data["STATUS"]["devices"]["microphones"];
    var keys = Object.keys(microphones);
    for (let micro in microphones) {
        if (microphones[micro]["active"])        { setStatusColor(status_id="status_active_"+micro, "white"); }
        else                                     { setStatusColor(status_id="status_active_"+micro, "black"); }
        if (microphones[micro]["active_stream"]) { setTextById("show_stream_count_"+micro, 1); }
        else                                     { setTextById("show_stream_count_"+micro, 0); }
        if (microphones[micro]["error"])  {
            setStatusColor(status_id="status_error_"+micro, "red");
            setHeaderColor(header_id=micro, header_color=header_color_error);
            setHeaderColor(header_id=micro+"_error", header_color=header_color_error);
            }
        else if (microphones[micro]["active"]) {
            setStatusColor(status_id="status_error_"+micro, "green");
            setHeaderColor(header_id=micro+"_error", header_color="");
            }
        else {
            setStatusColor(status_id="status_error_"+micro, "black");
            setHeaderColor(header_id=micro, header_color="");
            setHeaderColor(header_id=micro+"_error", header_color="");
            }

        setTextById("info_micro_"+micro, "Connected=" + microphones[micro]["connected"] + "; " +
                                         "Error=" + microphones[micro]["error"] + "; " +
                                         "Last_active=" + Math.round(microphones[micro]["last_active"]*10)/10 + "s; " +
                                         "Last_reload=" + Math.round(microphones[micro]["last_reload"]*10)/10 + "s; "
                                         );
        setTextById("error_micro_"+micro, microphones[micro]["error_msg"].join("<br/>"))
    }
}

/*
* check a bunch of system status information and fill respective placeholders with status information (if exist)
* this includes the following information: DB connection; health check; usage of memory, hdd and cpu; ...
*
* @param (dict) data: response from API status request
*/
function birdhouseStatus_system(data) {
    var settings   = data["SETTINGS"]["server"];
    var status_sys = data["STATUS"]["system"];
    var status_srv = data["STATUS"]["server"];
    var status_db  = data["STATUS"]["database"];
    var start_time = data["STATUS"]["start_time"];
    var show_error = false;

    // add database information
    var db_info = "type=" + settings["database_type"]+"; ";
    if (settings["database_type"] == "couch") { db_info += "connected=" + status_db["db_connected_couch"]; }
    setTextById("system_info_database", db_info);

    // db error
    if (!status_db["db_connected"] || status_db["db_connected"].toString().indexOf("False") >= 0) {
        setTextById("system_info_db_connection", "<font color='red'>Error: " + status_db["db_connected"] + " (" + status_db["type"] + ")</font>");
        show_error = true;
        }
    else {
        setTextById("system_info_db_connection", "Connected: " + status_db["type"]);
        }
    if (status_db["handler_error"] == true || status_db["handler_error"].toString().indexOf("True") >= 0) {
        setTextById("system_info_db_handler", "<font color='red'>Error:</font> " + status_db["handler_error_msg"].toString());
        show_error = true;
        }
    else {
        setTextById("system_info_db_handler", "OK");
        }
    if (status_db["db_error"] == true || status_db["db_error"].toString( ).indexOf("True") >= 0) {
        setTextById("system_info_db_error", "<font color='red'>Error: " + status_db["db_error"] + "</font> " + status_db["db_error_msg"].join("<br/>"));
        show_error = true;
        }
    else {
        setTextById("system_info_db_error", "OK");
        }

    // health check
    if (status_srv["health_check"] != "OK" && status_srv["health_check"] != undefined) {
        setTextById("system_health_check", "<font color='red'>" + status_srv["health_check"] + "</font>");
        show_error = true;
        }
    else if (status_srv["health_check"] == undefined) {
        setTextById("system_health_check", "starting");
        }
    else {
        setTextById("system_health_check", status_srv["health_check"]);
        }

    // add system information
    percentage_1 = (status_sys["mem_used"]/status_sys["mem_total"])*100;
    percentage_2 = (status_sys["hdd_used"]/status_sys["hdd_total"])*100;
    setTextById("system_info_mem_total",        (Math.round(status_sys["mem_total"]*10)/10)+" MB");
    setTextById("system_info_mem_used",         (Math.round(status_sys["mem_used"]*10)/10)+" MB (" + Math.round(percentage_1) + "%)");
    setTextById("system_info_cpu_usage",        (Math.round(status_sys["cpu_usage"]*10)/10)+"%");
    setTextById("system_info_cpu_temperature",  (Math.round(status_sys["cpu_temperature"]*10)/10)+"°C");
    setTextById("system_info_hdd_used",         (Math.round(status_sys["hdd_used"]*10)/10)+" GB (" + Math.round(percentage_2) + "%)");
    setTextById("system_info_hdd_archive",      (Math.round(status_sys["hdd_archive"]*10)/10)+" GB");
    setTextById("system_info_hdd_data",         (Math.round(status_sys["hdd_data"]*10)/10)+" GB");
    setTextById("system_info_hdd_total",        (Math.round(status_sys["hdd_total"]*10)/10)+" GB");
    setTextById("system_info_connection",       "Connected");
    setTextById("system_info_start_time",       start_time);
    setTextById("server_start_time",            lang("STARTTIME") + ": " + start_time);
    setTextById("system_queue_wait",            (Math.round(status_srv["queue_waiting_time"]*10)/10) + "s");

    if (show_error || app_connection_error) {
        if (getTextById("server_info_header") != loading_dots_red) {
            setTextById("server_info_header", loading_dots_red);
            }
        }
    else {
        setTextById("server_info_header", "");
        }

    var cpu_details = "";
    if (status_sys["cpu_usage_detail"]) {
        for (var i=0;i<status_sys["cpu_usage_detail"].length;i++) {
            cpu_details += "cpu"+i+"="+Math.round(status_sys["cpu_usage_detail"][i])+"%, ";
            }
        setTextById("system_info_cpu_usage_detail", cpu_details);
        }
}

/*
* check if views are still loading and fill respective placeholders with status information (if exist)
*
* @param (dict) data: response from API status request
* @param (string) view: specific view
* @return (string): loading status if specific view is set
*/
function birdhouseStatus_loadingViews(data, view="") {
    var views = ["object", "archive", "favorite"];

    if (view == "") {
        for (var i=0;i<views.length;i++) {
            var status = data["STATUS"]["server"]["view_"+views[i]+"_loading"];
            var progress = data["STATUS"]["server"]["view_"+views[i]+"_progress"];
            if (status == "in progress") {
                setTextById("loading_status_"+views[i], progress);
                setTextById("processing_"+views[i]+"_view", progress);
                app_processing_active = true;
            }
            else if (status == "started") {
                setTextById("loading_status_"+views[i], lang("WAITING"));

                if (views[i] != "object" || data["STATUS"]["object_detection"]["active"]) {
                    setTextById("processing_"+views[i]+"_view", lang("WAITING"));
                    app_processing_active = true;
                    }
            }
            else if (status == "done") {
                setTextById("loading_status_"+views[i], lang("DONE"));
                setTextById("processing_"+views[i]+"_view", lang("INACTIVE"));
            }
        }
    }
    else {
         return data["STATUS"]["server"]["view_"+view+"_loading"];
    }
}

/*
* check running object detection and fill respective placeholders with status information
*
* @param (dict) data: response from API status request
*/
function birdhouseStatus_detection(data) {

    if (data["STATUS"]["object_detection"]["progress"]) {
        message_1 = data["STATUS"]["object_detection"]["progress"] + " %";
        message_2 = message_1;
        if (data["STATUS"]["object_detection"]["waiting"] > 1) {
            message_1 += "<br/><i>(" + lang("WAITING_DATES", [data["STATUS"]["object_detection"]["waiting"]]) + ")</i>";
            message_2 += " &nbsp; <i>(" + lang("WAITING_DATES", [data["STATUS"]["object_detection"]["waiting"]]) + ")</i>";
            }
        else if (data["STATUS"]["object_detection"]["waiting"] == 1) {
            message_1 += "<br/><i>(" + lang("WAITING_DATE") + ")</i>";
            message_2 += " &nbsp; <i>(" + lang("WAITING_DATE") + ")</i>";
            }
        setTextById("last_answer_detection_progress", message_1);
        setTextById("processing_object_detection", message_2);
        app_processing_active = true;
        }
    else if (data["STATUS"]["object_detection"]["progress"] != undefined && data["STATUS"]["object_detection"]["waiting"] == 0) {
        setTextById("processing_object_detection", lang("INACTIVE"));
        }

    var status   = app_data["STATUS"]["object_detection"];
    var settings = app_data["SETTINGS"]["devices"]["cameras"];

    Object.entries(settings).forEach(([key,value])=> {
        if (value["object_detection"]["active"])      { setStatusColor("status_" + key + "_detection_active", "white"); }
        else                                          { setStatusColor("status_" + key + "_detection_active", "black"); }

        if (!value["object_detection"]["active"])     { setStatusColor("status_" + key + "_detection_loaded", "black"); }
        else if (status["models_loaded_status"][key]) { setStatusColor("status_" + key + "_detection_loaded", "green"); }
        else                                          { setStatusColor("status_" + key + "_detection_loaded", "red"); }
        });

    }

/*
* check recording status and set recording buttons on index view
*
* @param (dict) data: response from API status request
*/
function birdhouseStatus_recordButtons(data) {
    status_data  = data["STATUS"]["video_recording"];
    p_video      = document.getElementById("processing_video");
    p_video_info = "";

    Object.entries(status_data).forEach(([key,value]) => {
        b_start  = document.getElementById("rec_start_"+key);
        b_stop   = document.getElementById("rec_stop_"+key);
        b_cancel = document.getElementById("rec_cancel_"+key);

        if (p_video != undefined) {
            p_video_info += key.toUpperCase() + ": ";
            if (value["error"])                                   { p_video_info += "error "; }
            else if (!value["processing"] && !value["recording"]) { p_video_info += "inactive"; }
            else if (value["active"])                             { p_video_info += "OK "; }

            if (value["recording"])       { p_video_info += "; recording (" + value["info"]["length"] + "s)<br/>"; }
            else if (value["processing"]) { p_video_info += "; processing (" + value["info"]["percent"] + "%)<br/>"; }
            else                          { p_video_info += "<br/>"}
            }

        if (b_start != undefined) {
            if (!value["active"])           { b_start.disabled = "disabled"; b_start.style.color = "white";}
            else if (value["recording"])    { b_start.disabled = "disabled"; b_start.style.color = "red"; }
            else if (value["processing"])   { b_start.disabled = "disabled"; b_start.style.color = "yellow"; }
            else                            { b_start.disabled = ""; b_start.style.color = "lightgray"; }
            }
        if (b_stop != undefined) {
            if (value["recording"])         { b_stop.disabled = ""; }
            else                            { b_stop.disabled = "disabled"; }
            }
        if (b_cancel != undefined) {
            if (value["recording"] || value["processing"])        { b_cancel.disabled = ""; }
            else if (!value["recording"] && !value["processing"]) { b_cancel.disabled = "disabled"; }
            else                                                  { b_cancel.disabled = "disabled"; }
            }
    });

    if (p_video_info == "") { p_video_info = "inactive"; }
    setTextById("processing_video", p_video_info);
}

/*
* check running download preparation processes and fill respective placeholders with status information
*
* @param (dict) data: response from API status request
*/
function birdhouseStatus_downloads(data) {
    if (data["STATUS"]["server"]["downloads"] != {}) {
        var all_links_1 = "";
        var all_links_2 = "<ul>";
        var count_processes = 0;
        var count_downloads = 0;
        Object.entries(data["STATUS"]["server"]["downloads"]).forEach(([key,value]) => {
            if (value.indexOf("in progress") > 0)   { var link = "<i>" + lang("WAITING") + "</i>"; count_processes += 1; }
            else                                    { var link = "<a href='"+value+"'>"+value+"</a>"; count_downloads += 1; }
            all_links_1 += link + "<br/>";
            all_links_2 += "<li>" + link + "</li>";
            setTextById("archive_download_link_" + key, link);
            });
        all_links_2 += "</ul>";
        var message = count_processes + " Downloads under preparation. <br/>" + count_downloads + " Download ready: <br/>";
        message    += all_links_2;
        setTextById("archive_download_link", all_links_1);
        }
    if (count_downloads + count_processes > 0)  { setTextById("processing_downloads", message); app_processing_active = true; }
    else                                        { setTextById("processing_downloads", lang("INACTIVE")); }

    collect4download_amount = app_collect_list.length;
    setTextById("collect4download_amount", collect4download_amount);
    setTextById("collect4download_amount2", collect4download_amount);
    }

/*
* check running processes and fill respective placeholders with status information (if exist)
*
* @param (dict) data: response from API status request
*/
function birdhouseStatus_processing(data) {
    var process_information = {
        "Object Detection":                 "processing_object_detection",
        "Download preparation":             "processing_downloads",
        "Loading archive view":             "processing_archive_view",
        "Loading favorite view":            "processing_favorite_view",
        "Loading object detection view":    "processing_object_view",
        "Video recording / processing":     "processing_video"
    }

    if (data["STATUS"]["server"]["backup_process_running"])     { setTextById("processing_backup", lang("ACTIVE")); app_processing_active = true; }
    else                                                        { setTextById("processing_backup", lang("INACTIVE")); }

    if (app_processing_active) {
        var text = getTextById("processing_info_header");
        if (text != loading_dots_green) {
            setTextById("processing_info_header", loading_dots_green);
            }
        }
    else { setTextById("processing_info_header", ""); }
}


app_scripts_loaded += 1;