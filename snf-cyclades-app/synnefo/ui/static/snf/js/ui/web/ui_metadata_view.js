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


    views.MetadataView = views.Overlay.extend({
        
        view_id: "metadata_view",
        content_selector: "#metadata-overlay-content",
        css_class: 'overlay-metadata overlay-info',
        overlay_id: "metadata-overlay",

        subtitle: "",
        title: "Manage tags",

        initialize: function(options) {
            views.MetadataView.__super__.initialize.apply(this);
            _.bindAll(this);

            this.current_vm = undefined;
            this.list = this.$(".options-list");
            this.tpl = this.$("li.meta-object-tpl");
            this.editor = this.$(".editor");

            this.pre_init_handlers();
        },

        pre_init_handlers: function() {
            this.$(".editor .cancel").click(_.bind(function(){
                this.close_editor();
            }, this))
            this.$(".editor .create").click(_.bind(function(){
                this.submit_editor();
            }, this));
        },

        show: function(vm) {
            this.current_vm = vm;
            this.current_vm.bind("change", this.handle_vm_change);
            views.MetadataView.__super__.show.apply(this);
        },

        get_meta: function() {
            return this.current_vm.get('metadata').values;
        },
        
        get_meta_el: function(key, value) {
            return this.tpl.clone();
        },

        beforeOpen: function() {
            this.update_layout();
        },

        update_layout: function() {
            if (!this.editing) {
                this.editor.hide();
            }

            this.update_vm_details();
            // update metadata
            this.list.empty();
            _.each(this.get_meta(), _.bind(function(value, key) {
                var el = this.get_meta_el();
                el.find(".title").text(util.truncate(key, 15)).attr("title", key);
                el.find(".value").text(util.truncate(value, 15)).attr("title", value);
                el.data('meta', {'key':key, 'value':value});
                this.list.append(el);
                $(el).data({key:key, value:value});
            }, this));

            this.list.append('<li class="options-object create">' + 
                             '<div class="options-object-cont">' +
                             '<span class="title">Add new</span>' + 
                             '<span class="value">tag</span>' + 
                             '</div>' + 
                             '</li>')

            this.list.show();
            this.init_handlers();
        },
        
        meta_from_el: function(el) {
            return el.closest("li").data("meta");
        },
    
        show_editor: function(meta, el) {
            this.editing = true;

            this.editor.find("label").removeClass("error");
            if (meta) {
                this.editor.find(".predefined").hide();
                this.editor.find("input.meta-key").val(meta.key).attr("disabled", true);
                this.editor.find("input.meta-value").val(meta.value);
            } else {
                this.editor.find(".predefined").show();
                this.editor.find("input.meta-key").val("").attr("disabled", false);
                this.editor.find("input.meta-value").val("");
            }
            this.$(".editor").fadeIn(200);

            if (meta) {
                this.editor.find("input.meta-value").focus().select();
            } else {
                this.editor.find("input.meta-key").focus();
            }
            
            // remove predefined for existing keys
            var existing_keys = this.current_vm.get_meta_keys();
            if (!meta) {
                this.editor.find(".predefined-meta-key").each(function(i, el){
                    if (_.contains(existing_keys, $(el).text())) {
                        $(el).hide();
                    } else {
                        $(el).show();
                    }
                })
            }
        },

        update_vm_details: function() {
            // show proper title
            this.set_subtitle(this.current_vm.escape("name") + snf.ui.helpers.vm_icon_tag(this.current_vm, "small"));
        },

        validate: function(meta) {
            if (!meta) { return false };
            if ((meta.key && meta.key != "") && (meta.value && meta.value != "")) {
                return true;
            }
            return false;
        },

        get_editor_values: function() {
            var meta = {};
            meta.key = this.editor.find("input.meta-key").val();
            meta.value = this.editor.find("input.meta-value").val();

            meta.key = _(meta.key).trim();
            meta.value = _(meta.value).trim();
            return meta;
        },
    
        submit_editor: function() {
            if (!this.editing) { return };
            this.editing = false;
            var meta = this.get_editor_values();
            if (this.validate(meta)) {
                this.$(".editor .create").addClass('in-progress');
                this.current_vm.save_meta(meta, _.bind(function() {
                    this.close_editor();
                    this.$(".editor .create").removeClass('in-progress');
                }, this));
            } else {
                this.editing = true;
                this.editor.find(".form-field label").addClass("error");
            }

        },

        remove_meta: function(key) {
            this.current_vm.remove_meta(key);
        },

        close_editor: function() {
            this.$(".editor").fadeOut(100);
            this.editing = false;
        },

        init_handlers: function() {
            var self = this;
            this.list.find(".remove").click(function(e){
                e.preventDefault();
                var meta = self.meta_from_el($(this));
                self.remove_meta(meta.key);
                $(this).parent().parent().parent().remove();
            });

            this.list.find(".edit").click(function(e) {
                e.preventDefault();
                var meta = self.meta_from_el($(this));
                self.show_editor(meta, $(this));
            })

            //this.list.find(".options-object").dblclick(function(e) {
                //e.preventDefault();
                //var meta = self.meta_from_el($(this));
                //self.show_editor(meta, $(this));
            //})

            this.list.find("li.create").click(function(){
                self.show_create();
            })
            
            this.editor.find("input").keyup(_.bind(function(e){
                e.keyCode = e.keyCode || e.which;
                if (e.keyCode == 13) { this.submit_editor() };    
                if (e.keyCode == 27) { this.close_editor() };    
            }, this));

            this.editor.find(".predefined-meta-key").click(function() {
                self.editor.find("input.meta-key").val($(this).text());
                self.editor.find("input.meta-value").focus();
            })

        },

        show_create: function() {
            this.$(".editor .create").removeClass('in-progress');
            this.show_editor();
        },

        unbind_vm_handlers: function() {
            if (!this.current_vm) { return }
            this.current_vm.unbind("change", this.handle_vm_change);
        },

        handle_vm_change: function(vm) {
            // if overlay has been closed and for
            // some reason change event still triggers
            // force event unbind
            if (!this.current_vm) {
                vm.unbind("change", this.handle_vm_change);
                return;
            } 

            this.update_vm_details();
            this.update_layout();
        },

        onClose: function() {
            this.editing = false;
            this.unbind_vm_handlers();
            this.current_vm = undefined;
        }
    });
    
})(this);
