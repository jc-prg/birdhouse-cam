//----------------------------------------

function videoOverlay(filename, description="", favorit="", to_be_deleted="") {
        check_iOS = iOS();
        if (check_iOS == true) {
          window.location.href = filename;
          }
        else {
          document.getElementById("overlay").style.display = "block";
          document.getElementById("overlay_content").style.display = "block";
          html  = "";
          html += "<div id=\"overlay_close\" onclick='overlayHide();'>[X]</div>";
          html += "<div id=\"overlay_image_container\">";
          html += "<video id='overlay_video' src=\"" + filename + "\" controls>Video not supported</video>"
          html += "<br/>&nbsp;<br/>"+description+"</div>";
          document.getElementById("overlay_content").innerHTML = html;
          }
	}


//----------------------------------------

function imageOverlay(filename, description="", favorit="", to_be_deleted="") {
        document.getElementById("overlay").style.display = "block";
        document.getElementById("overlay_content").style.display = "block";
        html  = "";
        html += "<div id=\"overlay_close\" onclick='overlayHide();'>[X]</div>";
        html += "<div id=\"overlay_image_container\"><img id='overlay_image' src='"+filename+"'><br/>&nbsp;<br/>"+description+"</div>";
        document.getElementById("overlay_content").innerHTML = html;
	}


//----------------------------------------

function overlayHide() {
       document.getElementById("overlay").style.display = "none";
       document.getElementById("overlay_content").style.display = "none";
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

function removeFiles(command) {
   if (confirm("Sollen die Dateien wirklich gelöscht werden?") == true) {
      requestAPI(command, removeFilesAnswer);
      }
   }
   
function removeFilesAnswer() {
   alert("Files removed");
   location.reload();
   }

//----------------------------------------

function setRecycle(index, status, lowres_file="") {
        requestAPI("/recycle", setRecycleShow, index, status, lowres_file);
	}

function setRecycleShow(command, index, status, lowres_file="") {
        console.log("setRecycleShow: "+lowres_file+" | "+status+" | "+index)
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
        console.log("setFavoritShow: "+lowres_file+" | "+status+" | "+index)
        if (status == 1) { setRecycleShow(command, index, 0, lowres_file); } // server-side: if favorit -> 1, trash -> 0
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
        	document.getElementById("group_intro_"+id).style.display = "block"
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
        	document.getElementById("group_intro_"+id).style.display = "none"
        	document.getElementById("group_link_"+id).innerHTML = "(+)"
		}
	}
	
//----------------------------------------
	
function iOS() {
  return [
    'iPad Simulator',
    'iPhone Simulator',
    'iPod Simulator',
    'iPad',
    'iPhone',
    'iPod'
  ].includes(navigator.platform)
  // iPad on iOS 13 detection
  || (navigator.userAgent.includes("Mac") && "ontouchend" in document)
}
