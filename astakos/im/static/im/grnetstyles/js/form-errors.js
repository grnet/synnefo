(function($){

  $.fn.formErrors = function(options) {  
    return this.each(function() {
        var $this = $(this);
        var errors = $this.find(".errorlist");
        if (errors.length == 0) {
            return;
        }

        var el = $('<div class="form-error" />');
        errors.find("li").each(function(){
            el.html(el.html() + $(this).text() + "<br />");
        })

        $("body").append(el);
        var left = $this.offset().left + $this.width() - 20;
        var top = $this.offset().top + el.height()/2 - 2;

        el.css({left: left + "px", top: top + "px", width: 'auto'});
        errors.remove();
    });

  };
})( jQuery );
