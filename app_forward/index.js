
var html = "";
var port_html = 8000;
var port_video = 8007;

Object.entries(birdhouses).forEach(([key,value]) => {
    html += '<div class="image_container"><center>';

    html += '<a href="http://[' + value + ']:' + port_html + '" style="color:yellow">Birdhouse ' + key + '<br/>';
    html += '<img src="http://[' + value + ']:' + port_video + '/lowres/stream.mjpg?cam1?' + key + '?bh-' + key + '-' + timestamp + '" class="image" id="bh-' + key + '" style="display:block;"/>';

    html += '</a><br/>&nbsp;<br/>&nbsp;</center></div>';

});

document.getElementById('birdhouses').innerHTML = html;