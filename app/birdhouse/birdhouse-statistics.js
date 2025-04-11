/*
* cache statistic data to not every time reload statistic data
*/
var birdhouse_STATISTICS_cache = {};
var birdhouse_STATISTICS_selected_1 = "overview";
var birdhouse_STATISTICS_selected_2 = "";
var birdhouse_STATISTICS_day_1 = "today";
var birdhouse_STATISTICS_day_2 = "today";
var birdhouse_STATISTICS_labels = {"day": [], "charts": ["overview"]}

/*
* create view with server and usage statistics
*
* @param (string) title: title to be displayed
* @param (dict) data: API response for list specific request
*/
function birdhouse_STATISTICS(title, data) {
    birdhouse_STATISTICS_cache = data;
    var link        = "";
    var date        = birdhouse_STATISTICS_day_1;
    var statistics  = data["DATA"]["data"]["entries"][date];
    var timeframes  = data["DATA"]["data"]["entries"];
    var html        = "";

    this.create_container = function(chart_id) {
        var html    = "";
        var link    = "birdhouse_STATISTICS_click('"+chart_id+"', 'overview', '');";
        html += "<div class='statistic-container label'>";
        html += "<div id='label_"+chart_id+"_overview' class=\"statistic-label\" onclick=\""+link+"\">&nbsp;Overview&nbsp;</div>";
        Object.keys(statistics).sort().forEach(key => {
            birdhouse_STATISTICS_labels["charts"].push(key);
            link    = "birdhouse_STATISTICS_click('"+chart_id+"', '"+key+"', '');";
            html += "<div id='label_"+chart_id+"_"+key+"' class=\"statistic-label\" onclick=\""+link+"\">&nbsp;"+key.toUpperCase()+"&nbsp;</div>";
            });
        Object.keys(timeframes).forEach(key => {
            birdhouse_STATISTICS_labels["day"].push(key);
            link    = "birdhouse_STATISTICS_click('"+chart_id+"', '', '"+key+"');";
            html += "<div id='label_"+chart_id+"_"+key+"' class=\"statistic-label\" onclick=\""+link+"\" style=\"background:darkgreen;color:white;\">&nbsp;"+key.toUpperCase()+"&nbsp;</div>";
            });
        html += "</div>";
        html += "<div id='chart_container_"+chart_id+"' class='statistic-container'></div>";
        return html;
        }

    // write and load overview into the first container, 2nd stays empty at first
    html += this.create_container("1");
    html += this.create_container("2");
    appSettings.write(1, lang("STATISTICS"), html);
    birdhouse_STATISTICS_click("1");
    }

/*
* load statistics into container build in birdhouse_STATISTICS and add a glow to selected labels
*
* @param (string) chart_id: chart_id
* @param (string) select: key for chart to be loaded
* @param (string) date: date_key for chart to be loaded (today, yesterday, 3days)
*/
function birdhouse_STATISTICS_click(chart_id, select="", date="") {
    if (date != ""   && chart_id == "1")   { birdhouse_STATISTICS_day_1 = date; }
    if (date != ""   && chart_id == "2")   { birdhouse_STATISTICS_day_2 = date; }
    if (select != "" && chart_id == "1")   { birdhouse_STATISTICS_selected_1 = select; }
    if (select != "" && chart_id == "2")   { birdhouse_STATISTICS_selected_2 = select; }

    // remove all glows
    for (var i=0;i<birdhouse_STATISTICS_labels["day"].length;i++) {
        var label = "label_" + chart_id + "_" + birdhouse_STATISTICS_labels["day"][i];
        if (document.getElementById(label)) { document.getElementById(label).className = "statistic-label"; }
        }
    for (var i=0;i<birdhouse_STATISTICS_labels["charts"].length;i++) {
        var label = "label_" + chart_id + "_" + birdhouse_STATISTICS_labels["charts"][i];
        if (document.getElementById(label)) { document.getElementById(label).className = "statistic-label"; }
        }

    // add glows for selected entries
    if (chart_id == "1")   {
        label_select = "label_1_"+birdhouse_STATISTICS_selected_1;
        label_day    = "label_1_"+birdhouse_STATISTICS_day_1;
        }
    if (chart_id == "2")   {
        label_select = "label_2_"+birdhouse_STATISTICS_selected_2;
        label_day    = "label_2_"+birdhouse_STATISTICS_day_2;
        }
    if (document.getElementById(label_select)) { document.getElementById(label_select).className = "statistic-label glow"; }
    if (document.getElementById(label_day))    { document.getElementById(label_day).className    = "statistic-label glow"; }

    // print charts
    var chart_html = birdhouse_printStatistic("",
                        birdhouse_STATISTICS_cache,
                        eval("birdhouse_STATISTICS_day_"+chart_id),
                        eval("birdhouse_STATISTICS_selected_"+chart_id),
                        groups=false, chart_id
                        );
    setTextById("chart_container_" + chart_id, chart_html);
    }

/*
* create view with server and usage statistics
*
* @param (string) title: title to be displayed
* @param (dict) data: API response for list specific request
*/
function birdhouse_printStatistic(title, data, date, chart_type="all", groups=true, id=0) {
	var html          = "";
	var admin         = data["STATUS"]["admin_allowed"];
	var statistics    = data["DATA"]["data"]["entries"][date];
	var camera_status = data["STATUS"]["devices"]["cameras"];
	var open_category = [];
	var system_data   = app_data["STATUS"]["system"];
	var tab           = new birdhouse_table();
	tab.style_cells["vertical-align"]   = "top";
	tab.style_cells["padding"]          = "3px";

    this.print_line_chart = function(chart_id, key, open, groups) {
        var html   = "";
        var info   = "";
        var status = camera_status[key];
        var chart = "&nbsp;<br/>";
        chart += birdhouseChart_create(label="", titles=statistics[key]["titles"],
                                       data=statistics[key]["data"],
                                       type="line",
                                       sort_keys=false,
                                       id="statisticsChart_"+key+"_"+chart_id,
                                       size={"height": "250px", "width": "100%"},
                                       set_colors=chartJS_darkColors);
        chart += "<br/>&nbsp;<br/>";

        if (groups) { html  += birdhouse_OtherGroup( "chart_"+key, lang("TODAY") + " " + key.toUpperCase() + " " + info, chart, open ); }
        else        { html  += chart; }
        return html;
        }

    if (chart_type == "all" || chart_type == "overview") {
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
                                          sort_keys=false, id="hdd_pie_"+id, size={"height": "270px", "width":"270px"},
                                          set_colors=chartJS_hddPieChart,
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
            html += this.print_line_chart(id, key, open, groups);
            });
        }
    else if (statistics[chart_type]) {
        var key = chart_type;
        if (open_category.indexOf(key) > -1) { var open = true; }
        else                                 { var open = false; }
        html += this.print_line_chart(id, key, open, groups);
        }
    return html;
}


app_scripts_loaded += 1;
