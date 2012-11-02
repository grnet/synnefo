(function($){
  
  $.fn.formCheckBoxes = function(options) {
    
    return this.each(function() {
      // process checkboxes
      var $this = $(this);
      var el = $('<a class="checkbox-widget" href="javascript:void(0)"/>');
      var form = $this.closest(".form-row");
	  var className = $this.attr('class');

      // add class to identify form rows which contain a checkbox
      form.addClass("with-checkbox");
      
      if ($this.prev().length > 0) {
        var lbl = $this.prev()[0];
        if (lbl.nodeName == "LABEL" || lbl.nodeName == "label") {
            $(lbl).addClass("checkbox-label");

            $(lbl).click(function(e){
                var src = e.srcElement.nodeName;
                if (src == "LABEL" || src == "label") {
                    el.toggleClass("checked");
					
                };
                if ($this.attr('checked')=='checked') {
					($this.removeAttr('checked'))
				} else {
					$this.attr('checked','checked')
				}
            })
        }
      }
      $this.hide();
      
      if ($this.attr('checked')) {
        el.addClass("checked");  
        
      }

	  el.addClass(className);	
		
      el.click(function() {
        el.toggleClass("checked");
        $this.attr('checked', el.hasClass("checked"));
      });
      
      el.keypress(function(e){
      	
      	if (e.keyCode == 0 || e.keyCode == 32){
      		e.preventDefault();
      		el.toggleClass("checked");
        	$this.attr('checked', el.hasClass("checked"));
      	}
      })

      $this.prev('label').before(el);
    });


  }

  $.fn.formErrors = function(options) {  
    return this.each(function() {
        var $this = $(this);

        // does the field has any errors ?
        var errors = $this.find(".errorlist");
        if (errors.length == 0) {
            return;
        }
        
        // create the custom error message block
        // and copy the contents of the original
        // error list
        var el = $('<div class="form-error" />');
        errors.find("li").each(function(){
            el.html(el.html() + $(this).text() + "<br />");
        })
        
        var formel = $this.find("input, select");
        var lbl = $this.find("label");
        var form = $this.closest("form");


        // append element on form row 
        // and apply the appropriate styles
        formel.closest(".form-row").append(el);
        errors.remove();
        var left = formel.width();
        var top = formel.height();
        var marginleft = lbl.width();
        
        // identify the position
        // forms with innerlbales class
        // display the label within the input fields
        if ($(form).hasClass("innerlabels")) {
            marginleft = 0;
        }
        
        var styles = {
            left: left + "px", 
            top: top + "px", 
            width: formel.outerWidth() - 10,
            marginLeft: marginleft,
            marginBottom: 5
        }
        
        if (formel.attr("type") != "checkbox") {
            el.css(styles);
        } else {
            el.css("margin-top", "5px");
        }
    });

  };
})( jQuery );

