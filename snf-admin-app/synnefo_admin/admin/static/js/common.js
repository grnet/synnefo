$(document).ready(function(){

  $("[data-toggle=popover]").click(function(e) {
    e.preventDefault();
  })
  $("[data-toggle=popover]").popover();
  $("[data-toggle=tooltip]").tooltip();
});