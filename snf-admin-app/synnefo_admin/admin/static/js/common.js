$(document).ready(function(){

	$('.error-sign').click(function(e) {
		e.preventDefault();
	});

	$("[data-toggle=popover]").click(function(e) {
		e.preventDefault();
	});
	$("[data-toggle=popover]").popover();
	$("[data-toggle=tooltip]").tooltip();
});

snf = {
	funcs: {
		showBottomModal: function($modal) {
			var height = -$modal.outerHeight(true)
			if($modal.css('bottom') !== '0px')
				$modal.css('bottom', height)
			$modal.show();
			$modal.animate({'bottom': '0px'}, 'slow')
		}
	}
};