//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// birdhouse views
//--------------------------------------

function birdhouse_INDEX(data, camera) {

	var html          = "";
	var active_camera = camera;
	var cameras       = app_data["SETTINGS"]["devices"]["cameras"];
	var title         = app_data["SETTINGS"]["title"];
	var index_view    = app_data["SETTINGS"]["views"]["index"];
	var admin_allowed = data["STATUS"]["admin_allowed"];
	var camera_status = data["STATUS"]["devices"]["cameras"];
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
                    "description" : key.toUpperCase + ": " + cameras[key]["camera_name"],
                    "error"       : camera_status[key]["error"]
                    }
                }
            else {
                var other_cam  = {
                    "name"        : key,
                    "stream"      : cameras[key]["video"]["stream"],
                    "description" : key.toUpperCase + ": " + cameras[key]["camera_name"],
                    "error"       : camera_status[key]["error"]
                    }
                other_cams.push(other_cam);
                }

            app_camera_source[key]                      = stream_server + cameras[key]["video"]["stream"];
            app_camera_source["lowres_" + key]          = stream_server + cameras[key]["video"]["stream_lowres"];
            app_camera_source["pip_" + key]             = stream_server + cameras[key]["video"]["stream_pip"];
            app_camera_source["detect_" + key]          = stream_server + cameras[key]["video"]["stream_detect"];
            app_camera_source["detect_" + key + "_img"] = stream_server + cameras[key]["video"]["stream_detect"];
            app_camera_source["overlay_" + key]         = stream_server + cameras[key]["video"]["stream_detect"];
            }
		}
	if (active_cam == {} && other_cams != [])                   { active_cam = other_cams[0]; other_cams.shift(); }
	if (Object.keys(cameras).length == 0 || active_cam == {})   { html += lang("NO_ENTRIES"); }
	if (other_cams.length == 1 && admin_allowed == false) {
	    if (other_cams[0]["error"])     { other_cams = []; }
	    else if (active_cam["error"])   { active_cam = other_cams[0]; other_cams = []; }
	}

    console.log("---> birdhouse_INDEX: " + camera + "/" + app_active_cam);

	var replace_tags = {};
	replace_tags["OFFLINE_URL"]     = app_error_connect_image;
    replace_tags["CAM1_ID"]         = active_camera;
    replace_tags["CAM1_URL"]        = stream_server + cameras[active_cam["name"]]["video"]["stream"];

    if (selected_view != "picture-in-picture" || other_cams.length == 0) {
        //replace_tags["CAM1_LOWRES_URL"] = birdhouse_StreamURL(active_cam["name"], stream_server + cameras[active_cam["name"]]["video"]["stream_lowres"], "main_lowres", true);
        replace_tags["CAM1_URL"]        = birdhouse_StreamURL(active_cam["name"], stream_server + cameras[active_cam["name"]]["video"]["stream"], "main", true);
        }

    if (selected_view == "picture-in-picture" && other_cams.length > 0) {
        replace_tags["CAM1_PIP_URL"]    = birdhouse_StreamURL(other_cams[0]["name"], stream_server + cameras[active_cam["name"]]["video"]["stream_pip"], "main_pip", true);
        replace_tags["CAM1_PIP_URL"]    = replace_tags["CAM1_PIP_URL"].replace("{2nd-camera-key}", other_cams[0]["name"]);
        replace_tags["CAM1_PIP_URL"]    = replace_tags["CAM1_PIP_URL"].replace("{2nd-camera-pos}", index_view["lowres_position"]);
    }
    if (selected_view != "picture-in-picture" && other_cams.length > 0) {
        replace_tags["CAM2_ID"]         = other_cams[0]["name"];
        //replace_tags["CAM2_URL"]        = birdhouse_StreamURL(other_cams[0]["name"], stream_server + cameras[other_cams[0]["name"]]["video"]["stream"], "2nd", true);
        replace_tags["CAM2_LOWRES_URL"] = birdhouse_StreamURL(other_cams[0]["name"], stream_server + cameras[other_cams[0]["name"]]["video"]["stream_lowres"], "2nd_lowres", true);
        replace_tags["CAM2_LOWRES_POS"] = index_lowres_position[index_view["lowres_position"].toString()];
    }

    var selected_view = "";
	if (Object.keys(cameras).length == 1 || other_cams.length == 0)         { selected_view = "single"; }
    else if (index_template[index_view["type"]])                            { selected_view = index_view["type"]; }
	else                                                                    { selected_view = "default"; }
    if (admin_allowed && index_template[selected_view+"_admin"])            { selected_view += "_admin"; }

    html += index_template[selected_view];
    html += index_template["offline"];
    html  = html.replace("<!--ADMIN-->", index_template["admin"]);

    Object.keys(replace_tags).forEach( key => {
        html = html.replaceAll("<!--"+key+"-->", replace_tags[key]);
    });

	setTextById(app_frame_content, html);
	setTextById(app_frame_header, "<center><h2>" + title + "</h2></center>");

    if (other_cams.length == 0)                                { elementHidden("admin_status_index"); }
    if (!cameras[active_camera]["video"]["allow_recording"])   { elementHidden("admin_record_index"); }
}

function birdhouse_VIDEO_DETAIL( title, data ) {

	var html        = "";
	var video       = data["DATA"]["data"]["entries"];
	var admin       = data["STATUS"]["admin_allowed"];
	var server_info = app_data["SETTINGS"]["server"];
    var tab         = new birdhouse_table();

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

        tab.style_rows["height"]           = "20px";
        tab.style_cells["vertical-align"]  = "top";

        var video_title  = "";
        if (video[key]["title"]) { video_title  = video[key]["title"]; }
        var onclick_video = "birdhouse_editVideoTitle(title=\"set_video_title\", video_id=\""+key+"\", camera=\""+video[key]["camera"]+"\");";
        var edit_title    = "<input id='set_video_title' value='"+video_title+"' style='width:100px;'>&nbsp;&nbsp;";
        edit_title       += "<button class='button-video-edit' onclick='"+onclick_video+"'>"+lang("SAVE")+"</button>";

		html += "<div class='camera_info' style='height:auto;'>";
		html += "<div class='camera_info_image video_edit'>";
		html += video_stream;
		if (short) {
			html += video_stream_short;
			}
		html += "</div>";
		html += "<div class='camera_info_text'>";
		html += "<h3>"+video_name+"</h3>";
		html += "&nbsp;<br/>";

        html += tab.start();
		html += tab.row(lang("CAMERA")      + ": ", video[key]["camera"].toUpperCase() + " - " + video[key]["camera_name"]);
		html += tab.row(lang("TITLE")       + ": ", edit_title);
		html += tab.row(lang("LENGTH")      + ": ", Math.round(video[key]["length"]*10)/10 + " s<br/>");
		html += tab.row(lang("FRAMERATE")   + ": ", video[key]["framerate"]   + " fps");
		html += tab.row(lang("FRAME_COUNT") + ": ", video[key]["image_count"]);
		html += tab.row(lang("IMAGESIZE")   + ": ", video[key]["image_size"]);
//		html += lang("FILES")  + ": " + video[key]["video_file"]  + "<br/>";
		if (short) {
//			html += lang("FILES")  + ": " + video[key]["video_file_short"]  + "<br/>";
			html += tab.row(lang("SHORT_VERSION") + ": ", Math.round(video[key]["video_file_short_length"]*10)/10 + " s");
			}

		if (admin) {
		    html += tab.row("&nbsp;");
			html += tab.row(lang("EDIT") + ":", "<button onclick=\"birdhouse_videoOverlayToggle();\" class=\"button-video-edit\">&nbsp;"+lang("SHORTEN_VIDEO")+"&nbsp;</button>&nbsp;");

			var player = "<div id='camera_video_edit_overlay' class='camera_video_edit_overlay' style='display:none'></div>";
			player += "<div id='camera_video_edit' class='camera_video_edit' style='display:none'>";
			player += "<div style='height:46px;width:100%'></div>";
			var trim_command = "appMsg.wait_small('"+lang("PLEASE_WAIT")+"');birdhouse_createShortVideo();";

			loadJS(videoplayer_script, "", document.body);

            var video_stream_server = "";
            if (server_info["ip4_stream_video"] != "") {
                video_stream_server = server_info["ip4_stream_video"];
                }
            else if (server_info["ip4_address"] != "") {
                video_stream_server = server_info["ip4_address"];
                }
            else {
                video_stream_server = window.location.href.split("//")[1];
                video_stream_server = video_stream_server.split("/")[0];
                video_stream_server = video_stream_server.split(":")[0];
                }
			video_stream_server = "http://" + video_stream_server + ":" + server_info["port_video"] + "/";

			video_values = {};
			video_values["VIDEOID"]    = key;
			video_values["ACTIVE"]     = app_active_cam;
			video_values["LENGTH"]     = video[key]["length"];
			video_values["THUMBNAIL"]  = "";
			// video_values["VIDEOFILE"]  = video[key]["directory"] + video[key]["video_file"];
			video_values["VIDEOFILE"]  = video_stream_server + video[key]["video_file"];
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
    html += tab.end();
    html += "</div>";

	setTextById(app_frame_content,html);
	}

function birdhouse_LIST(title, data, camera, header_open=true) {

	var html              = "";
	var entry_category    = [];
	var same_img_size     = false;
	var data_list         = data["DATA"];
	var status_data       = app_data["STATUS"]["devices"]["cameras"][camera];

	var active_page       = data_list["active"]["active_page"];
	var entries           = data_list["data"]["entries"];
	var entries_yesterday = data_list["data"]["entries_yesterday"];
	var entries_delete    = data_list["data"]["entries_delete"];
	var groups            = data_list["data"]["groups"];
	var weather_data      = data_list["data"]["weather_data"];
	var chart_data        = data_list["data"]["chart_data"];
	var entry_count       = data_list["view"]["view_count"];

	var sensors           = app_data["SETTINGS"]["devices"]["sensors"];
	var camera_settings   = app_data["SETTINGS"]["devices"]["cameras"];
	var current_weather   = app_data["WEATHER"]["forecast"]["today"];

	var group_list        = [];
	var tab               = new birdhouse_table();
	tab.style_cells["vertical-align"] = "top";

	if (data_list["view"]["max_image_size"]) {
        var max_image_size_LR  = data_list["view"]["max_image_size"]["lowres"];
        var max_image_size_HR  = data_list["view"]["max_image_size"]["hires"];
        }
    else {
        var max_image_size_LR  = 0;
        var max_image_size_HR  = 0;
        }

	var active_page       = app_active_page;
	var active_date       = data_list["active"]["active_date"];

	var admin             = data["STATUS"]["admin_allowed"];
	var server_status     = app_data["STATUS"]["server"];
	var video_short       = true;
	var page_title        = "";
	var page_status       = "";

	var link_day_back      = "";
	var link_day_forward   = "";
	if (data_list["data"]["day_back"] != "")    {
	    var onclick_back    = "birdhousePrint_load(view=\"TODAY\", camera=\""+camera+"\", date=\""+data_list["data"]["day_back"]+"\");";
	    link_day_back       = "<div onclick='" + onclick_back + "' class='button-back-and-forth' style='float:right;'>" + lang("DAY_BACK") + " &#187;</div>";
	    }
	if (data_list["data"]["day_forward"] != "") {
	    var onclick_forward = "birdhousePrint_load(view=\"TODAY\", camera=\""+camera+"\", date=\""+data_list["data"]["day_forward"]+"\");";
	    link_day_forward    = "<div onclick='" + onclick_forward + "' class='button-back-and-forth' style='float:left;'>&#171; " + lang("DAY_FORWARD") + "</div>";
	    }

	if (active_page == "VIDEOS")                           { entry_category = [ "video" ]; }
	else if (active_page == "TODAY" && active_date == "")  { entry_category = [ "today" ]; }
	else if (active_page == "TODAY" && active_date != "")  { entry_category = [ "backup", active_date ]; }

    // create slider
	if (admin && active_page == "TODAY_COMPLETE" || (admin & active_page == "TODAY" && active_date != "" && active_date != undefined)) {
	    var cam_settings = camera_settings[camera];

	    var threshold_slider_onchange   = "document.getElementById(\"set_threshold_"+app_active_cam+"\").value=this.value;";
	    var threshold_input_onchange    = "document.getElementById(\"threshold_slider_"+app_active_cam+"\").value=this.value;";
	    var threshold_initial_value     = cam_settings["similarity"]["threshold"];
	    var threshold_onclick_try       = "birdhouse_view_images_threshold(document.getElementById(\"set_threshold_"+app_active_cam+"\").value);";

	    if (active_page == "TODAY_COMPLETE") {
	        var threshold_onclick_set       = "birdhouse_edit_send(\"set_threshold_"+app_active_cam+"\",\""+app_active_cam+"\");";
	        threshold_onclick_set          += "birdhouseReloadView();";
	        var threshold_onclick_set_cmd   = "Save";
	        }
	    else {
	        var threshold_onclick_set       = "alert(\"Not implemented yet.\");";
	        var threshold_onclick_set       = "current_threshold = document.getElementById(\"set_threshold_"+app_active_cam+"\").value;"
	        threshold_onclick_set          += "birdhouse_recycleThreshold(\"backup\", \""+active_date+"\", current_threshold, 1, \""+app_active_cam+"\");";
	        var threshold_onclick_set_cmd   = "Recycle";
	    }

	    var threshold_onclick_reset     = "document.getElementById(\"threshold_slider_"+app_active_cam+"\").value = "+threshold_initial_value+";";
	    threshold_onclick_reset        += "document.getElementById(\"set_threshold_"+app_active_cam+"\").value = "+threshold_initial_value+";";
	    threshold_onclick_reset        += "birdhouse_view_images_threshold(100);";

	    var threshold_slider        = "<div style='float:left;'><input type='range' id='threshold_slider_"+app_active_cam+"' onchange='"+threshold_slider_onchange+"' class='bh-slider' style='width:80%;' min='0' max='100' value='"+threshold_initial_value+"'>";
	    threshold_slider           += "<input id='set_threshold_"+app_active_cam+"' class='bh-slider-value' style='width:10%;' onchange='"+threshold_input_onchange+"' value='"+threshold_initial_value+"'>";
	    threshold_slider           += "<input id='set_threshold_"+app_active_cam+"_data' style='display:none;' value='devices:cameras:"+app_active_cam+":similarity:threshold'>";
	    threshold_slider           += "<input id='set_threshold_"+app_active_cam+"_data_type' style='display:none;' value='float'></div>";
        threshold_slider           += "<div style='float:left;'><button class='bh-slider-button' onclick='"+threshold_onclick_try+"' style='float:none;'>Try</button>";
        threshold_slider           += "<button class='bh-slider-button' onclick='"+threshold_onclick_reset+"' style='float:none;'>Reset</button>";
        threshold_slider           += "<button class='bh-slider-button' onclick='"+threshold_onclick_set+"' style='float:none;'>"+threshold_onclick_set_cmd+"</button></div>";
        threshold_slider           += "<div id='info_set_threshold' style='padding:5px;width:100%;float:left;'>&nbsp;</div>";
    }
	// details for admins - TODAY COMPLETE
	if (admin && active_page == "TODAY_COMPLETE") {
	    var info_text    = "";
	    var cam_settings = camera_settings[camera];
	    var record_from  = status_data["record_image_start"];
	    var record_to    = status_data["record_image_end"];
        var rhythm       = cam_settings["image_save"]["rhythm"] + "s";
        var onclick      = "birdhouse_createDayVideo('"+camera+"');";
        var create       =  "<div onclick=\""+onclick+"\" style=\"cursor:pointer\"><u>" + lang("CREATE_DAY") + ": " + app_data["WEATHER"]["current"]["date"] + "</u></div>";
        tab.style_rows["height"] = "25px";

        info_text += "&nbsp;";
	    info_text += tab.start();
	    info_text += tab.row("&nbsp;&nbsp;" + lang("CAMERA") + ":", "<b>" + camera.toUpperCase() + "</b> - " + cam_settings["name"]);
	    info_text += tab.row("&nbsp;&nbsp;" + lang("RECORDING_TIMES") + ":", lang("FROM_TO_EVERY", [record_from, record_to, rhythm]));
	    info_text += tab.row("&nbsp;&nbsp;" + lang("VIDEO") + ":", create );
	    info_text += tab.row("&nbsp;&nbsp;" + lang("THRESHOLD") + ":", threshold_slider );
	    info_text += tab.end();
	    info_text += "&nbsp;<br/>&nbsp;";

        html += birdhouse_OtherGroup( "info", lang("SETTINGS"), info_text, false );
	}
	// settings for admins - BACKUP
	if (admin && active_page == "TODAY" && active_date != "" && active_date != undefined) {

	    var info_text    = "";
        info_text += "&nbsp;";
	    info_text += tab.start();
	    info_text += tab.row("&nbsp;&nbsp;" );
	    info_text += tab.row("&nbsp;&nbsp;" + lang("THRESHOLD") + ":", threshold_slider );
	    info_text += tab.end();
	    info_text += "&nbsp;<br/>&nbsp;";

        html += birdhouse_OtherGroup("settings", lang("SETTINGS"), info_text, false );
	}

    // create chart data
    if (active_page == "TODAY_COMPLETE" || (active_page == "TODAY" && active_date != "" && active_date != undefined)) {
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
        chart    += birdhouseChart_weatherOverview(weather_data); // + "<br/>";

        if (active_page == "TODAY") {
            chart += "<hr/><div style='width:100%'>" + link_day_forward + " &nbsp; " + link_day_back + "</div><br/>&nbsp;";
            }
        else {
            chart += "<br/>&nbsp;";
            }
        html     += birdhouse_OtherGroup( "chart", lang("WEATHER"), chart, true );
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
			group_list.push(title);
			count_groups += 1;
        });
        if (html == "" && server_status["view_favorite_loading"] == "done") {
            html += "<center>&nbsp;<br/>"+lang("NO_ENTRIES")+"<br/>&nbsp;</center>";
        }
        else if (html == "") {
            html += "<center>&nbsp;<br/>"+lang("DATA_LOADING_TRY_AGAIN")+"<br/>&nbsp;</center>";
            appMsg.alert(lang("DATA_LOADING_TRY_AGAIN"));
            return false;
        }
        if (group_list.length > 0) {
            html += "<div id='group_list' style='display:none;'>" + group_list.join(" ") + "</div>";
        }
    }

	// today, backup, video
	else {
		entries_available = false;
		if (active_date != undefined && active_date != "") {
		    title = active_date.substring(6,8) + "." + active_date.substring(4,6) + "." + active_date.substring(0,4);
        }
        else if (title.length() == 8) {
            title = title.substring(6,8) + "." + title.substring(4,6) + "." + title.substring(0,4);
        }
        if (entries != undefined &&  Object.keys(entries).length > 0) {
            html += birdhouse_ImageGroup(title, entries, entry_count, entry_category, header_open, admin, video_short,
                                         same_img_size, max_image_size_LR);
			group_list.push(title);
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
    			appMsg.alert(lang("DATA_LOADING_TRY_AGAIN"));
    			return false;
   			    }
			}
        html += "<div id='group_list' style='display:none;'>" + group_list.join(" ") + "</div>";
		}

	// Set title
	if (active_page == "TODAY" && active_date != "")    {
	    var archive_title = "<span style='cursor:pointer' onclick='app_active_page=\"ARCHIVE\";birdhouseReloadView();'>";
	    archive_title    += "<u>" + lang("ARCHIVE") + "</u>";
	    archive_title    += "</span>";
	    page_title        = archive_title + " " + active_date.substring(6,8) + "." + active_date.substring(4,6) + "." + active_date.substring(0,4);
	    }
	else                                                { page_title = lang(active_page); }
	if (active_page == "TODAY" && active_date == "")    { page_status = "status_error_record_" + app_active_cam; }
	if (active_page == "TODAY_COMPLETE")                { page_status = "status_error_record_" + app_active_cam; }
	if (active_page != "FAVORITES")                     { page_title += "  (" + camera_settings[app_active_cam]["name"] + ")"; }

	birdhouse_frameHeader(page_title, page_status);
	setTextById(app_frame_content, html);
	}
