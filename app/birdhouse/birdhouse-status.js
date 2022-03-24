//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// show status functions
//--------------------------------------
/* INDEX:
*/
//--------------------------------------

function birdhouseStatus_print(data) {
    var sensors = data["DATA"]["sensors"];
    html = "<center>";
    html += "Temperature (";
    var count = 0;
    for (let sensor in sensors) {
        if sensors[sensor]["active"] {
            html += sensor;
            if (count < sensors.length) { html += "/"; }
        }
    }
    html += "): ";
    for (let sensor in sensors) {
        if sensors[sensor]["active"] {
            html += "<font id='temp"+sensor+"'>"+sensors[sensor]["values"]["temperature"]+"</font>°C ";
            if (count < sensors.length) { html += "/"; }
        }
    }
    html += "</center>";
    setTextById("frame3", html);
}

