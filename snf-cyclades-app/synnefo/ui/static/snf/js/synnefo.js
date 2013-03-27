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

function show_invitations() {
    
    function display_resend_success(msg) {
        clear_resend_messages();
        $("#invsent .message.success").text(msg).show();
    }

    function display_resend_error(msg) {
        clear_resend_messages();
        $("#invsent .message.errormsg").text(msg).show();
    }

    // clear resent messages
    function clear_resend_messages() {
        $("#invsent .message").hide();
    }

    // register resent click handlers
    function register_invitation_resends() {
        $(".invitations .resend-invitation").click(function() {
            var invid = $(this).attr("id");

            if (invid == null)
                return;

            var id = invid.split("-")[1];

            if (id == null)
                return;

            var child = $(this).find("img");
            child.attr('src', '/static/progress-tiny.gif');

            $.ajax({
                type: "POST",
                url : "/invitations/resend",
                data : {invid : id},
                success: function(msg) {
                    display_resend_success("Invitation has been resent");
                    child.attr('src', '/static/resend.png');
                },
                error : function(xhr, status, error) {
                    display_resend_error("Something seems to have gone wrong. " +
                          "Please try again in a few minutes.");
                    child.attr('src', '/static/resend.png');
                }
            });
        });
    }

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
        
        // sending finished or first invitations view
        $(".invitations .sending").hide();
        $(".invitations .submit").show();
        $(".invitations #fieldheaders").show();
        $(".invitations #fields").show();

        // reset title
        $("#notification-box .header-box").html("");
        $("#notification-box .header-box").html(window.INVITATIONS_TITLE + " " + $($(".invitations-left")[0]).text());
    
        // resend buttons
        register_invitation_resends();
        clear_resend_messages();

        // handle form submit
        form.submit(function(evn){
            evn.preventDefault();
            
            // sending...
            $(".invitations .sending").show();
            $(".invitations .submit").hide();
            $(".invitations #fieldheaders").hide();
            $(".invitations #fields").hide();

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

    $(".machine .ipv6-text").each(function(index, el){
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
            //update_machine_stats(serverID, data);
        },

        // pass server id to ajax settings
        serverID: serverID
    });
    return false;
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
        var image = synnefo.storage.images.get(vm.imageRef).attributes;
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
    var msg = BUILDING_MESSAGES[status];

    // image copy state display extended user information
    //if (status == "IMAGE_COPY") {
        //msg = msg.format(readablizeBytes(copied*(1024*1024)), readablizeBytes(to_copy*(1024*1024)), progress)
    //}

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

// machines images utils
function set_machine_os_image(machine, machines_view, state, os, skip_reset_states, remove_state) {
    var views_map = {'single': '.single-image', 'icon': '.logo'};
    var states_map = {'on': 'state1', 'off': 'state3', 'hover': 'state4', 'click': 'state2'}
    var sizes_map = {'single': 'large', 'icon': 'medium'}

    var size = sizes_map[machines_view];
    var img_selector = views_map[machines_view];
    var cls = states_map[state];
 
    var new_img = 'url("' + synnefo.config.machines_icons_url + size + '/' + os + '-sprite.png")';

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

// return machine entry from serverID
function get_machine(serverID) {
    return synnefo.storage.vms.get(serverID).attributes;
}

