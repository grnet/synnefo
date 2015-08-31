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

    views.ListMultipleActions = views.View.extend({
        
        view_id: "list_actions",

        initialize: function(view) {
            this.parent = view;
            this.el = this.parent.el;
           
            views.ListMultipleActions.__super__.initialize.call(this);
            this.set_handlers();
            this.update_layout();

            this.selected_action = undefined;
            this.available_actions = [];
            this.multi_view = synnefo.ui.main.multiple_actions_view;
            this.hovered = false;

            this.update_actions = _.throttle(this.update_actions, 100);
        },

        set_handlers: function() {
            var self = this;
            storage.vms.bind("change:pending_action", function() {
                if (!storage.vms.has_pending_actions()) {
                    self.parent.$(".actions a").removeClass("selected");
                    self.parent.clear_indicators();
                }
            });
            
            var self = this;
            this.parent.$(".actions a.enabled").live('click', function() {
                self.parent.$(".actions a").removeClass("selected");
                $(this).addClass("selected");
                self.parent.select_action($(this).attr("id").replace("action-",""));
            });

            this.parent.$(".actions a.enabled").live({
                'mouseenter': function() {
                    self.hovered = true;
                    self.parent.set_indicator_for($(this).attr("id").replace("action-",""));
                }, 
                'mouseleave': function() {
                    self.hovered = false;
                    self.parent.clear_indicators();
                }
            });
        },
        
        update_actions: function() {
            actions = undefined;
            this.available_actions = [];
            _.each(this.parent.get_selected_vms(), function(vm) {
                if (!actions) {
                    actions = vm.get_available_actions();
                    return;
                }
                actions = _.intersection(actions, vm.get_available_actions());
            });

            this.available_actions = actions;

            this.$(".actions a").removeClass("enabled");
            _.each(this.available_actions, _.bind(function(name){
                this.$("#action-" + name).addClass("enabled");
            }, this))
        },

        update_selected: function() {
            this.$("tr").removeClass("checked");
            this.$("tr input:checked").parent().parent().addClass("checked");
        },

        update_layout: function() {
            this.update_actions();
            this.update_selected();
        }
    });

    // VMs list view
    views.ListView = views.VMListView.extend({
        
        // view id (this could be used to identify 
        // the view object from global context
        view_id: 'vm_list',

        el: '#machinesview-list',
        id_tpl: 'list-vm-',
        link_id_tpl: 'list-vm-at-',

        hide_actions: false,

        selectors: {
            'vms': '.list-container',
            'vm': '#list-vm-',
            'view': '#machinesview-list',
            'tpl': '.list-container#machine-container-template',
            'spinner': '.large-spinner',
            'vm_spinner': '#list-vm-{0} .spinner',
            'vm_wave': '#list-vm-{0} .wave',
            'os_icon': '#list-vm-{0} .os_icon',
            'vm_cont_active': '#machinesview-list',
            'vm_cont_terminated': '#machinesview-list'
        },
        
        initialize: function() {
            this.current_vm = 0;
            
            // button selectors
            this.prev_button = this.$(".controls .previous");
            this.next_button = this.$(".controls .next");

            this.actions = this.$(".actions").show();
            this.datatable_cont = this.$(".dataTables_wrapper").show();
            this.content = this.$("#machinesview_content").show();
            this.filter = this.$(".dataTables_filter").show().css({'display':'block'});
            this.table_el = this.$(".list-machines").show();
            this.select_all = $("#list-view-select-all");

            this.actions = new views.ListMultipleActions(this);

            this.table = $("div.list table.list-machines").dataTable({
                "bInfo": false,
                "bRetrieve": true,
                "bPaginate": false,
                "bAutoWidth": false,
                "bSort": true,
                "bStateSave": true,
                "sScrollXInner": "500px",
                "aoColumnDefs": [
                    { "bSortable": false, "aTargets": [ 0 ] }
                ]
            });

            this.table_data = {};
            views.ListView.__super__.initialize.apply(this, arguments);

            this.update_layout = _.throttle(this.update_layout, 100);
        },
        
        reset: function() {
        },

        hide_actions: function() {
            this.$(".actions a").removeClass("selected");
        },

        // overload show function
        show_view: function() {
            this.log.debug("showing");
            this.sel('spinner').hide();
            this.__update_layout();
        },
        
        check_vm_container: function() {
        },

        // identify vm model instance id based on DOM element
        vm_id_for_element: function(el) {
            return el.attr('id').replace("list-vm-", "");
        },

        reset_actions: function() {
            this.$(".actions a").removeClass("selected");
            storage.vms.reset_pending_actions();
        },
        
        // set generic view handlers
        set_handlers: function() {
            this.$(".list-vm-checkbox").live('change', _.bind(function(){
                this.reset_actions();
                this.actions.update_layout();
                if (this.$("tbody input:checked").length > 0) {
                    this.select_all.attr("checked", true);
                } else {
                    this.select_all.attr("checked", false);
                }
                self.actions.update_layout();
            }, this))

            var self = this;
            this.select_all.click(function(){
                if ($(this).is(":checked")) {
                    self.$("tbody input").attr("checked", true);
                } else {
                    self.$("tbody input").attr("checked", false);
                }
                self.actions.update_layout();
            });
        },  

        get_selected_vms: function() {
            var selected = $(this.el).find(".list-vm-checkbox:checked");
            var vms = []
            _.each(selected, function(el){
                var id = parseInt($(el).attr("id").replace("checkbox-list-vm-", ""));
                vm = storage.vms.get(id);
                if (!vm) { return };
                vms.push(vm);
            });

            return vms;
        },

        select_action: function(action) {
            this.reset_actions();
            this.$(".actions a#action-" + action).addClass("selected");
            var vms = this.get_selected_vms();
            _.each(vms, function(vm){
                vm.update_pending_action(action);
            })
        },

        reset: function() {
            this.reset_actions();
        },

        create_vm: function(vm) {
            params = this.get_vm_table_data(vm);
            var index = this.table.fnAddData.call(this.table, params);
            this.table_data["vm_" + vm.id] = {index: index[0], params: params};
            // append row id
            $(this.table.fnGetNodes(index)).attr("id", this.id_tpl + vm.id);
                
            var vm_el = $("#" + this.id_tpl + vm.id);
            this._vm_els[vm.id] = vm_el;
            // hide indicators on creation
            this.vm(vm).find(".spinner").hide();
            this.vm(vm).find(".wave").hide();
            this.vm(vm).find(".os_icon").show();
            this.vm(vm).find(".action-indicator").hide();
            
            // ancestor method
            this.__set_vm_handlers(vm);
            this.post_add(vm);
            return this.vm(vm);
        },

        // remove vm
        remove_vm: function(vm) {
            this.vm(vm).find("input[type=checkbox]").removeAttr("checked");
            var vm_data = this.table_data["vm_" + vm.id];

            // update triggered on removed vm, skipping
            if (!vm_data) { return };

            var index = vm_data.index;
            this.table.fnDeleteRow(index);
            delete this.table_data["vm_" + vm.id];
            this.update_data();

            if (hasKey.call(this._vm_els, vm.id)) {
                delete this._vm_els[vm.id];
            }
        },

        update_data: function() {
            var new_data = this.table.fnGetData();
            _.each(new_data, _.bind(function(row, i){
                this.table_data["vm_" + row[5]].index = i;
                this.table_data["vm_" + row[5]].params = row;
            }, this));
        },

        set_indicator_for: function(action) {
            var vms = this.get_selected_vms();
            _.each(vms, _.bind(function(vm){
                var vmel = this.vm(vm);
                vmel.find("img.spinner, img.wave, img.os_icon").hide();
                vmel.find("span.action-indicator").show().removeClass().addClass(action + " action-indicator");
            }, this));
        },

        clear_indicators: function() {
            var vms = storage.vms.models;
            _.each(vms, _.bind(function(vm){
                var vmel = this.vm(vm);

                vmel.find("img.wave").hide();
                
                if (vm.pending_action) {
                    vmel.find("img.os_icon").hide();
                    vmel.find("span.action-indicator").show().removeClass().addClass(vm.pending_action + " action-indicator");
                    return;
                }

                if (vm.in_transition()) {
                    vmel.find("span.action-indicator").hide();
                    vmel.find("img.spinner").show();
                    return;
                }

                if (!this.actions.hovered) {
                    vmel.find("img.os_icon").show();
                    vmel.find("span.action-indicator").hide();
                    vmel.find("img.spinner").hide();
                }
                

            }, this));
        },

        get_vm_table_data: function(vm) {
            var cls = views.ListView.STATE_CLASSES[vm.state()] || [];
            var checkbox = '<input type="checkbox" class="' + 
                cls.join(" ") + 
                ' list-vm-checkbox" id="checkbox-' + this.id_tpl + vm.id + '"/>';

            var img = '<img class="os_icon" src="'+ this.get_vm_icon_path(vm, "small") +'" />';
            img = img + '<img src="'+snf.config.indicators_icons_url+'small/progress.gif" class="spinner" />';
            img = img + '<img src="'+snf.config.indicators_icons_url+'medium/wave.gif" class="wave" />';
            img = img + '<span class="action-indicator" />';

            var name;
            var flavor;

            if (vm.get('is_ghost')) {
              name = "Unknown"
              flavor = "Unknown";
            } else {
              name = _.escape(util.truncate(vm.get('name'), 25));
              flavor = vm.get_flavor().details_string();
            }

            var status = STATE_TEXTS[vm.state()];
            
            return [checkbox, img, name, flavor, status, vm.id];
        },

        post_add: function(vm) {
        },

        // is vm in transition ??? show the progress spinner
        update_transition_state: function(vm) {
            if (!vm) { return };
            if (this.in_transition) { return };
            
            if ((this.actions.hovered && this.vm(vm).find("input").is(":checked")) || vm.pending_action) {
                this.sel('vm_spinner', vm.id).hide();
                this.sel('vm_wave', vm.id).hide();
                this.sel('os_icon', vm.id).hide();
                this.vm(vm).find(".action-indicator").show();
                return;
            }

            if (vm.in_transition()){
                this.sel('vm_spinner', vm.id).show();
                this.sel('vm_wave', vm.id).hide();
                this.sel('os_icon', vm.id).hide();
                this.vm(vm).find(".action-indicator").hide();
            } else {
                this.sel('vm_spinner', vm.id).hide();
                this.vm(vm).find(".action-indicator").hide();
                this.sel('os_icon', vm.id).show();
            }
        },

        // display transition animations
        show_transition: function(vm) {
            this.in_transition = true;

            if (!this.visible()) { 
                this.in_transition = false; 
                this.update_transition_state(); 
                return 
            };

            var wave = this.sel('vm_wave', vm.id);
            if (!wave.length) {
                this.in_transition = false
                return
            }
            
            this.sel('vm_spinner', vm.id).hide();
            this.sel('os_icon', vm.id).hide();

            var src = wave.attr('src');
            var self = this;
            
            // change src to force gif play from the first frame
            // animate for 500 ms then hide
            wave.attr('src', "").show().attr('src', src).fadeIn(500).delay(700).fadeOut(300, function() {
                self.in_transition = false;
                self.update_transition_state(vm);
            });
        },

        update_actions_layout: function(vm) {
        },

        post_update_vm: function(vm) {
            
            // skip update for these changes for performance issues
            if (vm.hasOnlyChange(["pending_action", "stats"])) { return };

            var index = this.table_data["vm_" + vm.id].index;
            params = this.get_vm_table_data(vm);
            this.table_data["vm_" + vm.id].params = params;
            data = this.table.fnGetData()[index];

            // do not recreate checkboxes and images to avoid messing
            // with user interaction
            this.table.fnUpdate(params[2], parseInt(index), 2);
            this.table.fnUpdate(params[3], parseInt(index), 3);
            this.table.fnUpdate(params[4], parseInt(index), 4);

            var active_class = vm.is_active() ? "active" : "inactive";
            this.vm(vm).removeClass("active").removeClass("inactive").addClass(active_class);
            $(this.vm(vm).find("td").get(4)).addClass("status");
            $(this.vm(vm).find("td").get(3)).addClass("flavor");
            $(this.vm(vm).find("td").get(2)).addClass("name");

            if (vm.status() == "ERROR") {
                this.vm(vm).removeClass("active").removeClass("inactive").addClass("error");
            } else {
                this.vm(vm).removeClass("error").addClass(active_class);
            }
            
            this.update_os_icon(vm);
            this.update_transition_state(vm);
        },

        update_os_icon: function(vm) {
            this.sel('os_icon', vm.id).attr('src', this.get_vm_icon_path(vm, "small"));
        },
        
        // vm specific event handlers
        set_vm_handlers: function(vm) {
        },

        // generic stuff to do on each view update
        // called once after each vm has been updated
        update_layout: function() {
            this.actions.update_layout();
        },

        // update vm details
        update_details: function(vm) {
        },
            
        get_vm_icon_os: function(vm) {
            var os = vm.get_os();
            var icons = window.os_icons || views.ListView.VM_OS_ICONS;
            if (icons.indexOf(os) == -1) {
                os = snf.config.unknown_os;
            }
            return os;
        },

        // TODO: move to views.utils (the method and the VM_OS_ICON vars)
        get_vm_icon_path: function(vm, icon_type) {
            var os = vm.get_os();
            var icons = window.os_icons || views.ListView.VM_OS_ICONS;

            if (icons.indexOf(os) == -1) {
                os = snf.config.unknown_os;
            }
            
            var st = "off";
            if (vm.is_active()) {
                st = "on"
            }

            return views.ListView.VM_OS_ICON_TPLS()[icon_type].format(os, st);
        }
    });

    views.ListView.VM_OS_ICON_TPLS = function() {
        return {
            "small": snf.config.machines_icons_url + "small/{0}-{1}.png"
        }
    }

    views.ListView.VM_OS_ICONS = window.os_icons || [];

    views.ListView.STATE_CLASSES = {
        'UNKNOWN':          ['unknown-state'],
        'BUILD':            ['build-state'],
        'REBOOT':           ['rebooting-state'],
        'STOPPED':          ['terminated-state'],
        'ACTIVE':           ['running-state'],
        'ERROR':            ['error-state'],
        'DELETED':          ['destroying-state'],
        'DESTROY':          ['destroying-state'],
        'SHUTDOWN':         ['shutting-state'],
        'START':            ['starting-state'],
        'CONNECT':          ['connecting-state'],
        'DISCONNECT':       ['disconnecting-state'],
        'ATTACH_VOLUME':    ['connecting-state'],
        'DETACH_VOLUME':    ['disconnecting-state'],
        'RESIZE':           ['rebooting-state']
    };

})(this);
