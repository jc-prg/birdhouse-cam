//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// main functions 
//--------------------------------------
/* INDEX:
function birdhousePrint_load(view="INDEX", camera="", date="")
function birdhousePrint(data, active_page="", camera="")
function birdhousePrintTitle(data, active_page="", camera="")
function birdhouseSetMainVars(data)
function birdhouseHeaderFunctions()
function birdhouseSwitchCam()
function birdhouseReloadView()
function birdhouse_INDEX(data, camera)
function birdhouse_CAMERAS( title, data )
function birdhouse_VIDEO_DETAIL( title, data )
function birdhouse_LIST(title, data, camera, header_open=true)
function birdhouse_Camera(main, view, onclick, camera, stream_server, admin_allowed=false)
function birdhouse_ImageGroup(title, entries, entry_count, entry_category, header_open, admin=false, video_short=false)
function birdhouse_OtherGroupHeader( key, title, header_open )
function birdhouse_ImageGroupHeader( key, title, header_open, count={} )
function birdhouse_ImageURL(URL)
function birdhouse_Image(title, entry, header_open=true, admin=false, video_short=false, group_id="")
function birdhouse_Links(link_list)
*/
//--------------------------------------

var color_code = {
	"star"    : "lime",
	"detect"  : "aqua",
	"recycle" : "red",
	"default" : "white",
	"request" : "yellow"
	}
	
var app_available_cameras = [];
var app_active_page       = "";
var app_active_date       = "";
var app_camera_source     = {};
var app_recycle_range     = {};
var app_active_cam        = "cam1";
var app_admin_allowed     = false;

//-----------------------------------------
// load content from API and call print
//-----------------------------------------

function birdhousePrint_load(view="INDEX", camera="", date="") {

	var commands = [view];
	if (camera != "" && date != "")	{ commands.push(camera); commands.push(date); }
	else if (camera != "")			{ commands.push(camera); }
	else					{ commands.push(app_active_cam); }

	console.debug("Request "+view+" / "+camera+" / "+date);	
	appFW.requestAPI('GET',commands,"",birdhousePrint,"","birdhousePrint_load");
	}
	
//-----------------------------------------
// print views based on active page
//-----------------------------------------

function birdhousePrint(data) {

	console.debug("Request->Print ...");	

	birdhouseCameras  = data["DATA"]["cameras"];
	var date          = data["DATA"]["active_date"];
	var camera        = data["DATA"]["active_cam"];
	if (camera == "") 	{ camera = app_active_cam; }
	else			{ app_active_cam = camera; }
	
	console.log("Request->Print "+app_active_page+" / "+camera+" / "+date);	

	birdhouseSetMainVars(data);
	birdhousePrintTitle(data, app_active_page, camera);	
	setTextById("headerRight", birdhouseHeaderFunctions() );

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
	var switch_cam  = "<img class='header_icon' src='birdhouse/img/switch-camera-white.png' onclick='birdhouseSwitchCam();' style='position:relative;top:-4px;'>";
	var reload_view = "<img class='header_icon' src='birdhouse/img/reload-white.png' onclick='birdhouseReloadView();'>";
	var active_cam  = "<text style='position:relative;left:22px;top:2px;font-size:7px;'>"+app_active_cam.toUpperCase()+"</text>";	
	var info        = "&nbsp;";	
	var info = birdhouse_tooltip( info, "<div id='command_dropdown' style='width:90%;margin:auto;'>empty</div>", "info", "" );
	
	html = reload_view + active_cam + switch_cam + "&nbsp;&nbsp;&nbsp;" + info;
	
	if (app_available_cameras == undefined)	{ html = reload_view + "&nbsp;&nbsp;&nbsp;&nbsp;" + info; }
	else if (app_available_cameras.length > 1)	{ html = reload_view + active_cam + switch_cam + "&nbsp;&nbsp;&nbsp;" + info; }
	else						{ html = reload_view + "&nbsp;&nbsp;&nbsp;&nbsp;" + info; }
	
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
	
	if (app_active_page == "INDEX")
		for (let key in app_camera_source) {
			var image = document.getElementById("stream_"+key);
			image.src = "";
			
			app_camera_source[key] = app_camera_source[key].replace(/\/\//g,"/");
			app_camera_source[key] = app_camera_source[key].replace(":/","://");
			if (app_unique_stream_url)	{ image.src = app_camera_source[key]+"?"+app_unique_stream_id; }
			else				{ image.src = app_camera_source[key]; }
			}
	else {
		birdhousePrint_load(view=app_active_page, camera=app_active_cam, date=app_active_date);
		}
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
		html += birdhouse_Camera(main=true, view="cam1", onclick=onclick, camera=active_cam, stream_server=stream_server, admin_allowed=admin_allowed);
		html += "<br/>&nbsp;<br/>";
		app_camera_source[active_cam["name"]] = stream_server + cameras[active_cam["name"]]["stream"];
		}
	else {
		var onclick  = "birdhousePrint_load(view=\"INDEX\", camera=\""+other_cams[0]["name"]+"\");";
		html += birdhouse_Camera(main=false, view="cam1cam2", onclick=onclick, camera=other_cams[0], stream_server=stream_server, admin_allowed=admin_allowed);
		app_camera_source[other_cams[0]["name"]] = stream_server + cameras[other_cams[0]["name"]]["stream"];

		onclick      = "birdhousePrint_load(view=\"TODAY\", camera=\""+active_camera+"\");";
		html += birdhouse_Camera(main=true, view="cam1cam2", onclick=onclick, camera=active_cam, stream_server=stream_server, admin_allowed=admin_allowed);
		app_camera_source[active_cam["name"]] = stream_server + cameras[active_cam["name"]]["stream"];
		}
		
	setTextById("frame2",html);
	}
	
//-----------------------------------------

function birdhouse_CAMERAS( title, data ) {
	var cameras	= data["DATA"]["entries"];
	var admin 	= data["STATUS"]["admin_allowed"];
	var html	= "";
	
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
		if (admin && cameras[camera]["active"]) {
			var onclick = "birdhouse_createDayVideo('"+camera+"');";
			html += "<button onclick=\""+onclick+"\" class=\"button-video-edit\">&nbsp;"+lang("CREATE_DAY")+"&nbsp;</button>";
			}
	        html  += "</div></div>";
	        html  += "</div>";
		}
	setTextById("frame2",html);
	}

//-----------------------------------------

function birdhouse_VIDEO_DETAIL( title, data ) {
	var html = "";
	var video = data["DATA"]["entries"];
	var admin = data["STATUS"]["admin_allowed"];

	for (let key in video) {
		app_active_date         = key;
		var short               = false;
		var video_name          = video[key]["date"];
		var video_stream        = birdhouse_Image("Complete", video[key]);
		var video_stream_short  = "";
		
		console.log(video_stream);
	        
		if (video[key]["video_file_short"] != undefined && video[key]["video_file_short"] != "") {
	                short                     = true;
		        var video_short           = {};
		        Object.assign( video_short, video[key] );
		        var short_video_file      = video[key]["video_file_short"];
		        video_short["video_file"] = short_video_file;
		        video_stream_short        = birdhouse_Image("Short", video_short);
		        }
	        
		console.log(video_stream);
		console.log(video_stream_short);

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
		html += lang("LENGTH")     + ": " + Math.round(video[key]["length"]*10)/10 + " s<br/>";
		html += lang("FRAMERATE")  + ": " + video[key]["framerate"]   + " fps<br/>";
		html += lang("FRAMECOUNT") + ": " + video[key]["image_count"] + "<br/>";
		html += lang("IMAGESIZE")  + ": " + video[key]["image_size"]  + "<br/>";
//		html += lang("FILES")  + ": " + video[key]["video_file"]  + "<br/>";
		if (short) {
//			html += lang("FILES")  + ": " + video[key]["video_file_short"]  + "<br/>";
			html += lang("SHORT_VERSION") + ": " + Math.round(video[key]["video_file_short_length"]*10)/10 + " s<br/>";
			}
		if (admin) {
			html += "&nbsp;<br/>";
			html += lang("EDIT") + ":&nbsp; <button onclick=\"birdhouse_videoOverlayToggle();\" class=\"button-video-edit\">&nbsp;"+lang("SHORTEN_VIDEO")+"&nbsp;</button>&nbsp;<br/>";
			html += "</div>";
		
			var player = "<div id='camera_video_edit_overlay' class='camera_video_edit_overlay' style='display:none'></div>";
			player += "<div id='camera_video_edit' class='camera_video_edit' style='display:none'>";
			player += "<div style='height:46px;width:100%'></div>";
			var trim_command = "appMsg.wait_small('"+lang("PLEASE_WAIT")+"');birdhouse_createShortVideo();"; 
		
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
	var video_short       = true;
	
	if (active_page == "VIDEOS")					{ entry_category = [ "video" ]; }
	else if (active_page == "TODAY" && active_date == "")	{ entry_category = [ "today" ]; }
	else if (active_page == "TODAY" && active_date != "")	{ entry_category = [ "backup", active_date ]; }
	
        if (active_page == "VIDEOS")					{ entry_category = [ "video" ]; }
        else if (active_page == "TODAY" && active_date == "")	{ entry_category = [ "today" ]; }
        else if (active_page == "TODAY" && active_date != "")	{ entry_category = [ "backup", active_date ]; }
        
        if (active_page == "TODAY_COMPLETE") {
        	var data_labels = "";
        	var data_data   = "";
        	var keys        = Object.keys(entries);
        	keys            = keys.sort();
        	for (var i=0;i<keys.length;i++) {
        		key = keys[i];
        		data_labels += "'"+entries[key]["time"]+"', ";
        		data_data   += Math.round((100-entries[key]["similarity"])*10)/10+", ";
        		}
        	html += "[ "+data_labels+" ]";
        	html += "<hr>";
        	html += "[ "+data_data+" ]";
        	}

	// group favorits per month
        if (active_page == "FAVORITS") { 
                var groups2 = {}
                Object.entries(groups).forEach(([key, value]) => {
                        if (key.indexOf(".") > 0) {
                                [day,month,year] = key.split(".");
                                if (!groups2[year+"-"+month]) { groups2[year+"-"+month] = value; }
                                else {groups2[year+"-"+month] = groups2[year+"-"+month].concat(value);}
                                }
                        else {
                                groups2[key] = value;
                                }
                        })
                groups = groups2;
                }
	
	// today complete, favorits
	if (groups != undefined && groups != {}) {
		var count_groups = 0;
		for (let group in groups) {
			var title = group;
			var group_entries = {};
			for (i=0;i<groups[group].length;i++) {
				key                = groups[group][i];
				group_entries[key] = entries[key];
				}
			if (active_page == "ARCHIVE") { 
				title = lang("ARCHIVE") + " &nbsp;(" + group + ")";
				if (count_groups > 0) { header_open = false; }
				//--> doesn't work if image names double across the different groups; image IDs have to be changed (e.g. group id to be added)
				}
			delete group_entries["999999"];
			html += birdhouse_ImageGroup(title, group_entries, entry_count, entry_category, header_open, admin, video_short);
			count_groups += 1;
			}
		}
	// today, backup, video
	else {
		entries_available = false;
		if (active_date != undefined && active_date != "")						{ title = active_date; }
	        if (entries != undefined &&  Object.keys(entries).length > 0)				{ html += birdhouse_ImageGroup(title, entries, entry_count, entry_category, header_open, admin, video_short); entries_available = true; }
		if (admin) {
		        if (entries_yesterday != undefined && Object.keys(entries_yesterday).length > 0)	{ html += birdhouse_ImageGroup(lang("YESTERDAY"), entries_yesterday, entry_count, entry_category, false, admin, video_short); entries_available = true; }
		        if (entries_delete != undefined && Object.keys(entries_delete).length > 0)		{ html += birdhouse_ImageGroup(lang("RECYCLE"), entries_delete, ["recycle"], entry_category, false, admin, video_short); entries_available = true; }
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

function birdhouse_Camera(main, view, onclick, camera, stream_server, admin_allowed=false) {
	var html      = "";
	var style_cam = view;
	
	if (main) { var container = 'main'; }
	else      { var container = '2nd'; }

	if (app_unique_stream_url)	{ var stream_link    = stream_server + camera["stream"] + "?" + app_unique_stream_id; }
	else 				{ var stream_link    = stream_server + camera["stream"]; }
	stream_link = stream_link.replace(/\/\//g,"/");
	stream_link = stream_link.replace(":/","://");
	
	var livestream     = "<img src='"+stream_link+"' id='stream_"+camera["name"]+"' class='livestream_"+container+"'/>";
	var command_record = "appFW.requestAPI(\"POST\",[\"start\",\"recording\",\""+camera["name"]+"\"],\"\",\"\",\"\",\"birdhouse_INDEX\");"; //requestAPI(\"/start/recording/cam2\");
	var command_stop   = "appFW.requestAPI(\"POST\",[\"stop\", \"recording\",\""+camera["name"]+"\"],\"\",\"\",\"\",\"birdhouse_INDEX\");";; //requestAPI(\"/stop/recording/cam2\");
	
	html     += "<center><div class='livestream_"+container+"_container "+view+"'>";
	html     += "  <a onclick='"+onclick+"' style='cursor:pointer;'>" + livestream + "</a>";
	if (main && admin_allowed) {
		html     += "  <div class='livestream_record "+view+"'>";
		html     += "     <button onclick='"+command_record+"' class='button-video-record'>Record ("+camera["name"]+")</button> &nbsp;";
		html     += "     <button onclick='"+command_stop+"'   class='button-video-record'>Stop ("+camera["name"]+")</button>";
		html     += "  </div>";
		}
	html     += "</div></center>";

	return html;
	}

//-----------------------------------------

function birdhouse_ImageGroup(title, entries, entry_count, entry_category, header_open, admin=false, video_short=false) {

	var count     = {};
	var html      = "";
	var image_ids = "";
	var display   = "";
	var group_id  = title;
		
	if (admin) {
		for (i=0;i<entry_count.length;i++) 	{ count[entry_count[i]] = 0; }
		if (count["all"] != undefined) 	{ count["all"] = Object.keys(entries).length; }
		
		for (let key in entries) {
			var img_id2 = "";
			img_id2 += entries[key]["directory"] + entries[key]["lowres"];
			img_id2 = img_id2.replace( /\//g, "_");

			if (count["star"] != undefined    && parseInt(entries[key]["favorit"]) == 1)			{ count["star"]    += 1; }
			else if (count["recycle"] != undefined && parseInt(entries[key]["to_be_deleted"]) == 1)	{ count["recycle"] += 1; }
			else if (count["detect"] != undefined && parseInt(entries[key]["detect"]) == 1)		{ count["detect"]  += 1; }
			if (header_open == false && entries[key]["lowres"] != undefined)				{ image_ids += " " + img_id2; }
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
			var del_command = "appFW.requestAPI(#POST#,[#remove#"+command+"],##,birdhouse_AnswerDelete,##,#birdhouse_ImageGroup#);"; 
			var onclick     = "appMsg.confirm(\""+lang("DELETE_SURE")+"\",\""+del_command+"\");";
			html    += "<div id='group_intro_recycle' class='separator' style='display: block;'><center><br/>";
			html    += "<a onclick='"+onclick+"' style='cursor:pointer;'>" + lang("RECYCLE_DELETE") + "</a>";
			html    += "<br/>&nbsp;</center></div>";
			}
		}
	else if (admin) {
		html    += "<div id='recycle_range_"+group_id+"' class='separator' style='display: none;'><center><i><br/>";
		html    += "<text id='recycle_range_"+group_id+"_info'>...</text>";
		html    += "<br/>&nbsp;</i></center></div>";
		}
	//html += "<div class='separator'>&nbsp;</div>";

	entry_keys = Object.keys(entries).sort().reverse();
	for (var i=0;i<entry_keys.length;i++) {
		key   = entry_keys[i];
		var img_title = key;
		//if (entry_keys[key]["type"] == "video") {  title = entry_keys[key]["date"]; }
		html += birdhouse_Image(title=img_title, entry=entries[key], header_open=header_open, admin=admin, video_short=video_short, group_id=group_id);
		}
		
	html += "</div>";
	return html;
	}
	
//-----------------------------------------

function birdhouse_OtherGroupHeader( key, title, header_open ) {
	var status = "−";
	if (header_open == false) { status = "+"; }
	var html   = "";
	html += "<div id='group_header_"+key+"' class='separator_group' onclick='birdhouse_groupToggle(\""+key+"\")'>";
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
	html += "<div id='group_header_"+key+"' class='separator_group' onclick='birdhouse_groupToggle(\""+key+"\")'>";
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

function birdhouse_Image(title, entry, header_open=true, admin=false, video_short=false, group_id="") {
	var html        = "";
	var play_button = "";
	var dont_load   = "";
	var edit        = false;
	var category    = "";
	
	console.log(app_active_page);
	
	if (entry["type"] == "image") {	
		var lowres      = birdhouse_ImageURL(RESTurl + entry["directory"] + entry["lowres"]);
		var hires       = birdhouse_ImageURL(RESTurl + entry["directory"] + entry["hires"]);
		var description = entry["time"] + " (" + entry["similarity"] + "%)";

		if (app_active_page == "FAVORITS") {
			[day,month,year]  = entry["date"].split(".");
			[hour,minute,sec] = entry["time"].split(":");
			description       = entry["date"]+" ("+hour+":"+minute+")";
			}
		
		var onclick     = "birdhouse_imageOverlay(\""+hires+"\",\""+description+"\");";
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
		var description = title;
		var lowres      = birdhouse_ImageURL(RESTurl + entry["lowres"]);
		var hires       = birdhouse_ImageURL(RESTurl + entry["hires"]);
		var onclick     = "birdhouse_imageOverlay(\""+hires+"\",\""+description+"\");";
		//if (app_unique_stream_url) { hires += "?" + app_unique_stream_id; }
		}		
	else if (entry["type"] == "video") {
		var note        = "";
		var video_file  = entry["video_file"];
		if (entry["video_file_short"] != undefined && entry["video_file_short"] != "") { 
			if (video_short) {
				video_file  = entry["video_file_short"];
				note = "*"; 
			}	}
		var lowres      = birdhouse_ImageURL(RESTurl + entry["path"] + entry["thumbnail"]);
		var hires       = birdhouse_ImageURL(birdhouseCameras[entry["camera"]]["streaming_server"] + video_file);
		var description = "";
		if (title.indexOf("_") > 0)	{ description = entry["date"] + "[br/]" + entry["camera"].toUpperCase() + ": " + entry["camera_name"]; }
		else				{ description = title + "[br/]" + entry["camera"].toUpperCase() + ": " + entry["camera_name"]; }
		var onclick     = "birdhouse_videoOverlay(\""+hires+"\",\""+description+"\");";
		var play_button = "<img src=\"birdhouse/img/play.png\" class=\"play_button\" onclick='"+onclick+"' />";
		entry["lowres"] = entry["thumbnail"];
		description     = description.replace(/\[br\/\]/g,"<br/>");
		if (admin) {
			var cmd_edit = "birdhousePrint_load(view=\"VIDEO_DETAIL\", camera=\""+app_active_cam+"\", date=\""+entry["date_start"]+"\");"
			description += "<br/><a onclick='"+cmd_edit+"' style='cursor:pointer;'>"+lang("EDIT")+"</a>"+note;
			}
		edit            = true;
		}
	if (header_open == false) {
		dont_load       = "data-";
		}
	
	var style       = "";
	var star        = "";
	var recycle     = "";
	
	var img_id2 = "";
	img_id2 += entry["directory"] + entry["lowres"];
	img_id2 = img_id2.replace( /\//g, "_");
	
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

		var onclick_star    = "birdhouse_setFavorit(index=\""+img_id+"\",status=document.getElementById(\"s_"+img_id2+"_value\").innerHTML,lowres_file=\""+img_name+"\",img_id=\""+img_id2+"\");";
		var onclick_recycle = "birdhouse_setRecycle(index=\""+img_id+"\",status=document.getElementById(\"d_"+img_id2+"_value\").innerHTML,lowres_file=\""+img_name+"\",img_id=\""+img_id2+"\");";
		onclick_recycle    += "birdhouse_recycleRange(group_id=\""+group_id+"\", index=\""+img_id+"\", status=document.getElementById(\"d_"+img_id2+"_value\").innerHTML, lowres_file=\""+img_name+"\")"; 
		
		star        = "<div id='s_"+img_id2+"_value' style='display:none;'>"+img_star_r+"</div>   <img class='star_img'    id='s_"+img_id2+"' src='"+img_dir+"star"+img_star+".png'       onclick='"+onclick_star+"'/>";
		recycle     = "<div id='d_"+img_id2+"_value' style='display:none;'>"+img_recycle_r+"</div><img class='recycle_img' id='d_"+img_id2+"' src='"+img_dir+"recycle"+img_recycle+".png' onclick='"+onclick_recycle+"'/>";
		}
		
	html += "<div class='image_container'>";
	html += "  <div class='star'>"+star+"</div>";
	html += "  <div class='recycle'>"+recycle+"</div>";
	html += "  <div class='thumbnail_container'>"
//	html += "    <a onclick='"+onclick+"' style='cursor:pointer;'><img "+dont_load+"src='"+lowres+"' id='"+entry["lowres"]+"' class='thumbnail' style='"+style+"'/></a>";
	html += "    <a onclick='"+onclick+"' style='cursor:pointer;'><img "+dont_load+"src='"+lowres+"' id='"+img_id2+"' class='thumbnail' style='"+style+"'/></a>";
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
// EOF
	

