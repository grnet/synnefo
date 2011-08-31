$(function() {
	$('table.id-sorted').tablesorter({ sortList: [[0, 0]] });

	$('tr.row-template').hide();
	$('div.alert-message').hide();
});

$('.add-row').live('click', function() {
	template = $('tr.row-template');
	row = template.clone();
	row.removeClass('row-template');
	row.show();
	template.parent().append(row);
});

$('.delete-row').live('click', function() {
	$(this).parents('tr').remove();
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

