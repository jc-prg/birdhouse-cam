//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// settings
//--------------------------------------
/* INDEX:
function birdhouse_app_settings (name="Settings")
	this.create	= function (data)
	this.toggle	= function (active=false)
*/
//--------------------------------------

var app_settings_active = false;
var birdhouse_settings  = new birdhouse_app_settings();

// ------------------------------------

function birdhouse_app_settings (name="Settings") {

	this.create	= function (data) {

        var tab     = new birdhouse_table();
        tab.style_rows["height"] = "27px";
        tab.style_cells["width"] = "40%";

        html  = "<h2>Information: System &amp; App</h2>";
		html += "<hr style='border:1px solid gray;'>"

		html += tab.start();
		html += tab.row("App:",				app_title);
		html += tab.row("Versions:",
						"App: " 		+ app_version + "<br/>" +
						"API: " 		+ app_api_version + "<br/>" +
						"jcMsg: " 		+ appMsg.appVersion + "<br/>" + 
						"jcApp: "		+ appFW.appVersion);

		html += tab.row("Source:","<a href='https://github.com/jc-prg/birdhouse-cam/' target='_blank'>https://github.com/jc-prg/birdhouse-cam/</a>");
		html += tab.row("&nbsp;","");
		html += tab.row("API Call","<button onclick='window.open(\"" + RESTurl + "api/list/\",\"_blank\");' style='background-color:lightgray;color:black;width:100px;';>REST API</button>");
		html += tab.row("&nbsp;","");
		html += tab.row("Reload Interval:", app_reload_interval + "s");
		html += tab.row("&nbsp;","");
		html += tab.row("Active Camera:&nbsp;", app_active_cam);
		html += tab.row("Available Cameras:&nbsp;", app_available_cameras.length);
		html += tab.row("Active Page:&nbsp;", app_active_page);
		html += tab.row("Active Date:&nbsp;", app_active_date);
		html += tab.row("&nbsp;","");
		html += tab.row("Unique stream URL:&nbsp;", app_unique_stream_url);
		html += tab.row("Unique stream ID:&nbsp;",	app_unique_stream_id);

		html += tab.row("&nbsp;","");
		html += tab.row("Window:", document.body.clientWidth + "x" + document.body.clientHeight );
		html += tab.row("Position:", "<div id='scrollPosition'>0 px</div>" );
		html += tab.end();

		setTextById("setting1", html);

        html  = "<h2>"+lang("SETTINGS")+": Server</h2>";
		html += "<hr style='border:1px solid gray;'>"

		html += tab.start();
		html += tab.row("Title:&nbsp;", birdhouse_edit_field(id="set_title", field="title", type="input") );
		html += tab.row("Backup-Time:&nbsp;", birdhouse_edit_field(id="set_backup", field="backup:time", type="input") );
		html += tab.row("Backup-Preview:&nbsp;", birdhouse_edit_field(id="set_preview", field="backup:preview", type="input") );
		html += tab.row("RPi Active:&nbsp;", birdhouse_edit_field(id="set_rpi", field="server:rpi_active", type="select", options="true,false", data_type="boolean") );
        html += tab.row("<hr>");
		html += tab.row("HTTP IP4 Address:&nbsp;", birdhouse_edit_field(id="set_ip4", field="server:ip4_address", type="input", options="true,false", data_type="string") );
		html += tab.row("HTTP Port:&nbsp;", birdhouse_edit_field(id="set_port", field="server:port", type="input", options="true,false", data_type="integer") );
		html += tab.row("Videostream IP4:&nbsp;", birdhouse_edit_field(id="set_ip4_video", field="server:ip4_stream_video", type="input", options="true,false", data_type="string") );
		html += tab.row("Videostream Port:&nbsp;", birdhouse_edit_field(id="set_ip4_video_port", field="server:port_video", type="input", data_type="integer") );
		html += tab.row("Audiostream IP4:&nbsp;", birdhouse_edit_field(id="set_ip4_audio", field="server:ip4_stream_audio", type="input", options="true,false", data_type="string") );
		html += tab.row("Deny admin from IP4:&nbsp;", birdhouse_edit_field(id="set_ip4_deny", field="server:ip4_admin_deny", type="input", options="true,false", data_type="json") );
        html += tab.row("<hr>");
		html += tab.row("", birdhouse_edit_save("set_main","set_title:set_backup:set_preview:set_rpi:set_ip4:set_port:set_ip4_audio:set_ip4_video:set_ip4_deny:set_ip4_video_port") );
        html += tab.row("&nbsp;");

		setTextById("setting2", html);
        setTextById("setting3", "");

		this.toggle();
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


