// Copyright (C) 2010-2015 GRNET S.A. and individual contributors
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
    
    views.ext.VM_STATUS_CLS_MAP = {
        'UNKNOWN':          ['status-unknown'],
        'BUILD':            ['build-state status-progress'],
        'REBOOT':           ['status-progress reboot-state'],
        'STOPPED':          ['status-terminated'],
        'ACTIVE':           ['status-active'],
        'ERROR':            ['status-error'],
        'DELETED':          ['destroying-state'],
        'DESTROY':          ['destroying-state'],
        'SHUTDOWN':         ['shutting-state'],
        'START':            ['starting-state'],
        'CONNECT':          ['connecting-state'],
        'DETACH_VOLUME':    ['disconnecting-state'],
        'ATTACH_VOLUME':    ['connecting-state'],
        'DISCONNECT':       ['disconnecting-state'],
        'RESIZE':           ['rebooting-state']
    };

    views.CreateVolumeSelectProjectView = 
        views.CreateVMSelectProjectView.extend({
            tpl: '#create-view-projects-select-tpl',
            required_quota: function() {
                var size = Math.pow(1024, 3);
                var img = this.parent_view.parent.steps[1].selected_image;

                if (img && !img.id == "empty-disk") {
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
            
        default_type: 'empty',
        type_selections: {},
        type_selections_order: [],

        initialize: function() {
            views.CreateVolumeImageStepView.__super__.initialize.apply(this, arguments);
            this.$(".other-types-cont").removeClass("hidden");

            this.empty_image = new synnefo.glance.models.GlanceImage();
            this.empty_image.set({
                id: "empty-disk",
                name: "Empty disk",
                size: 0,
                description: "Empty disk"
            });
            this.create_types_selection_options();
            this.create_snapshot_types_selection_options();
        },
        
        get_image_icon_tag: function(image) {
            if (image.get("id") == "empty-disk") {
                var url = snf.config.images_url + "volume-icon-small.png";
                return '<img src="{0}" />'.format(url);
            }
            return views.CreateVolumeImageStepView.__super__.get_image_icon_tag.call(this, image);
        },

        display_warning_for_image: function(image) {
          if (image && !image.is_system_image() && 
              !image.owned_by(synnefo.user) && image.get("id") != "empty-disk") {
            this.parent.el.find(".image-warning").show();
            this.parent.el.find(".create-controls").hide();
          } else {
            this.parent.el.find(".image-warning").hide();
            this.parent.el.find(".create-controls").show();
          }
        },

        update_images: function(images) {
            if (this.selected_type == "empty") {
                this.images = [this.empty_image];
                this.images_ids = [this.empty_image.get("id")];
                return this.images;
            }
            return views.CreateVolumeImageStepView.__super__.update_images.call(this, images);
        },

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

    views.CreateVolumeProjectStepView = views.CreateWizardStepView.extend({
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
                    if (!parseInt(value)) { 
                        value = this.min_size; 
                        this.size_input.val(value);
                    }
                    if (parseInt(value)) {
                        this.size_input.simpleSlider("setValue", value);
                    }
                }, this), 50);
            }, this));
            this.size_input.simpleSlider(this.slider_settings);
            this.min_size = 1;
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
        
        init_subviews: function() {
          if (!this.project_select_view) {
            var view_cls = views.CreateVolumeSelectProjectView;
            this.project_select_view = new view_cls({
              container: this.projects_list,
              collection: synnefo.storage.joined_projects,
              parent_view: this
            });

            this.project_select_view.show(true);
          }

          this.project_select_view.bind("change", 
                                _.bind(this.handle_project_select, this));
          
          this.project_select_view.set_current(this.parent.project);
          this.handle_project_select(this.parent.project);
        },

        hide_step: function() {
          window.setTimeout(_.bind(function() {
              this.project_select_view && this.project_select_view.hide(true);
          }, this), 50);
        },
        
        hide: function() {
          this.project_select_view.unbind("change");
          this.project_select_view && this.project_select_view.hide(true);
          views.CreateVolumeProjectStepView.__super__.hide.apply(this, arguments);
        },

        update_layout: function() {
        },
        
        handle_project_select: function(projects) {
          if (!projects.length ) { return }
          var project = projects[0];
          this.parent.set_project(project);
        },

        handle_project_change: function() {
            if (!this.parent.project) { return }
            var disk = this.parent.project.quotas.get("cyclades.disk");
            var available = disk.get("available");
            var max_size = synnefo.config.volume_max_size;
            available = available / Math.pow(1024, 3);
            if (disk.infinite()) {
                available = max_size;
            }
            if (available > max_size) { available = max_size; }
            this.set_slider_max(parseInt(available));
            this.update_layout();
        },

        handle_image_change: function(image) {
            if (!this.parent.project) { return }
            this.current_image = image;
            var size = image ? image.get("size") : 1;
            size = size / Math.pow(1024, 3);
            if (size > parseInt(size)) {
                size = parseInt(size) + 1;
            }
            this.set_slider_min(size);
            this.min_size = size || 1;
            this.update_layout();
        },
            
        reset_slider: function() {
            this.size_input.simpleSlider("setRatio", 0);
        },
        
        select_available_project: function() {
          var img_view = this.parent.steps[1];
          var img = img_view.selected_image;
          var size = 1 * Math.pow(1024, 3);
          if (img) { size = img.get('size'); }
          var current = this.parent.project;
          if (current.quotas.can_fit({'cyclades.disk': size})) { return }
          var projects = img_view.get_available_projects_for_disk_size(size);
          if (!projects.length) { return }
          this.project_select_view.set_current(projects[0]);
        },
        
        show: function() {
          var args = _.toArray(arguments);
          this.init_subviews();
          this.project_select_view.show(true);
          this.select_available_project();
          this.reset_slider();
          views.CreateVolumeProjectStepView.__super__.show.apply(this, arguments);
        },

        get: function() {
            return {
                'project': this.parent.project,
                'size': parseInt(this.size_input.val()) || 1
            }
        }
    });

    views.CreateVolumeMachineStepView = views.CreateWizardStepView.extend({
        step: 3,
        initialize: function() {
            views.CreateVolumeMachineStepView.__super__.initialize.apply(
                this, arguments);
            this.vm_select_view = undefined;
        },

        update_layout: function() {
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

          this.vm_select_view.bind("deselect", 
                                _.bind(this.handle_vm_select, this));
          this.vm_select_view.bind("change", 
                                _.bind(this.handle_vm_select, this));
          this.vm_select_view.bind("change:select", 
                                _.bind(this.handle_vm_select, this));
        },

        vm_filter: function(m) {
            return m.can_attach_volume();
        },

        disabled_filter_ext: function(m) {
            var check = !m.can_attach_volume() || !m.is_ext();
            if (check) {
                return "You can only attach an empty disk to this machine."
            }
            return false;
        },

        disabled_filter: function(m) {
            return !m.can_attach_volume();
        },

        handle_vm_select: function() {
            if (this.vm_select_view && this.vm_select_view.get_selected().length) {
                this.parent.next_btn.show();
            } else {
                this.parent.next_btn.hide();
            }
        },

        validate_vms: function() {
            if (this.vm_select_view.get_selected().length == 0) {
                this.parent.next_btn.hide();
            } else {
                this.parent.next_btn.show();
            }
        },

        update_vms_filter: function() {
            var img_view = this.parent.steps[1];
            var img = img_view.selected_image;
            
            if (img && img.id != "empty-disk") {
                this.vm_select_view.disabled_filter = this.disabled_filter_ext;
            } else {
                this.vm_select_view.disabled_filter = this.disabled_filter;
            }
            this.vm_select_view.update_disabled();
        },

        reset: function() {
        },
        
        hide_step: function() {
          window.setTimeout(_.bind(function() {
              this.vm_select_view && this.vm_select_view.hide(true);
          }, this), 200);
        },

        hide: function() {
          this.vm_select_view.unbind("deselect");
          this.vm_select_view.unbind("change");
          views.CreateVolumeMachineStepView.__super__.hide.apply(this, arguments);
        },

        show: function() {
          var args = _.toArray(arguments);
          this.init_subviews();
          this.validate_vms();
          this.vm_select_view.show(true);
          this.update_vms_filter();
          views.CreateVolumeMachineStepView.__super__.show.apply(this, arguments);
        },

        get: function() {
            return {
                'vm': this.vm_select_view.get_selected()[0]
            }
        }

    });

    views.CreateVolumeDetailsStepView = views.CreateWizardStepView.extend({
        step: 4,
        initialize: function() {
            views.CreateVolumeDetailsStepView.__super__.initialize.apply(
                this, arguments);
            this.desc_input = this.$(".volume-info");
            this.name_input = this.$(".volume-name");
            this.name_changed = false;
            this.desc_changed = false;
            this.name_input.keyup( _.bind(function() {
                this.name_changed = true;
            }, this));
            this.desc_input.keyup(_.bind(function() {
                this.desc_changed = true;
            }, this));
        },

        update_volume_details: function() {
            var img = this.parent.steps[1].selected_image;
            if (!this.name_changed && !this.desc_changed) {
                if (img) {
                    this.name_input.val(img.get('name') + ' volume');
                    this.desc_input.val(img.get('description'));
                } else {
                    this.name_input.val(this.new_volume_title);
                    this.desc_input.val('');
                }
            }
        },
        
        update_layout: function() {
        },
        
        reset: function() {
          this.name_changed = false;
          this.desc_changed = false;
          this.name_input.val(this.new_volume_title);
          this.desc_input.val('');
        },

        show: function() {
          this.update_volume_details();
          window.setTimeout(_.bind(function() {
            this.name_input.select();
          }, this), 50);
          views.CreateVolumeDetailsStepView.__super__.show.apply(this, arguments);
        },

        get: function() {
            return {
                'name': _.trim(this.name_input.val()) || this.new_volume_title,
                'description': _.trim(this.desc_input.val()) || ""
            }
        }
    });

    views.CreateVolumeConfirmStepView = views.CreateWizardStepView.extend({
        step: 5,
        update_layout: function() {
          var params = this.parent.get_params();
          var image_name = "Empty disk"
          if (params.image) {
              image_name = params.image.get("name");
          }
          this.$(".image-name").text(snf.util.truncate(image_name, 44));
          
          var project_name = params.project.get("name");
          this.$(".project-name").text(snf.util.truncate(project_name, 44));

          var name = params.name;
          this.$(".volume-name").text(snf.util.truncate(name, 54));

          var desc = params.description;
          this.$(".volume-info").text(desc);

          var vm= params.vm;
          this.$(".volume-machine").text(snf.util.truncate(vm.get("name"), 44));

          var size = params.size;
          this.$(".volume-size").text(size + " GB");
        },

        get: function() { return {} }
    });

    views.VolumeCreateView = views.VMCreateView.extend({
        view_id: "create_volume_view",
        content_selector: "#createvolume-overlay-content",
        title: "Create new disk",
        min_quota: min_volume_quota,
        
        setup_step_views: function() {
            this.steps[1] = new views.CreateVolumeImageStepView(this);
            this.steps[1].bind("change", _.bind(function(data) {
                this.trigger("image:change", data)
            }, this));
            this.steps[2] = new views.CreateVolumeProjectStepView(this);
            this.steps[3] = new views.CreateVolumeMachineStepView(this);
            this.steps[4] = new views.CreateVolumeDetailsStepView(this);
            this.steps[5] = new views.CreateVolumeConfirmStepView(this);
        },
        
        show_step: function(step) {
            views.VolumeCreateView.__super__.show_step.call(this, step);
        },
        
        validate: function() { return true },

        onClose: function() {
          this.current_view && this.current_view.hide && this.current_view.hide(true);
        },

        submit: function() {
            if (this.submiting) { return };
            var self = this;
            var data = this.get_params();
            var meta = {};
            var extra = {};

            if (this.validate(data)) {
                this.submit_btn.addClass("in-progress");
                this.submiting = true;
                if (data.image.get("id") == "empty-disk") {
                    data.image = undefined;
                }
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
        }
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
              if (self.desc_editing) { return }
              self.enable_desc_edit();
          });
          this.desc_edit_btn.bind('click', function() {
              if (self.desc_editing) { return }
              self.enable_desc_edit();
          });

          this.reset_description();
          this.disable_desc_edit();
      },
      
      reset_description: function() {
          var desc = this.model.get('display_description');
          this.desc_text.val(desc || "No info set");
      },

      update_description: function() {
          var desc = this.desc_text.val();
          this.model.update_description(desc);
          this.disable_desc_edit();
          this.toggle_desc();
      },

      enable_desc_edit: function() {
          this.desc_edit_btn.addClass("hidden");
          this.desc_text.attr("readonly", false);
          this.desc_text.removeClass("readonly");
          this.desc_text.focus();
          this.desc_actions.show();
          this.desc_editing = true;
      },

      disable_desc_edit: function() {
          this.desc_edit_btn.removeClass("hidden");
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

      check_can_reassign: function() {
          var action = this.$(".project-name");
          if (this.model.get("is_root") && !this.model.get("is_ghost")) {
              snf.util.set_tooltip(action, "You cannot change the project of boot disks.<br>Boot disks are assigned to the same project as the parent VM.", {tipClass:"tooltip warning"});
              return "project-name-cont disabled";
          } else {
              snf.util.unset_tooltip(action);
              return "project-name-cont";
          }
      },

      status_cls: function() { var status = this.model.get('status'); var vm =
          this.model.get("vm"); if (status == "in_use" && vm) {
            return snf.views.ext.VM_STATUS_CLS_MAP[vm.state()].join(" ");
          } else {
            return this.status_cls_map[this.model.get('status')];
          }
      },

      status_display: function(v) {
        var vm_status = "";
        var volume_status = this.model.get('status');
        var volume_status_disp = this.status_map[volume_status];
        if (this.model.get('vm')) {
            vm_status = STATE_TEXTS[this.model.get('vm').state()] || "";
        }
        if (!vm_status || volume_status != "in_use") { 
            return volume_status_disp; 
        }
        return volume_status_disp + " - " + vm_status;
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

      check_empty: function() {
        views.VolumesCollectionView.__super__.check_empty.apply(this, arguments);
        if (this.collection.filter(function(n){ return !n.get('is_root')}).length == 0) {
          this.list_el.find(".custom").hide();  
        } else {
          this.list_el.find(".custom").show();  
        }
      },

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
      },

      flavor_tpl: function() {
        var vm = this.model.get("vm");
        var flavor = vm && vm.get_flavor();
        var tpl = flavor && flavor.get("disk_template");
        var map = synnefo.config.flavors_disk_templates_info;
        if (tpl in map) {
            tpl = map[tpl].name || tpl;
        }
        return tpl ? '- <span class="disk-template">' + tpl + '</span>' : '';
      },

      vm_status_cls: function(vm) {
        var cls = 'inner clearfix main-content';
        if (!this.model.get('vm')) { return cls }
        if (this.model.get('vm').in_error_state()) {
          cls += ' vm-status-error';
        }
        return cls
      },

      vm_style: function() {
        var cls, icon_state;
        var style = "background-image: url('{0}')";
        var vm = this.model.get('vm')
        if (!vm) { return }
        this.$(".model-logo").removeClass("state1 state2 state3 state4");
        icon_state = vm.is_active() ? "on" : "off";
        if (icon_state == "on") {
          cls = "state1"
        } else {
          cls = "state2"
        }
        this.$(".model-logo").addClass(cls);
        return style.format(this.get_vm_icon_path(this.model.get('vm'), 
                                                  'medium2'));
      },

      get_vm_icon_path: function(vm, icon_type) {
        var os = vm.get_os();
        var icons = window.os_icons || views.IconView.VM_OS_ICONS;

        if (icons.indexOf(os) == -1) {
          os = "unknown";
        }

        return views.IconView.VM_OS_ICON_TPLS()[icon_type].format(os);
      },
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
                display_description: desc,
                volume_id: this.volume.id
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

          var date = synnefo.util.formatDate(d).replace(/\//g, '-');
            
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
