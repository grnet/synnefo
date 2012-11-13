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
		e.preventDefault(); 
		$(this).siblings('fieldset').find('input').val('');
		
		$(this).siblings('fieldset').find('.checkbox-widget.unlimited').addClass('checked');
		$(this).siblings('fieldset').find('.checkbox-widget.limited').removeClass('checked');
		$(this).siblings('fieldset').find('input[type="checkbox"].limited').removeAttr('checked');  
		$(this).siblings('fieldset').find('input[type="checkbox"].unlimited').attr('checked','checked');  
		$(this).siblings('fieldset').find('.double-checks input[type="text"]').hide();
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
		console.log($(this).attr('checked'));
		if ($(this).attr('checked')){
			$(this).siblings('input[type="text"]').toggle();
			$(this).siblings('input[type="text"]').focus();
		 	parentdiv = $(this).parents('.form-row').prev('.form-row');
		 	parentdiv.find('input[type="checkbox"].unlimited').removeAttr('checked');  
		 	parentdiv.find('.checkbox-widget').removeClass('checked');
		}
		
		 
	});
	
	$('.quotas-form input.unlimited').bind("changed", function(e){
		parentdiv = $(this).parents('.form-row').next('.form-row');
		if (parentdiv.find('.checkbox-widget').hasClass('checked')){
			parentdiv.find('.checkbox-widget').removeClass('checked');
			parentdiv.find('input[type="checkbox"].limited').removeAttr('checked');  
			parentdiv.find('input[type="text"]').val('');	
			parentdiv.find('input[type="text"]').hide();	
		}
		
		
		
	});

 
	 
	$('.quotas-form .quota input[type="text"]').change(function () {
	 	
	 	// get value from input
	 	var value = $(this).val();
	 	
	 	// replace , with .  and get number 
	 	value = value.replace(",",".");
	 	var num = parseFloat(value);
	 	var bytes = num;
	 	
	 	if ($(this).hasClass('dehumanize')){
	 		 // get suffix. 'i' renders it case insensitive
		 	var suf = value.match( new RegExp('GB|KB|MB|TB|bytes', 'i'));
		 	if (suf){
		 		
		 		suf = suf[0].toLowerCase(); 
		 	
			 	// transform to bytes
			 	switch (suf){
			 		case 'bytes': 
			 		  bytes = num*Math.pow(1024,0);
			 		  break;
			 		case 'byte': 
			 		  bytes = num*Math.pow(1024,0);
			 		  break;
			 		case 'kb':
			 		  bytes = num*Math.pow(1024,1);
			 		  break;
			 		case 'mb':
			 		  bytes = num*Math.pow(1024,2);
			 		  break;
			 		case 'gb':
			 		  bytes = num*Math.pow(1024,3);
			 		  break;
			 		case 'tb':
			 		  bytes = num*Math.pow(1024,4);
			 		  break;    
			 		default:
			 		  bytes = num; 
		 		}
		 	} else {
		 		 bytes = num; 
		 	}
	 	}
	 	
	 	
	 	var human_value = value;
	 	var machine_value = bytes;
	 	
	 	//get input name without _proxy
	 	hidden_name = $(this).attr('name').replace("_proxy","");
	 	var hidden_input = $("input[name='"+hidden_name+"']");
	 	
	 	hidden_input.val(bytes);
	 	
	 	$(this).parents('.form-row').find('.msg').html( human_value+ machine_value  ); 
	 });
	
});