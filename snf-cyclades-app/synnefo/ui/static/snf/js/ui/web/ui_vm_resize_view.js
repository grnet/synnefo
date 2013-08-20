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
        
        init_handlers: function() {
            this.$el.on('click', 'li.choice', _.bind(function(e) {
                var el = $(e.target).closest('li');
                if (el.hasClass('disabled')) { return }
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
                    var found = false;
                    _.each(this.flavors, _.bind(function(f){
                        if (found) { return }
                        if (f.get(choice) == value) {
                            found = true;
                            to_select = f;
                        }
                    }, this));
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
            var quotas = this.quotas.get_available_for_vm({'active': true});
            var extra_quotas = this.extra_quotas;
            var user_excluded = storage.flavors.unavailable_values_for_quotas(
              quotas, 
              storage.flavors.active());
            _.each(user_excluded, _.bind(function(values, key) {
                _.each(values, _.bind(function(value) {
                    var choice_el = this.select_choice(key, value);
                    choice_el.addClass("disabled");
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
            this.each_choice(function(choice){
                var el = this[choice + '_el'];
                var choice = el.find('.choice-'+choice+'[data-value='+flavor.get(choice)+']');
                choice.addClass("selected");
            });
            this.selected_flavor = flavor;
            this.trigger("flavor:select", this.selected_flavor);
        },

        each_choice: function(f) {
            return _.each(this.choices, _.bind(f, this));
        }
    });

    views.VmResizeView = views.Overlay.extend({
        
        view_id: "vm_resize_view",
        content_selector: "#vm-resize-overlay-content",
        css_class: 'overlay-vm-resize overlay-info',
        overlay_id: "vm-resize-overlay",

        subtitle: "",
        title: "Resize Machine",

        initialize: function(options) {
            this.flavors_view = undefined; 
            views.VmResizeView.__super__.initialize.apply(this);
            _.bindAll(this);
            this.submit = this.$(".form-action");
            this.pre_init_handlers();
        },

        pre_init_handlers: function() {
            this.submit.click(_.bind(function(){
                if (this.submit.hasClass("disabled")) {
                    return;
                };
                this.submit_resize(this.flavors_view.selected_flavor);
            }, this));
        },
        
        submit_resize: function(flv) {
            this.submit.addClass("in-progress");
            var complete = _.bind(function() {
              this.vm.set({'flavor': flv});
              this.vm.set({'flavorRef': flv.id});
              this.hide()
            }, this);
            this.vm.call("resize", complete, complete, {flavor:flv.id});
        },

        show: function(vm) {
            this.submit.removeClass("in-progress");
            this.vm = vm;
            this.vm.bind("change", this.handle_vm_change);
            if (this.flavors_view) {
                this.flavors_view.remove();
            }

            if (!this.vm.can_resize()) {
                this.$(".warning").show();
                this.submit.hide();
            } else {
                this.$(".warning").hide();
                this.submit.show();
                this.$(".flavor-options-inner-cont").append("<div>");
                this.flavors_view = new snf.views.FlavorOptionsView({
                    flavors:this.vm.get_resize_flavors(),
                    el: this.$(".flavor-options-inner-cont div"),
                    hidden_choices:['disk', 'disk_template'],
                    selected_flavor: this.vm.get_flavor(),
                    extra_quotas: this.vm.get_flavor_quotas()
                });
                this.flavors_view.bind("flavor:select", this.handle_flavor_select)
                this.submit.addClass("disabled");
            }
            views.VmResizeView.__super__.show.apply(this);
        },

        handle_flavor_select: function(flv) {
            if (flv.id == this.vm.get_flavor().id) {
                this.submit.addClass("disabled");
            } else {
                this.submit.removeClass("disabled");
            }
        },

        beforeOpen: function() {
            this.update_layout();
            this.init_handlers();
        },

        update_layout: function() {
            this.update_vm_details();
            this.render_choices();
        },
          
        render_choices: function() {
        },

        update_vm_details: function() {
            this.set_subtitle(this.vm.escape("name") + 
                              snf.ui.helpers.vm_icon_tag(this.vm, 
                                                         "small"));
        },

        handle_vm_change: function() {
          this.update_layout();
        },

        init_handlers: function() {
        },

        onClose: function() {
            this.editing = false;
            this.vm.unbind("change", this.handle_vm_change);
            this.vm = undefined;
        }
    });
    
})(this);

