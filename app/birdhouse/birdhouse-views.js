//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// birdhouse views
//--------------------------------------

function birdhouse_INDEX(data, camera) {

	var html          = "";
	var active_camera = camera;
	var cameras       = data["DATA"]["devices"]["cameras"];
	var admin_allowed = data["STATUS"]["admin_allowed"];
	var stream_server = RESTurl;
	var active_cam    = {};
	var other_cams    = [];

	for (let key in cameras) {
	    if (cameras[key]["active"] ) { //&& cameras[key]["status"]["error"] == false) {
    	    if (active_camera == undefined) { active_camera = key; }
            if (key == active_camera) {
                active_cam  = {
                    "name"        : key,
                    "stream"      : cameras[key]["video"]["stream"],
                    "description" : key.toUpperCase + ": " + cameras[key]["camera_name"]
                    }
                }
            else {
                var other_cam  = {
                    "name"        : key,
                    "stream"      : cameras[key]["video"]["stream"],
//                    "stream"      : cameras[key]["video"]["stream_lowres"],
//                    "stream"      : cameras[key]["video"]["stream_pip"], // replace {2nd-camera-key}
                    "description" : key.toUpperCase + ": " + cameras[key]["camera_name"]
                    }
                other_cams.push(other_cam);
                }
            }
		}
	if (active_cam == {} && other_cams != []) { active_cam = other_cams[0]; other_cams.shift(); }

	if (Object.keys(cameras).length == 0 || active_cam == {}) {
	    html += lang("NO_ENTRIES");
	}
	console.log(cameras);
	console.log(active_cam);
	console.log(active_camera);

    html += "<div id='video_stream_online' style='display:block;'>";
	if (Object.keys(cameras).length == 1 || other_cams.length == 0) {
		var onclick  = "birdhousePrint_load(view=\"TODAY\", camera=\""+active_camera+"\");";
		html += birdhouse_Camera(main=true, view="cam1", onclick=onclick, camera=active_cam, stream_server=stream_server, admin_allowed=admin_allowed);
		html += "<br/>&nbsp;<br/>";
		app_camera_source[active_cam["name"]] = stream_server + cameras[active_cam["name"]]["video"]["stream"];
		//app_camera_source[active_cam["name"]] = birdhouse_StreamURL(active_cam["name"], cameras[active_cam["name"]]["video"]["stream"], "stream_in_list");
    }
	else {
		var onclick  = "birdhousePrint_load(view=\"INDEX\", camera=\""+other_cams[0]["name"]+"\");";
		html += birdhouse_Camera(main=false, view="cam1cam2", onclick=onclick, camera=other_cams[0], stream_server=stream_server, admin_allowed=admin_allowed);
		app_camera_source[other_cams[0]["name"]] = stream_server + cameras[other_cams[0]["name"]]["video"]["stream"];
		//app_camera_source[other_cams[0]["name"]] = birdhouse_StreamURL(other_cams[0]["name"], cameras[other_cams[0]["name"]]["video"]["stream"], "stream_in_list_2");

		onclick = "birdhousePrint_load(view=\"TODAY\", camera=\""+active_camera+"\");";
		html += birdhouse_Camera(main=true, view="cam1cam2", onclick=onclick, camera=active_cam, stream_server=stream_server, admin_allowed=admin_allowed);
		app_camera_source[active_cam["name"]] = stream_server + cameras[active_cam["name"]]["video"]["stream"];
		//app_camera_source[active_cam["name"]] = birdhouse_StreamURL(active_cam["name"], cameras[active_cam["name"]]["video"]["stream"], "stream_in_list_3");
	}
    html += "</div>";
    html += "<div id='video_stream_offline' style='display:none;'><center>&nbsp;<br/>&nbsp;<br/>";
    html += "<img src='"+app_error_connect_image+"' style='width:80%;border:1px solid white;'>";
    html += "<br/>&nbsp;<br/>&nbsp;</center></div>";
	setTextById(app_frame_content,html);
}

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

	setTextById(app_frame_content,html);
	}

function birdhouse_LIST(title, data, camera, header_open=true) {

	var html              = "";
	var entry_category    = [];
	var same_img_size     = false;

	var entry_count       = data["DATA"]["view_count"];
	var entries           = data["DATA"]["entries"];
	var entries_yesterday = data["DATA"]["entries_yesterday"];
	var entries_delete    = data["DATA"]["entries_delete"];
	var active_date       = data["STATUS"]["view"]["active_date"];
	if (data["DATA"]["max_image_size"]) {
        var max_image_size_LR  = data["DATA"]["max_image_size"]["lowres"];
        var max_image_size_HR  = data["DATA"]["max_image_size"]["hires"];
        }
    else {
        var max_image_size_LR  = 0;
        var max_image_size_HR  = 0;
        }
	var active_page       = app_active_page;
	var groups            = data["DATA"]["groups"];
	var admin             = data["STATUS"]["admin_allowed"];
	var server_status     = data["STATUS"]["server"];
	var sensors           = data["DATA"]["devices"]["sensors"];
	var video_short       = true;

	if (active_page == "VIDEOS")                           { entry_category = [ "video" ]; }
	else if (active_page == "TODAY" && active_date == "")  { entry_category = [ "today" ]; }
	else if (active_page == "TODAY" && active_date != "")  { entry_category = [ "backup", active_date ]; }

    if (active_page == "VIDEOS")                           { entry_category = [ "video" ]; }
    else if (active_page == "TODAY" && active_date == "")  { entry_category = [ "today" ]; }
    else if (active_page == "TODAY" && active_date != "")  { entry_category = [ "backup", active_date ]; }

    // create chart data
    if (active_page == "TODAY_COMPLETE" || (active_page == "TODAY" && active_date != "" && active_date != undefined)) {
        var chart_data = data["DATA"]["chart_data"];
        var chart_titles = [];
        for (var x=0;x<chart_data["titles"].length;x++) {
            if (chart_data["titles"][x].indexOf(":")>-1) {
                var sensor = chart_data["titles"][x].split(":");
                var translation = lang(sensor[1].toUpperCase().replace(" ",""));
                if (translation.indexOf("not found") < 0) { sensor[1] = translation; }
                var title_s = sensor[1].charAt(0).toUpperCase() + sensor[1].slice(1);
                if (sensors[sensor[0]]) {
                    title_s += " ("+sensors[sensor[0]]["name"]+")";
                    }
                else if (sensor[0].indexOf("WEATHER/") >= 0) {
                    var location = sensor[0].replace("WEATHER/", "");
                    title_s += " ("+location+")";
                    }
                }
            else {
                var translation = lang(chart_data["titles"][x].toUpperCase());
                if (translation.indexOf("not found") < 0) { chart_data["titles"][x] = translation; }
                title_s = chart_data["titles"][x];
                }
            title_s = title_s.replace("&szlig;", "ß");
            title_s = title_s.replace("&uuml;", "ü");
            title_s = title_s.replace("&auml;", "ä");
            title_s = title_s.replace("&ouml;", "ö");
            chart_titles.push(title_s);
        }
        var chart = birdhouseChart_create(title=chart_titles,data=chart_data["data"]);
        html += birdhouse_OtherGroup( "chart", lang("ANALYTICS"), chart, true );

        // Weather -> to be optimizes incl error check if no entries
        html += birdhouseChart_weatherOverview(entries);
    }

    if (active_page != "FAVORITES" && app_active_page != "VIDEOS" && app_active_page != "ARCHIVE") {
        same_img_size = true;
    }

	// group favorites per month
    if (active_page == "FAVORITES" && groups != undefined) {
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

	// today complete, favorites
	if (groups != undefined && groups != {}) {
		var count_groups = 0;

        Object.keys(groups).sort().reverse().forEach( group => {
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
			html += birdhouse_ImageGroup(title, group_entries, entry_count, entry_category, header_open, admin,
			                             video_short, same_img_size, max_image_size_LR);
			count_groups += 1;
        });
        if (html == "" && server_status["view_favorite_loading"] == "done") {
            html += "<center>&nbsp;<br/>"+lang("NO_ENTRIES")+"<br/>&nbsp;</center>";
        }
        else if (html == "") {
            html += "<center>&nbsp;<br/>"+lang("DATA_LOADING_TRY_AGAIN")+"<br/>&nbsp;</center>";
        }
    }

	// today, backup, video
	else {
		entries_available = false;
		if (active_date != undefined && active_date != "") {
		    title = active_date;
        }
        if (entries != undefined &&  Object.keys(entries).length > 0) {
            html += birdhouse_ImageGroup(title, entries, entry_count, entry_category, header_open, admin, video_short,
                                         same_img_size, max_image_size_LR);
            entries_available = true;
            }
		if (admin) {
		        if (entries_yesterday != undefined && Object.keys(entries_yesterday).length > 0) {
		            html += birdhouse_ImageGroup(lang("YESTERDAY"), entries_yesterday, entry_count, entry_category,
		                                         false, admin, video_short, same_img_size, max_image_size_LR);
		            entries_available = true;
		            }
		        if (entries_delete != undefined && Object.keys(entries_delete).length > 0) {
		            html += birdhouse_ImageGroup(lang("RECYCLE"), entries_delete, ["recycle"], entry_category, false,
		                                         admin, video_short, same_img_size, max_image_size_LR);
		            entries_available = true;
		            }
		        }
		if (entries_available == false) {
		    if (server_status["view_favorite_loading"] == "done" && server_status["view_archive_loading"] == "done") {
   			    html += "<center>&nbsp;<br/>"+lang("NO_ENTRIES")+"<br/>&nbsp;</center>";
   			    }
   			else {
    			html += "<center>&nbsp;<br/>"+lang("DATA_LOADING_TRY_AGAIN")+"<br/>&nbsp;</center>";
   			    }
			}
		}
	setTextById(app_frame_content, html);
	}
