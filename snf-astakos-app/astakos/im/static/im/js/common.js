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


//equal heights
 
(function($) {
	$.fn.equalHeights = function(minHeight, maxHeight) {
		tallest = (minHeight) ? minHeight : 0;
		this.each(function() {
			if($(this).height() > tallest) {
				tallest = $(this).height();
			}
		});
		if((maxHeight) && tallest > maxHeight) tallest = maxHeight;
		return this.each(function() {
			$(this).height(tallest);
		});
	}
})(jQuery);



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

if (navigator.userAgent.match(/iPhone/i)) {
	document.addEventListener("gesturestart", gestureStart, false);
}
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
    
    
     
	$('select').dropkick();
 
    
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
        }, 600);
      }, 
      function () {

        $(this).animate({top: '0'}, 600, function() {
        	var src = $(this).find('img').attr('src').replace('_top.png', '.png')
       		$(this).find('img').attr("src", src);
		});
        $(this).siblings('p').find('img').animate({
          width: '65%'       
        },600);
      }
    );
    
    
   
    
    
    if ($('.widjets'.length > 0)) {
		$('.widjets li div').equalHeights();
	}
    
    $(function() {
    	if($("#id_issue_date").length > 0 ){
			$( "#id_issue_date" ).datepicker({
				defaultDate: "+0", 
				dateFormat: "yy-mm-dd",
				onSelect: function( selectedDate ) {
					$( "#id_expiration_date" ).datepicker( "option", "minDate", selectedDate );
				}
			});
			$( "#id_expiration_date" ).datepicker({
				defaultDate: "+1w", 
				dateFormat: "yy-mm-dd",
				onSelect: function( selectedDate ) {
					$( "#id_issue_date" ).datepicker( "option", "maxDate", selectedDate );
				}
			});
		}
	});
	
	
	$(".table_sorting").tablesorter(); 
	
	$('table .more-info').click(function(e){
		e.preventDefault();
		$(this).toggleClass('open');
		$(this).parents('tr').next('tr').toggle();
		check_table_info();
	})
	
	function check_table_info() {
	   if ($('table .more-info').hasClass('open')){
	   		$(this).text('[- Less Info]')
	   } else {
	   		$(this).text('[+ More Info]')
	   }
	}
});

$(window).resize(function() {
    
   setContainerMinHeight('.container .wrapper');
   if ($('.widjets').length > 0) {
		$('.widjets  li div').equalHeights();
	}

}); 