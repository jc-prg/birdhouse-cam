//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// show and edit device information
//--------------------------------------
/* INDEX:
function birdhouseDevices( title, data )
*/
//--------------------------------------

var birdhouse_device_list = [];

function birdhouseDevices( title, data ) {
	var html = "";
	var index = [];
	var tab     = new birdhouse_table();
	tab.style_rows["height"] = "27px";

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

    var html_index = "<div class='camera_info'>";
    html_index += "<div class='camera_info_image'>&nbsp;<br/>";
    html_index +=  "<div id='loading_img'><img src='"+app_loading_image+"' style='width:50%;'></div>";
    html_index += "<br/>&nbsp;</div>";
    html_index += "<div class='camera_info_text'>";

    html_index += tab.start();
    birdhouse_device_list = [];
    for (var i=0;i<index.length;i++) {
        Object.keys(index[i]).forEach(key => {
            birdhouse_device_list.push(index[i][key]["group"]);
            var onclick = "birdhouseDevices_openOne('"+index[i][key]["group"]+"')";
            var button = "<button onclick=\""+onclick+"\" class=\"button-video-edit\">&nbsp;"+lang("SHOW")+"&nbsp;</button>";
            var action = "<div id='status_active_" + index[i][key]["id"] + "' style='float:left;'><div id='black'></div></div>";
            action    += "<div id='status_error_" + index[i][key]["id"] + "' style='float:left;'><div id='black'></div></div>";
            action    += "&nbsp;&nbsp;&nbsp;" + button;
            html_index += tab.row(key, action);
        });
    }
    html_index += tab.end();
    html_index += "<br/>&nbsp;"
    html_index += "</div></div>";

	setTextById(app_frame_content, html_index + html);
	setTextById(app_frame_header, "<center><h2>" + lang("DEVICES") + "</h2></center>");
}

function birdhouseDevices_cameras(data) {
	var cameras	= data["DATA"]["devices"]["cameras"];
	var admin 	= data["STATUS"]["admin_allowed"];
	var html	= "";
	var index_info = {};
	var tab     = new birdhouse_table();
	tab.style_rows["height"] = "27px";

	for (let camera in cameras) {
    	var onclick  = "birdhouse_createDayVideo('"+camera+"');";
    	var onclick2 = "birdhouse_reconnectCamera('"+camera+"');";
    	var open    = true;
    	var info    = {};
		var id_list = "";

	    Object.assign(info, cameras[camera]);
	    info["type"]  = "detection";
	    info["id"]    = camera;
	    camera_name   = camera.toUpperCase() + ": " + cameras[camera]["name"];
	    camera_stream = birdhouse_Image(camera_name, info);
	    index_info[camera_name] = {};
	    index_info[camera_name]["active"] = cameras[camera]["active"];
	    index_info[camera_name]["group"] = camera;
	    index_info[camera_name]["id"] = camera;

	    resolution_max = cameras[camera]["image"]["resolution_max"];
	    resolution_act = cameras[camera]["image"]["resolution_current"];

		if (cameras[camera]["active"] == false || cameras[camera]["active"] == "false") {
		    open = false;
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
        var options = data["STATUS"]["system"]["video_devices_02"];
        html_temp += tab.row("Source:", birdhouse_edit_field(id="set_source_"+camera, field="devices:cameras:"+camera+":source", type="select_dict", options=options, data_type="string"));
		html_temp += tab.end();
		html_temp += "&nbsp;<br/>";
		id_list += "set_name_"+camera+":set_type_"+camera+":set_active_"+camera+":set_source_"+camera+":";

        html_entry = tab.start();
		html_entry += tab.row("- Set Resolution:", birdhouse_edit_field(id="set_resolution_"+camera, field="devices:cameras:"+camera+":image:resolution", type="input", options="", data_type="string"));
		html_entry += tab.row("- Resolution:", "current=(" + resolution_act + "), max=(" + resolution_max + ")");
		html_entry += tab.row("- Rotation:", birdhouse_edit_field(id="set_rotation_"+camera, field="devices:cameras:"+camera+":image:rotation", type="select", options="0,90,180,270", data_type="integer"));
		html_entry += tab.row("- Black&White:", birdhouse_edit_field(id="set_black_white_"+camera, field="devices:cameras:"+camera+":image:black_white", type="select", options="false,true", data_type="boolean"));
		html_entry += tab.row("- Crop (relative):", birdhouse_edit_field(id="set_crop_"+camera, field="devices:cameras:"+camera+":image:crop", type="input", options="", data_type="json"));
		html_entry += tab.row("- Crop (absolute):", "<div id='get_crop_area_"+camera+"'>Please wait ...</div>");
		html_entry += tab.row("- Preview Scale:", birdhouse_edit_field(id="set_scale_"+camera, field="devices:cameras:"+camera+":image:preview_scale", type="input", options="", data_type="integer") + " %");
		html_entry += tab.row("- Show Framerate:", birdhouse_edit_field(id="set_show_framerate_"+camera, field="devices:cameras:"+camera+":image:show_framerate", type="select", options="true,false", data_type="boolean") + " fps");
        html_entry += tab.end();

		id_list += "set_resolution_"+camera+":set_rotation_"+camera+":set_show_framerate_"+camera+":set_crop_"+camera+":set_scale_"+camera+":set_black_white_"+camera+":";
        html_temp += birdhouse_OtherGroup( camera+"_image", "Image/Video", html_entry, false );

        html_entry = tab.start();
		html_entry += tab.row("- Show Time:", birdhouse_edit_field(id="set_time_"+camera, field="devices:cameras:"+camera+":image:date_time", type="select", options="true,false", data_type="boolean"));
		html_entry += tab.row("- Position:", birdhouse_edit_field(id="set_time_pos_"+camera, field="devices:cameras:"+camera+":image:date_time_position", type="input", options="", data_type="json"));
		html_entry += tab.row("- Font Size:", birdhouse_edit_field(id="set_time_size_"+camera, field="devices:cameras:"+camera+":image:date_time_size", type="input", options="", data_type="float"));
		html_entry += tab.row("- Font Color:", birdhouse_edit_field(id="set_time_color_"+camera, field="devices:cameras:"+camera+":image:date_time_color", type="input", options="", data_type="json"));
        html_entry += tab.end();

		id_list += ":set_time_"+camera+":set_time_size_"+camera+":set_time_pos_"+camera+":set_time_color_"+camera+":";
        html_temp += birdhouse_OtherGroup( camera+"_time", "Time Information", html_entry, false );

        html_entry = tab.start();
		html_entry += tab.row("- Area:", birdhouse_edit_field(id="set_area_"+camera, field="devices:cameras:"+camera+":similarity:detection_area", type="input", options="", data_type="json"));
		html_entry += tab.row("- Threshold:", birdhouse_edit_field(id="set_threshold_"+camera, field="devices:cameras:"+camera+":similarity:threshold", type="input", options="", data_type="float") + " %");
        html_entry += tab.end();

		id_list += "set_area_"+camera+":set_threshold_"+camera+":";
        html_temp += birdhouse_OtherGroup( camera+"_detect", "Similarity Detection", html_entry, false );

        html_entry = tab.start();
		html_entry += tab.row("- Record:", birdhouse_edit_field(id="set_record_"+camera, field="devices:cameras:"+camera+":video:allow_recording", type="select", options="true,false", data_type="boolean"));
		html_entry += tab.row("- Hours:", JSON.stringify(cameras[camera]["image_save"]["hours"]).replace(/,/g,", "));
		html_entry += tab.row("- Seconds:", JSON.stringify(cameras[camera]["image_save"]["seconds"]).replace(/,/g,", "));
        html_entry += tab.end();

		id_list += "set_record_"+camera+":";
        html_temp += birdhouse_OtherGroup( camera+"_record", "Record Images", html_entry, false );

        html_entry = tab.start();
        html_entry += tab.row("Last Recorded:", "<div id='last_image_recorded_"+camera+"'>please wait ...</div>");
		html_entry += tab.row("Current Streams:", "<div id='show_stream_count_"+camera+"'>Please wait ...</div>");
        html_entry += tab.row("Error Camera:", "<textarea id='error_cam_"+camera+"' class='settings_error_msg'></textarea>");
        html_entry += tab.row("Error Image:", "<textarea id='error_img_"+camera+"' class='settings_error_msg'></textarea>");
        html_entry += tab.end();
        html_temp += birdhouse_OtherGroup( camera+"_error", "Status", html_entry, false );

        if (admin && cameras[camera]["active"]) { var create =  "<button onclick=\""+onclick+"\" class=\"button-video-edit\">&nbsp;"+lang("CREATE_DAY")+"&nbsp;</button> &nbsp; "; }
    	else { var create = ""; }

    	var reconnect =  "<button onclick=\""+onclick2+"\" class=\"button-video-edit\">&nbsp;"+lang("RECONNECT_CAMERA")+"&nbsp;</button> &nbsp; ";

		html_temp += "<hr/>&nbsp;<br/><center>" + reconnect + create + birdhouse_edit_save(id="edit_"+camera, id_list)+"</center><br/>";
	    html_temp += "</div></div>";

		html += birdhouse_OtherGroup( camera, camera_name, html_temp, false );
	}
	return [html, index_info];
}

function birdhouseDevices_sensors(data) {
	var sensors = data["DATA"]["devices"]["sensors"];
	var admin 	= data["STATUS"]["admin_allowed"];
	var html    = "";
	var index_info = {};
	var tab     = new birdhouse_table();
	tab.style_rows["height"] = "27px";

	for (let sensor in sensors) {
        open = true;
	    sensor_name   = sensor.toUpperCase() + ": " + sensors[sensor]["name"];
	    index_info[sensor_name] = {};
	    index_info[sensor_name]["active"] = sensors[sensor]["active"];
	    index_info[sensor_name]["group"] = sensor;
	    index_info[sensor_name]["id"] = sensor;

		if (sensors[sensor]["active"] == false) {
		    open = false;
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
        html_temp += tab.row("Last Recorded:", "<div id='status_sensor_last_"+sensor+"'>please wait ...</div>");
		html_temp += tab.row("Running:",       "<div id='status_sensor_"+sensor+"'>Please wait ...</div>");
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
	var weather_config  = data["DATA"]["weather"];
	var weather_data = data["WEATHER"];
	var info_key = lang("WEATHER").toUpperCase()+": "+weather_config["location"];
	var index_info = {};
	index_info[info_key] = {};
    index_info[info_key]["active"] = weather_config["active"];
    index_info[info_key]["group"] = "weather_settings";
    index_info[info_key]["id"] = "WEATHER";

	var admin = data["STATUS"]["admin_allowed"];
	var html = "";
	var open = true;
	var tab = new birdhouse_table();
	tab.style_rows["height"] = "27px";

    var html_entry = "<div class='camera_info'>";
    html_entry += "<div class='camera_info_image'>&nbsp;<br/>";
    html_entry +=  "<div id='weather_info_icon' style='font-size:80px;'></div>";
    html_entry += "<br/>&nbsp;</div>";
    html_entry += "<div class='camera_info_text'>";

    html_entry += tab.start();
    html_entry += tab.row("Location:", birdhouse_edit_field(id="set_weather_location", field="weather:location", type="input"));
    html_entry += tab.row("GPS Position:", weather_data["info_position"].toString());
    html_entry += tab.row("Active:", birdhouse_edit_field(id="set_weather_active", field="weather:active", type="select", options="true,false", data_type="boolean"));
    html_entry += tab.row("Source:", weather_config["source"]);
    html_entry += tab.row("Last Update:", "<div id='weather_info_update'>Please wait ...</div>");
    html_entry += tab.end();
    html_entry += "<br/>";

    var html_temp = tab.start();
    html_temp += tab.row("Error:", "<textarea id='weather_info_error' class='settings_error_msg'></textarea>");
    html_temp += tab.end();
    html_entry += birdhouse_OtherGroup( "weather_error", "Status    ", html_temp, false );

    var id_list = "set_weather_location:set_weather_active";
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
	var micros  = data["DATA"]["devices"]["microphones"];
	var admin 	= data["STATUS"]["admin_allowed"];
	var html = "";
	var index_info = {};
	var tab     = new birdhouse_table();
	tab.style_rows["height"] = "27px";

	for (let micro in micros) {
	    open = true;
	    micro_name = micro.toUpperCase() + ": " + micros[micro]["name"];

	    index_info[micro_name] = {};
	    index_info[micro_name]["active"] = micros[micro]["active"];
	    index_info[micro_name]["group"] = micro;
        index_info[micro_name]["id"] = micro;

		if (micros[micro]["active"] == false) {
		    open = false;
		    micro_name += " &nbsp; <i>(inactive)</i>";
        }
        url = "http://"+micros[micro]["stream_server"]+"/"+micro+".mp3";
        html_entry = "<div class='camera_info'>";
        html_entry += "<div class='camera_info_image'>&nbsp;<br/>";
        html_entry += "<div id='mic_img_"+micro+"'>"
        html_entry += birdhouseStream_toggle_image(micro);
        html_entry += "</div></div>";
        html_entry += "<div class='camera_info_text'>";
        html_entry += tab.start();
		html_entry += tab.row("Name:", birdhouse_edit_field(id="set_name_"+micro, field="devices:microphones:"+micro+":name", type="input"));
		html_entry += tab.row("Type:", birdhouse_edit_field(id="set_type_"+micro, field="devices:microphones:"+micro+":type", type="select", options="usb"));
		html_entry += tab.row("Active:", birdhouse_edit_field(id="set_active_"+micro, field="devices:microphones:"+micro+":active", type="select", options="true,false", data_type="boolean"));
		html_entry += tab.row("Port:", birdhouse_edit_field(id="set_source_"+micro, field="devices:microphones:"+micro+":port", type="input", options="", data_type="integer"));
		html_entry += tab.row("Audio-Stream:", "<a href='"+url+"' target='_blank'>"+url+"</a>");
		html_entry += tab.row("Audio-Control:", "<a onclick='birdhouseStream_play(\""+micro+"\");' style='cursor:pointer;'><u>PLAY</u></a> / <a onclick='birdhouseStream_stop(\""+micro+"\");' style='cursor:pointer;'><u>STOP</u></a>");
		html_entry += tab.row("<hr/>");
		var id_list = "set_name_"+micro+":set_type_"+micro+":set_active_"+micro+":set_source_"+micro;
		html_entry += tab.row("<center>"+birdhouse_edit_save(id="edit_"+micro, id_list)+"</center>");
		html_entry += tab.end();
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
