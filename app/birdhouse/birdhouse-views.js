//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// birdhouse views
//--------------------------------------
/* INDEX:
function birdhouse_INDEX(data, camera)
function birdhouse_CAMERAS( title, data )
function birdhouse_VIDEO_DETAIL( title, data )
function birdhouse_LIST(title, data, camera, header_open=true)
*/
//--------------------------------------

function birdhouse_INDEX(data, camera) {

	var html          = "";
	var active_camera = camera;
	var cameras       = data["DATA"]["cameras"];
	var admin_allowed = data["STATUS"]["admin_allowed"];
	var stream_server = RESTurl;
	var active_cam    = {};
	var other_cams    = [];

	for (let key in cameras) {
		if (key == active_camera) {
			active_cam  = {
				"name"        : key,
				"stream"      : cameras[key]["stream"],
				"description" : key.toUpperCase + ": " + cameras[key]["camera_name"]
				}
			}
		else {
			var other_cam  = {
				"name"        : key,
				"stream"      : cameras[key]["stream"],
				"description" : key.toUpperCase + ": " + cameras[key]["camera_name"]
				}
			other_cams.push(other_cam);
			}
		}

	if (active_cam == {}) { active_cam = other_cams[0]; other_cams.shift(); }
	if (cameras.length == 1 || other_cams.length == 0) {
		var onclick  = "birdhousePrint_load(view=\"TODAY\", camera=\""+active_camera+"\");";
		html += birdhouse_Camera(main=true, view="cam1", onclick=onclick, camera=active_cam, stream_server=stream_server, admin_allowed=admin_allowed);
		html += "<br/>&nbsp;<br/>";
		app_camera_source[active_cam["name"]] = stream_server + cameras[active_cam["name"]]["stream"];
		}
	else {
		var onclick  = "birdhousePrint_load(view=\"INDEX\", camera=\""+other_cams[0]["name"]+"\");";
		html += birdhouse_Camera(main=false, view="cam1cam2", onclick=onclick, camera=other_cams[0], stream_server=stream_server, admin_allowed=admin_allowed);
		app_camera_source[other_cams[0]["name"]] = stream_server + cameras[other_cams[0]["name"]]["stream"];

		onclick      = "birdhousePrint_load(view=\"TODAY\", camera=\""+active_camera+"\");";
		html += birdhouse_Camera(main=true, view="cam1cam2", onclick=onclick, camera=active_cam, stream_server=stream_server, admin_allowed=admin_allowed);
		app_camera_source[active_cam["name"]] = stream_server + cameras[active_cam["name"]]["stream"];
		}

	setTextById(app_frame_content,html);
	}

function birdhouse_CAMERAS( title, data ) {
	var cameras	= data["DATA"]["entries"];
	var sensors = data["DATA"]["sensors"];
	var micros  = data["DATA"]["microphones"];
	var admin 	= data["STATUS"]["admin_allowed"];
	var html	= "";

	for (let camera in cameras) {
	    info          = cameras[camera];
	    camera_name   = camera.toUpperCase() + ": " + cameras[camera]["name"];
	    camera_stream = birdhouse_Image(camera_name, cameras[camera]);

		html += birdhouse_OtherGroupHeader( camera, camera_name, true )
		html += "<div id='group_"+camera+"'>";

	    html  += "<div class='camera_info'>";
	    if (cameras[camera]["active"])	{ html  += "<div class='camera_info_image'>"+camera_stream+"</div>"; }
	    else					{ html  += "<div class='camera_info_image'>"+lang("CAMERA_INACTIVE")+"</div>"; }
		html  += "<div class='camera_info_text'>";
		html   += "<ul>"
		html   += "<li>Type: "   + info["camera_type"] + "</li>";
		html   += "<li>Active: " + info["active"] + "</li>";
		html   += "<li>Record: " + info["record"] + "</li>";
		html   += "<li>Image: <ul>";
		html     += "<li>Crop: "   + info["image"]["crop"] + " (yellow rectangle)</li>";
		html     += "<li>Show Time: "   + info["image"]["date_time"] + "</li>";
		html   += "</ul></li>";
		html   += "<li>Detection: <ul>";
		html     += "<li>Threshold: " + info["similarity"]["threshold"] + "%</li>";
		html     += "<li>Area: "      + info["similarity"]["detection_area"] + " (red rectangle)</li>";
		html   += "</ul></li>";
		html   += "<li>Streaming-Server: "+info["video"]["streaming_server"]+"</li>";
		html   += "</ul>";
		html   += "<br/>&nbsp;";
		if (admin && cameras[camera]["active"]) {
			var onclick = "birdhouse_createDayVideo('"+camera+"');";
			html += "<button onclick=\""+onclick+"\" class=\"button-video-edit\">&nbsp;"+lang("CREATE_DAY")+"&nbsp;</button>";
			}
	    html  += "</div></div>";
	    html  += "</div>";
	}
	for (let sensor in sensors) {
        html += birdhouse_OtherGroupHeader( sensor, sensor.toUpperCase()+": "+sensors[sensor]["name"], true );
        html += "<div id='group_"+sensor+"'>";
        html += "<div class='camera_info'>";
        html += "<div class='camera_info_image'>&nbsp;</div>";
        html += "<div class='camera_info_text'><ul>";
        html += "<li>Type: "+sensors[sensor]["type"]+" ("+sensors[sensor]["pin"]+")</li>";
        for (let key in sensors[sensor]["values"]) {
            html += "<li>"+key+": "+sensors[sensor]["values"][key]+" "+sensors[sensor]["units"][key]+"</li>";
        }
        html += "</ul></div></div>";
	    html += "</div>";
	}
	for (let micro in micros) {
	    if (micros[micro]["active"]) {
            url = "http://"+data["DATA"]["ip4_address"]+":"+micros[micro]["port"]+"/";
            html += birdhouse_OtherGroupHeader( micro, micro.toUpperCase()+": "+micros[micro]["name"], true );
            html += "<div id='group_"+micro+"'>";
            html += "<div class='camera_info'>";
            html += "<div class='camera_info_image'>";
            html += birdhouseStream_toggle_image(micro);
            html += "</div>";
            html += "<div class='camera_info_text'><ul>";
            html += "<li>Type: "+micros[micro]["type"]+"</li>";
            html += "<li>URL: <a href='"+url+"' target='_blank'>"+url+"</a></li>";
            html += "<li>Control: <a onclick='birdhouseStream_play(\""+micro+"\");'><u>PLAY</u></a> / ";
            html += "<a onclick='birdhouseStream_stop(\""+micro+"\");'><u>STOP</u></a></li>";
            html += "</ul></div></div>";
            html += "</div>";
	    }
	}
	setTextById(app_frame_content,html);
}

function birdhouse_VIDEO_DETAIL( title, data ) {
	var html = "";
	var video = data["DATA"]["entries"];
	var admin = data["STATUS"]["admin_allowed"];

	for (let key in video) {
		app_active_date         = key;
		var short               = false;
		var video_name          = video[key]["date"];
		var video_stream        = birdhouse_Image("Complete", video[key]);
		var video_stream_short  = "";

		console.log(video_stream);

		if (video[key]["video_file_short"] != undefined && video[key]["video_file_short"] != "") {
	                short                     = true;
		        var video_short           = {};
		        Object.assign( video_short, video[key] );
		        var short_video_file      = video[key]["video_file_short"];
		        video_short["video_file"] = short_video_file;
		        video_stream_short        = birdhouse_Image("Short", video_short);
		        }

		console.log(video_stream);
		console.log(video_stream_short);

		html += "<div class='camera_info'>";
		html += "<div class='camera_info_image'>";
		html += video_stream;
		if (short) {
			html += video_stream_short;
			}
		html += "</div>";
		html += "<div class='camera_info_text'>";
		html += "<h3>"+video_name+"</h3>";
		html += "&nbsp;<br/>";
		html += lang("CAMERA")     + ": " + video[key]["camera"].toUpperCase() + " - " + video[key]["camera_name"] + "<br/>";
		html += lang("LENGTH")     + ": " + Math.round(video[key]["length"]*10)/10 + " s<br/>";
		html += lang("FRAMERATE")  + ": " + video[key]["framerate"]   + " fps<br/>";
		html += lang("FRAMECOUNT") + ": " + video[key]["image_count"] + "<br/>";
		html += lang("IMAGESIZE")  + ": " + video[key]["image_size"]  + "<br/>";
//		html += lang("FILES")  + ": " + video[key]["video_file"]  + "<br/>";
		if (short) {
//			html += lang("FILES")  + ": " + video[key]["video_file_short"]  + "<br/>";
			html += lang("SHORT_VERSION") + ": " + Math.round(video[key]["video_file_short_length"]*10)/10 + " s<br/>";
			}
		if (admin) {
			html += "&nbsp;<br/>";
			html += lang("EDIT") + ":&nbsp; <button onclick=\"birdhouse_videoOverlayToggle();\" class=\"button-video-edit\">&nbsp;"+lang("SHORTEN_VIDEO")+"&nbsp;</button>&nbsp;<br/>";
			html += "</div>";

			var player = "<div id='camera_video_edit_overlay' class='camera_video_edit_overlay' style='display:none'></div>";
			player += "<div id='camera_video_edit' class='camera_video_edit' style='display:none'>";
			player += "<div style='height:46px;width:100%'></div>";
			var trim_command = "appMsg.wait_small('"+lang("PLEASE_WAIT")+"');birdhouse_birdhouse_createShortVideo();";

			loadJS(videoplayer_script, "", document.body);

			video_values = {};
			video_values["VIDEOID"]    = key;
			video_values["ACTIVE"]     = app_active_cam;
			video_values["LENGTH"]     = video[key]["length"];
			video_values["THUMBNAIL"]  = "";
			video_values["VIDEOFILE"]  = video[key]["directory"] + video[key]["video_file"];
			video_values["JAVASCRIPT"] = trim_command;
			videoplayer  = videoplayer_template;
			for (let key in video_values) {
				videoplayer = videoplayer.replace("<!--"+key+"-->",video_values[key]);
				}
			player += videoplayer;
			player += "</div>";

			setTextById("videoplayer",player);
			}
		}

	setTextById(app_frame_content,html);
	}

function birdhouse_LIST(title, data, camera, header_open=true) {

	var html              = "";
	var entry_category    = [];

	var entry_count       = data["DATA"]["view_count"];
	var entries           = data["DATA"]["entries"];
	var entries_yesterday = data["DATA"]["entries_yesterday"];
	var entries_delete    = data["DATA"]["entries_delete"];
	var active_date       = data["DATA"]["active_date"];
	var active_page       = app_active_page;
	var groups            = data["DATA"]["groups"];
	var admin             = data["STATUS"]["admin_allowed"];
	var video_short       = true;

	if (active_page == "VIDEOS")					{ entry_category = [ "video" ]; }
	else if (active_page == "TODAY" && active_date == "")	{ entry_category = [ "today" ]; }
	else if (active_page == "TODAY" && active_date != "")	{ entry_category = [ "backup", active_date ]; }

        if (active_page == "VIDEOS")					{ entry_category = [ "video" ]; }
        else if (active_page == "TODAY" && active_date == "")	{ entry_category = [ "today" ]; }
        else if (active_page == "TODAY" && active_date != "")	{ entry_category = [ "backup", active_date ]; }

        // create chart data
        if (active_page == "TODAY_COMPLETE") {
        	var chart_data = {};
        	var chart_titles = ["Activity"];
        	var chart_keys = Object.keys(entries);
        	for (var i=0;i<chart_keys.length;i++) {
        		var key    = chart_keys[i];
        		if (key.indexOf(":") > 0) { key_print = key.substring(0,5); }
        		else                      { key_print = key.substring(0,2) + ":" + key.substring(2,4); }
        		var value1 = entries[key]["similarity"];
        		if (value1 == 0) { value1 = 100; }
        		value1     = 100 - value1;
        		value1     = Math.round( value1*10) / 10;
        		chart_data[key_print] = [ value1 ];
        	}
            var chart_data_sensor = {}
            var chart_keys_sensor = {}
            for (var i=0;i<chart_keys.length;i++) {
                var key    = chart_keys[i];
        		if (key.indexOf(":") > 0) { key_print = key.substring(0,5); }
        		else                      { key_print = key.substring(0,2) + ":" + key.substring(2,4); }
            	if (entries[key]["sensor"]) {
       		        sensor_data = entries[key]["sensor"];
        		    for (key_sensor in sensor_data) {
        		        for (key_value in sensor_data[key_sensor]) {
        		            key_name = key_value.charAt(0).toUpperCase() + key_value.slice(1) + " ("+key_sensor+")";
        		            chart_keys_sensor[key_name] = 1;
                            if (!chart_data_sensor[key_print]) { chart_data_sensor[key_print] = {}; }
                            chart_data_sensor[key_print][key_name] = sensor_data[key_sensor][key_value];
        		        }
        		    }
        		}
        	}
        	var chart_titles_sensor = Object.keys(chart_keys_sensor);
        	chart_titles_sensor.sort();
        	chart_titles = chart_titles.concat(chart_titles_sensor);
        	for (var key in chart_data) {
        	    if (chart_data_sensor[key]){
                    for (var i=0;i<chart_titles_sensor.length;i++) {
                        var sensor_key = chart_titles_sensor[i];
                        chart_data[key].push(chart_data_sensor[key][sensor_key]);
                    }
        	    }
        	    else {
                    for (var i=0;i<chart_titles_sensor.length;i++) {
                        chart_data[key].push(undefined);
                    }
        	    }
        	}
        	/*
            console.log(entries);
            console.log(chart_titles_sensor);
            console.log(chart_data);
            console.log(chart_data_sensor);
            */
            console.log(chart_titles);
            console.log(chart_data);

            //html += birdhouseChart_create(title=chart_titles, data=chart_data);
            html += birdhouseChart_create(title=data["DATA"]["chart_data"]["titles"],data=data["DATA"]["chart_data"]["data"]);
        }

	// group favorits per month
        if (active_page == "FAVORITS") {
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
                groups = groups2;
                }

	// today complete, favorits
	if (groups != undefined && groups != {}) {
		var count_groups = 0;
		for (let group in groups) {
			var title = group;
			var group_entries = {};
			for (i=0;i<groups[group].length;i++) {
				key                = groups[group][i];
				group_entries[key] = entries[key];
				}
			if (active_page == "ARCHIVE") {
				title = lang("ARCHIVE") + " &nbsp;(" + group + ")";
				if (count_groups > 0) { header_open = false; }
				//--> doesn't work if image names double across the different groups; image IDs have to be changed (e.g. group id to be added)
				}
			delete group_entries["999999"];
			html += birdhouse_ImageGroup(title, group_entries, entry_count, entry_category, header_open, admin, video_short);
			count_groups += 1;
			}
		}
	// today, backup, video
	else {
		entries_available = false;
		if (active_date != undefined && active_date != "")						{ title = active_date; }
	        if (entries != undefined &&  Object.keys(entries).length > 0)				{ html += birdhouse_ImageGroup(title, entries, entry_count, entry_category, header_open, admin, video_short); entries_available = true; }
		if (admin) {
		        if (entries_yesterday != undefined && Object.keys(entries_yesterday).length > 0)	{ html += birdhouse_ImageGroup(lang("YESTERDAY"), entries_yesterday, entry_count, entry_category, false, admin, video_short); entries_available = true; }
		        if (entries_delete != undefined && Object.keys(entries_delete).length > 0)		{ html += birdhouse_ImageGroup(lang("RECYCLE"), entries_delete, ["recycle"], entry_category, false, admin, video_short); entries_available = true; }
		        }
		if (entries_available == false) {
			html += "<center>"+lang("NO_ENTRIES")+"</center>";
			}
		}
	setTextById(app_frame_content, html);
	}


