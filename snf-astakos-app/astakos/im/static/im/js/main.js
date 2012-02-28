$(function() {
	$('table.id-sorted').tablesorter({ sortList: [[0, 0]] });

	$('tr.row-template').hide();
	$('div.alert-message').hide();
});

$('.needs-confirm').live('click', function() {
	$('div.alert-message').show('fast');
	$('div.actions').hide('fast');
	return false;
});

$('.alert-close').live('click', function() {
	$('div.alert-message').hide('fast');
	$('div.actions').show('fast');
	return false;
});
