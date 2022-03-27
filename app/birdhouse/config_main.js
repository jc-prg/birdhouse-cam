//--------------------------------
// config menu and main functions
//--------------------------------

var app_frame_count       = 5;
var app_frame_style       = "frame_column wide";
var app_setting_count     = 4;
var app_setting_style     = "setting_bg";
var app_last_load         = 0;
var app_title             = "jc://birdhouse/";
var app_version           = "v0.9.1"; 
var app_api_version       = "N/A";
var app_api_dir           = "api/";
var app_api_status        = "status";
var app_reload_interval   = 5;
var app_loading_image     = "birdhouse/img/bird.gif"; // source: https://gifer.com/en/ZHug
var app_unique_stream_url = true;			// doesn't work for chrome (assumption: mjpeg-streams are not closed correctly)
var app_unique_stream_id  = new Date().getTime();     // new ID per App-Start


//--------------------------------
// create menu entries
//--------------------------------

function app_menu_entries() {
	var hideSettings = "birdhouse_settings.toggle(true);";
	var app_menu = [
		[lang("LIVESTREAM"),   "script", hideSettings+"birdhousePrint_load('INDEX',   '"+app_active_cam+"');"],
		[lang("FAVORITS"),     "script", hideSettings+"birdhousePrint_load('FAVORITS','"+app_active_cam+"');"],
		[lang("TODAY"),        "script", hideSettings+"birdhousePrint_load('TODAY',   '"+app_active_cam+"');"],
		[lang("VIDEOS"),       "script", hideSettings+"birdhousePrint_load('VIDEOS',  '"+app_active_cam+"');"],
		[lang("ARCHIVE"),      "script", hideSettings+"birdhousePrint_load('ARCHIVE', '"+app_active_cam+"');"],
		];
	if (app_admin_allowed) {
		app_menu = app_menu.concat([
		["LINE"],
		[lang("TODAY_COMPLETE"),"script", hideSettings+"birdhousePrint_load('TODAY_COMPLETE','"+app_active_cam+"');"],
		["LINE"],
		[lang("DEVICES"),       "script", hideSettings+"birdhousePrint_load('CAMERAS','"+app_active_cam+"');"],
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
	

