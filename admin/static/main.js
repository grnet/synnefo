$(function() {
	$('table.id-sorted').tablesorter({ sortList: [[0, 0]] });

	$('tr.row-template').hide();
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
