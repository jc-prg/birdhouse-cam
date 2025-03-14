//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// show and edit device information
//--------------------------------------


var birdhouse_device_list = [];
var birdhouse_camera_interval = {};

/*
* Create and show view with settings of all devices
*
* @param (string) title: view title
* @param (dict) data: complete setting and status data from API
* @param (boolean) show_settings: show complete settings (true) or only devices status (false)
*/
function birdhouseDevices(title, data, show="settings", subset="all") {
	var html = "";
	var index = [];

    if (subset != "devices") {
        var [settings, info] = birdhouseDevices_cameras(data, subset);
        html += settings;
        index.push(info);
        }

    if (subset != "cameras") {
        var [settings, info] = birdhouseDevices_weather(data);
        html += settings;
        index.push(info);

        var [settings, info] = birdhouseDevices_sensors(data);
        html += settings;
        index.push(info);

        var [settings, info] = birdhouseDevices_relays(data);
        html += settings;
        index.push(info);
        }

    if (subset != "devices") {
        var [settings, info] = birdhouseDevices_microphones(data);
        html += settings;
        index.push(info);
        }

    if (show == "settings") {
        var html_index = birdhouseDevices_status(index=index, show="interactive");
        if (subset == "cameras")   { appSettings.write(1, lang("CAMERA_SETTINGS"), html_index + html); }
        else                       { appSettings.write(1, lang("DEVICE_SETTINGS"), html_index + html); }
        }
    else if (show == "information") {
        var html_index = birdhouseDevices_status(index=index, show="complete");
        return html_index;
        }
    else {
        var html_index = birdhouseDevices_status(index=index, show="short");
        return html_index;
        }
}

/*
* Create status view for all configured devices - to be filled and updated by birdhouseStatus_print();
*
* @param (dict) index: device definition
* @param (boolean) show_button: show link to open respective group with details
* @returns (string): html with status information
*/
function birdhouseDevices_status(index, show) {

	var tab         = new birdhouse_table();
    var show_button = false;
    var short       = false;
    var short_data  = {};

    if (show == "interactive")  { show_button = true; }
    if (show == "short")        { short = true; }

    if (show_button) {
        tab.style_rows["height"]        = "27px";
        tab.style_cells["min-width"]    = "150px";
        }
    if (!short) {
        tab.style_rows["height"]        = "27px";
        tab.style_cells["width"]        = "50%";
        tab.style_cells["min-width"]    = "";
        }
    else  {
        tab.style_rows["max-height"]    = "20px";
        tab.style_cells["width"]        = "60px";
        tab.style_cells["min-width"]    = "";
        }

    var html_index = "";
    if (!short && show_button) {
        html_index += "<div class='camera_info'>";
        html_index += "<div class='camera_info_image'>&nbsp;<br/>";
        html_index += "<div id='loading_img' style='height:120px;'><img src='"+app_loading_image+"' style='width:50%;max-width:100px;'></div>";
        html_index += "</div>";
        html_index += "<div class='camera_info_text'>";
    }

    html_index += tab.start();
    birdhouse_device_list = [];
    for (var i=0;i<index.length;i++) {
        Object.keys(index[i]).forEach(key => {
            birdhouse_device_list.push(index[i][key]["group"]);
            var onclick     = "birdhouseDevices_openOne('"+index[i][key]["group"]+"')";
            var device_type = index[i][key]["type"];
            var button      = "";

            if (device_type != "relay") {
                if (show_button) { var device_key = "<text onclick=\""+onclick+"\" style=\"cursor:pointer;\"><u><b>" + key + "</b></u></text>"; }
                else             { var device_key = key; }

                if (short) {
                    if (typeof short_data[device_type] == 'undefined') { short_data[device_type] = ""; }
                    short_data[device_type] += "<div id='status_" + index[i][key]["status"][1] + "_" + index[i][key]["id"] + "' style='float:left;'><div id='black'></div></div>";
                    }
                else {
                    var action = "<div style='float:left;'>";
                    for (var a=0; a<index[i][key]["status"].length;a++) {
                        action += "<div id='status_" + index[i][key]["status"][a] + "_" + index[i][key]["id"] + "' style='float:left;'><div id='black'></div></div>"; //
                    }
                    for (var a=index[i][key]["status"].length; a<3; a++) {
                        action += "<div id='status_" + index[i][key]["status"][a] + "_" + index[i][key]["id"] + "' style='float:left;height:24px;width:24px;'></div>";
                    }
                    if (!show_button && (index[i][key]["type"] == "camera" || index[i][key]["type"] == "microphone")) {
                        action += "<div style='float:left;padding:5px;width:70px;'><font id='show_stream_count_" + index[i][key]["id"] + "'>0 Streams</font></div>";
                    }
                    else if (index[i][key]["type"] == "camera" || index[i][key]["type"] == "microphone") {
                        action += "<div style='padding:5px;float:left;width:70px;'><font id='show_stream_count_" + index[i][key]["id"] + "'>0 Streams</font></div>";
                    }
                    action += "</div>";
                    html_index += tab.row(device_key, action);
                    }
                }
        });
    }
    if (short) {
        Object.keys(short_data).forEach(key => {
            var key_description = "&nbsp;&nbsp;" + key.charAt(0).toUpperCase() + key.slice(1) + ":";
            html_index += tab.row("<div style='float:left;'>" + key_description + "</div>", short_data[key]);
            });
        }
    html_index += tab.end();
    if (!short && show_button) {
        html_index += "</div></div>";
        }
    if (!short) {
        html_index += "<br/>&nbsp;"
        }
    return html_index;
}

/*
* Create edit form for camera settings
*
* @param (dict) data: complete setting and status data from API
* @returns (string, dict): html and index information
*/
function birdhouseDevices_cameras(data, subset="") {
	var cameras	    = data["SETTINGS"]["devices"]["cameras"];
	var settings    = app_data["SETTINGS"]
	var micros      = "," + Object.keys(data["SETTINGS"]["devices"]["microphones"]).join(",");
	var relay_list  = "," + Object.keys(data["SETTINGS"]["devices"]["relays"]).join(",");
	var admin 	    = data["STATUS"]["admin_allowed"];
	var html	    = "";
	var index_info  = {};
	var tab         = new birdhouse_table();
	tab.style_rows["height"] = "27px";
	tab.style_cells["vertical-align"] = "top";

    if (subset != "short") {
	    for (let camera in cameras) {
    	var onclick  = "birdhouse_createDayVideo('"+camera+"');";
    	var onclick2 = "birdhouse_reconnectCamera('"+camera+"');";
    	var info    = {};
		var id_list = "";

	    Object.assign(info, cameras[camera]);
	    info["type"]  = "detection";
	    info["id"]    = camera;
	    camera_name   = camera.toUpperCase() + ": " + cameras[camera]["name"];
	    camera_stream = birdhouse_Image(camera_name, "info", info);
	    index_info[camera_name] = {};
	    index_info[camera_name]["active"] = cameras[camera]["active"];
	    index_info[camera_name]["group"]  = camera;
	    index_info[camera_name]["id"]     = camera;
	    index_info[camera_name]["type"]   = "camera";
	    index_info[camera_name]["status"] = ["active", "error", "error_record"];

        var source_info = "";
        var source = app_data["SETTINGS"]["devices"]["cameras"][camera]["source"];
	    var source_alternative = app_data["STATUS"]["devices"]["cameras"][camera]["active_device"];
	    if (source_alternative != undefined && source_alternative != null && source != source_alternative) {
            source_info = "</br>" + lang("DIFFERENT_VIDEO_DEVICE", [source_alternative, source]);
	        }

        var resolution_max = "N/A";
        var resolution_act = "N/A";
	    if (cameras[camera]["image"]["resolution_max"])     { resolution_max = "[" + cameras[camera]["image"]["resolution_max"][0]+"x"+cameras[camera]["image"]["resolution_max"][1] +"]"; }
	    if (cameras[camera]["image"]["resolution_current"]) { resolution_act = "[" + cameras[camera]["image"]["resolution_current"][0]+"x"+cameras[camera]["image"]["resolution_current"][1] + "]"; }

		if (cameras[camera]["active"] == false || cameras[camera]["active"] == "false") {
		    camera_name += " &nbsp; <i>(inactive)</i>";
            }
	    html_temp = "<div class='camera_info'><div class='camera_info_image'>";
	    if (cameras[camera]["active"])
	         { html_temp  += camera_stream; }
	    else { html_temp  += lang("CAMERA_INACTIVE"); }
		html_temp += "</div>";
		html_temp += "<div class='camera_info_text'>";

        var on_change_source = "birdhouseDevices_cameras_resolutions(\""+camera+"\", this.value);";
        var device_options = app_data["STATUS"]["devices"]["available"]["video_devices_short"];
		html_temp += tab.start();
        html_temp += tab.row("Active:",     birdhouse_edit_field(id="set_active_"+camera, field="devices:cameras:"+camera+":active", type="select", options="true,false", data_type="boolean"));
		html_temp += tab.row("Name:",       birdhouse_edit_field(id="set_name_"+camera, field="devices:cameras:"+camera+":name", type="input"));
        html_temp += tab.row("Source:",     birdhouse_edit_field(id="set_source_"+camera, field="devices:cameras:"+camera+":source", type="select_dict_sort", options=device_options, data_type="string", on_change=on_change_source) +
                                            source_info);
		html_temp += tab.row("Micro:",      birdhouse_edit_field(id="set_micro_"+camera, field="devices:cameras:"+camera+":record_micro", type="select", options=micros, data_type="boolean"));
        html_temp += tab.row("Detection:",  birdhouse_edit_field(id="set_detection_mode_"+camera, field="devices:cameras:"+camera+":detection_mode", type="select", options="similarity,object", data_type="string"));
		html_temp += tab.end();
		html_temp += "&nbsp;<br/>";
		id_list += "set_name_"+camera+":set_active_"+camera+":set_source_"+camera+":"+":set_micro_"+camera+":set_detection_mode_"+camera+":";

        var current_available_resolutions = birdhouseDevices_cameras_resolutions(camera, cameras[camera]["source"] );
        var available_colors = ",RGB,BGR"
        html_entry = tab.start();
		html_entry += tab.row("- Resolution:",              birdhouse_edit_field(id="set_resolution_"+camera, field="devices:cameras:"+camera+":image:resolution", type="input", options="", data_type="string"));
		html_entry += tab.row("&nbsp;",                     "<b>current</b>=<label id='current_resolution_"+camera+"'>" + resolution_act + "</label>, <b>max</b>=<label id='max_resolution_"+camera+"'>" + resolution_max + "</label>,<br/>" +
                                                            "<b>available</b>=<label id='resolution_per_device_"+camera+"'>" + current_available_resolutions + "</label>");
		html_entry += tab.row("- Black &amp; White:",       birdhouse_edit_field(id="set_black_white_"+camera, field="devices:cameras:"+camera+":image:black_white", type="select", options="false,true", data_type="boolean"));
		html_entry += tab.row("- Color Schema:",            birdhouse_edit_field(id="set_color_schema_"+camera, field="devices:cameras:"+camera+":image:color_schema", type="select", options=available_colors, data_type="boolean"));
		html_entry += tab.row("- Rotation:",                birdhouse_edit_field(id="set_rotation_"+camera, field="devices:cameras:"+camera+":image:rotation", type="select", options="0,90,180,270", data_type="integer"));
		html_entry += tab.row("- Crop (relative):",         birdhouse_edit_field(id="set_crop_"+camera, field="devices:cameras:"+camera+":image:crop", type="input", options="", data_type="json"));
		html_entry += tab.row("- Crop (absolute):",         "<div id='get_crop_area_"+camera+"'>"+lang("PLEASE_WAIT")+"..</div>");
		html_entry += tab.row("- Preview Scale:",           birdhouse_edit_field(id="set_scale_"+camera, field="devices:cameras:"+camera+":image:preview_scale", type="input", options="", data_type="integer") + " %");
		html_entry += tab.row("- Show Framerate:",          birdhouse_edit_field(id="set_show_framerate_"+camera, field="devices:cameras:"+camera+":image:show_framerate", type="select", options="true,false", data_type="boolean"));
		html_entry += tab.row("- Image Manipulation:",      "<a href='index.html?IMAGE_SETTINGS'>"+lang("IMAGE_SETTINGS")+"</a>");
        html_entry += tab.end();

		id_list += "set_resolution_"+camera+":set_black_white_"+camera+":set_color_schema_"+camera+":";
		id_list += "set_rotation_"+camera+":set_show_framerate_"+camera+":set_crop_"+camera+":set_scale_"+camera+":";
        html_temp += birdhouse_OtherGroup( camera+"_image", "Image Settings", html_entry, false );

        html_entry = tab.start();
		html_entry += tab.row("- Detection Area:",      birdhouse_edit_field(id="set_area_"+camera, field="devices:cameras:"+camera+":similarity:detection_area", type="input", options="", data_type="json"));
		html_entry += tab.row("- Threshold:", birdhouse_edit_field(id="set_threshold_"+camera, field="devices:cameras:"+camera+":similarity:threshold", type="input", options="", data_type="float") + " %");
        html_entry += tab.end();

		id_list += "set_area_"+camera+":set_threshold_"+camera+":";
        html_temp += birdhouse_OtherGroup( camera+"_detect", "Image Similarity Detection", html_entry, false );

        if (settings["server"]["detection_active"]) {
            var model_options = app_data["STATUS"]["object_detection"]["models_available"].join(",");
            html_entry = tab.start();
            html_entry += tab.row("- Image Detection:",     birdhouse_edit_field(id="set_detect_active_"+camera, field="devices:cameras:"+camera+":object_detection:active", type="select", options="true,false", data_type="boolean"));
            html_entry += tab.row("- Detection Size:",      birdhouse_edit_field(id="set_detect_size_"+camera, field="devices:cameras:"+camera+":object_detection:detection_size", type="input", options="", data_type="integer") + " %");
            html_entry += tab.row("- Threshold:",           birdhouse_edit_field(id="set_detect_threshold_"+camera, field="devices:cameras:"+camera+":object_detection:threshold", type="input", options="", data_type="float") + " %");
            html_entry += tab.row("- Classes:",             birdhouse_edit_field(id="set_detect_classes_"+camera, field="devices:cameras:"+camera+":object_detection:classes", type="input", options="", data_type="json"));
            html_entry += tab.row("- Model:",               birdhouse_edit_field(id="set_detect_models_"+camera, field="devices:cameras:"+camera+":object_detection:model", type="select", options=model_options, data_type="string"));
            html_entry += tab.end();

            id_list += "set_detect_active_"+camera+":set_detect_size_"+camera+":set_detect_threshold_"+camera+":set_detect_classes_"+camera+":set_detect_models_"+camera+":";
            html_temp += birdhouse_OtherGroup( camera+"_detect_object", "Image Object Detection", html_entry, false );
            }

		var hours = "00,01,02,03,04,05,06,07,08,09,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24";
        html_entry = tab.start();
		html_entry += tab.row("- Record:",              birdhouse_edit_field(id="set_record_"+camera, field="devices:cameras:"+camera+":video:allow_recording", type="select", options="true,false", data_type="boolean"));
		html_entry += tab.row("- Rhythm:",              "record every " + birdhouse_edit_field(id="set_record_rhythm_"+camera, field="devices:cameras:"+camera+":image_save:rhythm", type="select", options="05,10,15,20", data_type="string") + " s");
		html_entry += tab.row("- Record time:",         "from " + birdhouse_edit_field(id="set_record_from_"+camera, field="devices:cameras:"+camera+":image_save:record_from", type="select", options="sunrise-1,sunrise+0,sunrise+1,"+hours, data_type="string") + " &nbsp; " +
		                                                "to " + birdhouse_edit_field(id="set_record_to_"+camera, field="devices:cameras:"+camera+":image_save:record_to", type="select", options="sunset-1,sunset+0,sunset+1,"+hours, data_type="string")
		    );
		html_entry += tab.row("", "<text id='get_record_image_time_"+camera+"'></text>");
		html_entry += tab.row("- Record offset:",       birdhouse_edit_field(id="set_record_offset_"+camera, field="devices:cameras:"+camera+":image_save:rhythm_offset", type="select", options="0,3,6,12", data_type="string"));
		html_entry += tab.end();

		id_list += "set_record_"+camera+":set_record_rhythm_"+camera+":set_record_from_"+camera+":set_record_to_"+camera+":set_record_offset_"+camera+":";
        html_temp += birdhouse_OtherGroup( camera+"_record_image", "Image Recording", html_entry, false );

        var frame_rates = "4,6,8,10,12,15,18,20,25";
        html_entry = tab.start();
		html_entry += tab.row("- Recording active:",    birdhouse_edit_field(id="set_video_active_"+camera, field="devices:cameras:"+camera+":video:allow_recording", type="select", options="true,false", data_type="boolean"));
		html_entry += tab.row("- Max framerate (HiRes):", birdhouse_edit_field(id="set_max_fps_"+camera, field="devices:cameras:"+camera+":image:framerate", type="select", options=frame_rates, data_type="integer"));
		html_entry += tab.row("- Max length:",          birdhouse_edit_field(id="set_video_max_"+camera, field="devices:cameras:"+camera+":video:max_length", type="select", options="60,120,180,240,300", data_type="integer") + " seconds");
        html_entry += tab.end();

		id_list += "set_video_active_"+camera+":set_video_max_"+camera+":set_max_fps_"+camera+":";
        html_temp += birdhouse_OtherGroup( camera+"_record_video", "Video Recording", html_entry, false );

        if (cameras[camera]["camera_light"]) {
            var relay_names = relay_list;
            var relay_modes = "auto,manual,off,on";
            var relay       = cameras[camera]["camera_light"]["switch"];
            var api_call    = "<button onclick='birdhouse_relayOnOff(\""+relay+"\",\"on\");' class='button-video-edit'  style='background:green;color:white;width:50px;'>ON</button>";
            api_call       += "<button onclick='birdhouse_relayOnOff(\""+relay+"\",\"off\");' class='button-video-edit' style='background:red;color:white;width:50px;'>OFF</button>";

            html_entry = tab.start();
            html_entry += tab.row("- Light switch:",  birdhouse_edit_field(id="set_light_switch_"+camera, field="devices:cameras:"+camera+":camera_light:switch", type="select", options=relay_names, data_type="string"));
            html_entry += tab.row("- Mode:",          birdhouse_edit_field(id="set_light_mode_"+camera, field="devices:cameras:"+camera+":camera_light:mode", type="select", options=relay_modes, data_type="string"));
            html_entry += tab.row("",                 "(auto: on from sunset till sunrise / on: always on / off: always off / manual: start off and control manually)");
            html_entry += tab.row("- Brightness threshold:",  birdhouse_edit_field(id="set_light_threshold_"+camera, field="devices:cameras:"+camera+":camera_light:threshold", type="input", options="", data_type="integer") + " %");
            if (relay != "") {
                html_entry += tab.row("- Test switch:",   api_call);
                }
            html_entry += tab.end();

            id_list += "set_light_switch_"+camera+":set_light_mode_"+camera+":set_light_threshold_"+camera+":";
            html_temp += birdhouse_OtherGroup( camera+"_camera_light", "Camera Light", html_entry, false );
            }

        html_entry = tab.start();
		html_entry += tab.row("- Show Time:",           birdhouse_edit_field(id="set_time_"+camera, field="devices:cameras:"+camera+":image:date_time", type="select", options="true,false", data_type="boolean"));
		html_entry += tab.row("- Position:",            birdhouse_edit_field(id="set_time_pos_"+camera, field="devices:cameras:"+camera+":image:date_time_position", type="input", options="", data_type="json"));
		html_entry += tab.row("- Font Size:",           birdhouse_edit_field(id="set_time_size_"+camera, field="devices:cameras:"+camera+":image:date_time_size", type="input", options="", data_type="float"));
		html_entry += tab.row("- Font Color:",          birdhouse_edit_field(id="set_time_color_"+camera, field="devices:cameras:"+camera+":image:date_time_color", type="input", options="", data_type="json"));
        html_entry += tab.end();

		id_list += ":set_time_"+camera+":set_time_size_"+camera+":set_time_pos_"+camera+":set_time_color_"+camera+":";
        html_temp += birdhouse_OtherGroup( camera+"_time", "Time Information", html_entry, false );

        html_entry = tab.start();
        html_entry += tab.row("Last Recorded:",         "<div id='last_image_recorded_"+camera+"'>"+lang("PLEASE_WAIT")+"..</div>");
        html_entry += tab.row("Image first connect:",  "<a href='/images/test_connect_"+camera+".jpg' target='_blank'>Download test image for "+camera+"</a>");
        html_entry += tab.row("Error Streams:",         "<div id='error_streams_"+camera+"'></div>");
        html_entry += tab.end();

        html_temp += birdhouse_OtherGroup( camera+"_error", "Status", html_entry, false );

        var create = "";
        //if (admin && cameras[camera]["active"]) { var create =  "<button onclick=\""+onclick+"\" class=\"button-video-edit\">&nbsp;"+lang("CREATE_DAY")+"&nbsp;</button> &nbsp; "; }
    	var reconnect =  "<button onclick=\""+onclick2+"\" class=\"button-video-edit\">&nbsp;"+lang("RECONNECT_CAMERA")+"&nbsp;</button> &nbsp; ";

		html_temp += "<hr/>&nbsp;<br/><center>" + reconnect + create + birdhouse_edit_save(id="edit_"+camera, id_list, camera)+"</center><br/>";
	    html_temp += "</div></div>";

		html += birdhouse_OtherGroup( camera, camera_name, html_temp, false, "settings" );
	}
	    }

	return [html, index_info];
}

/*
* Identify available resolutions for the camera
*
* @param (string) camera: camera ID
* @param (string) source: source identifier of the camera
* @returns (string): list of available resolutions
*/
function birdhouseDevices_cameras_resolutions(camera, source="") {

    	var cameras	= app_data["SETTINGS"]["devices"]["cameras"];
    	if (source == "") {
    	    source = getValueById("set_source_"+camera);
    	    }

        var current_available_resolutions = "<u>" + source + "</u>";
        if (app_data["STATUS"]["devices"]["available"]["video_devices_complete"][source]) {
            current_available_resolutions += ": " + JSON.stringify(app_data["STATUS"]["devices"]["available"]["video_devices_complete"][source]["resolutions"]);
            current_available_resolutions = current_available_resolutions.replaceAll(",", ", ");
            // setTextById("set_resolution_"+camera, value);
            }
        else {
            current_available_resolutions += ": N/A";
            }

    setTextById("resolution_per_device_"+camera, current_available_resolutions);
    return current_available_resolutions;
    }

/*
* Create edit form for sensor settings
*
* @param (dict) data: complete setting and status data from API
* @returns (string, dict): html and index information
*/
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
		html_entry += tab.row("Active:", birdhouse_edit_field(id="set_active_"+sensor, field="devices:sensors:"+sensor+":active", type="select", options="true,false", data_type="boolean"));
		html_entry += tab.row("Name:", birdhouse_edit_field(id="set_name_"+sensor, field="devices:sensors:"+sensor+":name", type="input"));
		html_entry += tab.row("Source:", birdhouse_edit_field(id="set_source_"+sensor, field="devices:sensors:"+sensor+":pin", type="input", options="", data_type="integer")
		                + " (data pin on RPi)");
		html_entry += tab.row("Type:", birdhouse_edit_field(id="set_type_"+sensor, field="devices:sensors:"+sensor+":type", type="select", options="dht11,dht22"));
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
		html += birdhouse_OtherGroup( sensor, sensor_name, html_entry, false, "settings" );
	}
	return [html, index_info];
}

/*
* Create edit form for relay settings
*
* @param (dict) data: complete setting and status data from API
* @returns (string, dict): html and index information
*/
function birdhouseDevices_relays(data) {
	var relays = app_data["SETTINGS"]["devices"]["relays"];
	var admin 	= data["STATUS"]["admin_allowed"];
	var html    = "";
	var index_info = {};
	var tab     = new birdhouse_table();
	tab.style_rows["height"] = "27px";

	for (let relay in relays) {
	    relay_name   = relay.toUpperCase() + ": " + relays[relay]["name"];
	    index_info[relay_name] = {};
	    index_info[relay_name]["active"] = relays[relay]["active"];
	    index_info[relay_name]["group"] = relays;
	    index_info[relay_name]["id"] = relay;
	    index_info[relay_name]["type"] = "relay";
	    index_info[relay_name]["status"] = ["active", "error"];

		if (relays[relay]["active"] == false) {
		    relay_name += " &nbsp; <i>(inactive)</i>";
        }
        html_entry = "<div class='camera_info'>";
        html_entry += "<div class='camera_info_image'>";
        html_entry +=  "<div class='sensor_info' id='relay_info_"+relay+"'></div>";
        html_entry += "</div>";
        html_entry += "<div class='camera_info_text'>";
        html_entry += tab.start();
		html_entry += tab.row("Active:", birdhouse_edit_field(id="set_active_"+relay, field="devices:relays:"+relay+":active", type="select", options="true,false", data_type="boolean"));
		html_entry += tab.row("Name:", birdhouse_edit_field(id="set_name_"+relay, field="devices:relays:"+relay+":name", type="input"));
	    html_entry += tab.row("Source:", birdhouse_edit_field(id="set_source_"+relay, field="devices:relays:"+relay+":pin", type="input", options="", data_type="integer") + " (data pin on RPi)");
		html_entry += tab.row("Type:", birdhouse_edit_field(id="set_type_"+relay, field="devices:relays:"+relay+":type", type="select", options="JQC3F"));
        html_entry += tab.end();

        var id_list = "set_name_"+relay+":set_type_"+relay+":set_active_"+relay+":set_source_"+relay;
        html_entry += "<hr/>";
        html_entry += tab.start();
		html_entry += tab.row("<center>"+birdhouse_edit_save(id="edit_"+relay, id_list)+"</center>");
		html_entry += tab.end();
        html_entry += "</div>";
        html_entry += "</div>";
		html += birdhouse_OtherGroup( relay, relay_name, html_entry, false, "settings" );
	}
	return [html, index_info];
}

/*
* Create edit form for weather settings
*
* @param (dict) data: complete setting and status data from API
* @returns (string, dict): html and index information
*/
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
    html_entry += tab.row("Active:", birdhouse_edit_field(id="set_weather_active", field="weather:active", type="select", options="true,false", data_type="boolean"));
    html_entry += tab.row("Source:", birdhouse_edit_field(id="set_weather_source", field="weather:source", type="select", options=weather_config["available_sources"].toString(), data_type="string"));
    html_entry += tab.row("Location:", birdhouse_edit_field(id="set_weather_location", field="weather:location", type="input"));
    // html_entry += tab.row("GPS Position:", birdhouse_edit_field(id="set_weather_gps", field="weather:gps_location", type="input", options="", data_type="json"));
    html_entry += tab.row("GPS Position:", "<div id='gps_coordinates'>"+lang("PLEASE_WAIT")+"..</div>");
    html_entry += tab.end();
    html_entry += "<br/>";

    var html_temp = tab.start();
    html_temp += tab.row("Last Update:", "<div id='weather_info_update'>"+lang("PLEASE_WAIT")+"..</div>");
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
    html += birdhouse_OtherGroup( "weather_settings", title, html_entry, false, "settings" );

	return [html, index_info];
}

/*
* Create edit form for microphone settings
*
* @param (dict) data: complete setting and status data from API
* @returns (string, dict): html and index information
*/
function birdhouseDevices_microphones(data) {
	var micros  = app_data["SETTINGS"]["devices"]["microphones"];
	var devices = app_data["STATUS"]["devices"]["available"]["audio_devices"];
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
        url_new = birdhouseAudioStream_URL(micro, "device_settings", micros[micro]["codec"]);

        html_entry = "<div class='camera_info'>";
        html_entry += "<div class='camera_info_image'>&nbsp;<br/>";
        html_entry += "<div id='mic_img_"+micro+"'>"
        html_entry += birdhouseAudioStream_toggle_image(micro, micros[micro]["codec"]);
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

		id_list += "set_name_"+micro+":set_active_"+micro+":set_device_"+micro+":set_device_name_"+micro+":set_sample_rate_"+micro+":set_chunk_"+micro+":";
		id_list += "set_channels_"+micro+":set_audio_delay_"+micro+":";

        html_entry += tab.start();
		html_entry += tab.row("Active:",      birdhouse_edit_field(id="set_active_"+micro, field="devices:microphones:"+micro+":active", type="select", options="true,false", data_type="boolean"));
		html_entry += tab.row("Name:",        birdhouse_edit_field(id="set_name_"+micro, field="devices:microphones:"+micro+":name", type="input"));
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
		html_temp += tab.row("Audio Delay:",    birdhouse_edit_field(id="set_audio_delay_"+micro, field="devices:microphones:"+micro+":record_audio_delay", type="input", options="", data_type="float") + "s");
        html_temp += tab.end();
        html_entry += birdhouse_OtherGroup( micro + "_settings", "Device settings", html_temp, false );

        html_temp = tab.start();
		html_temp += tab.row("Audio-Stream:",   "<a href='"+url_new+"' target='_blank'>"+url_new+"</a>");
		//html_temp += tab.row("Audio-Control [try-out]",   "<audio controls><source src='"+url_new+"' type='audio/x-wav;codec=PCM'></audio>");
		html_temp += tab.row("Audio-Control:",  "<a onclick='birdhouseAudioStream_play(\""+micro+"\", \""+micros[micro]["codec"]+"\");' style='cursor:pointer;'><u>PLAY</u></a> / <a onclick='birdhouseAudioStream_stop(\""+micro+"\");' style='cursor:pointer;'><u>STOP</u></a>");
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

        html += birdhouse_OtherGroup( micro, micro_name, html_entry, false, "settings" );
	}

	return [html, index_info];
}

/*
* Open one specific group with settings and close all the other
*
* @param (string) group_id: id of the group that shall be opened
*/
function birdhouseDevices_openOne(group_id) {
    for (var i=0;i<birdhouse_device_list.length;i++) {
        if (birdhouse_device_list[i] == group_id) { birdhouse_groupOpen(birdhouse_device_list[i]); }
        else                                      { birdhouse_groupClose(birdhouse_device_list[i]); }
    }
}

/*
* Create view with images settings of all available cameras
*
* @param (dict) data: complete setting and status data from API
*/
function birdhouseDevices_cameraSettings (data) {

    var this_camera_properties  = {};
	var camera_properties       = data["STATUS"]["devices"]["cameras"];
	var camera_settings	        = app_data["SETTINGS"]["devices"]["cameras"];

	var admin   = data["STATUS"]["admin_allowed"];
	var html    = "";
	var tab     = new birdhouse_table();
	tab.style_rows["height"] = "27px";

	for (let camera in camera_settings) {
	    id_list = "";
        info    = {};

        var camera_settings_write   = [];
        var camera_settings_read    = [];
        var camera_settings_measure = [];
    	var camera_settings_main    = ["brightness", "saturation", "contrast", "exposure", "sharpness"];
        var picamera_info           = "";
        var api_call                = "";

        if (camera_settings[camera]["camera_light"] && camera_settings[camera]["camera_light"]["switch"]) {
            var relay = camera_settings[camera]["camera_light"]["switch"];
            if (relay != "") {
                api_call    = "<button onclick='birdhouse_relayOnOff(\""+relay+"\",\"on\");' class='button-video-edit'  style='background:green;color:white;width:50px;'>ON</button>";
                api_call    += "<button onclick='birdhouse_relayOnOff(\""+relay+"\",\"off\");' class='button-video-edit' style='background:red;color:white;width:50px;'>OFF</button>";
            }   }

        // basic settings
        Object.assign(info, camera_settings[camera]);
	    info["type"]  = "detection";
	    info["id"]    = camera + "_img";
	    camera_name   = camera.toUpperCase() + ": " + camera_settings[camera]["name"];
	    camera_stream = birdhouse_Image(camera_name, "info", info);

        // check if camera available
	    if (!camera_properties[camera] || (camera_properties[camera]["error"] || camera_settings[camera]["active"] == false)) {
	        html += "&nbsp;<br/><center>";
	        html += "Camera " + camera.toUpperCase() + " is not available at the moment.<br/>";
	        html += "<a href='index.html?DEVICES'>See device settings for details.</a>";
	        html += "<br/>&nbsp;</center><hr/>";
	        continue;
	        }

        // start settings section
        html += "<div class='camera_info'><div class='camera_info_image'>";
        if (camera_settings[camera]["active"])   { html  += camera_stream; }
        else                                     { html  += lang("CAMERA_INACTIVE"); }
        html += "</div>";
        html += "<div class='camera_info_text'>";

        // check which kind of camera presets
        if (camera_properties[camera]["properties_new"] && Object.keys(camera_properties[camera]["properties_new"]).length > 0) {
            this_camera_properties = camera_properties[camera]["properties_new"];
            this_camera_type = "new";
            if (this_camera_properties["CameraType"] && this_camera_properties["CameraType"][0].indexOf("PiCamera") >= 0) { picamera_info = "(PiCamera)"; }
            }
        else {
            this_camera_properties = camera_properties[camera]["properties"];
            this_camera_type = "old";
            }

        Object.entries(this_camera_properties).forEach(([key,value]) => {
            if (value[1].indexOf("w") >= 0)      { camera_settings_write.push(key); }
            else if (value[1].indexOf("r") >= 0) { camera_settings_read.push(key); }
            if (value[1].indexOf("m") >= 0)      { camera_settings_measure.push(key); }
            });

        console.debug(camera + "/" + this_camera_type);
        console.debug(this_camera_properties);

        var count      = 0;
        var count_sub  = 0;
        html_entry     = "&nbsp;<br/>";
        html_entry    += tab.start();
        html_entry_sub = html_entry;

        for (var i=0;i<camera_settings_write.length;i++) {
            var value = camera_settings_write[i].toLowerCase();
            var key   = camera_settings_write[i].replaceAll("_", " ");

            if (this_camera_type == "new") {
                var range      = "";
                var range      = "";
                var range_text = "";
                var prop       = "";
                var data_type  = this_camera_properties[key][2];
                var data_edit  = "";

                if (this_camera_properties[key][3] != []) {
                    range      = this_camera_properties[key][3][0] + ":" + this_camera_properties[key][3][1];
                    range_text = "[" + this_camera_properties[key][3][0] + ":" + this_camera_properties[key][3][1] + " - " + data_type + "]";
                    }
                if (data_type == "float" || data_type == "integer") {
                    data_edit  = birdhouse_edit_field(id="set_"+value+"_"+camera, field="devices:cameras:"+camera+":image_presets:"+value, type="range", options=range, data_type=data_type);
                    data_edit += " " + birdhouseDevices_cameraSettingsButton(camera, value, "set_"+value+"_"+camera, "change");
                    }
                else if (data_type == "boolean") {
                    data_edit  = "<div style='float:left'>";
                    data_edit += birdhouse_edit_field(id="set_"+value+"_"+camera, field="devices:cameras:"+camera+":image_presets:"+value, type="select", options=",false,true", data_type=data_type);
                    data_edit += "&nbsp; </div>";
                    data_edit += " " + birdhouseDevices_cameraSettingsButton(camera, value, "set_"+value+"_"+camera, "change");
                    }

                if (camera_settings_main.indexOf(key.toLowerCase()) >= 0) {
                    html_entry += tab.row("<b>" + key + ":</b><br/>" + range_text, data_edit);
                    html_entry += tab.row("",   prop);
                    count      += 1;
                    }
                else {
                    html_entry_sub += tab.row("<b>" + key + ":</b><br/>" + range_text, data_edit);
                    html_entry_sub += tab.row("",   prop);
                    count_sub      += 1;
                    }
                }

            else {

                if (this_camera_properties[value][2] != this_camera_properties[value][3]) {
                    var range  = this_camera_properties[2] + ":" + this_camera_properties[value][3];
                    if (this_camera_properties[value].length > 4) {
                        range += ":" + this_camera_properties[value][4];
                        }
                    var range_text  = "[" + this_camera_properties[value][2] + ".." + this_camera_properties[value][3] + "]";
                    var prop        = "";

                    if (camera_settings_measure.indexOf(camera_settings_write[i]) > -1) { prop += "<i>(image=<span id='img_"+value+"_"+camera+"'></span>)</i>"; }
                    html_entry += tab.row("<b>" + key + ":</b><br/>" + range_text,
                                          birdhouse_edit_field(id="set_"+value+"_"+camera, field="devices:cameras:"+camera+":image_presets:"+value, type="range", options=range, data_type="float") +
                                          " " + birdhouseDevices_cameraSettingsButton (camera, value, "set_"+value+"_"+camera, "change"));
                    html_entry += tab.row("",   prop);

                    id_list += "set_"+value+"_"+camera+":";
                    count += 1;
                    }
                else {
                    camera_settings_read.push(camera_settings_write[i]);
                    }
                }
            }
        html_entry     += tab.end();
        if (count == 0) {html_entry += "<center>No entries to edit.</center>"; }
        html_entry += "&nbsp;<br/>";
        html += birdhouse_OtherGroup( camera+"_camera_1", camera.toUpperCase() + " - Camera Settings " + picamera_info, html_entry, true, "settings" );

        if (api_call != "") {
            var call =  "<center>" + api_call + "</center>";
            html += birdhouse_OtherGroup( camera+"_camera_1b", camera.toUpperCase() + " - Camera Light", call, true, "settings" );
            }

        if (count_sub > 0) {
            html_entry_sub += tab.end();
            html_entry_sub += "&nbsp;<br/>";
            html += birdhouse_OtherGroup( camera+"_camera_1c", camera.toUpperCase() + " - Further Camera Settings", html_entry_sub, false, "settings" );
            }

        html_entry = tab.start();
        for (var i=0;i<camera_settings_read.length;i++) {
            var value = camera_settings_read[i].toLowerCase();
            var key   = camera_settings_read[i].replaceAll("_", " ");
            html_entry += tab.row(key + ":", "<span id='prop_"+value+"_"+camera+"'></span>");
        }
        html_entry += tab.end();
        html_entry += "&nbsp;<br/>";
        html += birdhouse_OtherGroup( camera+"_camera_2", camera.toUpperCase() + " - Further Camera Metadata", html_entry, false, "settings" );

        html += "<center>&nbsp;<br/>";
        html += birdhouse_edit_save(id="edit_"+camera, id_list, camera);
        html += birdhouse_edit_other("birdhouse_cameraResetPresets(\""+camera+"\");", lang("RESET"));
        html += "</center>";

        html += "</div></div>";
        html += "&nbsp;<br/>";
        html += "<hr/>";
	}
    html += "&nbsp;<br/>";

    //appSettings.show();
    this.appSettings.write(1, lang("IMAGE_SETTINGS"), html);

    //setTextById(app_frame_content, html);
    //setTextById(app_frame_header, "<center><h2>" + lang("IMAGE_SETTINGS") + "</h2></center>");

	for (let camera in camera_settings) {
        birdhouseDevices_cameraSettingsLoad(camera);
        }
}

/*
* Activate or deactivate interval updating for image settings of the cameras
*
* @param (string) camera: camera ID
* @param (boolean) active: activate (true) or deactivate (false)
*/
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

/*
* Activate or deactivate interval updating for image settings of the cameras
*
* @param (string) camera: camera ID
* @param (string) key: parameter name
* @param (string) field_id: id of field or range slider to grab the value from
* @param (string) description: text on the button
* @returns (string): html code of button
*/
function birdhouseDevices_cameraSettingsButton (camera, key, field_id, description) {
    var onclick = "var cam_value=document.getElementById('"+field_id+"').value; birdhouse_cameraSettings(camera='"+camera+"', key='"+key+"', value=cam_value);"
    var button = "<button onclick=\""+onclick+"\"  class=\"bh-slider-button\">"+description+"</button>";
    return button;
}

app_scripts_loaded += 1;