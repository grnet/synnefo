function setContainerMinHeight( applicableDiv){
	
    if ( $(applicableDiv).length > 0 ) {
        //var h = $('.header').height(); div.header is not found 
        var f = $('.footer').height();
        var w = $(window).height();
        var pTop = parseInt (($(applicableDiv).css('padding-top').replace("px", "")) );
        var pBottom = parseInt (($(applicableDiv).css('padding-bottom').replace("px", "")));

        var c = w - ( f+pTop+pBottom+36);//36 is header's height.
        $(applicableDiv).css('min-height', c);
    }    

}

$(document).ready(function() {
	
	 
    setContainerMinHeight('.container .wrapper');
    
	
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
	
	var fixTopMessageHeight = function() {
		var topMargin = parseInt($('.mainlogo img').height())+parseInt($('.top-msg').css('marginBottom'));
		$('.mainlogo').css('marginTop','-'+topMargin+'px');
	}
	
	if ($('.mainlogo img').length > 0) {
		$('.mainlogo img').bind('load', fixTopMessageHeight)
	} else {
		fixTopMessageHeight();
	}
	
	$('.top-msg a.close').click(function(e) {
		e.preventDefault();
        $('.top-msg').animate({
            paddingTop:'0',
            paddingBottom:'0',
            height:'0'
        }, 1000, function (){
             $('.top-msg').removeClass('active')
        });
        $('.mainlogo').animate({
            marginTop:'0'
        }, 1000, function (){
             //todo
        });
    });	
    //$('select').dropkick();
    
 
    
    $('.top-msg .success').parents('.top-msg').css(
    	{
    		backgroundColor: '#00A2B1',
    		color: '#fff'
    	}
    )
    
    $('.top-msg .error').parents('.top-msg').css(
    	{
    		backgroundColor: '#C43F73',
    		color: '#fff'
    	}
    )
    
    
    $('.top-msg .warning').parents('.top-msg').css(
    	{
    		backgroundColor: '#F0A216',
    		color: '#fff'
    	}
    )
    
    $('.top-msg .info').parents('.top-msg').css(
    	{
    		backgroundColor: '#75A23A',
    		color: '#fff'
    	}
    )
    
});

$(window).resize(function() {
    
   setContainerMinHeight('.container .wrapper');

});
