//--------------------------------
// config menu and main functions
//--------------------------------

var app_frame_count       = 5;
var app_frame_style       = "frame_column wide";
var app_setting_count     = 4;
var app_setting_style     = "frame_column wide";
var app_last_load         = 0;
var app_title             = "jc://birdhouse/";
var app_version           = "v0.9.4";
var app_api_version       = "N/A";
var app_api_dir           = "api/";
var app_api_status        = "status";
var app_reload_interval   = 5;
var app_loading_image     = "birdhouse/img/bird.gif"; // source: https://gifer.com/en/ZHug
var app_error_connect_image = "birdhouse/img/camera_na_server.jpg";
var app_unique_stream_url = true;			// doesn't work for chrome (assumption: mjpeg-streams are not closed correctly)
var app_unique_stream_id  = new Date().getTime();     // new ID per App-Start


//--------------------------------
// create menu entries
//--------------------------------

function app_menu_entries(data) {
	var hideSettings = "birdhouse_settings.toggle(true);";
	var weather_active = data["DATA"]["localization"]["weather_active"];
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
		app_menu = app_menu.concat([
		["LINE"],
		[lang("TODAY_COMPLETE"),"script", hideSettings+"birdhousePrint_load('TODAY_COMPLETE','"+app_active_cam+"');"],
		["LINE"],
		[lang("DEVICES"),       "script", hideSettings+"birdhousePrint_load('DEVICES','"+app_active_cam+"');"],
		[lang("SETTINGS"),      "script", "birdhouse_settings.create();" ],
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
    if (data["DATA"]["localization"]["language"]) { LANG = data["DATA"]["localization"]["language"]; }
	}

//--------------------------------
// function to request status, update menu etc. (including initial load)
//--------------------------------


function app_status(data) {
	if (reload) { 
		birdhousePrint_load("INDEX","cam1");
		}
		
	if (data["DATA"]["last_answer"] != "") {
		var msg = data["DATA"]["last_answer"];
		appMsg.alert(lang(msg[0]));
		if (msg[0] == "RANGE_DONE") { button_tooltip.hide("info"); }
		birdhouseReloadView();
		}
	if (data["DATA"]["background_process"] == true)	{ setTextById("statusLED","<div id='blue'></div>"); }
	else 							{ setTextById("statusLED","<div id='green'></div>"); }

    birdhouseStatus_print(data);
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

var app_connection_status = true;
function app_connection_lost(error=false) {
    if (app_connection_status != error) {
        if (error) {
            // code if lost connection
            elementVisible("video_stream_offline");
            elementHidden("video_stream_online");
            app_connection_status = false;
        }
        else {
            // code if got back connection
            elementVisible("video_stream_online");
            elementHidden("video_stream_offline");
            birdhouseReloadView();
            app_connection_status = true;
        }
    }
    app_connection_status = error;
}



