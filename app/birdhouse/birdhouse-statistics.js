/*
* cache statistic data to not every time reload statistic data
*/
var birdhouse_STATISTICS_cache = {};
var birdhouse_STATISTICS_selected = "";
var birdhouse_STATISTICS_day = "today";

/*
* create view with server and usage statistics
*
* @param (string) title: title to be displayed
* @param (dict) data: API response for list specific request
*/
function birdhouse_STATISTICS(title, data) {
    birdhouse_STATISTICS_cache = data;
    var date        = birdhouse_STATISTICS_day;
    var statistics  = data["DATA"]["data"]["entries"][date];
    var timeframes  = data["DATA"]["data"]["entries"];
    var html        = "";

    if (birdhouse_STATISTICS_selected == "") { birdhouse_STATISTICS_selected == "hdd-overview"; }

    // container for date labels ...

    // container for the first diagram
    var link = "birdhouse_STATISTICS_load(chart='hdd-overview', 'chart_container_1');";
    html += "<div class='statistic-container label'>";
    html += "<div class=\"statistic-label\" onclick=\""+link+"\">&nbsp;Overview&nbsp;</div>";
    Object.keys(statistics).sort().forEach(key => {
        var link = "birdhouse_STATISTICS_load(chart='"+key+"', 'chart_container_1');";
        html += "<div class=\"statistic-label\" onclick=\""+link+"\">&nbsp;"+key.toUpperCase()+"&nbsp;</div>";
        });
    html += "</div>";
    html += "<div id='chart_container_1' class='statistic-container'></div>";

    // container for the second diagram
    var link = "birdhouse_STATISTICS_load(chart='hdd-overview', 'chart_container_2');";
    html += "<div class='statistic-container label'>";
    html += "<div class=\"statistic-label\" onclick=\""+link+"\">&nbsp;Overview&nbsp;</div>";
    Object.keys(statistics).sort().forEach(key => {
        var link = "birdhouse_STATISTICS_load(chart='"+key+"', 'chart_container_2');";
        html += "<div class=\"statistic-label\" onclick=\""+link+"\">&nbsp;"+key.toUpperCase()+"&nbsp;</div>";
        });
    html += "</div>";
    html += "<div id='chart_container_2' class='statistic-container'>&nbsp;</div>";

    // write and load overview into the first container, 2nd stays empty at first
    appSettings.write(1, lang("STATISTICS"), html);
    setTextById("chart_container_1", birdhouse_printStatistic(title, data, date, chart="hdd-overview", groups=false));
    }

/*
* load statistics into container build in birdhouse_STATISTICS
*
* @param (string) chart: chart key
* @param (string) container: container ID
*/
function birdhouse_STATISTICS_load(chart, container) {
        date = birdhouse_STATISTICS_day;
        setTextById(container, birdhouse_printStatistic(title, birdhouse_STATISTICS_cache, date, chart=chart, groups=false));
        }

/*
* create view with server and usage statistics
*
* @param (string) title: title to be displayed
* @param (dict) data: API response for list specific request
*/
function birdhouse_printStatistic(title, data, date, chart_type="all", groups=true) {
	var html          = "";
	var admin         = data["STATUS"]["admin_allowed"];
	var statistics    = data["DATA"]["data"]["entries"][date];
	var camera_status = data["STATUS"]["devices"]["cameras"];
	var open_category = [];
	var system_data   = app_data["STATUS"]["system"];
	var tab           = new birdhouse_table();
	tab.style_cells["vertical-align"]   = "top";
	tab.style_cells["padding"]          = "3px";

    this.print_line_chart = function(key, open, groups) {
        var html   = "";
        var info   = "";
        var status = camera_status[key];
        var chart = "&nbsp;<br/>";
        chart += birdhouseChart_create(label="", titles=statistics[key]["titles"],
                                       data=statistics[key]["data"],
                                       type="line",
                                       sort_keys=true,
                                       id="statisticsChart_"+key,
                                       size={"height": "250px", "width": "100%"});
        chart += "<br/>&nbsp;<br/>";

        if (groups) { html  += birdhouse_OtherGroup( "chart_"+key, lang("TODAY") + " " + key.toUpperCase() + " " + info, chart, open ); }
        else        { html  += chart; }
        return html;
        }

    if (chart_type == "all" || chart_type == "hdd-overview") {
        // resource usage
        pie_data = { "titles": [], "data": []}
        pie_data["titles"].push("Data");
        pie_data["data"].push(system_data["hdd_data"] - system_data["hdd_archive"]);
        pie_data["titles"].push("Archive");
        pie_data["data"].push(system_data["hdd_archive"]);
        pie_data["titles"].push("System");
        pie_data["data"].push(system_data["hdd_used"] - system_data["hdd_data"]);
        pie_data["titles"].push("Available");
        pie_data["data"].push(system_data["hdd_total"] - system_data["hdd_used"]);

        var chart = birdhouseChart_create(label="HDD Usage", titles=pie_data["titles"], data=pie_data["data"], type="pie",
                                          sort_keys=false, id="hdd_pie", size={"height": "270px", "width":"270px"},
                                          set_colors=["red", "orange", "darkblue", "green"],
                                          set_menu="right");

        var info  = "<br/>&nbsp;<br/>";
        info += "Max parallel streams: " + statistics["streams"]["info"]["max"] + "<br/>&nbsp;<br/>";
        info += "Total viewing time: " + statistics["streams"]["info"]["views"] + "min<br/>&nbsp;";

        var html_entry = tab.start();
        html_entry    += tab.row(chart, info);
        html_entry    += tab.end();

        if (groups) { html  += birdhouse_OtherGroup( "chart_hdd_pie", lang("TODAY") + " HDD Usage", html_entry, true ); }
        else        { html  += html_entry; }
        }

    if (chart_type == "all") {
        // statistics of the current day
        Object.keys(statistics).sort().forEach((key) => {
            if (open_category.indexOf(key) > -1) { var open = true; }
            else                                 { var open = false; }
            html += this.print_line_chart(key, open, groups);
            });
        }
    else if (statistics[chart_type]) {
        var key = chart_type;
        if (open_category.indexOf(key) > -1) { var open = true; }
        else                                 { var open = false; }
        html += this.print_line_chart(key, open, groups);
        }

	//birdhouse_frameHeader(lang("STATISTICS"));
	//setTextById(app_frame_content, html);
    return html;
}


app_scripts_loaded += 1;
