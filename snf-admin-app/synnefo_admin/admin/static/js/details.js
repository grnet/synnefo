$(document).ready(function() {

	var navsHeight = $('.main-nav').height() + $('.sub-nav').height();
	$('.sub-nav .link-to-anchor').click(function(e) {
		e.preventDefault();
		var pos = $($.attr(this, 'href')).offset().top - navsHeight;
		$('html, body').animate({
			scrollTop: pos
		}, 500)
	})
	// the arrow next to the name of the resource
	$('.object-details h4 .arrow').click(function(){
		var $expandBtn = $(this);
		var hasNotClass = !$expandBtn.closest('h4').hasClass('expanded');
		$expandBtn.closest('h4').toggleClass('expanded');

		if(hasNotClass) {
			$expandBtn.removeClass('snf-angle-down').addClass('snf-angle-up');
			$expandBtn.closest('h4').siblings('.object-details-content').stop().slideDown('slow');
		}
		else {
			$expandBtn.removeClass('snf-angle-up').addClass('snf-angle-down')
			$expandBtn.closest('h4').siblings('.object-details-content').stop().slideUp('slow');
		}

		var $areas = $expandBtn.closest('.info-block.object-details') // *** add another class

		var allSameClass = true;

		($areas.find('.object-details')).each(function() {
			if(hasNotClass){
				allSameClass = allSameClass && $(this).find('h4').hasClass('expanded');
			}
			else{
				allSameClass = allSameClass && !$(this).find('h4').hasClass('expanded');
			}

			if(!allSameClass){
				return false;
			}
		});
		var $toggleAllBtn = $expandBtn.closest('.info-block.object-details').find('.js-show-hide-all');
		if(allSameClass){
			if($expandBtn.closest('h4').hasClass('expanded')) {
				$toggleAllBtn.addClass('open');
			}
			else {
				$toggleAllBtn.removeClass('open');
			}
		}
		else {
			$toggleAllBtn.removeClass('open');
		}
	});


	// expand/collapse
	$('.btn-toggle-info').click(function(e) {
		e.preventDefault();
		$(this).toggleClass('open');
		if($(this).hasClass('open')) {
			$(this).parent().siblings('.js-slide-area').stop().slideDown('slow');
		}
		else {
			$(this).parent().siblings('.js-slide-area').stop().slideUp('slow');
		}
	});

	// hide/show
	$('.toggle-fade').click(function(e) {
		e.preventDefault();
		var $areaToHide = $(this).siblings('.fade-area.vis');
		var $areaToShow = $(this).siblings('.fade-area:not(.vis)');
		var $btn = $(this);
		$areaToHide.fadeOut('fast', function() {
			$(this).removeClass('vis');
			if($(this).hasClass('area-0')) {
				$btn.addClass('open');
			}
			else {
				$btn.removeClass('open');
			}
			$areaToShow.fadeIn('slow', function() {
				$(this).addClass('vis');
			});
		});
	});

	var txt_format = ['Show raw data', 'Show formated data'];


  $('.js-show-hide-all').click(function(e){
    e.preventDefault();
    $(this).toggleClass('open');
    var tabs = $(this).parent('.info-block').find('.object-details-content');

    if ($(this).hasClass('open')){
      tabs.each(function() {
        $(this).stop().slideDown('slow');
        $(this).siblings('h4').addClass('expanded');
        $(this).siblings('h4').find('.arrow').removeClass('snf-angle-down').addClass('snf-angle-up')
      });


    } else {
      // $(this).find('span.txt').text( txt_all[0]);
      tabs.each(function() {
        $(this).stop().slideUp('slow');
        $(this).siblings('h4').removeClass('expanded');
        $(this).siblings('h4').find('.arrow').removeClass('snf-angle-up').addClass('snf-angle-down')
      });
    }
  }); 

	$('.main .object-details h4 .arrow').trigger('click');



		/* Modals */

	$('.actions-per-item .custom-btn').click(function() {
		var itemID = $(this).closest('.object-details').data('id');
		var itemName = $(this).closest('.object-details').find('h4 .title').text();
		var modalID = $(this).data('target');
		drawModalSingleItem(modalID, itemName, itemID);
	});

	function resetItemInfo(modal) {
		var $modal = $(modal);
		$modal.find('.summary dl').remove();
	}

	function drawModalSingleItem(modalID, itemName, itemID) {
		var tpl;
		var html;
		var $summary = $(modalID).find('.modal-body .summary');
		var $actionBtn = $(modalID).find('.apply-action');
		// cannot use JSON.parse because data-keys inlude single quotes
		var inputsNames = $actionBtn.attr('data-keys').slice(1, -1).replace(/ /g,'').split(',');
		inputsNames = inputsNames.map(function(item) {
			return item.slice(1, -1); // remove extra quotes
		});
		if (modalID == '#user-modify_email') {
			tpl = snf.modals.html.singleItemInfoWithEmailInput;
			html = _.template(tpl,
				{
					name: itemName,
					id: itemID,
					inputName: inputsNames[0] // modify_email has only 1 input
				}
			);
		}
		else{
			tpl = snf.modals.html.singleItemInfo;
			html = _.template(tpl, {name: itemName, id: itemID});
		}
		$actionBtn.attr('data-ids','['+itemID+']');
		$summary.append(html);
	};


	function collectActionData(modal) {
		var $list = $(modal).find('.info-list');
		var actionData = [];
		var hasInputs = $list.find('dd input').length > 0;
		var itemData = {};
		itemData['id'] = $list.attr('data-itemid');
		if(hasInputs) {
			itemData['data'] = {};
			var key = $list.find('dd input').attr('name');
			var value = $list.find('dd input').val();
			itemData['data'][key] = value;
		}

			actionData.push(itemData)
		return actionData;
	};

	$('.modal').find('.cancel').click(function() {
		$modal =$(this).closest('.modal');
		snf.modals.resetInputs($modal);
		snf.modals.resetErrors($modal);
		resetItemInfo($modal);
		$('[data-toggle="popover"]').popover('hide');

	});

	var $notificationArea = $('.notify');
	var countAction = 0;
	$('.modal .apply-action').click(function(e) {
		var $modal = $(this).closest('.modal');
		var noError = true;
		if($modal.attr('data-type') === 'contact') {
			noError = snf.modals.validateContactForm($modal);
		}
		if($modal.attr('data-type') === 'modify_email') {
			var validForm = snf.modals.validateModifyEmailForm($modal);
			noError = noError && validForm;
		}
		if(!noError) {
			e.preventDefault();
			e.stopPropagation();
		}
		else {
			snf.modals.performAction($modal, $notificationArea, snf.modals.html.notifyRefreshPage, collectActionData($modal), 0, countAction);
			snf.modals.resetInputs($modal);
			snf.modals.resetErrors($modal);
			resetItemInfo($modal);
			$('[data-toggle="popover"]').popover('hide');
			countAction++;
		}
	});

    setDropdownHeight();
});

$(window).resize(function(){
    setDropdownHeight();
})

function setDropdownHeight() {
    var mainNavH = $('.navbar-default').height();
    var subNavH = $('.sub-nav').height();
    var windowH = $(window).height();
    // 20 is the distance from the bottom of the page so that
    // the dropdown does not collapse with the window
    var res = windowH - (mainNavH + subNavH) - 20;
    $('.dropdown-menu').each(function(){
        $(this).css('max-height', res);
    });
}


