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
		var $toggleAllBtn = $expandBtn.closest('.info-block.object-details').find('.show-hide-all');
		if(allSameClass){
			if($expandBtn.closest('h4').hasClass('expanded')){
				$toggleAllBtn.addClass('open');
				$toggleAllBtn.find('.txt').text(txt_all[1]);
			}
			else {
				$toggleAllBtn.removeClass('open');
				$toggleAllBtn.find('.txt').text(txt_all[0]);
			}
		}
		else {
			$toggleAllBtn.removeClass('open');
			$toggleAllBtn.find('.txt').text(txt_all[0]);
		}
	});

	   // hide/show expand/collapse 
  

  var txt_all = ['Expand all','Collapse all'];
  

  $('.show-hide-all span.txt').text(txt_all[0]);
  
  
  $('.show-hide-all').click(function(e){
    e.preventDefault();
    $(this).toggleClass('open');
    var tabs = $(this).parent('.info-block').find('.object-details-content');

    if ($(this).hasClass('open')){
      $(this).find('span.txt').text( txt_all[1]);
      tabs.each(function() {
        $(this).stop().slideDown('slow');
        $(this).siblings('h4').addClass('expanded');
        $(this).siblings('h4').find('.arrow').removeClass('snf-angle-down').addClass('snf-angle-up')
      });


    } else {
      $(this).find('span.txt').text( txt_all[0]);
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

	function resetItemInfo(modal) {
		var $modal = $(modal);
		$modal.find('.summary .info-list').remove();
	}

	function drawModalSingleItem(modalID, itemName, itemID) {
		var $summary = $(modalID).find('.modal-body .summary');
		var $actionBtn = $(modalID).find('.apply-action');
		var html = _.template(snf.modals.html.singleItemInfo);

		$actionBtn.attr('data-ids','['+itemID+']');
		$summary.append(html({name: itemName, id: itemID}));
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
		if(!noError) {
			e.preventDefault();
			e.stopPropagation();
		}
		else {
			snf.modals.performAction($modal, $notificationArea, snf.modals.html.notifyRefreshPage, 0, countAction);
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


