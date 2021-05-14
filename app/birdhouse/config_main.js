//--------------------------------
// config menu and main functions
//--------------------------------

var app_frame_count   = 4;
var app_frame_style   = "frame_column wide";
var app_setting_count = 4;
var app_setting_style = "setting_bg";
var app_last_load     = 0;
var app_title         = "jc://birdhouse/";
var app_version       = "v0.8.4"; 
var app_api_dir       = "api/";
var app_api_status    = "status";
var app_loading_image = "birdhouse/img/bird.gif"; //https://gifer.com/en/ZHug


//--------------------------------
// create menu entries
//--------------------------------

function app_menu_entries() {
	var app_menu = [
		[lang("LIVESTREAM"),   "script", "birdhousePrint_load('INDEX','"+app_active_cam+"');"],
		[lang("FAVORITS"),     "script", "birdhousePrint_load('FAVORITS','"+app_active_cam+"');"],
		[lang("TODAY"),        "script", "birdhousePrint_load('TODAY','"+app_active_cam+"');"],
		[lang("VIDEOS"),       "script", "birdhousePrint_load('VIDEOS','"+app_active_cam+"');"],
		[lang("ARCHIVE"),      "script", "birdhousePrint_load('ARCHIVE','"+app_active_cam+"');"],
		];
	if (app_admin_allowed) {
		app_menu = app_menu.concat([
		["LINE"],
		[lang("CAMERAS"),       "script", "birdhousePrint_load('CAMERAS','"+app_active_cam+"');"],
		[lang("TODAY_COMPLETE"),"script", "birdhousePrint_load('TODAY_COMPLETE','"+app_active_cam+"');"],
		["LINE"],
		[lang("SETTINGS"),      "script", "appMsg.alert('"+lang('NOT_IMPLEMENTED')+"');" ],
		]);
		}
	return app_menu;
	}
	
//--------------------------------
// function to request status, update menu etc. (including initial load)
//--------------------------------

function app_initialize(data) {
	setTextById("headerRight", birdhouseHeaderFunctions() );
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
		}
	if (data["DATA"]["background_process"] == true) {
		setTextById("statusLED","<div id='blue'></div>");
		}
	else {
		setTextById("statusLED","<div id='green'></div>");
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
	

