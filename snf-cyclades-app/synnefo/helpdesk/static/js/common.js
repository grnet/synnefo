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

})

