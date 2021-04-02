//----------------------------------------

function imageOverlay(filename, description="", favorit="", to_be_deleted="") {
        document.getElementById("overlay").style.display = "block";
        document.getElementById("overlay_content").style.display = "block";
        html  = "";
        html += "<div id=\"overlay_close\" onclick='document.getElementById(\"overlay\").style.display = \"none\";document.getElementById(\"overlay_content\").style.display = \"none\";'>[X]</div>";
        html += "<div id=\"overlay_image_container\"><img id='overlay_image' src='"+filename+"'><br/>&nbsp;<br/>"+description+"</div>";
        document.getElementById("overlay_content").innerHTML = html;
	}


//----------------------------------------

function requestAPI(command, callback, index="", value="", lowres_file="") {
    var requestURL = command + index + "/" + value;
    var xhttp = new XMLHttpRequest();
    xhttp.onreadystatechange = function() {
         if (this.readyState == 4 && this.status == 200) {
             //alert(this.responseText);
             callback( command, index, value, lowres_file);
         }
         else if (this.readyState == 4) {
             alert("Fehler: "+requestURL);
             callback( command, index, value );
         }
    };
    xhttp.open("POST", requestURL, true);
    xhttp.setRequestHeader("Content-type", "application/json");
    xhttp.send("{ GO : 1 }");
    }

//----------------------------------------

function setTrash(index, status, lowres_file="") {
        requestAPI("/delete", setTrashShow, index, status, lowres_file);
	}

function setTrashShow(command, index, status, lowres_file="") {
        if (status == 1) { setFavoritShow(command, index, 0, lowres_file); } // server-side: if favorit -> 1, trash -> 0
        document.getElementById("d_"+index).src  = "/html/recycle"+status+".png";
        if (status == 1) { status = 0; color = "red"; }
        else             { status = 1; color = "black"; }
        document.getElementById("d_"+index+"_value").innerHTML = status;
        document.getElementById(lowres_file).style.borderColor = color;
	}

//----------------------------------------

function setFavorit(index, status, lowres_file="") {
        requestAPI("/favorit", setFavoritShow, index, status, lowres_file);
	}

function setFavoritShow(command, index, status, lowres_file="") {
        if (status == 1) { setTrashShow(command, index, 0, lowres_file); } // server-side: if favorit -> 1, trash -> 0
        document.getElementById("s_"+index).src          = "/html/star"+status+".png";
        if (status == 1) { status = 0; color = "lime"; }
        else             { status = 1; color = "black"; }
        document.getElementById("s_"+index+"_value").innerHTML = status;
        document.getElementById(lowres_file).style.borderColor = color;
	}

//----------------------------------------

function showHideGroup(id) {
        if (document.getElementById("group_"+id).style.display == "none") {
                document.getElementById("group_"+id).style.display = "block"
                document.getElementById("group_link_"+id).innerHTML = "(&minus;)"
                images     = document.getElementById("group_ids_"+id).innerHTML;
                image_list = images.split(" ");
                for (let i=0; i<image_list.length; i++) {
			 img      = document.getElementById(image_list[i]);
                        img_file = img.getAttribute('data-src');
                        img.src  = img_file;
			}
		}
	else {
        	document.getElementById("group_"+id).style.display = "none"
        	document.getElementById("group_link_"+id).innerHTML = "(+)"
		}
	}
