//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// additional functions 
//--------------------------------------
/* INDEX:
function birdhouse_imageOverlay(filename, description="", favorit="", to_be_deleted="")
function birdhouse_videoOverlay(filename, description="", favorit="", to_be_deleted="")
function birdhouse_videoOverlayToggle(status="")
function birdhouse_overlayHide()
function birdhouse_groupToggle(id)
function iOS()
var loadJS = function(url, implementationCode, location)
var yourCodeToBeCalled = function()
*/
//----------------------------------------

// Tooltips
//----------------------------------------

function birdhouse_initTooltip() {
	tooltip_mode     = "other";
	tooltip_width    = "160px";
	tooltip_height   = "100px";
	tooltip_distance = 47;

	button_tooltip = new jcTooltip("button_tooltip") ;
	button_tooltip.settings( tooltip_mode, tooltip_width, tooltip_height, tooltip_distance );	
	}
	
function birdhouse_tooltip( tooltip_element, tooltip_content, name, left="" ) {
	return button_tooltip.create( tooltip_element, tooltip_content, name, left );
	}

birdhouse_initTooltip();

//----------------------------------------

function birdhouse_imageOverlay(filename, description="", favorit="", to_be_deleted="") {
        var overlay = "<div id=\"overlay_content\" class=\"overlay_content\" onclick=\"birdhouse_overlayHide();\"><!--overlay--></div>";
        setTextById("overlay_content",overlay);
        document.getElementById("overlay").style.display         = "block";
        document.getElementById("overlay_content").style.display = "block";
        document.getElementById("overlay_parent").style.display  = "block";
        
        description = description.replace(/\[br\/\]/g,"<br/>");
        html  = "";
        html += "<div id=\"overlay_image_container\">";
        html += "<div id=\"overlay_close\" onclick='birdhouse_overlayHide();'>[X]</div>";
        html += "<img id='overlay_image' src='"+filename+"'>";
        html += "<br/>&nbsp;<br/>"+description+"</div>";
        document.getElementById("overlay_content").innerHTML = html;
        
        myElement = document.getElementById("overlay_content");
	new window.PinchZoom.default(myElement);
	}

//--------------------------------------

function birdhouse_videoOverlay(filename, description="", favorit="", to_be_deleted="") {
        check_iOS = iOS();
        if (check_iOS == true) {
          window.location.href = filename;
          }
        else {
          document.getElementById("overlay").style.display = "block";
          document.getElementById("overlay_content").style.display = "block";
          description = description.replace(/\[br\/\]/g,"<br/>");
          html  = "";
          html += "<div id=\"overlay_close\" onclick='birdhouse_overlayHide();'>[X]</div>";
          html += "<div id=\"overlay_image_container\">";
          html += "<video id='overlay_video' src=\"" + filename + "\" controls>Video not supported</video>"
          html += "<br/>&nbsp;<br/>"+description+"</div>";
          document.getElementById("overlay_content").innerHTML = html;
          }
	}

//----------------------------------------
	
function birdhouse_videoOverlayToggle(status="") {
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
	        console.error("birdhouse_videoOverlayToggle: Video edit doesn't exist.");
		}
	}

//----------------------------------------

function birdhouse_overlayHide() {
       document.getElementById("overlay").style.display = "none";
       document.getElementById("overlay_content").style.display = "none";
       document.getElementById("overlay_parent").style.display = "none";
       }


//----------------------------------------

function birdhouse_groupToggle(id) {
        if (document.getElementById("group_"+id).style.display == "none") {
                document.getElementById("group_"+id).style.display = "block"
        	if (document.getElementById("group_intro_"+id)) { document.getElementById("group_intro_"+id).style.display = "block"; }
                document.getElementById("group_link_"+id).innerHTML = "(&minus;)"
                images     = document.getElementById("group_ids_"+id).innerHTML;
                image_list = images.split(" ");
                for (let i=0; i<image_list.length; i++) {
                  if (image_list[i] != "") {
			 img      = document.getElementById(image_list[i]);
			 if (img != undefined) {
	                        img_file = img.getAttribute('data-src');
	                        img.src  = img_file;
	                        }
		   }	}
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

//-----------------------------------------
// load addition javascript
//-----------------------------------------

var loadJS = function(url, implementationCode, location){
    //url is URL of external file, implementationCode is the code
    //to be called from the file, location is the location to 
    //insert the <script> element

    //var scriptTag = document.createElement('script');
    var scriptTag = document.getElementById('videoplayer-script');
    scriptTag.src = url;

    scriptTag.onload = implementationCode;
    scriptTag.onreadystatechange = implementationCode;

    location.appendChild(scriptTag);
};

var yourCodeToBeCalled = function(){
//your code goes here
}

//-----------------------------------------
// EOF
