$(document).ready(function(){
	$('.main .object-details').first().find('h4').addClass('expanded');
	$('.main .object-details').first().find('.object-details-content').slideDown('slow');


	 $('.object-details h4 .arrow,.object-details h4 .title').click(function(){
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
      $(this).text( txt_all[1]);
      tabs.each(function() {
        $(this).slideDown('slow');
        $(this).siblings('h4').addClass('expanded');
      });


    } else {
      $(this).text( txt_all[0]);
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
		var modalID = $(this).data('target')
		console.log('itemID', itemID);
		console.log('itemName', itemName);
		console.log('modalID', modalID);
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
		$modal.find('textarea').val('');
		$modal.find('input[type=text]').val('');

	};

	function resetItemInfo(modal) {
		var $modal = $(modal);
		$modal.find('.summary .info-list').remove();
	}

	$('.modal button[type=submit]').click(function(e) {
		var $modal = $(this).closest('.modal');
		if($modal.attr('id') === 'user-contact') {
			var $emailSubj = $modal.find('.subject')
			var $emailCont = $modal.find('.email-content')
			if(!$.trim($emailSubj.val())) {
				e.preventDefault();
				showError($modal, 'empty-subject');
				checkInput($modal, $emailSubj, 'empty-subject');
			}
			if(!$.trim($emailCont.val())) {
				e.preventDefault();
				showError($modal, 'empty-body')
				checkInput($modal, $emailCont, 'empty-body');
			}
		}
	});


	function drawModalSingleItem(modalID, itemName, itemID) {
		var $summary = $(modalID).find('.modal-body .summary');
		var $actionBtn = $(modalID).find('.apply-action');
		var html = '<dl class="dl-horizontal info-list"><dt>Name:</dt><dd>'+itemName+'</dd><dt>ID:</dt><dd>'+itemID+'</dd><dl>'
		$actionBtn.attr('data-ids','['+itemID+']');
		$summary.append(html);
	};

	$('.modal').find('*[data-dismiss="modal"]').click(function() {
		$modal =$(this).closest('.modal');
		resetInputs($modal);
		resetErrors($modal);
		resetItemInfo($modal);

	});

});