//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// birdhouse image views
//--------------------------------------

var birdhouse_active_video_streams  = {};
var birdhouse_image_ids_error       = [];
var birdhouse_image_ids             = [];

function birdhouse_KillActiveStreams() {
    for (let key in birdhouse_active_video_streams) {
        if (birdhouse_active_video_streams[key] == true) {
            var param = key.split("&");
            birdhouse_killStream(param[0], key);
            }
        }
    window.stop();
    }

function birdhouse_CountActiveStreams() {
    count = 0;
    for (let key in birdhouse_active_video_streams) {
        if (birdhouse_active_video_streams[key] == true) {
            count += 1;
            }
        }
    return count;
}

function birdhouse_StreamURL(camera, stream_url, stream_id, new_uid=false) {
    var stream_server = RESTurl;
    var stream_link   = stream_url;
    var stream_id_ext = camera;

    if (stream_link.indexOf("http:") > -1 || stream_link.indexOf("https:") > -1) {}
    else { stream_link = stream_server + stream_link; }

    if (new_uid)  {
        app_unique_stream_id += 1;
    }
    var stream_uid    = app_unique_stream_id;

    if (stream_id != "")        {
        stream_link   += "&" + stream_id;
        stream_id_ext += "&" + stream_id;
        }
    if (stream_uid)  {
        stream_link   += "&" + stream_uid;
        stream_id_ext += "&" + stream_uid;
        }
    birdhouse_active_video_streams[stream_id_ext] = true;

	stream_link = stream_link.replaceAll("//", '/');
	stream_link = stream_link.replace(":/","://");
    return [stream_link, stream_id_ext];
    }

function birdhouse_Camera( main, view, onclick, camera, stream_server, admin_allowed=false ) {
	var html      = "";
	var style_cam = view;

	if (main) { var container = 'main'; }
	else      { var container = '2nd'; }

    var [stream_link, stream_uid]  = birdhouse_StreamURL(camera["name"], camera["stream"], "stream_main", true);
	var livestream     = "<img src='"+stream_link+"' id='stream_"+camera["name"]+"' class='livestream_"+container+"'/>";
	var command_record = "birdhouse_recordStart(\""+camera["name"]+"\");"; //requestAPI(\"/stop/recording/cam2\");
	var command_stop   = "birdhouse_recordStop(\""+camera["name"]+"\");"; //requestAPI(\"/stop/recording/cam2\");

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


function birdhouse_OtherGroup( key, title, content, header_open, css_class="") {
    if (app_header_opened["group_"+key] != undefined) {
        header_open = app_header_opened["group_"+key];
        }

    var html = "";
    var display = "";
	if (header_open == false) { display = "style='display:none;'"; }
    if (css_class != "") { css_class = " " + css_class; }

    html += birdhouse_OtherGroupHeader( key, title, header_open, css_class);
    html += "<div id='group_"+key+"' "+display+" class='separator_group_body"+css_class+"'>";
    html += content;
    html += "</div>";
    return html;
}

function birdhouse_OtherGroupHeader( key, title, header_open, css_class="") {
	var status = "−";
	if (header_open == false) { status = "+"; }
	var html   = "";
	html += "<div id='group_header_"+key+"' class='separator_group"+css_class+"' onclick='birdhouse_groupToggle(\""+key+"\")'>";
	html += "<text id='group_link_"+key+"' style='cursor:pointer;'>("+status+")</text> ";
	html += title;
	html += "</div>";
	return html;
}


function birdhouse_ImageGroup( group_id, title, entries, entry_count, entry_category, header_open, admin=false, video_short=false,
                               same_img_size=false, max_lowres_size=0, max_text_lines=1) {

	var count     = {};
	var html      = "";
	var image_ids = "";
	var display   = "";

	if (admin) {
		for (i=0;i<entry_count.length;i++) 	{ count[entry_count[i]] = 0; }
		if (count["all"] != undefined) 	    { count["all"] = Object.keys(entries).length; }

		for (let key in entries) {
			var img_id2 = "";
			img_id2 += entries[key]["directory"] + entries[key]["lowres"];
			img_id2 = img_id2.replaceAll( "/", "_");

            if (entries[key]["type"] != "data") {
                if (count["star"] != undefined && parseInt(entries[key]["favorit"]) == 1) {
                    count["star"]    += 1;
                }
                else if (count["recycle"] != undefined && (entries[key]["to_be_deleted"]) == 1)	{
                    count["recycle"] += 1;
                }
                else if (count["object"] != undefined && entries[key]["detections"] && entries[key]["detections"].length > 0) {
                    count["object"]  += 1;
                }
                else if (count["detect"] != undefined && parseInt(entries[key]["detect"]) == 1) {
                    count["detect"]  += 1;
                }
            }
			if (count["data"] == undefined && count["all"] != undefined) { }
			if (count["data"] != undefined && entries[key]["type"] == "data") { count["data"] += 1; }
        }
		if (count["all"] != undefined && count["data"] != undefined) { count["all"] -= count["data"]; }
    }

	for (let key in entries) {
			var img_id2 = "";
			if (entries[key]["lowres"] != undefined) {
                img_id2 += entries[key]["directory"] + entries[key]["lowres"];
                img_id2 = img_id2.replaceAll( "/", "_");
			    image_ids += " " + img_id2;
            }
			if (entries[key]["thumbnail"] != undefined) {
                img_id2 += entries[key]["directory"] + entries[key]["thumbnail"];
                img_id2 = img_id2.replaceAll( "/", "_");
			    image_ids += " " + img_id2;
            }
	}

    if (app_header_opened["group_"+group_id] != undefined) {
        header_open = app_header_opened["group_"+group_id];
        }

	if (header_open == false) {
		display = "style='display:none;'";
    }

    // calculate optimal thumbnail size based on max image size and lines of text
    var lowres_size = {};
    if (max_lowres_size != 0) {
        lowres_width  = max_lowres_size[0];
        lowres_height = max_lowres_size[1];
        frame_width   = document.getElementById("frame1").offsetWidth - 12;

        if (frame_width < 400) {
            container_width = (frame_width - 12) / 3;
        }
        else if (frame_width < 500) {
            container_width = (frame_width - 12) / 4;
        }
        else if (frame_width < 600) {
            container_width = (frame_width - 12) / 4;
        }
        else if (frame_width < 700) {
            container_width = (frame_width - 12) / 5;
        }
        else if (frame_width < 800) {
            container_width = (frame_width - 12) / 6;
        }
        else if (frame_width < 900) {
            container_width = (frame_width - 12) / 7;
        }
        else {
            container_width = (frame_width - 12) / 8;
        }

        lowres_size["container_width"]  = Math.round(container_width) - 4;
        lowres_size["thumbnail_width"]  = lowres_size["container_width"] - 2;
        lowres_size["thumbnail_height"] = Math.round(lowres_height / lowres_width * lowres_size["container_width"]);
        lowres_size["container_height"] = lowres_size["thumbnail_height"] + 30 + (max_text_lines * 23);

        console.debug("Thumbnail size: frame-width=" + frame_width + "; thumbnail-width=" + lowres_size["thumbnail_width"]);
        console.debug("              : container-width=" + lowres_size["container_width"]  + "; container-height=" + lowres_size["container_height"]);
        console.debug("              : lowres-width=" + lowres_width + "; lowres-height=" + lowres_height);
    }

	html += birdhouse_ImageGroupHeader( group_id, title, header_open, count );
	html += "<div id='group_ids_"+group_id+"' style='display:none;'>" + image_ids + "</div>";
	html += "<div id='group_"+group_id+"' "+display+">";

	if (title == lang("RECYCLE")) {
		var command  = "";
		if (entry_category.length == 1)	{ command = "#"+entry_category[0]+"#,##"; }
		if (entry_category.length == 2)	{ command = "#"+entry_category[0]+"#,#"+entry_category[1]+"#"; }
		if (command != "") {
			var del_command = "birdhouse_deleteMarkedFiles("+command+");";
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
		html += birdhouse_Image(title=img_title, entry=entries[key], header_open=header_open, admin=admin,
		                        video_short=video_short, group_id=group_id, same_img_size=same_img_size,
		                        lowres_size=lowres_size);
    }

	html += "</div>";
	return html;
}

function birdhouse_ImageGroupHeader( key, title, header_open, count={} ) {
	var status = "−";
    birdhouse_image_ids_error = [];
    birdhouse_image_ids       = [];

	if (header_open == false) { status = "+"; }
	var html   = "";
	html += "<div id='group_header_"+key+"' class='separator_group' onclick='birdhouse_groupToggle(\""+key+"\")'>";
	html += "<text id='group_link_"+key+"' style='cursor:pointer;'>("+status+")</text> ";
	html += title + "<font color='gray'> &nbsp; &nbsp; ";

	info       = "";
	info_count = 1;
	if (count["all"] != undefined) {
		if (count["all"] > 0) { color = color_code["default"]; } else { color = "gray"; }
		info += "all: <font color='"+color+"' id='image_count_all_"+key+"'>"   + count["all"].toString().padStart(3,"0")     + "</font>";
		if (info_count < Object.keys(count).length) { info += " | "; }
		info_count += 1;
		}
	if (count["star"] != undefined) {
		if (count["star"] > 0) { color = color_code["star"]; } else { color = "gray"; }
		info += "star: <font color='"+color+"' id='image_count_star_"+key+"'>"   + count["star"].toString().padStart(2,"0")    + "</font>";
		if (info_count < Object.keys(count).length) { info += " | "; }
		info_count += 1;
		}
	if (count["object"] != undefined) {
		if (count["object"] > 0) { color = color_code["object"]; } else { color = "gray"; }
		info += "object: <font color='"+color+"' id='image_count_detect_"+key+"'>" + count["object"].toString().padStart(2,"0")  + "</font>";
		if (info_count < Object.keys(count).length) { info += " | "; }
		info_count += 1;
		}
	if (count["detect"] != undefined) {
		if (count["detect"] > 0) { color = color_code["detect"]; } else { color = "gray"; }
		info += "detect: <font color='"+color+"' id='image_count_detect_"+key+"'>" + count["detect"].toString().padStart(2,"0")  + "</font>";
		if (info_count < Object.keys(count).length) { info += " | "; }
		info_count += 1;
		}
	if (count["recycle"]  != undefined) {
		if (count["recycle"] > 0) { color = color_code["recycle"]; } else { color = "gray"; }
		info += "recycle: <font color='"+color+"' id='image_count_recycle_"+key+"'>" + count["recycle"].toString().padStart(2,"0") + "</font>";
		if (info_count < Object.keys(count).length) { info += " | "; }
		info_count += 1;
		}
	if (count["data"]  != undefined) {
		if (count["data"] > 0) { color = color_code["data"]; } else { color = "gray"; }
		info += "data: <font color='"+color+"' id='image_count_data_"+key+"'>" + count["data"].toString().padStart(2,"0") + "</font>";
		}
	if (info != "") { html += "[" + info + "]"; }

	html += "</font></div>";
	return html;
	}

function birdhouse_Image(title, entry, header_open=true, admin=false, video_short=false, group_id="", same_img_size=false, lowres_size=0) {

	var html        = "";
	var play_button = "";
	var dont_load   = "";
	var edit        = false;
	var category    = "";
    var rotation    = 0;
	var onclick_difference = "";
	var settings     = app_data["SETTINGS"];
	var settings_cam = app_data["SETTINGS"]["devices"]["camera"];
	var img_url      = ""; // RESTurl;
	var img_missing  = false;
	var detect_sign  = "";

	if (entry["directory"] && entry["directory"].charAt(entry["directory"].length - 1) != "/") { entry["directory"] += "/"; }

	console.log(app_active_page);

	if (entry["type"] == "data") {

		return "";
    }
	else if (entry["type"] == "image") {
		var lowres      = birdhouse_ImageURL(img_url + entry["directory"] + entry["lowres"]);
		var hires       = birdhouse_ImageURL(img_url + entry["directory"] + entry["hires"]);
		var description = entry["time"] + " (" + entry["similarity"] + "%)";

		if (app_active_page == "FAVORITES") {
			[day,month,year]  = entry["date"].split(".");
			[hour,minute,sec] = entry["time"].split(":");
			description       = entry["date"]+" ("+hour+":"+minute+")";
        }
        else if (app_active_page == "TODAY") {
			[hour,minute,sec] = entry["time"].split(":");
		    description = hour + ":" + minute + " (" + entry["similarity"] + "%)";
        }

        if (entry["hires_detect"] && entry["detections"] && entry["detections"].length > 0) {
            var description_labels = "[center][div style=align:center;][br/][hr/]";
            var hires_description = description;
            var counted_labels = {}
            var confidence = {};
            for (var i=0;i<entry["detections"].length;i++) {
                if (!counted_labels[entry["detections"][i]["label"]]) { counted_labels[entry["detections"][i]["label"]] = 1; }
                else                                                  { counted_labels[entry["detections"][i]["label"]] += 1; }

                confidence[entry["detections"][i]["label"]] = Math.round(entry["detections"][i]["confidence"] * 1000)/10;
                }
            Object.keys(counted_labels).forEach( key => {
                var info = "";
                var amount = counted_labels[key];
                if (amount > 1) { info = amount; }
                else            { info = confidence[key] + "%"; }
                description_labels += "[div class=detection_label style=cursor:default;]&nbsp;"+bird_lang(key)+"&nbsp;("+info+")&nbsp;[/div]";
                });
            description_labels += "[/div][/center]";
            hires_description += description_labels;
            var onclick = "birdhouse_imageOverlay(\""+hires+"\",\""+hires_description+"\", \""+birdhouse_ImageURL(img_url + entry["directory"] + entry["hires_detect"])+"\");"; detect_sign = "<sup>D</sup>";
            }
		else {
		    var onclick = "birdhouse_imageOverlay(\""+hires+"\",\""+description+"\");"; entry["hires_detect"] = "";
		    }
		description = description.replace(/\[br\/\]/g,"<br/>");

        if (admin && entry["compare"][1] != "000000" && app_active_page == "TODAY_COMPLETE") {
            var diff_image      = RESTurl + "compare/"+entry["compare"][0]+"/"+entry["compare"][1]+"/"+entry["similarity"]+"/image.jpg?"+entry["camera"];
            onclick_diff        = "birdhouse_imageOverlay(\""+diff_image+"\",\"Difference Detection - "+description+"\");";
            onclick_difference  = entry["time"] +" (<u onclick='"+onclick_diff+"' style='cursor:pointer;'>";
            onclick_difference += entry["similarity"] + "%</u>)";
    		description         = onclick_difference;
        }
		edit            = true;
    }
    else if (entry["type"] == "label") {
		var lowres      = birdhouse_ImageURL(img_url + entry["directory"] + entry["lowres"]);
		var hires       = birdhouse_ImageURL(img_url + entry["directory"] + entry["hires_detect"]);
		//var description = "<div class='detection_label' style='float:none;cursor:default;max-height:unset;height:unset;width:100px;'>"+title+"</div>";
		var description = "<div class='detection_label image'>"+title+"</div>";
        var onclick     = "birdhouse_imageOverlay(\""+hires+"\",\""+title+"\");";

        same_img_size = true;
    }
	else if (entry["type"] == "directory") {

        var description = "";
        var detection = "";
        if (entry["detection"]) { detection = "<sup>D</sup>"; }
    	if (entry["lowres"] == "" && entry["count_cam"] == 0) {
            description += "<b>" + entry["date"] + "</b><br/>";
            description += "<i>"+lang("NO_IMAGE_IN_ARCHIVE_2")+"</i>";
            img_missing = true;
    	    }
        else {
            var lowres      = birdhouse_ImageURL(img_url + entry["directory"] + entry["lowres"]);
            var onclick     = "birdhousePrint_load(view=\"TODAY\", camera = \""+entry["camera"]+"\", date=\""+entry["datestamp"]+"\");";
            if (entry["count_cam"] != entry["count"]) {
                description += "<b>" + entry["date"] + "</b>"+detection+"<br/>" + entry["count_cam"] + " / " + entry["count"];
                if (entry["count_delete"] > 0) { description += "*"; }
                description += "<br/><i>[" + Math.round(entry["dir_size"]*10)/10 + " MB]</i>";
                }
            else {
                description += "<b>" + entry["date"] + "</b>"+detection+"<br/>" + entry["count_cam"];
                description += "<br/><i>[" + Math.round(entry["dir_size"]*10)/10 + " MB]</i>";
                }
            }
        }
	else if (entry["type"] == "addon") {
		var lowres = birdhouse_ImageURL(img_url + entry["lowres"]);
		var [lowres, stream_uid]  = birdhouse_StreamURL(app_active_cam, entry["stream"], "stream_list_5", true);
		var onclick     = "birdhousePrint_load(view=\"INDEX\", camera = \""+entry["camera"]+"\");";
		var description = lang("LIVESTREAM");
        }
	else if (entry["type"] == "camera") {
		var description = title;
		//var lowres      = entry["video"]["stream"];
		var [lowres, stream_uid] = birdhouse_StreamURL(entry["id"], entry["video"]["stream"], "image_stream", true);
		var hires       = lowres;
		var onclick     = "birdhouse_imageOverlay(\""+hires+"\",\""+description+"\");";
    }
	else if (entry["type"] == "detection") {
		var description = title;
		//var lowres      = entry["video"]["stream_detect"];
		var [lowres, stream_uid] = birdhouse_StreamURL(entry["id"], entry["video"]["stream_detect"], "image_stream_detect", true);
		var hires       = lowres;
		var onclick     = "birdhouse_imageOverlay(\""+hires+"\",\""+description+"\", \"\", \"stream_overlay_"+entry["id"]+"\");";
    }
	else if (entry["type"] == "video") {
		var note        = "";
		var video_file  = entry["video_file"];
		if (entry["video_file_short"] != undefined && entry["video_file_short"] != "") {
			if (video_short) {
				video_file  = entry["video_file_short"];
				note = "*";
        }	}
        var stream_server = "";
        if (settings["server"]["ip4_stream_video"] && settings["server"]["ip4_stream_video"] != "") {
            stream_server = settings["server"]["ip4_stream_video"] + ":" + settings["server"]["port_video"];
        }
        else {
            var this_server = window.location.href;
            this_server     = this_server.split("//")[1];
            this_server     = this_server.split("/")[0];
            this_server     = this_server.split(":")[0];
            stream_server   = this_server + ":" + settings["server"]["port_video"];
        }

        var streaming_url = "http://"+stream_server+"/";
		var lowres      = birdhouse_ImageURL(img_url + entry["path"] + entry["thumbnail"]);
		var hires       = birdhouse_ImageURL(streaming_url + video_file);
		var description = "";
		var image_title = "";
		if (entry["title"] && entry["title"] != "") { image_title = "<b>" + entry["title"] + "</b>"; }
		else                                        { image_title = entry["camera"].toUpperCase() + ": " + entry["camera_name"]; }
		if (title.indexOf("_") > 0) { description = entry["date"] + "[br/]" + image_title; }
		else                        { description = title + "[br/]" + image_title; }

		var onclick     = "birdhouse_videoOverlay(\""+hires+"\",\""+description+"\");";
		var play_button = "<img src=\"birdhouse/img/play.png\" class=\"play_button\" style=\"min-width:auto;min-height:auto;\" onclick='"+onclick+"' />";
		entry["lowres"] = entry["thumbnail"];
		description     = description.replace(/\[br\/\]/g,"<br/>");
		if (admin) {
			var cmd_edit = "birdhousePrint_load(view=\"VIDEO_DETAIL\", camera=\""+app_active_cam+"\", date=\""+entry["date_start"]+"\");"
			description += "<br/><a onclick='"+cmd_edit+"' style='cursor:pointer;'>"+lang("EDIT")+"</a>"+note;
        }
		edit            = true;
    }

	if (header_open == false) { dont_load = "data-"; }

	var style       = "";
	var star        = "";
	var recycle     = "";

	var img_id2 = "";
    if (entry["type"] == "addon")           { img_id2 = "stream_lowres_" + app_active_cam; }
    else if (entry["type"] == "detection")  { img_id2 = "stream_detect_" + entry["id"]; }
    else                                    { img_id2 += entry["directory"] + entry["lowres"]; img_id2 = img_id2.replaceAll( "/", "_"); }

	if (entry["favorit"] == 1 || entry["favorit"] == "1")                    { style = "border: 1px solid "+color_code["star"]+";"; }
	else if (entry["to_be_deleted"] == 1 || entry["to_be_deleted"] == "1")   { style = "border: 1px solid "+color_code["recycle"]+";"; }
	else if (entry["detections"] && entry["detections"].length > 0)          { style = "border: 1px solid "+color_code["object"]+";"; }
	else if (entry["detect"] == 1)                                           { style = "border: 1px solid "+color_code["detect"]+";"; }

	if (admin && edit) {
		var img_id      = entry["category"];
		var img_name    = entry["lowres"];
		var img_star    = entry["favorit"];
		var img_recycle = entry["to_be_deleted"];
		var img_dir     = "birdhouse/img/";
		if (img_star == undefined || img_star == -1)         { img_star = 0; }
		if (img_recycle == undefined || img_recycle == -1)   { img_recycle = 0; }
		if (parseInt(img_star) == 0)     { img_star_r = 1; }    else { img_star_r = 0; }
		if (parseInt(img_recycle) == 0)  { img_recycle_r = 1; } else { img_recycle_r = 0; }

		var onclick_star    = "birdhouse_setFavorite(index=\""+img_id+"\",status=document.getElementById(\"s_"+img_id2+"_value\").innerHTML,lowres_file=\""+img_name+"\",img_id=\""+img_id2+"\");";
		var onclick_recycle = "birdhouse_setRecycle(index=\""+img_id+"\",status=document.getElementById(\"d_"+img_id2+"_value\").innerHTML,lowres_file=\""+img_name+"\",img_id=\""+img_id2+"\");";
		if (app_active_page == "TODAY" || app_active_page == "TODAY_COMPLETE") {
		    onclick_recycle    += "birdhouse_recycleRange(group_id=\""+group_id+"\", index=\""+img_id+"\", status=document.getElementById(\"d_"+img_id2+"_value\").innerHTML, lowres_file=\""+img_name+"\")";
		    }
		star                = "<div id='s_"+img_id2+"_value' style='display:none;'>"+img_star_r+"</div>   <img class='star_img'    id='s_"+img_id2+"' src='"+img_dir+"star"+img_star+".png'       onclick='"+onclick_star+"'/>";
		recycle             = "<div id='d_"+img_id2+"_value' style='display:none;'>"+img_recycle_r+"</div><img class='recycle_img' id='d_"+img_id2+"' src='"+img_dir+"recycle"+img_recycle+".png' onclick='"+onclick_recycle+"'/>";

        if (app_collect4download) {
            if (entry["type"] == "image") {
                var collect_entry    = entry["camera"]+"_"+entry["datestamp"]+"_"+entry["time"].replaceAll(":","");
                var onclick_checkbox = "collect4download_toggle(\"" + collect_entry + "\", \""+img_id2+"\");";
                onclick              = onclick_checkbox;
                var img_checkbox     = collect4download_image(collect_entry);
                checkbox = "<div id='c_"+img_id2+"_value' style='display:none;'>"+img_recycle_r+"</div><img class='checkbox_img' id='cb_"+img_id2+"' src='"+img_checkbox+"' onclick='"+onclick_checkbox+"'/>";
                star = checkbox;
                recycle = "";
                }
            else {
                star    = "";
                recycle = "";
                onclick = "";
                }
            }
        }

    var height                  = "";
    var container_style         = "";
    var thumb_container_style   = "";
    var container_id            = "";

    if (!same_img_size) {
        height = " fixed_height";
        }
    else if (lowres_size != 0) {
        container_width  = lowres_size["container_width"];
        container_height = lowres_size["container_height"];
        thumbnail_width  = lowres_size["thumbnail_width"];
        thumbnail_height = lowres_size["thumbnail_height"];
        style           += "width:" + thumbnail_width + "px;height:" + thumbnail_height + "px;";
        container_style += "width:" + container_width + "px;height:" + container_height + "px;";
        thumb_container_style += "width:" + thumbnail_width + "px;";
        }

    if (entry["type"] == "addon")   { container_id = "lowres_today"; }
    else                            { container_id = img_id2 + "_container"; }

	html += "<div id='"+container_id+"' class='image_container"+height+"' style='" + container_style + "'>";
	html += "  <div class='star'>"+star+"</div>";
	html += "  <div class='recycle'>"+recycle+"</div>";
    html += "  <div class='thumbnail_container' style='" + thumb_container_style + "'>";

    if (!img_missing) {
        html += "    <a onclick='"+onclick+"' style='cursor:pointer;'><img "+dont_load+"src='"+lowres+"' id='"+img_id2+"' class='thumbnail' style='"+style+"'/></a>";
        if (entry["similarity"]) {
            html += "<input id='"+img_id2+"_similarity' value='"+entry["similarity"]+"' style='display:none;'>";
            }
        //if (entry["detections"]) {
            var labels = "";
            if (entry["detections"]) {
                for (var i=0;i<entry["detections"].length;i++) {
                    var label = entry["detections"][i]["label"];
                    if (label == "") { label = "without-label"; }
                    if (labels.indexOf(label) < 0) { labels += label + ","; }
                    }
                }
            if (entry["type"] == "video") { labels += "video,"; }
            html += "<input id='"+img_id2+"_objects' value='"+labels+"' style='display:none;'>";
        //    }

        birdhouse_image_ids.push(img_id2);
        html += play_button;
        }
    else {
        if (style == "") { style = "height:140px;"; }
        html += "<div class='thumbnail error' style='"+style+"' id='error_"+img_id2+"'>";
        html += "&nbsp;<br>&nbsp;<br>"+lang("NO_IMAGE_IN_ARCHIVE")+"</div>";
        birdhouse_image_ids_error.push(img_id2);
        }
	html += "    <br/><center><small>" + description + detect_sign + "</small></center>";
	html += "  </div>";
	html += "</div>";

	if (entry["type"] == "addon") {
        html += "<div id='lowres_today_error' class='image_container"+height+"' style='" + container_style +  ";display:none;'>";
        html += "  <div class='star'></div>";
        html += "  <div class='recycle'></div>";
        html += "  <div class='thumbnail_container' style='" + thumb_container_style + "'>";
        html += "     <div class='thumbnail error' style='width:" + thumbnail_width + "px;height:" + thumbnail_height + "px;'>&nbsp;<br/>&nbsp;<br/>"+lang("CONNECTION_ERROR")+"</div>"
        html += "    <br/>";
        html += "  </div>";
        html += "</div>";
	}

	return html;
}

function birdhouse_ImageErrorSize() {}

function birdhouse_ImageURL(URL) {
	URL = URL.replaceAll("//","/");
	URL = URL.replace("http:/","http://");
	URL = URL.replace("https:/","https://");
	return URL;
	}

app_scripts_loaded += 1;