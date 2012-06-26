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

// fix for iPhone - iPad orientation bug 
var metas = document.getElementsByTagName('meta');
function resetViewport() {
    var i;
    if (navigator.userAgent.match(/iPhone/i)) {
  		for (i=0; i<metas.length; i++) {
    		if (metas[i].name == "viewport") {
      			metas[i].content = "width=device-width, minimum-scale=1.0, maximum-scale=1.0";
    		}
  		}
  	}
}
resetViewport();
    
window.onorientationchange = function() {
    resetViewport();
};
    
function gestureStart() {
  for (i=0; i<metas.length; i++) {
    if (metas[i].name == "viewport") {
      metas[i].content = "width=device-width, minimum-scale=0.25, maximum-scale=1.6";
    }
  }
}
document.addEventListener("gesturestart", gestureStart, false);

//end of fix

$(document).ready(function() {
	
	 
    setContainerMinHeight('.container .wrapper');
    
	
    $('.show-extra').click(function(e) {
        e.preventDefault();
        $(this).parents('.bg-wrap').find('.extra').slideToggle(600);
    });
    $('.hide-extra').click(function(e) {
        e.preventDefault();
        $(this).parents('.bg-wrap').find('.extra').slideUp(600);
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
    		backgroundColor: '#77C596',
    		color: '#fff'
    	}
    );
    
    $('.top-msg .error').parents('.top-msg').css(
    	{
    		backgroundColor: '#EF4F54',
    		color: '#fff'
    	}
    );
    
    
    $('.top-msg .warning').parents('.top-msg').css(
    	{
    		backgroundColor: '#F6921E',
    		color: '#fff'
    	}
    );
    
    $('.top-msg .info').parents('.top-msg').css(
    	{
    		backgroundColor: '#C3C3B9',
    		color: '#fff'
    	}
    );
    
    // clouds homepage animation
    $('#animation a').hover(
      function () {
      	
        $(this).animate({
           top: '+=-10'   
           }, 600, function() {
           	if ($(this).find('img').attr('src').indexOf("_top") == -1) {
           		var src = $(this).find('img').attr('src').replace('.png', '_top.png')
        		$(this).find('img').attr("src", src);
           	}

		});
        $(this).siblings('p').find('img').animate({
          width: '60%'       
        });
      }, 
      function () {

        $(this).animate({top: '0'}, 600, function() {
        	var src = $(this).find('img').attr('src').replace('_top.png', '.png')
       		$(this).find('img').attr("src", src);
		});
        $(this).siblings('p').find('img').animate({
          width: '65%'       
        });
      }
    );
    
    
    /*$('#animation a').hover(
      function () {
      	var src = $(this).find('img').attr('src').replace('.png', '_top.png')
        $(this).find('img').attr("src", src);
        $(this).animate({
           top: '+=-10'   
           }, 600, function() {
           		// action to do when animation is finished
		});
        $(this).siblings('p').find('img').animate({
          width: '60%'       
        });
      }, 
      function () {
      	
        $(this).animate({
         top: '0'   
            
        }, 600, function() {
           	var src = $(this).find('img').attr('src').replace('_top.png', '.png')
        	$(this).find('img').attr("src", src);
		});
        $(this).siblings('p').find('img').animate({
          width: '65%'       
        });
      }
    );*/
    
    
});

$(window).resize(function() {
    
   setContainerMinHeight('.container .wrapper');

});
