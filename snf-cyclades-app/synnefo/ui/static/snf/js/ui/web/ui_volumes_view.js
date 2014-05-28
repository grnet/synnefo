// Copyright (C) 2010-2014 GRNET S.A.
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.
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
    
    
    var min_volume_quota = {
      'cyclades.disk': 1
    };
    
    views.CreateVolumeSelectProjectView = 
        views.CreateVMSelectProjectView.extend({
            tpl: '#create-view-projects-select-tpl',
            required_quota: function() {
                var size = 1;
                var img = this.parent_view.parent.steps[1].selected_image;
                if (img) {
                    size = img.get("size");
                }
                return {'cyclades.disk': size}
            },
            model_view_cls: views.CreateVMSelectProjectItemView.extend({
                display_quota: min_volume_quota
            })
        });
    
    views.CreateVolumeImageStepView = views.CreateImageSelectView.extend({
        step: 1,

        get_available_projects_for_disk_size: function(size) {
            var check = function(p) {
                var q = p.quotas.get('cyclades.disk');
                if (!q) { return false }
                return q.get('available') >= size;
            }
            return synnefo.storage.projects.filter(check)
        },

        validate: function() {
            if (!this.selected_image) {
                this.parent.$(".form-action.next").hide();
            } else {
                if (this.get_available_projects_for_disk_size(
                    this.selected_image.get("size")).length > 0) {
                        this.parent.$(".form-action.next").show();
                        this.parent.$(".no-project-notice").hide();
                } else {
                        this.parent.$(".form-action.next").hide();
                        this.parent.$(".no-project-notice").show();
                }

            }
        }
    });

    views.CreateVolumeDetailsStepView = views.CreateWizardStepView.extend({
        step: 2,
        
        new_volume_title: "New disk",

        initialize: function() {
            views.CreateVolumeDetailsStepView.__super__.initialize.apply(
                this, arguments);
            this.parent.bind("image:change", 
                             _.bind(this.handle_image_change, this));
            this.parent.bind("project:change", 
                             _.bind(this.handle_project_change, this));
            this.projects_list = this.$(".project-select");
            this.project_select_view = undefined;


            this.size_input = this.el.find(".size-slider");
            this.size_input.bind("keyup", _.bind(function() {
                window.setTimeout(_.bind(function() {
                    var value = this.size_input.val();
                    if (parseInt(value)) {
                        this.size_input.simpleSlider("setValue", value);
                    }
                }, this), 200);
            }, this));
            this.size_input.simpleSlider(this.slider_settings);

            this.desc_input = this.$(".volume-description");
            this.name_input = this.$(".volume-name");
            this.name_changed = false;
            this.name_input.bind("keypup", _.bind(function() {
                this.name_changed = true;
            }));
        },

        slider_settings: {
            range: [1, 1000],
            theme: 'volume-size',
            step: 1
        },

        set_slider_max: function(val) {
            this.size_input.simpleSlider("setMax", val);
        },

        set_slider_min: function(val) {
            if (val < 1) { val = 1 }
            this.size_input.simpleSlider("setMin", val);
        },
        
        reset: function() {
            this.name_changed = false;
            this.name_input.val(this.new_volume_title);
            this.desc_input.val('');
        },
        
        vm_filter: function(m) {
            return m.can_attach_volume();
        },

        disabled_filter_ext: function(m) {
            var check = !m.can_attach_volume() || !m.is_ext();
            if (check) {
                return "You cannot attach non empty disk to this machine."
            }
            return false;
        },

        disabled_filter: function(m) {
            return !m.can_attach_volume();
        },

        init_subviews: function() {
          if (!this.vm_select_view) {

            this.vms_collection = new Backbone.FilteredCollection(undefined, {
              collection: synnefo.storage.vms,
              collectionFilter: this.vm_filter
            });

            this.vm_select_view = new views.VMSelectView({
              collection: this.vms_collection, 
              container: this.$(".vms-list"),
              parent: this,
              allow_multiple: false,
              allow_empty: false
            });
            this.vm_select_view.max_title_length = 38;
            this.vm_select_view.show(true);
          }

          if (!this.project_select_view) {
            var view_cls = views.CreateVolumeSelectProjectView;
            this.project_select_view = new view_cls({
              container: this.projects_list,
              collection: synnefo.storage.joined_projects,
              parent_view: this
            });

            this.project_select_view.show(true);
          }

          this.vm_select_view.bind("deselect", 
                                _.bind(this.handle_vm_select, this));
          this.vm_select_view.bind("change", 
                                _.bind(this.handle_vm_select, this));
          this.project_select_view.bind("change", 
                                _.bind(this.handle_project_select, this));
          this.project_select_view.set_current(this.parent.project);
          this.handle_project_select(this.parent.project);
        },

        hide_step: function() {
          this.project_select_view && this.project_select_view.hide(true);
          this.vm_select_view && this.vm_select_view.hide(true);
        },
        
        hide: function() {
          this.vm_select_view.unbind("deselect");
          this.vm_select_view.unbind("change");
          this.project_select_view.unbind("change");
        },

        update_layout: function() {
        },
        
        handle_vm_select: function() {
            this.parent.submit_btn.show();
        },

        handle_project_select: function(projects) {
          if (!projects.length ) { return }
          var project = projects[0];
          this.parent.set_project(project);
        },

        handle_project_change: function() {
            if (!this.parent.project) { return }
            var available = 
                this.parent.project.quotas.get("cyclades.disk")
                .get("available");

            available = available / Math.pow(1024, 3);
            this.set_slider_max(parseInt(available));
            this.update_layout();
        },

        handle_image_change: function(image) {
            if (!this.parent.project) { return }
            this.current_image = image;
            var size = image ? image.get("size") : 1;
            this.set_slider_min(size / Math.pow(1024, 3));
            this.update_layout();
        },
            
        reset_slider: function() {
            this.size_input.simpleSlider("setRatio", 0);
        },
        
        get: function() {
            return {
                'name': _.trim(this.name_input.val()) || this.new_volume_title,
                'description': _.trim(this.desc_input.val()) || "",
                'size': parseInt(this.size_input.val()) || 1,
                'vm': this.vm_select_view.get_selected()[0],
                'project': this.parent.project
            }
        },
        
        select_available_project: function() {
          var img_view = this.parent.steps[1];
          var img = img_view.selected_image;
          var size = 1 * Math.pow(1024, 3);
          if (img) { img.get('size') }
          var projects = img_view.get_available_projects_for_disk_size(size);
          if (!projects.length) { return }
          this.project_select_view.set_current(projects[0]);
        },
        
        update_image_name: function() {
          var img_view = this.parent.steps[1];
          var img = img_view.selected_image;
          var name = "Empty disk";
          if (img) {
              name = img.get("name");
          }
          this.$(".volume-image").text(snf.util.truncate(name, 34));
        },
        
        update_vms_filter: function() {
            var img_view = this.parent.steps[1];
            var img = img_view.selected_image;

            if (img) {
                this.vm_select_view.disabled_filter = this.disabled_filter_ext;
            } else {
                this.vm_select_view.disabled_filter = this.disabled_filter;
            }
            this.vm_select_view.update_disabled();
        },

        update_volume_details: function() {
            var img = this.parent.steps[1].selected_image;
            if (!this.name_changed) {
                if (img) {
                    this.name_input.val(img.get('name') + ' volume');
                    this.desc_input.val(img.get('description'));
                } else {
                    this.name_input.val(this.new_volume_title);
                    this.desc_input.val('');
                }
            }
        },
        
        validate_vms: function() {
            if (this.vm_select_view.get_selected().length == 0) {
                this.parent.submit_btn.hide();
            } else {
                this.parent.submit_btn.show();
            }
        },

        show: function() {
          var args = _.toArray(arguments);
          this.init_subviews();
          this.project_select_view.show(true);
          this.select_available_project();
          this.vm_select_view.show(true);
          this.update_vms_filter();
          window.setTimeout(_.bind(function() {
            this.name_input.select();
          }, this), 50);
          this.update_image_name();
          this.update_volume_details();
          this.reset_slider();
          this.validate_vms();
          views.CreateVolumeDetailsStepView.__super__.show.call(this, args);
        },
    });

    views.VolumeCreateView = views.VMCreateView.extend({
        view_id: "create_volume_view",
        content_selector: "#createvolume-overlay-content",
        title: "Create new disk",
        
        setup_step_views: function() {
            this.steps[1] = new views.CreateVolumeImageStepView(this);
            this.steps[1].default_type = undefined;
            this.steps[1].bind("change", _.bind(function(data) {
                this.trigger("image:change", data)
            }, this));
            this.steps[2] = new views.CreateVolumeDetailsStepView(this);
            this.no_source_button = this.el.find(".empty-volume");
            this.no_source_button.click(_.bind(function() {
                this.steps[1].selected_image = undefined;
                this.steps[2].set_slider_min(1);
                this.set_step(2);
                this.update_layout();
            }, this));
        },
        
        show_step: function(step) {
            views.VolumeCreateView.__super__.show_step.call(this, step);
            if (step > 1) {
                this.no_source_button.hide();
            } else {
                this.no_source_button.show();
            }
        },
        
        validate: function() { return true },

        submit: function() {
            if (this.submiting) { return };
            var self = this;
            var data = this.get_params();
            var meta = {};
            var extra = {};

            if (this.validate(data)) {
                this.submit_btn.addClass("in-progress");
                this.submiting = true;
                storage.volumes.create(
                    data.name, data.size, data.vm, data.project, data.image,
                    data.description, {}, 
                    _.bind(function(data) {
                      window.setTimeout(function() {
                        self.submiting = false;
                        self.close_all();
                      }, 1000);
                    }, this));
            }
        },
    });

    views.VolumeView = views.ext.ModelView.extend({
        
      init: function() {
          views.VolumeView.__super__.init.apply(this, arguments);
          this.desc_toggle = this.$(".cont-toggler.desc");
          this.desc_toggle.bind("click", _.bind(this.toggle_desc, this));
          this.desc_content = this.$(".content-cont");
          this.desc_actions = this.$(".content-cont .rename-actions");
          this.desc_save = this.$(".content-cont .btn.confirm");
          this.desc_reset = this.$(".content-cont .btn.cancel");
          this.desc_text = this.$(".content-cont textarea");
          this.desc_edit_btn = this.$(".content-cont .edit-btn");
          this.desc_content.hide();
          
          var self = this;
          this.desc_save.unbind('click').bind('click', function() {
              self.update_description();
          });
          this.desc_reset.unbind('click').bind('click', function() {
              self.reset_description();
              self.disable_desc_edit();
          });
          this.desc_text.bind('dblclick', function() {
              if (self.desc_editing) { retrun }
              self.enable_desc_edit();
          });
          this.desc_edit_btn.bind('click', function() {
              if (self.desc_editing) { retrun }
              self.enable_desc_edit();
          });

          this.reset_description();
          this.disable_desc_edit();
      },
      
      reset_description: function() {
          var desc = this.model.get('display_description');
          this.desc_text.val(desc || "No description");
      },

      update_description: function() {
          var desc = this.desc_text.val();
          this.model.update_description(desc);
          this.disable_desc_edit();
          this.toggle_desc();
      },

      enable_desc_edit: function() {
          this.desc_edit_btn.hide();
          this.desc_text.attr("readonly", false);
          this.desc_text.removeClass("readonly");
          this.desc_text.focus();
          this.desc_actions.show();
          this.desc_editing = true;
      },

      disable_desc_edit: function() {
          this.desc_edit_btn.show();
          this.desc_text.attr("readonly", true);
          this.desc_text.addClass("readonly");
          this.desc_actions.hide();
          this.desc_editing = false;
      },

      toggle_desc: function() {
        this.reset_description();
        this.disable_desc_edit();

          if (this.desc_toggle.hasClass("open")) {
              this.desc_toggle.removeClass("open");
              this.el.removeClass("light-background");
          } else {
              this.desc_toggle.addClass("open");
              this.el.addClass("light-background");
          }
          this.desc_content.slideToggle({
              step: function() {
                  $(window).trigger("resize");
              }
          });
      },

      display_name: function() {
        if (!this.model.get('display_name')) {
          var vm = this.model.get('vm');
          if (vm) { return vm.get('name') + ' disk'};
        }
        return this.model.get('name');
      },

      status_map: {
        'in_use': 'Attached',
        'error': 'Error',
        'deleting': 'Destroying...',
        'creating': 'Building...'
      },

      status_cls_map: {
        'in_use': 'status-active',
        'error': 'status-error',
        'deleting': 'status-progress destroying-state',
        'creating': 'status-progress build-state'
      },

      tpl: '#volume-view-tpl',
        
      size_display: function() {
          var size = this.model.get('size');
          size = size * Math.pow(1024, 3);
          var display = snf.util.readablizeBytes(size);
          display = display.replace(" ", "").replace(".00", "");
          return display;
      },

      show_reassign_view: function() {
          if (this.model.get('is_root')) { return }
          synnefo.ui.main.volume_reassign_view.show(this.model);
      },

      status_cls: function() {
        return this.status_cls_map[this.model.get('status')];
      },

      status_display: function(v) {
        return this.status_map[this.model.get('status')];
      },
      
      model_icon: function() {
        var img = 'volume-icon-detached.png';
        var src = synnefo.config.images_url + '{0}';
        if (this.model.get('port_id')) {
          img = 'volume-icon.png';
        }
        return src.format(img);
      },

      show_snapshot_create_overlay: function() {
        var vm = this.model.get('vm');
        if (!vm) { return }
        synnefo.ui.main.create_snapshot_view.show(vm, this.model);
      },

      remove: function(model, e) {
        e && e.stopPropagation();
        this.model.do_destroy();
      }
    });

    views.VolumesCollectionView = views.ext.CollectionView.extend({
      collection: storage.volumes,
      collection_name: 'volumes',
      model_view_cls: views.VolumeView,
      create_view_cls: views.VolumeCreateView,
      quota_key: 'volume',
      parent_for_model: function(m) {
        if (m.get('is_root')) {
          return this.list_el.find(".system");
        } else {
          return this.list_el.find(".custom");
        }
      }    
    });

    views.VolumesPaneView = views.ext.PaneView.extend({
      id: "pane",
      el: '#volumes-pane',
      collection_view_cls: views.VolumesCollectionView,
      collection_view_selector: '#volumes-list-view'
    });

    views.VolumeVmView = views.ext.ModelView.extend({
      tpl: '#volume-vm-view-tpl',
      os_icon: function() {
          var data = '<img src="{0}" />';
          return data.format(synnefo.ui.helpers.vm_icon_path(this.model));
      }
    });

    views.SnapshotCreateView = views.Overlay.extend({
        view_id: "snapshot_create_view",
        content_selector: "#snapshot-create-content",
        css_class: 'overlay-snapshot-create overlay-info',
        overlay_id: "snapshot-create-overlay",

        title: "Create new snapshot",
        subtitle: "Machines",

        initialize: function(options) {
            views.SnapshotCreateView.__super__.initialize.apply(this);

            this.create_button = this.$("form .form-action.create");
            this.text = this.$(".snapshot-create-name");
            this.description = this.$(".snapshot-create-desc");
            this.form = this.$("form");
            this.success = this.$("p.success");
            this.done_button = this.$(".form-action.btn-close");
            this.init_handlers();
            this.creating = false;
        },
        
        show: function(vm, volume) {
          this.vm = vm;
          this.volume = volume || null;
          this.reset_success();
          views.SnapshotCreateView.__super__.show.apply(this);
        },

        init_handlers: function() {
            this.done_button.click(_.bind(function(e){
                e.preventDefault();
                this.hide();
            }, this));

            this.create_button.click(_.bind(function(e){
                this.submit();
            }, this));

            this.form.submit(_.bind(function(e){
                e.preventDefault();
                this.submit();
                return false;
            }, this))

            this.text.keypress(_.bind(function(e){
                if (e.which == 13) {this.submit()};
            },this))
        },

        submit: function() {
            if (this.validate()) {
                this.create();
            };
        },
        
        validate: function() {
            // sanitazie
            var t = this.text.val();
            t = t.replace(/^\s+|\s+$/g,"");
            this.text.val(t);

            if (this.text.val() == "") {
                this.text.closest(".form-field").addClass("error");
                this.text.focus();
                return false;
            } else {
                this.text.closest(".form-field").removeClass("error");
            }
            return true;
        },

        show_success: function() {
            this.success.show();
            this.$(".col-fields").hide();
            this.create_button.hide();
            this.done_button.show();
        },

        reset_success: function() {
            this.success.hide();
            this.$(".col-fields").show();
            this.create_button.show();
            this.done_button.hide();
        },
        
        create: function() {
            if (this.creating) { return }
            this.create_button.addClass("in-progress");

            var name = this.text.val();
            var desc = this.description.val();
            
            this.creating = true;
            this.vm.create_snapshot({
                display_name: name, 
                display_description: desc
            }, _.bind(function() {
              this.creating = false;
              this.show_success();
            }, this), _.bind(function() {
                this.creating = false;
            }, this));
        },
        
        _default_values: function() {
          var d = new Date();
          var vmname = this.vm.get('name');
          var vmid = this.vm.id;
          var index = this.volume.get_index();
          var id = this.vm.id;
          var vname = this.volume.get('display_name');
          var vid = this.volume.get('id');
          var trunc = snf.util.truncate;

          var date = '{0}-{1}-{2} {3}:{4}:{5}'.format(
            d.getFullYear(), d.getMonth()+1, d.getDate(), d.getHours(), 
            d.getMinutes(), d.getSeconds());
            
          var trunc_len = 40;
          var sname = trunc(vname, trunc_len);
          if (index == 0) {
              sname = trunc(vmname, trunc_len);
          }

          var name = "'{0}' snapshot".format(sname);
          name += " {0}".format(date);
          name = snf.util.truncate(name, 120);

          var description = "Volume id: {0}".format(vid);
          description += "\n" + "Volume name: {0}".format(vname);
          description += "\n" + "Volume index: {0}".format(index);
          description += "\n" + "Server id: {0}".format(vmid);
          description += "\n" + "Server name: {0}".format(vmname);
          description += "\n" + "Timestamp: {0}".format(d.toJSON());

          return {
            'name': name,
            'description': description
          }
        },

        beforeOpen: function() {
            this.create_button.removeClass("in-progress")
            this.text.closest(".form-field").removeClass("error");
            var defaults = this._default_values();

            this.text.val(defaults.name);
            this.description.val(defaults.description);
            this.text.show();
            this.text.focus();
            this.description.show();
        },

        onOpen: function() {
            this.text.focus();
        }
    });

    views.VolumeItemRenameView = views.ModelRenameView.extend({
        title_attr: 'display_name'
    });

})(this);
