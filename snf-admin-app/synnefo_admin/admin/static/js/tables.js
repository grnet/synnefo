var mydata;
var cols = [];
(function($, Django){

    var table;
    $(function(){
        var url = $('#table-items-total').data("url");
        var serverside = Boolean($('#table-items-total').data("server-side"));
        var table;
        $.fn.dataTable.ext.legacy.ajax = true;
        table = $('#table-items-total').dataTable({
            "bPaginate": true,
            //"sPaginationType": "bootstrap",
            "bProcessing": true,
            "serverSide": true,
            "ajax": {
                "url": url,
                data: function(data) {
                    data.testme = "testme!!!"
                },
                "dataSrc" : function(response) {
                    console.log(response);
                    mydata = {data: response.aaData};
                    return response.aaData;

                }
            },
        });

       $('.refresh').click(function() {
            table.api().ajax.reload();
       });
});

}(window.jQuery, window.Django));

