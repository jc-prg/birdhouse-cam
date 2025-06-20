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

loadingImage                = "birdhouse/img/bird.gif";
var app_loading_image       = "birdhouse/img/bird.gif";

var app_available           = { cameras: [], sensors : [], micros: [] };
var app_frame               = { header: "frame1", content: "frame2", info: "frame3", index: "frame4" };
var app_active              = { cam: "cam1", page: "", date: "", mic: "" };
var app_active_history      = [];
var app_active_history_max  = 10;
var app_active_history_pos  = 0;
var app_frame_info          = "frame3";

var app_birdhouse_closed    = false;
var app_last_active_page    = "";
var app_camera_source       = {};
var app_recycle_range       = {};
var app_admin_allowed       = false;
var app_session_id          = "";
var app_session_id_count    = 0;
var app_data                = {};
var app_bird_names          = {};

var app_collect4download    = false;
var app_collect_list        = [];
var app_header_opened       = {};

var app_scripts_loaded      = 0;
var app_first_load          = true;
var app_2nd_load            = true;

var app_pages_content  = ["INDEX", "TODAY", "ARCHIVE", "FAVORITES", "VIDEOS", "TODAY_COMPLETE", "OBJECTS", "WEATHER", "DIARY", "VIDEO_DETAIL"];
var app_pages_lists    = ["TODAY", "ARCHIVE", "FAVORITES", "VIDEOS", "TODAY_COMPLETE"];
var app_pages_settings = ["SETTINGS", "SETTINGS_CAMERAS", "SETTINGS_IMAGE", "SETTINGS_DEVICES", "SETTINGS_INFORMATION", "SETTINGS_STATISTICS", "SETTINGS_SERVER"];
var app_pages_admin    = ["SETTINGS", "SETTINGS_CAMERAS", "SETTINGS_IMAGE", "SETTINGS_DEVICES", "SETTINGS_INFORMATION", "SETTINGS_STATISTICS", "SETTINGS_SERVER", "TODAY_COMPLETE"];
var app_pages_other    = ["LOGIN", "LOGOUT"];
var app_pages_cam_id   = ["INDEX", "TODAY", "ARCHIVE", "TODAY_COMPLETE"];

/*
* additional scripts and style sheet files to be loaded
*/
var birdhouse_js = [
    "config_language.js",
    "config_main.js",
    "config_stage.js",
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
    "birdhouse-views-overlay.js",
    "birdhouse-weather.js",
    "birdhouse-diary.js",
    "birdhouse-navigation.js",
    "video-player-template.js",
    "video-player.js",
];

var birdhouse_css = [
    "style-v2.css",
    "style-v2-dark.css",
    "style-v2-diary.css",
    "style-v2-diary-dark.css",
    "style-v2-streams.css",
    "style-v2-frames.css",
    "style-v2-frames-dark.css",
    "style-v2-navigation.css",
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

/*
* check, if all required JavaScript modules have been loaded
*/
function birdhouse_modules_loaded() {
    if (app_scripts_loaded == birdhouse_js.length)  { return true; }
    else                                            { return false; }
}

//setTimeout(function(){ appApiLogging = "error_log2"; elementVisible("error_log2"); }, 2000);

/*
* load a specific page or view, uses existing parameter or vars app_active.cam and app_active.date
* this function decides depending on the view, whether to load data or just to generate the view
*
* @param (string) page: available: INDEX, TODAY, TODAY_COMPLETE, ARCHIVE, OBJECT, SETTINGS, FAVORITES, VIDEOS, INFO, ...
* @param (string) camera: camera ID (or other param)
* @param (string) date: selected date
* @param (string) label: selected label, e.g., detected object
*/
function birdhousePrint_page(page="INDEX", cam="", date="", label="") {

    var page_history = false;

    // scroll to the top
	window.scrollTo(0,0);

    console.log("==> birdhousePrint_page: " + page + " / " + cam + " / " + date + " / " + label);
    console.log("                   from: " + app_active.page + " / " + app_active.cam + " / " + app_active.date);

    // set app_active values
    if (page == "") { page = app_active.page; }
    if (!app_pages_other.includes(page)) {
        if (page != "")              { app_active.page = page; }
        if (date != "")              { app_active.date = date; }
        if (cam.indexOf("cam") >= 0) { app_active.cam  = cam; }
        }

    // navigate in history views
    if (page.indexOf("PAGE_HISTORY") > -1) {
        var direction = parseInt(page.split("|")[1]);

        console.debug("--> history page: " + page + "|" + direction + "|" + app_active_history_pos);

        page_history = true;
        app_active_history_pos += direction;

        if (app_active_history_pos < 0)                             { app_active_history_pos = 0; }
        if (app_active_history_pos >= app_active_history.length)    { app_active_history_pos = app_active_history.length - 1; }

        app_active.page    = app_active_history[app_active_history_pos].page;
        app_active.cam     = app_active_history[app_active_history_pos].cam;
        app_active.date    = app_active_history[app_active_history_pos].date;
        page = app_active.page;

        if (app_active_history.length > 1) {
            if (app_active_history_pos+1 < app_active_history.length) { elementVisible("moveBack"); elementHidden("moveBack_off"); }
            else                                                      { elementVisible("moveBack_off"); elementHidden("moveBack"); }
            if (app_active_history_pos > 0 )                          { elementVisible("moveForth"); elementHidden("moveForth_off"); }
            else                                                      { elementVisible("moveForth_off"); elementHidden("moveForth"); }
            }

        console.log("--> history page: " + page + "|" + cam + "|" + app_active_history_pos + " ("+app_active_history.length+")");
        }
    else if (app_active_history_pos != 0) {
        var temp_history = [];
        for (var i=app_active_history_pos;i<app_active_history.length;i++) {
            temp_history.push(app_active_history[i]);
            }
        app_active_history = temp_history;
        }

    console.log("                     to: " + app_active.page + " / " + app_active.cam + " / " + app_active.date);

	// clear possible active update processes
    for (let camera in app_data["SETTINGS"]["devices"]["cameras"]) { birdhouseDevices_cameraSettingsLoad(camera, false); }

    // load content pages
    if (app_pages_content.includes(page)) {
        console.log("Load content page: " + page + " / " + cam + " / " + date + " / " + label);
        birdhouse_settings.toggle(true);
        appSettings.hide();
        //app_active.page = page;
        //birdhousePrint_load(view=app_active.page, camera=app_active.cam, date=app_active.date, label=label, page_call=true);
        birdhousePrint_load(view=page, camera=cam, date=date, label=label, page_call=true);
        }

    // load setting pages
    else if (app_pages_settings.includes(page)) {

        console.log("Load settings page: " + page);
        app_active = { page: page, cam: app_active.cam, date: "" };
        if (page != "SETTINGS") { appSettings.create(page); }
        else                    { appSettings.create(); }
        appSettings.clear_content_frames();
        }

    // load other pages such as LOGIN and LOGOUT
    else if (app_pages_other.includes(page)) {
        console.log("Load other page: " + page);
        if (page == "LOGIN") {
            if (cam == "")                  { page = "INDEX"; }
            else                            { page = cam; }
            if (page.indexOf("cam") >= 0)   { app_active.cam = page; }
            birdhouse_loginDialog(cam);
            }
        else if (page == "LOGOUT") {
            if (app_pages_admin.includes(app_active.page)) { app_active.page = "INDEX"; }
            birdhouse_logout();
            }
        }

    // load last page (as page not known)
    else {
        console.warn("birdhousePrint_page: requested page '" + page + "' not found.");
        birdhousePrint_load(page="INDEX", camera="", date="", label="", page_call=false);
        }

    this.compare = function (obj1, obj2) {
        return Object.keys(obj1).every(key => obj1[key] === obj2[key]);
        }

    if (!page_history) {
        var state_copy       = { ...app_active };
        if (app_active_history.length == 0 || !this.compare(state_copy, app_active_history[0])) {
            app_active_history.unshift(state_copy);
            }
        if (app_active_history.length > app_active_history_max) { app_active_history.pop(); }
        app_active_history_pos = 0;
        }
    }

/*
* request loading date for a specific view -> calls birdhousePrint() with returned data, should be called
* using birdhousePrint_page() all the times
*
* @param (string) view: view to be requested; available: INDEX, TODAY, TODAY_COMPLETE, ARCHIVE, OBJECT, FAVORITES, VIDEOS, VIDEO_DETAIL, SETTINGS, SETTINGS_SERVER, ...
* @param (string) camera: camera id of active camera
* @param (string) data: active date, to be combined with view TODAY in format YYYYMMDD
* @param (string) label: selected label, e.g., detected object
*/
function birdhousePrint_load(view="INDEX", camera="", date="", label="", page_call=false) {
    var login_timeout = 3000;

	if (app_first_load || app_2nd_load) {
	    if (app_first_load) { app_first_load = false; }
	    else                { app_2nd_load = false; }

        // if parameters given in the URL try to load pages directly (and login, if settings)
	    if (window.location.href.indexOf("?") > 0 && page_call == false) {
	        params = getUrlParams(window.location.href);

	        if (params["page"] && (app_pages_content.includes(params["page"].toUpperCase()) || app_pages_settings.includes(params["page"].toUpperCase()))) {
	            page = params["page"].toUpperCase();

	            if (params["cam"].indexOf("cam") >= 0)          { camera = params["cam"]; }
	            else if (params["camera"].indexOf("cam") >= 0)  { camera = params["camera"]; }
	            else                                            { camera = app_active.cam; }
	            if (params["date"])                             { date = params["date"]; }

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

	            birdhousePrint_page(page, camera, date);
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
	if (camera.indexOf("cam") >= 0 && date != "") { commands.push(date); commands.push(camera); app_active.cam = camera; }
	else if (camera.indexOf("cam") >= 0)          { commands.push(camera); app_active.cam = camera; }
	else                                          { commands.push(app_active.cam); }
	if (label != "")                              { commands.push(label); }

	console.log("---> birdhousePrint_load: " + view + " / " + camera + " /  " +date + " / "+ JSON.stringify(commands));
	birdhouse_genericApiRequest("GET", commands, birdhousePrint);
	}

/*
* create views with specific data, should only be called by birdhousePrint_load()
*
* @param (dict) data: data returned from API
*/
function birdhousePrint(data) {

	window.scrollTo(0,0);
    overlayImageList = [];

    if (data["DATA"] != {} && data["DATA"]["active"]) {

        var data_active     = data["DATA"]["active"];
        app_active.page     = data_active["active_page"];
        app_active.date     = data_active["active_date"];

        if (app_pages_cam_id.includes(data_active["active_page"])) {
            var camera      = data_active["active_cam"];
            if (camera == "") 	                    { camera = app_active.cam; }
            else if (camera.indexOf("cam") >= 0)    { app_active.cam = camera; }
            }

        birdhouseAudioStream_load(app_data["SETTINGS"]["devices"]["microphones"]);

        if (app_active.page == "INDEX") {
            birdhouseSetMainVars(data);
            birdhouseSetMainStatus(data);
            }
        }

    setTextById("headerRight", birdhouseHeaderFunctions() );
    birdhouse_KillActiveStreams();
	birdhousePrintTitle(data, app_active.page);

    var success = true;
	console.log("---> birdhousePrint: "+app_active.page+" / "+app_active.cam+" / "+app_active.date);

    // load selected view
    if (app_pages_lists.includes(app_active.page))          { birdhouse_LIST(app_active.page, data, app_active.cam); }
    else if (app_pages_settings.includes(app_active.page))  { birdhouse_SETTINGS(app_active.page, data); }
	else if (app_active.page == "INDEX")                    { birdhouse_INDEX(data, app_active.cam); }
	else if (app_active.page == "DIARY")                    { birdhouse_DIARY(data); }
	else if (app_active.page == "VIDEO_DETAIL")	            { birdhouse_VIDEO_DETAIL(data); }
	else if (app_active.page == "OBJECTS")                  { birdhouse_OBJECTS(data); }
	else if (app_active.page == "WEATHER")                  { birdhouse_WEATHER(data); }
	else                                                    { birdhousePrint_page("INDEX"); success = false; }

	if (success == false)   { app_active.page = app_last_active_page; }
	else                    { app_last_active_page = app_active.page; }
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
	                                                            { app_available.cameras.push(key) }}
	    }
	if (data_settings["devices"]["sensors"] != undefined) {
	    for (let key in data_settings["devices"]["sensors"]) {
	        if (data_settings["devices"]["sensors"][key]["active"])
	                                                            { app_available.sensors.push(key) }}
	    }
	if (data_settings["devices"]["microphones"] != undefined) {
	    for (let key in data_settings["devices"]["microphones"]) {
	        if (data_settings["devices"]["microphones"][key]["active"])
	                                                            { app_available.micros.push(key) }}
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

	app_active.mic = app_available.micros[0];

	if (status_view["active_page"] != "" && status_view["active_page"] != undefined && status_view["active_page"] != "status")
	                                                        { app_active.page = status_view["active_page"]; }
	else if (status_view["active_page"] != "status")        { app_active.page = "INDEX"; }

	if (status_view["active_date"] != "" && status_view["active_date"] != undefined)
	                                                        { app_active.date = status_view["active_date"]; }
	else                                                    { app_active.date = ""; }

    if (data["SETTINGS"] && data["SETTINGS"]["localization"] && data["SETTINGS"]["localization"]["language"]) {
        LANG_old = LANG;
        LANG = data["SETTINGS"]["localization"]["language"];
        if (LANG != LANG_old) { app_setting_entries(); }
        }
	}

/*
* create header icons depending on status information (active devices, active download, ...)
*
* @returns (string): html header content
*/
function birdhouseHeaderFunctions() {

    if (app_active.mic != "") {
        var audio_stream    = "";
        var mic_config      = app_data["SETTINGS"]["devices"]["microphones"][app_active.mic];
        if (mic_config) {
	        audio_stream    = "<img id='stream_toggle_header' class='header_icon_wide' src='birdhouse/img/icon_bird_mute.png' onclick='birdhouseAudioStream_toggle(\"\",\"\",\""+mic_config["codec"]+"\");'>";
	        }
	    }
	else {
	    var audio_stream    = "";
	    var mic_config      = {};
	    }

	var html = "";
	var download_info   = "<img class='header_icon' src='birdhouse/img/download-white.png' onclick='archivDownload_requestList();' style='position:relative;right:22px;top:-2px;'>";
	download_info       = "<text class='download_label' id='collect4download_amount2' onclick='archivDownload_requestList();'>0</text>" + download_info;
	var switch_cam      = "<img class='header_icon' src='birdhouse/img/switch-camera-white.png' onclick='birdhouseSwitchCam();' style='position:relative;top:-4px;'>";
	switch_cam         += "<div id='selected_cam' style='display:none;'>"+app_active.cam+"</div>";
	var reload_view     = "<img class='header_icon' src='birdhouse/img/reload-white.png' onclick='birdhouseReloadView();'>";
	var active_cam      = app_active.cam;
	try { active_cam = app_active.cam.toUpperCase(); } catch(err) { console.warn(err.message); console.warn(app_active); }
	active_cam      = "<text style='position:relative;left:22px;top:2px;font-size:7px;'>"+active_cam+"</text>";

    if (app_active.mic && mic_config && mic_config["codec"] && mic_config["codec"] == "mp3")
                                         { var active_mic  = "<text style='position:relative;left:22px;top:2px;font-size:7px;'>"+app_active.mic.toUpperCase()+"</text>"  + audio_stream; }
	else if (app_active.mic && !iOS())   { var active_mic  = "<text style='position:relative;left:22px;top:2px;font-size:7px;'>"+app_active.mic.toUpperCase()+"</text>"  + audio_stream; }
	else                                 { var active_mic = ""; }

	var info_parent     = "&nbsp;";
	var info            = birdhouse_tooltip( info_parent, "<div id='command_dropdown' style='width:90%;margin:auto;'>empty</div>", "info", "" );
	
	html = reload_view;
	if (app_available.cameras != undefined && app_available.cameras.length > 1) { html += active_cam + switch_cam; }
	if (app_available.cameras != undefined && app_available.micros.length > 1)  { html += active_mic; }
	if (app_collect4download) { html = download_info + html; }
/*
	if (app_available.cameras == undefined)	{ html = reload_view + audio_stream + "&nbsp;&nbsp;&nbsp;&nbsp;" + info; }
	else if (app_available.cameras.length > 1) { html = reload_view + audio_stream + active_cam + switch_cam + "&nbsp;&nbsp;&nbsp;" + info; }
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
    var selected_cam = "";
    selected_cam = ("selected_cam");
    if (selected_cam == "") { selected_cam = app_active.cam};

	var current_cam = 0;
	for (i=0;i<app_available.cameras.length;i++) {
		if (app_available.cameras[i] == app_active.cam) { current_cam = i; }
		}
	var next_cam = current_cam + 1;
	if (next_cam > app_available.cameras.length-1) { next_cam = 0; }
	
	console.log("---> birdhouseSwitchCam: "+app_active.cam+"->"+app_available.cameras[next_cam]);

	app_active.cam = app_available.cameras[next_cam];
    setTextById("selected_cam", app_active.cam);
	birdhousePrint_page(page=app_active.page, cam=app_available.cameras[next_cam], date=app_active.date);

	if (app_floating_lowres) {
 	    setTimeout(function(){
            startFloatingLowres(app_active.cam);
            //repositionFloatingLowres();
            }, 1000);
	    }
}

/*
* trigger view reload while keeping all the current settings (page, camera, date, ...)
*/
function birdhouseReloadView() {
	console.log("----> birdhouseReloadView: "+app_active.page+"/"+app_active.cam+"/"+app_active.date);
	app_recycle_range = {};
	birdhouse_overlayHide();
	setTextById("headerRight", birdhouseHeaderFunctions() );

	var no_reload_views = ["INDEX", "SETTINGS_IMAGE", "SETTINGS_DEVICES"];

    console.log("RELOAD -> " + app_active.page);

	if (app_floating_lowres) {
	    startFloatingLowres(app_floating_cam, app_floating_stream);
	    }

	if (!no_reload_views.includes(app_active.page)) {
		birdhousePrint_page(page=app_active.page, cam=app_active.cam, date=app_active.date);
		}

	else if (no_reload_views.includes(app_active.page)) {
		for (let key in app_camera_source) {
		    console.log("---> active:"+app_active.cam + " / key:" + key +" --- " + app_camera_source[key]);

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


