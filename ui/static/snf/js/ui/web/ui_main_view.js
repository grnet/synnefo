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
    
    // TODO: implement me
    views.NoticeView = views.Overlay.extend({});

    views.MultipleActionsView = views.View.extend({
        view_id: "multiple_actions",

        _actions: {},
        el: '#multiple_actions_container',
        
        initialize: function() {
            this.actions = {};
            views.MultipleActionsView.__super__.initialize.call(this);
            
            // view elements
            this.confirm_actions = this.$(".confirm_multiple_actions");
            this.confirm_actions_yes = this.$(".confirm_multiple_actions button.yes");
            this.confirm_actions_no = this.$(".confirm_multiple_actions button.no");
            this.confirm_reboot = this.$(".confirm_reboot_required");
            this.confirm_reboot_yes = this.$(".confirm_reboot_required button.yes");
            this.confirm_reboot_no = this.$(".confirm_reboot_required button.no");
            this.confirm_reboot_list = this.confirm_reboot.find(".reboot-machines-list");

            this.init_handlers();
            this.update_layout();
            
            // for heavy resize/scroll window events
            // do it `like a boss` 
            this.fix_position = _.throttle(this.fix_position, 100);
            this.update_layout = _.throttle(this.update_layout, 100);
            this.show_limit = 1;
        },

        init_handlers: function() {
            var self = this;

            $(window).resize(_.bind(function(){
                this.fix_position();
            }, this));

            $(window).scroll(_.bind(function(){
                this.fix_position();
            }, this));
            
            // confirm/cancel button handlers
            var self = this;
            this.confirm_actions_yes.click(function(){ self.do_all(); })
            this.confirm_actions_no.click(function(){
                self.reset_actions();
            });

            this.confirm_reboot_yes.click(function(){ self.do_reboot_all(); })
            this.confirm_reboot_no.click(function(){
                self.reset_reboots();
            });

            storage.vms.bind("change:pending_action", _.bind(this.handle_vm_change, this));
            storage.vms.bind("change:reboot_required", _.bind(this.handle_vm_change, this));

        },

        handle_vm_change: function(vm) {
            if (vm.has_pending_action()) {
                var action = vm.get("pending_action");
                this.add_action(vm, action);
            } else {
                this.remove_action(vm);
            }
            this.update_layout();
        },

        add_action: function(vm, action) {
            this._actions[vm.id] = {'vm': vm, 'action': action};
        },

        remove_action: function(vm) {
            delete this._actions[vm.id];
        },

        reset: function() {
            this._actions = {};
            this.update_layout();
        },
        
        reboot_vm: function(vm) {
            vm.call("reboot");
        },

        do_reboot_all: function() {
            _.each(storage.vms.get_reboot_required(), function(vm){
                this.reboot_vm(vm)
            }, this)  
        },

        do_all: function() {
            _.each(this._actions, function(action){
                action.vm.call(action.action);
            }, this)  
            this.reset_actions();
        },

        reset_reboots: function () {
            _.each(storage.vms.get_reboot_required(), function(vm) {vm.set({'reboot_required': false})}, this);
            this.update_layout();
        },

        reset_actions: function() {
            _.each(this._actions, _.bind(function(action){
                try {
                    action.vm.clear_pending_action();
                    this.remove_action(action.vm);
                } catch(err) {
                    console.error("vm " + action.vm.id + " failed to reset", err);
                }
            }, this))  
        },
        
        fix_position: function() {
            $('.confirm_multiple').removeClass('fixed');
            if (($(this.el).offset().top +$(this.el).height())> ($(window).scrollTop() + $(window).height())) {
                $('.confirm_multiple').addClass('fixed');
            }
        },
        
        check_notify_limit: function() {
            this.show_limit = 1;
            if (ui.main.current_view && ['networks', 'vm_list'].indexOf(ui.main.current_view.view_id) > -1) {
                this.show_limit = 0;
            }
        },
        
        update_reboot_required_list: function(vms) {
            this.confirm_reboot_list.empty();
        },

        update_reboot_required: function() {
            var vms = storage.vms.get_reboot_required();
            if (vms.length) {
                this.confirm_reboot.find(".actionLen").text(vms.length);
                this.update_reboot_required_list();
                this.confirm_reboot.show();
                $(this.el).show();
            } else {
                if (!this.actions_visible) {
                   $(this.el).hide();
                }
                this.confirm_reboot.hide();
            }
        },

        update_layout: function() {
            this.check_notify_limit();
            this.actions_visible = false;

            if (_.size(this._actions) > this.show_limit) {
                this.actions_visible = true;
                $(this.el).show();
                this.confirm_actions.show();
            } else {
                $(this.el).hide();
                this.confirm_actions.hide();
            }

            this.update_reboot_required();
            this.confirm_actions.find(".actionLen").text(_.size(this._actions));
            $(window).trigger("resize");
        }
    })
    
    // menu wrapper view
    views.SelectView = views.View.extend({
        
        initialize: function(view) {
            this.parent = view;

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
                // FIXME: title from href ? omg
                self.title.text($(this).attr("href"));
            }, function(){
                self.title.text(self.parent.get_title());
            });

            this.pane_view_selector.find("a#machines_view_link").click(_.bind(function(ev){
                ev.preventDefault();
                this.parent.show_view("machines");
            }, this))
            this.pane_view_selector.find("a#networks_view_link").click(_.bind(function(ev){
                ev.preventDefault();
                this.parent.show_view("networks");
            }, this))
            this.pane_view_selector.find("a#disks_view_link").click(_.bind(function(ev){
                ev.preventDefault();
                this.parent.show_view("disks");
            }, this))
            
            this.machine_view_selector.find("a#machines_view_icon_link").click(_.bind(function(ev){
                ev.preventDefault();
                var d = $.now();
                this.parent.show_view("icon");
            }, this))
            this.machine_view_selector.find("a#machines_view_list_link").click(_.bind(function(ev){
                ev.preventDefault();
                this.parent.show_view("list");
            }, this))
            this.machine_view_selector.find("a#machines_view_single_link").click(_.bind(function(ev){
                ev.preventDefault();
                this.parent.show_view("single");
            }, this))
        },

        update_layout: function() {
            this.clear_active();

            var pane_index = this.parent.pane_ids[this.parent.current_view_id];
            $(this.pane_view_selector.find("a")).removeClass("active");
            $(this.pane_view_selector.find("a").get(pane_index)).addClass("active");
            
            if (this.parent.current_view && this.parent.current_view.vms_view) {

                if (storage.vms.length > 0) {
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
            'disks': 'disks'
        },

        // indexes registry
        views_indexes: {0: 'icon', 2:'single', 1: 'list', 3:'networks'},
        views_pane_indexes: {0:'single', 1:'networks', 2:'disks'},

        // views classes registry
        views_classes: {'icon': views.IconView, 'single': views.SingleView, 
            'list': views.ListView, 'networks': views.NetworksView},

        // view ids
        views_ids: {'icon':0, 'single':2, 'list':1, 'networks':3},

        // on which pane id each view exists
        // machine views (icon,single,list) are all on first pane
        pane_ids: {'icon':0, 'single':0, 'list':0, 'networks':1, 'disks':2},
    
        initialize: function(show_view) {
            if (!show_view) { show_view = 'icon' };
            
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
                this.set_interval_timeouts(snf.config.update_interval);
            } else {
                this.focused = false;
                this.set_interval_timeouts(snf.config.blur_delay);
            }
        },

        set_interval_timeouts: function(time) {
            _.each([this._networks, this._vms], function(fetcher){
                if (!fetcher) { return };
                fetcher.timeout = time;
                fetcher.stop().start();
            })
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
            storage.vms.bind("change", _.bind(this.check_empty, this));
            storage.vms.bind("reset", _.bind(this.check_empty, this));
            
            // api calls handlers
            synnefo.api.bind("error", _.bind(this.handle_api_error, this));
            synnefo.api.bind("change:error_state", _.bind(this.handle_api_error_state, this));
            synnefo.ui.bind("error", _.bind(this.handle_ui_error, this));
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
            if (args.code == 401) { snf.ui.logout(); return };

            var error_entry = [args.ns, args.code, args.message, args.type, args.details, args];
            this.error_view.show_error.apply(this.error_view, error_entry);
        },

        handle_ui_error: function(data) {
            var msg = data.msg, code = data.code, err_obj = data.error;
            error = msg + "<br /><br />" + snf.util.stacktrace().replace("at", "<br /><br />at");
            params = { title: "UI error", extra_details: data.extra };
            params.allow_close = data.extra.allow_close === undefined ? true : data.extra.allow_close;
            this.error_view.show_error("UI", -1, msg, "JS Exception", error, params);
        },

        init_overlays: function() {
            this.create_vm_view = new views.CreateVMView();
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
        
        items_to_load: 4,
        completed_items: 0,
        check_status: function(loaded) {
            this.completed_items++;
            // images, flavors loaded
            if (this.completed_items == 2) {
                this.load_nets_and_vms();
            }

            if (this.completed_items == this.items_to_load) {
                this.update_status("Rendering layout");
                var self = this;
                window.setTimeout(function(){
                    self.after_load();
                }, 100)
            }
        },

        load_nets_and_vms: function() {
            var self = this;
            this.update_status("Loading vms...");
            storage.vms.fetch({refresh:true, update:false, success: function(){
                self.update_status("VMS Loaded.");
                self.check_status();
            }});

            this.update_status("Loading networks...");
            storage.networks.fetch({refresh:true, update:false, success: function(){
                self.update_status("Networks loaded.");
                self.check_status();
            }});
        },  

        init_intervals: function() {
            this._networks = storage.networks.get_fetcher(snf.config.update_interval, 
                                                          snf.config.update_interval / 2, 
                                                          1, true, undefined);
            this._vms = storage.vms.get_fetcher(snf.config.update_interval, 
                                                snf.config.update_interval / 2, 
                                                1, true, undefined);
        },

        stop_intervals: function() {
            if (this._networks) { this._networks.stop(); }
            if (this._vms) { this._vms.stop(); }
            this.intervals_stopped = true;
        },

        update_intervals: function() {
            if (this._networks) {
                this._networks.stop();
                this._networks.start();
            } else {
                this.init_intervals();
            }

            if (this._vms) {
                this._vms.stop();
                this._vms.start();
            } else {
                this.init_intervals();
            }

            this.intervals_stopped = false;
        },

        after_load: function() {
            this.update_status("Setting vms update interval...");
            this.init_intervals();
            this.update_intervals();
            this.update_status("Loaded");
            // FIXME: refactor needed
            // initialize views
            
            // bypass update_hidden_views in initial view
            // rendering to force all views to get render
            // on their creation
            var uhv = snf.config.update_hidden_views;
            snf.config.update_hidden_views = true;
            this.initialize_views()

            this.update_status("Initializing overlays...");
            this.init_overlays();
            // display initial view
            this.loaded = true;
            this.show_initial_view();
            this.check_empty();
            snf.config.update_hidden_views = uhv;
        },

        load: function() {
            this.error_view = new views.ErrorView();
            this.feedback_view = new views.FeedbackView();
            var self = this;
            // initialize overlay views
            
            // display loading message
            this.show_loading_view();
            // sync load initial data
            this.update_status("Loading images...");
            storage.images.fetch({refresh:true, update:false, success: function(){
                self.check_status()
            }});
            this.update_status("Loading flavors...");
            storage.flavors.fetch({refresh:true, update:false, success:function(){
                self.check_status()
            }});
        },

        update_status: function(msg) {
            this.log.debug(msg)
            this.status = msg;
            $("#loading-view .info").removeClass("hidden")
            $("#loading-view .info").text(this.status);
        },

        initialize_views: function() {
            this.empty_view = new views.EmptyView();
            this.select_view = new views.SelectView(this);
            this.metadata_view = new views.MetadataView();
            this.multiple_actions_view = new views.MultipleActionsView();
            
            this.add_view("icon");
            this.add_view("list");
            this.add_view("single");
            this.add_view("networks");

            this.init_menu();
        },

        init_menu: function() {
            $(".usermenu .feedback").click(_.bind(function(){
                this.feedback_view.show();
            }, this));
        },
        
        // initial view based on user cookie
        show_initial_view: function() {
          this.set_vm_view_handlers();
          this.hide_loading_view();
          this.show_view(this.initial_view);
          this.trigger("initial");
        },

        show_vm_details: function(vm) {
            snf.ui.main.show_view("single")
            snf.ui.main.current_view.show_vm(vm);
        },

        set_vm_view_handlers: function() {
            $("#createcontainer #create").click(_.bind(function(){
                this.create_vm_view.show();
            }, this))
        },

        check_empty: function() {
            if (!this.loaded) { return }
            if (storage.vms.length == 0) {
                this.show_view("machines");
                this.show_empty();
            } else {
                this.hide_empty();
            }
            this.select_view.update_layout();
        },

        show_empty: function() {
            $("#machines-pane-top").addClass("empty");

            this.$(".panes").hide();
            this.$("#machines-pane").show();

            this.hide_views([]);
            this.empty_view.show();
        },

        hide_empty: function() {
            $("#machines-pane-top").removeClass("empty");

            this.empty_view = new views.EmptyView();
            this.empty_view.hide();
            if (this.current_view && !this.current_view.visible()) { 
                this.current_view.show(); 
            }
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
                        window.positionFooter();
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
                    $(view.el).hide();
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
            try {
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
                storage.vms.stop_stats_update();

                // show current view
                this.show_view_pane();
                view.show();
                
                // update menus
                if (this.select_view) {
                    this.select_view.update_layout();
                }
                this.current_view.__update_layout();

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
            } catch (err) {
                snf.ui.trigger_error(-2, "Cannot show view: " + view_id, err);
            }
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
    
    snf.ui.logout = function() {
        $.cookie("X-Auth-Token", null);
        if (snf.config.logout_url !== undefined)
        {
            window.location = snf.config.logout_url;
        } else {
            window.location.reload();
        }
    }

    snf.ui.init = function() {
        if (snf.config.handle_window_exceptions) {
            window.onerror = function(msg, file, line) {
                snf.ui.trigger_error("CRITICAL", msg, {}, { file:file + ":" + line, allow_close: false });
            };
        }
        snf.ui.main.load();
    }

})(this);
