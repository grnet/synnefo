$(document).ready(function() {
	var selectedCheckboxes = 0;
	
	$(window).scroll(function() {
		fixedMime();
	});

	$('.table-users'). find('tbody input[type=checkbox]').click(function(e) {
		e.stopPropagation();
		if (this.checked) {
			selectedCheckboxes++;
			$(this).closest('tr').addClass('selected');
		}
		else {
			selectedCheckboxes--;
			$(this).closest('tr').removeClass('selected');
		}
		$('.filters').find('.selected .badge').html(selectedCheckboxes);
	});

	$('.table-users'). find('tbody tr').click(function() {
		if(!$(this).hasClass('selected'))
			$(this).find('input[type=checkbox]').prop('checked', true).triggerHandler('click');
		else
			$(this).find('input[type=checkbox]').prop('checked', false).triggerHandler('click');
	});

	$('.filters').find('a').click(function (e) {
		e.preventDefault();
		filterUsersTable(this);
	});


	// subnav-fixed is added/removed from processScroll()
	function fixedMime() {
		if($('.messages').find('.sidebar').hasClass('subnav-fixed'))
			$('.messages').find('.info').addClass('info-fixed').removeClass('info');
		else
			$('.messages').find('.info').removeClass('info-fixed').addClass('info');
	};

	function filterUsersTable(clickedFilter) {
		var link = $(clickedFilter);
		var tableRows, linkAll;
		var links;
		var linkSelected = link.closest('li').siblings('li').find('a.selected');

		link.toggleClass('current');
		
		if(link.data('state') === 'all') {
			linkSelected.removeClass('current');
			links = link.closest('li').siblings('li').find('a:not(.selected)');
			tableRows = $('.table-users').find('tbody tr');
			if(link.hasClass('current')) {
				links.addClass('current');
				tableRows.show();
			}
			else {
				links.removeClass('current');
				tableRows.hide();
			}
		}
		else if(link.data('state') === 'selected') {
			links = link.closest('li').siblings('li').find('a');
			links.removeClass('current');
			$('.table-users').find('tbody tr').hide();
			$('.table-users').find('.checkbox input[type=checkbox]:checked').closest('tr').show();
		}
		else {
			linkSelected.removeClass('current');
			links = link.closest('li').siblings('li').find('a.current');
			tableRows = $('.table-users').find("tr[data-state='" + link.data('state') + "']");
			linkAll = link.closest('li').siblings('li').find('a[data-state=all]');
			if(link.hasClass('current')) {
				tableRows.show();
				if(links.length === 2 && !links.hasClass('selected'))
					linkAll.addClass('current');
			}
			else {
				tableRows.hide();
				linkAll.removeClass('current');

				if(links.length < 2)
					linkAll.removeClass('current');
			}
		}
	}
});
