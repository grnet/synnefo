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
    var views = snf.views = snf.views || {}
    var storage = snf.storage = snf.storage || {};
    var util = snf.util = snf.util || {};

    views.IpPortView = views.ext.ModelView.extend({
      tpl: '#ip-port-view-tpl',
      
      init: function() {
        this.model.bind("remove", function() {
          this.el.remove();
        }, this);
      },

      vm_status_cls: function(vm) {
        var cls = 'inner clearfix main-content';
        if (!this.model.get('vm')) { return cls }
        if (this.model.get('vm').in_error_state()) {
          cls += ' vm-status-error';
        }
        return cls
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
        
      show_reassign_view: function() {
          synnefo.ui.main.ip_reassign_view.show(this.model);
      },

      status_cls: function() {
        return this.status_cls_map[this.model.get('status')];
      },

      status_display: function(v) {
        return this.status_map[this.model.get('status')];
      },
      
      show_reassign_view: function() {
          synnefo.ui.main.ip_reassign_view.show(this.model);
      },

      model_icon: function() {
        var img = 'ip-icon-detached.png';
        var src = synnefo.config.images_url + '/{0}';
        if (this.model.get('port_id')) {
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
        this.model.do_disconnect();
      },

      connect_vm: function(vms) {
        var overlay = this.parent_view.connect_view;
        overlay.set_in_progress();
        _.each(vms, function(vm) {
          vm.connect_floating_ip(this.model, 
                                 _.bind(this.connect_complete,this),
                                 _.bind(this.connect_error, this));
        }, this);
      },

      connect_complete: function() {
        var overlay = this.parent_view.connect_view;
        overlay.hide();
        overlay.unset_in_progress();
        this.model.set({'status': 'CONNECTING'});
      },

      connect_error: function() {
        var overlay = this.parent_view.connect_view;
        overlay.hide();
        overlay.unset_in_progress();
      },

      remove: function(model, e) {
        e && e.stopPropagation();
        this.model.do_destroy();
      }
    });
      
    views.FloatingIPCreateView = views.Overlay.extend({
        view_id: "ip_create_view",
        content_selector: "#ips-create-content",
        css_class: 'overlay-ip-create overlay-info',
        overlay_id: "ip-create-overlay",

        title: "Create new IP address",
        subtitle: "IP addresses",

        initialize: function(options) {
            views.FloatingIPCreateView.__super__.initialize.apply(this);

            this.create_button = this.$("form .form-action.create");
            this.form = this.$("form");
            this.project_select = this.$(".project-select");
            this.init_handlers();
        },

        init_handlers: function() {
            this.create_button.click(_.bind(function(e){
                this.submit();
            }, this));

            this.form.submit(_.bind(function(e){
                e.preventDefault();
                this.submit();
                return false;
            }, this))
        },

        submit: function() {
            if (this.validate()) {
                this.create();
            };
        },
        
        validate: function() {
            var project = this.get_project();
            if (!project || !project.quotas.can_fit({'cyclades.floating_ip': 1})) {
                this.project_select.closest(".form-field").addClass("error");
                this.project_select.focus();
                return false;
            }
            return true;
        },
        
        create: function() {
            if (this.create_button.hasClass("in-progress")) { return }
            this.create_button.addClass("in-progress");

            var project_id = this.project_select.val();
            var project = synnefo.storage.projects.get(project_id);


            var cb = _.bind(function() { 
              synnefo.api.trigger("quota:update");
              this.hide(); 
            }, this);

            snf.storage.floating_ips.create({
                floatingip: {
                  project: project_id
                }
              }, 
              { 
                complete: cb 
              });
        },
        
        update_projects: function() {
          this.project_select.find("option").remove();
          var min_ip_quota = {'cyclades.floating_ip': 1}
          synnefo.storage.projects.each(function(project){
            var el = $("<option></option>");
            el.attr("value", project.id);
            var project_name = util.truncate(project.get('name'), 34);
            var name = '{0} ({1} available)'.format(project_name, 
              project.quotas.get('cyclades.floating_ip').get('available'));
            el.text(name);
            if (!project.quotas.can_fit(min_ip_quota)) {
              el.attr('disabled', true);
            }
            this.project_select.append(el);
          }, this);
        },
        
        get_project: function() {
          var project_id = this.project_select.val();
          var project = synnefo.storage.projects.get(project_id);
          return project;
        },

        beforeOpen: function() {
            this.update_projects();
            this.create_button.removeClass("in-progress")
            this.$(".form-field").removeClass("error");
        },

        onOpen: function() {
            this.project_select.focus();
        }    
    });

    views.IpCollectionView = views.ext.CollectionView.extend({
      collection: storage.floating_ips,
      collection_name: 'floating_ips',
      model_view_cls: views.IpView,
      create_view_cls: views.FloatingIPCreateView,
      quota_key: 'ip',
      initialize: function() {
        views.IpCollectionView.__super__.initialize.apply(this, arguments);
        this.connect_view = new views.IPConnectVmOverlay();
      }
    });

    views.IpsPaneView = views.ext.PaneView.extend({
      el: '#ips-pane',
      collection_view_cls: views.IpCollectionView,
    });

    views.IPConnectVmOverlay = views.NetworkConnectVMsOverlay.extend({
        css_class: "overlay-info connect-ip",
        title: "Attach IP to machine",
        allow_multiple: false,

        show_vms: function(ip, vms, selected, callback, subtitle) {
            views.IPConnectVmOverlay.__super__.show_vms.call(this, 
                  undefined, vms, selected, callback, subtitle);
            this.ip = ip;
            this.set_desc("Select machine to attach <em>" + 
                          ip.escape('floating_ip_address') + 
                          "</em> to.");
        },
        
        set_desc: function(desc) {
            this.$(".description p").html(desc);
        }

    });


})(this);
