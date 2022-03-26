//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// settings
//--------------------------------------
/* INDEX:
function birdhouse_app_settings (name="Settings")
	this.create	= function (data)
	this.toggle	= function (active=false)
	this.tab_start	= function ()
	this.tab_row	= function (td1,td2)
	this.tab_end	= function ()
*/
//--------------------------------------

var app_settings_active = false;
var birdhouse_settings  = new birdhouse_app_settings();

function birdhouse_app_settings (name="Settings") {

	this.create	= function (data) {
		html  = "<center><h2>"+lang("SETTINGS")+"</h2></center>";
		setTextById("setting1", html);

        html = "<h3>System &amp; App</h3>";
		html += "<hr style='border:1px solid gray;'>"

		html += this.tab_start();
		html += this.tab_row("App:",				app_title);
		html += this.tab_row("Versions:",
						"App: " 		+ app_version + "<br/>" +
						"API: " 		+ app_api_version + "<br/>" +
						"jcMsg: " 		+ appMsg.appVersion + "<br/>" + 
						"jcApp: "		+ appFW.appVersion);

		html += this.tab_row("Source:","<a href='https://github.com/jc-prg/birdhouse-cam/' target='_blank'>https://github.com/jc-prg/birdhouse-cam/</a>");
		html += this.tab_row("&nbsp;","");
		html += this.tab_row("API Call","<button onclick='window.open(\"" + RESTurl + "api/list/\",\"_blank\");' style='background-color:lightgray;color:black;width:100px;';>REST API</button>");
		html += this.tab_row("&nbsp;","");
		html += this.tab_row("Reload Interval:", app_reload_interval + "s");
		html += this.tab_row("&nbsp;","");
		html += this.tab_row("Active Camera:&nbsp;", app_active_cam);
		html += this.tab_row("Available Cameras:&nbsp;", app_available_cameras.length);
		html += this.tab_row("Active Page:&nbsp;", app_active_page);
		html += this.tab_row("Active Date:&nbsp;", app_active_date);
		html += this.tab_row("&nbsp;","");
		html += this.tab_row("Unique stream URL:&nbsp;", app_unique_stream_url);
		html += this.tab_row("Unique stream ID:&nbsp;",	app_unique_stream_id);

		html += this.tab_row("&nbsp;","");
		html += this.tab_row("Window:", document.body.clientWidth + "x" + document.body.clientHeight );
		html += this.tab_row("Position:", "<div id='scrollPosition'>0 px</div>" );
		html += this.tab_end();

		setTextById("setting2", html);

		html = "<h3>Devices &amp; Data</h3>";
		html += "<hr style='border:1px solid gray;'>"

		html += this.tab_start();
		html += this.tab_row("Title:&nbsp;",app_data["DATA"]["title"]);
		html += this.tab_row("Backup-Time:&nbsp;",app_data["DATA"]["backup_time"]);
		html += this.tab_row("Backup-Preview:&nbsp;",app_data["DATA"]["preview_backup"]);
		html += this.tab_row("RPi Active:&nbsp;",app_data["DATA"]["rpi_active"]);

		html += this.tab_row("&nbsp;","");
		for (let camera in birdhouseCameras) {
    		html += this.tab_start();
			html += this.tab_row("<i>Status &quot;"+camera+"&quot;</i>","");
			html += this.tab_row("&nbsp;-&nbsp;running:", birdhouseCameras[camera]["status"]["running"]);
			html += this.tab_row("&nbsp;-&nbsp;error/image:", birdhouseCameras[camera]["status"]["error"] + "/" + birdhouseCameras[camera]["status"]["img_error"]);
    		html += this.tab_row("&nbsp;","");
			html += this.tab_end();
			html += "<textarea style='width:95%'>"+JSON.stringify(birdhouseCameras[camera]["status"]["img_msg"])+"</textarea>";
			html += "<br/>&nbsp;<br/>"
    		}

		for (let mic in app_data["DATA"]["microphones"]) {
		    var host = location.host.split(":");
		    var URL = "http://"+host[0]+":"+app_data["DATA"]["microphones"][mic]["port"]+"/";
    		html += this.tab_start();
			html += this.tab_row("<i>Status &quot;"+mic+"&quot;</i>","");
			html += this.tab_row("&nbsp;-&nbsp;active:", app_data["DATA"]["microphones"][mic]["active"]);
			html += this.tab_row("&nbsp;-&nbsp;type:", app_data["DATA"]["microphones"][mic]["type"]);
			html += this.tab_row("&nbsp;-&nbsp;stream:", "<a href='"+URL+"' target='_blank'>" + URL + "</a>");
    		html += this.tab_row("&nbsp;","");
			html += this.tab_end();
    		}

		setTextById("setting3", html);

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

	this.tab_start	= function ()		{ return "<table>"; }
	this.tab_row	= function (td1,td2) 	{ return "<tr><td valign=\"top\">" + td1 + "</td><td>" + td2 + "</td></tr>"; }
	this.tab_end	= function ()		{ return "</table>"; }
	}


