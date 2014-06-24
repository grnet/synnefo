

$(document).ready(function(){

 // fix sub nav on scroll
  var $win = $(window)
    , $nav = $('.subnav:not(.main-nav)')
    , navTop = $('.subnav:not(.main-nav)').length && $('.subnav:not(.main-nav)').offset().top
    , isFixed = 0,
      navMainTop = $('.main-nav').outerHeight();

  function processScroll() {
    var i, scrollTop = $win.scrollTop();
    var navTemp = navTop - navMainTop*2;
    if (scrollTop >= (navTop - navMainTop*2) && !isFixed) {
      console.log('1 scrollTop: '+scrollTop+' navTop: '+navTemp);
      isFixed = 1;
      $nav.addClass('subnav-fixed');
    } else if (scrollTop <= (navTop -navMainTop*2) && isFixed) {
      console.log('2 scrollTop: '+scrollTop+' navTop: '+navTemp);
      isFixed = 0;
      $nav.removeClass('subnav-fixed');
    }
  }

  processScroll();

  // hack sad times - holdover until rewrite for 2.1
  $nav.on('click', function () {
    if (!isFixed) setTimeout(function () {  $win.scrollTop($win.scrollTop()) }, 10)
  })

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

  /* Temporary: the server should indicate the current place */
  var curPath = window.location.pathname;

  function showCurrentPlace() {
    var pathArray = curPath.split('/');

    $('.main-nav li').each(function () {

      if($(this).find('a').attr('href') === curPath) {
        if($(this).closest('ul').hasClass('dropdown-menu')) {
          $(this).closest('li').addClass('active');
          $(this).closest('ul').closest('li').addClass('active');
        }
        else {
          $(this).closest('li').addClass('active');

        }
      }
      else if('/'+pathArray[1]+'/'+pathArray[2] === $(this).find('a').attr('href')) { // sumvasi! ***
        $(this).closest('li').addClass('active');
      }
      else {
        $(this).closest('li').removeClass('active');
      }
    });
  };

  showCurrentPlace();


})
