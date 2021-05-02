//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// additional functions 
//--------------------------------------
/* INDEX:
*/
//--------------------------------------

function requestAPI(command, callback, index="", value="", lowres_file="") {

    commands = command.split("/");
    mboxApp.requestAPI('POST',commands,"",appPrintStatus,"","appPrintStatus_load"); 
    }

//----------------------------------------

function createShortVideo() {
        video_id = document.getElementById("video-id");
        if (video_id != null) {
                video_id_value = video_id.value;
                tc_in          = document.getElementById("tc-in").value;
                tc_out         = document.getElementById("tc-out").value;
                cam            = document.getElementById("active-cam").value;
                
	        commands = ["create-short-video",video_id_value,tc_in,tc_out,cam];
	        mboxApp.requestAPI('POST', commands, '', birdhouse_AnswerTrim,'','createShortVideo');
	        }
	else {
	        console.error("createShortVideo: Field 'video-id' is missing!");
		}
	}
	
//----------------------------------------
// change favorit / recycle status
//----------------------------------------

function setRecycle(index, status, lowres_file="") {
        commands    = index.split("/");
        commands[0] = "recycle";
        commands.push(status);
        
        document.getElementById(lowres_file).style.borderColor = color_code["request"];
        mboxApp.requestAPI('POST',commands,"",[setRecycleShow,[index,status,lowres_file]],"","setRecycle"); 
	}

function setRecycleShow(command, param) {
	[ index, status, lowres_file ] = param
        console.log("setRecycleShow: "+lowres_file+" | "+status+" | "+index)
        if (status == 1) { setFavoritShow(command, [ index, 0, lowres_file ]); } // server-side: if favorit -> 1, trash -> 0
        document.getElementById("d_"+index).src  = "birdhouse/img/recycle"+status+".png";       
        if (status == 1) { status = 0; color = color_code["recycle"]; }
        else             { status = 1; color = color_code["default"]; 
        }
        document.getElementById("d_"+index+"_value").innerHTML = status;
        document.getElementById(lowres_file).style.borderColor = color;
	}

//----------------------------------------

function setFavorit(index, status, lowres_file="") {
        commands    = index.split("/");
        commands[0] = "favorit";
        commands.push(status);

        document.getElementById(lowres_file).style.borderColor = color_code["request"];
        mboxApp.requestAPI('POST',commands,"",[setFavoritShow,[index,status,lowres_file]],"","setFavorit"); 
	}

function setFavoritShow(command, param) {
	[ index, status, lowres_file ] = param
        console.log("setFavoritShow: "+lowres_file+" | "+status+" | "+index)
        if (status == 1) { setRecycleShow(command, [ index, 0, lowres_file ]); } // server-side: if favorit -> 1, trash -> 0
        document.getElementById("s_"+index).src          = "birdhouse/img/star"+status+".png";
        if (status == 1) { status = 0; color = color_code["star"]; }
        else             { status = 1; color = color_code["default"]; }
        document.getElementById("s_"+index+"_value").innerHTML = status;
        document.getElementById(lowres_file).style.borderColor = color;
	}

//-----------------------------------------
// Answers
//-----------------------------------------

function requestAPI_answer(data) {
	console.log(data);
	appMsg.alert("OK!");
	}

//-----------------------------------------

function birdhouse_AnswerDelete(data) {
	//console.log(data);
	appMsg.alert(lang("DELETE_DONE") + "<br/>(" + data["deleted_count"] + " " + lang("FILES")+")","");
	birdhouseReloadView();
	}

//-----------------------------------------

function birdhouse_AnswerTrim(data) {
	//console.log(data);
	appMsg.alert(lang("TRIM_DONE"));
	birdhouseReloadView();
	}

//----------------------------------------
// EOF
