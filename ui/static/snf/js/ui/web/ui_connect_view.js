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
        },

        handle_vm_change: function(vm) {
            if (this.vm.state() == "DESTROY") {
                this.hide();
            }
            this._update_vm_details();
        },
        
        update_vm_details: function() {
        }

    });
    
})(this);
