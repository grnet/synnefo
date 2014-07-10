$(document).ready(function(){
	var $notificationArea = $('.notify');
	$notificationArea.css('bottom', -$notificationArea.outerHeight(true))
	$('.error-sign').click(function(e) {
		e.preventDefault();
	});

	$("[data-toggle=popover]").click(function(e) {
		e.preventDefault();
	});
	$("[data-toggle=popover]").popover();
	$("[data-toggle=tooltip]").tooltip();

	$('body').on('click', function (e) {
    //did not click a popover toggle or popover
    if ($(e.target).data('toggle') !== 'popover'
        && $(e.target).parents('.popover.in').length === 0) {
        $('[data-toggle="popover"]').popover('hide');
    }
});

	$('.modal').on('hidden.bs.modal', function () {
		$(this).find('.cancel').trigger('click');
	});

	$(document).keyup(function(e) {
		console.log(e.which, e.keyCode)
		if (!($(e.target).closest("input")[0] || $(e.target).closest("textarea")[0])) {
			if(e.keyCode === 73) {
				snf.funcs.toggleBottomModal($notificationArea);
			}
		}
	});
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

});

snf = {
	funcs: {
		showBottomModal: function($modal) {
			var height = -$modal.outerHeight(true)
				$modal.css('bottom', height)
				$modal.animate({'bottom': '0px'}, 'slow');
		},
		hideBottomModal: function($modal) {
			var height = -$modal.outerHeight(true)
			$modal.animate({'bottom': height}, 'slow', function() {
				if($modal.find('.log').length === 0) {
					$modal.find('.warning').remove();
				}
			});
		},
		toggleBottomModal: function($modal) {
			if($modal.css('bottom') !== '0px') {
				snf.funcs.showBottomModal($modal);
			}
			else {
				snf.funcs.hideBottomModal($modal);
			}
		}
	},
};