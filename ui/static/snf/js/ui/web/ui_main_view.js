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
    
    views.ErrorView = views.Overlay.extend({
        
        view_id: "error_view",
        content_selector: "#error-overlay-content",
        css_class: 'overlay-error',
        overlay_id: "error-overlay",

        initialize: function() {
            views.ErrorView.__super__.initialize.apply(this, arguments);
            var self = this;

            this.error_state = false;

            this.$(".actions .show-details, .actions .hide-details").click(function() {
                self.$(".error-details").toggle();
                self.$(".show-details").toggle();
                self.$(".hide-details").toggle();
            });

            this.$(".key.details").click(function() {
                $(this).next().toggle();
                if (!$(this).next().is(":visible")) {
                    $(this).addClass("expand");
                } else {
                    $(this).removeClass("expand");
                }
            })

            this.$(".actions .report-error").click(_.bind(function() {
                this.report_error();
            }, this));

            this.$(".actions .hide-details").hide();

            this.$(".reload-app").click(function(){
                window.location.reload(true);
            })
        },

        error_object: function() {
            return {ns:this.ns, code:this.code, message:this.message, details:this.details};
        },

        report_error: function() {
            this.feedback_view = this.feedback_view || ui.main.feedback_view;
            this.feedback_view.show(this.get_report_message(), true, {error: this.error_object()});
        },

        get_report_message: function() {
            var fdb_msg =   "Error report\n" +
                "-------------------" + "\n" +
                "Code: " + this.code + "\n" + 
                "Type: " + this.type + "\n" +
                "Message: " + this.message + "\n" +
                "Module: " + this.ns + "\n" +
                "Details: " + this.details + "\n\n" +
                "Please describe the actions that triggered the error:\n"
            
            return fdb_msg;
        },

        show_error: function(ns, code, message, type, details, error_options) {
            this.error_options = {'allow_report': true, 'allow_reload': true, 'extra_details': {}, 'non_critical': false};

            if (error_options) {
                this.error_options = _.extend(this.error_options, error_options);
            }

            this.hide();

            this.code = code;
            this.ns = ns;
            this.type = type;
            this.details = details ? (details.toString ? details.toString() : details) : undefined;
            this.message = message;

            this.update_details();
            
            if (error_options.non_critical) {
                this.el.addClass("non-critical");
            } else {
                this.el.removeClass("non-critical");
            }

            this.show();
            
            this.$(".actions .show-details").click();
            this.$(".key.details").click();
            this.$(".error-more-details").hide();
        },

        update_details: function() {
            var title = "Application error";
            if (this.ns && this.type) {
                title = this.type + ": " + this.message;
            }
            this.$(".header .title").text(title);
            this.$(".error-code").text(this.code || "");
            this.$(".error-type").text(this.type || "");
            this.$(".error-module").text(this.ns || "");
            this.$(".message p").text(this.message || "");
            this.$(".error-more-details p").html(this.details || "no info");

            this.$(".extra-details").remove();
            _.each(this.error_options.extra_details, function(value, key){
                var opt = $(('<span class="extra-details key">{0}</span>' +
                            '<span class="extra-details value">{1}</span>').format(key, value))
                this.$(".value.error-type").after(opt);
            })

        },

        beforeOpen: function() {
            this.$(".error-details").hide();
            this.$(".show-details").show();
            this.$(".hide-details").hide();

            if (this.error_options.allow_report) {
                this.$(".report-error").show();
            } else {
                this.$(".report-error").hide();
            }

            if (this.error_options.allow_reload) {
                this.$(".reload-app").show();
            } else {
                this.$(".reload-app").hide();
            }
        },

        onClose: function() {
            this.trigger("close", this);
        }
    });

    views.NoticeView = views.Overlay.extend({
    
    });

    views.MultipleActionsView = views.View.extend({
        view_id: "multiple_actions",

        _actions: {},
        el: '#multiple_actions_container',
        
        initialize: function() {
            this.actions = {};
            views.MultipleActionsView.__super__.initialize.call(this);
            this.init_handlers();
            this.update_layout();
            
            // for heavy resize/scroll window events
            // do it `like a boss` 
            this.fix_position = _.throttle(this.fix_position, 50);
            this.show_limit = 1;
        },

        init_handlers: function() {
            
            // position handlers
            $(window).bind("view:change", function(){
            })
            $(window).resize(_.bind(function(){
                this.fix_position();
            }, this));
            $(window).scroll(_.bind(function(){
                this.fix_position();
            }, this));
            var self = this;
            $(this.el).find("button.yes").click(function(){
                self.do_all();
            })
            $(this.el).find("button.no").click(function(){
                self.reset_action_views();
                self.reset();
            });

            storage.vms.bind("change:pending_action", _.bind(function(vm) {
                this.handle_vm_pending_action_change(vm);
            }, this));
        },
    
        handle_vm_pending_action_change: function(vm) {
            if (vm.has_pending_action()) {
                var action = vm.get("pending_action");
                this.add_action(vm, action, ui.main.current_view);
            } else {
                this.remove_action(vm);
            }
        },

        add_action: function(vm, action, view) {
            if (this._actions[vm.id] && this._actions[vm.id].views.indexOf(view) == -1) {
                var new_views = this._actions[vm.id].views;
                new_views.push(view);
                this._actions[vm.id] = {'vm': vm, 'action': action, 'views': new_views};
            } else {
                this._actions[vm.id] = {'vm': vm, 'action': action, 'views': [view]};
            }
            this.update_layout();
        },

        remove_action: function(vm) {
            delete this._actions[vm.id];
            this.update_layout();
        },

        reset: function() {
            this._actions = {};
            this.update_layout();
        },

        do_all: function() {
            _.each(this._actions, function(action){
                action.vm.call(action.action);
            }, this)  
            this.reset_action_views();
        },

        reset_action_views: function() {
            _.each(this._actions, function(action){
                var action = action;
                _.each(action.views, function (view) {
                    try {
                        view.reset();
                        view.update_layout();
                        view.hide_actions();
                    } catch(err) {
                        console.error("view", view, "failed to reset");
                    }
                })
            })  
        },
        
        handle_add: function(data) {
            if (data.remove) {
                this.remove_action(data.vm);
            } else {
                this.add_action(data.vm, data.action, data.view);
            }

            this.update_layout();
        },
        
        fix_position: function() {
            $('.confirm_multiple').removeClass('fixed');
            if (($(this.el).offset().top +$(this.el).height())> ($(window).scrollTop() + $(window).height())) {
                $('.confirm_multiple').addClass('fixed');
            }
        },
        
        set_title: function() {
            $(this.$("p").get(0)).html('Your actions will affect <span class="actionLen"></span> machines');
        },

        set_force_title: function() {
            $(this.$("p").get(0)).html('<span class="actionLen"></span> machines needs to be rebooted for changes to apply');
        },

        check_force_notify: function() {
            this.show_limit = 1;
            this.set_title();
            storage.vms.each(_.bind(function(vm) {
                if (vm.get("force_pending_notify")) {
                    this.show_limit = 0;
                    this.set_force_title(window.force_actions_title);
                }
            }, this));
        },

        update_layout: function() {
            this.check_force_notify();
            if (_.size(this._actions) > this.show_limit) {
                $(this.el).show();
            } else {
                $(this.el).hide();
                return;
            }
            $(this.el).find(".actionLen").text(_.size(this._actions));
            $(window).trigger("resize");
            this.fix_position();
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

            this.el = $("body");
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
            synnefo.ui.bind("error", _.bind(this.handle_ui_error, this));
        },
        
        handle_error_close: function(view) {
            snf.api.stop_calls = false;
            this.update_intervals();
        },

        handle_api_error: function(xhr, type, message) {
            this.error_state = true;
            this.log.error("API ERRROR", arguments);
            
            var xhr = arguments[0];
            var args = util.parse_api_error(arguments);
            
            this.stop_intervals();
            snf.api.stop_calls = true;
            this.error_view.show_error(args.ns, args.code, args.message, args.type, args.details, args);
        },

        handle_ui_error: function(error) {
            error = error + "<br /><br />" + snf.util.stacktrace().replace("at", "<br /><br />at");
            this.error_view.show_error("Application", -1, "Something went wrong", "JS Exception", error);
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
                this.after_load();
            }
        },

        load_nets_and_vms: function() {
            var self = this;
            this.update_status("Loading vms...");
            storage.vms.fetch({refresh:true, update:false, success: function(){
                self.update_status("VMS Loaded.");
                self.check_status()
            }});
            this.update_status("Loading networks...");
            storage.networks.fetch({refresh:true, update:false, success: function(){
                self.update_status("Networks loaded.");
                self.check_status()
            }});
        },  

        init_intervals: function() {
            this._networks = storage.networks.get_fetcher(snf.config.update_interval, snf.config.update_interval/3, 3, true, undefined);
            this._vms = storage.vms.get_fetcher(snf.config.update_interval, snf.config.update_interval/3, 3, true, undefined);
        },

        stop_intervals: function() {
            this._networks.stop();
            this._vms.stop();
        },

        update_intervals: function() {
            this._networks.stop();
            this._networks.start();
            this._vms.stop();
            this._vms.start();
        },

        after_load: function() {
            this.update_status("Setting vms update interval...");
            this.init_intervals();
            this.update_intervals();
            this.update_status("Loaded");
            // FIXME: refactor needed
            // initialize views
            this.initialize_views()
            this.update_status("Initializing overlays...");
            this.init_overlays();
            // display initial view
            this.loaded = true;
            this.show_initial_view();
        },

        load: function() {
            this.error_view = new views.ErrorView();
            this.error_view.bind("close", _.bind(this.handle_error_close, this));
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
            this.feedback_view = new views.FeedbackView();
            
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
                    } catch (err) {snf.ui.trigger("error", err)}
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
            // same view, visible
            // get out of here asap
            if (this.current_view && 
                this.current_view.id == view_id && 
                this.current_view.visible()) {
                return;
            }

            view_id = this.identify_view(view_id);
            // add/create view and update current view
            var view = this.add_view(view_id);

            this.current_view = view;
            this.current_view_id = view_id;

            // hide all other views
            this.hide_views([this.current_view]);
            
            // FIXME: depricated
            $(".large-spinner").remove();

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
            
            this.trigger("view:change", this.current_view.view_id);
            $(window).trigger("view:change");
            storage.vms.reset_pending_actions();
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

})(this);
