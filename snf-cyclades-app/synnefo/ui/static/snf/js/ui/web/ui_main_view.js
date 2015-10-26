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

    var views = snf.views = snf.views || {}

    // shortcuts
    var bb = root.Backbone;
    var util = snf.util;
    
    // generic details overlay view.
    views.DetailsView = views.Overlay.extend({
        view_id: "details_view",
        
        content_selector: "#details-overlay",
        css_class: 'overlay-api-info overlay-info',
        overlay_id: "overlay-details",

        subtitle: "",
        title: "Details",
        
        show: function(title, msg, content) {
            this.title = title;
            this.msg = msg;
            this.content = content;
            views.DetailsView.__super__.show.apply(this);
        },

        beforeOpen: function() {
            this.set_title(this.title);
            if (!this.msg) { 
                this.$(".description.intro").hide() 
            } else {
                this.$(".description.intro").html(this.msg).show();
            }

            if (!this.content) { 
                this.$(".description.subinfo").hide() 
            } else {
                this.$(".description.subinfo").html(this.content).show(); 
            };
        }

    });

    views.SuspendedVMView = views.FeedbackView.extend({
        view_id: "suspended_info_view",
        
        css_class: 'overlay-api-info overlay-error non-critical',
        overlay_id: "overlay-api-info",

        subtitle: "",
        title: "VM Suspended",

        beforeOpen: function() {
            views.SuspendedVMView.__super__.beforeOpen.apply(this);
            $(this.$(".form-field label")[0]).html($("#suspended-vm-overlay .description").html())
        },

        show: function(vm, data, collect_data, extra_data, cb) {
            this.vm = vm;
            data = "Suspended VM Details";
            data += "\n====================";
            data += "\nID: " + vm.id;
            data += "\nName: " + vm.get('name');
            var public_ips = vm.get_public_ips();
            _.each(public_ips, function(ip) {
              data += "\nPublic IP{0}: {1}".format(ip.get('type'), ip.get('ip_address'));
            });
            data += "\n\n";
            views.SuspendedVMView.__super__.show.call(this, data, collect_data, extra_data, cb);
        }

    });

    views.ApiInfoView = views.Overlay.extend({
        view_id: "api_info_view",
        
        content_selector: "#api-info-overlay",
        css_class: 'overlay-api-info overlay-info',
        overlay_id: "overlay-api-info",

        subtitle: "",
        title: "API Access",

        beforeOpen: function() {
            var cont = this.$(".copy-content p");
            var token = snf.user.get_token();

            cont.html("");
            cont.text(token);
            
            this.cont = cont;
            this.token = token;
            try { delete this.clip; } catch (err) {};
        },

        onOpen: function() {
            views.ApiInfoView.__super__.onOpen(this, arguments);
            this.clip = new snf.util.ClipHelper(this.cont.parent(), this.token);
        },

        onClose: function() {
            var cont = this.$(".copy-content p");
            var token = snf.user.token;
            cont.html("");
        }
    });

    // TODO: implement me
    views.NoticeView = views.Overlay.extend({});

    views.MultipleActionsView = views.View.extend({
        view_id: "multiple_actions",

        _actions: {},
        el: '#multiple_actions_container',
        
        initialize: function() {
            this.actions = {};
            this.ns_config = {};

            views.MultipleActionsView.__super__.initialize.call(this);

            this.ns_tpl = this.$(".confirm_multiple_actions-template").clone()

            this.init_handlers();
            this.update_layout();
            
            // for heavy resize/scroll window events
            // do it `like a boss` 
            this.fix_position = _.throttle(this.fix_position, 100);
            this.update_layout = _.throttle(this.update_layout, 100);
            this.show_limit = 1;

            this.init_ns("vms", {
                msg_tpl:"Your actions will affect 1 machine",
                msg_tpl_plural:"Your actions will affect {0} machines",
                actions_msg: {confirm: "Confirm all", cancel: "Cancel all"},
                limit: 1,
                cancel_all: function() { snf.storage.vms.reset_pending_actions(); },
                do_all: function() { snf.storage.vms.do_all_pending_actions(); }
            });
            
            this.init_ns("nets", {
                msg_tpl:"Your actions will affect 1 private network",
                msg_tpl_plural:"Your actions will affect {0} private networks",
                actions_msg: {confirm: "Confirm all", cancel: "Cancel all"},
                limit: 1,
                cancel_all: function(actions, config) {
                  _.each(actions, function(action, id) {
                    action.model.actions.reset_pending();
                  });
                },
                do_all: function(actions, config) {
                  _.each(actions, function(action, id) {
                    var action_method = "do_{0}".format(action.actions[0]);
                    action.model[action_method].apply(action.model);
                  });
                }
            });

            this.init_ns("reboots", {
                msg_tpl:"1 machine needs to be rebooted for changes to apply.",
                msg_tpl_plural:"{0} machines needs to be rebooted for changes to apply.",
                actions_msg: {confirm: "Reboot all", cancel: "Cancel all"},
                limit: 0,
                cancel_all: function() { snf.storage.vms.reset_reboot_required(); },
                do_all: function() { snf.storage.vms.do_all_reboots(); }
            });

            this.init_ns("ips", {
                msg_tpl:"Your actions will affect 1 IP address.",
                msg_tpl_plural:"{0} actions will affect {0} IP addresses.",
                actions_msg: {confirm: "Confirm all", cancel: "Cancel all"},
                limit: 1,
                cancel_all: function(actions, config) {
                  _.each(actions, function(action, id) {
                    action.model.actions.reset_pending();
                  });
                },
                do_all: function(actions, config) {
                  _.each(actions, function(action, id) {
                    var action_method = "do_{0}".format(action.actions[0]);
                    action.model[action_method].apply(action.model);
                  });
                }
            });

            this.init_ns("volumes", {
                msg_tpl:"Your actions will affect 1 Volume.",
                msg_tpl_plural:"{0} actions will affect {0} Volumes.",
                actions_msg: {confirm: "Confirm all", cancel: "Cancel all"},
                limit: 1,
                cancel_all: function(actions, config) {
                  _.each(actions, function(action, id) {
                    action.model.actions.reset_pending();
                  });
                },
                do_all: function(actions, config) {
                  _.each(actions, function(action, id) {
                    var action_method = "do_{0}".format(action.actions[0]);
                    action.model[action_method].apply(action.model);
                  });
                }
            });

            this.init_ns("keys", {
                msg_tpl:"Your actions will affect 1 public key.",
                msg_tpl_plural:"{0} actions will affect {0} public keys.",
                actions_msg: {confirm: "Confirm all", cancel: "Cancel all"},
                limit: 1,
                cancel_all: function(actions, config) {
                  _.each(actions, function(action, id) {
                    action.model.actions.reset_pending();
                  });
                },
                do_all: function(actions, config) {
                  _.each(actions, function(action, id) {
                    var action_method = "do_{0}".format(action.actions[0]);
                    action.model[action_method].apply(action.model);
                  });
                }

            });
        },
        
        init_ns: function(ns, params) {
            this.actions[ns] = {};
            var nsconf = this.ns_config[ns] = params || {};
            nsconf.cont = $(this.$("#conirm_multiple_cont_template").clone());
            nsconf.cont.attr("id", "confirm_multiple_cont_" + ns);
            $(this.el).find(".ns-confirms-cont").append(nsconf.cont).addClass(ns);
            $(this.el).find(".ns-confirms-cont").append(nsconf.cont).addClass("confirm-ns");
            nsconf.cont.find(".msg button.yes").text(
                nsconf.actions_msg.confirm).click(_.bind(this.do_all, this, ns));
            nsconf.cont.find(".msg button.no").text(
                nsconf.actions_msg.cancel).click(_.bind(this.cancel_all, this, ns));
        },

        do_all: function(ns) {
            this.ns_config[ns].do_all.apply(this, [this.actions[ns], this.ns_config[ns]]);
        },

        cancel_all: function(ns) {
            this.ns_config[ns].cancel_all.apply(this, [this.actions[ns], this.ns_config[ns]]);
        },
        
        register_actions_ns: function(store, ns) {
          store.bind("action:set-pending", function(action, actions, model) {
            this.handle_action_add(ns, model, [action]);
          }, this);
          store.bind("action:unset-pending", function(action, actions, model) {
            this.handle_action_remove(ns, model, action);
          }, this);
          store.bind("action:reset-pending", function(actions, model) {
            _.each(actions.actions, function(action) {
              this.handle_action_remove(ns, model, action);
            }, this);
          }, this);
        },

        init_handlers: function() {
            var self = this;

            $(window).resize(_.bind(function(){
                this.fix_position();
            }, this));

            $(window).scroll(_.bind(function(){
                this.fix_position();
            }, this));

            storage.vms.bind("change:pending_action", 
                             _.bind(this.handle_action_add, this, "vms"));
            storage.vms.bind("change:reboot_required", 
                             _.bind(this.handle_action_add, this, "reboots"));
            
            var ns_map = {
              'ips': storage.floating_ips,
              'keys': storage.keys,
              'volumes': storage.volumes,
              'nets': storage.networks
            }
            _.each(ns_map, function(store, ns) {
              this.register_actions_ns(store, ns);
            }, this);
        },
        
        handle_action_remove: function(type, model, action) {
          var actions = this.actions[type];
          var model_actions = actions[model.id] && actions[model.id].actions;
          if (!model_actions) { return }
          actions[model.id].actions = _.without(model_actions, action);
          if (actions[model.id].actions.length == 0) {
            delete actions[model.id];
          }
          this.update_layout();
        },

        handle_action_add: function(type, model, action) {
            var actions = this.actions[type];
            
            if (type == "keys") {
                actions[model.id] = {model: model, actions: action};
            }

            if (type == "ips") {
                actions[model.id] = {model: model, actions: action};
            }

            if (type == "volumes") {
                actions[model.id] = {model: model, actions: action};
            }

            if (type == "nets") {
                actions[model.id] = {model: model, actions: action};
            }

            if (type == "vms") {
                _.each(actions, function(action) {
                    if (action.model.id == model.id) {
                        delete actions[action]
                    }
                });

                var actobject = {};
                actobject[action] = [[]];
                actions[model.id] = {model: model, actions: actobject};
                if (typeof action == "undefined") {
                    delete actions[model.id]
                }
            }

            if (type == "reboots") {
                _.each(actions, function(action) {
                    if (action.model.id == model.id) {
                        delete actions[action]
                    }
                });
                var actobject = {};
                actobject['reboot'] = [[]];
                actions[model.id] = {model: model, actions: actobject};
                if (!action) {
                    delete actions[model.id]
                }
            }
            
            this.update_layout();
        },

        update_actions_content: function(ns) {
            var conf = this.ns_config[ns];
            conf.cont.find(".details").empty();
            conf.cont.find(".msg p").text("");
            
            var count = 0;
            var actionscount = 0;
            _.each(this.actions[ns], function(actions, model_id) {
                count++;
                _.each(actions.actions, function(params, act_name){
                    if (_.isString(params)) {
                      actionscount++;
                      return
                    }
                    if (params && params.length) {
                        actionscount += params.length;
                    } else {
                        actionscount++;
                    }
                })
                this.total_confirm_actions++;
            });
            
            var limit = conf.limit;
            if (ui.main.current_view.view_id == "vm_list") {
                limit = 0;
            }

            if (actionscount > limit) {
                conf.cont.show();
                this.confirm_ns_open++;
            } else {
                conf.cont.hide();
            }
            
            var msg = count > 1 ? conf.msg_tpl_plural : conf.msg_tpl;
            conf.cont.find(".msg p").text(msg.format(count));

            return conf.cont;
        },

        fix_position: function() {
            $('.confirm_multiple').removeClass('fixed');
            if (($(this.el).offset().top +$(this.el).height())> ($(window).scrollTop() + $(window).height())) {
                $('.confirm_multiple').addClass('fixed');
            }
        },
        
        update_layout: function() {
            this.confirm_ns_open = 0;
            this.total_confirm_actions = 0;

            $(this.el).show();
            $(this.el).find("#conirm_multiple_cont_template").hide();
            $(this.el).find(".confirm-ns").show();
            
            _.each(this.ns_config, _.bind(function(params, key) {
                this.update_actions_content(key);
            }, this));

            if (this.confirm_ns_open > 0) {
                $(this.el).show();
                this.$(".confirm-all-cont").hide();
                this.$(".ns-confirms-cont").show();
            } else {
                $(this.el).hide();
                this.$(".confirm-all-cont").hide();
                this.$(".ns-confirms-cont").hide();
            }

            $(window).trigger("resize");
        }
    })
    
    // menu wrapper view
    views.SelectView = views.View.extend({
        
        initialize: function(view, router) {
            this.parent = view;
            this.router = router;
            this.pane_view_selector = $(".css-tabs");
            this.machine_view_selector = $("#view-select");
            this.el = $(".css-tabs");
            this.title = $(".tab-name");

            this.set_handlers();
            this.update_layout();

            views.SelectView.__super__.initialize.apply(this, arguments);
        },
        
        clear_active: function() {
            this.pane_view_selector.find("a").removeClass("active");
            this.machine_view_selector.find("a").removeClass("activelink");
        },
        
        // intercept menu links
        set_handlers: function() {
            var self = this;
            this.pane_view_selector.find("a").hover(function(){
                self.title.text($(this).data("hover-title"));
            }, function(){
                self.title.text(self.parent.get_title());
            });

            this.pane_view_selector.find("a#machines_view_link").click(
              _.bind(function(ev){
                ev.preventDefault();
                this.router.vms_index();
              }, this)
            );

            this.pane_view_selector.find("a#networks_view_link").click(
              _.bind(function(ev){
                ev.preventDefault();
                this.router.networks_view();
              }, this)
            );

            this.pane_view_selector.find("a#ips_view_link").click(
              _.bind(function(ev){
                ev.preventDefault();
                this.router.ips_view();
              }, this)
            );

            this.machine_view_selector.find("a#volumes_view_list_link").click(
              _.bind(function(ev){
                ev.preventDefault();
                this.router.volumes_view();
              }, this)
            );

            this.pane_view_selector.find("a#public_keys_view_link").click(
              _.bind(function(ev){
                ev.preventDefault();
                this.router.public_keys_view();
              }, this)
            );
            
            this.machine_view_selector.find("a#machines_view_icon_link").click(
              _.bind(function(ev){
                ev.preventDefault();
                var d = $.now();
                this.router.vms_icon_view();
              }, this)
            );

            this.machine_view_selector.find("a#machines_view_list_link").click(
              _.bind(function(ev){
                ev.preventDefault();
                this.router.vms_list_view();
              }, this)
            );
            
            var selector = "a#machines_view_single_link"
            this.machine_view_selector.find(selector).click(
              _.bind(function(ev){
                ev.preventDefault();
                this.router.vms_single_view();
              }, this)
            );
        },

        update_layout: function() {
            this.clear_active();

            var pane_index = this.parent.pane_ids[this.parent.current_view_id];
            $(this.pane_view_selector.find("a")).removeClass("active");
            $(this.pane_view_selector.find("a").get(pane_index)).addClass("active");
            
            if (this.parent.current_view && this.parent.current_view.vms_view) {

                if (storage.vms.no_ghost_vms().length > 0) {
                    this.machine_view_selector.show();
                    var machine_index = this.parent.views_ids[this.parent.current_view_id];
                    $(this.machine_view_selector.find("a").get(machine_index)).addClass("activelink");
                } else {
                    this.machine_view_selector.hide();
                }
            } else {
                this.machine_view_selector.hide();
            }

        }
    });

    views.MainView = views.View.extend({
        el: 'body',
        view_id: 'main',
        
        // FIXME: titles belong to SelectView
        views_titles: {
            'icon': 'machines', 'single': 'machines', 
            'list': 'machines', 'networks': 'networks',
            'ips': 'IP addresses',
            'volumes': 'disks',
            'public-keys': 'public keys'
        },

        // indexes registry
        views_indexes: {
          0: 'icon', 
          2: 'single', 
          1: 'list', 
          3: 'networks', 
          4: 'ips',
          5: 'volumes',
          6: 'public-keys'
        },

        views_pane_indexes: {
          0: 'single', 
          1: 'networks', 
          2: 'ips', 
          3: 'volumes',
          4: 'public-keys'
        },

        // views classes registry
        views_classes: {
            'icon': views.IconView, 
            'single': views.SingleView, 
            'list': views.ListView, 
            'networks': views.NetworksPaneView, 
            'ips': views.IpsPaneView,
            'volumes': views.VolumesPaneView,
            'public-keys': views.PublicKeysPaneView
        },

        // view ids
        views_ids: {
          'icon': 0, 
          'single': 2, 
          'list': 1, 
          'networks': 3, 
          'ips': 4, 
          'volumes': 5,
          'public-keys': 6
        },

        // on which pane id each view exists
        // machine views (icon,single,list) are all on first pane
        pane_ids: {
          'icon': 0, 
          'single': 0, 
          'list': 0, 
          'volumes': 1, 
          'networks': 2, 
          'ips': 3, 
          'public-keys': 4
        },
    
        initialize: function(show_view) {
            if (!show_view) { show_view = 'icon' };
            
            this.router = snf.router;
            this.empty_hidden = true;
            // fallback to browser error reporting (true for debug)
            this.skip_errors = true

            // reset views
            this.views = {};

            this.el = $("#app");
            // reset main view status
            this._loaded = false;
            this.status = "Initializing...";

            // initialize handlers
            this.init_handlers();

            // identify initial view from user cookies
            // this view will be visible after loading of
            // main view
            this.initial_view = this.session_view();

            views.MainView.__super__.initialize.call(this);

            $(window).focus(_.bind(this.handle_window_focus, this, "focus"));
            $(window).blur(_.bind(this.handle_window_focus, this, "out"));

            this.focused = true;
        },

        handle_window_focus: function(focus) {
            if (!snf.config.delay_on_blur) { return };

            if (focus === "focus") {
                this.focused = true;
                this.set_interval_timeouts();
            } else {
                this.focused = false;
                this.set_interval_timeouts();
            }
        },

        set_interval_timeouts: function(time) {
            _.each(this._fetchers, _.bind(function(fetcher){
                if (!fetcher) { return };
                if (this.focused) {
                    fetcher.interval = fetcher.normal_interval;
                    fetcher.stop(false).start(true);
                } else {
                    fetcher.interval = fetcher.maximum_interval;
                    fetcher.stop(false).start(false);
                }

            }, this));
        },
        
        vms_handlers_registered: false,

        // register event handlers
        // 
        // vms storage events to identify if vms list 
        // is empty and display empty view if user viewing
        // a machine view
        //
        // api/ui error event handlers
        init_handlers: function() {
            // vm handlers
            storage.vms.bind("remove", _.bind(this.check_empty, this));
            storage.vms.bind("add", _.bind(this.check_empty, this));
            storage.vms.bind("change:status", _.bind(this.check_empty, this));
            storage.vms.bind("reset", _.bind(this.check_empty, this));
            storage.quotas.bind("change", _.bind(this.update_create_buttons_status, this));
            // additionally check quotas the first time they get fetched
            storage.quotas.bind("add", _.bind(this.update_create_buttons_status, this));
            
        },
        
        handle_api_error_state: function(state) {
            if (snf.api.error_state === snf.api.STATES.ERROR) {
                this.stop_intervals();
            } else {
                if (this.intervals_stopped) {
                    this.update_intervals();
                }
            }
        },
        
        handle_api_error: function(args) {
            if (arguments.length == 1) { arguments = _.toArray(arguments[0])};

            if (!_.last(arguments).display) {
                return;
            }

            this.error_state = true;
            
            var xhr = arguments[0];
            var args = util.parse_api_error.apply(util, arguments);
            
            // force logout if UNAUTHORIZED request arrives
            if (args.code == 401) { snf.auth_client.redirect_to_login(); return };

            var error_entry = [args.ns, args.code, args.message, 
                               args.api_message, args.type, 
                               args.details, args];
            this.error_view.show_error.apply(this.error_view, error_entry);
        },

        handle_ui_error: function(data) {
            var msg = data.msg, code = data.code, err_obj = data.error;
            error = msg + "<br /><br />" + snf.util.stacktrace().replace("at", "<br /><br />at");
            params = { title: "UI error", extra_details: data.extra };
            delete data.extra.allow_close;
            params.allow_close = data.extra.allow_close === undefined ? true : data.extra.allow_close;
            this.error_view.show_error("UI", -1, msg, undefined, 
                                       "JS Exception", error, params);
        },

        init_overlays: function() {
            this.create_vm_view = new views.VMCreateView();
            this.create_snapshot_view = new views.SnapshotCreateView();
            this.api_info_view = new views.ApiInfoView();
            this.details_view = new views.DetailsView();
            this.suspended_view = new views.SuspendedVMView();
            //this.notice_view = new views.NoticeView();
        },
        
        show_loading_view: function() {
            $("#container #content").hide();
            $("#loading-view").show();
        },

        hide_loading_view: function() {
            $("#container #content").show();
            $("#loading-view").hide();
            $(".css-panes").show();
        },
        
        items_to_load: 8,
        completed_items: 0,
        check_status: function(loaded) {
            this.completed_items++;
            // images, flavors loaded
            if (this.completed_items == this.items_to_load) {
                this.update_status("layout", 1);
                var self = this;
                window.setTimeout(function(){
                    self.after_load();
                }, 10)
            }
        },
            
        load_missing_images: function(cb) {
            synnefo.storage.vms.load_missing_images(cb);
        },

        load_nets_and_vms: function() {
            var self = this;
            this.update_status("vms", 0);
            storage.vms.fetch({refresh:true, update:false, success: function(){
                self.load_missing_images(function(){
                    self.update_status("vms", 1);
                    self.update_status("layout", 0);
                    self.check_status();
                });
            }});

            this.update_status("networks", 0);
            $.when([
                   storage.networks.fetch({refresh: true}), 
                   storage.floating_ips.fetch({refresh: true}),
                   storage.subnets.fetch({refresh: true}),
                   storage.ports.fetch({refresh: true})
            ]).done(function() {
              self.update_status("networks", 1);
              self.check_status();
            })
        },  
        
        _fetchers: {},
        init_interval: function(key, collection) {
            if (this._fetchers[key]) { return }
            var fetcher_params = [snf.config.update_interval, 
                                  snf.config.update_interval_increase || 500,
                                  snf.config.fast_interval || snf.config.update_interval/2, 
                                  snf.config.update_interval_increase_after_calls || 4,
                                  snf.config.update_interval_max || 20000,
                                  true, 
                                  {is_recurrent: true},
                                  key];
            var fetcher = collection.get_fetcher.apply(collection, _.clone(fetcher_params));
            this._fetchers[key] = fetcher;
            collection.fetch();

        },

        init_intervals: function() {
            _.each({
              'networks': storage.networks,
              'vms': storage.vms,
              'quotas': storage.quotas,
              'projects': storage.projects,
              'ips': storage.floating_ips,
              'subnets': storage.subnets,
              'ports': storage.ports,
              'volumes': storage.volumes,
              'keys': storage.keys
            }, function(col, name) {
              this.init_interval(name, col)
            }, this);
        },

        stop_intervals: function() {
            _.each(this._fetchers, function(fetcher) {
                fetcher.stop();
            });
            this.intervals_stopped = true;
        },

        update_intervals: function() {
            _.each(this._fetchers, function(fetcher) {
                fetcher.stop();
                fetcher.start();
            })
            this.intervals_stopped = false;
        },

        after_load: function() {
            var self = this;
            this.init_intervals();
            this.update_intervals();
            this.update_status("layout", 0);
            
            // bypass update_hidden_views in initial view
            // rendering to force all views to get render
            // on their creation
            var uhv = snf.config.update_hidden_views;
            snf.config.update_hidden_views = true;
            this.initialize_views();
            snf.config.update_hidden_views = uhv;

            window.setTimeout(function() {
                self.load_initialize_overlays();
            }, 20);
        },

        load_initialize_overlays: function() {
            this.init_overlays();
            // display initial view
            this.loaded = true;
            
            // application start point
            this.check_empty();
            this.show_initial_view();
        },

        load: function() {
            if (synnefo.config.use_glance) {
                synnefo.glance.register();
            }
            this.error_view = new views.ErrorView();
            this.vm_resize_view = new views.VmResizeView();
            this.vm_reassign_view = new views.VmReassignView();
            this.ip_reassign_view = new views.IPReassignView();
            this.network_reassign_view = new views.NetworkReassignView();
            this.volume_reassign_view = new views.VolumeReassignView();

            // api request error handling
            synnefo.api.bind("error", _.bind(this.handle_api_error, this));
            synnefo.api.bind("change:error_state", _.bind(this.handle_api_error_state, this));
            synnefo.ui.bind("error", _.bind(this.handle_ui_error, this));

            this.feedback_view = new views.FeedbackView();
            
            if (synnefo.config.use_glance) {
                this.custom_images_view = new views.CustomImagesOverlay();
            }

            var self = this;
            // initialize overlay views
            
            // display loading message
            this.show_loading_view();
            this.update_status("flavors", 0);
            storage.flavors.fetch({refresh:true, update:false, success:function(){
                self.update_status("flavors", 1);
                self.check_status()
            }});

            this.update_status("resources", 0);
            storage.resources.fetch({refresh:true, update:false, success: function(){
                self.update_status("resources", 1);
                self.update_status("projects", 0);
                self.check_status();
                storage.projects.fetch({refresh:true, update:true, success: function() {
                  self.update_status("projects", 1);
                  self.update_status("quotas", 0);
                  self.check_status();
                  storage.quotas.fetch({refresh:true, update:true, success: function() {
                    self.update_status("quotas", 1);
                    self.check_status();
                    self.update_status("volumes", 0);
                    storage.volumes.fetch({refresh:true, update:false, success: function(){
                          self.update_status("volumes", 1);
                          self.check_status();
                    }});  

                    // sync load initial data
                    self.update_status("images", 0);
                    storage.images.fetch({refresh:true, update:false, success: function(){
                        self.update_status("images", 1);
                        self.check_status();
                        self.load_nets_and_vms();
                    }});
                  }});
                }})
            }})
        },

        update_status: function(ns, state) {
            var el = $("#loading-view .header."+ns);
            if (state == 0) {
                el.removeClass("off").addClass("on");
            }
            if (state == 1) {
                el.removeClass("on").addClass("done");
            }
        },

        initialize_views: function() {
            this.select_view = new views.SelectView(this, this.router);
            this.empty_view = new views.EmptyView();
            this.metadata_view = new views.MetadataView();
            this.multiple_actions_view = new views.MultipleActionsView();
            
            this.add_view("icon");
            this.add_view("list");
            this.add_view("single");
            this.add_view("networks");
            this.add_view("ips");
            this.add_view("public-keys");

            this.init_menu();
        },

        init_menu: function() {
            $(".usermenu .feedback").click(_.bind(function(e){
                e.preventDefault();
                this.feedback_view.show();
            }, this));
        },
        
        // initial view based on user cookie
        show_initial_view: function() {
          this.set_vm_view_handlers();
          this.hide_loading_view();
          bb.history.start();
          this.trigger("ready");
        },

        show_vm_details: function(vm) {
            if (vm) {
              this.router.vm_details_view(vm.id);
            }
        },
        
        update_create_buttons_status: function() {
            var vms = storage.quotas.can_create('vm');
            var create_button = $("#createcontainer #create"); 
            var msg = snf.config.limit_reached_msg;
            if (!vms) {
                create_button.addClass("disabled");
                snf.util.set_tooltip(create_button, msg, {tipClass: 'warning tooltip'});
            } else {
                create_button.removeClass("disabled");
                snf.util.unset_tooltip(create_button);
            }
        },

        set_vm_view_handlers: function() {
            var self = this;
            $("#createcontainer #create").click(function(e){
                e.preventDefault();
                if ($(this).hasClass("disabled")) { return }
                self.router.vm_create_view();
            });
        },

        check_empty: function() {
            if (!this.loaded) { return }
            if (storage.vms.no_ghost_vms().length == 0) {
                if (!(this.current_view instanceof synnefo.views.VMListView)) { 
                  this.show_empty();
                  return;
                }
                this.show_view("machines");
                this.router.show_welcome();
                this.empty_hidden = false;
            } else {
                this.hide_empty();
            }
        },

        show_empty: function() {
            if (!this.empty_hidden) { return };
            $("#machines-pane-top").addClass("empty");

            this.$(".panes").hide();
            this.$("#machines-pane").show();

            this.hide_views([]);
            this.empty_hidden = false;
            this.empty_view.show();
            this.select_view.update_layout();
            this.empty_hidden = false;
        },

        hide_empty: function() {
            if (this.empty_hidden) { return };
            $("#machines-pane-top").removeClass("empty");

            this.empty_view.hide(true);
            this.router.vms_index();
            this.empty_hidden = true;
            this.select_view.update_layout();
        },
        
        get_title: function(view_id) {
            var view_id = view_id || this.current_view_id;
            return this.views_titles[view_id];
        },

        // return class object for the given view or false if
        // the view is not registered
        get_class_for_view: function (view_id) {
            if (!this.views_classes[view_id]) {
                return false;
            }
            return this.views_classes[view_id];
        },

        view: function(view_id) {
            return this.views[view_id];
        },

        add_view: function(view_id) {
            if (!this.views[view_id]) {
                var cls = this.get_class_for_view(view_id);
                if (this.skip_errors) {
                    this.views[view_id] = new cls();
                    $(this.views[view_id]).bind("resize", _.bind(function() {
                        window.forcePositionFooter();
                        this.multiple_actions_view.fix_position();
                    }, this));
                } else {
                    // catch ui errors
                    try {
                        this.views[view_id] = new cls();
                        $(this.views[view_id]).bind("resize", _.bind(function() {
                            window.positionFooter();
                            this.multiple_actions_view.fix_position();
                        }, this));
                    } catch (err) {snf.ui.trigger_error(-1, "Cannot add view", err)}
                }
            } else {
            }

            if (this.views[view_id].vms_view) {
                this.views[view_id].metadata_view = this.metadata_view;
            }
            return this.views[view_id];
        },
            
        hide_views: function(skip) {
            _.each(this.views, function(view) {
                if (skip.indexOf(view) === -1) {
                    view.hide();
                }
            }, this)
        },
        
        get: function(view_id) {
            return this.views[view_id];
        },
        
        session_view: function() {
            if (this.pane_view_from_session() > 0) {
                return this.views_pane_indexes[this.pane_view_from_session()];
            } else {
                return this.views_indexes[this.machine_view_from_session()];
            }
        },

        pane_view_from_session: function() {
            return $.cookie("pane_view") || 0;
        },

        machine_view_from_session: function() {
            return $.cookie("machine_view") || 0;
        },

        update_session: function() {
            $.cookie("pane_view", this.pane_ids[this.current_view_id]);
            if (this.current_view.vms_view) {
                $.cookie("machine_view", this.views_ids[this.current_view_id]);
            }
        },

        identify_view: function(view_id) {
            // machines view_id is an alias to
            // one of the 3 machines view
            // identify which one (if no cookie set defaults to icon)
            if (view_id == "machines") {
                var index = this.machine_view_from_session();
                view_id = this.views_indexes[index];
            }
            return view_id;
        },
        
        // switch to current view pane
        // if differs from the visible one
        show_view_pane: function() {
            if (this.current_view.pane != this.current_pane) {
                $(this.current_view.pane).show();
                $(this.current_pane).hide();
                this.current_pane = this.current_view.pane;
            }
        },
        
        show_view: function(view_id) {
            //var d = new Date;
            var ret = this._show_view(view_id);
            //console.log((new Date)-d)
            return ret;
        },

        _show_view: function(view_id) {
                // same view, visible
                // get out of here asap
                if (this.current_view && 
                    this.current_view.id == view_id && 
                    this.current_view.visible()) {
                    return;
                }
                
                // choose proper view_id
                view_id = this.identify_view(view_id);

                // add/create view and update current view
                var view = this.add_view(view_id);
                
                // set current view
                this.current_view = view;
                this.current_view_id = view_id;

                // hide all other views
                this.hide_views([this.current_view]);
                
                // FIXME: depricated
                $(".large-spinner").remove();

                storage.vms.reset_pending_actions();
                //storage.networks.reset_pending_actions();
                storage.vms.stop_stats_update();

                // show current view
                this.show_view_pane();
                view.show(true);
                
                // update menus
                if (this.select_view) {
                    this.select_view.update_layout();
                }

                var update_layout = this.current_view.__update_layout;
                update_layout && update_layout.call(this.current_view);

                // update cookies
                this.update_session();
                
                // machines view subnav
                if (this.current_view.vms_view) {
                    $("#machines-pane").show();
                } else {
                    $("#machines-pane").hide();
                }
                
                // fix footer position
                // TODO: move footer handlers in
                // main view (from home.html)
                if (window.positionFooter) {
                    window.positionFooter();
                }

                // trigger view change event
                this.trigger("view:change", this.current_view.view_id);
                this.select_view.title.text(this.get_title());
                $(window).trigger("view:change");
                return view;
        },

        reset_vm_actions: function() {
        
        },
        
        // identify current view
        // based on views element visibility
        current_view_id: function() {
            var found = false;
            _.each(this.views, function(key, value) {
                if (value.visible()) {
                    found = value;
                }
            })
            return found;
        }

    });

    snf.ui.main = new views.MainView();
    
    snf.ui.init = function() {
        if (snf.config.handle_window_exceptions) {
            window.onerror = function(msg, file, line) {
                snf.ui.trigger_error("CRITICAL", msg, {}, { file:file + ":" + line, allow_close: true });
            };
        }
        snf.ui.main.load();
    }

})(this);
