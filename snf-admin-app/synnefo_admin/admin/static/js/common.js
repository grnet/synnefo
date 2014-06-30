

$(document).ready(function(){

  // elements that adjust their position over scroll
  var $actionbar = $('.actionbar');
  var $infoBlock = $('.info-block');
  var infoBlockMarg = $infoBlock.css('marginRight');
  var actionbarTop = $actionbar.offset().top;
  var actionBarWidth = $actionbar.outerWidth(true);
  var $win = $(window),
      isFixed = 0,
      navHeight = $('.main-nav').outerHeight(true),
      filtersHeight = $('.filters').outerHeight()

    function processScroll() {
      var i, scrollTop = $win.scrollTop();
      if(scrollTop >= navHeight+filtersHeight && !isFixed) {
        console.log('1')
        isFixed = 1;
        $actionbar.addClass('fixed');
        $actionbar.css('top', navHeight);
        if(!$infoBlock.hasClass('.fixed-arround')) {
          $infoBlock.addClass('fixed-arround');
          $infoBlock.css('marginLeft', actionBarWidth);
        }
      }
      else if(scrollTop <= navHeight+filtersHeight && isFixed){
        console.log('2');
        isFixed = 0;
        $actionbar.removeClass('fixed');
        if($infoBlock.hasClass('fixed-arround')) {
          $infoBlock.removeClass('fixed-arround');
          $infoBlock.css('marginLeft', infoBlockMarg);
        }
        
      }
    }
  processScroll();

 
  $win.on('scroll', processScroll)


/* General */

  /* When the user scrolls check if sidebar needs to get fixed position */
  /*$(window).scroll(function() {
    fixedMimeSubnav();
  });*/


  /* Sets sidebar's position fixed */
  /* subnav-fixed is added/removed from processScroll() */
/*  function fixedMimeSubnav() {
    if($('.actionbar').hasClass('subnav-fixed'))
      $('.info').addClass('info-fixed').removeClass('info');
    else
      $('.info').removeClass('info-fixed').addClass('info');
  };

*/

  // $('input').blur(); // onload there is no input field focus
  $("[data-toggle=popover]").click(function(e) {
    e.preventDefault();
  })
  $("[data-toggle=popover]").popover();
  $("[data-toggle=tooltip]").tooltip();
});