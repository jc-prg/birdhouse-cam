//--------------------------------------
// jc://app-framework/, (c) Christoph Kloth
//--------------------------------------
// main functions to load the app
//--------------------------------------
/* INDEX:
*/
//--------------------------------------

var color_code = {
	"star"    : "lime",
	"detect"  : "aqua",
	"recycle" : "red",
	"default" : "white"
	}

//-----------------------------------------
// load content from API and call print
//-----------------------------------------

function birdhousePrint_load(view="INDEX", camera="", date="") {

	var commands = [view];
	if (camera != "" && date != "")	{ commands.push(camera); commands.push(date); }
	else if (camera != "")			{ commands.push(camera); }
	
	console.log("birdhousePrint_load();");
	console.log(commands);

	mboxApp.requestAPI('GET',commands,"",birdhousePrint,"","appPrintStatus_load");
	}
	
//-----------------------------------------
	// print titel and footer
//-----------------------------------------

function birdhousePrintTitle(data, active_page="", camera="") {

	if (data["DATA"]["title"] != undefined)	{ setNavTitle(data["DATA"]["title"]); setTextById("title",data["DATA"]["title"]); }
	else						{ setNavTitle("<No Name>"); }
	if (data["DATA"]["subtitle"] != undefined)	{ setTextById("frame1", "<center><h2>" + data["DATA"]["subtitle"] + "</h2></center>"); }
	else						{ setTextById("frame1", "<center><h2>" + data["DATA"]["title"] + "</h2></center>"); }
	if (data["DATA"]["links"] != undefined)	{ setTextById("frame3", "<center>" + birdhouse_Links(data["DATA"]["links"]) + "</center>"); }
	if (data["STATUS"]["start_time"] != undefined){ setTextById("frame4", "<center><small>" + lang( "STARTTIME") + ": " + data["STATUS"]["start_time"] + "</small></center>"); }
	else						{ setTextById("frame4", ""); }
	}

//-----------------------------------------
// handle status updates based on active page
//-----------------------------------------

function birdhousePrint(data, active_page="", camera="") {

	birdhousePrintTitle(data, active_page, camera);	
	birdhouseCameras = {};
	if (data["DATA"]["cameras"] != undefined) { birdhouseCameras = data["DATA"]["cameras"]; }
	if (data["DATA"]["active_camera"] != undefined) { app_active_cam = data["DATA"]["active_camera"]; }

	if (active_page == "" && data["DATA"]["active_page"] != undefined) {
		active_page = data["DATA"]["active_page"];
		}
		
	// check if admin allowed! -> create respective menu
	
	if (active_page == "INDEX")			{ birdhouse_INDEX(data, camera); }
	else if (active_page == "CAMERAS")		{ birdhouse_CAMERAS(lang("CAMERAS"),     data, camera); }
	else if (active_page == "FAVORITS")		{ birdhouse_LIST(lang("FAVORITS"),       data, camera); }
	else if (active_page == "VIDEOS")		{ birdhouse_LIST(lang("VIDEOS"),         data, camera); }
	else if (active_page == "ARCHIVE")		{ birdhouse_LIST(lang("ARCHIVE"),        data, camera); }
	else if (active_page == "TODAY")		{ birdhouse_LIST(lang("TODAY"),          data, camera); }
	else if (active_page == "TODAY_COMPLETE")	{ birdhouse_LIST(lang("TODAY_COMPLETE"), data, camera, false); }
	else						{ setTextById("frame2",lang("ERROR") + ": "+active_page); }
	
	scroll(0,0);
	}
	
	
//-----------------------------------------
	
function birdhouse_INDEX(data, camera) {

	if (data["DATA"]["active_cam"] == undefined || data["DATA"]["active_cam"] == "")	{ active_camera = camera; }
	else 											{ active_camera = data["DATA"]["active_cam"]; }
        
	var html        = "";
	var cameras     = Object.keys(data["DATA"]["cameras"]);
	var stream_link = RESTurl_noport + ":" + data["DATA"]["cameras"][active_camera]["server_port"];
	stream_link    += data["DATA"]["cameras"][active_camera]["stream"];
	var livestream  = "<img src='"+stream_link+"' id='stream_"+active_camera+"' class='livestream_main'/>";
	
	var onclick        = "birdhousePrint_load(view=\"TODAY\", camera=\""+active_camera+"\");";
	var command_record = "mboxApp.requestAPI(\"POST\",[\"start\",\"recording\",\""+active_camera+"\"],\"\",\"\",\"\",\"birdhouse_INDEX\");"; //requestAPI(\"/start/recording/cam2\");
	var command_stop   = "mboxApp.requestAPI(\"POST\",[\"stop\", \"recording\",\""+active_camera+"\"],\"\",\"\",\"\",\"birdhouse_INDEX\");";; //requestAPI(\"/stop/recording/cam2\");
	
	
	
	if (cameras.length == 1) {
		style_cam = "cam1";
		html     += "<center><div class='livestream_main_container "+style_cam+"'>";
		html     += "  <a onclick='"+onclick+"' style='cursor:pointer;'>" + livestream + "</a>";
		html     += "  <div class='livestream_record cam1'>";
		html     += "     <button onclick='"+command_record+"' class='button-video-record'>Record ("+active_camera+")</button> &nbsp;";
		html     += "     <button onclick='"+command_stop+"' class='button-video-record'>Stop ("+active_camera+")</button>";
		html     += "     <br/>&nbsp;<br/>";
		html     += "     <br/>&nbsp;";
		html     += "</div></center>";
		}
	else {
		// version with 2 cameras is missing
		html     = livestream;
		}
	
/*	
<div class='livestream_main_container cam1'>
  <a href='list_short.html?cam2'><img src="/stream.mjpg?cam2" class='livestream_main'></a>  
  <div class='livestream_record cam1'><br/>CAM2: <button onclick='requestAPI("/start/recording/cam2");'>Record</button> &nbsp;<button onclick='requestAPI("/stop/recording/cam2");'>Stop</button></div>
  <div class='livestream_links cam1'><hr/><a href='/list_star.html?cam2'>Favoriten</a> / <a href='/list_short.html?cam2'>Heute</a> / <a href='/list_backup.html?cam2'>Archiv</a> / <a href='/cameras.html?cam2'>Kameras</a><hr/></div>
  <div class='livestream_startinfo cam1' onclick="javascript:window.location.reload();">Server Start: 25.04.2021 22:40:54</div>
</div>
*/
		
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
		
/*
<center><button onclick='requestAPI("/start/recording/cam2");'>Record</button> &nbsp;<button onclick='requestAPI("/stop/recording/cam2");'>Stop</button></center>
*/
	setTextById("frame2",html);
	}
	
function birdhouse_VIDEODETAIL() {
/*
<div class='camera_info'>
  <div class='camera_info_image'>
	<div class='image_container'>
	<div class='star'></div><div class='trash'></div>
	<div class='thumbnail_container'>
	<a onclick='javascript:videoOverlay("http://192.168.1.20:8008/video_cam2_20210427_215943.mp4","<b>Vollst&auml;ndiges Video</b>");' style='cursor:pointer;'><img src='/videos/video_cam2_20210427_215943_thumb.jpeg' id='video_cam2_20210427_215943_thumb.jpeg' class='thumbnail' style='border:1px solid white;'/></a><br/><img src="/html/play.png" class="play_button" onclick='javascript:videoOverlay("http://192.168.1.20:8008/video_cam2_20210427_215943.mp4","<b>Vollst&auml;ndiges Video</b>");'/>
	<small><b>Vollst&auml;ndiges Video</b></small>
	</div>
  </div>
</div>
<div class='camera_info_text'>
  <b>27.04.2021 21:59:43</b><br/>&nbsp;<br/>
  Kamera: CAM2 - Außen<br/>L&auml;nge: 8.0 s<br/>
  Framerate: 44.4 fps<br/>Bildgr&ouml;&szlig;e: [480, 480]<br/>
  Kurzversion: nicht vorhanden <br/>&nbsp;<br/>
  Bearbeiten: &nbsp;  <button onclick="toggleVideoEdit();" class="button-video-edit">&nbsp;K&uuml;rzen&nbsp;</button>&nbsp;<br/>
</div>
<div id='camera_video_edit' class='camera_video_edit'>
<!-- INSERT TEMPLATE -->
</div>
*/
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
	var active_page       = data["DATA"]["active_page"];
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

function birdhouse_DeleteAnswer(data) {
	console.log(data);
	appMsg.alert(lang("DELETE_DONE") + "<br/>(" + data["deleted_count"] + " " + lang("FILES")+")","");
	// check how to reload the current view ...
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
			var del_command = "mboxApp.requestAPI(#POST#,[#remove#"+command+"],##,birdhouse_DeleteAnswer,##,#birdhouse_ImageGroup#);"; 
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
	URL = URL.replace(/http:\//g,"http://");
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
		
/*
<div class='star'><div id='s_/current/202010_value' style='display:none;'>1</div><img class='star_img' id='s_/current/202010' src='/html/star0.png' onclick='setFavorit("/current/202010",document.getElementById("s_/current/202010_value").innerHTML,"image_cam2_202010.jpg");'/></div>
<div class='trash'><div id='d_/current/202010_value' style='display:none;'>1</div><img class='trash_img' id='d_/current/202010' src='/html/recycle0.png' onclick='setRecycle("/current/202010",document.getElementById("d_/current/202010_value").innerHTML,"image_cam2_202010.jpg");'/></div>
*/

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
	for (var i=0;i<keys.length;i++) {
		var key     = keys[i];
		var onclick = "birdhousePrint_load(view=\""+link_list[key]["link"]+"\", camera=\""+app_active_cam+"\");";
		html += "<a style='cursor:pointer;' onclick='"+onclick+"'>"+lang(link_list[key]["link"])+"</a> ";
		if (i+1 < keys.length) { html += " | "; }
		}
	return html;
	}

//-----------------------------------------
// EOF
	

