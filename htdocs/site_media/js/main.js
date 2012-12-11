$(document).ready(function(){

    $(".download").click(function(){
        window.location = $(this).find("a").attr("href");
    })
})