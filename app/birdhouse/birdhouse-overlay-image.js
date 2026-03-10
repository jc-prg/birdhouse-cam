//--------------------------------------
// jc://birdhouse/overlay-image/
//--------------------------------------


/*
* create, manage, and navigate images in overlay and fullscreen mode
*/
class BirdhouseOverlayImage {
    constructor(name) {
        this.name = name;

        this.overlay = document.getElementById("overlay");
        this.currentIndex = 0;
        this.touchStartX  = 0;
        this.initialScale = 1;
        this.overlayImageList = [];
        this.overlayImageEntries = {}

        this.next = this.next.bind(this);
        this.previous = this.previous.bind(this);

    }

    /*
    * create overlay with scalable hires image
    *
    * @param (string) filename - filename of the hires image
    * @param (string) description - description to be displayed below the image
    * @param (string) overlay_replace - alternative image (e.g. with detected objects) to be displayed when moving over the [D]
    * @param (string) overlay_id - id of parent element
    */
    image (filename, description="", overlay_replace="", swipe=false, overlay_id="overlay_image", favorite=false) {

        let existing = !!document.getElementById("overlay_content");

        let overlay = "<div id=\"overlay_content\" class=\"overlay_content\" onclick=\""+this.name+".hide();\"><!--overlay--></div>";
        setTextById("overlay_content",overlay);

        document.getElementById("overlay").style.display         = "block";
        document.getElementById("overlay_content").style.display = "block";
        document.getElementById("overlay_parent").style.display  = "block";
        document.body.style.overflow = 'hidden';

        description = description.replaceAll("[br/]","<br/>");
        description = description.replaceAll("[","<");
        description = description.replaceAll("]",">");

        let html = "";
        html += "<div id=\"overlay_image_container\">";
        html += "<div>";
        html += "  <div id=\"overlay_close\" onclick='"+this.name+".hide();'>[X]</div>";
        if (overlay_replace !== "") {
            let onmouseover    = this.name+".image_toggle(\""+overlay_id+"\", select=\"replace\")";
            let onmouseout     = this.name+".image_toggle(\""+overlay_id+"\", select=\"original\")";
            let onmousetoggle  = this.name+".image_toggle(\""+overlay_id+"\")";

            html += "  <div id=\"overlay_replace\" onmouseover='"+onmouseover+"' onmouseout='"+onmouseout+"' onclick='"+onmousetoggle+"'>[D]</div>";
            html += "  <img id='"+overlay_id+"_replace' src='"+overlay_replace+"' style='display:none;'  onclick=\"event.stopPropagation();\" alt=''/>";
        }
        else {
            html += "  <div id=\"overlay_replace\" style='display:none;'>&nbsp;</div>";
        }

        let border_style = "";
        if (favorite === true) { border_style = "border-color:"+color_code["star"]+";"; }

        html += "    <img id='"+overlay_id+"' src='"+filename+"' style='display:block;"+border_style+"'  onclick=\"event.stopPropagation();\"/>";
        html += "</div>";
        html += "<br/>&nbsp;<br/><center>"+description+"</center></div>";
        if (swipe) {
            html += '<div class="left-arrow" onclick="event.stopPropagation();'+this.name+'.previous()"></div>';
            html += '<div class="right-arrow" onclick="event.stopPropagation();'+this.name+'.next()"></div>';
        }

        document.getElementById("overlay_content").innerHTML = html;
        this.add_touch_scale("overlay_content", 1);

        if (swipe) {
            this.add_touch_swipe("overlay_content");
        }
    }

    /*
    * show hide the alternative image defined in overlay_replace
    *
    * @param (string) overlay - id of image to be replaces
    * @param (string) select - if left empty, toggle, else use "replace" or "original" to show a specific image
    */
    image_toggle (overlay_id, select="") {
        if (select === "") {
            if (document.getElementById(overlay_id).style.display !== "none") {
                elementHidden(overlay_id);
                elementVisible(overlay_id+"_replace");
            }
            else {
                elementHidden(overlay_id+"_replace");
                elementVisible(overlay_id);
            }
        }
        else if (select === "replace") {
            elementHidden(overlay_id);
            elementVisible(overlay_id+"_replace");
        }
        else {
            elementHidden(overlay_id+"_replace");
            elementVisible(overlay_id);
        }
    }

    /*
    * create overlay with playable video
    *
    * @param (string) filename - filepath of video (incl. streaming server)
    * @param (string) description - description to be displayed below the video
    */
    video (filename, description="", swipe=false) {
        const check_iOS = iOS();
        if (check_iOS === true && swipe === false) {
            window.location.href = filename;
        }
        else {
            document.getElementById("overlay").style.display = "block";
            document.getElementById("overlay_content").style.display = "block";
            document.getElementById("overlay_parent").style.display  = "block";

            description = description.replace(/\[br\/\]/g,"<br/>");
            let html  = "";
            html += "<div id=\"overlay_close\" onclick='"+this.name+".hide();'>[X]</div>";
            html += "<div id=\"overlay_image_container\">";
            html += "<video id='overlay_video' src=\"" + filename + "\" controls>Video not supported</video>";
            html += "<br/>&nbsp;<br/>"+description+"</div>";

            if (swipe) {
                html += '<div class="left-arrow" onclick="event.stopPropagation();'+this.name+'.previous()"></div>';
                html += '<div class="right-arrow" onclick="event.stopPropagation();'+this.name+'.next()"></div>';
            }

            document.getElementById("overlay_content").innerHTML = html;
            this.add_touch_scale("overlay_content", 1);

            if (swipe) {
                this.add_touch_swipe("overlay_content");
            }
        }
    }

    /*
    * toggle between display and not display video overlay
    *
    * @param (boolean) status - if left empty toggle, else actively show or hide
    */
    video_toggle (status="") {
        toggleVideoEdit(status);
    }

    /*
    * Load a list of hires images for swipe functionality in overlay mode
    *
    * @param (array) entry_keys: sorted list of keys inside the entries
    * @param (dict) entries: dict of entries that should be accessible with swiping ... tbc. which data exactly (raw data or data prepared for image display)
    */
    load_list (entry_keys=[], entries={}, active_page, admin) {
        if (entry_keys === []) { this.overlayImageList = []; }
        else {
            this.overlayImageList = entry_keys;
            for (let i=0;i<entry_keys.length;i++) {
                let key = entry_keys[i];
                this.overlayImageEntries[key] = birdhouse_ImageDisplayData("...", key, entries[key], active_page, admin);
            }
        }
        this.currentIndex = 0;
    }

    /*
* Function to show the next image
*/
    next () {
        this.currentIndex = (this.currentIndex + 1) % this.overlayImageList.length;
        this.show_by_index(this.currentIndex);
    }

    /*
    * Function to show the previous image
    */
    previous () {
        this.currentIndex = (this.currentIndex - 1 + this.overlayImageList.length) % this.overlayImageList.length;
        this.show_by_index(this.currentIndex);
    }

    /*
* get image data for based on the index in the currently loaded image entries
*
* @param (integer) index: position in the currently loaded image entries
* @returns (dict): image entry for respected overlay image
*/
    get_by_index (index) {

        if (index < 0 || index > this.overlayImageList.length) {
            console.error("BirdhouseOverlayImage.get_by_index: index out of range.");
            return {};
        }
        else {
            const entry_id = this.overlayImageList[index];
            return this.overlayImageEntries[entry_id];
        }
    }

    /*
    * show or replace the overlay image by the next address via the given index
    *
    * @param (integer) index: position of the image in the list of all loaded images
    */
    show_by_index (index) {

        let img_data = this.get_by_index(index);
        let description = img_data["description"];
        if (img_data["description_hires"] !== "" && img_data["description_hires"] !== undefined) { description = img_data["description_hires"]; }

        //description += "..." + index + "/" + overlayImageList.length;
        if (img_data["type"] === "video") {
            this.video(img_data["hires"], img_data["description"], img_data["swipe"]);
        }
        else if (img_data["hires_stream"]) {
            let [hires, stream_uid]     = birdhouse_StreamURL(app_active.cam, img_data["hires_stream"], "stream_list_5", true, "OVERLAY");
            this.image(hires, description,  img_data["hires_detect"], img_data["swipe"], "overlay_image", img_data["favorite"]);
        }
        else {
            this.image(img_data["hires"], description,  img_data["hires_detect"], img_data["swipe"], "overlay_image", img_data["favorite"]);
        }
        this.currentIndex = index;

        if (index === 0)                        {
            img_data = this.get_by_index(overlayImageList.length-1);
            let img = new Image();
            img.src = img_data["hires"];
            img = null;
        }
        else if (index > 0) {
            img_data = this.get_by_index(index-1);
            let img = new Image();
            img.src = img_data["hires"];
            img = null;
        }

        if (index === this.overlayImageList.length-1) {
            img_data = this.get_by_index(0);
            let img = new Image();
            img.src = img_data["hires"];
        }
        else if (index < this.overlayImageList.length-1) {
            img_data = this.get_by_index(index+1);
            let img = new Image();
            img.src = img_data["hires"];
        }
    }

    /*
    * show or replace the overlay image by the next address via the given index
    *
    * @param (string) entry_id: identifier of the image to be loaded
    */
    show_by_id (entry_id) {
        let img_data = this.overlayImageEntries[entry_id];
        if (img_data === undefined) {
            console.error("Could not find '" + entry_id + "' in 'overlayImageEntries'.");
        }
        else {
            this.currentIndex = this.overlayImageList.indexOf(entry_id);
            this.show_by_index(this.currentIndex);
        }
    }

    /*
    * hide image or video overlay completely
    */
    hide () {
        document.getElementById("overlay").style.display = "none";
        document.getElementById("overlay_content").style.display = "none";
        document.getElementById("overlay_parent").style.display = "none";
        document.body.style.overflow = 'auto';

        if (video) {
            if (!document.getElementById("overlay_video")) {
                video.pause();
            }
            if (!document.getElementById("video")) {
                video.pause();
            }
        }
    }

    /*
    * open image in fullscreen mode
    *
    * @param (string) imageId: id of image or even better its container to be opened in fullscreen mode
    */
    fullscreen (imageId) {
        const img = document.getElementById(imageId);
        const container = document.createElement('div');

        // Style the container for fullscreen
        container.id = 'fullscreen_container';
        container.style.position = 'fixed';
        container.style.top = '0';
        container.style.left = '0';
        container.style.width = '100%';
        container.style.height = '100%';
        container.style.backgroundColor = 'black';
        container.style.display = 'flex';
        container.style.justifyContent = 'center';
        container.style.alignItems = 'center';
        container.style.zIndex = '9999';
        container.style.cursor = 'zoom-out';

        // Clone the image to avoid layout disruption
        const fullscreenImg = img.cloneNode();
        fullscreenImg.style.width = '100vw';
        fullscreenImg.style.height = '100vh';
        fullscreenImg.style.maxWidth = '100%';
        fullscreenImg.style.maxHeight = '100%';
        fullscreenImg.style.objectFit = 'contain'; // or 'cover' based on preference
        fullscreenImg.style.border = "0px";

        // Make the cloned image clickable to exit fullscreen
        fullscreenImg.onclick = () => document.exitFullscreen();
        fullscreenImg.ontouchstart = () => this.fullscreen_exit();
        container.ontouchstart = () => this.fullscreen_exit();

        container.appendChild(fullscreenImg);
        document.body.appendChild(container);

        // Check for full-screen API support
        if (container.requestFullscreen) {
            // For most modern browsers
            container.requestFullscreen().then(() => {
                container.setAttribute('id', 'fullscreen_container');
            }).catch((err) => {
                console.error(`Error entering fullscreen: ${err.message}`);
            });
        } else if (container.webkitRequestFullscreen) {
            // For iOS Safari and older webkit browsers
            container.webkitRequestFullscreen();
        }

        // Exit fullscreen clean-up
        document.addEventListener('fullscreenchange', () => {
            if (!document.fullscreenElement) {
                const container = document.getElementById('fullscreen_container');
                if (container) container.remove();
            }
        });

        document.addEventListener('webkitfullscreenchange', () => {
            if (!document.webkitFullscreenElement) {
                const container = document.getElementById('fullscreen_container');
                if (container) container.remove();
            }
        });

    }

    /*
    * close fullscreen mode (iPhone and default browser)
    */
    fullscreen_exit () {

        if (document.getElementById('fullscreen_container')) {
            setTimeout(function(){
                // Standard Fullscreen Exit
                if (document.exitFullscreen) {
                    document.exitFullscreen();
                }
                // iOS Safari fullscreen exit
                else if (document.webkitExitFullscreen) {
                    document.webkitExitFullscreen();
                }

                // Clean up fullscreen container
                const container = document.getElementById('fullscreen_container');
                if (container) container.remove();
            }, 500);
        }
    }

    /*
    * Add all event listeners -  for scaling and swiping
    *
    * @param (string) div_id - element id of image to be scaled
    * @param (string) div_id - initial scaling factor, default=1
    */
    add_touch(div_id, initScale=1) {

        this.add_touch_scale(div_id, initScale);
        this.add_touch_swipe(div_id);
    }

    /*
    * Function to handle touch events for scaling image; note: it's important to add style "touch-action: none" to the body html element
    *
    * @param (string) div_id - element id of image to be scaled
    * @param (string) div_id - initial scaling factor, default=1
    */
    add_touch_scale(div_id, initScale = 1) {
        let overlayImage = document.getElementById(div_id);
        let startScale = false;
        let initialPinchDistance = 0;

        // Store the initial position
        let initialLeft = overlayImage.offsetLeft;
        let initialTop = overlayImage.offsetTop;
        let touchStartX;
        let touchStartY;

        overlayImage.addEventListener("touchstart", (event) => {
            if (event.touches.length === 2) {
                startScale = true;
                touchStartX = event.touches[0].clientX;
                touchStartY = event.touches[0].clientY;
                initialPinchDistance = Math.hypot(
                    event.touches[1].pageX - event.touches[0].pageX,
                    event.touches[1].pageY - event.touches[0].pageY
                );

                const computedTransform = getComputedStyle(overlayImage).transform;
                if (computedTransform && computedTransform !== 'none') {
                    // Extract the scale from the transformation matrix
                    const matrixValues = computedTransform.split('(')[1].split(')')[0].split(',');
                    this.initialScale = parseFloat(matrixValues[0]);
                }
            } else {
                startScale = false;
            }
        });

        overlayImage.addEventListener("touchmove", (event) => {
            if (startScale && event.touches.length === 2) {
                let touchMoveX = event.touches[0].clientX;
                let touchMoveY = event.touches[0].clientY;
                const currentPinchDistance = Math.hypot(
                    event.touches[1].pageX - event.touches[0].pageX,
                    event.touches[1].pageY - event.touches[0].pageY
                );
                const scale = this.initialScale * (currentPinchDistance / initialPinchDistance);
                overlayImage.style.transform = `scale(${scale})`;

                let deltaX = touchMoveX - touchStartX;
                let deltaY = touchMoveY - touchStartY;
                overlayImage.style.left = deltaX + "px";
                overlayImage.style.top = deltaY + "px";
            }
        });

        // Add double-tap event listener
        let touch_time = 0;
        overlayImage.addEventListener("touchstart", (event) => {
            if (touch_time === 0) {
                // Record the time of the first tap
                touch_time = new Date().getTime();
            } else {
                // Calculate the time difference between the first and second tap
                let diff = (new Date().getTime()) - touch_time;
                if (diff < 800 && !startScale) {
                    // If the time difference is less than 800 milliseconds, it's a double tap
                    resetImage(); // Call the function to reset the image
                    touch_time = 0; // Reset touch time
                } else {
                    // If the time difference is more than 800 milliseconds, it's not a double tap
                    touch_time = 0; // Reset touch time
                }
            }
        });

        // Function to reset the image to its initial size and position
        function resetImage() {
            overlayImage.style.transform = `scale(${initScale})`;
            overlayImage.style.left = initialLeft + "px";
            overlayImage.style.top = initialTop + "px";
        }
    }

    /*
    * Function to handle touch events for swiping between images
    *
    * @param (string) div_id - element id of image to be swiped
    */
    add_touch_swipe(div_id) {
        let overlayImage = document.getElementById(div_id);
        let touchStartTime = 0;
        let initialScale = 1;
        let initialLeft = 0;
        let initialTop = 0;
        let touchStartX = 0;
        let touchStartY = 0;

        // Check if event listeners have already been added
        if (!overlayImage.hasSwipeListeners) {
            overlayImage.addEventListener("touchstart", function(event) {
                if (event.touches.length === 1) {
                    touchStartX = event.touches[0].clientX;
                    touchStartTime = Date.now(); // Record the start time
                }
                let swipeDetected = false; // Reset the flag on touchstart
            });

            overlayImage.addEventListener("touchend", (event) => {
                if (event.changedTouches.length === 1) {
                    const touchEndX = event.changedTouches[0].clientX;
                    const deltaX = touchEndX - touchStartX;
                    const touchDuration = Date.now() - touchStartTime; // Calculate touch duration

                    if (Math.abs(deltaX) > 100 && touchDuration < 1000) { // Check for 100px movement in less than 1 second
                        if (deltaX > 0) {
                            resetImage();
                            this.previous();
                        } else {
                            resetImage();
                            this.next();
                        }
                        console.debug(deltaX);
                    }
                }
            });

            // Mark the element as having event listeners
            overlayImage.hasSwipeListeners = true;
        }

        // Function to reset the image to its initial size and position
        function resetImage() {
            overlayImage.style.transform = `scale(${initialScale})`;
            overlayImage.style.left = initialLeft + "px";
            overlayImage.style.top = initialTop + "px";
        }
    }
}


let bhOverlay;
app_scripts_loaded += 1;
