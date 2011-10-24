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
    
    views.CollectionView = views.View.extend({

        collection: undefined,
        
        id_tpl: 'model-item-{0}',
        list_tpl: '#model-item-tpl',
        
        force_reset_before_fetch: true,
        auto_append_actions: true,

        initialize: function(options) {
            views.CollectionView.__super__.initialize.apply(this, arguments);
            _.bindAll(this);

            this.loading = this.$(".loading-models");
            this.content = this.$(".content");
            this.list = this.$(".model-list .items-list");
            this.list_cont = this.$(".model-list");
            this.form = this.$(".model-form");
            this.empty_msg = this.$(".items-empty-msg");
            
            this.init_collection_handlers();
            this.init_handlers();
            this.close_form();
            this.content.hide();
            this.loading.show();
            this.update_models();
            this.items = [];
            this.submiting = false;
        },
        
        update_models: function() {
            this.collection.fetch({success:this.handle_reset});
        },
        
        init_handlers: function() {
            this.$(".add-new").click(_.bind(this.show_form, this, undefined));

            this.form.find(".form-action.cancel").click(this.close_form);
            this.form.find(".form-action.submit").click(this.submit_form);
            
            var self = this;
            this.form.find("form").submit(function(e){
                e.preventDefault();
                self.submit_form();
                return false;
            });

            this.$(".quick-add").click(_.bind(this.show_form, this, undefined));
        },

        init_collection_handlers: function() {
            this.collection.bind("reset", this.handle_reset);
        },

        reset_handlers: function() {
            this.collection.unbind("reset", this.handle_reset);
        },
            
        set_items: function(models) {
            this.items = _.map(models, function(m) { return m.id });
        },

        handle_reset: function(collection, models) {
            this.loading.hide();
            this.content.show();

            if (this.force_reset_before_update) {
                this.reset_list();
            }

            this.update_list(this.collection.models);
            this.update_removed(this.items, this.collection.models);

            this.set_items(this.collection.models);
        },

        show_form: function(model) {
            var create = (model === undefined ? true : false);
        
            if (create) {
                this.form.find(".new-title").show();
                this.form.find(".edit-title").hide();
            } else {
                this.form.find(".new-title").hide();
                this.form.find(".edit-title").show();
            }

            var model = model || new this.collection.model();
            this.list_cont.hide();

            this.reset_form(model);
            if (!snf.util.canReadFile()) {
                this.form.find(".fromfile-field").hide();
            }
            this.form.show();

            this.editing = true;
            this.editing_id = model.id;
            this.creating = create ? true : false;

            $(this.form.find("input").get(0)).focus();
            this.reset_form_errors();
        },

        reset_form: function(model) {
            if (!model) {
                this.form.find("input, textarea").val("");
                return;
            }

            this.update_form_from_model(model);
        },
        
        show_list_msg: function(type, msg) {
            this.list_messages = this.list_messages || this.$(".list-messages");
            var el = $('<div class="{0}">{1}</div>'.format(type, msg));
            this.list_messages.append(el);
            window.setTimeout(function(){
                el.fadeOut(300).delay(300).remove();
            }, this.message_timeout || 4000)
        },
        
        get_fields_map: function() {
            return {};
        },
        
        reset_form_errors: function() {
            this.form.find(".form-field").removeClass("error");
            this.form.find(".form-field .errors").empty();
        },

        show_form_errors: function(errors) {
            this.reset_form_errors();
            var fields_map = this.get_fields_map();
            this.form_messages = this.form_messages || this.$(".form-messages");
            
            _.each(errors.errors, _.bind(function(error, key){
                var field = this.form.find(fields_map[key]).closest(".form-field");
                field.addClass("error");
                _.each(error, function(error_msg) {
                    var error_el = $('<div class="error">{0}</div>'.format(error_msg));
                    field.find(".errors").append(error_el);
                });
            }, this));
            //var el = $('<div class="error">{1}</div>'.format(type, msg));
            //this.list_messages.append(el);
        },

        clean_form_errors: function() {
        },
        
        submit_form: function() {
            if (this.submiting) { return };
            var errlist = this.validate_data(this.get_form_data());
            if (errlist.empty()) {
                this.save_model(this.get_form_data());
            } else {
                this.show_form_errors(errlist);
            }
        },

        close_form: function() {
            this.editing = false;
            this.editing_id = undefined;
            this.creating = false;

            this.form.hide();
            this.list_cont.show();
            this.list_cont.find("h3").show();
        },

        create_model_element: function(model) {
            var el = this.$(this.list_tpl).clone();

            el.removeClass("hidden");
            el.addClass("model-item");
            el.attr("id", "item-content-" + this.id_tpl.format(model.id));

            if (this.auto_append_actions) {
                this.append_actions(el, model);
            }

            return el;
        },

        append_actions: function(el, model) {
            var actions = $('<div class="item-actions">' +
                            '<div class="item-action remove">remove</div>' + 
                            '<div class="item-action confirm-remove confirm">' +
                            '<span class="text">confirm</span>' + 
                            '<span class="cancel-remove cancel">cancel</span></div>' + 
                            '<div class="item-action edit">edit</div>' +
                            '</div>');
            el.append(actions);
        },

        bind_list_item_actions: function(el, model) {
            el.find(".item-actions .edit").click(_.bind(this.show_form, this, model));
            el.find(".item-actions .remove").click(_.bind(this.show_confirm_remove, this, el, model));
            el.find(".item-actions .confirm-remove .do-confirm").click(_.bind(this.delete_model, this, model)).hide();
            el.find(".item-actions .confirm-remove .cancel-remove").click(_.bind(this.cancel_confirm_remove, 
                                                                        this, el, model)).hide();
            
            // initialize download link
            snf.util.promptSaveFile(el.find(".item-actions .download"), model.get_filename(), model.get("content"))
        },

        show_confirm_remove: function(el, model) {
            var confirmed = confirm("Are you sure you want to delete this key ?");
            if (confirmed) {
                this.delete_model(model);
            }
            //el.closest(".model-item").addClass("pending-delete");
        },

        cancel_confirm_remove: function(el, model) {
            el.closest(".model-item").removeClass("pending-delete");
        },

        new_list_el: function(model) {
            var list_el = $("<li></li>");
            el = this.create_model_element(model);
            list_el.attr("id", this.id_tpl.format(model.id));
            list_el.addClass("model-item");
            this.update_list_item(el, model, true);
            list_el.append(el);
            this.bind_list_item_actions(list_el, model);
            return list_el;
        },

        item_el: function(id) {
            return this.$("#" + this.id_tpl.format(id));
        },

        item_exists: function(model) {
            return this.item_el(model.id).length > 0;
        },

        reset_list: function() {
            this.list.find("model-item").remove();
        },
        
        save_model: function(data) {
            this.form.find("form-action.submit").addClass("in-progress");
            this.submiting = true;

            var options = {
                success: _.bind(function(){
                    this.update_models();
                    this.close_form();
                    this.show_list_msg("success", "Public key created");
                }, this),

                error: _.bind(function(){
                    this.show_form_errors({'':'Public key submition failed'})
                }, this),

                complete: _.bind(function(){
                    this.submiting = false;
                    this.form.find("form-action.submit").addClass("in-progress");
                }, this)
            }

            if (this.editing_id && this.collection.get(this.editing_id)) {
                var model = this.collection.get(this.editing_id);
                model.save(data, options);
            } else {
                this.collection.create(data, options);
            }
        },

        delete_model: function(model) {
            this.item_el(model.id).addClass("in-progress").addClass("deleting");
            var self = this;
            model.destroy({success:this.update_models, error: function() {
                    self.show_list_msg("error", "Remove failed");
                    self.item_el(model.id).removeClass("in-progress").removeClass("deleting");
                }});
        },
        
        update_removed: function(ids, models) {
            var newids = _.map(models, function(m) { return m.id });
            _.each(_.difference(ids, newids), _.bind(function(id){
                this.item_el(id).remove();
            }, this));
        },

        update_list: function(models, reset) {
            var reset = reset || false;
            if (reset) { this.reset_list() };
            
            // handle removed items
            _.each(models, _.bind(function(model) {
                if (this.item_exists(model)) { 
                    this.update_list_item(this.item_el(model.id), model);
                    return;
                };
                this.list.append(this.new_list_el(model))
            }, this));

            this.check_empty();
        },

        check_empty: function() {
            if (this.collection.length == 0) {
                this.empty_msg.show();
                this.list.find(".header").hide();
                this.el.addClass("empty");
            } else {
                this.empty_msg.hide();
                this.list.find(".header").show();
                this.el.removeClass("empty");
            }
        },

        reset: function (){}

    });

    views.PublicKeysView = views.CollectionView.extend({
        collection: storage.keys,

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
                self.$(".private-cont").hide();
                self.$(".private-cont textarea").val("");   
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
        
        __generate_new: function(generate_text) {
            var key = storage.keys.generate_new();
            var self = this;

            storage.keys.add_crypto_key(key,
                _.bind(function(instance, data) {
                    self.update_models();
                    this.generating = false;
                    this.$(".add-generate").text(generate_text).removeClass(
                        "in-progress").addClass("download");
                    this.show_download_private(key, instance);
                },this),

                _.bind(function() {
                    self.show_list_msg("error", "Cannot generate public key, please try again later.");
                    
                    this.generating = false;
                    this.download_private = false;

                    this.$(".add-generate").text(generate_text).removeClass("in-progress").removeClass("download");
                }, this)
            );
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
        
        show_download_private: function(key, data) {
            var download_cont = this.$(".private-cont");
            download_cont.find(".key-contents textarea").val("");
            download_cont.find(".private-msg, .down-button").hide();

            var pr = snf.util.promptSaveFile(download_cont.find(".down-button"), 
                                             "{0}_private.pem".format(data.get("name")), key.privatePEM());
            //pr = false;
            if (pr) {
                download_cont.find(".private-msg.download").show();
                download_cont.find(".down-button").show();
                download_cont.find(".key-contents textarea").val("").hide();
            } else {
                download_cont.find(".key-contents textarea").val(key.privatePEM()).show();
                download_cont.find(".private-msg.copy").show();
            }

            download_cont.show();
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
        },

        show: function() {
            this.subview.reset();
            views.PublicKeysOverlay.__super__.show.apply(this, arguments);
        },

        init_handlers: function() {
        }
        
    });
})(this);


