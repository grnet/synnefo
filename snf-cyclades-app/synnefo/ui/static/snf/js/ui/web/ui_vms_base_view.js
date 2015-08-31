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

    var views = snf.views = snf.views || {}

    // shortcuts
    var bb = root.Backbone;
    
    // logging
    var logger = new snf.logging.logger("SNF-VIEWS");
    var debug = _.bind(logger.debug, logger);
    
    var hasKey = Object.prototype.hasOwnProperty;

    // base class for views that contain/handle VMS
    views.VMListView = views.View.extend({

        // just a flag to identify that
        // views of this type handle vms
        vms_view: true,

        selectors: {},
        hide_actions: true,
        pane: "#machines-pane",
        metadata_view: undefined,

        initialize: function() {
            views.VMListView.__super__.initialize.call(this);
            this._vm_els = {};
            this.set_storage_handlers();
            this.set_handlers();
            this.vms_updated_handler();
            this.connect_overlay = new views.VMConnectView();
        },

        // display vm diagnostics detail overlay view, update based on
        // diagnostics_update_interval config value.
        show_build_details_for_vm: function(vm) {
            var cont = null;
            var success = function(data) {
                var message = "";
                var title = vm.get('name');
                var info = '<em>Status log messages:</em>';

                var list_el = $('<div class="diagnostics-list">');
                list_el.append('<div class="empty">No data available</div>');

                cont = list_el;
                var messages = _.clone(data);

                update_overlay_diagnostics(data, cont);
                synnefo.ui.main.details_view.show(title, info, cont);
            }

            var update_overlay_diagnostics = function(data) {
                var existing = cont.find(".msg-log-entry");
                var messages = _.clone(data);
                
                var to_append = messages.slice(0, messages.length - existing.length);
                to_append.reverse();

                var appending = to_append.length != messages.length;
                
                if (to_append.length) { cont.find(".empty").hide() } else {
                    if (!messages.length) { cont.find(".empty").show() }
                }
                _.each(to_append, function(msg){
                    var el = $('<div class="clearfix msg-log-entry ' + msg.level.toLowerCase() + '">');
                    if (msg.details) {
                      el.addClass("with-details");
                    }
                    var display_source_date = synnefo.config.diagnostics_display_source_date;
                    var source_date = "";
                    if (display_source_date) {
                        source_date = '('+synnefo.util.formatDate(new Date(msg.source_date))+')';
                    }

                    el.append('<span class="date">' + synnefo.util.formatDate(new Date(msg.created)) + source_date + '</span>');
                    el.append('<span class="src">' + _.escape(msg.source) + '</span>');
                    el.append('<span class="msg">' + _.escape(msg.message) + '</span>');
                    if (msg.details) {
                        el.append('<pre class="details">' + _.escape(msg.details) + '</pre>');
                    }
                    if (appending) { el.hide(0); el.css({'display':'none'})}
                    cont.prepend(el);
                    el.click(function(el) {
                        $(this).find(".details").slideToggle();
                        $(this).toggleClass("expanded");
                    });

                    if (appending) { el.fadeIn(800); }
                });
                
                window.setTimeout(function(){
                    if (cont.is(":visible")) {
                        vm.get_diagnostics(update_overlay_diagnostics);
                    }
                }, synnefo.config.diagnostics_update_interval);
            }

            vm.get_diagnostics(success);
        },

        // Helpers
        //
        // get element based on this.selectors key/value pairs
        sel: function(id, params) {
            if (!this.selectors[id]){ return };
            return $(this.selectors[id].format(params));
        },
        
        // vm element based on vm model instance provided
        vm: function(vm) {
            if (hasKey.call(this._vm_els, vm.id)) {
                ret = this._vm_els[vm.id];
            } else {
                return $([]);
            }

            return ret;
        },
        
        // get vm model instance from DOM element
        vm_for_element: function(el) {
            return storage.vms.sel(this.vm_id_for_element(el));
        },
        

        // Event binding and stuff like that
        //
        set_storage_handlers: function() {
            storage.vms.bind("add", _.bind(this.vms_updated_handler, this, "add"));
            storage.vms.bind("change", _.bind(this.vms_updated_handler, this, "change"));
            storage.vms.bind("reset", _.bind(this.vms_updated_handler, this, "reset"));
            storage.vms.bind("remove", _.bind(this.vms_updated_handler, this, "remove"));
        },
        
        // vms updated triggered, update view vms
        vms_updated_handler: function (method, model, arg2, arg3) {
            var updated = storage.vms.models;
            if (method == "add") { updated = [model] };
            if (method == "change") { updated = [model] };
            if (method == "remove") { updated = [model] };

            if (method == "remove") {
                this.remove_vm(model)
                return;
            }
            
            this.update_vms(updated);
        },

        // create vm
        // append it on proper view container
        create_vm: function(vm) {
            // create dom element
            var vm_view = this.create_vm_element(vm);
            vm_view.find(".vm-actions").attr("id", this.view_id+"-actions-" + vm.id);
            this._vm_els[vm.id] = vm_view;
            var container = this.get_vm_container(vm);
            container.append(vm_view);
            vm_view.find(".action-indicator").text("");
            if (this.visible()) {
                container.show()
            }

            // initialize vm specific event handlers 
            this.__set_vm_handlers(vm);
            vm_view.find(".suspended-notice").click(function(){
              synnefo.ui.main.suspended_view.show(vm);
            })
            return vm_view;
        },
        
        // create vm dom element
        create_vm_element: function(vm) {
            // clone template
            return this.sel('tpl').clone().attr("id", this.id_tpl + vm.id)
        },

        // get proper vm container
        get_vm_container: function(vm) {
            if (vm.is_active()) {
                return this.sel("vm_cont_active");
            } else {
                return this.sel("vm_cont_terminated");
            }
        },

        // create and append inside the proper container the vm model
        // if it doesn't exist update vm data and make it visible
        add: function(vm) {
            // create if it does not exist
            if (!hasKey.call(this._vm_els, vm.id)) {
                var el = this.create_vm(vm);
                el.show();
                this.post_add(vm);
                this.init_vm_view_handlers(vm);
            }

            return this.vm(vm);
        },

        init_vm_view_handlers: function(vm) {
            var self = this;
            var el = this.vm(vm);

            var project = vm.get('project');
            if (!vm.get('is_ghost')) {
              if (project) {
                project.bind('change', function() {
                  el.find(".project-name").text(
                    _.truncate(project.get('name'), 20));
                }, this);
              }
            } else {
                el.find(".project-name-cont").addClass("disabled");
                if (project) {
                  el.find(".project-name").text(
                    _.truncate(project.get('name'), 20))
                } else {
                  el.find(".project-name").text("[Unknown]");
                }
            }

            // hidden feature, double click on indicators to display 
            // vm diagnostics.
            el.find(".indicators").bind("dblclick", function(){
                if (vm.get('is_ghost')) { return }
                self.show_build_details_for_vm(vm);
            });

            // this button gets visible if vm creation failed.
            el.find("div.build-progress .btn").click(function(){
                if (vm.get('is_ghost')) { return }
                self.show_build_details_for_vm(vm);
            });
        },
        
        // helpers for VMListView descendants
        post_add: function(vm) { throw "Not implemented" },
        set_vm_handlers: function(vm) { throw "Not implemented" },
        set_handlers: function() { throw "Not implemented" },
        update_layout: function() { throw "Not implemented" },
        post_update_vm: function(vm) { throw "Not implemented" },
        update_details: function(vm) {},
        
        // remove vm
        remove_vm: function(vm) {
            // FIXME: some kind of transiton ??? effect maybe ???
            this.vm(vm).remove();
            this.post_remove_vm(vm);
            if (hasKey.call(this._vm_els, vm.id)) {
                delete this._vm_els[vm.id];
            }
        },
        
        // remove all vms from view
        clear: function() {
            this.sel('vms').remove();
            this.__update_layout();
        },

        show: function() {
            views.VMListView.__super__.show.apply(this, arguments);
            if (storage.vms.length == 0) { this.hide() };
            if (!snf.config.update_hidden_views) {
                this.update_vms(storage.vms.models);
            }
        },

        // do update for provided vms, then update the view layout
        update_vms: function(vms) {
            if (!this.visible() && !snf.config.update_hidden_views) { return };

            _.each(vms, _.bind(function(vm){
                // vm will be removed
                // no need to update
                if (vm.get("status") == "DELETED") { return; }
                this.add(vm);
                this.update_vm(vm);
            }, this));
            
            // update view stuff
            this.__update_layout();
        },
        
        disable_toggler: function(vm, t) {
            this.vm(vm).find(".cont-toggler-wrapper."+t).addClass("disabled");
            var info_view = this.info_views && this.info_views[vm.id];
            var el = info_view && info_view[t+'_el'];
            if (el) {
              el.hide();
            }
        },

        enable_toggler: function(vm, t) {
            this.vm(vm).find(".cont-toggler-wrapper." + t).removeClass("disabled");
        },


        update_toggles_visibility: function(vm) {
          if (vm.get('is_ghost')) {
            this.disable_toggler(vm, 'info');
            this.disable_toggler(vm, 'tags');
          }
          if (vm.is_building() || vm.in_error_state() || vm.get("status") == "DESTROY") {
              this.disable_toggler(vm, 'ips');
              this.disable_toggler(vm, 'volumes');
          } else {
              this.enable_toggler(vm, 'ips');
              if (vm.volumes.length) {
                  this.enable_toggler(vm, 'volumes');
              } else {
                  this.disable_toggler(vm, 'volumes');
              }
          }
        },

        // update ui for the given vm
        update_vm: function(vm) {
            // do not update deleted state vms
            if (!vm || vm.get("status") == 'DELETED') { return };
            this.check_vm_container(vm);
            this.update_details(vm);
            this.update_transition_state(vm);
            this.update_toggles_visibility(vm);

            if (this.action_views) {
                this.action_views[vm.id].update();
                this.action_views[vm.id].update_layout();
            }

            var el = this.vm(vm);
            if (!vm.in_error_state()) {
                el.addClass("can-resize");
            } else {
                el.removeClass("can-resize");
            }

            if (vm.get('suspended')) {
              el.addClass("suspended");
            } else {
              el.removeClass("suspended");
            }

            try {
                this.post_update_vm(vm);
            } catch (err) {};
        },

        // check if vm is placed properly within the view
        // container (e.g. some views might have different
        // containers for terminated or running machines
        check_vm_container: function(vm){
            var el = this.vm(vm);
            if (!el.length) { return };
            var self = this;
            var selector = vm.is_active() ? 'vm_cont_active' : 'vm_cont_terminated';
            if (el.parent()[0] != this.sel(selector)[0]) {
                var cont = this.sel(selector);
                var self = this;

                el.hide().appendTo(cont).fadeIn(300);
                $(window).trigger('resize');

                //el.fadeOut(200, function() {
                    //el.appendTo(cont); 
                    //el.fadeIn(200);
                    //self.sel(selector).show(function(){
                        //$(window).trigger("resize");
                    //});
                //});
            }
        },

        __update_layout: function() {
            this.update_layout();
        },
        
        // append handlers for vm specific events
        __set_vm_handlers: function(vm) {
            // show transition on vm status transit
            vm.bind('transition', _.bind(function(){this.show_transition(vm)}, this));
            this.set_vm_handlers(vm);
        },
        
        // is vm in transition ??? show the progress spinner
        update_transition_state: function(vm) {
            if (vm.in_transition() && !vm.has_pending_action()){
                this.sel('vm_spinner', vm.id).show();
            } else {
                this.sel('vm_spinner', vm.id).hide();
            }
        },
        
        show_reassign_view: function(vm) {
          if (vm.get('is_ghost')) { return }
          synnefo.ui.main.vm_reassign_view.show(vm);
        },

        show_indicator: function(vm, action) {
            var action = action || vm.pending_action;
            this.sel('vm_wave', vm.id).hide();
            this.sel('vm_spinner', vm.id).hide();
            this.vm(vm).find(".action-indicator").removeClass().addClass(action + " action-indicator").show();
        },

        hide_indicator: function(vm) {
            this.vm(vm).find(".action-indicator").removeClass().addClass("action-indicator").hide();
            this.update_transition_state(vm);
        },

        // display transition animations
        show_transition: function(vm) {
            var wave = this.sel('vm_wave', vm.id);
            if (!wave || !wave.length) { return }

            var src = wave.attr('src');
            // change src to force gif play from the first frame
            // animate for 500 ms then hide
            wave.attr('src', "").show();
            wave.attr('src', src).fadeIn(200).delay(700).fadeOut(300, function() {
                wave.hide();
            });
        },

        connect_to_console: function(vm) {
            // It seems that Safari allows popup windows only if the window.open
            // call is made within an html element click event context. 
            // Otherwise its behaviour is based on "Block Pop-Up Windows" 
            // setting, which when enabled no notification appears for the user. 
            // Since there is no easy way to check for the setting value we use
            // async:false for the action call so that action success handler 
            // which opens the new window is called inside the click event 
            // context.
            var use_async = true;
            if ($.client.browser == "Safari") {
                use_async = false;
            }

            vm.call("console", function(console_data) {
                var url = vm.get_console_url(console_data);
                snf.util.open_window(url, "VM_" + vm.get("id") + "_CONSOLE", {'scrollbars': 1, 'fullscreen': 0});
            }, undefined, {async: use_async});
        }

    });
    
    // empty message view (just a wrapper to the element containing 
    // the empty information message)
    views.EmptyView = views.View.extend({
        el: '#emptymachineslist'
    })

    views.VMActionsView = views.View.extend({
        
        initialize: function(vm, parent, el, hide) {
            this.hide = hide || false;
            this.view = parent;
            this.vm = vm;
            this.vm_el = el;
            this.el = $("#" + parent.view_id + "-actions-" + vm.id);
            this.all_action_names = _.keys(views.VMActionsView.STATUS_ACTIONS);
            
            // state params
            this.selected_action = false;

            _.bindAll(this);
            window.acts = this;
            this.view_id = "vm_" + vm.id + "_actions";
            views.VMActionsView.__super__.initialize.call(this);

            this.hovered = false;
            this.set_hover_handlers();
        },

        action: function(name) {
            return $(this.el).find(".action-container." + name);
        },

        action_link: function(name) {
            return this.action(name).find("a");
        },
        
        action_confirm_cont: function(name) {
            return this.action_confirm(name).parent();
        },

        action_confirm: function(name) {
            return this.action(name).find("button.yes");
        },

        action_cancel: function(name) {
            return this.action(name).find("button.no");
        },

        hide_actions: function() {
            $(this.el).find("a").css("visibility", "hidden");
        },
        
        set_can_start: function() {
          var el = $(this.el).find("a.action-start").parent();
          el.removeClass("disabled-visible");
        },

        set_cannot_start: function() {
          var el = $(this.el).find("a.action-start").parent();
          el.addClass("disabled-visible")
        },

        set_can_resize: function() {
          var el = $(this.el).find("a.action-resize").parent();
          el.removeClass("disabled-visible");
        },

        set_cannot_resize: function() {
          var el = $(this.el).find("a.action-resize").parent();
          el.addClass("disabled-visible");
        },


        // update the actions layout, depending on the selected actions
        update_layout: function() {
            if (!this.vm) { return }

            if (this.vm.get('status') == 'STOPPED') {
              if (this.vm.can_start()) {
                this.set_can_start();
              } else {
                this.set_cannot_start();
              }

              if (this.vm.can_resize()) {
                  this.set_can_resize();
              } else {
                  this.set_cannot_resize();
              }
            }

            if (!this.vm_handlers_initialized) {
                this.vm = storage.vms.get(this.vm.id);
                this.init_vm_handlers();
            }

            if (!this.hovered && !this.vm.has_pending_action() && this.hide && !this.vm.action_error) { 
                this.el.hide();
                this.view.hide_indicator(this.vm);
                return 
            };

            if (!this.el.is(":visible") && !this.hide) { return };
            if (!this.handlers_initialized) { this.set_handlers(); }


            // update selected action
            if (this.vm.pending_action) {
                this.selected_action = this.vm.pending_action;
            } else {
                this.selected_action = false;
            }
            
            // vm actions tha can be performed
            var actions = this.vm.get_available_actions();
            
            // had pending action but actions changed and now selected action is
            // not available, hide it from user
            if (this.selected_action && actions.indexOf(this.selected_action) == -1) {
                this.reset();
            }
            
            this.el.show();
            
            if ((this.selected_action || this.hovered) && !this.vm.action_error) {
                // show selected action
                $(this.el).show();
                $(this.el).find("a").css("visibility", "visible");
                // show action icon
                this.view.show_indicator(this.vm);
            } else {
                if (this.hide || this.vm.action_error) {
                    // view shows actions on machine hover
                    $(this.el).find("a").css("visibility", "hidden");
                } else {
                    if (!this.vm.action_error) {
                        // view shows actions always
                        $(this.el).find("a").css("visibility", "visible");
                        $(this.el).show();
                    }
                }
                
                this.view.hide_indicator(this.vm);
            }
                
            var vm_view = this.view.vm(this.vm);
            vm_view.removeClass("action-pending");
            // update action link styles and shit
            _.each(models.VM.ACTIONS, function(action, index) {
                if (actions.indexOf(action) > -1) {
                    this.action(action).removeClass("disabled");
                    var inactive = models.VM.AVAILABLE_ACTIONS_INACTIVE[action];

                    if (inactive && !_.contains(inactive, this.vm.get('status'))) {
                      this.action(action).addClass("inactive");
                    } else {
                      this.action(action).removeClass("inactive");
                    }

                    if (this.selected_action == action) {
                        this.action_confirm_cont(action).css('display', 'block');
                        this.action_confirm(action).show();
                        this.action(action).removeClass("disabled");
                        this.action_link(action).addClass("selected");
                        vm_view.addClass("action-pending");
                    } else {
                        this.action_confirm_cont(action).hide();
                        this.action_confirm(action).hide();
                        this.action_link(action).removeClass("selected");
                    }
                } else {
                    this.action().hide();
                    this.action(action).addClass("disabled");
                    this.action_confirm(action).hide();
                }
            }, this);
        },
        
        init_vm_handlers: function() {
            try {
                this.vm.unbind("action:fail", this.update_layout)
                this.vm.unbind("action:fail:reset", this.update_layout)
            } catch (err) { console.error(err)};
            
            this.vm.bind("action:fail", this.update_layout)
            this.vm.bind("action:fail:reset", this.update_layout)

            this.vm_handlers_initialized = true;
        },
        
        set_hover_handlers: function() {
            // vm container hover (icon view)
            this.view.vm(this.vm).hover(_.bind(function() {
                this.hovered = true;
                this.update_layout();

            }, this),  _.bind(function() {
                this.hovered = false;
                this.update_layout();
            }, this));
        },

        // bind event handlers
        set_handlers: function() {
            var self = this;
            var vm = this.vm;
            
            // initial hide
            if (this.hide) { $(this.el).hide() };
            
            if (this.$('.snapshot').length) {
              this.$('.snapshot').click(_.bind(function() {
                synnefo.ui.main.create_snapshot_view.show(this.vm);
              }, this));
            }
            // action links events
            _.each(models.VM.ACTIONS, function(action) {
                var action = action;
                // indicator hovers
                this.view.vm(this.vm).find(".action-container."+action+" a").hover(function() {
                    self.view.show_indicator(self.vm, action);
                }, function() {
                    // clear or show selected action indicator
                    if (self.vm.pending_action) {
                        self.view.show_indicator(self.vm);
                    } else {
                        self.view.hide_indicator(self.vm);
                    }
                })
                
                // action links click events
                $(this.el).find(".action-container."+action+" a").click(function(ev) {
                    ev.preventDefault();
                    if (
                      action == "start" && 
                      !self.vm.can_start() && 
                      !vm.in_error_state()) {
                        if (!vm.can_resize()) { return }
                        ui.main.vm_resize_view.show_with_warning(self.vm);
                        return;
                    }

                    if (action == "resize") {
                      //if (!vm.can_resize()) { return }
                      ui.main.vm_resize_view.show(self.vm);
                      return;
                    } else if (action == "reassign") {
                      ui.main.vm_reassign_view.show(self.vm);
                      return;
                    } else {
                        self.set(action);
                    }
                }).data("action", action);

                // confirms
                $(this.el).find(".action-container."+action+" button.no").click(function(ev) {
                    ev.preventDefault();
                    self.reset();
                });

                // cancels
                $(this.el).find(".action-container."+action+" button.yes").click(function(ev) {
                    ev.preventDefault();
                    // override console
                    // ui needs to act (open the console window)
                    if (action == "console") {
                        self.view.connect_to_console(self.vm);
                    } else {
                        self.vm.call(action);
                    }
                    self.reset();
                });
            }, this);

            this.handlers_initialized = true;
        },
        
        // reset actions
        reset: function() {
            var prev_action = this.selected_action;
            this.selected_action = false;
            this.vm.clear_pending_action();
            this.trigger("change", {'action': prev_action, 'vm': this.vm, 'view': this, remove: true});
            this.trigger("remove", {'action': prev_action, 'vm': this.vm, 'view': this, remove: true});
        },
        
        // set selected action
        set: function(action_name) {
            if (action_name == "snapshot") { return }
            this.selected_action = action_name;
            this.vm.update_pending_action(this.selected_action);
            this.view.vm(this.vm).find(".action-indicator").show().removeClass().addClass(action_name + " action-indicator");
            this.trigger("change", {'action': this.selected_action, 'vm': this.vm, 'view': this});
        },

        update: function() {
        }
    })


    views.VMActionsView.STATUS_ACTIONS = { 
        'reboot':        ['UNKOWN', 'ACTIVE', 'REBOOT'],
        'shutdown':      ['UNKOWN', 'ACTIVE', 'REBOOT'],
        'console':       ['ACTIVE'],
        'start':         ['UNKOWN', 'STOPPED'],
        'resize':        ['UNKOWN', 'ACTIVE', 'STOPPED', 'REBOOT', 'ERROR', 'BUILD'],
        'snapshot':      ['ACTIVE', 'STOPPED'],
        'destroy':       ['UNKOWN', 'ACTIVE', 'STOPPED', 'REBOOT', 'ERROR', 'BUILD']
    };

    // UI helpers
    var uihelpers = snf.ui.helpers = {};
    
    // OS icon helpers
    var os_icon = uihelpers.os_icon = function(os) {
        var icons = window.os_icons;
        if (!icons) { return "unknown" }
        if (icons.indexOf(os) == -1) {
            os = "unknown";
        }
        return os;
    }

    var os_icon_path = uihelpers.os_icon_path = function(os, size, active) {
        size = size || "small";
        if (active == undefined) { active = true };

        var icon = os_icon(os);
        if (active) {
            icon = icon + "-on";
        } else {
            icon = icon + "-off";
        }

        return (snf.config.machines_icons_url + "{0}/{1}.png").format(size, icon)
    }

    var os_icon_tag = uihelpers.os_icon_tag = function (os, size, active, attrs) {
        attrs = attrs || {};
        return '<img src="{0}" />'.format(os_icon_path(os, size, active));
    }

    // VM Icon helpers
    //
    // identify icon
    var vm_icon = uihelpers.vm_icon = function(vm) {
        return os_icon(vm.get_os());
    }
    
    // get icon url
    var vm_icon_path = uihelpers.vm_icon_path = function(vm, size) {
        return os_icon_path(vm.get_os(), size, vm.is_active());
    }
    
    // get icon IMG tag
    var vm_icon_tag = uihelpers.vm_icon_tag = function (vm, size, attrs) {
       return os_icon_tag(vm.get_os(), size, vm.is_active(), attrs);
    }
    

    snf.ui = _.extend(snf.ui, bb.Events);
    snf.ui.trigger_error = function(code, msg, error, extra) {
        if (msg.match(/Script error/i)) {
          // No usefull information to display in this case. Plus it's an
          // exception that probably doesn't affect our app.
          return 0;
        }
        snf.ui.trigger("error", { code:code, msg:msg, error:error, extra:extra || {} });
    };
    
    views.VMPortView = views.ext.ModelView.extend({
      tpl: '#vm-port-view-tpl',
      classes: 'inner-item port-item clearfix',
      
      update_in_progress: function() {
        if (this.model.get("in_progress_no_vm")) {
          this.set_in_progress();
        } else {
          this.unset_in_progress();
        }
      },

      set_in_progress: function() {
        this.el.find(".type").hide();
        this.el.find(".in-progress").removeClass("hidden").show();
      },

      unset_in_progress: function() {
        this.el.find(".type").show();
        this.el.find(".in-progress").hide();
      },

      disconnect_port: function(model, e) {
        e && e.stopPropagation();
        var network = this.model.get("network");
        this.model.actions.reset_pending();
        this.model.disconnect(_.bind(this.disconnect_port_complete, this));
      },

      disconnect_port_complete: function() {
      },

      get_network_name: function() {
        var network = this.model.get('network');
        var name = network && network.get('name');
        if (!name) {
          if (network && network.get('is_public')) {
            name = 'Internet'
          } else {
            name = '(no network name)'
          }
        }
        var truncate_length = this.parent_view.options.truncate || 40;
        name = synnefo.util.truncate(name, truncate_length, '...');
        return name || 'Loading...';
      },

      get_network_icon: function() {
        var ico;
        var network = this.model.get('network');
        if (network) {
          ico = network.get('is_public') ? 'internet-small.png' : 'network-small.png';
        } else {
          ico = 'network-small.png';
        }
        return synnefo.config.media_url + 'images/' + ico;
      },
    });
    
    views.VMPortListView = views.ext.CollectionView.extend({
      tpl: '#vm-port-list-view-tpl',
      model_view_cls: views.VMPortView
    });

    views.VMPortIpView = views.ext.ModelView.extend({
      tpl: '#vm-port-ip-tpl',
      css_classes: "clearfix"
    });

    views.VMPortIpsView = views.ext.CollectionView.extend({
      tpl: '#vm-port-ips-tpl',
      model_view_cls: views.VMPortIpView
    });

    views.VMVolumeView = views.ext.ModelView.extend({
      tpl: '#vm-volume-view-tpl',
      classes: 'volume-item clearfix inner-item',
      show_snapshot_create_overlay: function() {
        var vm = this.model.get('vm');
        if (!vm) { return }
        synnefo.ui.main.create_snapshot_view.show(vm, this.model);
      }

    });

    views.VMVolumeListView = views.ext.CollectionView.extend({
      tpl: '#vm-volume-list-view-tpl',
      model_view_cls: views.VMVolumeView    });      

})(this);
