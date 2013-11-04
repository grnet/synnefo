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
    var models = snf.models = snf.models || {}
    var storage = snf.storage = snf.storage || {};
    var ui = snf.ui = snf.ui || {};
    var util = snf.util = snf.util || {};

    var views = snf.views = snf.views || {}

    // shortcuts
    var bb = root.Backbone;


    views.VMCreationPasswordView = views.Overlay.extend({
        view_id: "creation_password_view",
        content_selector: "#creation-password-overlay",
        css_class: 'overlay-password overlay-info',
        overlay_id: "creation-password-overlay",

        subtitle: "",
        title: "Machine password",

        initialize: function(options) {
            views.FeedbackView.__super__.initialize.apply(this, arguments);
            _.bindAll(this, 'show_password');

            this.password = this.$("#new-machine-password");
            this.copy = this.$(".clipboard");

            this.$(".show-machine").click(_.bind(function(){
                if (this.$(".show-machine").hasClass("in-progress")) {
                    return;
                }
                this.hide();
            }, this));

            _.bindAll(this, "handle_vm_added");
            storage.vms.bind("add", this.handle_vm_added);
            this.password.text("");
        },

        handle_vm_added: function() {
            this.$(".show-machine").removeClass("in-progress");
        },
        
        show_password: function() {
            this.$(".show-machine").addClass("in-progress");
            this.password.text(this.pass);
            if (storage.vms.get(this.vm_id)) {
                this.$(".show-machine").removeClass("in-progress");
            }
            
            this.clip = new snf.util.ClipHelper(this.copy, this.pass);
        },

        onClose: function() {
            this.password.text("");
            this.vm_id = undefined;
            try { delete this.clip; } catch (err) {};
        },
        
        beforeOpen: function() {
            this.copy.empty();
        },
        
        onOpen: function() {
            this.show_password();
        },

        show: function(pass, vm_id) {
            this.pass = pass;
            this.vm_id = vm_id;
            
            views.VMCreationPasswordView.__super__.show.apply(this, arguments);
        }
    })


    
    views.CreateVMStepView = views.View.extend({
        step: "1",
        title: "Image",
        submit: false,

        initialize: function(view) {
            this.parent = view;
            this.el = view.$("div.create-step-cont.step-" + this.step);
            this.header = this.$(".step-header .step-" + this.step);
            this.view_id = "create_step_" + this.step;

            views.CreateVMStepView.__super__.initialize.apply(this);
        },

        show: function() {
            // show current
            this.el.show();
            this.header.addClass("current");
            this.header.show();
            this.update_layout();
        },

        reset: function() {
        }
    })

    views.CreateImageSelectView = views.CreateVMStepView.extend({

        initialize: function() {
            views.CreateImageSelectView.__super__.initialize.apply(this, arguments);

            // elements
            this.images_list_cont = this.$(".images-list-cont");
            this.images_list = this.$(".images-list-cont ul");
            this.image_details = this.$(".images-info-cont");
            this.image_details_desc = this.$(".images-info-cont .description p");
            this.image_details_title = this.$(".images-info-cont h4");
            this.image_details_size = this.$(".images-info-cont .size p");
            this.image_details_os = this.$(".images-info-cont .os p");
            this.image_details_kernel = this.$(".images-info-cont .kernel p");
            this.image_details_gui = this.$(".images-info-cont .gui p");
            this.image_details_vm = this.$(".images-info-cont .vm-name p");

            this.categories_list = this.$(".category-filters");
            
            // params initialization
            this.type_selections = {"system": "System"};
            this.type_selections_order = ['system'];
            
            this.images_storage = snf.storage.images;

            // apply image service specific image types
            if (this.images_storage.type_selections) {
                this.type_selections = _.extend(
                    this.images_storage.type_selections,
                    this.type_selections)

                this.type_selections_order = this.images_storage.type_selections_order;
            }

            this.selected_type = undefined;
            this.selected_categories = [];

            this.images = [];
            this.images_ids = [];
            this.custom_images = [];

            // handlers initialization
            this.create_types_selection_options();
            this.init_handlers();
            this.init_position();
        },
        
        init_position: function() {
            //this.el.css({position: "absolute"});
            //this.el.css({top:"10px"})
        },
        
        init_handlers: function() {
            var self = this;
            this.types.live("click", function() {
                self.select_type($(this).attr("id").replace("type-select-",""));
            });
            
            this.image_details.find(".hide").click(_.bind(function(){
                this.hide_image_details();
            }, this));

            this.$(".register-custom-image").live("click", function(){
                var confirm_close = true;
                if (confirm_close) {
                    snf.ui.main.custom_images_view.show(self.parent);
                } else {
                }
            })

            $(".image-warning .confirm").bind('click', function(){
                $(".image-warning").hide();
                $(".create-controls").show();
            })
        },

        update_images: function(images) {
            this.images = images;
            this.images_ids = _.map(this.images, function(img){return img.id});
            return this.images;
        },

        create_types_selection_options: function() {
            var list = this.$("ul.type-filter");
            _.each(this.type_selections_order, _.bind(function(key) {
                list.append('<li id="type-select-{0}">{1}</li>'.format(key, this.type_selections[key]));
            }, this));
            this.types = this.$(".type-filter li");
        },

        update_layout: function() {
            if (!this.selected_type) {
                this.selected_type = _.keys(this.type_selections)[0];
            }
            this.select_type(this.selected_type);
        },
        
        get_categories: function(images) {
            return [];
            return ["Desktop", "Server", "Linux", "Windows"];
        },

        reset_categories: function() {
            var categories = this.get_categories(this.images);
            this.categories_list.find("li").remove();

            _.each(categories, _.bind(function(cat) {
                var el = $("<li />");
                el.text(cat);
                this.categories_list.append(el);
            }, this));

            if (!categories.length) { 
                this.categories_list.parent().find(".clear").hide();
                this.categories_list.parent().find(".empty").show();
            } else {
                this.categories_list.parent().find(".clear").show();
                this.categories_list.parent().find(".empty").hide();
            }
        },
        
        show_loading_view: function() {
            this.$(".images-list-cont .empty").hide();
            this.images_list.hide();
            this.$(".images-list-cont .loading").show();
            this.$(".images-list-cont .images-list").hide();
            this.reset_categories();
            this.update_images([]);
            this.reset_images();
            this.hide_list_loading();
        },

        hide_loading_view: function(images) {
            this.$(".images-list-cont .loading").hide();
            this.$(".images-list-cont .images-list").show();
            this.reset_categories();
            this.update_images(images);
            this.reset_images();
            this.select_image(this.selected_image);
            this.hide_list_loading();
            $(".custom-image-help").hide();
            if (this.selected_type == 'personal' && !images.length) {
                $(".custom-image-help").show();
            }

        },

        select_type: function(type) {
            this.selected_type = type;
            this.types.removeClass("selected");
            this.types.filter("#type-select-" + this.selected_type).addClass("selected");
            this.images_storage.update_images_for_type(
                this.selected_type, 
                _.bind(this.show_loading_view, this), 
                _.bind(this.hide_loading_view, this)
            );

            this.update_layout_for_type(type);
        },

        update_layout_for_type: function(type) {
            if (type != "system") {
                this.$(".custom-action").hide();
            } else {
                this.$(".custom-action").hide();
            }

        },

        show_list_loading: function() {
            this.$(".images-list-cont").addClass("loading");
        },

        hide_list_loading: function() {
            this.$(".images-list-cont").removeClass("loading");
        },
        
        display_warning_for_image: function(image) {
          if (image && !image.is_system_image() && !image.owned_by(synnefo.user)) {
            $(".create-vm .image-warning").show();
            $(".create-controls").hide();
          } else {
            $(".create-vm .image-warning").hide();
            $(".create-controls").show();
          }
        },

        select_image: function(image) {
            if (image && image.get('id') && !_.include(this.images_ids, image.get('id'))) {
                image = undefined;
            }
            if (!image && this.images_ids.length) {
                if (this.selected_image && this.images_ids.indexOf(this.selected_image.id) > -1) {
                    image = this.selected_image;
                } else {
                    image = this.images_storage.get(this.images_ids[0]);
                }
            }
             
            // no images select null image so that next button gets hidden
            if (!this.images_ids.length) { image = undefined };
            
            if ((!this.selected_image && image) || (this.selected_image != image))
                this.trigger("change", image);
                this.display_warning_for_image(image);

            this.selected_image = image;
                
            if (image) {
                this.images_list.find(".image-details").removeClass("selected");
                this.images_list.find(".image-details#create-vm-image-" + this.selected_image.id).addClass("selected");
                this.update_image_details(image);

            } else {
            }

            this.image_details.hide();
            this.validate();
        },

        update_image_details: function(image) {
            this.image_details_desc.hide().parent().hide();
            if (image.get_description()) {
                this.image_details_desc.html(image.get_description(false)).show().parent().show();
            }
            var img = snf.ui.helpers.os_icon_tag(image.escape("OS"))
            if (image.get("name")) {
                this.image_details_title.html(img + image.escape("name")).show().parent().show();
            }
            
            var extra_details = this.image_details.find(".extra-details");
            // clean prevously added extra details
            extra_details.find(".image-detail").remove();
            
            var skip_keys = ['description', 'sortorder']
            var meta_keys = ['owner', 'OS', 'kernel', 'GUI'];
            var detail_tpl = ('<div class="clearfix image-detail {2}">' +
                             '<span class="title clearfix">{0}' +
                             '<span class="custom">custom</span></span>' +
                             '<p class="value">{1}</p>' + 
                             '</div>');
            meta_keys = _.union(meta_keys, this.images_storage.display_metadata || []);
            
            var append_metadata_row = function(key, is_extra) {
                var value;
                var method = 'get_' + key.toLowerCase();
                var display_method = 'display_' + key.toLowerCase();
                 
                if (image[display_method]) {
                    value = image[display_method]();
                } else if (image[method]) {
                    value = image[method]();
                } else {
                    value = image.get(key);

                    if (!value) {
                        value = image.get_meta(key);
                    }
                }
                    
                if (!value) { return; }
                 
                var label = this.images_storage.meta_labels[key];
                if (!label) {
                    var label = _(key.replace(/_/g," ")).capitalize();
                }
                var row_cls = key.toLowerCase();
                if (is_extra) { row_cls += " extra-meta" };
                extra_details.append(detail_tpl.format(_.escape(label), value, row_cls));
            }

            _.each(meta_keys, function(key) {
                append_metadata_row.apply(this, [key]);
            }, this);
            
            if (synnefo.storage.images.display_extra_metadata) {
                _.each(image.get('metadata'), function(value, key) {
                    if (!_.contains(meta_keys, key) && 
                        !_.contains(meta_keys, key.toLowerCase()) &&
                        !_.contains(meta_keys, key.toUpperCase()) &&
                        !_.contains(skip_keys, key)) {
                            append_metadata_row.apply(this, [key, true]);
                    }
                }, this);
            }
        },

        reset_images: function() {
            this.images_list.find("li").remove();
            _.each(this.images, _.bind(function(img){
                this.add_image(img);
            }, this))
            
            if (this.images.length) {
                this.images_list.parent().find(".empty").hide();
                this.images_list.show();
            } else {
                this.images_list.parent().find(".empty").show();
                this.images_list.hide();
            }

            var self = this;
            this.images_list.find(".image-details").click(function(){
                self.select_image($(this).data("image"));
            });
            
        },

        show: function() {
            this.image_details.hide();
            this.parent.$(".create-controls").show();

            views.CreateImageSelectView.__super__.show.apply(this, arguments);
        },

        add_image: function(img) {
            var image = $(('<li id="create-vm-image-{1}"' +
                           'class="image-details clearfix">{2}{0}'+
                           '<span class="show-details">details</span>'+
                           '<span class="size"><span class="prepend">by </span>{5}</span>' + 
                           '<span class="owner">' +
                           '<span class="prepend"></span>' +
                           '{3}</span>' + 
                           '<p>{4}</p>' +
                           '</li>').format(img.escape("name"), 
                                                  img.id, 
                                                  snf.ui.helpers.os_icon_tag(img.escape("OS")),
                                                  _.escape(img.get_readable_size()),
                                                  util.truncate(img.get_description(false), 35),
                                                  _.escape(img.display_owner())));
            image.data("image", img);
            image.data("image_id", img.id);
            this.images_list.append(image);
            image.find(".show-details").click(_.bind(function(e){
                e.preventDefault();
                e.stopPropagation();
                this.show_image_details(img);
            }, this))
        },
            
        hide_image_details: function() {
            this.image_details.fadeOut(200);
            this.parent.$(".create-controls").show();
        },

        show_image_details: function(img) {
            this.parent.$(".create-controls").hide();
            this.update_image_details(img);
            this.image_details.fadeIn(100);
        },

        reset: function() {
            this.selected_image = false;
            this.select_type("system");
        },

        get: function() {
            return {'image': this.selected_image};
        },

        validate: function() {
            if (!this.selected_image) {
                this.parent.$(".form-action.next").hide();
            } else {
                this.parent.$(".form-action.next").show();
            }
        }
    });

    views.CreateFlavorSelectView = views.CreateVMStepView.extend({
        step: 2,
        initialize: function() {
            views.CreateFlavorSelectView.__super__.initialize.apply(this, arguments);
            this.parent.bind("image:change", _.bind(this.handle_image_change, this));

            this.cpus = this.$(".flavors-cpu-list");
            this.disks = this.$(".flavors-disk-list");
            this.disk_templates = this.$(".flavors-disk-template-list");
            this.mems = this.$(".flavors-mem-list");

            this.predefined_flavors = SUGGESTED_FLAVORS;
            this.predefined_flavors_keys = _.keys(SUGGESTED_FLAVORS);
            this.predefined_flavors_keys = _.sortBy(this.predefined_flavors_keys, _.bind(function(k){
                var flv = this.predefined_flavors[k];
                return (flv.ram * flv.cpu * flv.disk);
            }, this));

            this.predefined = this.$(".predefined-list");
        },

        handle_image_change: function(data) {
            this.current_image = data;
            this.update_valid_predefined();
            this.current_flavor = undefined;
            this.update_flavors_data();
            this.update_predefined_flavors();
            this.reset_flavors();
            this.update_layout();
        },

        validate_selected_flavor: function() {
            if (!this.flavor_is_valid(this.current_flavor)) {
                this.select_valid_flavor();
            }
        },

        reset_flavors: function() {
            this.$(".flavor-opts-list .option").remove();
            this.create_flavors();
        },

        update_predefined_flavors: function() {
            this.predefined.find("li").remove();
            _.each(this.predefined_flavors_keys, _.bind(function(key) {
                var val = this.predefined_flavors[key];
                var el = $(('<li class="predefined-selection" id="predefined-flavor-{0}">' +
                           '{1}</li>').format(key, _.escape(_(key).capitalize())));

                this.predefined.append(el);
                el.data({flavor: storage.flavors.get_flavor(val.cpu, val.ram, val.disk, val.disk_template, this.flavors)});
                el.click(_.bind(function() {
                    this.handle_predefined_click(el);
                }, this))
            }, this));
            this.update_valid_predefined();
        },

        handle_predefined_click: function(el) {
            if (el.hasClass("disabled")) { return };
            this.set_current(el.data("flavor"));
        },

        select_valid_flavor: function() {
            var found = false;
            var self = this;

            _.each(["cpu", "mem", "disk"], function(t) {
              var el = $(".flavor-options."+t);
              var all = el.find(".flavor-opts-list li").length;
              var disabled = el.find(".flavor-opts-list li.disabled").length;
              if (disabled >= all) {
                el.find("h4").addClass("error");
              } else {
                el.find("h4").removeClass("error");
              }
            })

            _.each(this.flavors, function(flv) {
                if (self.flavor_is_valid(flv)) {
                    found = flv;
                    return false;
                }
            });
            
            if (found) {
                this.set_current(found);
            } else {
                this.current_flavor = undefined;
                this.validate();
                this.$("li.predefined-selection").addClass("disabled");
                this.$(".flavor-opts-list li").removeClass("selected");
            }
        },

        update_valid_predefined: function() {
            this.update_unavailable_values();
            var self = this;
            this.valid_predefined = _.select(_.map(this.predefined_flavors, function(flv, key){
                var existing = storage.flavors.get_flavor(flv.cpu, flv.ram, flv.disk, flv.disk_template, self.flavors);
                // non existing
                if (!existing) {
                    return false;
                }
                
                // not available for image
                if (self.unavailable_values && self.unavailable_values.disk.indexOf(existing.get_disk_size()) > -1) {
                    return false
                }

                return key;
            }), function(ret) { return ret });
            
            $("li.predefined-selection").addClass("disabled");
            _.each(this.valid_predefined, function(key) {
                $("#predefined-flavor-" + key).removeClass("disabled");
            })
        },

        update_selected_predefined: function() {
            var self = this;
            this.predefined.find("li").removeClass("selected");

            _.each(this.valid_predefined, function(key){
                var flv = self.predefined_flavors[key];
                var exists = storage.flavors.get_flavor(flv.cpu, flv.ram, flv.disk, flv.disk_template, self.flavors);

                if (exists && (exists.id == self.current_flavor.id)) {
                    $("#predefined-flavor-" + key).addClass("selected");
                }
            })
        },
        
        update_flavors_data: function() {
            this.flavors = storage.flavors.active();
            this.flavors_data = storage.flavors.get_data(this.flavors);
            
            var self = this;
            var set = false;
            
            // FIXME: validate current flavor
            
            if (!this.current_flavor) {
                _.each(this.valid_predefined, function(key) {
                    var flv = self.predefined_flavors[key];
                    var exists = storage.flavors.get_flavor(flv.cpu, flv.ram, flv.disk, flv.disk_template, self.flavors);
                    if (exists && !set) {
                        self.set_current(exists);
                        set = true;
                    }
                })
            }

            this.update_unavailable_values();
        },

        update_unavailable_values: function() {
            
            var unavailable = {disk:[], ram:[], cpu:[]}
            var user_excluded = {disk:[], ram:[], cpu:[]}
            var image_excluded = {disk:[], ram:[], cpu:[]}

            if (this.current_image) {
              image_excluded = storage.flavors.unavailable_values_for_image(this.current_image);
            }

            var quotas = synnefo.storage.quotas.get_available_for_vm({active: true});
            var user_excluded = storage.flavors.unavailable_values_for_quotas(quotas);

            unavailable.disk = user_excluded.disk.concat(image_excluded.disk);
            unavailable.ram = user_excluded.ram.concat(image_excluded.ram);
            unavailable.cpu = user_excluded.cpu.concat(image_excluded.cpu);
            
            this.unavailable_values = unavailable;
        },
        
        flavor_is_valid: function(flv) {
            if (!flv) { return false };

            var existing = storage.flavors.get_flavor(flv.get("cpu"), flv.get("ram"), flv.get("disk"), flv.get("disk_template"), this.flavors);
            if (!existing) { return false };
            
            if (this.unavailable_values && (this.unavailable_values.disk.indexOf(parseInt(flv.get("disk")) * 1000) > -1)) {
                return false;
            }
            if (this.unavailable_values && (this.unavailable_values.ram.indexOf(parseInt(flv.get("ram"))) > -1)) {
                return false;
            }
            if (this.unavailable_values && (this.unavailable_values.cpu.indexOf(parseInt(flv.get("cpu"))) > -1)) {
                return false;
            }
            return true;
        },
            
        set_valid_current_for: function(t, val) {
            var found = this.flavors[0];
            _.each(this.flavors, function(flv) {
                if (flv.get(t) == val) {
                    found = flv;
                }
            });

            this.set_current(found);
            this.validate_selected_flavor();
        },

        set_current: function(flv) {

            if (!flv) {
                // user clicked on invalid combination
                // force the first available choice for the
                // type of option he last clicked
                this.set_valid_current_for.apply(this, this.last_choice);
                return;
            }

            this.current_flavor = flv;
            this.trigger("change");
            if (this.current_flavor) {
                this.update_selected_flavor();
                this.update_selected_predefined();
            }
            
            this.validate();
        },
        
        select_default_flavor: function() {
               
        },

        update_selected_from_ui: function() {
            this.set_current(this.ui_selected());
        },
        
        update_disabled_flavors: function() {
            this.$(".flavor-options.disk li").removeClass("disabled");
            if (!this.unavailable_values) { return }
            
            this.$("#create-vm-flavor-options .flavor-options.disk li").each(_.bind(function(i, el){
                var el_value = $(el).data("value") * 1000;
                if (this.unavailable_values.disk.indexOf(el_value) > -1) {
                    $(el).addClass("disabled");
                    $(el).removeClass("selected");
                };
            }, this));

            this.$("#create-vm-flavor-options .flavor-options.mem li").each(_.bind(function(i, el){
                var el_value = $(el).data("value");
                if (this.unavailable_values.ram.indexOf(el_value) > -1) {
                    $(el).addClass("disabled");
                    $(el).removeClass("selected");
                };
            }, this));

            this.$("#create-vm-flavor-options .flavor-options.cpu li").each(_.bind(function(i, el){
                var el_value = $(el).data("value");
                if (this.unavailable_values.cpu.indexOf(el_value) > -1) {
                    $(el).addClass("disabled");
                    $(el).removeClass("selected");
                };
            }, this));
        },

        create_flavors: function() {
            var flavors = this.get_active_flavors();
            var valid_flavors = this.get_valid_flavors();
            this.__added_flavors = {'cpu':[], 'ram':[], 'disk':[], 'disk_template':[] };

            _.each(flavors, _.bind(function(flv){
                this.add_flavor(flv);
            }, this));
            
            this.sort_flavors(this.disks);
            this.sort_flavors(this.cpus);
            this.sort_flavors(this.mems);
            this.sort_flavors(this.disk_templates);

            var self = this;
            this.$(".flavor-options li.option").click(function(){
                var el = $(this);

                if (el.hasClass("disabled")) { return }

                el.parent().find(".option").removeClass("selected");
                el.addClass("selected");

                if (el.hasClass("mem")) { self.last_choice = ["ram", $(this).data("value")] }
                if (el.hasClass("cpu")) { self.last_choice = ["cpu", $(this).data("value")] }
                if (el.hasClass("disk")) { self.last_choice = ["disk", $(this).data("value")] }
                if (el.hasClass("disk_template")) { self.last_choice = ["disk_template", $(this).data("value")] }

                self.update_selected_from_ui();
            });

            $(".flavor-opts-list").each(function(){
              var el = $(this);
              if (el.find(".option").length > 6) {
                el.addClass("compact");
              }
            });
        },

        sort_flavors: function(els) {
            var prev = undefined;
            els.find("li").each(function(i,el){
                el = $(el);
                if (!prev) { prev = el; return true };
                if (el.data("value") < prev.data("value")) {
                    prev.before(el);
                }
                prev = el;
            })
        },
        
        ui_selected: function() {
            var args = [this.$(".option.cpu.selected").data("value"), 
                this.$(".option.mem.selected").data("value"), 
                this.$(".option.disk.selected").data("value"),
                this.$(".option.disk_template.selected").data("value"),
            this.flavors];
            
            var flv = storage.flavors.get_flavor.apply(storage.flavors, args);
            return flv;
        },

        update_selected_flavor: function() {
            var flv = this.current_flavor;
            if (!flv) { return }
            this.$(".option").removeClass("selected");

            this.$(".option.cpu.value-" + flv.get("cpu")).addClass("selected");
            this.$(".option.mem.value-" + flv.get("ram")).addClass("selected");
            this.$(".option.disk.value-" + flv.get("disk")).addClass("selected");
            this.$(".option.disk_template.value-" + flv.get("disk_template")).addClass("selected");
            
            var disk_el = this.$(".option.disk_template.value-" + flv.get("disk_template"));
            var basebgpos = 470;
                
            var append_to_bg_pos = 40 + (disk_el.index() * 91);
            var bg_pos = basebgpos - append_to_bg_pos;

            this.$(".disk-template-description").css({backgroundPosition:'-' + bg_pos + 'px top'})
            this.$(".disk-template-description p").html(flv.get_disk_template_info().description || "");
        },
        
        __added_flavors: {'cpu':[], 'ram':[], 'disk':[], 'disk_template':[]},
        add_flavor: function(flv) {
            var values = {'cpu': flv.get('cpu'), 
                          'mem': flv.get('ram'), 
                          'disk': flv.get('disk'), 
                          'disk_template': flv.get('disk_template')};

            disabled = "";
            
            if (this.__added_flavors.cpu.indexOf(values.cpu) == -1) {
                var cpu = $(('<li class="option cpu value-{0} {1}">' + 
                             '<span class="value">{0}</span>' + 
                             '<span class="metric">x</span></li>').format(
                            _.escape(values.cpu), disabled)).data('value', values.cpu);
                this.cpus.append(cpu);
                this.__added_flavors.cpu.push(values.cpu);
            }

            if (this.__added_flavors.ram.indexOf(values.mem) == -1) {
                var mem_value = parseInt(_.escape(values.mem))*1024*1024;
                var displayvalue = synnefo.util.readablizeBytes(mem_value, 
                                                               0).split(" ");
                var mem = $(('<li class="option mem value-{2}">' + 
                             '<span class="value">{0}</span>' + 
                             '<span class="metric">{1}</span></li>').format(
                          displayvalue[0], displayvalue[1], values.mem)).data(
                          'value', values.mem);
                this.mems.append(mem);
                this.__added_flavors.ram.push(values.mem);
            }

            if (this.__added_flavors.disk.indexOf(values.disk) == -1) {
                var disk = $(('<li class="option disk value-{0}">' + 
                              '<span class="value">{0}</span>' + 
                              '<span class="metric">GB</span></li>').format(
                            _.escape(values.disk))).data('value', values.disk);
                this.disks.append(disk);
                this.__added_flavors.disk.push(values.disk)
            }
            
            if (this.__added_flavors.disk_template.indexOf(values.disk_template) == -1) {
                var template_info = flv.get_disk_template_info();
                var disk_template = $(('<li title="{2}" class="option disk_template value-{0}">' + 
                                       '<span class="value name">{1}</span>' +
                                       '</li>').format(values.disk_template, 
                                            _.escape(template_info.name), 
                                            template_info.description)).data('value', 
                                                                values.disk_template);

                this.disk_templates.append(disk_template);
                //disk_template.tooltip({position:'top center', offset:[-5,0], delay:100, tipClass:'tooltip disktip'});
                this.__added_flavors.disk_template.push(values.disk_template)
            }
            
        },
        
        get_active_flavors: function() {
            return storage.flavors.active();
        },

        get_valid_flavors: function() {
            return this.flavors;
        },

        update_layout: function() {
            this.update_selected_flavor();
            this.update_disabled_flavors();
            this.validate();
            this.validate_selected_flavor();
            this.update_quota_display();
        },
        
        update_quota_display: function() {

          var quotas = synnefo.storage.quotas;
          _.each(["disk", "ram", "cpu"], function(type) {
            var active = true;
            var key = 'available';
            var available_dsp = quotas.get('cyclades.'+type).get_readable(key, active);
            var available = quotas.get('cyclades.'+type).get_available(key);
            var content = "({0} left)".format(available_dsp);
            if (available <= 0) { content = "(None left)" }
            
            if (type == "ram") { type = "mem" }
            $(".flavor-options."+type+" h4 .available").text(content);
            if (available <= 0) {
              $(".flavor-options."+type+" h4 .available").addClass("error");
            } else {
              $(".flavor-options."+type+" h4 .available").removeClass("error");
            }
          })
        },

        reset: function() {
            this.current_image = storage.images.at(0);
            this.flavors = [];
            this.flavors_data = {'cpu':[], 'mem':[], 'disk':[]};
            this.update_flavors_data();
        },

        validate: function() {
            if (!this.current_flavor) {
                this.parent.$(".form-action.next").hide();
            } else {
                this.parent.$(".form-action.next").show();
            }
        },

        get: function() {
            return {'flavor': this.current_flavor}
        }
    });
    

    views.CreateColumnSelectOptionView = bb.View.extend({
        tagName: 'li',
        el: undefined,
        model: undefined,
        id_prefix: 'model-',
        tpl: '<input type="checkbox" class="check"/><span class="title"></span>',
        className: 'list-item-option clearfix',
        events: {
          'click': 'handle_click'
        },

        initialize: function(options) {
          _.bindAll(this);
          this.model.bind("change", this.render);
          this.model.bind("remove", this.remove);
          this.selected = false;
          if (options.get_model_title) {
            this.get_model_title = _.bind(options.get_model_title, this);
          }
          this.model_title_attr = options.model_title_attr;
          $(this.el).append($(this.tpl));
        },
        
        id: function() {
          return this.id_prefix + this.model && this.model.id || '';
        },
        
        handle_click: function() {
          this.selected = !this.selected;
          this.render();
        },

        remove: function() {
          this.model.unbind("change", this.render);
          this.model.unbind("remove", this.remove);
        },
        
        get_model_title: function() {
          return this.model.get(this.model_title_attr || 'id');
        },

        render: function() {
          $(this.el).find(".title").text(this.get_model_title());
          $(this.el).toggleClass('selected', this.selected);
          if (this.selected) {
            $(this.el).find("input").attr("checked", true);
          } else {
            $(this.el).find("input").attr("checked", false);
          }
        }
    });
    
    views.CreateColumnIPOptionView = views.CreateColumnSelectOptionView.extend({
      get_model_title: function() {
        return this.model.get('ip');
      }
    });

    views.CreateColumnPrivateNetworkOptionView = views.CreateColumnSelectOptionView.extend({
      get_model_title: function() {
        return this.model.get('name');
      }
    });

    views.CreateColumnSelectListView = bb.View.extend({
        collection: undefined,
        header: undefined,
        tagName: 'div',
        extra_class: '',
        el: undefined,
        title_tpl: undefined,
        title: 'List view',
        description: 'List view description.',
        empty_msg: 'No entries.',
        item_cls: views.CreateColumnSelectOptionView,
        className: 'list-cont create-column-select personalize-cont',

        initialize: function(options) {
          _.bindAll(this);
          if (options.extra_class) {
            $(this.el).addClass(options.extra_class);
          }
          this.update_collection = options.update_collection;
          this.title = options.title || this.title;
          this.titple_tpl = options.title_tpl || this.title_tpl;
          this.description = options.description || this.description;
          this.empty_msg = options.empty_msg || this.empty_msg;
          this.item_cls = options.item_cls || this.item_cls;
          this.select_first_as_default = options.select_first_as_default;
          this.filter_items = options.filter_items;
          this.post_render_entries = options.post_render_entries || function() {};
          this.init_events = options.init_events || function() {};

          this.init_events = _.bind(this.init_events, this);
          this.post_render_entries = _.bind(this.post_render_entries, this);

          this._ul = $('<ul class="confirm-params">');
          this._title = $("<h4>");
          this._description = $("<p class='desc'>");
          this._empty = $("<p class='empty hidden desc'>");
          this._empty.html(this.empty_msg);
        
          this.item_views = [];

          $(this.el).append(this._title);
          $(this.el).append(this._description);
          $(this.el).append(this._empty);
          $(this.el).append(this._ul);

          this['$el'] = $(this.el);

          if (!this.title_tpl) { this.title_tpl = this.title };

          this.collection.bind("change", this.render_entries);
          this.collection.bind("reset", this.render_entries);
          this.collection.bind("add", this.render_entries);
          this.collection.bind("remove", this.remove_entry);
          
          this.fetcher = undefined;
          if (this.update_collection) {
            this.fetcher_params = [snf.config.update_interval, 
                                  snf.config.update_interval_increase || 500,
                                  snf.config.fast_interval || snf.config.update_interval/2, 
                                  snf.config.update_interval_increase_after_calls || 4,
                                  snf.config.update_interval_max || 20000,
                                  true, 
                                  {is_recurrent: true, update: true}];
              this.fetcher = this.collection.get_fetcher.apply(this.collection, 
                                                _.clone(this.fetcher_params));
              this.fetcher.start();
          }
          this.render();
          this.init_events();
        },
        
        render: function() {
          this._title.html(this.title_tpl);
          this._description.html(this.description);
          this.render_entries();
        },
        
        remove_entry: function(model) {
          if (!this.item_views[model.id]) { return }
          this.item_views[model.id].remove();
          delete this.item_views[model.pk]
        },
        
        get_selected: function() {
          return _.map(_.filter(this.item_views, function(v) { 
            return v.selected
          }), function(v) {
            return v.model
          });
        },
        
        check_empty: function() {
          if (this.item_views.length == 0) {
            this._empty.show();
          } else {
            this._empty.hide();
          }
        },

        render_entries: function() {
          var entries;
          if (this.filter_items) {
            entries = this.collection.filter(this.filter_items);
          } else {
            entries = this.collection.models;
          }
          
          var selected = this.get_selected();
          
          _.each(entries, _.bind(function(model) {
            if (this.item_views[model.id]) {
              this.item_views[model.id].render();
            } else {
              var view = new this.item_cls({model:model});
              if (!selected.length && this.select_first_as_default) { 
                view.selected = true; selected = [1] 
              }
              view.render();
              this.item_views[model.id] = view;
              this._ul.append($(view.el));
            }
          }, this));
          this.check_empty();
          this.post_render_entries();
        },

        remove: function() {
          _.each(this.item_views, function(v){
            v.remove();
          });
          if (this.update_collection) { this.fetcher.stop() }
          this.unbind();
          this.collection.unbind("change", this.render_entries);
          this.collection.unbind("reset", this.render_entries);
          this.collection.unbind("add", this.render_entries);
          this.collection.unbind("remove", this.remove_entry);
          views.CreateColumnSelectListView.__super__.remove.apply(this, arguments);
        }
    });

    views.CreateNetworkingView = views.CreateVMStepView.extend({
        step: 3,
        initialize: function() {
            views.CreateNetworkingView.__super__.initialize.apply(this, arguments);
            this.init_handlers();
            this.ssh_list = this.$(".ssh ul");
            this.selected_keys = [];

            var self = this;
            this.$(".create-ssh-key").click(function() {
                var confirm_close = true;
                if (confirm_close) {
                    snf.ui.main.public_keys_view.show(self.parent);
                } else {
                }
            });

        },
        
        init_subviews: function() {
            var create_view = this.parent;
            if (!this.ips_view) {
              this.ips_view = new views.CreateColumnSelectListView({
                collection: synnefo.storage.floating_ips,
                extra_class: 'public-ips',
                update_collection: true,
                title: 'IP addresses <span class="create-ip-address"><a href="#">manage ip\'s</a></span>',
                description: 'Select IP addresses to be assigned to the created machine.',
                item_cls: views.CreateColumnIPOptionView,
                empty_msg: 'No IP addresses available. <span><a href="">Create a new IP address.</a></span>',
                select_first_as_default: true,
                filter_items: function(model) { 
                  return !(model.get('port_id'))
                },
                init_events: function() {
                  var msg = this.$(".empty span a");
                  this.$(".empty a").bind('click', function(e) {
                      e.preventDefault();
                      msg.text("Creating...");
                      synnefo.storage.floating_ips.create({
                        address:undefined, pool: undefined
                      }, {
                        error: function() {
                          alert("Cannot create new ip address");
                        },
                        complete: function() {
                          msg.text("Create a new IP address.");
                          msg.show();
                        },
                        skip_api_error: true,
                      })
                  });
                }
              });
              $(this.ips_view.el).appendTo(this.$(".personalize-conts"));
            }
            if (!this.networks_view) {
              this.networks_view = new views.CreateColumnSelectListView({
                collection: synnefo.storage.networks,
                extra_class: 'private-networks',
                title: 'Private networks',
                description: 'Select private networks to connect the created machine to. You can manage your private networks from the networks tab.',
                item_cls: views.CreateColumnPrivateNetworkOptionView,
                filter_items: function(model) { return !model.is_public() }
              });
              $(this.networks_view.el).appendTo(this.$(".personalize-conts"));
            }
        },

        init_handlers: function() {
        },

        show: function() {
            views.CreateNetworkingView.__super__.show.apply(this, arguments);
            this.init_subviews();
            this.update_layout();
        },
        
        update_layout: function() {
        },

        reset: function() {
            this.selected_keys = [];
            this.update_layout();
        },
        
        get_selected_networks: function() {
          if (!this.networks_view) { return [] }
          return this.networks_view.get_selected();
        },
        
        get_selected_addresses: function() {
          if (!this.networks_view) { return [] }
          return this.ips_view.get_selected();
        },

        get: function() {
            return {
              'addresses': this.get_selected_addresses(),
              'networks': this.get_selected_networks()
            }
        },

        remove: function() {
          if (this.ips_view) {
            this.ips_view.remove();
            delete this.ips_view;
          }
          
          if (this.networks_view) {
            this.networks_view.remove();
            delete this.networks_view;
          }
        }
    });

    views.CreatePersonalizeView = views.CreateVMStepView.extend({
        step: 4,
        initialize: function() {
            views.CreateSubmitView.__super__.initialize.apply(this, arguments);
            this.roles = this.$("li.predefined-meta.role .values");
            this.name = this.$("input.rename-field");
            this.name_changed = false;
            this.init_suggested_roles();
            this.init_handlers();
            this.ssh_list = this.$(".ssh ul");
            this.selected_keys = [];

            var self = this;
            this.$(".create-ssh-key").click(function() {
                var confirm_close = true;
                if (confirm_close) {
                    snf.ui.main.public_keys_view.show(self.parent);
                } else {
                }
            });
        },

        init_suggested_roles: function() {
            var cont = this.roles;
            cont.empty();
            
            // TODO: get suggested from snf.api.conf
            _.each(window.SUGGESTED_ROLES, function(r){
                var el = $('<span class="val">{0}</span>'.format(_.escape(r)));
                el.data("value", r);
                cont.append(el);
                el.click(function() {
                    $(this).parent().find(".val").removeClass("selected");
                    $(this).toggleClass("selected");
                })
            });
            
            var self = this;
            $(".ssh li.ssh-key-option").live("click", function(e) {
                var key = $(this).data("model");
                self.select_key(key);
            });
        },

        select_key: function(key) {
            var exists = this.selected_keys.indexOf(key.id);
            if (exists > -1) {
                this.selected_keys.splice(exists, 1);
            } else {
                this.selected_keys.push(key.id);
            }
            this.update_ui_keys_selections(this.selected_keys);
        },

        update_ui_keys_selections: function(keys) {
            var self = this;
            self.$(".ssh-key-option").removeClass("selected");
            self.$(".ssh-key-option .check").attr("checked", false);
            _.each(keys, function(kid) {
                $("#ssh-key-option-" + kid).addClass("selected");
                $("#ssh-key-option-" + kid).find(".check").attr("checked", true);
            });
        },

        update_ssh_keys: function() {
            this.ssh_list.empty();
            var keys = snf.storage.keys.models;
            if (keys.length == 0) { 
                this.$(".ssh .empty").show();
            } else {
                this.$(".ssh .empty").hide();
            }
            _.each(keys, _.bind(function(key){
                var el = $('<li id="ssh-key-option-{1}" class="ssh-key-option">{0}</li>'.format(_.escape(key.get("name")), key.id));
                var check = $('<input class="check" type="checkbox"></input>')
                el.append(check);
                el.data("model", key);
                this.ssh_list.append(el);
            }, this));
        },

        init_handlers: function() {
            this.name.bind("keypress", _.bind(function(e) {
                this.name_changed = true;
                if (e.keyCode == 13) { this.parent.set_step(5); this.parent.update_layout() };    
            }, this));

            this.name.bind("click", _.bind(function() {
                if (!this.name_changed) {
                    this.name.val("");
                }
            }, this))
        },

        show: function() {
            views.CreatePersonalizeView.__super__.show.apply(this, arguments);
            this.update_layout();
        },
        
        update_layout: function() {
            var params = this.parent.get_params();

            if (!params.image || !params.flavor) { return }

            if (!params.image) { return }
            var vm_name_tpl = snf.config.vm_name_template || "My {0} server";
            var vm_name = vm_name_tpl.format(_.escape(params.image.get("name")));
            var orig_name = vm_name;
            
            var existing = true;
            var j = 0;

            while (existing && !this.name_changed) {
                var existing = storage.vms.select(function(vm){
                  return vm.get("name") == vm_name
                }).length;
                if (existing) {
                    j++;
                    vm_name = orig_name + " " + j;
                }
            }

            if (!_(this.name.val()).trim() || !this.name_changed) {
                this.name.val(vm_name);
            }

            if (!this.name_changed && this.parent.visible()) {
                if (!$.browser.msie && !$.browser.opera) {
                    this.$("#create-vm-name").select();
                } else {
                    window.setTimeout(_.bind(function(){
                        this.$("#create-vm-name").select();
                    }, this), 400)
                }
            }
            
            var img = snf.ui.helpers.os_icon_path(params.image.get("OS"))
            this.name.css({backgroundImage:"url({0})".format(img)})
            
            if (!params.image.supports('ssh')) {
                this.disable_ssh_keys();
            } else {
                this.enable_ssh_keys();
                this.update_ssh_keys();
            }

            this.update_ui_keys_selections(this.selected_keys);
        },

        disable_ssh_keys: function() {
            this.$(".disabled.desc").show();
            this.$(".empty.desc").hide();
            this.$(".ssh .confirm-params").hide();
            this.selected_keys = [];
        },

        enable_ssh_keys: function() {
            this.$(".ssh .confirm-params").show();
            this.$(".disabled.desc").hide();
        },

        reset: function() {
            this.roles.find(".val").removeClass("selected");
            this.name_changed = false;
            this.selected_keys = [];
            this.update_layout();
        },

        get_meta: function() {
            if (this.roles.find(".selected").length == 0) {
                return false;
            }

            var role = $(this.roles.find(".selected").get(0)).data("value");
            return {'Role': role }
        },

        get: function() {
            var val = {'name': this.name.val() };
            if (this.get_meta()) {
                val.metadata = this.get_meta();
            }

            val.keys = _.map(this.selected_keys, function(k){ return snf.storage.keys.get(k)});
            
            return val;
        }
    });

    views.CreateSubmitView = views.CreateVMStepView.extend({
        step: 5,
        initialize: function() {
            views.CreateSubmitView.__super__.initialize.apply(this, arguments);
            this.roles = this.$("li.predefined-meta.role .values");
            this.confirm = this.$(".confirm-params ul");
            this.name = this.$("h3.vm-name");
            this.keys = this.$(".confirm-params.ssh");
            this.meta = this.$(".confirm-params.meta");
            this.ip_addresses = this.$(".confirm-params.ip-addresses");
            this.private_networks = this.$(".confirm-params.private-networks");
            this.init_handlers();
        },

        init_handlers: function() {
        },

        show: function() {
            views.CreateSubmitView.__super__.show.apply(this, arguments);
            this.update_layout();
        },
        
        update_network_details: function() {
            var data = this.parent.get_params();
            var ips = data.addresses;
            var networks = data.networks;

            this.ip_addresses.empty();
            if (!ips|| ips.length == 0) {
                this.ip_addresses.append(this.make("li", {'class':'empty'}, 
                                           'No ip addresses selected'))
            }
            _.each(ips, _.bind(function(ip) {
                var el = this.make("li", {'class':'selected-ip-address'}, 
                                  ip.get('ip'));
                this.ip_addresses.append(el);
            }, this))

            this.private_networks.empty();
            if (!networks || networks.length == 0) {
                this.private_networks.append(this.make("li", {'class':'empty'}, 
                                             'No private networks selected'))
            }
            _.each(networks, _.bind(function(network) {
                var el = this.make("li", {'class':'selected-private-network'}, 
                                  network.get('name'));
                this.private_networks.append(el);
            }, this))

        },

        update_flavor_details: function() {
            var flavor = this.parent.get_params().flavor;

            function set_detail(sel, key) {
                var val = key;
                if (key == undefined) { val = flavor.get(sel) };
                this.$(".confirm-cont.flavor .flavor-" + sel + " .value").text(val)
            }
            
            set_detail("cpu", flavor.get("cpu") + "x");
            set_detail("ram", flavor.get("ram") + " MB");
            set_detail("disk", util.readablizeBytes(flavor.get("disk") * 1024 * 1024 * 1024));
            set_detail("disktype", flavor.get_disk_template_info().name);
        },

        update_image_details: function() {
            var image = this.parent.get_params().image;

            function set_detail(sel, key) {
                var val = key;
                if (key == undefined) { val = image.get(sel) };
                this.$(".confirm-cont.image .image-" + sel + " .value").text(val)
            }
            
            set_detail("description", image.get_description());
            set_detail("name");
            set_detail("os", _(image.get_os()).capitalize());
            set_detail("gui", image.get_gui());
            set_detail("size", _.escape(image.get_readable_size()));
            set_detail("kernel");
        },

        update_selected_keys: function(keys) {
            this.keys.empty();
            if (!keys || keys.length == 0) {
                this.keys.append(this.make("li", {'class':'empty'}, 'No keys selected'))
            }
            _.each(keys, _.bind(function(key) {
                var el = this.make("li", {'class':'selected-ssh-key'}, key.get('name'));
                this.keys.append(el);
            }, this))
        },

        update_selected_meta: function(meta) {
            this.meta.empty();
            if (!meta || meta.length == 0) {
                this.meta.append(this.make("li", {'class':'empty'}, 'No tags selected'))
            }
            _.each(meta, _.bind(function(value, key) {
                var el = this.make("li", {'class':'confirm-value'});
                var name = this.make("span", {'class':'ckey'}, key);
                var value = this.make("span", {'class':'cval'}, value);

                $(el).append(name)
                $(el).append(value);
                this.meta.append(el);
            }, this));
        },

        update_layout: function() {
            var params = this.parent.get_params();
            if (!params.image || !params.flavor) { return }

            if (!params.image) { return }

            this.name.text(params.name);

            this.confirm.find("li.image .value").text(params.flavor.get("image"));
            this.confirm.find("li.cpu .value").text(params.flavor.get("cpu") + "x");
            this.confirm.find("li.mem .value").text(params.flavor.get("ram"));
            this.confirm.find("li.disk .value").text(params.flavor.get("disk"));

            var img = snf.ui.helpers.os_icon_path(params.image.get("OS"))
            this.name.css({backgroundImage:"url({0})".format(img)})

            this.update_image_details();
            this.update_flavor_details();
            this.update_network_details();

            if (!params.image.supports('ssh')) {
                this.keys.hide();
                this.keys.prev().hide();
            } else {
                this.keys.show();
                this.keys.prev().show();
                this.update_selected_keys(params.keys);
            }
            
            this.update_selected_meta(params.metadata);
        },

        reset: function() {
            this.update_layout();
        },

        get_meta: function() {
        },

        get: function() {
            return {};
        }
    });

    views.CreateVMView = views.Overlay.extend({
        
        view_id: "create_vm_view",
        content_selector: "#createvm-overlay-content",
        css_class: 'overlay-createvm overlay-info',
        overlay_id: "metadata-overlay",

        subtitle: false,
        title: "Create new machine",

        initialize: function(options) {
            views.CreateVMView.__super__.initialize.apply(this);
            this.current_step = 1;

            this.password_view = new views.VMCreationPasswordView();

            this.steps = [];
            this.steps[1] = new views.CreateImageSelectView(this);
            this.steps[1].bind("change", _.bind(function(data) {this.trigger("image:change", data)}, this));

            this.steps[2] = new views.CreateFlavorSelectView(this);
            this.steps[3] = new views.CreateNetworkingView(this);
            this.steps[4] = new views.CreatePersonalizeView(this);
            this.steps[5] = new views.CreateSubmitView(this);

            this.cancel_btn = this.$(".create-controls .cancel");
            this.next_btn = this.$(".create-controls .next");
            this.prev_btn = this.$(".create-controls .prev");
            this.submit_btn = this.$(".create-controls .submit");

            this.history = this.$(".steps-history");
            this.history_steps = this.$(".steps-history .steps-history-step");
            
            this.init_handlers();
        },

        init_handlers: function() {
            var self = this;
            this.next_btn.click(_.bind(function(){
                this.set_step(this.current_step + 1);
                this.update_layout();
            }, this))
            this.prev_btn.click(_.bind(function(){
                this.set_step(this.current_step - 1);
                this.update_layout();
            }, this))
            this.cancel_btn.click(_.bind(function(){
                this.close_all();
            }, this))
            this.submit_btn.click(_.bind(function(){
                this.submit();
            }, this))
            
            this.history.find(".completed").live("click", function() {
                var step = parseInt($(this).attr("id").replace("vm-create-step-history-", ""));
                self.set_step(step);
                self.update_layout();
            })
        },

        set_step: function(st) {
        },
        
        validate: function(data) {
            if (_(data.name).trim() == "") {
                this.$(".form-field").addClass("error");
                return false;
            } else {
                return true;
            }
        },

        submit: function() {
            if (this.submiting) { return };
            var data = this.get_params();
            var meta = {};
            var extra = {};
            var personality = [];

            if (this.validate(data)) {
                this.submit_btn.addClass("in-progress");
                this.submiting = true;
                if (data.metadata) { meta = data.metadata; }
                if (data.keys && data.keys.length > 0) {
                    personality.push(
                      data.image.personality_data_for_keys(data.keys))
                }

                if (personality.length) {
                    extra['personality'] = _.flatten(personality);
                }
                
                extra['networks'] = _.map(data.networks, function(n) { return n.get('id') });
                extra['floating_ips'] = _.map(data.addresses, function(ip) { return ip.get('ip') });
                storage.vms.create(data.name, data.image, data.flavor, 
                                   meta, extra, _.bind(function(data){
                    _.each(data.addresses, function(ip) {
                      ip.set({'status': 'connecting'});
                    });
                    this.close_all();
                    this.password_view.show(data.server.adminPass, 
                                            data.server.id);
                    this.submiting = false;
                }, this));
            }
        },

        close_all: function() {
          this.hide();
        },

        onClose: function() {
          this.steps[3].remove();
        },

        reset: function() {
          this.current_step = 1;

          this.steps[1].reset();
          this.steps[2].reset();
          this.steps[3].reset();
          this.steps[4].reset();

          //this.steps[1].show();
          //this.steps[2].show();
          //this.steps[3].show();
          //this.steps[4].show();

          this.submit_btn.removeClass("in-progress");
        },

        onShow: function() {
        },

        update_layout: function() {
            this.show_step(this.current_step);
            this.current_view.update_layout();
        },

        beforeOpen: function() {
            if (!this.skip_reset_on_next_open) {
                this.submiting = false;
                this.reset();
                this.current_step = 1;
                this.$(".steps-container").css({"margin-left":0 + "px"});
                this.show_step(1);
            }
            
            this.skip_reset_on_next_open = false;
            this.update_layout();
        },
        
        set_step: function(step) {
            if (step <= 1) {
                step = 1
            }
            if (step > this.steps.length - 1) {
                step = this.steps.length - 1;
            }
            this.current_step = step;
        },

        show_step: function(step) {
            // FIXME: this shouldn't be here
            // but since we are not calling step.hide this should work
            this.steps[1].image_details.hide();

            this.current_view = this.steps[step];
            this.update_controls();

            this.steps[step].show();
            var width = this.el.find('.container').width();
            var left = (step -1) * width * -1;
            this.$(".steps-container").animate({"margin-left": left + "px"}, 300);

            this.update_steps_history();
        },

        update_steps_history: function() {
            var self = this;
            function get_step(s) {
                return self.history.find(".step" + s + "h");
            }
            
            var current_step = parseInt(this.current_view.step);
            _.each(this.steps, function(stepv) {
                var step = parseInt(stepv.step);
                get_step(step).removeClass("completed").removeClass("current");
                if (step == current_step) {
                    get_step(step).removeClass("completed").addClass("current");
                }
                if (step < current_step) {
                    get_step(step).removeClass("current").addClass("completed");
                }
            });
        },

        update_controls: function() {
            var step = this.current_step;
            if (step == 1) {
                this.prev_btn.hide();
                this.cancel_btn.show();
            } else {
                this.prev_btn.show();
                this.cancel_btn.hide();
            }
            
            if (step == this.steps.length - 1) {
                this.next_btn.hide();
                this.submit_btn.show();
            } else {
                this.next_btn.show();
                this.submit_btn.hide();
            }
        },

        get_params: function() {
            return _.extend({}, this.steps[1].get(), this.steps[2].get(), this.steps[3].get(), this.steps[4].get());
        }
    });
    
})(this);

