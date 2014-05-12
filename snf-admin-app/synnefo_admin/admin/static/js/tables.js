var mydata;
var cols = [];
var myflag = true;
(function($, Django){

$(function(){
    var url = $('#table-items-total').data("url");
    var serverside = Boolean($('#table-items-total').data("server-side"));
    var table;
    $.fn.dataTable.ext.legacy.ajax = true;
    var tableDomID = '#table-items-total';
    table = $(tableDomID).dataTable({
        "bPaginate": true,
        //"sPaginationType": "bootstrap",
        "bProcessing": true,
        "serverSide": true,
        "ajax": {
            "url": url,
            "data": function(data) {
                // here must be placed the additional data that needs to be send with the ajax call
                // data.testme = "testme!!!"
            },
            "dataSrc" : function(response) {
                console.log(response);
                mydata = response;
                if(response.aaData.length != 0) {
                    var cols = response.aaData;
                    var rowL = cols.length;
                    var detailsCol = cols[0].length;
                    var summaryCol = ++cols[0].length;
                    
                    for (var i=0; i<rowL; i++) {
                        response.extra[i]["url"] = "user/"+response.aaData[i][0]; // temp
                        response.extra[i]["actions"] ='action-'.concat('contact'); // temp
                        cols[i][detailsCol] = response.extra[i].url;
                        cols[i][summaryCol] = response.extra[i]
                    }
                }
                return response.aaData;

            }
        },
        "columnDefs": [{
            "targets": -2, // the second column counting from the right is "Details"
            "render": function(data, type, rowData)  {
                return '<a href="'+data+'" class="">Details</a>';
            }
        },
        {
            "targets": -1, // the first column counting from the right is "Summary"
            // data: "test",
            "render": function(data, type, rowData) {
                return summaryTemplate(data);
            }
        },
        {
            targets: 0,
            visible: false
        }
        ],
        "order": [1, "asc"],
        "createdRow": function(row, data, dataIndex) {
          
            var dataL = data.length;
            var extraIndex = dataL -1;
            row.id = data[extraIndex].id;
            var actions = data[extraIndex].actions;
            $(row).addClass(actions);
            clickSummary(row);

        } 
    });
});


function summaryTemplate(data) {
    var listStructure = '<dt>{key}:</dt><dd>{value}</dd>';
    var list = [];
    // var listItem = 
    list[0] = listStructure.replace('{key}', 'UUID').replace('{value}',data.id);
    list[1] = listStructure.replace('{key}', 'Account State').replace('{value}',data.status);


    var html = '<a href="#" class="summary-expand expand-area"><span class="snf-icon snf-angle-down"></span></a><dl class="info-summary dl-horizontal">'+list.join(',').replace(',', '')+'</dl>';
    return html;
}

    function clickSummary(row) {
        $(row).find('a.expand-area').click(function(e) {
            e.preventDefault();
            e.stopPropagation();
            var $summaryTd = $(this).closest('td');
            var $btn = $summaryTd.find('.expand-area span');
            var $summaryContent = $summaryTd.find('.info-summary');
            
            var summaryContentWidth = $summaryTd.closest('tr').width()// - parseInt($summaryContent.css('padding-right').replace("px", "")) - parseInt($summaryContent.css('padding-left').replace("px", ""));
            var summaryContPos = summaryContentWidth - $summaryTd.width() - parseInt($summaryContent.css('padding-left').replace("px", "")) -2; // border width?

            $summaryContent.css({
                width: summaryContentWidth +'px',
                right: summaryContPos +'px'
            });
            $btn.toggleClass('snf-angle-up snf-angle-down');
            $summaryContent.stop().slideToggle(600, function() {
                if ($summaryContent.is(':visible')) {
                    $btn.removeClass('snf-angle-down').addClass('snf-angle-up');    
                }
                else {
                    $btn.removeClass('snf-angle-up').addClass('snf-angle-down');
                }
            });

        })
    }
    $(tableDomID).on('click', 'tbody tr', function() {
        $(this).toggleClass('selected');
    })
}(window.jQuery, window.Django));

