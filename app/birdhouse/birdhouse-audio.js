//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// streaming functions
//--------------------------------------

var birdhouse_stream = {};
var birdhouse_stream_play = {};
var birdhouse_infinity = false;
var birdhouse_active_audio_streams = {};

function birdhouseAudioStream_load(server, microphones) {
    var audio_container = "audio_stream_container";

    if (!document.getElementById(audio_container)) {
        container = document.createElement("div");
        container.style.display = "none";
        container.setAttribute("id", audio_container);
        document.body.appendChild(container);
    }
    else {
        container = document.getElementById(audio_container);
        console.log("Reload audio stream not implemented yet.")
    }
    for (let mic in microphones) {
        var stream_url = "http://"+microphones[mic]["stream_server"]+"/";
        stream_url += mic+".mp3";
        if (!birdhouse_stream[mic]) {
            console.log("Load Audio Streams: "+stream_url);
            birdhouse_stream[mic] = document.createElement("audio");
            birdhouse_stream[mic].setAttribute("id", "stream_"+mic);
            birdhouse_stream[mic].setAttribute("src", stream_url);
            birdhouse_stream[mic].setAttribute("type","audio/mp3");
            //document.body.appendChild(birdhouse_stream[mic]);
            container.appendChild(birdhouse_stream[mic]);
            birdhouse_stream_play[mic] = false;
        }
    }
}

function birdhouseAudioStream_URL(micro) {
        //url = "http://"+micros[micro]["stream_server"]+"/"+micro+".mp3";
        var timestamp = new Date().getTime();
        var call_id =  micro + "&device_settings&" + timestamp;
        var url = RESTurl + "audio.wav?" + call_id;
        birdhouse_active_audio_streams[call_id] == true;
        return url;
}

function birdhouseAudioStream_play(mic) {
    var id = "stream_"+mic;
    var player = document.getElementById(id);
    var src = player.getAttribute("src");
    if (player.duration === Infinity) {
        player.currentTime = 1e101;
        birdhouse_infinity = true;
        }
    else if (birdhouse_infinity) { player.currentTime = player.duration - 1; }

    console.log("Play Audio Streams: "+mic+" (ID:"+id+" | URL:"+src+" | DURATION:"+player.duration+" | POS:"+player.currentTime+")");
    player.muted = false;
    player.play();
    birdhouse_stream_play[mic] = true;
}

function birdhouseAudioStream_stop(mic) {
    var id = "stream_"+mic;
    var player = document.getElementById(id);

    console.log("Pause Audio Streams: "+mic+" (ID:"+id+" | DURATION:"+player.duration+" | POS:"+player.currentTime+")");
    player.pause();
    birdhouse_stream_play[mic] = false;
}

function birdhouseAudioStream_toggle(mic="", add_id="") {
    for (let micro in birdhouseMicrophones) { if (mic == "" && birdhouseMicrophones[micro]["active"]) { mic = micro; }}
    var id = "stream_"+mic;
    var player = document.getElementById(id);

    if (birdhouse_stream_play[mic] == true) {
        birdhouseAudioStream_stop(mic);
        birdhouseAudioStream_image_header(false);
        if (document.getElementById("toggle_stream_"+mic+"_"+add_id)) {
            document.getElementById("toggle_stream_"+mic+"_"+add_id).innerHTML = birdhouseAudioStream_image(false);
        }
    }
    else {
        birdhouseAudioStream_play(mic);
        birdhouseAudioStream_image_header(true);
        if (document.getElementById("toggle_stream_"+mic+"_"+add_id)) {
            document.getElementById("toggle_stream_"+mic+"_"+add_id).innerHTML = birdhouseAudioStream_image(true);
        }
        try {
            var id = "stream_"+mic;
            console.log("Play Audio Streams: ID-"+id);
            document.getElementById(id).play();
        }
        catch(err) {
            console.warning(err.message);
        }
        setTimeout(function(){
            if (document.getElementById("stream_"+mic).paused) {
                birdhouseAudioStream_stop(mic);
                birdhouseAudioStream_image_header(false);
                if (document.getElementById("toggle_stream_"+mic+"_"+add_id)) {
                    document.getElementById("toggle_stream_"+mic+"_"+add_id).innerHTML = birdhouseAudioStream_image(false);
                }
            }
        },1000);
    }
}

function birdhouseAudioStream_toggle_image(mic, add_id="") {
    var html = "";
    html += "<div id='toggle_stream_"+mic+"_"+add_id+"_container' class='audiostream_bird_container'>";
    html += "<div id='toggle_stream_"+mic+"_"+add_id+"' class='audiostream_bird_image' onclick='birdhouseAudioStream_toggle(\""+mic+"\",\""+add_id+"\");'>"+birdhouseAudioStream_image(false)+"</div>";
    html += "<div class='audiostream_bird_info' onclick='birdhouseAudioStream_toggle(\""+mic+"\",\""+add_id+"\");' >"+mic+"</div>";
    html += "</div>";
    return html;
}

function birdhouseAudioStream_image(on=true) {
    var img_on = 'birdhouse/img/bird_sing_on.png';
    var img_off = 'birdhouse/img/bird_sing_off.png';
    var size = "height:90px;width:90px;";

    if (on) { return "<img src='"+img_on+"' style='"+size+"'>"; }
    else { return "<img src='"+img_off+"' style='"+size+"'>"; }
}

function birdhouseAudioStream_image_header(on=true) {
    var img_on = 'birdhouse/img/icon_bird_sing.png';
    var img_off = 'birdhouse/img/icon_bird_mute.png';

    //"<img id='stream_toggle_header' class='header_icon_wide' src='birdhouse/img/icon_bird_mute.png' onclick='birdhouseAudioStream_toggle();'>"
    if (on) { document.getElementById('stream_toggle_header').setAttribute("src",img_on); }
    else    { document.getElementById('stream_toggle_header').setAttribute("src",img_off); }
}