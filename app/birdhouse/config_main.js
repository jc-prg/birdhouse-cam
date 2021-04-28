//--------------------------------
// config menu and main functions
//--------------------------------

var app_frame_count   = 4;
var app_setting_count = 4;
var app_active_cam    = "cam2";

var app_menu = [
	[lang("LIVESTREAM"),   "script", "birdhousePrint_load('INDEX','"+app_active_cam+"');"],
	[lang("FAVORITS"),     "script", "birdhousePrint_load('FAVORITS','"+app_active_cam+"');"],
	[lang("TODAY"),        "script", "birdhousePrint_load('TODAY','"+app_active_cam+"');"],
	[lang("VIDEOS"),       "script", "birdhousePrint_load('VIDEOS','"+app_active_cam+"');"],
	[lang("ARCHIVE"),      "script", "birdhousePrint_load('ARCHIVE','"+app_active_cam+"');"],
	["LINE"],
	[lang("CAMERAS"),       "script", "birdhousePrint_load('CAMERAS','"+app_active_cam+"');"],
	[lang("TODAY_COMPLETE"),"script", "birdhousePrint_load('TODAY_COMPLETE','"+app_active_cam+"');"],
	["LINE"],
	[lang("SETTINGS"),      "script", "appMsg.alert('"+lang('NOT_IMPLEMENTED')+"');" ],
	]
	
//--------------------------------
// function to request status, update menu etc. (including initial load)
//--------------------------------

function app_status(data) {
	if (reload) { birdhousePrint(data=data, active_page=appActivePage, camera=app_active_cam); reload = false; }
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
