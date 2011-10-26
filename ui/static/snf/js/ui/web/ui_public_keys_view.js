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
    
    views.PublicKeysView = views.CollectionView.extend({
        collection: storage.keys,

        confirm_delete_msg: 'Are you sure you want to remove this key ?',
        create_success_msg: 'Public key created successfully.',
        create_failed_msg: 'Failed to create public key.',

        initialize: function(options) {
            views.PublicKeysView.__super__.initialize.apply(this, arguments);
            this.$(".private-cont").hide();
            _.bindAll(this);
        },

        append_actions: function(el, model) {
            var actions = $('<div class="item-actions">' +
                            '<div class="item-action remove">remove</div>' + 
                            '<div class="item-action confirm-remove">' + 
                            '<span class="text do-confirm">confirm</span>' + 
                            '<span class="cancel-remove cancel">X</span></div>' + 
                            '<div class="item-action edit">edit</div>' + 
                            '<div class="item-action show">show key</div>' + 
                            '</div>');
            el.append(actions);
        },
        
        close_private: function() {
            this.$(".private-cont").hide();
            this.$(".private-cont textarea").val("");   
            this.$('.private-cont [name=data]').val("");
            this.$('.private-cont [name=name]').val("");
        },

        init_handlers: function() {
            views.PublicKeysView.__super__.init_handlers.apply(this, arguments);
            
            this.$(".add-generate").click(_.bind(this.generate_new, this, undefined));

            // browser compat check
            if (snf.util.canReadFile()) {
                var self = this;
                this.form.find(".fromfile").get(0).addEventListener("change", function(e){
                    var f = undefined;
                    var files = e.target.files;
                    if (files.length == 0) { return };

                    f = files[0];
                    var data = snf.util.readFileContents(f, _.bind(function(data) {
                        this.form.find("textarea").val(data);   
                    }, self));
                });
            }

            var self = this;
            this.$(".private-cont .close-private").live("click", function(e) {
                self.close_private();
            });

            this.$(".item-action.show, .item-action.hide").live("click", function(e) {
                var open = $(this).parent().parent().parent().hasClass("expanded");
                if (open) {
                    $(this).text("show key");
                    $(this).addClass("show").removeClass("hide");
                } else {
                    $(this).text("hide key");
                    $(this).removeClass("show").addClass("hide");
                }
                $(this).parent().parent().parent().toggleClass("expanded");
            });
        },
        
        __save_new: function(generate_text, key) {
            var self = this;
            storage.keys.add_crypto_key(key.public,
                _.bind(function(instance, data) {
                    self.update_models();
                    this.generating = false;
                    this.$(".add-generate").text(generate_text).removeClass(
                        "in-progress").addClass("download");
                    this.show_download_private(instance.get('name'), key.private, instance);
                },this),

                _.bind(function() {
                    self.show_list_msg("error", "Cannot generate public key, please try again later.");
                    
                    this.generating = false;
                    this.download_private = false;

                    this.$(".add-generate").text(generate_text).removeClass("in-progress").removeClass("download");
                }, this)
            );
        },

        __generate_new: function(generate_text) {
            var self = this;
            var key = storage.keys.generate_new(_.bind(this.__save_new, this, generate_text), function(){
                self.show_list_msg("error", "Cannot generate new key pair");
                self.generating = false;
                self.download_private = false;
                self.$(".add-generate").text(generate_text).removeClass(
                        "in-progress").addClass("download");
            });
        },

        generate_new: function() {
            if (this.generating) { return false };
            this.$(".private-cont").hide();
            this.generating = true;
            this.download_private = false;

            var generate_text = this.$(".add-generate").text();
            this.$(".add-generate").text("Generating...").addClass("in-progress").removeClass("download");
            
            window.setTimeout(_.bind(this.__generate_new, this, generate_text), 400);

        },
        
        show_download_private: function(name, private) {
            var download_cont = this.$(".private-cont");
            download_cont.show();
            download_cont.find(".key-contents textarea").val("");
            download_cont.find(".private-msg, .down-button").show();
            download_cont.find(".private-msg.copy").hide();
            download_cont.find(".private-msg.download").hide();
            download_cont.find("textarea").hide();
            download_cont.find("form").attr({action: snf.config.userdata_keys_url + '/download'})
            download_cont.find('[name=data]').val(private);
            download_cont.find('[name=name]').val(name);
        },

        update_list_item: function(el, model) {
            el.find(".name").text(model.get("name"));
            el.find(".key-type").text(model.identify_type() || "unknown");
            el.find(".publicid .param-content textarea").val(model.get("content"));
            el.find(".publicid").attr("title", _(model.get("content")).truncate(1000, "..."));
            return el;
        },

        update_form_from_model: function(model) {
            this.form.find("input.input-name").val(model.get("name"));
            this.form.find("textarea.input-content").val(model.get("content"));
        },

        get_form_data: function() {
            return {
                'name': this.form.find("input.input-name").val(),
                'content': this.form.find("textarea.input-content").val()
            }
        },
        
        get_fields_map: function() {
            return {'name': "input.input-name", 'content': "textarea.input-content"};
        },
        
        validate_data: function(data) {
            var user_data = _.clone(data)
            var errors = new snf.util.errorList();

            if (!data.name || _.clean(data.name) == "") {
                errors.add("name", "Provide a valid public key name");
            }

            if (!data.content || _.clean(data.content) == "") {
                errors.add("content", "Provide valid public key content");
                return errors;
            }
            
            try {
                var content = snf.util.validatePublicKey(data.content);
                if (content) {
                    this.form.find("textarea.input-content").val(content);
                }
            } catch (err) {
                errors.add("content", "Invalid key content (" + err + ")");
            }

            return errors;
        },

        reset: function() {
            this.$(".private-cont").hide();
            this.$(".list-messages").empty();
            this.$(".form-messages").empty();
            this.$(".model-item").removeClass("expanded");
            this.close_private();
            this.close_form();
        }

    })

    views.PublicKeysOverlay = views.Overlay.extend({
        
        view_id: "public_keys_view",
        content_selector: "#user_public_keys",
        css_class: 'overlay-public-keys overlay-info',
        overlay_id: "user_public_keys_overlay",

        title: "Manage your ssh keys",
        subtitle: "SSH keys",

        initialize: function(options) {
            views.PublicKeysOverlay.__super__.initialize.apply(this, arguments);
            this.subview = new views.PublicKeysView({el:this.$(".public-keys-view")});
            
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
            views.PublicKeysOverlay.__super__.show.apply(this, arguments);
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


