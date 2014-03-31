$(document).ready(function() {
	var selectedItems = {
		actions: {
			activate: true,
			accept: true,
			verify: true,
			deactivate: true,
			reject: true
		},
		uuids: []
	};

    var items = [];

	$(window).scroll(function() {
		fixedMime();
	});

	$('.sidebar a').click(function(e) {
		if($(this).attr('disabled') !== undefined) {
			e.preventDefault();
			e.stopPropagation();
		}
		else {
			var modal = $(this).data('target');
			$(modal).find('.modal-footer form input[name="uuids"]').val('['+selectedItems.uuids+']');
		}
	});

	$('.table-users'). find('tbody input[type=checkbox]').click(function(e) {
		e.stopPropagation();
		var trEl = $(this).closest('tr');
		var item = {
			actions: {
				activate: trEl.data('allow-activate'),
				accept: trEl.data('allow-accept'),
				verify: trEl.data('allow-verify'),
				deactivate: trEl.data('allow-deactivate'),
				reject: trEl.data('allow-reject')
			},
			id: trEl.attr('id')
		};
		if (this.checked) {
			trEl.addClass('selected');
			items.push(item);
			enableActions(item);
			selectedItems.uuids.push(item.id);
		}
		else {
			trEl.removeClass('selected');
			removeItem(trEl.attr('id'), selectedItems.uuids);
			removeItem(item, items);
			resetEnabledActions();
			for(var i=0; i<items.length; i++) {
				enableActions(items[i]);
			}
		}
		$('.filters').find('.selected .badge').html(selectedItems.uuids.length);
		for(var action in selectedItems.actions) {
			var actionBtn = $('.sidebar').find('a.'+action);
			if(!selectedItems.actions[action])
				actionBtn.attr('disabled', 'disabled');
			else
				actionBtn.removeAttr('disabled')
		};
		if(selectedItems.uuids.length !== 0)
			$('.sidebar').find('a.contact').removeAttr('disabled');
		else
			$('.sidebar').find('a').attr('disabled', 'disabled');
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
	function resetEnabledActions() {
		for(var prop in selectedItems.actions)
			selectedItems.actions[prop] = true;
	};

	function removeItem(item, array) {
		var index;
		if (typeof(item) === 'object') {
			index = array.map(function(item) {
				return item.id;
			}).indexOf(item.id);
		}
		else
			index = array.indexOf(item);

		if(index > -1) {
			array.splice(index, 1);
		}
	};

	function enableActions(item) {
		var prevActions = selectedItems.actions;
        var boolAction;
		for(var prop in prevActions) {
            boolAction = (item.actions[prop] === "True");
             prevActions[prop] = prevActions[prop] && boolAction;
		}

	};

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
		var dataName = Object.keys(link.data()).toString().toDash();
		var dataValue = link.data(dataName);
		link.toggleClass('current');
		if(dataName == 'state') {
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
				$('.table-users').find('.checkbox-column input[type=checkbox]:checked').closest('tr').show();
			}
		}
		else {
			linkSelected.removeClass('current');
			links = link.closest('li').siblings('li').find('a.current');
			tableRows = $('.table-users').find("tr[data-"+dataName+"='"+dataValue+"']");
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
	};
	String.prototype.toDash = function(){
		return this.replace(/([A-Z])/g, function($1){return "-"+$1.toLowerCase();});
	};
});

