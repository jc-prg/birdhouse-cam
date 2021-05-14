//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// additional functions 
//--------------------------------------
/* INDEX:
function birdhouse_createShortVideo()
function birdhouse_createDayVideo(camera)
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

function birdhouse_setRecycle(index, status, lowres_file="") {
        commands    = index.split("/");
        commands[0] = "recycle";
        commands.push(status);
        
        document.getElementById(lowres_file).style.borderColor = color_code["request"];
        appFW.requestAPI('POST',commands,"",[birdhouse_setRecycleShow,[index,status,lowres_file]],"","birdhouse_setRecycle"); 
	}

function birdhouse_setRecycleShow(command, param) {
	[ index, status, lowres_file ] = param
        console.log("birdhouse_setRecycleShow: "+lowres_file+" | "+status+" | "+index)
        if (status == 1) { birdhouse_setFavoritShow(command, [ index, 0, lowres_file ]); } // server-side: if favorit -> 1, trash -> 0
        document.getElementById("d_"+index).src  = "birdhouse/img/recycle"+status+".png";       
        if (status == 1) { status = 0; color = color_code["recycle"]; }
        else             { status = 1; color = color_code["default"]; 
        }
        document.getElementById("d_"+index+"_value").innerHTML = status;
        document.getElementById(lowres_file).style.borderColor = color;
	}

//----------------------------------------

function birdhouse_setFavorit(index, status, lowres_file="") {
        commands    = index.split("/");
        commands[0] = "favorit";
        commands.push(status);

        document.getElementById(lowres_file).style.borderColor = color_code["request"];
        appFW.requestAPI('POST',commands,"",[birdhouse_setFavoritShow,[index,status,lowres_file]],"","birdhouse_setFavorit"); 
	}

function birdhouse_setFavoritShow(command, param) {
	[ index, status, lowres_file ] = param
        console.log("birdhouse_setFavoritShow: "+lowres_file+" | "+status+" | "+index)
        if (status == 1) { birdhouse_setRecycleShow(command, [ index, 0, lowres_file ]); } // server-side: if favorit -> 1, trash -> 0
        document.getElementById("s_"+index).src          = "birdhouse/img/star"+status+".png";
        if (status == 1) { status = 0; color = color_code["star"]; }
        else             { status = 1; color = color_code["default"]; }
        document.getElementById("s_"+index+"_value").innerHTML = status;
        document.getElementById(lowres_file).style.borderColor = color;
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
