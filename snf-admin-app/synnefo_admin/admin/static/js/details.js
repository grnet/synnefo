$(document).ready(function(){
	$('.main .object-details').first().find('h4').addClass('expanded');
	$('.main .object-details').first().find('.object-details-content').slideDown('slow');


	 $('.object-details h4 .arrow,.object-details h4 .title .arrow').click(function(){
	var $expandBtn = $(this);
	var $areas = $expandBtn.closest('.info-block.object-details') // *** add another class
	$expandBtn.closest('h4').siblings('.object-details-content').toggle('slow');
	$expandBtn.closest('h4').toggleClass('expanded');
	var hasClass = $expandBtn.closest('h4').hasClass('expanded');
	var allSameClass = true;

	($areas.find('.object-details')).each(function() {
		if(hasClass)
			allSameClass = allSameClass && $(this).find('h4').hasClass('expanded');
		else
			allSameClass = allSameClass && !$(this).find('h4').hasClass('expanded');

		if(!allSameClass)
			return false;
	});
	console.log(allSameClass)
	if(allSameClass)
		$expandBtn.closest('.info-block.object-details').find('.show-hide-all').trigger('click');
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
        $(this).slideDown('slow');
        $(this).siblings('h4').addClass('expanded');
      });


    } else {
      $(this).find('span').text( txt_all[0]);
      tabs.each(function() {
        $(this).slideUp('slow');
        $(this).siblings('h4').removeClass('expanded');
      });
    }
  }); 


		/* Modals */

	$('.actions-per-item .custom-btn').click(function() {
		console.log('you clicked me');
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

	function resetInputs(modal) {
		var $modal = $(modal);
		$modal.find('textarea').val('Dear ,\n\n\nIf you did not sign up for this account you can ignore this email.\n\n\nFor any remarks or problems you may contact support@synnefo.live.\nThank you for participating in Synnefo.\n GRNET');
		$modal.find('input[type=text]').val('New email from ~okeanos');
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
		success: function(response, statusText, jqXHR) {
		  console.log('did it!', statusText)
		},
		error: function(jqXHR, statusText) {
		  console.log('error', statusText)
		}
		});
	}

	$('.modal').find('.cancel').click(function() {
		console.log('- cancel -')
		$modal =$(this).closest('.modal');
		resetInputs($modal);
		resetErrors($modal);
		resetItemInfo($modal);
		$('[data-toggle="popover"]').popover('hide');

	});


	$('.modal .apply-action').click(function(e) {
		console.log('- apply action -')
		var $modal = $(this).closest('.modal');
		var completeAction = true;
		if($modal.attr('id') === 'user-contact') {
			var $emailSubj = $modal.find('.subject');
			var $emailCont = $modal.find('.email-content');
			if(!$.trim($emailSubj.val())) {
				// e.preventDefault();
				e.stopPropagation();
				console.log('empty')
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
			resetErrors($modal);
			resetInputs($modal);
		}
	});

	
});