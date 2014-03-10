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
    
    // Reusable collection view
    // Helpers handling list/edit functionality of a specific Collection object
    views.CollectionView = views.View.extend({

        collection: undefined,
        
        id_tpl: 'model-item-{0}',
        list_tpl: '#model-item-tpl',
        
        force_reset_before_fetch: true,
        auto_append_actions: true,
        fetch_params: {},

        initialize: function(options) {
            views.CollectionView.__super__.initialize.apply(this, arguments);
            _.bindAll(this);

            this.loading = this.$(".loading-models");
            this.content = this.$(".content");
            this.list = this.$(".model-list .items-list");
            this.list_cont = this.$(".model-list");
            this.form = this.$(".model-form-cont");
            this.empty_msg = this.$(".items-empty-msg");
            
            this.init_collection_handlers();
            this.init_handlers();
            this.close_form();
            this.content.hide();
            this.loading.show();
            this.update_models();
            this.items = [];
            this.create_disabled = false;
            this.submiting = false;
        },
        
        update_models: function() {
            var params = {};
            _.extend(params, this.fetch_params);
            params['success'] = this.handle_reset;
            this.collection.fetch(params);
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

        _get_models: function() {
            return this.collection.models;
        },

        handle_reset: function(collection, models) {
            this.loading.hide();
            this.content.show();

            if (this.force_reset_before_update) {
                this.reset_list();
            }

            this.update_list(this._get_models());
            this.update_removed(this.items, this._get_models());

            this.set_items(this._get_models());
        },

        show_form: function(model) {
            if (this.create_disabled) { return };
            var create = (model === undefined || model.id === undefined ? true : false);
        
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
            if (!model.id) {
                this.form.find("input, textarea").val("");
                this.form.find("select").each(function() {
                    $(this).get(0).selectedIndex = 0;
                });
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
            this.form.find(".form-messages").empty();
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
            
            var msg = errors[''];
            if (msg) {
                var el = $('<div class="error">{0}</div>'.format(msg));
                this.$(".form-messages").append(el);
            }
        },

        clean_form_errors: function() {

        },

        get_save_params: function(data, options) {
            return options;
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
        },

        show_confirm_remove: function(el, model) {
            var confirmed = confirm(this.confirm_delete_msg || "Are you sure you want to delete this entry ?");
            if (confirmed) {
                this.delete_model(model);
            }
            //el.closest(".model-item").addClass("pending-delete");
        },

        cancel_confirm_remove: function(el, model) {
            el.closest(".model-item").removeClass("pending-delete");
        },
      
        _list_el: "<li></li>",

        new_list_el: function(model) {
            var list_el = $(this._list_el);
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
            var created = this.creating;
            var options = {
                success: _.bind(function(){
                    this.update_models();
                    this.close_form();
                    if (created) {
                        this.show_list_msg("success", this.create_success_msg || "Entry created");
                    } else {
                        this.show_list_msg("success", this.update_success_msg || "Entry updated");
                    }
                }, this),

                error: _.bind(function(data, xhr){
                    var resp_error = "";
                    // try to parse response
                    try {
                        json_resp = JSON.parse(xhr.responseText);
                        resp_error = json_resp.errors[json_resp.non_field_key].join("<br />");
                    } catch (err) {}

                    var form_error = resp_error != "" ? 
                                this.create_failed_msg + " ({0})".format(resp_error) : 
                                this.create_failed_msg;
                    this.show_form_errors({'': form_error || this.submit_failed_msg || 'Entry submition failed'})
                }, this),

                complete: _.bind(function(){
                    this.submiting = false;
                    this.form.find("form-action.submit").addClass("in-progress");
                }, this),

                skip_api_error: true
            }

            if (this.editing_id && this.collection.get(this.editing_id)) {
                var model = this.collection.get(this.editing_id);
                model.save(data, this.get_save_params(data, options));
            } else {
                this.collection.create(data, this.get_save_params(data, options));
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
                var item_el = this.new_list_el(model);
                this.list.prepend(item_el);
                this.trigger("item:add", this.list, item_el, model);
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
})(this);
