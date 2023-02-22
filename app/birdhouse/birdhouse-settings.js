//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// settings
//--------------------------------------

var app_settings_active = false;
var birdhouse_settings  = new birdhouse_app_settings();


function birdhouse_app_settings (name="Settings") {

	this.create	= function (type="SETTINGS") {

        var tab             = new birdhouse_table();
        var initial_setup   = app_data["DATA"]["server"]["initial_setup"];
        var cameras         = app_data["DATA"]["devices"]["cameras"];
        var weather         = app_data["WEATHER"];
        var button_style    = "background-color:lightgray;color:black;width:90px;margin:3px;";
        var open_settings = {
            "app_info_01" : true,
            "app_info_02" : false,
            "api_calls"   : false,
            "server_info" : true,
            "display_info": false
            }

        if (initial_setup) {
            open_settings["app_info_01"] = false;
            open_settings["server_info"] = false;

            var img = "<img src='"+app_loading_image+"' width='250'><br/>&nbsp;<br/>"
            appMsg.confirm(img + lang("INITIAL_SETUP"), "console.log('.');", 400);
            }


        tab.style_rows["height"] = "27px";
        tab.style_cells["width"] = "40%";

        var api_call = "<button onclick='window.open(\"" + RESTurl + "api/list/\",\"_blank\");' style='"+button_style+"';>REST API</button>";
        api_call    += "<button onclick='window.open(\"" + RESTurl + "api/INDEX/\",\"_blank\");' style='"+button_style+"';>INDEX</button>";
        api_call    += "<button onclick='birdhouse_forceBackup();' style='"+button_style+"';>Force Backup</button>";
        api_call    += "<button onclick='birdhouse_recreateImageConfig();' style='"+button_style+"';>NewImgCfg</button>";
	    for (let camera in cameras) {
	        api_call += "<button onclick='window.open(\"" + RESTurl + "api/TODAY/"+camera+"/\",\"_blank\");' style='"+button_style+"';>Today "+camera.toUpperCase()+"</button>";
	        api_call += "<button onclick='window.open(\"" + RESTurl + "api/TODAY_COMPLETE/"+camera+"/\",\"_blank\");' style='"+button_style+"';>Compl. "+camera.toUpperCase()+"</button>";
	        api_call += "<button onclick='window.open(\"" + RESTurl + "api/ARCHIVE/"+camera+"/\",\"_blank\");' style='"+button_style+"';>Archive "+camera.toUpperCase()+"</button>";
            }
        api_call += "<button onclick='appFW.requestAPI(\"POST\",[\"check-timeout\"],\"\",\"\",\"\");' style='"+button_style+"';>Timeout</button>";

        html  = "<h2>Information</h2>";
		html += "<hr style='border:1px solid gray;'>"

		html_entry = tab.start();
		html_entry += tab.row("App:",	"<a href='/app/index.html?INFO' target='_blank'>"+ app_title + "</a>");
		html_entry += tab.row("Versions:",
						"App: " 		+ app_version + "<br/>" +
						"API: " 		+ app_api_version + "<br/>" +
						"jcMsg: " 		+ appMsg.appVersion + "<br/>" + 
						"jcApp: "		+ appFW.appVersion);

		html_entry += tab.row("Source:","<a href='https://github.com/jc-prg/birdhouse-cam/' target='_blank'>https://github.com/jc-prg/birdhouse-cam/</a>");
		html_entry += tab.row("&nbsp;");
		html_entry += tab.end();
        html += birdhouse_OtherGroup( "app_info_01", "App Information (Version)", html_entry, open_settings["app_info_01"] );

        html_entry = tab.start();
    	html_entry += tab.row("Active Streams:",      "<div id='system_active_streams'>please wait ...</div>");
    	html_entry += tab.row("CPU Temperature:",     "<div id='system_info_cpu_temperature'>please wait ...</div>");
    	html_entry += tab.row("CPU Usage:",           "<div id='system_info_cpu_usage'>please wait ...</div>");
    	html_entry += tab.row("CPU Usage (Details):", "<div id='system_info_cpu_usage_detail'>please wait ...</div>");
    	html_entry += tab.row("Memory Total:",        "<div id='system_info_mem_total'>please wait ...</div>");
    	html_entry += tab.row("Memory Used:",         "<div id='system_info_mem_used'>please wait ...</div>");
    	html_entry += tab.row("HDD used:",            Math.round(app_data["STATUS"]["system"]["hdd_used"]*10)/10 + " GB");
    	html_entry += tab.row("HDD total:",           Math.round(app_data["STATUS"]["system"]["hdd_total"]*10)/10 + " GB");
        html_entry += tab.row("&nbsp;");
        html_entry += tab.end();
        html += birdhouse_OtherGroup( "server_info", "Server Information", html_entry, open_settings["server_info"] );

        if (type == "SETTINGS") {
            api_call = "&nbsp;<br/><center>"+api_call+"</center><br/>&nbsp;";
            html += birdhouse_OtherGroup( "api_calls", "API Calls", api_call, open_settings["api_calls"] );

            html_entry = tab.start();
            html_entry += tab.row("Window:", document.body.clientWidth + "x" + document.body.clientHeight );
            html_entry += tab.row("Position:", "<div id='scrollPosition'>0 px</div>" );
            html_entry += tab.row("Format:", print_display_definition());
            html_entry += tab.row("Browser:", navigator.userAgent);
            html_entry += tab.end();

            html += birdhouse_OtherGroup( "display_info", "Display information", html_entry, open_settings["display_info"] );

            html_entry = tab.start();
            html_entry += tab.row("Reload Interval:", app_reload_interval + "s");
            html_entry += tab.row("Active Camera:&nbsp;", app_active_cam);
            html_entry += tab.row("Available Cameras:&nbsp;", app_available_cameras.length);
            html_entry += tab.row("Active Page:&nbsp;", app_active_page);
            html_entry += tab.row("Active Date:&nbsp;", app_active_date);
            html_entry += tab.row("Unique stream URL:&nbsp;", app_unique_stream_url);
            html_entry += tab.row("Unique stream ID:&nbsp;",	app_unique_stream_id);
            html_entry += tab.end();

            html += birdhouse_OtherGroup( "app_info_02", "App Information (Cookie, Reload)", html_entry, open_settings["app_info_02"] );

            html_entry = tab.start();
            html_entry += tab.row("Location:", weather["info_city"] + " (" + weather["info_update"] + ")");
            html_entry += tab.row("Sunrise / Sunset:", weather["forecast"]["today"]["sunrise"] + " / " + weather["forecast"]["today"]["sunset"]);
            html_entry += tab.row("Weather:", "<big>" + weather["current"]["description_icon"] + "</big> &nbsp;" + weather["current"]["temperature"] + "°C");
            html_entry += tab.end();

            html += birdhouse_OtherGroup( "weather_info", "Weather Information", html_entry, false );
            }

        if (type == "INFO_ONLY") {
            setTextById("frame2", html)
            }

        if (type == "SETTINGS") {
            setTextById("setting1", html);
            setTextById("setting2", "");
            setTextById("setting3", "");

            html = "<h2>"+lang("SETTINGS")+"</h2>";
            html += "<hr style='border:1px solid gray;'>"

            timezones = "UTC-12,UTC-11,UTC-10,UTC-9,UTC-8,UTC-7,UTC-6,UTC-5,UTC-4,UTC-3,UTC-2,UTC-1,UTC+0,UTC+1,UTC+2,UTC+3,UTC+4,UTC+5,UTC+6,UTC+7,UTC+8,UTC+9,UTC+10,UTC+11,UTC+12"

            html += "<div style='display:none'>Edit initial setup: "+birdhouse_edit_field(id="set_initial_setup", field="server:initial_setup", type="select", options="false", data_type="boolean")+"</div>";
            html += tab.start();
            html += tab.row("Title:&nbsp;", birdhouse_edit_field(id="set_title", field="title", type="input") );
            html += tab.row("Language:&nbsp;", birdhouse_edit_field(id="set_language", field="language", type="select", options="EN,DE") );
            html += tab.row("Backup-Time:&nbsp;", birdhouse_edit_field(id="set_backup", field="backup:time", type="input") );
            html += tab.row("Backup-Preview:&nbsp;", birdhouse_edit_field(id="set_preview", field="backup:preview", type="input") );
            html += tab.row("Timezone:&nbsp;", birdhouse_edit_field(id="set_timezone", field="server:timezone", type="select", options=timezones, data_type="string") );
            html += tab.row("RPi Active:&nbsp;", birdhouse_edit_field(id="set_rpi", field="server:rpi_active", type="select", options="true,false", data_type="boolean") );
            html += tab.row("<hr/>");
            link = "http://"+app_data["DATA"]["server"]["ip4_address"]+":5100/_utils/";
            html += tab.row("DB Server:","<a href='"+link+"' target='_blank'>"+link+"</a>");
            html += tab.row("HTTP Server:&nbsp;", birdhouse_edit_field(id="set_ip4", field="server:ip4_address", type="input", options="true,false", data_type="string") );
            html += tab.row("HTTP Port:&nbsp;", birdhouse_edit_field(id="set_port", field="server:port", type="input", options="true,false", data_type="integer") );
            html += tab.row("Videostream Srv:&nbsp;", birdhouse_edit_field(id="set_ip4_video", field="server:ip4_stream_video", type="input", options="true,false", data_type="string") );
            html += tab.row("Videostream Port:&nbsp;", birdhouse_edit_field(id="set_ip4_video_port", field="server:port_video", type="input", data_type="integer") );
            html += tab.row("Audiostream Srv:&nbsp;", birdhouse_edit_field(id="set_ip4_audio", field="server:ip4_stream_audio", type="input", options="true,false", data_type="string") );
            html += tab.row("Deny admin from IP4:&nbsp;", birdhouse_edit_field(id="set_ip4_deny", field="server:ip4_admin_deny", type="input", options="true,false", data_type="json") );
            html += tab.row("<hr>");
            html += tab.row("", birdhouse_edit_save("set_main","set_initial_setup:set_language:set_timezone:set_title:set_backup:set_preview:set_rpi:set_ip4:set_port:set_ip4_audio:set_ip4_video:set_ip4_deny:set_ip4_video_port") );
            html += tab.row("&nbsp;");
            html += tab.end();

            setTextById("setting2", html);
    		this.toggle();
            }


		}


	this.toggle	= function (active=false) {
	
		if (active)	{ view_frame = "block"; view_settings = "none";  app_settings_active = false; }
		else		{ view_frame = "none";  view_settings = "block"; app_settings_active = true;  }

		for (var i=1;i<=app_frame_count;i++) {
			var element = document.getElementById("frame"+i);
			element.style.display = view_frame;
			}
		for (var i=1;i<=app_setting_count;i++) {
			var element = document.getElementById("setting"+i);
			element.style.display = view_settings;
			}
		}
	}


