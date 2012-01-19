;(function(root){

    // root
    var root = root;
    
    // setup namepsaces
    var snf = root.synnefo = root.synnefo || {};
    var api = snf.api = snf.api || {};
    var models = snf.models = snf.models || {}
    var storage = snf.storage = snf.storage || {};
    var ui = snf.ui = snf.ui || {};
    var util = snf.util = snf.util || {};

    var views = snf.views = snf.views || {}

    // shortcuts
    var bb = root.Backbone;
    var urlregex = new RegExp("^(http:\/\/www.|https:\/\/www.|ftp:\/\/www.|www.){1}([0-9A-Za-z]+\.)");

    views.CustomImagesView = views.CollectionView.extend({

        confirm_delete_msg: 'Are you sure you want to remove this image ?',
        create_success_msg: 'Custom image created successfully.',
        update_success_msg: 'Custom image updated successfully.',
        create_failed_msg: 'Failed to register custom image.',


        initialize: function(options) {
            this.collection = storage.images;
            views.CustomImagesView.__super__.initialize.apply(this, arguments);
            _.bindAll(this);
            this.keys_limit = snf.config.userdata_keys_limit || 10000;
            this.bind("item:add", this.animate_on_add);
        },

        _get_models: function() {
            return this.collection.get_personal_images();
        },

        animate_on_add: function(list, el, model) {
            el.hide();
            el.fadeIn(400);
        },

        append_actions: function(el, model) {
            var actions = $('<div class="item-actions">' +
                            '<div class="item-action remove">remove</div>' + 
                            '<div class="item-action confirm-remove">' + 
                            '<span class="text do-confirm">confirm</span>' + 
                            '<span class="cancel-remove cancel">X</span></div>' + 
                            '<div class="item-action edit">edit</div>' + 
                            '</div>');
            el.append(actions);
        },

        update_list_item: function(el, model) {
            el.find(".name").text(model.get("name"));
            return el;
        },

        update_list: function() {
            views.CustomImagesView.__super__.update_list.apply(this, arguments);
            this.check_limit();
        },

        check_limit: function() {
            if (snf.storage.keys.length >= this.keys_limit) {
                this.$(".collection-action").hide();
                this.$(".limit-msg").show();
            } else {
                this.$(".collection-action").show();
                this.$(".limit-msg").hide();
            }
        },

        update_form_from_model: function(model) {
            this.form.find("input.input-name").val(model.get("name"));
        },

        get_save_params: function(data, options) {
            options.data = {'image': {'serverRef':3, 'name': "test image"}};
            return options
        },

        get_form_data: function() {
            return {
                'name': this.form.find("input.input-name").val(),
                'url': this.form.find("input.input-url").val(),
                'format': this.form.find("input.input-forma").val(),
                'is_public': this.form.find("input.input-public").val()
            }
        },
        
        get_fields_map: function() {
            return {
                    'name': "input.input-name", 
                    'url': "input.input-url",
                    'public': "input.input-public",
                    'format': "input.input-format"
                };
        },
        
        validate_data: function(data) {
            var user_data = _.clone(data)
            var errors = new snf.util.errorList();
            
            if (!data.name || _.clean(data.name) == "") {
                errors.add("name", "Provide a valid image name");
            }

            if (!data.url || _.clean(data.url) == "" || !urlregex.test(data.url)) {
                errors.add("url", "Provide a valid url");
            }

            return errors;
        },

        reset: function() {
            this.$(".list-messages").empty();
            this.$(".form-messages").empty();
            this.$(".model-item").removeClass("expanded");
            this.close_form();
        }

    })

    views.CustomImagesOverlay = views.Overlay.extend({
        
        view_id: "custom_images_view",
        content_selector: "#user_custom_images",
        css_class: 'overlay-custom-images overlay-info',
        overlay_id: "user_custom_images_overlay",

        title: "Manage your OS images",
        subtitle: "OS Images",

        initialize: function(options) {
            views.CustomImagesOverlay.__super__.initialize.apply(this, arguments);
            this.subview = new views.CustomImagesView({el:this.$(".custom-images-view")});
            
            var self = this;
            this.$(".previous-view-link").live('click', function(){
                self.hide();
            })
        },

        show: function(view) {
            this.from_view = view || undefined;
            
            if (this.from_view) {
                this.$(".previous-view-link").show();
            } else {
                this.$(".previous-view-link").hide();
            }

            this.subview.reset();
            views.CustomImagesOverlay.__super__.show.apply(this, arguments);
        },
        
        onClose: function() {
            if (this.from_view) {
                this.hiding = true;
                this.from_view.skip_reset_on_next_open = true;
                this.from_view.show();
                this.from_view = undefined;
            }
        },

        init_handlers: function() {
        }
        
    });
})(this);

