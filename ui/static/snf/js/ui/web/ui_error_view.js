;(function(root){

    // root
    var root = root;
    
    // setup namepsaces
    var snf = root.synnefo = root.synnefo || {};
    var models = snf.models = snf.models || {}
    var storage = snf.storage = snf.storage || {};
    var ui = snf.ui = snf.ui || {};
    var util = snf.util = snf.util || {};

    var views = snf.views = snf.views || {}

    // shortcuts
    var bb = root.Backbone;

    views.ErrorView = views.Overlay.extend({
        
        view_id: "error_view",
        content_selector: "#error-overlay-content",
        css_class: 'overlay-error',
        overlay_id: "error-overlay",
        error_stack: {},

        initialize: function() {
            views.ErrorView.__super__.initialize.apply(this, arguments);
            var self = this;

            this.error_state = false;

            this.$(".actions .show-details, .actions .hide-details").click(function() {
                self.$(".error-details").toggle();
                self.$(".show-details").toggle();
                self.$(".hide-details").toggle();
            });

            this.$(".key.details").click(function() {
                $(this).next().toggle();
                if (!$(this).next().is(":visible")) {
                    $(this).addClass("expand");
                } else {
                    $(this).removeClass("expand");
                }
            })

            this.$(".actions .report-error").click(_.bind(function() {
                this.report_error();
            }, this));

            this.$(".actions .hide-details").hide();

            this.$(".reload-app").click(function(){
                window.location.reload(true);
            })
        },

        error_object: function() {
            return {ns:this.ns, code:this.code, message:this.message, details:this.details};
        },

        report_error: function() {
            this.feedback_view = this.feedback_view || ui.main.feedback_view;
            this.hide(false);
            window.setTimeout(_.bind(function() {
                this.feedback_view.show(this.get_report_message(), true, {error: this.error_object()});
            }, this), 400);
        },

        get_report_message: function() {
            var fdb_msg =   "Error report\n" +
                "-------------------" + "\n" +
                "Code: " + this.code + "\n" + 
                "Type: " + this.type + "\n" +
                "Message: " + this.message + "\n" +
                "Module: " + this.ns + "\n" +
                "Details: " + this.details + "\n\n" +
                "Please describe the actions that triggered the error:\n"
            
            return fdb_msg;
        },
        
        show_error: function(ns, code, message, type, details, error_options) {
            if (!snf.api.error_state) { this.error_stack = {} };
                
            if (error_options.fatal_error) {
                snf.api.error_state = true;
                snf.api.trigger("change:error_state", true);
            } else {
                snf.api.error_state = false;
                snf.api.trigger("change:error_state", false);
            }

            var error_entry = [ns, code, message, type, details, error_options];
            this.error_stack[new Date()] = error_entry;
            this.display_error.apply(this, error_entry);
            this.show();
        },

        display_error: function(ns, code, message, type, details, error_options) {
            this.error_options = {'allow_report': true, 'allow_reload': true, 'extra_details': {}, 'non_critical': false, 'allow_details': false };

            if (error_options) {
                this.error_options = _.extend(this.error_options, error_options);
            }

            this.code = code;
            this.ns = ns;
            this.type = type;
            this.details = details ? (details.toString ? details.toString() : details) : undefined;
            this.message = message;

            this.update_details();
            
            if (error_options.non_critical) {
                this.el.addClass("non-critical");
                this.error_options.allow_details = false;
            } else {
                this.el.removeClass("non-critical");
                this.error_options.allow_details = true;
            }
            
            //if (APP_DEBUG) {
                //this.error_options.allow_details = true;
            //}

            this.$(".actions .show-details").click();
            this.$(".key.details").click();
            this.$(".error-more-details").hide();
        },

        update_details: function() {
            var title = "Application error";
            if (this.ns && this.type) {
                title = this.title || this.type + " Error";
            }
            this.$(".header .title").text(title);
            this.$(".error-code").text(this.code || "");
            this.$(".error-type").text(this.type || "");
            this.$(".error-module").text(this.ns || "");
            this.$(".message p").text(this.message || "");
            this.$(".error-more-details p").html(this.details || "no info");

            this.$(".extra-details").remove();
            _.each(this.error_options.extra_details, function(value, key){
                var opt = $(('<span class="extra-details key">{0}</span>' +
                            '<span class="extra-details value">{1}</span>').format(key, value))
                this.$(".value.error-type").after(opt);
            })

        },

        beforeOpen: function() {
            this.$(".error-details").hide();
            this.$(".show-details").show();
            this.$(".hide-details").hide();
            
            if (this.error_options.allow_details) {
                this.$(".show-details").show();
            } else {
                this.$(".show-details").hide();
            }

            if (this.error_options.allow_report) {
                this.$(".report-error").show();
            } else {
                this.$(".report-error").hide();
            }

            if (this.error_options.allow_reload) {
                this.$(".reload-app").show();
            } else {
                this.$(".reload-app").hide();
            }
        },

        hide: function(reset_state) {
            if (reset_state === undefined) { reset_state = true };
            if (reset_state) {
                snf.api.error_state = false;
                snf.api.trigger("change:error_state", snf.api.error_state);
            }
            views.ErrorView.__super__.hide.apply(this);
        },

        onClose: function(reset_state) {
            this.trigger("close", this);
        }
    });

})(this);
