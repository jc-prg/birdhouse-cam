//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// main functions 
//--------------------------------------

var color_code = {
	"star"    : "lime",
	"detect"  : "aqua",
	"recycle" : "red",
	"default" : "white",
	"request" : "yellow",
	"data"    : "lightblue"
	}
	
var app_available_cameras = [];
var app_available_sensors = [];
var app_available_micros  = [];

var app_active_page       = "";
var app_active_date       = "";
var app_active_mic        = "";
var app_camera_source     = {};
var app_recycle_range     = {};
var app_active_cam        = "cam1";
var app_admin_allowed     = false;
var app_data              = {};

var app_frame_header = "frame1";
var app_frame_content = "frame2";
var app_frame_info = "frame3";
var app_frame_index = "frame4";


function birdhousePrint_load(view="INDEX", camera="", date="") {

	var commands = [view];
	if (camera != "" && date != "")	{ commands.push(camera); commands.push(date); }
	else if (camera != "")			{ commands.push(camera); }
	else					{ commands.push(app_active_cam); }
	
	console.debug("Request "+view+" / "+camera+" / "+date);	
	appFW.requestAPI('GET',commands,"",birdhousePrint,"","birdhousePrint_load");
	}
	
function birdhousePrint(data) {
    app_data = data;
	console.debug("Request->Print ...");
	var sensor_data = data["DATA"]["devices"]["sensors"];
	if (sensor_data["sensor1"]) {
	    console.log("Sensor data: "+sensor_data["sensor1"]["temperature"] + "C / "+ sensor_data["sensor1"]["humidity"] + "%");
	    }

	birdhouseCameras = data["DATA"]["devices"]["cameras"];
	birdhouseMicrophones = data["DATA"]["devices"]["microphones"];
	birdhouseStream_load(data["DATA"]["server"]["ip4_address"], birdhouseMicrophones);
	//setTimeout(function(){  },2000);

	var date          = data["DATA"]["active_date"];
	var camera        = data["DATA"]["active_cam"];
	if (camera == "") 	{ camera = app_active_cam; }
	else			{ app_active_cam = camera; }
	
	console.log("Request->Print "+app_active_page+" / "+camera+" / "+date);	

	birdhouseSetMainVars(data);
	birdhousePrintTitle(data, app_active_page, camera);	
	setTextById("headerRight", birdhouseHeaderFunctions() );

	// check if admin allowed! -> create respective menu
	
	if (app_active_page == "INDEX")                 { birdhouse_INDEX(data, camera); }
	else if (app_active_page == "CAMERAS")          { birdhouseDevices(lang("DEVICES"), data, camera); }
	else if (app_active_page == "FAVORITES")        { birdhouse_LIST(lang("FAVORITES"),  data, camera); }
	else if (app_active_page == "ARCHIVE")          { birdhouse_LIST(lang("ARCHIVE"), data, camera); }
	else if (app_active_page == "TODAY")            { birdhouse_LIST(lang("TODAY"), data, camera); }
	else if (app_active_page == "TODAY_COMPLETE")   { birdhouse_LIST(lang("TODAY_COMPLETE"), data, camera, false); }
	else if (app_active_page == "VIDEOS")           { birdhouse_LIST(lang("VIDEOS"), data, camera); }
	else if (app_active_page == "VIDEO_DETAIL")	    { birdhouse_VIDEO_DETAIL(lang("VIDEOS"), data, camera); }
	else { setTextById(app_frame_content,lang("ERROR") + ": "+app_active_page); }

	birdhouseStatus_print(data);

	scroll(0,0);
	}

function birdhousePrintTitle(data, active_page="", camera="") {

	var title = document.getElementById("navTitle");
	if (title.innerHTML == "..." && data["DATA"]["title"] != undefined)	{ setNavTitle(data["DATA"]["title"]); setTextById("title",data["DATA"]["title"]); }
	if (data["DATA"]["subtitle"] != undefined)   { setTextById(app_frame_header, "<center><h2>" + data["DATA"]["subtitle"] + "</h2></center>"); }
	else                                         { setTextById(app_frame_header, "<center><h2>" + data["DATA"]["title"] + "</h2></center>"); }
	if (data["DATA"]["links"] != undefined)      { setTextById(app_frame_index, "<center>" + birdhouse_Links(data["DATA"]["links"]) + "</center>"); }
	if (data["STATUS"]["start_time"] != undefined) { setTextById("frame5", "<center><small>" + lang( "STARTTIME") + ": " + data["STATUS"]["start_time"] + "</small></center>"); }
	else                                           { setTextById("frame5", ""); }
	}


function birdhouseSetMainVars(data) {

	if (data["DATA"]["devices"]["cameras"] != undefined) {
	    for (let key in data["DATA"]["devices"]["cameras"]) { if (data["DATA"]["devices"]["cameras"][key]["active"]) { app_available_cameras.push(key) }}
	    }
	if (data["DATA"]["devices"]["sensors"] != undefined) {
	    for (let key in data["DATA"]["devices"]["sensors"]) { if (data["DATA"]["devices"]["sensors"][key]["active"]) { app_available_sensors.push(key) }}
	    }
	if (data["DATA"]["devices"]["microphones"] != undefined) {
	    for (let key in data["DATA"]["devices"]["microphones"]) { if (data["DATA"]["devices"]["microphones"][key]["active"]) { app_available_micros.push(key) }}
	    }

	if (data["DATA"]["active_cam"] != undefined && data["DATA"]["active_cam"] != "") { app_active_cam = data["DATA"]["active_cam"]; }
	else                                                                             { app_active_cam = app_available_cameras[0]; }
	app_active_mic = app_available_micros[0];

	if (data["DATA"]["active_page"] != "" && data["DATA"]["active_page"] != undefined && data["DATA"]["active_page"] != "status") { app_active_page = data["DATA"]["active_page"]; }
	else if (data["DATA"]["active_page"] != "status")                                  { app_active_page = "INDEX"; }

	if (data["DATA"]["active_date"] != "" && data["DATA"]["active_date"] != undefined) { app_active_date = data["DATA"]["active_date"]; }
	else                                                                               { app_active_date = ""; }

	if (data["STATUS"]["admin_allowed"] != undefined)                                  { app_admin_allowed = data["STATUS"]["admin_allowed"]; }
	}
	
function birdhouseHeaderFunctions() {
	var html = "";
	var switch_cam  = "<img class='header_icon' src='birdhouse/img/switch-camera-white.png' onclick='birdhouseSwitchCam();' style='position:relative;top:-4px;'>";
	var reload_view = "<img class='header_icon' src='birdhouse/img/reload-white.png' onclick='birdhouseReloadView();'>";
	var audio_stream = "<img id='stream_toggle_header' class='header_icon_wide' src='birdhouse/img/icon_bird_mute.png' onclick='birdhouseStream_toggle();'>";
	var active_cam  = "<text style='position:relative;left:22px;top:2px;font-size:7px;'>"+app_active_cam.toUpperCase()+"</text>";
	if (app_active_mic && !iOS()) { var active_mic  = "<text style='position:relative;left:22px;top:2px;font-size:7px;'>"+app_active_mic.toUpperCase()+"</text>"  + audio_stream; }
	else                        { var active_mic = ""; }
	var info        = "&nbsp;";
	var info = birdhouse_tooltip( info, "<div id='command_dropdown' style='width:90%;margin:auto;'>empty</div>", "info", "" );
	
	//html = reload_view + audio_stream + active_cam + switch_cam + "&nbsp;&nbsp;&nbsp;" + info;
	html = reload_view;
	if (app_available_cameras != undefined && app_available_cameras.length > 1) { html += active_cam + switch_cam; }
	if (app_available_cameras != undefined && app_available_micros.length > 1)  { html += active_mic; }
/*
	if (app_available_cameras == undefined)	{ html = reload_view + audio_stream + "&nbsp;&nbsp;&nbsp;&nbsp;" + info; }
	else if (app_available_cameras.length > 1) { html = reload_view + audio_stream + active_cam + switch_cam + "&nbsp;&nbsp;&nbsp;" + info; }
	else { html = reload_view + audio_stream + "&nbsp;&nbsp;&nbsp;&nbsp;" + info; }
*/
	html += "&nbsp;&nbsp;&nbsp;" + info;
	return html;
	}
	
function birdhouseSwitchCam() {
	var current_cam = 0;
	for (i=0;i<app_available_cameras.length;i++) {
		if (app_available_cameras[i] == app_active_cam) { current_cam = i; }
		}
	var next_cam = current_cam + 1;
	if (next_cam > app_available_cameras.length-1) { next_cam = 0; }
	
	console.log("birdhouseSwitchCam: "+app_active_cam+"->"+app_available_cameras[next_cam]);
	birdhousePrint_load(view=app_active_page, camera=app_available_cameras[next_cam], date=app_active_date);
}

function birdhouseReloadView() {
	console.log("birdhouseReloadView: "+app_active_page+"/"+app_active_cam+"/"+app_active_date);
	app_recycle_range = {};
	birdhouse_overlayHide();
	setTextById("headerRight", birdhouseHeaderFunctions() );
	
	if (app_active_page == "INDEX") {
		for (let key in app_camera_source) {
			var image = document.getElementById("stream_"+key);
			image.src = "";
			
			app_camera_source[key] = app_camera_source[key].replaceAll("//","/");
			app_camera_source[key] = app_camera_source[key].replace(":/","://");
			if (app_unique_stream_url)	{ image.src = app_camera_source[key]+"?"+app_unique_stream_id; }
			else                        { image.src = app_camera_source[key]; }
			}
		}
	else {
		birdhousePrint_load(view=app_active_page, camera=app_active_cam, date=app_active_date);
		}
	}	

