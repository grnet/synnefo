// Copyright (C) 2010-2015 GRNET S.A. and individual contributors
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
    var hasKey = Object.prototype.hasOwnProperty;
        
    views.SingleListViewMixin = {
        
        toggler_id: 'ips',

        init_togglers: function() {
            var self = this;

            this._open = false;
            this.vm_el = $(this.options.vm_view);
            this.tags_toggler = this.vm_el.find(".tags-header");
            this.tags_content = this.vm_el.find(".tags-content");
            this.toggler = this.vm_el.find(
                ".toggler-header." + this.toggler_id);
            this.toggler_content = this.vm_el.find(
                "."+this.toggler_id+"-content");
            this.toggler_content.hide();
            this.other_togglers = this.vm_el.find(".cont-toggler-wrapper");

            $(this.el).show();
            
            this.other_togglers.click(function() {
                var toggler = $(this);
                if (!toggler.hasClass(self.toggler_id) && self._open) {
                        self.toggle();
                }
            });

            this.toggler.click(function() {
                var disabled = self.toggler.parent().find(
                    ".cont-toggler-wrapper").hasClass("disabled");
                if (disabled) { return; }
                self.toggle();
            });

            this.tags_toggler.click(function() {
                self.toggler.find(".toggler").removeClass("open");
                self.toggler_content.slideUp(f);
                var f = function() { 
                    self.hide(true);
                }
                self._open = false;
            });
        },

        toggle: function() {
            var self = this;
            this._open = !this._open;

            if (this._open) {
                this.show(true);
                this.tags_toggler.find(".toggler").removeClass("open");
                this.tags_content.slideUp();
                this.toggler.find(".toggler").addClass("open");
                this.toggler_content.removeClass(".hidden").slideDown();
            } else {
                this.toggler.find(".toggler").removeClass("open");
                var f = function() { self.hide(true) }
                this.toggler_content.removeClass(".hidden").slideUp();
            }
        }
    };

    views.VMSingleVolumesListView = views.VMVolumeListView.extend(_.extend({
        init: function() {
            views.VMSingleVolumesListView.__super__.init.apply(this);
            this.init_togglers();
        },

        hide: function() {
            views.VMSingleVolumesListView.__super__.init.apply(this);
            this._open = false;
        }
    }, views.SingleListViewMixin, {
        toggler_id: 'ips'                                                                     
    }));

    views.VMSinglePortListView = views.VMPortListView.extend(_.extend({
        init: function() {
            views.VMSinglePortListView.__super__.init.apply(this);
            this.init_togglers();
        },

        hide: function() {
            views.VMSingleVolumesListView.__super__.init.apply(this);
            this._open = false;
        }
    }, views.SingleListViewMixin, {
        toggler_id: 'volumes'                                                        
    }));

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
            if (this.vm(this.current_vm).get('id_ghost')) { return }
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
            this.ports_views = this.ports_views || {};
            this.volumes_views = this.volumes_views || {};

            //this.stats_views[vm.id] = new views.IconStatsView(vm, this);

            // same as icon view
            this.action_views[vm.id] = new views.VMActionsView(vm, this, this.vm(vm), this.hide_actions);
            this.stats_views[vm.id] = new views.VMStatsView(vm, this, {stats_type: 'series'});
            this.connect_views[vm.id] = new views.IconVMConnectView(vm, this);
            this.tags_views[vm.id] = new views.VMTagsView(vm, this, true, 20, 10, 35);
            this.details_views[vm.id] = new views.SingleDetailsView(vm, this);
            this.action_error_views[vm.id] = new views.VMActionErrorView(vm, this);

            var ports_container = this.vm(vm).find(".ips-content");
            var ports_toggler = this.vm(vm).find(".toggler-header.ips");

            var volumes_container = this.vm(vm).find(".volumes-content");
            var volumes_toggler = this.vm(vm).find(".toggler-header.volumes");

            var ports_view = new views.VMSinglePortListView({
              vm_view: this.vm(vm),
              collection: vm.ports,
              container: ports_container,
              parent: this,
              truncate: 50
            });
            this.ports_views[vm.id] = ports_view
            ports_view.show();

            var volumes_view = new views.VMSingleVolumesListView({
              vm_view: this.vm(vm),
              collection: vm.volumes, 
              container: volumes_container,
              parent: this,
              truncate: 50
            });
            this.volumes_views[vm.id] = volumes_view;
            volumes_view.show();

            if (storage.vms.models.length > 1) { this.vm(vm).hide(); };
        },

        post_update_vm: function(vm) {
          if (vm.in_error_state()) {
            var view = this.ports_views[vm.id];
            view.toggler.find(".toggler").removeClass("open");
            view.toggler_content.hide();
            view.hide(true);
            view.open = false;
          }
        },
        
        hide_vm: function(vm) {
            this.vm(vm).hide();
        },

        // vm specific event handlers
        set_vm_handlers: function(vm) {
        },
        
        // handle selected vm
        show_current: function() {
            var index = this.current_vm;
            var vm = storage.vms.at(index);

            this.$(".server-name").removeClass("column3-selected");
            
            _.each(storage.vms.models, function(vmo){
                if (vm && (vm.id != vmo.id)) {
                    if (!hasKey.call(this._vm_els, vmo.id)) { return };
                    this.hide_vm(vmo);
                }
            }, this);

            if (vm) { this.vm(vm).show(); };

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

            var project = vm.get('project');
            if (project) {
              el.find(".project-name").text(_.truncate(project.get('name'), 20));
            }
            // truncate name
            el.find(".machine-detail.name").text(util.truncate(vm.get("name"), 45));
            el.find(".fqdn").val(vm.get("fqdn") || vm.get_hostname());
            // set the state (i18n ??)
            el.find(".state-label").text(STATE_TEXTS[vm.state()]);
            // set state class
            el.find(".state").removeClass().addClass(views.SingleView.STATE_CLASSES[vm.state()].join(" "));
            // os icon
            el.find(".single-image").css({'background-image': "url(" + this.get_vm_icon_path(vm, "medium") + ")"});

            var logo = el.find('.single-image');
            if (vm.get('is_ghost')) {
              logo.addClass('logo-ghost');
            } else {
              logo.removeClass('logo-ghost');
            }

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
        'UNKNOWN':          ['state', 'unknown-state'],
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
        'ATTACH_VOLUME':    ['state', 'connecting-state'],
        'DETACH_VOLUME':    ['state', 'disconnecting-state'],
        'RESIZE':           ['state', 'rebooting-state']
    };

})(this);
