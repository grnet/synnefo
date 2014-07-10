var mydata; // temp

$(document).ready(function() {

		var $actionbar = $('.actionbar');

	if($actionbar.length > 0) {
		var $infoBlock = $('.info-block'),
			infoBlockMarg = $infoBlock.css('marginRight'),
			actionbarTop = $actionbar.offset().top,
			actionBarWidth = $actionbar.outerWidth(true),
			$win = $(window),
			isFixed = 0,
			navHeight = $('.main-nav').outerHeight(true),
			filtersHeight = $('.filters').outerHeight();

		function processScroll() {
			var i, scrollTop = $win.scrollTop();
			if(scrollTop >= navHeight+filtersHeight && !isFixed) {
				isFixed = 1;
				$actionbar.addClass('fixed');
				$actionbar.css('top', navHeight);
				if(!$infoBlock.hasClass('.fixed-arround')) {
					$infoBlock.addClass('fixed-arround');
					$infoBlock.css('marginLeft', actionBarWidth);
				}
			}
			else if(scrollTop <= navHeight+filtersHeight && isFixed){
				isFixed = 0;
				$actionbar.removeClass('fixed');
				if($infoBlock.hasClass('fixed-arround')) {
					$infoBlock.removeClass('fixed-arround');
					$infoBlock.css('marginLeft', infoBlockMarg);
				}
			}
		}
		processScroll();
		$win.on('scroll', processScroll);
	}

	var $lastClicked = null;
	var $prevClicked = null;
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
			var modal = $(this).data('target');
			drawModal(modal);
		}
	});


	/* Table */
	/* For the tables we have used DataTables 1.10.0 */
	var url = $('#table-items-total').data("url");
	var serverside = Boolean($('#table-items-total').data("server-side"));
	var table;
	// var tableSelected;
	$.fn.dataTable.ext.legacy.ajax = true;
	var extraData;
	// sets the classes of the btns that are used for navigation throw the pages (next, prev, 1, 2, 3...)
	// $.fn.dataTableExt.oStdClasses.sPageButton = "btn btn-primary";
	var maxCellChar = 30;
	var tableDomID = '#table-items-total';
	var tableSelectedDomID = '#table-items-selected'
	var tableMassiveDomID = '#total-list'
	table = $(tableDomID).DataTable({
		"paging": true,
		// "stateSave": true,
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
			// "targets": '_all' this must be the last item of the array
			{
				"targets": '_all',
				"render": function( data, type, row, meta ) {
					if(data.length > maxCellChar) {
						return trimedCellTemplate(data, maxCellChar);
					}
					else {
						return data;
					}
				}
			},
		],
		"order": [1, "asc"],
		"createdRow": function(row, data, dataIndex) {
			var extraIndex = data.length - 1;
			row.id = data[extraIndex].id.value; //sets the dom id
			clickSummary(row);
			clickDetails(row);
		},

		"dom": '<"custom-buttons">frtilp',
		"language" : {
			"sLengthMenu": 'Pagination _MENU_'
		},
		"drawCallback": function(settings) {
			isSelected();
			updateToggleAllSelect();
			$("[data-toggle=popover]").popover();
		}
	});
	var btn1 = '<a href="" id="select-page" class="select line-btn" data-karma="neutral" data-caution="none"><span>Select Page</span></a>';
	var btn2 = '<a href="" class="select select-all line-btn" data-karma="neutral" data-caution="warning" data-toggle="modal" data-target="#massive-actions-warning"><span>Select All</span></a>';
	var btn3 = '<a href="" id="clear-all" class="disabled deselect line-btn" data-karma="neutral" data-caution="warning" data-toggle="modal" data-target="#clear-all-warning"><span class="snf-font-remove"></span><span>Clear All</span></a>';
	var btn4 = '<a href="" class="disabled toggle-selected extra-btn line-btn" data-karma="neutral"><span class="text">Show selected </span><span class="badge num selected-num">0</span></a>';
	var btn5 = '<a href="" id="reload-table" class="select line-btn" data-karma="neutral" data-caution="none"><span class="snf-font-reload"></span><span>Reload Table</span></a>';

	if($actionbar.length > 0) {
		$("div.custom-buttons").html(btn5+btn1+btn2+btn3+btn4);
	}
	else {
		$("div.custom-buttons").html(btn5);
	}
	$('.container').on('click', '#reload-table', function(e) {
		e.preventDefault();
		$(tableDomID).dataTable().api().ajax.reload();
	})

	function trimedCellTemplate(strData, limit) {
		console.log(strData, limit)
		var html = '<span title="click to see">'+'<span data-container="body" data-toggle="popover" data-placement="bottom" data-content="'+strData+'">'+strData.substring(0, limit)+'...'+'</span>'+'</span>';
		return html;
	};

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
						$(table.row(j).nodes()).find('td:first-child .selection-indicator').addClass('snf-checkbox-checked').removeClass('snf-checkbox-unchecked');
						break;
					}
				}
			}
		}
	}

	var newTable = true;
	$('.select-all-confirm').click(function(e) {
		console.profile("test");
		console.time("test");
		$(this).closest('.modal').addClass('in-progress');
		console.log('select all items', new Date);
		if(newTable) {
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
								rowsArray[i][extraCol] = response.extra[i] // ***
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
					console.time('info')
					var info = data[data.length - 1];
					console.timeEnd('info')
					console.time('newItem')
					var newItem = addItem(info);
					console.timeEnd('newItem')
					if(newItem !== null) {
						console.time('enableActions')
						enableActions(newItem.actions);
						console.timeEnd('enableActions')
						console.time('keepSelected')
						keepSelected(data);
						console.timeEnd('keepSelected')
							if(dataIndex>=500 && dataIndex%500 === 0) {
									setTimeout(function() {
										return true;
									}, 50);
							}
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
					updateToggleAllSelect();
					console.profileEnd("test");
					console.timeEnd("test");
					updateClearAll();
				console.log($(tableMassiveDomID).find('tr').length)
				}
			});
		}
		else {
			console.log($(tableMassiveDomID).find('tr').length)
			console.time('reload')
			$(tableMassiveDomID).dataTable().api().ajax.reload();
			console.timeEnd('reload')

		}
	});

	tableSelected = $(tableSelectedDomID).DataTable({
		// "stateSave": true,
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
		"createdRow": function(row, data, dataIndex) {
			var extraIndex = data.length - 1;
			row.id = 'selected-'+data[extraIndex].id.value; //sets the dom id
			clickDetails(row);
			clickSummary(row);
		},
	});

	function keepSelected(data, drawNow) {
		//return;
		if(drawNow) {
			tableSelected.row.add(data).draw();
		}
		else
			tableSelected.row.add(data).node();
	};


	/* Removes a row from the table of selected items */
	function removeSelected(rowID) {
		if(rowID === true) {
			tableSelected.clear().draw()
		}
		else {
			tableSelected.row('#selected-'+rowID).remove().draw();
		}
	};

	/* Applies style that indicates that a row from the main table is not selected */
	function deselectRow(itemID) {
		table.row('#'+itemID).nodes().to$().removeClass('selected');
		$(table.row('#'+itemID).nodes()).find('td:first-child .selection-indicator').addClass('snf-checkbox-unchecked').removeClass('snf-checkbox-checked');
	}

	function updateDisplaySelected() {
		if(selected.items.length > 0) {
			$('a.toggle-selected').removeClass('disabled');
		}
		else {
			$('a.toggle-selected').addClass('disabled');
		}
	}

	$(tableSelectedDomID).on('click', 'tbody tr td:first-child .selection-indicator', function() {
		var $tr = $(this).closest('tr');
		var column = $tr.find('td').length - 1;
		var $trID = $tr.attr('id');
		var selectedRow = tableSelected.row('#'+$trID);
		var itemID = tableSelected.cell('#'+$trID, column).data().id.value;
		$tr.find('td:first-child .selection-indicator').addClass('snf-checkbox-unchecked').removeClass('snf-checkbox-checked');
		$tr.fadeOut('slow', function() {
			selectedRow.remove().draw();
			table.row('#'+itemID).nodes().to$().removeClass('selected');
			$(table.row('#'+itemID).nodes()).find('td:first-child .selection-indicator').addClass('snf-checkbox-unchecked').removeClass('snf-checkbox-checked');
			deselectRow(itemID)

		});
		removeItem(itemID);
		enableActions(undefined, true);
		updateCounter('.selected-num');
		updateToggleAllSelect();
	});


	$(tableDomID).on('click', 'tbody tr .selection-indicator', function(e) {
		$prevClicked = $lastClicked;
		$lastClicked =  $(this).closest('tr');
		if(!e.shiftKey) {
			selectRow($lastClicked, e.type);
		}
		else {
			var select;
			if($lastClicked.hasClass('selected')) {
				select = false;
			}
			else {
				select = true;
			}
			if(e.shiftKey && $prevClicked !== null && $lastClicked !== null) {
				var startRow;
				var start = $prevClicked.index();
				var end = $lastClicked.index();
				if(start < end) {
					startRow = $prevClicked;
					for (var i = start; i<=end; i++) {
						if((select && !($(startRow).hasClass('selected'))) || (!select && $(startRow).hasClass('selected'))) {
							selectRow(startRow);
						}
						startRow = startRow.next();
					}
				}
				else if(end < start) {
					startRow = $prevClicked;
					for (var i = start; i>=end; i--) {
						if((select && !($(startRow).hasClass('selected'))) || (!select && $(startRow).hasClass('selected'))) {
							selectRow(startRow);
						}
						startRow = startRow.prev();
					}
				}
			}
		}
		updateClearAll();
	});

	$(document).bind('keydown', function(e){
		if(e.shiftKey) {
			$(tableDomID).addClass('with-shift')
		}
	});

	$(document).bind('keyup', function(e){
		if(e.which === 16) {
			deselectText();
			$(tableDomID).removeClass('with-shift')
		}
	});

	function deselectText() {
	if (window.getSelection) {
		if (window.getSelection().empty) {  // Chrome
			window.getSelection().empty();
		} else if (window.getSelection().removeAllRanges) {  // Firefox
			window.getSelection().removeAllRanges();
		}
		} else if (document.selection) {  // IE?
			document.selection.empty();
		}
	}

	function selectRow(row) {
		var $row = $(row);
		$row.find('td:first-child .selection-indicator').toggleClass('snf-checkbox-checked snf-checkbox-unchecked');
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
		if(data.length > maxCellChar) {
			data = trimedCellTemplate(data, maxCellChar);
		}
		if($actionbar.length > 0)
			return '<span class="snf-font-admin snf-checkbox-'+initState+' selection-indicator"></span>'+data;
		else
			return data;

	}

	function extraTemplate(data) {


			var listTemplate = '<dt>{key}:</dt><dd>{value}</dd>';
			var list = '';
			var listItem = listTemplate.replace('{key}', prop).replace('{value}',data[prop]);
			var html;
			var hasDetails = false;
			for(var prop in data) {
				if(prop !== "details_url") {
					if(data[prop].visible) {
						list += listTemplate.replace('{key}', data[prop].display_name).replace('{value}',data[prop].value);
					}
				}
				else {
					hasDetails = true;
				}
			}
			if(hasDetails)
			html = '<a title="Details" href="'+ data["details_url"].value +' " class="details-link"><span class="snf-font-admin snf-search"></span></a><a title="Show summary" href="#" class="summary-expand expand-area"><span class="snf-font-admin snf-angle-down"></span></a><dl class="info-summary dl-horizontal">'+ list +'</dl>';
		else 
			html = '<a title="Show summary" href="#" class="summary-expand expand-area"><span class="snf-font-admin snf-angle-down"></span></a><dl class="info-summary dl-horizontal">'+ list +'</dl>';
			return html;
	};

	function clickDetails(row) {
		$(row).find('td:last-child a.details-link').click(function(e) {
			e.stopPropagation();
		})
	}

	function clickSummary(row) {
		$(row).find('td:last-child a.expand-area').click(function(e) {
			e.preventDefault();
			e.stopPropagation();
			var $summaryTd = $(this).closest('td');
			var $btn = $summaryTd.find('.expand-area span');
			var $summaryContent = $summaryTd.find('.info-summary');
			
			var summaryContentWidth = $summaryTd.closest('tr').width();
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
		   "contact_email": infoObj.contact_email.value,
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

	function resetAll(tableDomID) {
		selected.items = [];
		removeSelected(true); //removes all selected items from the table of selected items
		updateCounter('.selected-num');
		enableActions(undefined, true);
		$(table.rows('.selected').nodes()).find('td:first-child .selection-indicator').toggleClass('snf-checkbox-checked snf-checkbox-unchecked');
		$(tableDomID).dataTable().api().rows('.selected').nodes().to$().removeClass('selected');

		updateToggleAllSelect();
		updateClearAll();
	};


	 /* select-page button */

	$('#select-page').click(function(e) {
		e.preventDefault();
		toggleVisSelected(tableDomID, $(this).hasClass('select'));
		updateClearAll();
	});


	/* select-page / deselect-page */
	function toggleVisSelected(tableDomID, selectFlag) {
		$lastClicked = null;
		$prevClicked = null;
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
		var $togglePageItems = $('#select-page');
		var $label = $togglePageItems.find('span')
		var $tr = $(tableDomID).find('tbody tr');
		if($tr.length >= 1) {
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
			$label.text('Select Page')
		}
	};

	function updateClearAll() {
		var $clearAllBtn = $('#clear-all')
		if(selected.items.length === 0) {
			$clearAllBtn.addClass('disabled');
		}
		else {
			$clearAllBtn.removeClass('disabled');
		}
	}


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
	var defaultEmailSubj = $('.modal[data-type="contact"]').find('.subject').val();
	var defaultEmailBody = $('.modal[data-type="contact"]').find('.email-content').val();
	function resetInputs(modal) {
		var $modal = $(modal);
		$modal.find('input[type=text]').val(defaultEmailSubj);
		$modal.find('textarea').val(defaultEmailBody);
	};
	function removeWarnings(modal) {
		var $modal = $(modal);
		$modal.find('.warning-duplicate').remove();
	}

	function resetToggleAllBtn(modal) {
		var $modal = $(modal);
		$modal.find('.toggle-more').removeClass('open').addClass('closed');
		$modal.find('.toggle-more').find('span').text('Show all');
	}
	$('.modal .cancel').click(function(e) {
		$('[data-toggle="popover"]').popover('hide');
		var $modal = $(this).closest('.modal');
		resetErrors($modal);
		resetInputs($modal);
		removeWarnings($modal);
		resetToggleAllBtn($modal);
		// resetAll(tableDomID);
		updateToggleAllSelect();
		updateClearAll();
		enableActions(undefined, true);
	});

	$('.modal .clear-all-confirm').click(function() {
		resetAll(tableDomID);
	});

	$('.modal .apply-action').click(function(e) {
		var $modal = $(this).closest('.modal');
		var completeAction = true;
		if(selected.items.length === 0) {
			e.stopPropagation();
			showError($modal, 'no-selected');
			completeAction = false;
		}
		if($modal.attr('id') === 'user-contact') {
			var $emailSubj = $modal.find('.subject');
			var $emailCont = $modal.find('.email-content');
			if(!$.trim($emailSubj.val())) {
				e.stopPropagation();
				showError($modal, 'empty-subject');
				checkInput($modal, $emailSubj, 'empty-subject');
				completeAction = false;
			}
			if(!$.trim($emailCont.val())) {
				// e.preventDefault();
				e.stopPropagation();
				showError($modal, 'empty-body')
				checkInput($modal, $emailCont, 'empty-body');
				completeAction = false;
			}
		}
		if(completeAction) {
			$('[data-toggle="popover"]').popover('hide');
			performAction($modal);
			resetErrors($modal);
			resetInputs($modal);
			removeWarnings($modal);
			resetAll(tableDomID);
			resetToggleAllBtn($modal);
		}
	});

	/* remove an item after the modal is visible */
	$('.modal').on('click', '.remove', function(e) {
		e.preventDefault();
		var $modal = $(this).closest('.modal')
		var $actionBtn = $modal.find('.modal-footer .apply-action');
		var $num = $modal.find('.num');
		var $tr = $(this).closest('tr');
		var itemID = $tr.attr('data-itemid');
		// uuidsArray has only the uuids of selected items, none of the other info
		idsArray = [];
		deselectRow(itemID)
		removeSelected(itemID)
		removeItem(itemID, false);
		var selectedNum = selected.items.length;
		for (var i=0; i< selectedNum; i++)
			idsArray.push(selected.items[i].id);
		$actionBtn.attr('data-ids','[' + idsArray + ']');
		$tr.slideUp('slow', function() {
			$(this).siblings('.hidden-row').first().css('display', 'table-row');
			$(this).siblings('.hidden-row').first().removeClass('hidden-row');
			if($(this).siblings('.hidden-row').length === 0) {
				$modal.find('.toggle-more').hide(); // it would be better to be visible and disabled? ***
			}
		});
		$num.html(selectedNum); // should this use updateCounter?
		updateCounter('.selected-num');
	});

	var $notificationArea = $('.notify');
	var countAction = 0;
	function performAction(modal) {
		var $modal = $(modal);
		var $actionBtn = $modal.find('.apply-action')
		var url = $actionBtn.attr('data-url');
		var countItems = selected.items.length;
		var actionName = $actionBtn.find('span').text();
		var logID = 'action-'+countAction;
		countAction++;
		var removeBtn = '<a href="" class="remove-icon remove-log" title="Remove this line">X</a>';
		var warningMsg = '<p class="warning">The data of the table maybe out of date. Click "Reload Table" to update them.</p>'
		var data = {
		op: $actionBtn.attr('data-op'),
		target: $actionBtn.attr('data-target'),
		ids: $actionBtn.attr('data-ids')
		}
		var contactAction = (data.op === 'contact' ? true : false);

		if(contactAction) {
			data['subject'] = $modal.find('input[name="subject"]').val();
			data['text'] = $modal.find('textarea[name="text"]').val();
		}
		$.ajax({
			url: url,
			type: 'POST',
			data: JSON.stringify(data),
			contentType: 'application/json',
			timeout: 100000,
			beforeSend: function(jqXHR, settings) {
				var htmlPending = '<p class="log" id='+logID+'><span class="pending state-icon snf-font-admin snf-exclamation-sign"></span>Action <em>"'+actionName+'"</em> for '+countItems+' items is <em class="pending">pending</em>.'+removeBtn+'</p>';
				if($notificationArea.find('.warning').length === 0) {
					$notificationArea.find('.container').append(htmlPending);
					$notificationArea.find('.container').append(warningMsg);
				}
				else {
					$notificationArea.find('.warning').before(htmlPending);
				}
				snf.funcs.showBottomModal($notificationArea);
				$notificationArea.find('.warning').fadeIn('slow');
			},
			// complete: function()
			success: function(response, statusText, jqXHR) {
				var htmlSuccess = '<p class="log"><span class="success state-icon snf-font-admin snf-ok"></span>Action <em>"'+actionName+'"</em> for '+countItems+' items has <em class="succeed">succeed</em>.'+removeBtn+'</p>';
				$notificationArea.find('#'+logID).replaceWith(htmlSuccess);
				snf.funcs.showBottomModal($notificationArea);
			},
			error: function(jqXHR, statusText) {
				console.log(jqXHR, statusText, jqXHR.status);
				var htmlErrorSum = '<p><span class="error state-icon snf-font-admin snf-remove"></span>Action <em>"'+actionName+'"</em> for '+countItems+' items has <em class="error">failed</em>.'+removeBtn+'</p>'
				var htmlErrorReason, htmlErrorIDs, htmlError;
				if(jqXHR.status === 500 || jqXHR.status === 0) {
					htmlErrorReason = '<dl class="dl-horizontal"><dt>Reason:</dt><dd>'+jqXHR.statusText+' (code: '+jqXHR.status+').</dd></dl>';
					htmlErrorIDs = '';
				}
				else {
					htmlErrorReason = '<dl class="dl-horizontal">'+'<dt>Reason:</dt><dd>'+jqXHR.responseJSON.result+'</dd>';
					htmlErrorIDs ='<dt>IDs:</dt><dd>'+jqXHR.responseJSON.error_ids.toString().replace(/\,/gi, ', ')+'</dd>'+'</dl>'
				}

				htmlError = '<div class="log">'+htmlErrorSum+htmlErrorReason+htmlErrorIDs+'</div>'
				$notificationArea.find('#'+logID).replaceWith(htmlError);
				if($notificationArea.find('.warning').length === 0) {
					$notificationArea.find('.container').append(warningMsg);
				}

				snf.funcs.showBottomModal($notificationArea);
			}
		});
	};

	$notificationArea.on('click', '.remove-log', function(e) {
		e.preventDefault();
		console.log($(this));
		var $log = $(this).closest('.log');
		$log.fadeOut('slow', function() {
			$log.remove();
			if($notificationArea.find('.log').length === 0) {
				$notificationArea.find('.close-notifications').trigger('click');

			}
		});
	});
	$notificationArea.on('click', '.close-notifications', function(e) {
		e.preventDefault();
		snf.funcs.hideBottomModal($notificationArea);
	});

	function drawModal(modalID) {
		var $tableBody = $(modalID).find('.table-selected tbody');
		var modalType = $(modalID).data('type');
		var $counter = $(modalID).find('.num');
		var rowsNum = selected.items.length;
		var $actionBtn = $(modalID).find('.apply-action');
		console.log('drawModal', $actionBtn);
		var maxVisible = 5;
		var currentRow;
		var htmlRows = '';
		var unique = true;
		var uniqueProp = '';
		var count = 0;
		// var $idsInput = $(modalID).find('.modal-footer form input[name="ids"]');
		var idsArray = [];
		var warningMsg = '<p class="warning-duplicate">Duplicate accounts have been detected</p>';
		var warningInserted = false;
		$tableBody.empty();
		if(modalType === "contact") {
			uniqueProp = 'contact_id'
			var templateRow = '<tr title="" data-itemid=""><td class="full-name"></td><td class="email"><a class="remove" title="Remove item from selection">X</a></td></tr>';
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
					currentRow = currentRow.replace('title=""', 'title="related with: '+selected.items[i].item_name+'"')
					currentRow = currentRow.replace('<td class="full-name"></td>', '<td class="full-name">'+selected.items[i].contact_name+'</td>');
					currentRow = currentRow.replace('<td class="email"><', '<td class="email">'+selected.items[i].contact_email+'<');
					if(i >= maxVisible)
						currentRow = currentRow.replace('<tr', '<tr class="hidden-row"');
					htmlRows += currentRow;
				}
				else {
					htmlRows = htmlRows.replace('" data-itemid="' + selected.items[i].contact_id + '"', ', '+selected.items[i].item_name+'" data-itemid="' + selected.items[i].contact_id+'"');
					if(!warningInserted) {
						$tableBody.closest('table').before(warningMsg);
						warningInserted = true;
					}
				}
			}
		}


		else {
			uniqueProp = 'id';
			var templateRow = '<tr data-itemid=""><td class="item-name"></td><td class="item-id"></td><td class="owner-name"></td><td class="owner-email"><a class="remove" title="Remove item from selection">X</a></td></tr>';
			for(var i=0; i<rowsNum; i++) {
				idsArray.push(selected.items[i][uniqueProp]);
				currentRow =templateRow.replace('data-itemid=""', 'data-itemid="'+selected.items[i].id+'"')
				currentRow = currentRow.replace('<td class="item-name"></td>', '<td class="item-name">'+selected.items[i].item_name+'</td>');
				currentRow = currentRow.replace('<td class="item-id"></td>', '<td class="item-id">'+selected.items[i].id+'</td>');
				currentRow = currentRow.replace('<td class="owner-name"></td>', '<td class="owner-name">'+selected.items[i].contact_name+'</td>');
				currentRow = currentRow.replace('<td class="owner-email"><', '<td class="owner-email">'+selected.items[i].contact_email+'<');
				if(i >= maxVisible)
					currentRow = currentRow.replace('<tr', '<tr class="hidden-row"');
				htmlRows += currentRow;
			}
		}
		$tableBody.append(htmlRows); // should change
		$actionBtn.attr('data-ids','['+idsArray+']');
		updateCounter($counter, idsArray.length); // ***
		
		if(idsArray.length >= maxVisible) {
			var $btn = $(modalID).find('.toggle-more');
			// rowsNum = idsArray.length;

			$btn.css('display', 'block');

					}
	};

	$('.modal .toggle-more').click( function() {
		var $tableBody = $(this).closest('.modal').find('table');
		if($(this).hasClass('closed')) {
			$(this).find('span').text('Show less');
			$tableBody.find('.hidden-row').slideDown('slow');
		}
		else {
			var that = this;
			$tableBody.find('tr.hidden-row').slideUp('slow', function() {
				$(that).find('span').text('Show all');
			});
		}
		$(this).toggleClass('closed open');
		});




	$('.toggle-selected').click(function (e) {
		e.preventDefault();
		var $label = $(this).find('.text');
		var label1 = 'Show selected'
		var label2 = 'Hide selected'
		$(this).toggleClass('open');
		if($(this).hasClass('open')) {
			$('#table-items-selected_wrapper').slideDown('slow', function() {
				$label.text(label2);
			});
		}
		else {
			$('#table-items-selected_wrapper').slideUp('slow', function() {
				$label.text(label1);
			});
		}
	});

	 /* Filters */

	 var filters = {};

	function dropdownSelect(filterEl) {
		var $dropdownList = $(filterEl).find('.choices');

		$dropdownList.find('li a').click(function(e) {
			e.preventDefault();
			var $li = $(this).closest('li');
			var key = $(this).closest(filterEl).data('filter');
			var value = $(this).text();
			if($(this).closest('.filter-dropdown').hasClass('filter-boolean')) {
				if($li.hasClass('reset')) {
					delete filters[key];
					$li.find('.selection-indicator').toggleClass('snf-radio-unchecked snf-radio-checked');
					$li.addClass('active');
					$li.siblings('.active').find('.selection-indicator').toggleClass('snf-radio-unchecked snf-radio-checked');
					$li.siblings('.active').removeClass('active');
					$(this).closest(filterEl).find('.selected-value').text(value);
				}
				$li.toggleClass('active')
				if($li.hasClass('active')) {
					$li.find('.selection-indicator').removeClass('snf-radio-unchecked').addClass('snf-radio-checked');
					$li.siblings('li').removeClass('active');
					$li.siblings('li').find('.selection-indicator').removeClass('snf-radio-checked').addClass('snf-radio-unchecked');
					$(this).closest(filterEl).find('.selected-value').text(value);
					filters[key] = value;
				}
				else {
					delete filters[key];
					var resetLabel = $li.siblings('.reset').text();
					$li.siblings('li.reset').addClass('active');
					$li.siblings('li.reset').find('.selection-indicator').removeClass('snf-radio-unchecked').addClass('snf-radio-checked');
					$(this).closest(filterEl).find('.selected-value').text(resetLabel);
				}
			}
			else {
				if($li.hasClass('reset')) {
					delete filters[key];
					$li.find('.selection-indicator').toggleClass('snf-checkbox-unchecked snf-checkbox-checked');
					$li.addClass('active');

					$li.siblings('.active').find('.selection-indicator').toggleClass('snf-checkbox-unchecked snf-checkbox-checked');
					$li.siblings('.active').removeClass('active');
					$(this).closest(filterEl).find('.selected-value').text(value);
				}
				else {
					$li.toggleClass('active');
					$li.find('.selection-indicator').toggleClass('snf-checkbox-unchecked snf-checkbox-checked');
					if($li.hasClass('active')) {
						$li.siblings('.reset').removeClass('active')
						$li.siblings('.reset').find('.selection-indicator').addClass('snf-checkbox-unchecked').removeClass('snf-radio-checked');
						if($li.siblings('.active').length > 0) {
							arrayFilter(filters, key, value);
							$(this).closest(filterEl).find('.selected-value').append(', '+value)
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
							$li.siblings('li.reset').addClass('active');
							$li.siblings('li.reset').find('.selection-indicator').removeClass('snf-radio-unchecked').addClass('snf-checkbox-checked');
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
});

