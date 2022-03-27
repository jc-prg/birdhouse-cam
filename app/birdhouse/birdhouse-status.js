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
    html += "Temperature - ";
    var count = 0;
    var keys = Object.keys(sensors);
    for (let sensor in sensors) {
        if (sensors[sensor]["active"]) {
            html += sensors[sensor]["name"] + ": ";
            html += "<font id='temp"+sensor+"'>"+sensors[sensor]["values"]["temperature"]+"</font>";
            html += sensors[sensor]["units"]["temperature"];
            count += 1;
            if (count < keys.length) { html += " / "; }
        }
    }
    html += "</font></i></center>";
    setTextById(app_frame_info, html);
}

