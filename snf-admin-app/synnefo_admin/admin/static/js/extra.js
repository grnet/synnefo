var mydata; // temp

(function($, Django){

$(function(){
	var lastClicked = null;
	var prevClicked = null;
	 selected = {
		items: [],
		actions: {}
	};

	var availableActions = {};
	var allowedActions= {};

	/* Actionbar */
	$('.actionbar a').each(function() {
		availableActions[$(this).data('action')] = true;
	});

	for(var prop in availableActions) {
		allowedActions[prop] = true;
	}

	/* If the sidebar link is not disabled show the corresponding modal */
	$('.actionbar a').click(function(e) {
		if($(this).hasClass('disabled')) {
			e.preventDefault();
			e.stopPropagation();
		}
		else {
			if($(this).hasClass('toggle-selected')) {
				if($(this).hasClass('open')) {
					$(this).removeClass('open');
					$('#table-items-selected_wrapper').slideUp('slow');
				}
				else {
					$(this).addClass('open');
					$('#table-items-selected_wrapper').slideDown('slow');
				}
			}
			else {
				var modal = $(this).data('target');
				drawModal(modal);
			}
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
	// var tableSelected;
	$.fn.dataTable.ext.legacy.ajax = true;
	var extraData;
	// sets the classes of the btns that are used for navigation throw the pages (next, prev, 1, 2, 3...)
	// $.fn.dataTableExt.oStdClasses.sPageButton = "btn btn-primary";

	var tableDomID = '#table-items-total';
	var tableSelectedDomID = '#table-items-selected'
	var tableMassiveDomID = '#total-list'
	table = $(tableDomID).DataTable({
		"paging": true,
		"processing": true,
		"serverSide": serverside,
		"ajax": {
			"url": url,
			"data": function(data, callback, settings) {

				var prefix = 'sSearch_';

				if(!$.isEmptyObject(filters)) {
					for (var prop in filters) {
						data[prefix+prop] = filters[prop];
					}
				}
			},
			"dataSrc" : function(response) {
				mydata = response;
				extraData = response.extra;
				if(response.aaData.length != 0) {
					var rowsArray = response.aaData;
					var rowL = rowsArray.length;
					var extraCol = rowsArray[0].length; //last column
					for (var i=0; i<rowL; i++) {
						rowsArray[i][extraCol] = response.extra[i]
					}
				}
				console.log('return response', new Date)
				return response.aaData;
			}
		},
		"columnDefs": [
		{
			"targets": 0,
			"render": function(data, type, rowData) {
				return checkboxTemplate(data, 'unchecked');
			}
		},
		{
			"targets": -1, // the first column counting from the right is "Summary"
			"orderable": false,
			"render": function(data, type, rowData) {
				return extraTemplate(data);
			}
		},
		],
		"order": [1, "asc"],
		"createdRow": function(row, data, dataIndex) {
			var extraIndex = data.length - 1;
			row.id = data[extraIndex].id.value; //sets the dom id
		},
		"dom": '<"custom-buttons">frtilp',
		"language" : {
			"sLengthMenu": 'Pagination _MENU_'
		},
		"drawCallback": function(settings) {
			isSelected();
			updateToggleAllSelect();
			clickSummary(this);
			clickDetails(this);
		}
	});
	$("div.custom-buttons").html('<a href="" class="select-page select custom-btn" data-karma="neutral"><span>Select Page</span></a>'+'<a href="" class="select select-all custom-btn" data-karma="neutral" data-toggle="modal" data-target="#massive-actions-warning"><span>Select All</span></a>'+'<a href="" class="deselect clear-all custom-btn" data-karma="neutral" data-toggle="modal" data-target="#clear-all-warning"><span>Clear All</span></a>');

	function isSelected() {
		var tableLength = table.rows()[0].length;
		var selectedL = selected.items.length;
		if(selectedL !== 0 && tableLength !== 0) { // ***
			var dataLength = table.row(0).data().length
			var extraIndex = dataLength - 1;
			for(var j = 0; j<tableLength; j++) { // index of rows start from zero
				for(var i = 0; i<selectedL; i++){
					if (selected.items[i].id === table.row(j).data()[extraIndex].id.value) {
						$(table.row(j).nodes()).addClass('selected');
						$(table.row(j).nodes()).find('td:first-child .selection-indicator').toggleClass('snf-checkbox-checked snf-checkbox-unchecked');
						break;
					}
				}
			}
		}
	}

	var newTable = true;
	$('.select-all-confirm').click(function(e) {
		$(this).closest('.modal').addClass('in-progress');
		console.log('select all items', new Date);
		if(newTable) {
			// console.log('newtable')
			newTable = false;
			countme = true;
			$(tableMassiveDomID).DataTable({
				"paging": false,
				"processing": false,
				"serverSide": true,
				"ajax": {
					"url": url,
					"data": function(data, callback, settings) {

						var prefix = 'sSearch_';

						if(!$.isEmptyObject(filters)) {
							for (var prop in filters) {
								data[prefix+prop] = filters[prop];
							}
						}
					},

					"dataSrc" : function(response) {
						alldata = response;
						extraData = response.extra;
						if(response.aaData.length != 0) {
							var rowsArray = response.aaData;
							var rowL = rowsArray.length;
							var extraCol = rowsArray[0].length; //last column
							for (var i=0; i<rowL; i++) {
								rowsArray[i][extraCol] = response.extra[i]
							}
						}
						console.log('return response', new Date)
						return response.aaData;
					}
				},
				createdRow: function(row, data, dataIndex) {
					if(countme) {
						console.log('1st row', new Date);
						countme = false;
					}
					var info = data[data.length - 1];
					// console.log(info);
					var newItem = addItem(info);
					if(newItem !== null) {
						enableActions(newItem.actions);
						keepSelected(data);
					}

				},
				"drawCallback": function(settings) {
					console.log('1-drawCallback', new Date)
					isSelected();
					updateCounter('.selected-num')
					$('#massive-actions-warning').modal('hide')
					$('#massive-actions-warning').removeClass('in-progress')
					console.log('2-drawCallback', new Date)
					tableSelected.rows().draw();
					console.log('3-drawCallback', new Date)
				}
			});
		}
		else {
			$(tableMassiveDomID).dataTable().api().ajax.reload();
		}
	});

	tableSelected = $(tableSelectedDomID).DataTable({
		"columnDefs": [
		{
			"targets": 0,
			"render": function(data, type, rowData) {
				return checkboxTemplate(data, 'checked');
			}
		},
		{
			"targets": -1, // the first column counting from the right is "Summary"
			"orderable": false,
			"render": function(data, type, rowData) {
				return extraTemplate(data);
			},
		},
		],
		"order": [1, "asc"],
		"lengthMenu": [[5, 10, 25, 50, -1], [5, 10, 25, 50, "All"]],
		"dom": 'frtilp',
		"language" : {
			"sLengthMenu": 'Pagination _MENU_'
		},
		"drawCallback": function(settings) {
			clickSummary(this);
			clickDetails(this);
		},
		"createdRow": function(row, data, dataIndex) {
			var extraIndex = data.length - 1;
			row.id = 'selected-'+data[extraIndex].id.value; //sets the dom id
		},
	});

	function keepSelected(data, drawNow) {
		if(drawNow) {
			tableSelected.row.add(data).draw();
		}
		else
			tableSelected.row.add(data).node();
	};

	function removeSelected(rowID) {
		if(rowID === true) {
			tableSelected.clear().draw()
		}
		else {
			tableSelected.row('#selected-'+rowID).remove().draw();
		}
	};

	function updateDisplaySelected() {
		if(selected.items.length > 0) {
			$('.actionbar').find('a.toggle-selected').removeClass('disabled');
		}
		else {
			$('.actionbar').find('a.toggle-selected').addClass('disabled');	
		}
	}

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
		$row.find('td:first-child .selection-indicator').toggleClass('snf-checkbox-checked snf-checkbox-unchecked');
		if(event === "click") { // the param is event from a tr
			prevClicked = lastClicked;
			lastClicked = $row
		}
		var infoRow = table.row($row).data();
		var info = infoRow[infoRow.length - 1]
		// var info = $(tableDomID).dataTable().api().cell($row.find('td:last-child')).data();
		if($row.hasClass('selected')) {
			$row.removeClass('selected');
			removeItem(info.id.value);
			enableActions(undefined, true);
			removeSelected($row.attr('id'));
		}
		else {
			$row.addClass('selected');
			var newItem = addItem(info);
			enableActions(newItem.actions)
			selData = table.row($row).data();
			keepSelected(selData, true);
		}
		updateCounter('.selected-num');
		updateToggleAllSelect();
	};

	function updateCounter(counterDOM, num) {
		var $counter = $(counterDOM);
		if(num) {
			$counter.text(num);			
		}
		else {
			$counter.text(selected.items.length);
		}
	};

	function checkboxTemplate(data, initState) {
		var html = '<span class="snf-icon snf-checkbox-'+initState+' selection-indicator"></span>'+data;
		return html;
	}

	function extraTemplate(data) {

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

		html = '<a href="'+ data["details_url"].value +'" class="details-link"><span class="snf-icon snf-search"></span></a><a href="#" class="summary-expand expand-area"><span class="snf-icon snf-angle-down"></span></a><dl class="info-summary dl-horizontal">'+ list +'</dl>';
		return html;
	};

	function clickDetails(table) {
		$(table).find('tbody td:last-child a.details-link').click(function(e) {
			e.stopPropagation();
		})
	}

	function clickSummary(table) {
		$(table).find('tbody td:last-child a.expand-area').click(function(e) {
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
		var $selectedNum = $('.actionbar a').find('.selected-num');
		var itemsL;
		var newItem = {}
		var isNew = true;
		var actionsArray = infoObj.allowed_actions.value;
		var actionsL = actionsArray.length;
		var newItem = {
		   "id": infoObj.id.value,
		   "item_name": infoObj.item_name.value,
		   "contact_id": infoObj.contact_id.value,
		   "contact_name": infoObj.contact_name.value,
		   "contact_email": infoObj.contact_mail.value,
		   "actions": {}
		}

		itemsL = selected.items.length;
			for(var i=0; i<itemsL; i++) {
				if(selected.items[i].id === newItem.id) {
					isNew = false;
					break;
				}
			}
		if(isNew) {
			for (var i = 0; i<actionsL; i++) {
				newItem.actions[actionsArray[i]] = true;
			}
			for(var prop in availableActions) {
				if(!(prop in newItem.actions)) {
					newItem.actions[prop] = false;
				}
			}
			selected.items.push(newItem);
			return newItem
		}
		else
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
		updateDisplaySelected();
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
				$actionBar.find('a[data-action='+prop+']').removeClass('disabled');
			}
			else {
				$actionBar.find('a[data-action='+prop+']').addClass('disabled');
			}
		}
	};

	function resetTable(tableDomID) {
		selected.items = [];
		removeSelected(true); //removes all selected items from the table of selected items
		updateCounter('.selected-num');
		enableActions(undefined, true);
		$(table.rows('.selected').nodes()).find('td:first-child .selection-indicator').toggleClass('snf-checkbox-checked snf-checkbox-unchecked');
		$(tableDomID).dataTable().api().rows('.selected').nodes().to$().removeClass('selected');

		updateToggleAllSelect();
	};


	 /* select-page button */

	$('.select-page').click(function(e) {
		e.preventDefault();
		toggleVisSelected(tableDomID, $(this).hasClass('select'));
	});


	/* select-page / deselect-page */
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
		// console.log('updateToggleAllSelect', new Date)
		var $togglePageItems = $('.select-page');
		var $label = $togglePageItems.find('span')
		var $tr = $(tableDomID).find('tbody tr');
		if($tr.length > 1) {
			var allSelected = true
			$tr.each(function() {
				allSelected = allSelected && $(this).hasClass('selected');
				return allSelected;
			});
			if($togglePageItems.hasClass('select') && allSelected) {
				$togglePageItems.addClass('deselect').removeClass('select');
				$label.text('Deselect Page')
			}
			else if($togglePageItems.hasClass('deselect') && !allSelected) {
				$togglePageItems.addClass('select').removeClass('deselect');
				$label.text('Select Page')
			}
		}
		else {
			$togglePageItems.addClass('select').removeClass('deselect')
			$label.text('Select All')
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
	function removeWarnings(modal) {
		var $modal = $(modal);
		modal.find('.warning-duplicate').remove();
	}

	$('.modal .reset-all').click(function(e) {
		// var table = '#'+ 'table-items-total_wrapper';
		var $modal = $(this).closest('.modal');
		resetErrors($modal);
		resetInputs($modal);
		removeWarnings($modal);
		resetTable(tableDomID);
	});
	$('.modal button[type=submit]').click(function(e) {
		var $modal = $(this).closest('.modal');

		// if(selected.items.length === 0) {
		// 	e.preventDefault();
		// 	showError($modal, 'no-selected');
		// }
		if($modal.attr('id') === 'contact') {
			var $emailSubj = $modal.find('.subject')
			var $emailCont = $modal.find('.email-content')
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


	function drawModal(modalID) {
		var $tableBody = $(modalID).find('.table-selected tbody');
		var modalType = $(modalID).data('type');
		var $counter = $(modalID).find('.num');
		var rowsNum = selected.items.length;
		var maxVisible = 5;
		var currentRow;
		var htmlRows = '';
		var unique = true;
		var uniqueProp = '';
		var count = 0;
		var $idsInput = $(modalID).find('.modal-footer form input[name="ids"]');
		var idsArray = [];
		var warningMsg = '<p class="warning-duplicate">Duplicate accounts have been detected</p>';
		$tableBody.empty();
		if(modalType === "contact") {
			uniqueProp = 'contact_id'
			var templateRow = '<tr data-toggle="tooltip" data-placement="bottom" title="" data-itemid=""><td class="full-name"></td><td class="email"></td><td class="remove"><a>X</a></td></tr>';
			for(var i=0; i<rowsNum; i++) {
				for(var j = 0; j<i; j++) {
					if(selected.items[i][uniqueProp] === selected.items[j][uniqueProp]) {
						unique = false;
						break;
					}
				}
				if(unique === true) {
					idsArray.push(selected.items[i][uniqueProp]);
					currentRow = templateRow.replace('data-itemid=""', 'data-itemid="'+selected.items[i].contact_id+'"');
					currentRow = currentRow.replace('title=""', 'title="'+selected.items[i].item_name+'"')
					currentRow = currentRow.replace('<td class="full-name"></td>', '<td class="full-name">'+selected.items[i].contact_name+'</td>');
					currentRow = currentRow.replace('<td class="email"></td>', '<td class="email">'+selected.items[i].contact_email+'</td>');
					if(i >= maxVisible)
						currentRow = currentRow.replace('<tr', '<tr class="hidden-row"');
					htmlRows += currentRow;
				}
				else {
					htmlRows = htmlRows.replace('" data-itemid="' + selected.items[i].contact_id + '"', ', '+selected.items[i].item_name+'" data-itemid="' + selected.items[i].contact_id+'"');
					$tableBody.closest('table').before(warningMsg);
				}
			}
		}


		else {
			uniqueProp = 'id';

			var templateRow = '<tr data-itemid=""><td class="item-name"></td><td class="item-id"></td><td class="owner-name"></td><td class="owner-email"></td><td class="remove"><a>X</a></td></tr>';
			for(var i=0; i<rowsNum; i++) {
				idsArray.push(selected.items[i][uniqueProp]);
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
		$tableBody.append(htmlRows); // should change
		$tableBody.find('tr').tooltip();
		$idsInput.val('['+idsArray+']');
		updateCounter($counter, idsArray.length); // ***
		
		if(idsArray.length >= maxVisible) {
			var $btn = $(modalID).find('.toggle-more');
			// rowsNum = idsArray.length;

			$btn.css('display', 'block');

			$btn.click( function(e) {
				var that = this;
				if($(this).hasClass('closed')) {
					$(this).toggleClass('closed open');
					$tableBody.find('tr').slideDown('slow', function() {
						$(that).text('Show Less');
						// $(this).removeClass('hidden-row')
					});
				}
				else if($(this).hasClass('open')) {
					$(this).toggleClass('closed open');
					$tableBody.find('tr.hidden-row').slideUp('slow', function() {
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
			$(this).siblings('.hidden-row').first().css('display', 'table-row');
			$(this).siblings('.hidden-row').first().removeClass('hidden-row');
			if($(this).siblings('.hidden-row').length === 0) {
				$modal.find('.toggle-more').hide(); // it would be better to be visible and disabled? ***
			}
		});
		$num.html(selectedNum);
	});


	/* General */

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

    $('.actionbar .toggle-selected').click(function (e) {
        e.preventDefault();
    })

    $('.main .object-details').first().find('h4').addClass('expanded');
    $('.main .object-details').first().find('.object-details-content').slideDown('slow');



	 /* Filters */

	 var filters = {};

	function dropdownSelect(filterEl) {
		var $dropdownList = $(filterEl).find('.choices');

		$dropdownList.find('li a').click(function(e) {
				e.preventDefault();
				var $li = $(this).closest('li');
				var key = $(this).closest(filterEl).data('filter');
				var value = $(this).text();


				if($li.hasClass('reset')) {
					delete filters[key];
					$li.addClass('active')
					$li.siblings('.active').removeClass('active');
					$(this).closest(filterEl).find('.selected-value').text(value);
				}
				else {
					$li.toggleClass('active')
					if($(this).closest('.filter-dropdown').hasClass('filter-boolean')) {
						if($li.hasClass('active')) {
							$li.siblings('li').removeClass('active');
							$(this).closest(filterEl).find('.selected-value').text(value);
								filters[key] = value;
						}
						else {
							delete filters[key];
							var resetLabel = $li.siblings('.reset').text();
							$li.siblings('li').find('.reset').closest('li').addClass('active');
							$(this).closest(filterEl).find('.selected-value').text(resetLabel)

						}
					}
					else {
						if($li.hasClass('active')) {
							$li.siblings('.reset').removeClass('active')

							if($li.siblings('.active').length > 0) {
								arrayFilter(filters, key, value);
								$(this).closest(filterEl).find('.selected-value').append(','+value)
							}
							else {
								$(this).closest(filterEl).find('.selected-value').text(value);
								filters[key] = [value]
							}
						}
						else {
							if($li.siblings('.active').length >0) {
								arrayFilter(filters, key, value, true);
								$(this).closest(filterEl).find('.selected-value').text(filters[key])
							}
							else {
								delete filters[key];
								var resetLabel = $li.siblings('.reset').text();
								$li.siblings('li').find('.reset').closest('li').addClass('active');
								$(this).closest(filterEl).find('.selected-value').text(resetLabel)

							}
						}
					}
				}
				$(tableDomID).dataTable().api().ajax.reload();
		});
	};

	function arrayFilter(filters, key, value, removeItem) {
		var prefix = 'sSearch_';
		if(!removeItem) {
			for(var prop in filters) {
				if(prop === key) {
						filters[prop].push(value);
				}
			}
		}
		else {
			if(filters[key].lenght === 1) {
				delete filters[key];
			}
			else {
				var index = filters[key].indexOf(value);
				filters[key].splice(index, 1);
			}
		}
	};

	function textFilter(extraSearch) {
		var $input = $(extraSearch).find('input');
		$input.keyup(function(e) {
			// if enter or space is pressed do nothing
			if(e.which !== '32' && e.which !== '13') {
				var key, value;
				key = $(this).data('filter');
				value = $.trim($(this).val());

				filters[key] = value;
				if (filters[key] === '') {
					delete filters[key];
				}
					$(tableDomID).dataTable().api().ajax.reload();
			}
		})
	};

	textFilter('.filter-text');
	dropdownSelect('.filters .filter-dropdown .dropdown');

	$('input').blur(); // onload there is no input field focus
});


}(window.jQuery, window.Django));
