$(document).ready(function(){
    
    /*
    * LINKS CONFIGURATION
    */

    var PROFILE_URL = "https://accounts.cloud.grnet.gr";

    // cookie plugin https://raw.github.com/carhartl/jquery-cookie/master/jquery.cookie.js 
    //  * Copyright (c) 2010 Klaus Hartl, @carhartl
    //  * Dual licensed under the MIT and GPL licenses
    var cookie=function(key,value,options){if(arguments.length>1&&(!/Object/.test(Object.prototype.toString.call(value))||value===null||value===undefined)){options=$.extend({},options);if(value===null||value===undefined){options.expires=-1}if(typeof options.expires==='number'){var days=options.expires,t=options.expires=new Date();t.setDate(t.getDate()+days)}value=String(value);return(document.cookie=[encodeURIComponent(key),'=',options.raw?value:encodeURIComponent(value),options.expires?'; expires='+options.expires.toUTCString():'',options.path?'; path='+options.path:'',options.domain?'; domain='+options.domain:'',options.secure?'; secure':''].join(''))}options=value||{};var decode=options.raw?function(s){return s}:decodeURIComponent;var pairs=document.cookie.split('; ');for(var i=0,pair;pair=pairs[i]&&pairs[i].split('=');i++){if(decode(pair[0])===key)return decode(pair[1]||'')}return null};

    var ACTIVE_MENU = window.CLOUDBAR_ACTIVE_SERVICE || 'cloud';
    var USER_DATA = window.CLOUDBAR_USER_DATA || {'user': 'Not logged in', 'logged_in': false};
    var COOKIE_NAME = window.CLOUDBAR_COOKIE_NAME || '_pithos2_a';

    var cssloc = window.CLOUDBAR_LOCATION || "http://127.0.0.1:8989/";
    
    // load css
    var css = $("<link />");
    css.attr({rel:'stylesheet', type:'text/css', href:cssloc + 'cloudbar.css'});
    $("head").append(css);

    // load service specific css
    var SKIP_ADDITIONAL_CSS = window.SKIP_ADDITIONAL_CSS == undefined ? false : window.SKIP_ADDITIONAL_CSS;

    if (!SKIP_ADDITIONAL_CSS) {
        var css = $("<link />");
        css.attr({rel:'stylesheet', type:'text/css', href:cssloc + 'service_' + ACTIVE_MENU + '.css'});
        $("head").append(css);
    }

    var root = $('body');
    var bar = $('<div class="servicesbar"></div>');
    var services = $('<div class="services"></div>');
    var profile = $('<div class="profile"></div>');
    
    var get_services_url = window.GET_SERVICES_URL || window.CLOUDBAR_SERVICES;
    
    // create services links and set the active class to the current service
    $.getJSON(get_services_url + "?callback=?", function(data) {
            $.each(data, function(i, el){
            var slink = $("<a>");
            if (el.icon) {
                slink.append($('<img src="'+cssloc+el.icon+'"/>'));
            } else {
                slink.text(el.name);
            }
            slink.attr('href', el.url);
            slink.attr('title', el.name);
            services.append(slink);
            if (el.id == ACTIVE_MENU) {
                slink.addClass("active");
            }
        });
      });
    
    // create profile links
    var user = $('<div class="user"></div>');    
    var username = $('<a href="#"></a>');
    var usermenu = $("<ul>");
    var get_menu_url = (window.GET_MENU_URL || window.CLOUDBAR_MENU) + '?callback=?&location=' + window.location.toString();

    $.getJSON(get_menu_url, function(data) {
        $.each(data, function(i,el) {
            if (i == 0){
                username.text(el.name);
                username.attr('href', el.url);
            }else{
                var link = $("<a />");
                link.text(el.name);
                link.attr({href:el.url});
                var li = $("<li />");
                li.append(link);
                usermenu.append(li);
            }
        });
    });
    
    //profile.filter(".user a").attr("href", 
                                   //profile.find("li a").get(0).attr("href"))
    
    user.append(username);
    user.append(usermenu);
    profile.append(user);
    bar.append(services).append(profile);
    

    root.prepend(bar);
    var firstlink = profile.find("ul li:first-child a").attr("href");
    profile.find(".user > a").attr("href", firstlink);
});
