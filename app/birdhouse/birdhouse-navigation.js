
var img_plus       = '<img id="streamToggle_black" src="birdhouse/img/plus.png" class="nav-img-2">';
var img_minus      = '<img id="streamToggle_black" src="birdhouse/img/minus.png" class="nav-img-2">';
var img_up_full    = '<img id="streamToggle_black" src="birdhouse/img/nav-up-full.png" class="nav-img-3">';
var img_up         = '<img id="streamToggle_black" src="birdhouse/img/nav-up.png" class="nav-img-3">';
var img_back_full  = '<img id="streamToggle_black" src="birdhouse/img/nav-back-full.png" class="nav-img-3">';
var img_back       = '<img id="streamToggle_black" src="birdhouse/img/nav-back.png" class="nav-img-3">';
var img_forth_full = '<img id="streamToggle_black" src="birdhouse/img/nav-forth-full.png" class="nav-img-3">';
var img_forth      = '<img id="streamToggle_black" src="birdhouse/img/nav-forth.png" class="nav-img-3">';

var app_navigation = `<div class="nav-container">
                <div class="nav-bar" id="nav-bar-1">
                    <div class="controls">

                        <span id="stream" onclick="toggleFloatingLowRes();" class="nav-on">
                            <img id="streamToggle" src="birdhouse/img/camera.png" class="nav-img">
                            <img id="streamToggle_black" src="birdhouse/img/camera_black.png" class="nav-img" style="display:none;">
                        </span>

                        <span id="moveUp_off" class="nav-off">`+img_up+`</span>
                        <span id="moveUp" class="nav-on" style="display:none;" onclick="window.scrollTo(0,0);">`+img_up_full+`</span>

                        <span id="moveForth_off" class="nav-off">`+img_forth+`</span>
                        <span id="moveForth" class="nav-on" style="display:none;" onclick="birdhousePrint_page('PAGE_HISTORY|-1');">`+img_forth_full+`</span>

                        <span id="moveBack_off" class="nav-off">`+img_back+`</span>
                        <span id="moveBack" class="nav-on" style="display:none;" onclick="birdhousePrint_page('PAGE_HISTORY|1');">`+img_back_full+`</span>
                    </div>
                </div>
            </div>
            <div class="nav-container-top" onclick="birdhouse_toggleNavigation();">
                <div class="nav-bar top" id="nav-bar-2">
                    `+img_plus+`
                </div>
            </div>`;

setTextById("navigation", app_navigation);

var navBar1 = undefined;
var navBar2 = undefined;

function birdhouse_loadNavigation() {
    navBar1 = document.getElementById('nav-bar-1');
    navBar2 = document.getElementById('nav-bar-2');

    navBar2.addEventListener('mouseenter', () => {
        navBar1.classList.add('expanded');
        navBar2.innerHTML = img_minus;
        });

    navBar1.addEventListener('mouseleave', () => {
        navBar1.classList.remove('expanded');
        navBar2.innerHTML = img_plus;
        });
    }

function birdhouse_toggleNavigation() {
    if (navBar1.className.indexOf("expanded") > 0) { navBar1.classList.remove('expanded'); navBar2.innerHTML = "+"; }
    else                                           { navBar1.classList.add('expanded'); navBar2.innerHTML = "-"; }
    }

birdhouse_loadNavigation();
app_scripts_loaded += 1;
