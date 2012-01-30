// Copyright 2011 GRNET S.A. All rights reserved.
// 
// Redistribution and use in source and binary forms, with or
// without modification, are permitted provided that the following
// conditions are met:
// 
//   1. Redistributions of source code must retain the above
//      copyright notice, this list of conditions and the following
//      disclaimer.
// 
//   2. Redistributions in binary form must reproduce the above
//      copyright notice, this list of conditions and the following
//      disclaimer in the documentation and/or other materials
//      provided with the distribution.
// 
// THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
// OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
// WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
// PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
// CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
// SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
// LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
// USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
// AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
// LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
// ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
// POSSIBILITY OF SUCH DAMAGE.
// 
// The views and conclusions contained in the software and
// documentation are those of the authors and should not be
// interpreted as representing official policies, either expressed
// or implied, of GRNET S.A.
// 

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
            });

            this.$(".show-next").click(_.bind(function(){
                this.show_next_error();
            }, this));

            this.$(".show-prev").click(_.bind(function(){
                this.show_prev_error();
            }, this));

            this.displaying_error = false;
            this.error_stack_index = [];
            this.error_stack = {};
        },

        error_object: function() {
            return {ns:this.ns, code:this.code, message:this.message, details:this.details};
        },

        report_error: function() {
            this.feedback_view = this.feedback_view || ui.main.feedback_view;
            this.hide(false);
            this.displaying_error = true;

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
            
            var error_entry = [ns, code, message, type, details, error_options];
            var last_error_key = this.update_errors_stack(error_entry);
            
            if (!this.is_visible && !this.displaying_error) {
                this.current_error = last_error_key;
                this.display_error.call(this, last_error_key);
                this.show();
            }

            this.update_errors_stack();
        },

        update_errors_stack: function(entry) {
            if (snf.api.error_state != snf.api.STATES.ERROR) { 
                this.error_stack = {};
                this.error_stack_index = [];
            };

            var stack_key = (new Date()).getTime();
            this.error_stack[stack_key] = entry;
            this.error_stack_index.push(stack_key);
            this.errors_occured = this.error_stack_index.length;
            
            this.$(".error-nav").hide();
            //this.update_errors_stack_layout();
            return stack_key;
        },

        is_last_error: function(stack_key) {
            return this.error_stack_index.indexOf(stack_key) == this.error_stack_index.length - 1;
        },

        is_first_error: function(stack_key) {
            return this.error_stack_index.indexOf(stack_key) == 0;
        },

        update_errors_stack_layout: function() {
            if (!this.current_error) { return };

            if (this.errors_occured <= 1) {
                this.$(".error-nav").hide();
            } else {
                this.$(".error-nav").show();
            };
            
            if (this.is_last_error(this.current_error)) {
                this.$(".show-next").hide();
            } else {
                this.$(".show-next").show();
            }

            if (this.is_first_error(this.current_error)) {
                this.$(".show-prev").hide();
            } else {
                this.$(".show-prev").show();
            }
        },

        show_next_error: function() {
        },

        show_prev_error: function() {
        },

        display_error: function(stack_key) {
            var err = this.error_stack[stack_key];
            var ns = err[0], code = err[1], message = err[2], type = err[3], details = err[4], error_options = err[5]

            this.error_options = {'allow_report': true, 'allow_reload': true, 
                'extra_details': {}, 'non_critical': false, 
                'allow_details': false,
                'allow_close': true };
            
            if (error_options) {
                this.error_options = _.extend(this.error_options, error_options);
            }

            this.code = code;
            this.ns = ns;
            this.type = type;
            this.details = details ? (details.toString ? details.toString() : details) : undefined;
            this.message = message;
            this.title = error_options.title || undefined;

            this.update_details();
            
            if (error_options.non_critical) {
                this.el.addClass("non-critical");
                this.error_options.allow_details = false;
            } else {
                this.el.removeClass("non-critical");
                this.error_options.allow_details = true;
            }
            
            if (APP_DEBUG) {
                this.error_options.allow_details = true;
            }
            
            this.$(".actions .show-details").click();
            this.$(".error-details").hide();
            this.$(".key.details").click();
            this.$(".error-more-details").hide();
        },

        update_details: function() {
            var title = "Application error";
            if (this.ns && this.type) {
                title = this.title || this.type + " Error";
            }

            this.$(".overlay-header .title").text(title);
            this.$(".error-code").text(this.code || "");
            this.$(".error-type").text(this.type || "");
            this.$(".error-module").text(this.ns || "");
            this.$(".message p").text(this.message || "");
            this.$(".error-more-details p").html($("<pre />", {text:this.details}) || "no info");

            this.$(".extra-details").remove();
            _.each(this.error_options.extra_details, function(value, key){
                var opt = $(('<span class="extra-details key">{0}</span>' +
                            '<span class="extra-details value">{1}</span>').format(key, value))
                this.$(".value.error-type").after(opt);
            })

        },

        beforeOpen: function() {
            this.$(".error-details").hide();
            this.$(".key.details").addClass("expand");
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

            if (this.error_options.allow_close) {
                this.$(".closeme").show();
            } else {
                this.$(".closeme").hide();
            }

        },

        onOpen: function() {
            this.displaying_error = true;
            var self = this;

            this.$(".closeme").unbind("click");
            this.$(".closeme").bind("click", function(){
                self.hide("reset");
            })
        },

        hide: function(reset_state) {
            if (reset_state === "reset") {
                // delay reset error state for fade out
                window.setTimeout(_.bind(function(){
                    this.displaying_error = false;
                    this.error_stack = {};
                    snf.api.trigger("reset");
                }, this), 500);
            } else {
                this.displaying_error = false;
            }
            views.ErrorView.__super__.hide.apply(this);
        },

        onClose: function(reset_state) {
            this.trigger("close", this);
        }
    });

})(this);
