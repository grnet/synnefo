$(document).ready(function() {
	if($('#stats').length > 0) {
		function syntaxHighlight(json) {
		    if (typeof json != 'string') {
		         json = JSON.stringify(json, undefined, 4); // the number of levels tah json has
		    }
		    json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
		    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
		        var cls = 'number';
		        if (/^"/.test(match)) {
		            if (/:$/.test(match)) {
		                cls = 'key';
		            } else {
		                cls = 'string';
		            }
		        } else if (/true|false/.test(match)) {
		            cls = 'boolean';
		        } else if (/null/.test(match)) {
		            cls = 'null';
		        }
		        return '<span class="' + cls + '">' + match + '</span>';
		    });
		}
		
			$.getJSON( "/stats/", function( data ) {			
				$( "<pre/>", {
				    "class": "stats",
				    html: syntaxHighlight(data)
			 	}).appendTo("#stats");
			});
		}

    $('.stats .custom-btn').click(function(e){
        var url = $(this).attr('href');
        var download = $(this).attr('download');
        var d = new Date();
        var month = d.getMonth()+1;
        var day = d.getDate();
        var output = '_' + d.getFullYear() + '_' +
                ((''+month).length<2 ? '0' : '') + month + '_' +
                    ((''+day).length<2 ? '0' : '') + day;
        var fName = download + output;
        $(this).attr('download', fName);
        var spinner = $(this).parents('section').find('.spinner');
        spinner.show(); 
        $.ajax({
            url: url,
            dataType: "json",
            success: function(data){
                spinner.hide();
            },
        })
    });

});
