//--------------------------------------
// jc://birdhouse/statistics/
//--------------------------------------


/*
* create statistics view for settings
*/
class BirdhouseStatistics {
    constructor(name) {
        this.name = name;

        this.cache = {};
        this.selected_1 = "overview";
        this.selected_2 = "";
        this.day_1 = "today";
        this.day_2 = "today";
        this.labels = {"day": [], "charts": ["overview"]};

        this.tab = new birdhouse_table();
    }

    /*
    * create view with server and usage statistics
    *
    * @param (string) title: title to be displayed
    * @param (dict) data: API response for list specific request
    */
    create (data) {
        this.cache = data;
        let html = "";
        html += this.create_container("1");
        html += this.create_container("2");
        appSettings.write(1, lang("STATISTICS"), html);
        this.click("1");
    }

    /*
    * create container for chart
    */
    create_container (chart_id) {
        let html = "";
        let link = this.name+".click('"+chart_id+"', 'overview', '');";
        let date = this.day_1;
        const statistics  = this.cache["DATA"]["data"]["entries"][date];
        const timeframes  = this.cache["DATA"]["data"]["entries"];

        html += "<div class='statistic-container label'>";
        html += "<div id='label_"+chart_id+"_overview' class=\"statistic-label\" onclick=\""+link+"\">&nbsp;Overview&nbsp;</div>";
        Object.keys(statistics).sort().forEach(key => {
            this.labels["charts"].push(key);
            link    = this.name+".click('"+chart_id+"', '"+key+"', '');";
            html += "<div id='label_"+chart_id+"_"+key+"' class=\"statistic-label\" onclick=\""+link+"\">&nbsp;"+key.toUpperCase()+"&nbsp;</div>";
        });
        Object.keys(timeframes).forEach(key => {
            this.labels["day"].push(key);
            link    = this.name+".click('"+chart_id+"', '', '"+key+"');";
            html += "<div id='label_"+chart_id+"_"+key+"' class=\"statistic-label\" onclick=\""+link+"\" style=\"background:darkgreen;color:white;\">&nbsp;"+key.toUpperCase()+"&nbsp;</div>";
        });
        html += "</div>";
        html += "<div id='chart_container_"+chart_id+"' class='statistic-container'></div>";
        return html;
    }

    /*
    * load statistics into container build in birdhouse_STATISTICS and add a glow to selected labels
    *
    * @param (string) chart_id: chart_id
    * @param (string) select: key for chart to be loaded
    * @param (string) date: date_key for chart to be loaded (today, yesterday, 3days)
    */
    click (chart_id, select="", date="") {
        if (date !== ""   && chart_id === "1")   { this.day_1 = date; }
        if (date !== ""   && chart_id === "2")   { this.day_2 = date; }
        if (select !== "" && chart_id === "1")   { this.selected_1 = select; }
        if (select !== "" && chart_id === "2")   { this.selected_2 = select; }

        // remove all glows
        for (let i=0;i<this.labels["day"].length;i++) {
            let label = "label_" + chart_id + "_" + this.labels["day"][i];
            if (document.getElementById(label)) { document.getElementById(label).className = "statistic-label"; }
        }
        for (let i=0;i<this.labels["charts"].length;i++) {
            let label = "label_" + chart_id + "_" + this.labels["charts"][i];
            if (document.getElementById(label)) { document.getElementById(label).className = "statistic-label"; }
        }

        let label_select, label_day;
        // add glows for selected entries
        if (chart_id === "1")   {
            label_select = "label_1_"+this.selected_1;
            label_day    = "label_1_"+this.day_1;
        }
        if (chart_id === "2")   {
            label_select = "label_2_"+this.selected_2;
            label_day    = "label_2_"+this.day_2;
        }
        if (document.getElementById(label_select)) { document.getElementById(label_select).className = "statistic-label glow"; }
        if (document.getElementById(label_day))    { document.getElementById(label_day).className    = "statistic-label glow"; }

        // print charts
        let chart_html = this.print("", this.cache, eval(this.name+".day_"+chart_id), eval(this.name+".selected_"+chart_id), false, chart_id);
        setTextById("chart_container_" + chart_id, chart_html);
    }

    /*
    * create view with server and usage statistics
    *
    * @param (string) title: title to be displayed
    * @param (dict) data: API response for list specific request
    */
    print (title, data, date, chart_type="all", groups=true, id=0) {
        let html = "";
        let open_category = [];

        const statistics = data["DATA"]["data"]["entries"][date];
        const camera_status = app_data["STATUS"]["devices"]["cameras"];
        const system_data   = app_data["STATUS"]["system"];

        this.tab.style_cells = { "vertical-align": "top", "padding": "3px" }

        if (chart_type === "all" || chart_type === "overview") {
            // resource usage
            let pie_data = { "titles": [], "data": []}
            pie_data["titles"].push("Data");
            pie_data["data"].push(system_data["hdd_data"] - system_data["hdd_archive"]);
            pie_data["titles"].push("Archive");
            pie_data["data"].push(system_data["hdd_archive"]);
            pie_data["titles"].push("System");
            pie_data["data"].push(system_data["hdd_used"] - system_data["hdd_data"]);
            pie_data["titles"].push("Available");
            pie_data["data"].push(system_data["hdd_total"] - system_data["hdd_used"]);

            let chart = birdhouseChart_create("HDD Usage", pie_data["titles"], pie_data["data"], "pie",
                false, "hdd_pie_"+id, {"height": "270px", "width":"270px"},
                chartJS_hddPieChart,
                "right");

            let info  = "";
            info += "Date:<br/><b><big>" + date + "</big></b><br/>&nbsp;<br/>";
            info += "Max parallel streams:<br/><b><big>" + statistics["streams"]["info"]["max"] + "</big></b><br/>&nbsp;<br/>";
            info += "Total viewing time:<br/><b><big>" + convert_second2time(Math.round(statistics["streams"]["info"]["views"])) + "</big></b><br/>&nbsp;";

            let html_entry = "<div><div style='float:left;padding:5px;'>" + chart + "</div>";
            html_entry    += "<div style='float:left;padding:5px;'>" + info + "</div></div>";

            if (groups) { html  += birdhouse_OtherGroup( "chart_hdd_pie", lang("TODAY") + " HDD Usage", html_entry, true ); }
            else        { html  += html_entry; }
        }

        let open;
        if (chart_type === "all") {
            // statistics of the current day
            Object.keys(statistics).sort().forEach((key) => {
                open = open_category.indexOf(key) > -1;
                html += this.print_line_chart(data, id, key, open, groups, date);
            });
        }
        else if (statistics[chart_type]) {
            let key = chart_type;
            open = open_category.indexOf(key) > -1;
            html += this.print_line_chart(data, id, key, open, groups, date);
        }
        return html;
    }

    /*
    * create pie chart
    */
    print_pie_chart () {

    }

    /*
    * create line chart
    */
    print_line_chart (data, chart_id, key, open, groups, date) {
        let html   = "";
        let info   = "";
        let chart = "&nbsp;<br/>";
        const statistics = data["DATA"]["data"]["entries"][date];

        chart += birdhouseChart_create("", statistics[key]["titles"],
            statistics[key]["data"],
            "line",
            false,
            "statisticsChart_"+key+"_"+chart_id,
            {"height": "250px", "width": "100%"},
            chartJS_darkColors
        );
        chart += "<br/>&nbsp;<br/>";

        if (groups) { html  += birdhouse_OtherGroup( "chart_"+key, lang("TODAY") + " " + key.toUpperCase() + " " + info, chart, open ); }
        else        { html  += chart; }
        return html;
    }
}


let bhStatistics;
app_scripts_loaded += 1;
