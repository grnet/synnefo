// Array Remove - By John Resig (MIT Licensed)
Array.prototype.remove = function(from, to) {
  var rest = this.slice((to || from) + 1 || this.length);
  this.length = from < 0 ? this.length + from : from;
  return this.push.apply(this, rest);
};

function ResourcesModule(el, conf) {
    
    var defaults = {'page_limit': 5};
    this.conf = $.extend(defaults, conf);

    this.el = el;
    
    this.selected_category = window.location.hash.replace("#","");
    if (!this.selected_category) { this.selected_category = undefined };
    
    this.categories = this.el.find(".categories ul li");
    this.orig_categories = this.categories.clone();
        
    //this.update_page_objects();
    
    this.grid_height = 251;
    this.grid_width = 251;
    this.grid_gap = 22;

    var self = this;
    $(window).bind('hashchange', function() {
        self.selected_category = window.location.hash.substring(1);
        self.update_page_objects();
        self.update_selected_category();
    })

    self.update_page_objects();
    self.update_selected_category();
}

ResourcesModule.prototype.switch = function(hide, show) {
    var hide = $(hide), show = $(show);
    var toparent = hide.parent();
    var newshow = show.clone();
    toparent.append(newshow);
    hide.animate({top:"-249px"})
    newshow.animate({
                    top:"-249px"
                }, 
                {
                    complete:function(){
                        hide.remove();
                        newshow.css({top:0});
                }
    })
}


ResourcesModule.prototype.resources = function() {
    this._resources  = this.el.find(".resource-wrapper");
    return this._resources;
}

ResourcesModule.prototype.hide = function(q) {
    q.fadeOut(300);
}

ResourcesModule.prototype.animate_els = function(els) {
    $(el).css({ position:'absolute' });
    var left = i % 3 == 0 ? 0 : (i % 3) * (self.grid_width) + ((i % 3)-1) * self.grid_gap;

    var row = Math.floor(i/3);
    var top = row * (self.grid_gap + self.grid_height);

    $(el).animate({left: left}, { complete: function(){
        $(el).animate({top: top}, {complete: function(){
        
            self.el.height((self.grid_height + self.grid_gap) * (Math.floor(to_show.length/3) + 1));
        
        }});
    }});
     
    $(el).removeClass("hidden");
    $(el).show('slow');
}

ResourcesModule.prototype.update_selected_category = function() {
    if (!this.selected_category) {
        this.categories.removeClass("inactive").removeClass("active");
        this.categories.show();
        this.el.find(".categories a.clear").hide();
        return;
    }

    var to_hide = this.categories.filter("[data-id="+this.selected_category+"]");
    var to_show = this.categories.filter("[data-id!="+this.selected_category+"]");

    to_show.removeClass("active").addClass("inactive");
    to_hide.removeClass("inactive").addClass("active");
    this.el.find(".categories a.clear").show();
}

ResourcesModule.prototype.update_page_objects = function() {
    var to_show = this.resources().filter("[data-category="+this.selected_category+"]");
    var to_hide = this.resources().filter("[data-category!="+this.selected_category+"]");
        
    if (!this.selected_category) { to_show = this.resources(); }
    _.each(to_hide, function(el){
        $(el).hide('slow');
    });

    _.each(to_show, function(el, i){
         
        $(el).fadeIn(40);
    });
}

$(document).ready(function(){
    var rm = new ResourcesModule($("#resources-list"), {}, []);
    window.rm = rm;
})


