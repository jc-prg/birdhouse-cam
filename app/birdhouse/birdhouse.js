//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// main functions 
//--------------------------------------

var color_code = {
	"star"    : "lime",
	"detect"  : "DodgerBlue",
	"object"  : "aqua",
	"recycle" : "red",
	"default" : "white",
	"request" : "yellow",
	"data"    : "gray"
	}

loadingImage = "birdhouse/img/bird.gif";

var app_loading_image     = "birdhouse/img/bird.gif";
var app_available_cameras = [];
var app_available_sensors = [];
var app_available_micros  = [];

var app_active_page       = "";
var app_last_active_page  = "";
var app_active_date       = "";
var app_active_mic        = "";
var app_camera_source     = {};
var app_recycle_range     = {};
var app_active_cam        = "cam1";
var app_admin_allowed     = false;
var app_data              = {};
var app_bird_names        = {};

var app_collect4download  = false;
var app_collect_list      = [];
var app_header_opened     = {};

var app_frame_header    = "frame1";
var app_frame_content   = "frame2";
var app_frame_info      = "frame3";
var app_frame_index     = "frame4";

var app_scripts_loaded  = 0;
var app_first_load      = true;
var app_2nd_load        = true;

/*
* additional scripts and style sheet files to be loaded
*/
var birdhouse_js = [
    "birdhouse-api-requests.js",
    "birdhouse-audio.js",
    "birdhouse-charts.js",
    "birdhouse-devices.js",
    "birdhouse-downloads.js",
    "birdhouse-functions.js",
    "birdhouse-image.js",
    "birdhouse-image-overlay.js",
    "birdhouse-objects.js",
    "birdhouse-settings.js",
    "birdhouse-status.js",
    "birdhouse-views.js",
    "birdhouse-views-index.js",
    "birdhouse-weather.js",
    "video-player-template.js",
//    "pinch-zoom.umd.js",
    "config_language.js",
    "config_main.js",
    "config_stage.js"
];

var birdhouse_css = [
    "style.css",
    "style-streams.css",
    "video-player.css",
    "style-settings.css",
    "style-labels.css",
    "style-laptop.css",
    "style-iphone.css",
    "style-ipad.css",
    "style-image-overlay.css",
    "style-dark.css",
    "style-slider.css",
    "style-slider-dark.css",
];

function birdhouse_modules_loaded() {
    if (app_scripts_loaded == birdhouse_js.length)  { return true; }
    else                                            { return false; }
}

/*
* request loading of a specific view -> calls birdhousePrint() with retuned data
*
* @param (string) view: view to be requested; available: INDEX, TODAY, TODAY_COMPLETE, ARCHIVE, OBJECT, SETTINGS, FAVORITES, VIDEOS, VIDEO_DETAIL, PROCESSING, INFO, ...
* @param (string) camera: camera id of active camera
* @param (string) data: active date, to be combined with view TODAY in format YYYYMMDD
* @param (string) label: active label, will simulate a click on a object/bird label when loaded the complete view
*/
function birdhousePrint_load(view="INDEX", camera="", date="", label="") {

	if (app_first_load || app_2nd_load) {
	    if (app_first_load) { app_first_load = false; }
	    else                { app_2nd_load = false; }
	    var param = window.location.href.split("?");
	    var options = ["INDEX", "DEVICES", "FAVORITES", "ARCHIVE", "OBJECTS", "TODAY", "INFO",
	                   "WEATHER", "IMAGE_SETTINGS", "SETTINGS", "PROCESSING", "STATISTICS"];
	    if (options.includes(param[1])) {
	        view = param[1];
	        app_active_page = param[1];
	        app_last_active_page = param[1];
	        }

        birdhouse_loadChartJS();
	    birdhouse_birdNamesRequest();
	    }

	var commands = [view];
	if (camera != "" && date != "")	{ commands.push(date); commands.push(camera); app_active_cam = camera; }
	else if (camera != "")          { commands.push(camera); app_active_cam = camera; }
	else                            { commands.push(app_active_cam); }
	if (label != "")                { commands.push(label); }
	
	console.debug("Request "+view+" / "+camera+" / "+date+" / "+label);
	birdhouse_genericApiRequest("GET", commands, birdhousePrint);
	}

/*
* coordinate complete view creation (depending data returned to an API request)
*
* @param (dict) data: data returned from API
*/
function birdhousePrint(data) {
    //app_data = data;
	console.debug("Request->Print ...");

	window.scrollTo(0,0);
	var data_settings = app_data["SETTINGS"];
	var data_active   = data["DATA"]["active"];

    birdhouseSetMainVars(data);
    overlayImageList = [];

    var initial_setup   = data["STATUS"]["server"]["initial_setup"];
	var date            = data_active["active_date"];
	var camera          = data_active["active_cam"];
	if (camera == "") 	{ camera = app_active_cam; }
	else			    { app_active_cam = camera; }

    for (let camera in app_data["SETTINGS"]["devices"]["cameras"]) {
        birdhouseDevices_cameraSettingsLoad(camera, false);
    }

    if (data_settings["localization"]["language"]) { LANG = data_settings["localization"]["language"]; }

	var sensor_data = data_settings["devices"]["sensors"];
	if (sensor_data["sensor1"]) {
	    console.log("Sensor data: "+sensor_data["sensor1"]["temperature"] + "C / "+ sensor_data["sensor1"]["humidity"] + "%");
	    }

    var server_link = "";
    if (data_settings["server"]["ip4_address"] == "") {
        var this_server = window.location.href;
        this_server     = this_server.split("//")[1];
        this_server     = this_server.split("/")[0];
        this_server     = this_server.split(":")[0];
        server_link     = this_server;
    }
    else {
        server_link = data_settings["server"]["ip4_address"];
    }

	birdhouseCameras     = data_settings["devices"]["cameras"];
	birdhouseMicrophones = data_settings["devices"]["microphones"];

	birdhouseAudioStream_load(birdhouseMicrophones);
    birdhouse_KillActiveStreams();
	birdhouseSetMainStatus(data);
	birdhousePrintTitle(data, app_active_page);
    setTextById("headerRight", birdhouseHeaderFunctions() );

	console.log("---> birdhousePrint: "+app_active_page+" / "+camera+" / "+date);

    var success = true;
	if (app_active_page == "INDEX" && initial_setup) { birdhouse_settings.create(); return; }
	else if (app_active_page == "ARCHIVE")           { success = birdhouse_LIST(lang("ARCHIVE"), data, camera); }
	else if (app_active_page == "DEVICES")           { birdhouseDevices(lang("DEVICES"), data, camera); }
	else if (app_active_page == "FAVORITES")         { success = birdhouse_LIST(lang("FAVORITES"), data, camera); }
	else if (app_active_page == "IMAGE_SETTINGS")    { birdhouseDevices_cameraSettings(data); }
	else if (app_active_page == "INDEX")             { birdhouse_INDEX(data, camera); }
	else if (app_active_page == "INFO") 	         { birdhouse_settings.create("INFO_ONLY"); }
	else if (app_active_page == "PROCESSING")        { birdhouse_settings.create("PROCESSING"); }
	else if (app_active_page == "OBJECTS")           { birdhouse_OBJECTS(lang("BIRDS_DETECTED"), data); }
	else if (app_active_page == "SETTINGS")          { birdhouse_settings.create(); }
	else if (app_active_page == "STATISTICS")        { birdhouse_STATISTICS("STATISTICS", data); }
	else if (app_active_page == "TODAY")             { birdhouse_LIST(lang("TODAY"), data, camera); }
	else if (app_active_page == "TODAY_COMPLETE")    { birdhouse_LIST(lang("TODAY_COMPLETE"), data, camera, false); }
	else if (app_active_page == "VIDEOS")            { birdhouse_LIST(lang("VIDEOS"), data, camera); }
	else if (app_active_page == "VIDEO_DETAIL")	     { birdhouse_VIDEO_DETAIL(lang("VIDEOS"), data, camera); }
	else if (app_active_page == "WEATHER")           { birdhouse_showWeather(); }
	else { setTextById(app_frame_content,lang("ERROR") + ": "+app_active_page); }

	if (success == false) {
	    app_active_page = app_last_active_page;
	    }
	else {
	    app_last_active_page = app_active_page;
	    }
	}

/*
* set title in the header and prepare footer for server data to be loaded
*
* @param (dict) data: data returned from API
* @param (string) active_page: active page
*/
function birdhousePrintTitle(data, active_page="") {

	var title         = document.getElementById("navTitle");
	var data_view     = data["DATA"]["view"];
	var data_settings = data["SETTINGS"];

	if (title.innerHTML == "..." && data_settings["title"] != undefined)
	                                             { setNavTitle(data_settings["title"]); setTextById("title",data_settings["title"]); }

	if (data_view["subtitle"] != undefined)      { birdhouse_frameHeader(data_view["subtitle"]); }
	else if (data_view["title"] != undefined)    { birdhouse_frameHeader(data_view["title"]); }

	if (data_view["links"] != undefined)         { birdhouse_frameFooter(birdhouse_Links(data_view["links"])); }

	setTextById("frame5", "<center><small><div id='server_start_time'>" + lang("PLEASE_WAIT") + "</div></small></center>");
	}

/*
* cache latest data from API in the var app_data
*
* @param (dict) data: data returned from API
*/
function birdhouseLoadSettings(data) {

    app_data = data;
}

/*
* This function sets main variables based on the provided data. It checks if certain data properties are defined
* and active, and if so, it populates arrays with available cameras, sensors, and microphones.
*
* @param (dict) data: data returned from API
*/
function birdhouseSetMainVars(data) {
    //if (!data["STATUS"]) { data["STATUS"] = app_data["STATUS"]; }
    var data_settings = data["SETTINGS"];
    var initial_setup = data["STATUS"]["server"]["initial_setup"];

	if (data_settings["devices"]["cameras"] != undefined) {
	    for (let key in data_settings["devices"]["cameras"]) {
	        if (data_settings["devices"]["cameras"][key]["active"])
	                                                            { app_available_cameras.push(key) }}
	    }
	if (data_settings["devices"]["sensors"] != undefined) {
	    for (let key in data_settings["devices"]["sensors"]) {
	        if (data_settings["devices"]["sensors"][key]["active"])
	                                                            { app_available_sensors.push(key) }}
	    }
	if (data_settings["devices"]["microphones"] != undefined) {
	    for (let key in data_settings["devices"]["microphones"]) {
	        if (data_settings["devices"]["microphones"][key]["active"])
	                                                            { app_available_micros.push(key) }}
	    }
    }

/*
* This function sets main status variables based on the provided data. It checks if certain data properties are defined
* and active, and if so, it populates the active page, micro, and date, and if logged in as admin.
*
* @param (dict) data: data returned from API
*/
function birdhouseSetMainStatus(data) {
    var status_view  = data["STATUS"]["view"];
    var status_admin = data["STATUS"]["admin_allowed"];

	app_active_mic = app_available_micros[0];

	if (status_view["active_page"] != "" && status_view["active_page"] != undefined && status_view["active_page"] != "status")
	                                                        { app_active_page = status_view["active_page"]; }
	else if (status_view["active_page"] != "status")        { app_active_page = "INDEX"; }

	if (status_view["active_date"] != "" && status_view["active_date"] != undefined)
	                                                        { app_active_date = status_view["active_date"]; }
	else                                                    { app_active_date = ""; }

	if (status_admin != undefined) { app_admin_allowed = status_admin; }
	}

/*
* create header icons depending on status information (active devices, active download, ...)
*
* @returns (string): html header content
*/
function birdhouseHeaderFunctions() {
	var html = "";
	var download_info   = "<img class='header_icon' src='birdhouse/img/download-white.png' onclick='archivDownload_requestList();' style='position:relative;right:22px;top:-2px;'>";
	download_info       = "<text class='download_label' id='collect4download_amount2' onclick='archivDownload_requestList();'>0</text>" + download_info;
	var switch_cam      = "<img class='header_icon' src='birdhouse/img/switch-camera-white.png' onclick='birdhouseSwitchCam();' style='position:relative;top:-4px;'>";
	var reload_view     = "<img class='header_icon' src='birdhouse/img/reload-white.png' onclick='birdhouseReloadView();'>";
	var audio_stream    = "<img id='stream_toggle_header' class='header_icon_wide' src='birdhouse/img/icon_bird_mute.png' onclick='birdhouseAudioStream_toggle();'>";
	var active_cam      = "<text style='position:relative;left:22px;top:2px;font-size:7px;'>"+app_active_cam.toUpperCase()+"</text>";
	var mic_config      = app_data["SETTINGS"]["devices"]["microphones"][app_active_mic];

    if (app_active_mic && mic_config && mic_config["codec"] && mic_config["codec"] == "mp3")
                                    { var active_mic  = "<text style='position:relative;left:22px;top:2px;font-size:7px;'>"+app_active_mic.toUpperCase()+"</text>"  + audio_stream; }
	if (app_active_mic && !iOS())   { var active_mic  = "<text style='position:relative;left:22px;top:2px;font-size:7px;'>"+app_active_mic.toUpperCase()+"</text>"  + audio_stream; }
	else                            { var active_mic = ""; }

	console.error(app_active_mic);
	console.error(app_data["SETTINGS"]["devices"]["microphones"][app_active_mic]);

	var info_parent     = "&nbsp;";
	var info            = birdhouse_tooltip( info_parent, "<div id='command_dropdown' style='width:90%;margin:auto;'>empty</div>", "info", "" );
	
	//html = reload_view + audio_stream + active_cam + switch_cam + "&nbsp;&nbsp;&nbsp;" + info;
	html = reload_view;
	if (app_available_cameras != undefined && app_available_cameras.length > 1) { html += active_cam + switch_cam; }
	if (app_available_cameras != undefined && app_available_micros.length > 1)  { html += active_mic; }
	if (app_collect4download) { html = download_info + html; }
/*
	if (app_available_cameras == undefined)	{ html = reload_view + audio_stream + "&nbsp;&nbsp;&nbsp;&nbsp;" + info; }
	else if (app_available_cameras.length > 1) { html = reload_view + audio_stream + active_cam + switch_cam + "&nbsp;&nbsp;&nbsp;" + info; }
	else { html = reload_view + audio_stream + "&nbsp;&nbsp;&nbsp;&nbsp;" + info; }
*/
    setTextById("headerRightToolTip", info)
	html += "&nbsp;&nbsp;&nbsp;";// + info;
	return html;
	}

/*
* toggle between available cameras and trigger view reload
*/
function birdhouseSwitchCam() {
	var current_cam = 0;
	for (i=0;i<app_available_cameras.length;i++) {
		if (app_available_cameras[i] == app_active_cam) { current_cam = i; }
		}
	var next_cam = current_cam + 1;
	if (next_cam > app_available_cameras.length-1) { next_cam = 0; }
	
	console.log("---> birdhouseSwitchCam: "+app_active_cam+"->"+app_available_cameras[next_cam]);

	app_active_cam = app_available_cameras[next_cam];
	birdhousePrint_load(view=app_active_page, camera=app_available_cameras[next_cam], date=app_active_date);
}

/*
* trigger view reload while keeping all the current settings (view, camera, date, ...)
*/
function birdhouseReloadView() {
	console.log("----> birdhouseReloadView: "+app_active_page+"/"+app_active_cam+"/"+app_active_date);
	app_recycle_range = {};
	birdhouse_overlayHide();
	setTextById("headerRight", birdhouseHeaderFunctions() );

	if (app_active_page != "INDEX" && app_active_page != "IMAGE_SETTINGS" && app_active_page != "DEVICES") {
		birdhousePrint_load(view=app_active_page, camera=app_active_cam, date=app_active_date);
		}
	// if (app_active_page == "INDEX" || app_active_page == "TODAY" || app_active_page == "DEVICES") {
	if (app_active_page == "INDEX" || app_active_page == "IMAGE_SETTINGS" || app_active_page == "DEVICES") {
		for (let key in app_camera_source) {

		    console.log("--->"+app_active_cam+"/"+key);
		    console.log(app_camera_source[key]);

			var image = document.getElementById("stream_"+key);
			if (image) {
			    console.log("---> birdhouseReloadView: Restart streaming image: " + key + " / " + app_camera_source[key]);
                image.src = "";
                app_camera_source[key] = app_camera_source[key].replaceAll("//","/");
                app_camera_source[key] = app_camera_source[key].replace(":/","://");
                if (app_unique_stream_url)	{ image.src = app_camera_source[key]+"&"+app_unique_stream_id; }
                else                        { image.src = app_camera_source[key]; }
                }
            else {
			    console.debug("---> birdhouseReloadView: Streaming not active: " + key + " / " + app_camera_source[key]);
                }
			}
		}
	}


