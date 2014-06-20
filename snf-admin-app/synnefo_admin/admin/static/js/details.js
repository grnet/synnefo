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


});