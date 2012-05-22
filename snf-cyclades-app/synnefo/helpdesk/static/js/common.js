$(document).ready(function(){ $("input").focus(); })

$(document).ready(function(){
 // fix sub nav on scroll
  var $win = $(window)
    , $nav = $('.subnav')
    , navTop = $('.subnav').length && $('.subnav').offset().top
    , isFixed = 0

  function processScroll() {
    var i, scrollTop = $win.scrollTop()
    if (scrollTop >= navTop && !isFixed) {
      isFixed = 1
      $nav.addClass('subnav-fixed')
    } else if (scrollTop <= navTop && isFixed) {
      isFixed = 0
      $nav.removeClass('subnav-fixed')
    }
  }

  processScroll();

  // hack sad times - holdover until rewrite for 2.1
  $nav.on('click', function () {
    if (!isFixed) setTimeout(function () {  $win.scrollTop($win.scrollTop()) }, 10)
  })

  $win.on('scroll', processScroll)
	
	  
  
  // hide/show expand/collapse 
  
  $('.subnav a').click(function(){
  	$('.info-block-content, .show-hide-all').show();
  })
  
  function  checkBadgeExpanded(el){
  	if (el.hasClass('expanded')){
  		el.html( txt_tab[1]);
  	} else {
  		el.html( txt_tab[0]);
  	}
  }
  	
  var txt_tab = ['+ Show Info','- Hide Info'];
  var txt_all = ['+ Expand all','- Collapse all'];
  
  $('.show-hide-tabs span').html(txt_tab[0]); 	 
  $('.show-hide-all span').html(txt_all[0]); 	 
  
  
  $('.show-hide-all').click(function(){
  	var badgeAll = $(this).children('span');	
  	var tabs = $(this).parents('.info-block').find('.show-hide-tabs');
  	badgeAll.toggleClass('open');
  	
  	if (badgeAll.hasClass('open')){
  		badgeAll.html( txt_all[1]);
  		tabs.each(function() {
	  		$(this).next().show('slow');
		    $(this).children('span').addClass('expanded');
		    checkBadgeExpanded($(this).children('span'));
	    });
  		
  		
  	} else {
  		badgeAll.html( txt_all[0]);
  		tabs.each(function() {
	  		$(this).next().hide('slow');
		    $(this).children('span').removeClass('expanded');
		    checkBadgeExpanded($(this).children('span'));
	    });
  	}
	
  	 
  });   

  		    
  $('.show-hide-tabs').click(function(){	
  	
  	$(this).next().toggle('slow');
  	var badge = $(this).children('span');
  	badge.toggleClass('expanded');
  	checkBadgeExpanded(badge);

  }); 
  
  $('.info-block h3').click(function(){
  	$(this).next('.info-block-content').toggle();
  	$(this).prev('.show-hide-all').toggle();
  })  
	
})

