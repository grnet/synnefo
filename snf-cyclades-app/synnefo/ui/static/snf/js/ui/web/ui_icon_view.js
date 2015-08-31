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
    var util = snf.util = snf.util || {};

    var views = snf.views = snf.views || {}

    // shortcuts
    var bb = root.Backbone;
    
    // handle extended info toggler
    views.VMActionErrorView = views.View.extend({
    
        initialize: function (vm, view) {
            this.vm = vm;
            this.view = view;
            this.vm_view = this.view.vm(vm);

            this.has_error = false;
            
            this.error = this.vm_view.find(".action-error");
            this.close = this.vm_view.find(".close-action-error");
            this.show_btn = this.vm_view.find(".show-action-error");
            this.project_view = this.vm_view.find(".project-name");


            this.init_handlers();
            this.handle_tooltips();
            this.update_layout();
        },
        
        init_handlers: function() {
              this.project_view.bind('click', _.bind(function() {
                synnefo.ui.main.vm_reassign_view.show(this.vm);
              }, this));

            // action call failed notify the user
            this.vm.bind("action:fail", _.bind(function(args){
                if (this.vm.action_error) {
                    this.has_error = true;
                    var action = "undefined";
                    try {
                        action = _.last(args).error_params.extra_details['Action'];
                    } catch (err) {console.error(err)};
                    
                    this.error.find(".action").text(action);
                    this.error.show();
                }
            }, this));
            
            // show error overlay
            this.show_btn.click(_.bind(function() {
                if (this.vm.action_error) {
                    this.show_error_overlay(this.vm.action_error);
                }
                this.vm.reset_action_error();
            }, this));
            
            // user requests to forget about the error
            this.close.click(_.bind(_.bind(function() {
                this.error.hide();
                this.vm.reset_action_error();
            }, this)));
            
            // hide error message if action fail get reset
            this.vm.bind("action:fail:reset", _.bind(function(){
                this.error.hide();
            }, this));

            this.vm.bind("change:is_ghost", _.bind(function() {
              this.handle_tooltips();
            }, this));
        },

        handle_tooltips: function() {
          var main_content = this.vm_view.find(".machine-data");
          if (this.vm.get('is_ghost')) {
            snf.util.set_tooltip(main_content,
              'You do not have access to this resource.<br/>You are only seeing' +
              ' it because it is related to another resource already' +
              ' shared to you.', {tipClass: 'info tooltip'});
          } else {
            snf.util.unset_tooltip(main_content);
          }
          if (this.vm.get('shared_to_me')) {
            snf.util.set_tooltip(this.project_view,
              'Not the owner of this resource, cannot reassign.',
              {tipClass: "tooltip"});
          } else {
            snf.util.unset_tooltip(this.project_view);
          }
        },

        show_reassign_view: function(vm) {
          synnefo.ui.main.reassign_view.show(vm);
        },

        show_error_overlay: function(args) {
            var args = util.parse_api_error.apply(util, args);
            
            // force logout if UNAUTHORIZED request arrives
            if (args.code == 401) { snf.ui.logout(); return };
            
            var error_entry = [args.ns, args.code, args.message, '', args.type, args.details, args];
            ui.main.error_view.show_error.apply(ui.main.error_view, error_entry);
        },

        update_layout: function() {
            if (this.vm.action_error) {
                this.error.show();
            }
        }
    });

    // handle extended info toggler
    views.IconInfoView = views.View.extend({
    
        initialize: function (vm, view) {
            this.vm = vm;
            this.view = view;
            this.vm_view = this.view.vm(vm);
            
            this.info_toggle = $(".cont-toggler-wrapper.info .toggler", 
                                 this.vm_view);
            this.ips_toggle = $(".cont-toggler-wrapper.ips .toggler", 
                                this.vm_view);
            this.volumes_toggle = $(".cont-toggler-wrapper.volumes .toggler", 
                                    this.vm_view);
            this.info_el = $("div.info-content.vm-info", this.vm_view);
            this.ips_el = $("div.info-content.ips", this.vm_view);
            this.volumes_el = $("div.info-content.volumes", this.vm_view);

            this.label = $(".label", this.vm_view);

            this.logo_shared = $(".logo-shared", this.vm_view);
            this.logo_shared.hide();

            this.set_handlers();
            this.update_layout();
        },

        update_layout: function() {
            if (this.vm.get('shared_to_me')) {
              this.logo_shared.attr('src', snf.config.media_url + '/images/shared-to-me.png');
              this.logo_shared.show();
            } else if (this.vm.get('shared_to_project')) {
              this.logo_shared.attr('src', snf.config.media_url + '/images/shared-by-me.png');
              this.logo_shared.show();
            } else {
              this.logo_shared.hide();
            }

          },


        set_handlers: function() {
            this.info_toggle.click(_.bind(function(){
                if (this.info_toggle.parent().hasClass("disabled")) {
                    return;
                }
                this.ips_el.slideUp();
                this.ips_toggle.removeClass("open");
                this.volumes_el.slideUp();
                this.volumes_toggle.removeClass("open");

                this.info_el.slideToggle();
                var vm_view = this.view.vm(this.vm);

                if (this.info_toggle.hasClass("open")) {
                    this.info_toggle.removeClass("open");
                    this.vm.stop_stats_update();
                    vm_view.removeClass("light-background");
                } else {
                    this.info_toggle.addClass("open");
                    this.view.details_views[this.vm.id].update_layout();
                    this.view.tags_views[this.vm.id].update_layout();
                    this.view.stats_views[this.vm.id].update_layout();
                    vm_view.addClass("light-background");
                }
                
                var self = this;
                window.setTimeout(function() {
                  $(self.view).trigger("resize")
                }, 300);
            }, this));

            this.volumes_toggle.click(_.bind(function(){
                if(this.volumes_toggle.parent().hasClass("disabled")) {
                  return;
                }
                this.info_el.slideUp();
                this.info_toggle.removeClass("open");
                this.ips_el.slideUp();
                this.ips_toggle.removeClass("open");
                var vm_view = this.view.vm(this.vm);

                this.volumes_el.slideToggle();
                var self = this;
                if (this.volumes_toggle.hasClass("open")) {
                    this.volumes_toggle.removeClass("open");
                    vm_view.removeClass("light-background");
                } else {
                    this.volumes_toggle.addClass("open");
                    vm_view.addClass("light-background");
                }
                window.setTimeout(function() {
                  $(self.view).trigger("resize")
                }, 300);
            }, this));


            this.ips_toggle.click(_.bind(function(){
                if(this.ips_toggle.parent().hasClass("disabled")) { return; }
                this.info_el.slideUp();
                this.info_toggle.removeClass("open");
                this.volumes_el.slideUp();
                this.volumes_toggle.removeClass("open");

                var vm_view = this.view.vm(this.vm);

                this.ips_el.slideToggle();
                var self = this;
                if (this.ips_toggle.hasClass("open")) {
                    this.ips_toggle.removeClass("open");
                    vm_view.removeClass("light-background");
                } else {
                    this.ips_toggle.addClass("open");
                    vm_view.addClass("light-background");
                }
                window.setTimeout(function() {
                  $(self.view).trigger("resize")
                }, 300);
            }, this));
            
            this.vm_view.find(".stats-report").click(_.bind(function(e){
                e.preventDefault();
                snf.ui.main.show_vm_details(this.vm);
            }, this)).attr("href", 
                           "#machines/single/details/{0}".format(this.vm.id));
        }
    
    })

    // rename handler view
    // only icon view contains rename capability
    views.IconRenameView = views.View.extend({
        
        initialize: function(vm, view) {
            this.vm = vm;
            this.view = view;
            // name container
            this.el = $('div#' + this.view.id_tpl + vm.id + " div.name").get(0);
            // name inline element
            this.name = this.$('span.name');
            // rename button
            this.rename = this.$('span.rename');
            // save button
            this.save = this.$('.save');
            // cancel rename button
            this.cancel = this.$('.cancel');
            // where to place the input field
            this.edit_cont = this.$(".namecontainer");
            // buttons container
            this.buttons = this.$(".editbuttons");
            // current state
            this.renaming = false;
            // init event handlers
            this.set_handlers();
            // paint
            this.update_layout();
            views.IconRenameView.__super__.initialize.call(this);
        },
        
        // update elements visibility/state
        update_layout: function() {
            if (this.vm.get('is_ghost')) {
                this.name.text("Unknown");
                this.rename.hide();
                return;
            }

            // if in renaming state
            if (this.renaming) {
                // if name is hidden we are already in renaming state
                // dont do nothing
                if (this.name.is(":hidden")){return}
                
                // hide name element to make space for the 
                // text input
                this.name.hide();
                this.rename.hide();
                // show confirm/cancel buttons
                this.buttons.show();
                // create text element
                this.create_input();
            } else {
                // name is visible not in edit mode
                if (this.name.is(":visible")){return}

                this.name.show();
                this.rename.show();
                this.buttons.hide();
                this.remove_input();
            }
        },
        
        // create rename input field and set appropriate 
        // event handlers
        create_input: function() {
            var self = this;
            this.edit_cont.append('<input class="vm-rename nametextbox" type="text" />');
            this.$('input').val(this.vm.get('name'));
            // give edit focus
            this.$('input').focus();
            // handle enter press
            this.$('input').keydown(function(ev){
                ev.keyCode = ev.keyCode || ev.which;
                if (ev.keyCode == 13) { self.submit(); }
                if (ev.keyCode == 27) { self.renaming = false; self.update_layout(); }
            })
        },
        
        // remove input element
        remove_input: function() {
            this.$('input').remove();
        },
        
        // initialize event handlers
        set_handlers: function() {
            var self = this;
            // start rename when rename button is pressed
            this.rename.click(function() {
                self.renaming = true;
                self.update_layout();
            });
            
            // double click on name
            $(this.el).dblclick(function() {
                self.renaming = true;
                self.update_layout();
            });

            // cancel rename
            this.cancel.click(function() {
                self.renaming = false;
                self.update_layout();
            })
            
            // apply the rename
            // TODO: check if name is equal than the previous value
            this.save.click(function() {
                self.submit();
            })
        },

        submit: function() {
            var value = _(this.$('input').val()).trim();
            if (value == "") { return };
            this.renaming = false;
            this.vm.rename(this.$('input').val());
            this.update_layout();
        }
    });
    
    // VM connect interaction view
    views.IconVMConnectView = views.View.extend({
        
        initialize: function(vm, view) {
            // parent view (single, icon, list)
            this.parent = view;
            this.vm = vm;
            this.el = view.vm(vm);
            this.set_handlers();
            views.IconVMConnectView.__super__.initialize.call(this);
        },
        
        // set the appropriate handlers
        set_handlers: function() {
            // setup connect handler on vm icon interaction
            var el = this.el;
            var vm = this.vm;

            // element that triggers the connect handler
            var connect = el.find("div.connect-arrow, .logo");
            // connect status handler
            var handler = _.bind(this.connect_handler, {vm:vm, el:el, view:this.parent});
            $(connect).bind({'mouseover': handler, 'mouseleave': handler, 
                            'mousedown': handler, 'mouseup': handler,
                            'click': handler });
            
            // setup connect arrow display handlers 
            // while hovering vm container
            el.bind("mouseover", function(){
                if (vm.is_connectable()) {
                    el.find(".connect-border").show();
                    el.find(".connect-arrow").show();
                    el.find(".logo").css({cursor:"pointer"});
                } else {
                    el.find(".connect-border").hide();
                    el.find(".connect-arrow").hide();
                    el.find(".logo").css({cursor: "default"});
                }
            }).bind("mouseleave", function(){
                el.find(".connect-border").hide();
                el.find(".connect-arrow").hide();
            });
        },
        
        // connect arrow interaction handlers
        // BEWARE, this function has different context
        // than the View object itself, see set_vm_handlers
        connect_handler: function(event) {
            // nothing to do if we cannot connect to the vm
            if (!this.vm.is_connectable()) {return}
            
            var logo = this.el.find(".logo");
            var arrow = this.el.find(".connect-arrow");
            var border = this.el.find(".connect-border");
            
            // clear icon states
            logo.removeClass('single-image-state1 single-image-state2 single-image-state3 single-image-state4');

            // append the appropriate state class
            switch (event.type) {
                case "mouseover":       
                    logo.addClass('single-image-state4');
                    arrow.addClass('border-hover');
                    break;
                
                case "mouseleave":
                    logo.addClass('single-image-state1');
                    arrow.removeClass('border-hover');
                    break;

                case "mouseup":
                    logo.addClass('single-image-state4');
                    //this.view.connect_overlay.show(this.vm);
                    break;

                case "mousedown":
                    logo.addClass('single-image-state2');
                    break;

                case "click":
                    //logo.addCLass('single-image-state4');
                    //this.view.connect_to_console(vm);
                    this.view.connect_overlay.show(this.vm);
                    break;

                default:
                    ;
            }
        },
        
        update_layout: function() {
        }

    });
    
    // vm metadata subview for icon and single view
    views.VMTagsView = views.View.extend({
        view_id: 'vm_tags',
        // metadata container selector
        el_sel: '.vm-metadata',
        // metadata row template
        tag_tpl: '<span class="tag-item"><span class="key">{0}</span><span class="value">{1}</span></span>',
        // how many tags to show
        tag_limit: 4,
        // truncate options (because container has different size on icon/single views)
        tag_key_truncate: 7,
        tag_value_truncate: 15,

        initialize: function(vm, view, toggle, limit, tag_key_truncate, tag_value_truncate) {
            this.tag_limit = limit || this.tag_limit;

            this.tag_key_truncate = tag_key_truncate || this.tag_key_truncate;
            this.tag_value_truncate = tag_value_truncate || this.tag_value_truncate;

            // does the view toggles the metadata container (single view)
            this.toggle = toggle || false;
            // parent view
            this.parent = view;
            this.vm = vm;
            this.el = this.parent.vm(vm);
            this.view_id = this.view_id + "_" + vm.id;

            // link to raise the metadata manager overlay
            this.link = this.$('a.manage-metadata');

            views.VMTagsView.__super__.initialize.call(this);
            this.set_handlers();
            this.update_layout();
        },
        
        // set the appropriate handlers
        set_handlers: function() {
            var self = this;
            // show the metadata editor overlay
            this.link.click(_.bind(function(ev) {
                ev.preventDefault();
                this.parent.metadata_view.show(this.vm);
            }, this));

            // tags/ips have show/hide control ? bind events for them
            var self = this;
            if (this.toggle) {
                $(this.el).find(".tags-header").click(_.bind(function(){
                    if (this.vm.get('is_ghost')) { return }
                    $(self.el).find(".tags-content").slideToggle(600);
                    var details_toggler = $(this.el).find(".tags-header " +
                                                          ".cont-toggler");
                    if (details_toggler.hasClass("open")) {
                        details_toggler.removeClass("open");
                    } else {
                        details_toggler.addClass("open");
                    }
                }, this));
                $(this.el).find(".tags-header").find(".toggler").removeClass("open");
                $(self.el).find(".tags-content").hide();
            }
        },
        
        // update metadata container and data
        update_layout: function() {

            // api metadata object
            var meta =  this.vm.get('metadata');

            var i = 0;
            var cont = $(this.el).find(".items");

            // clear existing items
            cont.find(".tag-item").remove();
            
            // create tag elements
            _.each(meta, function(value, key){
                // respect the limit
                if (i > this.tag_limit) {
                    return;
                }
                
                // create element
                var _key = _.escape(util.truncate(key, this.tag_key_truncate));
                var _value = _.escape(util.truncate(": " + value, this.tag_value_truncate));
                var new_el = $(this.tag_tpl.format(_key, _value));

                // add title attributes, improve accesibility
                // truncated values
                new_el.find("span.key").attr("title", key);
                new_el.find("span.value").attr("title", _.escape(value));

                cont.append(new_el);
            }, this);
        }
    });
    

    // stats subview for single/icon views
    views.VMStatsView = views.View.extend({

        initialize: function(vm, view, options) {
            if (!options) {options = {}};
            this.vm = vm;
            this.parent = view;
            this.sel = options.el || this.el_sel || ".lower";
            this.el = this.parent.vm(vm).find(this.sel);
            this.selected_stats_period = 'hourly';
            
            // elements shortcuts
            this.cpu_loading = this.el.find(".cpu-graph .stat-busy");
            this.cpu_error = this.el.find(".cpu-graph .stat-error");
            this.cpu_img = this.el.find(".cpu-graph .stat-img");
            this.net_loading = this.el.find(".network-graph .stat-busy");
            this.net_error = this.el.find(".network-graph .stat-error");
            this.net_img = this.el.find(".network-graph .stat-img");

            this.loading = this.el.find(".stat-busy");
            this.error = this.el.find(".stat-error");
            this.img = this.el.find(".stat-img");
            this.stats_period_options = this.el.find(".stats-select-option");
            

            // handle stats period option select
            var self = this;
            this.stats_period_options.click(function(){
                // skip if current selection is clicked
                if ($(this).filter(".stats-" + self.selected_stats_period).length) {
                    return
                } else {
                    // identify class
                    var cls = $(this).attr("class");
                    regex = /.*\sstats-(\w+)/;
                    self.set_stats_period(cls.match(regex)[1]);
                }
            });
            
            // initial state paremeters
            this.stats = this.vm.get("stats");

            // timeseries or bar images ?
            this.stats_type = options.stats_type || "bar";

            views.VMStatsView.__super__.initialize.apply(this, arguments);
            this.set_handlers();
            this.update_layout();

            this.net_loading.show();
            this.net_error.hide();
            this.cpu_loading.show();
            this.cpu_error.hide();

            this.net_img.hide();
            this.cpu_img.hide();
            
            if (!window.t) {
                window.t = [];
            }
            if (this.parent.menu) {
                window.t[window.t.length] = this;
            }
        },

        
        set_stats_period: function(period) {
            this.selected_stats_period = period;
            this.update_layout();
        },

        set_handlers: function() {
            // update view state when vm stats update gets triggered
            this.vm.bind("stats:update", _.bind(function(){
                // update the layout
                this.update_layout();
            }, this));
        },
        
        get_images: function (type, period) {
            var period = period || 'hourly';
            var images;

            if (type == 'bar') {
                images = {'cpu': this.stats.cpuBar, 'net': this.stats.netBar };
            } else {
                images = {'cpu': this.stats.cpuTimeSeries, 
                          'net': this.stats.netTimeSeries };
            }

            if (period == 'weekly' && type != 'bar') {
                if (images.cpu)
                    images.cpu = images.cpu.replace('cpu-ts', 'cpu-ts-w')
                if (images.net)
                    images.net = images.net.replace('net-ts', 'net-ts-w')
            }
            return images
        },

        update_layout: function() {
            if (!this.vm.stats_available) {
                this.loading.show();
                this.loading.hide();
                this.img.hide();
                this.error.hide();
            } else {
                this.loading.hide();
                this.stats = this.vm.get("stats");
                var images = this.get_images(this.stats_type, 
                                             this.selected_stats_period)

                if (images.cpu) {
                    this.cpu_img.attr({src:images.cpu}).show();
                    this.cpu_error.hide();
                } else {
                    this.cpu_img.hide();
                    this.cpu_error.show();
                }

                if (images.net) {
                    this.net_img.attr({src:images.net}).show();
                    this.net_error.hide();
                } else {
                    this.net_img.hide();
                    this.net_error.show();
                }
            }
                
            // update selected stats period
            this.stats_period_options.removeClass("selected");
            this.stats_period_options.filter(".stats-" + this.selected_stats_period).addClass("selected")

            $(window).trigger("resize");
        }
    });

    views.VMDetailsView = views.View.extend({
        view_id: "vm_details",
        el_sel: '.vm-details',
        

        selectors: {
            'cpu': '.cpu-data',
            'ram': '.ram-data',
            'disk': '.disk-data',
            'image_name': '.image-data',
            'image_size': '.image-size-data'
        },

        initialize: function(vm, view) {
            this.parent = view;
            this.vm = vm;
            this.el = $(this.parent.vm(vm)).find(this.el_sel).get(0);
            this.view_id = "vm_{0}_details".format(vm.id);
            
            views.VMDetailsView.__super__.initialize.call(this);
            
            this.resize_actions = this.$(".trigger-resize");
            this.init_handlers();
            this.update_layout();
        },
        
        init_handlers: function() {
          this.resize_actions.bind('click', _.bind(function(e){
              if (this.vm.in_error_state()) { return }
              if (this.vm.get('is_ghost'))  {return }
              ui.main.vm_resize_view.show(this.vm);
          }, this));
        },

        update_layout: function() {
            if (!this.visible() && this.parent.details_hidden) { return };

            var image = this.vm.get_image(_.bind(function(image){
                this.sel('image_name').text(
                    util.truncate(image.get('name'), 17)).attr("title",
                    image.escape('name'));
                    this.sel('image_size').text(
                      image.get_readable_size()).attr('title',
                      image.get_readable_size());
            }, this));

            if (this.vm.get('is_ghost')) {
              this.sel('cpu').text('Unknown');
              this.sel('ram').text('Unknown');
              this.sel('disk').text('Unknown');
              this.sel('image_name').text('Unknown');
              this.sel('image_size').text('Unknown');
              this.resize_actions.removeClass('trigger-resize')
            }

            var flavor = this.vm.get_flavor();
            if (!flavor || !image) {
                return;
            }

            this.sel('cpu').text(flavor.get('cpu'));
            this.sel('ram').text(flavor.get('ram'));
            this.sel('disk').text(flavor.get('disk'));

            this.parent.tags_views[this.vm.id].update_layout();
            this.parent.stats_views[this.vm.id].update_layout();
            
            if (this.parent.details_hidden) {
                this.vm.start_stats_update(true);
            }
        }
    });
    
    // VMs icon view
    views.IconView = views.VMListView.extend({
        
        // view id (this could be used to identify 
        // the view object from global context
        view_id: 'vm_icon',
        
        details_hidden: true,

        el: '#machinesview-icon',
        id_tpl: 'icon-vm-',

        selectors: {
            'vms': '.machine-container',
            'vm': '#icon-vm-',
            'view': '#machinesview-icon',
            'tpl': '#machinesview-icon.standard #machine-container-template',
            'spinner': '.large-spinner',
            'vm_spinner': '#icon-vm-{0} .state .spinner',
            'vm_wave': '#icon-vm-{0} .wave',
            'vm_cont_active': '#machinesview-icon.standard .running',
            'vm_cont_terminated': '#machinesview-icon.standard .terminated'
        },
            
        reset: function() {},
        // overload show function
        show_view: function() {
            $(this.el).show();
            this.__update_layout();
        },

        post_update_vm: function(vm) {
        },

        // identify vm model instance id based on DOM element
        vm_id_for_element: function(el) {
            return el.attr('id').replace("icon-vm-","");
        },
        
        // set generic view handlers
        set_handlers: function() {
        },  
        
        // stuff to do when a new vm has been created.
        // - create vm subviews
        post_add: function(vm) {
            this.rename_views = this.rename_views || {};
            this.stats_views = this.stats_views || {};
            this.connect_views = this.connect_views || {};
            this.tags_views = this.tags_views || {};
            this.details_views = this.details_views || {};
            this.info_views = this.info_views || {};
            this.action_error_views = this.action_error_views || {};
            this.action_views = this.action_views || {};
            this.ports_views = this.ports_views || {};
            this.volumes_views = this.volumes_views || {};

            this.action_views[vm.id] = new views.VMActionsView(
                vm, this, this.vm(vm), this.hide_actions);

            this.rename_views[vm.id] = new views.IconRenameView(vm, this);
            this.stats_views[vm.id] = new views.VMStatsView(vm, this, {el:'.vm-stats'});
            this.connect_views[vm.id] = new views.IconVMConnectView(vm, this);
            this.tags_views[vm.id] = new views.VMTagsView(vm, this);
            this.details_views[vm.id] = new views.VMDetailsView(vm, this);
            this.action_error_views[vm.id] = new views.VMActionErrorView(vm, this);
            
            var ports_container = this.vm(vm).find(".machine-data");
            var ports_view = new views.VMPortListView({
              collection: vm.ports, 
              container: ports_container,
              parent: this
            });
            this.ports_views[vm.id] = ports_view;
            ports_view.show();
            ports_view.el.hide();

            var volumes_container = this.vm(vm).find(".machine-data");
            var volumes_view = new views.VMVolumeListView({
              collection: vm.volumes,
              container: ports_container,
              parent: this
            });
            this.volumes_views[vm.id] = volumes_view;
            volumes_view.show();
            volumes_view.el.hide();

            this.info_views[vm.id] = new views.IconInfoView(vm, this);
        },
        
        // vm specific event handlers
        set_vm_handlers: function(vm) {
        },

        check_terminated_is_empty: function() {
            // hide/show terminated container
            if (this.$(".terminated .machine-container").length == 0) {
                this.$(".terminated").hide()
            } else {
                this.$(".terminated").show()
            }

            $(window).trigger("resize");
        },
        
        update_layout: function() {
            if (storage.vms.models.length > 0) {
                this.$(".running").removeClass("disabled");
            } else {
                this.$(".running").addClass("disabled");
            }

            
            this.check_terminated_is_empty();
    
            // FIXME: code from old js api
            this.$("div.separator").show();
            this.$("div.machine-container:last-child").find("div.separator").hide();
        },
  
        update_status_message: function(vm) {
            var el = this.vm(vm);
            var message = vm.get_status_message();
            if (message) {
                // update bulding progress
                el.find("div.machine-ips").hide();
                el.find("div.build-progress").show();
                el.find("div.build-progress .message").text(util.truncate(message, 42));

                if (vm.in_error_state()) {
                    el.find("div.build-progress .btn").show();
                } else {
                    el.find("div.build-progress .btn").hide();
                }
            } else {
                // hide building progress
                el.find("div.machine-ips").show()
                el.find("div.build-progress").hide();
                el.find("div.build-progress .btn").hide();
            }
        },

        // update vm details
        update_details: function(vm) {
            var el = this.vm(vm);
            var project = vm.get('project')
            if (project) {
              el.find(".project-name").text(
                 "[" +  _.truncate(project.get('name'), 20) + "]"
              );
            }
            // truncate name
            el.find("span.name").text(util.truncate(vm.get("name"), 37));

            el.find('.fqdn').val(vm.get_hostname());

            el.find("div.status").text(STATE_TEXTS[vm.state()]);
            // set state class
            var cls = views.IconView.STATE_CLASSES[vm.state()] || ['state'];
            el.find("div.state").removeClass().addClass(cls.join(" "));
            // os icon
            el.find("div.logo").css({
                'background-image': "url(" + 
                    this.get_vm_icon_path(vm, "medium") + ")"
            });

            var logo = el.find('div.logo');
            if (vm.get('is_ghost')) {
              logo.addClass('logo-ghost');
            } else {
              logo.removeClass('logo-ghost');
            }
            
            el.removeClass("connectable");
            if (vm.is_connectable()) {
                el.addClass("connectable");
            }
            
            var status = vm.get("status");
            var state = vm.get("state");
            
            this.update_status_message(vm);

            icon_state = vm.is_active() ? "on" : "off";
            set_machine_os_image(el, "icon", icon_state, 
                                 this.get_vm_icon_os(vm));
            
            // update subviews
            this.rename_views[vm.id].update_layout();
            this.connect_views[vm.id].update_layout();
            this.details_views[vm.id].update_layout();
        },

        post_remove_vm: function(vm) {
            this.check_terminated_is_empty();
            $(window).trigger("resize");
        },
            
        get_vm_icon_os: function(vm) {
            var os = vm.get_os();
            var icons = window.os_icons || views.IconView.VM_OS_ICONS;

            if (icons.indexOf(os) == -1) {
                os = "unknown";
            }

            return os;
        },

        // TODO: move to views.utils (the method and the VM_OS_ICON vars)
        get_vm_icon_path: function(vm, icon_type) {
            var os = vm.get_os();
            var icons = window.os_icons || views.IconView.VM_OS_ICONS;

            if (icons.indexOf(os) == -1) {
                os = "unknown";
            }

            return views.IconView.VM_OS_ICON_TPLS()[icon_type].format(os);
        }
    })

    views.IconView.VM_OS_ICON_TPLS = function() {
        return {
            "medium": snf.config.machines_icons_url + "medium/{0}-sprite.png",
            "medium2": snf.config.machines_icons_url + "medium/{0}-sprite2.png"
        }
    }

    views.IconView.VM_OS_ICONS = window.os_icons || [];

    views.IconView.STATE_CLASSES = {
        'UNKNOWN':          ['state', 'unknown-state'],
        'BUILD':            ['state', 'build-state'],
        'REBOOT':           ['state', 'rebooting-state'],
        'STOPPED':          ['state', 'terminated-state'],
        'ACTIVE':           ['state', 'running-state'],
        'ERROR':            ['state', 'error-state'],
        'DELETED':          ['state', 'destroying-state'],
        'DESTROY':          ['state', 'destroying-state'],
        'SHUTDOWN':         ['state', 'shutting-state'],
        'START':            ['state', 'starting-state'],
        'CONNECT':          ['state', 'connecting-state'],
        'DISCONNECT':       ['state', 'disconnecting-state'],
        'ATTACH_VOLUME':    ['state', 'connecting-state'],
        'DETACH_VOLUME':    ['state', 'disconnecting-state'],
        'RESIZE':           ['state', 'rebooting-state']
    };

})(this);
