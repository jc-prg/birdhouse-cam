
var html = "";
var port_html = 8000;
var port_video = 8007;


function checkAvailability(key, apiURL) {
    // Make the GET request
    Object.entries(birdhouses).forEach(([key,value]) => {

        var port_http = value["http"];
        var port_api  = value["api"];
        var server    = '['  + value["ipv6"] + ']';

        if (value["server"] != "") {
            server = value["server"];
            }

        var timestamp = Date.now() + "";
        var apiUrl    = 'http://' + server + ':' + port_api + '/api/status/';
        var streamUrl = 'http://' + server + ':' + port_api + '/lowres/stream.mjpg?cam1?' + key + '?bh-' + key + '-' + timestamp;
        if (document.getElementById("bh-image-id-" + key)) {
            var image_id = document.getElementById("bh-image-id-" + key).innerHTML;
            }
        else {
            var image_id = "";
        }

        fetch(apiUrl)
          .then(response => {
            // Check if request was successful
            if (!response.ok) {
              var error_msg = "This birdhouse is currently not available.";
              document.getElementById("bh-" + key).style.display = "none";
              document.getElementById("bh-error-" + key).style.display = "block";
              error_msg = error_msg.replaceAll(":", ": ");

              document.getElementById("bh-error-" + key).innerHTML = "&nbsp;<br/>&nbsp;<br/>" + error_msg;
              document.getElementById("bh-image-id-" + key).innerHTML = "update";

              throw new Error(error_msg);
            }
            // Parse JSON response
            return response.json();
          })
          .then(data => {
            // Data is now a JavaScript object
            console.log(data);
            document.getElementById("bh-" + key).style.display = "block";
            document.getElementById("bh-error-" + key).style.display = "none";
            document.getElementById("bh-label-" + key).innerHTML = data["SETTINGS"]["title"];

            if (image_id == "update") {
                var html = '<img src="http://' + server + ':' + port_api +  '/lowres/stream.mjpg?cam1?' + key + '?bh-' + key + '-' + timestamp + '" class="image" id="bh-' + key + '" style="display:block;"/>';
                document.getElementById("bh-image-" + key).innerHTML = html;
                document.getElementById("bh-image-id-" + key).innerHTML = timestamp;
            }
            // You can access properties of the data object as needed
          })
          .catch(error => {
              var error_msg = 'This birdhouse is currently not available. <br/>&nbsp;<br/><small>' + error + '</small>';
              document.getElementById("bh-" + key).style.display = "none";
              document.getElementById("bh-error-" + key).style.display = "block";
              error_msg = error_msg.replaceAll(":", ": ");

              document.getElementById("bh-error-" + key).innerHTML = "&nbsp;<br/>&nbsp;<br/>" + error_msg;
              document.getElementById("bh-image-id-" + key).innerHTML = "update";

              console.error(error_msg);
          });
      });
}

var interval = 0;

Object.entries(birdhouses).forEach(([key,value]) => {
    html += '<div class="image_container"><center>';

    var port_http = value["http"];
    var port_api  = value["api"];
    var server    = '['  + value["ipv6"] + ']';

    if (value["server"] != "") {
        server = value["server"];
        }

    html += '<a href="http://' + server + ':' + port_http + '/"><b><label id="bh-label-' + key + '">Birdhouse ' + key + '</label></b><br/>&nbsp;<br/>';
    html += '<div id="bh-image-id-'+ key +'" style="display:none;">' + timestamp + "</div>";
    html += '<div id="bh-image-'+ key +'">';
    html += '<img src="http://' + server + ':' + port_api +  '/lowres/stream.mjpg?cam1?' + key + '?bh-' + key + '-' + timestamp + '" class="image" id="bh-' + key + '" style="display:block;"/>';
    html += "</div></a>";
    html += '<div class="image_error" id="bh-error-' + key + '" style="display:none;">Test</div>';

    html += '<br/>&nbsp;<br/>&nbsp;</center></div>';
});

checkAvailability();
interval = setInterval(function() { checkAvailability(); }, 5000);

document.getElementById('birdhouses').innerHTML = html;