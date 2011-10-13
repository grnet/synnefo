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

    views.InvitationsView = views.Overlay.extend({
        
        view_id: "invitations_view",
        content_selector: "#invitations-overlay-content",
        css_class: 'overlay-invitations overlay-info',
        overlay_id: "invitations-overlay",

        subtitle: "",
        title: "Invitations",

        initialize: function(options) {
            views.InvitationsView.__super__.initialize.apply(this, arguments);

            _.bindAll(this);

            this.entry_tpl = this.$(".form-entry-tpl");
            this.form_entries = this.$(".form-entries");
            this.add = this.$(".add-new-invitation");
            this.remove = this.$(".remove-invitation");
            this.send = this.$(".send-invitations");
            this.top_info = this.$(".top-info");
            this.sent = this.$(".invitations-sent-cont");
            this.sent_pages = this.$(".invitations-sent-pages");
            this.sent_tpl = this.$(".invitation-sent-tpl");
            this.entry_tpl.hide();

            this.inv_sent_per_page = 9;

            this.init_handlers();
        },

        init_handlers: function() {
            var self = this;
            this.add.click(this.add_new_entry);
            this.send.click(this.send_entries);
            this.remove.live('click', function() {
                return self.remove_entry($(this).parent().parent());
            });
        },
        
        remove_entry: function(entry) {
            if (entry.hasClass("sending")) { return };
            entry.remove();
            this.fix_entries();
        },

        add_new_entry: function() {
            var new_entry = this.create_form_entry().show()
            this.form_entries.append(new_entry).show();
            $(new_entry.find("input").get(0)).focus();
            this.fix_entries();
        },
        
        show_entry_error: function(entry, error) {
            entry.find(".send-error").text(error)
            entry.find(".send-error").show();
            entry.addClass("error");
            entry.find("input").attr("disabled", false);
        },
        
        get_entry_data: function(entry) {
            var data = {name: entry.find("input.name").val(), email:entry.find("input.email").val()};
            return data;
        },

        entry_is_valid: function(entry) {
            var data = this.get_entry_data(entry);

            entry.find(".send-error").hide();
            entry.removeClass("error");
            entry.find("input").removeClass("has-errors");

            error = false;
            if (!data.name || data.name.split(" ").length == 1) {
                error = "Invalid name";
                entry.find("input.name").addClass("has-errors");
            }

            var reg = /^([A-Za-z0-9_\-\.])+\@([A-Za-z0-9_\-\.])+\.([A-Za-z]{2,4})$/;
            if (!data.email || reg.test(data.email) == false) {
                error = "Invalid email";
                entry.find("input.email").addClass("has-errors");
            }
            
            if (error) { this.show_entry_error(entry, error) };
            return error
        },
        
        send_entries: function() {
            var self = this;
            this.form_entries.find(".form-entry").each(function(index, el) { self.entry_is_valid($(el)) });
            var entries_to_send = this.form_entries.find(".form-entry:not(.error):not(.sending)");
            this._send_entries(entries_to_send);
        },

        _send_entries: function(entries) {
            $(entries).addClass("sending").find("input").attr("disabled", true);
            var self = this;
            _.each(entries, function(e) {
                var e = $(e);
                var data = self.get_entry_data(e);
                self.send_invitation(data.name, 
                                     data.email,
                                     _.bind(self.invitation_send, this, e), 
                                     _.bind(self.invitation_failed, this, e));
            });
        },

        invitation_send: function(entry, data) {
            entry.removeClass("sending");
            if (data.errors && data.errors.length) {
                this.show_entry_error($(entry), data.errors[0]);
                return;
            } else {
                entry.remove();
                this.show_send_success(entry.find("input.name").val(), data);
            }
        },

        show_send_success: function(to, data) {
            var msg = "Invitation to " + to + " was sent.";
            var msg_el = $('<div class="msg">{0}</div>'.format(msg));

            this.top_info.append(msg_el);

            window.setTimeout(function(){
                msg_el.fadeOut(600, function(){$(this).remove()});
            }, 2000);

            this.fix_entries();
            this.reset_invitations_sent();
        },

        invitation_failed: function(entry) {
            entry.removeClass("sending");
            this.show_entry_error(entry, "Cannot send email, please try again later");
        },

        send_invitation: function(name, email, success, fail) {
            var url = snf.config.invitations_url;
            var payload = {name_1: name, email_1: email, csrftoken: $.cookie('csrftoken')};
            params = {
                success: success,
                error: fail,
                url: url,
                data: $.param(payload),
                skip_api_error: true
            }
            snf.api.sync("create", undefined, params);
        },

        get_entries: function() {
            return this.form_entries.find(".form-entry");
        },

        fix_entries: function() {
            this.$(".remove-invitation").hide();
            if (this.get_entries().length == 0) {
                this.add_new_entry();
            }

            if (this.get_entries().length > 1) {
                this.$(".remove-invitation").show();
            }
            this.$(".form-entry:first-child label").show();
            this.$(".form-entry:not(:first-child) label").hide();
        },

        show: function() {
            views.InvitationsView.__super__.show.apply(this, arguments);
            this.current_page = 0;
            this.reset_invitations_sent();
            this.reset();

            this.add_new_entry();
            this.add_new_entry();
            this.add_new_entry();
        },

        create_form_entry: function() {
            return this.entry_tpl.clone().removeClass("form-entry-tpl").addClass("form-entry").removeClass("hidden");
        },
            
        reset: function() {
            this.get_entries().remove();
            this.add_new_entry();
        },
        
        new_invitation_sent_el: function() {
            return this.sent_tpl.clone().removeClass("invitation-sent-tpl").addClass("invitation-sent");
        },
        
        show_invitations_sent_error: function() {
            this.sent.hide();
            this.$(".invitations-sent-error").show();
        },

        reset_invitations_sent: function() {
            var self = this;
            var url = snf.config.invitations_url;
            params = {
                success: function(data) {
                    if (!data || !data.invitations) {
                        self.show_invitations_sent_error();
                    } else {
                        self.sent.empty();
                        self.add_invitations_sent(data.invitations);
                    }
                    
                    //data.invitations_left = 0;
                    self.$(".description .left").text(data.invitations_left);
                    if(data.invitations_left > 0) {
                        self.$(".invitations-form").show();
                        self.$(".description .left").removeClass("none");
                        self.el.removeClass("none-left");
                    } else {
                        self.$(".invitations-form").hide();
                        self.$(".description .left").addClass("none");
                        self.el.addClass("none-left");
                    }
                },
                error: _.bind(this.show_invitations_sent_error, this),
                url: url,
                skip_api_error: true
            }

            snf.api.sync("read", undefined, params);
        },

        add_invitations_sent: function(invs) {
            _.each(invs, _.bind(function(inv) {
                var el = this.new_invitation_sent_el();
                el.find(".name").text(inv.targetname);
                el.find(".email").text(inv.target);
                el.find(".action").addClass("sent");
                if (!inv.accepted) {
                    el.find(".action").removeClass("resend").addClass("resend")
                }
                el.removeClass("hidden");
                this.sent.append(el);
            }, this));
            this.update_pagination();
            this.sent_pages.trigger("setPage", this.current_page || 0);
        },
        
        inv_sent_per_page: 5,
        update_pagination: function() {
            this.sent.css({minHeight:this.inv_sent_per_page * 35 + "px"})
            this.sent_pages.pagination(this.sent.children().length, {items_per_page:this.inv_sent_per_page, callback: this.page_cb});
        },

        page_cb: function(index, pager) {
            this.current_page = index;
            var start = index * this.inv_sent_per_page;
            var end = start + this.inv_sent_per_page -1;
            var items = this.sent.children();
            items.hide().removeClass("last");
            for (var i = start; i<=end; i++) {
                $(items.get(i)).show();
            }
            $(items.get(end)).addClass("last");
            return false;
        }
        
    });
})(this);

