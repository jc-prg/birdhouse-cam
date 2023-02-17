//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// show and edit device information
//--------------------------------------
/* INDEX:
function birdhouseDevices( title, data )
*/
//--------------------------------------

function birdhouseDevices( title, data ) {
	var cameras	= data["DATA"]["devices"]["cameras"];
	var sensors = data["DATA"]["devices"]["sensors"];
	var micros  = data["DATA"]["devices"]["microphones"];
	var admin 	= data["STATUS"]["admin_allowed"];
	var html	= "";
	var tab     = new birdhouse_table();
	tab.style_rows["height"] = "27px";

    //birdhouse_KillActiveStreams();

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
		html_temp += tab.row("Type:", birdhouse_edit_field(id="set_type_"+camera, field="devices:cameras:"+camera+":type", type="select", options="default,pi,usb"));

		if (cameras[camera]["type"] != "default") {
		    html_temp += tab.row("Source:", birdhouse_edit_field(id="set_source_"+camera, field="devices:cameras:"+camera+":source", type="select", options="0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21", data_type="integer"));
            }
        else {
		    var options = data["STATUS"]["system"]["video_dev_new2"];
		    html_temp += tab.row("Source:", birdhouse_edit_field(id="set_source_"+camera, field="devices:cameras:"+camera+":source", type="select_dict", options=options, data_type="string"));
		    }

		html_temp += tab.row("Active:", birdhouse_edit_field(id="set_active_"+camera, field="devices:cameras:"+camera+":active", type="select", options="true,false", data_type="boolean"));
		html_temp += tab.row("Streaming:", cameras[camera]["video"]["streaming_server"]);
		html_temp += tab.end();
		html_temp += "&nbsp;<br/>"
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
		html_entry += tab.row("- Current Streams:", "<div id='show_stream_count_"+camera+"'>Please wait ...</div>");
        html_entry += tab.end();

		id_list += "set_resolution_"+camera+":set_rotation_"+camera+":set_show_framerate_"+camera+":set_crop_"+camera+":set_scale_"+camera+":set_black_white_"+camera+":";
        html_temp += birdhouse_OtherGroup( camera+"_image", "Image/Video", html_entry, false );

        html_entry = tab.start();
		html_entry += tab.row("- Show Time:", birdhouse_edit_field(id="set_time_"+camera, field="devices:cameras:"+camera+":image:date_time", type="select", options="true,false", data_type="boolean"));
		html_entry += tab.row("- Font Size:", birdhouse_edit_field(id="set_time_size_"+camera, field="devices:cameras:"+camera+":image:date_time_size", type="input", options="", data_type="float"));
		html_entry += tab.row("- Font Position:", birdhouse_edit_field(id="set_time_pos_"+camera, field="devices:cameras:"+camera+":image:date_time_position", type="input", options="", data_type="json"));
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
        html_entry += tab.row("Error Camera:", "<textarea id='error_cam_"+camera+"' class='settings_error_msg'></textarea>");
        html_entry += tab.row("Error Image:", "<textarea id='error_img_"+camera+"' class='settings_error_msg'></textarea>");
        html_entry += tab.end();
        html_temp += birdhouse_OtherGroup( camera+"_error", "Error messages", html_entry, false );

        if (admin && cameras[camera]["active"]) { var create =  "<button onclick=\""+onclick+"\" class=\"button-video-edit\">&nbsp;"+lang("CREATE_DAY")+"&nbsp;</button> &nbsp; "; }
    	else { var create = ""; }

    	var reconnect =  "<button onclick=\""+onclick2+"\" class=\"button-video-edit\">&nbsp;"+lang("RECONNECT_CAMERA")+"&nbsp;</button> &nbsp; ";

		html_temp += "<hr/>&nbsp;<br/><center>" + reconnect + create + birdhouse_edit_save(id="edit_"+camera, id_list)+"</center><br/>";
	    html_temp += "</div></div>";

		html += birdhouse_OtherGroup( camera, camera_name, html_temp, open );
	}
	for (let sensor in sensors) {
        open = true;
	    sensor_name   = sensor.toUpperCase() + ": " + sensors[sensor]["name"];
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
        if (sensors[sensor]["status"] && sensors[sensor]["status"]["error"] == true) {
    		html_entry += tab.row("<hr/>");
            html_entry += tab.row("Error-Msg:", sensors[sensor]["status"]["error_msg"]);
        }
		html_entry += tab.row("<hr/>");
		var id_list = "set_name_"+sensor+":set_type_"+sensor+":set_active_"+sensor+":set_source_"+sensor;
		html_entry += tab.row("<center>"+birdhouse_edit_save(id="edit_"+sensor, id_list)+"</center>");
		html_entry += tab.end();
        html_entry += "</div></div>";

		html += birdhouse_OtherGroup( sensor, sensor_name, html_entry, open );
	}
	for (let micro in micros) {
	    open = true;
	    micro_name = micro.toUpperCase() + ": " + micros[micro]["name"];
		if (micros[micro]["active"] == false) {
		    open = false;
		    micro_name += " &nbsp; <i>(inactive)</i>";
        }
        url = "http://"+micros[micro]["stream_server"]+"/"+micro+".mp3";
        html_entry = "<div class='camera_info'>";
        html_entry += "<div class='camera_info_image'>";
        html_entry += birdhouseStream_toggle_image(micro);
        html_entry += "</div>";
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

        html += birdhouse_OtherGroup( micro, micro_name, html_entry, open );
	}

	setTextById(app_frame_content,html);
}
