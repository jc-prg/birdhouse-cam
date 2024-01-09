//--------------------------------
// config menu and main functions
//--------------------------------

var app_frame_count       = 5;
var app_frame_style       = "frame_column wide";
var app_setting_count     = 4;
var app_setting_style     = "frame_column wide";
var app_last_load         = 0;
var app_title             = "jc://birdhouse/";
var app_version           = "v1.0.7";
var app_api_version       = "N/A";
var app_api_dir           = "api/";
var app_api_status        = "status";
var app_reload_interval   = 5;
var app_loading_image     = "birdhouse/img/bird.gif"; // source: https://gifer.com/en/ZHug
var app_error_connect_image = "birdhouse/img/camera_na_server.jpg";
var app_unique_stream_url = true;			// doesn't work for chrome (assumption: mjpeg-streams are not closed correctly)
var app_unique_stream_id  = new Date().getTime();     // new ID per App-Start
var app_session_id        = "";

//--------------------------------
// create menu entries
//--------------------------------

function app_menu_entries(data) {
	var hideSettings    = "birdhouse_settings.toggle(true);";
	var weather_active  = data["SETTINGS"]["localization"]["weather_active"];
	var admin_type      = data["SETTINGS"]["server"]["admin_login"];

	var app_menu = [
		[lang("LIVESTREAM"),   "script", hideSettings+"birdhousePrint_load('INDEX',   '"+app_active_cam+"');"],
		[lang("FAVORITES"),    "script", hideSettings+"birdhousePrint_load('FAVORITES','"+app_active_cam+"');"],
		[lang("TODAY"),        "script", hideSettings+"birdhousePrint_load('TODAY',   '"+app_active_cam+"');"],
		[lang("VIDEOS"),       "script", hideSettings+"birdhousePrint_load('VIDEOS',  '"+app_active_cam+"');"],
		[lang("ARCHIVE"),      "script", hideSettings+"birdhousePrint_load('ARCHIVE', '"+app_active_cam+"');"]
		];

	if (weather_active) {
	    app_menu.push([lang("WEATHER"),      "script", hideSettings+"birdhousePrint_load('WEATHER', '"+app_active_cam+"');"]);
    }

	if (app_admin_allowed) {
	    birdhouse_adminAnswer(true);
        }

	if (app_admin_allowed) {
		app_menu = app_menu.concat([
		["LINE"],
		[lang("TODAY_COMPLETE"),"script", hideSettings+"birdhousePrint_load('TODAY_COMPLETE','"+app_active_cam+"');"],
		["LINE"],
		[lang("DEVICES"),   "script", hideSettings+"birdhousePrint_load('DEVICES','"+app_active_cam+"');"],
		[lang("CAMERAS"),   "script", hideSettings+"birdhousePrint_load('CAMERA_SETTINGS','"+app_active_cam+"');"],
		[lang("SETTINGS"),  "script", hideSettings+"birdhousePrint_load('SETTINGS','"+app_active_cam+"');"],
		]);
		if (admin_type == "LOGIN") {
    	    app_menu = app_menu.concat([
            ["LINE"],
            [lang("LOGOUT"), "script", "birdhouse_logout();"],
    		]);
		    }
		}
	else if (admin_type == "LOGIN") {
	    app_menu = app_menu.concat([
		["LINE"],
		[lang("LOGIN"),     "script", "birdhouse_loginDialog();"],
		]);
    }
	return app_menu;
}
	
//--------------------------------
// function to request status, update menu etc. (including initial load)
//--------------------------------

function app_initialize(data) {
	setTextById("headerRight", birdhouseHeaderFunctions() );
	app_api_version = data["API"]["version"];
	app_data = data;

	var settings = data["SETTINGS"];
    if (settings["localization"]["language"]) { LANG = settings["localization"]["language"]; }

	}

//--------------------------------
// function to request status, update menu etc. (including initial load)
//--------------------------------


function app_status(data) {

	if (reload) {
        birdhouse_loadSettings();
		birdhousePrint_load("INDEX","cam1");
		//app_active_cam = "cam1";
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
        // if (active["active_cam"] && active["active_cam"] != "")   { app_active_cam = active["active_cam"]; }
        if (status["background_process"] == true)	{ setTextById("statusLED","<div id='blue'></div>"); }
        else 					                	{ setTextById("statusLED","<div id='green'></div>"); }
        birdhouseStatus_print(data);
        }

	app_last_load = Date.now();
	}
	
//--------------------------------
// add code when checked the status
//--------------------------------

function app_check_status() {
	}
	
//--------------------------------
// add code when menu icon is clicked
//--------------------------------

function app_click_menu() {
	}
	
//--------------------------------
// add code when forced a reload
//--------------------------------

function app_force_reload(data) {
	birdhouseReloadView();
	}
	
//--------------------------------
// add code when theme changed
//--------------------------------

function app_theme_changed(theme) {
	}

//--------------------------------
// add code when screen size changed
//--------------------------------

function app_screen_size_changed(width, height) {
	console.log("Changed screen size to " + width + "x" + height);
	}

//--------------------------------
// add code when connection is lost
//--------------------------------

app_connection_error = false;
function app_connection_lost(error=false) {
    if (app_connection_error != error) {
        if (error) {
            // code if lost connection
            elementVisible("video_stream_offline");
            elementHidden("video_stream_online");
            elementVisible("lowres_today_error");
            elementHidden("lowres_today");
            birdhouseStatus_connectionError();
            app_connection_error = true;
        }
        else {
            app_unique_stream_id  = new Date().getTime();
            // code if got back connection
            elementVisible("video_stream_online");
            elementHidden("video_stream_offline");
            elementVisible("lowres_today");
            elementHidden("lowres_today_error");
            app_connection_error = false;
            birdhouseReloadView();
        }
    }
    app_connection_error = error;
}



