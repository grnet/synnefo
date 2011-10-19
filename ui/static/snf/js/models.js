;(function(root){
    
    // root
    var root = root;
    
    // setup namepsaces
    var snf = root.synnefo = root.synnefo || {};
    var models = snf.models = snf.models || {}
    var storage = snf.storage = snf.storage || {};
    var util = snf.util = snf.util || {};

    // shortcuts
    var bb = root.Backbone;
    var slice = Array.prototype.slice

    // logging
    var logger = new snf.logging.logger("SNF-MODELS");
    var debug = _.bind(logger.debug, logger);
    
    // get url helper
    var getUrl = function(baseurl) {
        var baseurl = baseurl || snf.config.api_url;
        return baseurl + "/" + this.path;
    }
    
    // i18n
    BUILDING_MESSAGES = window.BUILDING_MESSAGES || {'INIT': 'init', 'COPY': '{0}, {1}, {2}', 'FINAL': 'final'};

    // Base object for all our models
    models.Model = bb.Model.extend({
        sync: snf.api.sync,
        api: snf.api,
        has_status: false,

        initialize: function() {
            if (this.has_status) {
                this.bind("change:status", this.handle_remove);
                this.handle_remove();
            }
            models.Model.__super__.initialize.apply(this, arguments)
        },

        handle_remove: function() {
            if (this.get("status") == 'DELETED') {
                if (this.collection) {
                    try { this.clear_pending_action();} catch (err) {};
                    try { this.reset_pending_actions();} catch (err) {};
                    try { this.stop_stats_update();} catch (err) {};
                    this.collection.remove(this.id);
                }
            }
        },
        
        // custom set method to allow submodels to use
        // set_<attr> methods for handling the value of each
        // attribute and overriding the default set method
        // for specific parameters
        set: function(params, options) {
            _.each(params, _.bind(function(value, key){
                if (this["set_" + key]) {
                    params[key] = this["set_" + key](value);
                }
            }, this))
            var ret = bb.Model.prototype.set.call(this, params, options);
            return ret;
        },

        url: function(options) {
            return getUrl.call(this, this.base_url) + "/" + this.id;
        },

        api_path: function(options) {
            return this.path + "/" + this.id;
        },

        parse: function(resp, xhr) {
            return resp.server;
        },

        remove: function() {
            this.api.call(this.api_path(), "delete");
        },

        changedKeys: function() {
            return _.keys(this.changedAttributes() || {});
        },

        hasOnlyChange: function(keys) {
            var ret = false;
            _.each(keys, _.bind(function(key) {
                if (this.changedKeys().length == 1 && this.changedKeys().indexOf(key) > -1) { ret = true};
            }, this));
            return ret;
        }

    })
    
    // Base object for all our model collections
    models.Collection = bb.Collection.extend({
        sync: snf.api.sync,
        api: snf.api,
        supportIncUpdates: true,
        url: function(options) {
            return getUrl.call(this, this.base_url) + (options.details || this.details ? '/detail' : '');
        },

        fetch: function(options) {
            // default to update
            if (!this.noUpdate) {
                if (!options) { options = {} };
                if (options.update === undefined) { options.update = true };
                if (!options.removeMissing && options.refresh) { options.removeMissing = true };
            }
            // custom event foreach fetch
            return bb.Collection.prototype.fetch.call(this, options)
        },

        get_fetcher: function(timeout, fast, limit, initial, params) {
            var fetch_params = params || {};
            fetch_params.skips_timeouts = true;

            var timeout = parseInt(timeout);
            var fast = fast || 1000;
            var limit = limit;
            var initial_call = initial || true;
            
            var last_ajax = undefined;
            var cb = _.bind(function() {
                // clone to avoid referenced objects
                var params = _.clone(fetch_params);
                updater._ajax = last_ajax;
                if (last_ajax) {
                    last_ajax.abort();
                }
                last_ajax = this.fetch(params);
            }, this);
            var updater = new snf.api.updateHandler({'callback': cb, timeout:timeout, 
                                                    fast:fast, limit:limit, 
                                                    call_on_start:initial_call});

            snf.api.bind("call", _.throttle(_.bind(function(){ updater.faster(true)}, this)), 1000);
            return updater;
        }
    });
    
    // Image model
    models.Image = models.Model.extend({
        path: 'images',

        get_size: function() {
            return parseInt(this.get('metadata') ? this.get('metadata').values.size : -1)
        },

        get_readable_size: function() {
            return this.get_size() > 0 ? util.readablizeBytes(this.get_size() * 1024 * 1024) : "unknown";
        },

        get_os: function() {
            return this.get("OS");
        },

        get_sort_order: function() {
            return parseInt(this.get('metadata') ? this.get('metadata').values.sortorder : -1)
        }
    });

    // Flavor model
    models.Flavor = models.Model.extend({
        path: 'flavors',

        details_string: function() {
            return "{0} CPU, {1}MB, {2}GB".format(this.get('cpu'), this.get('ram'), this.get('disk'));
        },

        get_disk_size: function() {
            return parseInt(this.get("disk") * 1000)
        }

    });
    
    //network vms list helper
    var NetworkVMSList = function() {
        this.initialize = function() {
            this.vms = [];
            this.pending = [];
            this.pending_for_removal = [];
        }
        
        this.add_pending_for_remove = function(vm_id) {
            if (this.pending_for_removal.indexOf(vm_id) == -1) {
                this.pending_for_removal.push(vm_id);
            }

            if (this.pending_for_removal.length) {
                this.trigger("pending:remove:add");
            }
        },

        this.add_pending = function(vm_id) {
            if (this.pending.indexOf(vm_id) == -1) {
                this.pending[this.pending.length] = vm_id;
            }

            if (this.pending.length) {
                this.trigger("pending:add");
            }
        }

        this.check_pending = function() {
            var len = this.pending.length;
            var args = [this.pending];
            this.pending = _.difference(this.pending, this.vms);
            if (len != this.pending.length) {
                if (this.pending.length == 0) {
                    this.trigger("pending:clear");
                }
            }

            var len = this.pending_for_removal.length;
            this.pending_for_removal = _.intersection(this.pending_for_removal, this.vms);
            if (this.pending_for_removal.length == 0) {
                this.trigger("pending:remove:clear");
            }

        }


        this.add = function(vm_id) {
            if (this.vms.indexOf(vm_id) == -1) {
                this.vms[this.vms.length] = vm_id;
                this.trigger("network:connect", vm_id);
                this.check_pending();
                return true;
            }
        }

        this.remove = function(vm_id) {
            if (this.vms.indexOf(vm_id) > -1) {
                this.vms = _.without(this.vms, vm_id);
                this.trigger("network:disconnect", vm_id);
                this.check_pending();
                return true;
            }
        }

        this.get = function() {
            return this.vms;
        }

        this.list = function() {
            return storage.vms.filter(_.bind(function(vm){
                return this.vms.indexOf(vm.id) > -1;
            }, this))
        }

        this.initialize();
    };
    _.extend(NetworkVMSList.prototype, bb.Events);
    
    // vm networks list helper
    var VMNetworksList = function() {
        this.initialize = function() {
            this.networks = {};
            this.network_ids = [];
        }

        this.add = function(net_id, data) {
            if (!this.networks[net_id]) {
                this.networks[net_id] = data || {};
                this.network_ids[this.network_ids.length] = net_id;
                this.trigger("network:connect", net_id);
                return true;
            }
        }

        this.remove = function(net_id) {
            if (this.networks[net_id]) {
                delete this.networks[net_id];
                this.network_ids = _.without(this.network_ids, net_id);
                this.trigger("network:disconnect", net_id);
                return true;
            }
            return false;
        }

        this.get = function() {
            return this.networks;
        }

        this.list = function() {
            return storage.networks.filter(_.bind(function(net){
                return this.network_ids.indexOf(net.id) > -1;
            }, this))
        }

        this.initialize();
    };
    _.extend(VMNetworksList.prototype, bb.Events);
        
    models.ParamsList = function(){this.initialize.apply(this, arguments)};
    _.extend(models.ParamsList.prototype, bb.Events, {

        initialize: function(parent, param_name) {
            this.parent = parent;
            this.actions = {};
            this.param_name = param_name;
            this.length = 0;
        },
        
        has_action: function(action) {
            return this.actions[action] ? true : false;
        },
            
        _parse_params: function(arguments) {
            if (arguments.length <= 1) {
                return [];
            }

            var args = _.toArray(arguments);
            return args.splice(1);
        },

        contains: function(action, params) {
            params = this._parse_params(arguments);
            var has_action = this.has_action(action);
            if (!has_action) { return false };

            var paramsEqual = false;
            _.each(this.actions[action], function(action_params) {
                if (_.isEqual(action_params, params)) {
                    paramsEqual = true;
                }
            });
                
            return paramsEqual;
        },
        
        is_empty: function() {
            return _.isEmpty(this.actions);
        },

        add: function(action, params) {
            params = this._parse_params(arguments);
            if (this.contains.apply(this, arguments)) { return this };
            var isnew = false
            if (!this.has_action(action)) {
                this.actions[action] = [];
                isnew = true;
            };

            this.actions[action].push(params);
            this.parent.trigger("change:" + this.param_name, this.parent, this);
            if (isnew) {
                this.trigger("add", action, params);
            } else {
                this.trigger("change", action, params);
            }
            return this;
        },
        
        remove_all: function(action) {
            if (this.has_action(action)) {
                delete this.actions[action];
                this.parent.trigger("change:" + this.param_name, this.parent, this);
                this.trigger("remove", action);
            }
            return this;
        },

        reset: function() {
            this.actions = {};
            this.parent.trigger("change:" + this.param_name, this.parent, this);
            this.trigger("reset");
            this.trigger("remove");
        },

        remove: function(action, params) {
            params = this._parse_params(arguments);
            if (!this.has_action(action)) { return this };
            var index = -1;
            _.each(this.actions[action], _.bind(function(action_params) {
                if (_.isEqual(action_params, params)) {
                    index = this.actions[action].indexOf(action_params);
                }
            }, this));
            
            if (index > -1) {
                this.actions[action].splice(index, 1);
                if (_.isEmpty(this.actions[action])) {
                    delete this.actions[action];
                }
                this.parent.trigger("change:" + this.param_name, this.parent, this);
                this.trigger("remove", action, params);
            }
        }

    });

    // Image model
    models.Network = models.Model.extend({
        path: 'networks',
        has_status: true,
        
        initialize: function() {
            this.vms = new NetworkVMSList();
            this.vms.bind("pending:add", _.bind(this.handle_pending_connections, this, "add"));
            this.vms.bind("pending:clear", _.bind(this.handle_pending_connections, this, "clear"));
            this.vms.bind("pending:remove:add", _.bind(this.handle_pending_connections, this, "add"));
            this.vms.bind("pending:remove:clear", _.bind(this.handle_pending_connections, this, "clear"));

            var ret = models.Network.__super__.initialize.apply(this, arguments);

            storage.vms.bind("change:linked_to_nets", _.bind(this.update_connections, this, "vm:change"));
            storage.vms.bind("add", _.bind(this.update_connections, this, "add"));
            storage.vms.bind("remove", _.bind(this.update_connections, this, "remove"));
            storage.vms.bind("reset", _.bind(this.update_connections, this, "reset"));

            this.bind("change:linked_to", _.bind(this.update_connections, this, "net:change"));
            this.update_connections();
            this.update_state();
            
            this.set({"actions": new models.ParamsList(this, "actions")});

            return ret;
        },

        update_state: function() {
            if (this.vms.pending.length) {
                this.set({state: "CONNECTING"});
                return
            }

            if (this.vms.pending_for_removal.length) {
                this.set({state: "DISCONNECTING"});
                return
            }   
            
            var firewalling = false;
            _.each(this.vms.get(), _.bind(function(vm_id){
                var vm = storage.vms.get(vm_id);
                if (!vm) { return };
                if (!_.isEmpty(vm.pending_firewalls)) {
                    this.set({state:"FIREWALLING"});
                    firewalling = true;
                    return false;
                }
            },this));
            if (firewalling) { return };

            this.set({state:"NORMAL"});
        },

        handle_pending_connections: function(action) {
            this.update_state();
        },

        // handle vm/network connections
        update_connections: function(action, model) {
            
            // vm removed disconnect vm from network
            if (action == "remove") {
                var removed_from_net = this.vms.remove(model.id);
                var removed_from_vm = model.networks.remove(this.id);
                if (removed_from_net) {this.trigger("vm:disconnect", model, this); this.change()};
                if (removed_from_vm) {model.trigger("network:disconnect", this, model); this.change()};
                return;
            }
            
            // update links for all vms
            var links = this.get("linked_to");
            storage.vms.each(_.bind(function(vm) {
                var vm_links = vm.get("linked_to") || [];
                if (vm_links.indexOf(this.id) > -1) {
                    // vm has connection to current network
                    if (links.indexOf(vm.id) > -1) {
                        // and network has connection to vm, so try
                        // to append it
                        var add_to_net = this.vms.add(vm.id);
                        var index = _.indexOf(vm_links, this.id);
                        var add_to_vm = vm.networks.add(this.id, vm.get("linked_to_nets")[index]);
                        
                        // call only if connection did not existed
                        if (add_to_net) {this.trigger("vm:connect", vm, this); this.change()};
                        if (add_to_vm) {vm.trigger("network:connect", this, vm); vm.change()};
                    } else {
                        // no connection, try to remove it
                        var removed_from_net = this.vms.remove(vm.id);
                        var removed_from_vm = vm.networks.remove(this.id);
                        if (removed_from_net) {this.trigger("vm:disconnect", vm, this); this.change()};
                        if (removed_from_vm) {vm.trigger("network:disconnect", this, vm); vm.change()};
                    }
                } else {
                    // vm has no connection to current network, try to remove it
                    var removed_from_net = this.vms.remove(vm.id);
                    var removed_from_vm = vm.networks.remove(this.id);
                    if (removed_from_net) {this.trigger("vm:disconnect", vm, this); this.change()};
                    if (removed_from_vm) {vm.trigger("network:disconnect", this, vm); vm.change()};
                }
            },this));
        },

        is_public: function() {
            return this.id == "public";
        },

        contains_vm: function(vm) {
            var net_vm_exists = this.vms.get().indexOf(vm.id) > -1;
            var vm_net_exists = vm.is_connected_to(this);
            return net_vm_exists && vm_net_exists;
        },
        
        call: function(action, params, success, error) {
            if (action == "destroy") {
                this.set({state:"DESTROY"});
                this.get("actions").remove("destroy");
                this.remove(_.bind(function(){
                    success();
                }, this), error);
            }
            
            if (action == "disconnect") {
                _.each(params, _.bind(function(vm_id) {
                    var vm = snf.storage.vms.get(vm_id);
                    this.get("actions").remove("disconnect", vm_id);
                    if (vm) {
                        this.remove_vm(vm, success, error);
                    }
                }, this));
            }
        },

        add_vm: function (vm, callback, error, options) {
            var payload = {add:{serverRef:"" + vm.id}};
            payload._options = options || {};
            return this.api.call(this.api_path() + "/action", "create", 
                                 payload,
                                 _.bind(function(){
                                     this.vms.add_pending(vm.id);
                                     if (callback) {callback()}
                                 },this), error);
        },

        remove_vm: function (vm, callback, error, options) {
            var payload = {remove:{serverRef:"" + vm.id}};
            payload._options = options || {};
            return this.api.call(this.api_path() + "/action", "create", 
                                 {remove:{serverRef:"" + vm.id}},
                                 _.bind(function(){
                                     this.vms.add_pending_for_remove(vm.id);
                                     if (callback) {callback()}
                                 },this), error);
        },

        rename: function(name, callback) {
            return this.api.call(this.api_path(), "update", {
                network:{name:name}, 
                _options:{
                    critical: false, 
                    error_params:{
                        title: "Network action failed",
                        ns: "Networks",
                        extra_details: {"Network id": this.id}
                    }
                }}, callback);
        },

        get_connectable_vms: function() {
            var servers = this.vms.list();
            return storage.vms.filter(function(vm){
                return servers.indexOf(vm) == -1 && !vm.in_error_state();
            })
        },

        state_message: function() {
            if (this.get("state") == "NORMAL" && this.is_public()) {
                return "Public network";
            }

            return models.Network.STATES[this.get("state")];
        },

        in_progress: function() {
            return models.Network.STATES_TRANSITIONS[this.get("state")] != undefined;
        },

        do_all_pending_actions: function(success, error) {
            var destroy = this.get("actions").has_action("destroy");
            _.each(this.get("actions").actions, _.bind(function(params, action) {
                _.each(params, _.bind(function(with_params) {
                    this.call(action, with_params, success, error);
                }, this));
            }, this));
        }
    });
    
    models.Network.STATES = {
        'NORMAL': 'Private network',
        'CONNECTING': 'Connecting...',
        'DISCONNECTING': 'Disconnecting...',
        'FIREWALLING': 'Firewall update...',
        'DESTROY': 'Destroying...'
    }

    models.Network.STATES_TRANSITIONS = {
        'CONNECTING': ['NORMAL'],
        'DISCONNECTING': ['NORMAL'],
        'FIREWALLING': ['NORMAL']
    }

    // Virtualmachine model
    models.VM = models.Model.extend({

        path: 'servers',
        has_status: true,
        initialize: function(params) {
            this.networks = new VMNetworksList();
            
            this.pending_firewalls = {};
            
            models.VM.__super__.initialize.apply(this, arguments);

            this.set({state: params.status || "ERROR"});
            this.log = new snf.logging.logger("VM " + this.id);
            this.pending_action = undefined;
            
            // init stats parameter
            this.set({'stats': undefined}, {silent: true});
            // defaults to not update the stats
            // each view should handle this vm attribute 
            // depending on if it displays stat images or not
            this.do_update_stats = false;
            
            // interval time
            // this will dynamicaly change if the server responds that
            // images get refreshed on different intervals
            this.stats_update_interval = synnefo.config.STATS_INTERVAL || 5000;
            this.stats_available = false;

            // initialize interval
            this.init_stats_intervals(this.stats_update_interval);
            
            this.bind("change:progress", _.bind(this.update_building_progress, this));
            this.update_building_progress();

            this.bind("change:firewalls", _.bind(this.handle_firewall_change, this));
            
            // default values
            this.set({linked_to_nets:this.get("linked_to_nets") || []});
            this.set({firewalls:this.get("firewalls") || []});

            this.bind("change:state", _.bind(function(){if (this.state() == "DESTROY") { this.handle_destroy() }}, this))
        },

        handle_firewall_change: function() {

        },
        
        set_linked_to_nets: function(data) {
            this.set({"linked_to":_.map(data, function(n){ return n.id})});
            return data;
        },

        is_connected_to: function(net) {
            return _.filter(this.networks.list(), function(n){return n.id == net.id}).length > 0;
        },
        
        status: function(st) {
            if (!st) { return this.get("status")}
            return this.set({status:st});
        },

        set_status: function(st) {
            var new_state = this.state_for_api_status(st);
            var transition = false;

            if (this.state() != new_state) {
                if (models.VM.STATES_TRANSITIONS[this.state()]) {
                    transition = this.state();
                }
            }
            
            // call it silently to avoid double change trigger
            this.set({'state': this.state_for_api_status(st)}, {silent: true});
            
            // trigger transition
            if (transition && models.VM.TRANSITION_STATES.indexOf(new_state) == -1) { 
                this.trigger("transition", {from:transition, to:new_state}) 
            };
            return st;
        },

        update_building_progress: function() {
            if (this.is_building()) {
                var progress = this.get("progress");
                if (progress == 0) {
                    this.state("BUILD_INIT");
                    this.set({progress_message: BUILDING_MESSAGES['INIT']});
                }
                if (progress > 0 && progress < 99) {
                    this.state("BUILD_COPY");
                    var params = this.get_copy_details(true);
                    this.set({progress_message: BUILDING_MESSAGES['COPY'].format(params.copy, 
                                                                                 params.size, 
                                                                                 params.progress)});
                }
                if (progress == 100) {
                    this.state("BUILD_FINAL");
                    this.set({progress_message: BUILDING_MESSAGES['FINAL']});
                }
            } else {
            }
        },

        get_copy_details: function(human, image) {
            var human = human || false;
            var image = image || this.get_image();

            var progress = this.get('progress');
            var size = image.get_size();
            var size_copied = (size * progress / 100).toFixed(2);
            
            if (human) {
                size = util.readablizeBytes(size*1024*1024);
                size_copied = util.readablizeBytes(size_copied*1024*1024);
            }
            return {'progress': progress, 'size': size, 'copy': size_copied};
        },

        start_stats_update: function(force_if_empty) {
            var prev_state = this.do_update_stats;

            this.do_update_stats = true;
            
            // fetcher initialized ??
            if (!this.stats_fetcher) {
                this.init_stats_intervals();
            }


            // fetcher running ???
            if (!this.stats_fetcher.running || !prev_state) {
                this.stats_fetcher.start();
            }

            if (force_if_empty && this.get("stats") == undefined) {
                this.update_stats(true);
            }
        },

        stop_stats_update: function(stop_calls) {
            this.do_update_stats = false;

            if (stop_calls) {
                this.stats_fetcher.stop();
            }
        },

        // clear and reinitialize update interval
        init_stats_intervals: function (interval) {
            this.stats_fetcher = this.get_stats_fetcher(this.stats_update_interval);
            this.stats_fetcher.start();
        },
        
        get_stats_fetcher: function(timeout) {
            var cb = _.bind(function(data){
                this.update_stats();
            }, this);
            var fetcher = new snf.api.updateHandler({'callback': cb, timeout:timeout});
            return fetcher;
        },

        // do the api call
        update_stats: function(force) {
            // do not update stats if flag not set
            if ((!this.do_update_stats && !force) || this.updating_stats) {
                return;
            }

            // make the api call, execute handle_stats_update on sucess
            // TODO: onError handler ???
            stats_url = this.url() + "/stats";
            this.updating_stats = true;
            this.sync("GET", this, {
                handles_error:true, 
                url: stats_url, 
                refresh:true, 
                success: _.bind(this.handle_stats_update, this),
                error: _.bind(this.handle_stats_error, this),
                complete: _.bind(function(){this.updating_stats = false;}, this),
                critical: false,
                display: false,
                log_error: false
            });
        },

        get_stats_image: function(stat, type) {
        },
        
        _set_stats: function(stats) {
            var silent = silent === undefined ? false : silent;
            // unavailable stats while building
            if (this.get("status") == "BUILD") { 
                this.stats_available = false;
            } else { this.stats_available = true; }

            if (this.get("status") == "DESTROY") { this.stats_available = false; }
            
            this.set({stats: stats}, {silent:true});
            this.trigger("stats:update", stats);
        },

        unbind: function() {
            models.VM.__super__.unbind.apply(this, arguments);
        },

        handle_stats_error: function() {
            stats = {};
            _.each(['cpuBar', 'cpuTimeSeries', 'netBar', 'netTimeSeries'], function(k) {
                stats[k] = false;
            });

            this.set({'stats': stats});
        },

        // this method gets executed after a successful vm stats api call
        handle_stats_update: function(data) {
            var self = this;
            // avoid browser caching
            
            if (data.stats && _.size(data.stats) > 0) {
                var ts = $.now();
                var stats = data.stats;
                var images_loaded = 0;
                var images = {};

                function check_images_loaded() {
                    images_loaded++;

                    if (images_loaded == 4) {
                        self._set_stats(images);
                    }
                }
                _.each(['cpuBar', 'cpuTimeSeries', 'netBar', 'netTimeSeries'], function(k) {
                    
                    stats[k] = stats[k] + "?_=" + ts;
                    
                    var stat = k.slice(0,3);
                    var type = k.slice(3,6) == "Bar" ? "bar" : "time";
                    var img = $("<img />");
                    var val = stats[k];
                    
                    // load stat image to a temporary dom element
                    // update model stats on image load/error events
                    img.load(function() {
                        images[k] = val;
                        check_images_loaded();
                    });

                    img.error(function() {
                        images[stat + type] = false;
                        check_images_loaded();
                    });

                    img.attr({'src': stats[k]});
                })
                data.stats = stats;
            }

            // do we need to change the interval ??
            if (data.stats.refresh * 1000 != this.stats_update_interval) {
                this.stats_update_interval = data.stats.refresh * 1000;
                this.stats_fetcher.timeout = this.stats_update_interval;
                this.stats_fetcher.stop();
                this.stats_fetcher.start(false);
            }
        },

        // helper method that sets the do_update_stats
        // in the future this method could also make an api call
        // immediaetly if needed
        enable_stats_update: function() {
            this.do_update_stats = true;
        },
        
        handle_destroy: function() {
            this.stats_fetcher.stop();
        },

        require_reboot: function() {
            if (this.is_active()) {
                this.set({'reboot_required': true});
            }
        },
        
        set_pending_action: function(data) {
            this.pending_action = data;
            return data;
        },

        // machine has pending action
        update_pending_action: function(action, force) {
            this.set({pending_action: action});
        },

        clear_pending_action: function() {
            this.set({pending_action: undefined});
        },

        has_pending_action: function() {
            return this.get("pending_action") ? this.get("pending_action") : false;
        },
        
        // machine is active
        is_active: function() {
            return models.VM.ACTIVE_STATES.indexOf(this.state()) > -1;
        },
        
        // machine is building 
        is_building: function() {
            return models.VM.BUILDING_STATES.indexOf(this.state()) > -1;
        },
        
        in_error_state: function() {
            return this.state() === "ERROR"
        },

        // user can connect to machine
        is_connectable: function() {
            // check if ips exist
            if (!this.get_addresses().ip4 && !this.get_addresses().ip6) {
                return false;
            }
            return models.VM.CONNECT_STATES.indexOf(this.state()) > -1;
        },
        
        set_firewalls: function(data) {
            _.each(data, _.bind(function(val, key){
                if (this.pending_firewalls && this.pending_firewalls[key] && this.pending_firewalls[key] == val) {
                        this.require_reboot();
                        this.remove_pending_firewall(key, val);
                }
            }, this));
            return data;
        },

        remove_pending_firewall: function(net_id, value) {
            if (this.pending_firewalls[net_id] == value) {
                delete this.pending_firewalls[net_id];
                storage.networks.get(net_id).update_state();
            }
        },
            
        remove_meta: function(key, complete, error) {
            var url = this.api_path() + "/meta/" + key;
            this.api.call(url, "delete", undefined, complete, error);
        },

        save_meta: function(meta, complete, error) {
            var url = this.api_path() + "/meta/" + meta.key;
            var payload = {meta:{}};
            payload.meta[meta.key] = meta.value;
            payload._options = {
                critical:false, 
                error_params: {
                    title: "Machine metadata error",
                    extra_details: {"Machine id": this.id}
            }};

            this.api.call(url, "update", payload, complete, error);
        },

        set_firewall: function(net_id, value, callback, error, options) {
            if (this.get("firewalls") && this.get("firewalls")[net_id] == value) { return }

            this.pending_firewalls[net_id] = value;
            this.trigger("change", this, this);
            var payload = {"firewallProfile":{"profile":value}};
            payload._options = _.extend({critical: false}, options);
            
            // reset firewall state on error
            var error_cb = _.bind(function() {
                thi
            }, this);

            this.api.call(this.api_path() + "/action", "create", payload, callback, error);
            storage.networks.get(net_id).update_state();
        },

        firewall_pending: function(net_id) {
            return this.pending_firewalls[net_id] != undefined;
        },
        
        // update/get the state of the machine
        state: function() {
            var args = slice.call(arguments);
                
            // TODO: it might not be a good idea to set the state in set_state method
            if (args.length > 0 && models.VM.STATES.indexOf(args[0]) > -1) {
                this.set({'state': args[0]});
            }

            return this.get('state');
        },
        
        // get the state that the api status corresponds to
        state_for_api_status: function(status) {
            return this.state_transition(this.state(), status);
        },
        
        // vm state equals vm api status
        state_is_status: function(state) {
            return models.VM.STATUSES.indexOf(state) != -1;
        },
        
        // get transition state for the corresponging api status
        state_transition: function(state, new_status) {
            var statuses = models.VM.STATES_TRANSITIONS[state];
            if (statuses) {
                if (statuses.indexOf(new_status) > -1) {
                    return new_status;
                } else {
                    return state;
                }
            } else {
                return new_status;
            }
        },
        
        // the current vm state is a transition state
        in_transition: function() {
            return models.VM.TRANSITION_STATES.indexOf(this.state()) > -1 || 
                models.VM.TRANSITION_STATES.indexOf(this.get('status')) > -1;
        },
        
        // get image object
        // TODO: update images synchronously if image not found
        get_image: function() {
            var image = storage.images.get(this.get('imageRef'));
            if (!image) {
                storage.images.update_unknown_id(this.get('imageRef'));
                image = storage.images.get(this.get('imageRef'));
            }
            return image;
        },
        
        // get flavor object
        get_flavor: function() {
            var flv = storage.flavors.get(this.get('flavorRef'));
            if (!flv) {
                storage.flavors.update_unknown_id(this.get('flavorRef'));
                flv = storage.flavors.get(this.get('flavorRef'));
            }
            return flv;
        },

        // retrieve the metadata object
        get_meta: function() {
            try {
                return this.get('metadata').values
            } catch (err) {
                return {};
            }
        },
        
        // get metadata OS value
        get_os: function() {
            return this.get_meta().OS || (this.get_image() ? this.get_image().get_os() || "okeanos" : "okeanos");
        },
        
        // get public ip addresses
        // TODO: public network is always the 0 index ???
        get_addresses: function(net_id) {
            var net_id = net_id || "public";
            
            var info = this.get_network_info(net_id);
            if (!info) { return {} };
            addrs = {};
            _.each(info.values, function(addr) {
                addrs["ip" + addr.version] = addr.addr;
            });
            return addrs
        },

        get_network_info: function(net_id) {
            var net_id = net_id || "public";
            
            if (!this.networks.network_ids.length) { return {} };

            var addresses = this.networks.get();
            try {
                return _.select(addresses, function(net, key){return key == net_id })[0];
            } catch (err) {
                //this.log.debug("Cannot find network {0}".format(net_id))
            }
        },

        firewall_profile: function(net_id) {
            var net_id = net_id || "public";
            var firewalls = this.get("firewalls");
            return firewalls[net_id];
        },

        has_firewall: function(net_id) {
            var net_id = net_id || "public";
            return ["ENABLED","PROTECTED"].indexOf(this.firewall_profile()) > -1;
        },
    
        // get actions that the user can execute
        // depending on the vm state/status
        get_available_actions: function() {
            return models.VM.AVAILABLE_ACTIONS[this.state()];
        },

        set_profile: function(profile, net_id) {
        },
        
        // call rename api
        rename: function(new_name) {
            //this.set({'name': new_name});
            this.sync("update", this, {
                critical: true,
                data: {
                    'server': {
                        'name': new_name
                    }
                }, 
                // do the rename after the method succeeds
                success: _.bind(function(){
                    //this.set({name: new_name});
                    snf.api.trigger("call");
                }, this)
            });
        },
        
        get_console_url: function(data) {
            var url_params = {
                machine: this.get("name"),
                host_ip: this.get_addresses().ip4,
                host_ip_v6: this.get_addresses().ip6,
                host: data.host,
                port: data.port,
                password: data.password
            }
            return '/machines/console?' + $.param(url_params);
        },

        // action helper
        call: function(action_name, success, error) {
            var id_param = [this.id];

            success = success || function() {};
            error = error || function() {};

            var self = this;

            switch(action_name) {
                case 'start':
                    this.__make_api_call(this.get_action_url(), // vm actions url
                                         "create", // create so that sync later uses POST to make the call
                                         {start:{}}, // payload
                                         function() {
                                             // set state after successful call
                                             self.state("START"); 
                                             success.apply(this, arguments);
                                             snf.api.trigger("call");
                                         },  
                                         error, 'start');
                    break;
                case 'reboot':
                    this.__make_api_call(this.get_action_url(), // vm actions url
                                         "create", // create so that sync later uses POST to make the call
                                         {reboot:{type:"HARD"}}, // payload
                                         function() {
                                             // set state after successful call
                                             self.state("REBOOT"); 
                                             success.apply(this, arguments)
                                             snf.api.trigger("call");
                                             self.set({'reboot_required': false});
                                         },
                                         error, 'reboot');
                    break;
                case 'shutdown':
                    this.__make_api_call(this.get_action_url(), // vm actions url
                                         "create", // create so that sync later uses POST to make the call
                                         {shutdown:{}}, // payload
                                         function() {
                                             // set state after successful call
                                             self.state("SHUTDOWN"); 
                                             success.apply(this, arguments)
                                             snf.api.trigger("call");
                                         },  
                                         error, 'shutdown');
                    break;
                case 'console':
                    this.__make_api_call(this.url() + "/action", "create", {'console': {'type':'vnc'}}, function(data) {
                        var cons_data = data.console;
                        success.apply(this, [cons_data]);
                    }, undefined, 'console')
                    break;
                case 'destroy':
                    this.__make_api_call(this.url(), // vm actions url
                                         "delete", // create so that sync later uses POST to make the call
                                         undefined, // payload
                                         function() {
                                             // set state after successful call
                                             self.state('DESTROY');
                                             success.apply(this, arguments)
                                         },  
                                         error, 'destroy');
                    break;
                default:
                    throw "Invalid VM action ("+action_name+")";
            }
        },
        
        __make_api_call: function(url, method, data, success, error, action) {
            var self = this;
            error = error || function(){};
            success = success || function(){};

            var params = {
                url: url,
                data: data,
                success: function(){ self.handle_action_succeed.apply(self, arguments); success.apply(this, arguments)},
                error: function(){ self.handle_action_fail.apply(self, arguments); error.apply(this, arguments)},
                error_params: { ns: "Machines actions", 
                                title: "'" + this.get("name") + "'" + " " + action + " failed", 
                                extra_details: { 'Machine ID': this.id, 'URL': url, 'Action': action || "undefined" },
                                allow_reload: false
                              },
                display: false,
                critical: false
            }
            this.sync(method, this, params);
        },

        handle_action_succeed: function() {
            this.trigger("action:success", arguments);
        },
        
        reset_action_error: function() {
            this.action_error = false;
            this.trigger("action:fail:reset", this.action_error);
        },

        handle_action_fail: function() {
            this.action_error = arguments;
            this.trigger("action:fail", arguments);
        },

        get_action_url: function(name) {
            return this.url() + "/action";
        },

        get_connection_info: function(host_os, success, error) {
            var url = "/machines/connect";
            params = {
                ip_address: this.get_addresses().ip4,
                os: this.get_os(),
                host_os: host_os,
                srv: this.id
            }

            url = url + "?" + $.param(params);

            var ajax = snf.api.sync("read", undefined, { url: url, 
                                                         error:error, 
                                                         success:success, 
                                                         handles_error:1});
        }
    })
    
    models.VM.ACTIONS = [
        'start',
        'shutdown',
        'reboot',
        'console',
        'destroy'
    ]

    models.VM.AVAILABLE_ACTIONS = {
        'UNKNWON'       : ['destroy'],
        'BUILD'         : ['destroy'],
        'REBOOT'        : ['shutdown', 'destroy', 'console'],
        'STOPPED'       : ['start', 'destroy'],
        'ACTIVE'        : ['shutdown', 'destroy', 'reboot', 'console'],
        'ERROR'         : ['destroy'],
        'DELETED'        : [],
        'DESTROY'       : [],
        'BUILD_INIT'    : ['destroy'],
        'BUILD_COPY'    : ['destroy'],
        'BUILD_FINAL'   : ['destroy'],
        'SHUTDOWN'      : ['destroy'],
        'START'         : [],
        'CONNECT'       : [],
        'DISCONNECT'    : []
    }

    // api status values
    models.VM.STATUSES = [
        'UNKNWON',
        'BUILD',
        'REBOOT',
        'STOPPED',
        'ACTIVE',
        'ERROR',
        'DELETED'
    ]

    // api status values
    models.VM.CONNECT_STATES = [
        'ACTIVE',
        'REBOOT',
        'SHUTDOWN'
    ]

    // vm states
    models.VM.STATES = models.VM.STATUSES.concat([
        'DESTROY',
        'BUILD_INIT',
        'BUILD_COPY',
        'BUILD_FINAL',
        'SHUTDOWN',
        'START',
        'CONNECT',
        'DISCONNECT',
        'FIREWALL'
    ]);
    
    models.VM.STATES_TRANSITIONS = {
        'DESTROY' : ['DELETED'],
        'SHUTDOWN': ['ERROR', 'STOPPED', 'DESTROY'],
        'STOPPED': ['ERROR', 'ACTIVE', 'DESTROY'],
        'ACTIVE': ['ERROR', 'STOPPED', 'REBOOT', 'SHUTDOWN', 'DESTROY'],
        'START': ['ERROR', 'ACTIVE', 'DESTROY'],
        'REBOOT': ['ERROR', 'ACTIVE', 'STOPPED', 'DESTROY'],
        'BUILD': ['ERROR', 'ACTIVE', 'DESTROY'],
        'BUILD_COPY': ['ERROR', 'ACTIVE', 'BUILD_FINAL', 'DESTROY'],
        'BUILD_FINAL': ['ERROR', 'ACTIVE', 'DESTROY'],
        'BUILD_INIT': ['ERROR', 'ACTIVE', 'BUILD_COPY', 'BUILD_FINAL', 'DESTROY']
    }

    models.VM.TRANSITION_STATES = [
        'DESTROY',
        'SHUTDOWN',
        'START',
        'REBOOT',
        'BUILD'
    ]

    models.VM.ACTIVE_STATES = [
        'BUILD', 'REBOOT', 'ACTIVE',
        'BUILD_INIT', 'BUILD_COPY', 'BUILD_FINAL',
        'SHUTDOWN', 'CONNECT', 'DISCONNECT'
    ]

    models.VM.BUILDING_STATES = [
        'BUILD', 'BUILD_INIT', 'BUILD_COPY', 'BUILD_FINAL'
    ]

    models.Networks = models.Collection.extend({
        model: models.Network,
        path: 'networks',
        details: true,
        //noUpdate: true,
        defaults: {'linked_to':[]},

        parse: function (resp, xhr) {
            // FIXME: depricated global var
            if (!resp) { return []};
               
            var data = _.map(resp.networks.values, _.bind(this.parse_net_api_data, this));
            return data;
        },

        reset_pending_actions: function() {
            this.each(function(net) {
                net.get("actions").reset();
            })
        },

        do_all_pending_actions: function() {
            this.each(function(net) {
                net.do_all_pending_actions();
            })
        },

        parse_net_api_data: function(data) {
            if (data.servers && data.servers.values) {
                data['linked_to'] = data.servers.values;
            }
            return data;
        },

        create: function (name, callback) {
            return this.api.call(this.path, "create", {network:{name:name}}, callback);
        }
    })

    models.Images = models.Collection.extend({
        model: models.Image,
        path: 'images',
        details: true,
        noUpdate: true,
        supportIncUpdates: false,
        meta_keys_as_attrs: ["OS", "description", "kernel", "size", "GUI"],

        // update collection model with id passed
        // making a direct call to the image
        // api url
        update_unknown_id: function(id) {
            var url = getUrl.call(this) + "/" + id;
            this.api.call(this.path + "/" + id, "read", {_options:{async:false}}, undefined, 
            _.bind(function() {
                this.add({id:id, name:"Unknown image", size:-1, progress:100, status:"DELETED"})
            }, this), _.bind(function(image) {
                this.add(image.image);
            }, this));
        },

        parse: function (resp, xhr) {
            // FIXME: depricated global var
            var data = _.map(resp.images.values, _.bind(this.parse_meta, this));
            return resp.images.values;
        },

        get_meta_key: function(img, key) {
            if (img.metadata && img.metadata.values && img.metadata.values[key]) {
                return img.metadata.values[key];
            }
            return undefined;
        },

        comparator: function(img) {
            return -img.get_sort_order("sortorder") || 1000 * img.id;
        },

        parse_meta: function(img) {
            _.each(this.meta_keys_as_attrs, _.bind(function(key){
                img[key] = this.get_meta_key(img, key) || "";
            }, this));
            return img;
        },

        active: function() {
            return this.filter(function(img){return img.get('status') != "DELETED"});
        }
    })

    models.Flavors = models.Collection.extend({
        model: models.Flavor,
        path: 'flavors',
        details: true,
        noUpdate: true,
        supportIncUpdates: false,
        // update collection model with id passed
        // making a direct call to the flavor
        // api url
        update_unknown_id: function(id) {
            var url = getUrl.call(this) + "/" + id;
            this.api.call(this.path + "/" + id, "read", {_options:{async:false}}, undefined, 
            _.bind(function() {
                this.add({id:id, cpu:"", ram:"", disk:"", name: "", status:"DELETED"})
            }, this), _.bind(function(flv) {
                if (!flv.flavor.status) { flv.flavor.status = "DELETED" };
                this.add(flv.flavor);
            }, this));
        },

        parse: function (resp, xhr) {
            // FIXME: depricated global var
            return resp.flavors.values;
        },

        comparator: function(flv) {
            return flv.get("disk") * flv.get("cpu") * flv.get("ram");
        },

        unavailable_values_for_image: function(img, flavors) {
            var flavors = flavors || this.active();
            var size = img.get_size();
            
            var index = {cpu:[], disk:[], ram:[]};

            _.each(this.active(), function(el) {
                var img_size = size;
                var flv_size = el.get_disk_size();
                if (flv_size < img_size) {
                    if (index.disk.indexOf(flv_size) == -1) {
                        index.disk.push(flv_size);
                    }
                };
            });
            
            return index;
        },

        get_flavor: function(cpu, mem, disk, filter_list) {
            if (!filter_list) { filter_list = this.models };

            return this.select(function(flv){
                if (flv.get("cpu") == cpu + "" &&
                   flv.get("ram") == mem + "" &&
                   flv.get("disk") == disk + "" &&
                   filter_list.indexOf(flv) > -1) { return true; }
            })[0];
        },
        
        get_data: function(lst) {
            var data = {'cpu': [], 'mem':[], 'disk':[]};

            _.each(lst, function(flv) {
                if (data.cpu.indexOf(flv.get("cpu")) == -1) {
                    data.cpu.push(flv.get("cpu"));
                }
                if (data.mem.indexOf(flv.get("ram")) == -1) {
                    data.mem.push(flv.get("ram"));
                }
                if (data.disk.indexOf(flv.get("disk")) == -1) {
                    data.disk.push(flv.get("disk"));
                }
            })
            
            return data;
        },

        active: function() {
            return this.filter(function(flv){return flv.get('status') != "DELETED"});
        }
            
    })

    models.VMS = models.Collection.extend({
        model: models.VM,
        path: 'servers',
        details: true,
        copy_image_meta: true,
        
        parse: function (resp, xhr) {
            // FIXME: depricated after refactoring
            var data = resp;
            if (!resp) { return [] };
            data = _.filter(_.map(resp.servers.values, _.bind(this.parse_vm_api_data, this)), function(v){return v});
            return data;
        },
        
        get_reboot_required: function() {
            return this.filter(function(vm){return vm.get("reboot_required") == true})
        },

        has_pending_actions: function() {
            return this.filter(function(vm){return vm.pending_action}).length > 0;
        },

        reset_pending_actions: function() {
            this.each(function(vm) {
                vm.clear_pending_action();
            })
        },

        do_all_pending_actions: function(success, error) {
            this.each(function(vm) {
                if (vm.has_pending_action()) {
                    vm.call(vm.pending_action, success, error);
                    vm.clear_pending_action();
                }
            })
        },
        
        do_all_reboots: function(success, error) {
            this.each(function(vm) {
                if (vm.get("reboot_required")) {
                    vm.call("reboot", success, error);
                }
            });
        },

        reset_reboot_required: function() {
            this.each(function(vm) {
                vm.set({'reboot_required': undefined});
            })
        },
        
        stop_stats_update: function(exclude) {
            var exclude = exclude || [];
            this.each(function(vm) {
                if (exclude.indexOf(vm) > -1) {
                    return;
                }
                vm.stop_stats_update();
            })
        },
        
        has_meta: function(vm_data) {
            return vm_data.metadata && vm_data.metadata.values
        },

        has_addresses: function(vm_data) {
            return vm_data.metadata && vm_data.metadata.values
        },

        parse_vm_api_data: function(data) {
            // do not add non existing DELETED entries
            if (data.status && data.status == "DELETED") {
                if (!this.get(data.id)) {
                    console.error("non exising deleted vm", data)
                    return false;
                }
            }

            // OS attribute
            if (this.has_meta(data)) {
                data['OS'] = data.metadata.values.OS || "okeanos";
            }
            
            data['firewalls'] = {};
            if (data['addresses'] && data['addresses'].values) {
                data['linked_to_nets'] = data['addresses'].values;
                _.each(data['addresses'].values, function(f){
                    if (f['firewallProfile']) {
                        data['firewalls'][f['id']] = f['firewallProfile']
                    }
                });
            }
            
            // if vm has no metadata, no metadata object
            // is in json response, reset it to force
            // value update
            if (!data['metadata']) {
                data['metadata'] = {values:{}};
            }

            return data;
        },

        create: function (name, image, flavor, meta, extra, callback) {
            if (this.copy_image_meta) {
                meta['OS'] = image.get("OS");
           }
            
            opts = {name: name, imageRef: image.id, flavorRef: flavor.id, metadata:meta}
            opts = _.extend(opts, extra);

            this.api.call(this.path, "create", {'server': opts}, undefined, undefined, callback, {critical: false});
        }

    })

    models.PublicKey = models.Model.extend({
        path: 'keys/',
        base_url: '/ui/userdata'
    })
    
    models.PublicKeys = models.Collection.extend({
        path: 'keys/',
        base_url: '/ui/userdata'
    })
    

    // storage initialization
    snf.storage.images = new models.Images();
    snf.storage.flavors = new models.Flavors();
    snf.storage.networks = new models.Networks();
    snf.storage.vms = new models.VMS();
    snf.storage.keys = new models.PublicKeys();

    //snf.storage.vms.fetch({update:true});
    //snf.storage.images.fetch({update:true});
    //snf.storage.flavors.fetch({update:true});

})(this);
