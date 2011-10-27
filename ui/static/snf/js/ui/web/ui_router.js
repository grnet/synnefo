;(function(root){

    // root
    var root = root;
    
    // setup namepsaces
    var snf = root.synnefo = root.synnefo || {};
    var models = snf.models = snf.models || {}
    var storage = snf.storage = snf.storage || {};
    var ui = snf.ui = snf.ui || {};

    var views = snf.views = snf.views || {}

    // shortcuts
    var bb = root.Backbone;
    var util = snf.util;

    var WebAppRouter = Backbone.Router.extend({
        
        last_vm_view: "vms_icon_view",

        routes: {
            "":                                 "index",
            "welcome/":                         "show_welcome",

            // vm views
            "machines/icon/":                   "vms_icon_view",
            "machines/list/":                   "vms_list_view",
            "machines/single/details/:vm":      "vm_details_view",
            "machines/single/":                 "vms_single_view",
            "machines/create/":                 "vms_create_view",
            "machines/create/:step":            "vms_create_view",

            // network views
            "machines/single/":                 "vms_single_view",
        },
        
        show_welcome: function() {
            if (snf.storage.vms.length == 0) {
                ui.main.show_empty();
                this.navigate("welcome/");
            } else {
                this.index();
            }
        },

        index: function() {
            this.vms_index();
        },

        vms_index: function() {
            this[this.last_vm_view]();
        },

        vms_icon_view: function() {
            this.navigate("machines/icon/");
            this.last_vm_view = "vms_icon_view";
            ui.main.show_view("icon");
        },
        
        vms_list_view: function() {
            this.navigate("machines/list/");
            this.last_vm_view = "vms_list_view";
            ui.main.show_view("list");
        },

        vms_single_view: function() {
            //this.navigate("machines/single/");
            this.last_vm_view = "vms_single_view";
            ui.main.show_view("single");
            try {
                var current_vm = ui.main.current_view.current_vm_instance.id;
                this.vm_details_view(current_vm);
            } catch (err) {
                this.show_welcome();
            }
        },

        vm_create_view: function(step) {
            ui.main.create_vm_view.show();
            if (step) {
                ui.main.create_vm_view.show_step(parseInt(step));
            }
            this.navigate("machines/create/");
        },

        vm_details_view: function(vm) {
            this.navigate("machines/single/details/" + vm);
            ui.main.show_view("single");
            ui.main.current_view.show_vm(snf.storage.vms.get(parseInt(vm)));
        } 
    });

    snf.router = new WebAppRouter(); 
})(this);
