//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// birdhouse image views
//--------------------------------------

var birdhouse_active_streams = {};

function birdhouse_KillActiveStreams() {
    Object.keys(birdhouse_active_streams).forEach(function (key) {
        if (birdhouse_active_streams[key] == true) {
            var param = key.split("&");
            birdhouse_killStream(param[0], key);
            birdhouse_active_streams[key] = false;
            }
        });
    birdhouse_active_streams = {};
    }

function birdhouse_StreamURL(camera, stream_url, stream_id, new_uid=false) {
    var stream_server = RESTurl;
    var stream_link   = stream_server + stream_url;
    var stream_id_ext = camera;
    if (new_uid)  {
        app_unique_stream_id += 1;
    }
    var stream_uid    = app_unique_stream_id;

    //var app_unique_stream_id  = new Date().getTime();

    if (stream_id != "")        {
        stream_link   += "&" + stream_id;
        stream_id_ext += "&" + stream_id;
        }
    if (stream_uid)  {
        stream_link   += "&" + stream_uid;
        stream_id_ext += "&" + stream_uid;
        }
    birdhouse_active_streams[stream_id_ext] = true;

	stream_link = stream_link.replaceAll("//", '/');
	stream_link = stream_link.replace(":/","://");
    return stream_link;
    }

function birdhouse_Camera( main, view, onclick, camera, stream_server, admin_allowed=false ) {
	var html      = "";
	var style_cam = view;

	if (main) { var container = 'main'; }
	else      { var container = '2nd'; }

    var stream_link    = birdhouse_StreamURL(camera["name"], camera["stream"], "stream_main", true);
	var livestream     = "<img src='"+stream_link+"' id='stream_"+camera["name"]+"' class='livestream_"+container+"'/>";
	var command_record = "appFW.requestAPI(\"POST\",[\"start\",\"recording\",\""+camera["name"]+"\"],\"\",\"\",\"\",\"birdhouse_INDEX\");"; //requestAPI(\"/start/recording/cam2\");
	var command_stop   = "appFW.requestAPI(\"POST\",[\"stop\", \"recording\",\""+camera["name"]+"\"],\"\",\"\",\"\",\"birdhouse_INDEX\");"; //requestAPI(\"/stop/recording/cam2\");

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


function birdhouse_OtherGroup( key, title, content, header_open) {
    var html = "";
    var display = "";
	if (header_open == false) { display = "style='display:none;'"; }

    html += birdhouse_OtherGroupHeader( key, title, header_open );
    html += "<div id='group_"+key+"' "+display+">";
    html += content;
    html += "</div>";
    return html;
}

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


function birdhouse_ImageGroup( title, entries, entry_count, entry_category, header_open, admin=false, video_short=false,
                               same_img_size=false, max_lowres_size=0, max_text_lines=1) {
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
			img_id2 = img_id2.replaceAll( "/", "_");

            if (entries[key]["type"] != "data") {
                if (count["star"] != undefined && parseInt(entries[key]["favorit"]) == 1) {
                    count["star"]    += 1;
                }
                else if (count["recycle"] != undefined && (entries[key]["to_be_deleted"]) == 1)	{
                    count["recycle"] += 1;
                }
                else if (count["detect"] != undefined && parseInt(entries[key]["detect"]) == 1) {
                    count["detect"]  += 1;
                }
            }

			if (header_open == false && entries[key]["lowres"] != undefined) {
			    image_ids += " " + img_id2;
            }

			if (count["data"] == undefined && count["all"] != undefined) { }
			if (count["data"] != undefined && entries[key]["type"] == "data") { count["data"] += 1; }
        }
		if (count["all"] != undefined && count["data"] != undefined) { count["all"] -= count["data"]; }
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
        lowres_size["container_height"] = lowres_size["thumbnail_height"] + 22 + (max_text_lines * 18);

        console.debug("Thumbnail size: frame-width=" + frame_width + "; thumbnail-width=" + lowres_size["thumbnail_width"]);
        console.debug("              : container-width=" + lowres_size["container_width"]  + "; container-height=" + lowres_size["container_height"]);
        console.debug("              : lowres-width=" + lowres_width + "; lowres-height=" + lowres_height);
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
		html += birdhouse_Image(title=img_title, entry=entries[key], header_open=header_open, admin=admin,
		                        video_short=video_short, group_id=group_id, same_img_size=same_img_size,
		                        lowres_size=lowres_size);
    }

	html += "</div>";
	return html;
}

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
		if (info_count < Object.keys(count).length) { info += " | "; }
		info_count += 1;
		}
	if (count["data"]  != undefined) {
		if (count["data"] > 0) { color = color_code["data"]; } else { color = "gray"; }
		info += "data: <font color='"+color+"'>" + count["data"].toString().padStart(3,"0") + "</font>";
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

	console.log(app_active_page);

	if (entry["type"] == "data") {
		return "";
    }
	else if (entry["type"] == "image") {
		var lowres      = birdhouse_ImageURL(RESTurl + entry["directory"] + entry["lowres"]);
		var hires       = birdhouse_ImageURL(RESTurl + entry["directory"] + entry["hires"]);
		var description = entry["time"] + " (" + entry["similarity"] + "%)";

		if (app_active_page == "FAVORITES") {
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
		var lowres      = birdhouse_StreamURL(app_active_cam, entry["stream"], "stream_list_5");
		var onclick     = "birdhousePrint_load(view=\"INDEX\", camera = \""+entry["camera"]+"\");";
		var description = lang("LIVESTREAM");
    }
	else if (entry["type"] == "camera") {
		var description = title;
		//var lowres      = entry["video"]["stream"];
		var lowres      = birdhouse_StreamURL(entry["id"], entry["video"]["stream"], "image_stream");
		var hires       = lowres;
		var onclick     = "birdhouse_imageOverlay(\""+hires+"\",\""+description+"\");";
    }
	else if (entry["type"] == "detection") {
		var description = title;
		//var lowres      = entry["video"]["stream_detect"];
		var lowres      = birdhouse_StreamURL(entry["id"], entry["video"]["stream_detect"], "image_stream_detect");
		var hires       = lowres;
		var onclick     = "birdhouse_imageOverlay(\""+hires+"\",\""+description+"\");";
    }
	else if (entry["type"] == "video") {
		var note        = "";
		var video_file  = entry["video_file"];
		if (entry["video_file_short"] != undefined && entry["video_file_short"] != "") {
			if (video_short) {
				video_file  = entry["video_file_short"];
				note = "*";
        }	}
        var streaming_url = "http://"+app_data["DATA"]["devices"]["cameras"][app_active_cam]["video"]["stream_server"]+"/";
		var lowres      = birdhouse_ImageURL(RESTurl + entry["path"] + entry["thumbnail"]);
		var hires       = birdhouse_ImageURL(streaming_url + video_file);
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
	img_id2 = img_id2.replaceAll( "/", "_");

	if (entry["detect"] == 1)                                           { style = "border: 1px solid "+color_code["detect"]+";"; }
	if (entry["to_be_deleted"] == 1 || entry["to_be_deleted"] == "1")   { style = "border: 1px solid "+color_code["recycle"]+";"; }
	if (entry["favorit"] == 1 || entry["favorit"] == "1")               { style = "border: 1px solid "+color_code["star"]+";"; }

	if (admin && edit) {
		var img_id      = entry["category"];
		var img_name    = entry["lowres"];
		var img_star    = entry["favorit"];
		var img_recycle = entry["to_be_deleted"];
		var img_dir     = "birdhouse/img/";
		if (img_star == undefined)       { img_star = 0; }
		if (img_recycle == undefined)    { img_recycle = 0; }
		if (parseInt(img_star) == 0)     { img_star_r = 1; }    else { img_star_r = 0; }
		if (parseInt(img_recycle) == 0)  { img_recycle_r = 1; } else { img_recycle_r = 0; }
		var onclick_star    = "birdhouse_setFavorit(index=\""+img_id+"\",status=document.getElementById(\"s_"+img_id2+"_value\").innerHTML,lowres_file=\""+img_name+"\",img_id=\""+img_id2+"\");";
		var onclick_recycle = "birdhouse_setRecycle(index=\""+img_id+"\",status=document.getElementById(\"d_"+img_id2+"_value\").innerHTML,lowres_file=\""+img_name+"\",img_id=\""+img_id2+"\");";
		onclick_recycle    += "birdhouse_recycleRange(group_id=\""+group_id+"\", index=\""+img_id+"\", status=document.getElementById(\"d_"+img_id2+"_value\").innerHTML, lowres_file=\""+img_name+"\")";
		star                = "<div id='s_"+img_id2+"_value' style='display:none;'>"+img_star_r+"</div>   <img class='star_img'    id='s_"+img_id2+"' src='"+img_dir+"star"+img_star+".png'       onclick='"+onclick_star+"'/>";
		recycle             = "<div id='d_"+img_id2+"_value' style='display:none;'>"+img_recycle_r+"</div><img class='recycle_img' id='d_"+img_id2+"' src='"+img_dir+"recycle"+img_recycle+".png' onclick='"+onclick_recycle+"'/>";
    }

    var height = "";
    var container_style = "";

    if (!same_img_size) {
        height = " fixed_height";
        }
    else if (lowres_size != 0) {
        container_width  = lowres_size["container_width"];
        container_height = lowres_size["container_height"];
        thumbnail_width  = lowres_size["thumbnail_width"];
        style           += "width:" + thumbnail_width + "px";
        container_style += "width:" + container_width + "px;height:" + container_height +"px;";
        }

	html += "<div class='image_container"+height+"' style='" + container_style + "'>";
	html += "  <div class='star'>"+star+"</div>";
	html += "  <div class='recycle'>"+recycle+"</div>";
	html += "  <div class='thumbnail_container'>";
	html += "    <a onclick='"+onclick+"' style='cursor:pointer;'><img "+dont_load+"src='"+lowres+"' id='"+img_id2+"' class='thumbnail' style='"+style+"'/></a>";
	html +=      play_button;
	html += "    <br/><center><small>"+description+"</small></center>";
	html += "  </div>";
	html += "</div>";

	return html;
}


function birdhouse_ImageURL(URL) {
	URL = URL.replaceAll("//","/");
	URL = URL.replace("http:/","http://");
	URL = URL.replace("https:/","https://");
	return URL;
	}
