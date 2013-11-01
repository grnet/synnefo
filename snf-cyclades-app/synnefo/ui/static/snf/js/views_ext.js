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

    // Extended views module
    // View objects to provide more sophisticated base objects for views 
    // that are bind to existing storage model/collection objects.
    views.ext = {};
    
    views.ext.View = views.View.extend({
      rivets_view: false,
      rivets: undefined,

      storage_handlers: {},

      init: function() {},
      post_init: function() {},

      initialize: function() {
        this._subviews = [];
        if (this.tpl) {
          this.el = $(this.tpl).clone().removeClass("hidden").removeAttr('id');
        }
        this.init.apply(this, arguments);
        this.post_init.apply(this, arguments);
        _.bindAll(this);
      },

      create_view: function(view_cls, options) {
        var options = _.extend({}, options);
        options.parent_view = this;
        var view = new view_cls(options);
        return view;
      },

      add_subview: function(view) {
        view.parent_view = this;
        this._subviews.push(view);
      },

      remove_view: function(view) {
        this._subviews = _.without(this._subviews, view);
      },
      
      hide_subviews: function() {
        _.each(this._subviews, function(view) { 
          view.hide(true); 
        });
      },

      show_subviews: function() {
        _.each(this._subviews, function(view) { 
          view.show(true); 
        });
      },
      
      pre_hide: function() {
        this.rivets_unbind();
        this.remove_handlers();
      },
      
      get_extra_rivet_models: function() {},

      get_rivet_object: function() {
        return this.rivet_object;
      },

      post_hide: function() {
        this.hide_subviews();
        this.trigger("hide");
      },
      
      rivets_init: function() {
        if (!this.rivets_view) { return }
        var rivet_object = this.get_rivet_object();
        rivet_object['view'] = this;
        if (this.el != $("body").get(0)) {
          this.rivets = rivets.bind(this.el, rivet_object);
        } else {
        }
      },
      
      rivets_update: function() {
        if (!this.rivets_view) { return }
        this.rivets.update();
      },

      rivets_bind: function() {
        if (!this.rivets_view) { return }
        if (!this.rivets) { this.rivets_init(); return }
        var rivet_object = this.get_rivet_object();
        rivet_object['view'] = this;
        this.rivets.models = rivet_object;
        //this.rivets.build();
        this.rivets.bind();
      },

      rivets_unbind: function() {
        if (!this.rivets_view) { return }
        this.rivets.unbind();
      },

      pre_show: function() {
        this.set_handlers();
        this.rivets_bind();
        this.show_subviews();
      },
      
      resolve_storage_object: function(id) {
        var result;
        if (this['resolve_' + id + '_storage_object']) {
          return this['resolve_' + id + '_storage_object']();
        }
        result = synnefo.storage[id];
        return result ? result : this.collection
      },
      
      each_storage_handler: function(cb, context) {
        if (!context) { context = this }
        _.each(this.storage_handlers, function(handlers, object_name) {
          _.each(handlers, function(events, handler_name) {
            _.each(events, function(event) {
              object = this.resolve_storage_object(object_name);
              handler = this['handle_' + handler_name];
              if (!handler) {
                throw "Handler " + handler_name + " does not exist";
              }
              if (!object) {
                throw "Storage object " + object_name + " does not exist";
              }
              cb.call(context, object, event, handler);
            }, this);
          }, this);
        }, this);
      },
      
      get_handler: function(id) {
      },

      set_handlers: function() {
        this.each_storage_handler(this.set_handler, this);
      },

      remove_handlers: function() {
        this.each_storage_handler(this.remove_handler, this);
      },
      
      set_handler: function(object, event, handler) {
        object.bind(event, handler);
      },

      remove_handler: function(object, event, handler) {
        object.unbind(event, handler);
      }
    });

    views.ext.PaneView = views.ext.View.extend({
      collection_view_cls: null,
      collection_view_selector: '.collection',
      init: function() {
        var options = {};
        options['el'] = $(this.$(this.collection_view_selector).get(0));
        this.collection_view = this.create_view(this.collection_view_cls, options);
        this.add_subview(this.collection_view);
      },
    });

    views.ext.CollectionView = views.ext.View.extend({
      collection: undefined,
      model_view_cls: undefined,
      animation_speed: 200,

      init: function() {
        var handlers = {};
        handlers[this.collection_name] = {
          'collection_change': ['update', 'sort'],
          'collection_reset': ['reset'],
          'model_change': ['change'],
          'model_add': ['add'],
          'model_remove': ['remove']
        }
        this.storage_handlers = _.extend(handlers, this.storage_handlers)
        this._model_views = {};
        this.list_el = $(this.$(".items-list").get(0));
        this.empty_el = $(this.$(".empty-list").get(0));
        if (this.create_view_cls) {
          this._create_view = new this.create_view_cls();
        }
        this.$(".create-button a").click(_.bind(function(e) {
          e.preventDefault();
          this.handle_create_click();
        }, this));
      },
      
      handle_create_click: function() {
        if (this._create_view) {
          this._create_view.show();
        }
      },

      pre_show: function() {
        views.ext.CollectionView.__super__.pre_show.apply(this, arguments);
        this.update_models();
      },
      
      handle_collection_reset: function() {
        this.update_models();
      },

      handle_model_change: function(model) {
        var el, index, model, parent, view, anim;
        view = this._model_views[model.id];
        if (!view) { return }
        el = view.el;
        parent = this.parent_for_model(model);
        if (!parent.find(el).length) {
          index = this.collection.indexOf(model);
          anim = true;
          this.place_in_parent(parent, el, model, index, anim);
        }
      },

      handle_collection_change: function() {
        this.update_models();
      },

      handle_model_add: function(model, collection, options) {
        this.add_model(model);
      },

      handle_model_remove: function(model, collection, options) {
        this.remove_model(model);
      },
      
      show_empty: function() {
        this.empty_el.show();
      },

      hide_empty: function() {
        this.empty_el.hide();
      },

      check_empty: function() {
        if (this.collection.length == 0) {
          this.show_empty();
          this.list_el.hide();
        } else {
          this.list_el.show();
          this.hide_empty();
        }
      },
      
      parent_for_model: function(model) {
        return this.list_el;
      },
      
      place_in_parent: function(parent, el, m, index, anim) {
        var place_func, place_func_context, position_found;

        _.each(parent.find(".model-item"), function(el) {
          var el = $(el);
          var el_index = el.data('index');
          if (!el_index || position_found) { return };
          if (parseInt(el_index) < index) {
            place_func = el.before;
            place_func_context = el;
            position_found = true;
          }
        });
        
        if (!position_found) {
          place_func = parent.append;
          place_func_context = parent;
        }

        if (anim) {
          var self = this;
          el.fadeOut(this.animation_speed, function() {
            place_func.call(place_func_context, el);
            el.fadeIn(self.animation_speed);
          });
        } else {
          place_func.call(place_func_context, el);
        }
        el.attr("data-index", index);
      },
      
      get_model_view_cls: function(m) {
        return this.model_view_cls
      },

      add_model: function(m, index) {
        // if no available class for model exists, skip model add
        var view_cls = this.get_model_view_cls(m);
        if (!view_cls) { return }
        
        // avoid duplicate entries
        if (this._model_views[m.id]) { return }
        
        // handle empty collection
        this.check_empty();
        
        // initialize view
        var view = this.create_view(this.get_model_view_cls(m), {model: m});
        this.add_model_view(view, m, index);
      },

      add_model_view: function(view, model, index) {
        // append html element to the parent
        var el = view.init_element();
        // append to registry object
        this._model_views[model.id] = view;
        el.addClass("model-item");
        // where to place ?
        var parent = this.parent_for_model(model);
        // append
        this.place_in_parent(parent, el, model, index);
        // make it visible by default
        this.add_subview(view);
        view.show(true);
      },
      
      each_model_view: function(cb, context) {
        if (!context) { context = this };
        _.each(this._model_views, function(view, model_id){
          var model = this.collection.get(model_id);
          cb.call(this, model, view, model_id);
        }, this);
      },

      remove_model: function(m) {
        console.log("REMOVING MODEL", m);
        var model_view = this._model_views[m.id];
        if (!model_view) {
          console.error("no view found");
          return;
        }
        model_view.hide();
        model_view.el.remove();
        this.remove_view(model_view);
        delete this._model_views[m.id];
        this.check_empty();
      },

      update_models: function(m) {
        this.check_empty();
        this.collection.each(function(model, index) {
          if (!(model.id in this._model_views)) {
            this.add_model(model, index);
          } else {
            if (model != this._model_views[model.id].model) {
              this._model_views[model.id].model = model;
              this._model_views[model.id].rivets_unbind();
              this._model_views[model.id].rivets_bind();
            }
            this.handle_model_change(model);
          }
        }, this);
        
        this.each_model_view(function(model, view, model_id){
          if (!model) {
            model = {'id': model_id};
            this.remove_model(model);
          }
        })
      }
    });

    views.ext.ModelView = views.ext.View.extend({
      rivets_view: true,

      initialize: function() {
        views.ext.ModelView.__super__.initialize.apply(this, arguments);
        var actions = this.model.get('actions');
        if (actions) {
          this.init_action_methods(this.model.get('actions'));
          this.bind("hide", function() {
            actions.reset_pending();
          });
        }
      },
      
      set_confirm: function() {},
      unset_confirm: function() {},

      init_action_methods: function(actions) {
        _.each(actions.actions, function(action) {
          var method;
          method = 'set_{0}_confirm'.format(action);
          if (this[method]) { return }
          this[method] = _.bind(function(model, ev) {
            if (ev) { ev.stopPropagation() }
            var data = {};
            this.set_confirm(action);
            this.model.actions.set_pending_action(action);
          }, this);
          method = 'unset_{0}_confirm'.format(action);
          if (this[method]) { return }
          this[method] = _.bind(function(model, ev) {
            if (ev) { ev.stopPropagation() }
            var data = {};
            this.unset_confirm(action);
            this.model.actions.unset_pending_action(action);
          }, this);
        }, this);
      },

      get_rivet_object: function() {
        var model = {
          model: this.model
        }
        return model
      },

      post_init_element: function() {},

      init_element: function() {
        this.el.attr("id", "model-" + this.model.id);
        this.post_init_element();
        this.update_layout();
        return this.el;
      },

      update_layout: function() {}

    });
    
    views.ModelRenameView = views.ext.ModelView.extend({
      tpl: '#rename-view-tpl',
      title_attr: 'name',

      init: function() {
        views.ModelRenameView.__super__.init.apply(this, arguments);
        this.name_cont = this.$(".model-name");
        this.edit_cont = this.$(".edit");

        this.edit_btn = this.$(".edit-btn");
        this.value = this.$(".value");
        this.input = this.$("input");
        this.confirm = this.edit_cont.find(".confirm");
        this.cancel = this.edit_cont.find(".cancel");
        
        if (this.model.get('rename_disabled')) {
          this.edit_btn.remove();
        }

        this.value.dblclick(_.bind(function(e) {
          this.set_edit();
        }, this));
        this.input.bind('keyup', _.bind(function(e) {
          // enter keypress
          if (e.which == 13) { this.rename(); }
          // esc keypress
          if (e.which == 27) { this.unset_edit(); }
        }, this));
        // initial state
        this.unset_edit();
      },
      
      post_hide: function() {
        this.unset_edit();
      },

      set_edit: function() {
        if (this.model.get('rename_disabled')) { return }
        var self = this;
        this.input.val(this.model.get('name'));
        window.setTimeout(function() {
          self.input.focus();
        }, 20);
        this.name_cont.hide();
        this.edit_cont.show();
      },

      unset_edit: function() {
        this.name_cont.show();
        this.edit_cont.hide();
      },

      rename: function() {
        var value = _.trim(this.input.val());
        if (value) {
          this.model.rename(value);
          this.unset_edit();
        }
      }
    });
    
    views.ext.ModelCreateView = views.ext.ModelView.extend({});
    views.ext.ModelEditView = views.ext.ModelCreateView.extend({});

})(this);
