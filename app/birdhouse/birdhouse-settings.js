//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// settings
//--------------------------------------

var app_settings_active = false;
var birdhouse_settings  = new birdhouse_app_settings();


/*
* call specific settings page
*
* @param (string) page: settings page to be displayed
*/
function birdhouse_SETTINGS( page, data ) {

    console.log("birdhouse_SETTINGS: Load " + page);

    if (page == "SETTINGS_CAMERAS")           { birdhouseDevices(lang(page), data, "settings", "cameras"); }
	else if (page == "SETTINGS_DEVICES")      { birdhouseDevices(lang(page), data, "settings", "devices"); }
	else if (page == "SETTINGS_IMAGE")        { birdhouseDevices_cameraSettings(data); }
	else if (page == "SETTINGS_STATISTICS")   { birdhouse_STATISTICS(data); }
    }

/*
* class to create several views for settings and information
*/
function birdhouse_app_settings (name="Settings") {

    /*
    * set initial variables
    */
    this.init = function () {
        this.set             = appSettings;
        this.tab             = new birdhouse_table();
        this.tab.style_rows["height"] = "27px";
        this.tab.style_cells["width"] = "40%";
        this.frames_settings = this.set.frames_settings;
        this.frames_content  = this.set.frames_content;
        this.loading         = "<center>&nbsp;<br/>" + lang("PLEASE_WAIT") + " ...<br/>&nbsp;</center>";
        this.not_implemented = "<center>&nbsp;<br/>" + lang("NOT_IMPLEMENTED") + "<br/>&nbsp;</center>";
        }

    /*
    * prepare frame and initiate loading of selected setting category (old view)
    */
    this.create = function (type="SETTINGS") {
        this.setting_type = type;
        app_active.page = type;
        birdhouse_genericApiRequest("GET", ["status"], birdhouseStatus_print);
        if (app_data["STATUS"]["server"]["initial_setup"]) {
            html = "<center><br/>&nbsp;&nbsp;<br/><img src='"+app_loading_image+"' width='250'><br/>&nbsp;<br/>"+lang("PLEASE_WAIT")+"<br/>&nbsp;&nbsp;<br/>&nbsp;&nbsp;<br/></center>";
            setTextById(app_frame.content, html);
            }
      	setTimeout(function(){
      	    birdhouse_settings.create_exec(type);
		}, 500);
    }

    /*
    * get data and coordinate creation of all or selected setting category (old view)
    */
	this.create_exec = function (type="") {
        window.scrollTo(0,0);

        this.tab = new birdhouse_table();
        this.tab.style_rows["height"] = "27px";
        this.tab.style_cells["width"] = "40%";
        var tab = this.tab;

        var html = "";
        var initial_setup   = app_data["STATUS"]["server"]["initial_setup"];

        var current_url     = window.location.href;
        var current_server  = current_url.split("//")[1];
        current_server      = current_server.split("/")[0];
        this.current_server = current_server.split(":")[0];

        var open_settings = {
            "app_info_01" : false,
            "device_info" : false,
            "process_info": false,
            "server_info" : false,
            "api_calls"   : false,
            "api_info"    : false,
            "app_info_02" : false,
            "display_info": false,
            "app_under_construction": false
            }

        if (initial_setup) {
            open_settings["app_info_01"] = false;
            open_settings["server_info"] = false;
            open_settings["device_info"] = false;

            var img = "<img src='"+app_loading_image+"' width='250'><br/>&nbsp;<br/>";
            appMsg.confirm(img + lang("INITIAL_SETUP"), "console.log('.');", 400);
            }
        else if (this.setting_type == "INFO_ONLY") {
            open_settings["app_info_01"]  = true;
            open_settings["device_info"]  = true;
            open_settings["process_info"] = true;
        }
        else if (this.setting_type == "PROCESSING") {
            open_settings["process_info"] = true;
            }
        else {
            open_settings["app_info_01"]  = true;
            }

        if (this.setting_type != "INFO_ONLY") {
            html  = "<h2>Information</h2>";
            html += "<hr style='border:1px solid gray;'>"
        }

        html_entry = this.app_information();
        html += birdhouse_OtherGroup( "app_info_01", "App Information (Versions)", html_entry, open_settings["app_info_01"] );

        html_entry = this.device_information();
        html += birdhouse_OtherGroup( "device_info", "Device Information", html_entry, open_settings["device_info"] );

        html_entry = this.process_information();
        html += birdhouse_OtherGroup( "process_info", "Process Information &nbsp;<div id='processing_info_header'></div>", html_entry, open_settings["process_info"] );

        html_entry = this.server_information();
        html += birdhouse_OtherGroup( "server_info", "Server Information &nbsp;<div id='server_info_header'></div>", html_entry, open_settings["server_info"] );

        if (this.setting_type == "SETTINGS") {
            html_entry = this.display_information();
            html += birdhouse_OtherGroup( "display_info", "Display information", html_entry, open_settings["display_info"] );

            html_entry = this.app_information_detail();
            html += birdhouse_OtherGroup( "app_info_02", "App Information (Cookie, Reload)", html_entry, open_settings["app_info_02"] );

            }

        if (this.setting_type == "INFO_ONLY") {
            setTextById(app_frame.header, "<center><h2>" + lang("INFORMATION")) + "</h2></center>";
            setTextById("frame2", html)
            }
        else if (this.setting_type == "SETTINGS" || this.setting_type == "PROCESSING") {
            html += "<br/>&nbsp<br/>";
            html += this.settings();

            setTextById(app_frame.header, "<center><h2>" + lang("SETTINGS")) + "</h2></center>";
            setTextById(app_frame.content, html);
            }
		}

    /*
    * prepare frame and initiate loading of selected setting category (new view with categories and tiles)
    */
    this.create_new = function (type="", direct_access="") {
        this.set.show(true);
        window.scrollTo(0, 0);

        for (let camera in app_data["SETTINGS"]["devices"]["cameras"]) { birdhouseDevices_cameraSettingsLoad(camera, false); }
        var default_settings = ["SETTINGS_IMAGE", "SETTINGS_DEVICES", "SETTINGS_CAMERAS"];
        var load_settings    = ["SETTINGS_STATISTICS"];
        if (type == "SETTINGS_SERVER") {
            this.setting_type = "SETTINGS_SERVER";
            this.set.clear_frames();
            this.set.clear_content_frames();
            this.set.write(1, lang("SETTINGS"), this.settings(direct_access));
            this.set.show_entry(-1);
            app_active.page = "SETTINGS_SERVER";
            }
        else if (type == "SETTINGS_INFORMATION") {
            this.setting_type = type;
            this.set.write(1, lang("INFORMATION"), this.information());
            this.set.write(2, "", "");
            this.set.show_entry(2);
            app_active.page = "SETTINGS_INFORMATION";
            }
        else if (default_settings.includes(type)) {
            this.setting_type = type;
            this.set.clear_frames();
            this.set.clear_content_frames();
            this.set.write(1, "", this.loading);
            this.set.write(2, "", "");
            this.set.show_entry(2);
            birdhouse_SETTINGS(type, app_data);
            }
        else if (load_settings.includes(type)) {
            this.setting_type = type;
            this.set.clear_frames();
            this.set.clear_content_frames();
            this.set.write(1, "", this.loading);
            this.set.write(2, "", "");
            this.set.show_entry(2);
            birdhousePrint_load(type);
            }
        }

    /*
    * create setting view with app, server, processing, API, and client information (view only)
    */
    this.information = function () {

        var open_settings = {
            "app_info_01"           : true,
            "server_dashboard_1"    : true,
            "server_dashboard_2"    : false,
            "device_info"           : false,
            "process_info"          : false,
            "server_info"           : false,
            "api_calls"             : false,
            "api_info"              : false,
            "app_info_02"           : false,
            "display_info"          : false,
            "app_active_history"    : false,
            "app_under_construction": false,
            "api_performance"       : false,
            "server_performance"    : false,
            "server_queues"         : false,
            }

        var html = "";
        var html_entry = "";

        html_entry = this.app_information();
        html += birdhouse_OtherGroup( "app_info_01", "App (module versions)", html_entry, open_settings["app_info_01"] );

        html_entry = this.server_dashboard("server");
        html += birdhouse_OtherGroup( "server_dashboard_1", "Overview Server", html_entry, open_settings["server_dashboard_1"] );

        html_entry = this.server_dashboard("operation");
        html += birdhouse_OtherGroup( "server_dashboard_2", "Overview Operation", html_entry, open_settings["server_dashboard_2"] );

        //html_entry = this.device_information();
        //html += birdhouse_OtherGroup( "device_info", "Devices", html_entry, open_settings["device_info"] );

        html_entry = this.process_information();
        html += birdhouse_OtherGroup( "process_info", "Processing &nbsp;<div id='processing_info_header'></div>", html_entry, open_settings["process_info"] );

        html_entry = this.server_information();
        html += birdhouse_OtherGroup( "server_info", "Server &nbsp;<div id='server_info_header'></div>", html_entry, open_settings["server_info"] );

        html_entry = this.app_active_history();
        html += birdhouse_OtherGroup( "app_active_history", "View history &nbsp;<div id='server_info_header'></div>", html_entry, open_settings["app_active_history"] );

        html_entry = this.display_information();
        html += birdhouse_OtherGroup( "display_info", "Display", html_entry, open_settings["display_info"] );

        html_entry = this.api_performance();
        html += birdhouse_OtherGroup( "api_performance", "API performance", html_entry, open_settings["api_performance"] );

        html_entry = this.server_performance();
        html += birdhouse_OtherGroup( "server_performance", "Server performance", html_entry, open_settings["server_performance"] );

        //html_entry = this.server_queues();
        //html += birdhouse_OtherGroup( "server_queues", "Server queues", html_entry, open_settings["server_queues"] );

        return html;
        }

    /*
    * create setting view to edit overarching app settings and see overarching server settings (from .env)
    */
    this.settings = function (direct_access="") {

        var html        = "";
        var tab         = new birdhouse_table();
        var settings    = app_data["SETTINGS"];
        var initial     = app_data["STATUS"]["server"]["initial_setup"];
        var timezones   = "UTC-12,UTC-11,UTC-10,UTC-9,UTC-8,UTC-7,UTC-6,UTC-5,UTC-4,UTC-3,UTC-2,UTC-1,UTC+0,UTC+1,UTC+2,UTC+3,UTC+4,UTC+5,UTC+6,UTC+7,UTC+8,UTC+9,UTC+10,UTC+11,UTC+12"
        var settings_open = {
            "SRV_MAINTENANCE": true,
            "APP_SETTINGS": false,
            "APP_SETTINGS_ACCESS": false,
            "SRV_SETTINGS": false,
            "API_CALLS": false,
            "APP_CONSTRUCTION": false,
        }
        if (direct_access != "") {
            Object.keys(settings_open).forEach(key => { settings_open[key] = false; });
            settings_open[direct_access] = true;
            }
        if (initial == true) {
            settings_open["SRV_MAINTENANCE"] = false;
            settings_open["APP_SETTINGS"]    = true;
            }
        else {
            html_entry = this.api_calls(show="maintenance");
            html_entry += "&nbsp;<br/>";
            html += birdhouse_OtherGroup( "SRV_MAINTENANCE", "Maintenance", html_entry, settings_open["SRV_MAINTENANCE"], "settings" );
            }

        html += "<div style='display:none'>Edit initial setup: <select id='set_initial_setup'><option selected>false</option></select>";
        html += "<input id='set_initial_setup_data' value='server:initial_setup'>";
        html += "<input id='set_initial_setup_data_type' value='boolean'></div>";

        html_entry = this.settings_app_detail();
        html += birdhouse_OtherGroup( "APP_SETTINGS", "APP Settings", html_entry, settings_open["APP_SETTINGS"], "settings" );

        html_entry = this.settings_app_access();
        html += birdhouse_OtherGroup( "APP_SETTINGS_ACCESS", "APP Access", html_entry, settings_open["APP_SETTINGS_ACCESS"], "settings" );

        if (initial == false) {
            html_entry = this.server_side_settings();
            html += birdhouse_OtherGroup( "SRV_SETTINGS", "SERVER settings <i>(edit in &quot;.env&quot;)</i>", html_entry, settings_open["SRV_SETTINGS"], "settings" );

            html_entry = this.api_calls(show="api");
            html_entry += "&nbsp;<br/>";
            html += birdhouse_OtherGroup( "API_CALLS", "Development: API Calls", html_entry, settings_open["API_CALLS"], "settings" );

            html_entry = this.app_under_construction();
            html += birdhouse_OtherGroup( "APP_CONSTRUCTION", "Development: Direct Links", html_entry, settings_open["APP_CONSTRUCTION"], "settings" );
            }

        return html;
        }

    /*
    * create dialog to open or close the birdhouse for visitors
    */
    this.settings_app_open_close = function () {
        var html_entry  = "";
        var id_list = "set_closed:";
        var button1  = "<button id='init_b1' onclick='birdhouse_edit_send(\""+id_list+"\", \"\");' style='background:var(--setting-btn-index-background);'>&nbsp;"+lang("SAVE")+"&nbsp;</button>";
        var button2  = "<button id='init_b2' onclick='birdhouse_settings.create_new(\"SETTINGS_SERVER\",\"APP_SETTINGS_ACCESS\");' style='background:var(--setting-btn-index-background);'>&nbsp;"+lang("EDIT")+"&nbsp;</button>";
        var data    = app_data["SETTINGS"]["maintenance"];
        html_entry += "<center>";
        html_entry += "<table><tr>";
        html_entry += "<td>"+birdhouse_edit_field(id="set_closed", field="maintenance:closed", type="toggle", options="false:true", data_type="boolean") +"</td><td>" + lang("CLOSE_BIRDHOUSE") + "</td>";
        html_entry += "</tr></table>";
        html_entry += this.tab.end();
        html_entry += "<br/>";
        html_entry += button1 + "&nbsp;" + button2;
        html_entry += "</center>";

        return html_entry;
    }


    /*
    * create dialog to edit main settings for the app
    */
    this.settings_app_detail = function () {
        var html_entry  = "";
        var settings    = app_data["SETTINGS"];
        var timezones   = "UTC-12,UTC-11,UTC-10,UTC-9,UTC-8,UTC-7,UTC-6,UTC-5,UTC-4,UTC-3,UTC-2,UTC-1,UTC+0,UTC+1,UTC+2,UTC+3,UTC+4,UTC+5,UTC+6,UTC+7,UTC+8,UTC+9,UTC+10,UTC+11,UTC+12"

        html_entry = this.tab.start();
        html_entry += this.tab.row("Title:&nbsp;",              birdhouse_edit_field(id="set_title", field="title", type="input") );
        html_entry += this.tab.row("Language:&nbsp;",           birdhouse_edit_field(id="set_language", field="localization:language", type="select", options="EN,DE") );
        html_entry += this.tab.row("Timezone:&nbsp;",           birdhouse_edit_field(id="set_timezone", field="localization:timezone", type="select", options=timezones, data_type="string") );
        html_entry += this.tab.row("<hr/>");
        html_entry += this.tab.row("Backup-Time:&nbsp;",        birdhouse_edit_field(id="set_backup", field="backup:time", type="input") );
        html_entry += this.tab.row("BU Index Favorite:&nbsp;",  birdhouse_edit_field(id="set_preview_fav", field="backup:preview_fav", type="select", options="true,false", data_type="boolean") );
        html_entry += this.tab.row("BU Index Time:&nbsp;",      birdhouse_edit_field(id="set_preview", field="backup:preview", type="input") );
        html_entry += this.tab.row("<hr/>");

        html_entry += this.tab.row("Index View:&nbsp;",                birdhouse_edit_field(id="set_index_view", field="views:index:type", type="select", options="default,overlay,picture-in-picture", data_type="string") );
        html_entry += this.tab.row("LowRes Position (CAM1):&nbsp;",    birdhouse_edit_field(id="set_index_lowres", field="views:index:lowres_pos_cam1", type="select_dict_sort", options=index_lowres_position, data_type="integer") );
        html_entry += this.tab.row("LowRes Position (CAM2):&nbsp;",    birdhouse_edit_field(id="set_index_lowres2", field="views:index:lowres_pos_cam2", type="select_dict_sort", options=index_lowres_position, data_type="integer") );

        var id_list = "set_preview_fav:set_initial_setup:set_language:";
        id_list    += "set_timezone:set_title:set_backup:set_preview:set_rpi:set_index_lowres:set_index_view:set_index_lowres2";
        //id_list    += ":set_db_server:set_db_clean_up:set_db_type:set_ip4_video_port:set_weather_location:set_ip4:set_port:set_ip4_audio:set_ip4_video:set_ip4_deny:";

        var button2 = "";
        if (app_data["STATUS"]["server"]["initial_setup"]) {
            session_id    = "&session_id=" + app_session_id;
            var button_style1 = "style='background:gray;width:100px;height:38px;float:left;overflow:hidden;display:block;'";
            var button_style2 = "style='background:gray;width:100px;height:38px;float:left;overflow:hidden;display:none;'";
            var command       = "elementHidden(\"init_b1\");elementVisible(\"init_b2\");elementVisible(\"init_b3\");";

            button1  = "<button id='init_b1' onclick='birdhouse_edit_send(\""+id_list+"\", \"\");"+command+"' "+button_style1+">"+lang("SAVE")+"</button>";
            button2 += "<button id='init_b2' onclick='window.open(window.location.href.split(\"?\")[0]+\"?page=SETTINGS_CAMERAS"+session_id+"\", \"_blank\");' "+button_style2+">"+lang("DEVICE_SETTINGS_PROCEED_1")+"</button>";
            button2 += "<button id='init_b3' onclick='window.open(window.location.href.split(\"?\")[0]+\"?page=SETTINGS_DEVICES"+session_id+"\", \"_blank\");' "+button_style2+">"+lang("DEVICE_SETTINGS_PROCEED_2")+"</button>";

            html_entry += this.tab.row("&nbsp;");
            html_entry += this.tab.row("", button1 + "&nbsp;" + button2);
            }
        else {
            html_entry += this.tab.row("&nbsp;");
            html_entry += this.tab.row("", birdhouse_edit_save("set_main",id_list));
            }

        html_entry += this.tab.row("&nbsp;");
        html_entry += this.tab.end();

        return html_entry;
        }

    /*
    * create dialog to edit app access for visitors
    */
    this.settings_app_access = function () {
        var html_entry  = "";
        var settings    = app_data["SETTINGS"];
        var timezones   = "UTC-12,UTC-11,UTC-10,UTC-9,UTC-8,UTC-7,UTC-6,UTC-5,UTC-4,UTC-3,UTC-2,UTC-1,UTC+0,UTC+1,UTC+2,UTC+3,UTC+4,UTC+5,UTC+6,UTC+7,UTC+8,UTC+9,UTC+10,UTC+11,UTC+12"

        html_entry = this.tab.start();
        html_entry += this.tab.row(lang("CLOSE_BIRDHOUSE") + ":&nbsp;", birdhouse_edit_field(id="set_closed", field="maintenance:closed", type="select", options="true,false", data_type="boolean") );
        html_entry += this.tab.row("Message:&nbsp;", birdhouse_edit_field(id="set_close_msg", field="maintenance:message", type="input_text") );

        var id_list = "set_closed:set_close_msg:";
        html_entry += this.tab.row("&nbsp;");
        html_entry += this.tab.row("", birdhouse_edit_save("set_main",id_list));
        html_entry += this.tab.row("&nbsp;");
        html_entry += this.tab.end();

        return html_entry;
        }

    /*
    * create setting view with a collection of buttons with most important API calls
    */
	this.api_calls = function (show="all") {

	    this.button_api = function (command, description) {
	        return "<button onclick='window.open(\"" + RESTurl + command + "\",\"_blank\");' class='button-settings-api';>" + description + "</button>";
	        }
	    this.button_system = function (command, description, style="") {
	        return "<button onclick='" + command + "' class='button-settings-system " + style + "';>" + description + "</button>";
	        }

	    var api_call        = "";
        var cameras         = app_data["SETTINGS"]["devices"]["cameras"];
        var microphones     = app_data["SETTINGS"]["devices"]["microphones"];
        var relays          = app_data["SETTINGS"]["devices"]["relays"];
        var server_settings = app_data["SETTINGS"]["server"];
        delete this.tab.style_cells["width"];
        var html_entry      = this.tab.start();

        if (show == "maintenance" || show == "all") {
            if (show == "all") { html_entry = this.tab.row("Maintenance commands ..."); }
            api_call    = this.button_system("birdhouse_forceBackup();",                    "<b>Backup data</b><br/> of TODAY now");
            api_call   += this.button_system("birdhouse_forceUpdateViews(\"all\");",        "<b>Update views</b><br/> (favorite, archive, objects)");
            api_call   += this.button_system("birdhouse_forceUpdateViews(\"all\",true);",   "<b>Update views</b>,<br/> complete reload from archive data");
            api_call   += this.button_system("birdhouse_recreateImageConfig();",            "<b>Recreate data</b><br/> for TODAY based on recorded images");
            api_call   += this.button_system("birdhouse_removeDataToday();",                "<b>Delete data</b><br/> for TODAY (images and configs)");
            api_call   += this.button_system("birdhouse_checkTimeout();",                   "Test / demonstrate <b>Timeout</b>", "other");

            if (server_settings["server_mode"] == "DOCKER" && server_settings["server_restart"] != "no" && server_settings["server_restart"] != "on-failure") {
                api_call   += this.button_system("birdhouse_forceRestart();",     "<b>Restart</b><br/> birdhouse server ("+server_settings["server_mode"]+")", "attention");
                }
            else if (server_settings["server_mode"] == "DOCKER") {
                api_call   += this.button_system("birdhouse_forceShutdown();",     "<b>Shutdown</b><br/> birdhouse server ("+server_settings["server_mode"]+")", "attention");
                }
            else {
                api_call   += this.button_system("birdhouse_forceRestart();",      "<b>Restart</b><br/> birdhouse server ("+server_settings["server_mode"]+")", "attention");
                api_call   += this.button_system("birdhouse_forceShutdown();",     "<b>Shutdown</b><br/> birdhouse server ("+server_settings["server_mode"]+")", "attention");
                }
            html_entry += this.tab.row(api_call);
            }

        if (show == "all" || show == "api") {
            api_call    = this.button_api("api/no-id/status/",          lang("STATUS") + " #1");
            api_call   += this.button_api("api/no-id/list/",            lang("STATUS") + " #2");
            api_call   += this.button_api("api/no-id/INDEX/",           lang("INDEX"));
            api_call   += this.button_api("api/no-id/DIARY/",           lang("DIARY"));
            api_call   += this.button_api("api/no-id/OBJECTS/",         lang("OBJECT_DETECTION"));
            api_call   += this.button_api("api/no-id/STATISTICS/",      lang("STATISTICS"));
            api_call   += this.button_api("api/no-id/VIDEOS/",          lang("VIDEOS"));
            api_call   += this.button_api("api/no-id/FAVORITES/",       lang("FAVORITES"));
            api_call   += this.button_api("api/no-id/WEATHER/",         lang("WEATHER"));
            api_call   += this.button_api("api/no-id/IMAGE_SETTINGS/",  lang("IMAGE_SETTINGS"));
            api_call   += this.button_api("api/no-id/DEVICE_SETTINGS/", lang("DEVICE_SETTINGS"));
            api_call   += this.button_api("api/no-id/last-answer/",     "LAST ANSWER");
            api_call   += this.button_api("api/no-id/python-pkg/",      "PYTHON PACKAGES");
            html_entry += this.tab.row("API Calls", api_call);
            }

	    if (show == "all" || show == "api" || show == "devices") {
            for (let camera in cameras) {
                api_call  = "<button onclick='window.open(\"" + RESTurl + "api/no-id/TODAY/"+camera+"/\",\"_blank\");' class='button-settings-api'>Today "+camera.toUpperCase()+"</button>";
                api_call += "<button onclick='window.open(\"" + RESTurl + "api/no-id/TODAY_COMPLETE/"+camera+"/\",\"_blank\");' class='button-settings-api'>Compl. "+camera.toUpperCase()+"</button>";
                api_call += "<button onclick='window.open(\"" + RESTurl + "api/no-id/ARCHIVE/"+camera+"/\",\"_blank\");' class='button-settings-api'>Archive "+camera.toUpperCase()+"</button>";
                html_entry += this.tab.row("API "+camera, api_call);
            }

            for (let micro in microphones) {
                api_call    = "<button onclick='birdhouse_recordStartAudio(\""+micro+"\");' class='button-settings-api'>Record "+micro+"</button>";
                api_call   += "<button onclick='birdhouse_recordStopAudio(\""+micro+"\");' class='button-settings-api'>Stop "+micro+"</button>";
                html_entry += this.tab.row("API "+micro, api_call);
            }

            for (let relay in relays) {
                api_call    = "<button onclick='birdhouse_relayOnOff(\""+relay+"\",\"on\");' class='button-settings-api'>"+relay+" ON</button>";
                api_call   += "<button onclick='birdhouse_relayOnOff(\""+relay+"\",\"off\");' class='button-settings-api'>"+relay+" OFF</button>";
                html_entry += this.tab.row("API " + relay, api_call);
                }
            }

        html_entry += this.tab.end();
        this.tab.style_cells["width"] = "40%";
        return html_entry;
	}

    /*
    * create setting view to show the performance of API commands
    */
	this.api_performance = function () {
	    var answer = appFW.getAverageRequestDurations();
        var html = "&nbsp;<br/>";
        var tab  = new birdhouse_table();
        tab.style_cells["vertical-align"] = "top";

        html += "<i><b>Response times per API request:</i></b><br/>&nbsp;<br/>";
	    html += tab.start();
	    Object.keys(answer).sort().forEach(key => {
	        var key_print = key.replace(app_session_id, "");
	        var key_parts = key.split("/");
	        if (/^\d+$/.test(key_parts[1])) { key_print = key_print.replace("/" + key_parts[1],""); }
	        if (key_print.indexOf("kill-stream") < 0) {
	            html += tab.row(key_print, answer[key].toFixed(4)+"s");
	            }
	        });
	    html += tab.end();
	    html += "&nbsp;";

	    return html;
	    }

    /*
    * create setting view to show app and module versions and helpful URLs
    */
	this.app_information = function () {
	    var instance = " (prod)";
	    if (test) { instance = " (test)"; }
		var html_entry = this.tab.start();
		var settings = app_data["SETTINGS"];

		html_entry += this.tab.row("App:",	"<a href='/app/index.html?INFORMATION&" + app_session_id + "' target='_blank'>"+ app_title + "</a>" + instance);
		html_entry += this.tab.row("Versions:",
						"App: " 		+ app_version + "<br/>" +
						"Server: "      + app_data["API"]["version"] + "<br/>" +
						"jcMsg: " 		+ appMsg.appVersion + "<br/>" +
						"jcApp: "		+ appFW.appVersion);
		html_entry += this.tab.row("Source:","<a href='https://github.com/jc-prg/birdhouse-cam/' target='_blank'>https://github.com/jc-prg/birdhouse-cam/</a>");
		html_entry += this.tab.row("Client:",
		                "IP: " + app_data["API"]["request_ip"] + "<br/>" +
		                "Session: " + app_session_id + "<br/>" +
		                "<a href='" + window.location.href + "' target=_blank>" + window.location.href + "</a>");

        if (settings["webdav"] && settings["webdav"]["show"] == true) {
            var webdav_url = window.location.href.split("//")[1].split("/")[0].split(":")[0];

            if (settings["webdav"]["active"])   { var running = "<font color=" + header_color_ok + ">[" + lang("ACTIVE") + "]</font>"; }
            else                                { var running = "<font color=" + header_color_error + ">[" + lang("INACTIVE") + "]</font>"; }

            webdav_url_1    = "dav://" + settings["webdav"]["user"] + ":" + settings["webdav"]["pwd"] + "@" + webdav_url + ":" + settings["webdav"]["port"] + "/";
            webdav_url_2    = "dav://" + webdav_url + ":" + settings["webdav"]["port"] + "/";
            webdav_url_3    = "http://" + settings["webdav"]["user"] + ":" + settings["webdav"]["pwd"] + "@" + webdav_url + ":" + settings["webdav"]["port"] + "/";
            webdav_url_4    = "http://" + webdav_url + ":" + settings["webdav"]["port"] + "/";

            html_entry += this.tab.row("WebDAV "+running+":", "<a href='" + webdav_url_1 + "' target=_blank>" + webdav_url_2 + "</a> (Webdav-App)<br/>" +
                                       "<a href='" + webdav_url_3 + "' target=_blank>" + webdav_url_4 + "</a> (Browser)");
            }
		html_entry += this.tab.row("&nbsp;");
		html_entry += this.tab.end();
        return html_entry;
	}

    /*
    * create setting view to show some overarching app variables
    */
	this.app_information_detail = function () {
	    var html_entry = "";
        html_entry = this.tab.start();
        html_entry += this.tab.row("Reload Interval:", app_reload_interval + "s");
        html_entry += this.tab.row("Active Camera:&nbsp;", app_active.cam);
        html_entry += this.tab.row("Active Client Streams:&nbsp;", "<font id='show_stream_count_client'>0 Streams</font>");
        html_entry += this.tab.row("Available Cameras:&nbsp;", app_available.cameras.length);
        html_entry += this.tab.row("Active Page:&nbsp;", app_active.page);
        html_entry += this.tab.row("Active Date:&nbsp;", app_active.date);
        html_entry += this.tab.row("Unique stream URL:&nbsp;", app_unique_stream_url);
        html_entry += this.tab.row("Unique stream ID:&nbsp;",	app_unique_stream_id);
        html_entry += this.tab.end();
        return html_entry;
	}

    /*
    * create setting view to show some display related values
    */
	this.display_information = function () {
	    var html_entry = "";
        html_entry = this.tab.start();
        html_entry += this.tab.row("Window Size:", "<text id='windowWidth'>"+window.innerWidth + "x" + window.innerHeight+"</text>" );
        html_entry += this.tab.row("Screen Size:", "<text id='screenWidth'>"+screen.width + "x" + screen.height+"</text>" );
        html_entry += this.tab.row("Position:", "<div id='scrollPosition'>0 px</div>" );
        html_entry += this.tab.row("Format:", print_display_definition());
        html_entry += this.tab.row("Browser:", navigator.userAgent);
        html_entry += this.tab.end();
        return html_entry;
    }

    /*
    * create setting view to visualize object detection information (not used any more)
    */
	this.device_information = function () {
	    var status   = app_data["STATUS"]["object_detection"];
        var tab      = new birdhouse_table();
        tab.style_rows["height"]        = "27px";
        tab.style_cells["min-width"]    = "150px";
        tab.style_cells["width"]        = "50%";

	    var html = birdhouseDevices("", app_data, show="information");

        if (status["active"]) {
            html += tab.start();
            Object.entries(status["models_loaded"]).forEach(([key,value])=> {
                var description = "Detection " + key + " (" + value + "):";
                var action = "<div style='float:left;'>";
                action += "<div id='status_" + key + "_detection_active' style='float:left;'><div id='black'></div></div>";
                action += "<div id='status_" + key + "_detection_loaded' style='float:left;'><div id='black'></div></div>";

                html += tab.row(description, action);
                });
            html += tab.end();
            }
        else {
            html += "<i>" + lang("OBJECT_DETECTION_INACTIVE") + "</i><br/>&nbsp;";
            }
        html += "<br/>&nbsp;<br/>";

	    return html;
	}

    /*
    * create setting view to show running process information (filled by birdhouse-status.js)
    */
	this.process_information = function () {
	    var html = "";
        var tab      = new birdhouse_table();
        tab.style_rows["height"] = "27px";
        tab.style_cells["width"] = "50%";
        tab.style_cells["vertical-align"] = "top";

        var process_information = {
            "Backup process":                   "processing_backup",
            "Download preparation":             "processing_downloads",
            "Loading archive view":             "processing_archive_view",
            "Loading favorite view":            "processing_favorite_view",
            "Loading object detection view":    "processing_object_view",
            "Video recording":                  "processing_video",
            "Video create day video":           "processing_video_day",
            "Object Detection":                 "processing_object_detection",
        }

        html += tab.start();
        Object.entries(process_information).forEach(([key, value]) => {
            html += tab.row(key+":", "<div id='" + value + "'>N/A</div>");
        });
        html += tab.end();
        html += "<br/>&nbsp;<br/>";

 	    return html;
	    }

    /*
    * create setting view to show the performance of API commands (more details than self.api_performance())
    */
	this.server_performance = function () {
        var answer = app_data["STATUS"]["server_performance"];
        var html   = "&nbsp;<br/>";
        var tab    = new birdhouse_table();
        tab.style_cells["vertical-align"]   = "top";
        tab.style_cells["max-width"]        = "50%";

	    html += "<i><b>Server process durations:</i></b><br/>&nbsp;<br/>";
	    html += tab.start();
	    Object.keys(answer).sort().forEach(key => {
	        var print_key     = key.replaceAll("_", " ");
	        var print_entry   = tab.start();
	        var print_update  = "";
	        Object.keys(answer[key]).sort().forEach(device => {
	            if (device == "last_update") { print_update = tab.row("<i>update:</i> ", "<i>" + answer[key][device].split(" ")[1]) + "</i>"; }
	            else                         { print_entry += tab.row("<i>" + device + ":</i>", answer[key][device] + "s"); }
	            });
	        print_entry      += print_update;
	        print_entry      += tab.row("&nbsp;");
	        print_entry      += tab.end();
            html             += tab.row(print_key + ":", print_entry);
            });
	    html += tab.end();
	    html += "&nbsp;";
	    return html;
	    }

    /*
    * create setting view to show main server side settings defined in the .env-file
    */
    this.server_side_settings = function() {
        var settings = app_data["SETTINGS"];
        var status   = app_data["STATUS"];
        if (settings["server"]["rpi_active"])           { rpi_active = "true"; }        else { rpi_active = "false"; }
        if (settings["server"]["detection_active"])     { detection_active = "true"; }  else { detection_active = "false"; }
        if (settings["server"]["daily_clean_up"])       { daily_clean_up = "true"; }    else { daily_clean_up = "false"; }

        if (settings["server"]["database_server"] && settings["server"]["database_server"] != "") {
            var link = "http://"+settings["server"]["database_server"]+":"+settings["server"]["database_port"]+"/_utils/";
        }
        else {
            var link = "http://"+this.current_server+":"+settings["server"]["database_port"]+"/_utils/";
        }

        var html_internal = "";
        html_internal += this.tab.start();
        html_internal += this.tab.row("DB Server:&nbsp;",          settings["server"]["database_server"]);
        html_internal += this.tab.row("DB Type:&nbsp;",            settings["server"]["database_type"]);
        html_internal += this.tab.row("DB Daily Clean Up:&nbsp;",  daily_clean_up);
        html_internal += this.tab.row("DB Port:&nbsp;",            settings["server"]["database_port"]);
        html_internal += this.tab.row("DB Admin:",                 "<a href='"+link+"' target='_blank'>"+link+"</a>");
        html_internal += this.tab.row("DB Cache:",                 "<div id='system_info_db_cache'>"+lang("PLEASE_WAIT")+"..</div>");
    	html_internal += this.tab.row("DB Cache (Archive):",       "<div id='system_info_db_cache_archive'>"+lang("PLEASE_WAIT")+"..</div>");
        html_internal += this.tab.row("<hr/>");

        html_internal += this.tab.row("HTTP Server:&nbsp;",        settings["server"]["ip4_address"]);
        html_internal += this.tab.row("HTTP Port:&nbsp;",          settings["server"]["port"]);
        html_internal += this.tab.row("Video stream port:&nbsp;",  settings["server"]["port_video"]);
        html_internal += this.tab.row("Audio stream server:&nbsp;",settings["server"]["server_audio"]);
        html_internal += this.tab.row("Audio stream port:&nbsp;",  settings["server"]["port_audio"]);
        html_internal += this.tab.row("RPi Active:&nbsp;",         rpi_active);
        html_internal += this.tab.row("Object detection:&nbsp;",   detection_active);

        if (detection_active == true || detection_active == "true") {
            var loading_info = status["object_detection"]["status"] + " - " + status["object_detection"]["status_details"];
            if (status["object_detection"]["status"] == true)   { loading_info += " - " + JSON.stringify(status["object_detection"]["models_loaded"]).replaceAll(",", ", ").replaceAll(":", " : "); }
            else                                                { loading_info = "<font color=" + header_color_error + ">" + loading_info + "</font>"; }
            html_internal += this.tab.row("Object detection loaded:&nbsp;", loading_info);
            }

        html_internal += this.tab.row("<hr>");
        html_internal += this.tab.row("Admin access via:&nbsp;",   settings["server"]["admin_login"]);
        html_internal += this.tab.row("ADM Deny from IP4:&nbsp;",  settings["server"]["ip4_admin_deny"]);
        html_internal += this.tab.row("ADM Allow from IP4:&nbsp;", settings["server"]["ip4_admin_allow"]);

        html_internal += this.tab.row("&nbsp;");
        html_internal += this.tab.end();

        return html_internal;
    }

    /*
    * create setting view to show queue sizes (not used any more)
    */
	this.server_queues = function () {
        var answer_1 = app_data["STATUS"]["server_config_queues"];
        var answer_2 = app_data["STATUS"]["server_object_queues"];
        var html     = "&nbsp;<br/>";
        var tab      = new birdhouse_table();
        tab.style_cells["vertical-align"] = "top";
        tab.style_cells["max-width"] = "50%";

	    html += "<i><b>Server queues size:</i></b><br/>&nbsp;<br/>";
	    html += tab.start();
	    Object.keys(answer_1).sort().forEach(key => {
            html += tab.row("config &gt; " + key + ":", answer_1[key]);
            });
	    Object.keys(answer_2).sort().forEach(key => {
            html += tab.row("object &gt; " + key + ":", answer_2[key]);
            });
	    html += tab.end();
	    html += "&nbsp;";
	    return html;
	}

    /*
    * create setting view to show several server status information
    */
	this.server_information = function () {
        var html_entry = this.tab.start();
    	html_entry += this.tab.row("Server Connection:",   "<div id='system_info_connection'>"+lang("PLEASE_WAIT")+"..</div>");
    	html_entry += this.tab.row("Server start time:",   "<div id='system_info_start_time'>"+lang("PLEASE_WAIT")+"..</div>");
    	html_entry += this.tab.row("Active Streams:",      "<div id='system_active_streams'>"+lang("PLEASE_WAIT")+"..</div>");
    	html_entry += this.tab.row("Queue waiting time:",  "<div id='system_queue_wait'>"+lang("PLEASE_WAIT")+"..</div>");
    	html_entry += this.tab.row("Health check:",        "<div id='system_health_check'>"+lang("PLEASE_WAIT")+"..</div>");
        html_entry += this.tab.row("<hr/>");
    	html_entry += this.tab.row("DB Connection:",       "<div id='system_info_db_connection'>"+lang("PLEASE_WAIT")+"..</div>");
    	html_entry += this.tab.row("DB Handler:",          "<div id='system_info_db_handler'>"+lang("PLEASE_WAIT")+"..</div>");
    	html_entry += this.tab.row("DB:",                  "<div id='system_info_db_error'>"+lang("PLEASE_WAIT")+"..</div>");
        html_entry += this.tab.row("<hr/>");
    	html_entry += this.tab.row("CPU Temperature:",     "<div id='system_info_cpu_temperature'>"+lang("PLEASE_WAIT")+"..</div>");
    	html_entry += this.tab.row("CPU Usage:",           "<div id='system_info_cpu_usage'>"+lang("PLEASE_WAIT")+"..</div>");
    	html_entry += this.tab.row("CPU Usage (Details):", "<div id='system_info_cpu_usage_detail'>"+lang("PLEASE_WAIT")+"..</div>");
        html_entry += this.tab.row("<hr/>");
    	html_entry += this.tab.row("Memory Used:",         "<div id='system_info_mem_used'>"+lang("PLEASE_WAIT")+"..</div>");
    	html_entry += this.tab.row("Memory Total:",        "<div id='system_info_mem_total'>"+lang("PLEASE_WAIT")+"..</div>");
    	html_entry += this.tab.row("HDD used:",            "<div id='system_info_hdd_used'>"+lang("PLEASE_WAIT")+"..</div>");
    	html_entry += this.tab.row("HDD data:",            "<div id='system_info_hdd_data'>"+lang("PLEASE_WAIT")+"..</div>");
    	html_entry += this.tab.row("HDD archive:",         "<div id='system_info_hdd_archive'>"+lang("PLEASE_WAIT")+"..</div>");
    	html_entry += this.tab.row("HDD total:",           "<div id='system_info_hdd_total'>"+lang("PLEASE_WAIT")+"..</div>");
        html_entry += this.tab.row("&nbsp;");
        html_entry += this.tab.end();
        return html_entry;
	}

    /*
    * show app_active_history
    */
    this.app_active_history = function () {
        var html = "";
        for (var i=0;i<app_active_history.length;i++) {
            var item = app_active_history[i];
            var onclick = "birdhousePrint_page(\""+item.page+"\",\""+item.cam+"\",\""+item.date+"\")";
            if (i == app_active_history_pos) { html += "<font color='green'>"; }
            html += "<b>" + i + ".</b> &nbsp; <text onclick='"+onclick+"' style='cursor:pointer;'>" + item.page + " / " + item.cam + " / " + item.date + "</text><br/>";
            if (i == app_active_history_pos) { html += "</font>"; }
            }
        return html;
        }


    /*
    * create setting view to show several direct links to video streams or categories (such as INDEX, SETTINGS, INFO, ...
    */
	this.app_under_construction = function() {
		var html_entry = this.tab.start();
		link = RESTurl + "stream.mjpg?cam1";
		html_entry += this.tab.row("Stream:", "<a href='"+link+"' target='_blank'>"+link+"</a>");
		link = RESTurl + "lowres/stream.mjpg?cam1";
		html_entry += this.tab.row("Stream LowRes:", "<a href='"+link+"' target='_blank'>"+link+"</a>");
		link = RESTurl + "detection/stream.mjpg?cam1";
		html_entry += this.tab.row("Stream Detection Areas:", "<a href='"+link+"' target='_blank'>"+link+"</a>");
		link = RESTurl + "object/stream.mjpg?cam1";
		html_entry += this.tab.row("Stream Object Detection:", "<a href='"+link+"' target='_blank'>"+link+"</a>");
		link = RESTurl + "pip/stream.mjpg?cam1+cam2:1";
		html_entry += this.tab.row("Stream Picture-in-Picture:", "<a href='"+link+"' target='_blank'>"+link+"</a>");

        var direct_links = app_pages_content.concat(app_pages_settings);
        //["ARCHIVE", "FAVORITES", "TODAY", "TODAY_COMPLETE", "OBJECT", "SETTINGS", "SETTINGS_INFORMATION", "SETTINGS_SERVER", "SETTINGS_CAMERAS", "SETTINGS_DEVICES"];

        for (var i=0;i<direct_links.length;i++) {
            link = window.location.href.split("?")[0] + "?page=" + direct_links[i] + "&session_id=" + app_session_id;
            html_entry += this.tab.row("Direct Link "+direct_links[i]+":", "<a href='"+link+"' target='_blank'>"+link+"</a>");
            }

		html_entry += this.tab.row("&nbsp;");
		html_entry += this.tab.end();
        return html_entry;
	}

    /*
    * create setting view to monitor several server status information in real time
    */
	this.server_dashboard = function (part="all") {
	    var html = "<div class='dashboard_container'>";
	    var data    = app_data["STATUS"];
	    var data_p  = data["server_performance"];

        if (part == "server" || part == "all") {
            html     += this.set.dashboard_item(id="server_up_time",     type="number", title="Server up time",   description=data["start_time"]);
            html     += this.set.dashboard_item(id="server_boot_time",   type="number", title="Server boot time", description=data["start_time"]);
            html     += this.set.dashboard_item(id="cpu_usage",          type="number", title="CPU", description="current usage (" + data["system"]["cpu_usage_detail"].length + " CPUs)" );
            html     += this.set.dashboard_item(id="cpu_temperature",    type="number", title="CPU", description="temperature" );
            html     += this.set.dashboard_item(id="hdd_available",      type="number", title="HDD", description="available disk space" );
            html     += this.set.dashboard_item(id="mem_available",      type="number", title="Memory", description="available memory" );
            }

        if (part == "operation" || part == "all") {
            html     += this.set.dashboard_item(id="api_status_request", type="number", title="API", description="status request duration");
            if (data["server_config_queues"]) {
                html     += this.set.dashboard_item(id="config_queue_wait", type="number", title="Config queue", description="current waiting time");
                html     += this.set.dashboard_item(id="config_queue_write", type="number", title="Config queue", description="config writing duration");
                html     += this.set.dashboard_item(id="config_queue_size", type="number", title="Config queue", description="entries");
                }
            if (data["server_object_queues"]) {
                html     += this.set.dashboard_item(id="object_queue_size", type="number", title="Object queue", description="entries");
                }
            Object.keys(app_data["SETTINGS"]["devices"]["cameras"]).forEach(key => {
                if (data["server_performance"]["camera_recording_image"] && data["server_performance"]["camera_recording_image"][key]) {
                    html += this.set.dashboard_item(id="record_image_"+key, type="number", title=key, description="image recording duration");
                    }
                });
            if (data_p["object_detection"]) {
                html     += this.set.dashboard_item(id="object_detection", type="number", title="Object detection", description="detection time per image");
                }
            if (data["database"]["type"] == "json" || data["database"]["type"] == "both") {
                html     += this.set.dashboard_item(id="locked_db", type="number", title="Database JSON", description="locked json DB ("+data["database"]["type"]+")");
                }
            if (data["database"]["type"] == "json") {
                html     += this.set.dashboard_item(id="locked_db_wait", type="number", title="Database JSON", description="waiting time locked DB");
                }
            html     += this.set.dashboard_item(id="mem_used",   type="number", title="Memory", description="memory used by server" );
            html     += this.set.dashboard_item(id="cache_size", type="number", title="Database", description="data in cache ("+data["database"]["cache_active"]+")");
            }

	    setTimeout(function() {birdhouse_settings.server_dashboard_fill(app_data);}, 1000);
	    html += "</div>";
	    return html;
	    }

    /*
    * fill tiles with real time status information
    */
	this.server_dashboard_fill = function (data) {
	    var status     = data["STATUS"];
	    var status_cam = data["SETTINGS"]["devices"]["cameras"];
	    var status_prf = status["server_performance"];
	    var status_api = appFW.getAverageRequestDurations();
	    var data_q     = {"config" : 0, "object" : 0};
	    var up_time    = convert_second2time(status["up_time"]);

	    this.round = function(value) {
	        if (value < 1)       { value = Math.round(value*1000)/1000}
	        else if (value < 10) { value = Math.round(value*100)/100}
	        else                 { value = Math.round(value*10)/10}
	        return value;
	        }
	    this.data_size = function(value) {
	        var unit = "B";
	        if (value > 1024 * 1024 * 1024)     { value = value / 1024 / 1024 / 1024; unit = "GB"}
	        if (value > 1024 * 1024)            { value = value / 1024 / 1024; unit = "MB"}
	        else if (value > 1024)              { value = value / 1024; unit = "kB"}
	        value = this.round(value);
	        return [value, unit];
	        }

        this.set.dashboard_item_fill(id="server_up_time",           value=up_time);
        this.set.dashboard_item_fill(id="server_boot_time",         value=this.round(status_prf["server"]["boot"]),     unit="s", benchmark=true, warning=120, alarm=180);
        this.set.dashboard_item_fill(id="api_status_request",       value=this.round(status_api["/status"]),            unit="s", benchmark=true, warning=0.5, alarm=2.0);

        if (status["server_config_queues"]) {
            Object.keys(status["server_config_queues"]).forEach(key => { data_q["config"] += status["server_config_queues"][key]; });
            this.set.dashboard_item_fill(id="config_queue_wait",    value=this.round(status_prf["config"]["queue"]*-1), unit="s", benchmark=true, warning=10, alarm=20);
            this.set.dashboard_item_fill(id="config_queue_write",   value=this.round(status_prf["config"]["write"]),    unit="s", benchmark=true, warning=5, alarm=15);
            this.set.dashboard_item_fill(id="config_queue_size",    value=data_q["config"],                             unit="",  benchmark=true, warning=10, alarm=30);
            }
        if (status["server_object_queues"]) {
            Object.keys(status["server_object_queues"]).forEach(key => { data_q["object"] += status["server_object_queues"][key]; });
            this.set.dashboard_item_fill(id="object_queue_size",    value=data_q["object"], unit="", benchmark=true, warning=3, alarm=10);
            }
        Object.keys(status_cam).forEach(key => {
            if (status_prf["camera_recording_image"][key]) {
                html += this.set.dashboard_item_fill(id="record_image_"+key, value=this.round(status_prf["camera_recording_image"][key]), unit="s", benchmark=true, warning=0.5, alarm=1.0);
                }
            });
        if (status_prf["object_detection"]) {
            html += this.set.dashboard_item_fill(id="object_detection", value=this.round(status_prf["object_detection"]["image"]), unit="s", benchmark=true, warning=6, alarm=12);
            }
        if (status["database"]["type"] == "json" || status["database"]["type"] == "both") {
            html += this.set.dashboard_item_fill(id="locked_db",        value=status["database"]["db_locked_json"], unit="", benchmark=true, warning=2, alarm=4);
            html += this.set.dashboard_item_fill(id="locked_db_wait",   value=this.round(status["database"]["db_waiting_json"]), unit="s", benchmark=true, warning=2, alarm=4);
            }

        var available_hdd = status["system"]["hdd_total"] - status["system"]["hdd_used"];
        var available_mem = (status["system"]["mem_total"] - status["system"]["mem_used"]) / 1024;

        var [cache_value, cache_unit] = this.data_size(status["database"]["cache_size"]);
        if (cache_unit == "B" || cache_unit == "kB")    { cache_warning = 10000; cache_alarm = 20000; }
        else if (cache_unit == "MB")                    { cache_warning = 15; cache_alarm = 100; }
        else if (cache_unit == "GB")                    { cache_warning = 0; cache_alarm = 0.1; }

        html += this.set.dashboard_item_fill(id="cache_size",       value=cache_value,                                          unit=cache_unit, benchmark=true, warning=cache_warning, alarm=cache_alarm);
        html += this.set.dashboard_item_fill(id="cpu_usage",        value=this.round(status["system"]["cpu_usage"]),            unit="%",  benchmark=true, warning=70, alarm=90);
        html += this.set.dashboard_item_fill(id="cpu_temperature",  value=this.round(status["system"]["cpu_temperature"]),      unit="°C", benchmark=true, warning=60, alarm=75);
        html += this.set.dashboard_item_fill(id="hdd_available",    value=this.round(available_hdd),                            unit="GB", benchmark=true, warning=5, alarm=2);
        html += this.set.dashboard_item_fill(id="mem_available",    value=this.round(available_mem),                            unit="GB", benchmark=true, warning=1, alarm=0.4);
        html += this.set.dashboard_item_fill(id="mem_used",         value=this.round(status["system"]["mem_process"] / 1024),   unit="GB", benchmark=true, warning=1.5, alarm=2.5);
	    }

    /*
    * show or hide setting frames
    */
	this.toggle	= function (active=false) {
	
		if (active)	{ view_frame = "block"; view_settings = "none";  app_settings_active = false; window.scrollTo(0,0); }
		else		{ view_frame = "none";  view_settings = "block"; app_settings_active = true;  }

		for (var i=1;i<=app_frame_count;i++) {
			var element = document.getElementById("frame"+i);
			element.style.display = view_frame;
			}
		for (var i=1;i<=app_setting_count;i++) {
			var element = document.getElementById("setting"+i);
			element.style.display = view_settings;
			}
		}
}


app_scripts_loaded += 1;