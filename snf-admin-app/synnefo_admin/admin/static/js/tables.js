var mydata;

(function($, Django){

$(function(){
    var selected = {
        items: [],
        actions: {}
    };

    var availableActions = {};
    var allowedActions= {};
    $('.actionbar button').each(function() {
        availableActions[$(this).data('action')] = true;
    });

    for(var prop in availableActions) {
        allowedActions[prop] = true;
    }


    var url = $('#table-items-total').data("url");
    var serverside = Boolean($('#table-items-total').data("server-side"));
    var table;
    $.fn.dataTable.ext.legacy.ajax = true;
    var extraData;
    // sets the classes of the btns that are used for navigation throw the pages (next, prev, 1, 2, 3...)
    // $.fn.dataTableExt.oStdClasses.sPageButton = "btn btn-primary";
    var tableDomID = '#table-items-total';
    table = $(tableDomID).DataTable({
        "bPaginate": true,
        //"sPaginationType": "bootstrap",
        "bProcessing": true,
        "serverSide": serverside,
        "ajax": {
            "url": url,
            "data": function(data) {
                // here must be placed the additional data that needs to be send with the ajax call
                // data.extraKey = "extraValue";
            },
            "dataSrc" : function(response) {
                console.log(response);
                mydata = response;
                extraData = response.extra;
                if(response.aaData.length != 0) {
                    var cols = response.aaData;
                    var rowL = cols.length;
                    var detailsCol = cols[0].length;
                    var summaryCol = ++cols[0].length;
                    for (var i=0; i<rowL; i++) {
                        cols[i][detailsCol] = response.extra[i].details_url;
                        cols[i][summaryCol] = response.extra[i]
                    }
                }
                return response.aaData;
            }
        },
        "columnDefs": [{
            "targets": -2, // the second column counting from the right is "Details"
            "orderable": false,
            "render": function(data, type, rowData)  {
                return '<a href="'+ data.value +'" class="">'+ data.display_name+'</a>';
            }
        },
        {
            "targets": -1, // the first column counting from the right is "Summary"
            "orderable": false,
            "render": function(data, type, rowData) {
                return summaryTemplate(data);
            },
        },
        {
            targets: 0,
            visible: false
        }
        ],
        "order": [1, "asc"],
        "createdRow": function(row, data, dataIndex) {
          
            var extraIndex = data.length - 1;
            row.id = data[extraIndex].id.value; //sets the dom id

            clickSummary(row);
        } 
    });

    $(tableDomID).on('click', 'tbody tr', function() {
        var info = $(tableDomID).dataTable().api().cell($(this).find('td:last-child')).data();
        if($(this).hasClass('selected')) {
            $(this).removeClass('selected');
            removeItem(info.id.value);
        }
        else {
            $(this).addClass('selected');
            addItem(info)
        }
    });



function summaryTemplate(data) {
    var listTemplate = '<dt>{key}:</dt><dd>{value}</dd>';
    var list = [];
    var listItem = listTemplate.replace('{key}', prop).replace('{value}',data[prop]);
    var i = 0;
    for(var prop in data) {
        if(prop !== "details_url") {
            if(data[prop].visible) {
                list[i] = listTemplate.replace('{key}', data[prop].display_name).replace('{value}',data[prop].value);
                i++;
                
            }
        }
    }

    var html = '<a href="#" class="summary-expand expand-area"><span class="snf-icon snf-angle-down"></span></a><dl class="info-summary dl-horizontal">'+list.join(',').replace(/,/g, '')+'</dl>';
    return html;
};

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
    };


    function addItem(infoObj) {
        var $selectedNum = $('.sidebar button').find('.selected-num');
        var itemsL;
        var newItem = {}
        var isNew = true;
        var actionsArray = infoObj.allowed_actions.value;
        var actionsL = actionsArray.length;
        console.log('addItem')
        var newItem = {
           "id": infoObj.id.value,
           "item_name": infoObj.item_name.value,
           "contact_name": infoObj.contact_name.value,
           "contact_email": infoObj.contact_mail.value,
           "actions": {}
        }

        for (var i = 0; i<actionsL; i++) {
            newItem.actions[actionsArray[i]] = true;
        }
        for(var prop in availableActions) {
            if(!(prop in newItem.actions)) {
                newItem.actions[prop] = false;
            }
        }

        itemsL = selected.items.length;
            for(var i=0; i<itemsL; i++) {
                if(selected.items[i].id === newItem.id) {
                    isNew = false;
                }
            }
        if(isNew) {
            selected.items.push(newItem);
            enableActions(newItem.actions)
        }
    };

    function removeItem(itemID) {
        var items = selected.items;
        var itemsL = items.length;
        for (var i = 0; i<itemsL; i++) {
            if(items[i].id === itemID) {
                items.splice(i, 1);
                enableActions(undefined, true);
                break;
            }
        }
    }


    /* It enables the btn (link) of the corresponding allowed action */
    function enableActions(actionsObj, removeItemFlag) {

        var itemActionsL =selected.items.length;
        var $actionBar = $('.actionbar');
        var itemActions = {};
        if (removeItemFlag) {
            if(!selected.items.length) {
                for(var prop in allowedActions) {
                    allowedActions[prop] = false;
                }
            }
            else {
                for(var prop in allowedActions) {
                    allowedActions[prop] =true;
                    for(var i=0; i<itemActionsL; i++) {
                        allowedActions[prop] = allowedActions[prop] && selected.items[i].actions[prop];
                    }
                }
            }
        }
        else {
            if(selected.items.length === 1) {
                for(var prop in allowedActions) {
                    allowedActions[prop] = availableActions[prop] && actionsObj[prop];
                }
            }
            else {
                for(var prop in allowedActions) {
                    allowedActions[prop] = allowedActions[prop] && actionsObj[prop];
                }
            }
        }
        for(var prop in allowedActions) {
            if(allowedActions[prop]) {
                $actionBar.find('button[data-action='+prop+']').removeClass('disabled');
            }
            else {
                $actionBar.find('button[data-action='+prop+']').addClass('disabled');
            }
        }
    };
});
}(window.jQuery, window.Django));
