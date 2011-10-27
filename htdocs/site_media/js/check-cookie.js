$(document).ready(function(){
    if ($.cookie("X-Auth-Token")) {
        $("body").addClass("auth");
    }
});