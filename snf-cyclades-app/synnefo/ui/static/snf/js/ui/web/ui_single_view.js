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
    var hasKey = Object.prototype.hasOwnProperty;

    views.SingleDetailsView = views.VMDetailsView.extend({
    
        view_id: "vm_details_single",
        el_sel: '.machine-details',
        
        selectors: {
            'cpu': '.machine-detail.cpus',
            'ram': '.machine-detail.ram',
            'disk': '.machine-detail.disk',
            'image_name': '.machine-detail.image-name',
            'image_size': '.machine-detail.image-size'
        }
    
    })

    // VMs single view
    views.SingleView = views.VMListView.extend({
        
        // view id (this could be used to identify 
        // the view object from global context
        view_id: 'vm_single',

        el: '#machinesview-single',
        id_tpl: 'single-vm-',
        link_id_tpl: 'single-vm-at-',

        hide_actions: false,

        selectors: {
            'vms': '.single-container',
            'vm': '#single-vm-',
            'view': '#machinesview-single',
            'tpl': '.single-container-template',
            'spinner': '.large-spinner',
            'vm_spinner': '#single-vm-{0} .state .spinner',
            'vm_wave': '#single-vm-{0} img.wave',
            'vm_cont_active': '#machinesview-single',
            'vm_cont_terminated': '#machinesview-single'
        },
        
        initialize: function() {
            this.current_vm = 0;
            
            // button selectors
            this.prev_button = this.$(".controls .previous");
            this.next_button = this.$(".controls .next");
            this.menu = $("#single-servers-list");

            views.SingleView.__super__.initialize.apply(this, arguments);
            this.update_current_vm();
        },

        // overload show function
        show: function() {
            views.SingleView.__super__.show.apply(this, arguments);
            this.log.debug("showing");
            this.$(".column3").show();
            this.show_vm_menu();
            this.show_current();
        },

        show_vm: function(vm) {
            if (!vm) { return };
            this.current_vm_instance = vm;
            this.show_vm_menu();
            this.show_current();
            this.update_layout();
        },

        // identify vm model instance id based on DOM element
        vm_id_for_element: function(el) {
            return el.attr('id').replace("single-vm-", "");
        },
        
        // set generic view handlers
        set_handlers: function() {
            this.prev_button.click(_.bind(function(ev){
                storage.vms.reset_pending_actions();
                ev.preventDefault();
                this.show_prev();
            }, this));

            this.next_button.click(_.bind(function(ev){
                storage.vms.reset_pending_actions();
                ev.preventDefault();
                this.show_next();
            }, this));
        },  

        update_current_vm: function() {
            try {
                this.current_vm_instance = storage.vms.at(this.current_vm);
                this.current_vm_instance.start_stats_update(true);
                storage.vms.stop_stats_update([this.current_vm_instance]);
            } catch (err) {
                this.log.debug("Cannot select current vm instance for: {0}".format(this.current_vm));
                this.current_vm_instance = undefined;
                this.current_vm = 0;
            }
        },

        show_next: function() {
            this.current_vm++;
            if (this.current_vm >= storage.vms.models.length) {
                this.current_vm = 0;
            }
            
            this.update_current_vm();

            // this might fail when vms get empty
            // catch the exception
            try {
                snf.router.vm_details_view(this.current_vm_instance.id);
            } catch (err) {};
        },

        show_prev: function() {
            this.current_vm--;
            if (this.current_vm < 0) {
                this.current_vm = storage.vms.length - 1;
            }

            this.update_current_vm();
            snf.router.vm_details_view(this.current_vm_instance.id);
        },

        post_remove_vm: function(vm) {
            // current vm removed or does not exist after an update
            this.show_vm_menu();
            if (!this.current_vm_instance || this.current_vm_instance.id == vm.id) {
                this.current_vm++;
                if (this.current_vm >= storage.vms.models.length) {
                    this.current_vm = 0;
                }
                this.update_current_vm();
                this.show_current();
            // this might fail when vms get empty
            // catch the exception
            } else {
                this.show_current();
            }
        },
        
        // stuff to do when a new vm has been created.
        // - create vm subviews
        post_add: function(vm) {
            this.vm(vm).removeClass("single-container-template");
            this.show_vm_menu();
            this.show_current();

            // rename views index
            this.stats_views = this.stats_views || {};
            this.connect_views = this.connect_views || {};
            this.tags_views = this.tags_views || {};
            this.details_views = this.details_views || {};
            this.action_views = this.action_views || {};
            this.action_error_views = this.action_error_views || {};

            //this.stats_views[vm.id] = new views.IconStatsView(vm, this);

            // same as icon view
            this.action_views[vm.id] = new views.VMActionsView(vm, this, this.vm(vm), this.hide_actions);
            this.stats_views[vm.id] = new views.VMStatsView(vm, this, {stats_type: 'series'});
            this.connect_views[vm.id] = new views.IconVMConnectView(vm, this);
            this.tags_views[vm.id] = new views.VMTagsView(vm, this, true, 20, 10, 35);
            this.details_views[vm.id] = new views.SingleDetailsView(vm, this);
            this.action_error_views[vm.id] = new views.VMActionErrorView(vm, this);
            
            if (storage.vms.models.length > 1) { this.vm(vm).hide(); };
        },

        post_update_vm: function(vm) {
        },
        
        // vm specific event handlers
        set_vm_handlers: function(vm) {
        },
        
        // handle selected vm
        show_current: function() {
            var index = this.current_vm;
            var vm = storage.vms.at(index);

            this.$(".server-name").removeClass("column3-selected");
            
            if (vm) {
                this.vm(vm).show();
            };

            _.each(storage.vms.models, function(vmo){
                if (vm && (vm.id != vmo.id)) {
                    if (!hasKey.call(this._vm_els, vmo.id)) { return };
                    this.vm(vmo).hide();
                }
            }, this)

            if (!vm) {
                // empty list
                this.$(".column3").hide();
                return;
            }
            this.$(".column3").show();


            $("#" + this.link_id_tpl + this.current_vm).addClass("column3-selected");
            try {
                this.update_details(vm);
            } catch (err) {};
        },

        show_vm_menu: function() {
            this.menu.find(".server-name").remove();

            _.each(storage.vms.models, function(vm, index) {
                var el = $('<div class="server-name" id="'+this.link_id_tpl + index +'">' + 
                               util.truncate(vm.escape("name"),16)+'</div>')
                this.menu.append(el);

                vm.bind("change:name", function(){
                  el.html(util.truncate(vm.escape("name"), 16));
                })

                if (this.current_vm_instance && vm.id == this.current_vm_instance.id) {
                    this.current_vm = index;
                }
            }, this);
            
            var self = this;
            this.menu.find(".server-name").click(function(ev) {
                ev.preventDefault();
                var id = $(this).attr("id").replace("single-vm-at-", "");
                if (self.current_vm != id) {
                    storage.vms.reset_pending_actions();
                }
                self.current_vm = id;
                self.update_current_vm();
                snf.router.vm_details_view(self.current_vm_instance.id);
            })
        },

        // generic stuff to do on each view update
        // called once after each vm has been updated
        update_layout: function() {
            this.update_current_vm();
            fix_v6_addresses();
        },

        update_status_message: function(vm) {
            var el = this.vm(vm);
            var message = vm.get_status_message();
            if (message) {
                // update bulding progress
                el.find("div.machine-ips").hide();
                el.find("div.build-progress").show();
                el.find("div.build-progress .message").text(message);
                if (vm.in_error_state()) {
                    el.find("div.build-progress .btn").show();
                } else {
                    el.find("div.build-progress .btn").hide();
                }
            } else {
                // hide building progress
                el.find("div.machine-ips").show()
                el.find("div.build-progress").hide();
                el.find("div.build-progress .btn").hide();
            }
        },

        // update vm details
        update_details: function(vm) {
            var el = this.vm(vm);
            if (vm != this.current_vm_instance) { return };

            // truncate name
            el.find(".machine-detail.name").text(util.truncate(vm.get("name"), 35));
            el.find(".fqdn").text(vm.get("fqdn"));
            // set the state (i18n ??)
            el.find(".state-label").text(STATE_TEXTS[vm.state()]);
            // set state class
            el.find(".state").removeClass().addClass(views.SingleView.STATE_CLASSES[vm.state()].join(" "));
            // os icon
            el.find(".single-image").css({'background-image': "url(" + this.get_vm_icon_path(vm, "medium") + ")"});
            
            el.removeClass("connectable");
            if (vm.is_connectable()) {
                el.addClass("connectable");
            }

            this.update_status_message(vm);

            icon_state = vm.is_active() ? "on" : "off";
            set_machine_os_image(el, "single", icon_state, this.get_vm_icon_os(vm));
            
            // update subviews
            this.action_views[vm.id].update_layout();
            this.stats_views[vm.id].update_layout();
            this.connect_views[vm.id].update_layout();
            this.tags_views[vm.id].update_layout();
            this.details_views[vm.id].update_layout();
        },
            
        get_vm_icon_os: function(vm) {
            var os = vm.get_os();
            var icons = window.os_icons || views.SingleView.VM_OS_ICONS;
            if (icons.indexOf(os) == -1) {
                os = "unknown";
            }
            return os;
        },

        // TODO: move to views.utils (the method and the VM_OS_ICON vars)
        get_vm_icon_path: function(vm, icon_type) {
            var os = vm.get_os();
            var icons = window.os_icons || views.SingleView.VM_OS_ICONS;

            if (icons.indexOf(os) == -1) {
                os = "unknown";
            }

            return views.SingleView.VM_OS_ICON_TPLS()[icon_type].format(os);
        }
    })

    views.SingleView.VM_OS_ICON_TPLS = function() {
        return {
            "medium": snf.config.machines_icons_url + "large/{0}-sprite.png"
        }
    }

    views.SingleView.VM_OS_ICONS = window.os_icons || [];

    views.SingleView.STATE_CLASSES = {
        'UNKNOWN':          ['state', 'error-state'],
        'BUILD':            ['state', 'build-state'],
        'REBOOT':           ['state', 'rebooting-state'],
        'STOPPED':          ['state', 'terminated-state'],
        'ACTIVE':           ['state', 'running-state'],
        'ERROR':            ['state', 'error-state'],
        'DELETED':          ['state', 'destroying-state'],
        'DESTROY':          ['state', 'destroying-state'],
        'SHUTDOWN':         ['state', 'shutting-state'],
        'START':            ['state', 'starting-state'],
        'CONNECT':          ['state', 'connecting-state'],
        'DISCONNECT':       ['state', 'disconnecting-state'],
        'RESIZE':           ['state', 'rebooting-state']
    };

})(this);
