//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// main charts and analysis
//--------------------------------------
/* INDEX:

*/
//--------------------------------------

var chartJS_loaded = false;
var chartJS_URL    = 'https://cdn.jsdelivr.net/npm/chart.js';
var chartJS_config = {};
var chartJS_chart  = undefined;
var chartJS_defaultColors = [	"coral","cornflowblue", "cadetblue", 
				"crimson", "darkblue", "darkgoldenrod", "darkgreen", "darkmagenta",
				"darkorange", "darksalmon", "darkviolet", "dodgerblue", "firebrick",
				"forestgreen", "goldenrod", "greenyellow", "hotpink", "indigo"
				];
var chartJS_darkColors = [
				"aquamarine", "chartreuse","coral","cornflowblue", "cadetblue", 
				"crimson", "darkblue", "darkgoldenrod", "darkgreen", "darkmagenta",
				"darkorange", "darksalmon", "darkviolet", "dodgerblue", "firebrick",
				"forestgreen", "goldenrod", "greenyellow", "hotpink", "indigo"
				];

//-----------------------------------------
// load chart.js
//-----------------------------------------


function load_chartJS() {
	if (chartJS_loaded == false) {
		chartJS_script       = document.createElement('script');
		chartJS_script.async = false;
		chartJS_script.src   = chartJS_URL;
		chartJS_script.type  = 'text/javascript';
		(document.getElementsByTagName('HEAD')[0]||document.body).appendChild(chartJS_script);
		}
	}


//-----------------------------------------
// load chart.js
//-----------------------------------------

function birdhouseChart_create (title, data, type="line", sort_keys=true) {

      	// https://www.chartjs.org/docs/latest/samples/line/line.html
      	// data = { "label1" : [1, 2, 3], "label2" : [1, 2, 3] };

	var html 	= "";
      	var data_keys	= Object.keys(data);
      	if (sort_keys)	{ data_keys = data_keys.sort(); }
      	var data_rows	= data[data_keys[0]].length;		// startet with only 1 line per chart!

      	var data_labels = "";
      	var data_data   = "";
      	var data_sets   = [];
      	
      	for (var x=0;x<data_rows;x++) {
	      	var data_var = [];
	      	for (var i=0;i<data_keys.length;i++) {
        		var key       = data_keys[i];
        		data_var.push(data[key][x]);
        		}
        	if (Array.isArray(title)) { myTitle = title[x]; }
        	else                      { myTitle = title; }
        	
        	data_sets.push({
        		label : (x+1)+": "+myTitle,
      			backgroundColor : chartJS_defaultColors[x],
      			borderColor : chartJS_defaultColors[x],
      			borderWidth : 2,
      			pointRadius : 0,
      			data : data_var        		
        		});
        	}
        		
	load_chartJS();

      	html += "<div><canvas id=\"birdhouseChart\" style=\"height:300;width:100%;\"></canvas></div>\n";
      	
      	const chart_labels = data_keys;
      	const chart_data   = {
      		labels   : chart_labels,
      		datasets : data_sets
      		};
      	chartJS_config = {
      		type : type,
      		data : chart_data,
      		options : {
			responsive: true,
  	    		plugins: { 
  	    			legend: {
  				position: "right",
  				align: "middle",
  				labels : {
	  			    boxHeight : 12,
	  			    boxWidth : 12,
	  			    }
				}}
      			}
      		};
      		
      	setTimeout(function(){
      		chartJS_chart = new Chart(document.getElementById('birdhouseChart'), chartJS_config );
		}, 1000);

	return html;
	}


