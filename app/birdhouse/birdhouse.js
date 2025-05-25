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

loadingImage              = "birdhouse/img/bird.gif";
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
var app_session_id        = "";
var app_session_id_count  = 0;
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

var app_pages_content  = ["INDEX", "TODAY", "ARCHIVE", "FAVORITES", "VIDEOS", "TODAY_COMPLETE", "OBJECTS", "WEATHER"];
var app_pages_lists    = ["TODAY", "ARCHIVE", "FAVORITES", "VIDEOS", "TODAY_COMPLETE"];
var app_pages_settings = ["SETTINGS", "SETTINGS_CAMERAS", "SETTINGS_IMAGE", "SETTINGS_DEVICES", "SETTINGS_INFORMATION", "SETTINGS_STATISTICS", "SETTINGS_SERVER"];
var app_pages_admin    = ["SETTINGS", "SETTINGS_CAMERAS", "SETTINGS_IMAGE", "SETTINGS_DEVICES", "SETTINGS_INFORMATION", "SETTINGS_STATISTICS", "SETTINGS_SERVER", "TODAY_COMPLETE"];
var app_pages_other    = ["LOGIN", "LOGOUT"];

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
    "birdhouse-statistics.js",
    "birdhouse-status.js",
    "birdhouse-views.js",
    "birdhouse-views-index.js",
    "birdhouse-weather.js",
    "video-player-template.js",
    "config_language.js",
    "config_main.js",
    "config_stage.js"
];

var birdhouse_css = [
    "style-v2.css",
    "style-v2-dark.css",
    "style-v2-streams.css",
    "style-v2-frames.css",
    "style-v2-frames-dark.css",
    "style-v2-streams.css",
    "style-v2-streams-dark.css",
    "style-v2-labels.css",
    "style-v2-labels-dark.css",
    "style-v2-slider.css",
    "style-v2-slider-dark.css",
    "style-v2-gallery.css",
    "style-v2-gallery-overlay.css",
    "style-v2-settings.css",
    "style-v2-settings-dark.css",
    "style-v2-settings-processing.css",
    "style-v2-settings-statistics.css",
    "style-v2-other.css",
    "style-v2-other-dark.css",
    "style-v2-video-editing.css",
    "style-v2-ipad.css",
    "style-v2-iphone.css",
    "video-player.css"
];

function birdhouse_modules_loaded() {
    if (app_scripts_loaded == birdhouse_js.length)  { return true; }
    else                                            { return false; }
}


/*
* print a specific page, uses existing vars app_active_cam and app_active_date
*
* @param (string) page: available: INDEX, TODAY, TODAY_COMPLETE, ARCHIVE, OBJECT, SETTINGS, FAVORITES, VIDEOS, INFO, ...
*/
function birdhousePrint_page(page="INDEX", param="") {
	window.scrollTo(0,0);

    if (app_pages_content.includes(page)) {
        console.log("Load content page: " + page);
        birdhouse_settings.toggle(true);
        appSettings.hide();
        birdhousePrint_load(page, app_active_cam, app_active_date, lang(page));
        }
    else if (app_pages_settings.includes(page)) {
        console.log("Load settings page: " + page);
        if (page != "SETTINGS") { appSettings.create(page); }
        else                    { appSettings.create(); }
        app_active_page = page;
        appSettings.clear_content_frames();
        }
    else if (app_pages_other.includes(page)) {
        console.log("Load other page: " + page);
        if (page == "LOGIN") {
            birdhouse_loginDialog(param);
            }
        else if (page == "LOGOUT") {
            birdhouse_logout();
            if (app_pages_admin.includes(app_active_page)) { birdhousePrint_page("INDEX"); }
            }
        }
    else {
        console.warn("birdhousePrint_page: requested page '" + page + "' not found.");
        birdhousePrint_page(page="INDEX");
        }
    }

/*
* request loading of a specific view -> calls birdhousePrint() with returned data
*
* @param (string) view: view to be requested; available: INDEX, TODAY, TODAY_COMPLETE, ARCHIVE, OBJECT, FAVORITES, VIDEOS, VIDEO_DETAIL, SETTINGS, SETTINGS_SERVER, ...
* @param (string) camera: camera id of active camera
* @param (string) data: active date, to be combined with view TODAY in format YYYYMMDD
* @param (string) label: active label, will simulate a click on a object/bird label when loaded the complete view
*/
function birdhousePrint_load(view="INDEX", camera="", date="", label="") {
    var login_timeout = 3000;

	if (app_first_load || app_2nd_load) {
	    if (app_first_load) { app_first_load = false; }
	    else                { app_2nd_load = false; }

        // if parameters given in the URL try to load pages directly (and login, if settings)
	    if (window.location.href.indexOf("?") > 0) {
	        params = getUrlParams(window.location.href);
	        if (params["page"] && (app_pages_lists.includes(params["page"].toUpperCase()) || app_pages_settings.includes(params["page"].toUpperCase()))) {
	            page = params["page"].toUpperCase();

	            if (app_pages_admin.includes(page) && params["session_id"] == undefined && params["pwd"] == undefined) {
                    setTimeout(function() {
                        birdhousePrint_page("LOGIN", page);
                        }, login_timeout);
                    birdhousePrint_page("INDEX");
                    history.pushState({page: 1}, view, "/");
                    return;
	                }
	            else if (app_pages_admin.includes(page) && params["pwd"] != undefined) {
                    setTimeout(function() {
                        appMsg.alert(lang("VERIFY_PASSWORD"));
                        birdhouse_loginCheck(params["pwd"], params["page"]);
                        }, login_timeout);
                    birdhousePrint_page("INDEX");
                    history.pushState({page: 1}, view, "/");
	                return;
	                }

	            birdhousePrint_page(page);
                history.pushState({page: 1}, view, "/");
                console.log("Load page directly: " + page);
                return;
	            }
	        }

        // if initial start load login and settings
        var initial = app_data["STATUS"]["server"]["initial_setup"];
        if (initial) {
            setTimeout(function() {
                birdhousePrint_page("LOGIN", "SETTINGS_SERVER");
                }, login_timeout);
            birdhousePrint_page("INDEX");
            return;
            }

        birdhouse_loadChartJS();
	    birdhouse_birdNamesRequest();
	    }
	if (view == "SETTINGS") { birdhousePrint_page(view); return; }

	var commands = [view];
	if (camera != "" && date != "")	{ commands.push(date); commands.push(camera); app_active_cam = camera; }
	else if (camera != "")          { commands.push(camera); app_active_cam = camera; }
	else                            { commands.push(app_active_cam); }
	//if (label != "")                { commands.push(label); }
	
	console.log("---> birdhousePrint_Load: " + view + " / " + camera + " /  " +date + " / "+ JSON.stringify(commands));
	birdhouse_genericApiRequest("GET", commands, birdhousePrint);
	}

/*
* coordinate complete view creation (depending data returned to an API request)
*
* @param (dict) data: data returned from API
*/
function birdhousePrint(data) {

	window.scrollTo(0,0);
    overlayImageList = [];

	var data_active     = data["DATA"]["active"];
	var date            = data_active["active_date"];
	var camera          = data_active["active_cam"];
	if (camera == "") 	{ camera = app_active_cam; }
	else			    { app_active_cam = camera; }

    for (let camera in app_data["SETTINGS"]["devices"]["cameras"]) {
        birdhouseDevices_cameraSettingsLoad(camera, false);
    }
	birdhouseAudioStream_load(app_data["SETTINGS"]["devices"]["microphones"]);

    birdhouse_KillActiveStreams();
    birdhouseSetMainVars(data);
	birdhouseSetMainStatus(data);
	birdhousePrintTitle(data, app_active_page);

    var success = true;
	console.log("---> birdhousePrint: "+app_active_page+" / "+camera+" / "+date);

    if (app_pages_lists.includes(app_active_page))          { birdhouse_LIST(app_active_page, data, camera); }
    else if (app_pages_settings.includes(app_active_page))  { birdhouse_SETTINGS(app_active_page, data); }
	else if (app_active_page == "INDEX")                    { birdhouse_INDEX(data, camera); }
	else if (app_active_page == "VIDEO_DETAIL")	            { birdhouse_VIDEO_DETAIL(data); }
	else if (app_active_page == "OBJECTS")                  { birdhouse_OBJECTS(data); }
	else if (app_active_page == "WEATHER")                  { birdhouse_WEATHER(data); }
	else                                                    { birdhousePrint_page("INDEX"); success = false; }

	if (success == false)   { app_active_page = app_last_active_page; }
	else                    { app_last_active_page = app_active_page; }
	}

/*
* set title in the header and prepare footer for server data to be loaded
*
* @param (dict) data: data returned from API
* @param (string) active_page: active page
*/
function birdhousePrintTitle(data, active_page="") {

    if (!data["DATA"]["view"]) { return; }

	var title         = document.getElementById("navTitle");
	var data_view     = data["DATA"]["view"];
	var data_settings = data["SETTINGS"];

	if (title.innerHTML == "..." && data_settings["title"] != undefined)
	                                             { setNavTitle(data_settings["title"]); setTextById("title",data_settings["title"]); }

	if (data_view["subtitle"] != undefined)      { birdhouse_frameHeader(lang(data_view["subtitle"])); }
	else if (data_view["title"] != undefined)    { birdhouse_frameHeader(data_view["title"]); }

	if (data_view["links"] != undefined)         { birdhouse_frameFooter(birdhouse_Links(data_view["links"])); }

	setTextById("frame5", "<center><small><div id='server_start_time'></div></small></center>");
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

    var data_settings = data["SETTINGS"];
    if (!data["SETTINGS"]) { data_settings = app_data["SETTINGS"]; }

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

    if (data["STATUS"]["view"])                     { var status_view  = data["STATUS"]["view"]; }
    else if (data["DATA"]["active"])                { var status_view  = data["DATA"]["active"]; }
    else                                            { return; }

	app_active_mic = app_available_micros[0];

	if (status_view["active_page"] != "" && status_view["active_page"] != undefined && status_view["active_page"] != "status")
	                                                        { app_active_page = status_view["active_page"]; }
	else if (status_view["active_page"] != "status")        { app_active_page = "INDEX"; }

	if (status_view["active_date"] != "" && status_view["active_date"] != undefined)
	                                                        { app_active_date = status_view["active_date"]; }
	else                                                    { app_active_date = ""; }

    if (data["SETTINGS"] && data["SETTINGS"]["localization"]["language"]) { LANG = data["SETTINGS"]["localization"]["language"]; }
	}

/*
* create header icons depending on status information (active devices, active download, ...)
*
* @returns (string): html header content
*/
function birdhouseHeaderFunctions() {

    if (app_active_mic != "") {
        var mic_config      = app_data["SETTINGS"]["devices"]["microphones"][app_active_mic];
	    var audio_stream    = "<img id='stream_toggle_header' class='header_icon_wide' src='birdhouse/img/icon_bird_mute.png' onclick='birdhouseAudioStream_toggle(\"\",\"\",\""+mic_config["codec"]+"\");'>";
	    }
	else {
	    var audio_stream    = "";
	    var mic_config      = {};
	    }

	var html = "";
	var download_info   = "<img class='header_icon' src='birdhouse/img/download-white.png' onclick='archivDownload_requestList();' style='position:relative;right:22px;top:-2px;'>";
	download_info       = "<text class='download_label' id='collect4download_amount2' onclick='archivDownload_requestList();'>0</text>" + download_info;
	var switch_cam      = "<img class='header_icon' src='birdhouse/img/switch-camera-white.png' onclick='birdhouseSwitchCam();' style='position:relative;top:-4px;'>";
	var reload_view     = "<img class='header_icon' src='birdhouse/img/reload-white.png' onclick='birdhouseReloadView();'>";
	var active_cam      = "<text style='position:relative;left:22px;top:2px;font-size:7px;'>"+app_active_cam.toUpperCase()+"</text>";

    if (app_active_mic && mic_config && mic_config["codec"] && mic_config["codec"] == "mp3")
                                         { var active_mic  = "<text style='position:relative;left:22px;top:2px;font-size:7px;'>"+app_active_mic.toUpperCase()+"</text>"  + audio_stream; }
	else if (app_active_mic && !iOS())   { var active_mic  = "<text style='position:relative;left:22px;top:2px;font-size:7px;'>"+app_active_mic.toUpperCase()+"</text>"  + audio_stream; }
	else                                 { var active_mic = ""; }

	var info_parent     = "&nbsp;";
	var info            = birdhouse_tooltip( info_parent, "<div id='command_dropdown' style='width:90%;margin:auto;'>empty</div>", "info", "" );
	
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

	var no_reload_views = ["INDEX", "IMAGE", "DEVICES", "CAMERAS", "SETTINGS", "SERVER", "INFORMATION"];

    console.warn("RELOAD -> " + app_active_page);

	//if (app_active_page != "INDEX" && app_active_page != "IMAGE" && app_active_page != "DEVICES" && app_active_page != "CAMERAS") {
	if (!no_reload_views.includes(app_active_page)) {
		birdhousePrint_load(view=app_active_page, camera=app_active_cam, date=app_active_date);
		}
	// if (app_active_page == "INDEX" || app_active_page == "TODAY" || app_active_page == "DEVICES") {
	//if (app_active_page == "INDEX" || app_active_page == "IMAGE" || app_active_page == "DEVICES" || app_active_page == "CAMERAS") {

	if (no_reload_views.includes(app_active_page)) {
		for (let key in app_camera_source) {
		    console.log("---> active:"+app_active_cam + " / key:" + key +" --- " + app_camera_source[key]);

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


