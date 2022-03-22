//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// streaming functions
//--------------------------------------
/* INDEX:
*/
//--------------------------------------

birdhouse_stream = {};
birdhouse_stream_play = {};

function birdhouseStream_load(server, microphones) {
    for (let mic in microphones) {
        var stream_url = "http://"+server+":"+microphones[mic]["port"]+"/";
        if (!birdhouse_stream[mic]) {
            console.log("Load Audio Streams: "+stream_url);
            birdhouse_stream[mic] = document.createElement("audio");
            birdhouse_stream[mic].setAttribute("id", "stream_"+mic);
            birdhouse_stream[mic].setAttribute("src", stream_url);
            document.body.appendChild(birdhouse_stream[mic]);
            birdhouse_stream_play[mic] = false;
        }
    }
}

function birdhouseStream_play(mic) {
    console.log("Play Audio Streams: "+mic);
    var id = "stream_"+mic;
    console.log("Play Audio Streams: ID-"+id);
    document.getElementById(id).play();
    birdhouse_stream_play[mic] = true;
}

function birdhouseStream_stop(mic) {
    console.log("Pause Audio Streams: "+mic);
    var id = "stream_"+mic;
    document.getElementById(id).pause();
    birdhouse_stream_play[mic] = false;
}

function birdhouseStream_toggle(mic) {
    if (birdhouse_stream_play[mic]) {
        birdhouseStream_stop(mic);
        birdhouse_stream_play = false;
        document.getElementById("toggle_stream_"+mic).innerHTML = birdhouseStream_image(false);
    }
    else {
        birdhouse_stream_play = true;
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
                birdhouse_stream_play = false;
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