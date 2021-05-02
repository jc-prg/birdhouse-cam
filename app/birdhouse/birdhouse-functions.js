//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// additional functions 
//--------------------------------------
/* INDEX:
*/
//--------------------------------------

function videoOverlay(filename, description="", favorit="", to_be_deleted="") {
        check_iOS = iOS();
        if (check_iOS == true) {
          window.location.href = filename;
          }
        else {
          document.getElementById("overlay").style.display = "block";
          document.getElementById("overlay_content").style.display = "block";
          description = description.replace(/\[br\/\]/g,"<br/>");
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
        document.getElementById("overlay").style.display         = "block";
        document.getElementById("overlay_content").style.display = "block";
        description = description.replace(/\[br\/\]/g,"<br/>");
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
//----------------------------------------
	
function toggleVideoEdit(status="") {
        video_edit1 = document.getElementById("camera_video_edit");
        video_edit2 = document.getElementById("camera_video_edit_overlay");
        if (video_edit1 != null) {
        	if (status == "") {
	        	if (video_edit1.style.display == "none")	{ video_edit1.style.display = "block"; video_edit2.style.display = "block"; }
        		else						{ video_edit1.style.display = "none";  video_edit2.style.display = "none"; }
        		}
        	else if (status == false) { video_edit1.style.display = "none";  video_edit2.style.display = "none"; }
        	else if (status == true)  { video_edit1.style.display = "block"; video_edit2.style.display = "block"; }
        	}
	else {
	        console.error("toggleVideoEdit: Video edit doesn't exist.");
		}
	}

//----------------------------------------

function showHideGroup(id) {
        if (document.getElementById("group_"+id).style.display == "none") {
                document.getElementById("group_"+id).style.display = "block"
        	if (document.getElementById("group_intro_"+id)) { document.getElementById("group_intro_"+id).style.display = "block"; }
                document.getElementById("group_link_"+id).innerHTML = "(&minus;)"
                images     = document.getElementById("group_ids_"+id).innerHTML;
                image_list = images.split(" ");
                for (let i=0; i<image_list.length; i++) {
			 img      = document.getElementById(image_list[i]);
			 if (img != undefined) {
	                        img_file = img.getAttribute('data-src');
	                        img.src  = img_file;
	                        }
			}
		}
	else {
        	document.getElementById("group_"+id).style.display = "none";
        	if (document.getElementById("group_intro_"+id)) { document.getElementById("group_intro_"+id).style.display = "none"; }
        	document.getElementById("group_link_"+id).innerHTML = "(+)";
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
