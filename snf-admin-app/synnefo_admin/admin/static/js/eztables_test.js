(function($, Django){

    "use strict";


    $(function(){
        $('#items-table').dataTable({
            "bPaginate": true,
            // "sPaginationType": "bootstrap",
            "bProcessing": true,
            "bServerSide": true,
            "sAjaxSource": Django.url('admin-json'),
        });
    });

    }(window.jQuery, window.Django));
