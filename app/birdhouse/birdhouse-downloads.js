
function collect4download_activate() {
    app_collect4download = true;
    birdhouseReloadView();
}

function collect4download_deactivate() {
    app_collect4download = false;
    birdhouseReloadView();
}

function collect4download_exists(entry) {
    if (app_collect_list.includes(entry)) { return true; }
    else                                  { return false; }
}

/*
* add or remove entries in the download list
*
* @params (string) entry - entry in the format YYYYMMDD_HHMMSS
* @params (string) image_id - id of the image element, format 'c_' + image_id; image will be replaced depending on status
*/
function collect4download_toggle(entry, image_id) {
    var image = "";
    var img_dir     = "birdhouse/img/";

    if (collect4download_exists(entry)) {
        var index = app_collect_list.indexOf(entry);
        if (index != -1) { app_collect_list.splice(index, 1); }
        image = img_dir + "checkbox-white0.png";
        }
    else {
        app_collect_list.push(entry);
        image = img_dir + "checkbox-white1.png";
        }
    img_object = document.getElementById("cb_"+image_id);
    img_object.src = image;
}

function collect4download_image(entry) {
    var img_dir     = "birdhouse/img/";
    if (collect4download_exists(entry)) { return img_dir + "checkbox-white1.png"; }
    else                                { return img_dir + "checkbox-white0.png"; }
}