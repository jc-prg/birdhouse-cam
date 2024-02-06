//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// birdhouse object detection view
//--------------------------------------

/**
* create view for all detected objects with thumbnail and a list of all dates where the object was detected
*
* @param (string) title: title of this view
* @param (dict) data: data returned form server API for this view
*/
function birdhouse_OBJECTS(title, data) {

    var html = "";
    var detections     = data["DATA"]["data"]["entries"];
	var server_status  = app_data["STATUS"]["server"];

    if (!detections && server_status["view_archive_loading"] != "done") {
        var progress_info = "<i><div id='loading_status_object'></div></i>";
        appMsg.alert(lang("DATA_LOADING_TRY_AGAIN") + "<br/>" + progress_info);
        return false;
        }

	var tab = new birdhouse_table();
	tab.style_cells["vertical-align"] = "top";
	tab.style_cells["padding"] = "3px";

    // list of all available detections
    var all_labels = "<div id='label_all' class='detection_label_function' onclick='birdhouse_OBJECTS_open();birdhouse_labels_highlight(\"all\",\"label_key_list\");'>&nbsp;&nbsp;"+lang("ALL_LABELS")+"&nbsp;&nbsp;</div>";
    var all_labels_list = Object.keys(detections);
    all_labels_list.sort();

    for (var i=0;i<all_labels_list.length;i++) {
        var key = all_labels_list[i];
        var onclick = "birdhouse_OBJECTS_open(label=\""+key+"\");birdhouse_labels_highlight(\""+key+"\",\"label_key_list\");";
        all_labels += "<div id='label_"+key+"' class='detection_label' onclick='"+onclick+"'>&nbsp;&nbsp;" + bird_lang(key) + "&nbsp;&nbsp;</div>";
        }
    all_labels += "<div style='width:100%;height:25px;float:left;'></div>";
    html += birdhouse_OtherGroup( "list_of_labels", lang("ALL_LABELS"), all_labels, true);
    html += "<div id='label_key_list' style='display:none;'>" + all_labels_list.join(",") + "</div>";

    if (all_labels_list.length == 0 && server_status["view_archive_loading"] == "done")  {
        html += "<center>&nbsp;<br/>"+lang("NO_ENTRIES")+"<br/>&nbsp;</center>";
        }

    // info per detected object type / label
    for (var i=0;i<all_labels_list.length;i++) {

        var key            = all_labels_list[i];
        var value          = detections[key];
        value["type"]      = "label";

        var default_dates     = "";
        var favorite_label    = "";
        var entry_information = "";

        if (value["detections"]["favorite"] > 0 ) {
            var onclick = "birdhousePrint_load(\"FAVORITES\",\""+app_active_cam+"\", \"all-dates\", \""+key+"\");";
            favorite_label += "<div class='other_label' onclick='"+onclick+"'>&nbsp;&nbsp;" + lang("FAVORITES") + "&nbsp;(" + value["detections"]["favorite"] + ")&nbsp;&nbsp;</div>";
            }
        else  { value["detections"]["favorite"] = 0; }

        var day_count = 0;
        Object.entries(value["detections"]["default_dates"]).forEach(([camera, date_list])=>{
            date_list.sort();
            for (var k=0;k<date_list.length;k++) {
                var stamp      = date_list[k];
                var date       = stamp.substring(6,8) + "." + stamp.substring(4,6) + "." + stamp.substring(2,4);
                var onclick    = "birdhousePrint_load(view=\"TODAY\", camera=\""+camera+"\", date=\""+stamp+"\", label=\""+key+"\");";
                default_dates += "<div class='other_label' onclick='"+onclick+"'>&nbsp;" + camera + ": " + date + "&nbsp;</div>";
                day_count += 1;

                if (date_list.length > 10 && k == 8) {
                    onclick = "elementHidden(\"label_expand_click_"+key+"\");elementVisible(\"label_expand_"+key+"\");"
                    default_dates += "<div id='label_expand_click_"+key+"' class='other_label' onclick='"+onclick+"'>&nbsp;&nbsp;" + lang("FURTHER_DAYS", [date_list.length - 9]) + "&nbsp;...&nbsp;&nbsp;</div>";
                    default_dates += "<div id='label_expand_"+key+"' style='display:none;'>";
                    }
                else if (date_list.length > 10 && k + 1 == date_list.length) {
                    default_dates += "</div>";
                    }

                }
            });

        var image_count = (value["detections"]["favorite"] + value["detections"]["default"]);
        entry_information += "<b>" + image_count + " " + lang("IMAGES") + "</b> (" + day_count + ")<hr/>";
        entry_information += favorite_label + default_dates;

        var html_entry = tab.start();
        html_entry    += tab.row(birdhouse_Image(bird_lang(key), key, value), entry_information);
        html_entry    += tab.end();

        var bird_key = bird_lang(key);
        if (bird_key != key) { bird_key = "<b>" + bird_key + "</b>"; }
        html += birdhouse_OtherGroup( "label_"+key, bird_key, html_entry, true);
        }

	birdhouse_frameHeader(title);
	setTextById(app_frame_content, html);
    }

/*
* open all or selected label group in birds / objects view
*
* @param (string) label: object class name / label of the group(s) to be opened
*/
function birdhouse_OBJECTS_open(label="all") {

    var all_labels = document.getElementById("label_key_list").innerHTML.split(",");
    for (var i=0;i<all_labels.length;i++) {
        if (label == "all" )  { birdhouse_groupToggle("label_"+all_labels[i], true); }
        else                  { birdhouse_groupToggle("label_"+all_labels[i], false); }
    }
    if (label != "all")       { birdhouse_groupToggle("label_"+label, true); }
}

/*
* highlight selected labels (show glow)
*
* @param (string) key: element id of the label to be highlighted
* @param (string) list: element id of div that contains all available labels
*/
function birdhouse_labels_highlight(key, list="") {
    if (key == "") { key = "all"; }
    if (document.getElementById("label_"+key)) {
        document.getElementById("label_"+key).classList.add("glow");
    }
    if (list != "" && document.getElementById(list)) {
        label_keys = document.getElementById(list).innerHTML.split(",");
        if (key != "all") { label_keys.push("all"); }
        for (var i=0;i<label_keys.length;i++) {
            var this_key = label_keys[i];
            if (document.getElementById("label_"+this_key) && this_key != key) {
                document.getElementById("label_"+this_key).classList.remove("glow");
            }
        }
    }
}

/*
* translate bird class to selected language if available
*
* @param (string) bird_class: class name of detected bird (or object)
* @returns (string): translation if available, otherwise bird class
*/
function bird_lang(bird_class) {
    var key = bird_class.toUpperCase();
    if (!app_bird_names)            { return bird_class; }
    else if (!app_bird_names[key])  { return bird_class; }
    else {
        if (app_bird_names[key][LANG])      { return app_bird_names[key][LANG]; }
        else if (app_bird_names[key]["EN"]) { return app_bird_names[key]["EN"]; }
        else if (app_bird_names[key]["DE"]) { return app_bird_names[key]["DE"]; }
        else                                { return bird_class; }
    }
}


app_scripts_loaded += 1;
