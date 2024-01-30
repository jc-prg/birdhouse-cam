//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// functions to collect images to be downloaded
//--------------------------------------

/*
* activate collecting images for download
*/
function collect4download_activate() {
    app_collect4download = true;
    birdhouseReloadView();
}

/*
* deactivate collecting images for download
*/
function collect4download_deactivate() {
    app_collect4download = false;
    birdhouseReloadView();
}

/*
* check if image has been collected already
*
* @params (string) entry - entry in the format YYYYMMDD_HHMMSS
* @returns (string) - true if file already has been collected
*/
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
    if (collect4download_exists(entry)) {
        var index = app_collect_list.indexOf(entry);
        if (index != -1) { app_collect_list.splice(index, 1); }
        }
    else {
        app_collect_list.push(entry);
        }
    img_object = document.getElementById("cb_"+image_id);
    img_object.src = collect4download_image(entry);
}

/*
* get image path depending if image has been marked or not
*
* @params (string) entry - entry in the format YYYYMMDD_HHMMSS
* @returns (string) - path of checkbox image (with or without check mark)
*/
function collect4download_image(entry) {
    var img_dir     = "birdhouse/img/";
    if (collect4download_exists(entry)) { return img_dir + "checkbox-white1b.png"; }
    else                                { return img_dir + "checkbox-white0.png"; }
}

/*
* request download for list of id's
*/
function archivDownload_requestList() {
    if (app_collect_list.length == 0) {
        appMsg.alert(lang("DOWNLOAD_NO_ENTRIES"));
        return;
        }
    commands = ["archive-download-list"];
    birdhouse_apiRequest('POST', commands, app_collect_list, archivDownload_requestDayWait, "", "collect4download_request");
}

/*
* request download for data and specific camera
*/
function archivDownload_requestDay(date_stamp, camera) {
    commands = ["archive-download-day", date_stamp, camera];
	birdhouse_apiRequest('POST', commands, '', archivDownload_requestDayWait,'','birdhouse_archiveDayDownload(\"'+date_stamp+'\")');
}

/*
* Open dialog to wait for a download link
*/
function archivDownload_requestDayWait(data) {
    if (data["date"]) { appMsg.alert(lang("WAITING_FOR_DOWNLOAD") + ":<br/><div id='archive_download_link_"+data["date"]+"'></div>"); }
    else { appMsg.alert(lang("WAITING_FOR_DOWNLOAD") + ":<br/><div id='archive_download_link'></div>"); }
}


