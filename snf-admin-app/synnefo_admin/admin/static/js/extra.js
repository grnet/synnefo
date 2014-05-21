var mydata; // temp

(function($, Django){

$(function(){
	var lastClicked = null;
	var prevClicked = null;
	var selected = {
		items: [],
		actions: {}
	};

	var availableActions = {};
	var allowedActions= {};

	/* Actionbar */
	$('.actionbar button').each(function() {
		availableActions[$(this).data('action')] = true;
	});

	for(var prop in availableActions) {
		allowedActions[prop] = true;
	}

	/* If the sidebar link is not disabled show the corresponding modal */
	$('.actionbar button').click(function(e) {
		if($(this).hasClass('disabled')) {
			e.preventDefault();
			e.stopPropagation();
		}
		else {
			var modal = $(this).data('target');
			addData(modal);
		}
	});


	/* Table */

	/* Currently not in use */
	/* Sort a colum with checkboxes */
	/* Create an array with the values of all the checkboxes in a column */
	$.fn.dataTableExt.afnSortData['dom-checkbox'] = function  (oSettings, iColumn) {
		return $.map( oSettings.oApi._fnGetTrNodes(oSettings), function (tr, i) {
			return $('td:eq('+iColumn+') input', tr).prop('checked') ? '0' : '1';
		} );
	};

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
				return '<a href="'+ data.value +'" class="details-link">'+ data.display_name+'</a>';
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
			var selectedL = selected.items.length;
			if(selectedL !== 0) {
				for(var i = 0; i<selectedL; i++){
					if (selected.items[i].id === row.id) {
						$(row).addClass('selected')
					}
				}
			}

			clickSummary(row);
			clickDetails(row);
		},
		"dom": '<"custom-buttons">lfrtip'
	});
	$("div.custom-buttons").html('<button class="select-all select">Select All</button>');


	$(tableDomID).on('click', 'tbody tr', function(e) {
		selectRow(this, e.type);
		var select;
		if($(this).hasClass('selected')) {
			select = true;
		}
		else {
			select = false;
		}
		if(e.shiftKey && prevClicked !== null && lastClicked !== null) {
			var startRow;
			var start = prevClicked.index() + 1;
			var end = lastClicked.index();
			if(start < end) {
				startRow = prevClicked.next();
				for (var i = start; i<end; i++) {
					if((select && !($(startRow).hasClass('selected'))) || (!select && $(startRow).hasClass('selected'))) {
						selectRow(startRow);
					}
					startRow = startRow.next();
				}
			}
			else if(end < start) {
				startRow = prevClicked.prev();
				end = end+2;
				for (var i = start; i>end; i--) {
					if((select && !($(startRow).hasClass('selected'))) || (!select && $(startRow).hasClass('selected'))) {
						selectRow(startRow);
					}
					startRow = startRow.prev();
				}
			}
			}
	});

	$(document).bind('keydown', function(e){
		if(e.shiftKey) {
			$(tableDomID).addClass('with-shift')
		}
	});

	$(document).bind('keyup', function(e){
		if(e.which === 16) {
			$(tableDomID).removeClass('with-shift')
		}
	});

	function selectRow(row, event) {
		var $row = $(row);
		if(event === "click") { // the param is event from a tr
			prevClicked = lastClicked;
			lastClicked = $row
		}
		var info = $(tableDomID).dataTable().api().cell($row.find('td:last-child')).data();
		if($row.hasClass('selected')) {
			$row.removeClass('selected');
			removeItem(info.id.value);
			enableActions(undefined, true)
		}
		else {
			$row.addClass('selected');
			var newItem = addItem(info);
				enableActions(newItem.actions)
		}
		updateCounter('.selected-num');
		updateToggleAllSelect();
	};

	function updateCounter(counterDOM) {
		var $counter = $(counterDOM);
		$counter.text(selected.items.length);
	};

	function summaryTemplate(data) {
		var listTemplate = '<dt>{key}:</dt><dd>{value}</dd>';
		var list = '';
		var listItem = listTemplate.replace('{key}', prop).replace('{value}',data[prop]);
		var html;

		for(var prop in data) {
			if(prop !== "details_url") {
				if(data[prop].visible) {
					list += listTemplate.replace('{key}', data[prop].display_name).replace('{value}',data[prop].value);
				}
			}
		}

		html = '<a href="#" class="summary-expand expand-area"><span class="snf-icon snf-angle-down"></span></a><dl class="info-summary dl-horizontal">'+ list +'</dl>';
		return html;
	};

	function clickDetails(row) {
		$(row).find('a.details-link').click(function(e) {
			e.stopPropagation();
		})
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
	};


	function addItem(infoObj) {
		var $selectedNum = $('.actionbar button').find('.selected-num');
		var itemsL;
		var newItem = {}
		var isNew = true;
		var actionsArray = infoObj.allowed_actions.value;
		var actionsL = actionsArray.length;
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
			return newItem
		}
		return null;
	};

	function removeItem(itemID) {
		var items = selected.items;
		var itemsL = items.length;
		for (var i = 0; i<itemsL; i++) {
			if(items[i].id === itemID) {
				items.splice(i, 1);
				break;
			}
		}
	};


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

	function resetTable(tableDomID) {
		// $(tableDomID).find('thead .select-all input[type=checkbox]').attr('checked', false);
		selected.items = [];
		// $(tableDomID).find('thead .selected-num').html(selected.items.length);
		// $(this).siblings('table').find('thead .selected-num');
		updateCounter('.selected-num');
		enableActions(undefined, true);
		$(tableDomID).dataTable().api().rows('.selected').nodes().to$().removeClass('selected');
		updateToggleAllSelect();
	};

	$('.dataTables_filter input[type=search]').keypress(function(e) {
		// if space or enter is typed do nothing
		if(e.which !== '32' && e.which !== '13') {
			// $(tableDomID) = $(this).closest('.dataTables_wrapper').find('table').attr('id')
			resetTable(tableDomID);
		}
	});

	 /* Select-all button */

	$('.select-all').click(function() {
		toggleVisSelected(tableDomID, $(this).hasClass('select'));
	});

	/* select-all / deselect-all */
	function toggleVisSelected(tableDomID, selectFlag) {
		lastClicked = null;
		prevClicked = null;
		if(selectFlag) {
			$(tableDomID).find('tbody tr:not(.selected)').each(function() { // temp : shouldn't have a func that calls a named func
				selectRow(this);
			});
		}
		else {
			$(tableDomID).find('tbody tr.selected').each(function() { // temp : shouldn't have a func that calls a named func
				selectRow(this);
			});
		}
	};

	/* Checks how many rows are selected and adjusts the classes and
	the text of the select-qll btn */
	function updateToggleAllSelect() {

		var $toggleAll = $('.select-all');
		$tr = $(tableDomID).find('tbody tr');

		if($tr.length > 1) {
			var allSelected = true
			$tr.each(function() {
				allSelected = allSelected && $(this).hasClass('selected');
			});
			if($toggleAll.hasClass('select') && allSelected) {
				$toggleAll.addClass('deselect').removeClass('select');
				$toggleAll.text('Deselect All')
			}
			else if(!($toggleAll.hasClass('select')) && !allSelected) {
				$toggleAll.addClass('select').removeClass('deselect');
				$toggleAll.text('Select All')
			}
		}
		else {
			$toggleAll.addClass('select').removeClass('deselect')
			$toggleAll.text('Select All')
		}
	};


	/* Modals */

	function showError(modal, errorSign) {
		var $modal = $(modal);
		var $errorMsg = $modal.find('*[data-error="'+errorSign+'"]');
		$errorMsg.show();
	};

	function resetErrors(modal) {
		var $modal = $(modal);
		$modal.find('.error-sign').hide();
	};

	function checkInput(modal, inputArea, errorSign) {
		var $inputArea = $(inputArea);
		var $errorSign = $(modal).find('*[data-error="'+errorSign+'"]');

		$inputArea.keyup(function() {
			if($.trim($inputArea.val())) {
				$errorSign.hide();
			}
		})

	};
	function resetInputs(modal) {
		var $modal = $(modal);
		$modal.find('textarea').val('');
		$modal.find('input[type=text]').val('');

	};

	$('.modal .reset-all').click(function(e) {
		// var table = '#'+ 'table-items-total_wrapper';
		var $modal = $(this).closest('.modal');
		resetErrors($modal);
		resetInputs($modal);
		resetTable(tableDomID);
	});
	$('.modal button[type=submit]').click(function(e) {
		var $modal = $(this).closest('.modal');

		if(selected.items.length === 0) {
			e.preventDefault();
			showError($modal, 'no-selected');
		}
		if($modal.attr('id') === 'contact') {
			var $emailSubj = $modal.find('.subject')
			var $emailCont = $modal.find('.content')
			if(!$.trim($emailSubj.val())) {
				e.preventDefault();
				showError($modal, 'empty-subject');
				checkInput($modal, $emailSubj, 'empty-subject');
			}
			if(!$.trim($emailCont.val())) {
				e.preventDefault();
				showError($modal, 'empty-body')
				checkInput($modal, $emailCont, 'empty-body');
			}
		}
	});

	function addData(modalID) {
		var $idsInput = $(modalID).find('.modal-footer form input[name="ids"]');
		var $table = $(modalID).find('.table-selected');
		var selectedNum = selected.items.length;
		var $counter = $(modalID).find('.num');
		var idsArray = [];
		var unique = true;
		var queryProp = 'id'; // temp
		// var queryProp;
		var modalType = $(modalID).data('type');

		/* *** shouldn't do this check twice! *** */

		// if(modalType === "contact")
		// 	queryProp = 'id';
		// else
		// 	queryProp = 'user_id';

		// for (var i=0; i<selectedNum; i++) {
		// 	for (var j=0; j<i; j++) {
		// 		if(selected.items[i][queryProp] === selected.items[j][queryProp]) {
		// 			unique = false;
		// 			break;
		//     	}
		// 	}
		// 	if(unique) {
		   //      idsArray.push(selected.items[i][queryProp]);
		// 	}
		// 	unique = true;
		// }
		updateCounter($counter);
		$idsInput.val('['+idsArray+']');
		drawTableRows($table.find('tbody'), selectedNum,  modalType);
	};

	function drawTableRows(tableBody, rowsNum, modalType) {
		var maxVisible = 2;
		var currentRow;
		$(tableBody).empty();
		var htmlRows = '';
		var unique = true;
		var uniqueProp = 'contact_email'; // temp
		var count = 0;
		if(modalType === "contact") {
			var templateRow = '<tr data-itemid=""><td class="full-name"></td><td class="email"></td><td class="remove"><a>X</a></td></tr>';
			for(var i=0; i<rowsNum; i++) {
				for(var j = 0; j<i; j++) {
					if(selected.items[i][uniqueProp] === selected.items[j][uniqueProp]) {
						unique = false;
						break;
					}
				}
				if(unique === true) {
					currentRow =templateRow.replace('data-itemid=""', 'data-itemid="'+selected.items[i].id+'"')
					currentRow = currentRow.replace('<td class="full-name"></td>', '<td class="full-name">'+selected.items[i].contact_name+'</td>');
					currentRow = currentRow.replace('<td class="email"></td>', '<td class="email">'+selected.items[i].contact_email+'</td>');
					if(i >= maxVisible)
						currentRow = currentRow.replace('<tr', '<tr class="hidden-row"');
					htmlRows += currentRow;
				}
			}
		}
		else {
			var templateRow = '<tr data-itemid=""><td class="item-name"></td><td class="item-id"></td><td class="owner-name"></td><td class="owner-email"></td><td class="remove"><a>X</a></td></tr>';
			for(var i=0; i<rowsNum; i++) {
				currentRow =templateRow.replace('data-itemid=""', 'data-itemid="'+selected.items[i].id+'"')
				currentRow = currentRow.replace('<td class="item-name"></td>', '<td class="item-name">'+selected.items[i].item_name+'</td>');
				currentRow = currentRow.replace('<td class="item-id"></td>', '<td class="item-id">'+selected.items[i].id+'</td>');
				currentRow = currentRow.replace('<td class="owner-name"></td>', '<td class="owner-name">'+selected.items[i].contact_name+'</td>');
				currentRow = currentRow.replace('<td class="owner-email"></td>', '<td class="owner-email">'+selected.items[i].contact_email+'</td>');
				if(i >= maxVisible)
					currentRow = currentRow.replace('<tr', '<tr class="hidden-row"');
				htmlRows += currentRow;
			}
		}
		$(tableBody).append(htmlRows); // should change
		
		if(rowsNum >= maxVisible) {
			var $btn = $(tableBody).closest('.modal').find('.toggle-more');
			var rowsNum = selected.items.length;

			$btn.css('display', 'block');

			$btn.click( function(e) {
				// e.preventDefault();
					var that = this;
				if($(this).hasClass('closed')) {
					// $(this).text('Show Less');
					$(this).toggleClass('closed open');
					$(tableBody).find('tr').slideDown('slow', function() {
						$(that).text('Show Less');
					});
				}
				else if($(this).hasClass('open')) {
					$(this).toggleClass('closed open');
					$(tableBody).find('tr.hidden-row').slideUp('slow', function() {
					$(that).text('Show All');

					});
				}
			});
		}
	};

	/* remove an item after the modal is visible */
	$('.modal').on('click', 'td.remove a', function(e) {
		e.preventDefault();
		var $modal = $(this).closest('.modal')
		var $idsInput = $modal.find('.modal-footer form input[name="ids"]');
		var $num = $modal.find('.num');
		var $tr = $(this).closest('tr');
		var itemID = $tr.data('itemid');
		// uuidsArray has only the uuids of selected items, none of the other info
		idsArray = [];

		removeItem(itemID, false);

		var selectedNum = selected.items.length;
		for (var i=0; i< selectedNum; i++)
			idsArray.push(selected.items[i].id);
		$idsInput.val('[' + idsArray + ']');
		$tr.slideUp('slow', function() {
			$(this).siblings('.hidden-row').first().removeClass('hidden-row');
			if($(this).siblings('.hidden-row').length === 0) {
				$modal.find('.toggle-more').hide(); // it would be better to be visible and disabled? ***
			}
		});
		$num.html(selectedNum);
	});


	/* General */

	var curPath = window.location.pathname;
	$('.nav-main li').each(function () {
		if($(this).find('a').attr('href') === curPath) {
			$(this).closest('li').addClass('active');
		}
		else {
			$(this).closest('li').removeClass('active');
		}
	});


	/* When the user scrolls check if sidebar needs to get fixed position */
	/*$(window).scroll(function() {
		fixedMimeSubnav();
	});*/


	/* Sets sidebar's position fixed */
	/* subnav-fixed is added/removed from processScroll() */
/*  function fixedMimeSubnav() {
		if($('.actionbar').hasClass('subnav-fixed'))
			$('.info').addClass('info-fixed').removeClass('info');
		else
			$('.info').removeClass('info-fixed').addClass('info');
	};

*/

	/* Currently not in use */
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

	/* Currently not in use */
	/* Extend String Prototype */
	String.prototype.toDash = function(){
		return this.replace(/([A-Z])/g, function($1){
			return "-"+$1.toLowerCase();
		});
	};



});
}(window.jQuery, window.Django));
