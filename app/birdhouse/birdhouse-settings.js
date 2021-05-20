//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// settings
//--------------------------------------
/* INDEX:

*/
//--------------------------------------

var app_settings_active = false;
var birdhouse_settings  = new birdhouse_app_settings();

function birdhouse_app_settings (name="Settings") {

	this.create	= function () {

		html  = "<center><h2>"+lang("SETTINGS")+"</h2></center>";	
		setTextById("setting1", html);

		html  = this.tab_start();	
		html += this.tab_row("App:",			app_title);
		html += this.tab_row("Versions:",
						"App: " 		+ app_version + "<br/>" +
						//"API: " 		+ this.data["API"]["version"] + " / " + this.data["API"]["rollout"] + "<br/>" +
						"jcMsg: " 		+ appMsg.appVersion + "<br/>" + 
						"jcApp: "		+ appFW.appVersion);
		html += this.tab_row("Reload Interval:",		app_reload_interval + "s");

		html += this.tab_row("&nbsp;","");
		html += this.tab_row("Active Camera:&nbsp;",	app_active_cam);
		html += this.tab_row("Available Cameras:&nbsp;",	app_available_cameras.length);
		html += this.tab_row("Active Page:&nbsp;",	app_active_page);
		html += this.tab_row("Active Date:&nbsp;",	app_active_date);
		
		html += this.tab_row("&nbsp;","");
		html += this.tab_row("Unique stream URL:&nbsp;",	app_unique_stream_url);
		html += this.tab_row("Unique stream ID:&nbsp;",	app_unique_stream_id);

		html += this.tab_row("&nbsp;","");
		html += this.tab_row("Window:", 			document.body.clientWidth + "x" + document.body.clientHeight );
		html += this.tab_row("Position:",			"<div id='scrollPosition'>0 px</div>" );
		html += this.tab_end();
	
		setTextById("setting2", html);
		
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


