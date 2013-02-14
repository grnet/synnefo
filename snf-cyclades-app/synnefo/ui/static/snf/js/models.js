// Copyright 2011 GRNET S.A. All rights reserved.
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
    var util = snf.util = snf.util || {};

    // shortcuts
    var bb = root.Backbone;
    var slice = Array.prototype.slice

    // logging
    var logger = new snf.logging.logger("SNF-MODELS");
    var debug = _.bind(logger.debug, logger);
    
    // get url helper
    var getUrl = function(baseurl) {
        var baseurl = baseurl || snf.config.api_urls[this.api_type];
        return baseurl + "/" + this.path;
    }

    var NIC_REGEX = /^nic-([0-9]+)-([0-9]+)$/
    
    // i18n
    BUILDING_MESSAGES = window.BUILDING_MESSAGES || {'INIT': 'init', 'COPY': '{0}, {1}, {2}', 'FINAL': 'final'};

    // Base object for all our models
    models.Model = bb.Model.extend({
        sync: snf.api.sync,
        api: snf.api,
        api_type: 'compute',
        has_status: false,

        initialize: function() {
            if (this.has_status) {
                this.bind("change:status", this.handle_remove);
                this.handle_remove();
            }
            
            this.api_call = _.bind(this.api.call, this);
            models.Model.__super__.initialize.apply(this, arguments);
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
        },

        remove: function(complete, error, success) {
            this.api_call(this.api_path(), "delete", undefined, complete, error, success);
        },

        changedKeys: function() {
            return _.keys(this.changedAttributes() || {});
        },
            
        // return list of changed attributes that included in passed list
        // argument
        getKeysChanged: function(keys) {
            return _.intersection(keys, this.changedKeys());
        },
        
        // boolean check of keys changed
        keysChanged: function(keys) {
            return this.getKeysChanged(keys).length > 0;
        },

        // check if any of the passed attribues has changed
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
        api_type: 'compute',
        supportIncUpdates: true,

        initialize: function() {
            models.Collection.__super__.initialize.apply(this, arguments);
            this.api_call = _.bind(this.api.call, this);
        },

        url: function(options, method) {
            return getUrl.call(this, this.base_url) + (
                    options.details || this.details && method != 'create' ? '/detail' : '');
        },

        fetch: function(options) {
            if (!options) { options = {} };
            // default to update
            if (!this.noUpdate) {
                if (options.update === undefined) { options.update = true };
                if (!options.removeMissing && options.refresh) { options.removeMissing = true };
            } else {
                if (options.refresh === undefined) {
                    options.refresh = true;
                }
            }
            // custom event foreach fetch
            return bb.Collection.prototype.fetch.call(this, options)
        },

        create: function(model, options) {
            var coll = this;
            options || (options = {});
            model = this._prepareModel(model, options);
            if (!model) return false;
            var success = options.success;
            options.success = function(nextModel, resp, xhr) {
                if (success) success(nextModel, resp, xhr);
            };
            model.save(null, options);
            return model;
        },

        get_fetcher: function(interval, increase, fast, increase_after_calls, max, initial_call, params) {
            var fetch_params = params || {};
            var handler_options = {};

            fetch_params.skips_timeouts = true;
            handler_options.interval = interval;
            handler_options.increase = increase;
            handler_options.fast = fast;
            handler_options.increase_after_calls = increase_after_calls;
            handler_options.max= max;
            handler_options.id = "collection id";

            var last_ajax = undefined;
            var callback = _.bind(function() {
                // clone to avoid referenced objects
                var params = _.clone(fetch_params);
                updater._ajax = last_ajax;
                
                // wait for previous request to finish
                if (last_ajax && last_ajax.readyState < 4 && last_ajax.statusText != "timeout") {
                    // opera readystate for 304 responses is 0
                    if (!($.browser.opera && last_ajax.readyState == 0 && last_ajax.status == 304)) {
                        return;
                    }
                }
                
                last_ajax = this.fetch(params);
            }, this);
            handler_options.callback = callback;

            var updater = new snf.api.updateHandler(_.clone(_.extend(handler_options, fetch_params)));
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

        get_description: function(escape) {
            if (escape == undefined) { escape = true };
            if (escape) { return this.escape('description') || "No description available"}
            return this.get('description') || "No description available."
        },

        get_meta: function(key) {
            if (this.get('metadata') && this.get('metadata').values) {
                if (!this.get('metadata').values[key]) { return null }
                return _.escape(this.get('metadata').values[key]);
            } else {
                return null;
            }
        },

        get_meta_keys: function() {
            if (this.get('metadata') && this.get('metadata').values) {
                return _.keys(this.get('metadata').values);
            } else {
                return [];
            }
        },

        get_owner: function() {
            return this.get('owner') || _.keys(synnefo.config.system_images_owners)[0];
        },

        get_owner_uuid: function() {
            return this.get('owner_uuid');
        },

        is_system_image: function() {
          var owner = this.get_owner();
          return _.include(_.keys(synnefo.config.system_images_owners), owner)
        },

        owned_by: function(user) {
          if (!user) { user = synnefo.user }
          return user.username == this.get('owner_uuid');
        },

        display_owner: function() {
            var owner = this.get_owner();
            if (_.include(_.keys(synnefo.config.system_images_owners), owner)) {
                return synnefo.config.system_images_owners[owner];
            } else {
                return owner;
            }
        },
    
        get_readable_size: function() {
            if (this.is_deleted()) {
                return synnefo.config.image_deleted_size_title || '(none)';
            }
            return this.get_size() > 0 ? util.readablizeBytes(this.get_size() * 1024 * 1024) : '(none)';
        },

        get_os: function() {
            return this.get_meta('OS');
        },

        get_gui: function() {
            return this.get_meta('GUI');
        },

        get_created_users: function() {
            try {
              var users = this.get_meta('users').split(" ");
            } catch (err) { users = null }
            if (!users) { users = [synnefo.config.os_created_users[this.get_os()] || "root"]}
            return users;
        },

        get_sort_order: function() {
            return parseInt(this.get('metadata') ? this.get('metadata').values.sortorder : -1)
        },

        get_vm: function() {
            var vm_id = this.get("serverRef");
            var vm = undefined;
            vm = storage.vms.get(vm_id);
            return vm;
        },

        is_public: function() {
            return this.get('is_public') == undefined ? true : this.get('is_public');
        },

        is_deleted: function() {
            return this.get('status') == "DELETED"
        },
        
        ssh_keys_paths: function() {
            return _.map(this.get_created_users(), function(username) {
                prepend = '';
                if (username != 'root') {
                    prepend = '/home'
                }
                return {'user': username, 'path': '{1}/{0}/.ssh/authorized_keys'.format(username, 
                                                             prepend)};
            });
        },

        _supports_ssh: function() {
            if (synnefo.config.support_ssh_os_list.indexOf(this.get_os()) > -1) {
                return true;
            }
            if (this.get_meta('osfamily') == 'linux') {
              return true;
            }
            return false;
        },

        supports: function(feature) {
            if (feature == "ssh") {
                return this._supports_ssh()
            }
            return false;
        },

        personality_data_for_keys: function(keys) {
            return _.map(this.ssh_keys_paths(), function(pathinfo) {
                var contents = '';
                _.each(keys, function(key){
                    contents = contents + key.get("content") + "\n"
                });
                contents = $.base64.encode(contents);

                return {
                    path: pathinfo.path,
                    contents: contents,
                    mode: 0600,
                    owner: pathinfo.user,
                    group: pathinfo.user
                }
            });
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
        },

        get_disk_template_info: function() {
            var info = snf.config.flavors_disk_templates_info[this.get("disk_template")];
            if (!info) {
                info = { name: this.get("disk_template"), description:'' };
            }
            return info
        }

    });
    
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
        defaults: {'connecting':0},
        
        initialize: function() {
            var ret = models.Network.__super__.initialize.apply(this, arguments);
            this.set({"actions": new models.ParamsList(this, "actions")});
            this.update_state();
            this.bind("change:nics", _.bind(synnefo.storage.nics.update_net_nics, synnefo.storage.nics));
            this.bind("change:status", _.bind(this.update_state, this));
            return ret;
        },
        
        is_deleted: function() {
          return this.get('status') == 'DELETED';
        },

        toJSON: function() {
            var attrs = _.clone(this.attributes);
            attrs.actions = _.clone(this.get("actions").actions);
            return attrs;
        },
        
        set_state: function(val) {
            if (val == "PENDING" && this.get("state") == "DESTORY") {
                return "DESTROY";
            }
            return val;
        },

        update_state: function() {
            if (this.get("connecting") > 0) {
                this.set({state: "CONNECTING"});
                return
            }
            
            if (this.get_nics(function(nic){ return nic.get("removing") == 1}).length > 0) {
                this.set({state: "DISCONNECTING"});
                return
            }   
            
            if (this.contains_firewalling_nics() > 0) {
                this.set({state: "FIREWALLING"});
                return
            }   
            
            if (this.get("state") == "DESTROY") { 
                this.set({"destroyed":1});
            }
            
            this.set({state:this.get('status')});
        },

        is_public: function() {
            return this.get("public");
        },

        decrease_connecting: function() {
            var conn = this.get("connecting");
            if (!conn) { conn = 0 };
            if (conn > 0) {
                conn--;
            }
            this.set({"connecting": conn});
            this.update_state();
        },

        increase_connecting: function() {
            var conn = this.get("connecting");
            if (!conn) { conn = 0 };
            conn++;
            this.set({"connecting": conn});
            this.update_state();
        },

        connected_to: function(vm) {
            return this.get('linked_to').indexOf(""+vm.id) > -1;
        },

        connected_with_nic_id: function(nic_id) {
            return _.keys(this.get('nics')).indexOf(nic_id) > -1;
        },

        get_nics: function(filter) {
            var nics = synnefo.storage.nics.filter(function(nic) {
                return nic.get('network_id') == this.id;
            }, this);

            if (filter) {
                return _.filter(nics, filter);
            }
            return nics;
        },

        contains_firewalling_nics: function() {
            return this.get_nics(function(n){return n.get('pending_firewall')}).length
        },

        call: function(action, params, success, error) {
            if (action == "destroy") {
                var previous_state = this.get('state');
                var previous_status = this.get('status');

                this.set({state:"DESTROY"});

                var _success = _.bind(function() {
                    if (success) { success() };
                }, this);
                var _error = _.bind(function() {
                    this.set({state: previous_state, status: previous_status})
                    if (error) { error() };
                }, this);

                this.remove(undefined, _error, _success);
            }
            
            if (action == "disconnect") {
                if (this.get("state") == "DESTROY") {
                    return;
                }
                
                _.each(params, _.bind(function(nic_id) {
                    var nic = snf.storage.nics.get(nic_id);
                    this.get("actions").remove("disconnect", nic_id);
                    if (nic) {
                        this.remove_nic(nic, success, error);
                    }
                }, this));
            }
        },

        add_vm: function (vm, callback, error, options) {
            var payload = {add:{serverRef:"" + vm.id}};
            payload._options = options || {};
            return this.api_call(this.api_path() + "/action", "create", 
                                 payload,
                                 undefined,
                                 error,
                                 _.bind(function(){
                                     //this.vms.add_pending(vm.id);
                                     this.increase_connecting();
                                     if (callback) {callback()}
                                 },this), error);
        },

        remove_nic: function (nic, callback, error, options) {
            var payload = {remove:{attachment:"" + nic.get("attachment_id")}};
            payload._options = options || {};
            return this.api_call(this.api_path() + "/action", "create", 
                                 payload,
                                 undefined,
                                 error,
                                 _.bind(function(){
                                     nic.set({"removing": 1});
                                     nic.get_network().update_state();
                                     //this.vms.add_pending_for_remove(vm.id);
                                     if (callback) {callback()}
                                 },this), error);
        },

        rename: function(name, callback) {
            return this.api_call(this.api_path(), "update", {
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
            return storage.vms.filter(function(vm){
                return !vm.in_error_state() && !vm.is_building();
            })
        },

        state_message: function() {
            if (this.get("state") == "ACTIVE" && !this.is_public()) {
                if (this.get("cidr") && this.get("dhcp") == true) {
                    return this.get("cidr");
                } else {
                    return "Private network";
                }
            }
            if (this.get("state") == "ACTIVE" && this.is_public()) {
                  return "Public network";
            }

            return models.Network.STATES[this.get("state")];
        },

        in_progress: function() {
            return models.Network.STATES_TRANSITIONS[this.get("state")] != undefined;
        },

        do_all_pending_actions: function(success, error) {
          var params, actions, action_params;
          actions = _.clone(this.get("actions").actions);
            _.each(actions, _.bind(function(params, action) {
                action_params = _.map(actions[action], function(a){ return _.clone(a)});
                _.each(action_params, _.bind(function(params) {
                    this.call(action, params, success, error);
                }, this));
            }, this));
            this.get("actions").reset();
        }
    });
    
    models.Network.STATES = {
        'ACTIVE': 'Private network',
        'CONNECTING': 'Connecting...',
        'DISCONNECTING': 'Disconnecting...',
        'FIREWALLING': 'Firewall update...',
        'DESTROY': 'Destroying...',
        'PENDING': 'Pending...',
        'ERROR': 'Error'
    }

    models.Network.STATES_TRANSITIONS = {
        'CONNECTING': ['ACTIVE'],
        'DISCONNECTING': ['ACTIVE'],
        'PENDING': ['ACTIVE'],
        'FIREWALLING': ['ACTIVE']
    }

    // Virtualmachine model
    models.VM = models.Model.extend({

        path: 'servers',
        has_status: true,
        initialize: function(params) {
            
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
            
            // handle progress message on instance change
            this.bind("change", _.bind(this.update_status_message, this));
            // force update of progress message
            this.update_status_message(true);
            
            // default values
            this.bind("change:state", _.bind(function(){
                if (this.state() == "DESTROY") { 
                    this.handle_destroy() 
                }
            }, this));

            this.bind("change:nics", _.bind(synnefo.storage.nics.update_vm_nics, synnefo.storage.nics));
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
            
        get_diagnostics: function(success) {
            this.__make_api_call(this.get_diagnostics_url(),
                                 "read", // create so that sync later uses POST to make the call
                                 null, // payload
                                 function(data) {
                                     success(data);
                                 },  
                                 null, 'diagnostics');
        },

        has_diagnostics: function() {
            return this.get("diagnostics") && this.get("diagnostics").length;
        },

        get_progress_info: function() {
            // details about progress message
            // contains a list of diagnostic messages
            return this.get("status_messages");
        },

        get_status_message: function() {
            return this.get('status_message');
        },
        
        // extract status message from diagnostics
        status_message_from_diagnostics: function(diagnostics) {
            var valid_sources_map = synnefo.config.diagnostics_status_messages_map;
            var valid_sources = valid_sources_map[this.get('status')];
            if (!valid_sources) { return null };
            
            // filter messsages based on diagnostic source
            var messages = _.filter(diagnostics, function(diag) {
                return valid_sources.indexOf(diag.source) > -1;
            });

            var msg = messages[0];
            if (msg) {
              var message = msg.message;
              var message_tpl = snf.config.diagnostic_messages_tpls[msg.source];

              if (message_tpl) {
                  message = message_tpl.replace('MESSAGE', msg.message);
              }
              return message;
            }
            
            // no message to display, but vm in build state, display
            // finalizing message.
            if (this.is_building() == 'BUILD') {
                return synnefo.config.BUILDING_MESSAGES['FINAL'];
            }
            return null;
        },

        update_status_message: function(force) {
            // update only if one of the specified attributes has changed
            if (
              !this.keysChanged(['diagnostics', 'progress', 'status', 'state'])
                && !force
            ) { return };
            
            // if user requested to destroy the vm set the appropriate 
            // message.
            if (this.get('state') == "DESTROY") { 
                message = "Terminating..."
                this.set({status_message: message})
                return;
            }
            
            // set error message, if vm has diagnostic message display it as
            // progress message
            if (this.in_error_state()) {
                var d = this.get('diagnostics');
                if (d && d.length) {
                    var message = this.status_message_from_diagnostics(d);
                    this.set({status_message: message});
                } else {
                    this.set({status_message: null});
                }
                return;
            }
            
            // identify building status message
            if (this.is_building()) {
                var self = this;
                var success = function(msg) {
                    self.set({status_message: msg});
                }
                this.get_building_status_message(success);
                return;
            }

            this.set({status_message:null});
        },
            
        // get building status message. Asynchronous function since it requires
        // access to vm image.
        get_building_status_message: function(callback) {
            // no progress is set, vm is in initial build status
            var progress = this.get("progress");
            if (progress == 0 || !progress) {
                return callback(BUILDING_MESSAGES['INIT']);
            }
            
            // vm has copy progress, display copy percentage
            if (progress > 0 && progress <= 99) {
                this.get_copy_details(true, undefined, _.bind(
                    function(details){
                        callback(BUILDING_MESSAGES['COPY'].format(details.copy, 
                                                           details.size, 
                                                           details.progress));
                }, this));
                return;
            }

            // copy finished display FINAL message or identify status message
            // from diagnostics.
            if (progress >= 100) {
                if (!this.has_diagnostics()) {
                        callback(BUILDING_MESSAGES['FINAL']);
                } else {
                        var d = this.get("diagnostics");
                        var msg = this.status_message_from_diagnostics(d);
                        if (msg) {
                              callback(msg);
                        }
                }
            }
        },

        get_copy_details: function(human, image, callback) {
            var human = human || false;
            var image = image || this.get_image(_.bind(function(image){
                var progress = this.get('progress');
                var size = image.get_size();
                var size_copied = (size * progress / 100).toFixed(2);
                
                if (human) {
                    size = util.readablizeBytes(size*1024*1024);
                    size_copied = util.readablizeBytes(size_copied*1024*1024);
                }

                callback({'progress': progress, 'size': size, 'copy': size_copied})
            }, this));
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
            var fetcher = new snf.api.updateHandler({'callback': cb, interval: timeout, id:'stats'});
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
            this.sync("read", this, {
                handles_error:true, 
                url: stats_url, 
                refresh:true, 
                success: _.bind(this.handle_stats_update, this),
                error: _.bind(this.handle_stats_error, this),
                complete: _.bind(function(){this.updating_stats = false;}, this),
                critical: false,
                log_error: false,
                skips_timeouts: true
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
                this.stats_fetcher.interval = this.stats_update_interval;
                this.stats_fetcher.maximum_interval = this.stats_update_interval;
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
        
        remove_meta: function(key, complete, error) {
            var url = this.api_path() + "/meta/" + key;
            this.api_call(url, "delete", undefined, complete, error);
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

            this.api_call(url, "update", payload, complete, error);
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
        get_image: function(callback) {
            if (callback == undefined) { callback = function(){} }
            var image = storage.images.get(this.get('imageRef'));
            if (!image) {
                storage.images.update_unknown_id(this.get('imageRef'), callback);
                return;
            }
            callback(image);
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

        get_meta: function(key, deflt) {
            if (this.get('metadata') && this.get('metadata').values) {
                if (!this.get('metadata').values[key]) { return deflt }
                return _.escape(this.get('metadata').values[key]);
            } else {
                return deflt;
            }
        },

        get_meta_keys: function() {
            if (this.get('metadata') && this.get('metadata').values) {
                return _.keys(this.get('metadata').values);
            } else {
                return [];
            }
        },
        
        // get metadata OS value
        get_os: function() {
            var image = this.get_image();
            return this.get_meta('OS') || (image ? 
                                            image.get_os() || "okeanos" : "okeanos");
        },

        get_gui: function() {
            return this.get_meta('GUI');
        },
        
        connected_to: function(net) {
            return this.get('linked_to').indexOf(net.id) > -1;
        },

        connected_with_nic_id: function(nic_id) {
            return _.keys(this.get('nics')).indexOf(nic_id) > -1;
        },

        get_nics: function(filter) {
            ret = synnefo.storage.nics.filter(function(nic) {
                return parseInt(nic.get('vm_id')) == this.id;
            }, this);

            if (filter) {
                return _.filter(ret, filter);
            }

            return ret;
        },

        get_net_nics: function(net_id) {
            return this.get_nics(function(n){return n.get('network_id') == net_id});
        },

        get_public_nic: function() {
            return this.get_nics(function(n){ return n.get_network().is_public() === true })[0];
        },

        get_hostname: function() {
          var hostname = this.get_meta('hostname');
          if (!hostname) {
            if (synnefo.config.vm_hostname_format) {
              hostname = synnefo.config.vm_hostname_format.format(this.id);
            } else {
              hostname = this.get_public_nic().get('ipv4');
            }
          }
          return hostname;
        },

        get_nic: function(net_id) {
        },

        has_firewall: function() {
            var nic = this.get_public_nic();
            if (nic) {
                var profile = nic.get('firewallProfile'); 
                return ['ENABLED', 'PROTECTED'].indexOf(profile) > -1;
            }
            return false;
        },

        get_firewall_profile: function() {
            var nic = this.get_public_nic();
            if (nic) {
                return nic.get('firewallProfile');
            }
            return null;
        },

        get_addresses: function() {
            var pnic = this.get_public_nic();
            if (!pnic) { return {'ip4': undefined, 'ip6': undefined }};
            return {'ip4': pnic.get('ipv4'), 'ip6': pnic.get('ipv6')};
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
        call: function(action_name, success, error, params) {
            var id_param = [this.id];
            
            params = params || {};
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
                                         error, 'start', params);
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
                                         error, 'reboot', params);
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
                                         error, 'shutdown', params);
                    break;
                case 'console':
                    this.__make_api_call(this.url() + "/action", "create", {'console': {'type':'vnc'}}, function(data) {
                        var cons_data = data.console;
                        success.apply(this, [cons_data]);
                    }, undefined, 'console', params)
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
                                         error, 'destroy', params);
                    break;
                default:
                    throw "Invalid VM action ("+action_name+")";
            }
        },
        
        __make_api_call: function(url, method, data, success, error, action, extra_params) {
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
            _.extend(params, extra_params)
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

        get_diagnostics_url: function() {
            return this.url() + "/diagnostics";
        },

        get_connection_info: function(host_os, success, error) {
            var url = "/machines/connect";
            params = {
                ip_address: this.get_public_nic().get('ipv4'),
                hostname: this.get_hostname(),
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
        defaults: {'nics':[],'linked_to':[]},
        
        parse: function (resp, xhr) {
            // FIXME: depricated global var
            if (!resp) { return []};
            var data = _.filter(_.map(resp.networks.values, _.bind(this.parse_net_api_data, this)),
                               function(e){ return e });
            return data;
        },

        add: function() {
            ret = models.Networks.__super__.add.apply(this, arguments);
            // update nics after each network addition
            ret.each(function(r){
                synnefo.storage.nics.update_net_nics(r);
            });
        },

        reset_pending_actions: function() {
            this.each(function(net) {
                net.get("actions").reset();
            });
        },

        do_all_pending_actions: function() {
            this.each(function(net) {
                net.do_all_pending_actions();
            })
        },

        parse_net_api_data: function(data) {
            // append nic metadata
            // net.get('nics') contains a list of vm/index objects 
            // e.g. {'vm_id':12231, 'index':1}
            // net.get('linked_to') contains a list of vms the network is 
            // connected to e.g. [1001, 1002]
            if (data.attachments && data.attachments.values) {
                data['nics'] = {};
                data['linked_to'] = [];
                _.each(data.attachments.values, function(nic_id){
                  
                  var vm_id = NIC_REGEX.exec(nic_id)[1];
                  var nic_index = parseInt(NIC_REGEX.exec(nic_id)[2]);

                  if (vm_id !== undefined && nic_index !== undefined) {
                      data['nics'][nic_id] = {
                          'vm_id': vm_id, 
                          'index': nic_index, 
                          'id': nic_id
                      };
                      if (data['linked_to'].indexOf(vm_id) == -1) {
                        data['linked_to'].push(vm_id);
                      }
                  }
                });
            }

            if (data.status == "DELETED" && !this.get(parseInt(data.id))) {
              return false;
            }
            return data;
        },

        create: function (name, type, cidr, dhcp, callback) {
            var params = {
                network:{
                    name:name
                }
            };

            if (type) {
                params.network.type = type;
            }
            if (cidr) {
                params.network.cidr = cidr;
            }
            if (dhcp) {
                params.network.dhcp = dhcp;
            }

            if (dhcp === false) {
                params.network.dhcp = false;
            }
            
            return this.api_call(this.path, "create", params, callback);
        },

        get_public: function(){
          return this.filter(function(n){return n.get('public')});
        }
    })

    models.Images = models.Collection.extend({
        model: models.Image,
        path: 'images',
        details: true,
        noUpdate: true,
        supportIncUpdates: false,
        meta_keys_as_attrs: ["OS", "description", "kernel", "size", "GUI"],
        meta_labels: {},
        read_method: 'read',

        // update collection model with id passed
        // making a direct call to the image
        // api url
        update_unknown_id: function(id, callback) {
            var url = getUrl.call(this) + "/" + id;
            this.api_call(this.path + "/" + id, this.read_method, {
              _options:{
                async:true, 
                skip_api_error:true}
              }, undefined, 
            _.bind(function() {
                if (!this.get(id)) {
		            if (this.fallback_service) {
                        // if current service has fallback_service attribute set
                        // use this service to retrieve the missing image model
                        var tmpservice = new this.fallback_service();
                        tmpservice.update_unknown_id(id, _.bind(function(img){
                            img.attributes.status = "DELETED";
                            this.add(img.attributes);
                            callback(this.get(id));
                        }, this));
                    } else {
                        var title = synnefo.config.image_deleted_title || 'Deleted';
                        // else add a dummy DELETED state image entry
                        this.add({id:id, name:title, size:-1, 
                                  progress:100, status:"DELETED"});
                        callback(this.get(id));
                    }   
                } else {
                    callback(this.get(id));
                }
            }, this), _.bind(function(image, msg, xhr) {
                if (!image) {
                    var title = synnefo.config.image_deleted_title || 'Deleted';
                    this.add({id:id, name:title, size:-1, 
                              progress:100, status:"DELETED"});
                    callback(this.get(id));
                    return;
                }
                var img_data = this._read_image_from_request(image, msg, xhr);
                this.add(img_data);
                callback(this.get(id));
            }, this));
        },

        _read_image_from_request: function(image, msg, xhr) {
            return image.image;
        },

        parse: function (resp, xhr) {
            var parsed = _.map(resp.images.values, _.bind(this.parse_meta, this));
            parsed = this.fill_owners(parsed);
            return parsed;
        },

        fill_owners: function(images) {
            // do translate uuid->displayname if needed
            // store display name in owner attribute for compatibility
            var uuids = [];

            var images = _.map(images, function(img, index) {
                if (synnefo.config.translate_uuids) {
                    uuids.push(img['owner']);
                }
                img['owner_uuid'] = img['owner'];
                return img;
            });
            
            if (uuids.length > 0) {
                var handle_results = function(data) {
                    _.each(images, function (img) {
                        img['owner'] = data.uuid_catalog[img['owner_uuid']];
                    });
                }
                // notice the async false
                var uuid_map = this.translate_uuids(uuids, false, 
                                                    handle_results)
            }
            return images;
        },

        translate_uuids: function(uuids, async, cb) {
            var url = synnefo.config.user_catalog_url;
            var data = JSON.stringify({'uuids': uuids});
          
            // post to user_catalogs api
            snf.api.sync('create', undefined, {
                url: url,
                data: data,
                async: async,
                success:  cb
            });
        },

        get_meta_key: function(img, key) {
            if (img.metadata && img.metadata.values && img.metadata.values[key]) {
                return _.escape(img.metadata.values[key]);
            }
            return undefined;
        },

        comparator: function(img) {
            return -img.get_sort_order("sortorder") || 1000 * img.id;
        },

        parse_meta: function(img) {
            _.each(this.meta_keys_as_attrs, _.bind(function(key){
                if (img[key]) { return };
                img[key] = this.get_meta_key(img, key) || "";
            }, this));
            return img;
        },

        active: function() {
            return this.filter(function(img){return img.get('status') != "DELETED"});
        },

        predefined: function() {
            return _.filter(this.active(), function(i) { return !i.get("serverRef")});
        },
        
        fetch_for_type: function(type, complete, error) {
            this.fetch({update:true, 
                        success: complete, 
                        error: error, 
                        skip_api_error: true });
        },
        
        get_images_for_type: function(type) {
            if (this['get_{0}_images'.format(type)]) {
                return this['get_{0}_images'.format(type)]();
            }

            return this.active();
        },

        update_images_for_type: function(type, onStart, onComplete, onError, force_load) {
            var load = false;
            error = onError || function() {};
            function complete(collection) { 
                onComplete(collection.get_images_for_type(type)); 
            }
            
            // do we need to fetch/update current collection entries
            if (load) {
                onStart();
                this.fetch_for_type(type, complete, error);
            } else {
                // fallback to complete
                complete(this);
            }
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
        update_unknown_id: function(id, callback) {
            var url = getUrl.call(this) + "/" + id;
            this.api_call(this.path + "/" + id, "read", {_options:{async:false, skip_api_error:true}}, undefined, 
            _.bind(function() {
                this.add({id:id, cpu:"Unknown", ram:"Unknown", disk:"Unknown", name: "Unknown", status:"DELETED"})
            }, this), _.bind(function(flv) {
                if (!flv.flavor.status) { flv.flavor.status = "DELETED" };
                this.add(flv.flavor);
            }, this));
        },

        parse: function (resp, xhr) {
            return _.map(resp.flavors.values, function(o) { o.disk_template = o['SNF:disk_template']; return o});
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

        get_flavor: function(cpu, mem, disk, disk_template, filter_list) {
            if (!filter_list) { filter_list = this.models };
            
            return this.select(function(flv){
                if (flv.get("cpu") == cpu + "" &&
                   flv.get("ram") == mem + "" &&
                   flv.get("disk") == disk + "" &&
                   flv.get("disk_template") == disk_template &&
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
            var data = resp;
            if (!resp) { return [] };
            data = _.filter(_.map(resp.servers.values, _.bind(this.parse_vm_api_data, this)), function(v){return v});
            return data;
        },

        parse_vm_api_data: function(data) {
            // do not add non existing DELETED entries
            if (data.status && data.status == "DELETED") {
                if (!this.get(data.id)) {
                    return false;
                }
            }

            // OS attribute
            if (this.has_meta(data)) {
                data['OS'] = data.metadata.values.OS || "okeanos";
            }
            
            if (!data.diagnostics) {
                data.diagnostics = [];
            }

            // network metadata
            data['firewalls'] = {};
            data['nics'] = {};
            data['linked_to'] = [];

            if (data['attachments'] && data['attachments'].values) {
                var nics = data['attachments'].values;
                _.each(nics, function(nic) {
                    var net_id = nic.network_id;
                    var index = parseInt(NIC_REGEX.exec(nic.id)[2]);
                    if (data['linked_to'].indexOf(net_id) == -1) {
                        data['linked_to'].push(net_id);
                    }

                    data['nics'][nic.id] = nic;
                })
            }
            
            // if vm has no metadata, no metadata object
            // is in json response, reset it to force
            // value update
            if (!data['metadata']) {
                data['metadata'] = {values:{}};
            }

            return data;
        },

        add: function() {
            ret = models.VMS.__super__.add.apply(this, arguments);
            ret.each(function(r){
                synnefo.storage.nics.update_vm_nics(r);
            });
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

        create: function (name, image, flavor, meta, extra, callback) {

            if (this.copy_image_meta) {
                if (synnefo.config.vm_image_common_metadata) {
                    _.each(synnefo.config.vm_image_common_metadata, 
                        function(key){
                            if (image.get_meta(key)) {
                                meta[key] = image.get_meta(key);
                            }
                    });
                }

                if (image.get("OS")) {
                    meta['OS'] = image.get("OS");
                }
            }
            
            opts = {name: name, imageRef: image.id, flavorRef: flavor.id, metadata:meta}
            opts = _.extend(opts, extra);

            this.api_call(this.path, "create", {'server': opts}, undefined, undefined, callback, {critical: true});
        }

    })
    
    models.NIC = models.Model.extend({
        
        initialize: function() {
            models.NIC.__super__.initialize.apply(this, arguments);
            this.pending_for_firewall = false;
            this.bind("change:firewallProfile", _.bind(this.check_firewall, this));
            this.bind("change:pending_firewall", function(nic) {
                nic.get_network().update_state();
            });
            this.get_vm().bind("remove", function(){
                try {
                    this.collection.remove(this);
                } catch (err) {};
            }, this);
            this.get_network().bind("remove", function(){
                try {
                    this.collection.remove(this);
                } catch (err) {};
            }, this);

        },

        get_vm: function() {
            return synnefo.storage.vms.get(parseInt(this.get('vm_id')));
        },

        get_network: function() {
            return synnefo.storage.networks.get(this.get('network_id'));
        },

        get_v6_address: function() {
            return this.get("ipv6");
        },

        get_v4_address: function() {
            return this.get("ipv4");
        },

        set_firewall: function(value, callback, error, options) {
            var net_id = this.get('network_id');
            var self = this;

            // api call data
            var payload = {"firewallProfile":{"profile":value}};
            payload._options = _.extend({critical: false}, options);
            
            this.set({'pending_firewall': value});
            this.set({'pending_firewall_sending': true});
            this.set({'pending_firewall_from': this.get('firewallProfile')});

            var success_cb = function() {
                if (callback) {
                    callback();
                }
                self.set({'pending_firewall_sending': false});
            };

            var error_cb = function() {
                self.reset_pending_firewall();
            }
            
            this.get_vm().api_call(this.get_vm().api_path() + "/action", "create", payload, success_cb, error_cb);
        },

        reset_pending_firewall: function() {
            this.set({'pending_firewall': false});
            this.set({'pending_firewall': false});
        },

        check_firewall: function() {
            var firewall = this.get('firewallProfile');
            var pending = this.get('pending_firewall');
            var previous = this.get('pending_firewall_from');
            if (previous != firewall) { this.get_vm().require_reboot() };
            this.reset_pending_firewall();
        }
        
    });

    models.NICs = models.Collection.extend({
        model: models.NIC,
        
        add_or_update: function(nic_id, data, vm) {
            var params = _.clone(data);
            var vm;
            params.attachment_id = params.id;
            params.id = params.id + '-' + params.network_id;
            params.vm_id = parseInt(NIC_REGEX.exec(nic_id)[1]);

            if (!this.get(params.id)) {
                this.add(params);
                var nic = this.get(params.id);
                vm = nic.get_vm();
                nic.get_network().decrease_connecting();
                nic.bind("remove", function() {
                    nic.set({"removing": 0});
                    if (this.get_network()) {
                        // network might got removed before nic
                        nic.get_network().update_state();
                    }
                });

            } else {
                this.get(params.id).set(params);
                vm = this.get(params.id).get_vm();
            }
            
            // vm nics changed, trigger vm update
            if (vm) { vm.trigger("change", vm)};
        },
        
        reset_nics: function(nics, filter_attr, filter_val) {
            var nics_to_check = this.filter(function(nic) {
                return nic.get(filter_attr) == filter_val;
            });
            
            _.each(nics_to_check, function(nic) {
                if (nics.indexOf(nic.get('id')) == -1) {
                    this.remove(nic);
                } else {
                }
            }, this);
        },

        update_vm_nics: function(vm) {
            var nics = vm.get('nics');
            this.reset_nics(_.map(nics, function(nic, key){
                return key + "-" + nic.network_id;
            }), 'vm_id', vm.id);

            _.each(nics, function(val, key) {
                var net = synnefo.storage.networks.get(val.network_id);
                if (net && net.connected_with_nic_id(key) && vm.connected_with_nic_id(key)) {
                    this.add_or_update(key, vm.get('nics')[key], vm);
                }
            }, this);
        },

        update_net_nics: function(net) {
            var nics = net.get('nics');
            this.reset_nics(_.map(nics, function(nic, key){
                return key + "-" + net.get('id');
            }), 'network_id', net.id);

            _.each(nics, function(val, key) {
                var vm = synnefo.storage.vms.get(val.vm_id);
                if (vm && net.connected_with_nic_id(key) && vm.connected_with_nic_id(key)) {
                    this.add_or_update(key, vm.get('nics')[key], vm);
                }
            }, this);
        }
    });

    models.PublicKey = models.Model.extend({
        path: 'keys',
        base_url: '/ui/userdata',
        details: false,
        noUpdate: true,


        get_public_key: function() {
            return cryptico.publicKeyFromString(this.get("content"));
        },

        get_filename: function() {
            return "{0}.pub".format(this.get("name"));
        },

        identify_type: function() {
            try {
                var cont = snf.util.validatePublicKey(this.get("content"));
                var type = cont.split(" ")[0];
                return synnefo.util.publicKeyTypesMap[type];
            } catch (err) { return false };
        }

    })
    
    models.PublicKeys = models.Collection.extend({
        model: models.PublicKey,
        details: false,
        path: 'keys',
        base_url: '/ui/userdata',
        noUpdate: true,

        generate_new: function(success, error) {
            snf.api.sync('create', undefined, {
                url: getUrl.call(this, this.base_url) + "/generate", 
                success: success, 
                error: error,
                skip_api_error: true
            });
        },

        add_crypto_key: function(key, success, error, options) {
            var options = options || {};
            var m = new models.PublicKey();

            // guess a name
            var name_tpl = "my generated public key";
            var name = name_tpl;
            var name_count = 1;
            
            while(this.filter(function(m){ return m.get("name") == name }).length > 0) {
                name = name_tpl + " " + name_count;
                name_count++;
            }
            
            m.set({name: name});
            m.set({content: key});
            
            options.success = function () { return success(m) };
            options.errror = error;
            options.skip_api_error = true;
            
            this.create(m.attributes, options);
        }
    })
    
    // storage initialization
    snf.storage.images = new models.Images();
    snf.storage.flavors = new models.Flavors();
    snf.storage.networks = new models.Networks();
    snf.storage.vms = new models.VMS();
    snf.storage.keys = new models.PublicKeys();
    snf.storage.nics = new models.NICs();

    //snf.storage.vms.fetch({update:true});
    //snf.storage.images.fetch({update:true});
    //snf.storage.flavors.fetch({update:true});

})(this);
