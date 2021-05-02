//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// main functions 
//--------------------------------------
/* INDEX:
*/
//--------------------------------------

var color_code = {
	"star"    : "lime",
	"detect"  : "aqua",
	"recycle" : "red",
	"default" : "white",
	"request" : "yellow"
	}
	
var app_active_cam        = "";
var app_available_cameras = [];
var app_active_page       = "";
var app_active_date       = "";
var app_admin_allowed     = false;

//-----------------------------------------
// load content from API and call print
//-----------------------------------------

function birdhousePrint_load(view="INDEX", camera="", date="") {

	var commands = [view];
	if (camera != "" && date != "")	{ commands.push(camera); commands.push(date); }
	else if (camera != "")			{ commands.push(camera); }

	console.debug("Request "+view+" / "+camera+" / "+date);	
	mboxApp.requestAPI('GET',commands,"",birdhousePrint,"","birdhousePrint_load");
	}
	
//-----------------------------------------
// print views based on active page
//-----------------------------------------

function birdhousePrint(data, active_page="", camera="") {

	console.debug("Request->Print ...");	

	birdhouseSetMainVars(data);
	birdhousePrintTitle(data, active_page, camera);	
	birdhouseCameras = {};
	
	console.log("Request->Print "+app_active_page+" / "+data["DATA"]["active_cam"]+" / "+data["DATA"]["active_date"]);	

	if (data["DATA"]["cameras"] != undefined)	{ birdhouseCameras = data["DATA"]["cameras"]; }
	if (camera == "") 				{ camera = app_active_cam; }

	// check if admin allowed! -> create respective menu
	
	if (app_active_page == "INDEX")		{ birdhouse_INDEX(data, camera); }
	else if (app_active_page == "CAMERAS")	{ birdhouse_CAMERAS(lang("CAMERAS"),     data, camera); }
	else if (app_active_page == "FAVORITS")	{ birdhouse_LIST(lang("FAVORITS"),       data, camera); }
	else if (app_active_page == "ARCHIVE")	{ birdhouse_LIST(lang("ARCHIVE"),        data, camera); }
	else if (app_active_page == "TODAY")		{ birdhouse_LIST(lang("TODAY"),          data, camera); }
	else if (app_active_page == "TODAY_COMPLETE")	{ birdhouse_LIST(lang("TODAY_COMPLETE"), data, camera, false); }
	else if (app_active_page == "VIDEOS")		{ birdhouse_LIST(lang("VIDEOS"),         data, camera); }
	else if (app_active_page == "VIDEO_DETAIL")	{ birdhouse_VIDEO_DETAIL(lang("VIDEOS"), data, camera); }
	else						{ setTextById("frame2",lang("ERROR") + ": "+app_active_page); }
	
	scroll(0,0);
	}
	
	
//-----------------------------------------
// print titel and footer, set vars
//-----------------------------------------

function birdhousePrintTitle(data, active_page="", camera="") {

	var title = document.getElementById("navTitle");
	if (title.innerHTML == "..." && data["DATA"]["title"] != undefined)	{ setNavTitle(data["DATA"]["title"]); setTextById("title",data["DATA"]["title"]); }
	if (data["DATA"]["subtitle"] != undefined)		{ setTextById("frame1", "<center><h2>" + data["DATA"]["subtitle"] + "</h2></center>"); }
	else							{ setTextById("frame1", "<center><h2>" + data["DATA"]["title"] + "</h2></center>"); }
	if (data["DATA"]["links"] != undefined)		{ setTextById("frame3", "<center>" + birdhouse_Links(data["DATA"]["links"]) + "</center>"); }
	if (data["STATUS"]["start_time"] != undefined)	{ setTextById("frame4", "<center><small>" + lang( "STARTTIME") + ": " + data["STATUS"]["start_time"] + "</small></center>"); }
	else							{ setTextById("frame4", ""); }
	}

function birdhouseSetMainVars(data) {

	if (data["DATA"]["cameras"] != undefined)							{ app_available_cameras = Object.keys(data["DATA"]["cameras"]); }
	if (data["DATA"]["active_cam"] != undefined && data["DATA"]["active_cam"] != "")		{ app_active_cam        = data["DATA"]["active_cam"]; }
	else												{ app_active_cam        = app_available_cameras[0]; }
	if (data["DATA"]["active_page"] != "" && data["DATA"]["active_page"] != undefined && data["DATA"]["active_page"] != "status")	{ app_active_page       = data["DATA"]["active_page"]; }
	else if (data["DATA"]["active_page"] != "status")						{ app_active_page = "INDEX"; }
	if (data["DATA"]["active_date"] != "" && data["DATA"]["active_date"] != undefined)		{ app_active_date = data["DATA"]["active_date"]; }
	else 												{ app_active_date = ""; }
	if (data["STATUS"]["admin_allowed"] != undefined)						{ app_admin_allowed = data["STATUS"]["admin_allowed"]; }
	}
	
function birdhouseHeaderFunctions() {
	var html = "";
	var switch_cam  = "<img class='header_icon' src='birdhouse/img/switch-camera-white.png' onclick='birdhouseSwitchCam();'>";
	var reload_view = "<img class='header_icon' src='birdhouse/img/reload-white.png' onclick='birdhouseReloadView();'>";
	html = reload_view + "&nbsp;&nbsp;&nbsp;" + switch_cam + "&nbsp;&nbsp;&nbsp;";
	return html;
	}
	
function birdhouseSwitchCam() {
	var current_cam = 0;
	for (i=0;i<app_available_cameras.length;i++) {
		if (app_available_cameras[i] == app_active_cam) { current_cam = i; }
		}
	var next_cam = current_cam + 1;
	if (next_cam > app_available_cameras.length-1) { next_cam = 0; }
	
	birdhousePrint_load(view=app_active_page, camera=app_available_cameras[next_cam], date=app_active_date);
	}	

function birdhouseReloadView() {
	birdhousePrint_load(view=app_active_page, camera=app_active_cam, date=app_active_date);
	}	


//-----------------------------------------
// views
//-----------------------------------------
	
function birdhouse_INDEX(data, camera) {

	var html          = "";
	var active_camera = camera;
	var cameras       = data["DATA"]["cameras"];
	var admin_allowed = data["STATUS"]["admin_allowed"];
	var stream_server = RESTurl;
	var active_cam    = {};
	var other_cams    = [];
	
	for (let key in cameras) {
		if (key == active_camera) {
			active_cam  = {
				"name"        : key,
				"stream"      : cameras[key]["stream"],
				"description" : key.toUpperCase + ": " + cameras[key]["camera_name"]
				}
			}
		else {
			var other_cam  = {
				"name"        : key,
				"stream"      : cameras[key]["stream"],
				"description" : key.toUpperCase + ": " + cameras[key]["camera_name"]
				}
			other_cams.push(other_cam);
			}
		}
	if (active_cam == {}) { active_cam = other_cams[0]; other_cams.shift(); }
	if (cameras.length == 1 || other_cams.length == 0) {	
		var onclick  = "birdhousePrint_load(view=\"TODAY\", camera=\""+active_camera+"\");";
		html += birdhouse_Camera(main=true, view="cam1", onclick=onclick, camera=active_cam, stream_server=stream_server);
		}
	else {
		var onclick  = "birdhousePrint_load(view=\"INDEX\", camera=\""+other_cams[0]["name"]+"\");";
		html += birdhouse_Camera(main=false, view="cam1cam2", onclick=onclick, camera=other_cams[0], stream_server=stream_server);

		onclick      = "birdhousePrint_load(view=\"TODAY\", camera=\""+active_camera+"\");";
		html += birdhouse_Camera(main=true, view="cam1cam2", onclick=onclick, camera=active_cam, stream_server=stream_server);
		}
		
	setTextById("frame2",html);
	}
	
//-----------------------------------------

function birdhouse_CAMERAS( title, data ) {
	var cameras           = data["DATA"]["entries"];
	var html              = "";
	
	for (let camera in cameras) {
	        info          = cameras[camera];
	        camera_name   = camera.toUpperCase() + ": " + cameras[camera]["name"];
	        camera_stream = birdhouse_Image(camera_name, cameras[camera]);
	        
		html  += birdhouse_OtherGroupHeader( camera, camera_name, true )
		html += "<div id='group_"+camera+"'>";
		
	        html  += "<div class='camera_info'>";
	        if (cameras[camera]["active"])	{ html  += "<div class='camera_info_image'>"+camera_stream+"</div>"; }
	        else					{ html  += "<div class='camera_info_image'>"+lang("CAMERA_INACTIVE")+"</div>"; }
		html  += "<div class='camera_info_text'>";
		html   += "<ul>"
		html   += "<li>Type: "   + info["camera_type"] + "</li>"
		html   += "<li>Active: " + info["active"] + "</li>"
		html   += "<li>Record: " + info["record"] + "</li>"
		html   += "<li>Crop: "   + info["image"]["crop"] + "</li>"
		html   += "<li>Detection (red rectangle): <ul>"
		html     += "<li>Threshold: " + info["similarity"]["threshold"] + "%</li>"
		html     += "<li>Area: "      + info["similarity"]["detection_area"] + "</li>"
		html   += "</ul></li>"
		html   += "<li>Streaming-Server: "+info["video"]["streaming_server"]+"</li>"
		html   += "</ul>"
		html   += "<br/>&nbsp;"
	        html  += "</div></div>";
	        html  += "</div>";
		}
	setTextById("frame2",html);
	}

//-----------------------------------------

function birdhouse_VIDEO_DETAIL( title, data ) {
	var html = "";
	video = data["DATA"]["entries"];

	for (let key in video) {
		var short                     = false;
	        var video_name                = video[key]["date"];
	        var video_stream              = birdhouse_Image(video_name, video[key]);
	        
	        if (video[key]["video_file_short"] != undefined && video[key]["video_file_short"] != "") {
	                short                     = true;
		        var video_short           = {};
		        Object.assign( video_short, video[key] );
		        var short_video_file      = video[key]["video_file_short"];
		        video_short["video_file"] = short_video_file;
		        video_stream_short        = birdhouse_Image("Short", video_short);
		        }
	        
		html += "<div class='camera_info'>";
		html += "<div class='camera_info_image'>";
		html += video_stream;
		if (short) {
			html += video_stream_short;
			}
		html += "</div>";
		html += "<div class='camera_info_text'>";
		html += "<h3>"+video_name+"</h3>";
		html += "&nbsp;<br/>";
		html += lang("CAMERA")     + ": " + video[key]["camera"].toUpperCase() + " - " + video[key]["camera_name"] + "<br/>";
		html += lang("LENGTH")     + ": " + video[key]["length"]      + " s<br/>";
		html += lang("FRAMERATE")  + ": " + video[key]["framerate"]   + " fps<br/>";
		html += lang("FRAMECOUNT") + ": " + video[key]["image_count"] + "<br/>";
		html += lang("IMAGESIZE")  + ": " + video[key]["image_size"]  + "<br/>";
//		html += lang("FILES")  + ": " + video[key]["video_file"]  + "<br/>";
		if (short) {
//			html += lang("FILES")  + ": " + video[key]["video_file_short"]  + "<br/>";
			html += lang("SHORT_VERSION") + ": " + Math.round(video[key]["video_file_short_length"]*10)/10 + " s<br/>";
			}
		html += "&nbsp;<br/>";
		html += lang("EDIT") + ":&nbsp; <button onclick=\"toggleVideoEdit();\" class=\"button-video-edit\">&nbsp;"+lang("SHORTEN_VIDEO")+"&nbsp;</button>&nbsp;<br/>";
		html += "</div>";
		
		var player = "<div id='camera_video_edit_overlay' class='camera_video_edit_overlay' style='display:none'></div>";
		player += "<div id='camera_video_edit' class='camera_video_edit' style='display:none'>";
		player += "<div style='height:46px;width:100%'></div>";
		var trim_command = "createShortVideo();"; 
		
		loadJS(videoplayer_script, "", document.body);
		
		video_values = {};
		video_values["VIDEOID"]    = key;
		video_values["ACTIVE"]     = app_active_cam;
		video_values["LENGTH"]     = video[key]["length"];
		video_values["THUMBNAIL"]  = "";
		video_values["VIDEOFILE"]  = video[key]["directory"] + video[key]["video_file"];
		video_values["JAVASCRIPT"] = trim_command;
		videoplayer  = videoplayer_template;
		for (let key in video_values) {
			videoplayer = videoplayer.replace("<!--"+key+"-->",video_values[key]);
			}
		player += videoplayer;
		player += "</div>";
		setTextById("videoplayer",player);
		}

	setTextById("frame2",html);
	}

//-----------------------------------------

function birdhouse_LIST(title, data, camera, header_open=true) {

	var html              = "";
	var entry_category    = [];

	var entry_count       = data["DATA"]["view_count"];
	var entries           = data["DATA"]["entries"];
	var entries_yesterday = data["DATA"]["entries_yesterday"];
	var entries_delete    = data["DATA"]["entries_delete"];
	var active_date       = data["DATA"]["active_date"];
	var active_page       = app_active_page;
	var groups            = data["DATA"]["groups"];
	var admin             = data["STATUS"]["admin_allowed"];
	
	if (active_page == "VIDEOS")					{ entry_category = [ "video" ]; }
	else if (active_page == "TODAY" && active_date == "")	{ entry_category = [ "today" ]; }
	else if (active_page == "TODAY" && active_date != "")	{ entry_category = [ "backup", active_date ]; }
	
	// today complete, favorits
	if (groups != undefined && groups != {}) {
		for (let group in groups) {
			group_entries = {};
			for (i=0;i<groups[group].length;i++) {
				key                = groups[group][i];
				group_entries[key] = entries[key];
				}		
			html += birdhouse_ImageGroup(group, group_entries, entry_count, entry_category, header_open, admin);
			}
		}
	// today, backup, video
	else {
		entries_available = false;
		if (active_date != undefined && active_date != "")						{ title = active_date; }
	        if (entries != undefined &&  Object.keys(entries).length > 0)				{ html += birdhouse_ImageGroup(title, entries, entry_count, entry_category, header_open, admin); entries_available = true; }
		if (admin) {
		        if (entries_yesterday != undefined && Object.keys(entries_yesterday).length > 0)	{ html += birdhouse_ImageGroup(lang("YESTERDAY"), entries_yesterday, entry_count, entry_category, false, admin); entries_available = true; }
		        if (entries_delete != undefined && Object.keys(entries_delete).length > 0)		{ html += birdhouse_ImageGroup(lang("RECYCLE"), entries_delete, ["recycle"], entry_category, false, admin); entries_available = true; }
		        }
		if (entries_available == false) {
			html += "<center>"+lang("NO_ENTRIES")+"</center>";
			}
		}
	setTextById("frame2", html);
	}
	
//-----------------------------------------
// detail and elements for views
//-----------------------------------------

function birdhouse_Camera(main, view, onclick, camera, stream_server) {
	var html      = "";
	var style_cam = view;
	
	if (main) { var container = 'main'; }
	else      { var container = '2nd'; }

	var stream_link    = stream_server + camera["stream"];
	var livestream     = "<img src='"+stream_link+"' id='stream_"+camera["name"]+"' class='livestream_"+container+"'/>";
	var command_record = "mboxApp.requestAPI(\"POST\",[\"start\",\"recording\",\""+camera["name"]+"\"],\"\",\"\",\"\",\"birdhouse_INDEX\");"; //requestAPI(\"/start/recording/cam2\");
	var command_stop   = "mboxApp.requestAPI(\"POST\",[\"stop\", \"recording\",\""+camera["name"]+"\"],\"\",\"\",\"\",\"birdhouse_INDEX\");";; //requestAPI(\"/stop/recording/cam2\");
	
	html     += "<center><div class='livestream_"+container+"_container "+view+"'>";
	html     += "  <a onclick='"+onclick+"' style='cursor:pointer;'>" + livestream + "</a>";
	if (main) {
		html     += "  <div class='livestream_record "+view+"'>";
		html     += "     <button onclick='"+command_record+"' class='button-video-record'>Record ("+camera["name"]+")</button> &nbsp;";
		html     += "     <button onclick='"+command_stop+"' class='button-video-record'>Stop ("+camera["name"]+")</button>";
//		html     += "     <br/>&nbsp;<br/>";
//		html     += "     <br/>&nbsp;";
		}
	html     += "</div></center>";

	return html;
	}

//-----------------------------------------

function birdhouse_ImageGroup(title, entries, entry_count, entry_category, header_open, admin=false) {

	var count     = {};
	var html      = "";
	var image_ids = "";
	var display   = "";
	var group_id  = title;
	
	if (admin) {
		for (i=0;i<entry_count.length;i++) 	{ count[entry_count[i]] = 0; }
		if (count["all"] != undefined) 	{ count["all"] = Object.keys(entries).length; }
		
		for (let key in entries) {	
			if (count["star"] != undefined    && parseInt(entries[key]["favorit"]) == 1)		{ count["star"]    += 1; }
			if (count["recycle"] != undefined && parseInt(entries[key]["to_be_deleted"]) == 1)	{ count["recycle"] += 1; }
			if (count["detect"] != undefined && parseInt(entries[key]["detect"]) == 1)		{ count["detect"]  += 1; }
			if (header_open == false && entries[key]["lowres"] != undefined)			{ image_ids += " " + entries[key]["lowres"]; }
			}
		}
	if (header_open == false) {
		display = "style='display:none;'";
		}
	
	html += birdhouse_ImageGroupHeader( group_id, title, header_open, count );
	html += "<div id='group_ids_"+group_id+"' style='display:none;'>" + image_ids + "</div>";
	html += "<div id='group_"+group_id+"' "+display+">";
	
	if (title == lang("RECYCLE")) {
		var command  = "";
		if (entry_category.length == 1)	{ command = ",#"+entry_category[0]+"#"; }
		if (entry_category.length == 2)	{ command = ",#"+entry_category[0]+"#,#"+entry_category[1]+"#"; }
		if (command != "") {
			var del_command = "mboxApp.requestAPI(#POST#,[#remove#"+command+"],##,birdhouse_AnswerDelete,##,#birdhouse_ImageGroup#);"; 
			var onclick     = "appMsg.confirm(\""+lang("DELETE_SURE")+"\",\""+del_command+"\");";
			html    += "<div id='group_intro_recycle' class='separator' style='display: block;'><center><br/>";
			html    += "<a onclick='"+onclick+"' style='cursor:pointer;'>" + lang("RECYCLE_DELETE") + "</a>";
			html    += "<br/>&nbsp;</center></div>";
			}
		}
	//html += "<div class='separator'>&nbsp;</div>";

	entry_keys = Object.keys(entries).sort().reverse();
	for (var i=0;i<entry_keys.length;i++) {
		key   = entry_keys[i];
		html += birdhouse_Image(key, entries[key], header_open, admin)
		}
		
	html += "</div>";
	return html;
	}
	
//-----------------------------------------

function birdhouse_OtherGroupHeader( key, title, header_open ) {
	var status = "−";
	if (header_open == false) { status = "+"; }
	var html   = "";
	html += "<div id='group_header_"+key+"' class='separator_group' onclick='showHideGroup(\""+key+"\")'>";
	html += "<text id='group_link_"+key+"' style='cursor:pointer;'>("+status+")</text> ";
	html += title;
	html += "</div>";
	return html;
	}

//-----------------------------------------

function birdhouse_ImageGroupHeader( key, title, header_open, count={} ) {
	var status = "−";
	if (header_open == false) { status = "+"; }
	var html   = "";
	html += "<div id='group_header_"+key+"' class='separator_group' onclick='showHideGroup(\""+key+"\")'>";
	html += "<text id='group_link_"+key+"' style='cursor:pointer;'>("+status+")</text> ";
	html += title + "<font color='gray'> &nbsp; &nbsp; ";
	
	info       = "";
	info_count = 1;
	if (count["all"] != undefined) { 
		if (count["all"] > 0) { color = color_code["default"]; } else { color = "gray"; }
		info += "all: <font color='"+color+"'>"   + count["all"].toString().padStart(3,"0")     + "</font>"; 		
		if (info_count < Object.keys(count).length) { info += " | "; } 
		info_count += 1;
		}
	if (count["star"] != undefined) {
		if (count["star"] > 0) { color = color_code["star"]; } else { color = "gray"; }
		info += "star: <font color='"+color+"'>"   + count["star"].toString().padStart(3,"0")    + "</font>";
		if (info_count < Object.keys(count).length) { info += " | "; } 
		info_count += 1;
		}
	if (count["detect"] != undefined) {
		if (count["detect"] > 0) { color = color_code["detect"]; } else { color = "gray"; }
		info += "detect: <font color='"+color+"'>" + count["detect"].toString().padStart(3,"0")  + "</font>";
		if (info_count < Object.keys(count).length) { info += " | "; } 
		info_count += 1;
		}
	if (count["recycle"]  != undefined) { 
		if (count["recycle"] > 0) { color = color_code["recycle"]; } else { color = "gray"; }
		info += "recycle: <font color='"+color+"'>" + count["recycle"].toString().padStart(3,"0") + "</font>"; 
		}
	if (info != "") { html += "[" + info + "]"; }	

	html += "</font></div>";
	return html;
	}

//-----------------------------------------

function birdhouse_ImageURL(URL) {
	URL = URL.replace(/\/\//g,"/");
	URL = URL.replace("http:/","http://");
	URL = URL.replace("https:/","https://");
	return URL;
	}

//-----------------------------------------

function birdhouse_Image(title, entry, header_open=true, admin=false) {
	var html        = "";
	var play_button = "";
	var dont_load   = "";
	var edit        = false;
	var category    = "";
	
	if (entry["type"] == "image") {	
		var lowres      = birdhouse_ImageURL(RESTurl + entry["directory"] + entry["lowres"]);
		var hires       = birdhouse_ImageURL(RESTurl + entry["directory"] + entry["hires"]);
		var description = entry["time"] + " (" + entry["similarity"] + "%)";
		var onclick     = "imageOverlay(\""+hires+"\",\""+description+"\");";
		description     = description.replace(/\[br\/\]/g,"<br/>");
		edit            = true;
		}
	else if (entry["type"] == "directory") {
		var lowres      = birdhouse_ImageURL(RESTurl + entry["directory"] + entry["lowres"]);
		var onclick     = "birdhousePrint_load(view=\"TODAY\", camera = \""+entry["camera"]+"\", date=\""+entry["datestamp"]+"\");";
		var description = "<b>" + entry["date"] + "</b><br/>" + entry["count_cam"] + "/" + entry["count"] + " (" + entry["dir_size"] + " MB)";
		}		
	else if (entry["type"] == "addon") {
		var lowres      = birdhouse_ImageURL(RESTurl + entry["lowres"]);
		var onclick     = "birdhousePrint_load(view=\"INDEX\", camera = \""+entry["camera"]+"\");";
		var description = lang("LIVESTREAM");
		}		
	else if (entry["type"] == "camera") {
		var lowres      = birdhouse_ImageURL(RESTurl + entry["lowres"]);
		var hires       = birdhouse_ImageURL(RESTurl + entry["hires"]);
		var onclick     = "imageOverlay(\""+hires+"\",\""+description+"\");";
		var description = title;
		}		
	else if (entry["type"] == "video") {
		var lowres      = birdhouse_ImageURL(RESTurl + "videos/" + entry["thumbnail"]);
		var hires       = birdhouse_ImageURL(birdhouseCameras[entry["camera"]]["streaming_server"] + entry["video_file"]);
		var description = entry["date"] + "[br/]" + entry["camera"].toUpperCase() + ": " + entry["camera_name"];
		var onclick     = "videoOverlay(\""+hires+"\",\""+description+"\");";
		var play_button = "<img src=\"birdhouse/img/play.png\" class=\"play_button\" onclick='"+onclick+"' />";
		entry["lowres"] = entry["thumbnail"];
		description     = description.replace(/\[br\/\]/g,"<br/>");
		if (admin) {
			var cmd_edit = "birdhousePrint_load(view=\"VIDEO_DETAIL\", camera=\""+app_active_cam+"\", date=\""+entry["date_start"]+"\");"
			description += "<br/><a onclick='"+cmd_edit+"' style='cursor:pointer;'>"+lang("EDIT")+"</a>";
			}
		edit            = true;
		}
	if (header_open == false) {
		dont_load       = "data-";
		}
	
	var style       = "";
	var star        = "";
	var recycle     = "";
	
	if (entry["detect"] == 1)						{ style = "border: 1px solid "+color_code["detect"]+";"; }
	if (entry["to_be_deleted"] == 1 || entry["to_be_deleted"] == "1")	{ style = "border: 1px solid "+color_code["recycle"]+";"; }
	if (entry["favorit"] == 1 || entry["favorit"] == "1")		{ style = "border: 1px solid "+color_code["star"]+";"; }

	if (admin && edit) {
		var img_id      = entry["category"];
		var img_name    = entry["lowres"];
		var img_star    = entry["favorit"];
		var img_recycle = entry["to_be_deleted"]; 
		if (img_star == undefined)       { img_star = 0; }
		if (img_recycle == undefined)    { img_recycle = 0; }
		if (parseInt(img_star) == 0)     { img_star_r = 1; }    else { img_star_r = 0; }
		if (parseInt(img_recycle) == 0)  { img_recycle_r = 1; } else { img_recycle_r = 0; }
		var img_dir     = "birdhouse/img/";

		star        = "<div id='s_"+img_id+"_value' style='display:none;'>"+img_star_r+"</div>   <img class='star_img'    id='s_"+img_id+"' src='"+img_dir+"star"+img_star+".png'       onclick='setFavorit(\""+img_id+"\",document.getElementById(\"s_"+img_id+"_value\").innerHTML,\""+img_name+"\");'/>";
		recycle     = "<div id='d_"+img_id+"_value' style='display:none;'>"+img_recycle_r+"</div><img class='recycle_img' id='d_"+img_id+"' src='"+img_dir+"recycle"+img_recycle+".png' onclick='setRecycle(\""+img_id+"\",document.getElementById(\"d_"+img_id+"_value\").innerHTML,\""+img_name+"\");'/>";
		}
		
	html += "<div class='image_container'>";
	html += "  <div class='star'>"+star+"</div>";
	html += "  <div class='recycle'>"+recycle+"</div>";
	html += "  <div class='thumbnail_container'>"
	html += "    <a onclick='"+onclick+"' style='cursor:pointer;'><img "+dont_load+"src='"+lowres+"' id='"+entry["lowres"]+"' class='thumbnail' style='"+style+"'/></a>";
	html +=      play_button;
	html += "    <br/><center><small>"+description+"</small></center>";
	html += "  </div>";
	html += "</div>";
	
	return html;
	}


//-----------------------------------------

function birdhouse_Links(link_list) {
	var html = "";
	var keys = Object.keys(link_list);
	for (var i=0;i<keys.length;i++) { if (keys[i] != "active_cam") {
		var key     = keys[i];
		var onclick = "birdhousePrint_load(view=\""+link_list[key]["link"]+"\", camera=\""+app_active_cam+"\");";
		html += "<a style='cursor:pointer;' onclick='"+onclick+"'>"+lang(link_list[key]["link"])+"</a> ";
		if (i+1 < keys.length) { html += " | "; }
		} }
	return html;
	}


//-----------------------------------------
// load addition javascript
//-----------------------------------------

var loadJS = function(url, implementationCode, location){
    //url is URL of external file, implementationCode is the code
    //to be called from the file, location is the location to 
    //insert the <script> element

    //var scriptTag = document.createElement('script');
    var scriptTag = document.getElementById('videoplayer-script');
    scriptTag.src = url;

    scriptTag.onload = implementationCode;
    scriptTag.onreadystatechange = implementationCode;

    location.appendChild(scriptTag);
};

var yourCodeToBeCalled = function(){
//your code goes here
}

//-----------------------------------------
// EOF
	

