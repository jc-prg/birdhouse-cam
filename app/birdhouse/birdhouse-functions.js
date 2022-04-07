//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// additional functions 
//--------------------------------------

function birdhouse_edit_field(id, field, type="input", options="", data_type="string") {
    var fields = field.split(":");
    var data   = "";
    var html   = "";
    var style  = "";

    if (fields.length == 1) { data = app_data["DATA"][fields[0]]; }
    else if (fields.length == 2) { data = app_data["DATA"][fields[0]][fields[1]]; }
    else if (fields.length == 3) { data = app_data["DATA"][fields[0]][fields[1]][fields[2]]; }
    else if (fields.length == 4) { data = app_data["DATA"][fields[0]][fields[1]][fields[2]][fields[3]]; }
    else if (fields.length == 5) { data = app_data["DATA"][fields[0]][fields[1]][fields[2]][fields[3]][fields[4]]; }
    else if (fields.length == 6) { data = app_data["DATA"][fields[0]][fields[1]][fields[2]][fields[3]][fields[4]][fields[5]]; }

    if (data_type == "json") { data = JSON.stringify(data); }
    if (data_type == "integer" || data_type == "float") { style += "width:60px;" }
    if (type == "input") {
        html += "<input id='"+id+"' value='"+data+"' style='"+style+"' onblur='birdhouse_edit_check_values(\""+id+"\",\""+data_type+"\");'>";
    }
    else if (type == "select") {
        var values = options.split(",");
        html += "<select id='"+id+"'>";
        for (var i=0;i<values.length;i++) {
            if (data == true || data == false) { data_str = data.toString(); }
            else { data_str = data; }
            if (data_str == values[i])  { html += "<option selected='selected'>"+values[i]+"</option>"; }
            else                        { html += "<option>"+values[i]+"</option>"; }
        }
        html += "</select>";
    }
    html += "<input id='"+id+"_data' style='display:none' value='"+field+"'>\n";
    html += "<input id='"+id+"_data_type' style='display:none' value='"+data_type+"'>\n";
    return html;
}

function birdhouse_edit_save(id, id_list, text="") {
    var ids = id_list.split(":");
    var html = "<button onclick='birdhouse_edit_send(\""+id_list+"\");' style='background:gray;width:100px;'>"+lang("SAVE")+"</button>";
    return html;
}

function birdhouse_edit_check_values(id, data_type) {
    if (!document.getElementById(id)) {
        console.error("Element '"+id+"' doesn't exist!");
        return [true, "Element '"+id+"' doesn't exist!"];
        }
    var input = document.getElementById(id);
    var value = input.value;
    var error = false;
    var error_msg = "";

    input.style.backgroundColor = "white";

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

function birdhouse_edit_send(id_list) {
    var ids = id_list.split(":");
    var info = "";
    var error = false;
    var error_msg = "Error in the data fields:\n\n";
    for (var i=0;i<ids.length;i++) {
        if (document.getElementById(ids[i])) {
            var data_type = document.getElementById(ids[i]+"_data_type").value;
            var field_name = document.getElementById(ids[i]+"_data").value.split(":");
            var field_data = document.getElementById(ids[i]).value;
            field_name = field_name[(field_name.length-1)];

            var field_error = birdhouse_edit_check_values(ids[i], data_type);
            if (field_error[0]) { error = true; error_msg += field_error[1]; }

            info += document.getElementById(ids[i]+"_data").value + "==";
            info += encodeURI(field_data) + "||";
            info += document.getElementById(ids[i]+"_data_type").value;
            info += "/";
        }
        else {
            console.error("Could not find element: "+ids[i]);
        }
    }
    if (error) { alert(error_msg); }
    else { appFW.requestAPI('POST',[ "edit_presets", info ],"",birdhouse_edit_done,"",""); }
}

function birdhouse_edit_done(data) {

    appMsg.alert("Done");
}


function birdhouse_initTooltip() {
	tooltip_mode     	= "other";
	tooltip_width    	= 160;
	tooltip_height   	= 100;
	tooltip_offset_height	= 42;
	tooltip_offset_width	= -180;

	button_tooltip = new jcTooltip("button_tooltip") ;
	button_tooltip.settings( tooltip_mode, tooltip_width, tooltip_height, tooltip_offset_height, tooltip_offset_width );	
	}

function birdhouse_tooltip( tooltip_element, tooltip_content, name, left="" ) {
	result = button_tooltip.create( tooltip_element, tooltip_content, name, left );
	return result;
	}


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
        for (let key in this.style_table) { this.style_table_string += key+":"+this.style_table[key]+";"; }
        for (let key in this.style_rows)  { this.style_rows_string  += key+":"+this.style_rows[key]+";"; }
        for (let key in this.style_cells) { this.style_cells_string += key+":"+this.style_cells[key]+";"; }
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


function birdhouse_imageOverlay(filename, description="", favorit="", to_be_deleted="") {

        var overlay = "<div id=\"overlay_content\" class=\"overlay_content\" onclick=\"birdhouse_overlayHide();\"><!--overlay--></div>";
        setTextById("overlay_content",overlay);
        document.getElementById("overlay").style.display         = "block";
        document.getElementById("overlay_content").style.display = "block";
        document.getElementById("overlay_parent").style.display  = "block";
        
        description = description.replace(/\[br\/\]/g,"<br/>");
        html  = "";
        html += "<div id=\"overlay_image_container\">";
        html += "<div id=\"overlay_close\" onclick='birdhouse_overlayHide();'>[X]</div>";
        html += "<img id='overlay_image' src='"+filename+"'>";
        html += "<br/>&nbsp;<br/>"+description+"</div>";
        document.getElementById("overlay_content").innerHTML = html;
        
        myElement = document.getElementById("overlay_content");
	    pz = new PinchZoom.default(myElement);
/*
	    pz.zoomFactor = 1;
	    pz.offset = { x: 0, y: 0 };
	    pz.update();
*/
	    // check, how to destroy ...
	}

function birdhouse_videoOverlay(filename, description="", favorit="", to_be_deleted="") {
        check_iOS = iOS();
        if (check_iOS == true) {
          window.location.href = filename;
          }
        else {
          document.getElementById("overlay").style.display = "block";
          document.getElementById("overlay_content").style.display = "block";
          document.getElementById("overlay_parent").style.display  = "block";
          
          description = description.replace(/\[br\/\]/g,"<br/>");
          html  = "";
          html += "<div id=\"overlay_close\" onclick='birdhouse_overlayHide();'>[X]</div>";
          html += "<div id=\"overlay_image_container\">";
          html += "<video id='overlay_video' src=\"" + filename + "\" controls>Video not supported</video>"
          html += "<br/>&nbsp;<br/>"+description+"</div>";

          document.getElementById("overlay_content").innerHTML = html;
          }
	}

function birdhouse_videoOverlayToggle(status="") {
        video_edit1 = document.getElementById("camera_video_edit");
        video_edit2 = document.getElementById("camera_video_edit_overlay");
        if (video_edit1 != null) {
        	if (status == "") {
	        	if (video_edit1.style.display == "none")	{ video_edit1.style.display = "block"; video_edit2.style.display = "block"; }
        		else						{ video_edit1.style.display = "none";  video_edit2.style.display = "none"; }
        		}
        	else if (status == false) { video_edit1.style.display = "none";  video_edit2.style.display = "none"; }
        	else if (status == true)  { video_edit1.style.display = "block"; video_edit2.style.display = "block"; }
        	}
	else {
	        console.error("birdhouse_videoOverlayToggle: Video edit doesn't exist.");
		}
	}

function birdhouse_overlayHide() {
       document.getElementById("overlay").style.display = "none";
       document.getElementById("overlay_content").style.display = "none";
       document.getElementById("overlay_parent").style.display = "none";
/*
	    pz.zoomFactor = 2;
	    pz.lastScale = 1;
	    pz.offset = { x: 0, y: 0 };
	    pz.initialOffset = { x: 0, y: 0 };
        pz.setupMarkup();
        pz.bindEvents();
        pz.update();
        pz.enable();
*/
       }


function birdhouse_groupToggle(id) {
        if (document.getElementById("group_"+id).style.display == "none") {
                document.getElementById("group_"+id).style.display = "block";
            	if (document.getElementById("group_intro_"+id)) {
            	    document.getElementById("group_intro_"+id).style.display = "block";
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
	                        img.src  = img_file;
	                        }
		   }	}
		}
	else {
        	document.getElementById("group_"+id).style.display = "none";
        	if (document.getElementById("group_intro_"+id)) { document.getElementById("group_intro_"+id).style.display = "none"; }
        	document.getElementById("group_link_"+id).innerHTML = "(+)";
		}
	}


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

function toggleVideoEdit() {
        video_edit1 = document.getElementById("camera_video_edit");
        video_edit2 = document.getElementById("camera_video_edit_overlay");
        if (video_edit1 != null) {
        	if (video_edit1.style.display == "none")	{ 
        		video_edit1.style.display = "block"; 
        		video_edit2.style.display = "block"; 
        		}
        	else						{ 
        		video_edit1.style.display = "none"; 
        		video_edit2.style.display = "none"; 
        		}
        	}
	else {
	        console.error("toggleVideoEdit: Video edit doesn't exist.");
		}
	}

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

//-----------------------------------------

birdhouse_initTooltip();

