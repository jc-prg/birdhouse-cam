
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
                    <img src="<!--CAM1_URL-->" id="stream_<!--CAM1_ID-->" class="livestream_main">
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
                    <img src="<!--CAM1_URL-->" id="stream_<!--CAM1_ID-->" class="livestream_main">
                </a>
                <!--ADMIN-->
            </div>
        </center>
        <br>&nbsp;<br>
    </div>
`

//-------------------------------------------------

index_template["admin"] = `

    <center>
    <table border="0" width="100%">
    <tr>
    <td width="35%" align="center" valign="top">
            <button onclick="birdhouse_recordStart('<!--CAM1_ID-->');" class="button-video-record">Record (<!--CAM1_ID-->)</button><br/>
            <button onclick="birdhouse_recordStop('<!--CAM1_ID-->');" class="button-video-record">Stop (<!--CAM1_ID-->)</button><br/>
            <div id="button_object_detection" style="display:none;"><button onclick="<!--OBJECT-->" class="button-video-record">Objects <!--OBJECT_BUTTON--></button></div>
    </td>
    <td>
        <table border="0" width="100%">
            <tr>
                <td>
                    <div style="width:30%;float:left;height:20px;padding:5px;"><b>Status&nbsp;&quot;<!--CAM1_ID-->&quot;:</b></div>
                    <div style="float:left;">
                        <div id="status_error_<!--CAM1_ID-->" style="float:left;height:20px;"><div id="black"></div></div>
                        <div id="status_error_record_<!--CAM1_ID-->" style="float:left;height:20px;"><div id="black"></div></div>
                        <div style="float:left;padding:5px;height:20px;"><font id="show_stream_count_<!--CAM1_ID-->">0</font> Streams</div>
                        <div style="float:left;padding:5px;height:20px;">(<font id="show_stream_fps_<!--CAM1_ID-->">0</font> fps)</div>
                    </div>
                </td>
            </tr>
             <tr id="admin_status_index">
                <td>
                    <div style="width:30%;float:left;height:20px;padding:5px;"><b>Status&nbsp;&quot;<!--CAM2_ID-->&quot;:</b></div>
                    <div style="float:left;">
                        <div id="status_error_<!--CAM2_ID-->" style="float:left;height:20px;"><div id="black"></div></div>
                        <div id="status_error_record_<!--CAM2_ID-->" style="float:left;height:20px;"><div id="black"></div></div>
                        <div style="float:left;padding:5px;height:20px;"><font id="show_stream_count_<!--CAM2_ID-->">0</font> Streams</div>
                        <div style="float:left;padding:5px;height:20px;">(<font id="show_stream_fps_<!--CAM2_ID-->">0</font> fps)</div>
                    </div>
                </td>
            </tr>
            <tr>
                <td>
                    <div style="width:30%;float:left;height:20px;padding:5px;"><b>Status&nbsp;&quot;Client&quot;:</b></div>
                    <div style="float:left;">
                        <div style="float:left;padding:5px;height:20px;"><font id="show_stream_count_client">0</font> Streams&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div>
                    </div>
                </td>
            </tr>
            <tr><td height="20px">&nbsp;</td></tr>
        </table>

    </td></tr></table>
    </center>
`

//-------------------------------------------------

index_template["picture-in-picture"] = `
    <div id="video_stream_online" style="display:block;">
        <center>
            <div class="livestream_main_container cam1">
                <a onclick="birdhousePrint_load(view='TODAY', camera='<!--CAM1_ID-->');" style="cursor:pointer;">
                    <img src="<!--CAM1_PIP_URL-->" id="stream_pip_<!--CAM1_ID-->" class="livestream_main">
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
                <img src="<!--CAM1_URL-->" id="stream_<!--CAM1_ID-->" class="" style="width:100%;height:auto;border:white solid 1px;">
            </a>

            <div style="position:absolute;<!--CAM2_LOWRES_POS-->;width:25%;">
                <a onclick="birdhousePrint_load(view='INDEX', camera='<!--CAM2_ID-->');" style="cursor:pointer;">
                    <img src="<!--CAM2_LOWRES_URL-->" id="stream_lowres_<!--CAM2_ID-->" class=""  style="width:100%;height:auto;border:white solid 1px;">
                </a>
            </div>
        </div>
        </center>
    </div>
`

index_template["overlay_admin"] = `
    <div id="video_stream_online" style="display:block;">
        <center>
        <div style="position:relative;margin:10px;">

            <a onclick="birdhousePrint_load(view='TODAY', camera='<!--CAM1_ID-->');" style="cursor:pointer;">
                <img src="<!--CAM1_URL-->" id="stream_<!--CAM1_ID-->" class="" style="width:100%;height:auto;border:white solid 1px;">
            </a>

            <div style="position:absolute;<!--CAM2_LOWRES_POS-->;width:25%;">
                <a onclick="birdhousePrint_load(view='INDEX', camera='<!--CAM2_ID-->');" style="cursor:pointer;">
                    <img src="<!--CAM2_LOWRES_URL-->" id="stream_lowres_<!--CAM2_ID-->" class=""  style="width:100%;height:auto;border:white solid 1px;">
                </a>
            </div>

        </table>

        </div>
        <!--ADMIN-->
        </center>
    </div>
`

//-------------------------------------------------

index_template["default"] = `
    <div id="video_stream_online" style="display:block;">
        <center>
            <div class="livestream_2nd_container cam1cam2">
                <a onclick="birdhousePrint_load(view='INDEX', camera='<!--CAM1_ID-->');" style="cursor:pointer;">
                    <img src="<!--CAM2_URL-->" id="stream_<!--CAM2_ID-->" class="livestream_2nd">
                </a>
            </div>
        </center>
        <center>
            <div class="livestream_main_container cam1cam2">
                <a onclick="birdhousePrint_load(view='TODAY', camera='<!--CAM1_ID-->');" style="cursor:pointer;">
                    <img src="<!--CAM1_URL-->" id="stream_<!--CAM1_ID-->" class="livestream_main">
                </a>
            </div>
        </center>
    </div>
`

index_template["default_admin"] = `
    <div id="video_stream_online" style="display:block;">
        <center>
            <div class="livestream_2nd_container cam1cam2">
                <a onclick="birdhousePrint_load(view='INDEX', camera='<!--CAM1_ID-->');" style="cursor:pointer;">
                    <img src="<!--CAM2_URL-->" id="stream_<!--CAM2_ID-->" class="livestream_2nd">
                </a>
            </div>
        </center>
        <center>
            <div class="livestream_main_container cam1cam2">
                <a onclick="birdhousePrint_load(view='TODAY', camera='<!--CAM1_ID-->');" style="cursor:pointer;">
                    <img src="<!--CAM1_URL-->" id="stream_<!--CAM1_ID-->" class="livestream_main">
                </a>
                <!--ADMIN-->
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

