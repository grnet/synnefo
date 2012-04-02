(function($){
  
  $.fn.formCheckBoxes = function(options) {
    
    return this.each(function() {
      var $this = $(this);
      var el = $('<span class="checkbox-widget" />');
      
      if ($this.prev().length > 0) {
        var lbl = $this.prev()[0];
        if (lbl.nodeName == "LABEL" || lbl.nodeName == "label") {
            $(lbl).addClass("checkbox-label");

            $(lbl).click(function(){
                el.toggleClass("checked");
            })
        }
      }
      $this.hide();
      
      if ($this.is("checked")) {
        el.addClass("checked");  
      }

      el.click(function() {
        el.toggleClass("checked");
        $this.attr('checked', el.hasClass("checked"));
      })

      $this.after(el);
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
