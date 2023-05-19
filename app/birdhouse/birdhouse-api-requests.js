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
    console.error(commands);
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

    birdhouse_adminLastAnswer(false);
    appMsg.alert(lang("LOGOUT_MSG"));
}

function birdhouse_loginReturn(data) {
    if (data["check-pwd"]) {
        birdhousePrint_load();
        birdhouse_adminLastAnswer(true);
        appMsg.alert("Login successful.");
    }
    else {
        appMsg.alert("Wrong password!");
    }
}

function birdhouse_adminLastAnswer(set=true) {
    if (set) {
        intervalAdmin = setInterval(function() { birdhouse_adminLastAnswerRequest(); }, 5000 );
        }
    else {
        window.clearInterval(intervalAdmin);
    }
}

function birdhouse_adminLastAnswerRequest() {
    birdhouse_apiRequest("GET", ["last-answer"], "", birdhouse_adminLastAnswerReturn, "", "birdhouse_adminLastAnswer");
}

function birdhouse_adminLastAnswerReturn(data) {
    var status = data["STATUS"]["server"];
    if (status["last_answer"] != "") {
        var msg = status["last_answer"];
        appMsg.alert(lang(msg[0]));
        if (msg[0] == "RANGE_DONE") { button_tooltip.hide("info"); }
        birdhouseReloadView();
        }
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

function birdhouse_cameraSettings(camera, key, value) {
	commands = ["camera-settings", key, value, camera];
	birdhouse_apiRequest('POST', commands, '', '','','birdhouse_cameraSettings');
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

function birdhouse_recordStart(camera) {
    commands = ["start-recording", camera];
    birdhouse_apiRequest('POST',commands,"","","","birdhouse_recordStart");
}

function birdhouse_recordStop(camera) {
    commands = ["stop-recording", camera];
    birdhouse_apiRequest('POST',commands,"","","","birdhouse_recordStop");
}

function birdhouse_recordStartAudio(micro) {
    commands = ["start-recording-audio", micro];
    birdhouse_apiRequest('POST',commands,"","","","birdhouse_recordStartAudio");
}

function birdhouse_recordStopAudio(micro) {
    commands = ["stop-recording-audio", micro];
    birdhouse_apiRequest('POST',commands,"","","","birdhouse_recordStopAudio");
}

function birdhouse_forceBackup(camera) {
	commands = ["force-backup",camera];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerOther,'','birdhouse_forceBackup');
	}

function birdhouse_forceUpdateViews() {
	commands = ["update-views"];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerOther,'','birdhouse_forceUpdateViews');
	}

function birdhouse_forceRestart() {

    appMsg.confirm("Restart Birdhouse-Server?", "birdhouse_forceRestart_exec();", 250);
    }

function birdhouse_forceRestart_exec() {
	commands = ["force-restart"];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerOther,'','birdhouse_forceRestart');
	}

function birdhouse_killStream(camera_id, stream_id) {
    console.log("birdhouse_killStream: "+camera_id+" - "+stream_id);
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

    appMsg.confirm("Remove all the data from today?", "birdhouse_removeDataToday_exec();", 250);
}

function birdhouse_removeDataToday_exec() {
	commands = ["clean-data-today"];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerOther,'','birdhouse_removeDataToday');
}

function birdhouse_recreateImageConfig() {
	commands = ["recreate-image-config"];
	birdhouse_apiRequest('POST', commands, '', birdhouse_AnswerRecreateImageConfig,'','birdhouse_recreateImageConfig');
	}

function birdhouse_recycleRange(group_id, index, status, lowres_file) {
	console.log("birdhouse_recycleRange: "+group_id+"/"+index+"/"+lowres_file);
	
	if (group_id in app_recycle_range)              {}
	else                                            { app_recycle_range[group_id]        = {}; }
	if (status == 1)                                { app_recycle_range[group_id][index] = 1; }
	else if (index in app_recycle_range[group_id])  { delete app_recycle_range[group_id][index]; }

	console.log(app_recycle_range);
	
	info_text = document.getElementById("recycle_range_"+group_id+"_info");	
	info_keys = Object.keys(app_recycle_range[group_id]);
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
		
		info_text.innerHTML += "<br/><button id='recycle_button' onclick='"+onclick+"' class='button-video-edit' style='margin-top:6px;'>&nbsp;"+lang("RANGE_DELETE")+"&nbsp;</button>";
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
    camera = data["DATA"]["active"]["active_cam"];
    birdhouseStatus_cameraParam(data, camera);
}

function birdhouse_showWeather() {
	commands = ["status"];
	birdhouse_apiRequest('GET', commands, '', birdhouseWeather,'','birdhouseWeather');
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
