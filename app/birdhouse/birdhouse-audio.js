//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// streaming functions
//--------------------------------------

var birdhouse_stream = {};
var birdhouse_stream_play = {};
var birdhouse_infinity = false;
var birdhouse_active_audio_streams = {};
var birdhouse_player_id = {};

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
        var stream_url = birdhouseAudioStream_URL(mic, "player")
        if (!birdhouse_stream[mic]) {
            console.log("Load Audio Streams: "+stream_url);
            birdhouse_stream[mic] = document.createElement("audio");
            birdhouse_stream[mic].setAttribute("controls", true);
            birdhouse_stream[mic].setAttribute("id", "stream_"+mic);
            birdhouse_stream[mic].setAttribute("src", stream_url);
            //birdhouse_stream[mic].setAttribute("type","audio/mp3");
            birdhouse_stream[mic].setAttribute("type","audio/x-wav;codec=PCM");
            //document.body.appendChild(birdhouse_stream[mic]);
            container.appendChild(birdhouse_stream[mic]);
            birdhouse_stream_play[mic] = false;
        }
    }
}

function birdhouseAudioStream_URL(micro, player) {
        //url = "http://"+micros[micro]["stream_server"]+"/"+micro+".mp3";
        var timestamp = new Date().getTime();
        var call_id =  micro + "&" + player + "&" + timestamp;
        var url = RESTurl + "audio.wav?" + call_id;
        birdhouse_active_audio_streams[call_id] == true;
        return url;
}

function birdhouseAudioStream_play(mic) {
    var id = "stream_"+mic;
    var player = document.getElementById(id);

    var stream_url = birdhouseAudioStream_URL(mic, "player")
    player.setAttribute("src", stream_url);

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

    if (!birdhouse_player_id[mic]) {
        birdhouse_player_id[mic] = setInterval(function() {
            birdhouseAudioStream_playback_info(mic);
        }, 1000);
    }
}

function birdhouseAudioStream_playback_info(mic) {
    var id = "stream_"+mic;
    var player = document.getElementById(id);
    var info = "<b>Status: " + mic + "</b><br/>";
    info    += "ID:" + id + " | DURATION:" + player.duration + " | POS:" + Math.round(player.currentTime*10)/10 + "s<br/>";
    info    += "PAUSE:" + player.paused + " | ENDED:" + player.ended+" | MUTE:" + player.muted + "<br/>";
    info    += "VOLUME:" + player.volume;

    if (player.paused || player.ended)  { birdhouseAudioStream_image_header(on=false); }
    else                                { birdhouseAudioStream_image_header(on=true); }
    if (player.paused || player.ended)  { birdhouseAudioStream_image(on=false); }
    else                                { birdhouseAudioStream_image(on=true); }
    setTextById("playback_info_" + mic, info);
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