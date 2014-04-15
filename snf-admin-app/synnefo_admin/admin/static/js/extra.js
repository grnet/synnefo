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


	/* Head checkbox */

	/* Toggles the checked property of all the checkboxes in the body of the table */
	function toggleVisCheckboxes(checkboxState, tableDomID) {
		var $checkboxesVis = $('#'+tableDomID).find('tbody tr:visible .checkbox-column input[type=checkbox]');
		
		if(checkboxState) {
			$checkboxesVis.prop('checked', false).trigger('click');
		}
		else {
			if($checkboxesVis.prop('checked')) {
				console.log('yiou!')
				$checkboxesVis.trigger('click');
			}
			else
				$checkboxesVis.prop('checked', false).trigger('click');
		}
	};

	/* Items select/remove */

	/* Removes from an array an element */
	function removeItem(item, array) {
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
			console.log(currentRow);
			console.log($(tableBody));
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
		var uuidsArray = [];
		for(var i=0; i<selectedNum; i++) {
			if(selected.items[i].uuid === itemUUID) {
				removeItem(selected.items[i], selected.items);
			}
		}
		for (var i=0; i< --selectedNum; i++)
			uuidsArray.push(selected.items[i].uuid);
		$uuidsInput.val('['+uuidsArray+']');
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
	

	var oTable = $('#table-items-total').dataTable({
		"aaSorting": [[3, 'asc'], [1, 'asc']], // ascending
		"aoColumnDefs": [
			{ "bSortable": false, "aTargets": [5, 6] },
			{  "sSortDataType": "dom-checkbox", "aTargets": [0] }
		],
		"bSortClasses": false,
		// "sPaginationType": "full_numbers",
		"bRetrieve": true, // acces to all items of the dataTable
		"fnDrawCallback": function( oSettings ) {
      	clickRow();
      	clickRowCheckbox();
      	clickSummary();
    }

	});
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

	/* Select-all checkbox */

	$('table thead th:first input[type=checkbox]').click(function(e) {
		e.stopPropagation();
		console.log('ox');
		var tableDomID = $(this).closest('table').attr('id');
		var checkboxState = $(this).prop('checked');
		toggleVisCheckboxes(checkboxState, tableDomID);
	});

	$('.dataTables_filter input[type=text]').keypress(function(e) {
		// if space or enter is typed do nothing
		if(e.which !== '32' && e.which !== '13') {
			$(this).closest('.dataTables_wrapper').find('table thead .select-all input[type=checkbox]').attr('checked', false);
			selected.items = [];
			$(this).closest('.dataTables_wrapper').find('table thead .selected-num').html(selected.items.length);
		
			$(this).siblings('table').find('thead .selected-num');
			oTable.$('input').removeAttr('checked');
			oTable.$('tr').removeClass('selected');
		}
	});


	/* Checkboxes */
	function clickRowCheckbox() {
		$('table tbody input[type=checkbox]').click(function(e) {
			e.stopPropagation();

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
		});
	};
	
	function clickRow() {
		$('table tbody tr').click(function() {
			$(this).find('input[type=checkbox]').trigger('click');
		});
	};
});

