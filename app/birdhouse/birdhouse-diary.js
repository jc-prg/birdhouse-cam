//--------------------------------------
// jc://birdhouse/diary/
//--------------------------------------


/*
* class to create birdhouse diary that visualizes breeding events (such as first egg laid) in a schedule view
*/
class BirdhouseDiary {
    constructor (name) {
        this.name = name;

        this.diary_data = {};
        this.stage_definition = {};
        this.stage_legend = "";
        this.stage_values = {};
        this.brood_list = {};
        this.bird_definition = {};
        this.archive_keys = [];
        this.video_keys = [];
        this.dataset = sample_dataset["diary"];
        this.calendarContainer = undefined;
        this.currentOffset = 0;
        this.btn_previous = "<button onclick=\""+this.name+".changeMonth(-1)\" style=\"float:left\">&nbsp;&nbsp;◀</button>";
        this.btn_next = "<button onclick=\""+this.name+".changeMonth(1)\" style=\"float:right\">▶</button>";
        this.image_archive = "";
        this.image_video = "";
        this.image_add = "";
        this.image_edit = "";
        this.image_delete = "";
        this.last_stage_value = "";

        this.stage_values = {
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
        this.stage_definition = {
            "1": lang("NEST_BUILDING"),
            "2": lang("EGG_LAYING"),
            "3": lang("BREEDING"),
            "4": lang("HATCHING"),
            "5": lang("FEEDING"),
            "6": lang("LEAVING"),
            "7": lang("SPECIAL_EVENT")
        }

        this.tab = new birdhouse_table();
    }

    /*
    * function to show diary entries such as the first egg laid in a calendar view
    *
    * @param (object) data: API response
    */
    init (data) {
        // former: function birdhouse_DIARY(data) {}
        this.setVariables(data);

        let settings    = "";
        let html        = "";
        let calendar    = "";
        calendar       += "<div id='calendarContainer' class='calendar-container'></div>";
        calendar       += "<div id='calendarLegend' class='calendar-legend'>"+this.stage_legend+"</div>";

        if (app_admin_allowed) {
            settings += this.showBroodsOverview();
            html     += birdhouse_OtherGroup( "DIARY_SETTINGS", lang("SETTINGS"), settings, false, "settings" );
            html     += birdhouse_OtherGroup( "DIARY_CALENDAR", lang("CALENDAR"), calendar, true, "" );
        }
        else {
            html = calendar;
        }

        setTextById(app_frame.header, "<center><h2>" + lang("BIRDHOUSE") + " " + lang("DIARY") + "</h2></center>");
        setTextById(app_frame.content, html);

        this.calendarContainer = document.getElementById("calendarContainer");
        this.renderCalendars();
    }

    /*
    * set require vars
    *
    * @param (object) data: API response
    */
    setVariables(data="") {
        if (data !== "") {
            this.currentOffset  = 0;
            this.diary_data     = data["DATA"]["data"]["diary"];
            this.dataset        = this.diary_data["entries"];
            this.archive_keys   = this.diary_data["archive"];
            this.video_keys     = this.diary_data["videos"];
            //this.bird_class = this.diary_data["birds"];
            this.brood_list     = {};

            Object.entries(this.diary_data["broods"]).forEach(([key,entry]) => {
                this.brood_list[key] = this.diary_data["broods"][key]["title"] + " (" + bird_lang(this.diary_data["broods"][key]["bird"]) + ")";
            });

            Object.entries(this.diary_data["birds"]).forEach(([key,entry]) => {
                this.bird_definition[key] = bird_lang(key);
            });

        }

        this.image_archive       = "<div class='diary-icon diary-archive' title='"+lang("ARCHIVE")+"'></div>";
        this.image_video         = "<div class='diary-icon diary-video' title='"+lang("VIDEO")+"'></div>";
        this.image_add           = "<div class='diary-icon diary-add' title='"+lang("ADD")+"'></div>";
        this.image_edit          = "<div class='diary-icon diary-edit' title='"+lang("EDIT")+"'></div>";
        this.image_delete        = "<div class='diary-icon diary-delete' title='"+lang("DELETE")+"'></div>";
        this.image_info          = "<div class='diary-icon diary-info' title='"+lang("DIARY")+"' style='display:inline-block;'></div>";

        this.stage_legend        = "";
        this.stage_legend       += "<div class='legend-entry'><div class='milestone type-0'>"+this.image_archive+"</div>&nbsp;" + lang("ARCHIVE") + "&nbsp;&nbsp;&nbsp;&nbsp;</div>";
        this.stage_legend       += "<div class='legend-entry'><div class='milestone type-0'>"+this.image_video+"</div>&nbsp;" + lang("VIDEOS") + "&nbsp;&nbsp;&nbsp;&nbsp;</div>";

        Object.entries(this.stage_definition).forEach(([key,entry]) => {
            this.stage_legend += "<div class='legend-entry'><div class='milestone type-"+key+" filled'></div>&nbsp;" + entry + "&nbsp;&nbsp;&nbsp;&nbsp;</div>";
        });
    }

    /*
    * show (and later edit) details of a milestone entry, using a appMessage
    *
    * @param (string) title: title fo the milestone (= its key)
    * @param (object) entry: data of the milestone
    */
    showDetails(date, title, entry) {
        let commands = {
            "EDIT":   [lang("EDIT"), this.name+".editDetails('"+date+"', '"+title+"', 'diary_entry');"],
            "DELETE": [lang("DELETE"), this.name+".deleteEntryConfirm('"+date+"', '"+title+"');"],
            "CLOSE":  [lang("CLOSE"), ""]
        };

        let html = "";
        html    += "<div style='float:left;width:100%;'><h2><div class='milestone type-"+entry["type"]+" filled' style='vertical-align:center;'></div>";
        html    += "<center>&nbsp;&nbsp;"+title+"</center></h2></div><div style='float:left;width:100%;'><hr/><br/></div>";
        html    += this.tab.start();
        html    += this.tab.row(lang("DATE")+":", date + "<input id='add_key' value='"+date+"' style='display:none;'>");
        html    += this.tab.row(lang("TYPE")+":", this.stage_definition[entry["type"]]);
        if (this.stage_values[entry["value"]] !== undefined) {
            html    += this.tab.row(lang("VALUE")+":", this.stage_values[entry["value"]]);
        }
        html    += this.tab.row(lang("BROOD")+":", this.brood_list[entry["brood"]]);
        html    += this.tab.row(lang("COMMENT")+":", entry["comment"]);
        if (app_admin_allowed === false) {
            delete commands["EDIT"];
            delete commands["DELETE"];
            //html    += tab.row("",    "&nbsp;");
            //html    += tab.row("",    btn);
        }
        html    += this.tab.end();
        html    += "&nbsp;<br/>";
        html    += "&nbsp;<br/>";
        html    += "<input id='diary_entry' value='"+JSON.stringify(entry)+"' style='display:none;'>";

        appMsg.dialog(html, "", "300px", appMsg.message_width+"px", true, commands);
    }

    /*
    * list existing broods (list, edit, delete)
    */
    showBroodsOverview() {
        let onclick = "alert('not implemented yet');";
        let onclick2 = "";
        let html = "";

        html     += "&nbsp;<br/><center>";
        html     += "<div class='brood-list'>";
        html     += this.tab.start();
        Object.entries(this.diary_data["broods"]).forEach(([key, entry]) => {

            onclick = this.name+".editBrood(id='"+key+"');";
            onclick2 = this.name+".deleteEntryConfirm(id='"+key+"', '"+this.diary_data["broods"][key]["title"]+"', true);";
            entry  = this.diary_data["broods"][key]["title"] + " (" + bird_lang(this.diary_data["broods"][key]["bird"]) + ")";
            entry += "<div class='milestone type-edit' onclick=\""+onclick2+"\">" + this.image_delete + "</div>";
            entry += "<div class='milestone type-edit' onclick=\""+onclick+"\">" + this.image_edit + "</div>";
            html  += this.tab.row(key, entry);
        });

        onclick = this.name+".editBrood();";
        let entry = "<i>" + lang("NEW_ENTRY") + "</i><div class='milestone type-edit' onclick=\"" + onclick + "\">" + this.image_add + "</div>";
        html     += this.tab.row("", entry);
        html     += this.tab.end();
        html     += "</div>";
        html     += "<center><br/>&nbsp;";

        return html;
    }

    /*
    * form to edit an existing oder create a new brood entry
    */
    editBrood(brood_id="new") {
        let command = "ADD";
        let entry   = "";
        let fields  = "add_id,add_title,add_id_org,add_bird,add_comment";
        if (brood_id !== "" && this.diary_data["broods"][brood_id]) { entry = this.diary_data["broods"][brood_id]; }

        let commands = {
            "SAVE":   [lang("SAVE"),   this.name+".saveEntry('"+brood_id+"','brood', '"+fields+"');"],
            "DELETE": [lang("DELETE"), this.name+".deleteEntryConfirm('"+brood_id+"', '"+entry["title"]+"', true);"],
            "CLOSE":  [lang("CANCEL"), ""]
        };

        this.tab.style_cells["padding"] = "2px";

        if (entry === "") {
            entry = {};
            let fields = ["title", "bird", "comment"];
            for (let i=0;i<fields.length;i++) {
                entry[fields[i]] = "";
            }
        }

        let html = "";
        html    += "<div style='float:left;width:100%;'><h2><center>&nbsp;&nbsp;"+lang(command)+"</center></h2></div><div style='float:left;width:100%;'><hr/><br/></div>";
        html    += this.tab.start();
        html    += this.tab.row("ID:",                      birdhouse_edit_field("add_id", "this:"+brood_id, "input", "", "string") + "<input id='add_id_org' value='"+brood_id+"' style='display:none;'>");
        html    += this.tab.row(lang("TITLE")+":",        birdhouse_edit_field("add_title", "this:"+entry["title"], "input", "", "string"));
        html    += this.tab.row(lang("BIRD_SPECIES")+":", birdhouse_edit_field("add_bird",  "this:"+entry["bird"], "select_dict_sort", this.bird_definition, "integer"));
        html    += this.tab.row(lang("COMMENT")+":",      birdhouse_edit_field("add_comment", "this:"+entry["comment"], "input", "", "string"));
        html    += this.tab.end();
        html    += "&nbsp;<br/>";
        html    += "&nbsp;<br/>";
        html    += "<input id='diary_field_list' value='"+fields+"' style='display:none;'>";

        appMsg.dialog(html, "", "380px", appMsg.message_width+"px", true, commands);
    }

    /*
    * form to edit an existing or create a new milestone entry, using a appMessage
    *
    * @param (string) date: date for which an entry shall be added
    * @param (string) title: title / key for the entry
    * @param (object) entry: data of the milestone
    */
    editDetails(date, title="", entry="") {
        let command = "ADD";
        let fields  = "add_key,add_title,add_title_org,add_type,add_value,add_brood,add_comment";
        let save    = this.name+".saveEntry(\""+date+"\", \""+title+"\", \""+fields+"\");";
        let btn     = "<button onclick='"+save+"' style='background:gray;width:100px;float:left;'>"+lang("SAVE")+"</button>";

        let commands = {
            "SAVE":   [lang("SAVE"), this.name+".saveEntry('"+date+"', '"+title+"', '"+fields+"');"],
            "CLOSE":  [lang("CANCEL"), ""]
        };

        this.tab.style_cells["padding"] = "2px";

        if (entry !== "") {
            if (document.getElementById(entry)) { entry = JSON.parse(document.getElementById(entry).value); command = "EDIT"; }
            else                                { entry = ""; }
        }
        if (entry === "") {
            entry = {};
            let fields = ["type", "value", "brood", "comment"];
            for (let i=0;i<fields.length;i++) {
                entry[fields[i]] = "";
            }
        }

        let html = "";
        html    += "<div style='float:left;width:100%;'><h2><center>&nbsp;&nbsp;"+lang(command)+"</center></h2></div><div style='float:left;width:100%;'><hr/><br/></div>";
        html    += this.tab.start();
        html    += this.tab.row(lang("DATE")+":",    date + "<input id='add_key' value='"+date+"' style='display:none;'>");
        html    += this.tab.row(lang("TITLE")+":",   birdhouse_edit_field("add_title", "this:"+title, "input", "", "string") + "<input id='add_title_org' value='"+title+"' style='display:none;'>");
        html    += this.tab.row(lang("TYPE")+":",    birdhouse_edit_field("add_type",  "this:"+entry["type"], "select_dict_sort", this.stage_definition, "integer"));
        html    += this.tab.row(lang("VALUE")+":",   birdhouse_edit_field("add_value", "this:"+entry["value"], "select_dict_sort", this.stage_values, "string"));
        html    += this.tab.row(lang("BROOD")+":",   birdhouse_edit_field("add_brood", "this:"+entry["brood"], "select_dict_sort", this.brood_list, "string"));
        html    += this.tab.row(lang("COMMENT")+":", birdhouse_edit_field("add_comment", "this:"+entry["comment"], "input", "", "string"));
        html    += this.tab.end();
        html    += "&nbsp;<br/>";
        html    += "&nbsp;<br/>";
        html    += "<input id='diary_field_list' value='"+fields+"' style='display:none;'>";
        //appMsg.confirm(html, "", "440");

        appMsg.dialog(html, "", "380px", appMsg.message_width+"px", true, commands);
    }

    /*
    * send API request to edit an existing or create a new milestone entry
    *
    * @param (string) date: date for which an entry shall be added
    * @param (string) title: title / key for the entry
    * @param (object) id_list: list of field ids
    */
    saveEntry(date, org_title, id_list) {
        let commands = [];
        let fields   = id_list.split(",");
        let entry    = {};

        if (org_title === "brood")   { commands = ["diary-edit-brood", date]; }
        else                         { commands = ["diary-edit-milestone", date, org_title]; }

        for (let i=0;i<fields.length;i++) {
            let key  = fields[i].replace("add_","");
            entry[key] = getValueById(fields[i]);
        }

        birdhouse_apiRequest("POST", commands, entry, birdhouse_AnswerEditSend);
    }

    /*
    * confirm whether entry shall be deleted
    *
    * @param (string) date: date for which an entry shall be added
    * @param (string) title: title / key for the entry
    * @param (boolean) brood: true if to delete a brood entry, false for milestones
    */
    deleteEntryConfirm(date, title, brood=false) {
        let message         = lang("DELETE_ENTRY",["<b>"+title+"</b> ("+date+")"]);
        if (brood) { title = "brood"; }
        let delete_command  = this.name+".deleteEntry('"+date+"','"+title+"')";
        appMsg.confirm(message, delete_command, 200);
    }

    /*
    * send API request to delete entry
    *
    * @param (string) date: date for which an entry shall be added
    * @param (string) title: title / key for the entry
    */
    deleteEntry(date, title) {
        let commands = [];

        if (title === "brood")   { commands = ["diary-delete-brood", date]; }
        else                     { commands = ["diary-delete-milestone", date, title]; }
        birdhouse_apiRequest("POST", commands, "", birdhouse_AnswerEditSend);
    }

    /*
    * create string with details for the currently active brood
    */
    activeBrood() {
        let html    = "";
        let data    = app_data["STATUS"]["brood"];
        let details = data["brood_details"];

        this.setVariables();

        if (data["stage"]) {
            html += "<center><div class='brood-info'>";
            html += "<text class='milestone type-edit' onclick='birdhousePrint_page(\"DIARY\");' style='float:none; display:inline-block;height:15px;width:15px;'>" + this.image_info + "</text>";
            html += "&nbsp;";
            if (data["days_since_start"] === 0) {
                html += lang("ACTIVE_BROOD_TODAY", [bird_lang(details["bird"]), this.stage_definition[data["stage"]], data["days_since_start"]]);
            }
            else if (data["days_since_start"] === 1) {
                html += lang("ACTIVE_BROOD_1DAY", [bird_lang(details["bird"]), this.stage_definition[data["stage"]], data["days_since_start"]]);
            }
            else {
                html += lang("ACTIVE_BROOD", [bird_lang(details["bird"]), this.stage_definition[data["stage"]], data["days_since_start"]]);
            }
            html += "</div></center>";

        }
        else {
            html += "<center><div class='brood-info'>";
            html += lang("ACTIVE_BROOD_NO");
            html += "</div></center>";
        }

        return html;
    }

    /*
    * create the calender for a specific month and add know milestones (events)
    *
    * @param (string) year: year of month to be created
    * @param (string) mont: month to be created
    */
    createCalendar(year, month) {

        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        const monthName = firstDay.toLocaleString('default', { month: 'long' });

        const wrapper = document.createElement('div');
        wrapper.className = 'calendar-month';

        const monthDiv = document.createElement('div');
        monthDiv.classList.add('month');

        const monthTitle = document.createElement('div');
        monthTitle.className = 'month-name';
        monthTitle.innerHTML = `${monthName} ${year}` + this.btn_next + this.btn_previous;
        monthDiv.appendChild(monthTitle);

        const calendarGrid = document.createElement('div');
        calendarGrid.className = 'calendar';

        //const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
        const weekdays = lang("WEEKDAYS_SHORT");
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

        //let last_stage_value = "";
        days.forEach(week => {
            const weekRow = document.createElement('div');
            weekRow.className = 'week-row';

            let maxMilestones = 0;
            week.forEach(day => {
                if (!day) return;
                const dateKey = `${day.getFullYear()}${String(day.getMonth() + 1).padStart(2, '0')}${String(day.getDate()).padStart(2, '0')}`;
                const entries = this.dataset[dateKey];
                const count = entries ? Object.keys(entries).length : 0;
                maxMilestones = Math.max(maxMilestones, count);
            });
            week.forEach(day => {

                const dayDiv = document.createElement('div');
                dayDiv.className = 'day';

                let dayEntry;
                if (day) {
                    const d = day.getDate();
                    const dateKey = `${day.getFullYear()}${String(day.getMonth() + 1).padStart(2, '0')}${String(d).padStart(2, '0')}`;
                    const today = new Date();

                    // Compare the year, month, and day (ignore time part)
                    const isToday = day.getFullYear() === today.getFullYear() && day.getMonth() === today.getMonth() && day.getDate() === today.getDate();
                    const isFuture = day > today;
                    let edit = "";
                    let archive = "";
                    let date_key = day.getFullYear() + "" + String(day.getMonth() + 1).padStart(2, '0') + "" + String(day.getDate()).padStart(2, '0');

                    if (isToday) {
                        //dayDiv.style.backgroundColor = "#450000";
                        dayDiv.className = "day today";
                    }

                    if (app_admin_allowed) {
                        let on_click = this.name+".editDetails(\"" + dateKey + "\");"
                        edit = "<div class='milestone type-edit' onclick='" + on_click + "'>" + this.image_add + "</div>";
                    }

                    let icon;
                    dayDiv.innerHTML = `<strong>${d}${edit}</strong>`;
                    dayEntry = document.createElement("div");
                    dayEntry.className = "day-entries";

                    if (this.archive_keys.includes(dateKey)) {
                        icon = document.createElement("div");
                        icon.className = "milestone type-0";
                        icon.title = lang("ARCHIVE");
                        icon.innerHTML = this.image_archive;
                        icon.onclick = () => {
                            birdhousePrint_page("TODAY", app_active.cam, dateKey);
                        };
                        dayEntry.appendChild(icon);
                    }
                    if (this.video_keys.includes(dateKey)) {
                        icon = document.createElement("div");
                        icon.className = "milestone type-0";
                        icon.title = lang("VIDEOS");
                        icon.innerHTML = this.image_video;
                        icon.onclick = () => {
                            birdhousePrint_page("VIDEOS", app_active.cam, dateKey);    // !!!!!! add parameters to directly open the right month (e.g. using toggles);
                        };
                        dayEntry.appendChild(icon);
                    }

                    if (this.dataset[dateKey]) {
                        const milestones = this.dataset[dateKey];
                        Object.entries(milestones).forEach(([title, info]) => {
                            const milestone = document.createElement('div');
                            milestone.className = `milestone type-${info.type} filled`;
                            milestone.title = title;
                            milestone.innerHTML = " ";
                            if (info.value !== "" && info.value !== "start" && info.value !== "end" && info.value !== "termination" && info.value !== "one_day") {
                                milestone.textContent = info.value;
                                milestone.className = `milestone type-${info.type}`;
                            }

                            // visualize stage by coloring the <hr/> line element
                            if (info.value === "start") {
                                dayDiv.firstChild.className = `stage type-${info.type}`;
                                this.last_stage_value = info.type;
                            }
                            if (info.value === "one_day") {
                                dayDiv.firstChild.className = `stage type-${info.type}`;
                            }
                            if (this.last_stage_value !== "") {
                                dayDiv.firstChild.className = `stage type-${this.last_stage_value}`;
                            }
                            //if (last_stage_value == "end" || last_stage_value == "cancel")  { last_stage_value = ""; }
                            if (info.value === "end" || info.value === "cancel" || info.value === "termination") {
                                this.last_stage_value = "end";
                            }

                            milestone.onclick = () => {
                                this.showDetails(dateKey, title, info);
                            };
                            dayEntry.appendChild(milestone);
                        });
                    } else if (this.last_stage_value !== "" && !isFuture) {
                        dayDiv.firstChild.className = `stage type-${this.last_stage_value}`;
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
    renderCalendars() {
        this.last_stage_value            = '';
        this.calendarContainer.innerHTML = '';
        const baseDate = new Date();
        const startDate = new Date(baseDate.getFullYear(), baseDate.getMonth() + this.currentOffset - 1, 1);
        const nextDate = new Date(startDate.getFullYear(), startDate.getMonth() + 1, 1);

        this.calendarContainer.appendChild(this.createCalendar(startDate.getFullYear(), startDate.getMonth()));
        this.calendarContainer.appendChild(this.createCalendar(nextDate.getFullYear(), nextDate.getMonth()));
    }

    /*
    * move between months
    *
    * @param (integer) delta: define currentOffset to move between the months
    */
    changeMonth(delta) {
        this.currentOffset += delta;
        this.renderCalendars();
    }
}


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
            "Brut startet": { "brood": "2025-1", "type": "3", "stage": "Eier legen", "comment": "...", "value": "start" },
            "Specht": { "brood": "2025-1", "type": "7", "stage": "", "comment": "Specht inspiziert Vogelhaus" }
        },
        "20250522": {
            "7 Eier": { "brood": "2025-1", "type": "2", "stage": "Eier legen", "comment": "...", "value": "7"  }
        }
    }
};
const bhDiary = new BirdhouseDiary("bhDiary");


app_scripts_loaded += 1;
