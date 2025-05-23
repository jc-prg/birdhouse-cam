//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// additional functions 
//--------------------------------------

var intervalAdmin;

function birdhouse_apiRequest(method, commands, data, return_cmd, wait_till_executed, method_name) {
    // app_unique_stream_id -> timestamp
    // app_session_id -> pwd

    if (commands[0] != "status" && commands[0] != "version") {
        if (app_session_id != "")     { commands.unshift(app_session_id); }
        else                          { commands.unshift(app_unique_stream_id); }
        }
	appFW.requestAPI(method, commands, data, return_cmd, wait_till_executed, method_name);
}

function birdhouse_genericApiRequest(method, commands, return_cmd) {

	birdhouse_apiRequest(method, commands, '', return_cmd,'','birdhouse_genericApiRequest');
}

function birdhouse_loginDialog() {
    message  = lang("LOGIN_MSG") + "<br/>&nbsp;<br/>";
    message += "<input id='adm_pwd' type='password'>";
    appMsg.confirm(message, "birdhouse_loginCheck(document.getElementById('adm_pwd').value);", 200);
    document.getElementById('adm_pwd').focus();
}

function birdhouse_loginCheck(pwd) {
    // check via API
    // set session ID based on returned data, if pwd is valid
    // else show message, that pwd is wrong
    app_session_id = pwd;
    birdhouse_apiRequest("POST", ["check-pwd", pwd], "", birdhouse_loginReturn, "", "birdhouse_loginCheck");
}

function birdhouse_logout() {
    app_session_id = "";
    app_admin_allowed = false;
    birdhouse_apiRequest("POST", ["check-pwd", '--logout--'], "", birdhouse_logoutMsg, "", "birdhouse_loginCheck");
    }

function birdhouse_logoutMsg() {

    birdhouse_adminAnswer(false);
    appMsg.alert(lang("LOGOUT_MSG"));
}

function birdhouse_loginReturn(data) {
    if (data["check-pwd"]) {
        birdhousePrint_load();
        birdhouse_adminAnswer(true);
        appMsg.alert("Login successful.");
    }
    else {
        appMsg.alert("Wrong password!");
    }
}

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

function birdhouse_adminAnswerRequest() {

    birdhouse_apiRequest("GET", ["last-answer"], "", birdhouse_adminAnswerReturn, "", "birdhouse_adminLastAnswer");
}

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

function birdhouse_loadSettings() {
    commands = ["status"];
	birdhouse_apiRequest('GET', commands, '', birdhouseLoadSettings,'','birdhouse_loadSettings');
}

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
	
function birdhouse_createDayVideo(camera) {
	commands = ["create-day-video",camera];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerCreateDay,'','birdhouse_createDayVideo');
	}

function birdhouse_editVideoTitle(title, video_id, camera) {
    title    = document.getElementById(title).value;
    if (title == "") { title = "EMPTY_TITLE_FIELD"; }
	commands = ["edit-video-title", video_id, title, camera];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerOther,'','birdhouse_editVideoTitle');
}
	
function birdhouse_reconnectCamera(camera) {
	commands = ["reconnect-camera",camera];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerReconnect,'','birdhouse_reconnectCamera');
	}

function birdhouse_reconnectMicrophone(micro) {
	commands = ["reconnect-microphone",micro];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerReconnect,'','birdhouse_reconnectMicrophone');
	}

function birdhouse_cameraSettings(camera, key, value) {
	commands = ["camera-settings", key, value, camera];
	birdhouse_apiRequest('POST', commands, '', '','','birdhouse_cameraSettings');
}

function birdhouse_cameraResetPresets(camera) {
	commands = ["reset-image-presets",camera];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerOther,'','birdhouse_cameraResetPresets');
}

function birdhouse_checkTimeout() {
	commands = ["check_timeout"];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerOther,'','birdhouse_checkTimeout');
	}

function birdhouse_editData(data, camera) {
    commands = ["edit-presets", data, camera];
    birdhouse_apiRequest('POST',commands,"",birdhouse_AnswerEditSend,"","birdhouse_editData");
}

function birdhouse_recycleThreshold(category, date, threshold, del, camera) {
    commands = ["recycle-threshold", category, date, threshold, del, camera];
    birdhouse_apiRequest('POST',commands,"",birdhouse_AnswerEditSend,"","birdhouse_editData");
}

function birdhouse_recycleObject(category, date, del, camera) {
    commands = ["recycle-object-detection", category, date, del, camera];
    birdhouse_apiRequest('POST',commands,"",birdhouse_AnswerEditSend,"","birdhouse_editData");
}

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

function birdhouse_archiveRemoveObjectDetection(camera, date_stamp, date) {
    var message = lang("OBJECT_DETECTION_REQUEST_REMOVE", [date]);
    appMsg.confirm(message, "birdhouse_archiveRemoveObjectDetection_exec('"+camera+"', '"+date_stamp+"');", 150);
    }

function birdhouse_archiveObjectDetection_exec(camera, date, threshold) {
    commands = ["archive-object-detection", camera, date, threshold];
	birdhouse_apiRequest('POST', commands, '', birdhouse_archiveObjectDetection_progress,'','birdhouse_forceBackup');
    }

function birdhouse_archiveRemoveObjectDetection_exec(camera, date) {
    commands = ["remove-archive-object-detection", camera, date];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerOther,'','birdhouse_forceBackup');
    }

function birdhouse_archiveObjectDetection_progress(data) {

    var msg = lang("DETECTION_PROGRESS") + "<br/><text id='last_answer_detection_progress'>0 %</text>";
    appMsg.alert(msg);
    }

function birdhouse_archiveDayDelete(date_stamp, date) {

    appMsg.confirm(lang("DELETE_ARCHIVE_DAY", [date]), "birdhouse_archiveDayDelete_exec('"+date_stamp+"');", 150);
    }

function birdhouse_archiveDayDelete_exec(date_stamp) {
    commands = ["archive-remove-day", date_stamp];
	birdhouse_apiRequest('POST', commands, '', birdhouse_archiveDayDelete_done,'','birdhouse_archiveDayDelete_exec(\"'+date_stamp+'\")');
    }

function birdhouse_archiveDayDelete_done(data) {
    window.setTimeout(function(){
        app_active_page='ARCHIVE';
        birdhouseReloadView();
        appMsg.alert(lang("DONE") + "<br/>" + lang("MIGHT_TAKE_A_WHILE"));
        },5000);
    }

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

function birdhouse_recordStartAudio(micro) {
    commands = ["start-recording-audio", micro];
    birdhouse_apiRequest('POST',commands,"","","","birdhouse_recordStartAudio");
}

function birdhouse_recordStopAudio(micro) {
    commands = ["stop-recording-audio", micro];
    birdhouse_apiRequest('POST',commands,"","","","birdhouse_recordStopAudio");
}

function birdhouse_relayOnOff(relay, on_off) {
	commands = ["relay-"+on_off,relay];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerRequested,'','birdhouse_relayOnOff');
}

function birdhouse_forceBackup(camera) {
	commands = ["force-backup",camera];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerRequested,'','birdhouse_forceBackup');
	}

function birdhouse_forceUpdateViews(view="all", complete=false) {
    if (complete)   { commands = ["update-views-complete", view]; }
	else            { commands = ["update-views", view]; }
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerRequested,'','birdhouse_forceUpdateViews');
	}

function birdhouse_forceRestart() {

    appMsg.confirm("Restart Birdhouse-Server?", "birdhouse_forceRestart_exec();", 150);
    }

function birdhouse_forceRestart_exec() {
	commands = ["force-restart"];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerRequested,'','birdhouse_forceRestart');
	}

function birdhouse_forceShutdown() {

    appMsg.confirm("<font color='red'><b>Shutdown</b></font> Birdhouse-Server?", "birdhouse_forceShutdown_exec();", 150);
    }

function birdhouse_forceShutdown_exec() {
	commands = ["force-shutdown"];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerRequested,'','birdhouse_forceShutdown');
	}

function birdhouse_killStream(camera_id, stream_id) {

// !!!! Still kills things that are produced somehow even if not necessary?!

    console.log("birdhouse_killStream: "+camera_id+" - "+stream_id);
	birdhouse_active_video_streams[stream_id] = false;
    camera_id = camera_id.replace("_img", "");
    stream_id = stream_id.replace("_img", "");
	commands = ["kill-stream", stream_id, camera_id];
	birdhouse_apiRequest('POST', commands, '', birdhouse_killStreamAnswer, '', 'birdhouse_killStream');
    }

function birdhouse_killStreamAnswer(data) {
    if (data["kill-stream-id"] && birdhouse_active_video_streams[data["kill-stream-id"]] != undefined) {
        birdhouse_active_video_streams[data["kill-stream-id"]] = false;
        console.log("birdhouse_killStreamAnswer: killed stream " + data["kill-stream"] + "; id=" + data["kill-stream-id"]);
        }
    else if (data["kill-stream-id"] && birdhouse_active_video_streams[data["kill-stream-id"]] == undefined) {
        console.warn("birdhouse_killStreamAnswer: requested ID wasn't available any more.");
        }
    else {
        console.error("birdhouse_killStreamAnswer: unexpected data returned.");
        console.error(data);
    }
}

function birdhouse_deleteMarkedFiles(param1,param2) {
	commands = ["remove", param1, param2];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerDeleteRequest,'','birdhouse_deleteMarkedFiles');
    }

function birdhouse_removeDataToday() {

    appMsg.confirm("Remove all the data from today?", "birdhouse_removeDataToday_exec();", 150);
}

function birdhouse_removeDataToday_exec() {
	commands = ["clean-data-today"];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerRequested,'','birdhouse_removeDataToday');
}

function birdhouse_recreateImageConfig(date="") {

    appMsg.confirm(lang("RECREATE_IMG_CONFIG")+"?", "birdhouse_recreateImageConfig_exec();", 150);
}

function birdhouse_recreateImageConfig_exec(date="") {
	commands = ["recreate-image-config", date=""];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerRecreateImageConfig,'','birdhouse_recreateImageConfig');
	}

function birdhouse_recycleRange(group_id, index, status, lowres_file) {
	console.log("birdhouse_recycleRange: "+group_id+"/"+index+"/"+lowres_file);

	if (status == 1)                                { app_recycle_range[index] = 1; }
	else if (index in app_recycle_range[group_id])  { delete app_recycle_range[index]; }

	console.log(app_recycle_range);

	info_text = document.getElementById("recycle_range_"+group_id+"_info");
	info_keys = Object.keys(app_recycle_range);
	info_keys.sort();

	info_text = document.getElementById("command_dropdown");

	if (info_keys.length == 1) {
		info_text.innerHTML = lang("RANGE_ADD_ENTRY"); // + " ("+info_keys[0]+")";
		button_tooltip.show("info");
		}
	else if (info_keys.length == 2) {
		info_text.innerHTML = lang("RANGE_SELECTED"); // + " ("+info_keys[1]+"|"+info_keys[0]+")";

		var vars     = info_keys[0].split("/")
		var newindex = info_keys[1] + "/" + vars[(vars.length-1)];

		var onclick  = "birdhouse_setRecycleRange(\""+newindex+"\", 1);";
		onclick     += "document.getElementById(\"recycle_button\").innerHTML=\""+lang("PLEASE_WAIT")+"\";";
		onclick     += "document.getElementById(\"recycle_button\").disabled=true;";

		info_text.innerHTML += "<br/><button id='recycle_button' onclick='"+onclick+"' class='button-video-edit' style='margin-top:6px;float:unset;'>&nbsp;"+lang("RANGE_DELETE")+"&nbsp;</button>";
		button_tooltip.show("info");
		}
	else {
		button_tooltip.hide("info");
		}
	}

function birdhouse_setRecycleRange(index, status) {
	console.log("birdhouse_setRecycleRange: /"+index+"/"+status);
	
        commands    = index.split("/");
        commands[0] = "recycle-range";
        commands.push(status);
        birdhouse_apiRequest('POST',commands,"",[birdhouse_setRecycleRangeShow,[index,status,lowres_file]],"","birdhouse_setRecycleRange");
	}

function birdhouse_setRecycleRangeShow(command, param) {
	console.log("birdhouse_setRecycleRangeShow: /"+command+"/"+param);

	[ index, status, lowres_file, img_id ] = param
        console.log("birdhouse_setRecycleRangeShow: "+lowres_file+" | "+status+" | "+index+" | "+img_id)
        //setTimeout(function(){ birdhouseReloadView(); }, reloadInterval*1000);
	}
	
function birdhouse_setRecycle(index, status, lowres_file="", img_id="") {
        commands    = index.split("/");
        commands[0] = "recycle";
        commands.push(status);
        
        document.getElementById(img_id).style.borderColor = color_code["request"];
        birdhouse_apiRequest('POST',commands,"",[birdhouse_setRecycleShow,[index,status,lowres_file,img_id]],"","birdhouse_setRecycle");
	}

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

function birdhouse_setFavorite(index, status, lowres_file="", img_id="") {
        commands    = index.split("/");
        commands[0] = "favorit";
        commands.push(status);

        document.getElementById(img_id).style.borderColor = color_code["request"];
        birdhouse_apiRequest('POST',commands,"",[birdhouse_setFavoriteShow,[index,status,lowres_file,img_id]],"","birdhouse_setFavorit");
	}

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

function birdhouse_getCameraParam(camera) {
    commands = ["camera-param", camera];
    birdhouse_apiRequest('GET',commands,"",birdhouse_showCameraParam,"","birdhouse_getCameraParam");
}

function birdhouse_showCameraParam(data) {
    camera = data["DATA"]["active_cam"];
    birdhouseStatus_cameraParam(data, camera);
}

function birdhouse_showWeather() {
	commands = ["WEATHER"];
	birdhouse_apiRequest('GET', commands, '', birdhouseWeather,'','birdhouseWeather');
}

function birdhouse_birdNamesRequest() {
	commands = ["bird-names"];
	birdhouse_apiRequest('GET', commands, '', birdhouse_birdNamesSet,'','birdhouse_birdNamesRequest()');
}

function birdhouse_birdNamesSet(data) {
    //console.log(app_bird_names);
    app_bird_names = data["DATA"]["data"]["birds"];
}

function birdhouse_AnswerDelete(data) {
	//console.log(data);
	appMsg.alert(lang("DELETE_DONE") + "<br/>(" + data["STATUS"]["deleted_count"] + " " + lang("FILES")+")","");
	birdhouseReloadView();
	}

function birdhouse_AnswerDeleteRequest(data) {
	//console.log(data);
	appMsg.alert(lang("DELETE_REQUESTED"),"");
	birdhouseReloadView();
	}

function birdhouse_AnswerTrim(data) {
	//console.log(data);
	appMsg.alert(lang("TRIM_STARTED"));
	birdhouseReloadView();
	}

function birdhouse_AnswerCreateDay(data) {
	//console.log(data);
	appMsg.alert(lang("CREATE_DAY_STARTED"));
	birdhouseReloadView();
	}

function birdhouse_AnswerOther(data) {
	//console.log(data);
	appMsg.alert(lang("DONE"));
	birdhouseReloadView();
	}

function birdhouse_AnswerRequested(data) {
	//console.log(data);
	appMsg.alert(lang("REQUEST_SEND"));
	birdhouseReloadView();
	}

function birdhouse_AnswerReconnect(data) {
	//console.log(data);
	appMsg.alert(lang("DONE"));
	}

function birdhouse_AnswerEditSend(data) {
	//console.log(data);
	appMsg.alert(lang("DONE"));
	}

function birdhouse_AnswerRecreateImageConfig(data) {
	//console.log(data);
	appMsg.alert(lang("RECREATE_IMAGE_CONFIG"));
	birdhouseReloadView();
	}

app_scripts_loaded += 1;