//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// additional functions 
//--------------------------------------
/* INDEX:
function birdhouse_createShortVideo()
function birdhouse_createDayVideo(camera)
function birdhouse_recycleRange(group_id, index, status, lowres_file)
function birdhouse_setRecycleRange(index, status)
function birdhouse_setRecycleRangeShow(command, param)
function birdhouse_setRecycle(index, status, lowres_file="")
function birdhouse_setRecycleShow(command, param)
function birdhouse_setFavorit(index, status, lowres_file="")
function birdhouse_setFavoritShow(command, param)
function birdhouse_AnswerDelete(data)
function birdhouse_AnswerTrim(data)
function birdhouse_AnswerCreateDay(data)
*/
//--------------------------------------

function birdhouse_createShortVideo() {
        video_id = document.getElementById("video-id");
        if (video_id != null) {
                video_id_value = video_id.value;
                tc_in          = document.getElementById("tc-in").value;
                tc_out         = document.getElementById("tc-out").value;
                cam            = document.getElementById("active-cam").value;
                
	        commands = ["create-short-video",video_id_value,tc_in,tc_out,cam];
	        appFW.requestAPI('POST', commands, '', birdhouse_AnswerTrim,'','birdhouse_createShortVideo');
	        }
	else {
	        console.error("birdhouse_createShortVideo: Field 'video-id' is missing!");
		}
	}
	
//----------------------------------------

function birdhouse_createDayVideo(camera) {
	commands = ["create-day-video",camera];
	appFW.requestAPI('POST', commands, '', birdhouse_AnswerCreateDay,'','birdhouse_createDayVideo');
	}
	
//----------------------------------------
// change favorit / recycle status
//----------------------------------------

function birdhouse_recycleRange(group_id, index, status, lowres_file) {
	console.log("birdhouse_recycleRange: "+group_id+"/"+index+"/"+lowres_file);
	
	if (group_id in app_recycle_range) 			{}
	else 							{ app_recycle_range[group_id]        = {}; }
	if (status == 1) 					{ app_recycle_range[group_id][index] = 1; }
	else if (index in app_recycle_range[group_id])	{ delete app_recycle_range[group_id][index]; }

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
        appFW.requestAPI('POST',commands,"",[birdhouse_setRecycleRangeShow,[index,status,lowres_file]],"","birdhouse_setRecycleRange"); 
	}

function birdhouse_setRecycleRangeShow(command, param) {
	console.log("birdhouse_setRecycleRangeShow: /"+command+"/"+param);

	[ index, status, lowres_file, img_id ] = param
        console.log("birdhouse_setRecycleRangeShow: "+lowres_file+" | "+status+" | "+index+" | "+img_id)
        //setTimeout(function(){ birdhouseReloadView(); }, reloadInterval*1000);
	}
	
//----------------------------------------

function birdhouse_setRecycle(index, status, lowres_file="", img_id="") {
        commands    = index.split("/");
        commands[0] = "recycle";
        commands.push(status);
        
        document.getElementById(img_id).style.borderColor = color_code["request"];
        appFW.requestAPI('POST',commands,"",[birdhouse_setRecycleShow,[index,status,lowres_file,img_id]],"","birdhouse_setRecycle"); 
	}

function birdhouse_setRecycleShow(command, param) {
	[ index, status, lowres_file, img_id ] = param
        console.log("birdhouse_setRecycleShow: "+lowres_file+" | "+status+" | "+index+" | "+img_id);
        if (status == 1) { birdhouse_setFavoritShow(command, [ index, 0, lowres_file, img_id ]); } // server-side: if favorit -> 1, trash -> 0
        document.getElementById("d_"+img_id).src  = "birdhouse/img/recycle"+status+".png";       
        if (status == 1) { status = 0; color = color_code["recycle"]; }
        else             { status = 1; color = color_code["default"]; 
        }
        document.getElementById("d_"+img_id+"_value").innerHTML = status;
        document.getElementById(img_id).style.borderColor = color;
	}

//----------------------------------------

function birdhouse_setFavorit(index, status, lowres_file="", img_id="") {
        commands    = index.split("/");
        commands[0] = "favorit";
        commands.push(status);

        document.getElementById(img_id).style.borderColor = color_code["request"];
        appFW.requestAPI('POST',commands,"",[birdhouse_setFavoritShow,[index,status,lowres_file,img_id]],"","birdhouse_setFavorit"); 
	}

function birdhouse_setFavoritShow(command, param) {
	[ index, status, lowres_file, img_id ] = param
        console.log("birdhouse_setFavoritShow: "+lowres_file+" | "+status+" | "+index)
        if (status == 1) { birdhouse_setRecycleShow(command, [ index, 0, lowres_file, img_id ]); } // server-side: if favorit -> 1, trash -> 0
        document.getElementById("s_"+img_id).src          = "birdhouse/img/star"+status+".png";
        if (status == 1) { status = 0; color = color_code["star"]; }
        else             { status = 1; color = color_code["default"]; }
        document.getElementById("s_"+img_id+"_value").innerHTML = status;
        document.getElementById(img_id).style.borderColor = color;
	}

//-----------------------------------------
// Answers
//-----------------------------------------


function birdhouse_AnswerDelete(data) {
	//console.log(data);
	appMsg.alert(lang("DELETE_DONE") + "<br/>(" + data["deleted_count"] + " " + lang("FILES")+")","");
	birdhouseReloadView();
	}

//-----------------------------------------

function birdhouse_AnswerTrim(data) {
	//console.log(data);
	appMsg.alert(lang("TRIM_STARTED"));
	birdhouseReloadView();
	}

//-----------------------------------------

function birdhouse_AnswerCreateDay(data) {
	//console.log(data);
	appMsg.alert(lang("CREATE_DAY_STARTED"));
	birdhouseReloadView();
	}
	
//----------------------------------------
// EOF
