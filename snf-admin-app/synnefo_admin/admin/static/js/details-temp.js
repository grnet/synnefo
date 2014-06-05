$(document).ready(function() {
	var item = {};
	$('.actions a').click(function() {
		item.name =$(this).closest('.object-details').find('h4 .title').text();
		item.id =$(this).closest('.object-details').attr('data-id');
		console.log(item.name, item.id)
		if($(this).attr('data-action') === 'contact') {
			item.email =$(this).closest('.object-details').find('h4 .email').text();
			console.log(item.email);
		}
		drawModalSingle('#'+$(this).attr('data-action'))
	});
	function drawModalSingle(modalID) {
		var $modal = $(modalID);

		var $tableBody = $modal.find('.table-selected tbody');
		$tableBody.empty();

		var $idsInput = $(modalID).find('.modal-footer form input[name="ids"]');
		$idsInput.val([item.id])		

		if($modal.attr('data-action') === 'contact') {
			var templateRow = '<tr data-toggle="tooltip" data-placement="bottom" title="" data-itemid="'+item.id+'"><td class="full-name">'+item.name+'</td><td class="email">'+item.email+'</td></tr>';
		}
		else {
			var templateRow = '<tr data-itemid=""><td class="item-name">'+item.name+'</td><td class="item-id">'+item.id+'</td></tr>';
		}
		$tableBody.append(templateRow)
	}
})