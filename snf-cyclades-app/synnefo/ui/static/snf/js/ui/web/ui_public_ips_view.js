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
    var api = snf.api = snf.api || {};
    var models = snf.models = snf.models || {}
    var storage = snf.storage = snf.storage || {};
    var ui = snf.ui = snf.ui || {};
    var util = snf.util = snf.util || {};

    var views = snf.views = snf.views || {}

    // shortcuts
    var bb = root.Backbone;
    
    views.PublicIPsConnectOverlay = views.NetworkConnectVMsOverlay.extend({
        css_class: "overlay-info connect-ip",
        title: "Connect IP to machine",

        initialize: function() {
            views.PublicIPsConnectOverlay.__super__.initialize.apply(this, arguments);
        },

        show_vms: function(ip, vms, selected, callback, subtitle) {
            views.PublicIPsConnectOverlay.__super__.show_vms.call(this, 
                  undefined, vms, selected, callback, subtitle);
            this.ip = ip;
            this.set_desc("Select machine to assign <em>" + ip.escape('ip') + "</em> to.");
        },
        
        handle_vm_click: function(el) {
            var vm = $(el).data('vm');
            this.cb(vm, this.ip);
        },

        set_desc: function(desc) {
            this.$(".description p").html(desc);
        },

        onClose: function() {
            views.PublicIPsConnectOverlay.__super__.onClose.apply(this, arguments);
            synnefo.ui.main.public_ips_view.show();
        }

    });

    views.PublicIPsView = views.CollectionView.extend({
        collection: storage.public_ips,

        create_success_msg: "IP created",
        fetch_params: {update: true},

        initialize: function(options) {
            views.PublicIPsView.__super__.initialize.apply(this, arguments);
            this.$(".private-cont").hide();
            _.bindAll(this);
            this.bind("item:add", this.animate_on_add);
            this.connect_overlay = new views.PublicIPsConnectOverlay();
        },

        init_handlers: function() {
            views.PublicIPsView.__super__.init_handlers.apply(this, arguments);
        },

        bind_list_item_actions: function(el, model) {
            var self = this;
            views.PublicIPsView.__super__.bind_list_item_actions.apply(this, 
                                                                       arguments);
            el.find(".connect").bind("click", _.bind(function() {
                this.connect_to_vm(model);
            }, this));
            el.find(".disconnect").bind("click", _.bind(function() {
                var confirmed = confirm("Are you sure you want to release " + model.get('ip') + " ?");
                if (confirmed) {
                    this.disconnect_from_vm(model);
                }
            }, this));
            synnefo.storage.vms.bind('change:task_state', function(vm) {
                if (model.get_vm() == vm) {
                  self.update_list_item(el, model);
                }
            });
            model.bind('change', function(arguments) {
                self.update_list_item(el, model);
            });
        },
        
        connect_to_vm: function(ip) {
            this.connect_overlay.show_vms(ip, snf.storage.vms.get_connectable(), [], this.connect_vm);
        },

        connect_vm: function(vm, ip) {
            var self = this;
            vm.call('addFloatingIp', _.bind(function() {
                ip.set({'state': 'connecting'});
                synnefo.ui.main.public_ips_view.show();
            }, this), undefined, {address:ip.get('ip'), error: function(xhr, err, err_type) {
                snf.ui.main.public_ips_view.subview.connect_overlay.hide();
                snf.ui.main.public_ips_view.show();
                snf.ui.main.public_ips_view.subview.show_list_msg("error", 
                                                                  "Connect failed ("+err_type+")");
            }});
        },

        disconnect_from_vm: function(ip) {
            var self = this;
            var vm = ip.get_vm();
            ip.set({'state': 'disconnecting'});
            vm.call('removeFloatingIp', _.bind(function() {
            }, this), undefined, {address:ip.get('ip'), error: function(xhr, err, err_type) {
                ip.set({'state': null});
                snf.ui.main.public_ips_view.subview.show_list_msg("error", 
                                                                  "Disconnect failed ("+err_type+")");
            }});
        },

        update_list: function() {
            this.check_limit();
            views.PublicIPsView.__super__.update_list.apply(this, arguments);
        },

        update_list_item: function(el, model) {
            el.toggleClass('fixed-ip', model.get('fixed_ip'));
            el.toggleClass('connected', model.get_vm() != null);

            var in_progress = model.get('state') != null || model.get_vm() && model.get_vm().get('task_state') != "";
            el.toggleClass('in-progress', !!in_progress);
            if (in_progress) {
              var progress_msg = undefined;
              var ip_progress = model.get('state');
              if (ip_progress) {
                progress_msg_map = {'connecting': 'Connecting', 
                  'disconnecting': 'Disconnecting'};
                progress_msg = progress_msg_map[ip_progress]
              } else {
                  progress_msg = "Machine busy";
              };
              el.find(".progres-msg span").text(progress_msg);
            }
            
            el.find(".address").text(model.get('ip'));
            if (model.get_vm()) {
              el.find(".vm-name").text(model.get_vm().escape('name'));
            } else {
              el.find(".vm-name").text('');
            }
            return el;
        },

        reset: function() {
            this.check_limit();
        },

        show_form: function() {
            this.creating = true;
            this.submit_form();
            this.close_form();
        },

        get_form_data: function() {
            return {'pool': undefined, 'address': undefined}
        },
    
        validate_data: function() {
            return new snf.util.errorList();
        },

        show_form_errors: function(errors) {
            this.show_list_msg("error", errors[''])
        },

        check_limit: function() {
            var can_create = true;
            var resource = synnefo.storage.quotas.get('cyclades.floating_ip');
            if (!resource) { 
              can_create = true 
            } else {
              var limit = resource.get('limit');
              if (limit <= synnefo.storage.public_ips.length) {
                can_create = false;
              }
              var left = limit - synnefo.storage.public_ips.length;
              this.$(".quotas .available").text(left);
            };
            if (can_create) {
              this.$(".limit-msg").hide();
              this.$(".top-actions .collection-action").show();
            } else {
              this.$(".limit-msg").show();
              this.$(".top-actions .collection-action").hide();
            }
        },

        append_actions: function(el, model) {
            var actions = $('<div class="item-actions">' +
                            '<div class="item-action remove">remove</div>' + 
                            '<div class="item-action confirm-remove confirm">' +
                            '<span class="text">confirm</span>' + 
                            '<span class="cancel-remove cancel">cancel</span></div>' + 
                            '<div class="item-action disconnect">disconnect</div>' +
                            '<div class="item-action connect">connect to machine</div>' +
                            '</div>');
            el.append(actions);
        },

    })

    views.PublicIPsOverlay = views.Overlay.extend({
        
        view_id: "public_ips_view",
        content_selector: "#user_public_ips",
        css_class: 'overlay-public-ips overlay-info',
        overlay_id: "user_public_ips_overlay",

        title: "Manage your IP addresses",
        subtitle: "IP addresses",

        initialize: function(options) {
            views.PublicIPsOverlay.__super__.initialize.apply(this, arguments);
            this.subview = new views.PublicIPsView({el:this.$(".public-ips-view")});
            this.fetcher_params = [snf.config.update_interval, 
                                  snf.config.update_interval_increase || 500,
                                  snf.config.fast_interval || snf.config.update_interval/2, 
                                  snf.config.update_interval_increase_after_calls || 4,
                                  snf.config.update_interval_max || 20000,
                                  true, 
                                  {is_recurrent: true, update: true}]
        },

        show: function(view) {
            if (!this.fetcher) {
              this.fetcher = snf.storage.public_ips.get_fetcher.apply(snf.storage.public_ips, 
                                                        _.clone(this.fetcher_params));
            }
            this.fetcher.start();
            this.subview.reset();
            this.subview.update_models();
            views.PublicIPsOverlay.__super__.show.apply(this, arguments);
        },
        
        init_handlers: function() {
        },

        onClose: function() {
            if (this.fetcher) {
                this.fetcher.stop();
            }
        }
        
    });
})(this);
