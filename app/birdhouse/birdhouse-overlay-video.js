//--------------------------------------
// jc://birdhouse/floating-lowres/
//--------------------------------------


/*
* create a "floating lowres" that can be activated in each part of the app using the BirdhouseNavigation
*/
class BirdhouseFloatingVideo {
    constructor(name) {
        this.name = name;

        this.floatingHTML = `<div class="floating-header" id="dragHeader"><!--ACTIVE_CAM-->
                      <span class="close-btn" id="closeBtn">✖</span>
                    </div>
                    <div class="floating-image-container" id="lowres_floating_error" style="display:none;">
                        <div class="thumbnail error" id="lowres_floating_error_2" style="width:100%;height:100%;display:flex;justify-align:center;align-items:center;text-align:center;"><!--CONNECTION_ERROR--></div>
                    </div>
                    <div class="floating-image-container" id="lowres_floating" style="cursor:zoom-in;" onclick="birdhousePrint_page('INDEX');">
                      <img id="floatingImage" src="<!--STREAM_URL-->" alt="Floating Image">
                    </div>`;
        this.floatingWindow      = "";
        this.floatingHeader      = "";
        this.floatingImage       = "";
        this.floatingImageError  = "";

        this.initialized         = false;
        this.closeBtn            = "";
        this.offsetX             = 0;
        this.offsetY             = 0;
        this.isDragging          = false;
        this.initialized         = false;

        this.app_floating_lowres = false;
        this.app_floating_cam    = "";
        this.app_floating_stream = "";
        this.app_floating_bottom = 100;
        this.app_floating_left   = 20;

        this.drag = this.drag.bind(this);
        this.dragStart = this.dragStart.bind(this);
        this.dragStop = this.dragStop.bind(this);
    }

    /*
    * start load floating image with given active cam and streaming URL
    * (the content of this function is mainly AI generated)
    *
    * @param (string) active_cam: id of active cam (displayed in the header)
    * @param (string) stream_url: complete streaming URL to be displayed
    */
    start (active_cam="") {

        if (this.app_floating_lowres) { this.stop(); }
        if (active_cam === "")        { active_cam = app_active.cam; }

        const timestamp = new Date().getTime();
        const cameras = app_data["SETTINGS"]["devices"]["cameras"];
        let stream_url = RESTurl + cameras[active_cam]["video"]["stream_lowres"];

        this.app_floating_cam    = active_cam;
        this.app_floating_stream = stream_url;  // url creation incl. stream id ?!
        stream_url += "&floating_" + timestamp;

        if (this.floatingImage !== "") {
            this.floatingImage.src = "";
            this.floatingImage.removeAttribute('src');
        }

        this.floatingWindow  = document.getElementById('floatingWindow');
        let content = this.floatingHTML;
        content = content.replace("<!--ACTIVE_CAM-->", active_cam);
        content = content.replace("<!--STREAM_URL-->", stream_url);
        content = content.replace("<!--CONNECTION_ERROR-->", lang("CONNECTION_ERROR"));
        this.floatingWindow.innerHTML = content;
        this.floatingWindow.style.display = "flex";

        this.floatingHeader      = document.getElementById('dragHeader');
        this.closeBtn            = document.getElementById('closeBtn');
        this.floatingImage       = document.getElementById('floatingImage');
        this.floatingImageError  = document.getElementById('lowres_floating_error');

        this.floatingImage.addEventListener('load', () => {
            if (this.initialized) return; // only run once

            const imgWidth = this.floatingImage.naturalWidth;
            const imgHeight = this.floatingImage.naturalHeight;
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

            this.floatingImage.style.width = newWidth + 'px';
            this.floatingImage.style.height = newHeight + 'px';

            this.floatingImageError.style.width = newWidth + 'px';
            this.floatingImageError.style.height = newHeight + 'px';

            this.floatingWindow.style.display = "flex";
            this.floatingWindow.style.width = newWidth + 'px';
            this.floatingWindow.style.height = (newHeight + this.floatingHeader.offsetHeight) + 'px';

            this.floatingWindow.style.left = (screenW - newWidth - this.app_floating_left) + 'px';
            this.floatingWindow.style.top = (screenH - newHeight - this.floatingHeader.offsetHeight - this.app_floating_bottom) + 'px';
            this.floatingWindow.style.right = 'auto';
            this.floatingWindow.style.bottom = 'auto';

            this.initialized = true; // prevent resetting size/position on every image load
        });

        this.floatingHeader.addEventListener('mousedown', this.dragStart);
        this.floatingHeader.addEventListener('touchstart', this.dragStart);

        this.app_floating_lowres = true;

        // Close button
        this.closeBtn.addEventListener('click', () => {
            this.floatingWindow.style.display = 'none';
            this.app_floating_lowres = false;
        });
    }

    /*
    * stop floating window from outside (not using the cross)
    */
    stop () {
        this.floatingWindow  = document.getElementById('floatingWindow');
        this.floatingImage   = document.getElementById('floatingImage');
        this.closeBtn        = document.getElementById('closeBtn');
        this.closeBtn.click();

        this.app_floating_lowres      = false;
        this.floatingImage.src        = "";
        this.floatingImage.removeAttribute('src');
        this.floatingWindow.innerHTML = "";
        //floatingWindow           = "";
        this.floatingImage            = "";
        this.initialized              = false;

        window.stop();
    }

    /*
    * show / hide floating lowres
    */
    toggle () {
        if (this.app_floating_lowres) { this.stop(); } else { this.start(); }
    }

    /*
    * reposition the floating window to its initial position, e.g.m when resizing the browser window
    */
    reposition () {
        this.floatingWindow  = document.getElementById('this.floatingWindow');
        this.floatingImage   = document.getElementById('floatingImage');

        if (!this.floatingWindow) { return; }
        if (!this.floatingImage)  { return; }

        const imgWidth = this.floatingImage.naturalWidth;
        const imgHeight = this.floatingImage.naturalHeight;

        const screenW = window.innerWidth;
        const screenH = window.innerHeight;

        const maxW = screenW * 0.35;
        const maxH = screenH * 0.35;

        const widthRatio = maxW / imgWidth;
        const heightRatio = maxH / imgHeight;
        const scale = Math.min(widthRatio, heightRatio, 1);

        const newWidth = Math.floor(imgWidth * scale);
        const newHeight = Math.floor(imgHeight * scale);

        this.floatingImage.style.width = newWidth + 'px';
        this.floatingImage.style.height = newHeight + 'px';

        this.floatingImageError.style.width = newWidth + 'px';
        this.floatingImageError.style.height = newHeight + 'px';

        this.floatingWindow.style.display = "flex";
        this.floatingWindow.style.width = newWidth + 'px';
        this.floatingWindow.style.height = (newHeight + this.floatingHeader.offsetHeight) + 'px';

        this.floatingWindow.style.left = (screenW - newWidth - this.app_floating_left) + 'px';
        this.floatingWindow.style.top = (screenH - newHeight - this.floatingHeader.offsetHeight - this.app_floating_bottom) + 'px';
        this.floatingWindow.style.right = 'auto';
        this.floatingWindow.style.bottom = 'auto';
    }

    /*
    * start dragging the floating window
    * (this function is completely AI generated)
    */
    dragStart (e) {
        this.isDragging = true;
        const rect = this.floatingWindow.getBoundingClientRect();
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const clientY = e.touches ? e.touches[0].clientY : e.clientY;
        this.offsetX = clientX - rect.left;
        this.offsetY = clientY - rect.top;
        document.addEventListener('mousemove', this.drag);
        document.addEventListener('touchmove', this.drag, { passive: false });
        document.addEventListener('mouseup', this.dragStop);
        document.addEventListener('touchend', this.dragStop);
    }

    /*
    * drag the floating window
    * (this function is completely AI generated)
    */
    drag (e) {
        if (!this.isDragging) return;
        e.preventDefault();
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const clientY = e.touches ? e.touches[0].clientY : e.clientY;
        let left = clientX - this.offsetX;
        let top = clientY - this.offsetY;

        const winW = window.innerWidth;
        const winH = window.innerHeight;
        const fw = this.floatingWindow.offsetWidth;
        const fh = this.floatingWindow.offsetHeight;

        left = Math.max(0, Math.min(winW - fw, left));
        top = Math.max(0, Math.min(winH - fh, top));

        this.floatingWindow.style.left = left + 'px';
        this.floatingWindow.style.top = top + 'px';
        this.floatingWindow.style.right = 'auto';
        this.floatingWindow.style.bottom = 'auto';
    }

    /*
    * stop dragging the floating window
    * (this function is completely AI generated)
    */
    dragStop () {
        this.isDragging = false;
        document.removeEventListener('mousemove', this.drag);
        document.removeEventListener('touchmove', this.drag);
        document.removeEventListener('mouseup', this.dragStop);
        document.removeEventListener('touchend', this.dragStop);
    }
}


let bhFloating;
app_scripts_loaded += 1;
