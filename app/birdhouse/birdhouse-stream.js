//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// streaming functions
//--------------------------------------
/* INDEX:
function birdhouseStream_load(server, microphones)
function birdhouseStream_play(mic)
function birdhouseStream_stop(mic)
function birdhouseStream_toggle(mic)
function birdhouseStream_toggle_image(mic)
function birdhouseStream_image(on=true)
*/
//--------------------------------------

birdhouse_stream = {};
birdhouse_stream_play = {};
birdhouse_infinity = false;

function birdhouseStream_load(server, microphones) {
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
        var stream_url = "http://"+app_data["DATA"]["server"]["ip4_stream_audio"]+":"+microphones[mic]["port"]+"/";
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

function birdhouseStream_play(mic) {
    var id = "stream_"+mic;
    var player = document.getElementById(id);
    var src = player.getAttribute("src");
    if (player.duration === Infinity) {
        player.currentTime = 1e101;
        birdhouse_infinity = true;
        }
    else if (birdhouse_infinity) { player.currentTime = player.duration - 1; }

    console.log("Play Audio Streams: "+mic+" (ID:"+id+" | URL:"+src+" | DURATION:"+player.duration+" | POS:"+player.currentTime+")");
    player.play();
    birdhouse_stream_play[mic] = true;
}

function birdhouseStream_stop(mic) {
    var id = "stream_"+mic;
    var player = document.getElementById(id);

    console.log("Pause Audio Streams: "+mic+" (ID:"+id+" | DURATION:"+player.duration+" | POS:"+player.currentTime+")");
    player.pause();
    birdhouse_stream_play[mic] = false;
}

function birdhouseStream_toggle(mic) {
    var id = "stream_"+mic;
    var player = document.getElementById(id);

    if (birdhouse_stream_play[mic] == true) {
        birdhouseStream_stop(mic);
        document.getElementById("toggle_stream_"+mic).innerHTML = birdhouseStream_image(false);
    }
    else {
        birdhouseStream_play(mic);
        document.getElementById("toggle_stream_"+mic).innerHTML = birdhouseStream_image(true);
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
                birdhouseStream_stop(mic);
                document.getElementById("toggle_stream_"+mic).innerHTML = birdhouseStream_image(false);
            }
        },1000);
    }
}

function birdhouseStream_toggle_image(mic) {
    return "<div id='toggle_stream_"+mic+"' onclick='birdhouseStream_toggle(\""+mic+"\");'>"+birdhouseStream_image(false)+"</div>"
}

function birdhouseStream_image(on=true) {
    var img_on = 'birdhouse/img/bird_sing_on.png';
    var img_off = 'birdhouse/img/bird_sing_off.png';
    var size = "height:90px;width:90px;";

    if (on) { return "<img src='"+img_on+"' style='"+size+"'>"; }
    else { return "<img src='"+img_off+"' style='"+size+"'>"; }
}