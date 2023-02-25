//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// settings
//--------------------------------------

var app_settings_active = false;
var birdhouse_settings  = new birdhouse_app_settings();


function birdhouse_app_settings (name="Settings") {

	this.create	= function (type="SETTINGS") {

        this.tab = new birdhouse_table();
        this.tab.style_rows["height"] = "27px";
        this.tab.style_cells["width"] = "40%";
        var tab = this.tab;

        var initial_setup   = app_data["DATA"]["server"]["initial_setup"];

        var current_url     = window.location.href;
        var current_server  = current_url.split("//")[1];
        current_server      = current_server.split("/")[0];
        this.current_server = current_server.split(":")[0];

        var open_settings = {
            "app_info_01" : true,
            "server_info" : false,
            "api_calls"   : false,
            "app_info_02" : false,
            "display_info": false
            }

        if (initial_setup) {
            open_settings["app_info_01"] = false;
            open_settings["server_info"] = false;

            var img = "<img src='"+app_loading_image+"' width='250'><br/>&nbsp;<br/>"
            appMsg.confirm(img + lang("INITIAL_SETUP"), "console.log('.');", 400);
            }

        html  = "<h2>Information</h2>";
		html += "<hr style='border:1px solid gray;'>"

        html_entry = this.app_information();
        html += birdhouse_OtherGroup( "app_info_01", "App Information (Version)", html_entry, open_settings["app_info_01"] );

        html_entry = this.server_information();
        html += birdhouse_OtherGroup( "server_info", "Server Information", html_entry, open_settings["server_info"] );

        if (type == "SETTINGS") {
            html_entry = this.api_calls();
            html += birdhouse_OtherGroup( "api_calls", "API Calls", html_entry, open_settings["api_calls"] );

            html_entry = this.display_information();
            html += birdhouse_OtherGroup( "display_info", "Display information", html_entry, open_settings["display_info"] );

            html_entry = this.app_information_detail();
            html += birdhouse_OtherGroup( "app_info_02", "App Information (Cookie, Reload)", html_entry, open_settings["app_info_02"] );
            }

        if (type == "INFO_ONLY") {
            setTextById("frame2", html)
            }

        if (type == "SETTINGS") {
            setTextById("setting1", html);
            setTextById("setting2", "");
            setTextById("setting3", "");

            html = this.settings();

            setTextById("setting2", html);
    		this.toggle();
            }
		}

    this.settings = function () {
        var tab = new birdhouse_table();
        var timezones = "UTC-12,UTC-11,UTC-10,UTC-9,UTC-8,UTC-7,UTC-6,UTC-5,UTC-4,UTC-3,UTC-2,UTC-1,UTC+0,UTC+1,UTC+2,UTC+3,UTC+4,UTC+5,UTC+6,UTC+7,UTC+8,UTC+9,UTC+10,UTC+11,UTC+12"

        if (app_data["DATA"]["server"]["database_server"] && app_data["DATA"]["server"]["database_server"] != "") {
            var link = "http://"+app_data["DATA"]["server"]["database_server"]+":5100/_utils/";
        }
        else {
            var link = "http://"+this.current_server+":5100/_utils/";
        }

        var html = "<h2>"+lang("SETTINGS")+"</h2>";
        html += "<hr style='border:1px solid gray;'>"
        html += "<div style='display:none'>Edit initial setup: "+birdhouse_edit_field(id="set_initial_setup", field="server:initial_setup", type="select", options="false", data_type="boolean")+"</div>";
        html += this.tab.start();
        html += this.tab.row("Title:&nbsp;", birdhouse_edit_field(id="set_title", field="title", type="input") );
        html += this.tab.row("Language:&nbsp;", birdhouse_edit_field(id="set_language", field="localization:language", type="select", options="EN,DE") );
        html += this.tab.row("Timezone:&nbsp;", birdhouse_edit_field(id="set_timezone", field="localization:timezone", type="select", options=timezones, data_type="string") );
        html += this.tab.row("Backup-Time:&nbsp;", birdhouse_edit_field(id="set_backup", field="backup:time", type="input") );
        html += this.tab.row("Backup-Preview:&nbsp;", birdhouse_edit_field(id="set_preview", field="backup:preview", type="input") );
        html += this.tab.row("RPi Active:&nbsp;", birdhouse_edit_field(id="set_rpi", field="server:rpi_active", type="select", options="true,false", data_type="boolean") );
        html += this.tab.row("<hr/>");

        html += this.tab.row("DB Server:&nbsp;", birdhouse_edit_field(id="set_db_server", field="server:database_server", type="input", options="", data_type="string") );
        html += this.tab.row("DB Type:&nbsp;", birdhouse_edit_field(id="set_db_type", field="server:database_type", type="select", options="json,couch,both", data_type="string") );
        html += this.tab.row("DB Link:","<a href='"+link+"' target='_blank'>"+link+"</a>");
        html += this.tab.row("<hr/>");

        html += this.tab.row("HTTP Server:&nbsp;", birdhouse_edit_field(id="set_ip4", field="server:ip4_address", type="input", options="true,false", data_type="string") );
        html += this.tab.row("HTTP Port:&nbsp;", birdhouse_edit_field(id="set_port", field="server:port", type="input", options="true,false", data_type="integer") );
        html += this.tab.row("Videostream Srv:&nbsp;", birdhouse_edit_field(id="set_ip4_video", field="server:ip4_stream_video", type="input", options="true,false", data_type="string") );
        html += this.tab.row("Videostream Port:&nbsp;", birdhouse_edit_field(id="set_ip4_video_port", field="server:port_video", type="input", data_type="integer") );
        html += this.tab.row("Audiostream Srv:&nbsp;", birdhouse_edit_field(id="set_ip4_audio", field="server:ip4_stream_audio", type="input", options="true,false", data_type="string") );
        html += this.tab.row("Deny admin from IP4:&nbsp;", birdhouse_edit_field(id="set_ip4_deny", field="server:ip4_admin_deny", type="input", options="true,false", data_type="json") );
        html += this.tab.row("<hr>");

        html += this.tab.row("", birdhouse_edit_save("set_main","set_db_server:set_db_type:set_weather_location:set_initial_setup:set_language:set_timezone:set_title:set_backup:set_preview:set_rpi:set_ip4:set_port:set_ip4_audio:set_ip4_video:set_ip4_deny:set_ip4_video_port") );
        html += this.tab.row("&nbsp;");
        html += this.tab.end();
        return html;
    }

	this.api_calls = function () {
	    var api_call       = "";
        var cameras         = app_data["DATA"]["devices"]["cameras"];
        var button_style    = "background-color:lightgray;color:black;width:90px;margin:3px;";
        var html_entry = this.tab.start();

        api_call    = "<button onclick='window.open(\"" + RESTurl + "api/list/\",\"_blank\");' style='"+button_style+"';>REST API</button>";
        api_call   += "<button onclick='window.open(\"" + RESTurl + "api/INDEX/\",\"_blank\");' style='"+button_style+"';>INDEX</button>";
        html_entry += this.tab.row("API Calls", api_call);

        api_call    = "<button onclick='birdhouse_forceBackup();' style='"+button_style+"';>Force Backup</button>";
        api_call   += "<button onclick='birdhouse_recreateImageConfig();' style='"+button_style+"';>NewImgCfg</button>";
        api_call   += "<button onclick='appFW.requestAPI(\"POST\",[\"check-timeout\"],\"\",\"\",\"\");' style='"+button_style+"';>Timeout</button>";
        html_entry += this.tab.row("API Commands", api_call);

	    for (let camera in cameras) {
	        api_call  = "<button onclick='window.open(\"" + RESTurl + "api/TODAY/"+camera+"/\",\"_blank\");' style='"+button_style+"';>Today "+camera.toUpperCase()+"</button>";
	        api_call += "<button onclick='window.open(\"" + RESTurl + "api/TODAY_COMPLETE/"+camera+"/\",\"_blank\");' style='"+button_style+"';>Compl. "+camera.toUpperCase()+"</button>";
	        api_call += "<button onclick='window.open(\"" + RESTurl + "api/ARCHIVE/"+camera+"/\",\"_blank\");' style='"+button_style+"';>Archive "+camera.toUpperCase()+"</button>";
            html_entry += this.tab.row("API "+camera, api_call);
        }
        html_entry += this.tab.end();
        return html_entry;
	}

	this.app_information = function () {
		var html_entry = this.tab.start();
		html_entry += this.tab.row("App:",	"<a href='/app/index.html?INFO' target='_blank'>"+ app_title + "</a>");
		html_entry += this.tab.row("Versions:",
						"App: " 		+ app_version + "<br/>" +
						"API: " 		+ app_api_version + "<br/>" +
						"jcMsg: " 		+ appMsg.appVersion + "<br/>" +
						"jcApp: "		+ appFW.appVersion);
		html_entry += this.tab.row("Source:","<a href='https://github.com/jc-prg/birdhouse-cam/' target='_blank'>https://github.com/jc-prg/birdhouse-cam/</a>");
		html_entry += this.tab.row("&nbsp;");
		html_entry += this.tab.end();
        return html_entry;
	}

	this.app_information_detail = function () {
	    var html_entry = "";
        html_entry = this.tab.start();
        html_entry += this.tab.row("Reload Interval:", app_reload_interval + "s");
        html_entry += this.tab.row("Active Camera:&nbsp;", app_active_cam);
        html_entry += this.tab.row("Available Cameras:&nbsp;", app_available_cameras.length);
        html_entry += this.tab.row("Active Page:&nbsp;", app_active_page);
        html_entry += this.tab.row("Active Date:&nbsp;", app_active_date);
        html_entry += this.tab.row("Unique stream URL:&nbsp;", app_unique_stream_url);
        html_entry += this.tab.row("Unique stream ID:&nbsp;",	app_unique_stream_id);
        html_entry += this.tab.end();
        return html_entry;
	}

	this.display_information = function () {
	    var html_entry = "";
        html_entry = this.tab.start();
        html_entry += this.tab.row("Window:", document.body.clientWidth + "x" + document.body.clientHeight );
        html_entry += this.tab.row("Position:", "<div id='scrollPosition'>0 px</div>" );
        html_entry += this.tab.row("Format:", print_display_definition());
        html_entry += this.tab.row("Browser:", navigator.userAgent);
        html_entry += this.tab.end();
        return html_entry;
    }

	this.server_information = function () {
        var html_entry = this.tab.start();
    	html_entry += this.tab.row("Active Streams:",      "<div id='system_active_streams'>please wait ...</div>");
    	html_entry += this.tab.row("Active Database:",     "<div id='system_info_database'>please wait ...</div>");
    	html_entry += this.tab.row("CPU Temperature:",     "<div id='system_info_cpu_temperature'>please wait ...</div>");
    	html_entry += this.tab.row("CPU Usage:",           "<div id='system_info_cpu_usage'>please wait ...</div>");
    	html_entry += this.tab.row("CPU Usage (Details):", "<div id='system_info_cpu_usage_detail'>please wait ...</div>");
    	html_entry += this.tab.row("Memory Total:",        "<div id='system_info_mem_total'>please wait ...</div>");
    	html_entry += this.tab.row("Memory Used:",         "<div id='system_info_mem_used'>please wait ...</div>");
    	html_entry += this.tab.row("HDD used:",            Math.round(app_data["STATUS"]["system"]["hdd_used"]*10)/10 + " GB");
    	html_entry += this.tab.row("HDD total:",           Math.round(app_data["STATUS"]["system"]["hdd_total"]*10)/10 + " GB");
        html_entry += this.tab.row("&nbsp;");
        html_entry += this.tab.end();
        return html_entry;
	}

	this.device_information = function () {
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



