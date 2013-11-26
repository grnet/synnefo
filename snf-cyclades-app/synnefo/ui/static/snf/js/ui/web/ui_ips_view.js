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
    var views = snf.views = snf.views || {}
    var storage = snf.storage = snf.storage || {};

    views.IpPortView = views.ext.ModelView.extend({
      tpl: '#ip-port-view-tpl',
      
      init: function() {
        this.model.bind("remove", function() {
          this.el.remove();
        }, this);
      },

      vm_style: function() {
        var cls, icon_state;
        var style = "background-image: url('{0}')";
        var vm = this.model.get('vm')
        if (!vm) { return }
        this.$(".model-logo").removeClass("state1 state2 state3 state4");
        icon_state = vm.is_active() ? "on" : "off";
        if (icon_state == "on") {
          cls = "state1"
        } else {
          cls = "state2"
        }
        this.$(".model-logo").addClass(cls);
        return style.format(this.get_vm_icon_path(this.model.get('vm'), 
                                                  'medium2'));
      },

      get_vm_icon_path: function(vm, icon_type) {
        var os = vm.get_os();
        var icons = window.os_icons || views.IconView.VM_OS_ICONS;

        if (icons.indexOf(os) == -1) {
          os = "unknown";
        }

        return views.IconView.VM_OS_ICON_TPLS()[icon_type].format(os);
      },

      disconnect: function() {
        this.model.actions.reset_pending();
        this.model.set({status: 'DISCONNECTING'});
      }
    });

    views.IpView = views.ext.ModelView.extend({
      status_map: {
        'CONNECTED': 'In use',
        'ACTIVE': 'In use',
        'CONNECTING': 'Attaching',
        'DISCONNECTING': 'Detaching',
        'DOWN': 'In use',
        'DISCONNECTED': 'Available',
        'REMOVING': 'Destroying'
      },

      status_cls_map: {
        'CONNECTED': 'status-active',
        'ACTIVE': 'status-active',
        'CONNECTING': 'status-progress',
        'DISCONNECTING': 'status-progress',
        'DOWN': 'status-inactive',
        'DISCONNECTED': 'status-inactive',
        'UP': 'status-active',
        'REMOVING': 'status-progress destroying-state',
      },

      tpl: '#ip-view-tpl',
      auto_bind: ['connect_vm'],
        
      status_cls: function() {
        return this.status_cls_map[this.model.get('status')];
      },

      status_display: function(v) {
        return this.status_map[this.model.get('status')];
      },
      
      model_icon: function() {
        var img = 'ip-icon-detached.png';
        var src = synnefo.config.images_url + '/{0}';
        if (this.model.get('port')) {
          img = 'ip-icon.png';
        }
        return src.format(img);
      },

      show_connect_overlay: function() {
        this.model.actions.reset_pending();
        var vms = this.model.get("network").connectable_vms;
        var overlay = this.parent_view.connect_view;
        overlay.show_vms(this.model, vms, [], this.connect_vm);
      },
      
      disconnect: function(model, e) {
        e && e.stopPropagation();
        this.model.actions.reset_pending();
        this.model.disconnect(this.disconnect_complete)
      },

      disconnect_complete: function() {
      },

      connect_vm: function(vms) {
        var overlay = this.parent_view.connect_view;
        overlay.set_in_progress();
        _.each(vms, function(vm) {
          vm.connect_floating_ip(this.model, this.connect_complete);
        }, this);
      },

      connect_complete: function() {
        var overlay = this.parent_view.connect_view;
        overlay.hide();
        overlay.unset_in_progress();
        this.model.set({'status': 'CONNECTING'});
      },

      remove: function(model, e) {
        e && e.stopPropagation();
        this.model.actions.reset_pending();
        this.model.destroy({
          success: _.bind(function() {
            this.model.set({status: 'REMOVING'});
          }, this),
          silent: true
        });
      }
    });
      
    views.IpCollectionView = views.ext.CollectionView.extend({
      collection: storage.floating_ips,
      collection_name: 'floating_ips',
      model_view_cls: views.IpView,
      create_view: undefined, // no create overlay for IPs
      quota_key: 'cyclades.floating_ip',
      initialize: function() {
        views.IpCollectionView.__super__.initialize.apply(this, arguments);
        this.connect_view = new views.IPConnectVmOverlay();
        this.creating = false;
      },
      
      set_creating: function() {
        this.creating = true;
        this.create_button.addClass("in-progress");
      },
      
      reset_creating: function() {
        this.creating = false;
        this.create_button.removeClass("in-progress");
      },

      handle_create_click: function() {
        if (this.creating) { 
          return
        }

        this.set_creating();
        network = synnefo.storage.networks.get_floating_ips_network();
        this.collection.create({
          floatingip: {}
        }, 
        {
          success: _.bind(function() {
            this.post_create();
          }, this),
          complete: _.bind(function() {
            this.creating = false;
            this.reset_creating();
            this.collection.fetch();
        }, this)});
      }
    });

    views.IpsPaneView = views.ext.PaneView.extend({
      el: '#ips-pane',
      collection_view_cls: views.IpCollectionView,
    });

    views.IPConnectVmOverlay = views.NetworkConnectVMsOverlay.extend({
        css_class: "overlay-info connect-ip",
        title: "Connect IP to machine",
        allow_multiple: false,

        show_vms: function(ip, vms, selected, callback, subtitle) {
            views.IPConnectVmOverlay.__super__.show_vms.call(this, 
                  undefined, vms, selected, callback, subtitle);
            this.ip = ip;
            this.set_desc("Select machine to assign <em>" + 
                          ip.escape('floating_ip_address') + 
                          "</em> to.");
        },
        
        set_desc: function(desc) {
            this.$(".description p").html(desc);
        }

    });

})(this);
