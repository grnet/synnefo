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
        },

        set_handlers: function() {
            var self = this;
            storage.vms.bind("change:pending_action", function() {
                if (!storage.vms.has_pending_actions()) {
                    self.parent.$(".actions a").removeClass("selected");
                }
            })
            
            var self = this;
            this.parent.$(".actions a.enabled").live('click', function() {
                self.parent.$(".actions a").removeClass("selected");
                $(this).addClass("selected");
                self.parent.select_action($(this).attr("id").replace("action-",""));
            })
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

        update_layout: function() {
            this.update_actions();
        }
    });

    // VMs list view
    views.ListView = views.VMListView.extend({
        
        // view id (this could be used to identify 
        // the view object from global context
        view_id: 'vm_list',

        el: '#machinesview-list',
        id_tpl: 'list-vm-{0}',
        link_id_tpl: 'list-vm-at-{0}',

        hide_actions: false,

        selectors: {
            'vms': '.list-container',
            'vm': '#list-vm-{0}',
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
            //init_action_indicator_handlers('list');

            this.$(".list-vm-checkbox").live('change', _.bind(function(){
                this.reset_actions();
                this.actions.update_layout();
                if (this.$("tbody input:checked").length > 0) {
                    this.select_all.attr("checked", true);
                } else {
                    this.select_all.attr("checked", false);
                }
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
            $(this.table.fnGetNodes(index)).attr("id", this.id_tpl.format(vm.id));
            
            // hide indicators on creation
            this.vm(vm).find(".spinner").hide();
            this.vm(vm).find(".wave").hide();
            this.vm(vm).find(".os_icon").show();
            
            // ancestor method
            this.__set_vm_handlers(vm);
            this.set_vm_handlers(vm);
            this.post_add(vm);
        },

        // remove vm
        remove_vm: function(vm) {
            var index = this.table_data["vm_" + vm.id].index;
            this.table.fnDeleteRow(index);
            delete this.table_data["vm_" + vm.id];
            this.update_data();
        },

        update_data: function() {
            var new_data = this.table.fnGetData();
            _.each(new_data, _.bind(function(row, i){
                this.table_data["vm_" + row[5]].index = i;
                this.table_data["vm_" + row[5]].params = row;
            }, this));
        },

        get_vm_table_data: function(vm) {
            var checkbox = '<input type="checkbox" class="' + 
                views.ListView.STATE_CLASSES[vm.state()].join(" ") + 
                ' list-vm-checkbox" id="checkbox-' + this.id_tpl.format(vm.id) + '"/>';

            var img = '<img class="os_icon" src="'+ this.get_vm_icon_path(vm, "small") +'" />';
            img = img + '<img src="static/icons/indicators/small/progress.gif" class="spinner" />';
            img = img + '<img src="static/icons/indicators/medium/wave.gif" class="wave" />';

            var name = util.truncate(vm.get('name'), 20);
            var flavor = vm.get_flavor().details_string();
            var status = STATE_TEXTS[vm.state()];
            
            return [checkbox, img, name, flavor, status, vm.id];
        },

        post_add: function(vm) {
        },

        // is vm in transition ??? show the progress spinner
        update_transition_state: function(vm) {
            if (vm.in_transition()){
                this.sel('vm_spinner', vm.id).show();
                this.sel('vm_wave', vm.id).hide();
                this.sel('os_icon', vm.id).hide();
            } else {
                this.sel('vm_spinner', vm.id).hide();
            }
        },

        // display transition animations
        show_transition: function(vm) {
            var wave = this.sel('vm_wave', vm.id);
            if (!wave.length) {
                return
            }
            
            this.sel('vm_spinner', vm.id).hide();
            this.sel('os_icon', vm.id).hide();

            var src = wave.attr('src');
            var self = this;

            // change src to force gif play from the first frame
            // animate for 500 ms then hide
            wave.attr('src', "").show().attr('src', src).fadeIn(500).delay(700).fadeOut(300, function() {
                if (vm.in_transition()) {
                    self.sel("vm_spinner", vm.id).fadeIn(200);
                } else {
                    self.sel("os_icon", vm.id).fadeIn(200);
                }
            });
        },

        update_actions_layout: function(vm) {
        },

        post_update_vm: function(vm) {
            var index = this.table_data["vm_" + vm.id].index;
            params = this.get_vm_table_data(vm);
            this.table_data["vm_" + vm.id].params = params;
            data = this.table.fnGetData()[index];

            // do not recreate checkboxes and images to avoid messing
            // with user interaction
            this.table.fnUpdate(params[2], parseInt(index), 2);
            this.table.fnUpdate(params[3], parseInt(index), 3);
            this.table.fnUpdate(params[4], parseInt(index), 4);
            
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
                os = "unknown";
            }
            return os;
        },

        // TODO: move to views.utils (the method and the VM_OS_ICON vars)
        get_vm_icon_path: function(vm, icon_type) {
            var os = vm.get_os();
            var icons = window.os_icons || views.ListView.VM_OS_ICONS;

            if (icons.indexOf(os) == -1) {
                os = "unknown";
            }
            
            var st = "off";
            if (vm.is_active()) {
                st = "on"
            }

            return views.ListView.VM_OS_ICON_TPLS[icon_type].format(os, st);
        }
    })

    views.ListView.VM_OS_ICON_TPLS = {
        "small": "/static/icons/machines/small/{0}-{1}.png"
    }

    views.ListView.VM_OS_ICONS = window.os_icons || [];

    views.ListView.STATE_CLASSES = {
        'UNKNOWN':          ['error-state'],
        'BUILD':            ['build-state'],
        'REBOOT':           ['rebooting-state'],
        'STOPPED':          ['terminated-state'],
        'ACTIVE':           ['running-state'],
        'ERROR':            ['error-state'],
        'DELETE':           ['destroying-state'],
        'DESTROY':          ['destroying-state'],
        'BUILD_INIT':       ['build-state'], 
        'BUILD_COPY':       ['build-state'],
        'BUILD_FINAL':      ['build-state'],
        'SHUTDOWN':         ['shutting-state'],
        'START':            ['starting-state'],
        'CONNECT':          ['connecting-state'],
        'DISCONNECT':       ['disconnecting-state']
    };

})(this);
