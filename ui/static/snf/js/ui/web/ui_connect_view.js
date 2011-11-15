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
