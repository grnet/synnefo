$(document).ready(function() {

	var tableDomID = '#table-items-total';

	var filtersInfo = {}; // stores the type of each filter
	var tempFilters = {}; // use for filtering from compact view
	var filtersResetValue = {}; // the values are stored in upper case
	var filtersValidValues = {}; // the values are stored in upper case
	var enabledFilters = []; // visible filters on standard view
	var cookie_name = 'filters_'+ $('.table-items').attr('data-content');

	/* Extract type and valid keys and values for filtersInfo, filtersResetValue, filtersValidValues */
	$('.filters').find('.filter').each(function(index) {
		if(!$(this).hasClass('compact-filter') && !$(this).hasClass('filters-list')) {
			var key = $(this).attr('data-filter');
			var type; // possible values: 'singe-choice', 'multi-choice', 'text'
			var resetValue;
			if($(this).hasClass('filter-dropdown')) {
				type = ($(this).hasClass('filter-boolean')? 'single-choice' : 'multi-choice');
				resetValue = $(this).find('li.reset').text().toUpperCase();
				filtersResetValue[key] = resetValue;
				filtersValidValues[key] = [];
				$(this).find('li:not(.divider)').each(function() {
					filtersValidValues[key].push($(this).text().toUpperCase());
				});
			}
			else {
				type = 'text';
			}
			filtersInfo[key] = type;
		}
	});


	/* Standard View Functionality */

	function dropdownSelect(filterElem) {
		var $dropdownList = $(filterElem).find('.choices');
		$dropdownList.find('li a').click(function(e) {
			e.preventDefault();
			e.stopPropagation();
			var $currentFilter = $(this).closest('.filter');
			var $li = $(this).closest('li');

			if($(this).closest('.filter-dropdown').hasClass('filter-boolean')) {
				if(!$li.hasClass('active')) {
					$li.addClass('active');
					$li.siblings('.active').removeClass('active');
				}
			}
			// multichoice filter
			else {
				if($li.hasClass('reset')) {
					$li.addClass('active');
					$li.siblings('.active').removeClass('active');
				}
				else {
					$li.toggleClass('active');
					if($li.hasClass('active')) {
						$li.siblings('.reset').removeClass('active');
					}
					// deselect a choice
					else {
						//if there is no other selected value the reset value is checked
						if($li.siblings('.active').length === 0) {
							$li.siblings('li.reset').addClass('active');
						}
					}
				}
			}
			execChoiceFiltering($currentFilter);
		});
	};

	function execChoiceFiltering($filter) {
		var $filterSelections = $filter.find('ul li.active');
		var key = $filter.attr('data-filter');
		var value = [];
		snf.filters[key] = [];
		if($filterSelections.length === 1) {
			if($filterSelections.hasClass('reset')) {
				delete snf.filters[key]
			}
			else if($filter.hasClass('filter-boolean')) {
				snf.filters[key] = $filterSelections.text();
			}
			else {
				value.push($filterSelections.text());
				snf.filters[key] = snf.filters[key].concat(value);
			}
		}
		else {
			$filterSelections.each(function() {
				value.push($(this).text());
			});
			snf.filters[key] = snf.filters[key].concat(value);
		}
		$(tableDomID).dataTable().api().ajax.reload();
	};


	function textFilter(extraSearch) {
		snf.timer = 0;
		var $input = $(extraSearch).find('input');

		$input.keyup(function(e) {
			// if enter or space is pressed do nothing
			if(e.which !== 32 && e.which !== 13) {
				var key, value, pastValue, valuHasChanged;
				key = $(this).data('filter');
				value = $.trim($(this).val());
				if(snf.filters[key]) {
					pastValue = snf.filters[key];
				}
				else {
					pastValue = undefined;
				}
				snf.filters[key] = value;
				if (snf.filters[key] === '') {
					delete snf.filters[key];
				}
				valueHasChanged = snf.filters[key] !== pastValue;
				if(valueHasChanged) {
					if(snf.timer === 0) {
						snf.timer = 1;
						setTimeout(function() {
							$(tableDomID).dataTable().api().ajax.reload();
							snf.timer = 0;
						}, snf.ajaxdelay)
					}
				}
			}
		})
	};

	textFilter('.filter-text');
	dropdownSelect('.filters .filter-dropdown'); // every dropdown filter (.filters-list not included)

	/* Choose which filters will be visible */

	/* Each click should display the filter, add it to enabledFilters array and add to the corresponding cookie */

	$('.filters-list').on('click', '.choices li a', function(e) {
		var $li = $(this).closest('li');
		if($li.hasClass('reset') && $li.find('span').hasClass('snf-checkbox-unchecked')) {
			$li.addClass('active');
			$li.siblings('li:not(.reset):not(.divider)').removeClass('active');
			showAllFilters();
		}
		else if(!$li.hasClass('reset')) {
			$li.toggleClass('active');
			if($li.hasClass('active')) {
				if($li.siblings('.reset').hasClass('active')) {
				$li.siblings('.reset').removeClass('active');
					hideAllFilters();
				}
				showFilter($li.attr('data-filter-name'));
			}
			else {
				hideFilter($li.attr('data-filter-name'));
			}
		}
	});

	/* show the selected values of a choice-filter */
	$('.filters .filter .dropdown').on('hide.bs.dropdown', function() {
		showSelections($(this).closest('.filter'));
	});

	/* Every time the list of available filters appears the proper li elements are checked */
	$('.filters .filters-list #select-filters').on('shown.bs.popover', function() {
		showSelectedFilters();
	});

	function showSelections($filter) {
		var selectedFilterstext = '';
		var selectedFiltersLabels = [];
		$filter.find('.choices .active').each(function() {
			selectedFiltersLabels.push($(this).text());
		});
		selectedFilterstext = selectedFiltersLabels.toString().replace(/,/g, ', ');
		$filter.find('.selected-value').text(selectedFilterstext);
	};

	/* Display filters onload */
	(function showFiltersOnLoad() {
		var enabledFiltersNum;
		if($.cookie(cookie_name)) {
			enabledFilters = $.cookie(cookie_name).split(',');
			enabledFiltersNum = enabledFilters.length;
			if(enabledFilters[0] === 'all-filters') {
				$('.filters .filter:not(.compact-filter)').addClass('visible-filter selected');
			}
			else {
				for(var i=0; i<enabledFiltersNum; i++) {
					$('.filters').find('.filter[data-filter='+enabledFilters[i]+']').addClass('visible-filter selected');
				}
			}

		}
		else {
			/* by default the first 2 filters get enabled */
			$('.filters .filter:not(.filters-list)').each(function() {
				var show = false;
				var filter;
				if($(this).index('.filter:not(.filters-list)') === 0 || $(this).index('.filter:not(.filters-list)') === 1) {
					show = true;
					filter = $(this).attr('data-filter');
				}
				if(show) {
					showFilter(filter);
				}
			});
		}
	})();

	function showSelectedFilters() {
		var filtersNum = enabledFilters.length;
		$('.filters-list .choices li').removeClass('active');
		for(var i=0; i<filtersNum; i++) {
			$('.filters-list').find('[data-filter-name='+enabledFilters[i]+']').addClass('active');
		}
	};

	function resetFilterTextView($filter) {
		$filter.find('input').val('');
	};

	function resetFilterChoiceView($filter) {
		var resetLabel = $filter.find('.reset').text();
		$filter.find('.active').removeClass('active');
		$filter.find('.reset').addClass('active');
		$filter.find('.selected-value').text(resetLabel);
	};

	function showAllFilters() {
		$('.filters .filter:not(.compact-filter)').addClass('visible-filter selected');
		enabledFilters = [];
		enabledFilters.push('all-filters');
		$.cookie(cookie_name, enabledFilters.toString());
	};

	function hideAllFilters() {
		$('.filters .filter:not(.filters-list)').attr('style', '');
		$('.filters .filter:not(.filters-list)').removeClass('visible-filter visible-filter-fade selected');
		enabledFilters = [];
		$.cookie(cookie_name, '');
	};

	function showFilter(attrFilter) {
		$('.filters').find('.filter[data-filter='+attrFilter+']').addClass('visible-filter selected');
		enabledFilters.push(attrFilter)
		$.cookie(cookie_name, enabledFilters.toString());
	};

	function hideFilter(attrFilter) {
		var index = enabledFilters.indexOf(attrFilter);
		var $currentFilter = $('.filters').find('.filter[data-filter='+attrFilter+']');
		$currentFilter.removeClass('visible-filter visible-filter-fade selected');
		if(filtersInfo[attrFilter] === 'text') {
			resetFilterTextView($currentFilter);
		}
		else {
			if(!$currentFilter.find('.reset').hasClass('active')) {
				resetFilterChoiceView($currentFilter);
			}

		}
		enabledFilters.splice(index, 1);
		$.cookie(cookie_name, enabledFilters.toString());

		delete snf.filters[attrFilter];
		$(tableDomID).dataTable().api().ajax.reload();
	};

	/* Change Filters' View */

	$('.search-mode input').click(function(e) {
		e.stopPropagation();
		var $compact = $('.compact-filter');
		var $standard = $('.filter.selected, .filters-list');
		if($compact.is(':visible')) {
			$compact.removeClass('visible-filter visible-filter-fade');
			$standard.addClass('visible-filter-fade');
			$standard.each(function() {
				if(!$(this).hasClass('filters-list')) {
					var filter = $(this).attr('data-filter');
					var $filterOption = $('.filters .filters-list li[data-filter-name='+filter+']');

					if(!$filterOption.hasClass('active')) {
						$filterOption.trigger('click');
						showSelections($filterOption.closest('.filter'));
					}
				}
			});
			$standard.each(function() {
				if($(this).hasClass('filter-text') && $(this).hasClass('visible-filter-fade')) {
					$(this).find('input').focus();
					return false;				}
			})
			$.cookie('search_mode', 'standard');
		}
		else {
			$standard.removeClass('visible-filter visible-filter-fade');
			$compact.addClass('visible-filter-fade');
			standardToCompact();
			$.cookie('search_mode', 'compact');
			$('.compact-filter.visible-filter-fade').find('input').focus();
		}

	});

	if(!$.cookie('search_mode')) {
		$.cookie('search_mode', 'standard');
	}
	else {
		if($.cookie('search_mode') !== 'standard') {
			$('.search-mode input').trigger('click');
		}
	}


	/* Tranfer the search terms of standard view to compact view */

	function standardToCompact() {
		var $advFilt = $('.filters').find('input[data-filter=compact]');
		var updated = true;
		hideFilterError();
		$advFilt.val(filtersToString());
	};

	function filtersToString() {
		var text = '';
		var newTerm;
		for(var prop in snf.filters) {
			if(filtersInfo[prop] === 'text') {
				newTerm = prop + ': ' + snf.filters[prop];
				if(text.length == 0) {
					text = newTerm;
				}
				else {
					text = text + ' ' + newTerm;
				}
			}
			else {
				newTerm = prop + ': ' + snf.filters[prop].toString();
				if(text.length === 0) {
					text = newTerm;
				}
				else {
					text = text + ' ' + newTerm;
				}
			}
		}

		return text;
	};

	/* Compact View Functionality */

	$('.filters .compact-filter input').keyup(function(e) {
		if(e.which === 13) {
			$('.exec-search').trigger('click');
		}
	});

	$('.filters .toggle-instructions').click(function (e) {
		e.preventDefault();
		var that = this;
		$(this).toggleClass('open');
		$(this).siblings('.content').stop().slideToggle(function() {
			if($(that).hasClass('open') && $(this).css('display') === 'none') {
				$(that).removeClass('open');
			}
		});
	});

	$('.exec-search').click(function(e) {
		e.preventDefault();
		tempFilters = {};
		var text = $(this).siblings('.form-group').find('input').val().trim();
		hideFilterError();
		if(text.length > 0) {
			var terms = text.split(' ');
			var key = 'unknown', value;
			var termsL = terms.length;
			var keyIndex;
			var lastkey;
			var filterType;
			var isKey = false;
			for(var i=0; i<termsL; i++) {
				terms[i] = terms[i].trim();
				for(var prop in filtersInfo) {
					if(terms[i].substring(0, prop.length+1).toUpperCase() === prop.toUpperCase() + ':') {
						key = prop;
						value = terms[i].substring(prop.length + 1).trim();
						isKey = true;
						break;
					}
				}
				if(!isKey) {
					value = terms[i];
				}

				if(!tempFilters[key]) {
					tempFilters[key] = value;
				}
				else if(value.length > 0) {
					tempFilters[key] = tempFilters[key] + ' ' + value;
				}
				isKey = false;
			}
		}

		if(!_.isEmpty(tempFilters)) {
			for(var filter in tempFilters) {
				for(var prop in filtersInfo) {
					if(prop === filter && (filtersInfo[prop] === 'single-choice' || filtersInfo[prop] === 'multi-choice')) {
						tempFilters[filter] = tempFilters[filter].replace(/\s*,\s*/g ,',').split(',');
						break;
					}
				}
			}
			for(var prop in snf.filters) {
				if(!_.has(tempFilters, prop) && !tempFilters['unknown']) {
					delete snf.filters[prop];
					$(tableDomID).dataTable().api().ajax.reload();
				}
			}
		}
		compactToStandard();
	});

	function compactToStandard() {
		var $choicesLi;
		var valuesL;
		var validValues = [];
		var valid = true;
		var temp;
		if(_.isEmpty(tempFilters) && !_.isEmpty(snf.filters)) {
			snf.filters = {};
			$(tableDomID).dataTable().api().ajax.reload();
		}
		else {
			if(tempFilters['unknown']) {
				showFilterError(tempFilters['unknown']);
				valid = false;
			}
			for(var prop in tempFilters) {
				if(prop !== 'unknown') {
					temp = checkValues(prop);
					if(valid) {
						valid = temp;
					}
				}
			}
		}

		// execution
		if(valid) {
			resetStandardFiltersView();
			triggerFiltering();
			showSelectedFilters();
		}
	};

	function triggerFiltering() {
		var $choicesLi, valuesL;
		var $filters = $('.filters')
		for(var prop in tempFilters) {
			if(prop !== 'unknown') {
				$filters.find('.filter[data-filter="' + prop + '"]').addClass('selected');
				if(enabledFilters.indexOf('all-filters') === -1 && enabledFilters.indexOf(prop) === -1) {
					enabledFilters.push(prop);
					$.cookie(cookie_name, enabledFilters.toString());
				}
				if(filtersInfo[prop] === 'text'){
					$filters.find('input[data-filter="' + prop + '"]').val(tempFilters[prop]);
					$filters.find('input[data-filter="' + prop + '"]').trigger('keyup');
				}
				else {
					$choicesLi = $filters.find('.filter[data-filter="' + prop + '"] .choices').find('li');
					valuesL = tempFilters[prop].length;
					for(var i=0; i<valuesL; i++) { // for each filter
						$choicesLi.each(function() {
							if(tempFilters[prop][i].toUpperCase() === $(this).text().toUpperCase()) {
								if(!$(this).hasClass('active') || ($(this).hasClass('active')&& $(this).hasClass('reset')))	{
									$(this).find('a').trigger('click');
								}
							}
						});
						showSelections($filters.find('.filter[data-filter="' + prop + '"]'));
					}
				}
			}
		}
	};

	function checkValues(key) {
		var wrongTerm;
		var isWrong = false;
		if(filtersInfo[key] === 'text') {
			if(tempFilters[key] === '') {
				isWrong = true;
			}
		}
		else if(!isWrong) {
			var valuesUpperCased = $.map(tempFilters[key], function(item, index) {
				return item.toUpperCase();
			});
			var valuesL = valuesUpperCased.length;
			for(var i=0; i<valuesL; i++) {
				if(filtersValidValues[key].indexOf(valuesUpperCased[i]) === -1) {
					isWrong = true;
					break;
				}
			}
			if(!isWrong) {
				if(valuesUpperCased.indexOf(filtersResetValue[key])!==-1 && tempFilters[key].length>1) {
					isWrong = true;
				}
				else if(filtersInfo[key] === 'single-choice' && tempFilters[key].length > 1) {
					isWrong = true;
				}
			}
		}
		if(isWrong) {
			wrongTerm = key + ': ' + tempFilters[key].toString();
			showFilterError(wrongTerm);
			delete tempFilters[key];
		}
		return !isWrong;
	};

	function showFilterError(wrongTerm) {
		var msg, addition, prevMsg;
		$errorDescr = $('.compact-filter').find('.error-description');
		$errorSign = $('.compact-filter').find('.error-sign');
		if($errorDescr.text() === '') {
			msg = 'Invalid search: "' + wrongTerm + '" is not valid.';
		}
		else {
			prevMsg = $errorDescr.text();
			addition =  ', "' + wrongTerm + '" are not valid.';
			msg = prevMsg.replace('term:', 'terms:');
			msg = msg.replace(' are not valid.', addition);
			msg = msg.replace(' is not valid.', addition);
		}
		$errorDescr.text(msg);
		$errorSign.css('opacity', 1)
	};

	function hideFilterError() {
		$('.compact-filter').find('.error-sign').css('opacity', 0);
		$('.compact-filter').find('.error-description').text('');
	};

	function resetStandardFiltersView() {
		$('.filters .filter-dropdown').each(function() {
			$(this).find('li.reset').each(function() {
				if(!$(this).hasClass('active')) {
					$(this).addClass('active');
				}
			});
				$(this).find('li:not(.reset)').each(function() {
					if($(this).hasClass('active')) {
						$(this).removeClass('active');
					}
				});
			showSelections($(this).closest('.filter'));
		});

		$('.filters .filter-text').find('input').each(function() {
			if($(this).val().length !== 0) {
				$(this).val('');
			}
		});
	};
	$('.filter-text.visible-filter').first().find('input').focus();
	$('.compact-filter.visible-filter-fade').find('input').focus();

	var filtersListHTML = $('#select-filters').attr('popover-content');

	$('#select-filters').popover({
		trigger: 'click',
		html: true,
		content: filtersListHTML,
		placement: 'bottom'
	});

	$('#select-filters').attr('title', $('#select-filters').attr('link-title'));
});
