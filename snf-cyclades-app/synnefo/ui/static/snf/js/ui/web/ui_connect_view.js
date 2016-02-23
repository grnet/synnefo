// Copyright (C) 2010-2014 GRNET S.A.
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.
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


    views.VMConnectView = views.VMOverlay.extend({
        
        view_id: "connect_view",
        content_selector: "#vm-connect-overlay-content",
        css_class: 'overlay-vmconnect overlay-info',
        overlay_id: "vmconnect-overlay",

        subtitle: "",
        title: "Connect to machine",

        initialize: function(options) {
            views.VMConnectView.__super__.initialize.apply(this);
            _.bindAll(
                this,
                "handle_connection_success",
                "handle_connection_error",
                "handle_password_success",
                "handle_password_error"
            );

            this.error = this.$("div.error");
            this.info = this.$("div.connection-info");
            this.no_public = this.$("div.no-public-ip");
            this.closeme = this.$(".closeme");
            this.password_info = this.$(".password-info");
            this.confirm = this.info.find(".confirm");
            this.description = this.info.find(".description p");
            this.connect = this.info.find(".connect p");
            this.subinfo = this.info.find(".subinfo");
            this.v6_warn = this.info.find(".v6-warn");
            this.password_entry = this.password_info.find("#new-machine-password");
            this.password_disabled = this.password_info.find(".disabled");
            this.show_machine = this.password_info.find(".show-machine");
            this.password_confirmation = this.password_info.find(".confirm");

            var self = this;
            this.no_public.find("a").click(function(e) {
              e.preventDefault();
              self.hide();
              window.setTimeout(function() {
                synnefo.router.ips_view();
              }, 200)
            });

            this.password_confirmation.find("button.no").click(_.bind(function() {
                this.prevent_close = false;
                this.password_info.hide();
                this.get_connection_info();
            }, this));

            this.password_confirmation.find("button.yes").click(_.bind(function() {
                this.prevent_close = false;
                storage.vms.delete_admin_password(this.vm.id);
                this.password_info.hide();
                this.get_connection_info();
            }, this));

        },

        get_connection_info: function() {
            this.vm.get_connection_info($.client.os, this.handle_connection_success, this.handle_connection_error)
        },

        beforeOpen: function() {
            this.$(".clipboard").empty();
        },

        beforeClose: function() {
            this.$(".clipboard").empty();
            try { delete this.clip; } catch (err) {};
        },
        
        show_no_public_ip: function() {
            this.error.hide();
            this.info.hide();
            this.no_public.removeClass("hidden").show();
        },

        hide_no_public_ip: function() {
            this.no_public.addClass("hidden").hide();
        },

        handle_connection_success: function(data) {
            // clear previous click event handlers
            this.closeme.unbind("click");
            this.closeme.click(_.bind(function() {
                this.hide();
            }, this));

            this.error.hide();
            this.v6_warn.hide();
            this.no_public.hide();
            this.description.html(data.info);
            if (data.ssh) {
                this.connect.html(data.link.title);
            } else {
                this.connect.html('<a href="{0}">{1}</a>'.format(data.link.url, data.link.title))
            }

            if (data.ssh) {
                var ssh_msg = data.link.title;
                this.clip = new snf.util.ClipHelper(this.$(".clipboard"), ssh_msg);
            }

            this.show_connection_info(data);
        },

        handle_connection_error: function() {
            this.error.show();
            this.info.hide();
        },

        show_connection_info: function(data) {
            if (!this.vm.has_public_ip()) {
                this.show_no_public_ip();
                return;
            }

            this.info.show();

            if (data.subinfo) {
                this.subinfo.show();
            }

            if (!this.vm.has_public_ipv4()) {
                this.v6_warn.removeClass("hidden").show();
            } else {
                this.v6_warn.hide();
            }
        },

        handle_password_success: function(data) {
            // hide the confirmation message
            this.password_confirmation.hide();
            // show the OK button
            this.show_machine.show();

            this.password_entry.val(data.password);

            // hide the info because the password modal
            // shall appear first
            this.info.hide();
            this.password_disabled.hide();

            this.password_info.show();

            this.prevent_close = true;
            this.closeme.unbind("click");
            this.closeme.click(_.bind(function() {
            }, this));
            // OK button clicked
            this.show_machine.click(_.bind(function() {
                this.show_machine.hide();
                this.password_confirmation.show();
            }, this));
        },

        handle_password_error: function() {
            this.get_connection_info();
        },

        handle_vm_change: function(vm) {
            if (!this.vm) { this.vm = undefined; return; }
            if (this.vm.state() == "DESTROY") {
                this.hide();
            }
            this._update_vm_details();
        },
        
        update_vm_details: function() {
        },

        show: function() {
            views.VMConnectView.__super__.show.apply(this, arguments);
            
            this.error.hide();
            this.info.hide();
            this.hide_no_public_ip();

            storage.vms.get_admin_password(this.vm.id, this.handle_password_success, this.handle_password_error);
        }

    });
    
})(this);
