//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// show status functions
//--------------------------------------

var header_color_error      = "#993333";
var header_color_ok         = "#339933";
var header_color_warning    = "#666633";
var header_color_default    = "";
var weather_footer = [];
var loading_dots_red   = '<span class="loading-dots"><span class="dot red"></span><span class="dot red"></span><span class="dot red"></span></span>';
var loading_dots_green = '<span class="loading-dots"><span class="dot green"></span><span class="dot green"></span><span class="dot green"></span></span>';
var app_processing_active = false;
var app_active_processes = {};
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
    var relays      = app_data["SETTINGS"]["devices"]["relays"];

    setTextById("system_info_connection", "<font color='red'><b>Connection lost!</b></font>");

    for (let camera in cameras) {
        setStatusColor(status_id="status_active_"+camera, "red");
        setStatusColor(status_id="status_error_"+camera, "black");
        setStatusColor(status_id="status_error_record_"+camera, "black");

        setStatusColor(status_id="status_active_"+camera+"_object", "red");
        setStatusColor(status_id="status_error_"+camera+"_object", "black");

        setStatusColor(status_id="status_"+camera+"_detection_active", "red");
        setStatusColor(status_id="status_"+camera+"_detection_loaded", "black");
    }
    for (let sensor in sensors) {
        setStatusColor(status_id="status_active_"+sensor, "red");
        setStatusColor(status_id="status_error_"+sensor, "black");
    }
    for (let relay in relays) {
        setStatusColor(status_id="status_active_"+relay, "red");
        setStatusColor(status_id="status_error_"+relay, "black");
    }
    for (let micro in microphones) {
        setStatusColor(status_id="status_active_"+micro, "red");
        setStatusColor(status_id="status_error_"+micro, "black");
    }

    setStatusColor(status_id="status_active_WEATHER", "red");
    setStatusColor(status_id="status_error_WEATHER", "black");

    birdhouse_settings.server_dashboard_fill(app_data);
}

/*
* Orchestration of all status functions
*
* @param (dict) data: response from API status request
*/
function birdhouseStatus_print(data) {
    //if (!data["STATUS"]) { data["STATUS"] = app_data["STATUS"]; }
    console.debug("Update Status ("+app_active.page+") ...");
    setTextById("navActive", app_active.page);

    if (data["STATUS"]["admin_allowed"] != false)   { app_admin_allowed = true; }
    else {
        app_session_id_count += 1;
        if (app_session_id_count > 2 && app_session_id != "") {
            birdhouse_logout();
            app_session_id_count = 0;
            if (app_pages_admin.includes(app_active.page)) { birdhousePrint_page("INDEX"); }
        }
    }

    var pages_content   = ["INDEX", "OBJECTS", "FAVORITES", "ARCHIVE", "TODAY", "TODAY_COMPLETE", "WEATHER"];
    var pages_settings  = ["SETTINGS", "SETTINGS_CAMERAS", "SETTINGS_DEVICES", "SETTINGS_IMAGE", "SETTINGS_STATISTICS", "SETTINGS_INFORMATION"];

    // set latest status data to var app_data
    //app_data       = data;
    weather_footer = [];
    app_server_error = false;

    // check page length vs. screen height
    var body = document.body, html = document.documentElement;
    var height = Math.max( body.scrollHeight, body.offsetHeight, html.clientHeight, html.scrollHeight, html.offsetHeight );

    if (height > 1.5 * document.body.clientHeight)          { elementVisible("move_up"); }
    else                                                    { elementHidden("move_up"); }

    if (appSettings.loaded_index)                           { setTextById("device_status_short", birdhouseDevices("", data, "short")); appSettings.loaded_index = false; }

    if (pages_settings.includes(app_active.page))           { birdhouseStatus_system(data); }
    if (pages_settings.includes(app_active.page))           { birdhouseStatus_processing(data); }
    if (pages_settings.includes(app_active.page))           { birdhouseStatus_relays(data); }
    if (pages_settings.includes(app_active.page))           { birdhouse_settings.server_dashboard_fill(data); }

    if (app_active.page == "INDEX" || "SETTINGS_CAMERAS")   { birdhouseStatus_cameras(data); }
    if (app_active.page == "INDEX" || "SETTINGS_CAMERAS")   { birdhouseStatus_microphones(data); }

    if (app_active.page == "INDEX" ||
        pages_settings.includes(app_active.page))           { birdhouseStatus_recordVideo(data); }
    if (pages_settings.includes(app_active.page))           { birdhouseStatus_createVideoDay(data); }
    if (pages_content.includes(app_active.page))            { birdhouseStatus_loadingViews(data); }
    if (app_active.page == "ARCHIVE" || "TODAY")            { birdhouseStatus_downloads(data); }
    if (app_active.page == "ARCHIVE" || "TODAY")            { birdhouseStatus_detection(data); }

    if (pages_settings.includes(app_active.page))           { birdhouseStatus_weather(data); }
    else if (app_active.page == "WEATHER")                  { birdhouseStatus_weather(data); }
    else if (pages_content.includes(app_active.page))       { birdhouseStatus_weather(data, "content"); }

    if (pages_settings.includes(app_active.page))           { birdhouseStatus_sensors(data); }
    else if (pages_content.includes(app_active.page))       { birdhouseStatus_sensors(data, "content"); }

    //document.getElementById(app_frame.info).style.display = "block";
    html = "<center><i><font color='gray'>";
    html += weather_footer.join("&nbsp;&nbsp;/&nbsp;&nbsp;");
    html += "</font></i></center>";
    setTextById(app_frame.info, html);
    setTextById("server_start_time", lang("STARTTIME") + ": " + data["STATUS"]["start_time"]);
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
    var camera_offset   = [];
    var camera_amount   = cameras.length;

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

            // check offset settings
            if (document.getElementById("set_record_offset_"+camera)) {
                camera_offset.push(document.getElementById("set_record_offset_"+camera).value);
                if (camera_offset.length == 2) { if (camera_offset[0] == camera_offset[1]) { appMsg.alert(lang("ERROR_SAME_OFFSET")); } }
                if (camera_offset.length == 3) { if (camera_offset[0] == camera_offset[1] || camera_offset[1] == camera_offset[2] || camera_offset[0] == camera_offset[2]) { appMsg.alert(lang("ERROR_SAME_OFFSET")); } }
                }

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

    var camera_status   = data["DATA"]["camera_properties"];
    if (camera_status["properties"]) {
        for (let key in camera_status["properties"]) {
            var prop_text = camera_status["properties"][key][0];
            setTextById("prop_" + key.toLowerCase() + "_" + camera, prop_text);
            if (document.activeElement != document.getElementById("set_" + key.toLowerCase() + "_" + camera)
                    && document.activeElement != document.getElementById("set_" + key.toLowerCase() + "_" + camera + "_range")) {

                setValueById("set_" + key.toLowerCase() + "_" + camera, camera_status["properties"][key][0]);
                setValueById("set_" + key.toLowerCase() + "_" + camera + "_range", camera_status["properties"][key][0]);

                if (document.getElementById("set_" + key.toLowerCase() + "_" + camera + "_range")) {
                    document.getElementById("set_" + key.toLowerCase() + "_" + camera + "_range").className = "bh-slider start";
                    }
                }
            //console.error(key + ":" + camera_status[camera]["properties"][key].toString());
        }
        for (let key in camera_status["properties_image"]) {
            setTextById("img_" + key + "_" + camera, Math.round(camera_status["properties_image"][key]*100)/100);
            //console.error(key + ":" + camera_status[camera]["properties"][key].toString());
        }
    }
    if (camera_status["properties_new"]) {
        for (let key in camera_status["properties_new"]) {
            var prop_text = JSON.stringify(camera_status["properties_new"][key][0]);
            setTextById("prop_" + key.toLowerCase() + "_" + camera, prop_text.replaceAll(",", ",  "));
            setTextById("prop_" + key.toLowerCase() + "_" + camera, prop_text.replaceAll(",", ",  "));
            if (document.activeElement != document.getElementById("set_" + key + "_" + camera)
                    && document.activeElement != document.getElementById("set_" + key.toLowerCase() + "_" + camera + "_range")) {

                var data_type  = "";
                if (document.getElementById("set_" + key.toLowerCase() + "_" + camera + "_data_type")) {
                    data_type = document.getElementById("set_" + key.toLowerCase() + "_" + camera + "_data_type").value;
                    }

                var data_value = camera_status["properties_new"][key][0];
                var data_class = "start";
                var data_true  = [1, "True", "true", true];
                var data_false = [0, "False", "false", false];
                if (data_type == "boolean" && data_true.includes(data_value))    { data_value = 1; data_class = "on"; }
                if (data_type == "boolean" && data_false.includes(data_value)) { data_value = 0; data_class = "off"; }

                setValueById("set_" + key.toLowerCase() + "_" + camera, data_value);
                setValueById("set_" + key.toLowerCase() + "_" + camera + "_range", data_value);
                setValueById("set_" + key.toLowerCase() + "_" + camera, data_value);
                setValueById("set_" + key.toLowerCase() + "_" + camera + "_range", data_value);

                if (document.getElementById("set_" + key.toLowerCase() + "_" + camera + "_range")) {
                    document.getElementById("set_" + key.toLowerCase() + "_" + camera + "_range").className = "bh-slider " + data_class;
                    }
                }
            //console.error(key + ":" + camera_status[camera]["properties"][key].toString());
        }
    }
}

/*
* read latest weather information and fill respective placeholders with weather information if exist
*
* @param (dict) data: response from API status request
*/
function birdhouseStatus_weather(data, type="all") {
    // weather information
    var weather         = data["STATUS"]["weather"];
    var settings        = data["SETTINGS"]["devices"]["weather"];

    var entry           = "";
    var weather_icon    = "<small>N/A</small>";
    var weather_update  = "N/A";
    var weather_error   = "";

    if (weather["current"] && weather["current"]["description_icon"]) {
        if (settings["active"]) {
            if (weather["info_city"] != "")             { entry = weather["info_city"] + ": " + weather["current"]["temperature"] + "°C"; }
            else if (weather["info_module"]["name"])    { entry = weather["info_module"]["name"] + ": " + weather["current"]["temperature"] + "°C"; }
            else                                        { entry = "Internet: " + weather["current"]["temperature"] + "°C"; }
            entry = "<big>" + weather["current"]["description_icon"] + "</big> &nbsp; " + entry;
            weather_icon = weather["current"]["description_icon"];
            weather_update = weather["info_update"];
        }
        if (type == "all") {
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
        setTextById("weather_info_icon", weather_icon);
        setTextById("weather_info_update", weather_update);
        setTextById("weather_info_error", weather_error);

        coordinates = "(" + settings["gps_coordinates"].toString().replaceAll(",", ", ") + ")";
        setTextById("gps_coordinates", coordinates);
    }

    if (entry != "") { weather_footer.push(entry); }
}

/*
* check relay status and fill respective placeholder with this information if exists
*
* @param (dict) data: response from API status request
*/
function birdhouseStatus_relays(data) {

    var relay_status   = data["STATUS"]["devices"]["relays"];
    var relay_settings = data["SETTINGS"]["devices"]["relays"];

    for (let relay in relay_status) {
        var raw_status = relay_status[relay];
        var status     = ".";
        if (raw_status == false) { status = "OFF"; } else { status = "ON"; }
        setTextById("relay_status_" + relay, status);
        setTextById("relay_status_long_" + relay, lang("STATUS") + ": " + status);
        setTextById("relay_raw_status_" + relay, raw_status);

        if (relay_settings[relay]["active"]) { setStatusColor(status_id="status_active_"+relay, "white"); }
        else                                 { setStatusColor(status_id="status_active_"+relay, "black"); }
        }
    }

/*
* read latest sensor status information and fill respective placeholders with information if exist
*
* @param (dict) data: response from API status request
*/
function birdhouseStatus_sensors(data, type="all") {
    // add sensor information
    var sensors         = data["SETTINGS"]["devices"]["sensors"];
    var status_dev      = data["STATUS"]["devices"];

    var sensor_status   = status_dev["sensors"];
    var keys            = Object.keys(sensors);
    for (let sensor in sensors) {
        if (type == "all") {
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
    setTextById("system_info_db_cache", status_db["cache_active"]);
    setTextById("system_info_db_cache_archive", status_db["cache_archive_active"]);

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
                app_active_processes["processing_"+views[i]+"_view"] = true;
            }
            else if (status == "started") {
                setTextById("loading_status_"+views[i], lang("WAITING"));

                if (views[i] != "object" || data["STATUS"]["object_detection"]["active"]) {
                    setTextById("processing_"+views[i]+"_view", lang("WAITING"));
                    app_active_processes["processing_"+views[i]+"_view"] = true;
                    }
            }
            else if (status == "done") {
                setTextById("loading_status_"+views[i], lang("DONE"));
                setTextById("processing_"+views[i]+"_view", lang("INACTIVE"));
                app_active_processes["processing_"+views[i]+"_view"] = false;
            }
            else {
                app_active_processes["processing_"+views[i]+"_view"] = false;
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
    var i = 0;
    var message = "";
    var detection_cameras = data["STATUS"]["object_detection"]["processing_info"];
    var settings = app_data["SETTINGS"]["devices"]["cameras"];
    console.debug("Detection Status - processing: " + data["STATUS"]["object_detection"]["processing"] + " / " +
                  "progress: " + data["STATUS"]["object_detection"]["progress"] + " / waiting: " + data["STATUS"]["object_detection"]["waiting"]);


    if (detection_cameras != undefined && document.getElementById("processing_object_detection") != undefined) {
        Object.entries(detection_cameras).forEach(([key,value])=> {
            i++;
            message += key.toUpperCase() + ": ";
            if (detection_cameras[key] && detection_cameras[key]["active"] && detection_cameras[key]["processing"]) {
                message += "OK processing <b>" + detection_cameras[key]["progress"] + "%</b> "
                message += "(" + detection_cameras[key]["model"] + " | waiting: " + detection_cameras[key]["waiting"] + ")";
                app_active_processes["processing_object_detection_"+key] = true;
                }
            else if (detection_cameras[key] && detection_cameras[key]["active"]) {
                message += lang("INACTIVE");
                app_active_processes["processing_object_detection_"+key] = false;
                }
            else {
                message += "N/A";
                app_active_processes["processing_object_detection_"+key] = false;
                }
            message += "<br/>";
            });
        setTextById("processing_object_detection", message);
        }

    if (document.getElementById("last_answer_detection_progress") != undefined) {
        if (data["STATUS"]["object_detection"]["processing"]) {
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
            }
        }

    var status   = app_data["STATUS"]["object_detection"];

    Object.entries(settings).forEach(([key,value])=> {
        if (value["object_detection"]["active"])      { setStatusColor("status_" + key + "_detection_active", "white"); }
        else                                          { setStatusColor("status_" + key + "_detection_active", "black"); }

        if (value["object_detection"]["active"])      { setStatusColor("status_active_" + key + "_object", "white"); }
        else                                          { setStatusColor("status_active_" + key + "_object", "black"); }

        if (!value["object_detection"]["active"])     { setStatusColor("status_" + key + "_detection_loaded", "black"); }
        else if (status["models_loaded_status"][key]) { setStatusColor("status_" + key + "_detection_loaded", "green"); }
        else                                          { setStatusColor("status_" + key + "_detection_loaded", "red"); }

        if (!value["object_detection"]["active"])     { setStatusColor("status_error_" + key + "_object", "black"); }
        else if (status["models_loaded_status"][key]) { setStatusColor("status_error_" + key + "_object", "green"); }
        else                                          { setStatusColor("status_error_" + key + "_object", "red"); }
        });

    }

/*
* check recording status and set recording buttons on index view
*
* @param (dict) data: response from API status request
*/
function birdhouseStatus_recordVideo(data) {
    var status_data  = data["STATUS"]["video_recording"];
    var p_video      = document.getElementById("processing_video");
    var p_video_info = "";

    Object.entries(status_data).forEach(([key,value]) => {
        b_start  = document.getElementById("rec_start_"+key);
        b_stop   = document.getElementById("rec_stop_"+key);
        b_cancel = document.getElementById("rec_cancel_"+key);

        if (p_video != undefined) {
            p_video_info += key.toUpperCase() + ": ";
            if (value["error"])                                   { p_video_info += "N/A "; }
            else if (!value["processing"] && !value["recording"]) { p_video_info += lang("INACTIVE"); }
            else if (value["active"])                             { p_video_info += "OK "; }

            if (value["recording"])         {
                p_video_info += "; recording <b>" + value["info"]["length"] + "s</b><br/>";
                app_active_processes["processing_video_"+key] = true;
                }
            else if (value["processing"])   {
                p_video_info += "; processing <b>" + Math.round(value["info"]["percent"]*10)/10 + "%</b><br/>";
                app_active_processes["processing_video_"+key] = true;
                }
            else                            {
                p_video_info += "<br/>";
                app_active_processes["processing_video_"+key] = false;
                }
            console.debug("-> Status recordVideo");
            console.debug(value);
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
* check status of video creation for a day and include it into processing view
*
* @param (dict) data: response from API status request
*/
function birdhouseStatus_createVideoDay(data) {
    var status_data  = data["STATUS"]["video_creation_day"];
    var p_video      = document.getElementById("processing_video_day");
    var p_video_info = "";

    Object.entries(status_data).forEach(([key,value]) => {

        if (p_video != undefined) {
            p_video_info += key.toUpperCase() + ": ";
            if (value["error"])             { p_video_info += "N/A "; }
            else if (!value["processing"])  { p_video_info += "inactive"; }
            else if (value["active"])       { p_video_info += "OK "; }

            if (value["processing"])        {
                p_video_info += "; processing <b>" + Math.round(value["info"]["percent"]*10)/10 + "%</b><br/>";
                app_active_processes["processing_video_day_"+key] = true;
                }
            else                            {
                app_active_processes["processing_video_day_"+key] = false;
                p_video_info += "<br/>"
                }

            console.debug("-> Status createVideoDay");
            console.debug(value);
            }
    });

    if (p_video_info == "") { p_video_info = "inactive"; }
    setTextById("processing_video_day", p_video_info);
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
    if (count_downloads + count_processes > 0)  {
        setTextById("processing_downloads", message);
        }
    else {
        setTextById("processing_downloads", lang("INACTIVE"));
        }
    if (count_processes > 0)    { app_active_processes["processing_downloads"] = true; }
    else                        { app_active_processes["processing_downloads"] = false; }

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
        "Download preparation":             "processing_downloads",             // OK
        "Loading archive view":             "processing_archive_view",          // OK
        "Loading favorite view":            "processing_favorite_view",         // OK
        "Loading object detection view":    "processing_object_view",           // OK
        "Video recording":                  "processing_video",                 // OK
        "Video creation day":               "processing_video_day"              // OK
    }

    if (data["STATUS"]["server"]["backup_process_running"])     {
        setTextById("processing_backup", lang("ACTIVE"));
        app_active_processes["processing_backup"] = true;
        }
    else {
        setTextById("processing_backup", lang("INACTIVE"));
        app_active_processes["processing_backup"] = false;
        }

    var active_processes    = "";
    app_processing_active = false;
    Object.keys(app_active_processes).forEach( key => {
        if (app_active_processes[key] == true) {
            active_processes += key + ", ";
            app_processing_active = true;
            }
    });

    if (app_processing_active) {
        var text = getTextById("processing_info_header");
        if (text != loading_dots_green) {
            setTextById("processing_info_header", loading_dots_green);
            }
        console.log("Active processes: " + active_processes);
        }
    else { setTextById("processing_info_header", ""); }
}


app_scripts_loaded += 1;