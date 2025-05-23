//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// birdhouse image views
//--------------------------------------

var birdhouse_active_video_streams  = {};
var birdhouse_image_ids_error       = [];
var birdhouse_image_ids             = [];
var birdhouse_lowres_size           = {};


/*
* kill all active video streams in app and request a kill server side using birdhouse_killStream();
*/
function birdhouse_KillActiveStreams() {
    for (let key in birdhouse_active_video_streams) {
        if (birdhouse_active_video_streams[key] == true) {
            var param = key.split("&");
            birdhouse_killStream(param[0], key);
            //delete birdhouse_active_video_streams[key];
            birdhouse_active_video_streams[key] == false;
            }
        }
    window.stop();
    }

/*
* Get a list of active video streams
*
* @returns (integer): amount of streams
*/
function birdhouse_CountActiveStreams() {
    count = 0;
    for (let key in birdhouse_active_video_streams) {
        if (birdhouse_active_video_streams[key] == true) {
            count += 1;
            }
        }
    return count;
}

/*
* create a group with some html-content in it, that starts with a header and that can be opened and closed by clicking onto the header
*
* @param (string) key: unique key/identifier for the group (can be used to show or hide the group = group_id)
* @param (string) title: titel for the group displayed in the header
* @param (string) content: some html-based content
* @param (boolean) header_open: definition if header starts opened or closed
* @param (string) css_class: option to add a class definition; at the moment defined is 'settings' for a specific header color
* @returns (string): html sequence to display the group
*/
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

/*
* create a header for a group
*
* @param (string) key: unique key/identifier for the group (can be used to show or hide the group = group_id)
* @param (string) title: titel for the group displayed in the header
* @param (boolean) header_open: definition if header starts opened or closed
* @param (string) css_class: option to add a class definition; at the moment defined is 'settings' for a specific header color
* @returns (string): html sequence to display the group header
*/
function birdhouse_OtherGroupHeader( key, title, header_open, css_class="") {
	var status = "−";
	if (header_open == false) { status = "+"; }
	var html   = "";
	html += "<div id='group_header_"+key+"' class='separator_group"+css_class+"' onclick='birdhouse_groupToggle(\""+key+"\", \"toggle\", \"block\")'>";
	html += "<text id='group_link_"+key+"' style='cursor:pointer;'>("+status+")</text> ";
	html += title;
	html += "</div>";
	return html;
}

/*
* create a group of images, that starts with a header and that can be opened and closed by clicking onto the header
*
* @param (string) group_id: unique key/identifier for the group (can be used to show or hide the group = group_id)
* @param (string) title: titel for the group displayed in the header
* @param (dict) entries: database entries with all elements to be displayed in the group
* @param (array) entry_count: types that shall be counted in the header when logged in as admin, available: 'all', 'star', 'recycle', 'object', 'detect', 'data'
* @param (string) entry_category: ... tbc.
* @param (boolean) header_open: definition if header starts opened or closed
* @param (boolean) admin: value if logged in as admin
* @param (boolean) video_short: ... tbc.
* @param (boolean) same_img_size: use a fixed height for all image containers
* @param (dict) lowres_size: set lowres size using integers (pixel size) for the following values: 'container_width', 'container_height', 'thumbnail_width', 'thumbnail_height'
* @param (integer) max_lowres_size: ... tbc.
* @param (integer) max_text_lines: ... tbc.
* @returns (string): html sequence to display the image group
*/
function birdhouse_ImageGroup( group_id, title, entries, entry_count, entry_category, header_open, admin=false, video_short=false,
                               same_img_size=false, max_lowres_size=0, max_text_lines=1) {

	var count            = {};
	var html             = "";
	var image_ids        = "";
	var display          = "";
	var special_category = "";

    if (group_id.indexOf("FAVORITE") > 0 ) { special_category = "_FAV"; }

	if (admin && entry_count) {
		for (i=0;i<entry_count.length;i++) 	{ count[entry_count[i]] = 0; }
		if (count["all"] != undefined) 	    { count["all"] = Object.keys(entries).length; }

		for (let key in entries) {
			var img_id2 = "";
			img_id2 += entries[key]["directory"] + "/" + entries[key]["lowres"];
			img_id2 = img_id2.replaceAll( "//", "/");
			img_id2 = img_id2.replaceAll( "/", "_");

            if (entries[key] != undefined) {
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
            }
            if (count["data"] == undefined && count["all"] != undefined) { }
            if (count["data"] != undefined && entries[key]["type"] == "data") { count["data"] += 1; }
        }
		if (count["all"] != undefined && count["data"] != undefined) { count["all"] -= count["data"]; }
    }

	for (let key in entries) {
			var img_id2 = "";
			if (entries[key] != undefined) {
                if (entries[key]["lowres"] != undefined) {
                    img_id2 += entries[key]["directory"] + "/" + entries[key]["lowres"];
                    img_id2 = img_id2.replaceAll( "//", "/");
                    img_id2 = img_id2.replaceAll( ":/", "://");
                    img_id2 = img_id2.replaceAll( "/", "_");
                    image_ids += " " + img_id2;
                }
                if (entries[key]["thumbnail"] != undefined) {
                    img_id2 += entries[key]["directory"] + "/" + entries[key]["thumbnail"];
                    img_id2 = img_id2.replaceAll( "//", "/");
                    img_id2 = img_id2.replaceAll( ":/", "://");
                    img_id2 = img_id2.replaceAll( "/", "_");
                    image_ids += " " + img_id2;
                }
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
	html += "<div id='group_labels_"+group_id+"' style='display:none;'><!--LABELS--></div>";
	html += "<div id='group_"+group_id+"' "+display+" class='image_group'>";

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
	var detection_labels = [];
	for (var i=0;i<entry_keys.length;i++) {
        key   = entry_keys[i];
        if (entries[key] != undefined) {
            var img_title = key;
            html += birdhouse_Image(title=img_title, entry_id=key, entry=entries[key], header_open=header_open, admin=admin,
                                    video_short=video_short, group_id=group_id, same_img_size=same_img_size,
                                    lowres_size=lowres_size, special_category=special_category);
            if (entries[key]["detections"]) {
                for (var j=0;j<entries[key]["detections"].length;j++) {
                    var label = entries[key]["detections"][j]["label"];
                    if (detection_labels.indexOf(label) < 0) { detection_labels.push(label); }
                    }
                }
            if ((!entries[key]["detections"] || entries[key]["detections"].length == 0) && (detection_labels.indexOf("empty") < 0)) {
                detection_labels.push("empty");
                }
            }
        }

	html += "</div>";
    html = html.replace("<!--LABELS-->", detection_labels.join(","));
	return html;
}

/*
* create a header for an image group, for admins incl. information how many items of which type are in the group
*
* @param (string) key: unique key/identifier for the group (can be used to show or hide the group = group_id)
* @param (string) title: titel for the group displayed in the header
* @param (boolean) header_open: definition if header starts opened or closed
* @param (dict) count: amount of different items to be displayed in the header when logged in as admin
* @returns (string): html sequence to display the group header
*/
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

/*
* Check if group is open and depending on give value open or close the group
*
* @param (string) id: unique key/identifier of the group
* @param (string/boolean) open: command, default is "toggle", other values are true (open) or false (close)
*/
function birdhouse_groupToggle(id, open="toggle", show="flex") {
    if (open == "toggle") {
        if (document.getElementById("group_"+id).style.display == "none")   { birdhouse_groupOpen(id, show); }
        else                                                                { birdhouse_groupClose(id); }
    }
    else {
        if (open == true)   { birdhouse_groupOpen(id, show); }
        else                { birdhouse_groupClose(id); }
    }
}

/*
* Open content section of a group
*
* @param (string) id: unique key/identifier of the group
*/
function birdhouse_groupOpen(id, show="flex") {

    document.getElementById("group_"+id).style.display = show;
    app_header_opened["group_"+id] = true;

    if (document.getElementById("group_intro_"+id)) {
        document.getElementById("group_intro_"+id).style.display = show;
    }
    if (document.getElementById("group_ids_"+id)) {
        images = document.getElementById("group_ids_"+id).innerHTML;
    }
    else {
        images = "";
    }
    document.getElementById("group_link_"+id).innerHTML = "(&minus;)";
    image_list = images.split(" ");
    for (let i=0; i<image_list.length; i++) {
        if (image_list[i] != "") {
            img      = document.getElementById(image_list[i]);
            if (img != undefined) {
                img_file = img.getAttribute('data-src');
                if (img_file) {
                    img.src  = img_file;
                }
            }
        }
    }
}

/*
* Close content section of a group
*
* @param (string) id: unique key/identifier of the group
*/
function birdhouse_groupClose(id) {
        document.getElementById("group_"+id).style.display = "none";
        app_header_opened["group_"+id] = false;

        if (document.getElementById("group_intro_"+id)) { document.getElementById("group_intro_"+id).style.display = "none"; }
        document.getElementById("group_link_"+id).innerHTML = "(+)";
}

/*
* create lowres image incl. link to hires overlay image or video
*
* @param (string) title: image title, required for some image types, e.g., ...
* @param (dict) entry: database entry for image
* @param (boolean) header_open: value if image is defined for opened group or closed group (if closed, image will be loaded while opening)
* @param (boolean) admin: value if logged in as admin
* @param (boolean) video_short: ... tbc.
* @param (string) group_id: ... tbc.
* @param (boolean) same_img_size: use a fixed height for all image containers
* @param (dict) lowres_size: set lowres size using integers (pixel size) for the following values: 'container_width', 'container_height', 'thumbnail_width', 'thumbnail_height'
* @returns (string): html sequence to display lowres image
*/
function birdhouse_Image(title, entry_id, entry, header_open=true, admin=false, video_short=false, group_id="",
                         same_img_size=false, lowres_size=0, special_category="") {

	if (entry["type"] == "data") { return ""; }

	var html        = "";
	var category    = "";
    var rotation    = 0;
	var onclick_difference = "";
	var settings     = app_data["SETTINGS"];
	var settings_cam = app_data["SETTINGS"]["devices"]["camera"];
	var img_url      = ""; // RESTurl;
	var img_missing  = false;
	var detect_sign  = "";

	var dont_load   = "";
	if (header_open == false) { dont_load = "data-"; }
	if (entry["directory"] && entry["directory"].charAt(entry["directory"].length - 1) != "/") { entry["directory"] += "/"; }

    console.debug("Image: " + title + " - " + entry_id);
    console.debug(entry);

	var image_data        = birdhouse_ImageDisplayData(title, entry_id, entry, app_active_page, admin, video_short);
    var lowres            = image_data["lowres"];
    var hires             = image_data["hires"];
    var description       = image_data["description"];
    var description_hires = image_data["description_hires"];
    var onclick           = image_data["onclick"];
	var style             = image_data["style"];
    var edit              = image_data["edit"];
    var img_id2           = image_data["img_id2"] + special_category;
    var play_button       = image_data["play_button"];
    var img_missing       = image_data["img_missing"];

    console.debug("Image Display (" + image_data["type"] + "):");
    console.debug(image_data);

    if (image_data["same_img_size"]) { same_img_size = image_data["same_img_size"]; }

	var star                    = "";
	var recycle                 = "";
	var thumbnail_width         = "";
	var thumbnail_height        = "";

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

    var container_style         = "";
    var thumb_container_style   = "";
    var container_id            = "";
    var error_style             = "";

    container_width  = lowres_size["container_width"];
    container_height = lowres_size["container_height"];
    thumbnail_width  = lowres_size["thumbnail_width"];
    thumbnail_height = lowres_size["thumbnail_height"];
    error_style     += "width:" + thumbnail_width + "px;height:" + thumbnail_height + "px;";
    container_style += "width:" + container_width + "px;height:" + container_height + "px;";
    thumb_container_style += "width:" + thumbnail_width + "px;";

    if (entry["type"] == "addon")   {
        container_id     = "lowres_today";
        var image_onload = "onload='error_img=document.getElementById(\"lowres_error_"+entry["camera"]+"\");error_img.height=this.height;error_img.width=this.width;'";
        var image_onload = "";
        }
    else {
        container_id = img_id2 + "_container";
        var image_onload = "";
        }

    console.error(title + " --- " + lowres + " / " + img_name);

	html += "<div class='image_container' id='"+container_id+"'>";
    html += "  <div class='thumbnail_container'>";
	html += "    <div class='image_wrapper'>"

    if (!img_missing) {
        html += "<a onclick='"+onclick+"' style='cursor:pointer;'><img "+dont_load+"src='"+lowres+"' id='"+img_id2+"' class='thumbnail' style='"+style+"' "+image_onload+"/></a>";
        if (entry["similarity"]) {
            html += "<input id='"+img_id2+"_similarity' value='"+entry["similarity"]+"' style='display:none;'>";
            }
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

        birdhouse_image_ids.push(img_id2);
        html += play_button;
        }
    else {
        console.debug("birdhouse_Image - " + img_id2);
        console.debug(image_data);

        html += "<div class='thumbnail error' style='"+style+"' id='error_"+img_id2+"'>";
        html += lang("NO_IMAGE_IN_ARCHIVE")+"</div>";
        birdhouse_image_ids_error.push(img_id2);
        }
	html += "      <div class='star'>"+star+"</div>";
	html += "      <div class='recycle'>"+recycle+"</div>";
	html += "    </div>";
	html += "    <center style='margin-top:4px;'><small>" + description + "</small></center>";
	html += "  </div>";
	html += "</div>";

	if (entry["type"] == "addon") {
        html += "<div  class='image_container' id='lowres_today_error' style='" + container_style +  ";display:none;'>";
        html += "  <div class='thumbnail_container'>";
        html += "    <div class='image_wrapper'>"
        html += "      <div class='thumbnail_container' style='" + thumb_container_style + "'>";
        html += "        <div class='thumbnail error' id='lowres_error_"+entry["camera"]+"' style='"+error_style+";padding:0px;'>"+lang("CONNECTION_ERROR")+"</div>"
        html += "        <br/>";
        html += "       </div>";
        html += "    </div>";
        html += "  </div>";
        html += "</div>";
	}

	return html;
}

/* -------------------------------------------- */

/*
* create description, links and other information for lowres images
*
* @param (string) title: image title, required for some image types, e.g., ... tbc.
* @param (dict) entry: database entry for image
* @param (string) active_page: information which page is opened
* @param (boolean) admin: value if logged in as admin
* @returns (dict): definition of title, lowres and hires links as well as other data to show the image
*/
function birdhouse_ImageDisplayData(title, entry_id, entry, active_page="", admin=false, video_short=false) {
	const img_url = ""; // RESTurl;
	var settings      = app_data["SETTINGS"];
	var settings_cam  = app_data["SETTINGS"]["devices"]["camera"];
	var detect_sign   = "<sup>D</sup>";
    var image_data        = {
        "img_id2"       : "",
        "edit"          : false,
        "detect_sign"   : "",
        "play_button"   : "",
        "swipe"         : false,
        "style"         : "",
        "type"          : entry["type"]
        };

    if (entry["date"])  { [day,month,year]  = entry["date"].split("."); }
    else                { [day,month,year]  = ["","",""]; }
    if (entry["time"])  { [hour,minute,sec] = entry["time"].split(":"); }
    else                { [hour,minute,sec] = ["","",""]; }

    // activate swiping in overlay for some views
    if (active_page == "TODAY" || active_page == "TODAY_COMPLETE") { image_data["swipe"] = true; }
    if (active_page == "FAVORITES") { image_data["swipe"] = true; }

    // individual image properties
    if (entry["type"] == "image") {
        image_data["edit"]            = true;
		image_data["lowres"]          = birdhouse_ImageURL(img_url + entry["directory"] + entry["lowres"]);
		image_data["hires"]           = birdhouse_ImageURL(img_url + entry["directory"] + entry["hires"]);
        image_data["hires_detect"]    = "";
        image_data["detect_sign"]     = "";
        image_data["favorite"]        = false;

        if (entry["favorit"] && (entry["favorit"] == 1 || entry["favorit"] == "1")) {
            image_data["favorite"]    = true;
            }

        //image_data["onclick"]         = "birdhouse_imageOverlay(\""+image_data["hires"]+"\",\""+image_data["description"]+"\");";

        if (active_page == "FAVORITES")     { image_data["description"] = entry["date"]+" ("+hour+":"+minute+")"; }
        else if (active_page == "TODAY")    { image_data["description"] = hour + ":" + minute + " (" + entry["similarity"] + "%)"; }
        else                                { image_data["description"] = entry["time"] + " (" + entry["similarity"] + "%)"; }

        // add detection labels to description if exists
        if (entry["hires_detect"] && entry["detections"] && entry["detections"].length > 0) {
            image_data["description_hires"]  = image_data["description"];
            image_data["description_hires"] += "[center][div style=align:center;][br/][hr/]";
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
                image_data["description_hires"] += "[div class=detection_label style=cursor:default;]&nbsp;"+bird_lang(key)+"&nbsp;("+info+")&nbsp;[/div]";
                });

            if (app_admin_allowed) {
                var cmd_edit_labels = "onclick=birdhouse_labels_edit('"+app_active_date+"','"+entry_id+"','"+app_active_cam+"','');";
                image_data["description_hires"] += "[div class=detection_label style=cursor:default "+cmd_edit_labels+"][img src='/birdhouse/img/edit.png' style='max-height:10px;max-width:10px;'][/div]";
                }

            image_data["description_hires"] += "[/div][/center]";
            image_data["detect_sign"]        = detect_sign;
            image_data["hires_detect"]       = birdhouse_ImageURL(img_url + entry["directory"] + entry["hires_detect"]);
            //image_data["onclick"]            = "birdhouse_imageOverlay(\""+image_data["hires"]+"\",\""+image_data["description_hires"]+"\", \"" +
            //                             birdhouse_ImageURL(img_url + entry["directory"] + entry["hires_detect"])+"\");";
            }
        // add link to comparision of image similarity if admin and view TODAY_COMPLETE
        if (admin && entry["compare"][1] != "000000" && active_page == "TODAY_COMPLETE") {
            let diff_image          = RESTurl + "compare/"+entry["compare"][0]+"/"+entry["compare"][1]+"/"+entry["similarity"]+"/image.jpg?"+entry["camera"];
            let onclick_diff        = "birdhouse_imageOverlay(\""+diff_image+"\",\"Difference Detection - "+entry["description"]+"\");";
            let onclick_difference  = entry["time"] +" (<u onclick='"+onclick_diff+"' style='cursor:pointer;'>";
            onclick_difference     += entry["similarity"] + "%</u>)";
    		image_data["description"]     = onclick_difference;
            }

        image_data["onclick"]      = "birdhouse_overlayShowById(\"" + entry_id + "\");";
        image_data["description"] += image_data["detect_sign"];
        }
    else if (entry["type"] == "label") {
		image_data["lowres"]        = birdhouse_ImageURL(img_url + entry["directory"] + entry["lowres"]);
		image_data["hires"]         = birdhouse_ImageURL(img_url + entry["directory"] + entry["hires_detect"]);
		image_data["description"]   = "<div class='detection_label image'>"+title+"</div>";
        image_data["onclick"]       = "birdhouse_imageOverlay(\""+image_data["hires"]+"\",\""+title+"\");";
        image_data["same_img_size"] = true;
        }
    else if (entry["type"] == "addon") {
		var [lowres, stream_uid]    = birdhouse_StreamURL(app_active_cam, entry["stream"], "stream_list_5", true, "THUMBNAIL #1");
		image_data["lowres"]        = lowres;
		image_data["hires_stream"]  = entry["stream_hires"];
		image_data["onclick"]       = "birdhousePrint_load(view=\"INDEX\", camera = \""+entry["camera"]+"\");";
		image_data["description"]   = lang("LIVESTREAM");
        }
    else if (entry["type"] == "camera") {
        image_data["description"] = title;
		var [lowres, stream_uid] = birdhouse_StreamURL(entry["id"], entry["video"]["stream"], "image_stream", true, "THUMBNAIL #2");
		image_data["lowres"]      = lowres;
		image_data["hires"]       = lowres;
		image_data["onclick"]     = "birdhouse_imageOverlay(\""+image_data["hires"]+"\",\""+image_data["description"]+"\");";
        }
    else if (entry["type"] == "detection") {
		image_data["description"] = title;
		var [lowres, stream_uid] = birdhouse_StreamURL(entry["id"], entry["video"]["stream_detect"], "image_stream_detect", true, "THUMBNAIL #3");
		image_data["lowres"]      = lowres;
		image_data["hires"]       = lowres;
		image_data["onclick"]     = "birdhouse_imageOverlay(\""+image_data["hires"]+"\",\""+image_data["description"]+"\", \"\", false, \"stream_overlay_"+entry["id"]+"\");";
        }
    else if (entry["type"] == "directory") {
        image_data["description"]  = "";
        image_data["detect_sign"]  = "";
        if (entry["detection"]) { image_data["detect_sign"] = detect_sign; }
    	if (entry["lowres"] == "" && entry["count_cam"] == 0) {
            image_data["description"] += "<b>" + entry["date"] + "</b><br/>";
            image_data["description"] += "<i>"+lang("NO_IMAGE_IN_ARCHIVE_2")+"</i>";
            image_data["img_missing"] = true;

            console.debug("birdhouse_ImageDisplayData - " + entry["date"]);
            console.debug(entry);
    	    }
        else {
            image_data["lowres"]      = birdhouse_ImageURL(img_url + entry["directory"] + entry["lowres"]);
            image_data["onclick"]     = "birdhousePrint_load(view=\"TODAY\", camera = \""+entry["camera"]+"\", date=\""+entry["datestamp"]+"\");";

            if (entry["count_cam"] != entry["count"]) {
                image_data["description"]  += "<b>" + entry["date"] + "</b>"+image_data["detect_sign"]+"<br/>" + entry["count_cam"] + " / " + entry["count"];
                if (entry["count_delete"] > 0) { image_data["description"] += "*"; }
                image_data["description"]  += "<br/><i>[" + Math.round(entry["dir_size"]*10)/10 + " MB]</i>";
                }
            else {
                image_data["description"]  += "<b>" + entry["date"] + "</b>"+image_data["detect_sign"]+"<br/>" + entry["count_cam"];
                image_data["description"]  += "<br/><i>[" + Math.round(entry["dir_size"]*10)/10 + " MB]</i>";
                }
            }
        }
    else if (entry["type"] == "thumbnail") {
		image_data["lowres"]            = birdhouse_ImageURL(img_url + entry["path"] + entry["thumbnail"]);
		image_data["hires"]             = birdhouse_ImageURL(img_url + entry["path"] + entry["thumbnail"]);
		image_data["onclick"]           = "";
		image_data["play_button"]       = "";
		image_data["description"]       = title;
		image_data["description_hires"] = title;
        image_data["edit"]              = false;
        }
    else if (entry["type"] == "thumbnail_selected") {
		image_data["lowres"]            = birdhouse_ImageURL(img_url + entry["path"] + entry["thumbnail_selected"]);
		image_data["hires"]             = birdhouse_ImageURL(img_url + entry["path"] + entry["thumbnail_selected"]);
		image_data["onclick"]           = "";
		image_data["play_button"]       = "";
		image_data["description"]       = title;
		image_data["description_hires"] = title;
        image_data["edit"]              = false;
        }
	else if (entry["type"] == "video" || entry["type"] == "video_org") {
		var note        = "";
		var video_file  = entry["video_file"];
		if (entry["video_file_short"] != undefined && entry["video_file_short"] != "") {
			if (video_short) {
				video_file  = entry["video_file_short"];
				note = "*";
        }	}
        var stream_server = "";
        if (settings["server"]["ip4_stream_video"] && settings["server"]["ip4_stream_video"] != "") {
            stream_server       = settings["server"]["ip4_stream_video"] + ":" + settings["server"]["port_video"];
            var streaming_url   = "http://"+stream_server+"/";
        }
        else {
            var this_server     = RESTurl_noport;
            stream_server       = this_server + ":" + settings["server"]["port_video"];
            var streaming_url   = stream_server + "/";
        }

		var image_title   = "";
		if (entry["title"] && entry["title"] != "") { image_title = "<b>" + entry["title"] + "</b>"; }
		else                                        { image_title = entry["camera"].toUpperCase() + ": " + entry["camera_name"]; }

		var image_file    = entry["thumbnail"];
        if (entry["type"] == "video" && entry["thumbnail_selected"] != undefined && entry["thumbnail_selected"] != "") {
    		image_file    = entry["thumbnail_selected"];
            }

		image_data["lowres"]      = birdhouse_ImageURL(img_url + entry["path"] + image_file);

		console.error(title + " ..." + image_data["lowres"]);

		image_data["hires"]       = birdhouse_ImageURL(streaming_url + video_file);
		image_data["description"] = "";
		if (title.indexOf("_") > 0)                 { image_data["description"] = entry["date"] + "[br/]" + image_title; }
		else                                        { image_data["description"] = title + "[br/]" + image_title; }

		image_data["onclick"]     = "birdhouse_videoOverlay(\""+image_data["hires"]+"\",\""+image_data["description"]+"\");";
		image_data["play_button"] = "<img src=\"birdhouse/img/play.png\" class=\"play_button\" style=\"min-width:auto;min-height:auto;\" onclick='"+image_data["onclick"]+"' />";
		entry["lowres"]           = image_file;

		if (admin) {
			var cmd_edit = "birdhousePrint_load(view=\"VIDEO_DETAIL\", camera=\""+app_active_cam+"\", date=\""+entry["date_start"]+"\");"
			image_data["description"] += "<br/><a onclick='"+cmd_edit+"' style='cursor:pointer;'>"+lang("EDIT")+"</a>"+note;
            }
        image_data["edit"] = true;
        }
    else {
        console.warn("Entry type not supported: " + entry["type"]);
        console.warn(entry);
        }

    // further image properties -> img_id2
    if (entry["type"] == "addon")                                           { image_data["img_id2"] = "stream_lowres_" + app_active_cam; }
    else if (entry["type"] == "detection")                                  { image_data["img_id2"] = "stream_detect_" + entry["id"]; }
    else                                                                    { image_data["img_id2"] += entry["directory"] + entry["lowres"];
                                                                              image_data["img_id2"] = image_data["img_id2"].replaceAll( "/", "_"); }

    // further image properties -> border style
    if (entry["favorit"] == 1 || entry["favorit"] == "1")                   { image_data["style"] = "border: 1px solid "+color_code["star"]+";"; }
	else if (entry["to_be_deleted"] == 1 || entry["to_be_deleted"] == "1")  { image_data["style"] = "border: 1px solid "+color_code["recycle"]+";"; }
	else if (entry["detections"] && entry["detections"].length > 0)         { image_data["style"] = "border: 1px solid "+color_code["object"]+";"; }
	else if (entry["detect"] == 1)                                          { image_data["style"] = "border: 1px solid "+color_code["detect"]+";"; }

    if (image_data["description"]) {
        image_data["description"] = image_data["description"].replaceAll("[br/]","<br/>");
        }
    return image_data;
    }

/*
* create a complete streaming URL out of the given data
*
* @param (string) camera: id of the selected camera
* @param (string) stream_url: relative URL of the stream
* @param (integer) stream_id: unique id of the stream
* @param (boolean) new_uid: create a new stream id
* @returns (string, integer): returns the streaming link and the unique stream id
*/
function birdhouse_StreamURL(camera, stream_url, stream_id, new_uid=false, source="") {
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
    console.debug("NEW Stream ID: " + stream_id_ext + " (" + source + ")");

	stream_link = stream_link.replaceAll("//", '/');
	stream_link = stream_link.replace(":/","://");
    return [stream_link, stream_id_ext];
    }

/*
* ensure the image url has the right format as sometimes the the format isn't correct for some reason
*
* @param (string) URL: image url to be converted
* @returns (string): correct image url
*/
function birdhouse_ImageURL(URL) {
	URL = URL.replaceAll("//","/");
	URL = URL.replace("http:/","http://");
	URL = URL.replace("https:/","https://");
	return URL;
	}

/*
* load an area of an image - return HTML
*
* @param (string) id: ...
* @param (string) URL: ...
* @param (area) coordinates: ...
* @returns (string): html for image to be loaded
*/
function birdhouse_ImageCropped(id, URL, coordinates, style="") {
    var html     = "<img id=\""+id+"_crop\" src=\""+URL+"\" style=\"display:none;\" />";
    html        += "<div id=\""+id+"_coordinates\" style=\"display:none;\" />" + JSON.stringify(coordinates) + "</div>";
    html        += "<canvas id=\""+id+"_canvas\" style=\""+style+"\"></canvas>";

    setTimeout(function() {
        birdhouse_ImageCropped_load(id);
        }, 1000);
    return html;
}

/*
* load an area of an image - load cropped image into HTML
*
* @param (string) id: ...
*/
function birdhouse_ImageCropped_load(id) {

    const img           = document.getElementById(id+'_crop');
    const canvas        = document.getElementById(id+'_canvas');
    const coordinates   = JSON.parse(document.getElementById(id+'_coordinates').innerHTML);
    const ctx           = canvas.getContext('2d');

    //img.onload = function() {
      const imgWidth = img.naturalWidth;
      const imgHeight = img.naturalHeight;

      // Normalized coordinates (0 to 1)
      const normX = coordinates[0]; // 0.1;    // 10% from the left
      const normY = coordinates[1]; // 0.2;    // 20% from the top
      //const normW = coordinates[2]; // 0.5;    // 50% of image width
      //const normH = coordinates[3]; // 0.4;    // 40% of image height
      const normW = coordinates[2] - coordinates[0]; // 0.5;    // 50% of image width
      const normH = coordinates[3] - coordinates[1]; // 0.4;    // 40% of image height

      // Convert to absolute pixels
      const cropX = normX * imgWidth;
      const cropY = normY * imgHeight;
      const cropWidth = normW * imgWidth;
      const cropHeight = normH * imgHeight;

      // Set canvas size to match crop area
      canvas.width = cropWidth;
      canvas.height = cropHeight;

      // Draw cropped portion
      ctx.drawImage(
        img,
        cropX, cropY,
        cropWidth, cropHeight,
        0, 0,
        cropWidth, cropHeight
      );
    //};
}



app_scripts_loaded += 1;