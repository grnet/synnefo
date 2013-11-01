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

            // network views
            "networks/":                        "networks_view",
            // network views
            "ips/":                         	"ips_view",
            "public-keys/":                    	"public_keys_view",
            ":hash":                            "fallback"
        },
          
        fallback: function() {
            this.navigate("machines/icon/");
            this.index();
        },

        show_welcome: function() {
            if (snf.storage.vms.length == 0) {
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

        public_keys_view: function() {
            this.navigate("public-keys/");
            ui.main.show_view("public-keys");
        }

    });

    snf.router = new WebAppRouter(); 
})(this);
