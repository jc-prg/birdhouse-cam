//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// main charts and analysis
//--------------------------------------

var chartJS_loaded = false;
var chartJS_URL    = 'https://cdn.jsdelivr.net/npm/chart.js';
var chartJS_config = {};
var chartJS_chart  = undefined;
var chartJS_defaultColors = ["coral","cornflowerblue", "cadetblue",
				"crimson", "darkblue", "darkgoldenrod", "darkgreen", "darkmagenta",
				"darkorange", "darksalmon", "darkviolet", "dodgerblue", "firebrick",
				"forestgreen", "goldenrod", "greenyellow", "hotpink", "indigo"
				];
var chartJS_darkColors = ["red", "aquamarine", "chartreuse", "coral", "cadetblue",
				"crimson", "darkblue", "goldenrod", "green", "magenta",
				"orange", "salmon", "violet", "dodgerblue", "firebrick",
				"forestgreen", "goldenrod", "greenyellow", "hotpink", "indigo"
				];

/*
* load javascript file for chart rendering if not done before
* see https://www.chartjs.org/docs/latest/ for details
*/
function birdhouse_loadChartJS() {

	if (chartJS_loaded == false) {
		chartJS_script = document.createElement('script');
		if (chartJS_script) {

            chartJS_script.async = false;
            chartJS_script.src   = chartJS_URL;
            chartJS_script.type  = 'text/javascript';
            (document.getElementsByTagName('HEAD')[0]||document.body).appendChild(chartJS_script);
            setTimeout(function() {
                if (typeof Chart === 'function') { chartJS_loaded = true; }
            }, 1000);
            }
		}
	}

/*
* render a specific chart, data have to be prepared in the required format
* see https://www.chartjs.org/docs/latest/samples/line/line.html for details how to create line charts
*
* @param (string) label: dataset name for pie charts
* @param (string) title: title of the chart
* @param (dict) data: prepared chart data, see documentation of chartjs.org
* @param (string) type: type of chart, see documentation of chartjs.org
* @param (boolean) sort_keys: define if keys/labels should be sorted
* @param (string) id: id of div element
* @param (dict) size: possibility to overwrite size of chart, e.g., {"height": "100px", "width": "90%"}
*/
function birdhouseChart_create(label, titles, data, type="line", sort_keys=true, id="birdhouseChart", size="", set_colors=[], set_menu="bottom") {

    // https://www.chartjs.org/docs/latest/samples/line/line.html
    // data = { "label1" : [1, 2, 3], "label2" : [1, 2, 3] };

	var html 	        = "";
    var html_no_entries = "<center>&nbsp;<br/>"+lang("NO_ENTRIES")+"<br/>&nbsp;<br/>&nbsp;<br/>&nbsp;</center>";
	var canvas_size     = {"height": "unset", "width": "unset"};
    var data_keys	    = Object.keys(data);
    if (sort_keys)	    { data_keys = data_keys.sort(); }

	if (data == undefined || data == {} || data_keys.length == 0) {
	    html += html_no_entries;
	    return html;
	}
    var data_rows	= data[data_keys[0]].length;		// startet with only 1 line per chart!
    var data_labels = "";
    var data_data   = "";
    var data_sets   = [];
	var colors      = [];

    if (set_colors != [])        { colors = set_colors;            border_pie = "white"; }
	else if (appTheme == "dark") { colors = chartJS_darkColors;    border_pie = "white"; }
	else                         { colors = chartJS_defaultColors; border_pie = "white"; }

    if (type == "line") {
        for (var x=0;x<data_rows;x++) {
            var data_var = [];
            for (var i=0;i<data_keys.length;i++) {
                var key       = data_keys[i];
                data_var.push(data[key][x]);
                }
            if (Array.isArray(titles)) { myTitle = titles[x]; }
            else                      { myTitle = titles; }

            data_sets.push({
                label : (x+1)+": "+myTitle,
                backgroundColor : colors[x],
                borderColor : colors[x],
                borderWidth : 1,
                pointRadius : 0.5,
                data : data_var
                });
            }
        }
    else if (type == "pie") {
        data_keys = titles;
        data_sets = [{
            label: label,
            data: data,
            backgroundColor : colors,
            borderColor: border_pie,
            borderWidth: 1,
            hoverOffset: 40
            }];
        }
    else {
        console.error("birdhouseChart_create: Doesn't support chart type '" + type + "'.");
        }

    var canvas_style = "";
    Object.keys(size).forEach((key)        => { canvas_size[key] = size[key]; });
    Object.keys(canvas_size).forEach((key) => { canvas_style += key+":"+canvas_size[key]+";"; });
    html += "<div style=\""+canvas_style+"\"><canvas id=\""+id+"\" style=\""+canvas_style+"\"></canvas></div>\n";


    const chart_labels = data_keys;
    const chart_data   = {
        labels   : chart_labels,
        datasets : data_sets
        };

    if (chartJS_config == undefined) { chartJS_config = {}; }
    chartJS_config[id] = {
        type : type,
        data : chart_data,
        options : {
            responsive: true,
            plugins: {
                legend: {
                    position: set_menu,
                    align: "left",
                    labels : {
                        boxHeight : 12,
                        boxWidth : 12,
                        }
                    }
                }
            }
        };
    if (label != "") {
        //chartJS_config[id].options.plugins.title = {text: label, display: true}
    }
    setTimeout(function() {
        chartJS_chart = new Chart(document.getElementById(id), chartJS_config[id] );
        }, 1000 );
	return html;
	}


app_scripts_loaded += 1;