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
    var models = snf.models = snf.models || {}
    var storage = snf.storage = snf.storage || {};
    var ui = snf.ui = snf.ui || {};
    var util = snf.util = snf.util || {};

    var views = snf.views = snf.views || {}

    // shortcuts
    var bb = root.Backbone;

    
    views.FlavorOptionsView = views.View.extend({

        choices_meta: {
            'cpu': {title: 'CPUs', description: 'Choose number of CPU cores'},
            'ram': {title: 'Memory size', description: 'Choose memory size'},
            'disk': {title: 'Disk size', description: 'Choose disk size'},
            'disk_template': {title: 'Storage', description: 'Select storage type'}
        },

        initialize: function(options) {
            views.FlavorOptionsView.__super__.initialize.apply(this);
            _.bindAll(this);
            this.$el = $(this.el);
            this.flavors = options.flavors || synnefo.storage.flavors.active();
            this.collection = options.collection || synnefo.storage.flavors;
            this.choices = options.choices || ['cpu', 'ram', 'disk', 
                                               'disk_template'];
            this.hidden_choices = options.hidden_choices || [];
            this.quotas = options.quotas || synnefo.storage.quotas;
            this.selected_flavor = options.selected_flavor || undefined;
            this.extra_quotas = options.extra_quotas || undefined;
            this.project = options.project;
            this.render();
            if (this.selected_flavor) { this.set_flavor(this.selected_flavor)}
        },

        render: function() {
            this.$el.empty();
            this.each_choice(function(choice) {
                var el = this[choice + '_el'] = $("<div>");
                el.addClass("flavor-options clearfix");
                el.addClass(choice);
                var title = $("<h4 class='clearfix'><span class='title'>" + 
                              "</span><span class='available'></span>" +
                              "<span class='desc'></span></h4>");
                el.append(title);
                el.find("span.title").text(this.choices_meta[choice].title);
                el.find("span.desc").text(this.choices_meta[choice].description);
                var ul = $("<ul/>");
                ul.addClass("flavors-"+choice+"-list flavor-opts-list clearfix");
                el.append(ul);
                this.$el.append(el);
                if (this.hidden_choices.indexOf(choice) > -1) {
                    el.hide();
                }
            });
            this.update_quota_left();
            this.fill();
            this.set_unavailable();
            this.init_handlers();
        },
        
        get_current: function(choice, value) {
          var found = false;
          _.each(this.flavors, _.bind(function(f){
              if (found) { return }
              if (f.get(choice) == value) {
                  found = true;
                  to_select = f;
              }
          }, this));
        },

        init_handlers: function() {
            this.$el.on('click', 'li.choice', _.bind(function(e) {
                var el = $(e.target).closest('li');
                var choice = el.data('type');
                var value = el.data('value');
                var to_select = this.selected_flavor;
                if (to_select) {
                    var attrs = _.clone(to_select.attributes);
                    attrs[choice] = value;
                    to_select = this.collection.get_flavor(attrs.cpu, attrs.ram, 
                                                           attrs.disk, 
                                                           attrs.disk_template);
                }

                if (!to_select) {
                  to_select = this.get_current(choice, value);
                }
                this.set_flavor(to_select);
            }, this));
        },
        
        update_quota_left: function() {
            this.each_choice(function(choice){
                var el = this[choice + '_el'].find(".available");
                el.removeClass("error");
                var quota = this.quotas.get('cyclades.'+choice);
                if (!quota) { return }
                var type = choice;
                var active = true;
                var key = 'available';
                var quotas = synnefo.storage.quotas;
                var available_dsp = quotas.get('cyclades.'+type).get_readable(key, active);
                var available = quotas.get('cyclades.'+type).get(key);
                var content = "({0} left)".format(available_dsp);
                if (available <= 0) { content = "(None left)"; el.addClass("error") }
                el.text(content);
            });
        },

        metric_for_choice: function(choice) {
            var map = {ram:'MB', cpu:'X', disk:'GB', disk_template:''};
            return map[choice] || '';
        },
        
        set_unavailable: function() {
            this.$el.find("li.choice").removeClass("disabled");
            var quotas = this.project.quotas.get_available_for_vm({'active': true});
            var extra_quotas = this.extra_quotas;
            var user_excluded = storage.flavors.unavailable_values_for_quotas(
              quotas, 
              storage.flavors.active(), extra_quotas);
            _.each(user_excluded, _.bind(function(values, key) {
                _.each(values, _.bind(function(value) {
                    var choice_el = this.select_choice(key, value);
                    choice_el.addClass("disabled").removeClass("selected");
                }, this));
            }, this));
        },

        select_choice: function(key, value) {
            return this.$el.find(".choice[data-type="+key+"][data-value="+value+"]");
        },

        fill: function(flavors) {
            var flavors = flavors || this.flavors;
            var data = this.collection.get_data(flavors);
            this.each_choice(function(choice) {
                var el = this[choice + '_el'].find("ul");
                el.empty();
                var key = choice;
                if (key == 'ram') { key = 'mem'}
                var values = data[key];
                if (!values) { return }
                _.each(values, _.bind(function(value) {
                    var entry = $("<li class='choice choice-" + choice + "' " +
                                  "data-value=" + value +
                                  " data-type=" + choice + ">" +
                                  "<span class='value'></span>" +
                                  "<span class='metric'></span></li>");
                    entry.find(".value").text(value);
                    entry.find(".metric").text(this.metric_for_choice(choice));
                    el.append(entry);
                    el.attr('value', value);
                }, this));
            });
        },

        set_flavor: function(flavor) {
            this.$el.find("li").removeClass("selected");
            if (!flavor) {this.selected_flavor = undefined; return}
            var no_select = false;
            var self = this;
            this.each_choice(function(choice){
                var el = this[choice + '_el'];
                var choice = el.find('.choice-'+choice+'[data-value='+flavor.get(choice)+']');
                choice.addClass("selected");
            });
            this.selected_flavor = flavor;
            this.trigger("flavor:select", this.selected_flavor);
            return this.selected_flavor;
        },

        each_choice: function(f) {
            return _.each(this.choices, _.bind(f, this));
        }
    });

    views.VmResizeView = views.Overlay.extend({
        
        view_id: "vm_resize_view",
        content_selector: "#vm-resize-overlay-content",
        css_class: 'overlay-vm-resize overlay-info create-wizard-overlay',
        overlay_id: "vm-resize-overlay",

        subtitle: "",
        title: "Resize Machine",

        initialize: function(options) {
            this.flavors_view = undefined; 
            views.VmResizeView.__super__.initialize.apply(this);
            _.bindAll(this);
            this.submit = this.$(".form-action.resize");
            this.shutdown = this.$(".form-action.shutdown");
            this.pre_init_handlers();
            this.handle_shutdown_complete = _.bind(this.handle_shutdown_complete, this);
        },

        pre_init_handlers: function() {
            this.submit.click(_.bind(function(){
                if (this.submit.hasClass("disabled")) {
                    return;
                };
                this.submit_resize(this.flavors_view.selected_flavor);
            }, this));
            this.shutdown.click(_.bind(this.handle_shutdown, this));
        },
        
        handle_shutdown: function() {
          if (this.shutdown.hasClass("in-progress") || 
              this.shutdown.hasClass("disabled")) {
            return;
          }
          
          this.shutdown.addClass("in-progress");

          this.vm.unbind("change:status", this.handle_shutdown_complete);
          this.vm.bind("change:status", this.handle_shutdown_complete);

          var self = this;
          this.vm.call("shutdown", undefined, function() {
            self.shutdown.removeClass("in-progress");
            self.update_layout();
            self.hide();
          });
        },

        handle_shutdown_complete: function(vm) {
          if (!vm.is_active()) {
            this.shutdown.removeClass("in-progress");
            this.vm.unbind("change:status", this.handle_shutdown_complete);
          }
        },

        submit_resize: function(flv) {
            if (this.submit.hasClass("in-progress")) { return }
            this.submit.addClass("in-progress");
            var vm = this.vm;
            var complete = _.bind(function() {
              vm.set({'flavor': flv});
              vm.set({'flavorRef': flv.id});
              this.vm && this.hide();
            }, this);
            this.vm.call("resize", complete, complete, {flavor:flv.id});
        },
        
        show_with_warning: function(vm) {
          this.show(vm);
          this.start_warning.show();
        },

        show: function(vm) {
            this.start_warning = this.$(".warning.start").hide();
            this.start_warning.hide();
            this.submit.removeClass("in-progress");
            this.vm = vm;
            this.project = vm.get('project');
            this.vm.bind("change", this.handle_vm_change);
            if (this.flavors_view) {
                this.flavors_view.remove();
            }
            this.warning = this.$(".warning.shutdown");
            this.warning.hide();
            this.submit.show();
            this.shutdown.removeClass("in-progress");
            this.$(".flavor-options-inner-cont").append("<div>");
            var extra_quota = this.vm.get_flavor_quotas();
            if (!this.vm.is_active()) {
              extra_quota = undefined;
            }
            this.flavors_view = new snf.views.FlavorOptionsView({
                flavors:this.vm.get_resize_flavors(),
                el: this.$(".flavor-options-inner-cont div"),
                hidden_choices:['disk', 'disk_template'],
                selected_flavor: this.vm.get_flavor(),
                extra_quotas: extra_quota,
                project: this.project
            });
            this.selected_flavor = this.vm.get_flavor();
            this.handle_flavor_select(this.selected_flavor);
            this.flavors_view.bind("flavor:select", this.handle_flavor_select)
            this.submit.addClass("disabled");
            views.VmResizeView.__super__.show.apply(this);
        },

        handle_flavor_select: function(flv) {
            this.selected_flavor = flv;
            if (!flv || (flv.id == this.vm.get_flavor().id)) {
                this.submit.addClass("disabled");
                if (!this.shutdown.hasClass("in-progress")) {
                  this.shutdown.addClass("disabled");
                }
            } else {
                if (this.vm.can_resize()) {
                  this.submit.removeClass("disabled");
                } else {
                  this.shutdown.removeClass("disabled hidden");
                  this.warning.show();
                }
            }
            if (flv && !this.vm.can_start(flv, true)) {
              if (!this.vm.is_active()) {
                this.start_warning.show();
              }
            } else {
              this.start_warning.hide();
            }
            this.update_vm_status();
        },

        update_vm_status: function() {
          if (this.vm.get("status") == "STOPPED") {
            this.warning.hide();
          }
          if (this.vm.get("status") == "SHUTDOWN") {
            this.shutdown.addClass("in-progress").removeClass("disabled");
            this.warning.hide();
          }
        },

        beforeOpen: function() {
            this.update_layout();
            this.init_handlers();
        },

        update_layout: function() {
            this.update_actions();
            this.update_vm_details();
            this.render_choices();
            this.update_vm_status();
        },

        update_actions: function() {
          if (!this.vm.can_resize()) {
            this.shutdown.show();
            this.warning.show();
            this.shutdown.removeClass("disabled");
            if (this.selected_flavor) {
              this.handle_flavor_select(this.selected_flavor);
            } else {
              if (!this.shutdown.hasClass("in-progress")) {
                this.shutdown.addClass("disabled");
              }
            }
            this.submit.addClass("disabled");
          } else {
            if (this.selected_flavor && this.selected_flavor.id != this.vm.get_flavor().id) {
              this.submit.removeClass("disabled");
            }
            this.shutdown.hide();
          }
        },
          
        render_choices: function() {
        },

        update_vm_details: function() {
            var name = _.escape(util.truncate(this.vm.get("name"), 70));
            this.set_subtitle(name + snf.ui.helpers.vm_icon_tag(this.vm, "small"));
        },

        handle_vm_change: function() {
          this.update_layout();
        },

        init_handlers: function() {
        },

        onClose: function() {
            if (!this.visible()) { return }
            this.editing = false;
            this.vm.unbind("change", this.handle_vm_change);
            this.vm.unbind("change:status", this.handle_shutdown_complete);
            this.vm = undefined;
        }
    });
    
})(this);

