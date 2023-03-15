
var index_template = {};
var index_lowres_position = {
  "1": "top:6%;left:3%;",
  "2": "top:3%;right:3%;",
  "3": "bottom:3%;left:3%;",
  "4": "bottom:3%;right:3%;"
};

//-------------------------------------------------

index_template["single"] = `
    <div id="video_stream_online" style="display:block;">
        <center>
            <div class="livestream_main_container cam1">
                <a onclick="birdhousePrint_load(view='TODAY', camera='<!--CAM1_ID-->');" style="cursor:pointer;">
                    <img src="<!--CAM1_URL-->" id="stream_cam1" class="livestream_main">
                </a>
            </div>
        </center>
        <br>&nbsp;<br>
    </div>
`

index_template["single_admin"] = `
    <div id="video_stream_online" style="display:block;">
        <center>
            <div class="livestream_main_container cam1">
                <a onclick="birdhousePrint_load(view='TODAY', camera='<!--CAM1_ID-->');" style="cursor:pointer;">
                    <img src="<!--CAM1_URL-->" id="stream_cam1" class="livestream_main">
                </a>
                <div class="livestream_record cam1">
                    <button onclick="appFW.requestAPI('POST',['start','recording','<!--CAM1_ID-->'],'','','','birdhouse_INDEX');" class="button-video-record">Record (<!--CAM1_ID-->)</button>
                    &nbsp;
                    <button onclick="appFW.requestAPI('POST',['stop', 'recording','<!--CAM1_ID-->'],'','','','birdhouse_INDEX');" class="button-video-record">Stop (<!--CAM1_ID-->)</button>
                </div>
            </div>
        </center>
        <br>&nbsp;<br>
    </div>
`

//-------------------------------------------------

index_template["picture-in-picture"] = `
    <div id="video_stream_online" style="display:block;">
        <center>
            <div class="livestream_main_container cam1">
                <a onclick="birdhousePrint_load(view='TODAY', camera='<!--CAM1_ID-->');" style="cursor:pointer;">
                    <img src="<!--CAM1_PIP_URL-->" id="stream_cam1" class="livestream_main">
                </a>
            </div>
        </center>
        <br>&nbsp;<br>
    </div>
`

//-------------------------------------------------

index_template["overlay"] = `
    <div id="video_stream_online" style="display:block;">
        <center>
        <div style="position:relative;margin:10px;">

            <a onclick="birdhousePrint_load(view='TODAY', camera='<!--CAM1_ID-->');" style="cursor:pointer;">
                <img src="<!--CAM1_URL-->" id="stream_cam2" class="" style="width:100%;height:auto;border:white solid 1px;">
            </a>

            <div style="position:absolute;<!--CAM2_LOWRES_POS-->;width:25%;">
                <a onclick="birdhousePrint_load(view='INDEX', camera='<!--CAM2_ID-->');" style="cursor:pointer;">
                    <img src="<!--CAM2_LOWRES_URL-->" id="stream_cam1" class=""  style="width:100%;height:auto;border:white solid 1px;">
                </a>
            </div>
        </div>
        </center>
    </div>
`

//-------------------------------------------------

index_template["default"] = `
    <div id="video_stream_online" style="display:block;">
        <center>
            <div class="livestream_2nd_container cam1cam2">
                <a onclick="birdhousePrint_load(view='INDEX', camera='<!--CAM2_ID-->');" style="cursor:pointer;">
                    <img src="<!--CAM2_URL-->" id="stream_cam1" class="livestream_2nd">
                </a>
            </div>
        </center>
        <center>
            <div class="livestream_main_container cam1cam2">
                <a onclick="birdhousePrint_load(view='TODAY', camera='<!--CAM1_ID-->');" style="cursor:pointer;">
                    <img src="<!--CAM1_URL-->" id="stream_cam2" class="livestream_main">
                </a>
            </div>
        </center>
    </div>
`

index_template["default_admin"] = `
    <div id="video_stream_online" style="display:block;">
        <center>
            <div class="livestream_2nd_container cam1cam2">
                <a onclick="birdhousePrint_load(view='INDEX', camera='<!--CAM2_ID-->');" style="cursor:pointer;">
                    <img src="<!--CAM2_URL-->" id="stream_cam1" class="livestream_2nd">
                </a>
            </div>
        </center>
        <center>
            <div class="livestream_main_container cam1cam2">
                <a onclick="birdhousePrint_load(view='TODAY', camera='<!--CAM1_ID-->');" style="cursor:pointer;">
                    <img src="<!--CAM1_URL-->" id="stream_cam2" class="livestream_main">
                </a>
                <div class="livestream_record cam1cam2">
                    <button onclick="appFW.requestAPI('POST',['start','recording','<!--CAM1_ID-->'],'','','','birdhouse_INDEX');" class="button-video-record">Record (<!--CAM1_ID-->)</button>
                    &nbsp;
                    <button onclick="appFW.requestAPI('POST',['stop', 'recording','<!--CAM1_ID-->'],'','','','birdhouse_INDEX');" class="button-video-record">Stop (<!--CAM1_ID-->)</button>
                </div>
            </div>
        </center>
    </div>
`

//-------------------------------------------------

index_template["offline"] = `
    <div id="video_stream_offline" style="display:none;">
        <center>
            &nbsp;<br>&nbsp;<br>
            <img src="<!--OFFLINE_URL-->" style="width:80%;border:1px solid white;">
            <br>&nbsp;<br>&nbsp;
        </center>
    </div>
`

