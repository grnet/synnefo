var flavors = [], images = [], servers = [], disks = [], cpus = [], ram = [];

function list_view() {
    $.cookie("list", '1'); // set list cookie
    $("div#machinesview").load($("#list").attr("href"), function(){
        $("a#standard")[0].className += ' activelink';
        $("a#list")[0].className = '';
    });
    return false;
}

function standard_view() {
    $.cookie("list", '0');
    href=$("a#standard").attr("href");
    $("div#machinesview").load(href, function(){
        $("a#list")[0].className += ' activelink';
        $("a#standard")[0].className = '';
    });
    return false;
}

function choose_view() {
    if ($.cookie("list")=='1') {
        list_view();
    } else {
        standard_view();
    }
}

function toggleMenu() {
    var primary = $("ul.css-tabs li a.primary");
    var secondary = $("ul.css-tabs li a.secondary");
    var all = $("ul.css-tabs li a");			
    var toggled = $('ul.css-tabs li a.current').hasClass('secondary');
    
    // if anything is still moving, do nothing
    if ($(":animated").length) {
        return;
    } 
    
    // nothing is current to begin with
    $('ul.css-tabs li a.current').removeClass('current');
    
    // move stuff around
    all.animate({top:'30px'}, {complete: function() { 
        $(this).hide();
        if (toggled) {
            primary.show();
            primary.animate({top:'9px'}, {complete: function() {
                $('ul.css-tabs li a.primary#machines').addClass('current');
                $('a#machines').click();                           	
            }});
        } else {
            secondary.show();
            secondary.animate({top:'9px'}, {complete: function() {
                $('ul.css-tabs li a.secondary#files').addClass('current');
                $('a#files').click();                           			                	
            }});
        }            	                          
    }});
    
    // rotate arrow icon
    if (toggled) {
        $("#arrow").rotate({animateAngle: (0), bind:[{"click":function(){toggleMenu()}}]});
        $("#arrow").rotateAnimation(0);            	
    } else {
        $("#arrow").rotate({animateAngle: (-180), bind:[{"click":function(){toggleMenu()}}]});
        $("#arrow").rotateAnimation(-180);
    }            
}

// confirmation overlay generation
function confirm_action(action_string, action_function, serverIDs, serverNames) {
    if (serverIDs.length == 1){
        $("#yes-no h3").text('You are about to ' + action_string + ' vm ' + serverNames[0]);
    } else if (serverIDs.length > 1){
        $("#yes-no h3").text('You are about to ' + action_string + ' ' + serverIDs.length + ' machines');
    } else {
        return false;
    }
    // action confirmation overlay
    var triggers = $("a#confirmation").overlay({
	    // some mask tweaks suitable for modal dialogs
	    mask: {
		    color: '#ebecff',
		    opacity: '0.9'
	    },
        top: 'center',
        load: false
    });
    // yes or no?
    var buttons = $("#yes-no button").click(function(e) {
	    // get user input
	    var yes = buttons.index(this) === 0;
        //close the confirmation window
        $("a#confirmation").overlay().close(); 
        // return true=yes or false=no
        if (yes) {
            action_function(serverIDs);
        }
    });
    $("a#confirmation").data('overlay').load();
    return false;
}

var changes_since = '';
// get and show a list of running and terminated machines
function update_vms(interval) {
    try{ console.info('updating machines'); } catch(err){}

    $.ajax({
        url: '/api/v1.0/servers/detail?changes_since=' + changes_since,
        type: "GET",
        timeout: TIMEOUT,
        dataType: "json",
        error: function(jqXHR, textStatus, errorThrown) {
					// don't forget to try again later
					if (interval) { 
						setTimeout(update_vms,interval,interval);
					}
					// as for now, just show an error message
                    if (jqXHR.status != undefined) {
						ajax_error(jqXHR.status);
					} else {
						ajax_error();
					}				
                    return false;
                    },
        success: function(data, textStatus, jqXHR) {
            changes_since = '';
            try {
				servers = data.servers;
			} catch(err) { ajax_error('400');}
			update_machines_view(data);
			if (interval) {
				setTimeout(update_vms,interval,interval);
			}
        }
    });
    return false;
}

// get and show a list of available standard and custom images
function update_images() { 
    $.ajax({
        url: '/api/v1.0/images/detail',
        type: "GET",
        //async: false,
        dataType: "json",
        timeout: TIMEOUT,
        error: function(jqXHR, textStatus, errorThrown) { 
                    ajax_error(jqXHR.status);
                    },
        success: function(data, textStatus, jqXHR) {
            try {
				images = data.images;
			} catch(err){
				ajax_error("NO_IMAGES");
			}
            if ($("ul#standard-images li").toArray().length + $("ul#custom-images li").toArray().length == 0) {
                $.each(data.images, function(i,image){
                    var img = $('#image-template').clone().attr("id","img-"+image.id).fadeIn("slow");
                    img.find("label").attr('for',"img-radio-" + image.id);
                    img.find(".image-title").text(image.name);
                    img.find(".description").text(image.description);
                    img.find(".size").text(image.size);
                    img.find("input.radio").attr('id',"img-radio-" + image.id);
                    if (i==0) img.find("input.radio").attr("checked","checked"); 
                    img.find("img.image-logo").attr('src','static/os_logos/'+image_tags[image.id]+'.png');
                    if (image.serverId) {
                        img.appendTo("ul#custom-images");
                    } else {
                        img.appendTo("ul#standard-images");
                    }
                });
            }
        }
    });
    return false;
}

Array.prototype.unique = function () {
	var r = new Array();
	o:for(var i = 0, n = this.length; i < n; i++)
	{
		for(var x = 0, y = r.length; x < y; x++)
		{
			if(r[x]==this[i])
			{
				continue o;
			}
		}
		r[r.length] = this[i];
	}
	return r;
}

// get and configure flavor selection
function update_flavors() { 
    $.ajax({
        url: '/api/v1.0/flavors/detail',
        type: "GET",
        //async: false,
        dataType: "json",
        timeout: TIMEOUT,
        error: function(jqXHR, textStatus, errorThrown) { 
            try {
				ajax_error(jqXHR.status);
			} catch (err) {
				ajax_error(err);
			}
        },
        success: function(data, textStatus, jqXHR) {
            flavors = data.flavors;
            $.each(flavors, function(i, flavor) {
                cpus[i] = flavor['cpu'];
                disks[i] = flavor['disk'];
                ram[i] = flavor['ram'];
            });
            cpus = cpus.unique();
            disks = disks.unique();
            ram = ram.unique();
            // sliders for selecting VM flavor
            $("#cpu:range").rangeinput({min:0,
                                       value:0,
                                       step:1,
                                       progress: true,
                                       max:cpus.length-1});
            
            $("#storage:range").rangeinput({min:0,
                                       value:0,
                                       step:1,
                                       progress: true,
                                       max:disks.length-1});

            $("#ram:range").rangeinput({min:0,
                                       value:0,
                                       step:1,
                                       progress: true,
                                       max:ram.length-1});
            $("#small").click();
            
            // update the indicators when sliding
            $("#cpu:range").data().rangeinput.onSlide(function(event,value){
                $("#cpu-indicator")[0].value = cpus[Number(value)];
            });
            $("#cpu:range").data().rangeinput.change(function(event,value){
                $("#custom").click();				
			});			
            $("#ram:range").data().rangeinput.onSlide(function(event,value){
                $("#ram-indicator")[0].value = ram[Number(value)];
            });
            $("#ram:range").data().rangeinput.change(function(event,value){
                $("#custom").click();
            });			
            $("#storage:range").data().rangeinput.onSlide(function(event,value){
                $("#storage-indicator")[0].value = disks[Number(value)];
            });
            $("#storage:range").data().rangeinput.change(function(event,value){
                $("#custom").click();
            });			
        }
    });
    return false;
}
// return flavorRef from cpu, disk, ram values
function identify_flavor(cpu, disk, ram){
    for (i=0;i<flavors.length;i++){
        if (flavors[i]['cpu'] == cpu && flavors[i]['disk']==disk && flavors[i]['ram']==ram) {
            return flavors[i]['id']
        }
    }
    return 0;
}

// update the actions in the 
function updateActions() {
	var states = [];
	var on = [];
	var checked = $("table.list-machines tbody input[type='checkbox']:checked");
	// disable all actions to begin with
	for (action in actions) {
		$("#action-" + action).removeClass('enabled');
	}

	// are there multiple machines selected?
	if (checked.length>1)
		states[0] = 'multiple';
	
	// check the states of selected machines
	checked.each(function(i,checkbox) {
		states[states.length] = checkbox.className;
		var ip = $("#" + checkbox.id.replace('input-','') + ".ip span.public").text();
		if (ip.replace('undefined','').length)
			states[states.length] = 'network';
	});

	// decide which actions should be enabled
	for (a in actions) {
		var enabled = false;
		for (var s =0; s<states.length; s++) {
			if (actions[a].indexOf(states[s]) != -1 ) {
				enabled = true;
			} else {
				enabled = false;
				break;
			}
		}
		if (enabled)
			on[on.length]=a;
	}
	// enable those actions
	for (action in on) {
		$("#action-" + on[action]).addClass('enabled');
	}
}

// reboot action
function reboot(serverIDs){
	if (!serverIDs.length){
		ajax_success('DEFAULT');
		return false;
	}	
    // ajax post reboot call
    var payload = {
        "reboot": {"type" : "HARD"}
    };
    serverID = serverIDs.pop();
	
	$.ajax({
		url: '/api/v1.0/servers/' + serverID + '/action',
		type: "POST",        
		dataType: "json",
		data: JSON.stringify(payload),
		timeout: TIMEOUT,
		error: function(jqXHR, textStatus, errorThrown) {
					ajax_error(jqXHR.status);
				},
		success: function(data, textStatus, jqXHR) {
					if ( jqXHR.status == '202') {
                        try {
                            console.info('rebooted ' + serverID);
                        } catch(err) {}   		
						reboot(serverIDs);
					} else {
						ajax_error(jqXHR.status);
					}
				}
    });

    return false;
}

// shutdown action
function shutdown(serverIDs) {
	if (!serverIDs.length){
		ajax_success('DEFAULT');
		return false;
	}
    // ajax post shutdown call
    var payload = {
        "shutdown": {"timeout" : "5"}
    };   

	serverID = serverIDs.pop()
    $.ajax({
	    url: '/api/v1.0/servers/' + serverID + '/action',
	    type: "POST",
	    dataType: "json",
        data: JSON.stringify(payload),
        timeout: TIMEOUT,
        error: function(jqXHR, textStatus, errorThrown) { 
                    ajax_error(jqXHR.status);
                    },
        success: function(data, textStatus, jqXHR) {
                    if ( jqXHR.status == '202') {
						try {
                            console.info('suspended ' + serverID);
                        } catch(err) {}       				
                        shutdown(serverIDs);
                    } else {
                        ajax_error(jqXHR.status);
                    }
                }             
    });

    return false;    
}

// destroy action
function destroy(serverIDs) {
	if (!serverIDs.length){
		ajax_success('DEFAULT');
		return false;
	}
    // ajax post destroy call can have an empty request body
    var payload = {};   

	serverID = serverIDs.pop()
    $.ajax({
	    url: '/api/v1.0/servers/' + serverID,
	    type: "DELETE",
	    dataType: "json",
        data: JSON.stringify(payload),
        timeout: TIMEOUT,
        error: function(jqXHR, textStatus, errorThrown) { 
                    ajax_error(jqXHR.status);
                    },
        success: function(data, textStatus, jqXHR) {
                    if ( jqXHR.status == '202') {
						try {
                            console.info('destroyed ' + serverID);
                        } catch (err) {}        				
                        destroy(serverIDs);
                    } else {
                        ajax_error(jqXHR.status);
                    }
                }             
    });

    return false;    
}

// start action
function start(serverIDs){
	if (!serverIDs.length){
		ajax_success('DEFAULT');
		return false;
	}	
    // ajax post start call
    var payload = {
        "start": {"type" : "NORMAL"}
    };   

	serverID = serverIDs.pop()
    $.ajax({
        url: '/api/v1.0/servers/' + serverID + '/action',
        type: "POST",
        dataType: "json",
        data: JSON.stringify(payload),
        timeout: TIMEOUT,
        error: function(jqXHR, textStatus, errorThrown) { 
                    ajax_error(jqXHR.status);
                    },
        success: function(data, textStatus, jqXHR) {
                    if ( jqXHR.status == '202') {
					    try {
                            console.info('started ' + serverID);
                        } catch(err) {}      		
                        start(serverIDs);
                    } else {
                        ajax_error(jqXHR.status);
                    }
                }
    });

    return false;
}
