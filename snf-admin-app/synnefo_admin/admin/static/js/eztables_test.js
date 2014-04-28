//$(document).ready(function(){
    //$('#items-table').dataTable({
        //"bPaginate": true,
        //"sPaginationType": "bootstrap",
        //"bScrollCollapse": true,
        //"bServerSide": true,
        //"sAjaxSource": "test"
    //});
//});
(function($, Django){

    "use strict";


    $(function(){
        $('#items-table').dataTable({
            "bPaginate": true,
            "sPaginationType": "bootstrap",
            "bProcessing": true,
            "bServerSide": true,
            "sAjaxSource": Django.url('admin-json', "user"),
        });
    });

}(window.jQuery, window.Django));
