//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// birdhouse image overlay incl. scale and swipe
//--------------------------------------

// Array of image URLs
const imageUrls = [
"images/image1.jpeg",
"images/image2.jpeg",
"images/image3.jpeg",
"images/image4.jpeg",
"images/image5.jpeg",
"images/image6.jpeg",
"images/image7.jpeg",
"images/image8.jpeg",
"images/image9.jpeg",
"images/image10.jpeg"
];

const overlay = document.getElementById("overlay");
let currentIndex = 0;
let touchStartX  = 0;
let initialScale = 1;
let overlayImageList = [];
let overlayImageEntries = {}

/**
* create overlay with scalable hires image
*
* @param (string) filename - filename of the hires image
* @param (string) description - description to be displayed below the image
* @param (string) overlay_replace - alternative image (e.g. with detected objects) to be displayed when moving over the [D]
* @param (string) overlay_id - id of parent element
*/
function birdhouse_imageOverlay(filename, description="", overlay_replace="", swipe=false, overlay_id="overlay_image") {
    if (document.getElementById("overlay_content")) { existing = true; }
    else                                            { existing = false; }

    var overlay = "<div id=\"overlay_content\" class=\"overlay_content\" onclick=\"birdhouse_overlayHide();\"><!--overlay--></div>";
    setTextById("overlay_content",overlay);
    document.getElementById("overlay").style.display         = "block";
    document.getElementById("overlay_content").style.display = "block";
    document.getElementById("overlay_parent").style.display  = "block";

    description = description.replaceAll("[br/]","<br/>");
    description = description.replaceAll("[","<");
    description = description.replaceAll("]",">");

    html  = "";
    html += "<div id=\"overlay_image_container\">";
    html += "<div>";
    html += "  <div id=\"overlay_close\" onclick='birdhouse_overlayHide();'>[X]</div>";
    if (overlay_replace != "") {
        var onmouseover    = "birdhouse_imageOverlayToggle(\""+overlay_id+"\", select=\"replace\")";
        var onmouseout     = "birdhouse_imageOverlayToggle(\""+overlay_id+"\", select=\"original\")";
        var onmousetoggle  = "birdhouse_imageOverlayToggle(\""+overlay_id+"\")";

        html += "  <div id=\"overlay_replace\" onmouseover='"+onmouseover+"' onmouseout='"+onmouseout+"' onclick='"+onmousetoggle+"'>[D]</div>";
        html += "  <img id='"+overlay_id+"_replace' src='"+overlay_replace+"' style='display:none;'  onclick=\"event.stopPropagation();\"/>";
        }
    else {
        html += "  <div id=\"overlay_replace\" style='display:none;'>&nbsp;</div>";
        }

    html += "    <img id='"+overlay_id+"' src='"+filename+"' style='display:block;'  onclick=\"event.stopPropagation();\"/>";
    //html += "</div>";
    //html += "<div id=\"overlay_image_container2\">";
    html += "</div>";
    html += "<br/>&nbsp;<br/><center>"+description+"</center></div>";
    if (swipe) {
      html += '<div class="left-arrow" onclick="event.stopPropagation();prevImage()"></div>';
      html += '<div class="right-arrow" onclick="event.stopPropagation();nextImage()"></div>';
    }

    document.getElementById("overlay_content").innerHTML = html;
    addTouchListenersScale("overlay_content", 1);

    if (swipe) {
        addTouchListenersSwipe("overlay_content");
        }
	}

/**
* show hide the alternative image defined in overlay_replace
*
* @param (string) overlay - id of image to be replaces
* @param (string) select - if left empty, toggle, else use "replace" or "original" to show a specific image
*/
function birdhouse_imageOverlayToggle(overlay_id, select="") {
    if (select == "") {
        if (document.getElementById(overlay_id).style.display != "none") {
            elementHidden(overlay_id);
            elementVisible(overlay_id+"_replace");
            }
        else {
            elementHidden(overlay_id+"_replace");
            elementVisible(overlay_id);
            }
        }
    else if (select == "replace") {
        elementHidden(overlay_id);
        elementVisible(overlay_id+"_replace");
        }
    else {
        elementHidden(overlay_id+"_replace");
        elementVisible(overlay_id);
        }
    }

/**
* create overlay with playable video
*
* @param (string) filename - filepath of video (incl. streaming server)
* @param (string) description - description to be displayed below the video
*/
function birdhouse_videoOverlay(filename, description="", swipe=false) {
    check_iOS = iOS();
    if (check_iOS == true && swipe == false) {
          window.location.href = filename;
          }
    else {
          document.getElementById("overlay").style.display = "block";
          document.getElementById("overlay_content").style.display = "block";
          document.getElementById("overlay_parent").style.display  = "block";

          description = description.replace(/\[br\/\]/g,"<br/>");
          html  = "";
          html += "<div id=\"overlay_close\" onclick='birdhouse_overlayHide();'>[X]</div>";
          html += "<div id=\"overlay_image_container\">";
          html += "<video id='overlay_video' src=\"" + filename + "\" controls>Video not supported</video>"
          html += "<br/>&nbsp;<br/>"+description+"</div>";

          if (swipe) {
              html += '<div class="left-arrow" onclick="event.stopPropagation();prevImage()"></div>';
              html += '<div class="right-arrow" onclick="event.stopPropagation();nextImage()"></div>';
          }

          document.getElementById("overlay_content").innerHTML = html;
          addTouchListenersScale("overlay_content", 1);

          if (swipe) {
              addTouchListenersSwipe("overlay_content");
              }
        }
	}

/**
* toggle between display and not display video overlay
*
* @param (boolean) status - if left empty toggle, else actively show or hide
*/
function birdhouse_videoOverlayToggle(status="") {
        video_edit1 = document.getElementById("camera_video_edit");
        video_edit2 = document.getElementById("camera_video_edit_overlay");
        if (video_edit1 != null) {
        	if (status == "") {
	        	if (video_edit1.style.display == "none")    { video_edit1.style.display = "block"; video_edit2.style.display = "block"; }
        		else                                        { video_edit1.style.display = "none";  video_edit2.style.display = "none"; }
        		}
        	else if (status == false) { video_edit1.style.display = "none";  video_edit2.style.display = "none"; }
        	else if (status == true)  { video_edit1.style.display = "block"; video_edit2.style.display = "block"; }
        	}
	else {
	        console.error("birdhouse_videoOverlayToggle: Video edit doesn't exist.");
		}
	}

/**
* hide image or video overlay completely
*/
function birdhouse_overlayHide() {
       document.getElementById("overlay").style.display = "none";
       document.getElementById("overlay_content").style.display = "none";
       document.getElementById("overlay_parent").style.display = "none";
       }

/*
* Load a list of hires images for swipe functionality in overlay mode
*
* @param (array) entry_keys: sorted list of keys inside the entries
* @param (dict) entries: dict of entries that should be accessible with swiping ... tbc. which data exactly (raw data or data prepared for image display)
*/
function birdhouse_overlayLoadImages(entry_keys=[], entries={}, active_page, admin) {
    if (entry_keys == []) { overlayImageList = []; }
    else {
        overlayImageList = entry_keys;
        for (var i=0;i<entry_keys.length;i++) {
            var key = entry_keys[i];
            overlayImageEntries[key] = birdhouse_ImageDisplayData("...", key, entries[key], active_page, admin);
            }
        }
    currentIndex = 0;
    }

/*
* get image data for based on the index in the currently loaded image entries
*
* @param (integer) index: position in the currently loaded image entries
* @returns (dict): image entry for respected overlay image
*/
function birdhouse_overlayImageByIndex(index) {

    if (index < 0 || index > overlayImageList.length) {
        console.error("birdhouse_overlayImageByIndex: index out of range.");
        return {};
        }
    else {
        var entry_id = overlayImageList[index];
        return overlayImageEntries[entry_id];
        }
}

/*
* show or replace the overlay image by the next address via the given index
*
* @param (integer) index: position of the image in the list of all loaded images
*/
function birdhouse_overlayShowByIndex(index) {

    var img_data = birdhouse_overlayImageByIndex(index);
    var description = img_data["description"];
    if (img_data["description_hires"] != "" && img_data["description_hires"] != undefined) { description = img_data["description_hires"]; }

    //description += "..." + index + "/" + overlayImageList.length;
    if (img_data["type"] == "video") {
        birdhouse_videoOverlay(img_data["hires"], img_data["description"], img_data["swipe"]);
        }
    else if (img_data["hires_stream"]) {
        var [hires, stream_uid]     = birdhouse_StreamURL(app_active_cam, img_data["hires_stream"], "stream_list_5", true);
        birdhouse_imageOverlay(hires, description,  img_data["hires_detect"], img_data["swipe"]);
        }
    else {
        birdhouse_imageOverlay(img_data["hires"], description,  img_data["hires_detect"], img_data["swipe"]);
        }
    currentIndex = index;

    if (index == 0)                        {
        img_data = birdhouse_overlayImageByIndex(overlayImageList.length-1);
        var img = new Image();
        img.src = img_data["hires"];
        img = null;
        }
    else if (index > 0) {
        img_data = birdhouse_overlayImageByIndex(index-1);
        var img = new Image();
        img.src = img_data["hires"];
        img = null;
        }

    if (index == overlayImageList.length-1) {
        img_data = birdhouse_overlayImageByIndex(0);
        var img = new Image();
        img.src = img_data["hires"];
        }
    else if (index < overlayImageList.length-1) {
        img_data = birdhouse_overlayImageByIndex(index+1);
        var img = new Image();
        img.src = img_data["hires"];
        }
    }

/*
* show or replace the overlay image by the next address via the given index
*
* @param (string) entry_id: identifier of the image to be loaded
*/
function birdhouse_overlayShowById(entry_id) {
    var img_data = overlayImageEntries[entry_id];
    if (img_data == undefined) {
        console.error("Could not find '" + entry_id + "' in 'overlayImageEntries'.");
        }
    else {
        currentIndex = overlayImageList.indexOf(entry_id);
        birdhouse_overlayShowByIndex(currentIndex);
        }
    }

/*
* Add all event listeners -  for scaling and swiping
*
* @param (string) div_id - element id of image to be scaled
* @param (string) div_id - initial scaling factor, default=1
*/
function addTouchListeners(div_id, initScale=1) {

    addTouchListenersScale(div_id, initScale);
    addTouchListenersSwipe(div_id);
}

/*
* Function to handle touch events for scaling image; note: it's important to add style "touch-action: none" to the body html element
*
* @param (string) div_id - element id of image to be scaled
* @param (string) div_id - initial scaling factor, default=1
*/
function addTouchListenersScale(div_id, initScale=1) {
    var overlayImage = document.getElementById(div_id);
    let initialPinchDistance = 0;
    initialScale = initScale;
    currentIndex = 0;
    touchStartX = 0;

    overlayImage.addEventListener("touchstart", function(event) {
      if (event.touches.length === 2) {
        initialPinchDistance = Math.hypot(
          event.touches[1].pageX - event.touches[0].pageX,
          event.touches[1].pageY - event.touches[0].pageY
        );

        const computedTransform = getComputedStyle(overlayImage).transform;

        if (computedTransform && computedTransform !== 'none') {
          // Extract the scale from the transformation matrix
          const matrixValues = computedTransform.split('(')[1].split(')')[0].split(',');
          initialScale = parseFloat(matrixValues[0]);
        }

      } else if (event.touches.length === 1) {
        touchStartX = event.touches[0].clientX;
      }
    });

    overlayImage.addEventListener("touchmove", function(event) {
  if (event.touches.length === 2) {
    const currentPinchDistance = Math.hypot(
      event.touches[1].pageX - event.touches[0].pageX,
      event.touches[1].pageY - event.touches[0].pageY
    );
    const scale = initialScale * (currentPinchDistance / initialPinchDistance);
    overlayImage.style.transform = `scale(${scale})`;
  }
});
}

/*
* Function to handle touch events for swiping between images
*
* @param (string) div_id - element id of image to be swiped
*/
function addTouchListenersSwipe(div_id) {
    var overlayImage = document.getElementById(div_id);

    // Check if event listeners have already been added
    if (!overlayImage.hasSwipeListeners) {
        overlayImage.addEventListener("touchstart", function(event) {
            if (event.touches.length === 1) {
                touchStartX = event.touches[0].clientX;
                }
            swipeDetected = false; // Reset the flag on touchstart
            });

        overlayImage.addEventListener("touchend", function(event) {
            if (event.changedTouches.length === 1) { // Check if swipe hasn't been detected yet
                const touchEndX = event.changedTouches[0].clientX;
                const deltaX = touchEndX - touchStartX;
                if (Math.abs(deltaX) > 50) {
                    if (deltaX > 0) {
                        prevImage();
                    } else {
                        nextImage();
                        }
                    console.debug(deltaX);
                    }
                }
            });

        // Mark the element as having event listeners
        overlayImage.hasSwipeListeners = true;
        }
    }

/*
* Function to show the next image
*/
function nextImage() {
    currentIndex = (currentIndex + 1) % overlayImageList.length;
    birdhouse_overlayShowByIndex(currentIndex);
    }

/*
* Function to show the previous image
*/
function prevImage() {
    currentIndex = (currentIndex - 1 + overlayImageList.length) % overlayImageList.length;
    birdhouse_overlayShowByIndex(currentIndex);
    }


app_scripts_loaded += 1;
