// Copyright 2013 GRNET S.A. All rights reserved.
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
    var util = snf.util || {};
    var views = snf.views = snf.views || {}

    // shortcuts
    var bb = root.Backbone;
    
    // logging
    var logger = new snf.logging.logger("SNF-VIEWS");
    var debug = _.bind(logger.debug, logger);
    
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

            this.create_button.click(_.bind(function(e){
                this.submit();
            }, this));

            this.form.submit(_.bind(function(e){
                e.preventDefault();
                this.submit;
                return false;
            }, this))

            this.text.keypress(_.bind(function(e){
                if (e.which == 13) {this.submit()};
            },this))
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
            this.text.val(t);

            if (this.text.val() == "") {
                this.text.closest(".form-field").addClass("error");
                this.text.focus();
                return false;
            } else {
                this.text.closest(".form-field").removeClass("error");
            }
            
            if (this.dhcp_select.is(":checked")) {
                if (this.subnet_select.val() == "custom") {
                    var sub = this.subnet_custom.val();
                    sub = sub.replace(/^\s+|\s+$/g,"");
                    this.subnet_custom.val(sub);
                        
                    if (!synnefo.util.IP_REGEX.exec(this.subnet_custom.val())) {
                        this.subnet_custom.closest(".form-field").prev().addClass("error");
                        return false;
                    } else {
                        this.subnet_custom.closest(".form-field").prev().removeClass("error");
                    }
                };
            }

            return true;
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
            this.create_button.addClass("in-progress");

            var name = this.text.val();
            var dhcp = this.dhcp_select.is(":checked");
            var subnet = null;
            var type = this.type_select.val();

            if (dhcp) {
                if (this.subnet_select.val() == "custom") {
                    subnet = this.subnet_custom.val();
                } else if (this.subnet_select.val() == "auto") {
                    subnet = this.get_next_available_subnet()
                } else {
                    subnet = this.subnet_select.val();
                }
                
            }

            snf.storage.networks.create(name, type, subnet, dhcp, _.bind(function(){
                this.hide();
                // trigger parent view create handler
                this.parent_view.post_create();
            }, this));
        },

        beforeOpen: function() {
            this.create_button.removeClass("in-progress")
            this.text.closest(".form-field").removeClass("error");
            this.text.val("");
            this.text.show();
            this.text.focus();
            this.subnet_custom.val("");
            this.subnet_select.val("auto");
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
      
      vm_logo_url: function(vm) {
        if (!this.model.get('vm')) { return '' }
        return synnefo.ui.helpers.vm_icon_path(this.model.get('vm'), 'medium');
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

      toggle_ports: function(e, hide) {
        $(window).trigger("resize");
        hide = hide === undefined ? false : hide;
        if (hide) {
          this.ports.stop().hide();
        } else {
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
      
      status_map: {
        'ACTIVE': 'Active',
        'CONNECTING': 'Connecting',
        'DISCONNECTING': 'Disconnecting',
        'REMOVING': 'Destroying'
      },

      status_cls_map: {
        'ACTIVE': 'status-active',
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
      quota_key: 'cyclades.network.private',
      
      init: function() {
        this.public_added = false;
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
        if (m.get('is_public') && !this.public_added) {
          this.combined_public = new models.networks.CombinedPublicNetwork();
          this.combined_public_view = new views.NetworkView({
            model: this.combined_public
          });
          this.add_model_view(this.combined_public_view, this.combined_public, 0);
          this.public_added = true;
        }
        return views.NetworksCollectionView.__super__.add_model.call(this, m);
      },

      remove_model: function(m) {
        if (m.id == 'snf-combined-public-network') {
          return;
        } else {
          return views.NetworksCollectionView.__super__.remove_model.call(this, m);
        }
      },

      get_model_view_cls: function(m) {
        if (!this.public_added) {
        }
        if (m.get('is_public')) {
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
    
    views.VMSelectView = views.ext.SelectModelView.extend({
      tpl: '#vm-select-model-tpl',
      get_vm_icon: function() {
        return $(snf.ui.helpers.vm_icon_tag(this.model, "small")).attr("src")
      },
      status_cls: function() {
        return (views.IconView.STATE_CLASSES[this.model.get("state")] || []).join(" ") + " status clearfix"
      },
      status_display: function() {
        return STATE_TEXTS[this.model.get("state")]
      }
    });

    views.VMSelectView = views.ext.CollectionView.extend({
      init: function() {
        views.VMSelectView.__super__.init.apply(this);
      },
      tpl: '#vm-select-collection-tpl',
      model_view_cls: views.VMSelectView,
      
      trigger_select: function(view, select) {
        this.trigger("change:select", view, select);
      },

      post_add_model_view: function(view) {
        view.bind("change:select", this.trigger_select, this);
        if (!this.options.allow_multiple) {
          view.input.prop("type", "radio");
        }
      },

      post_remove_model_view: function(view) {
        view.unbind("change:select", this.trigger_select, this);
      },

      deselect_all: function(except) {
        _.each(this._subviews, function(view) {
          if (view != except) { view.deselect() }
        });
      },

      get_selected: function() {
        return _.filter(_.map(this._subviews, function(view) {
          if (view.selected) {
            return view.model;
          }
        }), function(m) { return m });
      }
    });

    views.NetworkConnectVMsOverlay = views.Overlay.extend({
        title: "Connect machine",
        overlay_id: "overlay-select-vms",
        content_selector: "#network-vms-select-content",
        css_class: "overlay-info",
        allow_multiple: true,

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
              allow_multiple: this.allow_multiple
            });
            this.collection_view.show(true);
            this.list.append($(this.collection_view.el));
            if (!this.allow_multiple) {
              this.collection_view.bind("change:select", 
                                        function(view, selected) {
                if (!selected) { return }
                this.collection_view.deselect_all(view);
              }, this);
            }
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

      post_init: function() {
        var parent = this.parent_view;
        var self = this;

        this.quota = synnefo.storage.quotas.get("cyclades.floating_ip");
        this.selected_ips = [];
        this.handle_ip_select = _.bind(this.handle_ip_select, this);
        this.create = this.$(".floating-ip.create");
        
        this.quota.bind("change", _.bind(this.update_available, this));
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
        var left = this.quota.get_available();
        var available = this.collection.length || left;
        if (!available) { 
          this.hide_parent();
          return;
        }
        this.select_first();
        this.parent_view.item.addClass("selected");
        this.parent_view.input.attr("checked", true);
        this.parent_view.selected = true;
        this.show(true);
      },

      update_available: function() {
        var left = this.quota.get_available();
        var available = this.collection.length || left;
        var available_el = this.parent_view.$(".available");
        var no_available_el = this.parent_view.$(".no-available");
        var parent_check = this.parent_view.$("input[type=checkbox]");
        var create = this.$(".create.model-item");
        var create_link = this.$(".create a");
        var create_no_available = this.$(".create .no-available");

        if (!available) {
          // no ip's available to select
          this.hide_parent();
          available_el.hide();
          no_available_el.show();
          parent_check.attr("disabled", true);
        } else {
          // available floating ip
          var available_text = "".format(
            this.collection.length + this.quota.get_available());
          available_el.removeClass("hidden").text(available_text).show();
          available_el.show();
          no_available_el.hide();
          parent_check.attr("disabled", false);
        }

        if (left) {
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
          //create_no_available.show();
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
        if (!this.quota.get_available()) { return }
        var self = this;
        this.set_creating();
        synnefo.storage.floating_ips.create({floatingip:{}}, {
          error: _.bind(this.handle_create_error, this),
          complete: function() {
            synnefo.storage.quotas.fetch();
            self.reset_creating();
          }
        });
      },
      
      select_first: function() {
        if (this.selected_ips.length > 0) { return }
        if (this._subviews.length == 0) { return }
        this._subviews[0].select();
        if (!_.contains(this.selected_ips, this._subviews[0].model)) {
          this.selected_ips.push(this._subviews[0].model);
        }
      },

      post_add_model_view: function(view, model) {
        view.bind("change:select", this.handle_ip_select)
        if (!this.selected_ips.length && this._subviews.length == 1) {
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
        this.quotas = synnefo.storage.quotas.get('cyclades.private_network');
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
        this.combined_public = new models.networks.CombinedPublicNetwork();
        this.combined_public.set({noselect: true, 
                                  name: 'Internet (public IPv4)', 
                                  forced: false});
        this.public_networks.add(this.combined_public);

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
