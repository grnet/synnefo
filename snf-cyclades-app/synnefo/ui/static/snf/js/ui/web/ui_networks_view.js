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
    var util = snf.util || {};
    var views = snf.views = snf.views || {}

    // shortcuts
    var bb = root.Backbone;
    
    // logging
    var logger = new snf.logging.logger("SNF-VIEWS");
    var debug = _.bind(logger.debug, logger);
    
    
    views.NetworkConnectVMsOverlay = views.Overlay.extend({
        title: "Connect machine",
        overlay_id: "overlay-select-vms",
        content_selector: "#network-vms-select-content",
        css_class: "overlay-info",

        initialize: function() {
            views.NetworkConnectVMsOverlay.__super__.initialize.apply(this);
            this.list = this.$(".vms-list ul");
            this.empty_message = this.$(".empty-message");

            // flag for submit handler to avoid duplicate bindings
            this.submit_handler_set = false;
        },
        
        init_handlers: function() {
            var self = this;
            this.list.find("li").click(function(){
                $(this).toggleClass("selected");
            });
            
            if (!this.submit_handler_set) {
                // avoid duplicate submits
                this.el.find(".create").click(_.bind(function() {
                    this.submit();
                }, this));
                this.submit_handler_set = true;
            }
        },

        reset: function() {
            this.list.find("li").remove();
        },

        beforeOpen: function() {
            this.reset();
            this.update_layout();
        },
        
        vm: function(vm) {
            if (vm.id) { var id = vm.id } else {var id = vm}
            return this.list.find(".vm-" + id);
        },

        get_selected: function() {
            return this.list.find(".selected").map(function() {return $(this).data('vm')})
        },

        update_layout: function() {
            if (this.vms.length == 0) {
                this.empty_message.show();
            } else {
                this.empty_message.hide();
            }

            _.each(this.vms, _.bind(function(vm){
                
                var html = '<li class="vm option options-object vm-{0}">' +
                           '<div class="options-object-cont">' +
                           '{2}' + 
                           '<span class="title">{1}</span>' + 
                           '<span class="value">{3}</span></div>' + 
                           '</li>';
                var el = $(html.format(vm.id, 
                                       util.truncate(_.escape(vm.get("name")), 23), 
                                       snf.ui.helpers.vm_icon_tag(vm, "small", {'class':'os'}),
                                       _.escape(vm.get_os())
                                      ))
                el.data({vm:vm, vm_id:vm.id})
                this.list.append(el);

                vm.bind("remove", function(){ el.remove()})
                vm.bind("change:name", function(i,v){el.find(".title").text(v)})
            }, this));
            
            this.init_handlers();
            this.set_selected();
        },

        set_selected: function() {
            _.each(this.selected, _.bind(function(el){
                this.vm(el).addClass("selected");
            }, this));
        },

        show_vms: function(network, vms, selected, callback) {
            this.network = network;
            this.reset();
            this.set_subtitle(network.escape("name"));
            this.vms = vms;
            if (!synnefo.config.network_allow_duplicate_vm_nics) {
                this.vms = _.filter(this.vms, function(vm) {
                    return !vm.connected_to(this.network);
                }, this);
            }

            this.selected = selected;
            this.cb = callback;
            this.show();
        },

        submit: function() {
            this.cb(this.get_selected());
        }
    })

    views.NetworkActionsView = views.View.extend({
        
        initialize: function(view, net, el, opts) {
            this.parent = view
            this.network = net;
            this.el = el;
            
            this.actions = this.$(".actions");
            this.selected = undefined;

            this.destroy = this.$(".actions .destroy a");
            this.connect = this.$(".actions .add");

            this.init_handlers();
            this.update_layout();
        },

        init_handlers: function() {
            this.connect.click(_.bind(function(e){
                e.preventDefault();
            }))
        },

        update_layout: function() {
        }
    });

    views.NetworkCreateView = views.Overlay.extend({
        view_id: "network_create_view",
        content_selector: "#networks-create-content",
        css_class: 'overlay-networks-create overlay-info',
        overlay_id: "network-create-overlay",

        title: "Create new private network",
        subtitle: "Networks",

        initialize: function(options) {
            views.NetworkCreateView.__super__.initialize.apply(this);

            this.create_button = this.$("form .form-action.create");
            this.text = this.$(".network-create-name");
            this.form = this.$("form");

            this.dhcp_select = this.$("#network-create-dhcp");
            this.type_select = this.$("#network-create-type");
            this.subnet_select = this.$("#network-create-subnet");
            this.subnet_custom = this.$("#network-create-subnet-custom");
                
            this.dhcp_form = this.$("#network-create-dhcp-fields");
            
            this.subnet_select.find(".subnet").remove();
            _.each(synnefo.config.network_suggested_subnets, function(subnet){
                this.subnet_select.append($('<option value='+subnet+' class="subnet">'+subnet+'</option>'));
            }, this);

            this.type_select.find(".subnet").remove();
            _.each(synnefo.config.network_available_types, function(name, value){
                this.type_select.append($('<option value='+value+' class="subnet">'+name+'</option>'));
            }, this);
            
            this.disable_network_type = false;
            if (_.keys(synnefo.config.network_available_types).length <= 1) {
                this.disable_network_type = true;
                this.type_select.closest(".form-field").hide();
            }

            this.check_dhcp_form();
            this.init_handlers();
        },

        reset_dhcp_form: function() {
          this.subnet_select.find("option")[0].selected = 1;
          this.subnet_custom.val("");
        },

        check_dhcp_form: function() {
            if (this.dhcp_select.is(":checked")) {
                this.dhcp_form.show();
            } else {
                this.dhcp_form.hide();
            }
            
            if (this.subnet_select.val() == "custom") {
                this.subnet_custom.show();
            } else {
                this.subnet_custom.hide();
            }
        },

        init_handlers: function() {

            this.dhcp_select.click(_.bind(function(e){
                this.check_dhcp_form();
                this.reset_dhcp_form();
            }, this));

            this.subnet_select.change(_.bind(function(e){
                this.check_dhcp_form();
                if (this.subnet_custom.is(":visible")) {
                    this.subnet_custom.focus();
                }
            }, this));

            this.create_button.click(_.bind(function(e){
                this.submit();
            }, this));

            this.form.submit(_.bind(function(e){
                e.preventDefault();
                this.submit;
                return false;
            }, this))

            this.text.keypress(_.bind(function(e){
                if (e.which == 13) {this.submit()};
            },this))
        },

        submit: function() {
            if (this.validate()) {
                this.create();
            };
        },
        
        validate: function() {
            // sanitazie
            var t = this.text.val();
            t = t.replace(/^\s+|\s+$/g,"");
            this.text.val(t);

            if (this.text.val() == "") {
                this.text.closest(".form-field").addClass("error");
                this.text.focus();
                return false;
            } else {
                this.text.closest(".form-field").removeClass("error");
            }
            
            if (this.dhcp_select.is(":checked")) {
                if (this.subnet_select.val() == "custom") {
                    var sub = this.subnet_custom.val();
                    sub = sub.replace(/^\s+|\s+$/g,"");
                    this.subnet_custom.val(sub);
                        
                    if (!synnefo.util.IP_REGEX.exec(this.subnet_custom.val())) {
                        this.subnet_custom.closest(".form-field").prev().addClass("error");
                        return false;
                    } else {
                        this.subnet_custom.closest(".form-field").prev().removeClass("error");
                    }
                };
            }

            return true;
        },

        create: function() {
            this.create_button.addClass("in-progress");

            var name = this.text.val();
            var dhcp = this.dhcp_select.is(":checked");
            var subnet = null;
            var type = this.type_select.val();

            if (this.disable_network_type) { type = null };

            if (dhcp) {
                if (this.subnet_select.val() == "custom") {
                    subnet = this.subnet_custom.val();
                } else if (this.subnet_select.val() == "auto") {
                    subnet = null;
                } else {
                    subnet = this.subnet_select.val();
                }
                
            }

            snf.storage.networks.create(name, type, subnet, dhcp, _.bind(function(){
                this.hide();
            }, this));
        },

        beforeOpen: function() {
            this.create_button.removeClass("in-progress")
            this.text.closest(".form-field").removeClass("error");
            this.text.val("");
            this.text.show();
            this.text.focus();
            this.subnet_custom.val("");
            this.subnet_select.val("auto");
            this.dhcp_select.attr("checked", true);
            this.type_select.val(_.keys(synnefo.config.network_available_types)[0]);
            this.check_dhcp_form();
        },

        onOpen: function() {
            this.text.focus();
        }
    });

    views.NetworkNICView = views.View.extend({

        initialize: function(nic, parent, firewall_controls, el) {
            this.firewall_controls = firewall_controls || false;
            this.nic = nic;
            this.vm = nic.get_vm();
            // parent view di
            this.parent = parent;
            // TODO make it better
            this.el = el || this.parent.get_nic_view(nic);

            this.init_layout();
            this.update_layout();

            this.disconnect = this.$(".action-disconnect");
            this.confirm_el = this.$(".confirm_single");
            this.cancel = this.$("button.no");
            this.confirm = this.$("button.yes");
            this.details = this.$(".action-details");
            this.vm_connect = this.$(".machine-connect");

            this.init_handlers();
            this.connect_overlay = new views.VMConnectView();
            
            this.firewall_view = undefined;
            if (this.firewall_controls) {
                this.firewall_view = new views.FirewallEditView(this.nic, this.parent.network, this);
            }

        },
        
        reset_all_net_actions: function(act_types) {
            synnefo.storage.networks.each(function(n){
                var actions = n.get('actions');
                _.each(act_types, function(type){
                    actions.remove_all(type);
                })
            })
        },

        init_handlers: function() {
            if (!this.parent.network.is_public()) {
                this.disconnect.click(_.bind(function(e){
                    e.preventDefault();
                    this.reset_all_net_actions(['destroy','disconnect']);
                    this.parent.network.get("actions").remove_all("disconnect");
                    this.parent.network.get("actions").add("disconnect", this.nic.id);
                    this.parent.network.get("actions").remove("destroy");
                }, this));
                this.cancel.click(_.bind(function(e){
                    this.parent.network.get("actions").remove("disconnect", this.nic.id);
                    e.preventDefault()
                }, this));

                this.confirm.click(_.bind(function(e){
                    e.preventDefault()
                    this.disconnect_nic();
                    this.confirm_el.hide();
                    this.disconnect.removeClass("selected");
                }, this));

                snf.ui.main.bind("view:change", _.bind(function(v) {
                    if (v == "networks" ){ return }
                    this.confirm_el.hide();
                    this.disconnect.removeClass("selected");
                }, this));

                this.$(".remove-icon").click(_.bind(function(){
                    this.reset_all_net_actions(['destroy','disconnect']);
                    this.parent.network.get("actions").remove_all("disconnect");
                    this.parent.network.get("actions").add("disconnect", this.nic.id);
                    this.parent.network.get("actions").remove("destroy");
                }, this));

                this.vm_connect.click(_.bind(function() {
                    this.connect_overlay.show(this.vm);
                }, this));
                
                this.parent.network.bind("change:actions", _.bind(function(model, action){
                    if (this.parent.network.get("actions").contains("disconnect", this.nic.id)) {
                        this.confirm_disconnect();
                    } else {
                        this.cancel_disconnect();
                    }
                }, this));
            }
            
            var vm = this.vm;
            this.details.click(function(e){
                e.preventDefault();
                snf.ui.main.show_vm_details(vm);
            });

        },

        cancel_disconnect: function() {
            this.confirm_el.hide();
            this.disconnect.removeClass("selected");
            this.$(".net-vm-actions a").removeClass("visible");
        },

        confirm_disconnect: function() {
            this.confirm_el.show();
            this.disconnect.addClass("selected");
            this.$(".net-vm-actions a").addClass("visible");
        },

        init_layout: function() {
            if (!this.firewall_controls) { return };
        },

        update_layout: function() {
            this.$(".vm-name").text(snf.util.truncate(this.vm.get("name"), 40));
            this.$("img.logo").attr("src", ui.helpers.vm_icon_path(this.vm, "medium"));

            if (this.firewall_view) {
                this.$(".ipv4-text").text(this.nic.get_v4_address());
                this.$(".ipv6-text").text(this.nic.get_v6_address());
            }

            if (this.firewall_view) {
                this.firewall_view.update_layout();
            }

            if (!this.firewall_view) {
                this.$(".ip4-container").hide();
                this.$(".ip6-container").hide();
                
                if (this.nic.get("ipv4")) {
                    this.$(".ipv4-text").text(this.nic.get_v4_address());
                    this.$(".ip4-container").show();
                    this.$(".machine-connect .content").hide();
                } else if (this.nic.get("ipv6")) {
                    this.$(".ipv6-text").text(this.nic.get_v6_address());
                    this.$(".ip6-container").show();
                    this.$(".machine-connect .content").hide();
                } else {
                    this.$(".machine-connect .content").show();
                }
            } else {
            }
        },

        disconnect_nic: function() {
            this.$("a.selected").removeClass("selected");
            this.nic.get_network().remove_nic(this.nic);
        },
    })

    views.NetworkModelRenameView = views.View.extend({
        initialize: function(parent, network) {
            this.parent = parent;
            this.network = network;
            this.el = this.parent.el.find(".name-div");

            this.icon = this.$(".rename-network");
            this.save = this.$("span.save");
            this.cancel = this.$("span.cancel");
            this.buttons = this.$(".editbuttons");
            this.name = this.$("span.name");
            this.editing = false;
            this.init_handlers();
            this.update_layout();
        },

        init_handlers: function() {
            this.icon.click(_.bind(function(){
                this.editing = true;
                this.update_layout();
            }, this));
            this.cancel.click(_.bind(function(){
                this.editing = false;
                this.update_layout();
            }, this));
            this.save.click(_.bind(function(){
                this.submit();
            }, this))
        },
        
        submit: function() {
            var value = _(this.input.val()).trim();
            if (value == "") { return }

            this.network.rename(value, _.bind(function(){
                this.editing = false;
                this.update_layout();
            }, this));
        },

        create_input: function() {
            this.input = $('<input type="text" class="network-rename-input" />');
            this.input.val(this.network.get("name"));
            this.el.append(this.input);
            this.input.focus();
            this.input.bind("keydown", _.bind(function(ev){
                ev.keyCode = ev.keyCode || ev.which;
                if (ev.keyCode == 13) { this.submit(); };
                if (ev.keyCode == 27) {this.editing = false; this.update_layout()};
            }, this));
        },

        remove_input: function() {
            if (!this.input) { return }
            this.input.remove();
        },

        update_layout: function() {
            if (this.editing) {
                if (this.buttons.is(":visible")) { return }
                this.icon.hide();
                this.buttons.show();
                this.create_input();
                this.name.hide();
            } else {
                this.buttons.hide();
                this.remove_input();
                this.name.show();
                this.icon.show();
            }
        }
    })

    views.FirewallEditView = views.View.extend({
        initialize: function(nic, network, parent) {
            this.parent = parent;
            this.vm = nic.get_vm();
            this.nic = nic;
            this.network = network;
            this.el = this.parent.el;

            views.FirewallEditView.__super__.initialize.apply(this);

            // elements
            this.toggler = this.$(".firewall-toggle");
            this.indicator = this.$(".machines-label span");
            this.progress = this.$(".network-progress-indicator");
            this.content = this.$(".firewall-content");
            this.inputs = this.$("input[type=radio]");
            this.labels = this.$("span.checkbox-legends, label.checkbox-legends");
            this.apply = this.$(".firewall-apply");

            this.$(".firewall-content").hide();
            this.$(".firewall-content input[type=radio]").attr("name", "firewall-opt-for-{0}".format(this.vm.id))
            var mode = this.vm.get_firewall_profile();
            this.$(".firewall-content input[value={0}]".format(mode)).attr("checked", true);

            this.init_handlers();
            this.update_layout();

            var self = this;
            this.nic.bind("change:pending_firewall_sending", function(nic, value) {
                if (value) {
                    self.apply.addClass("in-progress");       
                    self.progress.show();
                } else {
                    self.apply.removeClass("in-progress");       
                    self.progress.hide();
                    self.toggler.click();
                }
            });

            this.nic.bind("change:firewallProfile", function(nic){
                self.update_layout();
                self.reset_value();
            })

        },
        
        _get_selected: function() {
            return this.inputs.filter(":checked");
        },

        reset_selected: function() {
        },

        submit: function() {
        },

        reset_value: function() {
            this.inputs.filter("[value={0}]".format(
              this.nic.get('firewallProfile'))).attr("checked", true);
        },

        init_handlers: function() {
            this.toggler.click(_.bind(function(){
                cont = this.content;
                if (cont.is(":visible")) {
                    this.hide_firewall();
                    this.reset_value();
                } else {
                    this.show_firewall();
                }

                $(window).trigger("resize");
            }, this))
            
            this.apply.click(_.bind(function(){
                this.nic.set_firewall(this.value());
            }, this))

            this.inputs.change(_.bind(function(){
                this.update_selected();
            }, this))
            
            var self = this;
            this.$(".checkbox-legends").click(function(el) {
                var el = $(this);
                el.prev().click();
                self.update_selected();
            })
        },

        update_selected: function() {
            this.update_layout();
        },

        show_firewall: function() {
            this.content.slideDown(100, function(){$(window).trigger("resize")});
            this.toggler.addClass("open");
        },

        hide_firewall: function() {
            this.content.slideUp(100, function(){$(window).trigger("resize")});
            this.toggler.removeClass("open");
        },

        value: function() {
            return this._get_selected().val();
        },

        update_layout: function() {
            if (this.value() == this.vm.get_firewall_profile()) {
                this.apply.hide();
            } else {
                this.apply.show();
            }

            var profile = this.vm.get_firewall_profile();
            if (this.vm.has_firewall(this.network.id)) {
                this.$(".firewall-toggle .label span").text("On");
                this.$(".firewall-toggle .label span").removeClass("firewall-off");
                this.$(".firewall-toggle .label span").addClass("firewall-on");
            } else {
                this.$(".firewall-toggle .label span").text("Off");
                this.$(".firewall-toggle .label span").removeClass("firewall-on");
                this.$(".firewall-toggle .label span").addClass("firewall-off");
            }
            
            this.$("span.checkbox-legends").removeClass("current");
            this.inputs.filter("[value={0}]".format(profile)).next().addClass("current");
            
        }
    })

    views.NetworkModelView = views.View.extend({
        
        firewall: false,

        initialize: function(network, view) {
            this.parent_view = view;
            this.network = network;
            this.main_view_id = this.main_view_id ? this.main_view_id : "networks_view_" + network.id;
            this.is_public = network.is_public();

            this.init_nics_handlers();
            
            this.view_id = "networks_view_" + network.id;
            views.NetworkModelView.__super__.initialize.call(this);

            this.nics_views = {};

            this.el = this.create_el();

            // element helpers
            this.nics_list = this.$(".machines-list");
            this.nics_list_toggler = this.$(".list-toggle");
            
            this.init_handlers();
            this.init_toggler_handlers();
            this.update_nics();
            this.update_layout();

            this.hide_nics_list();
            this.nics_list.hide();

            this.rename_view = undefined;
            if (!this.network.is_public()) {
                // allow network rename for non public networks only
                this.rename_view = new views.NetworkModelRenameView(this, network);
            }
            
            var self = this;
            this.network.bind('change:status', function() {
                self.update_layout();
            });

        },

        init_nics_handlers: function() {
            storage.nics.bind("add", _.bind(this.nic_added_handler, this, "add"));
            storage.nics.bind("change", _.bind(this.nic_changed_handler, this, "change"));
            storage.nics.bind("reset", _.bind(this.nic_changed_handler, this, "reset"));
            storage.nics.bind("remove", _.bind(this.nic_removed_handler, this, "remove"));
        },


        show_nics_list: function() {
            //if (this.nics_empty()) { return }
            this.nics_list_toggler.addClass("open");
            this.nics_list.slideDown(function(){
                $(window).trigger("resize");
            }).closest(".network").addClass("expand");
            this.$(".empty-network-slot").slideDown();
            this.nics_visible = true;
        },

        hide_nics_list: function() {
            this.nics_list_toggler.removeClass("open");
            this.nics_list.slideUp(function(){
                $(window).trigger("resize");
            }).closest(".network").removeClass("expand");
            this.$(".empty-network-slot").slideUp();
            this.nics_visible = false;
        },
        
        init_toggler_handlers: function() {
            this.nics_list_toggler.click(_.bind(function(){
                if (this.nics_list.is(":visible")) {
                    this.hide_nics_list();
                } else {
                    this.fix_left_border();
                    this.show_nics_list();
                }

            }, this));
        },

        init_handlers: function() {
            var self = this;


            this.$(".action-add").click(_.bind(function(e){
                e.preventDefault();
                this.network.get("actions").remove("destroy");
                this.show_connect_vms();
            }, this))

            this.$(".add-icon").click(_.bind(function(e){
                e.preventDefault();
                this.show_connect_vms();
            }, this))

            this.$(".net-actions .destroy a").click(_.bind(function(e){
                e.preventDefault();
                synnefo.storage.networks.each(function(n) {
                    n.get('actions').remove_all("disconnect");
                    if (!synnefo.config.network_allow_multiple_destory) {
                        n.get('actions').remove_all("destroy");
                    }
                });
                self.network.get("actions").add("destroy");
                self.network.get("actions").remove_all("disconnect");
            }, this));

            self.network.bind("change:actions", _.bind(function(net, action) {
                if (this.network.get("actions").contains("destroy")) {
                    this.confirm_destroy();
                } else {
                    this.cancel_destroy();
                }
            }, this));
            

            // reset pending destory action after successful removal
            self.network.bind("remove", _.bind(function(net){
                net.get("actions").remove_all("destroy");
            }));

            this.$(".net-actions button.no").click(function(e){
                e.preventDefault();
                self.network.get("actions").remove("destroy");
            });

            this.$(".net-actions button.yes").click(function(e){
                e.preventDefault();
                var el = $(this);
                el.closest(".confirm_single").hide();
                el.parent().parent().find(".selected").removeClass("selected");
                self.network.call('destroy', {}, function(){
                    el.closest(".confirm_single").removeClass("in-progress");
                });
                el.closest(".confirm_single").addClass("in-progress");
            });

            snf.ui.main.bind("view:change", _.bind(function(v) {
                if (v == "networks" ){ return }
                this.$(".confirm_single").hide();
                this.$("a.selected").removeClass("selected");
            }, this));
            
            this.$(".empty-network-slot").hide();
            $(window).bind("resize", _.bind(function() {
                this.fix_left_border();
            }, this));
        },

        show_connect_vms: function() {
            this.$(".confirm_single").hide();
            this.$("a.selected").removeClass("selected");
            var vms = this.network.get_connectable_vms();
            this.parent_view.connect_machines_view.show_vms(this.network,
                                                            vms, [], 
                                                            _.bind(this.connect_vms, this));
        },

        cancel_destroy: function() {
            this.$(".net-actions .destroy .confirm_single").hide();
            this.$(".net-actions .destroy a.selected").removeClass("selected");
            this.$(".net-actions a").removeClass("visible");
        },

        confirm_destroy: function() {
            this.$(".destroy .confirm_single").show();
            this.$(".destroy a").addClass("selected");
            this.$(".net-actions a").addClass("visible");
        },

        connect_vms: function(vms) {
            _.each(vms, _.bind(function(vm){
                this.network.add_vm(vm);
            }, this));

            this.parent_view.connect_machines_view.hide();
        },

        create_el: function() {
            return this.$(this.tpl).clone().attr("id", this.main_view_id);
        },

        get_nic_id: function(nic) {
            return this.nic_id_tpl.format(nic.id);
        },

        get_nic_view: function(nic) {
            return $(this.get_nic_id(nic));
        },
        
        nic_in_network: function(nic) {
          return nic.get_network().id != this.network.id;
        },

        nic_added_handler: function(action, nic) {
            if (!this.nic_in_network(nic)) { return };
            this.add_or_update_nic(nic);
            this.update_layout();
            this.fix_left_border();
        },

        nic_changed_handler: function(action, nics, model, changes) {
            var nics = nics || [];

            // reset or update
            if (action == "reset") {
                nics = nics;
            } else {
                if (!_.isArray(nics)) {
                    nics = [nics]
                }
            }
            
            _.each(nics, _.bind(function(nic) {
                if (!this.nic_in_network(nic)) { return };
                this.add_or_update_nic(nic);
            }, this));

            this.update_layout();
        },

        nic_removed_handler: function(action, nic, model) {
            if (!this.nic_in_network(nic)) { return };
            this.fix_left_border();
            this.remove_nic(nic);
            this.update_layout();
        },

        remove_nic: function(nic) {
            var nic_view = this.get_nic_view(nic);
            if (nic_view.length) {
                nic_view.remove();
                try {
                    delete this.nics_views[nic.id]
                } catch (err) {
                }
            }
        },
        
        create_nic_view: function(nic) {
            var nic_el = $(this.nic_tpl).clone().attr({
                id: this.get_nic_id(nic).replace("#","")
            });
            this.nics_list.append(nic_el);
            this.post_nic_add(nic);

            if (!this.nics_views[nic.id]) {
                var nic_view = this.nics_views[nic.id] = new views.NetworkNICView(nic, this, this.firewall, nic_el);
            }
        },

        add_or_update_nic: function(nic) {
            if (!nic) { return };
                
            var nic_el = this.get_nic_view(nic);
            var nic_view = this.nics_views[nic.id];

            if (nic_el.length == 0) {
                nic_view = this.create_nic_view(nic);
            }
            
            if (nic_view) { nic_view.update_layout() };

            this.update_nic(nic);
            this.post_nic_update(nic);
        },

        update_nic: function(vm){},
        post_nic_add: function(vm){},
        post_nic_update: function(vm){},
        
        get_nics: function() {
          return this.network.get_nics();
        },

        update_nics: function(nics) {
            if (!nics) { nics = this.get_nics() };
            _.each(nics, _.bind(function(nic){
                this.add_or_update_nic(nic);
            }, this));
        },

        check_empty_nics: function() {
            if (this.get_nics().length == 0) {
                this.hide_nics_list();
            }
        },

        nics_empty: function() {
            return this.get_nics().length == 0;
        },

        remove: function() {
            $(this.el).remove();
        },

        update_layout: function() {
            // has vms ???
            this.check_empty_nics();

            // is expanded ???
            //
            // whats the network status ???
            //
            this.$(".machines-count").text(this.get_nics().length);

            var net_name = this.network.get("name");
            if (net_name == "public") { net_name = "Internet" }
            this.$(".name-div span.name").text(net_name);

            if (this.rename_view) {
                this.rename_view.update_layout();
            }
            
            this.$(".net-status").text(this.network.state_message());

            if (this.network.in_progress())  {
                this.$(".spinner").show();
                this.$(".network-indicator").addClass("in-progress");
            } else {
                this.$(".spinner").hide();
                this.$(".network-indicator").removeClass("in-progress");
            }
                
            if (this.network.get('state') == 'PENDING') {
                this.el.addClass("pending");
            } else {
                this.el.removeClass("pending");
            }

            if (this.network.get('state') == 'ERROR') {
                this.el.addClass("in-error");
                this.$(".network-indicator").addClass("error-state");
            } else {
                this.el.removeClass("in-error");
                this.$(".network-indicator").removeClass("error-state");
            }

            if (synnefo.config.network_strict_destroy) {
                if (this.get_nics().length == 0 && 
                        !this.network.in_progress()) {
                    this.el.removeClass("disable-destroy");
                } else {
                    this.el.addClass("disable-destroy");
                }
            }

            if (this.network.get("state") == "DESTROY") {
                this.$(".spinner").show();
                this.$(".state").addClass("destroying-state");
                this.$(".actions").hide();
            }
        },

        // fix left border position
        fix_left_border: function() {
            if (!this.nics_visible) { return };
            
            var imgheight = 2783;
            var opened_vm_height = 133 + 20;
            var closed_vm_height = 61 + 20;
            var additional_height = 25;

            if (!this.is_public) { 
                imgheight = 2700;
                additional_height = 65;
            };
            
            var contents = this.$(".network-contents");
            var last_vm = this.$(".network-machine:last .cont-toggler.open").length;
            var last_vm_height = closed_vm_height;
            if (last_vm > 0){
                last_vm_height = opened_vm_height;
            }

            var nics_opened = this.$(".network-machine .cont-toggler.open").length;
            var nics_closed = this.$(".network-machine").length - nics_opened;

            var calc_height = (nics_opened * opened_vm_height) + (nics_closed * closed_vm_height) + additional_height; 
            var bgpos = imgheight - calc_height + last_vm_height - 30;
            this.$(".network-contents").css({'background-position':'33px ' + (-bgpos) + 'px'});
        }
    })

    views.PublicNetworkView = views.NetworkModelView.extend({
        firewall: true,
        tpl: "#public-template",
        nic_tpl: "#public-nic-template",
        nic_id_tpl: "#nic-{0}",
        
        initialize: function(network, view) {
          views.PublicNetworkView.__super__.initialize.call(this, network, view);
        },

        init_handlers: function(vm) {}
    });

    views.GroupedPublicNetworkView = views.PublicNetworkView.extend({
        main_view_id: "grouped-public",

        initialize: function(network, view) {
          this.networks = {};
          this.add_network(network);
          views.GroupedPublicNetworkView.__super__.initialize.call(this, 
                                                                   network, 
                                                                   view);
        },
        
        nic_in_network: function(nic) {
          var nic_net  = nic.get_network();
          return _.filter(this.networks, function(n) { 
            return nic_net.id == n.id;
          }).length > 0;
        },

        get_nics: function() {
          var n = _.flatten(_.map(this.networks, function(n){ return n.get_nics(); }));
          return n
        },

        add_network: function(net) {
          this.networks[net.id] = net;
        },

        remove_network: function(net) {
          delete this.networks[net.id];
          this.update_nics();
        }

    })
    
    views.PrivateNetworkView = views.NetworkModelView.extend({
        tpl: "#private-template",
        nic_tpl: "#private-nic-template",
        nic_id_tpl: "#nic-{0}"
    })

    views.NetworksView = views.View.extend({
        
        view_id: "networks",
        pane: "#networks-pane",
        el: "#networks-pane",

        initialize: function() {
            // elements shortcuts
            this.create_cont = this.$("#networks-createcontainer");
            this.container = this.$("#networks-container");
            this.public_list = this.$(".public-networks");
            this.private_list = this.$(".private-networks");
            views.NetworksView.__super__.initialize.call(this);
            this.init_handlers();
            this.network_views = {};
            this.public_network = false;
            this.update_networks(storage.networks.models);
            this.create_view = new views.NetworkCreateView();
            this.connect_machines_view = new views.NetworkConnectVMsOverlay();
        },
        
        exists: function(net) {
            return this.network_views[net.id];
        },

        add_or_update: function(net) {
            var nv = this.exists(net);
            if (!nv) {
                if (net.is_public()){
                  if (synnefo.config.group_public_networks) {
                    if (!this.public_network) {
                      // grouped public not initialized
                      this.public_network = this.create_network_view(net);
                    } else {
                      // grouped public initialized, append
                      this.public_network.add_network(net);
                    }
                    nv = this.public_network;
                  } else {
                    // no grouped view asked, fallback to default create
                    nv = this.create_network_view(net);
                  }
                } else {
                  nv = this.create_network_view(net);
                }

                this.network_views[net.id] = nv;
                
                if (net.is_public()) {
                    this.public_list.append(nv.el);
                    this.public_list.show();
                } else {
                    this.private_list.append(nv.el);
                    this.private_list.show();
                }
            }

            // update vms
            // for cases where network servers list
            // get updated after vm addition and
            // vm_added_handler fails to append the
            // vm to the list
            nv.update_nics();
            nv.update_layout();
        },
        
        create_network_view: function(net) {
            if (net.is_public()) {
                if (synnefo.config.group_public_networks) {
                  if (self.public_network) { return self.public_network }
                  return new views.GroupedPublicNetworkView(net, this);
                } else {
                  return new views.PublicNetworkView(net, this);
                }
            }
            return new views.PrivateNetworkView(net, this);
        },
        
        init_handlers: function() {
            storage.networks.bind("add", _.bind(this.network_added_handler, this, "add"));
            storage.networks.bind("change", _.bind(this.network_changed_handler, this, "change"));
            storage.networks.bind("reset", _.bind(this.network_changed_handler, this, "reset"));
            storage.networks.bind("remove", _.bind(this.network_removed_handler, this, "remove"));

            this.$("#networkscreate").click(_.bind(function(e){
                e.preventDefault();
                this.create_view.show();
            }, this));
            
        },

        update_networks: function(nets) {
            _.each(nets, _.bind(function(net){
                if (net.get("status") == "DELETED") { return };
                view = this.add_or_update(net);
            }, this));
        },

        show: function() {
            this.container.show();
            $(this.el).show();
        },

        network_added_handler: function(type, net) {
            this.update_networks([net]);
        },

        network_changed_handler: function(type, models) {
            var nets = [];
            if (type == "change") {
                nets = [models]
            } else {
                nets = models.models;
            }

            this.update_networks(nets)
        },

        network_removed_handler: function(type, net) {
            this.remove_net(net)
            if (this.private_list.find(".network").length == 0) {
                this.private_list.hide();
            }
            
        },

        network_added: function(net) {
            return this.network_views[net.id];
        },

        get_network_view: function(net) {
            return this.network_views[net.id];
        },

        remove_net: function(net) {
            if (this.network_added(net)) {
                var view = this.get_network_view(net);
                if (view == this.public_network) {
                  this.public_network.remove_network(net);
                } else {
                  view.remove();
                }
                delete this.network_views[net.id];
            }
        },

        __update_layout: function() {
        }
    });

})(this);
