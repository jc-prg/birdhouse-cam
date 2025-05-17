
var index_template = {};
var index_lowres_position = {
  "1": "upper_left",
  "2": "upper_right",
  "3": "lower_left",
  "4": "lower_right",
};

//-------------------------------------------------

index_template["single"] = `
    <div id="video_stream_online">
        <center>
        <div class="streams_wrapper">
            <div class="streams_index_overlay">

                <a onclick="birdhousePrint_load(view='TODAY', camera='<!--CAM1_ID-->');" style="cursor:pointer;">
                    <img src="<!--CAM1_URL-->" id="stream_<!--CAM1_ID-->" class="streams_index_main">
                </a>

            </div>
        </div>
        </center>
    </div>
`

index_template["single_admin"] = `
    <div id="video_stream_online">
        <center>
        <div class="streams_wrapper">
            <div class="streams_index_overlay">

                <a onclick="birdhousePrint_load(view='TODAY', camera='<!--CAM1_ID-->');" style="cursor:pointer;">
                    <img src="<!--CAM1_URL-->" id="stream_<!--CAM1_ID-->" class="streams_index_main">
                </a>

            </div>
        </div>
        &nbsp;<br/>
        <!--ADMIN-->
        </center>
    </div>
`

index_template["picture-in-picture_admin"]  = index_template["single_admin"]
index_template["picture-in-picture"]        = index_template["single"]

//-------------------------------------------------

index_template["admin"] = `

    <center>
    <table border="0" width="100%">
    <tr>
    <td width="35%" align="center" valign="top">
            <button id="rec_start_<!--CAM1_ID-->"  onclick="birdhouse_recordStart('<!--CAM1_ID-->');"   class="button-video-record">&#9679;
            </button><button id="rec_stop_<!--CAM1_ID-->"   onclick="birdhouse_recordStop('<!--CAM1_ID-->');"    class="button-video-record" disabled="disabled">&#9632;
            </button><button id="rec_cancel_<!--CAM1_ID-->" onclick="birdhouse_recordCancel('<!--CAM1_ID-->');"  class="button-video-record" disabled="disabled" style="font-size:20px;padding:0px;line-height:0.8;"><b>&times;</b></button><br/>&nbsp;<br/>
            <div id="button_object_detection" style="display:none;"><button onclick="<!--OBJECT-->" class="button-video-record" style="width:100px;">Objects <!--OBJECT_BUTTON--></button></div>
    </td>
    <td>
        <table border="0" width="100%">
            <tr>
                <td>
                    <div style="width:50px;float:left;height:20px;padding:5px;"><b><!--CAM1_ID-->:</b></div>
                    <div style="float:left;width:250px;" class="admin_status_client_full">
                        <div style="float:left;height:20px;padding-top:1px;" id="status_error_<!--CAM1_ID-->"><div id="black"></div></div>
                        <div style="float:left;height:20px;padding-top:1px;" id="status_error_record_<!--CAM1_ID-->"><div id="black"></div></div>
                        <div style="float:left;padding:5px;height:20px;" id="show_stream_count_<!--CAM1_ID-->">0 Streams</div>
                        <div style="float:left;height:20px;padding:5px;display:block;width:70px;" id="show_stream_fps_<!--CAM1_ID-->">(0 fps)</div>
                        <div style="float:left;height:20px;padding:5px;display:none;width:70px;" id="show_stream_object_fps_<!--CAM1_ID-->">(0&nbsp;fps)</div>
                    </div>
                    <div style="float:left;width:130px;" class="admin_status_client_small">
                        <div style="float:left;height:20px;padding-top:1px;" id="status_error2_<!--CAM1_ID-->"><div id="black"></div></div>
                        <div style="float:left;height:20px;padding-top:1px;" id="status_error2_record_<!--CAM1_ID-->"><div id="black"></div></div>
                        <div style="float:left;height:20px;padding:5px;" id="show_stream_info_<!--CAM1_ID-->">(0: 0fps)</div>
                    </div>
                </td>
            </tr>
             <tr id="admin_status_index">
                <td>
                    <div style="width:50px;float:left;height:20px;padding:5px;"><b><!--CAM2_ID-->:</b></div>
                    <div style="float:left;width:250px;" class="admin_status_client_full">
                        <div style="float:left;height:20px;" id="status_error_<!--CAM2_ID-->"><div id="black"></div></div>
                        <div style="float:left;height:20px;" id="status_error_record_<!--CAM2_ID-->"><div id="black"></div></div>
                        <div style="float:left;height:20px;padding:5px;" id="show_stream_count_<!--CAM2_ID-->">0 Streams</div>
                        <div style="float:left;height:20px;padding:5px;" id="show_stream_fps_<!--CAM2_ID-->">(0 fps)</div>
                    </div>
                    <div style="float:left;width:130px;" class="admin_status_client_small">
                        <div style="float:left;height:20px;" id="status_error2_<!--CAM2_ID-->"><div id="black"></div></div>
                        <div style="float:left;height:20px;" id="status_error2_record_<!--CAM2_ID-->"><div id="black"></div></div>
                        <div style="float:left;height:20px;padding:5px;" id="show_stream_info_<!--CAM2_ID-->">(0: 0fps)</div>
                    </div>
                </td>
            </tr>
            <tr class="admin_status_client_full">
                <td>
                    <div style="width:60px;float:left;height:20px;padding:5px;padding-top:1px;"><b>Client:</b></div>
                    <div style="float:left;height:20px;">
                        <div style="padding:5px;height:20px;padding-top:1px;"><font id="show_stream_count_client">0 Streams</font></div>
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
    <div id="video_stream_online">
        <center>
        <div class="streams_wrapper">
            <div class="streams_index_overlay">

                <a onclick="birdhousePrint_load(view='TODAY', camera='<!--CAM1_ID-->');" style="cursor:pointer;">
                    <img src="<!--CAM1_URL-->" id="stream_<!--CAM1_ID-->" class="streams_index_main">
                </a>

                <a onclick="birdhousePrint_load(view='INDEX', camera='<!--CAM2_ID-->');" style="cursor:pointer;">
                    <img src="<!--CAM2_LOWRES_URL-->" id="stream_lowres_<!--CAM2_ID-->" class="streams_index_second <!--CAM2_LOWRES_POS-->">
                </a>

            </div>
        </div>
        </center>
    </div>
`

index_template["overlay_admin"] = `
    <div id="video_stream_online">
        <center>
        <div class="streams_wrapper">
            <div class="streams_index_overlay">

                <a onclick="birdhousePrint_load(view='TODAY', camera='<!--CAM1_ID-->');" style="cursor:pointer;">
                    <img src="<!--CAM1_URL-->" id="stream_<!--CAM1_ID-->" class="streams_index_main">
                </a>

                <a onclick="birdhousePrint_load(view='INDEX', camera='<!--CAM2_ID-->');" style="cursor:pointer;">
                    <img src="<!--CAM2_LOWRES_URL-->" id="stream_lowres_<!--CAM2_ID-->" class="streams_index_second <!--CAM2_LOWRES_POS-->">
                </a>

            </div>
        </div>
        &nbsp;<br/>
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
                    <img src="<!--CAM2_LOWRES_URL-->" id="stream_<!--CAM2_ID-->" class="livestream_2nd">
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
                    <img src="<!--CAM2_LOWRES_URL-->" id="stream_<!--CAM2_ID-->" class="livestream_2nd">
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

app_scripts_loaded += 1;
