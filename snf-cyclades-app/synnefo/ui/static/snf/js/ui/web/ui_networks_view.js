// Copyright (C) 2010-2015 GRNET S.A. and individual contributors
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
    var util = snf.util || {};
    var views = snf.views = snf.views || {}

    // shortcuts
    var bb = root.Backbone;
    
    // logging
    var logger = new snf.logging.logger("SNF-VIEWS");
    var debug = _.bind(logger.debug, logger);

    var min_network_quota = {
      'cyclades.network.private': 1
    };
    
    views.CreateNetworkSelectProjectView = 
        views.CreateVMSelectProjectView.extend({
            tpl: '#create-view-projects-select-tpl',
            required_quota: function() {
                return min_network_quota
            },
            model_view_cls: views.CreateVMSelectProjectItemView.extend({
                display_quota: min_network_quota
            })
        });
    
    views.NetworkCreateView = views.Overlay.extend({
        view_id: "network_create_view",
        content_selector: "#networks-create-content",
        css_class: 'overlay-networks-create overlay-info',
        overlay_id: "network-create-overlay",

        title: "Create new private network",
        subtitle: "Networks",

        initialize: function(options) {
            views.NetworkCreateView.__super__.initialize.apply(this);

            this.create_button = this.$("form .form-action.create");
            this.text = this.$(".network-create-name");
            this.form = this.$("form");

            this.dhcp_select = this.$("#network-create-dhcp");
            this.type_select = this.$("#network-create-type");
            this.subnet_select = this.$("#network-create-subnet");
            this.subnet_custom = this.$("#network-create-subnet-custom");

            this.gateway_select = this.$("#network-create-gateway");
            this.gateway_custom = this.$("#network-create-gateway-custom");
            
            this.projects_list = this.$(".projects-list");
            this.project_select_view = undefined;
                
            this.dhcp_form = this.$("#network-create-dhcp-fields");
            
            this.subnet_select.find(".subnet").remove();
            _.each(synnefo.config.network_suggested_subnets, function(subnet){
                this.subnet_select.append($('<option value='+subnet+
                                            ' class="subnet">'+subnet+
                                            '</option>'));
            }, this);

            this.type_select.find(".subnet").remove();
            _.each(synnefo.config.network_available_types, function(name, value){
                this.type_select.append($('<option value='+value+
                                          ' class="subnet">'+name+
                                          '</option>'));
            }, this);
            
            if (_.keys(synnefo.config.network_available_types).length <= 1) {
                this.type_select.closest(".form-field").hide();
            }
            
            this.check_dhcp_form();
            this.init_handlers();
        },

        reset_dhcp_form: function() {
          this.subnet_select.find("option")[0].selected = 1;
          this.subnet_custom.val("");
          this.gateway_select.find("option")[0].selected = 1;
          this.gateway_custom.val("");
          this.dhcp_form.find(".form-field").removeClass("error");
        },

        check_dhcp_form: function() {
            if (this.dhcp_select.is(":checked")) {
                this.dhcp_form.show();
            } else {
                this.dhcp_form.hide();
            }
            
            if (this.subnet_select.val() == "custom") {
                this.subnet_custom.show();
            } else {
                this.subnet_custom.hide();
            }

            if (this.gateway_select.val() == "custom") {
                this.gateway_custom.show();
            } else {
                this.gateway_custom.hide();
            }

            if (this.subnet_select.val() == "auto") {
                this.gateway_select.find("option")[1].disabled = true;
                if (this.gateway_select.val() == "custom") {
                    this.gateway_select.val("none");
                    this.gateway_custom.val("");
                    this.gateway_custom.hide();
                }
            } else {
                this.gateway_select.find("option")[1].disabled = false;
            }
        },

        init_handlers: function() {

            this.dhcp_select.click(_.bind(function(e){
                this.check_dhcp_form();
                this.reset_dhcp_form();
            }, this));

            this.subnet_select.change(_.bind(function(e){
                this.check_dhcp_form();
                if (this.subnet_custom.is(":visible")) {
                    this.subnet_custom.focus();
                }
            }, this));

            this.gateway_select.change(_.bind(function(e){
                this.check_dhcp_form();
                if (this.gateway_custom.is(":visible")) {
                    this.gateway_custom.focus();
                }
            }, this));

            this.create_button.click(_.bind(function(e){
                this.submit();
            }, this));

            this.form.submit(_.bind(function(e){
                e.preventDefault();
                this.submit;
                return false;
            }, this));

            this.text.keypress(_.bind(function(e){
                if (e.which == 13) {this.submit()};
            },this));
        },

        submit: function() {
            if (this.validate()) {
                this.create();
            };
        },
        
        validate: function() {
            // sanitazie
            var t = this.text.val();
            t = t.replace(/^\s+|\s+$/g,"");
            is_valid = true;
            this.text.val(t);

            if (this.text.val() == "") {
                this.text.closest(".form-field").addClass("error");
                this.text.focus();
                is_valid = false;
            } else {
                this.text.closest(".form-field").removeClass("error");
            }
            
            var project = this.get_project();
            if (!project || !project.quotas.can_fit({'cyclades.network.private': 1})) {
                this.projects_list.addClass("error");
                this.projects_list.focus();
                is_valid = false;
            }

            if (this.dhcp_select.is(":checked")) {
                if (this.gateway_select.val() == "custom") {
                    var gw = this.gateway_custom.val();
                    gw = gw.replace(/^\s+|\s+$/g,"");
                    this.gateway_custom.val(gw);
                        
                    if (!synnefo.util.IP_REGEX.exec(this.gateway_custom.val())) {
                        this.gateway_custom.closest(".form-field").prev().addClass("error");
                        this.gateway_custom.closest(".form-field").addClass("error");
                        is_valid = false;
                    } else {
                        this.gateway_custom.closest(".form-field").prev().removeClass("error");
                        this.gateway_custom.closest(".form-field").removeClass("error");
                    }
                }

                if (this.subnet_select.val() == "custom") {
                    var sub = this.subnet_custom.val();
                    sub = sub.replace(/^\s+|\s+$/g,"");
                    this.subnet_custom.val(sub);
                        
                    if (!synnefo.util.SUBNET_REGEX.exec(this.subnet_custom.val())) {
                        this.subnet_custom.closest(".form-field").prev().addClass("error");
                        this.subnet_custom.closest(".form-field").addClass("error");
                        is_valid = false;
                    } else {
                        this.subnet_custom.closest(".form-field").prev().removeClass("error");
                        this.subnet_custom.closest(".form-field").removeClass("error");
                    }
                };
            }
            return is_valid;
        },
        
        get_next_available_subnet: function() {
            var auto_tpl = synnefo.config.automatic_network_range_format;
            if (!auto_tpl) {
                return null
            }
            var index = 0;
            var subnet = auto_tpl.format(index);
            var networks = synnefo.storage.networks;
            var check_existing = function(n) { return n.get('cidr') == subnet }
            while (networks.filter(check_existing).length > 0 && index <= 255) {
                index++;
                subnet = auto_tpl.format(index); 
            }
            return subnet;
        },

        create: function() {
            if (this.create_button.hasClass("in-progress")) { return }
            this.create_button.addClass("in-progress");

            var name = this.text.val();
            var dhcp = this.dhcp_select.is(":checked");
            var subnet = null;
            var type = this.type_select.val();
            var project_id = this.get_project().get("id");
            var project = synnefo.storage.projects.get(project_id);

            var gateway = undefined;

            if (dhcp) {
                if (this.subnet_select.val() == "custom") {
                    subnet = this.subnet_custom.val();
                } else if (this.subnet_select.val() == "auto") {
                    subnet = this.get_next_available_subnet()
                } else {
                    subnet = this.subnet_select.val();
                }
                
                var gw_type = this.gateway_select.val();
                if (gw_type == "auto") { gateway = "auto"; }
                if (gw_type == "custom") {
                    gateway = this.gateway_custom.val();
                }
            }

            snf.storage.networks.create(
              project, name, type, subnet, dhcp, gateway, _.bind(function(){
                this.hide();
            }, this));
        },
        
        get_project: function() {
          var project = this.project_select_view.get_selected()[0];
          return project;
        },
        
        init_subviews: function() {
          if (!this.project_select_view) {
            var view_cls = views.CreateNetworkSelectProjectView;
            this.project_select_view = new view_cls({
              container: this.projects_list,
              collection: synnefo.storage.joined_projects,
              parent_view: this
            });
          }
          this.project_select_view.show(true);
          var project = synnefo.storage.quotas.get_available_projects(min_network_quota)[0];
          if (project) {
            this.project_select_view.set_current(project);
          }
        },
        
        hide: function() {
          this.project_select_view && this.project_select_view.hide(true);
          views.NetworkCreateView.__super__.hide.apply(this, arguments);
        },

        beforeOpen: function() {
            this.init_subviews();
            this.create_button.removeClass("in-progress")
            this.$(".form-field").removeClass("error");
            this.text.val("");
            this.text.show();
            this.text.focus();
            this.subnet_custom.val("");
            this.subnet_select.val("auto");
            this.gateway_select.val("none");
            this.gateway_custom.val("");
            this.dhcp_select.attr("checked", true);
            this.type_select.val(_.keys(synnefo.config.network_available_types)[0]);
            this.check_dhcp_form();
        },

        onOpen: function() {
            this.text.focus();
        }    
    });

    views.NetworkPortView = views.ext.ModelView.extend({
      tpl: '#network-port-view-tpl',
      
      error_status: function(status) {
        return status == "ERROR"
      },

      vm_logo_url: function(vm) {
        if (!this.model.get('vm'))
          { return synnefo.config.media_url + 'images/ip-icon-medium.png'}
        return synnefo.ui.helpers.vm_icon_path(this.model.get('vm'), 'medium');
      },

      vm_status_cls: function(vm) {
        var cls = 'inner clearfix main-content';
        if (!this.model.get('vm')) { return cls }
        if (this.model.get('vm').in_error_state()) {
          cls += ' vm-status-error';
        }
        return cls
      },
      
      set_confirm: function(action) {
        var parent = this.parent_view.parent_view.el;
        parent.addClass("subactionpending");
      },

      unset_confirm: function(action) {
        var parent = this.parent_view.parent_view.el;
        parent.removeClass("subactionpending");
      },

      post_init_element: function() {
        this.in_progress = false;
        this.firewall = this.$(".firewall-content").hide();
        this.firewall_toggler = this.$(".firewall-toggle");
        this.firewall_apply = this.$(".firewall-apply");
        this.firewall_legends = this.firewall.find(".checkbox-legends");
        this.firewall_inputs = this.firewall.find("input");
        this.firewall_apply = this.firewall.find("button");
        this.firewall_visible = false;

        this.firewall_toggler.click(_.bind(function() {
          this.toggle_firewall();
        }, this));

        this.firewall.find(".checkbox-legends, input").click(
          _.bind(this.handle_firewall_choice_click, this));
        this.update_firewall();
      },
      
      toggle_firewall: function(e, hide, cb) {
          hide = hide === undefined ? false : hide;
          if (hide) {
            this.firewall.stop().hide();
          } else {
            this.firewall.slideToggle(function() {
              cb && cb();
              $(window).trigger("resize");
            });
          }
          this.firewall_toggler.toggleClass("open");
          this.firewall_visible = this.firewall_toggler.hasClass("open");
          if (!this.firewall_visible) {
            this.firewall_apply.fadeOut(50);
          } else {
            this.model.actions.reset_pending();
          }
          this.update_firewall();
      },
    
      post_hide: function() {
        views.NetworkPortView.__super__.post_hide.apply(this);
        if (this.firewall_visible) {
          this.toggle_firewall({}, true);
        }
      },

      handle_firewall_choice_click: function(e) {
          var el = $(e.currentTarget);
          if (el.get(0).tagName == "INPUT") {
            el = el.next();
          }
          var current = this.model.get("firewall_status");
          var selected = el.prev().val();

          el.parent().find("input").attr("checked", false);
          el.prev().attr("checked", true);

          if (selected != current) {
            this.firewall_apply.show();
          } else {
            this.firewall_apply.hide();
          }
      },
      
      disconnect_port: function(model, e) {
        var parent = this.parent_view.parent_view.el;
        parent.removeClass("subactionpending");
        e && e.stopPropagation();
        var network = this.model.get("network");
        this.model.actions.reset_pending();
        this.model.disconnect(_.bind(this.disconnect_port_complete, this));
      },

      disconnect_port_complete: function() {
      },

      set_firewall: function() {
        var parent = this.parent_view.parent_view.el;
        parent.removeClass("subactionpending");
        var value = this.get_selected_value();
        this.firewall_apply.addClass("in-progress");
        var vm = this.model.get('vm');
        if (!vm) { return }
        this.model.set({'pending_firewall': value});
        vm.set_firewall(this.model, value, this.set_firewall_success,
                        this.set_firewall_error)
        this.in_progress = true;
      },
      
      set_firewall_success: function() {
        this.set_firewall_complete();
      },

      set_firewall_error: function() {
        this.model.set({'pending_firewall': undefined});
        this.set_firewall_complete();
      },

      set_firewall_complete: function() {
        this.in_progress = false;
        this.toggle_firewall({}, false, _.bind(function() {
          this.firewall_apply.removeClass("in-progress").show();
        }, this));
      },

      get_selected_value: function() {
        return this.firewall_inputs.filter(":checked").val();
      },

      update_firewall: function() {
        var value = this.model.get("firewall_status");
        var value_selector = "[value=" + value + "]"
        var status_span = this.firewall_toggler.find("span span");
        var current_choice = this.firewall_inputs.filter(value_selector);

        if (_.contains(["PROTECTED", "ENABLED"], value)) {
          status_span.removeClass("firewall-off").addClass("firewall-on");
          status_span.text("On");
        } else {
          status_span.removeClass("firewall-on").addClass("firewall-off");
          status_span.text("Off");
        }
        
        this.firewall_inputs.attr("checked", false);
        this.firewall_legends.removeClass("current");
        current_choice.attr("checked", true)
        current_choice.next().addClass("current");
      },

      show_vm_details: function() {
        var vm = this.model.get('vm');
        if (vm) { snf.ui.main.show_vm_details(vm) }
      }
    });

    views.NetworkPortCollectionView = views.ext.CollectionView.extend({
      tpl: '#network-port-collection-view-tpl',
      model_view_cls: views.NetworkPortView,
      rivets_view: true,
      get_rivet_object: function() {
        return {
          model: this.collection.network
        }
      },
      resolve_storage_object: function() {
        return this.collection
      },

      show_connect_vms_overlay: function() {
        this.parent_view.show_connect_vms_overlay();
      },

      check_empty: function() {
        views.NetworkPortCollectionView.__super__.check_empty.apply(this, arguments);
        if (this.collection.length == 0) {
          this.parent_view.set_ports_empty();
        } else {
          this.parent_view.unset_ports_empty();
        }
      }
    });

    views.NetworkView = views.ext.ModelView.extend({
      tpl: '#network-view-tpl',
      auto_bind: ['connect_vm'],
      post_init_element: function() {
        this.ports = this.$(".ports.nested-model-list");
        this.ports.hide();
        this.ports_toggler = this.$(".network-ports-toggler");
        this.ports_toggler.click(this.toggle_ports);
        this.ports_visible = false;
      },

      show_reassign_view: function() {
          if (!this.model.get('is_public')) {
            synnefo.ui.main.network_reassign_view.show(this.model);
          }
      },

      set_ports_empty: function() {
        if (this.ports_visible) {
          this.toggle_ports();
        }
        this.ports_empty = true;
        this.ports_toggler.find(".cont-toggler").addClass("disabled");
      },

      unset_ports_empty: function() {
        this.ports_toggler.find(".cont-toggler").removeClass("disabled");
        this.ports_empty = false;
      },

      toggle_ports: function(e, hide) {
        $(window).trigger("resize");
        hide = hide === undefined ? false : hide;
        if (hide) {
          this.ports.stop().hide();
        } else {
          if (this.ports_empty) { return }
          var self = this;
          this.ports.parent().parent().css({overflow: 'hidden'});
          this.ports.stop().slideToggle(function() {
              $(window).trigger("resize");
              self.ports.parent().parent().css({overflow: 'visible'});
            });
        }
        this.ports_toggler.find(".cont-toggler").toggleClass("open");
        this.ports_visible = this.ports_toggler.find(".cont-toggler").hasClass("open");
        if (this.ports_visible) {
          $(this.el).addClass("hovered");
        } else {
          $(this.el).removeClass("hovered");
        }
      },
      
      get_network_icon: function() {
        var ico = this.model.get('is_public') ? 'internet.png' : 'network.png';
        return synnefo.config.media_url + 'images/' + ico;
      },

      post_hide: function() {
        views.NetworkView.__super__.post_hide.apply(this);
        if (this.ports_visible) {
          this.toggle_ports({}, true);
        }
      },

      check_can_reassign: function() {
          var action = this.$(".project-name");
          if (this.model.get("shared_to_me")) {
              snf.util.set_tooltip(action,
                'Not the owner of this resource, cannot reassign.', {tipClass: "tooltip"});
              return "project-name-cont disabled";
          } else {
              snf.util.unset_tooltip(action);
              return "project-name-cont";
          }
      },

      status_map: {
        'ACTIVE': 'Active',
        'SNF:DRAINED': 'Drained',
        'CONNECTING': 'Connecting',
        'DISCONNECTING': 'Disconnecting',
        'REMOVING': 'Destroying'
      },

      status_cls_map: {
        'ACTIVE': 'status-active',
        'SNF:DRAINED': 'status-terminated',
        'DISCONNECTING': 'status-progress',
        'CONNECTING': 'status-progress',
        'REMOVING': 'status-progress'
      },
      
      status_cls: function(status) {    
        return this.status_cls_map[this.model.get('ext_status')]
      },

      status_display: function(status) {
        var status;
        var cidr = this.model.get('cidr');
        var status = this.model.get('ext_status');
        if (status != 'REMOVING' && cidr) {
          return cidr
        }
        if (this.model.id == "snf-combined-public-network" && !_.contains(
          ["CONNECTING", "DISCONNECTING"], status)) {
          return "Public"
        }

        return this.status_map[status];
      },
      
      connect_vms: function(vms, cb) {
        var finished = 0;
        var completed = function() {
          finished++;
          if (finished == vms.length) {
            cb();
          }
        }
        _.each(vms, function(vm) {
          this.model.connect_vm(vm, completed);
        }, this);
      },
      
      remove: function(model, e) {
        e && e.stopPropagation();
        this.model.do_remove();
      },

      show_connect_vms_overlay: function() {
        var view = new views.NetworkConnectVMsOverlay();
        this.model.actions.reset_pending();
        vms = this.model.connectable_vms;
        var cb = _.bind(function(vms) {
          view.set_in_progress();
          var cbinner = function() {
            view.hide();
            delete view;
          }
          this.connect_vms(vms, cbinner);
        }, this);
        view.show_vms(this.model, vms, [], cb, "subtitle", this);
      }

    });
    
    views.NetworksCollectionView = views.ext.CollectionView.extend({
      collection: storage.networks,
      collection_name: 'networks',
      model_view_cls: views.NetworkView,
      create_view_cls: views.NetworkCreateView,
      quota_key: 'network',

      group_key: 'name',
      group_network: function(n) {
        return n && n.get && n.get('is_public')
      },
      
      init: function() {
        this.grouped_networks = {};
        views.NetworksCollectionView.__super__.init.apply(this, arguments);
      },
      
      check_empty: function() {
        views.NetworksCollectionView.__super__.check_empty.apply(this, arguments);
        if (this.collection.filter(function(n){ return !n.is_public()}).length == 0) {
          this.$(".private").hide();  
        } else {
          this.$(".private").show();  
        }
      },

      add_model: function(m) {
        var CombinedPublic = models.networks.CombinedPublicNetwork;
        if (this.group_network(m) && synnefo.config.group_public_networks) {
          var group_value = m.get(this.group_key);
          if (!(group_value in this.grouped_networks)) {
            var combined_public = new CombinedPublic({name: group_value});
            combined_public_view = new views.NetworkView({
              model: combined_public
            });

            this.add_model_view(combined_public_view, 
                                combined_public, 0);
            this.grouped_networks[group_value] = combined_public;
          }
        }
        return views.NetworksCollectionView.__super__.add_model.call(this, m);
      },

      remove_model: function(m) {
        if (m.id == 'snf-combined-public-network' ||
            (this.group_network(m) && 
            synnefo.config.group_public_networks)) {
          return false;
        } else {
          return views.NetworksCollectionView.__super__.remove_model.call(this, m);
        }
      },

      get_model_view_cls: function(m) {
        if (m.id == 'snf-combined-public-network' || 
            (this.group_network(m) && 
             synnefo.config.group_public_networks)) {
          return false;
        }
        return views.NetworksCollectionView.__super__.get_model_view_cls.apply(this, [m]);
      },
      
      parent_for_model: function(m) {
        if (m.get('is_public')) {
          return this.list_el.find(".public");
        } else {
          return this.list_el.find(".private");
        }
      }
    });

    views.NetworksPaneView = views.ext.PaneView.extend({
      id: "pane",
      el: '#networks-pane',
      collection_view_cls: views.NetworksCollectionView,
      collection_view_selector: '#networks-list-view'
    });
    
    views.VMSelectItemView = views.ext.SelectModelView.extend({
      tpl: '#vm-select-model-tpl',
      max_title_length: 20,
      get_vm_icon: function() {
        return $(snf.ui.helpers.vm_icon_tag(this.model, "small")).attr("src")
      },
      status_cls: function() {
        return (views.IconView.STATE_CLASSES[this.model.get("state")] || []).join(" ") + " status clearfix"
      },
      status_display: function() {
        return STATE_TEXTS[this.model.get("state")];
      },
      truncate_title: function() {
        return snf.util.truncate(this.model.get("name"), this.max_title_length);
      }
    });

    views.VMSelectView = views.ext.CollectionSelectView.extend({
      tpl: '#vm-select-collection-tpl',
      model_view_cls: views.VMSelectItemView,
      max_title_length: 20,

      post_add_model_view: function(view) {
        views.VMSelectView.__super__.post_add_model_view.call(this, view);
        view.max_title_length = this.max_title_length;
        if (!this.options.allow_multiple) {
            view.input.prop("type", "radio");
        }
      }
    });

    views.NetworkConnectVMsOverlay = views.Overlay.extend({
        title: "Connect machine",
        overlay_id: "overlay-select-vms",
        content_selector: "#network-vms-select-content",
        css_class: "overlay-info",
        allow_multiple: true,
        allow_empty: true,

        initialize: function() {
            views.NetworkConnectVMsOverlay.__super__.initialize.apply(this);
            this.list = this.$(".vms-list ul");
            this.empty_message = this.$(".empty-message");
            // flag for submit handler to avoid duplicate bindings
            this.submit_handler_set = false;
            this.in_progress = false;

        },
        
        init_collection_view: function(collection) {
            this.collection_view = new views.VMSelectView({
              collection: collection,
              el: this.list,
              allow_multiple: this.allow_multiple,
              allow_empty: this.allow_empty
            });
            this.collection_view.show(true);
            this.list.append($(this.collection_view.el));
        },

        handle_vm_click: function(el) {
            if (!this.allow_multiple) {
              $(el).closest("ul").find(".selected").removeClass("selected");
              $(el).addClass("selected");
            } else {
              $(el).toggleClass("selected");
            }
        },

        init_handlers: function() {
            var self = this;
            
            if (!this.submit_handler_set) {
                // avoid duplicate submits
                this.el.find(".create, .assign").click(_.bind(function() {
                  if (!this.in_progress) {
                    this.submit();
                  }
                }, this));
                this.submit_handler_set = true;
            }
        },
        
        reset: function() {},
        beforeOpen: function() {
            this.reset();
            this.update_layout();
        },
        
        get_selected: function() {
          return this.collection_view.get_selected();
        },

        update_layout: function() {
            this.unset_in_progress();
            this.in_progress = false;

            if (this.vms.length == 0) {
                this.empty_message.show();
            } else {
                this.empty_message.hide();
            }

            this.init_handlers();
        },

        set_in_progress: function() {
          this.$(".form-action").addClass("in-progress");
          this.in_progress = true;
        },

        unset_in_progress: function() {
          this.$(".form-action").removeClass("in-progress");
          this.in_progress = false;
        },

        show_vms: function(network, vms, selected, callback, subtitle) {
            this.init_collection_view(vms);
            this.network = network;
            this.reset();
            if (network) {
              this.set_subtitle(network.escape("name"));
            } else {
              this.set_subtitle(subtitle);
            }
            this.vms = vms;
            this.selected = selected;
            this.cb = callback;
            this.unset_in_progress();
            this.show(true);
        },
        
        onClose: function() {
          this.collection_view && this.collection_view.hide(true);
          delete this.collection_view;
        },

        submit: function() {
            if (!this.get_selected().length) { return }
            this.cb(this.get_selected());
        }
    });
    
    views.NetworkSelectModelView = views.ext.SelectModelView.extend({});

    views.NetworkSelectNetworkTypeModelView = views.NetworkSelectModelView.extend({
      get_network_icon: function() {
        var ico = this.model.get('is_public') ? 'internet-small.png' : 'network-small.png';
        return synnefo.config.media_url + 'images/' + ico;
      },
      forced_title: 'You machine will be automatically connected ' +
                    'to this network.'
    });

    views.NetworkSelectPublicNetwork = views.NetworkSelectNetworkTypeModelView.extend({
      tpl: '#networks-select-public-item-tpl',
      classes: 'public-network',
      post_init_element: function() {
        views.NetworkSelectPublicNetwork.__super__.post_init_element.apply(this);
      },
      resolve_floating_ip_view_params: function() {
        return {
          project: this.parent_view.parent_view.project
        }
      }
    });

    views.NetworkSelectPrivateNetwork = views.NetworkSelectNetworkTypeModelView.extend({
      tpl: '#networks-select-private-item-tpl',
      classes: 'private-network'
    });
    
    views.NetworkSelectTypeView = views.ext.CollectionView.extend({});
    views.NetworkSelectPublicNetworks = views.NetworkSelectTypeView.extend({
      tpl: '#networks-select-public-tpl',
      model_view_cls: views.NetworkSelectPublicNetwork,
      get_floating_ips: function() {
        var ips = [];
        _.each(this._subviews, function(view) {
          _.each(view._subviews, function(view) {
            if (view.selected_ips) {
              _.each(view.selected_ips, function(m) {
                ips.push(m.id);
              }, this);
            }
          }, this);
        }, this);
        return ips;
      }
    });
    
    views.NetworkSelectFloatingIpView = views.NetworkSelectModelView.extend({
      tpl: '#networks-select-floating-ip-tpl'
    });

    views.NetworkSelectFloatingIpsView = views.ext.CollectionView.extend({
      tpl: '#networks-select-floating-ips-tpl',
      model_view_cls: views.NetworkSelectFloatingIpView,
      
      deselect_all: function() {
        this.each_ip_view(function(v) { v.deselect() });
      },

      each_ip_view: function(cb) {
        _.each(this._subviews, function(view) {
          if (view instanceof views.NetworkSelectFloatingIpView) {
            cb(view);
          }
        })
      },

      post_init: function(options) {
        var parent = this.parent_view;
        var self = this;
        
        this.quotas = this.options.project.quotas.get("cyclades.floating_ip");
        this.project = this.options.project;
        this.selected_ips = [];
        this.handle_ip_select = _.bind(this.handle_ip_select, this);
        this.create = this.$(".floating-ip.create");
        
        synnefo.storage.quotas.bind("change", _.bind(this.update_available, this));
        this.collection.bind("change", _.bind(this.update_available, this))
        this.collection.bind("add", _.bind(this.update_available, this))
        this.collection.bind("remove", _.bind(this.update_available, this))

        parent.bind("change:select", function(view, selected) {
          if (selected) { this.show_parent() } else { this.hide_parent() }
        }, this);

        this.create.click(function(e) {
          e.preventDefault();
          self.create_ip();
        });
        this.reset_creating();
      },
      
      hide_parent: function() {
        this.parent_view.item.removeClass("selected");
        this.parent_view.input.attr("checked", false);
        this.parent_view.selected = false;
        this.deselect_all();
        this.hide(true);
      },

      show_parent: function() {
        var left = this.quotas.get_available();
        var available = this.collection.length || left;
        if (!available) { 
          this.hide_parent();
          return;
        }
        this.parent_view.item.addClass("selected");
        this.parent_view.input.attr("checked", true);
        this.parent_view.selected = true;
        this.select_first();
        this.show(true);
      },

      update_available: function() {
        var can_create = synnefo.storage.quotas.can_create('ip');
        var available_el = this.parent_view.$(".available");
        var no_available_el = this.parent_view.$(".no-available");
        var parent_check = this.parent_view.$("input[type=checkbox]");
        var create = this.$(".create.model-item");
        var create_link = this.$(".create a");
        var create_no_available = this.$(".create .no-available");

        if (can_create) {
          // available quota
          create.removeClass("no-available");
          create.show();
          create_link.show();
          create_no_available.hide();
        } else {
          // no available quota
          create.addClass("no-available");
          create.hide();
          create_link.hide();
        }
        this.update_selected();
      },
      
      update_selected: function() {
        // reset missing entries
        _.each(this.selected_ips.length, function(ip) {
          if (!this.collection.get(ip.id)) {
            this.selected_ips = _.without(this.selected_ips, ip);
          }
        }, this);

        if (this.selected_ips.length) {
          this.parent_view.input.attr("checked", true);
          this.parent_view.item.addClass("selected");
          this.parent_view.selected = true;
        } else {
          this.parent_view.input.attr("checked", false);
          this.parent_view.item.removeClass("selected");
          this.parent_view.selected = false;
        }
      },

      post_remove_model_view: function(view) {
        view.deselect();
        view.unbind("change:select", this.handle_ip_select)
        this.update_available();
      },

      handle_create_error: function() {},
      
      set_creating: function() {
        var create_link = this.$(".create a");
        var create_no_available = this.$(".create .no-available");
        var loading = this.$(".create .loading");
        create_link.hide();
        loading.show();
      },

      reset_creating: function() {
        var loading = this.$(".create .loading");
        loading.hide();
        this.update_available();
      },

      create_ip: function() {
        var quotas = synnefo.storage.quotas;
        var required_quota = quotas.required_quota['ip'];
        var projects = quotas.get_available_projects(required_quota);
        var project = undefined;
        var use_view_project = projects.indexOf(this.project) > -1;
        if (use_view_project) {
          project = this.project;
        } else {
          if (projects.length) {
            project = projects[0];
          }
        }

        var self = this;
        this.set_creating();
        var data = {floatingip:{}};
        if (project) {
          data.floatingip['project'] = project.get('id');
        }
        synnefo.storage.floating_ips.create(data, {
          error: _.bind(this.handle_create_error, this),
          complete: function() {
            synnefo.storage.quotas.fetch();
            self.reset_creating();
          }
        });
      },
      
      select_first: function() {
        // automaticaly select a public IP address. Priority to the IPs 
        // assigned to the project selected in wizard.
        
        this.deselect_all();
        if (this._subviews.length == 0) { return }
        
        var project_ip_found = false;
        var project_uuid = this.project && this.project.get('id');
        _.each(this._subviews, function(view) {
          var view_project_uuid = view.model.get('project') && 
                                  view.model.get('project').get('id');
          if (view_project_uuid == project_uuid) {
            this.deselect_all();
            view.select();
            project_ip_found = true;
          }
        }, this);

        if (!project_ip_found) {
          this._subviews[0] && this._subviews[0].select();
        }
      },
      
      post_add_model_view: function(view, model) {
        view.bind("change:select", this.handle_ip_select)
      },
      
      auto_select: true,
      post_update_models: function() {
        if (this.collection.length && this.auto_select) {
          this.auto_select = false;
          this.select_first();
        }
      },

      handle_ip_select: function(view) {
        if (view.selected) {
          if (!_.contains(this.selected_ips, view.model)) {
            this.selected_ips.push(view.model);
          }
        } else {
          this.selected_ips = _.without(this.selected_ips, view.model);
        }
        this.update_selected();
      },
      
      post_show: function() {
        this.update_available();
      },

      get_floating_ips: function() {
        return this.selected_ips;
      }
    });

    views.NetworkSelectPrivateNetworks = views.NetworkSelectTypeView.extend({
      tpl: '#networks-select-private-tpl',
      model_view_cls: views.NetworkSelectPrivateNetwork,
      get_networks: function() {
        return _.filter(_.map(this._subviews, function(view) {
          if (view.selected) { return view.model.id }
        }), function(id) { return id });
      }

    });

    views.NetworkSelectView = views.ext.ModelView.extend({
      rivets_view: true,
      tpl: '#networks-select-view-tpl',
      select_public: true,
      
      forced_values_title_map: {
        "SNF:ANY_PUBLIC_IPV6": "Internet (public IPv6)",
        "SNF:ANY_PUBLIC_IPV4": "Internet (public IPv4)"
      },

      initialize: function(options) {
        this.project = options.project;
        this.quotas = this.project.quotas.get('cyclades.private_network');
        options = options || {};
        options.model = options.model || new models.Model();
        this.private_networks = new Backbone.FilteredCollection(undefined, {
          collection: synnefo.storage.networks,
          collectionFilter: function(m) {
            return !m.get('is_public')
        }});

        this.public_networks = new Backbone.Collection();
        this.public_networks.comparator = function(m) {
          if (m.get('forced')) {
            return -1
          }  
          return 100;
        }
        
        if (synnefo.config.forced_server_networks.length) {
          _.each(synnefo.config.forced_server_networks, function(network) {
            var forced = synnefo.storage.networks.get(network);
            if (!forced) {
              var name = this.forced_values_title_map[network];
              if (!name) { name = "Forced network ({0})".format(network)}
              forced = new models.networks.Network({
                id: network,
                name: name, 
                subnets: [],
                is_public: true,
                forced: true
              });
            } else {
              forced.set({'forced': true});
            }
            this.public_networks.add(forced);
          }, this);
        }

        // combined public
        this.floating_public = new models.networks.CombinedPublicNetwork('Internet');
        this.floating_public.set({noselect: true, 
                                  name: 'Internet (public IPv4)', 
                                  forced: false});
        this.public_networks.add(this.floating_public);

        model_attrs = {
          public_collection: this.public_networks,
          private_collection: this.private_networks,
          floating_selected: true
        }

        options.model.set(model_attrs);
        this._configure(options);
        return views.NetworkSelectView.__super__.initialize.call(this, options);
      },

      get_selected_floating_ips: function() {
        var ips = [];
        _.each(this._subviews, function(view) {
          if (view.get_floating_ips) {
            ips = _.union(ips, view.get_floating_ips());
          }
        }, this);
        return _.filter(
          _.map(ips, function(ipid) { 
          return synnefo.storage.floating_ips.get(parseInt(ipid))
        }), function(ip) { return ip });
      },

      get_selected_networks: function() {
        var networks = [];
        _.each(this._subviews, function(view) {
          if (view.get_networks) {
            networks = _.union(networks, view.get_networks());
          }
        }, this);
        return _.filter(
          _.map(networks, function(netid) { 
          return synnefo.storage.networks.get(netid)
        }), function(net) { return net });
      }
    });
 
})(this);
