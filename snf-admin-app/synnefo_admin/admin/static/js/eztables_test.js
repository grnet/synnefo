(function($, Django){

    "use strict";

    var url = $("#items-table").data("url");
    var serverside = Boolean($("#items-table").data("server-side"));

    $(function(){
        $('#items-table').dataTable({
            "bPaginate": true,
            //"sPaginationType": "bootstrap",
            "bProcessing": true,
            "bServerSide": serverside,
            "sAjaxSource": url,
        });
    });

}(window.jQuery, window.Django));
