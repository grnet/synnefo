$(document).ready(function(){
    
    /*
    * LINKS CONFIGURATION
    */

    var PROFILE_URL = "https://accounts.cloud.grnet.gr";
    var SERVICES_LINKS = window.CLOUDBAR_SERVICES_LINKS || {
        'cloud':   { url:'http://pithos.dev.grnet.gr/im/', name:'grnet cloud', id:'cloud', icon:'home-icon.png' },
        'okeanos': { url:'http://staging.okeanos.grnet.gr/ui/', name:'~okeanos', id:'okeanos' },
        'pithos':  { url:'http://pithos.dev.grnet.gr/ui/', name:'pithos+', id:'pithos' }
    };
    
    var PROFILE_LINKS = window.CLOUDBAR_PROFILE_LINKS || {
        'login': { url: '/im/login?next=' + window.location.toString(), auth:false, name: "login...", visible:false },
        'profile': { url: '/im/profile', auth:true, name: "change your profile..." },
        'invitations': { url: '/im/invite', auth:true, name: "invite some friends..." },
        'feedback': { url: '/im/feedback', auth:true, name: "feedback..." },
        'logout': { url: '/im/logout', auth:true, name: "logout..." }
    };


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
    
    
    // create services links and set the active class to the current service
    $.each(SERVICES_LINKS, function(i, el){
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

    var USERNAME, LOGGED_IN;
    var authcookie = cookie(COOKIE_NAME);
    var anonymous = {'user': 'Login...', 'logged_in': false};

    if (authcookie && authcookie.indexOf("|") > -1) {
        USER_DATA.logged_in = true;
        USER_DATA.user = authcookie.split("|")[0];
    } else {
        USER_DATA = anonymous;
    }

    USERNAME = USER_DATA.user;
    LOGGED_IN = USER_DATA.logged_in;

    // clear username
    USERNAME = USERNAME.replace(/\\'/g,'');
    USERNAME = USERNAME.replace(/\"/g,'');

    var user = $('<div class="user"></div>');
    var username = $('<a href="#"></a>');
    username.text(USERNAME);
    
    // create profile links
    var usermenu = $("<ul>");
    $.each(PROFILE_LINKS, function(i,el) {
        if (!LOGGED_IN && el.auth) { return }
        if (LOGGED_IN && !el.auth) { return }
        var li = $("<li />");
        var link = $("<a />");
        link.text(el.name);
        link.attr({href:el.url});
        li.append(link);
        if (el.visible == false) {
            li.hide();
        }
        usermenu.append(li);
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
