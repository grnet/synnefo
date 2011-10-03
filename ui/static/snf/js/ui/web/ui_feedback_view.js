;(function(root){

    // root
    var root = root;
    
    // setup namepsaces
    var snf = root.synnefo = root.synnefo || {};
    var api = snf.api = snf.api || {};
    var models = snf.models = snf.models || {}
    var storage = snf.storage = snf.storage || {};
    var ui = snf.ui = snf.ui || {};
    var util = snf.util = snf.util || {};

    var views = snf.views = snf.views || {}

    // shortcuts
    var bb = root.Backbone;

    views.FeedbackView = views.Overlay.extend({
        
        view_id: "feedback_view",
        content_selector: "#feedback-overlay-content",
        css_class: 'overlay-feedback overlay-info',
        overlay_id: "feedback-overlay",

        subtitle: "",
        title: "Send feedback",

        initialize: function(options) {
            views.FeedbackView.__super__.initialize.apply(this, arguments);
            
            _.bindAll(this, 'submit_form', 'show_error', 'show_success');

            this.submit = this.$("span.submit");
            this.text = this.$("textarea.feedback-message");
            this.text_row = this.$("div.form-field");
            this.messages = this.$(".messages").hide();
            this.error = this.$("p.error-message");
            this.success = this.$("p.success-message");
            this.form = this.$(".form");
            this.sending = this.$(".sending-message");

            this.init_handlers();
        },
        
        init_handlers: function() {
            this.submit.click(this.submit_form);
        },

        get_message: function() {
            var text = _(this.text.val()).trim();
            return text;
        },

        validate: function() {
            var msg = this.get_message();
            if (msg == "") {
                this.text_row.addClass("error");
                return false;
            } else {
                this.text_row.removeClass("error");
                return true;
            }
        },

        submit_form: function() {
            if (this.validate()) {
                this.show_sending();
                this.send_message(this.get_message(), {});
            } else {}
        },

        send_message: function(msg, extra) {
            var extra = extra || {};

            var data = {
                'feedback-msg': msg,
                'feedback-data': this.get_feedback_data() || ""
            }
            
            var opts = {
                'url': 'feedback',
                'data': $.param(data),
                'success': this.show_success,
                'error': this.show_error,
                'no_skip': true,
                'display': false,
                'handles_error': true
            }
            api.sync('create', undefined, opts);
        },

        get_feedback_data: function() {
            if (this.collect_data) return JSON.stringify(_.extend({}, snf.collect_user_data(),this.extra_data));
        },
        
        onOpen: function() {
            var self = this;
            var point = this.text.val().length;
            this.text.show().focus().setCursorPosition(point);

            this.$(".closeme").unbind("click");
            this.$(".closeme").bind("click", function(){
                self.hide("reset")
            });
        },

        show_form: function() {
            this.form.show();
            this.messages.hide();
            this.text.focus();
        },

        show_sending: function() {
            this.form.hide();
            this.messages.show();
            this.error.hide();
            this.success.hide();
            this.sending.show();
        },

        show_error: function() {
            this.form.hide();
            this.messages.show();
            this.error.show();
            this.success.hide();
            this.sending.hide();
        },

        show_success: function() {
            this.form.hide();
            this.messages.show();
            this.error.hide();
            this.success.show();
            this.sending.hide();
        },
        
        hide: function(reset_error_state) {
            // trigger api reset
            if (reset_error_state === "reset") {
                // report error feedback form
                if (snf.api.error_state == snf.api.STATES.ERROR) {
                    snf.api.trigger("reset");
                }
            }
            views.FeedbackView.__super__.hide.apply(this);
        },

        show: function(data, collect_data, extra_data, cb) {
            this.data = data || "";
            this.cb = cb || function () {};
            this.collect_data = collect_data || false;
            this.extra_data = extra_data || {};

            views.FeedbackView.__super__.show.apply(this, arguments);
            this.text.val(data);
            this.show_form();
        }
    });
})(this);
