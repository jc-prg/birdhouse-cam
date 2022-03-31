//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// show status functions
//--------------------------------------
/* INDEX:
function birdhouseStatus_print(data)
*/
//--------------------------------------

function birdhouseStatus_print(data) {
    console.debug("Update Status ...");
    var sensors = data["DATA"]["devices"]["sensors"];
    html = "<center><i><font color='gray'>";
    html_entry = "";
    var count = 0;
    var keys = Object.keys(sensors);
    for (let sensor in sensors) {
        if (sensors[sensor]["active"]) {
            html_entry += sensors[sensor]["name"] + ": ";
            html_entry += "<font id='temp"+sensor+"'>"+sensors[sensor]["values"]["temperature"]+"</font>";
            html_entry += sensors[sensor]["units"]["temperature"];
            count += 1;
            if (count < keys.length) { html_entry += " / "; }
        }
    }
    if (count > 0 ) {
        document.getElementById(app_frame_info).style.display = "block";
        html_entry = "Temperature - " + html_entry;
    }
    else {
        document.getElementById(app_frame_info).style.display = "none";
    }
    html += html_entry;
    html += "</font></i></center>";
    setTextById(app_frame_info, html);
}

