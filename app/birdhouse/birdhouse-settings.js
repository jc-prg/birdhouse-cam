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

function birdhouse_edit_field(id, field, type="input", options="") {
    var fields = field.split(":");
    var data   = "";
    var html   = "";

    if (fields.length == 1) { data = app_data["DATA"][fields[0]]; }
    else if (fields.length == 2) { data = app_data["DATA"][fields[0]][fields[1]]; }
    else if (fields.length == 3) { data = app_data["DATA"][fields[0]][fields[1]][fields[2]]; }
    else if (fields.length == 4) { data = app_data["DATA"][fields[0]][fields[1]][fields[2]][fields[3]]; }

    if (type == "input") { html += "<input id='"+id+"' value='"+data+"'>"; }
    else if (type == "select") {
        var values = options.split(",");
        html += "<select id='"+id+"'>";
        for (var i=0;i<values.length;i++) {
            data_str = data.toString();
            if (data_str == values[i])  { html += "<option selected='selected'>"+values[i]+"</option>"; }
            else                        { html += "<option>"+values[i]+"</option>"; }
        }
        html += "</select>";
    }
    html += "<input id='"+id+"_data' style='display:none' value='"+field+"'>\n";
    return html;
}

function birdhouse_edit_save(id, id_list, text="") {
    var ids = id_list.split(":");
    var html = "<button onclick='birdhouse_edit_send(\""+id_list+"\");' style='background:gray;width:100px;'>"+lang("SAVE")+"</button>";
    return html;
}

function birdhouse_edit_send(id_list) {
    var ids = id_list.split(":");
    var info = "";
    for (var i=0;i<ids.length;i++) {
        info += document.getElementById(ids[i]+"_data").value + "==";
        info += encodeURIComponent(document.getElementById(ids[i]).value);
        info += "/";
    }
    appFW.requestAPI('POST',[ "edit_presets", info ],"",birdhouse_edit_done,"","");
}

function birdhouse_edit_done(data) {
    alert("Done");
}

// ------------------------------------

function birdhouse_app_settings (name="Settings") {

	this.create	= function (data) {
        html  = "<h2>"+lang("SETTINGS")+": System &amp; App</h2>";
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

		setTextById("setting1", html);

        html  = "<h2>"+lang("SETTINGS")+": Devices &amp; Data</h2>";
		html += "<hr style='border:1px solid gray;'>"

		html += this.tab_start();
		html += this.tab_row("Title:&nbsp;", birdhouse_edit_field(id="set_title", field="title", type="input") );
		html += this.tab_row("Backup-Time:&nbsp;", birdhouse_edit_field(id="set_backup", field="backup:time", type="input") );
		html += this.tab_row("Backup-Preview:&nbsp;", birdhouse_edit_field(id="set_preview", field="backup:preview", type="input") );
		html += this.tab_row("RPi Active:&nbsp;", birdhouse_edit_field(id="set_rpi", field="server:rpi_active", type="select", options="true,false") );
		html += this.tab_row("", "<br/>"+birdhouse_edit_save("set_main","set_backup:set_preview:set_rpi") );

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

		for (let mic in birdhouseMicrophones) {
		    var host = location.host.split(":");
		    var URL = "http://"+host[0]+":"+birdhouseMicrophones[mic]["port"]+"/";
    		html += this.tab_start();
			html += this.tab_row("<i>Status &quot;"+mic+"&quot;</i>","");
			html += this.tab_row("&nbsp;-&nbsp;active:", birdhouseMicrophones[mic]["active"]);
			html += this.tab_row("&nbsp;-&nbsp;type:", birdhouseMicrophones[mic]["type"]);
			html += this.tab_row("&nbsp;-&nbsp;stream:", "<a href='"+URL+"' target='_blank'>" + URL + "</a>");
    		html += this.tab_row("&nbsp;","");
			html += this.tab_end();
    		}

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


