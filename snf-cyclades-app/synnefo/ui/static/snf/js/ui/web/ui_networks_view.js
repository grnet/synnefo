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
                this.subnet_select.append($('<option value='+subnet+' class="subnet">'+subnet+'</option>'));
            }, this);

            this.type_select.find(".subnet").remove();
            _.each(synnefo.config.network_available_types, function(name, value){
                this.type_select.append($('<option value='+value+' class="subnet">'+name+'</option>'));
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
      
      set_confirm: function() {
        var parent = this.parent_view.parent_view.el;
        parent.addClass("subactionpending");
      },

      unset_confirm: function() {
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
            if (!cb) { cb = function() {}}
            this.firewall.slideToggle(cb);
          }
          this.firewall_toggler.toggleClass("open");
          this.firewall_visible = this.firewall_toggler.hasClass("open");
          if (!this.firewall_visible) {
            this.firewall_apply.fadeOut(50);
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
        e && e.stopPropagation();
        this.model.actions.reset_pending();
        this.model.disconnect(_.bind(this.disconnect_port_complete, this));
      },

      disconnect_port_complete: function() {
      },

      set_firewall: function() {
        var value = this.get_selected_value();
        this.firewall_apply.addClass("in-progress");
        this.model.set({'pending_firewall': value});
        this.model.set_firewall(value, this.set_firewall_complete, 
                                       this.set_firewall_complete);
        this.in_progress = true;
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
        hide = hide === undefined ? false : hide;
        if (hide) {
          this.ports.stop().hide();
        } else {
          this.ports.stop().slideToggle();
        }
        this.ports_toggler.find(".cont-toggler").toggleClass("open");
        this.ports_visible = this.ports_toggler.find(".cont-toggler").hasClass("open");
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
        if (this.model.id == "snf-combined-public-network") {
          return "Internet"
        }

        status = this.status_map[this.model.get('ext_status')];
        return status;
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
        this.model.actions.reset_pending();
        this.model.destroy({
          complete: _.bind(function() {
            this.model.set({status: 'REMOVING'})
            this.model.set({ext_status: 'REMOVING'})
          }, this),
          silent: true
        });
      },

      show_connect_vms_overlay: function() {
        var view = new views.NetworkConnectVMsOverlay();
        vms = this.model.pluggable_vms();
        var cb = _.bind(function(vms) {
          view.set_in_progress();
          var cbinner = function() {
            view.hide();
            delete view;
          }
          this.connect_vms(vms, cbinner);
        }, this);
        view.show_vms(this.model, vms, [], cb, "subtitle");
      }

    });
    
    views.NetworksCollectionView = views.ext.CollectionView.extend({
      collection: storage.networks,
      collection_name: 'networks',
      model_view_cls: views.NetworkView,
      create_view_cls: views.NetworkCreateView,
      
      init: function() {
        this.public_added = false;
        views.NetworksCollectionView.__super__.init.apply(this, arguments);
      },
      
      check_empty: function() {
        views.NetworksCollectionView.__super__.check_empty.apply(this, arguments);
        //if (this.$(".private").children().length == 0) {
          //this.$(".private").hide();
        //} else {
          //this.$(".private").show();
        //}
      },

      add_model: function(m) {
        if (m.get('is_public') && !this.public_added) {
          this.combined_public = new models.networks.CombinedPublicNetwork();
          this.combined_public_view = new views.NetworkView({
            model: this.combined_public
          });
          this.add_model_view(this.combined_public_view, this.combined_public, 0);
          this.combined_public_view.$("i").hide();
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
            this.list.find("li").click(function() {
                self.handle_vm_click($(this));
            });
            
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

        reset: function() {
            this.list.find("li").remove();
        },

        beforeOpen: function() {
            this.reset();
            this.update_layout();
        },
        
        vm: function(vm) {
            if (vm.id) { var id = vm.id } else {var id = vm}
            return this.list.find(".vm-" + id);
        },

        get_selected: function() {
            return this.list.find(".selected").map(function() {return $(this).data('vm')})
        },

        update_layout: function() {
            this.unset_in_progress();
            this.in_progress = false;

            if (this.vms.length == 0) {
                this.empty_message.show();
            } else {
                this.empty_message.hide();
            }

            _.each(this.vms, _.bind(function(vm){
                var html = '<li class="vm option options-object vm-{0}">' +
                           '<div class="options-object-cont">' +
                           '{2}' + 
                           '<span class="title">{1}</span>' + 
                           '<span class="value">{3}</span></div>' + 
                           '</li>';
                var el = $(html.format(vm.id, 
                       util.truncate(_.escape(vm.get("name")), 23), 
                       snf.ui.helpers.vm_icon_tag(vm, "small", {'class':'os'}),
                       _.escape(vm.get_os())
                ));
                el.data({vm:vm, vm_id:vm.id});
                this.list.append(el);

                vm.bind("remove", function(){ el.remove()})
                vm.bind("change:name", function(i,v){el.find(".title").text(v)})
            }, this));
            
            this.init_handlers();
            this.set_selected();
        },

        set_selected: function() {
            _.each(this.selected, _.bind(function(el){
                this.vm(el).addClass("selected");
            }, this));
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

        submit: function() {
            if (!this.get_selected().length) { return }
            this.cb(this.get_selected());
        }
    });
 
})(this);
