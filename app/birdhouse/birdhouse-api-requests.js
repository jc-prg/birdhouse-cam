//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// additional functions 
//--------------------------------------

var intervalAdmin;

/*
* execute API request using the app_session_id if exists
*
* @param (string) method: API request method - GET or POST
* @param (list) commands: list of command parameters
* @param (object) data: data to be transmitted
* @param (object) return_cmd: callback function
* @param (boolean) wait_till_executed: set true for synchronous API request
* @param (string) method_name: name of requesting function for logging
*/
function birdhouse_apiRequest(method, commands, data="", return_cmd="", wait_till_executed=false, method_name="") {
    // app_unique_stream_id -> timestamp
    // app_session_id -> pwd

    if (app_session_id != "") {
        commands.unshift(app_session_id);
        }
    else if (commands[0] != "status" && commands[0] != "version") {
        commands.unshift(app_unique_stream_id);
        }
	appFW.requestAPI(method, commands, data, return_cmd, wait_till_executed, method_name);
}

/*
* execute API request (without using the app_session_id)
*
* @param (string) method: API request method - GET or POST
* @param (list) commands: list of command parameters
* @param (object) return_cmd: callback function
*/
function birdhouse_genericApiRequest(method, commands, return_cmd) {

	birdhouse_apiRequest(method, commands, '', return_cmd,'','birdhouse_genericApiRequest');
}

/*
* create dialog to login
*
* @param (string) login_type: page name to be opened after successful login
*/
function birdhouse_loginDialog(login_type="default") {
    message  = lang("LOGIN_MSG") + "<br/>&nbsp;<br/>";
    message += "<input id='adm_pwd' type='password'>";
    message += "<input id='login_type' type='string' value='"+login_type+"' style='display:none;'>";
    appMsg.confirm(message, "birdhouse_loginCheck(document.getElementById('adm_pwd').value,document.getElementById('login_type').value);", 200);
    document.getElementById('adm_pwd').focus();
}

/*
* send API request to check the password
*
* @param (string) pwd: admin password
* @param (string) login_type: page name to be opened after successful login
*/
function birdhouse_loginCheck(pwd, login_type="") {
    console.log("Check password: " + pwd + " / " + login_type);
    if (login_type == "INDEX" && app_active_page == "INDEX") { login_type == ""; }
    birdhouse_apiRequest("POST", ["check-pwd", pwd, login_type], "", birdhouse_loginReturn, "", "birdhouse_loginCheck");
}

/*
* check in if server returns the password was value
*
* @param (object) data: API response
*/
function birdhouse_loginReturn(data) {
    if (data["check-pwd"]) {
        birdhousePrint_load();
        birdhouse_adminAnswer(true);
        app_admin_allowed = true;
        app_session_id = data["session-id"];
        appFW.appList = app_session_id+"/status";
        appMsg.alert(lang("LOGIN_SUCCESS"));
        setTimeout(function(){ appMsg.hide(); }, 2000);
        if (data["return-page"] != "") { birdhousePrint_page(data["return-page"].toUpperCase()); }
    }
    else {
        appMsg.alert(lang("LOGIN_FAILED"));
    }
}

/*
* remove session id and trigger server-side logout
*/
function birdhouse_logout() {
    app_session_id = "";
    appFW.appList = "status";
    app_admin_allowed = false;
    birdhouse_apiRequest("POST", ["check-pwd", '--logout--'], "", birdhouse_logoutMsg, "", "birdhouse_logout");
    }

/*
* show message when server-side logout has been done
*/
function birdhouse_logoutMsg() {

    birdhousePrint_load("INDEX", app_active_cam);
    birdhouse_settings.toggle(true);
    appSettings.hide();
    birdhouse_adminAnswer(false);
    appMsg.alert(lang("LOGOUT_MSG"));
}

/*
* activate and clear interval request when logged in as administrator
*
* @param (boolean) set: true to start the interval request and false to clear the interval
*/
function birdhouse_adminAnswer(set=true) {
    if (set == true) {
        if (intervalAdmin == undefined) {
            intervalAdmin = setInterval(function() { birdhouse_adminAnswerRequest(); }, 3000 );
        } }
    else {
        window.clearInterval(intervalAdmin);
        intervalAdmin = undefined;
    }
}

/*
* regular interval request when logged in as administrator, this request looks for processes started by the
* administrator that have been finished
*/
function birdhouse_adminAnswerRequest() {

    birdhouse_apiRequest("GET", ["last-answer"], "", birdhouse_adminAnswerReturn, "", "birdhouse_adminLastAnswer");
}

/*
* show a message and reload view when an administrator process has been finished
*
* @param (object) data: API response
*/
function birdhouse_adminAnswerReturn(data) {
    var status = data["STATUS"]["server"];
    if (status["last_answer"] != "") {
        var msg = status["last_answer"];
        appMsg.alert(lang(msg[0]));
        if (msg[0] == "RANGE_DONE") { button_tooltip.hide("info"); }
        birdhouseReloadView();
        }

    birdhouseStatus_loadingViews(data);
    birdhouseStatus_detection(data);
}

/*
* API request to load status and settings (default request)
*/
function birdhouse_loadSettings() {
    commands = ["status"];
	birdhouse_apiRequest('GET', commands, '', birdhouseLoadSettings,'','birdhouse_loadSettings');
}

/*
* API request to shorten a video file based on given timecodes
*/
function birdhouse_createShortVideo() {
        video_id = document.getElementById("video-id");
        if (video_id != null) {
                video_id_value = video_id.value;
                tc_in          = document.getElementById("tc-in").value;
                tc_out         = document.getElementById("tc-out").value;
                cam            = document.getElementById("active-cam").value;
                
	        commands = ["create-short-video",video_id_value,tc_in,tc_out,cam];
	        birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerTrim,'','birdhouse_createShortVideo');
	        }
	else {
	        console.error("birdhouse_createShortVideo: Field 'video-id' is missing!");
		}
	}
	
/*
* API request to create another thumbnail base on a given timecode
*/
function birdhouse_createThumbVideo() {
        setTCin();
        video_id = document.getElementById("video-id");
        if (video_id != null) {
                video_id_value = video_id.value;
                tc_in          = document.getElementById("tc-in").value;
                tc_out         = document.getElementById("tc-out").value;
                cam            = document.getElementById("active-cam").value;

	        commands = ["create-thumb-video",video_id_value,tc_in,tc_out,cam];
	        birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerThumb,'','birdhouse_createThumbVideo');
	        }
	else {
	        console.error("birdhouse_createThumbVideo: Field 'video-id' is missing!");
		}
	}

/*
* API request to start the create of a time-lapse video from all recorded images of today
*/
function birdhouse_createDayVideo(camera) {
	commands = ["create-day-video",camera];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerCreateDay,'','birdhouse_createDayVideo');
	}

/*
* API request to change the title of a recorded video
*
* @param (string) title: new title for the video file
* @param (string) video_id: ID of the video file in the format YYYYMMDD_HHMMSS
* @param (string) camera: camera ID, e.g., "cam1" or "cam2"
*/
function birdhouse_editVideoTitle(title, video_id, camera) {
    title    = document.getElementById(title).value;
    if (title == "") { title = "EMPTY_TITLE_FIELD"; }
	commands = ["edit-video-title", video_id, title, camera];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerOther,'','birdhouse_editVideoTitle');
}

/*
* API request to trigger a camera reconnect
*
* @param (string) camera: camera ID, e.g., "cam1" or "cam2"
*/
function birdhouse_reconnectCamera(camera) {
	commands = ["reconnect-camera",camera];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerReconnect,'','birdhouse_reconnectCamera');
	}

/*
* API request to trigger a microphone reconnect
*
* @param (string) micro: microphone ID, e.g., "mic1" or "mic2"
*/
function birdhouse_reconnectMicrophone(micro) {
	commands = ["reconnect-microphone",micro];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerReconnect,'','birdhouse_reconnectMicrophone');
	}

/*
* API request to change image settings for a camera, e.g., brightness, contrast, hue or other (depending on camera model)
*
* @param (string) camera: camera ID, e.g., "cam1" or "cam2"
* @param (string) key: camera parameter to be change (depending on camera model)
* @param (float) value: value to be set for the parameter
*/
function birdhouse_cameraSettings(camera, key, value) {
	commands = ["camera-settings", key, value, camera];
	birdhouse_apiRequest('POST', commands, '', '','','birdhouse_cameraSettings');
}

/*
* API request to reset camera presets
*
* @param (string) camera: camera ID, e.g., "cam1" or "cam2"
*/
function birdhouse_cameraResetPresets(camera) {
	commands = ["reset-image-presets",camera];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerOther,'','birdhouse_cameraResetPresets');
}

/*
* trigger an API request timeout for demonstration purpose
*/
function birdhouse_checkTimeout() {
	commands = ["check_timeout"];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerOther,'','birdhouse_checkTimeout');
	}

/*
* API request to save changed settings in the main config file (server, cameras, devices, ...)
*
* @param (object) data: data to be saved
* @param (string) camera: camera ID, e.g., "cam1" or "cam2"
*/
function birdhouse_editData(data, camera) {
    commands = ["edit-presets", data, camera];
    birdhouse_apiRequest('POST',commands,"",birdhouse_AnswerEditSend,"","birdhouse_editData");
}

/*
* API request to set or unset recycling based on given threshold
*
* @param (string) category: config type (usually "backup")
* @param (string) date: date of config (archived day)
* @param (float) threshold: threshold to be set (0..100)
* @param (integer) del: 1 if to be deleted, 0 if to be "undeleted"
* @param (string) camera: camera ID, e.g., "cam1" or "cam2"
*/
function birdhouse_recycleThreshold(category, date, threshold, del, camera) {
    commands = ["recycle-threshold", category, date, threshold, del, camera];
    birdhouse_apiRequest('POST',commands,"",birdhouse_AnswerEditSend,"","birdhouse_editData");
}

/*
* API request to identify RECYCLE images based on detected objects
*
* @param (string) category: config type (usually "backup")
* @param (string) date: date of config (archived day)
* @param (integer) del: 1 if to be deleted, 0 if to be "undeleted"
* @param (string) camera: camera ID, e.g., "cam1" or "cam2"
*/
function birdhouse_recycleObject(category, date, del, camera) {
    commands = ["recycle-object-detection", category, date, del, camera];
    birdhouse_apiRequest('POST',commands,"",birdhouse_AnswerEditSend,"","birdhouse_editData");
}

/*
* confirm message if object detection for one or more archived days shall be started
*
* @param (string) camera: camera ID, e.g., "cam1" or "cam2"
* @param (string) date_stamp: ...
* @param (string) date: date of config (archived day)
* @param (string) date_list: list of date separated by comma
* @param (float) threshold: threshold to be used (0..100)
*/
function birdhouse_archiveObjectDetection(camera, date_stamp, date, date_list="", threshold="") {
    if (threshold != "") {
        var threshold = document.getElementById(threshold).value;
        }
    if (date_list != "") {
        var select = document.getElementById(date_list);
        var options = select && select.options;
        var result = [];
        var result_dates = [];
        var opt;
        var count = 0;
        for (var i=0; i<options.length; i++) {
            opt = options[i];
            if (opt.selected) {
                var date_stamp = opt.value.split("_")[0];
                var date = date_stamp.substring(6,8) + "." + date_stamp.substring(4,6) + "." + date_stamp.substring(0,4);
                count +=  Number(opt.value.split("_")[1]);
                result.push(date_stamp);
                result_dates.push(date);
           }    }
        date_list = result_dates.join(", ");
        date_stamp = result.join("_");
        var message = lang("OBJECT_DETECTION_REQUESTS", [date_list, count, threshold]);
    }
    else {
        var message = lang("OBJECT_DETECTION_REQUEST", [date, getTextById("image_count_all_" + date), threshold]);
        }
    appMsg.confirm(message, "birdhouse_archiveObjectDetection_exec('"+camera+"', '"+date_stamp+"', '" + threshold + "');", 150);
    }

/*
* API request to start object detection for one or more archived days
*
* @param (string) camera: camera ID, e.g., "cam1" or "cam2"
* @param (string) date: date of config (archived day)
* @param (float) threshold: threshold to be used (0..100)
*/
function birdhouse_archiveObjectDetection_exec(camera, date, threshold) {
    commands = ["archive-object-detection", camera, date, threshold];
	birdhouse_apiRequest('POST', commands, '', birdhouse_archiveObjectDetection_progress,'','birdhouse_forceBackup');
    }

/*
* alert message to observe the object detection process
*
* @param (object) data: API response
*/
function birdhouse_archiveObjectDetection_progress(data) {

    var msg = lang("DETECTION_PROGRESS") + "<br/><text id='last_answer_detection_progress'>0 %</text>";
    appMsg.alert(msg);
    }

/*
* confirm message whether to remove object detection data from an archived day
*
* @param (string) camera: camera ID, e.g., "cam1" or "cam2"
* @param (string) date_stamp: ...
* @param (string) date: date of the archived day to be removed
*/
function birdhouse_archiveRemoveObjectDetection(camera, date_stamp, date) {
    var message = lang("OBJECT_DETECTION_REQUEST_REMOVE", [date]);
    appMsg.confirm(message, "birdhouse_archiveRemoveObjectDetection_exec('"+camera+"', '"+date_stamp+"');", 150);
    }

/*
* API request to remove object detection data from an archived day
*
* @param (string) camera: camera ID, e.g., "cam1" or "cam2"
* @param (string) date: date of the archived day
*/
function birdhouse_archiveRemoveObjectDetection_exec(camera, date) {
    commands = ["remove-archive-object-detection", camera, date];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerOther,'','birdhouse_forceBackup');
    }

/*
* confirm message whether to delete all data of an archived day
*
* @param (string) date_stamp: ...
* @param (string) date: date of the archived day to be removed
*/
function birdhouse_archiveDayDelete(date_stamp, date) {

    appMsg.confirm(lang("DELETE_ARCHIVE_DAY", [date]), "birdhouse_archiveDayDelete_exec('"+date_stamp+"');", 150);
    }

/*
* API request to delete all data of an archived day
*
* @param (string) date_stamp: ...
*/
function birdhouse_archiveDayDelete_exec(date_stamp) {
    commands = ["archive-remove-day", date_stamp];
	birdhouse_apiRequest('POST', commands, '', birdhouse_archiveDayDelete_done,'','birdhouse_archiveDayDelete_exec(\"'+date_stamp+'\")');
    }

/*
* alert message for the information when deletion is done
*
* @param (object) data: API response
*/
function birdhouse_archiveDayDelete_done(data) {
    window.setTimeout(function(){
        app_active_page='ARCHIVE';
        birdhouseReloadView();
        appMsg.alert(lang("DONE") + "<br/>" + lang("MIGHT_TAKE_A_WHILE"));
        },5000);
    }

/*
* API request to start video recording for the given camera
*
* @param (string) camera: camera ID, e.g., "cam1" or "cam2"
*/
function birdhouse_recordStart(camera) {
    commands = ["start-recording", camera];
    birdhouse_apiRequest('POST',commands,"","","","birdhouse_recordStart");

    b_start  = document.getElementById("rec_start_"+camera);
    b_start.disabled = "disabled";
    b_start.style.color = "red";
    b_stop   = document.getElementById("rec_stop_"+camera);
    b_stop.disabled = "";
    b_cancel = document.getElementById("rec_cancel_"+camera);
    b_cancel.disabled = "";
}

/*
* API request to stop video recording for the given camera
*
* @param (string) camera: camera ID, e.g., "cam1" or "cam2"
*/
function birdhouse_recordStop(camera) {
    commands = ["stop-recording", camera];
    birdhouse_apiRequest('POST',commands,"","","","birdhouse_recordStop");

    b_start  = document.getElementById("rec_start_"+camera);
    b_start.disabled = "";
    b_start.style.color = "white";
    b_stop   = document.getElementById("rec_stop_"+camera);
    b_stop.disabled = "disabled";
    b_cancel = document.getElementById("rec_cancel_"+camera);
    b_cancel.disabled = "disabled";
}

/*
* API request to cancel the video recording or processing for the given camera
*
* @param (string) camera: camera ID, e.g., "cam1" or "cam2"
*/
function birdhouse_recordCancel(camera) {
    commands = ["cancel-recording", camera];
    birdhouse_apiRequest('POST',commands,"","","","birdhouse_recordCancel");

    b_start  = document.getElementById("rec_start_"+camera);
    b_start.disabled = "";
    b_start.style.color = "white";
    b_stop   = document.getElementById("rec_stop_"+camera);
    b_stop.disabled = "disabled";
    b_cancel = document.getElementById("rec_cancel_"+camera);
    b_cancel.disabled = "disabled";
}

/*
* API request to start audio recording into a test file (not used yet)
*
* @param (string) micro: microphone ID, e.g., "mic1" or "mic2"
*/
function birdhouse_recordStartAudio(micro) {
    commands = ["start-recording-audio", micro];
    birdhouse_apiRequest('POST',commands,"","","","birdhouse_recordStartAudio");
}

/*
* API request to stop audio recording into a test file (not used yet)
*
* @param (string) micro: microphone ID, e.g., "mic1" or "mic2"
*/
function birdhouse_recordStopAudio(micro) {
    commands = ["stop-recording-audio", micro];
    birdhouse_apiRequest('POST',commands,"","","","birdhouse_recordStopAudio");
}

/*
* API request to switch a relay on or off, e.g., a relay that is used to control an IR light inside the birdhouse
*
* @param (string) relay: microphone ID, e.g., "mic1" or "mic2"
* @param (string) on_off: target state "on" or "off"
*/
function birdhouse_relayOnOff(relay, on_off) {
	commands = ["relay-"+on_off,relay];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerRequested,'','birdhouse_relayOnOff');
}

/*
* API request to force an archiving of all images from today
*
* @param (string) camera: camera ID, e.g., "cam1" or "cam2"
*/
function birdhouse_forceBackup(camera) {
	commands = ["force-backup",camera];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerRequested,'','birdhouse_forceBackup');
	}

/*
* API request to force an update of all or specific views (archive, object, favorites)
*
* @param (string) view: all or name of the view to be updated (archive, object, favorites)
* @param (boolean) complete: update from config files (false) or recreate them partly (true), usually "false" should be enough
*/
function birdhouse_forceUpdateViews(view="all", complete=false) {
    if (complete)   { commands = ["update-views-complete", view]; }
	else            { commands = ["update-views", view]; }
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerRequested,'','birdhouse_forceUpdateViews');
	}

/*
* confirm message whether to restart the birdhouse-cam server
*/
function birdhouse_forceRestart() {

    appMsg.confirm("Restart Birdhouse-Server?", "birdhouse_forceRestart_exec();", 150);
    }

/*
* API request to force a restart of the birdhouse-cam server
*/
function birdhouse_forceRestart_exec() {
	commands = ["force-restart"];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerRequested,'','birdhouse_forceRestart');
	}

/*
* confirm message whether to shutdown the birdhouse-cam server
*/
function birdhouse_forceShutdown() {

    appMsg.confirm("<font color='red'><b>Shutdown</b></font> Birdhouse-Server?", "birdhouse_forceShutdown_exec();", 150);
    }

/*
* API request to force a shutdown of the birdhouse-cam server
*/
function birdhouse_forceShutdown_exec() {
	commands = ["force-shutdown"];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerRequested,'','birdhouse_forceShutdown');
	}

/*
* API request to kill a video stream on server side to ensure a better server performance
*
* @param (string) camera_id: camera ID, e.g., "cam1" or "cam2"
* @param (string) stream_id: stream ID of the stream to be killed
*/
function birdhouse_killStream(camera_id, stream_id) {

    console.debug("birdhouse_killStream: "+camera_id+" - "+stream_id);
	birdhouse_active_video_streams[stream_id] = false;
    camera_id = camera_id.replace("_img", "");
    stream_id = stream_id.replace("_img", "");
	commands = ["kill-stream", stream_id, camera_id];
	birdhouse_apiRequest('POST', commands, '', birdhouse_killStreamAnswer, '', 'birdhouse_killStream');
    }

/*
* Use API response to show in logs if the stream has been kill successfully
*
* @param (object) data: API response
*/
function birdhouse_killStreamAnswer(data) {
    if (data["kill-stream-id"] && birdhouse_active_video_streams[data["kill-stream-id"]] != undefined) {
        birdhouse_active_video_streams[data["kill-stream-id"]] = false;
        console.debug("birdhouse_killStreamAnswer: killed stream " + data["kill-stream"] + "; id=" + data["kill-stream-id"]);
        }
    else if (data["kill-stream-id"] && birdhouse_active_video_streams[data["kill-stream-id"]] == undefined) {
        console.warn("birdhouse_killStreamAnswer: requested ID wasn't available any more.");
        }
    else {
        console.error("birdhouse_killStreamAnswer: unexpected data returned.");
        console.error(data);
    }
}

/*
* API request to delete all image files marked as to be recycled
*
* @param (string) param1: entry category, e.g., video, today or backup
* @param (string) param2: entry date
*/
function birdhouse_deleteMarkedFiles(param1,param2) {
	commands = ["remove", param1, param2];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerDeleteRequest,'','birdhouse_deleteMarkedFiles');
    }

/*
* confirm message whether to remove all image data from today
*/
function birdhouse_removeDataToday() {

    appMsg.confirm("Remove all the data from today?", "birdhouse_removeDataToday_exec();", 150);
}

/*
* API request to remove all image data from today
*/
function birdhouse_removeDataToday_exec() {
	commands = ["clean-data-today"];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerRequested,'','birdhouse_removeDataToday');
}

/*
* confirm message whether to recreate the image config file for today or another date, e.g.,
* if the file is broken but the image files are still available
*
* @param (string) date: date of the day to recreate the image config file, leave empty for today
*/
function birdhouse_recreateImageConfig(date="") {

    appMsg.confirm(lang("RECREATE_IMG_CONFIG")+"?", "birdhouse_recreateImageConfig_exec();", 150);
}

/*
* API request to recreate the image config file for today or another date, e.g.,
* if the file is broken but the image files are still available
*
* @param (string) date: date of the day to recreate the image config file, leave empty for today
*/
function birdhouse_recreateImageConfig_exec(date="") {
	commands = ["recreate-image-config", date=""];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerRecreateImageConfig,'','birdhouse_recreateImageConfig');
	}

/*
* check, how many other images are selected in the same group and gather relevant data to request the recycling of a range
*
* @param (string) group_id: id of the group of images to analyze
* @param (string) index: id of the currently selected image
* @param (string) status: status of the currently selected image - 1 = recycle; 0 = not recycle
* @param (string) lowres_file: filename of lowres file
*/
function birdhouse_recycleRange(group_id, index, status, lowres_file) {
	console.log("birdhouse_recycleRange: "+group_id+"/"+index+"/"+lowres_file);

	if (status == 1)                                { app_recycle_range[index] = 1; }
	else if (index in app_recycle_range[group_id])  { delete app_recycle_range[index]; }

	console.log(app_recycle_range);

	info_text = document.getElementById("recycle_range_"+group_id+"_info");
	info_keys = Object.keys(app_recycle_range);
	info_keys.sort();

	info_text = document.getElementById("command_dropdown");

    var cancel_button = "<button id='recycle_button_cancel' onclick='button_tooltip.hide(\"info\");' class='button-video-edit' style='margin-top:6px;float:unset;'>&nbsp;"+lang("CANCEL")+"&nbsp;</button>"
	if (info_keys.length == 1) {
		info_text.innerHTML = lang("RANGE_ADD_ENTRY") + "<br/>" + cancel_button; // + " ("+info_keys[0]+")";
		button_tooltip.show("info");
		}
	else if (info_keys.length == 2) {
		info_text.innerHTML = lang("RANGE_SELECTED"); // + " ("+info_keys[1]+"|"+info_keys[0]+")";

		var vars     = info_keys[0].split("/")
		var newindex = info_keys[1] + "/" + vars[(vars.length-1)];

		var onclick  = "birdhouse_setRecycleRange(\""+newindex+"\", 1);";
		onclick     += "document.getElementById(\"recycle_button\").innerHTML=\""+lang("PLEASE_WAIT")+"\";";
		onclick     += "document.getElementById(\"recycle_button\").disabled=true;";

		info_text.innerHTML += "<br/>" + cancel_button +
		        "<button id='recycle_button' onclick='"+onclick+"' class='button-video-edit' style='margin-top:6px;float:unset;'>&nbsp;"+lang("RANGE_DELETE")+"&nbsp;</button>";
		button_tooltip.show("info");
		}
	else {
		button_tooltip.hide("info");
		}
	}

/*
* API request to recycle a range of images between two images marked as to be deleted
*
* @param (string) index: ids of both images that mark the range
* @param (integer) status: 1 = recycle; 0 = unset recycle
*/
function birdhouse_setRecycleRange(index, status) {
	console.log("birdhouse_setRecycleRange: /"+index+"/"+status);
	
        commands    = index.split("/");
        commands[0] = "recycle-range";
        commands.push(status);
        birdhouse_apiRequest('POST',commands,"",[birdhouse_setRecycleRangeShow,[index,status,lowres_file]],"","birdhouse_setRecycleRange");
	}

/*
* show API response for range recycling in the logs
*/
function birdhouse_setRecycleRangeShow(command, param) {
	[ index, status, lowres_file, img_id ] = param
	console.log("birdhouse_setRecycleRangeShow: /"+JSON.stringify(command)+"/"+JSON.stringify(param));
    console.log("birdhouse_setRecycleRangeShow: "+lowres_file+" | "+status+" | "+index+" | "+img_id)
    //setTimeout(function(){ birdhouseReloadView(); }, reloadInterval*1000);
	}
	
/*
* API request to change "recycle" status of an image
*
* @param (string) index: image entry id in the database (usually timestamp)
* @param (string) status: 1 = recycle, 0 = is not recycle
* @param (string) lowres_file: file name and path of the lowres file
* @param (string) img_id: id of the html image element
*/
function birdhouse_setRecycle(index, status, lowres_file="", img_id="") {
        commands    = index.split("/");
        commands[0] = "recycle";
        commands.push(status);
        
        document.getElementById(img_id).style.borderColor = color_code["request"];
        birdhouse_apiRequest('POST',commands,"",[birdhouse_setRecycleShow,[index,status,lowres_file,img_id]],"","birdhouse_setRecycle");
	}

/*
* React on API response to change "recycle" status of an image and visualize its new status
*
* @param (object) command: data of API response
* @param (array) param: param given by birdhouse_setRecycle
*/
function birdhouse_setRecycleShow(command, param) {
	[ index, status, lowres_file, img_id ] = param
        console.log("birdhouse_setRecycleShow: "+lowres_file+" | "+status+" | "+index+" | "+img_id);
        if (status == 1) { birdhouse_setFavoriteShow(command, [ index, 0, lowres_file, img_id ]); } // server-side: if favorit -> 1, trash -> 0
        document.getElementById("d_"+img_id).src  = "birdhouse/img/recycle"+status+".png";       
        if (status == 1) { status = 0; color = color_code["recycle"]; }
        else             { status = 1; color = color_code["default"]; 
        }
        document.getElementById("d_"+img_id+"_value").innerHTML = status;
        document.getElementById(img_id).style.borderColor = color;
	}

/*
* API request to change "favorite" status of an image
*
* @param (string) index: image entry id in the database (usually timestamp)
* @param (string) status: 1 = favorite, 0 = is not favorite
* @param (string) lowres_file: file name and path of the lowres file
* @param (string) img_id: id of the html image element
*/
function birdhouse_setFavorite(index, status, lowres_file="", img_id="") {
        commands    = index.split("/");
        commands[0] = "favorit";
        commands.push(status);

        document.getElementById(img_id).style.borderColor = color_code["request"];
        birdhouse_apiRequest('POST',commands,"",[birdhouse_setFavoriteShow,[index,status,lowres_file,img_id]],"","birdhouse_setFavorit");
	}

/*
* React on API response to change "favorite" status of an image and visualize its new status
*
* @param (object) command: data of API response
* @param (array) param: param given by birdhouse_setFavorite
*/
function birdhouse_setFavoriteShow(command, param) {
	[ index, status, lowres_file, img_id ] = param
        console.log("birdhouse_setFavoriteShow: "+lowres_file+" | "+status+" | "+index)
        if (status == 1) { birdhouse_setRecycleShow(command, [ index, 0, lowres_file, img_id ]); } // server-side: if favorit -> 1, trash -> 0
        document.getElementById("s_"+img_id).src          = "birdhouse/img/star"+status+".png";
        if (status == 1) { status = 0; color = color_code["star"]; }
        else             { status = 1; color = color_code["default"]; }
        document.getElementById("s_"+img_id+"_value").innerHTML = status;
        document.getElementById(img_id).style.borderColor = color;
	}

/*
* API request to load camera related data
*
* @param (string) camera: camera ID, e.g., "cam1" or "cam2"
*/
function birdhouse_getCameraParam(camera) {
    commands = ["camera-param", camera];
    birdhouse_apiRequest('GET',commands,"",birdhouse_showCameraParam,"","birdhouse_getCameraParam");
}

/*
* Use API response to load data and pass it to a function that fills the respective placeholders with camera information
*/
function birdhouse_showCameraParam(data) {
    camera = data["DATA"]["active_cam"];
    birdhouseStatus_cameraParam(data, camera);
}

/*
* API request to load data and pass it to the weather page
*/
function birdhouse_showWeather() {
	commands = ["WEATHER"];
	birdhouse_apiRequest('GET', commands, '', birdhouseWeather,'','birdhouseWeather');
}

/*
* API request to get available bird names from the server
*
* @param (object) data: API response
*/
function birdhouse_birdNamesRequest() {
	commands = ["bird-names"];
	birdhouse_apiRequest('GET', commands, '', birdhouse_birdNamesSet,'','birdhouse_birdNamesRequest()');
}

/*
* Set bird names for the app from requested data
*
* @param (object) data: API response
*/
function birdhouse_birdNamesSet(data) {
    //console.log(app_bird_names);
    app_bird_names = data["DATA"]["data"]["birds"];
}

/*
* Use API response to show deletion of how many files has been successful
*
* @param (object) data: API response
*/
function birdhouse_AnswerDelete(data) {
	//console.log(data);
	appMsg.alert(lang("DELETE_DONE") + "<br/>(" + data["STATUS"]["deleted_count"] + " " + lang("FILES")+")","");
	birdhouseReloadView();
	}

/*
* Use API response to show the API request to delete files
* has been accepted by the server and reload current view
*
* @param (object) data: API response
*/
function birdhouse_AnswerDeleteRequest(data) {
	//console.log(data);
	appMsg.alert(lang("DELETE_REQUESTED"),"");
	birdhouseReloadView();
	}

/*
* Use API response to show the API request to create a shortened video
* has been accepted by the server and reload current view
*
* @param (object) data: API response
*/
function birdhouse_AnswerTrim(data) {
	//console.log(data);
	appMsg.alert(lang("TRIM_STARTED"));
	birdhouseReloadView();
	}

/*
* Use API response to show the API request to create another video thumbnail
* has been accepted by the server and reload current view
*
* @param (object) data: API response
*/
function birdhouse_AnswerThumb(data) {
	//console.log(data);
	appMsg.alert(lang("THUMB_STARTED"));
	birdhouseReloadView();
	}

/*
* Use API response to show the API request to start the create of a time-lapse video from all recorded images of
* today has been accepted by the server and reload current view
*
* @param (object) data: API response
*/
function birdhouse_AnswerCreateDay(data) {
	//console.log(data);
	appMsg.alert(lang("CREATE_DAY_STARTED"));
	birdhouseReloadView();
	}

/*
* Use API response to show a request has been accepted by the server and reload current view
*
* @param (object) data: API response
*/
function birdhouse_AnswerOther(data) {
	//console.log(data);
	appMsg.alert(lang("DONE"));
	birdhouseReloadView();
	}

/*
* Use API response to show a request has been accepted by the server and reload current view
*
* @param (object) data: API response
*/
function birdhouse_AnswerRequested(data) {
	//console.log(data);
	appMsg.alert(lang("REQUEST_SEND"));
	birdhouseReloadView();
	}

/*
* Use API response to show reconnect request has been accepted by the server
*
* @param (object) data: API response
*/
function birdhouse_AnswerReconnect(data) {
	//console.log(data);
	appMsg.alert(lang("DONE"));
	}

/*
* Use API response to show data have been send and accepted by the server
*
* @param (object) data: API response
*/
function birdhouse_AnswerEditSend(data) {
	//console.log(data);
	appMsg.alert(lang("DONE"));
	}

/*
* Use API response to show the API request to start the recreation of the current day config file
* has been accepted by the server and reload current view
*
* @param (object) data: API response
*/
function birdhouse_AnswerRecreateImageConfig(data) {
	//console.log(data);
	appMsg.alert(lang("RECREATE_IMAGE_CONFIG"));
	birdhouseReloadView();
	}


app_scripts_loaded += 1;
