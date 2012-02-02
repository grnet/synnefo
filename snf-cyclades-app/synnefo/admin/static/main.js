function append_item(className, api_path) {
	var input = $('.' + className);
	var label = input.siblings('label');
	var id = input.val();

	if (!id) {
		label.hide();
		return;
	}

	$.getJSON(api_path + id, function(data) {
		label.show();
		var a = label.find('a');
		a.attr('href', data['ref']);
		a.empty();
		a.append(data['name']);
	});
}

function append_server() {
	append_item('append-server', '/admin/api/servers/');
}

$(function() {
	$('table.id-sorted').tablesorter({ sortList: [[0, 0]] });

	$('tr.row-template').hide();
	$('div.alert-message').hide();

	append_server();
	$('.append-server').change(function() {
		append_server();
	});
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
