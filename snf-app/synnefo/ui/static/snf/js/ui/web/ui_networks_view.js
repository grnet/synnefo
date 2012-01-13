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
        },
        
        init_handlers: function() {
            var self = this;
            this.list.find("li").click(function(){
                $(this).toggleClass("selected");
            });

            this.el.find(".create").click(_.bind(function() {
                this.submit();
            }, this));
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
                el.data({vm:vm,vm_id:vm.id})
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
            this.init_handlers();
        },

        init_handlers: function() {
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
                return true;
            }
        },

        create: function() {
            this.create_button.addClass("in-progress");
            snf.storage.networks.create(this.text.val(), _.bind(function(){
                this.hide();
            }, this));
        },

        beforeOpen: function() {
            this.create_button.removeClass("in-progress")
            this.text.closest(".form-field").removeClass("error");
            this.text.val("");
            this.text.show();
            this.text.focus();
        },

        onOpen: function() {
            this.text.focus();
        }
    });

    views.NetworkVMView = views.View.extend({

        initialize: function(vm, parent, firewall_controls, el) {
            this.firewall_controls = firewall_controls || false;
            this.vm = vm;
            // parent view di
            this.parent = parent;
            // TODO make it better
            this.el = el || this.parent.vm(vm);

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
                this.firewall_view = new views.FirewallEditView(this.vm, this.parent.network, this);
            }

        },
        
        init_handlers: function() {
            if (!this.parent.network.is_public()) {
                this.disconnect.click(_.bind(function(e){
                    e.preventDefault();
                    this.parent.network.get("actions").add("disconnect", this.vm.id);
                    this.parent.network.get("actions").remove("destroy");
                }, this));
                this.cancel.click(_.bind(function(e){
                    this.parent.network.get("actions").remove("disconnect", this.vm.id);
                    e.preventDefault()
                }, this));
                this.confirm.click(_.bind(function(e){
                    e.preventDefault()
                    this.disconnect_vm();
                    this.confirm_el.hide();
                    this.disconnect.removeClass("selected");
                }, this));

                snf.ui.main.bind("view:change", _.bind(function(v) {
                    if (v == "networks" ){ return }
                    this.confirm_el.hide();
                    this.disconnect.removeClass("selected");
                }, this));

                this.$(".remove-icon").click(_.bind(function(){
                    this.parent.network.get("actions").add("disconnect", this.vm.id);
                    this.parent.network.get("actions").remove("destroy");
                }, this));

                this.vm_connect.click(_.bind(function() {
                    this.connect_overlay.show(this.vm);
                }, this));
                
                this.parent.network.bind("change:actions", _.bind(function(model, action){
                    if (this.parent.network.get("actions").contains("disconnect", this.vm.id)) {
                        this.confirm_disconnect();
                    } else {
                        this.cancel_disconnect();
                    }
                }, this));
            }
            
            var vm = this.vm;
            this.details.click(function(){
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
                this.$(".ipv4-text").text(this.vm.get_addresses().ip4);
                this.$(".ipv6-text").text(this.vm.get_addresses().ip6);
            }

            if (this.firewall_view) {
                this.firewall_view.update_layout();
            }
        },

        disconnect_vm: function() {
            this.$("a.selected").removeClass("selected");
            this.parent.network.remove_vm(this.vm);
        },

        update_firewall_layout: function() {
        }


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
        initialize: function(vm, network, parent) {
            this.parent = parent;
            this.vm = vm;
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
            var mode = this.vm.firewall_profile(this.network.id);
            this.$(".firewall-content input[value={0}]".format(mode)).attr("checked", true);

            this.init_handlers();
            this.update_layout();
        },
        
        _get_selected: function() {
            return this.inputs.filter(":checked");
        },

        reset_selected: function() {
        },

        submit: function() {
        },

        reset_value: function() {
            this.inputs.filter("[value={0}]".format(this.vm.firewall_profile(this.network.id))).attr("checked");
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
                this.apply.addClass("in-progress");
                
                // make the api call
                this.vm.set_firewall(this.network.id, this.value(), 
                // complete
                _.bind(function() {
                    // complete callback
                    this.apply.removeClass("in-progress");
                }, this), 
                // error
                _.bind(function(){
                    this.vm.remove_pending_firewall(this.network.id, this.value());
                }, this));
                this.hide_firewall();
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
            if (this.value() == this.vm.firewall_profile(this.network.id)) {
                this.apply.hide();
            } else {
                this.apply.show();
            }

            profile = this.vm.firewall_profile(this.network.id);
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
            this.inputs.filter("[value={0}]".format(this.vm.firewall_profile(this.network.id))).next().addClass("current");

            var firewalling = this.vm.firewall_pending(this.network.id);
            var el = this.el;
            
            if (firewalling) {
                el.find("button").addClass("in-progress").show();
                el.find(".network-progress-indicator").show();
            } else {
                el.find("button").removeClass("in-progress");
                el.find(".network-progress-indicator").hide();
            }
        }
    })

    views.NetworkModelView = views.View.extend({
        
        firewall: false,

        initialize: function(network, view) {
            this.parent_view = view;
            this.network = network;
            this.is_public = network.is_public();

            this.init_vm_handlers();

            this.view_id = "networks_view_" + network.id;
            views.NetworkModelView.__super__.initialize.call(this);

            this.vm_views = {};

            this.el = this.create_el();

            // element helpers
            this.vms_list = this.$(".machines-list");
            this.vms_list_toggler = this.$(".list-toggle");
            
            this.init_handlers();
            this.update_vms();
            this.update_layout();

            this.hide_vm_list();
            this.vms_list.hide();

            this.rename_view = undefined;
            if (!this.network.is_public()) {
                this.rename_view = new views.NetworkModelRenameView(this, network);
            }
        },

        show_vm_list: function() {
            if (this.vms_empty()) { return }
            this.vms_list_toggler.addClass("open");
            this.vms_list.slideDown(function(){
                $(window).trigger("resize");
            }).closest(".network").addClass("expand");
            this.$(".empty-network-slot").show();
            this.vms_visible = true;
        },

        hide_vm_list: function() {
            this.vms_list_toggler.removeClass("open");
            this.vms_list.slideUp(function(){
                $(window).trigger("resize");
            }).closest(".network").removeClass("expand");
            this.$(".empty-network-slot").hide();
            this.vms_visible = false;
        },
        
        // fix left border position
        fix_left_border: function() {
            if (!this.vms_visible) { return };
            
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

            var vms_opened = this.$(".network-machine .cont-toggler.open").length;
            var vms_closed = this.$(".network-machine").length - vms_opened;

            var calc_height = (vms_opened * opened_vm_height) + (vms_closed * closed_vm_height) + additional_height; 
            var bgpos = imgheight - calc_height + last_vm_height - 30;
            this.$(".network-contents").css({'background-position':'33px ' + (-bgpos) + 'px'});
        },


        init_handlers: function() {
            var self = this;

            this.vms_list_toggler.click(_.bind(function(){
                if (this.vms_list.is(":visible")) {
                    this.hide_vm_list();
                } else {
                    this.fix_left_border();
                    this.show_vm_list();
                }

                this.check_empty_vms();
            }, this));

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
                self.network.get("actions").add("destroy");
                self.network.get("actions").remove_all("disconnect");
            }, this));

            self.network.bind("change:actions", _.bind(function(net, action) {
                if (this.network.get("actions").contains("destroy")) {
                    this.confirm_destroy();
                } else {
                    this.cancel_destroy();
                }
            }, this))

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
            var el = this.$(this.tpl).clone().attr("id", "network-" + this.network.id)
            return el;
        },

        init_vm_handlers: function() {
            storage.vms.bind("add", _.bind(this.vm_added_handler, this, "add"));
            storage.vms.bind("network:connect", _.bind(this.vm_changed_handler, this, "connect"));
            storage.vms.bind("change", _.bind(this.vm_changed_handler, this, "change"));
            storage.vms.bind("reset", _.bind(this.vm_changed_handler, this, "reset"));
            storage.vms.bind("remove", _.bind(this.vm_removed_handler, this, "remove"));
            storage.vms.bind("network:disconnect", _.bind(this.vm_removed_handler, this, "disconnect"));
        },

        get_vm_id: function(vm) {
            return this.vm_id_tpl.format(this.network.id, vm.id)
        },

        vm: function(vm) {
            return $(this.get_vm_id(vm))
        },

        vm_added_handler: function(action, vm) {
            if (!this.network.contains_vm(vm)) { return }
            this.add_or_update_vm(vm);
            this.update_layout();
            this.fix_left_border();
        },

        vm_changed_handler: function(action, vms, model, changes) {
            var vms = vms || [];
            // reset or change
            if (action == "reset") {
                vms = vms;
            } else {
                if (!_.isArray(vms)) {
                    vms = [vms]
                }
            }

            if (action == "connect") {
                vms = [model];
            }
            
            _.each(vms, _.bind(function(vm) {
                if (!this.network.contains_vm(vm)) { return }
                this.add_or_update_vm(vm);
            }, this));
            this.update_layout();
        },

        vm_removed_handler: function(action, vm, model) {
            if (action == "disconnect") { vm = model };
            this.fix_left_border();
            this.remove_vm(vm);
            this.update_layout();
        },

        remove_vm: function(vm) {
            if (this.vm(vm).length) {
                this.vm(vm).remove();
                try {
                    delete this.vm_views[vm.id]
                } catch (err) {
                }
            }
        },
        
        create_vm: function(vm) {
            vm_el = $(this.vm_tpl).clone().attr({id:this.get_vm_id(vm).replace("#","")});
            this.vms_list.append(vm_el);
            this.post_vm_add(vm);

            if (!this.vm_views[vm.id]) {
                vm_view = this.vm_views[vm.id] = new views.NetworkVMView(vm, this, this.firewall, vm_el);
            }
        },

        add_or_update_vm: function(vm) {
            if (!vm || !this.network.contains_vm(vm)) { return };

            var vm_el = this.vm(vm);
            var vm_view = this.vm_views[vm.id];

            if (vm_el.length == 0) {
                this.create_vm(vm);
            }
            
            if (vm_view) { vm_view.update_layout() };

            this.update_vm(vm);
            this.post_vm_update(vm);
        },
        update_vm: function(vm){},
        post_vm_add: function(vm){},
        post_vm_update: function(vm){},

        update_vms: function(vms) {
            if (!vms) { vms = this.network.vms.list() };
            _.each(vms, _.bind(function(vm){
                this.add_or_update_vm(vm);
            }, this));
        },

        check_empty_vms: function() {
            if (this.network.vms.get().length == 0) {
                this.hide_vm_list();
            }
        },

        vms_empty: function() {
            return this.network.vms.get().length == 0;
        },

        remove: function() {
            $(this.el).remove();
        },

        update_layout: function() {
            // has vms ???
            this.check_empty_vms(this.network.vms.list());

            // is expanded ???
            //
            // whats the network status ???
            //
            this.$(".machines-count").text(this.network.vms.get().length);

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

            if (this.network.get("state") == "DESTROY") {
                this.$(".spinner").show();
                this.$(".state").addClass("destroying-state");
            }
        }
    })

    views.PublicNetworkView = views.NetworkModelView.extend({
        firewall: true,
        tpl: "#public-template",
        vm_tpl: "#public-machine-template",
        vm_id_tpl: "#network-{0}-vm-{1}",

        update_vm: function(vm) {
        }
    })
    
    views.PrivateNetworkView = views.NetworkModelView.extend({
        tpl: "#private-template",
        vm_tpl: "#private-machine-template",
        vm_id_tpl: "#network-{0}-vm-{1}"
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
                nv = this.create_network_view(net)
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
            nv.update_vms();
            nv.update_layout();
        },
        
        create_network_view: function(net) {
            if (net.is_public()) {
                return new views.PublicNetworkView(net, this);
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
                if (net.get("status") == "DELETED") { return }
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
                view.remove();
                delete this.network_views[net.id];
            }
        },

        __update_layout: function() {
        }
    });

})(this);
