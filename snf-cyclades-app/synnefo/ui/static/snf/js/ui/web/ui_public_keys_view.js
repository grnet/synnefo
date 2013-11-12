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
    var util = snf.util || {};
    var views = snf.views = snf.views || {}

    // shortcuts
    var bb = root.Backbone;
    
    // logging
    var logger = new snf.logging.logger("SNF-VIEWS");
    var debug = _.bind(logger.debug, logger);
      
    views.PublicKeyCreateView = views.Overlay.extend({
        view_id: "public_key_create_view",
        
        content_selector: "#public-key-create-content",
        css_class: 'overlay-public-key-create overlay-info',
        overlay_id: "public_key_create_view",

        subtitle: "",
        title: "Create new SSH key",
        
        initialize: function() {
            views.PublicKeyCreateView.__super__.initialize.apply(this, arguments);
            this.form = this.$("form.model-form");
            this.submit = this.$(".form-actions .submit");
            this.cancel = this.$(".form-actions .cancel");
            this.close = this.$(".form-actions .close");
            this.error = this.$(".error-msg");
            this.model_actions = this.$(".model-actions");
            this.form_actions_cont = this.$(".form-actions");
            this.form_actions = this.$(".form-actions .form-action");

            this.input_name = this.form.find(".input-name");
            this.input_key = this.form.find("textarea");
            this.input_file = this.form.find(".content-input-file");
            
            this.generate_action = this.$(".model-action.generate");
            this.generate_msg = this.$(".generate-msg");
            this.generate_download = this.generate_msg.find(".download");
            this.generate_success = this.generate_msg.find(".success");

            this.generating = false;
            this.in_progress = false;
            this.init_handlers();
        },

        _init_reader: function() {
          var opts = {
            dragClass: "drag",
            accept: false,
            readAsDefault: 'BinaryString',
            on: {
              loadend: _.bind(function(e, file) {
                this.input_key.val(e.target.result);
                this.validate_form();
              }, this),
              error: function() {}
            }
          }
          FileReaderJS.setupInput(this.input_file.get(0), opts);
        },
        
        validate_form: function() {
          this.form.find(".error").removeClass("error");
          this.form.find(".errors").empty();

          var name = _.trim(this.input_name.val());
          var key = _.trim(this.input_key.val());
          var error = false;

          if (!name) {
            this.input_name.parent().addClass("error");
            error = true;
          }

          if (!key) {
            this.input_key.parent().addClass("error");
            error = true;
          } else {
            try {
              key = snf.util.validatePublicKey(key);
            } catch (err) {
              this.input_key.parent().addClass("error");
              this.input_key.parent().find(".errors").append("<span class='error'>"+err+"</span>");
              error = true;
            }
          }

          if (error) { return false }
          return { key: key, name: name }
        },

        _reset_form: function() {
          this.input_name.val("");
          this.input_key.val("");
          this.input_file.val("");
          this.form.find(".error").removeClass("error");
          this.form.find(".errors").empty();
          this.form.show();
          this.generate_msg.hide();
          this.form_actions.show();
          this.input_file.show();
          this.close.hide();
          this.error.hide();
          this.model_actions.show();
        },

        beforeOpen: function() {
          this.private_key = undefined;
          this._reset_form();
          this._init_reader();
          this.unset_in_progress();
        },
        
        init_handlers: function() {
          this.cancel.click(_.bind(function() { this.hide(); }, this));
          this.close.click(_.bind(function() { this.hide(); }, this));
          this.generate_action.click(_.bind(this.generate, this));
          this.generate_download.click(_.bind(this.download_key, this));
          this.form.submit(_.bind(function(e){
            e.preventDefault();
            this.submit_key(_.bind(function() {
              this.hide();
            }, this))
          }, this));
          this.submit.click(_.bind(function() {
            this.form.submit();
          }, this));
        },
        
        set_in_progress: function() {
          this.in_progress = true;
          this.submit.addClass("in-progress");
        },

        unset_in_progress: function() {
          this.in_progress = false;
          this.submit.removeClass("in-progress");
        },

        submit_key: function(cb) {
          var data = this.validate_form();
          if (!data) { return }
          this.set_in_progress();
          var params = {
            complete: _.bind(function() {
              synnefo.storage.keys.fetch();
              this.unset_in_progress();
              cb && cb();
            }, this)
          };

          synnefo.storage.keys.create({
            content: data.key, 
            name: data.name,
          }, params);
        },

        download_key: function() {
          try {
            var blob = new Blob([this.private_key], {
              type: "application/x-perm-key;charset=utf-8"
            });
            saveAs(blob, "id_rsa");
          } catch (err) {
            alert(this.private_key);
          }
        },
        
        _generated_key_name: function() {
          var name_tpl = "Generated ssh key name";
          var name = name_tpl;
          var exists = function() {
            return synnefo.storage.keys.filter(function(key){
              return key.get("name") == name;
            }).length > 0;
          }

          var count = 1;
          while(exists()) {
            name = name_tpl + " {0}".format(++count);
          }
          return name;
        },

        generate: function() {
          this.error.hide();
          this.generate_msg.hide();

          if (this.generating) { return }
          
          this.generating = true;
          this.generate_action.addClass("in-progress");
          
          var success = _.bind(function(key) {
            this.generating = false;
            this.generate_action.removeClass("in-progress");
            this.input_name.val(this._generated_key_name());
            this.input_key.val(key.public);
            this.generate_msg.show();
            this.private_key = key.private;
            this.form.hide();
            this.form_actions.hide();
            this.close.show();
            this.model_actions.hide();
            this.submit_key();
          }, this);
          var error = _.bind(function() {
            this.generating = false;
            this.generate_action.removeClass("in-progress");
            this.generate_progress.hide();
            this.private_key = undefined;
            this.show_error();
          }, this);
          var key = storage.keys.generate_new(success, error);
        },

        show_error: function(msg) {
          msg = msg === undefined ? "Something went wrong. Please try again later." : msg;
          if (msg) { this.error.find("p").html(msg) }
          this.error.show();
        }
    });

    views.PublicKeyView = views.ext.ModelView.extend({
      tpl: '#public-key-view-tpl',
      post_init_element: function() {
        this.content = this.$(".content-cont");
        this.content.hide();
        this.content_toggler = this.$(".cont-toggler");
        this.content_toggler.click(this.toggle_content);
        this.content_visible = false;
      },

      toggle_content: function() {
        if (!this.content_visible) {
          this.content.slideDown();
          this.content_visible = true;
          this.content_toggler.addClass("open");
        } else {
          this.content.slideUp();
          this.content_visible = false;
          this.content_toggler.removeClass("open");
        }
      },

      remove_key: function() {
        this.model.actions.reset_pending();
        this.model.remove(function() {
            synnefo.storage.keys.fetch();
        });
      }
    });
    
    views.PublicKeysCollectionView = views.ext.CollectionView.extend({
      collection: storage.keys,
      collection_name: 'keys',
      model_view_cls: views.PublicKeyView,
      create_view_cls: views.PublicKeyCreateView
    });

    views.PublicKeysPaneView = views.ext.PaneView.extend({
      id: "pane",
      el: '#public-keys-pane',
      collection_view_cls: views.PublicKeysCollectionView,
      collection_view_selector: '#public-keys-list-view'
    });

})(this);

