//--------------------------------
// config menu and main functions
//--------------------------------

var app_frame_count          = 5;
var app_frame_style          = "frame_column wide";
var app_setting_count        = 4;
var app_setting_style        = "frame_column wide";
var app_setting_style_header = "setting_bg header";

var app_last_load            = 0;
var app_title                = "jc://birdhouse/";
var app_version              = "v1.8.0";
var app_api_version          = "N/A";
var app_api_dir              = "api/";
var app_api_status           = "status";
var app_reload_interval      = 5;
var app_loading_image        = "birdhouse/img/bird.gif"; // source: https://gifer.com/en/ZHug
var app_error_connect_image  = "birdhouse/img/camera_na_server.jpg";
var app_unique_stream_url    = true;			// doesn't work for chrome (assumption: mjpeg-streams are not closed correctly)
var app_unique_stream_id     = new Date().getTime();     // new ID per App-Start
var app_session_id           = "";
var app_status_commands      = ["last-answer"];


/**
* create menu entries for the app
*
* @param (dict) object - data returned form server API
* @returns (array) - returns an array of array that contains the menu definition
*/
function app_menu_entries(data) {
	var hideSettings     = "birdhouse_settings.toggle(true);appSettings.hide();";
	var weather_active   = data["SETTINGS"]["localization"]["weather_active"];
	var detection_active = data["STATUS"]["object_detection"]["active"];
	var admin_type       = data["SETTINGS"]["server"]["admin_login"];

    if (!app_birdhouse_closed || app_admin_allowed) {
        var app_menu = [
            [lang("LIVESTREAM"),   "script", "birdhousePrint_page('INDEX');"],
            [lang("TODAY"),        "script", "birdhousePrint_page('TODAY');"],
            [lang("ARCHIVE"),      "script", "birdhousePrint_page('ARCHIVE');"],
            ["LINE"],
            [lang("FAVORITES"),    "script", "birdhousePrint_page('FAVORITES');"],
            [lang("VIDEOS"),       "script", "birdhousePrint_page('VIDEOS');"],
            [lang("DIARY"),        "script", "birdhousePrint_page('DIARY');"],
            ];

        if (detection_active) { app_menu.push([lang("BIRDS"),        "script", "birdhousePrint_page('OBJECTS');"]); }
        if (weather_active)   { app_menu.push([lang("WEATHER"),      "script", "birdhousePrint_page('WEATHER');"]); }

        if (app_admin_allowed) {
            birdhouse_adminAnswer(true);
            }

        if (app_admin_allowed) {
            app_menu = app_menu.concat([
            ["LINE"],
            [lang("TODAY_COMPLETE"),    "script", "birdhousePrint_page('TODAY_COMPLETE');"],
            [lang("SETTINGS"),          "script", "birdhousePrint_page('SETTINGS');"],
            ]);
            if (admin_type == "LOGIN") {
                app_menu = app_menu.concat([
                ["LINE"],
                [lang("LOGOUT"), "script", "birdhousePrint_page('LOGOUT');"],
                ]);
                }
            }
        else if (admin_type == "LOGIN") {
            app_menu = app_menu.concat([
                ["LINE"],
                [lang("LOGIN"),     "script", "birdhousePrint_page('LOGIN','INDEX');"],
                ]);
            }
        }
    else {
        var app_menu = [[lang("LOGIN"),     "script", "birdhousePrint_page('LOGIN','INDEX');"]];
        }
	return app_menu;
}

/*
* function to configure setting entries
*/

function app_setting_entries() {
    // add your setting entries here
    // appSettings.add_entry(id, title, icon, call_function, show_header=true);

    birdhouse_settings.init();

    var hideSettings     = "birdhouse_settings.toggle(true);";
    var init             = "appSettings.clear_frames();appSettings.show();"

    appSettings.icon_dir = "framework/";

    appSettings.setting_entries = {};

    appSettings.add_entry("START1", "jc://birdhouse-cam/",  "birdhouse/img/bird.gif",   "");
    appSettings.add_entry("START2", "<div id='device_status_short'><b>"+lang("DEVICE_OVERVIEW")+"</b><br/>"+lang("PLEASE_WAIT")+" ...</div>",  "",   "");

    appSettings.add_entry("SETTINGS_CAMERAS",       lang("SETTINGS_CAMERAS"),       "birdhouse/img/av_device",   "birdhouse_settings.create_new('SETTINGS_CAMERAS');");
    appSettings.add_entry("SETTINGS_IMAGE",         lang("SETTINGS_IMAGE"),         "birdhouse/img/image",       "birdhouse_settings.create_new('SETTINGS_IMAGE');");
    appSettings.add_entry("SETTINGS_DEVICES",       lang("SETTINGS_DEVICES"),       "birdhouse/img/temperature", "birdhouse_settings.create_new('SETTINGS_DEVICES');");
    appSettings.add_entry("SETTINGS_INFORMATION",   lang("SETTINGS_INFORMATION"),   "info",                      "birdhouse_settings.create_new('SETTINGS_INFORMATION');");
    appSettings.add_entry("SETTINGS_STATISTICS",    lang("SETTINGS_STATISTICS"),    "birdhouse/img/statistics",  "birdhouse_settings.create_new('SETTINGS_STATISTICS');");
    appSettings.add_entry("SETTINGS_SERVER",        lang("SETTINGS_SERVER"),        "settings",                  "birdhouse_settings.create_new('SETTINGS_SERVER');");

    appSettings.add_entry("CLOSE", "<div id='app_open_close'><b>"+lang("CLOSE_BIRDHOUSE")+"</b><br/>"+lang("PLEASE_WAIT")+" ...</div>",  "",   "");

    }

/*
* function to request status, update menu etc. (including initial load)
*
* @param (dict) object - data returned form server API
*/
function app_initialize(data) {
	setTextById("headerRight", birdhouseHeaderFunctions() );
	app_api_version = data["API"]["version"];
	app_data = data;

	var settings = data["SETTINGS"];
    if (settings["localization"]["language"]) {
        LANG = settings["localization"]["language"];
        app_setting_entries();
        }
	}

/*
* function to request status, update menu etc. (including initial load)
*
* @param (dict) object - data returned form server API
*/
function app_status(data) {

	if (reload) {
	    var maintenance = data["API"]["maintenance"];
	    if (maintenance) {
	        app_birdhouse_closed = maintenance["closed"];
	        }

        birdhouse_loadSettings();
		birdhousePrint_load("INDEX","cam1");
		reload = false;
		}
	else {
        var active = data["DATA"]["active"];
        var status = data["STATUS"]["server"] ;

        if (status["last_answer"] != "") {
            var msg = status["last_answer"];
            appMsg.alert(lang(msg[0]));
            if (msg[0] == "RANGE_DONE") { button_tooltip.hide("info"); }
            birdhouseReloadView();
            }
        // if (active["active_cam"] && active["active_cam"] != "")   { app_active.cam = active["active_cam"]; }
        if (status["background_process"] == true)	{ setTextById("statusLED","<div id='blue'></div>"); }
        else 					                	{ setTextById("statusLED","<div id='green'></div>"); }
        birdhouseStatus_print(data);
        }

    birdhouseSetMainVars(data);
    birdhouseSetMainStatus(data);
	app_last_load = Date.now();
	}
	
/*
* add code when checked the status
*/
function app_check_status() {
	}
	
/*
* add code when menu icon is clicked
*/
function app_click_menu() {
	}
	
/*
* add code when forced a reload
*
* @param (dict) object - data returned form server API
*/
function app_force_reload(data) {
	birdhouseReloadView();
	}

/*
* add code when theme changed
*
* @param (string) theme - active theme
*/
function app_theme_changed(theme) {
	}

/*
* add code when screen size changed
*
* @param (integer) width: screen width
* @param (integer) height: screen height
*/
function app_screen_size_changed(width, height) {
	console.log("Changed screen size to " + width + "x" + height);
	if (app_floating_lowres) {
        repositionFloatingLowres();
        }
	}

/*
* add code when connection is lost
*
* @param (boolean) error: true if connection error
*/
app_connection_error = false;
function app_connection_lost(error=false) {
    if (app_connection_error != error) {
        if (error) {
            // code if lost connection
            app_connection_error = true;
            elementVisible("video_stream_offline");
            elementHidden("video_stream_online");
            elementVisible("lowres_today_error");
            elementHidden("lowres_today");
            elementVisible("lowres_floating_error", "flex");
            elementHidden("lowres_floating");
            birdhouseStatus_connectionError();
            birdhouse_exitFullscreen();
        }
        else {
            app_connection_error = false;
            app_unique_stream_id = new Date().getTime();
            // code if got back connection
            elementVisible("video_stream_online");
            elementHidden("video_stream_offline");
            elementVisible("lowres_today");
            elementHidden("lowres_today_error");
            elementVisible("lowres_floating", "flex");
            elementHidden("lowres_floating_error");
            birdhouseReloadView();
        }
    }
    app_connection_error = error;
}


app_scripts_loaded += 1;
