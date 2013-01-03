function group_form_show_resources(el){
	
	el.addClass('selected');
	var id = el.attr('id');
	$('.quotas-form .group').each(function() {
		if( $(this).hasClass(id) ) {
			 
			$(this).appendTo('.visible');
			$(this).show('slow');
			$(this).find('input')[0].focus()
		}
	});
	if ($('.quotas-form .with-info .with-errors input[type="text"]')){
		$(this)[0].focus();	
	}

}


function bytesToSize2(bytes) {
    var sizes = [ 'n/a', 'bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    var i = +Math.floor(Math.log(bytes) / Math.log(1024));
    return  (bytes / Math.pow(1024, i)).toFixed( 0 ) + sizes[ isNaN( bytes ) ? 0 : i+1 ];
}

$(document).ready(function() {

	
	
	// ugly fix to transfer data easily 
	$('.with-info input[name^="is_selected_"]').each(function() {
		$(this).parents('.form-row').hide();
	});
    
	$('.quotas-form ul li a').click(function(e){
		
		// check the hidden input field
		$(this).siblings('input[type="hidden"]').val("1");
		
		// get the hidden input field without the proxy
		// and check the python form field
	 	hidden_name = $(this).siblings('input[type="hidden"]').attr('name').replace("proxy_","");
	 	$("input[name='"+hidden_name+"']").val("1");  
		
 		// prevent extra actions if it is checked		 
		if ( $(this).hasClass('selected')){
			e.preventDefault();
		} else {
			
			// show the relevant fieldsets
			group_form_show_resources($(this));
		}   
	});
	
	 
	
	
	 
	
	$('.quotas-form .group .delete').click(function(e){
		
		e.preventDefault(); 
		
		// clear form fields
		$(this).siblings('fieldset').find('input').val('');
		
		// clear errors
		$(this).siblings('fieldset').find('.form-row').removeClass('with-errors');
		 
		// hide relevant fieldset 
		$(this).parents('.group').hide('slow', function() {
		    $(this).appendTo('.not-visible');	
		});
		
		group_class = $(this).parents('.group').attr('class').replace('group ', '');
		
		// unselect group icon
		$('.quotas-form ul li a').each(function() {
			if($(this).attr('id')==group_class) {
				$(this).removeClass('selected');
				$(this).siblings('input[type="hidden"]').val('0');
				
				// get the hidden input field without the proxy
				// and check the python form field
			 	hidden_name = $(this).siblings('input[type="hidden"]').attr('name').replace("proxy_","");
			 	$("input[name='"+hidden_name+"']").val('0');  
				
			}
		}); 
		
		// clear hidden fields
		$(this).siblings('fieldset').find('input[type="text"]').each(function() {
			hidden_name = $(this).attr('name').replace("_proxy","");
	 		hidden_input = $("input[name='"+hidden_name+"']");
	 		hidden_input.val('');
		});
		 
		 
	});
	 	 
	// if you fill _proxy fields do stuff 
	$('.quotas-form .quota input[type="text"]').change(function () {
	 	
	 	if ( $('#icons span.info').hasClass('error-msg')){
			$('#icons span.info').find('span').html('Here you add resources to your Project. Each resource you specify here, will be granted to *EACH* user of this Project. So the total resources will be: &lt;Total number of members&gt; * &lt;amount_of_resource&gt; for each resource.');
	 	}
	 	 
	 	// get value from input
	 	var value = $(this).val();
	 	
	 	//get input name without _proxy
	 	hidden_name = $(this).attr('name').replace("_proxy","");
	 	var hidden_input = $("input[name='"+hidden_name+"']");
	 	
	 	if (value) {
		 	// actions for humanize fields
		 	if ($(this).hasClass('dehumanize')){
		 		
		 		var flag = 0;

				// check if the value is not float
		 		var num_float = parseFloat(value);
		 		num_float= String(num_float);

		 		if (num_float.indexOf(".") == 1){
		 			flag = 1 ; 
		 			msg="Please enter an integer";
		 		} else {
		 			var num = parseInt(value);
					if ( num == '0' ) { 
						flag = 1 ; msg="zero"
					} else {
						if ( value && !num ) { flag = 1 ; msg="Invalid format. Try something like 10GB, 2MB etc"}
				 	
					 	var bytes = num;
				 		
						// remove any numbers and get suffix		 		
				 		var suffix = value.replace( num, '');
		
				 		 // validate suffix. 'i' renders it case insensitive
					 	var suf = suffix.match( new RegExp('^(GB|KB|MB|TB|bytes|G|K|M|T|byte)$', 'i'));
					 	if (suf){
					 		
					 		suf = suf[0].toLowerCase(); 
					 		suf = suf.substr(0,1);
					 	
						 	// transform to bytes
						 	switch (suf){
						 		case 'b': 
						 		  bytes = num*Math.pow(1024,0);
						 		  break;
						 		case 'k':
						 		  bytes = num*Math.pow(1024,1);
						 		  break;
						 		case 'm':
						 		  bytes = num*Math.pow(1024,2);
						 		  break;
						 		case 'g':
						 		  bytes = num*Math.pow(1024,3);
						 		  break;
						 		case 't':
						 		  bytes = num*Math.pow(1024,4);
						 		  break;    
						 		default:
						 		  bytes = num; 
					 		}
					 	} else {
					 		if (num) {
					 		 	flag = 1;
					 		 	msg ="You must specify correct units" 
					 		}  
					 		 
					 	}
					}
				 	
		 			
		 			
		 		}
		 		
		 		 
			 	
			 	
			 	if ( flag == '1' ){ 
			 		$(this).parents('.form-row').addClass('with-errors');
			 		$(this).parents('.form-row').find('.error-msg').html(msg);
			 		bytes = value;
			 		$(this).focus();
			 		
			 		 
			 	} else {
			 		$(this).parents('.form-row').removeClass('with-errors');
			 	}
			 	
			 	hidden_input.val(bytes);
			 	
			 	
		 	}
		 	 
		 	// validation actions for int fields
		 	else {
	
		 		var is_int = value.match (new RegExp('^[0-9]*$'));
		 		if ( !is_int ){ 
		 			$(this).parents('.form-row').find('.error-msg').html('Enter a positive integer');
			 		$(this).parents('.form-row').addClass('with-errors');
			 		 
			 	} else {
			 		if ( value == '0'){
			 			$(this).parents('.form-row').find('.error-msg').html('Ensure this value is greater than or equal to 1');
			 			$(this).parents('.form-row').addClass('with-errors');
			 		}else {
			 			$(this).parents('.form-row').removeClass('with-errors');
			 		}
			 		
			 		
			 	}
			 	hidden_input.val(value);
	
		 	}
	 	
	 	} else {
	 		hidden_input.removeAttr('value');
	 	}
	 	$('#icons span.info').removeClass('error-msg');
	 	
	 });
	 
	
	// if hidden checkboxes are checked, the right group is selected 
	$('.with-info input[name^="is_selected_"]').each(function() {
		if ( ($(this).val()) == 1 ){
			
			// get hidden input name
			hidden_name = $(this).attr('name');
			$("input[name='proxy_"+hidden_name+"']").val("1"); 
			
			// pretend to check the ul li a
			// show the relevant fieldsets
			var mock_a = $("input[name='proxy_"+hidden_name+"']").siblings('a');
			group_form_show_resources(mock_a);
			 
		}
	}); 
	
	
	/*
	// if input_uplimit fields are filled,
	// fill the _uplimit_proxy ones
	 
	$('.with-info input[name$="_uplimit"]').each(function() {
		if ($(this).val()){
			
			// get value from input
	 		var value = $(this).val();
			
			
			// get hidden input name
			hidden_name = $(this).attr('name');
			var field = $("input[name='"+hidden_name+"_proxy']"); 
			
			
			if ( (field.hasClass('dehumanize')) && !($(this).parents('.form-row').hasClass('with-errors'))) {
				// for dehumanize fields transform bytes to KB, MB, etc
				// unless there is an error
				field.val(bytesToSize2(value))
			} else {
				// else just return the value
				field.val(value);	
			}
			
			var group_class = field.parents('div[class^="group"]').attr('class').replace('group ', '');
			
			 
			 
			
			// select group icon
			$('.quotas-form ul li a').each(function() {
				
				if($(this).attr('id') == group_class) {
					$(this).addClass('selected');
					$(this).siblings('input[type="hidden"]').attr('checked', 'checked');
					
					// get the hidden input field without the proxy
					// and check the python form field
				 	hidden_name = $(this).siblings('input[type="hidden"]').attr('name').replace("proxy_","");
				 	$("input[name='"+hidden_name+"']").attr('checked', 'checked');  
				 	
				 	group_form_show_resources($(this));
					
				}
			}); 
			
		
			
			// if the field has class error, transfer error to the proxy fields
			if ( $(this).parents('.form-row').hasClass('with-errors') ) {
				field.parents('.form-row').addClass('with-errors');
			}
			
			 
		}
	});*/
	// if input_uplimit fields are filled,
	// fill the _uplimit_proxy ones
	 
	$('.group input[name$="_uplimit_proxy"]').each(function() {
		if ($(this).val()){
			
			// get value from input
	 		var value = $(this).val();
			
			
			// get hidden input name
			hidden_name = $(this).attr('name');
			hidden_field_name = hidden_name.replace("_proxy","");
			$("input[name='"+hidden_field_name+"']").val(value);
			var field = $(this); 
			
			
			if ( (field.hasClass('dehumanize')) && !($(this).parents('.form-row').hasClass('with-errors'))) {
				// for dehumanize fields transform bytes to KB, MB, etc
				// unless there is an error
				field.val(bytesToSize2(value))
			} else {
				// else just return the value
				field.val(value);	
			}
			
			var group_class = field.parents('div[class^="group"]').attr('class').replace('group ', '');
			
			 
			 
			
			// select group icon
			$('.quotas-form ul li a').each(function() {
				
				if($(this).attr('id') == group_class) {
					$(this).addClass('selected');
					$(this).siblings('input[type="hidden"]').val("1");
					
					// get the hidden input field without the proxy
					// and check the python form field
				 	hidden_name = $(this).siblings('input[type="hidden"]').attr('name').replace("proxy_","");
				 	$("input[name='"+hidden_name+"']").val("1");  
				 	
				 	group_form_show_resources($(this));
					
				}
			}); 
			
		
			
			// if the field has class error, transfer error to the proxy fields
			if ( $(this).parents('.form-row').hasClass('with-errors') ) {
				field.parents('.form-row').addClass('with-errors');
			}
			
			 
		}
	});  
	
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
			$('#icons span.info').find('span').html('You must fill in at least one resource');
			return false;
			
		}
	});


	
	
	
});