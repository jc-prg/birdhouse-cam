//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// settings
//--------------------------------------
/* INDEX:

*/
//--------------------------------------

app_settings_active = false;

function birdhouse_settings() {

	var settings = new birdhouseSettings(); 
	settings.toggle(app_settings_active);
	
	if (app_settings_active) {
		html  = "<h1>"+lang("SETTINGS")+"</h1>";

		html += settings.tab_start();	
		html += settings.tab_row("App:",			app_title);
		html += settings.tab_row("Versions:",
						"App: " 		+ app_version + "<br/>" +
						//"API: " 		+ this.data["API"]["version"] + " / " + this.data["API"]["rollout"] + "<br/>" +
						"jcMsg: " 		+ appMsg.appVersion + "<br/>" + 
						"jcApp: "		+ appFW.appVersion);
		html += settings.tab_row("Reload Interval:",		app_reload_interval + "s");

		html += settings.tab_row("&nbsp;","");
		html += settings.tab_row("Active Camera:&nbsp;",	app_active_cam);
		html += settings.tab_row("Available Cameras:&nbsp;",	app_available_cameras.length);
		html += settings.tab_row("Active Page:&nbsp;",	app_active_page);
		html += settings.tab_row("Active Date:&nbsp;",	app_active_date);
		
		html += settings.tab_row("&nbsp;","");
		html += settings.tab_row("Unique stream URL:&nbsp;",	app_unique_stream_url);
		html += settings.tab_row("Unique stream ID:&nbsp;",	app_unique_stream_id);

		html += settings.tab_row("&nbsp;","");
		html += settings.tab_row("Window:", 			document.body.clientWidth + "x" + document.body.clientHeight );
		html += settings.tab_row("Position:",			"<div id='scrollPosition'>0 px</div>" );
		html += settings.tab_end();

		setTextById("setting1", html);
		}
	}
	
	
	
	
function birdhouseSettings (name="Settings") {


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


