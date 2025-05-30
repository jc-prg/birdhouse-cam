//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// additional functions 
//--------------------------------------

/*
* The following 4 functions are used to create a dialog to edit parameters of different types,
* to validate the input and to hand it over to the API functions. This first one creates an input field.
*
* @param (string) id: unique id for input element
* @param (string) field: field id to grab existing information from;
                         option (1) data from app_data["SETTINGS"] - list all key names separated by ":"
                         option (2) data from this field - format the value "this:<value>"
* @param (string) type: type of input field, options are: input, select, select_dict, select_dict_sort, range, boolean
* @param (Any) options: list of possible options for select types
                        option (1) for select use a string with comma separated values
                        option (2) for select_dict* use a dict = { "value": "description" }
* @param (string) data_type: type of date for verification, options are: string, integer, boolean, float, json
* @param (string) on_change: javascript command to be executed when value changes
*/
function birdhouse_edit_field(id, field="", type="input", options="", data_type="string", on_change="") {
    var fields = field.split(":");
    var settings = app_data["SETTINGS"];
    var data   = "";
    var html   = "";
    var style  = "";
    var step   = "1";

    if (field != "" && fields[0] == "this") {
        data = fields[1];
        }
    else if (field != "") {
        if (fields.length == 1)      { data = settings[fields[0]]; }
        else if (fields.length == 2) { data = settings[fields[0]][fields[1]]; }
        else if (fields.length == 3) { data = settings[fields[0]][fields[1]][fields[2]]; }
        else if (fields.length == 4) { data = settings[fields[0]][fields[1]][fields[2]][fields[3]]; }
        else if (fields.length == 5) { data = settings[fields[0]][fields[1]][fields[2]][fields[3]][fields[4]]; }
        else if (fields.length == 6) { data = settings[fields[0]][fields[1]][fields[2]][fields[3]][fields[4]][fields[5]]; }
        }

    if (data_type == "json")                            { data = JSON.stringify(data); }
    if (data_type == "integer" || data_type == "float") { style += "width:60px;" }

    if (type == "input") {
        html += "<input id='"+id+"' value='"+data+"' style='"+style+"' onblur='birdhouse_edit_check_values(\""+id+"\",\""+data_type+"\");' onchange='"+on_change+"'>";
        }
    else if (type == "select_dict" || type == "select_dict_sort") {

        if (type == "select_dict_sort") {
            var options_sorted = Object.entries(options);
            options_sorted.sort(function(a, b) { return a[1] - b[1]; });
            var option_keys = options_sorted.map((e) => { return e[0] });
            }
        else {
            var option_keys = "";
            }

        var exists = false;
        html += "<select id='"+id+"' onchange='"+on_change+"' style='max-width:220px;'>";
        html += "<option value=''>(empty)</option>";
        if (data == true || data == false)  { data_str = data.toString(); }
        else                                { data_str = data; }

        if (Object.prototype.toString.call(options) === '[object Array]') {
            for (var i=0;i<options.length;i++) {
                key = options[i];
                if (data_str == key)  { html += "<option selected='selected' value='"+key+"'>"+key+"</option>"; exists = true; }
                else                  { html += "<option value='"+key+"'>"+key+"</option>"; }
                }
            }
        else  {
            if (option_keys == "") { option_keys = Object.keys(options); }
            //Object.entries(option_keys).forEach (key => {
            for (var a=0;a<option_keys.length;a++) {
            //option_keys.forEach (key => {
                key = option_keys[a];
                if (data_str == key)  { html += "<option selected='selected' value='"+key+"'>"+options[key]+"</option>"; exists = true; }
                else                  { html += "<option value='"+key+"'>"+options[key]+"</option>"; }
                }
                //});
            }
        if (!exists && data_str != "") {
            html += "<option selected='selected'>"+data_str+"</option>";
            }
        html += "</select>";
        }
    else if (type == "select") {

        var values;
        if (typeof options === 'string')    { values = options.split(","); }
        else                                { values = options; }

        var exists = false;
        html += "<select id='"+id+"' onchange='"+on_change+"'>";
        if (data == true || data == false)  { data_str = data.toString(); }
        else                                { data_str = data; }

        for (var i=0;i<values.length;i++) {
            if (data_str == values[i])  { html += "<option selected='selected'>"+values[i]+"</option>"; exists = true;}
            else                        { html += "<option>"+values[i]+"</option>"; }
            }
        if (!exists) {
            html += "<option selected='selected'>"+data_str+"</option>";
            }
        html += "</select>";
        }
    else if (type == "boolean") {
        style     = "width:50px";
        on_value  = "if (this.value == 0)      { document.getElementById(\""+id+"_range\").value = 0; } ";
        on_value += "else if (this.value == 1) { document.getElementById(\""+id+"_range\").value = 1; }";
        on_value += "if (this.value.toLowerCase == \"false\")     { document.getElementById(\""+id+"_range\").value = 0; } ";
        on_value += "else if (this.value.toLowerCase == \"true\") { document.getElementById(\""+id+"_range\").value = 1; }";

        on_set    = "if (this.value == 0) { document.getElementById(\""+id+"\").value = false; } else { document.getElementById(\""+id+"\").value = true; }";
        on_set   += "this.className=\"bh-slider set\";";

        html += "<div class='bh-slidecontainer' style='float:left;width:100px;height:auto;'>";
        html += "<input id='"+id+"_range' class='bh-slider undef' type='range' name='' min='0' max='1' step='1' style='"+style+"' onchange='"+on_set+on_change+"'>";
        html += "</div><div style='float:left;margin-left:12px;'>";
        html += "<input id='"+id+"' class='bh-slider-value' style='width:30px;' onchange='"+on_value+"'>";
        html += "</div>";
        }
    else if (type == "range") {
        on_value  = "document.getElementById(\""+id+"_range\").value = this.value;";
        on_set    = "document.getElementById(\""+id+"\").value = this.value;";
        on_set   += "this.className=\"bh-slider set\";";

        range = options.split(":");
        if (options.indexOf(".") > 0)                       { step = "0.1"; }
        else if (range.length > 2 && range[2] == "float")   { step = "0.1"; }
        if (data_type == "float")                           { step = "0.1"; }

        style = "width:100px";
        if (range[0] == 0 && range[1] == 1) { style = "width:50px;"; }

        html += "<div class='bh-slidecontainer' style='float:left;width:100px;height:auto;'>";
        html += "<input id='"+id+"_range' class='bh-slider undef' type='range' name='' min='"+range[0]+"' max='"+range[1]+"' step='"+step+"' style='"+style+"' onchange='"+on_set+on_change+"'>";
        html += "</div><div style='float:left;margin-left:12px;'>";
        html += "<input id='"+id+"' class='bh-slider-value' style='width:30px;' onchange='"+on_value+"'>";
        html += "</div>";
        }
    else {
        html += "<font style='color:"+header_color_error+"'><i>wrong edit field type</i></font>";
        }
    html += "<input id='"+id+"_data' style='display:none' value='"+field+"'>\n";
    html += "<input id='"+id+"_data_type' style='display:none' value='"+data_type+"'>\n";
    return html;
}

/*
* create a button to save all fields defined in an id list
*
* @param (string) id: id for the button element
* @param (string) id_list: ":" separated list of field ids with values to be saved
* @param (string) camera: camera id
* @param (string) text: not used yet
*/
function birdhouse_edit_save(id, id_list, camera="", text="") {
    var ids = id_list.split(":");
    var html = "<button id='"+id+"' onclick='birdhouse_edit_send(\""+id_list+"\", \""+camera+"\");' style='background:gray;width:100px;float:left;'>"+lang("SAVE")+"</button>";
    return html;
}

/*
* validate if the input field with the given id contains content of a specific content type
*
* @param (string) id: id of field to be checked
* @param (string) data_type: expected date type - options are: string, integer, boolean, float, json
*/
function birdhouse_edit_check_values(id, data_type) {
    if (!document.getElementById(id)) {
        console.error("Element '"+id+"' doesn't exist!");
        return [true, "Element '"+id+"' doesn't exist!"];
        }
    var input = document.getElementById(id);
    var value = input.value;
    var error = false;
    var error_msg = "";

    input.style.backgroundColor = "";

    if (data_type == "json") {
        try { var json_test = JSON.parse(value); }
        catch(err) {
            error = true;
            error_msg += id.toUpperCase() + " isn't a correct JSON format.\n";
            input.style.backgroundColor = "#ffaaaa";
        }
    }
    if (data_type == "float") {
        console.log(parseFloat(value));
        if (isNaN(parseFloat(value))) {
            error = true;
            error_msg += id.toUpperCase() + " isn't a float number.\n";
            input.style.backgroundColor = "#ffaaaa";
        }
        else {
            input.value = parseFloat(value);
        }
    }
    if (data_type == "integer") {
        if (isNaN(parseInt(value)) || parseInt(value) != parseFloat(value)) {
            error = true;
            error_msg += id.toUpperCase() + " isn't an integer number.\n";
            input.style.backgroundColor = "#ffaaaa";
        }
        else {
            input.value = parseInt(value);
        }
    }
    return [error, error_msg ];
}

/*
* collect all data and handover to an API request to save all data from the fields in the id_list
*
* @param (string) id_list: ":" separated list of field ids with values to be saved
* @param (string) camera: camera id
*/
function birdhouse_edit_send(id_list, camera) {
    var ids = id_list.split(":");
    var info = "";
    var error = false;
    var error_msg = "Error in the data fields:\n\n";
    for (var i=0;i<ids.length;i++) {
        console.info(i+"_"+ids[i]);
        if (ids[i] != "" && document.getElementById(ids[i])) {
            var data_type = document.getElementById(ids[i]+"_data_type").value;
            var field_name = document.getElementById(ids[i]+"_data").value.split(":");
            var field_data = document.getElementById(ids[i]).value;

            field_name = field_name[(field_name.length-1)];
            field_data = field_data.replaceAll("/dev/v4l/by-id/", "-dev-v4l-by-id-")
            field_data = field_data.replaceAll("/dev/", "-dev-")

            var field_error = birdhouse_edit_check_values(ids[i], data_type);
            if (field_error[0]) { error = true; error_msg += field_error[1]; }

            info += document.getElementById(ids[i]+"_data").value + "==";
            info += encodeURI(field_data) + "||";
            info += document.getElementById(ids[i]+"_data_type").value;
            info += "///";
        }
        else if (ids[i] != "") {
            console.error("Could not find element: "+ids[i]);
        }
    }
    if (error) { alert(error_msg); }
    else { birdhouse_editData(info, camera); }
}

function birdhouse_edit_other(command, description) {
    var html = "<button onclick='"+command+"' style='background:gray;width:100px;float:left;'>"+description+"</button>";
    return html;
}

/*
* The following 2 functions are used to initialize and integrate the tool tip from jc://modules/ for this app.
* At the moment it's used in the form of a speech bubbel for range deletion.
*/
function birdhouse_initTooltip() {
	tooltip_mode     	= "other";
	tooltip_width    	= 160;
	tooltip_height   	= 100;
	tooltip_offset_height	= 42;
	tooltip_offset_width	= -180;

	button_tooltip = new jcTooltip("button_tooltip");
	button_tooltip.settings( tooltip_mode, tooltip_width, tooltip_height, tooltip_offset_height, tooltip_offset_width );	
	}

function birdhouse_tooltip( tooltip_element, tooltip_content, name, left="" ) {
	result = button_tooltip.create( tooltip_element, tooltip_content, name, left );
	return result;
	}

/*
* Check all images of the current view if their similarity is above the threshold and sets the display to
* "block" if yes and to "none" if not.
*/
function birdhouse_view_images_threshold(threshold) {
    group_list = document.getElementById("group_list").innerHTML.split(" ");
    image_list = [];
    image_list_active = [];
    for (var i=0;i<group_list.length;i++) {
        image_ids_in_group = document.getElementById("group_ids_"+group_list[i]).innerHTML.split(" ");
        image_list = image_list.concat(image_ids_in_group);
        for (a=0;a<image_ids_in_group.length;a++) {
            if (image_list[a] != "") {
                image_threshold = document.getElementById(image_ids_in_group[a]+"_similarity");
                image_container = image_ids_in_group[a] + "_container";
                if (image_threshold && image_threshold.value+0 <= threshold+0) {
                    image_list_active.push(image_ids_in_group[a]);
                    elementVisible(image_container);
                }
                else {
                    elementHidden(image_container);
                }
            }
        }
    }

    console.log("info_set_threshold: THRESHOLD=" + threshold + "%, FOUND=" + image_list_active.length + ", TOTAL=" + image_list.length)
    setTextById("info_set_threshold", "Threshold = " + threshold + "%: " + image_list_active.length + " of " + image_list.length + " selected.")
    //alert("birdhouse_view_images_threshold: threshold=" + threshold + "; all=" + image_list.length + "; select=" + image_list_active.length);
}

/*
* Check all images of the current view if the given object is detected in the image and sets the display to
* "block" if yes and to "none" if not.
*/
function birdhouse_view_images_objects(object) {

    if (!document.getElementById("group_list")) { return; }
    group_list += " TODAY_FAVORITE";
    group_list  = document.getElementById("group_list").innerHTML.split(" ");
    image_list  = [];
    image_list_active = [];

    var prefix = "";
    if (app_active_page == "FAVORITES")      { prefix = "FAVORITES_"; }
    if (app_active_page == "TODAY_COMPLETE") { prefix = "TODAY_COMPLETE_"; }

    for (var i=0;i<group_list.length;i++) {
        image_ids_in_group = document.getElementById("group_ids_"+prefix+group_list[i]).innerHTML.split(" ");
        image_list = image_list.concat(image_ids_in_group);
        }

    console.debug("birdhouse_view_images_objects() -> image_list");
    console.debug(image_list);

    for (a=0;a<image_list.length;a++) {
        if (image_list[a] != "") {
            image_objects = document.getElementById(image_list[a]+"_objects");
            image_container     = image_list[a] + "_container";
            image_container_fav = image_list[a] + "_FAV_container";
            if (object == "EMPTY" && image_objects != undefined && image_objects.value.indexOf(",") < 0) {
                image_list_active.push(image_list[a]);
                elementVisible(image_container);
                elementVisible(image_container_fav);
                }
            else if ((image_objects && image_objects.value && image_objects.value.indexOf(object) >= 0) || (object == "")) {
                image_list_active.push(image_list[a]);
                elementVisible(image_container);
                elementVisible(image_container_fav);
            }
            else {
                elementHidden(image_container);
                elementHidden(image_container_fav);
            }
        }

    }

    console.debug("birdhouse_view_images_objects: OBJECT=" + object + ", FOUND=" + image_list_active.length  + ", TOTAL=" + image_list.length);
}


/*
* The following 2 functions are use to format and display content in the header and footer frame.
*/
function birdhouse_frameHeader(title, status_id="") {
    if (status_id != "") {
        title = "<div id='"+status_id+"' style='float:left;'><div id='black'></div></div>" + title;
    }
    setTextById(app_frame_header, "<center><h2>" + title + "</h2></center>");
}

function birdhouse_frameFooter(content) {

    setTextById(app_frame_index, "<center>" + content + "</center>");
}

/*
* Class to create an easy table with two columns in a predefined and adaptable format.
*
* Usage:
*   var tab = birdhouse_table();
*   tab.style_rows["padding"] = "5px";
*   tab.update_settings();
*
*   var html = "";
*   html += tab.start();
*   html += tab.row("Content column 1", "Content column 2");
*   html += tab.end();
*/
function birdhouse_table () {

    this.style_table_string = "";
    this.style_table = {
        "width" : "100%",
    };
    this.style_rows_string = "";
    this.style_rows = {}
    this.style_cells_string = "";
    this.style_cells = {
        "vertical-align" : "middle",
    };

    this.update_settings = function () {
        this.style_table_string = "";
        for (let key in this.style_table) {
            var setting_string = key+":"+this.style_table[key]+";";
            this.style_table_string += setting_string;
        }
        this.style_rows_string = "";
        for (let key in this.style_rows)  {
            var setting_string = key+":"+this.style_rows[key]+";";
            this.style_rows_string += setting_string;
        }

        this.style_cells_string = "";
        for (let key in this.style_cells) {
            var setting_string = key+":"+this.style_cells[key]+";";
            this.style_cells_string += setting_string;
        }
    }

	this.start	= function () {
	    this.update_settings();
	    return "<table style='"+this.style_table_string+"'>";
	}

	this.row	= function (td1, td2=false) {
	    this.update_settings();
	    if (td2 != false) { return "<tr style='"+this.style_rows_string+"'><td width='30%' style='"+this.style_cells_string+"'>" + td1 + "</td><td width='70%' style='"+this.style_cells_string+"'>" + td2 + "</td></tr>"; }
	    else              { return "<tr style='"+this.style_rows_string+"'><td style='"+this.style_cells_string+"' colspan=\"2\">" + td1 + "</td></tr>"; }
	}

	this.end	= function () {
	    return "</table>";
	}
}

/*
* Create link list for the footer out of link information from API response
*/
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

/*
* Check if the app runs on iOS
*
* @returns (boolean): true if runs on iOS
*/
function iOS() {
  return [
    'iPad Simulator',
    'iPhone Simulator',
    'iPod Simulator',
    'iPad',
    'iPhone',
    'iPod'
  ].includes(navigator.platform)
  // iPad on iOS 13 detection
  || (navigator.userAgent.includes("Mac") && "ontouchend" in document)
}

/*
* Show / hide video editing overlay (toggle depending on current status)
*/
function toggleVideoEdit() {
        video_edit1 = document.getElementById("camera_video_edit");
        video_edit2 = document.getElementById("camera_video_edit_overlay");
        if (video_edit1 != null) {
        	if (video_edit1.style.display == "none") {
        		video_edit1.style.display = "block"; 
        		video_edit2.style.display = "block"; 
        		}
        	else {
        		video_edit1.style.display = "none"; 
        		video_edit2.style.display = "none";

               var video = document.getElementById("video");
               if (video != undefined) { video.pause(); }
        		}
        	}
	else {
	        console.error("toggleVideoEdit: Video edit doesn't exist.");
		}
	}

/*
* get URL parameters
*
* @params (string) url: url to identify parameters from
*/
function getUrlParams(analyze_url) {
    const url = new URL(analyze_url);

    // Get query parameters from the URL
    const params = new URLSearchParams(url.search);

    // Create an empty object to store the parameters
    let paramDict = {};

    // Loop through each parameter and add it to the object
    params.forEach((value, key) => {
        paramDict[key] = value;
        });

    return paramDict;
    }

//-----------------------------------------

var loadJS = function(url, implementationCode, location) {
    //url is URL of external file, implementationCode is the code
    //to be called from the file, location is the location to
    //insert the <script> element

    //var scriptTag = document.createElement('script');
    var scriptTag = document.getElementById('videoplayer-script');
    scriptTag.src = url;

    scriptTag.onload = implementationCode;
    scriptTag.onreadystatechange = implementationCode;

    location.appendChild(scriptTag);
}

birdhouse_initTooltip();

app_scripts_loaded += 1;