//
// Copyright 2011 GRNET S.A. All rights reserved.
//
// Redistribution and use in source and binary forms, with or
// without modification, are permitted provided that the following
// conditions are met:
//
//   1. Redistributions of source code must retain the above
//      copyright notice, this list of conditions and the following
//      disclaimer.
//
//   2. Redistributions in binary form must reproduce the above
//      copyright notice, this list of conditions and the following
//      disclaimer in the documentation and/or other materials
//      provided with the distribution.
//
// THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
// OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
// WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
// PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
// CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
// SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
// LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
// USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
// AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
// LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
// ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
// POSSIBILITY OF SUCH DAMAGE.
//
// The views and conclusions contained in the software and
// documentation are those of the authors and should not be
// interpreted as representing official policies, either expressed
// or implied, of GRNET S.A.
//
var API_URL = "/api/v1.1";
var changes_since = 0, deferred = 0, update_request = false, load_request = false, pending_actions = [];
var flavors = [], images = [], servers = [], disks = [], cpus = [], ram = [];
var networks = [], networks_changes_since = 0;
var error_timeout = 20000;
var last_request = {};
var CHANGES_SINCE_ERRORS = 0;

$.ajaxSetup({
    'beforeSend': function(xhr) {
          // save ajax settings, we might need them for error reporting
          last_request = this;
          xhr.setRequestHeader("X-Auth-Token", $.cookie("X-Auth-Token"));

          // append the date the request initialized to the ajax settings
          try {
            this.date_sent = new Date();
          } catch (err) {
          }
            
          if (CHANGES_SINCE_ERRORS > 0 && changes_since) {
            CHANGES_SINCE_ERRORS = 0;
          }
    },

    // catch uncaught error requests
    // stop interaction and show only for the 5xx errors
    // refresh the page after 20secs
    error: function(jqXHR, textStatus, errorThrown) {

        // check if xhr is in valid state (no status property)
        try {
            var status = jqXHR.status;
        } catch (err) {
            return false;
        }

        // stop interaction for important (aka 500) error codes only
        if (jqXHR.status >= 500 && jqXHR.status < 600)
        {
            handle_api_error(-11, undefined, 'Unknown', jqXHR, textStatus, errorThrown, this);
        }

        // refresh after 10 seconds
        window.setTimeout("window.location.reload()", window.error_timeout);
    }
});

// generic api error handler
//
// code: error code (uid or http status)
// context: something to identify the object 
//          that the error occured to (e.g. vm id) 
// xhr: xhr object
// jquery_error_status: error identified by the jquery ("timeout", "error" etc.)
// jquery_error: error identified by the jquery ("timeout", "error" etc.)
// ajax_settings: the settings 
// 
function handle_api_error(code, context, action, xhr, 
                          jquery_error_status, jquery_error, ajax_settings) {
    
    // handle timeouts (only for repeated requests)
    if (jquery_error_status == "timeout" && ajax_settings && ajax_settings.repeated) {
        // do not show error for the first timeout
        if (TIMEOUTS_OCCURED < SKIP_TIMEOUTS) {
            TIMEOUTS_OCCURED += 1;
            return;
        }
    }

    if (jquery_error_status == "timeout") {
        ajax_settings.disable_report = true;
        ajax_error("TIMEOUT", context, action, "", ajax_settings);
        return;
    }

    try {
        // malformed changes-since request, skip only first request
        // then ui will try to get requests with no changes-since parameter set
        // if for some reason server responds with 400/changes-since error
        // fallback to error message
        if (xhr.status === 400 && xhr.responseText.indexOf("changes-since") > -1 && CHANGES_SINCE_ERRORS == 0) {
            CHANGES_SINCE_ERRORS += 1;
            changes_since = 0;
            return;
        }

        // 413 no need to show report
        if (xhr.status === 413) {
            ajax_settings.disable_report = true;
            ajax_settings.no_details = false;
        }

        ajax_error(xhr.status, context, action, xhr.responseText, ajax_settings);
    } catch (err) {
        ajax_error(code, context, action, "NETWORK ERROR", ajax_settings);
    }
}

Object.prototype.toString = function(o){
    
    var parse = function(_o){
        var a = [], t;
        for(var p in _o){
            if(_o.hasOwnProperty(p)){
                t = _o[p];
                if(t && typeof t == "object"){
                    a[a.length]= p + ":{ " + arguments.callee(t).join(", ") + "}";
                }
                else {
                    if(typeof t == "string"){
                        a[a.length] = [ p+ ": \"" + t.toString() + "\"" ];
                    }
                    else{
                        a[a.length] = [ p+ ": " + t.toString()];
                    }
                }
            }
        }
        return a;
        
    }
    return "{" + parse(o).join(", ") + "}";
   
}

// http://stackoverflow.com/questions/499126/jquery-set-cursor-position-in-text-area 
$.fn.setCursorPosition = function(pos) {
    if ($(this).get(0).setSelectionRange) {
      $(this).get(0).setSelectionRange(pos, pos);
    } else if ($(this).get(0).createTextRange) {
      var range = $(this).get(0).createTextRange();
      range.collapse(true);
      range.moveEnd('character', pos);
      range.moveStart('character', pos);
      range.select();
    }
}

// jquery show/hide events
var _oldshow = $.fn.show;
$.fn.show = function(speed, callback) {
    $(this).trigger('show');
    return _oldshow.apply(this,arguments);
}
var _oldhide = $.fn.hide;
$.fn.hide = function(speed, callback) {
    $(this).trigger('hide');
    return _oldhide.apply(this,arguments);
}

function ISODateString(d){
    //return a date in an ISO 8601 format using UTC.
    //do not include time zone info (Z) at the end
    //taken from the Mozilla Developer Center
    function pad(n){ return n<10 ? '0'+n : n }
    return  d.getUTCFullYear()+ '-' +
            pad(d.getUTCMonth()+1) + '-' +
            pad(d.getUTCDate()) + 'T' +
            pad(d.getUTCHours()) + ':' +
            pad(d.getUTCMinutes()) + ':' +
            pad(d.getUTCSeconds()) +'Z'
}

function parse_error(responseText, errorCode){
    var errors = [];
    try {
        responseObj = JSON.parse(responseText);
    }
    catch(err) {
        errors[0] = {'code': errorCode};
        return errors;
    }
    for (var err in responseObj){
        errors[errors.length] = responseObj[err];
    }
    return errors;
}

// indexOf prototype for IE
if (!Array.prototype.indexOf) {
  Array.prototype.indexOf = function(elt /*, from*/) {
    var len = this.length;
    var from = Number(arguments[1]) || 0;
    from = (from < 0)
         ? Math.ceil(from)
         : Math.floor(from);
    if (from < 0)
      from += len;

    for (; from < len; from++) {
      if (from in this &&
          this[from] === elt)
        return from;
    }
    return -1;
  };
}

// trim prototype for IE
if(typeof String.prototype.trim !== 'function') {
    String.prototype.trim = function() {
        return this.replace(/^\s+|\s+$/g, '');
    }
}

// simple string format helper (http://stackoverflow.com/questions/610406/javascript-equivalent-to-printf-string-format)
String.prototype.format = function() {
    var formatted = this;
    for (var i = 0; i < arguments.length; i++) {
        var regexp = new RegExp('\\{'+i+'\\}', 'gi');
        formatted = formatted.replace(regexp, arguments[i]);
    }
    return formatted;
};


function update_confirmations() {
    // hide all confirm boxes to begin with
    $('#machines-pane div.confirm_single').hide();
    $('#machines-pane div.confirm_multiple').hide();
    var action_type = [];
    // standard view or single view
    if ($.cookie("view") == '0' || $.cookie("view") == '2') {
        for (var i=0; i<pending_actions.length; i++) {
            // show single confirms
            if (pending_actions[i][0] == reboot) {
                action_type = "reboot";
            } else if (pending_actions[i][0] == shutdown) {
                action_type = "shutdown";
            } else if (pending_actions[i][0] == start) {
                action_type = "start";
            } else if (pending_actions[i][0] == open_console) {
                action_type = "console";
            } else {
                action_type = "destroy";
            }
            $("#machines-pane #" + pending_actions[i][1] +
            " div.action-container." + action_type + " div.confirm_single").show();
        }
    }
    // if more than one pending action show multiple confirm box
    if (pending_actions.length>1 || $.cookie("view") == '1' && pending_actions.length == 1){
        $('#machines-pane div.confirm_multiple span.actionLen').text(pending_actions.length);
        $('#machines-pane div.confirm_multiple').show();
    }
}

function update_network_confirmations(){
    // hide all confirm boxes to begin with
    $('#networks-pane div.confirm_multiple').hide();

    for (var i=0;i<pending_actions.length;i++){
        // show single confirms depending on the action
        if (pending_actions[i][0] == delete_network) {
            $("#networks-pane div.network#net-"+pending_actions[i][1]).children('.confirm_single').show();
        } else if (pending_actions[i][0] == remove_server_from_network) {
            $("#networks-pane div.network #net-"+pending_actions[i][1]+"-server-"+pending_actions[i][2]).children('.confirm_single').show();
        } // else {}
    }

    // if more than one pending action show multiple confirm box
    if (pending_actions.length > 1){
        $('#networks-pane div.confirm_multiple span.actionLen').text(pending_actions.length);
        $('#networks-pane div.confirm_multiple').show();
    }

    try {
        update_network_confirmations_position();
    } catch (err) { console.error(err) };
}

function list_view() {
    changes_since = 0; // to reload full list
    pending_actions = []; // clear pending actions
    update_confirmations();
    clearTimeout(deferred);    // clear old deferred calls
    try {
        update_request.abort(); // cancel pending ajax updates
        load_request.abort();
    }catch(err){}
    $.cookie("view", '1'); // set list cookie
    uri = $("a#list").attr("href");
    load_request = $.ajax({
        url: uri,
        type: "GET",
        timeout: TIMEOUT,
        dataType: "html",
        error: function(jqXHR, textStatus, errorThrown) {
            return false;
        },
        success: function(data, textStatus, jqXHR) {
            $("a#list")[0].className += ' activelink';
            $("a#standard")[0].className = '';
            $("a#single")[0].className = '';
            $("div#machinesview").html(data);
        }
    });
    return false;
}

function single_view() {
    changes_since = 0; // to reload full list
    pending_actions = []; // clear pending actions
    update_confirmations();
    clearTimeout(deferred);    // clear old deferred calls
    try {
        update_request.abort(); // cancel pending ajax updates
        load_request.abort();
    }catch(err){}
    $.cookie("view", '2'); // set list cookie
    uri = $("a#single").attr("href");
    load_request = $.ajax({
        url: uri,
        type: "GET",
        timeout: TIMEOUT,
        dataType: "html",
        error: function(jqXHR, textStatus, errorThrown) {
            return false;
        },
        success: function(data, textStatus, jqXHR) {
            $("a#single")[0].className += ' activelink';
            $("a#standard")[0].className = '';
            $("a#list")[0].className = '';
            $("div#machinesview").html(data);
        }
    });
    return false;
}

function standard_view() {
    changes_since = 0; // to reload full list
    pending_actions = []; // clear pending actions
    update_confirmations();
    clearTimeout(deferred);    // clear old deferred calls
    try {
        update_request.abort() // cancel pending ajax updates
        load_request.abort();
    }catch(err){}
    $.cookie("view", '0');
    uri = $("a#standard").attr("href");
    load_request = $.ajax({
        url: uri,
        type: "GET",
        timeout: TIMEOUT,
        dataType: "html",
        error: function(jqXHR, textStatus, errorThrown) {
            return false;
        },
        success: function(data, textStatus, jqXHR) {
            $("a#standard")[0].className += ' activelink';
            $("a#list")[0].className = '';
            $("a#single")[0].className = '';
            $("div#machinesview").html(data);
        }
    });
    return false;
}

function choose_view() {
    if ($.cookie("view")=='1') {
        list_view();
    } else if ($.cookie("view")=='2'){
        single_view();
    } else {
        standard_view();
    }
}

// return value from metadata key "OS", if it exists
function os_icon(metadata) {
    if (!metadata) {
        return 'okeanos';
    }
    if (metadata.values.OS == undefined || metadata.values.OS == '') {
        return 'okeanos';
    } else {
        if (os_icons.indexOf(metadata.values.OS) == -1) {
            return 'okeanos';
        } else {
            return metadata.values.OS;
        }
    }
}

function os_icon_from_value(metadata) {
    if (!metadata) {
        return 'okeanos';
    }
if (metadata == undefined || metadata == '') {
        return 'okeanos';
    } else {
        if (os_icons.indexOf(metadata) == -1) {
            return 'okeanos';
        } else {
            return metadata;
        }
    }
}

// get and show a list of running and terminated machines
function update_vms(interval) {
    try{ console.info('updating machines'); } catch(err){}
    var uri= API_URL + '/servers/detail';

    if (changes_since != 0)
        uri+='?changes-since='+changes_since
    
    update_request = $.ajax({
        repeated: true,
        cache: false,
        url: uri,
        type: "GET",
        timeout: TIMEOUT,
        dataType: "json",
        error: function(jqXHR, textStatus, errorThrown) {
            // don't forget to try again later
            if (interval) {
                clearTimeout(deferred);    // clear old deferred calls
                deferred = setTimeout(function() {update_vms(interval);},interval,interval);
            }
            // as for now, just show an error message
            try { console.info('update_vms errback:' + jqXHR.status ) } catch(err) {}

            handle_api_error(-12, undefined, 'Update VMs', jqXHR, textStatus, errorThrown, this);
            return false;
        },
        success: function(data, textStatus, jqXHR) {
            // create changes_since string if necessary
            if (jqXHR.getResponseHeader('Date') != null){
                changes_since_date = new Date(jqXHR.getResponseHeader('Date'));
                changes_since = ISODateString(changes_since_date);
            }
            
            if (interval) {
                clearTimeout(deferred);    // clear old deferred calls
                deferred = setTimeout(function() {update_vms(interval);},interval,interval);
            }

            if (jqXHR.status == 200 || jqXHR.status == 203) {
                try {
                    //servers = data.servers.values;
                    update_servers_data(data.servers.values, data);
                    update_machines_view(data);
                } catch (err) { ajax_error(-503, "UI Error", 'Update VMs', err, this);}
            } else if (jqXHR.status != 304){
                try { console.info('update_vms callback:' + jqXHR.status ) } catch(err) {}
                /*
                FIXME:  Here it should return the error, however Opera does not support 304.
                        Instead 304 it returns 0. To dealt with this we treat 0 as an
                        304, which should be corrected (Bug #317).
                */
                // ajax_error(jqXHR.status, "Ajax error", 'Update VMs', jqXHR.responseText);
            }
            return false;
        }
    });
    return false;
}

function update_servers_data(servers_update, data) {
    $(window).trigger("vm:update", servers_update, data);

    // first call
    if (!window.servers || window.servers.length == 0) {
        window.servers = servers_update;
        return;
    }
    
    // server exists helper
    server_exists = function(server) {
        var id = server.id;
        var found = false;
        var index = 0;
        $.each(servers, function(i, s) {
            if (s.id == id) { found = true, index = i };
        });
        if (found)
            return [found, index];

        return false;
    }

    // merge object properties
    merge = function() {
        var initial = arguments[0];
        var status_changed = undefined;
        $.each(arguments, function(index, el) {
            $.each(el, function(key,v) {
                // new attribute added
                var previous_value = initial[key];
                var v = v;
                if (initial[key] == undefined) {
                    $(window).trigger("vm:attr:add", initial, key, v);
                } else {
                    // value changed
                    if (initial[key] != v) {
                        if (key == "status") {
                            // dont change if in destroy state
                            if (initial.status == "DESTROY") {
                                v = "DESTROY";
                            }
                            status_changed = {'old': previous_value, 'new': v}; 
                        }

                        $(window).trigger("vm:attr:change", {'initial': initial, 'attr': key, 'newvalue': v});
                    }
                }
                initial[key] = v;
            });
        });
        if (status_changed !== undefined) {
            $(window).trigger('vm:status:change', {'vm': initial, 'old': status_changed['old'], 'new': status_changed['new']});
        }
        return initial;
    }
    
    // server removed
    var remove = [];
    $.each(servers_update, function(index, server) {
        if (server.status == "DELETED") {
            remove.push(server.id);
        }
    });
    
    // check if server is in transition, apply appropriate logic
    function update_server_transition(vm) {
        if (vm.state_transition == "DESTROY" && vm.status != "DELETE") {
            return;
        }

        if (vm.state_transition == "SHUTDOWN" && vm.state_transition == "ACTIVE") {
            return;
        } else {
            // clear transition
            vm.state_transition = false;
            return;
        }

        if (vm.state_transition == "START" && vm.state_transition == "STOPPED") {
            return;
        } else {
            // clear transition
            vm.state_transition = false;
            return;
        }
    }

    // check server, if exists merge it with new values else add it
    $.each(servers_update, function(index, server) {
        var exists = server_exists(server);
        var old_server = servers[exists[1]];

        // reset network transition
        try {
            if (old_server.network_transition) {
                if (old_server.network_transition == "NETWORK_CHANGE") {
                    // network profile changed, servers data updated, so act if the change was made
                    // this flag will trigger ui to remove any transiiton indicators
                    // and hopefully apply the new value to the profile options
                    old_server.network_transition = "CHANGED"
                } else {
                    // nothing happened
                    old_server.network_transition = undefined;
                };
            }
        } catch (err) {
            // no old server
        }

        if (exists !== false) {
            try {
                servers[exists[1]] = merge(servers[exists[1]], server);
                update_server_transition(servers[exists[1]]);
            } catch (err) {
            }
        } else {
            servers.push(server);
            $(window).trigger("vm:add", server);
        }
        if (remove.indexOf(server.id) > -1) {
            var remove_exists = server_exists(server);
            servers.splice(remove_exists[1], 1);
            $(window).trigger("vm:remove", server);
        }
    });
}

// get a list of running and terminated machines, used in network view
function update_networks(interval) {
    try{ console.info('updating networks'); } catch(err){}
    var uri= API_URL + '/servers/detail';

    if (changes_since != 0)
        uri+='?changes-since='+changes_since

    update_request = $.ajax({
        repeated: true,
        cache: false,
        url: uri,
        type: "GET",
        timeout: TIMEOUT,
        dataType: "json",
        error: function(jqXHR, textStatus, errorThrown) {
            // don't forget to try again later
            if (interval) {
                clearTimeout(deferred);    // clear old deferred calls
                deferred = setTimeout(function() {update_networks(interval);},interval);
            }
            // as for now, just show an error message
            try { console.info('update_networks errback:' + jqXHR.status ) } catch(err) {}

            handle_api_error(-13, undefined, 'Update networks', jqXHR, textStatus, errorThrown, this);
            return false;
            },
        success: function(data, textStatus, jqXHR) {
            // create changes_since string if necessary
            if (jqXHR.getResponseHeader('Date') != null){
                changes_since_date = new Date(jqXHR.getResponseHeader('Date'));
                changes_since = ISODateString(changes_since_date);
            }

            if (interval) {
                clearTimeout(deferred);    // clear old deferred calls
                deferred = setTimeout(function() {update_networks(interval);},interval,interval);
            }

            if (jqXHR.status == 200 || jqXHR.status == 203) {
                try {
                    //servers = data.servers.values;
                    update_servers_data(data.servers.values, data);
                    update_network_names(data);
                } catch(err) { ajax_error(-505, "UI Error", 'Update networks', err, this);}
            } else if (jqXHR.status == 304) {
                update_network_names();
            }
            else {
                try { console.info('update_networks callback:' + jqXHR.status ) } catch(err) {}
                /*
                FIXME:  Here it should return the error, however Opera does not support 304.
                        Instead 304 it returns 0. To dealt with this we treat 0 as an
                        304, which should be corrected (Bug #317).
                */
                //ajax_error(jqXHR.status, undefined, 'Update networks', jqXHR.responseText);
                update_network_names();
            }
            return false;
        }
    });
    return false;
}

// get and show a list of public and private networks
function update_network_names(servers_data) {
    try{ console.info('updating network names'); } catch(err){}
    var uri= API_URL + '/networks/detail';

    if (networks_changes_since != 0)
        //FIXME: Comment out the following, until metadata do not 304 when changed
        uri+='?changes-since=' + networks_changes_since

    update_request = $.ajax({
        cache: false,
        url: uri,
        type: "GET",
        timeout: TIMEOUT,
        dataType: "json",
        error: function(jqXHR, textStatus, errorThrown) {
            // as for now, just show an error message
            try {
                console.info('update_network names errback:' + jqXHR.status )
            } catch(err) {}

            handle_api_error(-14, undefined, 'Update network names', jqXHR, textStatus, errorThrown, this);
            return false;
        },
        success: function(data, textStatus, jqXHR) {
            // create changes_since string if necessary
            if (jqXHR.getResponseHeader('Date') != null){
                changes_since_date = new Date(jqXHR.getResponseHeader('Date'));
                networks_changes_since = ISODateString(changes_since_date);
            }

            if (jqXHR.status == 200 || jqXHR.status == 203) {
                try {
                    networks = data.networks.values;
                    update_networks_view(servers_data, data);
                } catch(err) {
                    ajax_error(-507, "UI Error", 'Update network names', err, this);
                }
            } else if (jqXHR.status == 304) {
                    update_networks_view(servers_data);
            } else if (jqXHR.status != 304){
                try { console.info('update_network_names callback:' + jqXHR.status ) } catch(err) {}
                /*
                FIXME:  Here it should return the error, however Opera does not support 304.
                        Instead 304 it returns 0. To dealt with this we treat 0 as an
                        304, which should be corrected (Bug #317).
                */
                //ajax_error(jqXHR.status, undefined, 'Update network names', jqXHR.responseText);
                update_networks_view(servers_data);
            }
            return false;
        }
    });
    return false;
}

// get and show a list of available standard and custom images
function update_images() {
    $.ajax({
        url: API_URL + '/images/detail',
        type: "GET",
        //async: false,
        dataType: "json",
        timeout: TIMEOUT,
        error: function(jqXHR, textStatus, errorThrown) {
            handle_api_error(-15, undefined, 'Update images', jqXHR, textStatus, errorThrown, this);
        },
        success: function(data, textStatus, jqXHR) {
            try {
                images = data.images.values;
                jQuery.parseJSON(data);
                update_wizard_images();

                // update images options
                update_image_flavor_options();
                handle_image_choice_changed();
            } catch(err){
                ajax_error("NO_IMAGES");
            }
        }
    });
    return false;
}

// update images panel
function update_wizard_images() {
    if ($("ul#standard-images li").toArray().length + $("ul#custom-images li").toArray().length == 0) {
        $.each(images, function(i,image){
            var img = $('#image-template').clone().attr("id","img-"+image.id).fadeIn("slow");
            img.find("label").attr('for',"img-radio-" + image.id);
            img.find(".image-title").text(image.name);
            if (image.metadata) {
                if (image.metadata.values.description != undefined) {
                    img.find(".description").text(image.metadata.values.description);
                }
                if (image.metadata.values.size != undefined) {
                    img.find("#size").text(image.metadata.values.size);
                }
            }
            img.find("input.radio").attr('id',"img-radio-" + image.id);
            if (i==0) img.find("input.radio").attr("checked","checked");
            var image_logo = os_icon(image.metadata);
            img.find("img.image-logo").attr('src','static/icons/os/'+image_logo+'.png');
            if (image.metadata) {
                if (image.metadata.values.serverId != undefined) {
                    img.appendTo("ul#custom-images");
                } else {
                    img.appendTo("ul#standard-images");
                }
            } else {
                img.appendTo("ul#standard-images");
            }
        });
        
        $(".image-container input[type=radio]").change(function(){
            handle_image_choice_changed();
        });
    }
}


// get closest value from specified percentage
function get_closest_option(perc, map) {
    min = 1;
    max = Math.max.apply(Math, map);
    
    // create a map with percentages
    perc_map = [];
    $.each(map, function(i,v) {
        perc_map[i] = parseInt(range_value_to_percentage(v, map));

    })
    
    perc_map = perc_map.sort(function(a,b){return a>b});
    // find closest percentage
    var close = perc_map[0];
    found = close;
    found_pos = 0;
    diff = Math.abs(close - perc);
    
    // get closest based on map values
    for (var i=1; i< perc_map.length; i++) {
        if (Math.abs(perc_map[i] - perc) > diff) {
            break;
        } else {
            found = perc_map[i];
            found_pos = i;
            diff = Math.abs(perc_map[i] - perc);
        }
    }
    
    var val = range_percentage_to_value(perc_map[found_pos], map);
    return val;
}

// get closest percentage from specified value
function get_closest_from_value(value, map) {
    var perc = range_value_to_percentage(value, map, false);
    var close_val = get_closest_option(perc, map);
    var value = range_value_to_percentage(close_val, map);
    return value;
}

// convert a range value (e.g. ram 1024) to percentage
function range_value_to_percentage(value, map, valid) {
    if (valid == undefined) { valid = true }
    var pos = map.indexOf(value)
    
    // do we need to validate that value is in the map
    if (pos == -1 && valid ) { return 0 }
    if (value == 1) { return 0; }
    if (pos == map.length -1) { return 100; }

    perc = value * (100 / Math.max.apply(Math, map));

    // fix for small fragmentations
    min = 1; max = Math.max.apply(Math, map);
    if (max - min <= 4) {
        perc = perc - 12
    }

    return perc;
} 

// get range value to display based on the percentage value
// of the range control
function range_percentage_to_value(value, map) {
    min = 0; max = Math.max.apply(Math, map);
    ret = Math.round(value * max / 100);
    
    // fix for small fragmentations
    if (max - min <= 4) { ret = ret; }
    if (ret < min) { ret = min; }
    if (ret >= max) { ret = max; }
    ret = ret;
    // 0 is not an option
    ret = ret == 0 ? 1: ret;
    return ret;
}

// get flavor unique index key
function get_flavor_index_key(flv) {
    return "cpu:" + flv.cpu + ":ram:" + flv.ram + ":disk:" + flv.disk
}

// update last creation step information
function update_creating_vm_details() {
    var flavor = get_flavor_sliders_values();
    var image = IMAGES_DATA[get_selected_image_id()].image;

    var cont = $("#page3-container");
    var image_name = cont.find("#machine_image-label");
    var cpu = cont.find("#machine_cpu-label");
    var ram = cont.find("#machine_ram-label");
    var disk = cont.find("#machine_storage-label");

    image_name.text(image.name);
    cpu.text(flavor.cpu);
    ram.text(flavor.ram);
    disk.text(flavor.disk);

    var name = "My " + image.name + " server";
    
    // check if server with predefined name already exists
    j = 2;
    if (servers) {
        var predefined_name = name;
        $.each(servers, function(index, el) {
            console.log(el.name, name);
            if (el.name == name) {
                name = predefined_name + " " + j;
                j++;
            }
        })
    }
    cont.find("input[type=text][name=machine_name]").val(name);
}

// create a map with available flavors for each image
function update_image_flavor_options() {
    // invalid state, do not update, 
    // wait for both images and flavors to get filled/updated
    if (!window.images || !window.flavors) {
        return
    }
    
    // create images flavors map
    var images_options = {};
    $.each(images, function(i, img) {
        images_options[img.id] = {flavors:{}, options:{cpu:[], ram:[], disk:[]}};
        // check disk usage
        var disk_limit = img.metadata.values.size;
        var image_flavors = {};
        var image_options = {cpu:[], ram:[], disk:[]};
        var flavor_combinations = [];
        var default_flavor = undefined;
        $.each(flavors, function(j, flv) {
            var disk = flv.disk * 1000;
            // flavor size can contain image size
            if (disk > disk_limit) {
                image_flavors[flv.id] = flv;
                image_options.cpu.push(flv.cpu)
                image_options.ram.push(flv.ram)
                image_options.disk.push(flv.disk)
                
                // create combinations indexes
                flavor_combinations.push(get_flavor_index_key(flv));
                default_flavor = default_flavor || flv;
            } else {
            }
        });
        
        // update image suggested flavors
        var suggested = [];
        $.each(SUGGESTED_FLAVORS, function(i, el) {
            // image contains suggested flavor ???
            if (flavor_combinations.indexOf(get_flavor_index_key(el)) > -1){
                suggested.push(i);
            }
        });

        // unique data
        image_options.cpu = image_options.cpu.unique();
        image_options.ram = image_options.ram.unique();
        image_options.disk = image_options.disk.unique();
        flavor_combinations = flavor_combinations.unique();
        
        // sort data
        var numeric_sort = function(a,b){return a>b};
        image_options.cpu = image_options.cpu.sort(numeric_sort);
        image_options.ram = image_options.ram.sort(numeric_sort);
        image_options.disk = image_options.disk.sort(numeric_sort);

        // append data
        images_options[img.id].flavors = image_flavors;
        images_options[img.id].options = image_options;
        images_options[img.id].image = img;
        images_options[img.id].flavors_index = flavor_combinations;
        images_options[img.id].default_flavor = default_flavor;
        images_options[img.id].suggested = suggested;
    })
    
    // export it to global namespace
    window.IMAGES_DATA = images_options;
}

// is flavor available for the specified image ???
function image_flavor_available(image_ref, flavor_object) {
    return IMAGES_DATA[image_ref].flavors_index.indexOf(get_flavor_index_key(flavor_object)) > -1;
}

// update sliders and flavor choices on ui
function handle_image_choice_changed() {
    try {
        validate_selected_flavor_options();
        repaint_flavor_choices();
        update_suggested_flavors();
    } catch (err) {
        //console.error(err);
    }
}

// disable/enable suggested flavor options (small/medium/large)
function update_suggested_flavors() {
    var img_id = get_selected_image_id();
    var img = IMAGES_DATA[img_id];
    
    // disable all
    $("#machinetype input[type=radio]").attr("disabled", "disabled").parent().addClass("disabled");
    
    $.each(SUGGESTED_FLAVORS, function(i, el) {
        if (img.suggested.indexOf(i) != -1) {
            $("#machinetype label input[value="+i+"]").attr("disabled", "").parent().removeClass("disabled");
        }
    })
    $("#machinetype label input[value=custom]").attr("disabled", "").parent().removeClass("disabled");

    // select first enabled
    $($("#machinetype input[type=radio]").not(":disabled")[0]).click();
}

// clear points
function clean_flavor_choice_points() {
    $(".slider-container .slider .slider-point").remove();
}

function repaint_flavor_choices() {
    clean_flavor_choice_points();
    var img = IMAGES_DATA[get_selected_image_id()];
    function paint_slider_points(slider, points) {
        $.each(points, function(i, point) {
             // proper width
             var width = slider.width() - slider.find(".handle").width();
             // progress number
             var progress = slider.find(".progress").width();
             // percentage based on value
             var perc = range_value_to_percentage(point, points);
             // position
             var pos = perc*width/100;
            
             // handlers
             var last = false;
             var first = false;
             if (pos == 0) { first - true; pos = 2}
             if (pos == width) { last = true; }
            
             // create pointer container and text
             var text = $('<span class="slider-point-text">' + point + '</span>');
             var span = $('<span class="slider-point"></span>').css("left", pos + "px").addClass(pos <= progress ? "slider-point-light": "");
             span.append(text);
             
             // wait for element to get dimensions
             setTimeout(function() {
                 // choose text pointer position
                 move = "-" + ($(text).width()/2 + 1) + "px";
                 if (last) { move = "-" + ($(text).width() - 2) +  "px"; }
                 if (first) { move = "0px"; }
                 $(text).css("margin-left", move);
             }, 100);
             // append to slider
             slider.append(span);
        });
    }
    
    // paint points for each slider
    paint_slider_points($("#cpu-indicator").parent().find(".slider"), img.options.cpu);
    paint_slider_points($("#storage-indicator").parent().find(".slider"), img.options.disk);
    paint_slider_points($("#ram-indicator").parent().find(".slider"), img.options.ram);
}

function validate_selected_flavor_options(selected) {
    var img = IMAGES_DATA[get_selected_image_id()];
    if (!check_selected_flavor_values()) {
        var flv = img.default_flavor;
        set_flavor_sliders_values(flv.cpu, flv.disk, flv.ram);
    }

    update_creating_vm_details();
}

// check if selected values are available
// as a flavor for the image
function check_selected_flavor_values() {
    var img = IMAGES_DATA[get_selected_image_id()];
    var values = get_flavor_sliders_values();
    var found = false;
    
    // index lookup
    if (img.flavors_index.indexOf(get_flavor_index_key(values)) > -1) {
        // return flavor id
        return identify_flavor(values.cpu, values.disk, values.ram);
    }
    
    return false;
}

// find which image is selected
// return the options requested available for this image
function get_selected_image_options(opt_name) {
    var img_id = get_selected_image_id();
    var img = IMAGES_DATA[img_id];
    return img.options[opt_name];
}

// identify selected image
function get_selected_image_id() {
    return $(".image-container input:checked").attr("id").replace("img-radio-", "");
}

function update_wizard_flavors(){
    
    // find max range values
    cpus_max = Math.max.apply(Math, cpus); 
    cpus_min = 1;

    disks_max = Math.max.apply(Math, disks);
    disks_min = 1;

    ram_max = Math.max.apply(Math, ram);
    ram_min = 1;
    
    // sliders for selecting VM flavor
    $("#cpu:range").rangeinput({min:1,
                               value:0,
                               step:1,
                               progress: true,
                               max:100});

    $("#storage:range").rangeinput({min:1,
                               value:0,
                               step:1,
                               progress: true,
                               max:100});

    $("#ram:range").rangeinput({min:1,
                               value:0,
                               step:1,
                               progress: true,
                               max:100});

    // update the indicators when sliding
    $("#cpu:range").data().rangeinput.onSlide(function(event,value){
        var cpus = get_selected_image_options("cpu");
        $("#cpu-indicator")[0].value = range_percentage_to_value(value, cpus);
        $("#cpu-indicator").addClass('selectedrange');
    });
    $("#cpu:range").data().rangeinput.change(function(event,value){
        var cpus = get_selected_image_options("cpu");
        $("#cpu-indicator")[0].value = range_percentage_to_value(value, cpus);
        normal_value = range_value_to_percentage(get_closest_option(value, cpus), cpus);
        if (this.getValue() != normal_value) {
            this.setValue(normal_value);
        }
        $("#custom").click();
        $("#cpu-indicator").removeClass('selectedrange');
        validate_selected_flavor_options("cpu");
    });
    $("#ram:range").data().rangeinput.onSlide(function(event,value){
        var ram = get_selected_image_options("ram");
        $("#ram-indicator")[0].value = range_percentage_to_value(value, ram);
        $("#ram-indicator").addClass('selectedrange');
    });
    $("#ram:range").data().rangeinput.change(function(event,value){
        var ram = get_selected_image_options("ram");
        $("#ram-indicator")[0].value = range_percentage_to_value(value, ram);
        normal_value = range_value_to_percentage(get_closest_option(value, ram), ram);
        if (this.getValue() != normal_value) {
            this.setValue(normal_value);
        }
        $("#custom").click();
        $("#ram-indicator").removeClass('selectedrange');
        validate_selected_flavor_options("ram");
    });
    $("#storage:range").data().rangeinput.onSlide(function(event,value){
        var disks = get_selected_image_options("disk")
        $("#storage-indicator")[0].value = range_percentage_to_value(value, disks);
        $("#storage-indicator").addClass('selectedrange');
    });
    $("#storage:range").data().rangeinput.change(function(event,value){
        var disks = get_selected_image_options("disk")
        $("#storage-indicator")[0].value = range_percentage_to_value(value, disks);
        normal_value = range_value_to_percentage(get_closest_option(value, disks), disks);
        if (this.getValue() != normal_value) {
            this.setValue(normal_value);
        }
        $("#custom").click();
        $("#storage-indicator").removeClass('selectedrange');
        validate_selected_flavor_options("disk");
    });
}

function get_flavor_slider(name) {
    return $("#" + name + ":range").data().rangeinput;
}

// utility function to grab the value of the slider
function get_flavor_slider_value(name) {
    var maps = {
        'cpu': cpus,
        'ram': ram,
        'storage': disks
    }
    return range_percentage_to_value(get_flavor_slider(name).getValue(), maps[name]);
}

function set_flavor_sliders_values(cpu, disk, ram) {
    get_flavor_slider("cpu").setValue(range_value_to_percentage(cpu, get_selected_image_options("cpu")));
    get_flavor_slider("storage").setValue(range_value_to_percentage(disk, get_selected_image_options("disk")));
    get_flavor_slider("ram").setValue(range_value_to_percentage(ram, get_selected_image_options("ram")));
}

function get_flavor_sliders_values() {
    return {
        'cpu': get_flavor_slider_value("cpu"),
        'ram': get_flavor_slider_value("ram"),
        'disk': get_flavor_slider_value("storage")
    }
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
        url: API_URL + '/flavors/detail',
        type: "GET",
        //async: false,
        dataType: "json",
        timeout: TIMEOUT,
        error: function(jqXHR, textStatus, errorThrown) {
            handle_api_error(-16, undefined, 'Update flavors', jqXHR, textStatus, errorThrown, this);
        },
        success: function(data, textStatus, jqXHR) {

            try {
                flavors = data.flavors.values;
                jQuery.parseJSON(data);
                $.each(flavors, function(i, flavor) {
                    cpus[i] = flavor['cpu'];
                    disks[i] = flavor['disk'];
                    ram[i] = flavor['ram'];
                });

                // we only need unique and sorted arrays
                cpus = cpus.unique();
                disks = disks.unique();
                ram = ram.unique();
                
                // sort arrays
                var numeric_sort = function(a,b) { return a>b};
                disks.sort(numeric_sort);
                cpus.sort(numeric_sort);
                ram.sort(numeric_sort);
            
                // ui update handlers
                update_wizard_flavors();
                update_image_flavor_options();
            } catch(err){
                ajax_error("NO_FLAVORS");
            }
            // start updating vm list
            update_vms(UPDATE_INTERVAL);
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

// return image entry from imageRef
function get_image(imageRef) {
    for (i=0;i<images.length;i++){
        if (images[i]['id'] == imageRef) {
            return images[i];
        }
    }
    return 0;
}

// return machine entry from serverID
function get_machine(serverID) {
    for (i=0;i<servers.length;i++){
        if (servers[i]['id'] == serverID) {
            return servers[i];
        }
    }
    return 0;
}

// helper function, returns the name of the current view
function get_current_view() {
    
    if ($.cookie('pane') == 1) {
        return "network"
    }

    if ($.cookie('pane') == 2) {
        return "disks"
    }
    
    switch ($.cookie('view')) {
        case "0":
            return "icon";
            break;
        case "1":
            return "list";
            break;
        case "2":
            return "single";
            break;
    }

    return false;
}

// update vms actions based on current view
function update_machine_actions(serverID, server_status) {
    var view = get_current_view();
    
    // call the proper update actions method
    if (['icon', 'single'].indexOf(view) > -1) {
        update_iconview_actions(serverID, server_status);
    } else if (['list'].indexOf(view) > -1) {
        update_listview_actions();
    }
}

// update the actions in icon view, per server
function update_iconview_actions(serverID, server_status) {

    // vm in destroy status ???
    var vm = get_machine(serverID)
    if (vm.state_transition == "DESTROY") {
        server_status = "DESTROY";
    }

    if ($.cookie("view")=='2') {
        // remove .disable from all actions to begin with
        $('#machinesview-single #' + serverID + ' div.single-action').show();
        // decide which actions should be disabled
        for (current_action in actions) {
            if (actions[current_action].indexOf(server_status) == -1 ) {
                $('#machinesview-single #' + serverID + ' div.action-' + current_action).hide();
            }
        }
    } else {
        // remove .disable from all actions to begin with
        $('#machinesview-icon.standard #' + serverID + ' div.actions').find('a').removeClass('disabled');
        // decide which actions should be disabled
        for (current_action in actions) {
            if (actions[current_action].indexOf(server_status) == -1 ) {
                $('#machinesview-icon.standard #' + serverID + ' a.action-' + current_action).addClass('disabled');
            }
        }
    }
}

// update the actions in list view
function update_listview_actions() {
    var states = [];
    var on = [];
    var checked = $("table.list-machines tbody input[type='checkbox']:checked");
    // disable all actions to begin with
    $('#machinesview .list div.actions').children().removeClass('enabled');

    // are there multiple machines selected?
    if (checked.length>1)
        states[0] = 'multiple';

    // check the states of selected machines
    checked.each(function(i,checkbox) {

        // force destroy mode
        var vm = get_machine(checkbox.id);
        if (vm.state_transition == "DESTROY") {
            states[states.length] = "DESTROY";
        } else {
            states[states.length] = checkbox.className;
        }

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

// return a metadata dict containing the metadata
// that should be cloned from image to vm
function get_image_metadata_to_copy(imageRef) {
    var image = IMAGES_DATA[imageRef].image;
    var metadata = image.metadata;

    // if no metadata return empty object
    if (!metadata || !metadata.values) {
        return {};
    }
    
    var vm_meta = {};
    // find existing keys, copy their values to the server
    // metadata object
    $.each(VM_IMAGE_COMMON_METADATA, function(index, key) {
        if (metadata.values[key] !== undefined) {
            vm_meta[key] = metadata.values[key];
        }
    })

    return vm_meta;
}
//create server action
function create_vm(machineName, imageRef, flavorRef) {
    var image_logo = os_icon(get_image(imageRef).metadata);
    var uri = API_URL + '/servers';

    var vm_meta = get_image_metadata_to_copy(imageRef);

    var payload = {
        "server": {
            "name": machineName,
            "imageRef": imageRef,
            "flavorRef" : flavorRef,
            "metadata" : vm_meta
        }
    };

    $.ajax({
    url: uri,
    type: "POST",
    contentType: "application/json",
    dataType: "json",
    data: JSON.stringify(payload),
    timeout: TIMEOUT,
    error: function(jqXHR, textStatus, errorThrown) {
                // close wizard and show error box
                $('#machines-pane a#create').data('overlay').close();
                handle_api_error(-17, undefined, 'Create VM', jqXHR, textStatus, errorThrown, this);
           },
    success: function(data, textStatus, jqXHR) {
                if ( jqXHR.status == '202') {
                    ajax_success("CREATE_VM_SUCCESS", data.server.adminPass);
                } else {
                    // close wizard and show error box
                    $('#machines-pane a#create').data('overlay').close();
                    ajax_error(jqXHR.status, undefined, 'Create VM', jqXHR.responseText, this);
                }
            }
    });
}

// reboot action
function reboot(serverIDs){
    if (!serverIDs.length){
        //ajax_success('DEFAULT');
        return false;
    }
    // ajax post reboot call
    var payload = {
        "reboot": {"type" : "HARD"}
    };

    var serverID = serverIDs.pop();

    $.ajax({
        url: API_URL + '/servers/' + serverID + '/action',
        type: "POST",
        contentType: "application/json",
        dataType: "json",
        data: JSON.stringify(payload),
        timeout: TIMEOUT,
        error: function(jqXHR, textStatus, errorThrown) {
                    // in machine views
                    if ( $.cookie("pane") == 0) {
                        try {
                            display_failure(jqXHR.status, serverID, 'Reboot', jqXHR.responseText);
                        } catch (err) {
                            display_failure(0, serverID, 'Reboot', jqXHR.responseText);
                        }
                    }
                    // in network view
                    else {
                        try {
                            display_reboot_failure(jqXHR.status, serverID, jqXHR.responseText);
                        } catch (err) {
                            display_reboot_failure(0, serverID, jqXHR.responseText);
                        }
                    }
                },
        success: function(data, textStatus, jqXHR) {
                    if ( jqXHR.status == '202') {
                        try {
                            console.info('rebooted ' + serverID);
                        } catch(err) {}
                        // indicate that the action succeeded
                        // in machine views
                        if ( $.cookie("pane") == 0) {
                            display_success(serverID);
                        }
                        // in network view
                        else {
                            display_reboot_success(serverID);
                        }
                        // continue with the rest of the servers
                        reboot(serverIDs);
                    } else {
                        ajax_error(jqXHR.status, serverID, 'Reboot', jqXHR.responseText, this);
                    }
                }
    });
    return false;
}

// shutdown action
function shutdown(serverIDs) {
    if (!serverIDs.length){
        //ajax_success('DEFAULT');
        return false;
    }
    // ajax post shutdown call
    var payload = {
        "shutdown": {}
    };

    var serverID = serverIDs.pop();

    $.ajax({
        url: API_URL + '/servers/' + serverID + '/action',
        type: "POST",
        contentType: "application/json",
        dataType: "json",
        data: JSON.stringify(payload),
        timeout: TIMEOUT,
        error: function(jqXHR, textStatus, errorThrown) {
                    try {
                        display_failure(jqXHR.status, serverID, 'Shutdown', jqXHR.responseText);
                    } catch(err) {
                        display_failure(0, serverID, 'Shutdown', jqXHR.responseText);
                    }
                },
        success: function(data, textStatus, jqXHR) {
                    if ( jqXHR.status == '202') {
                        try {
                            console.info('suspended ' + serverID);
                        } catch(err) {}
                        // indicate that the action succeeded
                        var vm = get_machine(serverID);
                        vm.state_transition = "SHUTDOWN";

                        display_success(serverID);
                        // continue with the rest of the servers
                        shutdown(serverIDs);
                    } else {
                        ajax_error(jqXHR.status, serverID, 'Shutdown', jqXHR.responseText, this);
                    }
                }
    });
    return false;
}

// destroy action
function destroy(serverIDs) {
    if (!serverIDs.length){
        //ajax_success('DEFAULT');
        return false;
    }
    // ajax post destroy call can have an empty request body
    var payload = {};

    var serverID = serverIDs.pop();

    $.ajax({
        url: API_URL + '/servers/' + serverID,
        type: "DELETE",
        contentType: "application/json",
        dataType: "json",
        data: JSON.stringify(payload),
        timeout: TIMEOUT,
        error: function(jqXHR, textStatus, errorThrown) {
                    try {
                        display_failure(jqXHR.status, serverID, 'Destroy', jqXHR.responseText);
                    } catch(err) {
                        display_failure(0, serverID, 'Destroy', jqXHR.responseText);
                    }
                },
        success: function(data, textStatus, jqXHR) {
                    if ( jqXHR.status == '204') {
                        try {
                            console.info('destroyed ' + serverID);
                        } catch (err) {}

                        // update status on local storage object
                        vm = get_machine(serverID);
                        vm.status = "DESTROY";
                        vm.state_transition = "DESTROY";
                        
                        // state changed, update actions
                        update_machine_actions(serverID, vm.status);

                        // indicate that the action succeeded
                        display_success(serverID);
                        // continue with the rest of the servers
                        destroy(serverIDs);
                    } else {
                        ajax_error(jqXHR.status, serverID, 'Destroy', jqXHR.responseText, this);
                    }
                }
    });
    return false;
}

// start action
function start(serverIDs){
    if (!serverIDs.length){
        //ajax_success('DEFAULT');
        return false;
    }
    // ajax post start call
    var payload = {
        "start": {}
    };

    var serverID = serverIDs.pop();

    $.ajax({
        url: API_URL + '/servers/' + serverID + '/action',
        type: "POST",
        contentType: "application/json",
        dataType: "json",
        data: JSON.stringify(payload),
        timeout: TIMEOUT,
        error: function(jqXHR, textStatus, errorThrown) {
                    try {
                        display_failure(jqXHR.status, serverID, 'Start', jqXHR.responseText);
                    } catch(err) {
                        display_failure(0, serverID, 'Start', jqXHR.responseText);
                    }
                },
        success: function(data, textStatus, jqXHR) {
                    if ( jqXHR.status == '202') {
                        try {
                            console.info('started ' + serverID);
                        } catch(err) {}
                        var vm = get_machine(serverID);
                        vm.state_transition = "START";
                        // indicate that the action succeeded
                        display_success(serverID);
                        // continue with the rest of the servers
                        start(serverIDs);
                    } else {
                        ajax_error(jqXHR.status, serverID, 'Start', jqXHR.responseText, this);
                    }
                }
    });
    return false;
}

// Show VNC console
function vnc_attachment(host, port, password) {
    // FIXME: Must be made into parameters, in settings.py
    //vnc = open("", "displayWindow",
    //    "status=yes,toolbar=yes,menubar=yes");
    vd = document.open("application/x-vnc");

    vd.writeln("[connection]");
    vd.writeln("host=" + host);
    vd.writeln("port=" + port);
    vd.writeln("password=" + password);

    vd.close();
}

// Show VNC console
function show_vnc_console(serverID, serverName, serverIP, host, port, password) {
    var params_url = '?machine=' + serverName + '&host_ip=' + serverIP.v4 + '&host_ip_v6=' + serverIP.v6 + '&host=' + host + '&port=' + port + '&password=' + password;
    var params_window = 'scrollbars=no,' +
                        'menubar=no,' +
                        'toolbar=no,' +
                        'status=no,' +
                        'top=0,' +
                        'left=0,' +
                        'height=' + screen.height + ',' +
                        'width=' + screen.width + ',' +
                        'fullscreen=yes';
    
    var url = 'machines/console' + params_url;
    window.open(url, 'formresult' + serverID, params_window);

    // Restore os icon in list view
    osIcon = $('#'+serverID).parent().parent().find('.list-logo');
    osIcon.attr('src',osIcon.attr('os'));
    return false;
}

// console action
function open_console(serverIDs){
    if (!serverIDs.length){
        //ajax_success('DEFAULT');
        return false;
    }
    // ajax post start call
    var payload = {
        "console": {"type": "vnc"}
    };

    var serverID = serverIDs.pop();

    var machine = get_machine(serverID);
    var serverName = machine.name;
    try {
        var serverIP = {};
        serverIP.v4 = machine.addresses.values[0].values[0].addr;
        serverIP.v6 = machine.addresses.values[0].values[1].addr;
    } catch(err) { var serverIP = 'undefined'; }

    $.ajax({
        url: API_URL + '/servers/' + serverID + '/action',
        type: "POST",
        contentType: "application/json",
        dataType: "json",
        data: JSON.stringify(payload),
        timeout: TIMEOUT,
        error: function(jqXHR, textStatus, errorThrown) {
                    try {
                        display_failure(jqXHR.status, serverID, 'Console', jqXHR.responseText);
                    } catch(err) {
                        display_failure(0, serverID, 'Console', jqXHR.responseText);
                    }
                },
        success: function(data, textStatus, jqXHR) {
                    if ( jqXHR.status == '200') {
                        try {
                            console.info('got_console ' + serverID);
                        } catch(err) {}
                        // indicate that the action succeeded
                        // show_vnc_console(serverID, serverName, serverIP,
                        // data.console.host,data.console.port,data.console.password);
                        show_vnc_console(serverID, serverName, serverIP,
                                         data.console.host,data.console.port,data.console.password);
                        display_success(serverID);
                        // hide spinner
                        $('#' + serverID + ' .spinner').hide();
                        // continue with the rest of the servers
                        open_console(serverIDs);
                    } else {
                        ajax_error(jqXHR.status, serverID, 'Console', jqXHR.responseText, this);
                    }
                }
    });
    return false;
}

function vm_has_address(vmId) {
    var vm = get_machine(vmId);

    if (!vm) return false;

    try {
        var ip = vm.addresses.values[0].values[0].addr;
    } catch (err) {
        return false;
    }
    return ip;
}

// connect to machine action
function machine_connect(serverIDs){
    if (!serverIDs.length){
        //ajax_success('DEFAULT');
        return false;
    }
    
    // prefer metadata values for specific options (username, domain)
    var username_meta_key = 'loginname';
    var domain_meta_key = "logindomain";

    var serverID = serverIDs.pop();
    var machine = get_machine(serverID);
    var serverName = machine.name;
    
    try {
        var serverIP = machine.addresses.values[0].values[0].addr;
    } catch (err) { var serverIP = 'undefined'; }

    try {
        var os = os_icon(machine.metadata);
    } catch (err) { var os = 'undefined'; }

    var username = "";
    try {
        username = machine.metadata.values[username_meta_key];
    } catch (err) { username = undefined }

    var domain = "";
    try {
        domain = machine.metadata.values[domain_meta_key];
    } catch (erro) { domain = undefined }

    var params_url = '?ip_address=' + serverIP + '&os=' + os + "&host_os=" + $.client.os + "&srv=" + serverID;

    if (username) {
        params_url += "&username=" + username;
    }

    if (domain) {
        params_url += "&domain=" + domain;
    }
    
    //if ($.client.os == "Windows" && os == "windows") {
        //// request rdp file
        //window.open('machines/connect' + params_url + "&rdp=1");
        //return;
    //}
    
    // FIXME: I18n ???
    var title = 'Connect to: ' + '<span class="machine-title"><img src="static/icons/machines/small/'+os+'-on.png" /> ' + fix_server_name(serverName) + '</span>';
    
    // open msg box and fill it with json data retrieved from connect machine view
    try {
        // open msg box
        msg_box({
            title:title, 
            fixed: true,
            content:'loading...',
            extra:'', 'ajax':'machines/connect' + params_url,
            parse_data:function(data){
                var box_content = "<a href='"+data.link.url+"'>"+data.link.title+"</a>";
                if (!data.link.url) {
                    box_content = "<span class='cmd'>"+data.link.title+"</span>";
                }
                data.title = false;
                data.content = data.info;
                data.extra = box_content;
                return data;
            }
        });
    } catch (error) {
        // if msg box fails fallback redirecting the user to the connect url
        window.open('machines/connect' + params_url);
    }


    // Restore os icon in list view
    osIcon = $('#'+serverID).parent().parent().find('.list-logo');
    osIcon.attr('src',osIcon.attr('os'));

    return false;
}


// rename server
function rename(serverID, serverName){
    if (!serverID.length){
        //ajax_success('DEFAULT');
        return false;
    }
    // ajax post rename call
    var payload = {
        "server": {"name": serverName}
    };

    $.ajax({
        url: API_URL + '/servers/' + serverID,
        type: "PUT",
        contentType: "application/json",
        dataType: "json",
        data: JSON.stringify(payload),
        timeout: TIMEOUT,
        error: function(jqXHR, textStatus, errorThrown) {
                    try {
                        display_failure(jqXHR.status, serverID, 'Rename', jqXHR.responseText);
                    } catch(err) {
                        display_failure(0, serverID, 'Rename', jqXHR.responseText);
                    }
                },
        success: function(data, textStatus, jqXHR) {
                    if ( jqXHR.status == '204' || jqXHR.status == '1223') {
                        try {
                            console.info('renamed ' + serverID);
                        } catch(err) {}
                        // indicate that the action succeeded
                        display_success(serverID);
                    } else {
                        ajax_error(jqXHR.status, serverID, 'Rename', jqXHR.responseText, this);
                    }
                }
    });
    return false;
}

// get server metadata
function get_metadata(serverID, keys_only) {
    $.ajax({
        url: API_URL + '/servers/' + serverID + '/meta',
        cache: false,
        type: "GET",
        //async: false,
        dataType: "json",
        timeout: TIMEOUT,
        error: function(jqXHR, textStatus, errorThrown) {
            $("a#metadata-scrollable").data('overlay').close();
            handle_api_error(-18, undefined, 'Get metadata', jqXHR, textStatus, errorThrown, this);
        },
        success: function(data, textStatus, jqXHR) {
            // to list the new results in the edit dialog
            if (keys_only) {
                list_metadata_keys(serverID, data.metadata.values);
            } else {
                list_metadata(data);
                list_metadata_keys(serverID, data.metadata.values);
            }
            //hide spinner
            $('#metadata-wizard .large-spinner').hide();
        }
    });
    return false;
}

// delete metadata key-value pair
function delete_metadata(serverID, meta_key) {
    $.ajax({
        url: API_URL + '/servers/' + serverID + '/meta/' + meta_key,
        type: "DELETE",
        //async: false,
        dataType: "json",
        timeout: TIMEOUT,
        error: function(jqXHR, textStatus, errorThrown) {
            $("a#metadata-scrollable").data('overlay').close();
            handle_api_error(-19, undefined, 'Delete metadata', jqXHR, textStatus, errorThrown, this);
        },
        success: function(data, textStatus, jqXHR) {
                    // success: Do nothing, the UI is already updated
        }
    });
    return false;
}

// add metadata key-value pair
function update_metadata(serverID, meta_key, meta_value) {
    var payload = {
        "meta": {
        }
    };
    payload["meta"][meta_key] = meta_value;

    $.ajax({
        url: API_URL + '/servers/' + serverID + '/meta/' + meta_key,
        type: "PUT",
        contentType: "application/json",
        dataType: "json",
        data: JSON.stringify(payload),
        timeout: TIMEOUT,
        error: function(jqXHR, textStatus, errorThrown) {
            $("a#metadata-scrollable").data('overlay').close();
            handle_api_error(-20, undefined, 'Update metadata', jqXHR, textStatus, errorThrown, this);
        },
        success: function(data, textStatus, jqXHR) {
            // success: Update icons if meta key is OS
            if (meta_key == "OS") {
                $("#metadata-wizard .machine-icon").attr("src","static/icons/machines/small/" + os_icon_from_value(meta_value) + '-' + $("#metadata-wizard div#on-off").text() + '.png');
                var machine_icon = $("#machinesview-icon").find("div#" + serverID);
                var machine_single = $("#machinesview-single").find("div#" + serverID);

                var os = os_icon_from_value(meta_value);
                var state = $("#metadata-wizard div#on-off").text()
                var state_single = $(".state", machine_single).hasClass("terminated-state") ? "off" : "on";

                set_machine_os_image(machine_icon, "icon", state, os);
                set_machine_os_image(machine_single, "single", state_single, os);
            }
        }
    });
    return false;
}

// get stats
function get_server_stats(serverID) {
    
    // do not update stats if machine in build state
    var vm = get_machine(serverID);
    if (vm.status == "BUILD" && vm.stats_timeout) {
        els = get_current_view_stats_elements(vm.id);
        els.cpu.img.hide();
        els.net.img.hide();

        els.cpu.busy.show();
        els.net.busy.show();
        return;
    }

    $.ajax({
        repeated: true,
        url: API_URL + '/servers/' + serverID + '/stats',
        cache: false,
        type: "GET",
        //async: false,
        dataType: "json",
        timeout: TIMEOUT,
        error: function(jqXHR, textStatus, errorThrown) {
            handle_api_error(-21, undefined, 'Get server stats', jqXHR, textStatus, errorThrown, this);
        },
        success: function(data, textStatus, jqXHR) {
            update_machine_stats(serverID, data);
        },

        // pass server id to ajax settings
        serverID: serverID
    });
    return false;
}

// set timeout function to update machine stats
function set_stats_update_handler(vm_id, interval, clear) {
    var vm = get_machine(vm_id);

    if (clear) {
        window.clearInterval(vm.stats_timeout);
        vm.stats_timeout = false;
        return;
    }
    
    if (!vm.stats_timeout) {
        vm.stats_timeout = window.setInterval(function(){
            get_server_stats(vm_id);
        }, interval * 1000);
    }
}

// update machine stats
// call set_stats_update_handler if machine stats are visible
// to reupdate the stats (based on api interval)
function update_machine_stats(vm_id, data) {
    var els = get_current_view_stats_elements(vm_id);
    var from_error = false;
    var vm = get_machine(vm_id);    
    var clear = false;

    // stats container is hidden
    // do not update the stats
    if (!els || els.cont.length == 0 || !els.cont.is(":visible")) {
        clear = true;
    }
    
    // view changed and vm stats not visible now, clear interval
    if (clear) {
        set_stats_update_handler(vm_id, data.stats.refresh, clear);
        return;
    }
    
    // api error
    if (!data) {
        from_error = true;
    }

    // hide helpers
    function hide_imgs(els) {
        els.cpu.img.hide();
        els.net.img.hide();
    }

    function hide_busy(els) {
        els.cpu.busy.hide();
        els.net.busy.hide();
    }

    function hide_errors(els) {
        els.cpu.error.hide();
        els.net.error.hide();
    }

    // apply logic
    if (from_error) {
        // api call returned error show error messages
        clear = true;
    } else {
        // no need to show stats while machine in building state
        if (vm.status == "BUILD") {
            hide_imgs(els);
            hide_errors(els);
            els.cpu.busy.show();
            els.net.busy.show();
        } else {
            hide_busy(els);

            // update stats, decide for series or bar image
            // based on img class
            if (els.cpu.img.hasClass("series")) {
                els.cpu.img.attr("src", data.stats.cpuTimeSeries);
            } else {
                els.cpu.img.attr("src", data.stats.cpuBar);
            }

            if (els.net.img.hasClass("series")) {
                els.net.img.attr("src", data.stats.netTimeSeries);
            } else {
                els.net.img.attr("src", data.stats.netBar);
            }
        }
    }

    
    // set timeout to call the stats update
    set_stats_update_handler(vm_id, data.stats.refresh, clear);
}


// get stats elements based on current view
function get_current_view_stats_elements(vm_id) {
        // in icon view
        if ( $.cookie('view') == 0 ) {
            vm_el = $("#" + vm_id);
            return {
                'cont': vm_el.find('.vm-stats'),
                'cpu': {
                    'img': vm_el.find(' img.cpu'), 
                    'busy': vm_el.find('.cpu-cont .stat-busy'),
                    'error': vm_el.find('.cpu-cont .stat-error')
                },
                'net': { 
                    'img': vm_el.find('img.net'),
                    'busy': vm_el.find('.net-cont .stat-busy'),
                    'error': vm_el.find('.net-cont .stat-error')
                }
            }
        }
        // in single view
        else if ( $.cookie('view') == 2 ) {
            vm_el = $("#" + vm_id);
            return {
                'cont': vm_el.find('.lower'),
                'cpu': {
                    'img': vm_el.find('div.cpu-graph img.stats'), 
                    'busy': vm_el.find('div.cpu-graph img.stat-busy'),
                    'error': vm_el.find('div.cpu-graph .stat-error')
                },
                'net': { 
                    'img': vm_el.find('div.network-graph img.stats'),
                    'busy': vm_el.find('div.network-graph img.stat-busy'),
                    'error': vm_el.find('div.network-graph .stat-error')
                }
            }
        }
}

// create network
function create_network(networkName){
    // ajax post start call
    var payload = {
        "network": { "name": networkName }
    };

    $.ajax({
        url: API_URL + '/networks',
        type: "POST",
        contentType: "application/json",
        dataType: "json",
        data: JSON.stringify(payload),
        timeout: TIMEOUT,
        error: function(jqXHR, textStatus, errorThrown) {
            $("a#networkscreate").overlay().close();
            handle_api_error(-22, undefined, 'Create network', jqXHR, textStatus, errorThrown, this);
        },
        success: function(data, textStatus, jqXHR) {
            if ( jqXHR.status == '202') {
                try {
                    console.info('created network ' + networkName);
                } catch(err) {}
                /*
                On success of this call nothing happens.
                When the UI gets the first update containing the created server,
                the creation wizard is closed and the new network is inserted
                to the DOM. This is done in update_networks_view()
                */
            } else {
                // close wizard and show error box
                $("a#networkscreate").overlay().close();
                ajax_error(jqXHR.status, undefined, 'Create network', jqXHR.responseText, this);
            }
        }
    });
    return false;
}

// rename network
function rename_network(networkID, networkName){
    if (!networkID.length){
        //ajax_success('DEFAULT');
        return false;
    }
    // prepare payload
    var payload = {
        "network": {"name": networkName}
    };
    // ajax call
    $.ajax({
        url: API_URL + '/networks/' + networkID,
        type: "PUT",
        contentType: "application/json",
        dataType: "json",
        data: JSON.stringify(payload),
        timeout: TIMEOUT,
        error: function(jqXHR, textStatus, errorThrown) {
            handle_api_error(-23, undefined, 'Rename network', jqXHR, textStatus, errorThrown, this);
        },
        success: function(data, textStatus, jqXHR) {
            if ( jqXHR.status == '204') {
                try {
                    console.info('renamed network' + networkID);
                } catch(err) {}
            } else {
                ajax_error(jqXHR.status, undefined, 'Rename network', jqXHR.responseText, this);
            }
        }
    });
    return false;
}

function delete_network(networkIDs){
    if (!networkIDs.length){
        //ajax_success('DEFAULT');
        return false;
    }
    // get a network
    var networkID = networkIDs.pop();
    // ajax post destroy call can have an empty request body
    var payload = {};
    // ajax call
    $.ajax({
        url: API_URL + '/networks/' + networkID,
        type: "DELETE",
        contentType: "application/json",
        dataType: "json",
        data: JSON.stringify(payload),
        timeout: TIMEOUT,
        error: function(jqXHR, textStatus, errorThrown) {
            try {
                display_net_failure(jqXHR.status, networkID, 'Delete', jqXHR.responseText);
            } catch (err) {
                display_net_failure(0, networkID, 'Delete', jqXHR.responseText);
            }
        },
        success: function(data, textStatus, jqXHR) {
            if ( jqXHR.status == '204') {
                try {
                    console.info('deleted network ' + networkID);
                } catch(err) {}
                // continue with the rest of the servers
                delete_network(networkIDs);
            } else {
                try {
                    display_net_failure(jqXHR.status, networkID, 'Delete', jqXHR.responseText);
                } catch (err) {
                    display_net_failure(0, networkID, 'Delete', jqXHR.responseText);
                }
            }
        }
    });
    return false;
}

function add_server_to_network(networkID, serverIDs, serverNames, serverStates) {
    if (!serverIDs.length){
        // close the overlay when all the calls are made
        $("a#add-machines-overlay").overlay().close();
        return false;
    }
    // get a server
    var serverID = serverIDs.pop();
    var serverName = serverNames.pop();
    var serverState = serverStates.pop();
    // prepare payload
    var payload = {
            "add": { "serverRef": serverID }
        };
    // prepare ajax call
    $.ajax({
        url: API_URL + '/networks/' + networkID + '/action',
        type: "POST",
        contentType: "application/json",
        dataType: "json",
        data: JSON.stringify(payload),
        timeout: TIMEOUT,
        error: function(jqXHR, textStatus, errorThrown) {
            $("a#add-machines-overlay").data('overlay').close();
            handle_api_error(-24, undefined, 'Add server to network', jqXHR, textStatus, errorThrown, this);
        },
        success: function(data, textStatus, jqXHR) {
            if ( jqXHR.status == '202') {
                try {
                    console.info('added server ' + serverID + ' to network ' + networkID);
                } catch(err) {}
                // toggle the reboot dialog
                display_reboot_dialog(networkID, serverID, serverName, serverState);
                // continue with the rest of the servers
                add_server_to_network(networkID, serverIDs, serverNames, serverStates);
            } else {
                // close wizard and show error box
                $("a#add-machines-overlay").data('overlay').close();
                ajax_error(jqXHR.status, undefined, 'Add server to network', jqXHR.responseText, this);
            }
        }
    });
    return false;
}

function remove_server_from_network(networkIDs, serverIDs, serverNames, serverStates) {
    if (!networkIDs.length){
        //ajax_success('DEFAULT');
        return false;
    }
    // get a network and a server
    var networkID = networkIDs.pop();
    var serverID = serverIDs.pop();
    var serverName = serverNames.pop();
    var serverState = serverStates.pop();
    // prepare payload
    var payload = {
            "remove": { "serverRef": serverID }
        };
    // prepare ajax call
    $.ajax({
        url: API_URL + '/networks/' + networkID + '/action',
        type: "POST",
        contentType: "application/json",
        dataType: "json",
        data: JSON.stringify(payload),
        timeout: TIMEOUT,
        error: function(jqXHR, textStatus, errorThrown) {
            handle_api_error(-25, undefined, 'Remove server from network', jqXHR, textStatus, errorThrown, this);
        },
        success: function(data, textStatus, jqXHR) {
            if ( jqXHR.status == '202') {
                try {
                    console.info('deleted server ' + serverID + ' from network ' + networkID);
                } catch(err) {}
                // toggle the reboot dialog
                display_reboot_dialog(networkID, serverID, serverName, serverState);
                // continue with the rest of the servers
                remove_server_form_network(networkIDs, serverIDs, serverNames, serverStates);
            } else {
                ajax_error(jqXHR.status, undefined, 'Remove server form network', jqXHR.responseText, this);
            }
        }
    });
    return false;
}

function set_firewall(networkID, serverID, profile) {
    if (!networkID.length || !serverID.length || !profile.length){
        return false;
    }
    // prepare payload
    var payload = {
            "firewallProfile": { "profile": profile }
    };

    // prepare ajax call
    $.ajax({
        url: API_URL + '/servers/' + serverID + '/action',
        type: "POST",
        contentType: "application/json",
        dataType: "json",
        data: JSON.stringify(payload),
        timeout: TIMEOUT,
        error: function(jqXHR, textStatus, errorThrown) {
            handle_api_error(-26, undefined, 'Set firewall profile', jqXHR, textStatus, errorThrown, this);
        },
        success: function(data, textStatus, jqXHR) {
            if ( jqXHR.status == '202') {
                try {
                    console.info('for server ' + serverID + ' set firewall profile to ' + profile);
                } catch(err) {}
                // toggle the reboot dialog
                try {

                    var serverName = $('div#net-' + networkID + '-server-' + serverID + ' div.machine-name-div span.name').text();
                    var serverState = $('div#net-' + networkID + '-server-' + serverID + ' img.logo').attr('src').split('-')[1];
                    serverState = serverState.split('.')[0];
                    display_reboot_dialog(networkID, serverID, serverName, serverState);

                    //remove progress gif and toggle the content
                    $('div#net-' + networkID + '-server-' + serverID + ' button.firewall-apply').html(VARIOUS["APPLY"]);
                    $('div#net-' + networkID + '-server-' + serverID + ' button.firewall-apply').attr("disabled", false);
                    $('div#net-' + networkID + '-server-' + serverID + ' div.firewall-header').click();

                } catch (err) {
                }
                
                // api call was made, set transition state to get reset 
                // on the next machines update api call
                var vm = get_machine(serverID)
                vm.network_transition = "NETWORK_CHANGE";
                show_machine_network_indicator(vm.id, 'pub');
            } else {
                ajax_error(jqXHR.status, undefined, 'Set firewall profile', jqXHR.responseText, this);
            }
        }
    });
    return false;
}

// show the welcome screen
function showWelcome() {
    $("#view-select").fadeOut("fast");
    $("#emptymachineslist").fadeIn("fast");
    $("#machinesview").hide();
}

// hide the welcome screen
function hideWelcome() {
    $("#emptymachineslist").fadeOut("fast");
    $("#view-select").fadeIn("fast");
    $("div#view-select").show();
    $("#machinesview").show();
}

function log_server_status_change(server_entry, new_status) {
    // firebug console logging
    try {
        if ($("#machinesview-single").length > 0) {
            console.info(server_entry.find("div.machine-details div.name").text() +
                        ' from ' + server_entry.find(".state-label").text() +
                        ' to ' + STATUSES[new_status]);
        } else {
            console.info(server_entry.find("div.name span.name").text() +
                        ' from ' + server_entry.find(".status").text().replace(TRANSITION_STATE_APPEND, "") +
                        ' to ' + STATUSES[new_status]);
        }
    } catch(err) {}
}

function get_flavor_params(flavorRef) {
    var cpus, ram, disk;
    if ( flavors.length > 0 ) {
        var current_flavor = '';
        for (i=0; i<flavors.length; i++) {
            if (flavors[i]['id'] == flavorRef) {
                current_flavor = flavors[i];
            }
        }
        cpus = current_flavor['cpu'];
        ram = current_flavor['ram'];
        disk = current_flavor['disk'];
    } else {
        cpus = 'undefined';
        ram = 'undefined';
        disk = 'undefined';
    }
    return {'cpus': cpus, 'ram': ram, 'disk': disk};
}

function get_image_params(imageRef) {
    var image_name, image_size;
    if ( images.length > 0 ) {
        var current_image = '';
        for (i=0; i<images.length; i++) {
            if (images[i]['id'] == imageRef) {
                current_image = images[i];
            }
        }
        try {
            image_name = current_image['name'];
        } catch(err) { image_name = 'undefined'; }
        try{
            image_size = current_image['metadata']['values']['size'];
        } catch(err) { image_size = 'undefined'; }
    } else {
        image_name = 'undefined';
        image_size = 'undefined';
    }
    return {'name': image_name,'size': image_size};
}

function get_public_ips(server) {
    var ip4, ip6;
    try {
        if (server.addresses.values) {
            $.each (server.addresses.values, function(i, value) {
                if (value.id == 'public') {
                    try {
                        $.each (value.values, function(i, ip) {
                            if (ip.version == '4') {
                                ip4 = ip.addr;
                            } else if (ip.version == '6') {
                                ip6 = ip.addr;
                            } else {
                                ip4 = 'pending';
                                ip6 = 'pending';
                            }
                        });
                    } catch (err){
                        try{console.info('Server ' + server.id + ' has invalid ips')}catch(err){};
                        ip4 = 'pending';
                        ip6 = 'pending';
                    }
                }
            });
        }
    } catch (err) {
        try{console.info('Server ' + server.id + ' has no network addresses')}catch(err){};
        ip4 = 'pending';
        ip6 = 'pending';
    }
    return {'ip4': ip4, 'ip6': ip6};
}

function get_private_ips(server) {

}

function close_all_overlays() {
	try {
		$("a#networkscreate").overlay().close();
	} catch(err) {}
	try {
		$('a#create').overlay().close();
	} catch(err) {}
	try {
		$("a#add-machines-overlay").overlay().close();
	} catch(err) {}
	try {
		$("a#metadata-scrollable").overlay().close();
	} catch(err) {}
	try {
		$("a#msgbox").overlay().close();
	} catch(err) {}
	try {
		$("a#feedbackbox").overlay().close();
	} catch(err) {}
}

// logout
function user_session_logout() {
    $.cookie("X-Auth-Token", null);
    if (window.LOGOUT_REDIRECT !== undefined)
    {
        window.location = window.LOGOUT_REDIRECT;
    } else {
        window.location.reload();
    }
}

// action indicators
function init_action_indicator_handlers(machines_view)
{
    // init once for each view
    if (window.ACTION_ICON_HANDLERS == undefined)
    {
        window.ACTION_ICON_HANDLERS = {};
    }

    if (machines_view in window.ACTION_ICON_HANDLERS)
    {
        return;
    }
    window.ACTION_ICON_HANDLERS[machines_view] = 1;

    if (machines_view == "list")
    {
        // totally different logic for list view
        init_action_indicator_list_handlers();
        return;
    }

    function update_action_icon_indicators(force)
    {
        function show(el, action) {
            $(".action-indicator", $(el)).attr("class", "action-indicator " + action);
            $(".action-indicator", $(el)).show();
        }

        function hide(el) {
            $(".action-indicator", $(el)).hide();
        }

        function get_pending_actions(el) {
            return $(".confirm_single:visible", $(el));
        }

        function other_indicators(el) {
           return $("img.wave:visible, img.spinner:visible", $(el))
        }

        $("div.machine:visible, div.single-container").each(function(index, el){
            var el = $(el);
            var pending = get_pending_actions(el);
            var other = other_indicators(el);
            var action = undefined;
            var force_action = force;
            var visible = $(el).css("display") == "block";

            if (force_action !==undefined && force_action.el !== el[0]) {
                // force action for other vm
                // skipping force action
                force_action = undefined;
            }

            if (force_action !==undefined && force_action.el === el[0]) {
                action = force_action.action;
            }

            if (other.length >= 1) {
                return;
            }

            if (pending.length >= 1 && force_action === undefined) {
                action = $(pending.parent()).attr("class").replace("action-container","");
            }

            if (action in {'console':''}) {
                return;
            }

            if (action !== undefined) {
                show(el, action);
            } else {
                try {
                    if (el.attr('id') == pending_actions[0][1])
                    {
                        return;
                    }
                } catch (err) {
                }
                hide(el);
            }

        });
    }

    // action indicators
    $(".action-container").live('mouseover', function(evn) {
        force_action = {'el': $(evn.currentTarget).parent().parent()[0], 'action':$(evn.currentTarget).attr("class").replace("action-container","")};
        // single view case
        if ($(force_action.el).attr("class") == "upper")
        {
            force_action.el = $(evn.currentTarget).parent().parent().parent()[0]
        };
        update_action_icon_indicators(force_action);
    });

    $("img.spinner, img.wave").live('hide', function(){
        update_action_icon_indicators();
    });
    // register events where icons should get updated

    // hide action indicator image on mouse out, spinner appear, wave appear
    $(".action-container").live("mouseout", function(evn){
        update_action_icon_indicators();
    });

    $(".confirm_single").live("click", function(evn){
        update_action_icon_indicators();
    });

    $("img.spinner, img.wave").live('show', function(){
        $("div.action-indicator").hide();
    });

    $(".confirm_single button.no").live('click', function(evn){
        $("div.action-indicator", $(evn.currentTarget).parent().parent()).hide();
    });

    $(".confirm_multiple button.no").click(function(){
        $("div.action-indicator").hide();
    });

    $(".confirm_multiple button.yes").click(function(){
        $("div.action-indicator").hide();
    });
}

function init_action_indicator_list_handlers()
{
    var skip_actions = { 'connect':'','details':'' };

    var has_pending_confirmation = function()
    {
        return $(".confirm_multiple:visible").length >= 1
    }

    function update_action_indicator_icons(force_action, skip_pending)
    {
        // pending action based on the element class
        var pending_action = $(".selected", $(".actions"))[0];
        var selected = get_list_view_selected_machine_rows();

        // reset previous state
        list_view_hide_action_indicators();

        if (pending_action == undefined && !force_action)
        {
            // no action selected
            return;
        }

        if (force_action != undefined)
        {
            // user forced action choice
            var action_class = force_action;
        } else {
            // retrieve action name (reboot, stop, etc..)
            var action_class = $(pending_action).attr("id").replace("action-","");
        }

        selected.each(function(index, el) {
            if (has_pending_confirmation() && skip_pending)
            {
                return;
            }
            var el = $(el);
            var logo = $("img.list-logo", el);
            $(".action-indicator", el).remove();
            var cls = "action-indicator " + action_class;
            // add icon div
            logo.after('<div class="' + cls + '"></div>');
            // hide os logo
            $("img.list-logo", el).hide();
        });
    }

    // on mouseover we force the images to the hovered action
    $(".actions a").live("mouseover", function(evn) {
        var el = $(evn.currentTarget);
        if (!el.hasClass("enabled"))
        {
            return;
        }
        var action_class = el.attr("id").replace("action-","");
        if (action_class in skip_actions)
        {
            return;
        }
        update_action_indicator_icons(action_class, false);
    });


    // register events where icons should get updated
    $(".actions a.enabled").live("click", function(evn) {
        // clear previous selections
        $("a.selected").removeClass("selected");

        var el = $(evn.currentTarget);
        el.addClass("selected");
        update_action_indicator_icons(undefined, false);
    });

    $(".actions a").live("mouseout", function(evn) {
        update_action_indicator_icons(undefined, false);
    });

    $(".confirm_multiple button.no").click(function(){
        list_view_hide_action_indicators();
    });

    $(".confirm_multiple button.yes").click(function(){
        list_view_hide_action_indicators();
    });

    $("input[type=checkbox]").live('change', function(){
        // pending_actions will become empty on every checkbox click/change
        // line 154 machines_list.html
        pending_actions = [];
        if (pending_actions.length == 0)
        {
            $(".confirm_multiple").hide();
            $("a.selected").each(function(index, el){$(el).removeClass("selected")});
        }
        update_action_indicator_icons(undefined, false);
    });

}

function list_view_hide_action_indicators()
{
    $("tr td .action-indicator").remove();
    $("tr td img.list-logo").show();
}

function get_list_view_selected_machine_rows()
{
    var table = $("table.list-machines");
    var rows = $("tr:has(input[type=checkbox]:checked)",table);
    return rows;
}

// machines images utils
function set_machine_os_image(machine, machines_view, state, os, skip_reset_states, remove_state) {
    var views_map = {'single': '.single-image', 'icon': '.logo'};
    var states_map = {'on': 'state1', 'off': 'state3', 'hover': 'state4', 'click': 'state2'}
    var sizes_map = {'single': 'large', 'icon': 'medium'}

    var size = sizes_map[machines_view];
    var img_selector = views_map[machines_view];
    var cls = states_map[state];

    if (os === "unknown") { os = "okeanos" } ;
    var new_img = 'url("./static/icons/machines/' + size + '/' + os + '-sprite.png")';

    var el = $(img_selector, machine);
    var current_img = el.css("backgroundImage");
    if (os == undefined){
        new_img = current_img;
    }

    // os changed
    el.css("backgroundImage", new_img);

    // reset current state
    if (skip_reset_states === undefined)
    {
        el.removeClass("single-image-state1");
        el.removeClass("single-image-state2");
        el.removeClass("single-image-state3");
        el.removeClass("single-image-state4");
    }

    if (remove_state !== undefined)
    {
        remove_state = "single-image-" + states_map[remove_state];
        el.removeClass(remove_state);
        return;
    }
    
    // set proper state
    el.addClass("single-image-" + cls);
}


// generic info box
function show_feedback_form(msg, from_error, extra_data) {
    var box = $("#feedback-form");
    box.addClass("notification-box");

    // initialize
    box.find(".form-container").show();
    box.find("textarea").val("");
    box.find(".message").hide();
    
    var initial_msg = msg || undefined;
    
    var triggers = $("a#feedbackbox").overlay({
        // some mask tweaks suitable for modal dialogs
        mask: '#666',
        top: '10px',
        fixed: false,
        closeOnClick: false,
        oneInstance: false,
        load: false
    });

    
    if (initial_msg && from_error) {
        // feedback form from ajax_error window
        box.find("textarea").val(initial_msg);
        $("a#feedbackbox").overlay().onClose(function(){window.location.reload()});
        box.find("textarea").height(200);
        $("a#feedbackbox").overlay().onLoad(function(){box.find("textarea").focus().setCursorPosition(1500);});
        
    }
    
    var extra_data = extra_data;
    $("#feedback-form form").unbind("submit");
    $("#feedback-form form").submit(function(event) {
        event.preventDefault();
            
        // empty msg
        if ($("textarea.feedback-text").val().replace(/^\s*|\s*$/,"") == "") {
            alert($(".empty-error-msg", this).text());
            return;
        }

        // fill the textarea with user information jsonified
        $("textarea.data-text", this).val("").val(get_user_data_json(extra_data));

        $.ajax({
            url: FEEDBACK_URL,
            data: $(this).serialize(),
            type: "POST",
            // show loading
            beforeSend: function() {box.find(".form-container").hide(); box.find(".sending").fadeIn() },
            // hide form
            complete: function() { box.find(".form-container").hide(); box.find(".sending").hide() },
            // on success display success message
            success: function() { box.find(".success").fadeIn(); box.find(".sending").hide() },
            // display error message
            error: function() { box.find(".errormsg").fadeIn(); box.find(".sending").hide() }
        })
    });
    
    $("a#feedbackbox").data('overlay').load();

    // reset feedback_pending for ajax_errors
    window.FEEDBACK_PENDING = false;
    return false;
}

function get_user_data(extra_data) {
    try {
        var last_req = $.extend({}, last_request);

        // reset xhr, might raise exceptions while converting to JSON
        last_req.xhr = {};
    } catch (err) {
        var last_req = err;
    }
    
    var changes_since_date = changes_since_date || false;
    return $.extend({
        'servers': $.extend({}, servers),
        'client': {'browser': $.browser, 'screen': $.extend({}, screen), 'client': $.client},
        'dates': {'now': new Date, 'lastUpdate': changes_since_date},
        'last_request': last_req
    }, extra_data);
}

function get_user_data_json(extra) {
    try {
        return JSON.stringify(get_user_data(extra));
    } catch (err) {
        return JSON.stringify({'error': err});
    }
}

function msg_box(user_config) {
    var defaults = {'title':'Info message', 'content': 'this is an info message', 'ajax': false, 'extra':false};
    var config = $.extend(defaults, user_config);

    // prepare the error message
    // bring up success notification
    var box = $("#notification-box");
    box.addClass("notification-box");
    box.addClass('success');
    box.addClass(config.cls || '');
    box.removeClass('error');

    var sel = function(s){return $(s, box)};
    // reset texts
    sel("h3 span.header-box").html("");
    sel(".sub-text").html("");
    sel(".password-container .password").html("");
    sel("div.machine-now-building").html("");

    // apply msg box contents
    sel("h3 span.header-box").html(config.title);
    sel("div.machine-now-building").html(config.content);
    sel(".sub-text").html(config.sub_content || '');
    sel(".popup-header").removeClass("popup-header-error");
    box.removeClass("popup-border-error");
    sel(".popup-details").removeClass("popup-details-error");
    sel(".popup-separator").removeClass("popup-separator-error");
    
    sel(".password-container").hide();
    if (config.extra) {
        sel(".password-container .password").html(config.extra);
        sel(".password-container").show();
    }
    
    var conf = {
        // some mask tweaks suitable for modal dialogs
        mask: '#666',
        top: '10px',
        closeOnClick: false,
        oneInstance: false,
        load: false,
        onLoad: config.onLoad || false,
        fixed: config.fixed || false,
        onClose: function () {
            // With partial refresh working properly,
            // it is no longer necessary to refresh the whole page
            // choose_view();
        }
    }

    var triggers = $("a#msgbox").overlay(conf);

    try {
        conf = $("a#msgbox").data('overlay').getConf();
        conf.fixed = config.fixed || false;
    } catch (err) {}
    $("a#msgbox").data('overlay').load();
    
    var parse_data = config.parse_data || false;
    var load_html = config.html || false;
    var user_success = config.success || false;
    config.ajax = config.ajax || {};

    // requested to show remote data in msg_box
    if (config.ajax && !$.isEmptyObject(config.ajax)) {
        $.ajax($.extend({ 
            url:config.ajax, 
            success: function(data){
                // we want to get our data parsed before
                // placing them in content
                if (parse_data) {
                    data = parse_data(data);
                }

                // no json response
                // load html body
                if (load_html) {
                    sel("div.machine-now-building").html(data);
                } else {

                    if (data.title) {
                        sel("h3 span.header-box").text(data.title);
                    }

                    if (data.content) {
                        sel("div.machine-now-building").html(data.content);
                    }
                    if (data.extra) {
                        sel(".password-container .password").html(data.extra);
                        sel(".password-container").show();
                    }
                    if (data.subinfo) {
                        sel(".sub-text").html(data.subinfo);
                    } else {
                        sel(".sub-text").html("");
                    }
                }

                if (user_success) {
                    user_success($("div.machine-now-building"));
                }
            },
            error: function(xhr, status, err) {
                ajax_error(-519, "UI Error", "Machine connect", err, this);
            }
        }, config.ajax_config));
    }
    return false;
}


function show_api_overlay() {
    var config = {
        title: window.API_OVERLAY_TITLE,
        content: $(".api_overlay_content").html().replace("$api_key", $.cookie("X-Auth-Token")),
        extra: $.cookie("X-Auth-Token"),
        sub_content: window.API_OVERLAY_SUBCONTENT,
        cls: "api_content",
        ajax: false
    }
    msg_box(config);
}

function show_invitations() {

    handle_invitations = function(el) {

        // proper class to identify the overlay block
        el.addClass("invitations");

        var cont = el;
        var form = $(el).find("form");

        // remove garbage rows that stay in DOM between requests
        $(".removable-field-row:hidden").remove();

        // avoid buggy behaviour, close all overlays if something went wrong
        try {
            // form is in content (form is not displayed if user has no invitations)
            if ($("#invform #removable-name-container-1").length) {
                $("#invform #removable-name-container-1").dynamicField();
            }
        } catch (err) {
            close_all_overlays();
        }
        
        // we copy/paste it on the title no need to show it twice
        $(".invitations-left").hide();

        // reset title
        $("#notification-box .header-box").html("");
        $("#notification-box .header-box").html(window.INVITATIONS_TITLE + " " + $($(".invitations-left")[0]).text());

        // handle form submit
        form.submit(function(evn){
            evn.preventDefault();

            // do the post
            $.post(form.attr("action"), form.serialize(), function(data) {
                // replace data
                $(cont).html(data); 

                // append all handlers again (new html data need to redo all changes)
                handle_invitations(cont);
            });

            return false;
        });
    }
    
    // first time clicked (show the msg box with /invitations content)
    msg_box({
        title:window.INVITATIONS_TITLE, 
        content:'', 
        fixed: false,
        ajax:INVITATIONS_URL, 
        html:true, 
        success: function(el){ 
            handle_invitations(el)
        }
    });
}


function get_short_v6(v6, parts_to_keep) {
    var parts = v6.split(":");
    var new_parts = parts.slice(parts.length - parts_to_keep);
    return new_parts.join(":");
}

function fix_v6_addresses() {

    // what to prepend
    var match = "...";
    // long ip min length
    var limit = 20;
    // parts to show after the transformation
    // (from the end)
    var parts_to_keep_from_end = 4;

    $(".ipv6-text").each(function(index, el){
        var el = $(el);
        var ip = $(el).text();
            
        // transformation not applyied
        // FIXME: use $.data for the condition
        if (ip.indexOf(match) == -1 && ip != "pending") {
            
            // only too long ips
            if (ip.length > 20) {
                $(el).data("ipstring", ip);
                $(el).text(match + get_short_v6(ip, parts_to_keep_from_end));
                $(el).attr("title", ip);
                $(el).tooltip({'tipClass':'tooltip ipv6-tip', 'position': 'center center'});
            }
        } else {
            if (ip.indexOf(match) == 0) {
            } else {
                // not a long ip anymore
                $(el).data("ipstring", undefined);
                $(el).css({'text-decoration':'none'});

                if ($(el).data('tooltip')) {
                    $(el).data('tooltip').show = function () {};
                }
            }
        }
    });
}

function fix_server_name(str, limit, append) {
    limit = limit || 30;
    append = append || "...";

    if (str.length > limit) {
        str = str.substring(0,limit-append.length) + append;
    }
    return str;
}

function show_machine_network_indicator(vm_id, network_id) {
    var el = $("div#net-" + network_id + '-server-' + vm_id);
    el.find(".network-progress-indicator").show();
}


function get_firewall_profile(vm_id) {
    var vm = get_machine(vm_id);

    try {
        return vm.addresses.values[0].firewallProfile;
    } catch (err) {
        return undefined;
    }
}


function get_progress_details(id) {
    var vm = get_machine(id);
    var progress = vm.progress;

    // no details for active machines
    if (!vm.status == "BUILD") {
        return false;
    }
    
    // check if images not loaded yet
    try {
        var image = get_image_params(vm.imageRef);
        var size = image.size;
    } catch (err) {
        // images not loaded yet (can this really happen ??)
        return;
    }
    
    var to_copy = size;
    var copied = (size * progress / 100).toFixed(2);
    var status = "INIT"

    // apply state
    if (progress > 0) { status = "IMAGE_COPY" }
    if (progress >= 100) { status = "FINISH" }
    
    // user information
    var msg = BUILDING_STATUSES[status];

    // image copy state display extended user information
    if (status == "IMAGE_COPY") {
        msg = msg.format(readablizeBytes(copied*(1024*1024)), readablizeBytes(to_copy*(1024*1024)), progress)
    }

    var progress_data = {
        'percent': vm.progress,
        'build_status': status,
        'copied': copied,
        'to_copy': size,
        'msg': msg
    }

    return progress_data;
}

// display user friendly bytes amount
function readablizeBytes(bytes) {
    var s = ['bytes', 'kb', 'MB', 'GB', 'TB', 'PB'];
    var e = Math.floor(Math.log(bytes)/Math.log(1024));
    return (bytes/Math.pow(1024, Math.floor(e))).toFixed(2)+" "+s[e];
}

