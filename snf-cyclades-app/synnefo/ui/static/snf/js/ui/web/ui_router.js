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

            "networks/":                        "networks_view",
            "ips/":                         	"ips_view",
            "disks/":                         	"volumes_view",
            "public-keys/":                    	"public_keys_view",
            ":hash":                            "fallback"
        },
          
        fallback: function() {
            this.navigate("machines/icon/");
            this.index();
        },

        show_welcome: function() {
            if (snf.storage.vms.no_ghost_vms().length == 0) {
                ui.main.show_empty();
            } else {
                this.index();
            }
        },

        index: function() {
            ui.main.show_view("icon");
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
        },

        vm_details_view: function(vm) {
            this.navigate("machines/single/details/" + vm);
            ui.main.show_view("single");
            ui.main.current_view.show_vm(snf.storage.vms.get(parseInt(vm)));
        },

        networks_view: function() {
            this.navigate("networks/");
            ui.main.show_view("networks");
        },

        ips_view: function() {
            this.navigate("ips/");
            ui.main.show_view("ips");
        },
        
        volumes_view: function() {
          this.navigate("disks/");
          ui.main.show_view("volumes");
        },

        public_keys_view: function() {
            this.navigate("public-keys/");
            ui.main.show_view("public-keys");
        }

    });

    snf.router = new WebAppRouter(); 
})(this);
