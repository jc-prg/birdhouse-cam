//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// birdhouse views - floating video overlay
//--------------------------------------


var floatingHTML = `<div class="floating-header" id="dragHeader"><!--ACTIVE_CAM-->
                      <span class="close-btn" id="closeBtn">✖</span>
                    </div>
                    <div class="floating-image-container" id="lowres_floating_error" style="display:none;">
                        <div class="thumbnail error" id="lowres_floating_error_2" style="width:100%;height:100%;display:flex;justify-align:center;align-items:center;text-align:center;"><!--CONNECTION_ERROR--></div>
                    </div>
                    <div class="floating-image-container" id="lowres_floating" style="cursor:zoom-in;" onclick="birdhousePrint_page('INDEX');">
                      <img id="floatingImage" src="<!--STREAM_URL-->" alt="Floating Image">
                    </div>`;

var floatingWindow      = "";
var floatingHeader      = "";
var closeBtn            = "";
var floatingImage       = "";
var initialized         = false;
var offsetX = 0, offsetY = 0, isDragging = false;
var app_floating_lowres = false;
var app_floating_cam    = "";
var app_floating_stream = "";

/*
* start load floating image with given active cam and streaming URL
* (the content of this function is mainly AI generated)
*
* @param (string) active_cam: id of active cam (displayed in the header)
* @param (string) stream_url: complete streaming URL to be displayed
*/
function startFloatingLowres(active_cam) {

	var cameras       = app_data["SETTINGS"]["devices"]["cameras"];
    var stream_url = RESTurl + cameras[app_active_cam]["video"]["stream_lowres"];
    var timestamp = new Date().getTime();

    app_floating_cam    = active_cam;
    app_floating_stream = stream_url;  // url creation incl. stream id ?!
    stream_url         += "&floating_" + timestamp;

    if (floatingImage != "") {
        floatingImage.src = "";
        floatingImage.removeAttribute('src');
        }

    floatingWindow  = document.getElementById('floatingWindow');
    var content     = floatingHTML;
    content         = content.replace("<!--ACTIVE_CAM-->", active_cam);
    content         = content.replace("<!--STREAM_URL-->", stream_url);
    content         = content.replace("<!--CONNECTION_ERROR-->", lang("CONNECTION_ERROR"));
    floatingWindow.innerHTML = content;
    floatingWindow.style.display = "flex";

    floatingHeader      = document.getElementById('dragHeader');
    closeBtn            = document.getElementById('closeBtn');
    floatingImage       = document.getElementById('floatingImage');
    floatingImageError  = document.getElementById('lowres_floating_error');

    floatingImage.addEventListener('load', () => {
        if (initialized) return; // only run once

        const imgWidth = floatingImage.naturalWidth;
        const imgHeight = floatingImage.naturalHeight;
        console.log(`floatingImage dimensions: ${imgWidth}x${imgHeight}`);

        const screenW = window.innerWidth;
        const screenH = window.innerHeight;

        const maxW = screenW * 0.35;
        const maxH = screenH * 0.35;

        const widthRatio = maxW / imgWidth;
        const heightRatio = maxH / imgHeight;
        const scale = Math.min(widthRatio, heightRatio, 1);

        const newWidth = Math.floor(imgWidth * scale);
        const newHeight = Math.floor(imgHeight * scale);

        floatingImage.style.width = newWidth + 'px';
        floatingImage.style.height = newHeight + 'px';

        floatingImageError.style.width = newWidth + 'px';
        floatingImageError.style.height = newHeight + 'px';

        floatingWindow.style.display = "flex";
        floatingWindow.style.width = newWidth + 'px';
        floatingWindow.style.height = (newHeight + floatingHeader.offsetHeight) + 'px';

        floatingWindow.style.left = (screenW - newWidth - 20) + 'px';
        floatingWindow.style.top = (screenH - newHeight - floatingHeader.offsetHeight - 20) + 'px';
        floatingWindow.style.right = 'auto';
        floatingWindow.style.bottom = 'auto';

        initialized = true; // prevent resetting size/position on every image load
        });

    floatingHeader.addEventListener('mousedown', floatingStartDrag);
    floatingHeader.addEventListener('touchstart', floatingStartDrag);

    app_floating_lowres = true;

    // Close button
    closeBtn.addEventListener('click', () => {
        floatingWindow.style.display = 'none';
        app_floating_lowres = false;
        });
    }

/*
* stop floating window from outside (not using the cross)
*/
function stopFloatingLowres() {
    floatingWindow  = document.getElementById('floatingWindow');
    floatingImage   = document.getElementById('floatingImage');
    closeBtn        = document.getElementById('closeBtn');
    closeBtn.click();

    app_floating_lowres      = false;
    floatingImage.src        = "";
    floatingImage.removeAttribute('src');
    floatingWindow.innerHTML = "";
    //floatingWindow           = "";
    floatingImage            = "";
    initialized              = false;

    window.stop();
}

/*
* reposition the floating window to its initial position, e.g.m when resizing the browser window
*/
function repositionFloatingLowres() {
    floatingWindow  = document.getElementById('floatingWindow');
    floatingImage   = document.getElementById('floatingImage');

    if (!floatingWindow) { return; }
    if (!floatingImage)  { return; }

    const imgWidth = floatingImage.naturalWidth;
    const imgHeight = floatingImage.naturalHeight;

    const screenW = window.innerWidth;
    const screenH = window.innerHeight;

    const maxW = screenW * 0.35;
    const maxH = screenH * 0.35;

    const widthRatio = maxW / imgWidth;
    const heightRatio = maxH / imgHeight;
    const scale = Math.min(widthRatio, heightRatio, 1);

    const newWidth = Math.floor(imgWidth * scale);
    const newHeight = Math.floor(imgHeight * scale);

    floatingImage.style.width = newWidth + 'px';
    floatingImage.style.height = newHeight + 'px';

    floatingImageError.style.width = newWidth + 'px';
    floatingImageError.style.height = newHeight + 'px';

    floatingWindow.style.display = "flex";
    floatingWindow.style.width = newWidth + 'px';
    floatingWindow.style.height = (newHeight + floatingHeader.offsetHeight) + 'px';

    floatingWindow.style.left = (screenW - newWidth - 20) + 'px';
    floatingWindow.style.top = (screenH - newHeight - floatingHeader.offsetHeight - 20) + 'px';
    floatingWindow.style.right = 'auto';
    floatingWindow.style.bottom = 'auto';
}

/*
* start dragging the floating window
* (this function is completely AI generated)
*/
function floatingStartDrag(e) {
    isDragging = true;
    const rect = floatingWindow.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    offsetX = clientX - rect.left;
    offsetY = clientY - rect.top;
    document.addEventListener('mousemove', floatingDrag);
    document.addEventListener('touchmove', floatingDrag, { passive: false });
    document.addEventListener('mouseup', floatingStopDrag);
    document.addEventListener('touchend', floatingStopDrag);
    }

/*
* dragg the floating window
* (this function is completely AI generated)
*/
function floatingDrag(e) {
    if (!isDragging) return;
    e.preventDefault();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    let left = clientX - offsetX;
    let top = clientY - offsetY;

    const winW = window.innerWidth;
    const winH = window.innerHeight;
    const fw = floatingWindow.offsetWidth;
    const fh = floatingWindow.offsetHeight;

    left = Math.max(0, Math.min(winW - fw, left));
    top = Math.max(0, Math.min(winH - fh, top));

    floatingWindow.style.left = left + 'px';
    floatingWindow.style.top = top + 'px';
    floatingWindow.style.right = 'auto';
    floatingWindow.style.bottom = 'auto';
    }

/*
* stop dragging the floating window
* (this function is completely AI generated)
*/
function floatingStopDrag() {
    isDragging = false;
    document.removeEventListener('mousemove', floatingDrag);
    document.removeEventListener('touchmove', floatingDrag);
    document.removeEventListener('mouseup', floatingStopDrag);
    document.removeEventListener('touchend', floatingStopDrag);
    }


app_scripts_loaded += 1;
