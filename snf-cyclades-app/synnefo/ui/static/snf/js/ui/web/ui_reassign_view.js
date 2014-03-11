// Copyright 2014 GRNET S.A. All rights reserved.
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

    views.ProjectSelectItemView = views.ext.SelectModelView.extend({
      tpl: '#project-select-model-tpl',

      set_current: function() {
        this._is_current = true;
        this.model.trigger('change:_project_is_current');
        $(this.el).addClass("current");
        this.set_enabled();
      },

      unset_current: function() {
        this._is_current = false;
        this.model.trigger('change:_project_is_current');
        $(this.el).removeClass("current");
      },

      is_current_str: function() {
        if (this._is_current) {
          return 'current'
        } else {
          return ''
        }
      },

      quotas_html: function() {
        var data = "<div>";
        _.each(this.options.quotas_keys, function(key) {
          var q = this.model.quotas.get(key);
          if (!q) { return }
          var content = '<span class="resource-key">{0}:</span>';
          content += '<span class="resource-value">{1}</span>';
          data += content.format(q.get('resource').get('display_name'), 
                                 q.get_readable('available'));
        }, this);
        data += "</div>";
        return data;
      }
    });

    views.ProjectSelectView = views.ext.CollectionView.extend({
      initialize: function(options) {
        this.filter_func = options.filter_func || function(m) { return true }
        this.update_disabled = _.bind(this.update_disabled, this);
        views.ProjectSelectView.__super__.initialize.apply(this);
      },

      get_selected: function() {
        var selected = undefined;
        _.each(this._model_views, function(view, id){
          if (view.selected) { selected = view.model }
        });
        return selected;
      },
      
      post_remove_model_view: function(view) {
        view.unbind('click');
      },
      
      update_disabled: function(view) {
        if (this.filter_func) {
          if (!this.filter_func(view.model) && !view._is_current) {
            view.set_disabled();
            view.disabled = true;
          } else {
            view.set_enabled();
            view.disabled = false;
          }
        }
      },
      
      post_add_model_view: function(view, model) {
        this.update_disabled(view);
        view.bind('click', function() {
          if (view.disabled) { return }
          this.deselect_all();
        }, this);
      },
      
      _model_bindings: {},

      bind_custom_view_handlers: function(view, model) {
        var func
        model.quotas.bind('change', _.bind(function() {
          this.update_disabled(view)
        }, this));
      },
      
      unbind_custom_view_handlers: function(view, model) {
        model.quotas.unbind('change');
      },

      deselect_all: function(model) {
        this.collection.each(function(m) {
          var view = this._model_views[m.id];
          //if (view.disabled) { return }
          this._model_views[m.id].deselect();
        }, this);
      },

      set_selected: function(model) {
        this.deselect_all();
        this._model_views[model.id].select();
      },

      set_current: function(model) {
        _.each(this._model_views, function(v) {
          v.unset_current();
        });
        this._model_views[model.id].set_current();
      },

      model_view_options: function(model) {
        return {'quotas_keys': this.options.quotas_keys};
      },

      tpl: '#project-select-collection-tpl',
      model_view_cls: views.ProjectSelectItemView
    });
    
    views.ModelReassignView = views.Overlay.extend({
        title: "Reassign machine",
        overlay_id: "overlay-select-projects",
        content_selector: "#project-select-content",
        css_class: "overlay-info",
        can_fit_func: function(project) { 
          return project.quotas.can_fit(this.model_usage)
        },

        initialize: function(options) {
            views.ModelReassignView.__super__.initialize.apply(this);
            this.list = this.$(".projects-list ul");
            this.empty_message = this.$(".empty-message");
            this.submit_button = this.$(".form-action.submit");
            this.in_progress = false;
            this.init_handlers();
          
            this.$(".description").text(this.description || "");
            if (this.collection) { this.init_collection_view(this.collection) }
        },
        
        init_collection_view: function(collection) {
            if (this.collection_view) { this.collection_view.destroy() }
            this.collection_view = new views.ProjectSelectView({
              collection: collection,
              el: this.list,
              filter_func: _.bind(this.can_fit_func, this),
              quotas_keys: this.resources
            });
            this.collection_view.show(true);
            this.collection_view.set_current(this.model.get('project'));
            this.collection_view.set_selected(this.model.get('project'));
            this.list.append($(this.collection_view.el));
        },

        init_handlers: function() {
          this.submit_button.bind('click', _.bind(this.submit, this));
        },

        submit: function() {
          if (this.in_progress) { return }
          var project = this.collection_view.get_selected();
          if (project.id == this.model.get('project').id) {
            this.hide();
          }
          var complete = _.bind(function() {
            this.submit_button.removeClass("in-progress");
            this.in_progress = false;
            synnefo.storage.projects.delay_fetch(2000);
            this.hide();
          }, this);
          this.assign_to_project(this.model, project, complete, complete);
          this.submit_button.addClass("in-progress");
          this.in_progress = true;
        },
        
        update_model_details: function() {
          this.set_subtitle(this.model.get('name'));
        },

        show: function(model) {
          this.model = model;
          this.init_collection_view(synnefo.storage.projects);
          views.ModelReassignView.__super__.show.call(this);
          this.update_model_details();
        },

        onClose: function() {
          if (this.collection_view) {
            this.collection_view.destroy();
          }
          delete this.collection_view;
        }
    });

    views.VmReassignView = views.ModelReassignView.extend({
      title: 'Set machine project',
      description: 'Select project assign machine to',
      resources: ['cyclades.vm', 'cyclades.ram', 
                  'cyclades.cpu', 'cyclades.disk'],
      model_usage: {},
      can_fit_func: function(project) {
          var quotas = this.model.get_flavor().quotas();
          return project.quotas.can_fit(quotas);
      },
      
      update_model_details: function() {
          var name = _.escape(synnefo.util.truncate(this.model.get("name"), 70));
          this.set_subtitle(name + snf.ui.helpers.vm_icon_tag(this.model, "small"));

          var el = $("<div></div>");
          var cont = $(this.el).find(".model-usage");
          cont.hide();
          cont.empty().append(el);
          
          var flavor = this.model.get_flavor();
          _.each(['ram', 'disk', 'cpu'], function(key) {
            el.append($('<span class="key">' + key + '</span>'));
            el.append($('<span class="val">' + flavor.get_readable(key) + '</span>'));
          });
      },

      assign_to_project: function(model, project, complete, fail) {
        model.call("reassign", complete, fail, {project_id: project.id});
      }
    });

    views.IPReassignView = views.ModelReassignView.extend({
      title: 'Set IP address project',
      description: 'Select project to assign IP address to',
      resources: ['cyclades.floating_ip'],
      model_usage: {'cyclades.floating_ip': 1},
      assign_to_project: function(model, project, complete, fail) {
        this.model.reassign_to_project(project, complete, complete);
      }
    });

    views.NetworkReassignView = views.ModelReassignView.extend({
      title: 'Set private network project',
      resources: ['cyclades.network.private'],
      description: 'Select project to assign private network to',
      model_usage: {'cyclades.network.private': 1},
      assign_to_project: function(model, project, complete, fail) {
        this.model.reassign_to_project(project, complete, complete);
      }
    });

})(this);
