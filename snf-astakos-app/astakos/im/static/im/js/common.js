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

function tableFixedCols(table, firstColWidth ){
	ColsNum = $('table th').size();
	var ColWidth = parseFloat( (100 - firstColWidth)/ColsNum ).toFixed(0);
	var ColWidthPercentage = ColWidth+'%';
	var firstColWidthPercentage = firstColWidth+'%';
	$('table th, table td').attr('width',ColWidthPercentage ); 
	$('table tr td:first-child, table tr th:first-child').attr('width',firstColWidthPercentage );
	
}

function addClassHover(hoverEl, applicableEl){ 
	$(hoverEl).hover(
      function () {
      	 
         $(applicableEl).addClass('red-border')
      }, 
      function () {
      	$(applicableEl).removeClass('red-border');
    
    });
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
    //tableFixedCols('my-projects', 25);
	
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
	
	$('.with-info select').attr('tabindex','1');
    $('.with-info select').dropkick();
    
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
    
    
    
    
    $(function() {		 
		$( "#id_start_date" ).datepicker({
			minDate: 0,
			defaultDate: "+0", 
            dateFormat: "yy-mm-dd",
            onSelect: function( selectedDate ) {
                $( "#id_end_date" ).datepicker( "option", "minDate", selectedDate );
            }
        });
        
        $( "#id_end_date" ).datepicker({
        	defaultDate: "+3w", 
            dateFormat: "yy-mm-dd",
            onSelect: function( selectedDate ) {
                $( "#id_start_date" ).datepicker( "option", "maxDate", selectedDate );
            }
        });
	});
	
	 
	
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
	



 
	$("input.leave, input.join").click(function (e) {
        e.preventDefault();
        var form = $(this).parents('form');
        var dialog = $(this).parents('.msg-wrap').find('.dialog');

		$('.dialog').hide();
    if ($(this).parents('.form-actions').hasClass('inactive')) {
      return false;
    }
		$(this).parents('.msg-wrap').find('.dialog').show();
        var offset = dialog.offset();

        if (offset.left <= 10) {
          dialog.css({'left': '10px'})
        }
        if (offset.top <= 10) {
          dialog.css({'top': '10px'})
        }

        if (dialog.find('textarea').length > 0) {
          dialog.find('textarea').val('');
          dialog.find('textarea').focus();
        }

		return false;      
		
    });
    
     $('.msg-wrap .no').click( function(e){
    		e.preventDefault();
    		$(this).parents('.dialog').hide();
        e.stopPropagation();
    	})

      $(document).click(function() {
        $('.msg-wrap .dialog').hide();
      });

     
    $('.msg-wrap .yes').click( function(e){
		e.preventDefault();
        var dialog = $(this).parents('.msg-wrap').find('.dialog');
        var form = $(this).parents('.msg-wrap').find('form');
        var fields = dialog.find('input, textarea')
        
        var toremove = [];
        fields.each(function(){
          var f = $(this).clone();
          f.hide();
          form.append(f);
          f.val($(this).val());
          toremove.push(f);
        });
        
        form.submit();
	})
    
    $('.hidden-submit input[readonly!="True"]').focus(function () {
         $('.hidden-submit .form-row.submit').slideDown(500);
    });
    
    
    
   
      
    
    setTimeout(function() {
      if ($('input#id_username').val()){ 
      	$('input#id_username').siblings('label').css('opacity','0');
      };
      if ($('input#id_password').val()){ 
      	$('input#id_password').siblings('label').css('opacity','0');
      }
	}, 100);
	
	
	
	// landing-page initialization
    if ($('.landing-page').length > 0) {
      var wrapper = $(".landing-page");
      var services = wrapper.find(".landing-service");
      services.hover(function(e) {
        var cls, service_cls, cloudbar_li, offset, positionX;
        cls = _.filter($(this).attr("class").split(" "), function(cls) {
          return cls.indexOf("service-") == 0
        });
        if (!cls.length) { return }
        service_cls = $.trim(cls[0]);
        extra = 0;
        if (service_cls == 'service-astakos') {
          cloudbar_li = $(".cloudbar .profile");
          extra = 50;
        } else {
          cloudbar_li = $(".cloudbar ul.services li." + service_cls);
          if (cloudbar_li.index() != 0) {
            extra = 20;
          }
        }
      	offset = cloudbar_li.offset();
        if (!offset) { return }
      	positionX = offset.left + extra;
      	$('#hand').css('left',positionX + 'px');
        $('#hand').show();
      }, function (e) {
      	$('#hand').hide();
      });
    }

    $('.pagination a.disabled').click(function(e){
    	e.preventDefault();
    });
	  
	// fix for recaptcha fields
	$('#okeanos_recaptcha').parents('.form-row').find('.extra-img').hide();	  
   
   check_form_actions_inactive();  
/* project members page js */	 
function check_form_actions_inactive(){
   if ( $('#members-table tbody td.check input:checked').length >0 ) {
    $('.projects .form-actions').removeClass('inactive');
  } else {
    $('.projects .form-actions').addClass('inactive');
  }

  // updating form data
  var forms = $("form.link-like:has('input.members-batch-action')");
  forms.each(function(index, form){
    var member_ids, checked;
    form = $(form);
    form.find("input.member-option").remove();
    checked = $('#members-table tbody td.check input:checked');
    member_ids = _.map(checked, function(el) {
      return parseInt($(el).val());
    });
    
    _.each(member_ids, function(id) {
      var newel;
      newel = $("<input name='members' class='member-option' type='hidden' value='"+id+"'>");
      form.append(newel);
    });
  })
}

$('#members-table td.email').click(function(e){
  var that = $(this).parent('tr').find('.check').find('input[type="checkbox"]')
  if(that.is(":checked")){
    that.removeAttr('checked');
  } else {
    that.attr('checked', 'checked');
  }
  check_form_actions_inactive();

})




$('#members-table tr th.check input').click(function(e){
  if($(this).is(":checked")){
    $('#members-table tbody td.check input').attr('checked', 'checked');
  } else {
    $('#members-table tbody td.check input').removeAttr('checked');
  } 
});

$('#members-table tr .check input').click(function(e){
  check_form_actions_inactive()
});

/* end of project members page js */



	    
});
	
$(window).resize(function() {
    
   setContainerMinHeight('.container .wrapper');
    

});
