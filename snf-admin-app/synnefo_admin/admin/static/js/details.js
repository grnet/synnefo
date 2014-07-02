$(document).ready(function(){

	var navsHeight = $('.main-nav').height() + $('.sub-nav').height();
	$('.sub-nav .link-to-anchor').click(function(e) {
		e.preventDefault();
		var pos = $($.attr(this, 'href')).offset().top - navsHeight;
		$('html, body').animate({
			scrollTop: pos
		}, 500)
	})
	$('.object-details h4 .arrow').click(function(){
		var $expandBtn = $(this);
		var hasClass = !$expandBtn.closest('h4').hasClass('expanded');

		if(hasClass) {
			$expandBtn.removeClass('snf-angle-down').addClass('snf-angle-up');
			$expandBtn.closest('h4').siblings('.object-details-content').stop().slideDown('slow');
		}
		else {
			$(this).siblings('h4').find('.arrow').removeClass('snf-angle-up').addClass('snf-angle-down')
			$expandBtn.closest('h4').siblings('.object-details-content').stop().slideUp('slow');
		}

		var $areas = $expandBtn.closest('.info-block.object-details') // *** add another class

		var allSameClass = true;

		($areas.find('.object-details')).each(function() {
			if(hasClass)
				allSameClass = allSameClass && $(this).find('h4').hasClass('expanded');
			else
				allSameClass = allSameClass && !$(this).find('h4').hasClass('expanded');

			if(!allSameClass)
				return false;
		});
		if(allSameClass)
			$expandBtn.closest('.info-block.object-details').find('.show-hide-all').trigger('click');
		$expandBtn.closest('h4').toggleClass('expanded');
	});

	   // hide/show expand/collapse 
  

  var txt_all = ['+ Expand all','- Collapse all'];
  

  $('.show-hide-all span').text(txt_all[0]);
  
  
  $('.show-hide-all').click(function(e){
    e.preventDefault();
    $(this).toggleClass('open');
    var tabs = $(this).parent('.info-block').find('.object-details-content');

    if ($(this).hasClass('open')){
      $(this).find('span').text( txt_all[1]);
      tabs.each(function() {
        $(this).stop().slideDown('slow');
        $(this).siblings('h4').addClass('expanded');
        $(this).siblings('h4').find('.arrow').removeClass('snf-angle-down').addClass('snf-angle-up')
      });


    } else {
      $(this).find('span').text( txt_all[0]);
      tabs.each(function() {
        $(this).stop().slideUp('slow');
        $(this).siblings('h4').removeClass('expanded');
        $(this).siblings('h4').find('.arrow').removeClass('snf-angle-up').addClass('snf-angle-down')
      });
    }
  }); 

$('.main .object-details h4 .arrow').trigger('click')

		/* Modals */

	$('.actions-per-item .custom-btn').click(function() {
		var itemID = $(this).closest('.object-details').data('id');
		var itemName = $(this).closest('.object-details').find('h4 .title').text();
		var modalID = $(this).data('target');
		drawModalSingleItem(modalID, itemName, itemID);
	});


	function showError(modal, errorSign) {
		var $modal = $(modal);
		var $errorMsg = $modal.find('*[data-error="'+errorSign+'"]');
		$errorMsg.show();
	};

	function checkInput(modal, inputArea, errorSign) {
		var $inputArea = $(inputArea);
		var $errorSign = $(modal).find('*[data-error="'+errorSign+'"]');

		$inputArea.keyup(function() {
			if($.trim($inputArea.val())) {
				$errorSign.hide();
			}
		})

	};

	function resetErrors(modal) {
		var $modal = $(modal);
		$modal.find('.error-sign').hide();
	};

	var defaultEmailSubj = $('.modal[data-type="contact"]').find('.subject').val();
	var defaultEmailBody = $('.modal[data-type="contact"]').find('.email-content').val();
	function resetInputs(modal) {
		var $modal = $(modal);
		$modal.find('input[type=text]').val(defaultEmailSubj);
		$modal.find('textarea').val(defaultEmailBody);
	};
		
	function resetItemInfo(modal) {
		var $modal = $(modal);
		$modal.find('.summary .info-list').remove();
	}


	function drawModalSingleItem(modalID, itemName, itemID) {
		var $summary = $(modalID).find('.modal-body .summary');
		var $actionBtn = $(modalID).find('.apply-action');
		var html = '<dl class="dl-horizontal info-list"><dt>Name:</dt><dd>'+itemName+'</dd><dt>ID:</dt><dd>'+itemID+'</dd><dl>'
		$actionBtn.attr('data-ids','['+itemID+']');
		$summary.append(html);
	};

	var $notificationArea = $('.notify');
	function performAction(modal) {
		var $modal = $(modal);
		var $actionBtn = $modal.find('.apply-action')
		var url = $actionBtn.data('url');

		var data = {
		op: $actionBtn.data('op'),
		target: $actionBtn.data('target'),
		ids: $actionBtn.data('ids')
		}
		var contactAction = (data.op === 'contact' ? true : false);

		if(contactAction) {
			data['subject'] = $modal.find('input[name="subject"]').val();
			data['text'] = $modal.find('textarea[name="text"]').val();
		}
		console.log(data)
		$.ajax({
			url: url,
			type: 'POST',
			data: JSON.stringify(data),
			contentType: 'application/json',
			timeout: 100000,
			success: function(response, statusText, jqXHR) {
				var htmlSuccess = '<dl class="dl-horizontal"><dt><span class="success snf-font-admin snf-exclamation-sign"></span> Action '+data.op+': </dt><dd>'+response.result+'<a href="" class="remove-log" title="Remove this line">X</a></dd></dl>';
				$notificationArea.find('.btns').before(htmlSuccess);
				var height = -$notificationArea.outerHeight(true)
					if($notificationArea.css('bottom') !== '0px')
						$notificationArea.css('bottom', height)
					$notificationArea.show();
					$notificationArea.animate({'bottom': '0px'})
			},
			error: function(jqXHR, statusText) {
				console.log(jqXHR, statusText, jqXHR.status);
				var htmlError;
				if(jqXHR.status === 500 || jqXHR.status === 0) {
					htmlError = '<dl class="dl-horizontal"><dt><span class="error snf-font-admin snf-exclamation-sign"></span> Action '+data.op+': </dt><dd>[code: '+ jqXHR.status +'] '+jqXHR.statusText+'<a href="" class="remove-log" title="Remove this line">X</a></dd></dl>';
				}
				else {

					htmlError ='<dl class="dl-horizontal"><dt><span class="error snf-font-admin snf-exclamation-sign"></span> Action '+data.op+': </dt><dd>'+jqXHR.result+'</dd><dt>Error for the items: </dt><dd>'+jqXHR.error_ids.toString().replace(/\,/gi, ', ')+'<a href="" class="remove-log" title="Remove this line">X</a></dd></dl>';
				}

				$notificationArea.find('.btns').before(htmlError);
				var height = -$notificationArea.outerHeight(true)
				if($notificationArea.css('bottom') !== '0px') {
					$notificationArea.css('bottom', height)
				}
				$notificationArea.show();
				$notificationArea.animate({'bottom': '0px'})
			}
		});
	}

	$notificationArea.on('click', '.remove-log', function(e) {
		e.preventDefault();
		var $dl = $(this).closest('dl');
		$dl.fadeOut('slow', function() {
			$dl.remove();
			if($notificationArea.find('dl').length === 0) {
				$notificationArea.find('.close-notifications').trigger('click');
			}
		});
	});
	$notificationArea.on('click', '.close-notifications', function(e) {
		e.preventDefault();
		var height = -$notificationArea.outerHeight(true)
		$notificationArea.animate({'bottom': height}, 'slow')
	});
	$notificationArea.on('click', '.clear-notifications', function(e) {
		e.preventDefault();
		$notificationArea.find('dl').fadeOut('slow', function() {
			$(this).remove();
			$notificationArea.find('.close-notifications').trigger('click');
		});

	});

	$('.modal').find('.cancel').click(function() {
		$modal =$(this).closest('.modal');
		resetInputs($modal);
		resetErrors($modal);
		resetItemInfo($modal);
		$('[data-toggle="popover"]').popover('hide');

	});


	$('.modal .apply-action').click(function(e) {
		var $modal = $(this).closest('.modal');
		var completeAction = true;
		if($modal.attr('id') === 'user-contact') {
			var $emailSubj = $modal.find('.subject');
			var $emailCont = $modal.find('.email-content');
			if(!$.trim($emailSubj.val())) {
				// e.preventDefault();
				e.stopPropagation();
				showError($modal, 'empty-subject');
				checkInput($modal, $emailSubj, 'empty-subject');
				completeAction = false;
			}
			if(!$.trim($emailCont.val())) {
				// e.preventDefault();
				e.stopPropagation();
				showError($modal, 'empty-body')
				checkInput($modal, $emailCont, 'empty-body');
				completeAction = false;
			}
		}
		if(completeAction) {
			performAction($modal);
			resetInputs($modal);
			resetErrors($modal);
			resetItemInfo($modal);
			$('[data-toggle="popover"]').popover('hide');
		}
	});

	
});