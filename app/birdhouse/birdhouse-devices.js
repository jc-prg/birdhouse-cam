//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// show and edit device information
//--------------------------------------


var birdhouse_device_list = [];
var birdhouse_camera_interval = {};

function birdhouseDevices( title, data, show_settings=true ) {
	var html = "";
	var index = [];

    var [settings, info] = birdhouseDevices_cameras(data);
    html += settings;
    index.push(info);

    var [settings, info] = birdhouseDevices_weather(data);
    html += settings;
    index.push(info);

    var [settings, info] = birdhouseDevices_sensors(data);
    html += settings;
    index.push(info);

    var [settings, info] = birdhouseDevices_microphones(data);
    html += settings;
    index.push(info);

    if (show_settings) {
        var html_index = birdhouseDevices_status(index=index, show_button=true);
        setTextById(app_frame_content, html_index + html);
        setTextById(app_frame_header, "<center><h2>" + lang("DEVICES") + "</h2></center>");
    }
    else {
        var html_index = birdhouseDevices_status(index=index, show_button=false);
        return html_index;
    }
}

function birdhouseDevices_status(index, show_button) {
	var tab     = new birdhouse_table();
	tab.style_rows["height"] = "27px";
	tab.style_cells["width"] = "50%";

    var html_index = "";
    if (show_button) {
        html_index += "<div class='camera_info'>";
        html_index += "<div class='camera_info_image'>&nbsp;<br/>";
        html_index +=  "<div id='loading_img'><img src='"+app_loading_image+"' style='width:50%;'></div>";
        html_index += "<br/>&nbsp;</div>";
        html_index += "<div class='camera_info_text'>";
    }

    html_index += tab.start();
    birdhouse_device_list = [];
    for (var i=0;i<index.length;i++) {
        Object.keys(index[i]).forEach(key => {
            birdhouse_device_list.push(index[i][key]["group"]);
            var onclick = "birdhouseDevices_openOne('"+index[i][key]["group"]+"')";
            var button = "";
            var action = "<div style='float:left;'>";
            if (show_button) {
                button = "<button onclick=\""+onclick+"\" class=\"button-video-edit\">&nbsp;"+lang("SHOW")+"&nbsp;</button>";
                action = "<div style='float:left;'>" + button + "&nbsp;&nbsp;&nbsp;</div><div style='float:left;'>";
                }
            for (var a=0; a<index[i][key]["status"].length;a++) {
                action += "<div id='status_" + index[i][key]["status"][a] + "_" + index[i][key]["id"] + "' style='float:left;'><div id='black'></div></div>";
            }
            for (var a=index[i][key]["status"].length; a<3; a++) {
                action += "<div id='status_" + index[i][key]["status"][a] + "_" + index[i][key]["id"] + "' style='float:left;height:24px;width:24px;'></div>";
            }
            if (!show_button && (index[i][key]["type"] == "camera" || index[i][key]["type"] == "microphone")) {
                action += "<div style='float:left;padding:5px;'><font id='show_stream_count_" + index[i][key]["id"] + "'>0</font> Streams</div>";
            }
            else if (index[i][key]["type"] == "camera" || index[i][key]["type"] == "microphone") {
                action += "<br/><div style='padding:5px;width:100%;'><font id='show_stream_count_" + index[i][key]["id"] + "'>0</font> Streams</div>";
            }
            action += "</div>";
            html_index += tab.row(key, action);
        });
    }
    html_index += tab.end();
    html_index += "<br/>&nbsp;"
    if (show_button) {
        html_index += "</div></div>";
        }
    return html_index;
}

function birdhouseDevices_cameras(data) {
	var cameras	= data["SETTINGS"]["devices"]["cameras"];
	var admin 	= data["STATUS"]["admin_allowed"];
	var html	= "";
	var index_info = {};
	var tab     = new birdhouse_table();
	tab.style_rows["height"] = "27px";
	tab.style_cells["vertical-align"] = "top";

	for (let camera in cameras) {
    	var onclick  = "birdhouse_createDayVideo('"+camera+"');";
    	var onclick2 = "birdhouse_reconnectCamera('"+camera+"');";
    	var info    = {};
		var id_list = "";

	    Object.assign(info, cameras[camera]);
	    info["type"]  = "detection";
	    info["id"]    = camera;
	    camera_name   = camera.toUpperCase() + ": " + cameras[camera]["name"];
	    camera_stream = birdhouse_Image(camera_name, info);
	    index_info[camera_name] = {};
	    index_info[camera_name]["active"] = cameras[camera]["active"];
	    index_info[camera_name]["group"]  = camera;
	    index_info[camera_name]["id"]     = camera;
	    index_info[camera_name]["type"]   = "camera";
	    index_info[camera_name]["status"] = ["active", "error", "error_record"];

	    resolution_max = cameras[camera]["image"]["resolution_max"];
	    resolution_act = cameras[camera]["image"]["resolution_current"];

		if (cameras[camera]["active"] == false || cameras[camera]["active"] == "false") {
		    camera_name += " &nbsp; <i>(inactive)</i>";
            }
	    html_temp = "<div class='camera_info'><div class='camera_info_image'>";
	    if (cameras[camera]["active"])
	         { html_temp  += camera_stream; }
	    else { html_temp  += lang("CAMERA_INACTIVE"); }
		html_temp += "</div>";
		html_temp += "<div class='camera_info_text'>";

		html_temp += tab.start();
		html_temp += tab.row("Name:", birdhouse_edit_field(id="set_name_"+camera, field="devices:cameras:"+camera+":name", type="input"));
        var options = app_data["STATUS"]["system"]["video_devices_02"];
        html_temp += tab.row("Source:", birdhouse_edit_field(id="set_source_"+camera, field="devices:cameras:"+camera+":source", type="select_dict", options=options, data_type="string"));
        html_temp += tab.row("Active:", birdhouse_edit_field(id="set_active_"+camera, field="devices:cameras:"+camera+":active", type="select", options="true,false", data_type="boolean"));
		html_temp += tab.end();
		html_temp += "&nbsp;<br/>";
		id_list += "set_name_"+camera+":set_active_"+camera+":set_source_"+camera+":";

        html_entry = tab.start();
		html_entry += tab.row("- Resolution:",              birdhouse_edit_field(id="set_resolution_"+camera, field="devices:cameras:"+camera+":image:resolution", type="input", options="", data_type="string"));
		html_entry += tab.row("&nbsp;",                     "current=(" + resolution_act + "), max=(" + resolution_max + ")");
		html_entry += tab.row("- Black &amp; White:",       birdhouse_edit_field(id="set_black_white_"+camera, field="devices:cameras:"+camera+":image:black_white", type="select", options="false,true", data_type="boolean"));
		html_entry += tab.row("- Rotation:",                birdhouse_edit_field(id="set_rotation_"+camera, field="devices:cameras:"+camera+":image:rotation", type="select", options="0,90,180,270", data_type="integer"));
		html_entry += tab.row("- Crop (relative):",         birdhouse_edit_field(id="set_crop_"+camera, field="devices:cameras:"+camera+":image:crop", type="input", options="", data_type="json"));
		html_entry += tab.row("- Crop (absolute):",         "<div id='get_crop_area_"+camera+"'>"+lang("PLEASE_WAIT")+"..</div>");
		html_entry += tab.row("- Preview Scale:",           birdhouse_edit_field(id="set_scale_"+camera, field="devices:cameras:"+camera+":image:preview_scale", type="input", options="", data_type="integer") + " %");
		html_entry += tab.row("- Show Framerate:",          birdhouse_edit_field(id="set_show_framerate_"+camera, field="devices:cameras:"+camera+":image:show_framerate", type="select", options="true,false", data_type="boolean"));
		html_entry += tab.row("- Image Manipulation:",      "<a href='index.html?CAMERA_SETTINGS'>"+lang("CAMERA")+"-"+lang("SETTINGS")+"</a>");
        html_entry += tab.end();

		id_list += "set_resolution_"+camera+":set_black_white_"+camera+":";
		id_list += "set_rotation_"+camera+":set_show_framerate_"+camera+":set_crop_"+camera+":set_scale_"+camera+":";
        html_temp += birdhouse_OtherGroup( camera+"_image", "Image / Video Settings", html_entry, false );

		hours = "00,01,02,03,04,05,06,07,08,09,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24";
        html_entry = tab.start();
		html_entry += tab.row("- Record:", birdhouse_edit_field(id="set_record_"+camera, field="devices:cameras:"+camera+":video:allow_recording", type="select", options="true,false", data_type="boolean"));
		html_entry += tab.row("- Rhythm:", "record every " + birdhouse_edit_field(id="set_record_rhythm_"+camera, field="devices:cameras:"+camera+":image_save:rhythm", type="select", options="05,10,15,20", data_type="string") + " s");
		html_entry += tab.row("- Record time:",
		    "from " + birdhouse_edit_field(id="set_record_from_"+camera, field="devices:cameras:"+camera+":image_save:record_from", type="select", options="sunrise-1,sunrise+0,sunrise+1,"+hours, data_type="string") + " &nbsp; " +
		    "to " + birdhouse_edit_field(id="set_record_to_"+camera, field="devices:cameras:"+camera+":image_save:record_to", type="select", options="sunset-1,sunset+0,sunset+1,"+hours, data_type="string")
		    );
		html_entry += tab.row("", "<text id='get_record_image_time_"+camera+"'></text>");
		html_entry += tab.row("- Record offset:", birdhouse_edit_field(id="set_record_offset_"+camera, field="devices:cameras:"+camera+":image_save:rhythm_offset", type="select", options="0,3,6,12", data_type="string"));
		html_entry += tab.end();

		id_list += "set_record_"+camera+":set_record_rhythm_"+camera+":set_record_from_"+camera+":set_record_to_"+camera+":set_record_offset_"+camera+":";
        html_temp += birdhouse_OtherGroup( camera+"_record", "Image / Video Recording", html_entry, false );

        html_entry = tab.start();
		html_entry += tab.row("- Area:", birdhouse_edit_field(id="set_area_"+camera, field="devices:cameras:"+camera+":similarity:detection_area", type="input", options="", data_type="json"));
		html_entry += tab.row("- Threshold:", birdhouse_edit_field(id="set_threshold_"+camera, field="devices:cameras:"+camera+":similarity:threshold", type="input", options="", data_type="float") + " %");
        html_entry += tab.end();

		id_list += "set_area_"+camera+":set_threshold_"+camera+":";
        html_temp += birdhouse_OtherGroup( camera+"_detect", "Image Similarity Detection", html_entry, false );

        html_entry = tab.start();
		html_entry += tab.row("- Show Time:", birdhouse_edit_field(id="set_time_"+camera, field="devices:cameras:"+camera+":image:date_time", type="select", options="true,false", data_type="boolean"));
		html_entry += tab.row("- Position:", birdhouse_edit_field(id="set_time_pos_"+camera, field="devices:cameras:"+camera+":image:date_time_position", type="input", options="", data_type="json"));
		html_entry += tab.row("- Font Size:", birdhouse_edit_field(id="set_time_size_"+camera, field="devices:cameras:"+camera+":image:date_time_size", type="input", options="", data_type="float"));
		html_entry += tab.row("- Font Color:", birdhouse_edit_field(id="set_time_color_"+camera, field="devices:cameras:"+camera+":image:date_time_color", type="input", options="", data_type="json"));
        html_entry += tab.end();

		id_list += ":set_time_"+camera+":set_time_size_"+camera+":set_time_pos_"+camera+":set_time_color_"+camera+":";
        html_temp += birdhouse_OtherGroup( camera+"_time", "Time Information", html_entry, false );

        html_entry = tab.start();
        html_entry += tab.row("Last Recorded:", "<div id='last_image_recorded_"+camera+"'>"+lang("PLEASE_WAIT")+"..</div>");
        html_entry += tab.row("Error Streams:", "<div id='error_streams_"+camera+"'></div>");
        html_entry += tab.end();
        html_temp += birdhouse_OtherGroup( camera+"_error", "Status", html_entry, false );

        var create = "";
        //if (admin && cameras[camera]["active"]) { var create =  "<button onclick=\""+onclick+"\" class=\"button-video-edit\">&nbsp;"+lang("CREATE_DAY")+"&nbsp;</button> &nbsp; "; }
    	var reconnect =  "<button onclick=\""+onclick2+"\" class=\"button-video-edit\">&nbsp;"+lang("RECONNECT_CAMERA")+"&nbsp;</button> &nbsp; ";

		html_temp += "<hr/>&nbsp;<br/><center>" + reconnect + create + birdhouse_edit_save(id="edit_"+camera, id_list, camera)+"</center><br/>";
	    html_temp += "</div></div>";

		html += birdhouse_OtherGroup( camera, camera_name, html_temp, false );
	}
	return [html, index_info];
}

function birdhouseDevices_cameraSettings (data) {
	var camera_settings	  = app_data["SETTINGS"]["devices"]["cameras"];
	var camera_properties = data["STATUS"]["devices"]["cameras"];

	var admin             = data["STATUS"]["admin_allowed"];
	var html = "";
	var tab     = new birdhouse_table();
	tab.style_rows["height"] = "27px";

	var camera_settings_write   = ["Brightness", "Contrast", "Gain", "Gamma", "Hue", "Saturation", "Exposure", "FPS"];
	var camera_settings_read    = ["Auto_WB", "Auto_Exposure", "WB_Temperature"];
	var camera_settings_measure = ["Brightness", "Contrast", "Saturation"];

	for (let camera in camera_settings) {
	    id_list = "";
        info = {};
	    Object.assign(info, camera_settings[camera]);
	    info["type"]  = "detection";
	    info["id"]    = camera + "_img";
	    camera_name   = camera.toUpperCase() + ": " + camera_settings[camera]["name"];
	    camera_stream = birdhouse_Image(camera_name, info);

	    if (!camera_properties[camera] || (camera_properties[camera]["error"] || camera_settings[camera]["active"] == false)) {
	        html += "&nbsp;<br/><center>";
	        html += "Camera " + camera.toUpperCase() + " is not available at the moment.<br/>";
	        html += "<a href='index.html?DEVICES'>See device settings for details.</a>";
	        html += "<br/>&nbsp;</center><hr/>";
	        continue;
	    }

	    html += "<div class='camera_info'><div class='camera_info_image'>";
	    if (camera_settings[camera]["active"])   { html  += camera_stream; }
	    else                                     { html  += lang("CAMERA_INACTIVE"); }
		html += "</div>";
		html += "<div class='camera_info_text'>";

        var count = 0;
        html_entry = "&nbsp;<br/>";
        html_entry += tab.start();
        for (var i=0;i<camera_settings_write.length;i++) {
            var value = camera_settings_write[i].toLowerCase();
            var key   = camera_settings_write[i].replaceAll("_", " ");

            if (camera_properties[camera] && camera_properties[camera]["properties"][value][1] != camera_properties[camera]["properties"][value][2]) {
                var range       = camera_properties[camera]["properties"][value][1] + ":" + camera_properties[camera]["properties"][value][2];
                var range_text  = "[" + camera_properties[camera]["properties"][value][1] + ".." + camera_properties[camera]["properties"][value][2] + "]";
                var prop        = "";

                if (camera_settings_measure.indexOf(camera_settings_write[i]) > -1) { prop += "<i>(image=<span id='img_"+value+"_"+camera+"'></span>)</i>"; }
                html_entry += tab.row("<b>" + key + ":</b><br/>" + range_text,
                                      birdhouse_edit_field(id="set_"+value+"_"+camera, field="devices:cameras:"+camera+":image:"+value, type="range", options=range, data_type="float") +
                                      " " + birdhouseDevices_cameraSettingsButton (camera, value, "set_"+value+"_"+camera, "change"));
                html_entry += tab.row("",   prop);

                id_list += "set_"+value+"_"+camera+":";
                count += 1;
                }
            else {
                camera_settings_read.push(camera_settings_write[i]);
                }
            }
        html_entry += tab.end();
        if (count == 0) {html_entry += "<center>No entries to edit.</center>"; }
        html_entry += "&nbsp;<br/>";
        html += birdhouse_OtherGroup( camera+"_camera_1", camera.toUpperCase() + " - Camera Settings", html_entry, true );

        html_entry = tab.start();
        for (var i=0;i<camera_settings_read.length;i++) {
            var value = camera_settings_read[i].toLowerCase();
            var key   = camera_settings_read[i].replaceAll("_", " ");
            html_entry += tab.row(key + ":", "<span id='prop_"+value+"_"+camera+"'></span>");
        }
        html_entry += tab.end();
        html_entry += "&nbsp;<br/>";
        html += birdhouse_OtherGroup( camera+"_camera_2", camera.toUpperCase() + " - Camera Values", html_entry, false );

        html += "<center>&nbsp;<br/>";
        html += birdhouse_edit_save(id="edit_"+camera, id_list, camera);
        html += "</center>";

        html += "</div></div>";
        html += "&nbsp;<br/>";
        html += "<hr/>";
	}
    html += "&nbsp;<br/>";
    setTextById(app_frame_content, html);
    setTextById(app_frame_header, "<center><h2>" + lang("CAMERA") + "-" + lang("SETTINGS") + "</h2></center>");

	for (let camera in camera_settings) {
        birdhouseDevices_cameraSettingsLoad(camera);
    }
}

function birdhouseDevices_cameraSettingsLoad (camera, active=true) {
    clearInterval(birdhouse_camera_interval[camera]);
    delete birdhouse_camera_interval[camera];

    if (active) {
        birdhouse_getCameraParam(camera);
        birdhouse_camera_interval[camera] = setInterval( function() {
            birdhouse_getCameraParam(camera);
        }, 5000);
    }
}

function birdhouseDevices_cameraSettingsButton (camera, key, field_id, description) {
    var onclick = "var cam_value=document.getElementById('"+field_id+"').value; birdhouse_cameraSettings(camera='"+camera+"', key='"+key+"', value=cam_value);"
    var button = "<button onclick=\""+onclick+"\"  class=\"bh-slider-button\">"+description+"</button>";
    return button;
}

function birdhouseDevices_sensors(data) {
	var sensors = app_data["SETTINGS"]["devices"]["sensors"];
	var admin 	= data["STATUS"]["admin_allowed"];
	var html    = "";
	var index_info = {};
	var tab     = new birdhouse_table();
	tab.style_rows["height"] = "27px";

	for (let sensor in sensors) {
	    sensor_name   = sensor.toUpperCase() + ": " + sensors[sensor]["name"];
	    index_info[sensor_name] = {};
	    index_info[sensor_name]["active"] = sensors[sensor]["active"];
	    index_info[sensor_name]["group"] = sensor;
	    index_info[sensor_name]["id"] = sensor;
	    index_info[sensor_name]["type"] = "sensor";
	    index_info[sensor_name]["status"] = ["active", "error"];

		if (sensors[sensor]["active"] == false) {
		    sensor_name += " &nbsp; <i>(inactive)</i>";
        }
        html_entry = "<div class='camera_info'>";
        html_entry += "<div class='camera_info_image'>";
        html_entry +=  "<div class='sensor_info' id='sensor_info_"+sensor+"'></div>";
        html_entry += "</div>";
        html_entry += "<div class='camera_info_text'>";
        html_entry += tab.start();
		html_entry += tab.row("Name:", birdhouse_edit_field(id="set_name_"+sensor, field="devices:sensors:"+sensor+":name", type="input"));
		html_entry += tab.row("Type:", birdhouse_edit_field(id="set_type_"+sensor, field="devices:sensors:"+sensor+":type", type="select", options="dht11,dht22"));
		html_entry += tab.row("Source:", birdhouse_edit_field(id="set_source_"+sensor, field="devices:sensors:"+sensor+":pin", type="input", options="", data_type="integer")
		                + " (data pin on RPi)");
		html_entry += tab.row("Active:", birdhouse_edit_field(id="set_active_"+sensor, field="devices:sensors:"+sensor+":active", type="select", options="true,false", data_type="boolean"));
        html_entry += tab.end();

        var html_temp = tab.start();
        html_temp += tab.row("Last Recorded:", "<div id='status_sensor_last_"+sensor+"'>"+lang("PLEASE_WAIT")+"..</div>");
		html_temp += tab.row("Running:",       "<div id='status_sensor_"+sensor+"'>"+lang("PLEASE_WAIT")+"..</div>");
        html_temp += tab.row("Error Sensor:",  "<textarea id='error_sensor1_"+sensor+"' class='settings_error_msg'></textarea>");
        html_temp += tab.row("Error Message:", "<textarea id='error_sensor2_"+sensor+"' class='settings_error_msg'></textarea>");
        html_temp += tab.end();
        html_entry += birdhouse_OtherGroup( sensor+"_error", "Status", html_temp, false );

		var id_list = "set_name_"+sensor+":set_type_"+sensor+":set_active_"+sensor+":set_source_"+sensor;
        html_entry += "<hr/>";
        html_entry += tab.start();
		html_entry += tab.row("<center>"+birdhouse_edit_save(id="edit_"+sensor, id_list)+"</center>");
		html_entry += tab.end();
        html_entry += "</div>";
        html_entry += "</div>";
		html += birdhouse_OtherGroup( sensor, sensor_name, html_entry, false );
	}
	return [html, index_info];
}

function birdhouseDevices_weather(data) {
	var weather_config  = app_data["SETTINGS"]["weather"];
	var weather_data    = app_data["WEATHER"];
	var info_key        = lang("WEATHER").toUpperCase()+": "+weather_config["location"];
	var index_info      = {};
	index_info[info_key] = {};
    index_info[info_key]["active"] = weather_config["active"];
    index_info[info_key]["group"]  = "weather_settings";
    index_info[info_key]["id"]     = "WEATHER";
    index_info[info_key]["type"]   = "weather";
    index_info[info_key]["status"] = ["active", "error"];

	var admin = data["STATUS"]["admin_allowed"];
	var html = "";
	//var open = true;
	var tab = new birdhouse_table();
	tab.style_rows["height"] = "27px";

    var html_entry = "<div class='camera_info'>";
    html_entry += "<div class='camera_info_image'>&nbsp;<br/>";
    html_entry +=  "<div id='weather_info_icon' style='font-size:80px;'></div>";
    html_entry += "<br/>&nbsp;</div>";
    html_entry += "<div class='camera_info_text'>";

    html_entry += tab.start();
    html_entry += tab.row("Location:", birdhouse_edit_field(id="set_weather_location", field="weather:location", type="input"));
    // html_entry += tab.row("GPS Position:", birdhouse_edit_field(id="set_weather_gps", field="weather:gps_location", type="input", options="", data_type="json"));
    html_entry += tab.row("GPS Position:", "<div id='gps_coordinates'>"+lang("PLEASE_WAIT")+"..</div>");
    html_entry += tab.row("Active:", birdhouse_edit_field(id="set_weather_active", field="weather:active", type="select", options="true,false", data_type="boolean"));
    html_entry += tab.row("Source:", birdhouse_edit_field(id="set_weather_source", field="weather:source", type="select", options=weather_config["available_sources"].toString(), data_type="string"));
    html_entry += tab.row("Last Update:", "<div id='weather_info_update'>"+lang("PLEASE_WAIT")+"..</div>");
    html_entry += tab.end();
    html_entry += "<br/>";

    var html_temp = tab.start();
    html_temp += tab.row("Error:", "<textarea id='weather_info_error' class='settings_error_msg'></textarea>");
    html_temp += tab.end();
    html_entry += birdhouse_OtherGroup( "weather_error", "Status    ", html_temp, false );

    var id_list = "set_weather_location:set_weather_active:set_weather_source:set_weather_gps";
    html_entry += "<hr/>";
    html_entry += tab.start();
    html_entry += tab.row("<center>"+birdhouse_edit_save(id="edit_weather", id_list)+"</center>");
    html_entry += tab.end();

    html_entry += "</div></div>";

    var title = lang("WEATHER").toUpperCase();
    if (weather_config["weather_active"] == false) {
        title += " &nbsp; <i>(inactive)</i>";
    }
    html += birdhouse_OtherGroup( "weather_settings", title, html_entry, false );

	return [html, index_info];
}

function birdhouseDevices_microphones(data) {
	var micros  = app_data["SETTINGS"]["devices"]["microphones"];
	var devices = app_data["STATUS"]["system"]["audio_devices"];
	var admin 	= app_data["STATUS"]["admin_allowed"];
	var mic_devices = {};
	var html = "";
	var index_info = {};
	var tab     = new birdhouse_table();
	tab.style_rows["height"] = "27px";
	tab.style_cells["vertical-align"] = "top";

	for (let device in devices) {
	    if (devices[device]["input"] > 0) {
	        mic_devices[devices[device]["id"]] = device;
	    }
	}
	for (let micro in micros) {
	    micro_name = micro.toUpperCase() + ": " + micros[micro]["name"];

	    index_info[micro_name] = {};
	    index_info[micro_name]["active"] = micros[micro]["active"];
	    index_info[micro_name]["group"]  = micro;
        index_info[micro_name]["id"]     = micro;
	    index_info[micro_name]["type"]   = "microphone";
	    index_info[micro_name]["status"] = ["active", "error"];

		if (micros[micro]["active"] == false) {
		    micro_name += " &nbsp; <i>(inactive)</i>";
        }
        url = "http://"+micros[micro]["stream_server"]+"/"+micro+".mp3";
        url_new = birdhouseAudioStream_URL(micro, "device_settings");

        html_entry = "<div class='camera_info'>";
        html_entry += "<div class='camera_info_image'>&nbsp;<br/>";
        html_entry += "<div id='mic_img_"+micro+"'>"
        html_entry += birdhouseAudioStream_toggle_image(micro);
        html_entry += "</div></div>";
        html_entry += "<div class='camera_info_text'>";

		var id_list = "";
		var default_sample_rate = "";
		var on_change= "document.getElementById(\"set_device_name_"+micro+"\").value=this.options[this.selectedIndex].text;";
		for (let key in devices) {
		    if (devices[key]["id"] == micros[micro]["device_id"]) {
		        default_sample_rate = devices[key]["sample_rate"];
		    }
		}
		var sample_rates = Math.round(default_sample_rate) + "," + Math.round(default_sample_rate/2) + "," + Math.round(default_sample_rate/4);

		id_list += "set_name_"+micro+":set_active_"+micro+":set_device_"+micro+":set_device_name_"+micro+":set_sample_rate_"+micro+":set_chunk_"+micro;

        html_entry += tab.start();
		html_entry += tab.row("Name:",        birdhouse_edit_field(id="set_name_"+micro, field="devices:microphones:"+micro+":name", type="input"));
		html_entry += tab.row("Active:",      birdhouse_edit_field(id="set_active_"+micro, field="devices:microphones:"+micro+":active", type="select", options="true,false", data_type="boolean"));
		html_entry += tab.row("Device:",      birdhouse_edit_field(id="set_device_"+micro, field="devices:microphones:"+micro+":device_id", type="select_dict", options=mic_devices, data_type="integer", on_change=on_change));
		html_entry += tab.row("",             birdhouse_edit_field(id="set_device_name_"+micro, field="devices:microphones:"+micro+":device_name", type="input", options="", data_type="string"));

		/*
		id_list += "set_name_"+micro+":set_type_"+micro+":set_active_"+micro+":set_source_"+micro;
        html_entry += tab.row("Type:", birdhouse_edit_field(id="set_type_"+micro, field="devices:microphones:"+micro+":type", type="select", options="usb"));
		html_entry += tab.row("Port:", birdhouse_edit_field(id="set_source_"+micro, field="devices:microphones:"+micro+":port", type="input", options="", data_type="integer"));
		html_entry += tab.row("Audio-Stream:", "<a href='"+url+"' target='_blank'>"+url+"</a>");
		*/
		html_entry += tab.end();

        html_temp = tab.start();
		html_temp += tab.row("Sample-Rate:", birdhouse_edit_field(id="set_sample_rate_"+micro, field="devices:microphones:"+micro+":sample_rate", type="select", options=sample_rates, data_type="integer") +
		                                      " (default=" + default_sample_rate +")");
		html_temp += tab.row("Chunk size:",  "1024 * " + birdhouse_edit_field(id="set_chunk_"+micro, field="devices:microphones:"+micro+":chunk_size", type="input", options="", data_type="integer"));
		html_temp += tab.row("Channels:",    birdhouse_edit_field(id="set_channels_"+micro, field="devices:microphones:"+micro+":channels", type="select", options="1,2", data_type="integer"));
        html_temp += tab.end();
        html_entry += birdhouse_OtherGroup( micro + "_settings", "Device settings", html_temp, false );

        html_temp = tab.start();
		html_temp += tab.row("Audio-Stream:",   "<a href='"+url_new+"' target='_blank'>"+url_new+"</a>");
		//html_temp += tab.row("Audio-Control [try-out]",   "<audio controls><source src='"+url_new+"' type='audio/x-wav;codec=PCM'></audio>");
		html_temp += tab.row("Audio-Control:",  "<a onclick='birdhouseAudioStream_play(\""+micro+"\");' style='cursor:pointer;'><u>PLAY</u></a> / <a onclick='birdhouseAudioStream_stop(\""+micro+"\");' style='cursor:pointer;'><u>STOP</u></a>");
		html_temp += tab.row("Playback:",       "<div id='playback_info_"+micro+"'>N/A</div>");
        html_temp += tab.end();
        html_entry += birdhouse_OtherGroup( micro + "_playback", "Playback controls", html_temp, false );

        html_temp = tab.start();
        html_temp += tab.row("Last Recorded:", "<div id='info_micro_"+micro+"'>"+lang("PLEASE_WAIT")+"..</div>");
        html_temp += tab.row("Error Messages:", "<div id='error_micro_"+micro+"'></div>");
        html_temp += tab.end();
        html_entry += birdhouse_OtherGroup( micro + "_error", "Status", html_temp, false );

		html_entry += "<hr/>";
		html_entry += "<center>"+birdhouse_edit_save(id="edit_"+micro, id_list)+"</center>";

        html_entry += "</div></div>";

        html += birdhouse_OtherGroup( micro, micro_name, html_entry, false );
	}

	return [html, index_info];
}

function birdhouseDevices_openOne(group_id) {
    for (var i=0;i<birdhouse_device_list.length;i++) {
        if (birdhouse_device_list[i] == group_id) { birdhouse_groupOpen(birdhouse_device_list[i]); }
        else                                      { birdhouse_groupClose(birdhouse_device_list[i]); }
    }
}
