(function($, Django){

    "use strict";


    $(function(){
        $('#items-table').dataTable({
            "bPaginate": true,
            //"sPaginationType": "bootstrap",
            "bProcessing": true,
            "bServerSide": true,
            "sAjaxSource": "/admin/json/user",
        });
    });

    }(window.jQuery, window.Django));
