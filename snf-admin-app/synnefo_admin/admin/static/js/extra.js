$(document).ready(function() {
	
	/* Extend String Prototype */
	String.prototype.toDash = function(){
		return this.replace(/([A-Z])/g, function($1){
			return "-"+$1.toLowerCase();
		});
	};


	var selected = {
   		items: [],
		actions: {}
	};

	var availableActions = {};
	var allowedActions= {};
	$('.sidebar a').each(function() {
		availableActions[$(this).data('action')] = true;
	});

	for(var prop in availableActions) {
		allowedActions[prop] = true;
	}

	/* Functions */

	/* General */

	/* Sets sidebar's position fixed */	
	/* subnav-fixed is added/removed from processScroll() */	
	function fixedMimeSubnav() {
		if($('.messages').find('.sidebar').hasClass('subnav-fixed'))
			$('.messages').find('.info').addClass('info-fixed').removeClass('info');
		else
			$('.messages').find('.info').removeClass('info-fixed').addClass('info');
	};


	
	/* The parameter string has the following form: */
    /* ",str1,str2,...,strN," */
    /* The formDataListAttr function returns an array: [str1, str2, ..., strN]   */
    function formDataListAttr(strList) {

    	var array = strList.substring(1, strList.length-1).split(',');
    	var arrayL = array.length;
    	var obj = {};
    	for(var i=0; i<arrayL; i++) {
    		obj[array[i]] =true;
    	}
    	return obj;
    };



    /* It enables the btn (link) of the corresponding allowed action */
    function enableActions(actionsObj, removeItem) {
    	
    	var itemActionsL =selected.items.length;
    	var $actionBar = $('.sidebar');
    	if (removeItem) {
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
	    	if(!selected.items.length) {
	    		for(var prop in allowedActions) {
	    			allowedActions[prop] = availableActions[prop] && actionsObj[prop];
	    		}
	    	}
    		for(var prop in allowedActions) {
    			allowedActions[prop] = allowedActions[prop] && actionsObj[prop];
    		}
    	}
	    for(var prop in allowedActions) {
			if(allowedActions[prop]) {
    			$actionBar.find('a[data-action='+prop+']').removeAttr('disabled');
				
			}
			else {
				$actionBar.find('a[data-action='+prop+']').attr('disabled', '');
			}
		}
    };


	/* Modals */

	function addData(modal) {
		var $uuidsInput = 	$(modal).find('.modal-footer form input[name="ids"]');
		var $table = $(modal).find('.table-selected');
		var selectedNum = selected.items.length;
		var $selectedNum = $(modal).find('.num');
		var uuidsArray = [];

		for (var i=0; i<selectedNum; i++)
			uuidsArray.push(selected.items[i].uuid);

		$selectedNum.html(selectedNum);
		$uuidsInput.val('['+uuidsArray+']');
		drawTableRows($table.find('tbody'), selectedNum)
	};

	function drawTableRows(tableBody, rowsNum) {
		var maxVisible = 25;
		var templateRow = '<tr data-uuid=""><td class="full-name"></td><td class="email"></td><td class="remove"><a>X</a></td>';
		var currentRow;
		$(tableBody).empty();
		for(var i=0; i<rowsNum; i++) {
			currentRow =templateRow.replace('data-uuid=""', 'data-uuid="'+selected.items[i].uuid+'"')
			currentRow = currentRow.replace('<td class="full-name"></td>', '<td class="full-name">'+selected.items[i].name+'</td>');
			currentRow = currentRow.replace('<td class="email"></td>', '<td class="email">'+selected.items[i].email+'</td>');
			if(i > maxVisible)
				currentRow = currentRow.replace('<tr', '<tr class="hidden');
			$(tableBody).append(currentRow);
		}
	};

	/* remove an item after the modal is visible */
	$('.modal').on('click', 'td.remove a', function(e) {
		e.preventDefault();
		
		var $modal = $(this).closest('.modal')
		var $uuidsInput =	$modal.find('.modal-footer form input[name="ids"]');
		var $num = $modal.find('.num');
		var $tr = $(this).closest('tr');
		var itemUUID = $tr.data('uuid');
		var selectedNum = selected.items.length;
		// uuidsArray has only the uuids of selected items, none of the other info
		var uuidsArray = [];

		for(var i=0; i<selectedNum; i++) {
			if(selected.items[i].uuid === itemUUID) {
				removeItem(selected.items[i], selected.items);
				break;
			}
		}

		selectedNum = selected.items.length;
		for (var i=0; i< selectedNum; i++)
			uuidsArray.push(selected.items[i].uuid);
		$uuidsInput.val('[' + uuidsArray + ']');
		$tr.slideUp('slow');
		$num.html(selected.items.length);
	});

	/* When the user scrolls check if sidebar needs to get fixed position */
	$(window).scroll(function() {
		fixedMimeSubnav();
	});
	
	/* Sidebar */

	/* If the sidebar link is not disabled show the corresponding modal */
	$('.sidebar a').click(function(e) {
		if($(this).attr('disabled') !== undefined) {
			e.preventDefault();
			e.stopPropagation();
		}
		else {
			var modal = $(this).data('target');
			addData(modal);
		}
	});

	/* Table */
	
	/* Sort a colum with checkboxes */
	/* Create an array with the values of all the checkboxes in a column */
	$.fn.dataTableExt.afnSortData['dom-checkbox'] = function  (oSettings, iColumn) {
		return $.map( oSettings.oApi._fnGetTrNodes(oSettings), function (tr, i) {
			return $('td:eq('+iColumn+') input', tr).prop('checked') ? '0' : '1';
		} );
	}

	/* Initial table */
	
	function initTable(tableID) {

		// The last two colums in every table should be "Details" and "Summary"
		// These two shoudn't be sorted
		var colLength = $(tableID).find('thead th').length;
		var colsNotSort = [colLength-2, colLength-1];

		return $(tableID).dataTable({
			"aaSorting": [[3, 'asc'], [1, 'asc']], // ascending
			"aoColumnDefs": [
				{ "bSortable": false, "aTargets": colsNotSort },
				{  "sSortDataType": "dom-checkbox", "aTargets": [0] }
			],
			"bSortClasses": false, // Disables the addition of the classes 'sorting_1', 'sorting_2' and 'sorting_3' to the columns which are currently being sorted on
			// "sPaginationType": "full_numbers",
			"bRetrieve": true, // Access to all items of the dataTable
			"fnDrawCallback": function( oSettings ) {
				clickRow();
				clickRowCheckbox();
				clickSummary();
				updateToggleAllCheck('.select-all input[type=checkbox]');
		    }
		});
	}

	 var oTable = initTable('#table-items-total');


	function clickSummary() {
		$('table tbody a.summary-expand').click(function(e) {
			e.preventDefault();
			e.stopPropagation();

			var $summaryTd = $(this).closest('td');
			var $summaryContent = $summaryTd.find('.info-summary');
			
			var summaryContentWidth = $summaryTd.closest('tr').width() - parseInt($summaryContent.css('padding-right').replace("px", "")) - parseInt($summaryContent.css('padding-left').replace("px", ""));
			var summaryContPos = summaryContentWidth - $summaryTd.width() + parseInt($summaryContent.css('padding-left').replace("px", ""));
			
			$summaryContent.css({
				width: summaryContentWidth +'px',
				right: summaryContPos +'px'
			});

			$summaryContent.stop().slideToggle(600);

		})
	}

	$('.modal .reset-selected').click(function(e) {
		console.log('RESET');
		var table = '#'+ 'table-items-total_wrapper';
		resetTable(table);
	});
	$('.modal button[type=submit]').click(function(e) {
		if(selected.items.length === 0) {
			e.preventDefault();
			console.log('nothing to submit');
		}
	})

	/* Select-all checkbox */

	$('table thead th:first input[type=checkbox]').click(function(e) {
		e.stopPropagation();
		console.log('ox');
		var tableDomID = $(this).closest('table').attr('id');
		var checkboxState = $(this).prop('checked');
		toggleVisCheckboxes(checkboxState, tableDomID);
	});

/* *** Check fnRowCallback */
	$('.dataTables_filter input[type=text]').keypress(function(e) {

		// if space or enter is typed do nothing
		if(e.which !== '32' && e.which !== '13') {
			tableID = $(this).closest('.dataTables_wrapper').find('table').attr('id')
			resetTable('#'+tableID);
		}
	});

	function resetTable(tableDomID) {
		console.log('resetTable');
		$(tableDomID).find('thead .select-all input[type=checkbox]').attr('checked', false);
			selected.items = [];
			$(tableDomID).find('thead .selected-num').html(selected.items.length);
			$(tableDomID).find('thead .select-all input[type=checkbox]').prop('checked', false);
			// $(this).siblings('table').find('thead .selected-num');
			$('input:checked', oTable.fnGetNodes()).each(function(){
	            this.checked=false;
            });
            $(oTable.fnGetNodes()).each(function(){
	            this.className = this.className.replace('selected', '')
            });
            //  should use the code below
            // oTable.$('input').removeAttr('checked');
			// oTable.$('tr').removeClass('selected');
			enableActions(undefined, true);
	}

	/* Checkboxes */
	function clickRowCheckbox() {
		$('table tbody input[type=checkbox]').click(function(e) {
			e.stopPropagation();
			// console.log('good ', e)
			// console.log('e.target', e)
			var $tr = $(this).closest('tr');
			var $allActionsBtns = $('.sidebar a');
			var $selectedNum = $tr.closest('table').find('thead .selected-num');

			var uuid = $tr.attr('id');
			var name = $tr.find('td.name').text();
			var email = $tr.find('td.email').text();
			var itemsL;

			var newItem = {
				uuid: uuid,
				name: name,
				email: email,
				actions: {}
			}
			newItem.actions =  formDataListAttr($tr.data('op-list'));
			for(var prop in availableActions) {
				if(!(prop in newItem.actions)) {
					newItem.actions[prop] =false
				} 
			}
			
			if (this.checked) {
				itemsL = selected.items.length;
				var isNew = true;
				for(var i=0; i<itemsL; i++) {
					if(selected.items[i].uuid === uuid) {
						isNew = false;
					}
				}
				if(isNew) {
					$tr.addClass('selected');
					enableActions(newItem.actions)
					addItem(newItem, selected.items);
				}
			}
			else {
				$tr.removeClass('selected');
				removeItem(newItem, selected.items);
				enableActions(newItem.actions, true);
			}
				$selectedNum.html(selected.items.length);
			updateToggleAllCheck();
		});
	};
	function updateToggleAllCheck() {
		console.log('updateToggleAllCheck');
		var toggleAll = $('table .select-all input[type=checkbox]');
		if($('tbody tr').length > 1) {
			var allChecked = true
			$('tbody input[type=checkbox]').each(function() {
				allChecked = allChecked && $(this).prop('checked');
			});
			if(!toggleAll.prop('checked') && allChecked) {
				console.log('*1*')
				toggleAll.prop('checked', true)
			}
			else if(toggleAll.prop('checked') && !allChecked) {
				toggleAll.prop('checked', false)
			}
		}
		else {
			toggleAll.prop('checked', false);
		}
	};
	
	function clickRow() {
		$('table tbody tr').click(function(e) {
			$(this).find('input[type=checkbox]').trigger('click');
		});
	};

	var curPath = window.location.pathname;
	$('.nav-main li').each(function () {
		if($(this).find('a').attr('href') === curPath) {
			$(this).closest('li').addClass('active');
		}
		else {
			$(this).closest('li').removeClass('active');
		}
	});

	/* Head checkbox */

	/* Toggles the checked property of all the checkboxes in the body of the table */
	function toggleVisCheckboxes(checkboxState, tableDomID) {
		var $checkboxesVis = $('#'+tableDomID).find('tbody tr:visible .checkbox-column input[type=checkbox]');
		if(checkboxState) {
			$checkboxesVis.prop('checked', false).trigger('click');
		}
		else {
			if($checkboxesVis.prop('checked')) {
				$checkboxesVis.trigger('click');
			}
			else
				$checkboxesVis.prop('checked', false).trigger('click');
		}
	};

	/* Items select/remove */

	/* Removes from an array an element */
	function removeItem(item, array) {
		console.log('removeItem');
		var index;
		if (typeof(item) === 'object') {
			console.log('eimai ena object!')
			index = array.map(function(item) {
				console.log('item.id ', item.uuid)
				return item.uuid;
			}).indexOf(item.uuid);
			console.log('index ', index);
		}
		else
			index = array.indexOf(item);

		if(index > -1) {
			array.splice(index, 1);
		}
	};

	function addItem(item, array) {
		array.push(item);
	};
}); // end of document ready

