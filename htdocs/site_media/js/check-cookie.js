$(document).ready(function(){
    if ($.cookie("X-Auth-Token") || $.cookie("_pithos2_a")) {
        $("body").addClass("auth");
    }
});
