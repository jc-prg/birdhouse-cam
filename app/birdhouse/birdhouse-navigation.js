//--------------------------------------
// jc://birdhouse/navigation/
//--------------------------------------


/*
* create a navigation module in the lower right corner to navigate back and forth,
* and to get a quick access to the video stream
*/
class BirdhouseNavigation {
    constructor(name) {
        this.name = name;

        this.img_plus       = this.image("plus.png", 2);
        this.img_minus      = this.image("minus.png", 2);
        this.img_up_full    = this.image("nav-up-full.png", 3);
        this.img_up         = this.image("nav-up.png", 3);
        this.img_back_full  = this.image("nav-back-full.png", 3);
        this.img_back       = this.image("nav-back.png", 3);
        this.img_forth_full = this.image("nav-forth-full.png", 3);
        this.img_forth      = this.image("nav-forth.png", 3);

        this.navBar1 = undefined;
        this.navBar2 = undefined;
        this.waitLoading = 5000;
    }

    /*
    * load navigation after the value defined in this.waitLoading
    */
    load () {
        setTimeout(() => {
            this.create();
        }, this.waitLoading);
    }

    /*
    * load birdhouse navigation
    */
    create () {
        let app_navigation = `<div class="nav-container">
                        <div class="nav-bar" id="nav-bar-1">
                            <div class="controls">

                                <span id="stream" onclick="toggleFloatingLowRes();" class="nav-on">
                                    <img id="streamToggle" src="birdhouse/img/camera.png" class="nav-img" title="`+lang('SHOW_STREAM')+`" alt="">
                                    <img id="streamToggle_black" src="birdhouse/img/camera_black.png" class="nav-img" title="show stream" style="display:none;" alt="">
                                </span>

                                <span id="moveUp_off" class="nav-off">`+this.img_up+`</span>
                                <span id="moveUp" class="nav-on" title="`+lang('PAGE_SCROLL_TOP')+`" style="display:none;" onclick="window.scrollTo(0,0);">`+this.img_up_full+`</span>

                                <span id="moveBack_off" class="nav-off">`+this.img_back+`</span>
                                <span id="moveBack" class="nav-on" title="`+lang('PAGE_BACK')+`" style="display:none;" onclick="birdhousePrint_page('PAGE_HISTORY|1');">`+this.img_back_full+`</span>

                                <span id="moveForth_off" class="nav-off">`+this.img_forth+`</span>
                                <span id="moveForth" class="nav-on" title="`+lang('PAGE_FORWARD')+`" style="display:none;" onclick="birdhousePrint_page('PAGE_HISTORY|-1');">`+this.img_forth_full+`</span>
                            </div>
                        </div>
                    </div>
                    <div class="nav-container-top" onclick="birdhouse_toggleNavigation();">
                        <div class="nav-bar top" id="nav-bar-2">
                            `+this.img_plus+`
                        </div>
                    </div>`;

        setTextById("navigation", app_navigation);

        this.navBar2 = document.getElementById('nav-bar-2');
        this.navBar2.addEventListener('mouseenter', () => {
            navBar1.classList.add('expanded');
            navBar2.innerHTML = this.img_minus;
        });

        this.navBar1 = document.getElementById('nav-bar-1');
        this.navBar1.addEventListener('mouseleave', () => {
            navBar1.classList.remove('expanded');
            navBar2.innerHTML = this.img_plus;
        });

    }

    /*
    * show or hide navigation
    */
    toggle () {
        if (navBar1.className.indexOf("expanded") > 0) {
            this.navBar1.classList.remove('expanded');
            this.navBar2.innerHTML = this.img_plus;
        }
        else {
            this.navBar1.classList.add('expanded');
            this.navBar2.innerHTML = this.img_minus;
        }
    }

    /*
    * create navigation images
    *
    * @param (string) filename: complete filename without directory; file has to be stored in folder /app/birdhouse/img/
    * @param (integer) img_class: number of class, value can be 2 or 3
    */
    image (filename, img_class) {
        return '<img id="nav-image-'+filename+'" src="birdhouse/img/'+filename+'" class="nav-img-'+img_class+'" alt="">';
    }

}


let bhNavigation;
app_scripts_loaded += 1;
