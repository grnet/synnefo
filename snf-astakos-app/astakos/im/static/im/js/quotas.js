$(document).ready(function() {

	$('.quotas-form ul li a').click(function(e){
		$(this).siblings('input[type="hidden"]').val('1');
		if ( $(this).hasClass('selected')){
			e.preventDefault();
		}
		if ( !$(this).hasClass('selected')){
			$(this).addClass('selected');
			var id = $(this).attr('id');
			$('.quotas-form .group').each(function() {
				if( $(this).hasClass(id) ) {
					$(this).appendTo('.foo');
					$(this).show('slow');
					$(this).find('input')[0].focus()
				}
			});
		}   
	});
	
	$('.quotas-form .group .delete').click(function(e){
		 
		$(this).siblings('fieldset').find('input').val('');
		
		$(this).siblings('fieldset').find('.checkbox-widget.unlimited').addClass('checked');
		$(this).siblings('fieldset').find('.checkbox-widget.limited').removeClass('checked');
		$(this).siblings('fieldset').find('input[type="checkbox"].limited').removeAttr('checked');  
		$(this).siblings('fieldset').find('input[type="checkbox"].unlimited').attr('checked','checked');  
		$(this).siblings('fieldset').find('.double-checks input[type="text"]').removeClass('hideshow');
		$(this).parents('.group').hide('slow', function() {
		    $(this).appendTo('.not-foo');	
		});
		groupClass = $(this).parents('.group').attr('class').replace('group ', '');
		$('.quotas-form ul li a').each(function() {
			if($(this).attr('id')==groupClass) {
				$(this).removeClass('selected');
				$(this).siblings('input[type="hidden"]').val('0');
			}
		}); 
		 
		 
	});
	 
		
	$('.quotas-form input.limited').bind("changed", function(e){
		$(this).siblings('input[type="text"]').toggle();
		$(this).siblings('input[type="text"]').focus();
	 	parentdiv = $(this).parents('.form-row').prev('.form-row');
	 	parentdiv.find('input[type="checkbox"].unlimited').removeAttr('checked');  
	 	parentdiv.find('.checkbox-widget').removeClass('checked');
		 
	});
	
	$('.quotas-form input.unlimited').bind("changed", function(e){
		parentdiv = $(this).parents('.form-row').next('.form-row');
		if (parentdiv.find('.checkbox-widget').hasClass('checked')){
			parentdiv.find('.checkbox-widget').removeClass('checked');
			parentdiv.find('input[type="checkbox"].limited').removeAttr('checked');  
			parentdiv.find('input[type="text"]').val('');	
			parentdiv.find('input[type="text"]').hide();	
		}
		
		
		
	})
	
	//$('input:radio').uniform();
	$('.radio .radio span').each(function(index) {	    
		if ($(this).hasClass('checked')){
			alert('f');
		}
	});

	
	
});