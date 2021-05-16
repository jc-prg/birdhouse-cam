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
	birdhouse_settingsToggle(app_settings_active);
	if (app_settings_active) {
		html = "test";
		setTextById("setting1", html);
		}
	}
	
	
function birdhouse_settingsToggle(active=false) {
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
