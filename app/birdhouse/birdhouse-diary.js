//--------------------------------------
// jc://birdhouse/, (c) Christoph Kloth
//--------------------------------------
// function to manage the birdhouse diary
//--------------------------------------

const sample_dataset = {
  "info": {},
  "broods": {
    "2025-05": {
      "title": "Erst Brut 2025",
      "bird":  "KOHLMEISE",
    }
  },
  "entries": {
    "20250512": {
      "Nestbau startet": { "brood": "2025-1", "type": "1", "stage": "Nestbau", "comment": "Kohlmeisen ziehen ein", "value": "start" }
    },
    "20250513": {
      "Specht": { "brood": "2025-1", "type": "7", "stage": "", "comment": "Specht inspiziert Vogelhaus" }
    },
    "20250516": {
      "Eiablage startet": { "brood": "2025-1", "type": "2", "stage": "Eier legen", "comment": "Kohlmeisen ziehen ein", "value": "start" },
      "1 Ei":   { "brood": "2025-1", "type": "2", "stage": "Eier legen", "comment": "...", "value": "1" }
    },
    "20250517": {
      "2 Eier": { "brood": "2025-1", "type": "2", "stage": "Eier legen", "comment": "...", "value": "2"  }
    },
    "20250518": {
      "3 Eier": { "brood": "2025-1", "type": "2", "stage": "Eier legen", "comment": "...", "value": "3"  }
    },
    "20250519": {
      "4 Eier": { "brood": "2025-1", "type": "2", "stage": "Eier legen", "comment": "...", "value": "4"  }
    },
    "20250520": {
      "5 Eier": { "brood": "2025-1", "type": "2", "stage": "Eier legen", "comment": "...", "value": "5"  }
    },
    "20250521": {
      "6 Eier": { "brood": "2025-1", "type": "2", "stage": "Eier legen", "comment": "...", "value": "6"  },
      "Brüten startet": { "brood": "2025-1", "type": "3", "stage": "Eier legen", "comment": "...", "value": "start" },
      "Specht": { "brood": "2025-1", "type": "7", "stage": "", "comment": "Specht inspiziert Vogelhaus" }
    },
    "20250522": {
      "7 Eier": { "brood": "2025-1", "type": "2", "stage": "Eier legen", "comment": "...", "value": "7"  }
    }
  }
};

var diary_data          = {};
var stage_definition    = {};
var stage_legend        = "";
var stage_values        = {};
var brood_list          = {};
var archive_keys        = [];
var dataset             = sample_dataset["diary"];
var calendarContainer   = undefined;
var currentOffset       = 0;
var btn_previous        = "<button onclick=\"diary_changeMonth(-1)\" style=\"float:left\">&nbsp;&nbsp;◀</button>";
var btn_next            = "<button onclick=\"diary_changeMonth(1)\" style=\"float:right\">▶</button>";
var image_archive       = "<img src='birdhouse/img/image.png' style='max-width:15px;max-height:15px;'>";
var image_archive       = "<div class='diary-icon-image' title='"+lang("ARCHIVE")+"'></div>";
var image_archive_b     = "<img src='birdhouse/img/image_black.png' style='max-width:15px;max-height:15px;'>";
var image_add           = "<img src='birdhouse/img/add.png' style='max-width:15px;max-height:15px;'>";
var image_add           = "<div class='diary-icon-add'  title='"+lang("ADD")+"'></div>";
var image_add_b         = "<img src='birdhouse/img/add_black.png' style='max-width:15px;max-height:15px;'>";
var image_edit          = "<img src='birdhouse/img/edit.png' style='max-width:15px;max-height:15px;'>";
var image_edit           = "<div class='diary-icon-edit' title='"+lang("EDIT")+"'></div>";




/*
* function to show diary entries such as the first egg laid in a calendar view
*
* @param (object) data: API response
*/
function birdhouse_DIARY(data) {
    diary_setVariables(data);

    var html = "";
    html += "<div id='calendarContainer' class='calendar-container'></div>";
    html += "<div id='calendarLegend' class='calendar-legend'>"+stage_legend+"</div>";

    setTextById(app_frame_header, "<center><h2>" + lang("BIRDHOUSE") + " " + lang("DIARY") + "</h2></center>");
    setTextById(app_frame_content, html);

    calendarContainer = document.getElementById("calendarContainer");
    diary_renderCalendars();
}


/*
* set require vars
*
* @param (object) data: API response
*/
function diary_setVariables(data) {
    currentOffset   = 0;
    diary_data      = data["DATA"]["data"]["diary"];
    dataset         = diary_data["entries"];
    archive_keys    = diary_data["archive"];
    //bird_class      = diary_data["birds"];
    brood_list      = {};

    Object.entries(diary_data["broods"]).forEach(([key,entry]) => {
        brood_list[key] = diary_data["broods"][key]["title"] + " (" + bird_lang(diary_data["broods"][key]["bird"]) + ")";
        //brood_list[key] = brood_list["title"] + "(" + bird_lang(brood_list["bird"]) + ")";
    });

    stage_definition = {
        "1": lang("NEST_BUILDING"),
        "2": lang("EGG_LAYING"),
        "3": lang("BREEDING"),
        "4": lang("HATCHING"),
        "5": lang("FEEDING"),
        "6": lang("LEAVING"),
        "7": lang("SPECIAL_EVENT")
        };
    stage_legend     = "";

    Object.entries(stage_definition).forEach(([key,entry]) => {
        stage_legend += "<div class='legend-entry'><div class='milestone type-"+key+"'></div>&nbsp;" + entry + "&nbsp;&nbsp;&nbsp;&nbsp;</div>";
    });

    stage_values = {
        "start": lang("START"),
        "end": lang("END"),
        "one_day": lang("ONE_DAY"),
        "termination": lang("TERMINATION"),
        "1": "1",
        "2": "2",
        "3": "3",
        "4": "4",
        "5": "5",
        "6": "6",
        "7": "7",
        "8": "8",
        "9": "9",
        "10": "10",
        "11": "11",
        "12": "12",
        "13": "13",
        "14": "14",
        }
}

/*
* show (and later edit) details of a milestone entry, using a appMessage
*
* @param (string) title: title fo the milestone (= its key)
* @param (object) entry: data of the milestone
*/
function diary_showDetails(date, title, entry) {
    var tab  = new birdhouse_table();
    var btn  = "<button onclick='diary_editDetails(\""+date+"\", \""+title+"\", \"diary_entry\");' style='background:gray;width:100px;float:left;'>"+lang("EDIT")+"</button>";
    btn     += "<button onclick='diary_deleteEntryConfirm(\""+date+"\", \""+title+"\");' style='background:gray;width:100px;float:left;'>"+lang("DELETE")+"</button>";
    var html = "";
    html    += "<div style='float:left;width:100%;'><h2><div class='milestone type-"+entry["type"]+"' style='vertical-align:center;'></div>";
    html    += "<center>&nbsp;&nbsp;"+title+"</center></h2></div><div style='float:left;width:100%;'><hr/><br/></div>";
    html    += tab.start();
    html    += tab.row(lang("DATE")+":",    date + "<input id='add_key' value='"+date+"' style='display:none;'>");
    html    += tab.row(lang("TYPE")+":",    stage_definition[entry["type"]]);
    if (stage_values[entry["value"]] != undefined) {
        html    += tab.row(lang("VALUE")+":",   stage_values[entry["value"]]);
        }
    html    += tab.row(lang("BROOD")+":",   brood_list[entry["brood"]]);
    html    += tab.row(lang("COMMENT")+":", entry["comment"]);
    if (app_admin_allowed) {
        html    += tab.row("",    "&nbsp;");
        html    += tab.row("",    btn);
        }
    html    += tab.end();
    html    += "&nbsp;<br/>";
    html    += "<hr>";
    html    += "<input id='diary_entry' value='"+JSON.stringify(entry)+"' style='display:none;'>";

    appMsg.confirm(html, "", "380");
    }

/*
* form to edit an existing or create a new milestone entry, using a appMessage
*
* @param (string) date: date for which an entry shall be added
* @param (string) title: title / key for the entry
* @param (object) entry: data of the milestone
*/
function diary_editDetails(date, title="", entry="") {
    var command = "ADD";
    var fields  = "add_key,add_title,add_title_org,add_type,add_value,add_brood,add_comment";
    var save    = "diary_saveEntry(\""+date+"\", \""+title+"\", \""+fields+"\");";
    var btn     = "<button onclick='"+save+"' style='background:gray;width:100px;float:left;'>"+lang("SAVE")+"</button>";
    var tab     = new birdhouse_table();
    tab.style_cells["padding"] = "2px";

    if (entry != "") {
        if (document.getElementById(entry)) { entry = JSON.parse(document.getElementById(entry).value); command = "EDIT"; }
        else                                { entry = "" };
    }
    if (entry == "") {
        entry = {};
        var fields = ["type", "value", "brood", "comment"];
        for (var i=0;i<fields.length;i++) {
            entry[fields[i]] = "";
            }
        }

    var html = "";
    html    += "<div style='float:left;width:100%;'><h2><center>&nbsp;&nbsp;"+lang(command)+"</center></h2></div><div style='float:left;width:100%;'><hr/><br/></div>";
    html    += tab.start();
    html    += tab.row(lang("DATE")+":",    date + "<input id='add_key' value='"+date+"' style='display:none;'>");
    html    += tab.row(lang("TITLE")+":",   birdhouse_edit_field(id="add_title", field="this:"+title, type="input", options="", data_type="string") +
                                   "<input id='add_title_org' value='"+title+"' style='display:none;'>");
    html    += tab.row(lang("TYPE")+":",    birdhouse_edit_field(id="add_type",  field="this:"+entry["type"], type="select_dict_sort", options=stage_definition, data_type="integer"));
    html    += tab.row(lang("VALUE")+":",   birdhouse_edit_field(id="add_value", field="this:"+entry["value"], type="select_dict_sort", options=stage_values, data_type="string"));
    html    += tab.row(lang("BROOD")+":",   birdhouse_edit_field(id="add_brood", field="this:"+entry["brood"], type="select_dict_sort", options=brood_list, data_type="string"));
    html    += tab.row(lang("COMMENT")+":", birdhouse_edit_field(id="add_comment", field="this:"+entry["comment"], type="input", options="", data_type="string"));
    html    += tab.row("",    "&nbsp;");
    html    += tab.row("",    btn);
    html    += tab.end();
    html    += "&nbsp;<br/>";
    html    += "<input id='diary_field_list' value='"+fields+"' style='display:none;'>";
    html    += "<hr/>";
    appMsg.confirm(html, "", "440");
    }

/*
* send API request to edit an existing or create a new milestone entry
*
* @param (string) date: date for which an entry shall be added
* @param (string) title: title / key for the entry
* @param (object) id_list: list of field ids
*/
function diary_saveEntry(date, org_title, id_list){
    var commands = ["diary-edit-milestone", date, org_title];
    var fields   = id_list.split(",");
    var entry    = {};

    for (var i=0;i<fields.length;i++) {
        var key  = fields[i].replace("add_","");
        var data = getValueById(fields[i]);
        entry[key] = data;
    }

    birdhouse_apiRequest("POST", commands, entry, birdhouse_AnswerEditSend);
}

/*
* confirm whether entry shall be deleted
*
* @param (string) date: date for which an entry shall be added
* @param (string) title: title / key for the entry
*/
function diary_deleteEntryConfirm(date, title) {
    var message = "Shall the entry &quot;"+title+"&quot; (" + date +") really be deleted?";
    var delete_command = "diary_deleteEntry('"+date+"','"+title+"')";
    appMsg.confirm(message, delete_command, 200);
}

/*
* send API request to delete entry
*
* @param (string) date: date for which an entry shall be added
* @param (string) title: title / key for the entry
*/
function diary_deleteEntry(date, title) {
    var commands = ["diary-delete-milestone", date, title];
    birdhouse_apiRequest("POST", commands, "", birdhouse_AnswerEditSend);
}

/*
* create the calender for a specific month and add know milestones (events)
*
* @param (string) year: year of month to be created
* @param (string) mont: month to be created
*/
function diary_createCalendar(year, month) {
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const monthName = firstDay.toLocaleString('default', { month: 'long' });

    const wrapper = document.createElement('div');
    wrapper.className = 'calendar-month';

    const monthDiv = document.createElement('div');
    monthDiv.classList.add('month');

    const monthTitle = document.createElement('div');
    monthTitle.className = 'month-name';
    monthTitle.innerHTML = `${monthName} ${year}` + btn_next + btn_previous;
    monthDiv.appendChild(monthTitle);

    const calendarGrid = document.createElement('div');
    calendarGrid.className = 'calendar';

    const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    weekdays.forEach(day => {
        const weekdayDiv = document.createElement('div');
        weekdayDiv.className = 'weekday';
        weekdayDiv.textContent = day;
        calendarGrid.appendChild(weekdayDiv);
        });

    const days = [];
    let currentWeek = [];

    // Adjust start day to Monday
    let offset = (firstDay.getDay() + 6) % 7;
    for (let i = 0; i < offset; i++) {
        currentWeek.push(null);
        }

    for (let d = 1; d <= lastDay.getDate(); d++) {
        const date = new Date(year, month, d);
        currentWeek.push(date);

        if (currentWeek.length === 7 || d === lastDay.getDate()) {
            days.push(currentWeek);
            currentWeek = [];
            }
        }

    let last_stage_value = "";
    days.forEach(week => {
        const weekRow = document.createElement('div');
        weekRow.className = 'week-row';

        let maxMilestones = 0;
        week.forEach(day => {
            if (!day) return;
            const dateKey = `${day.getFullYear()}${String(day.getMonth() + 1).padStart(2, '0')}${String(day.getDate()).padStart(2, '0')}`;
            const entries = dataset[dateKey];
            const count = entries ? Object.keys(entries).length : 0;
            maxMilestones = Math.max(maxMilestones, count);
            });

        //const rowHeight = 40 + maxMilestones * 20;
        const rowHeight = 55;

        week.forEach(day => {
            const dayDiv            = document.createElement('div');
            dayDiv.className        = 'day';
            dayDiv.style.minHeight  = `${rowHeight}px`;
            dayDiv.style.Height     = `${rowHeight}px`;

            if (day) {
                const d             = day.getDate();
                const dateKey       = `${day.getFullYear()}${String(day.getMonth() + 1).padStart(2, '0')}${String(d).padStart(2, '0')}`;
                const today         = new Date();

                // Compare the year, month, and day (ignore time part)
                const isToday       = day.getFullYear() === today.getFullYear() &&
                                      day.getMonth() === today.getMonth() &&
                                      day.getDate() === today.getDate();
                const isFuture      = day > today;
                var edit            = "";
                var archive         = "";
                var date_key        = day.getFullYear() + "" + String(day.getMonth() + 1).padStart(2, '0') + "" + String(day.getDate()).padStart(2, '0');

                if (isToday) {
                    //dayDiv.style.backgroundColor = "#450000";
                    dayDiv.className = "day today";
                    }

                if (app_admin_allowed) {
                    var on_click    = "diary_editDetails(\""+dateKey+"\");"
                    edit            = "<div class='milestone type-edit' onclick='"+on_click+"'>"+image_add+"</div>";
                    }
                if (archive_keys.includes(dateKey)) {
                    var on_click    = "birdhousePrint_load(view=\"TODAY\", camera=\""+app_active_cam+"\", date=\""+dateKey+"\");";
                    archive         =  "<div class='milestone type-edit' onclick='"+on_click+"'>"+image_archive+"</div>";
                }

                dayDiv.innerHTML    = `<strong>${d}${edit}${archive}</strong>`;
                dayEntry            = document.createElement("div");

                if (dataset[dateKey]) {

                    const milestones = dataset[dateKey];
                    Object.entries(milestones).forEach(([title, info]) => {
                        const milestone         = document.createElement('div');
                        milestone.className     = `milestone type-${info.type}`;
                        milestone.title         = title;
                        milestone.textContent   = ' ';
                        if (info.type == "2" && info.value != "start" && info.value != "end"
                            && info.value != "termination" && info.value != "one_day") { milestone.textContent = info.value; }

                        // visualize stage by coloring the <hr/> line element
                        if (info.value == "start")   { dayDiv.firstChild.className = `stage type-${info.type}`; last_stage_value = info.type; }
                        if (info.value == "one_day") { dayDiv.firstChild.className = `stage type-${info.type}`; }
                        if (last_stage_value != "")  { dayDiv.firstChild.className = `stage type-${last_stage_value}`; }
                        if (last_stage_value == "end" || last_stage_value == "cancel")  { last_stage_value = ""; }

                        milestone.onclick = () => {
                            diary_showDetails(dateKey, title, info);
                            };
                        dayEntry.appendChild(milestone);
                        });
                    }
                else if (last_stage_value != "" && !isFuture)  {
                    dayDiv.firstChild.className = `stage type-${last_stage_value}`;
                    }

                dayDiv.appendChild(dayEntry);
                }

            weekRow.appendChild(dayDiv);
            });

        calendarGrid.appendChild(weekRow);
        });

    monthDiv.appendChild(calendarGrid);
    wrapper.appendChild(monthDiv);
    return wrapper;
}

/*
* render calendar with two months
*/
function diary_renderCalendars() {
    calendarContainer.innerHTML = '';
    const baseDate = new Date();
    const startDate = new Date(baseDate.getFullYear(), baseDate.getMonth() + currentOffset - 1, 1);
    const nextDate = new Date(startDate.getFullYear(), startDate.getMonth() + 1, 1);

    calendarContainer.appendChild(diary_createCalendar(startDate.getFullYear(), startDate.getMonth()));
    calendarContainer.appendChild(diary_createCalendar(nextDate.getFullYear(), nextDate.getMonth()));
    }

/*
* move between months
*
* @param (integer) delta: define currentOffset to move between the months
*/
function diary_changeMonth(delta) {
    currentOffset += delta;
    diary_renderCalendars();
    }

app_scripts_loaded += 1;
