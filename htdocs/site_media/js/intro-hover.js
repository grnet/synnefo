$(document).ready(function(){

    if ($(".logohover").length == 0) { return };

    var cont = $(".logocontent");

    var inactive = $("img.img1");
    var active = $("img.img2");

    active.hide();
    
    reposition = function() {
        var winheight = $(window).height();
        var winwidth = $(window).width();

        var imgheight = 590;
        var imgwidth = 524;

        var top = (winheight / 2) - (imgheight / 2);
        if (top < 0) { top = 0; };

        
        var left = (winwidth / 2) - (imgwidth / 2);
        if (left < 0) { left = 0; };

        $(".logohover img").css({top:top, left:left});
    }

    reposition();
    $(window).resize(reposition);

    var time = 500;
    var hovering = false;
    var capture = cont;
    capture.mouseenter(function() {
        if (hovering) { return };
        hovering = true;
        inactive.fadeOut(time);
        active.fadeIn(time);
    })
    capture.mouseleave(function() {
        if (!hovering) { return };
        
        hovering = false;
        active.fadeOut(time);
        inactive.fadeIn(time);
    });
})