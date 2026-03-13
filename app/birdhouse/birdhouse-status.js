//--------------------------------------
// jc://birdhouse/status/
//--------------------------------------

/*
* class to check an visualize status information
*/
class BirdhouseStatus {

    constructor(name) {
        this.name = name;

        this.header_color_error   = "#993333";
        this.header_color_ok      = "#339933";
        this.header_color_warning = "#666633";

        this.weather_footer = [];

        this.loading_dots_red = '<span class="loading-dots"><span class="dot red"></span><span class="dot red"></span><span class="dot red"></span></span>';
        this.loading_dots_green = '<span class="loading-dots"><span class="dot green"></span><span class="dot green"></span><span class="dot green"></span></span>';

        this.app_processing_active = false;
        this.app_active_processes  = {};
    }

    /*
    * change the color of a group header
    */
    setHeaderColor(header_id, header_color = "") {
        let header = document.getElementById("group_header_" + header_id);
        if (header) {
            header.style.background = header_color;
        }
    }

    /*
    * change the color of an status bullet
    */
    setStatusColor(status_id, status_color) {
        let status = "<div id='" + status_color + "'></div>";
        setTextById(status_id, status);
    }

    /*
    * connection error handler
    */
    connectionError() {

        let cameras     = app_data["SETTINGS"]["devices"]["cameras"];
        let microphones = app_data["SETTINGS"]["devices"]["microphones"];
        let sensors     = app_data["SETTINGS"]["devices"]["sensors"];
        let relays      = app_data["SETTINGS"]["devices"]["relays"];

        setTextById("system_info_connection", "<span style='color:red'><b>Connection lost!</b></span>");

        for (let camera in cameras) {

            this.setStatusColor("status_active_" + camera, "red");
            this.setStatusColor("status_error_" + camera, "black");
            this.setStatusColor("status_error_record_" + camera, "black");

            this.setStatusColor("status_active_" + camera + "_object", "red");
            this.setStatusColor("status_error_" + camera + "_object", "black");

            this.setStatusColor("status_" + camera + "_detection_active", "red");
            this.setStatusColor("status_" + camera + "_detection_loaded", "black");
        }

        for (let sensor in sensors) {
            this.setStatusColor("status_active_" + sensor, "red");
            this.setStatusColor("status_error_" + sensor, "black");
        }

        for (let relay in relays) {
            this.setStatusColor("status_active_" + relay, "red");
            this.setStatusColor("status_error_" + relay, "black");
        }

        for (let micro in microphones) {
            this.setStatusColor("status_active_" + micro, "red");
            this.setStatusColor("status_error_" + micro, "black");
        }

        this.setStatusColor("status_active_WEATHER", "red");
        this.setStatusColor("status_error_WEATHER", "black");

        bhSettings.server_dashboard_fill(app_data);
    }

    /*
    * Orchestration of all status functions
    */
    print(data) {

        console.debug("Update Status (" + app_active.page + ") ...");
        setTextById("navActive", app_active.page);

        if (data["STATUS"]["admin_allowed"] !== false) {
            app_admin_allowed = true;
        }
        else {

            app_session_id_count += 1;

            if (app_session_id_count > 2 && app_session_id !== "") {
                birdhouse_logout();
                app_session_id_count = 0;

                if (app_pages_admin.includes(app_active.page)) {
                    birdhousePrint_page("INDEX");
                }
            }
        }


        const pages_content = [
            "INDEX","OBJECTS","FAVORITES","ARCHIVE",
            "TODAY","TODAY_COMPLETE","WEATHER"
        ];

        const pages_settings = [
            "SETTINGS","SETTINGS_CAMERAS","SETTINGS_DEVICES",
            "SETTINGS_IMAGE","SETTINGS_STATISTICS",
            "SETTINGS_INFORMATION"
        ];


        // reload title
        let reload_icon = document.getElementById("reload_page");

        if (reload_icon) {

            let page = app_active.page;

            if (app_active.date !== "" && page === "TODAY") {
                page = "ARCHIVE";
            }

            if (app_active.date !== "") {
                reload_icon.title =
                    page + " | " + app_active.cam + " | " + app_active.date;
            }
            else {
                reload_icon.title =
                    page + " | " + app_active.cam;
            }
        }

        // reset status data
        this.weather_footer = [];

        // page height calculation
        let body = document.body;
        let html = document.documentElement;

        let height = Math.max(
            body.scrollHeight,
            body.offsetHeight,
            html.clientHeight,
            html.scrollHeight,
            html.offsetHeight
        );


        // scroll button
        let scrollY = window.scrollY || window.pageYOffset;

        if (height > 1.2 * document.body.clientHeight && scrollY > 10) {

            elementVisible("moveUp");
            elementHidden("moveUp_off");
        }
        else {

            elementVisible("moveUp_off");
            elementHidden("moveUp");
        }


        // navigation history buttons
        if (app_active_history.length > 1) {

            if (app_active_history_pos + 1 < app_active_history.length) {

                elementVisible("moveBack");
                elementHidden("moveBack_off");
            }
            else {

                elementVisible("moveBack_off");
                elementHidden("moveBack");
            }

            if (app_active_history_pos > 0) {

                elementVisible("moveForth");
                elementHidden("moveForth_off");
            }
            else {

                elementVisible("moveForth_off");
                elementHidden("moveForth");
            }
        }


        if (appSettings.loaded_index) {

            setTextById(
                "device_status_short",
                birdhouseDevices("", data, "short")
            );

            setTextById(
                "app_open_close",
                bhSettings.settings_app_open_close()
            );

            appSettings.loaded_index = false;
        }


        if (pages_settings.includes(app_active.page)) {
            this.system(data);
            this.processing(data);
            this.relays(data);
            bhSettings.server_dashboard_fill(data);
            this.createVideoDay(data);
        }


        // original logic preserved (contains JS bug intentionally)
        if (app_active.page === "INDEX" || "SETTINGS_CAMERAS") {
            this.cameras(data);
            this.microphones(data);
        }


        if (app_active.page === "INDEX" || pages_settings.includes(app_active.page)) {
            this.recordVideo(data);
        }

        if (pages_content.includes(app_active.page)) {
            this.loadingViews(data);
        }

        if (app_active.page === "ARCHIVE" || "TODAY") {
            this.downloads(data);
        }

        if (app_active.page === "ARCHIVE" || "TODAY") {
            this.detection(data);
        }


        if (pages_settings.includes(app_active.page)) {
            this.weather(data);
        }
        else if (app_active.page === "WEATHER") {
            this.weather(data);
        }
        else if (pages_content.includes(app_active.page)) {
            this.weather(data, "content");
        }


        if (pages_settings.includes(app_active.page)) {
            this.sensors(data);
        }
        else if (pages_content.includes(app_active.page)) {
            this.sensors(data, "content");
        }


        // footer weather info
        let html_footer = "<div style=\"text-align: center;font-style: italic; color: gray;\">";
        html_footer += this.weather_footer.join("&nbsp;&nbsp;/&nbsp;&nbsp;");
        html_footer += "</div>";

        setTextById(app_frame.info, html_footer);
        setTextById("server_start_time", lang("STARTTIME") + ": " + data["STATUS"]["start_time"]);
    }

    /*
    * read the latest camera status information and fill respective placeholders
    */
    cameras(data) {
        // add camera information
        const cameras         = data["SETTINGS"]["devices"]["cameras"];
        const camera_status   = data["STATUS"]["devices"]["cameras"];
        let camera_streams  = 0;
        let camera_offset   = [];
        let stream;

        for (let camera in cameras) {
            if (camera_status[camera]) {
                //console.error(camera_status);
                if (camera_status[camera]["active_streams"] === 1) { stream = lang("STREAM"); }
                else { stream = lang("STREAMS"); }

                setTextById("show_stream_count_"+camera, camera_status[camera]["active_streams"] + " " + stream);
                setTextById("show_stream_fps_"+camera,   "("+camera_status[camera]["stream_raw_fps"]+" fps)");
                setTextById("show_stream_info_"+camera,   "("+camera_status[camera]["active_streams"] + ": " + camera_status[camera]["stream_raw_fps"]+"fps)");
                setTextById("show_stream_object_fps_"+camera,   "("+camera_status[camera]["stream_object_fps"]+" fps)");
                camera_streams += cameras[camera]["image"]["current_streams"];

                // consolidate error messages
                let error_stream_info = "";
                for (let stream_id in camera_status[camera]["error_details"]) {
                    error_stream_info += "<b>" + stream_id + ":</b><br/>";
                    if (camera_status[camera]["error_details"][stream_id]) { error_stream_info += "<span style='color:red'>"; }
                    else                                                   { error_stream_info += "<span>"; } //  color='lightgray'

                    let no_error = true;
                    if (camera_status[camera]["error_details"][stream_id])                  { no_error = false; error_stream_info += "ERROR: "; }
                    if (camera_status[camera]["error_details_msg"][stream_id].length > 0)   { no_error = false; error_stream_info += "messages=" + camera_status[camera]["error_details_msg"][stream_id].length + "; "; }
                    if (no_error)                                                           { error_stream_info += "OK: "; }

                    if (stream_id !== "image" && stream_id !== "image_record" && stream_id !== "camera_handler") {
                        error_stream_info += "last_active=" + camera_status[camera]["error_details_health"][stream_id] + "s";
                    }

                    if (camera_status[camera]["error_details"][stream_id] && camera_status[camera]["error_details_msg"][stream_id].length > 0) {
                        let last_msg = camera_status[camera]["error_details_msg"][stream_id].length - 1;
                        error_stream_info += "<br/><i>" + camera_status[camera]["error_details_msg"][stream_id][last_msg] + ";</i> ";
                    }
                    error_stream_info += "</span><br/>";
                }

                setTextById("error_streams_"+camera, error_stream_info);
                setTextById("error_rec_"+camera, camera_status[camera]["record_image_error"]);

                // recording time
                let record_time_info = "from <u>" + camera_status[camera]["record_image_start"] + "</u> to <u>" + camera_status[camera]["record_image_end"] + "</u>";
                if (camera_status[camera]["record_image_start"] === "-1:-1") { record_time_info = "<i>N/A (camera not active)</i>"; }
                setTextById("get_record_image_time_"+camera, record_time_info);

                // check offset settings
                if (document.getElementById("set_record_offset_"+camera)) {
                    camera_offset.push(document.getElementById("set_record_offset_"+camera).value);
                    if (camera_offset.length === 2) { if (camera_offset[0] === camera_offset[1]) { appMsg.alert(lang("ERROR_SAME_OFFSET")); } }
                    if (camera_offset.length === 3) { if (camera_offset[0] === camera_offset[1] || camera_offset[1] === camera_offset[2] || camera_offset[0] === camera_offset[2]) { appMsg.alert(lang("ERROR_SAME_OFFSET")); } }
                }

                // error recording images
                if (camera_status[camera]["error"]) {
                    setTextById("last_image_recorded_"+camera, "Recording inactive due to camera error.");
                }
                else {
                    let record_image_reload;
                    if (!camera_status[camera]["record_image_active"]) { record_image_reload = "INACTIVE"; }
                    else                                               { record_image_reload = Math.round(camera_status[camera]["last_reload"]*10)/10 + "s"; }
                    setTextById("last_image_recorded_" + camera,
                        "last_recorded=" + Math.round(camera_status[camera]["record_image_last"]*10)/10 + "s" + "; last_reload=" + record_image_reload +
                        "<br/>active=" + camera_status[camera]["record_image_active"] + "; " + "error=" + camera_status[camera]["record_image_error"]);
                }

                // camera stream working correctly
                let error_count = 0;
                for (let stream_id in camera_status[camera]["error_details"]) {
                    if (camera_status[camera]["error_details"][stream_id]) { error_count += 1; }
                }
                if (camera_status[camera]["active"] && (camera_status[camera]["error"] || camera_status[camera]["error_details"]["stream_raw"])) {
                    this.setHeaderColor(camera+"_error", this.header_color_error);
                    this.setHeaderColor(camera, this.header_color_error);
                    this.setStatusColor("status_error_"+camera, "red");
                    this.setStatusColor("status_error2_"+camera, "red");
                }
                else if (camera_status[camera]["active"] && error_count > 0) {
                    this.setHeaderColor(camera+"_error", this.header_color_warning);
                    this.setHeaderColor(camera, this.header_color_warning);
                    this.setStatusColor("status_error_"+camera, "yellow");
                    this.setStatusColor("status_error2_"+camera, "yellow");
                }
                else {
                    this.setHeaderColor(camera+"_error", "");
                    this.setHeaderColor(camera, "");
                    this.setStatusColor("status_error_"+camera, "green");
                    this.setStatusColor("status_error2_"+camera, "green");
                }

                // image recording working correctly
                if (camera_status[camera]["record_image_active"] && camera_status[camera]["record_image_error"]) {
                    this.setStatusColor("status_error_record_"+camera, "red");
                }
                else if (camera_status[camera]["record_image_active"]) {
                    this.setStatusColor("status_error_record_"+camera, "green");
                    this.setStatusColor("status_error2_record_"+camera, "green");
                }
                else {
                    this.setStatusColor("status_error_record_"+camera, "black");
                    this.setStatusColor("status_error2_record_"+camera, "black");
                }

                // camera activated
                if (cameras[camera]["active"]) {
                    this.setStatusColor("status_active_"+camera, "white");
                }
                else {
                    this.setStatusColor("status_active_"+camera, "black");
                    this.setStatusColor("status_error_"+camera, "black");
                    this.setStatusColor("status_error2_"+camera, "black");
                    this.setStatusColor("status_error_record_"+camera, "black");
                    this.setStatusColor("status_error2_record_"+camera, "black");
                }

                if (cameras[camera]["image"]["crop_area"]) {
                    let crop = "[" + cameras[camera]["image"]["crop_area"][0] + ", " + cameras[camera]["image"]["crop_area"][1] + ", ";
                    crop += cameras[camera]["image"]["crop_area"][2] + ", " + cameras[camera]["image"]["crop_area"][2] + "] ";
                    setTextById("get_crop_area_"+camera, crop);
                }
            }
        }

        // client stream information
        let count_client_streams = birdhouse_CountActiveStreams();
        if (count_client_streams === 1) { stream = lang("STREAM"); } else { stream = lang("STREAMS"); }
        setTextById("show_stream_count_client", count_client_streams + " " + stream);
        setTextById("system_active_streams", camera_streams);

    }

    /*
    * read latest camera settings and fill respective placeholders with information if exist
    */
    cameraParam(data, camera) {

        let camera_status = data["DATA"]["camera_properties"];

        if (camera_status["properties"]) {

            for (let key in camera_status["properties"]) {

                let prop_text = camera_status["properties"][key][0];

                setTextById(
                    "prop_" + key.toLowerCase() + "_" + camera,
                    prop_text
                );

                if (
                    document.activeElement !== document.getElementById("set_" + key.toLowerCase() + "_" + camera) &&
                    document.activeElement !== document.getElementById("set_" + key.toLowerCase() + "_" + camera + "_range")
                ) {

                    setValueById(
                        "set_" + key.toLowerCase() + "_" + camera,
                        camera_status["properties"][key][0]
                    );

                    setValueById(
                        "set_" + key.toLowerCase() + "_" + camera + "_range",
                        camera_status["properties"][key][0]
                    );

                    if (document.getElementById("set_" + key.toLowerCase() + "_" + camera + "_range")) {

                        document.getElementById(
                            "set_" + key.toLowerCase() + "_" + camera + "_range"
                        ).className = "bh-slider start";
                    }
                }
            }


            for (let key in camera_status["properties_image"]) {

                setTextById(
                    "img_" + key + "_" + camera,
                    Math.round(camera_status["properties_image"][key] * 100) / 100
                );
            }
        }


        if (camera_status["properties_new"]) {

            for (let key in camera_status["properties_new"]) {

                let prop_text =
                    JSON.stringify(camera_status["properties_new"][key][0]);

                setTextById(
                    "prop_" + key.toLowerCase() + "_" + camera,
                    prop_text.replaceAll(",", ",  ")
                );

                setTextById(
                    "prop_" + key.toLowerCase() + "_" + camera,
                    prop_text.replaceAll(",", ",  ")
                );


                if (
                    document.activeElement !== document.getElementById("set_" + key + "_" + camera) &&
                    document.activeElement !== document.getElementById("set_" + key.toLowerCase() + "_" + camera + "_range")
                ) {

                    let data_type = "";

                    if (document.getElementById("set_" + key.toLowerCase() + "_" + camera + "_data_type")) {

                        data_type =
                            document.getElementById(
                                "set_" + key.toLowerCase() + "_" + camera + "_data_type"
                            ).value;
                    }


                    let data_value =
                        camera_status["properties_new"][key][0];

                    let data_class = "start";

                    let data_true  = [1, "True", "true", true];
                    let data_false = [0, "False", "false", false];

                    if (data_type === "boolean" && data_true.includes(data_value)) {

                        data_value = 1;
                        data_class = "on";
                    }

                    if (data_type === "boolean" && data_false.includes(data_value)) {

                        data_value = 0;
                        data_class = "off";
                    }


                    setValueById(
                        "set_" + key.toLowerCase() + "_" + camera,
                        data_value
                    );

                    setValueById(
                        "set_" + key.toLowerCase() + "_" + camera + "_range",
                        data_value
                    );

                    setValueById(
                        "set_" + key.toLowerCase() + "_" + camera,
                        data_value
                    );

                    setValueById(
                        "set_" + key.toLowerCase() + "_" + camera + "_range",
                        data_value
                    );


                    if (document.getElementById("set_" + key.toLowerCase() + "_" + camera + "_range")) {

                        document.getElementById(
                            "set_" + key.toLowerCase() + "_" + camera + "_range"
                        ).className = "bh-slider " + data_class;
                    }
                }
            }
        }
    }

    /*
    * weather status
    */
    weather(data, type = "all") {
        // weather information
        const weather         = data["STATUS"]["weather"];
        const settings        = data["SETTINGS"]["devices"]["weather"];

        let weather_icon    = "<small>N/A</small>";
        let weather_update  = "N/A";
        let weather_error   = "";

        if (weather["current"] && weather["current"]["description_icon"]) {
            if (settings["active"]) {
                weather_icon = weather["current"]["description_icon"];
                weather_update = weather["info_update"];
            }
            if (type === "all") {
                weather_error = "Running: " + weather["info_status"]["running"] + "\n";
                if (weather["info_status"]["error"] || weather["info_status"]["running"] === "error") {
                    weather_error += "Error: " + weather["info_status"]["error"].toString() + "\n";
                    weather_error += "Message: " + weather["info_status"]["error_msg"];
                    this.setHeaderColor("weather_error", this.header_color_error);
                    this.setHeaderColor("weather_settings", this.header_color_error);
                    this.setStatusColor("status_error_WEATHER", "red");
                } else if (weather["info_status"]["running"].indexOf("paused") > -1) {
                    this.setHeaderColor("weather_error", this.header_color_warning);
                    this.setStatusColor("status_error_WEATHER", "black");
                } else {
                    this.setHeaderColor("weather_settings", "");
                    this.setHeaderColor("weather_error", "");
                    this.setStatusColor("status_error_WEATHER", "green");
                }
                if (settings["active"] === true) {
                    this.setStatusColor("status_active_WEATHER", "white");
                } else {
                    this.setStatusColor("status_active_WEATHER", "black");
                    this.setStatusColor("status_error_WEATHER", "black");
                }
            }
            setTextById("weather_info_icon", weather_icon);
            setTextById("weather_info_update", weather_update);
            setTextById("weather_info_error", weather_error);

            let coordinates = "(" + settings["gps_coordinates"].toString().replaceAll(",", ", ") + ")";
            setTextById("gps_coordinates", coordinates);
        }
    }

    /*
    * relay status
    */
    relays(data) {

        let relay_status   = data["STATUS"]["devices"]["relays"];
        let relay_settings = data["SETTINGS"]["devices"]["relays"];

        for (let relay in relay_status) {
            let raw_status = relay_status[relay];
            let status     = ".";
            if (raw_status === false) { status = "OFF"; } else { status = "ON"; }
            setTextById("relay_status_" + relay, status);
            setTextById("relay_status_long_" + relay, lang("STATUS") + ": " + status);
            setTextById("relay_raw_status_" + relay, raw_status);

            if (relay_settings[relay]["active"]) { this.setStatusColor("status_active_"+relay, "white"); }
            else                                 { this.setStatusColor("status_active_"+relay, "black"); }
        }
    }

    /*
    * sensor status
    */
    sensors(data, type="all") {
            // add sensor information
            const sensors         = data["SETTINGS"]["devices"]["sensors"];
            const status_dev      = data["STATUS"]["devices"];
            const sensor_status   = status_dev["sensors"];

            for (let sensor in sensors) {
                if (type === "all") {
                    if (sensor_status[sensor]) {
                        //var status = sensors[sensor]["status"];
                        let status = sensor_status[sensor];
                        let sensor_error_01 = status["error_msg"]; //.join(",\n");
                        let sensor_error_02 = "Error: " + status["error"].toString() + "\n\n";
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
                        if (status["running"] === "OK") {
                            this.setStatusColor("status_active_"+sensor, "white");
                        }
                        else {
                            this.setStatusColor("status_active_"+sensor, "black");
                        }
                        if (status["error"] || status["error_module"] || status["connect"]) {
                            this.setHeaderColor(sensor+"_error", this.header_color_error);
                            this.setHeaderColor(sensor, this.header_color_error);
                            this.setStatusColor("status_error_"+sensor, "red");
                        }
                        else {
                            this.setHeaderColor(sensor+"_error", "");
                            this.setHeaderColor(sensor, "");
                            this.setStatusColor("status_error_"+sensor, "green");
                        }
                    }
                }

                if (sensors[sensor]["active"]) {
                    setStatusColor("status_active_"+sensor, "white");
                    let entry = "";
                    if (typeof(sensors[sensor]["values"]["temperature"]) != "undefined" && sensors[sensor]["values"]["temperature"] != null) {
                        entry += sensors[sensor]["name"] + ": ";
                        entry += "<span id='temp"+sensor+"'>"+sensors[sensor]["values"]["temperature"];
                        entry += sensors[sensor]["units"]["temperature"]+"</span>";
                        this.weather_footer.push(entry);
                    }

                    let summary = "";
                    for (let key in sensors[sensor]["values"]) {
                        summary += sensors[sensor]["values"][key] + sensors[sensor]["units"][key] + "<br/>";
                    }
                    setTextById("sensor_info_"+sensor, summary);
                }
                else {
                    this.setStatusColor("status_active_"+sensor, "black");
                    this.setStatusColor("status_error_"+sensor, "black");
                }
            }
        }

    /*
    * microphone status
    */
    microphones() {
        // add micro information
        let microphones  = app_data["STATUS"]["devices"]["microphones"];

        for (let micro in microphones) {
            if (microphones[micro]["active"])        { this.setStatusColor("status_active_"+micro, "white"); }
            else                                     { this.setStatusColor("status_active_"+micro, "black"); }
            if (microphones[micro]["active_stream"]) { setTextById("show_stream_count_"+micro, 1); }
            else                                     { setTextById("show_stream_count_"+micro, 0); }
            if (microphones[micro]["error"])  {
                this.setStatusColor("status_error_"+micro, "red");
                this.setHeaderColor(micro, this.header_color_error);
                this.setHeaderColor(micro+"_error", this.header_color_error);
            }
            else if (microphones[micro]["active"]) {
                this.setStatusColor("status_error_"+micro, "green");
                this.setHeaderColor(micro+"_error", "");
            }
            else {
                this.setStatusColor("status_error_"+micro, "black");
                this.setHeaderColor(micro, "");
                this.setHeaderColor(micro+"_error", "");
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
    * check a bunch of system status information and fill respective placeholders with status information
    */
    system(data) {

        const settings   = data["SETTINGS"]["server"];
        const status_sys = data["STATUS"]["system"];
        const status_srv = data["STATUS"]["server"];
        const status_db  = data["STATUS"]["database"];
        const start_time = data["STATUS"]["start_time"];

        let show_error = false;

        // database information
        let db_info = "type=" + settings["database_type"] + "; ";

        if (settings["database_type"] === "couch") {
            db_info += "connected=" + status_db["db_connected_couch"];
        }

        setTextById("system_info_database", db_info);


        // database connection
        if (!status_db["db_connected"] ||
            status_db["db_connected"].toString().indexOf("False") >= 0) {

            setTextById(
                "system_info_db_connection",
                "<span style='color:red'>Error: " +
                status_db["db_connected"] +
                " (" + status_db["type"] + ")</span>"
            );

            show_error = true;
        }
        else {
            setTextById(
                "system_info_db_connection",
                "Connected: " + status_db["type"]
            );
        }

        // handler error
        if (status_db["handler_error"] === true ||
            status_db["handler_error"].toString().indexOf("True") >= 0) {

            setTextById(
                "system_info_db_handler",
                "<span style='color:red'>Error:</span> " +
                status_db["handler_error_msg"].toString()
            );

            show_error = true;
        }
        else {
            setTextById("system_info_db_handler", "OK");
        }


        // db error
        if (status_db["db_error"] === true ||
            status_db["db_error"].toString().indexOf("True") >= 0) {

            setTextById(
                "system_info_db_error",
                "<span style='color:red'>Error: " +
                status_db["db_error"] +
                "</span> " +
                status_db["db_error_msg"].join("<br/>")
            );

            show_error = true;
        }
        else {
            setTextById("system_info_db_error", "OK");
        }

        setTextById("system_info_db_cache", status_db["cache_active"]);
        setTextById("system_info_db_cache_archive", status_db["cache_archive_active"]);


        // health check
        if (status_srv["health_check"] !== "OK" && status_srv["health_check"] !== undefined) {

            setTextById("system_health_check", "<span style='color:red'>" + status_srv["health_check"] + "</span>");
            show_error = true;
        }
        else if (status_srv["health_check"] === undefined) {
            setTextById("system_health_check", "starting");
        }
        else {
            setTextById("system_health_check", status_srv["health_check"]);
        }

        // system usage
        let percentage_1 = (status_sys["mem_used"] / status_sys["mem_total"]) * 100;
        let percentage_2 = (status_sys["hdd_used"] / status_sys["hdd_total"]) * 100;

        setTextById("system_info_mem_total", (Math.round(status_sys["mem_total"] * 10) / 10) + " MB");
        setTextById("system_info_mem_used", (Math.round(status_sys["mem_used"] * 10) / 10) + " MB (" + Math.round(percentage_1) + "%)");
        setTextById("system_info_cpu_usage", (Math.round(status_sys["cpu_usage"] * 10) / 10) + "%");
        setTextById("system_info_cpu_temperature", (Math.round(status_sys["cpu_temperature"] * 10) / 10) + "°C");
        setTextById("system_info_hdd_used", (Math.round(status_sys["hdd_used"] * 10) / 10) + " GB (" + Math.round(percentage_2) + "%)");
        setTextById("system_info_hdd_archive", (Math.round(status_sys["hdd_archive"] * 10) / 10) + " GB");
        setTextById("system_info_hdd_data", (Math.round(status_sys["hdd_data"] * 10) / 10) + " GB");
        setTextById("system_info_hdd_total", (Math.round(status_sys["hdd_total"] * 10) / 10) + " GB");
        setTextById("system_info_connection", "Connected");
        setTextById("system_info_start_time", start_time);
        setTextById("server_start_time", lang("STARTTIME") + ": " + start_time);
        setTextById("system_queue_wait",(Math.round(status_srv["queue_waiting_time"] * 10) / 10) + "s");

        // header error indicator
        if (show_error || app_connection_error) {

            if (getTextById("server_info_header") !== this.loading_dots_red) {
                setTextById("server_info_header", this.loading_dots_red);
            }
        }
        else {
            setTextById("server_info_header", "");
        }


        // cpu details
        let cpu_details = "";

        if (status_sys["cpu_usage_detail"]) {

            for (let i = 0; i < status_sys["cpu_usage_detail"].length; i++) {
                cpu_details += "cpu" + i + "=" + Math.round(status_sys["cpu_usage_detail"][i]) + "%, ";
            }

            setTextById("system_info_cpu_usage_detail", cpu_details);
        }

    }

    /*
    * loading view status
    */
    loadingViews(data, view="") {
        const views = ["object", "archive", "favorite"];

        if (view === "") {
            for (let i=0;i<views.length;i++) {
                const status = data["STATUS"]["server"]["view_"+views[i]+"_loading"];
                const progress = data["STATUS"]["server"]["view_"+views[i]+"_progress"];
                if (status === "in progress") {
                    setTextById("loading_status_"+views[i], progress);
                    setTextById("processing_"+views[i]+"_view", progress);
                    app_active_processes["processing_"+views[i]+"_view"] = true;
                }
                else if (status === "started") {
                    setTextById("loading_status_"+views[i], lang("WAITING"));

                    if (views[i] !== "object" || data["STATUS"]["object_detection"]["active"]) {
                        setTextById("processing_"+views[i]+"_view", lang("WAITING"));
                        app_active_processes["processing_"+views[i]+"_view"] = true;
                    }
                }
                else if (status === "done") {
                    setTextById("loading_status_"+views[i], lang("DONE"));
                    setTextById("processing_"+views[i]+"_view", lang("INACTIVE"));
                    this.app_active_processes["processing_"+views[i]+"_view"] = false;
                }
                else {
                    this.app_active_processes["processing_"+views[i]+"_view"] = false;
                }
            }
        }
        else {
            return data["STATUS"]["server"]["view_"+view+"_loading"];
        }
    }

    /*
    * object detection status
    */
    detection(data) {
        let i = 0;
        let message = "";
        const detection_cameras = data["STATUS"]["object_detection"]["processing_info"];
        const settings = app_data["SETTINGS"]["devices"]["cameras"];

        console.debug("Detection Status - processing: " + data["STATUS"]["object_detection"]["processing"] + " / " +
            "progress: " + data["STATUS"]["object_detection"]["progress"] + " / waiting: " + data["STATUS"]["object_detection"]["waiting"]);

        if (detection_cameras !== undefined && document.getElementById("processing_object_detection") !== undefined) {
            Object.entries(detection_cameras).forEach(([key,value])=> {
                i++;
                message += key.toUpperCase() + ": ";
                if (detection_cameras[key] && detection_cameras[key]["active"] && detection_cameras[key]["processing"]) {
                    message += "OK processing <b>" + detection_cameras[key]["progress"] + "%</b> "
                    message += "(" + detection_cameras[key]["model"] + " | waiting: " + detection_cameras[key]["waiting"] + ")";
                    this.app_active_processes["processing_object_detection_"+key] = true;
                }
                else if (detection_cameras[key] && detection_cameras[key]["active"]) {
                    message += lang("INACTIVE");
                    this.app_active_processes["processing_object_detection_"+key] = false;
                }
                else {
                    message += "N/A";
                    this.app_active_processes["processing_object_detection_"+key] = false;
                }
                message += "<br/>";
            });
            setTextById("processing_object_detection", message);
        }

        if (document.getElementById("last_answer_detection_progress") !== undefined) {
            if (data["STATUS"]["object_detection"]["processing"]) {
                let message_1 = data["STATUS"]["object_detection"]["progress"] + " %";
                if (data["STATUS"]["object_detection"]["waiting"] > 1) {
                    message_1 += "<br/><i>(" + lang("WAITING_DATES", [data["STATUS"]["object_detection"]["waiting"]]) + ")</i>";
                }
                else if (data["STATUS"]["object_detection"]["waiting"] === 1) {
                    message_1 += "<br/><i>(" + lang("WAITING_DATE") + ")</i>";
                }
                setTextById("last_answer_detection_progress", message_1);
            }
        }

        const status = app_data["STATUS"]["object_detection"];

        Object.entries(settings).forEach(([key,value])=> {
            if (value["object_detection"]["active"])      { this.setStatusColor("status_" + key + "_detection_active", "white"); }
            else                                          { this.setStatusColor("status_" + key + "_detection_active", "black"); }

            if (value["object_detection"]["active"])      { this.setStatusColor("status_active_" + key + "_object", "white"); }
            else                                          { this.setStatusColor("status_active_" + key + "_object", "black"); }

            if (!value["object_detection"]["active"])     { this.setStatusColor("status_" + key + "_detection_loaded", "black"); }
            else if (status["models_loaded_status"][key]) { this.setStatusColor("status_" + key + "_detection_loaded", "green"); }
            else                                          { this.setStatusColor("status_" + key + "_detection_loaded", "red"); }

            if (!value["object_detection"]["active"])     { this.setStatusColor("status_error_" + key + "_object", "black"); }
            else if (status["models_loaded_status"][key]) { this.setStatusColor("status_error_" + key + "_object", "green"); }
            else                                          { this.setStatusColor("status_error_" + key + "_object", "red"); }
        });

    }

    /*
    * video recording status
    */
    recordVideo(data) {

        const status_data  = data["STATUS"]["video_recording"];

        let p_video      = document.getElementById("processing_video");
        let p_video_info = "";

        let b_start, b_stop, b_cancel, b_object, b_photo;

        Object.entries(status_data).forEach(([key,value]) => {
            b_start  = document.getElementById("rec2_start_"+key);
            b_stop   = document.getElementById("rec2_stop_"+key);
            b_cancel = document.getElementById("rec2_cancel_"+key);
            b_object = document.getElementById("rec2_object_"+key);
            b_photo   = document.getElementById("rec2_foto_"+key);

            let object_detection = false;

            if (app_data["SETTINGS"]["devices"]["cameras"][key]) {
                object_detection = app_data["SETTINGS"]["devices"]["cameras"][key]["object_detection"]["active"];
            }

            if (p_video !== undefined) {
                p_video_info += key.toUpperCase() + ": ";
                if (value["error"])                                   { p_video_info += "N/A "; }
                else if (!value["processing"] && !value["recording"]) { p_video_info += lang("INACTIVE"); }
                else if (value["active"])                             { p_video_info += "OK "; }

                if (value["recording"])         {
                    p_video_info += "; recording <b>" + value["info"]["length"] + "s</b><br/>";
                    this.app_active_processes["processing_video_"+key] = true;
                }
                else if (value["processing"])   {
                    p_video_info += "; processing <b>" + Math.round(value["info"]["percent"]*10)/10 + "%</b><br/>";
                    this.app_active_processes["processing_video_"+key] = true;
                }
                else                            {
                    p_video_info += "<br/>";
                    this.app_active_processes["processing_video_"+key] = false;
                }
                console.debug("-> Status recordVideo");
                console.debug(value);
            }

            if (b_start) {
                if (!value["active"])           { b_start.disabled = "disabled"; }
                else if (value["recording"])    { b_start.disabled = "disabled"; b_start.style.backgroundColor = "darkred"; }
                else if (value["processing"])   { b_start.disabled = "disabled"; }
                else                            { b_start.disabled = ""; }
            }
            if (b_stop) {
                if (value["recording"])         { b_stop.disabled = ""; }
                else                            { b_stop.disabled = "disabled"; }
            }
            if (b_cancel) {
                if (value["recording"] || value["processing"])        { b_cancel.disabled = ""; }
                else if (!value["recording"] && !value["processing"]) { b_cancel.disabled = "disabled"; }
                else                                                  { b_cancel.disabled = "disabled"; }
            }
            if (b_photo) {
                if (value["recording"])         { b_photo.disabled = "disabled"; }
                else if (value["processing"])   { b_photo.disabled = "disabled"; }
                else                            { b_photo.disabled = ""; }
            }
            if (b_object) {
                if (object_detection === false)  { b_object.disabled = "disabled"; }
                else if (value["recording"])    { b_object.disabled = "disabled"; }
                else if (value["processing"])   { b_object.disabled = "disabled"; }
                else                            { b_object.disabled = ""; }
            }
        });

        if (p_video_info === "") { p_video_info = "inactive"; }
        setTextById("processing_video", p_video_info);

    }

    /*
    * video creation for day
    */
    createVideoDay(data) {
        const status_data  = data["STATUS"]["video_creation_day"];
        let p_video      = document.getElementById("processing_video_day");
        let p_video_info = "";

        Object.entries(status_data).forEach(([key,value]) => {

            if (p_video !== undefined) {
                p_video_info += key.toUpperCase() + ": ";
                if (value["error"])             { p_video_info += "N/A "; }
                else if (!value["processing"])  { p_video_info += "inactive"; }
                else if (value["active"])       { p_video_info += "OK "; }

                if (value["processing"])        {
                    p_video_info += "; processing <b>" + Math.round(value["info"]["percent"]*10)/10 + "%</b><br/>";
                    this.app_active_processes["processing_video_day_"+key] = true;
                }
                else                            {
                    this.app_active_processes["processing_video_day_"+key] = false;
                    p_video_info += "<br/>"
                }

                console.debug("-> Status createVideoDay");
                console.debug(value);
            }
        });

        if (p_video_info === "") { p_video_info = "inactive"; }
        setTextById("processing_video_day", p_video_info);
    }

    /*
    * download preparation
    */
    downloads(data) {
        let count_processes, count_downloads;
        if (data["STATUS"]["server"]["downloads"] !== {}) {

            let all_links_1 = "";
            let all_links_2 = "<ul>";
            count_processes = 0;
            count_downloads = 0;

            Object.entries(data["STATUS"]["server"]["downloads"]).forEach(([key,value]) => {

                let link;
                if (value.indexOf("in progress") > 0)   {
                    link = "<i>" + lang("WAITING") + "</i>";
                    count_processes += 1;
                }
                else {
                    link = "<a href='" + value + "'>" + value + "</a>";
                    count_downloads += 1;
                }

                all_links_1 += link + "<br/>";
                all_links_2 += "<li>" + link + "</li>";
                setTextById("archive_download_link_" + key, link);
            });

            all_links_2 += "</ul>";
            let message = count_processes + " Downloads under preparation. <br/>" + count_downloads + " Download ready: <br/>";
            message += all_links_2;
            setTextById("archive_download_link", all_links_1);
        }
        if (count_downloads + count_processes > 0)  {
            setTextById("processing_downloads", message);
        }
        else {
            setTextById("processing_downloads", lang("INACTIVE"));
        }
        this.app_active_processes["processing_downloads"] = count_processes > 0;

        let collect4download_amount = app_collect_list.length;
        setTextById("collect4download_amount", collect4download_amount);
        setTextById("collect4download_amount2", collect4download_amount);
    }

    /*
    * processing status
    */
    processing(data) {

        let active_processes    = "";

        if (data["STATUS"]["server"]["backup_process_running"])     {
            setTextById("processing_backup", lang("ACTIVE"));
            this.app_active_processes["processing_backup"] = true;
        }
        else {
            setTextById("processing_backup", lang("INACTIVE"));
            this.app_active_processes["processing_backup"] = false;
        }

        this.app_processing_active = false;
        Object.keys(this.app_active_processes).forEach( key => {
            if (this.app_active_processes[key] === true) {
                active_processes += key + ", ";
                this.app_processing_active = true;
            }
        });

        if (this.app_processing_active) {
            const text = getTextById("processing_info_header");
            if (text !== this.loading_dots_green) {
                setTextById("processing_info_header", this.loading_dots_green);
            }
            console.log("Active processes: " + active_processes);
        }
        else { setTextById("processing_info_header", ""); }
    }
}

/*
const bhStatus = new BirdhouseStatus();

const bhStatusMap = {
    birdhouseStatus_connectionError: "connectionError",
    birdhouseStatus_print: "print",
    birdhouseStatus_cameras: "cameras",
    birdhouseStatus_cameraParam: "cameraParam",
    birdhouseStatus_weather: "weather",
    birdhouseStatus_relays: "relays",
    birdhouseStatus_sensors: "sensors",
    birdhouseStatus_microphones: "microphones",
    birdhouseStatus_system: "system",
    birdhouseStatus_loadingViews: "loadingViews",
    birdhouseStatus_detection: "detection",
    birdhouseStatus_recordVideo: "recordVideo",
    birdhouseStatus_createVideoDay: "createVideoDay",
    birdhouseStatus_downloads: "downloads",
    birdhouseStatus_processing: "processing"
};

Object.entries(bhStatusMap).forEach(([oldName, newName]) => {
    window[oldName] = (...args) => bhStatus[newName](...args);
});
*/

let bhStatus;
app_scripts_loaded += 1;
