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
            this.copy = this.$(".clip-copy");

            this.$(".show-machine").click(_.bind(function(){
                this.hide();
                snf.ui.main.show_vm_details(storage.vms.get(this.vm_id));
            }, this));
            
        },
        
        show_password: function() {
            this.password.text(this.pass);
        },

        onClose: function() {
            this.password.text("");
        },
        
        beforeOpen: function() {
            if (this.clipboard) { return };
            this.clipboard = new util.ClipHelper(this.copy);
            this.clipboard.el.tooltip();
        },
        
        onOpen: function() {
            try {
                this.clipboard.setText(this.pass);
                this.copy.show();
            } catch (err) {
                this.copy.hide();
            }
        },

        show: function(pass, vm_id) {
            this.pass = pass;
            this.vm_id = vm_id;

            views.VMCreationPasswordView.__super__.show.apply(this, arguments);
            this.show_password();
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

            this.types = this.$(".type-filter li");
            this.categories_list = this.$(".category-filters");

            // params initialization
            this.type_selections = ["system", "custom"]
            this.selected_type = "system";
            this.selected_categories = [];
            this.images = [];

            // update
            this.update_images();

            // handlers initialization
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
            })
        },

        update_images: function() {
            this.images = storage.images.active();
            this.images_ids = _.map(this.images, function(img){return img.id});
            if (this.selected_type == "custom") { this.images = []; this.images_ids = []; }

            return this.images;
        },

        update_layout: function() {
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
        
        select_type: function(type) {
            this.selected_type = type;
            this.types.removeClass("selected");
            this.types.filter("#type-select-" + this.selected_type).addClass("selected");

            this.reset_categories();
            this.update_images();
            this.reset_images();
            this.select_image();
        },

        select_image: function(image) {
            if (!image && this.images_ids.length) {
                if (this.selected_image && this.images_ids.indexOf(this.selected_image.id) > -1) {
                    image = this.selected_image;
                } else {
                    image = storage.images.get(this.images_ids[0]);
                }
            }

            if (!this.images_ids.length) { image = this.selected_image || undefined };
            
            this.selected_image = image;
            this.trigger("change", image);
            
            if (image) {
                this.image_details.show();
                this.images_list.find(".image-details").removeClass("selected");
                this.images_list.find(".image-details#create-vm-image-" + this.selected_image.id).addClass("selected");
                
                this.image_details_desc.text(image.get("description"));
                
                var img = snf.ui.helpers.os_icon_tag(image.get("OS"))
                this.image_details_title.html(img + image.get("name"));
                this.image_details_os.text(_(image.get("OS")).capitalize());
                this.image_details_kernel.text(image.get("kernel"));

                var size = util.readablizeBytes(parseInt(image.get("size")) * 1024 * 1024);
                this.image_details_size.text(size);
                this.image_details_gui.text(image.get("GUI"));

            } else {
                this.image_details.hide();
            }
        },

        reset_images: function() {
            this.images_list.find("li").remove();
            _.each(this.images, _.bind(function(img){
                this.add_image(img);
            }, this))
            
            if (this.images.length) {
                this.images_list.parent().find(".empty").hide();
            } else {
                this.images_list.parent().find(".empty").show();
            }

            this.select_image();
            
            var self = this;
            this.images_list.find(".image-details").click(function(){
                self.select_image($(this).data("image"));
            });
            
        },

        show: function() {
            views.CreateImageSelectView.__super__.show.apply(this, arguments);
        },

        add_image: function(img) {
            var image = $(('<li id="create-vm-image-{1}"' +
                           'class="image-details clearfix">{2}{0}' +
                           '<p>{4}</p><span class="size">{3}' +
                           '</span></li>').format(img.get("name"), 
                                                  img.id, 
                                                  snf.ui.helpers.os_icon_tag(img.get("OS")),
                                                  util.readablizeBytes(parseInt(img.get("size"))* 1024 * 1024),
                                                  util.truncate(img.get("description"),35)));
            image.data("image", img);
            image.data("image_id", img.id);
            this.images_list.append(image);
        },

        reset: function() {
            this.selected_image = undefined;
            this.reset_images();
        },

        get: function() {
            return {'image': this.selected_image};
        }
    });

    views.CreateFlavorSelectView = views.CreateVMStepView.extend({
        step: 2,
        initialize: function() {
            views.CreateFlavorSelectView.__super__.initialize.apply(this, arguments);
            this.parent.bind("image:change", _.bind(this.handle_image_change, this));

            this.cpus = this.$(".flavors-cpu-list");
            this.disks = this.$(".flavors-disk-list");
            this.mems = this.$(".flavors-mem-list");

            this.predefined_flavors = SUGGESTED_FLAVORS;
            this.predefined_flavors_keys = _.keys(SUGGESTED_FLAVORS);
            this.predefined_flavors_keys = _.sortBy(this.predefined_flavors_keys, _.bind(function(k){
                var flv = this.predefined_flavors[k];
                return flv.ram * flv.cpu * flv.disk;
            }, this));

            this.predefined = this.$(".predefined-list");
            this.update_predefined_flavors();
        },

        handle_image_change: function(data) {
            this.current_image = data;
            this.update_valid_predefined();
            this.update_flavors_data();
            this.reset_flavors();
            this.update_layout();
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
                           '{1}</li>').format(key, _(key).capitalize()));

                this.predefined.append(el);
                el.data({flavor: storage.flavors.get_flavor(val.cpu, val.ram, val.disk, this.flavors)})
                el.click(_.bind(function() {
                    this.handle_predefined_click(el);
                }, this))
            }, this));
            this.update_valid_predefined();
        },

        handle_predefined_click: function(el) {
            if (el.hasClass("disabled")) { return };
            this.set_current(el.data("flavor"))
        },

        update_valid_predefined: function() {
            this.update_unavailable_values();
            var self = this;
            this.valid_predefined = _.select(_.map(this.predefined_flavors, function(flv, key){
                var existing = storage.flavors.get_flavor(flv.cpu, flv.ram, flv.disk, self.flavors);
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
                var exists = storage.flavors.get_flavor(flv.cpu, flv.ram, flv.disk, self.flavors);

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
                    var exists = storage.flavors.get_flavor(flv.cpu, flv.ram, flv.disk, self.flavors);
                    if (exists && !set) {
                        self.set_current(exists);
                        set = true;
                    }
                })
            }

            this.update_unavailable_values();
        },

        update_unavailable_values: function() {
            if (!this.current_image) { this.unavailable_values = {disk:[], ram:[], cpu:[]}; return };
            this.unavailable_values = storage.flavors.unavailable_values_for_image(this.current_image);
        },
        
        flavor_is_valid: function(flv) {
            if (!flv) { return false };
            var existing = storage.flavors.get_flavor(flv.get("cpu"), flv.get("ram"), flv.get("disk"), this.flavors);
            if (!existing) { return false };
            if (this.unavailable_values && this.unavailable_values.disk.indexOf(flv.get("disk") > -1)) {
                return false
            }
            return true;
        },
            
        set_current: function(flv) {
            //console.log(flv);
            //if (!this.flavor_is_valid(flv)) { flv = undefined };
            
            this.current_flavor = flv;
            this.trigger("change");
            this.update_selected_flavor();
            this.update_selected_predefined();
        },
        
        select_default_flavor: function() {
               
        },

        update_selected_from_ui: function() {
            this.set_current(this.ui_selected());
        },
        
        update_disabled_flavors: function() {
            this.$(".flavor-options.disk li").removeClass("disabled");
            if (!this.unavailable_values) { return }

            this.$(".flavor-options.disk li").each(_.bind(function(i, el){
                var el_value = $(el).data("value") * 1024;
                if (this.unavailable_values.disk.indexOf(el_value) > -1) {
                    $(el).addClass("disabled");
                };
            }, this));
        },

        create_flavors: function() {
            var flavors = this.get_active_flavors();
            var valid_flavors = this.get_valid_flavors();

            _.each(flavors, _.bind(function(flv){
                this.add_flavor(flv);
            }, this));
            
            var self = this;
            this.$(".flavor-options li.option").click(function(){
                var el = $(this);

                if (el.hasClass("disabled")) { return }

                el.parent().find(".option").removeClass("selected");
                el.addClass("selected");
                
                if (el.hasClass("mem")) { this.last_choice = "mem" }
                if (el.hasClass("cpu")) { this.last_choice = "cpu" }
                if (el.hasClass("disk")) { this.last_choice = "disk" }

                self.update_selected_from_ui();
            })
        },
        
        ui_selected: function() {
            var args = [this.$(".option.cpu.selected").data("value"), 
                this.$(".option.mem.selected").data("value"), 
                this.$(".option.disk.selected").data("value"),
            this.flavors];

            var flv = storage.flavors.get_flavor.apply(storage.flavors, args);
            return flv;
        },

        update_selected_flavor: function() {
            var flv = this.current_flavor;
            this.$(".option").removeClass("selected");

            this.$(".option.cpu.value-" + flv.get("cpu")).addClass("selected");
            this.$(".option.mem.value-" + flv.get("ram")).addClass("selected");
            this.$(".option.disk.value-" + flv.get("disk")).addClass("selected");
        },

        add_flavor: function(flv) {
            var values = {'cpu': flv.get('cpu'), 'mem': flv.get('ram'), 'disk': flv.get('disk')};

            disabled = "";

            if (this.$('li.option.cpu.value-{0}'.format(values.cpu)).length == 0) {
                var cpu = $(('<li class="option cpu value-{0} {1}">' + 
                             '<span class="value">{0}</span>' + 
                             '<span class="metric">x</span></li>').format(values.cpu, disabled)).data('value', values.cpu);

                this.cpus.append(cpu);
            }
            if (this.$('li.option.mem.value-{0}'.format(values.mem)).length == 0) {
                var mem = $(('<li class="option mem value-{0}">' + 
                             '<span class="value">{0}</span>' + 
                             '<span class="metric">MB</span></li>').format(values.mem)).data('value', values.mem);

                this.mems.append(mem);
            }
            if (this.$('li.option.disk.value-{0}'.format(values.disk)).length == 0) {
                var disk = $(('<li class="option disk value-{0}">' + 
                              '<span class="value">{0}</span>' + 
                              '<span class="metric">GB</span></li>').format(values.disk)).data('value', values.disk);

                this.disks.append(disk);
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
        },

        reset: function() {
            this.current_image = storage.images.at(0);
            this.flavors = [];
            this.flavors_data = {'cpu':[], 'mem':[], 'disk':[]};
            this.update_flavors_data();
            this.reset_flavors();
        },

        get: function() {
            return {'flavor': this.current_flavor}
        }

    });

    views.CreateSubmitView = views.CreateVMStepView.extend({
        step: 3,
        initialize: function() {
            views.CreateSubmitView.__super__.initialize.apply(this, arguments);
            this.roles = this.$("li.predefined-meta.role .values");
            this.confirm = this.$(".confirm-params ul");
            this.name = this.$("input.rename-field");
            this.name_changed = false;
            this.init_suggested_roles();
            this.init_handlers();
        },

        init_suggested_roles: function() {
            var cont = this.roles;
            cont.empty();
            
            // TODO: get suggested from snf.api.conf
            _.each(window.SUGGESTED_ROLES, function(r){
                var el = $('<span class="val">{0}</span>'.format(r));
                el.data("value", r);
                cont.append(el);
                el.click(function() {
                    $(this).parent().find(".val").removeClass("selected");
                    $(this).toggleClass("selected");
                })
            })
        },

        init_handlers: function() {
            this.name.bind("keypress", _.bind(function(e) {
                this.name_changed = true;
                if (e.keyCode == 13) { this.parent.submit() };    
            }, this));

            this.name.bind("click", _.bind(function() {
                if (!this.name_changed) {
                    this.name.val("");
                }
            }, this))
        },

        show: function() {
            views.CreateSubmitView.__super__.show.apply(this, arguments);
            this.update_layout();
        },
        
        update_flavor_details: function() {
            var flavor = this.parent.get_params().flavor;

            function set_detail(sel, key) {
                var val = key;
                if (key == undefined) { val = flavor.get(sel) };
                this.$(".confirm-cont.flavor .flavor-" + sel + " .value").text(val)
            }
            
            set_detail("cpu");
            set_detail("ram", flavor.get("ram") + " MB");
            set_detail("disk", util.readablizeBytes(flavor.get("disk") * 1024 * 1024 * 1024));
        },

        update_image_details: function() {
            var image = this.parent.get_params().image;

            function set_detail(sel, key) {
                var val = key;
                if (key == undefined) { val = image.get(sel) };
                this.$(".confirm-cont.image .image-" + sel + " .value").text(val)
            }
            
            set_detail("description");
            set_detail("name");
            set_detail("os", image.get("OS"));
            set_detail("gui", image.get("GUI"));
            set_detail("size", util.readablizeBytes(image.get_size() * 1024 * 1024));
            set_detail("kernel");
        },

        update_layout: function() {
            var params = this.parent.get_params();

            if (!params.image) { return }
            var vm_name = "My {0} server".format(params.image.get("name"));
            var orig_name = vm_name;
            
            var existing = true;
            var j = 0;

            while (existing && !this.name_changed) {
                var existing = storage.vms.select(function(vm){return vm.get("name") == vm_name}).length
                if (existing) {
                    j++;
                    vm_name = orig_name + " " + j;
                }
            }
            if (!_(this.name.val()).trim() || !this.name_changed) {
                this.name.val(vm_name);
            }

            this.confirm.find("li.image .value").text(params.flavor.get("image"));
            this.confirm.find("li.cpu .value").text(params.flavor.get("cpu") + "x");
            this.confirm.find("li.mem .value").text(params.flavor.get("ram"));
            this.confirm.find("li.disk .value").text(params.flavor.get("disk"));

            if (!this.name_changed) {
            }
            
            var img = snf.ui.helpers.os_icon_path(params.image.get("OS"))
            this.name.css({backgroundImage:"url({0})".format(img)})

            this.update_image_details();
            this.update_flavor_details();
        },

        reset: function() {
            this.roles.find(".val").removeClass("selected");
            this.name_changed = false;
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
            
            return val;
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
            this.steps[3] = new views.CreateSubmitView(this);

            this.cancel_btn = this.$(".create-controls .cancel")
            this.next_btn = this.$(".create-controls .next")
            this.prev_btn = this.$(".create-controls .prev")
            this.submit_btn = this.$(".create-controls .submit")
            
            this.init_handlers();
            this.update_layout();

        },

        init_handlers: function() {
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
            if (this.validate(data)) {
                this.submit_btn.addClass("in-progress");
                this.submiting = true;
                if (data.metadata) { meta = data.metadata; }
                storage.vms.create(data.name, data.image, data.flavor, meta, {}, _.bind(function(data){
                    this.close_all();
                    this.password_view.show(data.server.adminPass, data.server.id);
                    this.submiting = false;
                }, this));
            }
        },

        close_all: function() {
            this.hide();
        },

        reset: function() {
            this.current_step = 1;

            this.steps[1].reset();
            this.steps[2].reset();
            this.steps[3].reset();

            this.steps[1].show();
            this.steps[2].show();
            this.steps[3].show();

            this.submit_btn.removeClass("in-progress");
        },

        onShow: function() {
            this.reset()
            this.update_layout();
        },

        update_layout: function() {
            this.show_step(this.current_step);
            this.current_view.update_layout();
        },

        beforeOpen: function() {
            this.submiting = false;
            this.reset();
            this.current_step = 1;
            this.$(".steps-container").css({"margin-left":0 + "px"});
            this.show_step(1);
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
            this.current_view = this.steps[step];
            this.update_controls();

            this.steps[step].show();
            var width = this.el.find('.container').width();
            var left = (step -1) * width * -1;
            this.$(".steps-container").css({"margin-left": left + "px"});
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
            return _.extend({}, this.steps[1].get(), this.steps[2].get(), this.steps[3].get());
        }
    });
    
})(this);

