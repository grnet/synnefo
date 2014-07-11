snf = {
	modals: {
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
				snf.modals.showBottomModal($modal);
			}
			else {
				snf.modals.hideBottomModal($modal);
			}
		},
		showError: function(modal, errorSign) {
			var $modal = $(modal);
			var $errorMsg = $modal.find('*[data-error="'+errorSign+'"]');
			console.log('*', $modal, $errorMsg)
			$errorMsg.show();
		},
		resetErrors: function (modal) {
			var $modal = $(modal);
			$modal.find('.error-sign').hide();
		},
		checkInput: function(modal, inputArea, errorSign) {
			var $inputArea = $(inputArea);
			var $errorSign = $(modal).find('*[data-error="'+errorSign+'"]');

			$inputArea.keyup(function() {
				if($.trim($inputArea.val())) {
					$errorSign.hide();
				}
			})
		},
		defaultEmailSubj: undefined,
		defaultEmailBody: undefined,
		resetInputs: function(modal) {
			var $modal = $(modal);
			$modal.find('input[type=text]').val(snf.modals.defaultEmailSubj);
			$modal.find('textarea').val(snf.modals.defaultEmailBody);
		},
	},
};


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

	$('#toggle-notifications').click(function(e) {
		e.preventDefault();
		snf.modals.toggleBottomModal($notificationArea);
	});

	$(document).keyup(function(e) {
		if (!($(e.target).closest("input")[0] || $(e.target).closest("textarea")[0])) {
			if(e.keyCode === 73) {
				$('#toggle-notifications').trigger('click');
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
		snf.modals.hideBottomModal($notificationArea);
	});

	snf.modals.defaultEmailSubj = $('.modal[data-type="contact"]').find('.subject').val();
	snf.modals.defaultEmailBody = $('.modal[data-type="contact"]').find('.email-content').val();
});
