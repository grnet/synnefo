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
    
     
	$('select.dropkicked').dropkick({
		change: function (value, label) {
		    $(this).parents('form').submit();
		    
		}
	});
    
    $('.top-msg .success').parents('.top-msg').addClass('success');
    $('.top-msg .error').parents('.top-msg').addClass('error');
    $('.top-msg .warning').parents('.top-msg').addClass('warning');
    $('.top-msg .info').parents('.top-msg').addClass('info');
    
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
    
    
   
    
    
    ///if ($('.widjets'.length > 0)) {
		///$('.widjets li div .txt').equalHeights();
	///}
    
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
		
		if($("#id_issue_date_demo").length > 0 ){
			$( "#id_issue_date_demo" ).datepicker({
				defaultDate: "+0", 
				dateFormat: "yy-mm-dd",
				onSelect: function( selectedDate ) {
					$( "#id_expiration_date_demo" ).datepicker( "option", "minDate", selectedDate );
				}
			});
			$( "#id_expiration_date_demo" ).datepicker({
				defaultDate: "+1w", 
				dateFormat: "yy-mm-dd",
				onSelect: function( selectedDate ) {
					$( "#id_issue_date_demo" ).datepicker( "option", "maxDate", selectedDate );
				}
			});
		}
		$( "#id_start_date" ).datepicker({
            dateFormat: "yy-mm-dd",
            onSelect: function( selectedDate ) {
                $( "#id_start_date" ).datepicker( "option", "maxDate", selectedDate );
            }
        });
        
        $( "#id_end_date" ).datepicker({
            dateFormat: "yy-mm-dd",
            onSelect: function( selectedDate ) {
                $( "#id_end_date" ).datepicker( "option", "maxDate", selectedDate );
            }
        });
	});
	
	
	$(".table_sorting").tablesorter(); 
	
	$('table .more-info').click(function(e){
		e.preventDefault();
		$(this).toggleClass('open');
		if ($(this).hasClass('open')){
			$(this).html('- less info ')
		} else {
			$(this).html('+ more info ')
		}
		$(this).parents('tr').next('tr').toggle();
		 
	});
	
	$('.projects .details .edit').click( function(e){
		e.preventDefault();
		$(this).parents('.details').children('.data').hide();
		$(this).parents('.details').children('.editable').slideDown(500, 'linear');
		$(this).hide();
	});
	
	$('.editable .form-row').each(function() {
			if ( $(this).hasClass('with-errors') ){
				$('.editable').show();
				$('.projects .details a.edit, .projects .details .data').hide();
				
			}
		});
	
	$('.widjet-x').click(function(e){
		e.preventDefault();
		$(this).siblings('ul').hide('slow');
		$(this).hide();
	})

	// todo den doulevei
	$('#group_create_form').submit(function(){
		if ($('.quotas-form .group .form-row.with-errors').length>0 ){
			return false;
		}
		var flag = 0;
		$('.quotas-form .group input[type="text"]').each(function() {
			// get value from input
	 		var value = $(this).val();
			if (value){
				flag =1;
			}
		});
		if (flag =='0') {
			$('#icons span.info').addClass('error-msg');
			return false;
			
		}
	});
	
	
	
	$("input.leave, input.join").click(function () {
		$(this).parents('.msg-wrap').find('.dialog').show();
		return false;      
		
    });
    
     $('.msg-wrap .no').click( function(e){
		e.preventDefault();
		$(this).parents('.dialog').hide();
	})
    
    $('.msg-wrap .yes').click( function(e){
		e.preventDefault();
		$(this).parents('.dialog').siblings('form').submit();
	})
    
    $('.hidden-submit input[readonly!="True"]').focus(function () {
         $('.hidden-submit .form-row.submit').show(500);
    });
    
     $('.auth_methods').find('li>a').click(function(e){
     	e.preventDefault();
     	$(this).siblings('.wrap').toggle('slow');
     	$(this).toggleClass('up');
     });
     
     $('.auth_methods a.red').click(function(e){
     	e.preventDefault();
     	$(this).siblings('.dialog').show();
     })
     
      
     $('.auth_methods .dialog .no').click( function(e){	 
     	e.preventDefault();
     	console.log($(this));
     	$(this).parents('.dialog').hide();
     })
    
    setTimeout(function() {
      if ($('input#id_username').val()){ 
      	$('input#id_username').siblings('label').css('opacity','0');
      };
      if ($('input#id_password').val()){ 
      	$('input#id_password').siblings('label').css('opacity','0');
      }
	}, 100);
    
    
});
	
$(window).resize(function() {
    
   setContainerMinHeight('.container .wrapper');
    

});