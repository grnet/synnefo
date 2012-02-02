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


    views.VMConnectView = views.VMOverlay.extend({
        
        view_id: "connect_view",
        content_selector: "#vm-connect-overlay-content",
        css_class: 'overlay-vmconnect overlay-info',
        overlay_id: "vmconnect-overlay",

        subtitle: "",
        title: "Connect to machine",

        initialize: function(options) {
            views.VMConnectView.__super__.initialize.apply(this);
            _.bindAll(this, "handle_success", "handle_error");

            this.error = this.$("div.error");
            this.info = this.$("div.connection-info");
            this.description = this.info.find(".description p");
            this.connect = this.info.find(".connect p");
            this.subinfo = this.info.find(".subinfo");
        },

        beforeOpen: function() {
            this.$(".clipboard").empty();
        },

        beforeClose: function() {
            this.$(".clipboard").empty();
            try { delete this.clip; } catch (err) {};
        },

        handle_success: function(data) {
            this.error.hide();
            this.info.show();
            this.description.html(data.info);
            if (data.ssh) {
                this.connect.html(data.link.title);
            } else {
                this.connect.html('<a href="{0}">{1}</a>'.format(data.link.url, data.link.title))
            }

            this.subinfo.html(data.subinfo).show();
            if (!data.subinfo) { this.subinfo.hide() };
            
            if (data.ssh) {
                var ssh_msg = data.link.title;
                this.clip = new snf.util.ClipHelper(this.$(".clipboard"), ssh_msg);
            } else {
            }
        },

        handle_error: function() {
            this.error.show();
            this.info.hide();
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

            this.vm.get_connection_info($.client.os, this.handle_success, this.handle_error)
        }

    });
    
})(this);
