//----------------------------------------

function requestAPI(command, index, value, callback) {
    var requestURL = command + index + "/" + value;
    var xhttp = new XMLHttpRequest();
    xhttp.onreadystatechange = function() {
         if (this.readyState == 4 && this.status == 200) {
             //alert(this.responseText);
             callback( command, index, value);
         }
         else if (this.readyState == 4) {
             alert("Fehler: "+requestURL);
             callback( command, index, value );
         }
    };
    xhttp.open("POST", requestURL, true);
    xhttp.setRequestHeader("Content-type", "application/json");
    xhttp.send("{ GO : 1 }");
    }

//----------------------------------------

function setTrash(index, status) {
        requestAPI("/delete", index, status, setTrashShow );
	}

function setTrashShow(command, index, status) {
        document.getElementById("d_"+index).src          = "/html/recycle"+status+".png";
        if (status == 1) { status = 0; }
        else             { status = 1; }
        document.getElementById("d_"+index+"_value").innerHTML = status;
	}

//----------------------------------------

function setFavorit(index, status) {
        requestAPI("/favorit", index, status, setFavoritShow );
	}

function setFavoritShow(command, index, status) {
        document.getElementById("s_"+index).src          = "/html/star"+status+".png";
        if (status == 1) { status = 0; }
        else             { status = 1; }
        document.getElementById("s_"+index+"_value").innerHTML = status;
	}

//----------------------------------------

function showHideGroup(id) {
        if (document.getElementById("group_"+id).style.display == "none") {
        	document.getElementById("group_"+id).style.display = "block"
        	document.getElementById("group_link_"+id).innerHTML = "(&minus;)"
		images     = document.getElementById("group_ids_"+id).innerHTML;
                image_list = images.split(" ");
                for (let i=0; i<image_list.length; i++) {
			img      = document.getElementById(image_list[i]);
                        img_file = img.getAttribute('data-src');
                        img.src  = img_file;
			}
		}
	else {
        	document.getElementById("group_"+id).style.display = "none"
        	document.getElementById("group_link_"+id).innerHTML = "(+)"
		}
	}
