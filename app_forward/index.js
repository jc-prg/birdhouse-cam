
var html = "";
var port_html = 8000;
var port_video = 8007;

Object.entries(birdhouses).forEach(([key,value]) => {
    html += '<div class="image_container"><center>';

    html += '<a href="http://[' + value["ipv6"] + ']:' + value["http"] + '"><b><label id="bh-label-' + key + '">Birdhouse ' + key + '</label></b><br/>&nbsp;<br/>';
    html += '<img src="http://[' + value["ipv6"] + ']:' + value["api"] + '/lowres/stream.mjpg?cam1?' + key + '?bh-' + key + '-' + timestamp + '" class="image" id="bh-' + key + '" style="display:block;"/>';
    html += "</a>";
    html += '<div class="image_error" id="bh-error-' + key + '" style="display:none;">Test</div>';

    html += '<br/>&nbsp;<br/>&nbsp;</center></div>';

    // API endpoint
    const apiUrl = 'http://[' + value["ipv6"] + ']:' + value["api"] + '/api/status/';
    var birdhouseStatus = undefined;

    // Make the GET request
    fetch(apiUrl)
      .then(response => {
        // Check if request was successful
        if (!response.ok) {
          var error_msg = "This birdhouse is currently not available.";
          document.getElementById("bh-" + key).style.display = "none";
          document.getElementById("bh-error-" + key).style.display = "block";
          error_msg = error_msg.replaceAll(":", ": ");
          document.getElementById("bh-error-" + key).innerHTML = "&nbsp;<br/>&nbsp;<br/>" + error_msg;

          throw new Error(error_msg);
        }
        // Parse JSON response
        return response.json();
      })
      .then(data => {
        // Data is now a JavaScript object
        console.log(data);
        document.getElementById("bh-label-" + key).innerHTML = data["SETTINGS"]["title"];
        // You can access properties of the data object as needed
      })
      .catch(error => {
          var error_msg = 'This birdhouse is currently not available: ' + error;
          document.getElementById("bh-" + key).style.display = "none";
          document.getElementById("bh-error-" + key).style.display = "block";
          error_msg = error_msg.replaceAll(":", ": ");
          document.getElementById("bh-error-" + key).innerHTML = "&nbsp;<br/>&nbsp;<br/>" + error_msg;

          console.error(error_msg);
      });

});

document.getElementById('birdhouses').innerHTML = html;