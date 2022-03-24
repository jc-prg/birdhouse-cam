//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// show status functions
//--------------------------------------
/* INDEX:
*/
//--------------------------------------

function birdhouseStatus_print(data) {
console.log("!!!!");
    var sensors = data["DATA"]["sensors"];
    html = "<center>";
    html += "Temperature (";
    var count = 0;
    var keys = Object.keys(sensors);
    for (let sensor in sensors) {
        if (sensors[sensor]["active"]) {
            html += sensor;
            count += 1;
            if (count < keys.length) { html += " / "; }
        }
    }
    html += "): ";
    var count = 0;
    for (let sensor in sensors) {
        if (sensors[sensor]["active"]) {
            html += "<font id='temp"+sensor+"'>"+sensors[sensor]["values"]["temperature"]+"</font>°C ";
            count += 1;
            if (count < keys.length) { html += " / "; }
        }
    }
    html += "</center>";
    setTextById("frame3", html);
}

