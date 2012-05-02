function setContainerMinHeight(){

    var h = $('.header').height();
    var f = $('.footer').height();
    var w = $(window).height();
    var pTop = parseInt (($('.container .wrapper').css('padding-top').replace("px", "")) );
    var pBottom = parseInt (($('.container .wrapper').css('padding-bottom').replace("px", "")));

    var c = w - ( h+f+pTop+pBottom);
    $('.container .wrapper').css('min-height', c);
    

}

$(document).ready(function() {

	setContainerMinHeight();
	
    $('.show-extra').click(function(e) {
        e.preventDefault();
        
        $(this).parents('.bg-wrap').find('.extra').toggle('slow');
        $('.hide-extra').toggle();    
    });
    $('.hide-extra').click(function(e) {
        e.preventDefault();
        $(this).hide();
        $(this).parents('.bg-wrap').find('.extra').hide('slow');
    });
    
    $('.box-more p').click(function(e) {
        $(this).siblings('.clearfix').toggle('slow');
        $(this).parents('.box-more').toggleClass('border');
    });
	
		
	$('.top-msg a.close').click(function(e) {
        e.preventDefault();
        $(this).parents('.top-msg').slideUp('5000', function() {
             $('.top-msg').removeClass('active')
        });
    });
    
    //$('select').dropkick();
    
  
    if ( $('#os').length > 0 ) {
       var os = BrowserDetect.OS;
       if ( os!=="an unknown OS" ) {
           $('#os').html('version '+os);
        }
    }
    
    $('.top-msg .success').parents('.top-msg').css(
    	{
    		backgroundColor: '#f3c',
    		color: '#fff'
    	}
    )
    
    $('.top-msg .error').parents('.top-msg').css(
    	{
    		backgroundColor: 'red',
    		color: '#fff'
    	}
    )
    
    
    $('.top-msg .warning').parents('.top-msg').css(
    	{
    		backgroundColor: '#90f',
    		color: '#fff'
    	}
    )
    
});
