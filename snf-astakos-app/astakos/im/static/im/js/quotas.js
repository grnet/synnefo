$(document).ready(function() {

	// quota form actions
	$('.quotas-form ul li a').click(function(e){
		//e.preventDefault();
		if ( !$(this).hasClass('selected')){
			$(this).addClass('selected');
			var id = $(this).attr('id');
			$('.quotas-form .group').each(function() {
				if( $(this).hasClass(id) ) {
					$(this).appendTo('.foo');
					$(this).show('slow');
					$(this).find('input')[0].focus();
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
		$(this).parents('.group').appendTo('.not-foo');	
		$(this).parents('.group').hide('slow');
		groupClass = $(this).parents('.group').attr('class').replace('group ', '');
		$('.quotas-form ul li a').each(function() {
			if($(this).attr('id')==groupClass) {
				$(this).removeClass('selected');
			}
		}); 
		
		 
		 
	});
	 
		
	$('.quotas-form .checkbox-widget.limited').click(function(e){
		e.preventDefault();
		$(this).siblings('input[type="text"]').toggleClass('hideshow');
		$(this).siblings('input[type="text"]').focus();
	 	parentdiv = $(this).parents('.form-row').prev('.form-row');
	 	parentdiv.find('input[type="checkbox"].unlimited').removeAttr('checked');  
	 	parentdiv.find('.checkbox-widget').removeClass('checked');
	 		
	 	
	});
	
	$('.quotas-form .checkbox-widget.unlimited').click(function(e){
		parentdiv = $(this).parents('.form-row').next('.form-row');
		parentdiv.find('.checkbox-widget').removeClass('checked');
		parentdiv.find('input[type="checkbox"].limited').removeAttr('checked');  
		parentdiv.find('input[type="text"]').val('');	
		parentdiv.find('input[type="text"]').removeClass('hideshow');	
		
		
	})
	
});