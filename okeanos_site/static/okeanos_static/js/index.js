(function() {
    
    var menu = function(el) {
        this.el = el;
        var menu = this;
        var resumeVideo = false;
        var player = window.player;

        this.show_menu = function (event) {
            $("#video iframe").attr("src", "");
            var link = $(event.currentTarget);
            var id = link.attr("href");
            var li = $(link.parent());
            
            $(".page").hide(0);
            $(id).show(0);

            $("li").removeClass("selected");
            $("li").removeClass("current");
            $("li .close-button").css("visibility", "hidden");
                
            if (id !== "#video") {
                li.addClass("selected");
                li.addClass("current");
                $(link.parent()).find(".close-button").css("visibility", "visible");
                $(".inner-bottom").addClass("in-page");
            } else {
                $(".inner-bottom").removeClass("in-page");
            }
            event.preventDefault();
            //location.hash = id;
        }
        
        $(".page").hide();
        $("#video").show();
        $(".menu a").click(this.show_menu);
        
    }

    $(document).ready(function() {
        if ($.cookie('X-Auth-Token') != null) {
            $(".testuser").show();
            $(".banner-coming").hide();
        }

        window.menu = new menu($(".menu"));
        window.player = document.getElementById('player');

        var validHashes = ["#why","#who","#what"];
        var hash = location.hash.toString();

        if ($.inArray(location.hash.toString(), validHashes) >= 0) {
            var selector = "a.page-link[href=" + hash + "]";
            link = $("a.page-link[href=" + hash + "]");
            link.trigger("click");
        }

        $(".page-link").mousedown(function() {
            $(this).addClass("click");
        });
        $(".page-link").mouseup(function() {
            $(this).removeClass("click");
        });
    });
})();
