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
        update_success_msg: 'Public key updated successfully.',
        create_failed_msg: 'Failed to create public key.',


        initialize: function(options) {
            views.PublicKeysView.__super__.initialize.apply(this, arguments);
            this.$(".private-cont").hide();
            _.bindAll(this);
            this.keys_limit = snf.config.userdata_keys_limit || 10000;
            this.bind("item:add", this.animate_on_add);
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
                            '<div class="item-action show">show key</div>' + 
                            '</div>');
            el.append(actions);
        },

        bind_list_item_actions: function(el, model) {
            views.PublicKeysView.__super__.bind_list_item_actions.apply(this, arguments);
            // initialize download link
            //snf.util.promptSaveFile(el.find(".item-actions .download"), model.get_filename(), model.get("content"))
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
                    this.enable_create();
                },this),

                _.bind(function() {
                    self.show_list_msg("error", "Cannot generate public key, please try again later.");
                    
                    this.generating = false;
                    this.download_private = false;

                    this.$(".add-generate").text(generate_text).removeClass("in-progress").removeClass("download");
                    this.enable_create();
                }, this)
            );
        },

        __generate_new: function(generate_text) {
            var self = this;
            var key = storage.keys.generate_new(_.bind(this.__save_new, this, generate_text), function(xhr){
                var resp_error = "";
                // try to parse response
                try {
                    json_resp = JSON.parse(xhr.responseText);
                    resp_error = json_resp.errors[json_resp.non_field_key].join("<br />");
                } catch (err) {}
                
                var msg = "Cannot generate new key pair";
                if (resp_error) {
                    msg += " ({0})".format(resp_error);
                }
                self.show_list_msg("error", msg);
                self.generating = false;
                self.download_private = false;
                self.$(".add-generate").text(generate_text).removeClass(
                        "in-progress").addClass("download");
                self.enable_create();
            });
        },

        generate_new: function() {
            if (this.generating) { return false };

            this.$(".private-cont").hide();
            this.generating = true;
            this.download_private = false;
            this.disable_create();
            var generate_text = this.$(".add-generate").text();
            this.$(".add-generate").text("Generating...").addClass("in-progress").removeClass("download");
            
            window.setTimeout(_.bind(this.__generate_new, this, generate_text), 400);

        },

        disable_create: function() {
            this.create_disabled = true;
            this.$(".collection-action.add").addClass("disabled");
        },
        
        enable_create: function() {
            this.create_disabled = false;
            this.$(".collection-action.add").removeClass("disabled");
        },
        
        show_download_private: function(name, private) {
            var download_cont = this.$(".private-cont");
            var private_download_filename = "id_rsa";

            download_cont.show();
            download_cont.find(".key-contents textarea").val("");
            download_cont.find(".private-msg, .down-button").show();
            download_cont.find(".private-msg.copy").hide();
            download_cont.find(".private-msg.download").hide();
            download_cont.find("textarea").hide();
            download_cont.find("form").attr({action: snf.config.userdata_keys_url + '/download'})
            download_cont.find('[name=data]').val(private);
            download_cont.find('[name=name]').val(private_download_filename);
        },

        update_list_item: function(el, model) {
            el.find(".name").text(model.get("name"));
            el.find(".key-type").text(model.identify_type() || "unknown");
            el.find(".publicid .param-content textarea").val(model.get("content"));
            el.find(".fingerprint .text").text(model.get("fingerprint"));
            el.find(".publicid").attr("title", _(model.get("content")).truncate(1000, "..."));
            return el;
        },

        update_list: function() {
            views.PublicKeysView.__super__.update_list.apply(this, arguments);
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


