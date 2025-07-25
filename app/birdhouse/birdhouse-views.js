//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// birdhouse views
//--------------------------------------

/*
* create main index view with one or two video streams
*
* @param (dict) data: API response
* @param (string) camera: ID of active camera
* @param (boolean) object: object detection view (not in use at the moment)
*/
function birdhouse_INDEX(data, camera, object=false) {

	var html            = "";
    var html_no_entries = "<center>&nbsp;<br/>"+lang("NO_ENTRIES")+"<br/>&nbsp;<br/>&nbsp;<br/>&nbsp;</center>";
	var active_camera = camera;
	var cameras       = app_data["SETTINGS"]["devices"]["cameras"];
	var title         = app_data["SETTINGS"]["title"];
	var index_view    = app_data["SETTINGS"]["views"]["index"];
	var camera_status = app_data["STATUS"]["devices"]["cameras"];
	var object_detect = app_data["STATUS"]["object_detection"]["active"];
	var stream_server = RESTurl;
	var active_cam    = {};
	var other_cams    = [];
	var stream_ui1, stream_uid2 = "";
    var lowres_pos_cam1 = 0;

    if (app_birdhouse_closed && !app_admin_allowed) {
        var message = app_data["API"]["maintenance"]["message"].replaceAll("[br]", "<br/>");
        message = message.replaceAll("\n", "<br/>");
        if (message == "") { message = lang("CLOSED_DEFAULT_MSG"); }

        html += "&nbsp;<br/>&nbsp;<br/>";
        html += "<center><div class='closing-message'>";
        html += "<img src='" + app_loading_image + "' style='width:150px;'>";
        html += "<br/>&nbsp;";
        html += "<center><i>" + message + "</i></center>";
        html += "</div></center>";
        html += "<br/>&nbsp;";
        setTextById(app_frame.content, html);
        setTextById(app_frame.header, "<center><h2>" + title + "</h2></center>");
        setTextById(app_frame.index, "");
        return;
    }

	if (active_camera == "cam1" && index_view["lowres_pos_cam1"])       { lowres_position = index_view["lowres_pos_cam1"]; }
	else if (active_camera == "cam2" && index_view["lowres_pos_cam2"])  { lowres_position = index_view["lowres_pos_cam2"]; }
	else                                                                { lowres_position = index_view["lowres_position"]; }

    // if selected camera is not active, reset to use the first active camera
	if (active_camera != undefined && cameras[active_camera] && cameras[active_camera]["active"] == false) { active_camera = undefined; }

    // create streams from active cameras
	for (let key in cameras) {
	    console.log("---> birdhouse_INDEX: " + key + " / " + cameras[key]["active"])
	    if (cameras[key]["active"]) { //&& cameras[key]["status"]["error"] == false) {
    	    if (active_camera == undefined) { active_camera = key; }
            if (key == active_camera) {
                active_cam  = {
                    "name"        : key,
                    "stream"      : cameras[key]["video"]["stream"],
                    "description" : key.toUpperCase() + ": " + cameras[key]["name"],
                    "object"      : cameras[key]["object_detection"]["active"],
                    "error"       : camera_status[key]["error"]
                    }
                }
            else {
                var other_cam  = {
                    "name"        : key,
                    "stream"      : cameras[key]["video"]["stream"],
                    "description" : key.toUpperCase() + ": " + cameras[key]["name"],
                    "object"      : "",
                    "error"       : camera_status[key]["error"]
                    }
                other_cams.push(other_cam);
                }

            app_camera_source[key]                      = stream_server + cameras[key]["video"]["stream"];
            app_camera_source["lowres_" + key]          = stream_server + cameras[key]["video"]["stream_lowres"];
            app_camera_source["pip_" + key]             = stream_server + cameras[key]["video"]["stream_pip"];
            app_camera_source["detect_" + key]          = stream_server + cameras[key]["video"]["stream_detect"];
            app_camera_source["object_" + key]          = stream_server + cameras[key]["video"]["stream_object"];
            app_camera_source["detect_" + key + "_img"] = stream_server + cameras[key]["video"]["stream_detect"];
            app_camera_source["overlay_" + key]         = stream_server + cameras[key]["video"]["stream_detect"];
            }
		}

	if (active_cam == {} && other_cams != [])                   { active_cam = other_cams[0]; other_cams.shift(); }
	if (Object.keys(cameras).length == 0 || active_cam == {})   { html += html_no_entries; }
	if (other_cams.length == 1 && app_admin_allowed == false) {
	    if (other_cams[0]["error"])     { other_cams = []; }
	    else if (active_cam["error"])   { active_cam = other_cams[0]; other_cams = []; }
	}

    console.debug("---> birdhouse_INDEX: selected:" + camera + " / app_active:" + app_active.cam + " / view_active:" + active_camera +
                " / view:" + index_view["type"] + " / other:" + other_cams.length + " / admin: " + app_admin_allowed);
    console.debug(app_camera_source);

    if (active_cam != {} && active_cam["name"]) {
        var replace_tags = {};
        replace_tags["OFFLINE_URL"]     = app_error_connect_image;
        replace_tags["CAM1_ID"]         = active_camera;
        replace_tags["ACTIVE_BROOD"]    = diary_activeBrood();

        // ???? should be solved earlier, is just a workaround :-(
        if (app_camera_source[active_cam["name"]].indexOf("http:") > -1) {stream_server = "";};

        if (object) { replace_tags["CAM1_URL"]        = stream_server + app_camera_source["object_"+active_cam["name"]]; }
        else        { replace_tags["CAM1_URL"]        = stream_server + app_camera_source[active_cam["name"]]; }

        if (index_view["type"] != "picture-in-picture" || other_cams.length == 0) {
            if (object) { [replace_tags["CAM1_URL"], stream_uid1] = birdhouse_StreamURL(active_cam["name"], stream_server + app_camera_source["object_"+active_cam["name"]], "main", true, "INDEX #1"); }
            else        { [replace_tags["CAM1_URL"], stream_uid1] = birdhouse_StreamURL(active_cam["name"], stream_server + app_camera_source[active_cam["name"]], "main", true, "INDEX #2"); }
            }
        if (index_view["type"] == "picture-in-picture" && other_cams.length > 0) {
            [replace_tags["CAM1_PIP_URL"], stream_uid1] = birdhouse_StreamURL(other_cams[0]["name"], stream_server + cameras[active_cam["name"]]["video"]["stream_pip"], "main_pip", true, "INDEX #4");
            replace_tags["CAM1_PIP_URL"]  = replace_tags["CAM1_PIP_URL"].replace("{2nd-camera-key}", other_cams[0]["name"]);
            replace_tags["CAM1_PIP_URL"]  = replace_tags["CAM1_PIP_URL"].replace("{2nd-camera-pos}", lowres_position);
        }
        if (index_view["type"] != "picture-in-picture" && other_cams.length > 0) {
            replace_tags["CAM2_ID"]         = other_cams[0]["name"];
            [replace_tags["CAM2_LOWRES_URL"], stream_uid2] = birdhouse_StreamURL(other_cams[0]["name"], stream_server + cameras[other_cams[0]["name"]]["video"]["stream_lowres"], "2nd_lowres", true, "INDEX #5");
            replace_tags["CAM2_LOWRES_POS"] = index_lowres_position[lowres_position.toString()];
        }

        var selected_view = "";
        if (Object.keys(cameras).length == 1 || other_cams.length == 0)         { selected_view = "single"; }
        else if (index_template[index_view["type"]])                            { selected_view = index_view["type"]; }
        else                                                                    { selected_view = "default"; }
        if (app_admin_allowed)                                                  { selected_view += "_admin"; }

        html += index_template[selected_view];
        html += index_template["offline"];

        if (app_admin_allowed)  { html  = html.replace("<!--ADMIN-->", index_template["admin"]); }

        if (object) {
            object_command = "birdhouse_INDEX(app_data, '"+active_camera+"', false);";
            object_command += "birdhouse_killStream('"+replace_tags["CAM1_ID"]+"', '"+stream_uid1+"');";
            if (replace_tags["CAM2_ID"]) { object_command += "birdhouse_killStream('"+replace_tags["CAM2_ID"]+"', '"+stream_uid2+"');"; }
            replace_tags["OBJECT"] = object_command;
            replace_tags["OBJECT_BUTTON"] = "OFF";
            }
        else {
            object_command = "birdhouse_INDEX(app_data, '"+active_camera+"', true);"
            object_command += "birdhouse_killStream('"+replace_tags["CAM1_ID"]+"', '"+stream_uid1+"');";
            if (replace_tags["CAM2_ID"]) { object_command += "birdhouse_killStream('"+replace_tags["CAM2_ID"]+"', '"+stream_uid2+"');"; }
            replace_tags["OBJECT"] = object_command;
            replace_tags["OBJECT_BUTTON"] = "ON";
            }

        Object.keys(replace_tags).forEach( key => {
            html = html.replaceAll("<!--"+key+"-->", replace_tags[key]);
        });
        }
    else {
        html = "<br/><br/><br/><center><img src='"+app_loading_image+"' width='250'><br/>&nbsp;<br/><i>"+lang("NO_ACTIVE_CAMERA")+"</i></center><br/><br/><br/>";
        }

	setTextById(app_frame.content, html);
	setTextById(app_frame.header, "<center><h2>" + title + "</h2></center>");

	if (active_cam["object"] && object_detect && selected_view != "picture-in-picture") {
	    elementVisible("button_object_detection");
        if (object)  {
            elementHidden("show_stream_fps_"+replace_tags["CAM1_ID"]);
            elementVisible("show_stream_object_fps_"+replace_tags["CAM1_ID"]);
            }
        else  {
            elementVisible("show_stream_fps_"+replace_tags["CAM1_ID"]);
            elementHidden("show_stream_object_fps_"+replace_tags["CAM1_ID"]);
            }
	    }

    if (other_cams.length == 0)                                { elementHidden("admin_status_index"); }
    if (!cameras[active_camera]["video"]["allow_recording"])   { elementHidden("admin_record_index"); }
}

/*
* coordinate list view creation for all lists (today, today complete, favorites, videos, object detection, ...)
*
* @param (string) page: page to be displayed
* @param (dict) data: API response for list specific request
* @param (string) camera: ID of active camera
* @param (boolean) header_open: set if group header should be open
*/
function birdhouse_LIST(page, data, camera, header_open=true) {

    if (page == "FAVORITES" && birdhouseStatus_loadingViews(app_data, "favorite") != "done") { appMsg.alert(lang("DATA_LOADING_TRY_AGAIN")); return false; }
    if (page == "ARCHIVE"   && birdhouseStatus_loadingViews(app_data, "archive") != "done")  { appMsg.alert(lang("DATA_LOADING_TRY_AGAIN")); return false; }
    if (page == "OBJECTS"   && birdhouseStatus_loadingViews(app_data, "object") != "done")   { appMsg.alert(lang("DATA_LOADING_TRY_AGAIN")); return false; }

	var html              = "";
	var title             = lang(page);
	var html_no_entries   = "<center>&nbsp;<br/>"+lang("NO_ENTRIES")+"<br/>&nbsp;<br/>&nbsp;<br/>&nbsp;</center>";
	var entry_category    = [];
	var same_img_size     = false;
	var data_list         = data["DATA"];
	var status_data       = app_data["STATUS"]["devices"]["cameras"][camera];

	var active_page       = data_list["active"]["active_page"];
	var entries           = data_list["data"]["entries"];
	var entries_yesterday = data_list["data"]["entries_yesterday"];
	var entries_delete    = data_list["data"]["entries_delete"];
	var entries_favorite  = data_list["data"]["entries_favorites"];
	var groups            = data_list["data"]["groups"];
	var entry_count       = data_list["view"]["view_count"];
	var selected_label    = data_list["view"]["label"];
	var archive_exists    = data_list["view"]["archive_exists"];
	var camera_settings   = app_data["SETTINGS"]["devices"]["cameras"];

	var group_list        = [];
	var tab               = new birdhouse_table();
	tab.style_cells["vertical-align"] = "top";
	tab.style_cells["padding"] = "3px";

	if (data_list["view"]["max_image_size"]) {
        var max_image_size_LR  = data_list["view"]["max_image_size"]["lowres"];
        var max_image_size_HR  = data_list["view"]["max_image_size"]["hires"];
        }
    else {
        var max_image_size_LR  = 0;
        var max_image_size_HR  = 0;
        }

	var active_page       = app_active.page;
	var active_date       = data_list["active"]["active_date"];
	var server_status     = app_data["STATUS"]["server"];
	var video_short       = true;
	var page_title        = "";
	var page_status       = "";

	if (active_page == "VIDEOS")                           { entry_category = [ "video" ]; }
	else if (active_page == "TODAY" && active_date == "")  { entry_category = [ "today" ]; }
	else if (active_page == "TODAY" && active_date != "")  { entry_category = [ "backup", active_date ]; }

    console.log("---> birdhouse_LIST: " + active_page + " / " + camera + " / " + active_date);

    // complete list of images from today
    if (active_page == "TODAY_COMPLETE") {
        same_img_size = true;
        if (app_admin_allowed) { html += birdhouse_LIST_admin_today_complete(data, app_admin_allowed, camera, active_page, active_date); }
        html += "<div class='weather_chart'>";
        html += birdhouse_LIST_chart_weather(data, active_page, camera);
        html += "</div>";
        html += birdhouse_LIST_label(entries, active_page);
        }

    // short list of images from today
    else if (active_page == "TODAY" && (active_date == "" || active_date == undefined)) {
        same_img_size = true;
        html += birdhouse_LIST_label(entries, active_page);
        }

    // images from an archived day
    else if (active_page == "TODAY") {
        same_img_size = true;
        if (app_admin_allowed) { html += birdhouse_LIST_admin_archive(data, app_admin_allowed, camera, active_page, active_date); }
        html += birdhouse_LIST_chart_weather(data, active_page, camera);
        html += birdhouse_LIST_label(entries, active_page);
        }

    // overview of archived days
    else if (active_page == "ARCHIVE" && (active_date == "" || active_date == undefined)) {
        if (app_admin_allowed) { html += birdhouse_LIST_admin_archive_overview(data, app_admin_allowed, camera, active_page, active_date); }
        html += birdhouse_LIST_calendar(groups);
        }

    // all images marked as favorite
    else if (active_page == "FAVORITES") {
        if (groups != undefined) { groups = birdhouse_LIST_favorite_groups(groups); }
        html += birdhouse_LIST_label(entries, active_page);
        }

    // all videos
    else if (active_page == "VIDEOS") {
        // show calendar for videos
        html += birdhouse_LIST_calendar(groups);

        // check if a date is given to open the respective image group
        var open_video_group = "";
        if (data["API"]["request_param"]["parameter"][0]) {
            open_video_date  = data["API"]["request_param"]["parameter"][0];
            open_video_group = open_video_date.substring(0,4) + "-" + open_video_date.substring(4,6);
            }
    }

    // load images for detail view with swipe feature
    if (entries) {
        var overloadImageKeys    = Object.keys(entries).sort().reverse();
        var overloadImageEntries = Object.assign({}, entries);

        // include images from favorites group
        if (entries_favorite && Object.keys(entries_favorite).length > 0) {

            overloadImageKeys = Object.keys(entries_favorite).sort().reverse();
            var keys = Object.keys(entries).sort().reverse();
            var keys2 = overloadImageKeys.concat(keys);
            overloadImageKeys = keys2;
            group_list.push("TODAY_FAVORITE")

            for (var key in entries_favorite) { overloadImageEntries[key] = entries_favorite[key]; }
            }
        birdhouse_overlayLoadImages(overloadImageKeys, overloadImageEntries, app_active.page, app_admin_allowed);
        }

	// list today complete, favorites -> list in monthly or hourly groups
	if (groups != undefined && groups != {}) {
		var count_groups = 0;
		var favorites = false;

        // include favorites if exist
        if (entries_favorite && Object.keys(entries_favorite).length > 0) {
            var favorites_open = true;
            if (open_video_group != "") { favorites_open = false; }

            html += birdhouse_ImageGroup(active_page+"_FAVORITE", lang("FAVORITES"), entries_favorite, ["all"], entry_category,
                                         favorites_open, app_admin_allowed, video_short, same_img_size, max_image_size_LR);
            entries_available = true;
            favorites = true;
            group_list.push(lang("FAVORITES"));
            }

        Object.keys(groups).sort().reverse().forEach( group => {

			var title = group;
			var group_entries = {};
			for (i=0;i<groups[group].length;i++) {
				key                = groups[group][i];
				group_entries[key] = entries[key];
            }
			delete group_entries["999999"];

            // set which groups to start open
			if (active_page == "ARCHIVE") {
				title = lang("ARCHIVE") + " &nbsp; (" + group + ")";
				if (count_groups > 0) { header_open = false; }
            }
            else if (active_page == "VIDEOS" && favorites) {
                if (open_video_group == "" || open_video_group != title) { header_open = false; }
                else                                                     { header_open = true; }
            }

			html += birdhouse_ImageGroup(active_page + "_" + group, title, group_entries, entry_count, entry_category,
			                             header_open, app_admin_allowed,
			                             video_short, same_img_size, max_image_size_LR);

			if (active_page == "TODAY_COMPLETE") {
			    title = "TODAY_COMPLETE_" + title;
			    }
			group_list.push(title);
			count_groups += 1;
        });
        if (html == "" && server_status["view_favorite_loading"] == "done") {
            html += html_no_entries;
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

	// list today, backup, or videos
	else {
		entries_available = false;

        // include favorites and videos if exist
        if (entries_favorite && Object.keys(entries_favorite).length > 0) {
            html += birdhouse_ImageGroup(active_page+"_FAVORITE", lang("FAVORITES_VIDEOS"), entries_favorite, ["all"], entry_category, true,
                                         app_admin_allowed, video_short, same_img_size, max_image_size_LR);
            entries_available = true;
            }

		// set group title
		if (active_date != undefined && active_date != "")  { title = active_date.substring(6,8) + "." + active_date.substring(4,6) + "." + active_date.substring(0,4); }
        else if (title.length == 8)                         { title = title.substring(6,8) + "." + title.substring(4,6) + "." + title.substring(0,4); }

        // create image group (if no specific groups are defined)
        if (entries != undefined &&  Object.keys(entries).length > 0) {
            html += birdhouse_ImageGroup(title, title, entries, entry_count, entry_category, header_open, app_admin_allowed, video_short, same_img_size, max_image_size_LR);
			group_list.push(title);
            entries_available = true;
            }

        // check if no entries or still loading
		if (entries_available == false && (active_page == "TODAY" || active_page == "ARCHIVE" || active_page == "FAVORITES")) {
		    var empty = false;
		    if (active_page == "FAVORITES" && server_status["view_favorite_loading"] == "done")                         { empty = true; }
		    else if (active_page == "TODAY" && server_status["view_archive_loading"] == "done")                         { empty = true; }
		    else if (active_page == "ARCHIVE" && active_date != "" && server_status["view_archive_loading"] == "done")  { empty = true; }
   			else {
   			    var progress_info = "";
   			    if (active_page == "FAVORITES") { progress_info = "<i><div id='loading_status_favorite'></div></i>"; }
   			    if (active_page == "TODAY")     { progress_info = "<i><div id='loading_status_archive'></div></i>"; }
   			    if (active_page == "ARCHIVE")   { progress_info = "<i><div id='loading_status_archive'></div></i>"; }
    			appMsg.alert(lang("DATA_LOADING_TRY_AGAIN") + "<br/>" + progress_info + ".." + active_date);
    			return false;
   			    }
   	    	if (empty) { html += html_no_entries; }
            }
		if (entries_available == false && active_page == "VIDEOS") {

   	    	html += html_no_entries;
   	    	}

        html += "<div id='group_list' style='display:none;'>" + group_list.join(" ") + "</div>";
		}

    if (app_admin_allowed) {
        if (entries_yesterday != undefined && Object.keys(entries_yesterday).length > 0) {
            html += birdhouse_ImageGroup(active_page+"_YESTERDAY",lang("YESTERDAY"), entries_yesterday, entry_count, entry_category,
                                         false, app_admin_allowed, video_short, same_img_size, max_image_size_LR);
            entries_available = true;
            }
        if (entries_delete != undefined && Object.keys(entries_delete).length > 0) {
            html += birdhouse_ImageGroup(active_page+"_RECYCLE", lang("RECYCLE"), entries_delete, ["recycle"], entry_category, false,
                                         app_admin_allowed, video_short, same_img_size, max_image_size_LR);
            entries_available = true;
            }
        }

	// Set title
	if (active_page == "TODAY" && active_date != "")    {
	    var archive_title = "<span style='cursor:pointer' onclick='birdhousePrint_page(\"ARCHIVE\");'>";
	    archive_title    += "<u>" + lang("ARCHIVE") + "</u>";
	    archive_title    += "</span>";
	    page_title        = archive_title + " " + active_date.substring(6,8) + "." + active_date.substring(4,6) + "." + active_date.substring(0,4);
	    }
	else                                                        { page_title = lang(active_page); }
	if (active_page == "TODAY" && active_date == "")            { page_status = "status_error_record_" + app_active.cam; }
	if (active_page == "TODAY_COMPLETE")                        { page_status = "status_error_record_" + app_active.cam; }
	if (active_page != "FAVORITES" && active_page != "VIDEOS")  { page_title += "  (" + camera_settings[app_active.cam]["name"] + ")"; }


	if (active_page == "TODAY" && active_date != "")    {
        var data_list         = data["DATA"];
        var link_day_back      = "";
        var link_day_forward   = "";
        if (data_list["data"]["day_back"] != "")    {
            var onclick_back    = "birdhousePrint_page(page=\"TODAY\", cam=\""+camera+"\", date=\""+data_list["data"]["day_back"]+"\");";
            page_title         += "<span onclick='" + onclick_back + "' style='float:left;cursor:pointer;' title='"+lang("DAY_BACK")+"'>&#171;</span>";
            }
        if (data_list["data"]["day_forward"] != "") {
            var onclick_forward = "birdhousePrint_page(page=\"TODAY\", cam=\""+camera+"\", date=\""+data_list["data"]["day_forward"]+"\");";
            page_title         += "<span onclick='" + onclick_forward + "' style='float:right;cursor:pointer;' title='"+lang("DAY_FORWARD")+"'>&#187;</span>";
            }
    }

	birdhouse_frameHeader(page_title, page_status);
	setTextById(app_frame.content, html);

	if ((active_page == "FAVORITES" || active_page == "TODAY") && selected_label != undefined) {
        selected_label = selected_label.replaceAll("%20", " ");

        if (active_page == "FAVORITES") { var prefix = "FAVORITES_"}
        else                            { var prefix = "";
        }
	    birdhouse_view_images_objects(selected_label);
	    birdhouse_labels_highlight(selected_label);
	    }
	}


/*
* create admin functionalities for the archive view of a specific day
*
* @param (dict) data: API response for list specific request
* @param (boolean) admin: logged in as admin
* @param (string) camera: ID of active camera
* @param (string) active page: currently active page
* @param (string) active date: currently active date
* @returns (string): html with admin functionality for archive view
*/
function birdhouse_LIST_admin_archive(data, admin, camera, active_page, active_date) {
    var html                    = "";
    var info_text               = "";
    var threshold_slider        = birdhouse_LIST_admin_threshold_slider(camera, active_page, active_date);
	var camera_settings         = app_data["SETTINGS"]["devices"]["cameras"];
	var archive_info            = data["DATA"]["data"]["info"];

    // <button onclick='birdhouse_forceBackup();' class='button-settings-api'>Force Backup</button>";
    var detection_model         = camera_settings[app_active.cam]["object_detection"]["model"]; // devices:cameras:"+camera+":object_detection:model
    var detection_threshold     = camera_settings[app_active.cam]["object_detection"]["threshold"];
    var detection_date          = active_date.substring(6,8) + "." + active_date.substring(4,6) + "." + active_date.substring(0,4);
    var object_onclick          = "birdhouse_recycleObject(\"backup\", \""+active_date+"\", 1, \""+app_active.cam+"\");";
    object_onclick             += "setTimeout(function(){ birdhouseReloadView(); }, 1000);"

    var button_object_detection = "<button onclick='birdhouse_archiveObjectDetection(\""+app_active.cam+"\",\""+active_date+"\", \""+detection_date+"\", \"\", \"selection_threshold\");' class='bh-slider-button'  style='width:80px;'>Start</button>";
    var button_object_detection_rm = "<button onclick='birdhouse_archiveRemoveObjectDetection(\""+app_active.cam+"\",\""+active_date+"\", \""+detection_date+"\");' class='bh-slider-button'  style='width:80px;'>Remove</button>";
    var button_archive_deletion = "<button onclick='birdhouse_archiveDayDelete(\""+active_date+"\", \""+detection_date+"\");' class='bh-slider-button' style='width:80px;'>Delete</button>";
    var button_archive_download = "<button onclick='archivDownload_requestDay(\""+active_date+"\", \""+app_active.cam+"\");' class='bh-slider-button' style='width:80px;'>"+lang("DOWNLOAD")+"</button>";
    var button_object_recycle   = "<button onclick='"+object_onclick+"' class='bh-slider-button'  style='width:80px;'>Recycle</button>";

    var buttons_download_collection = "<div style='width:100%;float:left;'><button onclick='collect4download_activate();'  class='bh-slider-button' style='width:80px;'>"+lang("DOWNLOAD_START_COLLECTING")+"</button>";
    buttons_download_collection    += "<button onclick='collect4download_deactivate();' class='bh-slider-button' style='width:80px;'>"+lang("DOWNLOAD_STOP_COLLECTING")+"</button>";
    buttons_download_collection    += "<button onclick='archivDownload_requestList();' class='bh-slider-button' style='width:80px;'>"+lang("DOWNLOAD")+"</button></div><br/>";
    buttons_download_collection    += "<div style='width:100%;float:left;'>&nbsp;<br/>" + lang("COLLECTED_IMAGES") +": <text id='collect4download_amount'>0</text> " + lang("IMAGES") + "</div>";

    var available_thresholds = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95];
    var select_thresholds = "<select id='selection_threshold' style='height:30px;width:60px;float:left;margin:3px;'>";
    for (var i=0;i<available_thresholds.length;i++) {
        var this_selected = "";
        if (available_thresholds[i]*1 == detection_threshold*1 ) { this_selected = "selected"; }
        select_thresholds += "<option value='" + available_thresholds[i] + "' " + this_selected + ">" + available_thresholds[i] + "%</option>";
    }
    select_thresholds += "</select>&nbsp;";

    var detection_info = "";
    if (archive_info && archive_info["detection_"+camera]) {
        detection_info += "<div style='float:left;padding:3px;'>";
        detection_info += lang("LAST_DETECTION") + ": <br/>" + archive_info["detection_"+camera]["date"] + " (" + archive_info["detection_"+camera]["model"] + ")";
        detection_info += "</div>";
        }

	var tab = new birdhouse_table();
	tab.style_cells["vertical-align"] = "top";
	tab.style_cells["padding"] = "3px";

    info_text += "&nbsp;";
    info_text += tab.start();
    info_text += tab.row("");
    info_text += tab.row(lang("THRESHOLD_FOR_ARCHIVE") + ":", threshold_slider );
    if (app_data["SETTINGS"]["server"]["detection_active"]) {
        if (!camera_settings[app_active.cam]["object_detection"]["active"])
            { button_object_detection = lang("DETECTION_INACTIVE_CAM"); }
        else if (!app_data["STATUS"]["object_detection"]["models_loaded_status"][app_active.cam])
            { button_object_detection = lang("DETECTION_NOT_LOADED"); }
        info_text += tab.row(lang("OBJECT_DETECTION_FOR_ARCHIVE", [detection_model, detection_threshold]) + ":",
                             select_thresholds + button_object_detection + detection_info );
        }
    info_text += tab.row(lang("OBJECT_DETECTION_REMOVE") + ":", button_object_detection_rm);
    info_text += tab.row(lang("OBJECT_DETECTION_RECYCLE") + ":", button_object_recycle);
    info_text += tab.row(lang("DELETE_ARCHIVE") + ":", button_archive_deletion );
    info_text += tab.row(lang("DOWNLOAD_ARCHIVE") + ":", button_archive_download );
    info_text += tab.row(lang("DOWNLOAD_ARCHIVE_COLLECT") + ":", buttons_download_collection );
    info_text += tab.end();
    info_text += "&nbsp;<br/>&nbsp;";

    html += birdhouse_OtherGroup("settings", lang("SETTINGS"), info_text, false, "settings" );
    return html;
}

/*
* create admin functionalities for the archive overview
*
* @param (dict) data: API response for list specific request
* @param (boolean) admin: logged in as admin
* @param (string) camera: ID of active camera
* @param (string) active page: currently active page
* @param (string) active date: currently active date
* @returns (string): html with admin functionality for archive view
*/
function birdhouse_LIST_admin_archive_overview(data, admin, camera, active_page, active_date) {

    var html    = "";
    var tab     = new birdhouse_table();
    tab.style_cells["vertical-align"] = "top";
    tab.style_cells["padding"] = "3px";

    var info_text = "";
    info_text += "&nbsp;";
    info_text += tab.start();

    if (app_data["SETTINGS"]["server"]["detection_active"] == true) {

        var data_list         = data["DATA"];
        var entries           = data_list["data"]["entries"];
        var camera_settings   = app_data["SETTINGS"]["devices"]["cameras"];

        var detection_model      = camera_settings[app_active.cam]["object_detection"]["model"]; // devices:cameras:"+camera+":object_detection:model
        var detection_threshold  = camera_settings[app_active.cam]["object_detection"]["threshold"];
        var detection_date       = active_date.substring(6,8) + "." + active_date.substring(4,6) + "." + active_date.substring(0,4);
        var available_thresholds = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95];

        var select_thresholds = "<select id='selection_threshold' style='width:180px;'>";
        for (var i=0;i<available_thresholds.length;i++) {
            var this_selected = "";
            if (available_thresholds[i]*1 == detection_threshold*1 ) { this_selected = "selected"; }
            select_thresholds += "<option value='" + available_thresholds[i] + "' " + this_selected + ">" + available_thresholds[i] + "%</option>";
        }
        select_thresholds += "</select><br/>&nbsp;";
        var select_object_detection = "<select id='selection_dates' multiple style='width:180px;height:100px;'>";
        if (entries) {
            Object.entries(entries).forEach(([key,value]) => {
                var date = key.substring(6,8) + "." + key.substring(4,6) + "." + key.substring(0,4);
                var detection = "";
                if (value["detection"]) { detection = "; D";}
                select_object_detection += "<option value='"+key+"_"+value["count_cam"]+"'>" + date + " (" + value["count_cam"] + " " + lang("IMAGES") + detection + ")</option>";
                });
            }
        select_object_detection += "</select>";

        var button_object_detection = "<button onclick='birdhouse_archiveObjectDetection(\""+app_active.cam+"\",\""+active_date+"\", \"\", \"selection_dates\", \"selection_threshold\");' class='bh-slider-button'  style='width:80px;'>Start</button>";

        var detection_key = lang("OBJECT_DETECTION_FOR_ARCHIVES", [detection_model, detection_threshold]) + ":";

        if (!camera_settings[app_active.cam]["object_detection"]["active"]) {
            detection_key           = lang("OBJECT_DETECTION") + ":";
            button_object_detection = "";
            select_object_detection = "";
            select_thresholds       = lang("DETECTION_INACTIVE_CAM");
            }
        else if (!app_data["STATUS"]["object_detection"]["models_loaded_status"][app_active.cam]) {
            detection_key           = lang("OBJECT_DETECTION") + ":";
            button_object_detection = "";
            select_object_detection = "";
            select_thresholds       = lang("DETECTION_NOT_LOADED");
            }

        info_text += tab.row(detection_key,
                             select_thresholds + "<br/>" + select_object_detection + "<br/>&nbsp;<br/>" + button_object_detection );
        }

    info_text += tab.row(lang("UPDATE_VIEWS")+":",
                         "<button onclick='birdhouse_forceUpdateViews(\"archive\");' class='bh-slider-button' style='width:80px;'>Update</button>&nbsp;" +
                         "<button onclick='birdhouse_forceUpdateViews(\"archive\", true);' class='bh-slider-button' style='width:80px;'>Complete</button>");
    info_text += tab.end();
    info_text += "&nbsp;<br/>&nbsp;";

    html += birdhouse_OtherGroup( "info", lang("SETTINGS"), info_text, false, "settings" );
    return html;
}

/*
* create admin functionalities for the today_complete view
*
* @param (dict) data: API response for list specific request
* @param (boolean) admin: logged in as admin
* @param (string) camera: ID of active camera
* @param (string) active page: currently active page
* @param (string) active date: currently active date
* @returns (string): html with admin functionality for the today_complete view
*/
function birdhouse_LIST_admin_today_complete(data, admin, camera, active_page, active_date) {

    var html              = "";
    var info_text         = "";
    var threshold_slider  = birdhouse_LIST_admin_threshold_slider(camera, active_page, active_date);

	var status_data       = app_data["STATUS"]["devices"]["cameras"][camera];
	var camera_settings   = app_data["SETTINGS"]["devices"]["cameras"];
	var current_date      = app_data["STATUS"]["weather"]["current"]["date"];

    var cam_settings      = camera_settings[camera];
    var record_from       = status_data["record_image_start"];
    var record_to         = status_data["record_image_end"];
    var rhythm            = cam_settings["image_save"]["rhythm"] + "s";

	var tab = new birdhouse_table();
	tab.style_cells["vertical-align"] = "top";
	tab.style_cells["padding"] = "3px";
    tab.style_rows["height"] = "25px";

    info_text += "&nbsp;";
    info_text += tab.start();
    info_text += tab.row(lang("CAMERA") + ":", "<b>" + camera.toUpperCase() + "</b> - " + cam_settings["name"]);
    info_text += tab.row(lang("RECORDING_TIMES") + ":", lang("FROM_TO_EVERY", [record_from, record_to, rhythm]));
    info_text += tab.row(lang("THRESHOLD_ADJUST") + ":", threshold_slider );
    info_text += tab.row(lang("CREATE_DAY") + " (" + current_date + "/"+camera+"):",
                         "<button onclick='birdhouse_createDayVideo(\""+camera+"\");' class='bh-slider-button' style='width:100px'>"+lang("START")+"</button>" );
    info_text += tab.row(lang("FORCE_BACKUP") + ":",
                         "<button onclick='birdhouse_forceBackup();' class='bh-slider-button' style='width:100px'>"+lang("START")+"</button>" );
    info_text += tab.row(lang("RECREATE_IMG_CONFIG") + ":",
                         "<button onclick='birdhouse_recreateImageConfig();' class='bh-slider-button' style='width:100px'>"+lang("START")+"</button>" );
    info_text += tab.end();
    info_text += "&nbsp;<br/>&nbsp;";

    html += birdhouse_OtherGroup( "info", lang("SETTINGS"), info_text, false, "settings" );
    return html;
}

/*
* create slider to tryout and set the similarity detection threshold as one admin functionality in some views
*
* @param (string) camera: ID of active camera
* @param (string) active page: currently active page
* @param (string) active date: currently active date
* @returns (string): html with slider
*/
function birdhouse_LIST_admin_threshold_slider(camera, active_page, active_date) {

	var camera_settings     = app_data["SETTINGS"]["devices"]["cameras"];
    var cam_settings        = camera_settings[camera];

    var threshold_slider_onchange   = "document.getElementById(\"set_threshold_"+app_active.cam+"\").value=this.value;";
    var threshold_input_onchange    = "document.getElementById(\"threshold_slider_"+app_active.cam+"\").value=this.value;";
    var threshold_initial_value     = cam_settings["similarity"]["threshold"];
    var threshold_onclick_try       = "birdhouse_view_images_threshold(document.getElementById(\"set_threshold_"+app_active.cam+"\").value);";

    if (active_page == "TODAY_COMPLETE") {
        var threshold_onclick_set       = "birdhouse_edit_send(\"set_threshold_"+app_active.cam+"\",\""+app_active.cam+"\");";
        threshold_onclick_set          += "birdhouseReloadView();";
        var threshold_onclick_set_cmd   = "Save";
        }
    else {
        var threshold_onclick_set       = "alert(\"Not implemented yet.\");";
        var threshold_onclick_set       = "current_threshold = document.getElementById(\"set_threshold_"+app_active.cam+"\").value;"
        threshold_onclick_set          += "birdhouse_recycleThreshold(\"backup\", \""+active_date+"\", current_threshold, 1, \""+app_active.cam+"\");";
        var threshold_onclick_set_cmd   = "Recycle";
    }

    var threshold_onclick_reset     = "document.getElementById(\"threshold_slider_"+app_active.cam+"\").value = "+threshold_initial_value+";";
    threshold_onclick_reset        += "document.getElementById(\"set_threshold_"+app_active.cam+"\").value = "+threshold_initial_value+";";
    threshold_onclick_reset        += "birdhouse_view_images_threshold(100);";

    var threshold_slider        = "<div style='float:left;'><input type='range' id='threshold_slider_"+app_active.cam+"' onchange='"+threshold_slider_onchange+"' class='bh-slider' style='width:80%;' min='0' max='100' value='"+threshold_initial_value+"'>";
    threshold_slider           += "<input id='set_threshold_"+app_active.cam+"' class='bh-slider-value' style='width:10%;' onchange='"+threshold_input_onchange+"' value='"+threshold_initial_value+"'>";
    threshold_slider           += "<input id='set_threshold_"+app_active.cam+"_data' style='display:none;' value='devices:cameras:"+app_active.cam+":similarity:threshold'>";
    threshold_slider           += "<input id='set_threshold_"+app_active.cam+"_data_type' style='display:none;' value='float'></div>";
    threshold_slider           += "<div style='float:left;'><button class='bh-slider-button' onclick='"+threshold_onclick_try+"' style='float:none;'>Try</button>";
    threshold_slider           += "<button class='bh-slider-button' onclick='"+threshold_onclick_reset+"' style='float:none;'>Reset</button>";
    threshold_slider           += "<button class='bh-slider-button' onclick='"+threshold_onclick_set+"' style='float:none;'>"+threshold_onclick_set_cmd+"</button></div>";
    threshold_slider           += "<br/>&nbsp;<div id='threshold-info'>&nbsp;</div>";

    setTimeout(function(){ birdhouse_view_images_threshold(100);}, 500);
    return threshold_slider;
}

/*
* create a group with all available years and months for direct access; the click on a month opens the
* respective month and closes all the other. The calender starts opened when more than two month exists.
*
* @param (string) camera: ID of active camera
* @param (string) active page: currently active page
* @param (string) active date: currently active date
* @returns (string): html with calendar
*/
function birdhouse_LIST_calendar(groups) {

    var html = "";
    var group_html = "";
    var dates = {};
    var years = [];
    var calendar_icon = "&#x1F5D3;&#xFE0F;";
	var tab = new birdhouse_table();
	tab.style_cells["vertical-align"] = "top";
	tab.style_cells["padding"] = "3px";

    if (!groups) { return html; }

    Object.keys(groups).sort().reverse().forEach( group => {
        [year, month] = group.split("-");
        if (!dates[year]) { dates[year] = []; years.push(year); }
        dates[year].push(month);
    });

    var close_all = "";
    var count = 0;
    html += tab.start();
    for (var j=0;j<years.length;j++) {
        var year = years[j];
        var cell_1 = "<h1>" + calendar_icon + " " + year + "</h1>";
        var cell_2 = "";

        for (var i=0;i<dates[year].length;i++) {
            var onclick = "<!--CLOSE_ALL-->; birdhouse_groupToggle(\""+app_active.page+"_" +year + "-" + dates[year][i] +"\", true);"
            close_all += "birdhouse_groupToggle(\""+app_active.page+"_" +year + "-" + dates[year][i] +"\", false);"
            cell_2 += "<div class='other_label' onclick='"+onclick+"'>&nbsp;&nbsp;" + year + "-" + dates[year][i] + "&nbsp;&nbsp;</div>";
            count += 1;
            }
        html += tab.row(cell_1, cell_2);
        }
    var header_open = false;
    if (count > 2) { header_open = true; }
    html += tab.end();
    html += "<br/>&nbsp;<br/>";
    html = html.replaceAll("<!--CLOSE_ALL-->", close_all);
    group_html = birdhouse_OtherGroup("archive_calendar", lang("CALENDAR"), html, header_open);

    return group_html;
}

/*
* create a weather chart for different views (incl. last day / next day for archive view)
*
* @param (dict) data: API response for list specific request
* @param (string) active page: currently active page
* @param (string) camera: ID of active camera
* @returns (string): html with weather chart
*/
function birdhouse_LIST_chart_weather(data, active_page, camera) {
    var html = "";
    var chart_titles = [];

	var data_list         = data["DATA"];
	var weather_data      = data_list["data"]["weather_data"];
	var chart_data        = data_list["data"]["chart_data"];
	var sensors           = app_data["SETTINGS"]["devices"]["sensors"];

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
    var chart = birdhouseChart_create(label="", titles=chart_titles,
                                      data=chart_data["data"],
                                      type="line",
                                      sort_keys=true,
                                      id="weather_chart",
                                      size="", set_colors=[],
                                      set_menu="right"
                                      );
    chart    += birdhouseWeather_OverviewChart(weather_data); // + "<br/>";

    if (chartJS_loaded) {
        chart += "<br/>&nbsp;";
        html  += birdhouse_OtherGroup( "chart", lang("WEATHER"), chart, false );
        }
    else {
        var chart = birdhouseWeather_OverviewChart(weather_data);
        chart += "<br/>&nbsp;";
        html  += birdhouse_OtherGroup( "chart", lang("WEATHER") + " " + lang("NO_INTERNET_CHART"), chart, false );
        }
    return html;
}

/*
* create list of groups for favorite view  in the format MM.YYYY instead out of YYYY-MM
*
* @param (array) groups: list of groups in american format
* @returns (array): list of adapted groups
*/
function birdhouse_LIST_favorite_groups(groups) {
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
    return groups2;
}

/*
* create a list of labels for detected objects, where a click on the label shows the respective images with
* those objects and opens all groups, where those images are in
*
* @param (dict) entries: all images entries of the current view
* @param (string) active page: currently active page
* @param (boolean) empty: show label for images without detected objects (empty)
* @returns (string): html with list of labels
*/
function birdhouse_LIST_label(entries, active_page, empty=true) {
    var html = "";
    var video = false;
    var prefix = "";
    var count_labels = 0;
    if (active_page == "FAVORITES") { prefix = "FAVORITES_"; }

    if (entries != undefined &&  Object.keys(entries).length > 0) {
        var labels = {};
        var video_added = false;
        var label_information = "";
        var label_keys = [];

        // identify detected objects in the images
        Object.entries(entries).forEach(([key, value]) => {
            if (value["detections"]) {
                for (var i=0;i<value["detections"].length;i++) {
                    label = value["detections"][i]["label"];
                    label = label.replace(/^\s+/, '');
                    if (label == "") { label = "without-label"; }
                    if (!labels[label]) { labels[label] = []; }
                    labels[label].push(key);
                    count_labels += 1;
                    }
                }
            if (active_page == "FAVORITES" && value["type"] == "video") {
                video = true;
                label_keys.push("video");
                count_labels += 1;
                }
            });

        // create labels
        Object.entries(labels).sort().forEach(([key, value]) => {
            console.debug("     - " + key + ": " + value.length);
            var onclick = "birdhouse_view_images_objects(\""+key+"\"); birdhouse_labels_highlight(\""+key+"\", \"label_key_list\");";
            if (active_page == "TODAY_COMPLETE") { onclick    += "birdhouse_OBJECTS_open(\""+key+"\", true, \""+active_page+"\");"; }
            label_information += "<div id='label_"+key+"' class='detection_label' onclick='" + onclick + "'>&nbsp;" + bird_lang(key) + " (" + value.length + ")&nbsp;</div>";
            label_keys.push(key);
            });

        if (empty) {
            var onclick = "birdhouse_view_images_objects(\"EMPTY\"); birdhouse_labels_highlight(\"empty\", \"label_key_list\");";
            if (active_page == "TODAY_COMPLETE") { onclick    += "birdhouse_OBJECTS_open(\"empty\", true, \""+active_page+"\");"; }
            label_information +=  "<div id='label_empty' class='detection_label_function' onclick='" + onclick + "'>&nbsp;" + lang("EMPTY") + "&nbsp;</div>";
            label_keys.push("empty");
            }

        if (video) {
            var onclick = "birdhouse_view_images_objects(\"video\"); birdhouse_labels_highlight(\"video\", \"label_key_list\");";
            label_information +=  "<div id='label_video' class='detection_label_function' onclick='" + onclick + "'>&nbsp;" + lang("VIDEO") + "&nbsp;</div>";
            }

        if (count_labels > 0) {
            var onclick = "birdhouse_view_images_objects(\"\");  birdhouse_labels_highlight(\"all\", \"label_key_list\");";
            if (active_page == "TODAY_COMPLETE") { onclick    += "birdhouse_OBJECTS_open(\"all\", true, \""+active_page+"\");"; }
            label_information = "<div id='label_all' class='detection_label_function' onclick='" + onclick + "'>&nbsp;" + lang("ALL_IMAGES") + " (" + Object.entries(entries).length + ")&nbsp;</div>" +
                                label_information;
            html += birdhouse_OtherGroup("detection", lang("DETECTION"), label_information + "<div style='width:100%;height:25px;float:left;'></div>", true );
            label_keys.push("all");
        }
        html += "<div id='label_key_list' style='display:none'>"+label_keys.join(",")+"</div>";
    }
    return html;
}

/*
* create view for video editing (detail for video view)
*
* @param (string) title: title to be displayed
* @param (dict) data: API response for video specific request
*/
function birdhouse_VIDEO_DETAIL( data ) {

	var html         = "";
    var title        = lang("VIDEO_DETAIL");
	var video        = data["DATA"]["data"]["entries"];
	var server_info  = app_data["SETTINGS"]["server"];
    var tab          = new birdhouse_table();
    var analysis     = undefined;
    var video_exists = false;

	for (let key in video) {
	    video_exists                = true;
		app_active.date             = key;
        video[key]["directory"]     = "videos/";
        video[key]["path"]          = "videos/";
        video[key]["type"]          = "video_org";
        video[key]["long_length"]   = true;

		var short               = false;
		var thumbnail           = false;
		var video_name          = video[key]["date"];
		var video_stream        = birdhouse_Image("Complete", key, video[key]);
		var video_stream_short  = "";
		analysis                = video[key]["fps"];

        //console.log("---> video: " + key + ", " + JSON.stringify(video[key]));
		//console.log(video_stream);

		if (video[key]["video_file_short"] != undefined && video[key]["video_file_short"] != "") {
            short                      = true;
            var video_short            = {};
            Object.assign( video_short, video[key] );
            var short_video_file       = video[key]["video_file_short"];
            video_short["video_file"]  = short_video_file;
            video_short["long_length"] = false;
            video_stream_short         = birdhouse_Image("Short", "short", video_short);
            //console.log(video_stream_short);
            }

        if (video[key]["thumbnail_selected"] != undefined && video[key]["thumbnail_selected"] != "") {
            thumbnail                 = true;
            video[key]["type"]        = "thumbnail_selected";
            video_stream_thumb        = birdhouse_Image("Thumbnail", "thumb", video[key]);
            //console.log(video_stream_thumb);
        }

        tab.style_rows["height"]           = "20px";
        tab.style_cells["vertical-align"]  = "top";

        var video_title  = "";
        if (video[key]["title"]) { video_title  = video[key]["title"]; }
        var onclick_video = "birdhouse_editVideoTitle(title=\"set_video_title\", video_id=\""+key+"\", camera=\""+video[key]["camera"]+"\");";
        var edit_title    = "<input id='set_video_title' value='"+video_title+"' class='input-video-edit' style='width:100px;background:white;'>&nbsp;&nbsp;";
        edit_title       += "<button class='button-video-edit' onclick='"+onclick_video+"'>"+lang("SAVE")+"</button>";

		html += "<div class='camera_info' style='height:auto;'>";
		html += "<div class='camera_info_image video_edit'>";
		html += "<div class='video-edit-thumb'>" + video_stream + "</div>";
		if (short)      { html += "<div class='video-edit-thumb'>" + video_stream_short + "</div>"; }
		if (thumbnail)  { html += "<div class='video-edit-thumb'>" + video_stream_thumb + "</div>"; }
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

		if (app_admin_allowed) {
		    html += tab.row("&nbsp;");
			html += tab.row(lang("EDIT_VIDEO_2") + ":",
			    "<button onclick=\"birdhouse_videoOverlayToggle();this.blur();\" class=\"button-video-edit\">&nbsp;"+lang("SHORTEN_VIDEO")+"&nbsp;</button>&nbsp;"
			    );
			if (thumbnail || short) {
			    var delete_buttons = "";
			    if (thumbnail) { delete_buttons += "<button onclick=\"birdhouse_deleteThumbVideo('"+key+"');\" class=\"button-video-edit\">&nbsp;"+lang("DELETE_THUMBNAIL")+"&nbsp;</button>&nbsp;"; }
			    if (short)     { delete_buttons += "<button onclick=\"birdhouse_deleteShortVideo('"+key+"');\" class=\"button-video-edit\">&nbsp;"+lang("DELETE_SHORT_VIDEO")+"&nbsp;</button>&nbsp;"; }
                html += tab.row(lang("DELETE") + ":", delete_buttons);
			    }

			var player = "<div id='camera_video_edit_overlay' class='camera_video_edit_overlay' style='display:none'></div>";
			player += "<div id='camera_video_edit' class='camera_video_edit' style='display:none'>";
			player += "<div style='height:46px;width:100%'></div>";
			var trim_command  = "appMsg.wait_small('"+lang("PLEASE_WAIT")+"');birdhouse_createShortVideo();";
			var thumb_command = "setTCin();appMsg.wait_small('"+lang("PLEASE_WAIT")+"');birdhouse_createThumbVideo();";
            var video_stream_server = window.location.href.split("//")[1];
            video_stream_server = video_stream_server.split("/")[0];
            video_stream_server = video_stream_server.split(":")[0];
            video_stream_server = "http://" + video_stream_server + ":" + server_info["port_video"] + "/";

			console.log("-----> video-streaming: " + video_stream_server + " (http[s]: " + window.location.href  + ")");

			video_values = {};
			video_values["VIDEOID"]                 = key;
			video_values["ACTIVE"]                  = app_active.cam;
			video_values["LENGTH"]                  = video[key]["length"];
			video_values["THUMBNAIL"]               = lang("THUMBNAIL");
			video_values["CLOSE"]                   = lang("CLOSE") + " (ESC)";
			video_values["SHORTEN"]                 = lang("SHORTEN");
			video_values["CANCEL"]                  = lang("CANCEL");
			video_values["FILE_THUMBNAIL"]          = "";
			video_values["VIDEOFILE"]               = video_stream_server + video[key]["video_file"];
			video_values["JAVASCRIPT_SHORTEN"]      = trim_command;
			video_values["JAVASCRIPT_THUMBNAIL"]    = thumb_command;

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
    html += "<div id='video_analysis'></div>";
    html += "<div id='audio_analysis'></div>";

    if (!video_exists) {
        html += "<center>&nbsp;<br/><i>" + lang("NO_ENTRIES") + "</i><br/>&nbsp;</center>";
        }

	birdhouse_frameHeader(lang("EDIT_VIDEO"));
	setTextById(app_frame.content,html);

    if (video_exists) {
        if (analysis) {
            var chart_video = birdhouseChart_create(label="", titles=analysis["video"]["titles"],
                                              data=analysis["video"]["data"],
                                              type="line",
                                              sort_keys=true,
                                              id="video_chart",
                                              size="", set_colors=[],
                                              set_menu="right"
                                              );
            var chart_audio = birdhouseChart_create(label="", titles=analysis["audio"]["titles"],
                                              data=analysis["audio"]["data"],
                                              type="line",
                                              sort_keys=true,
                                              id="audio_chart",
                                              size="", set_colors=[],
                                              set_menu="right"
                                              );
            if (analysis != undefined && analysis != {}) { setTextById("video_analysis", chart_video); }
            if (analysis != undefined && analysis != {}) { setTextById("audio_analysis", chart_audio); }
            }

        load_videoplayer();
        }
	}

    function load_videoplayer() {
    videoSetVars();
    }

app_scripts_loaded += 1;
