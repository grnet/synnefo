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
        },
        
        show_password: function() {
            this.password.text(this.pass);
        },

        onClose: function() {
            this.password.text("");
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
            this.header = view.$(".subheader .step-" + this.step);
            this.view_id = "create_step_" + this.step;

            views.CreateVMStepView.__super__.initialize.apply(this);
        },

        show: function() {
            // show current
            this.el.show();
            this.header.addClass("current");
            this.update_layout();
        },

        reset: function() {
        }
    })

    views.CreateImageSelectView = views.CreateVMStepView.extend({

        initialize: function() {
            views.CreateImageSelectView.__super__.initialize.apply(this, arguments);

            this.predefined = this.$(".predefined-images ul");
            this.custom = this.$(".predefined-images ul");
            this.selected_image = undefined;
            this.reset_images();
        },

        update_layout: function() {
        },

        select_image: function(image) {
            if (!image) {
                image = storage.images.at(0);
            }

            this.selected_image = image;
            this.trigger("change", this.selected_image);
            
            this.predefined.find(".image-details").removeClass("selected");
            this.predefined.find(".image-details#create-vm-image-" + this.selected_image.id).addClass("selected")
        },

        reset_images: function() {
            this.$(".image-details").remove();
            storage.images.each(_.bind(function(img){
                this.add_image(img);
            }, this))

            this.select_image();
            
            var self = this;
            this.predefined.find(".image-details").click(function(){
                self.select_image($(this).data("image"));
            })
        },

        add_image: function(img) {
            var image = $('<li id="create-vm-image-{1}" class="image-details">{0}</li>'.format(img.get("name"), img.id));
            image.data("image", img);
            image.data("image_id", img.id);
            this.predefined.append(image);
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

            this.cpus = this.$(".flavors-cpu-list")
            this.disks = this.$(".flavors-disk-list")
            this.mems = this.$(".flavors-mem-list")

            this.reset();
            this.update_layout();
        },

        handle_image_change: function(data) {
            this.current_image = data;
            this.update_flavors_data();
            this.reset_flavors();
            this.update_layout();
        },

        reset_flavors: function() {
            this.$(".flavor-opts-list .option").remove();
            this.create_flavors();
        },

        update_flavors_data: function() {
            this.flavors = storage.flavors.for_image(this.current_image);
            this.flavors_data = storage.flavors.get_data(this.flavors);

            if (this.flavors.indexOf(this.current_flavor) == -1) {
                this.set_current(this.flavors[0]);
            }
        },

        set_current: function(flv) {
            this.current_flavor = flv;
            this.trigger("change");
            this.update_selected_flavor();
        },

        create_flavors: function() {
            var flavors = this.get_flavors();
            _.each(flavors, _.bind(function(flv){
                this.add_flavor(flv);
            }, this));
            
            var self = this;
            this.$(".flavor-options li.option").click(function(){
                var el = $(this);
                el.parent().find(".option").removeClass("selected");
                el.addClass("selected");
                self.update_selected_from_ui();
            })
        },
        
        ui_selected: function() {
            args = [this.$(".option.cpu.selected").data("value"), 
                this.$(".option.mem.selected").data("value"), 
                this.$(".option.disk.selected").data("value"),
            this.flavors];

            storage.flavors.apply(storage.flavors, args)
        },

        update_selected_flavor: function() {

        },

        add_flavor: function(flv) {
            var values = {'cpu': flv.get('cpu'), 'mem': flv.get('ram'), 'disk': flv.get('disk')};
            
            if (this.$('li.option.cpu.value-{0}'.format(values.cpu)).length == 0) {
                var cpu = $('<li class="option cpu value-{0}">{0}</li>'.format(values.cpu)).data('value', values.cpu);
                this.cpus.append(cpu);
            }
            if (this.$('li.option.mem.value-{0}'.format(values.mem)).length == 0) {
                var mem = $('<li class="option mem value-{0}">{0}</li>'.format(values.mem)).data('value', values.mem);
                this.mems.append(mem);
            }
            if (this.$('li.option.disk.value-{0}'.format(values.disk)).length == 0) {
                var disk = $('<li class="option disk value-{0}">{0}</li>'.format(values.disk)).data('value', values.disk);
                this.disks.append(disk);
            }
            
        },

        get_flavors: function() {
            return this.flavors;
        },

        update_layout: function() {
            var flv = this.current_flavor;
            this.$(".option.value").removeClass("selected");

            this.$(".option.cpu.value-" + flv.get("cpu")).addClass("selected");
            this.$(".option.mem.value-" + flv.get("ram")).addClass("selected");
            this.$(".option.disk.value-" + flv.get("disk")).addClass("selected");
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
            this.confirm = this.$(".confirm-params ul");
            this.name = this.$("input");
            this.name_changed = false;
            this.init_handlers();
        },

        init_handlers: function() {
            this.name.bind("keypress", _.bind(function() {
                this.name_changed = true;
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

        update_layout: function() {
            var params = this.parent.get_params();
            var vm_name = "My {0} server".format(params.image.get("name"));
            var orig_name = vm_name;
            
            var existing = true;
            var j = 0;
            while (existing) {
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
            this.confirm.find("li.cpu .value").text(params.flavor.get("cpu"));
            this.confirm.find("li.mem .value").text(params.flavor.get("ram"));
            this.confirm.find("li.disk .value").text(params.flavor.get("disk"));
        },

        reset: function() {
            this.update_layout();
        },

        get: function() {
            return {'name': this.name.val() };
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
                this.show_step(this.current_step + 1);
                this.update_layout();
            }, this))
            this.prev_btn.click(_.bind(function(){
                this.show_step(this.current_step - 1);
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
            var data = this.get_params();
            if (this.validate(data)) {
                this.submit_btn.addClass("in-progress");
                storage.vms.create(data.name, data.image, data.flavor, {}, {}, _.bind(function(data){
                    this.close_all();
                    this.password_view.show(data.server.adminPass);
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
            this.reset();
            this.current_step = 1;
            this.show_step(1);
        },

        show_step: function(step) {
            if (step <= 1) {
                step = 1
            }
            if (step > this.steps.length - 1) {
                step = this.steps.length - 1;
            }
                
            // hide other
            this.$(".subheader .header-step").removeClass("current");
            this.$(".create-step-cont").hide();
            
            this.steps[step].show();
            this.current_step = step;
            this.current_view = this.steps[step];
            //
            this.update_controls();
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

