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
        var append = "/";
        if (baseurl.split("").reverse()[0] == "/") {
          append = "";
        }
        return baseurl + append + this.path;
    }

    // i18n
    BUILDING_MESSAGES = window.BUILDING_MESSAGES || {'INIT': 'init', 'COPY': '{0}, {1}, {2}', 'FINAL': 'final'};

    // Base object for all our models
    models.Model = bb.Model.extend({
        sync: snf.api.sync,
        api: snf.api,
        api_type: 'compute',
        has_status: false,
        auto_bind: [],


        initialize: function() {
            var self = this;
            
            this._proxy_model_cache = {};
            _.each(this.auto_bind, function(fname) {
              self[fname] = _.bind(self[fname], self);
            });

            if (this.has_status) {
                this.bind("change:status", this.handle_remove);
                this.handle_remove();
            }
            
            this.api_call = _.bind(this.api.call, this);
              
            if (this.proxy_attrs) {
              this.init_proxy_attrs();             
            }

            if (this.storage_attrs) {
              this.init_storage_attrs();
            }

            if (this.model_actions) {
              this.init_model_actions();             
            }

            models.Model.__super__.initialize.apply(this, arguments);

        },
        
        // Initialize model actions object
        // For each entry in model's model_action object register the relevant 
        // model proxy `can_<actionname>` attributes.
        init_model_actions: function() {
          var actions = _.keys(this.model_actions);
          this.set({
            "actions": new models._ActionsModel({}, {
              actions: actions,
              model: this
            })
          });
          this.actions = this.get("actions");
          this.actions.bind("set-pending", function(action) {
            this.trigger("action:set-pending", action, this.actions, this);
          }, this);
          this.actions.bind("unset-pending", function(action) {
            this.trigger("action:unset-pending", action, this.actions, this);
          }, this);
          this.actions.bind("reset-pending", function() {
            this.trigger("action:reset-pending", this.actions, this);
          }, this);

          _.each(this.model_actions, function(params, key){
            var attr = 'can_' + key;
            if (params.length == 0) { return }
            var deps = params[0];
            var cb = _.bind(params[1], this);
            _.each(deps, function(dep) {
              this._set_proxy_attr(attr, dep, cb);
            }, this);
          }, this);
        },
        
        // Initialize proxy storage model attributes. These attribues allows 
        // us to automatically access cross collection associated objects.
        init_storage_attrs: function() {
          _.each(this.storage_attrs, function(params, attr) {
            var store, key, attr_name;
            store = synnefo.storage[params[0]];
            key = params[1];
            attr_resolver = params[2];
            if (!attr_resolver) {
              attr_resolver = function(model, attr) {
                return model.get(attr);
              }
            }
            attr_name = attr;
          
            var resolve_related_instance = function(storage, attr_name, val) {
              var data = {};

              if (!val) { 
                // update with undefined and return
                data[key] = undefined;
                this.set(data);
                return;
              };
            
              // retrieve related object (check if its a Model??)
              var obj = store.get(val);
              
              if (obj) {
                // set related object
                data[attr_name] = obj;
                this.set(data, {silent:true})
                this.trigger("change:" + attr_name, obj);
              } else {
                var self = this;
                var retry_to_resolve = function(store, val, key) {
                  var retries = 0;
                  var retry = window.setInterval(function(){
                    retries++;
                    if (retries > 200) {
                      clearInterval(retry);
                    }
                    var obj = store.get(val);
                    if (obj) {
                      data[key] = obj;
                      self.set(data, {silent:false});
                      clearInterval(retry);
                    }
                  }, 500);
                  return retry
                }
                retry_to_resolve(store, val, key);
              }
            }
            
            var self = this;
            function init_bindings(instance, store, key, attr, attr_resolver) {
              instance.bind('change:' + attr, function(model) {
                resolve_related_instance.call(model, store, key, attr_resolver(model, attr));
              }, this);

              instance.bind('add', function(model) {
                resolve_related_instance.call(model, store, key, attr_resolver(model, attr));
              }, this);
            }

            init_bindings(this, store, key, attr, attr_resolver);
            resolve_related_instance.call(this, store, key, attr_resolver(this, attr));
          }, this);
        },
        
        _proxy_model_cache: {},
        
        _bind_model: function(model, attr, check_attr, cb) {
          var proxy_cache_key = attr + '_' + check_attr;
          if (this._proxy_model_cache[proxy_cache_key]) {
            var proxy = this._proxy_model_cache[proxy_cache_key];
            proxy[0].unbind('change', proxy[1]);
          }
          var data = {};
          var changebind = _.bind(function() {
            data[attr] = cb.call(this, this.get(check_attr));
            this.set(data);
          }, this);
          model.bind('change', changebind);
          this._proxy_model_cache[proxy_cache_key] = [model, changebind];
        },

        _bind_attr: function(attr, check_attr, cb) {
          this.bind('change:' + check_attr, function() {
            if (this.get(check_attr) instanceof models.Model) {
              var model = this.get(check_attr);
              this._bind_model(model, attr, check_attr, cb);
            }
            var val = cb.call(this, this.get(check_attr));
            var data = {};
            if (this.get(attr) !== val) {
              data[attr] = val;
              this.set(data);
            }
          }, this);
        },

        _set_proxy_attr: function(attr, check_attr, cb) {
          // initial set
          var data = {};
          data[attr] = cb.call(this, this.get(check_attr));
          if (data[attr] !== undefined) {
            this.set(data, {silent:true});
          }
          if(this.get(check_attr) instanceof models.Model) {
            this._bind_model(this.get(check_attr), attr, check_attr, cb);
          }
          this._bind_attr(attr, check_attr, cb);
        },

        init_proxy_attrs: function() {
          _.each(this.proxy_attrs, function(opts, attr){
            var cb = opts[1];
            _.each(opts[0], function(check_attr){
              this._set_proxy_attr(attr, check_attr, cb)
            }, this);
          }, this);
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
        
        mapAttrs: function() {
          var params = _.toArray(arguments);
          return this.map(function(i) { 
            return _.map(params, function(attr) { 
              return i.get(attr);
            });
          })
        },

        mapAttr: function(attr) {
          return this.map(function(i) { return i.get(attr)})
        },

        filterAttr: function(attr, eq) {
          return this.filter(function(i) { return i.get(attr) === eq})
        },

        initialize: function() {
            models.Collection.__super__.initialize.apply(this, arguments);
            this.api_call = _.bind(this.api.call, this);
            if (this.sortFields) {
              _.each(this.sortFields, function(f) {
                this.bind("change:" + f, _.bind(this.resort, this));
              }, this);
            }
        },
          
        resort: function() {
          this.sort();
        },

        url: function(options, method) {
            return getUrl.call(this, this.base_url) + (
                    options.details || this.details && method != 'create' ? '/detail' : '');
        },
        
        delay_fetch: function(delay, options) {
          window.setTimeout(_.bind(function() {
            this.fetch(options)
          }, this), delay);
        },

        fetch: function(options) {
            if (!options) { options = {} };
            // default to update
            if (!this.noUpdate) {
                if (options.update === undefined) { options.update = true };
                if (!options.removeMissing && options.refresh) { 
                  options.removeMissing = true;
                };
                // for collections which associated models don't support 
                // deleted state identification through attributes, resolve  
                // deleted entries by checking for missing objects in fetch 
                // responses.
                if (this.updateEntries && options.removeMissing === undefined) {
                  options.removeMissing = true;
                }
            } else {
                if (options.refresh === undefined) {
                    options.refresh = true;
                    if (this.updateEntries) {
                      options.update = true;
                      options.removeMissing = true;
                    }
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
                if (coll.add_on_create) {
                  coll.add(nextModel, options);
                }
                synnefo.api.trigger("quota:update");
                if (success) success(nextModel, resp, xhr);
            };
            model.save(null, options);
            return model;
        },

        get_fetcher: function(interval, increase, fast, increase_after_calls, 
                              max, initial_call, params, fetcher_id) {
            var fetch_params = params || {};
            var handler_options = {};

            fetch_params.skips_timeouts = true;
            handler_options.interval = interval;
            handler_options.increase = increase;
            handler_options.fast = fast;
            handler_options.increase_after_calls = increase_after_calls;
            handler_options.max= max;
            handler_options.id = fetcher_id || "collection";

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
            return parseInt(this.get('metadata') ? this.get('metadata').size : -1)
        },

        get_description: function(escape) {
            if (escape == undefined) { escape = true };
            if (escape) { return this.escape('description') || "No description available"}
            return this.get('description') || "No description available."
        },

        has_metadata: function() {
            if (this.get('metadata')) {
                return !_.isEmpty(this.get('metadata'));
            }
            return false;
        },

        get_meta: function(key) {
            if (this.get('metadata') && this.get('metadata')) {
                if (!this.get('metadata')[key]) { return null }
                return _.escape(this.get('metadata')[key]);
            } else {
                return null;
            }
        },

        get_meta_keys: function() {
            if (this.get('metadata') && this.get('metadata')) {
                return _.keys(this.get('metadata'));
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

        listing_section: function() {
          var owner = this.get('owner_uuid');
          if (_.include(synnefo.config.image_listing_users, owner)) {
            var props = this.get('properties') || {};
            return props.listing_section;
          }
        },

        owned_by: function(user) {
          if (!user) { user = synnefo.user }
          return user.get_username() == this.get('owner_uuid');
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
            if (!users) {
                var osfamily = this.get_meta('osfamily');
                if (osfamily == 'windows') { 
                  users = ['Administrator'];
                } else {
                  users = ['root'];
                }
            }
            return users;
        },

        get_sort_order: function() {
            return parseInt(this.get('metadata') ? this.get('metadata').sortorder : -1)
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
            var exclude_list = synnefo.config.ssh_support_osfamily_exclude_list || [];
            var os = this.get_os();
            if (exclude_list.indexOf(os) > -1) {
                return false;
            } else if (!this.has_metadata() ||
                       this.get_meta("EXCLUDE_ALL_TASKS") != null ||
                       this.get_meta("EXCLUDE_TASK_ENFORCEPERSONALITY") != null) {
                return false;
            }
            return true;
        },

        _supports_password: function () {
          if (!this.has_metadata() ||
              this.get_meta('EXCLUDE_ALL_TASKS') != null ||
              this.get_meta("EXCLUDE_TASK_CHANGEPASSWORD") != null) {
              return false;
          }
          return true;
        },

        supports: function(feature) {
            if (feature == "ssh") {
                return this._supports_ssh()
            } else if (feature == "password") {
                return this._supports_password()
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
                    owner: pathinfo.user
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
            return parseInt(this.get("disk") * 1024)
        },

        get_ram_size: function() {
            return parseInt(this.get("ram"))
        },

        get_disk_template_info: function() {
            var info = snf.config.flavors_disk_templates_info[this.get("disk_template")];
            if (!info) {
                info = { name: this.get("disk_template"), description:'' };
            }
            return info
        },

        get_volume_type: function() {
            return parseInt(this.get("SNF:volume_type"))
        },

        disk_to_bytes: function() {
            return parseInt(this.get("disk")) * 1024 * 1024 * 1024;
        },

        ram_to_bytes: function() {
            return parseInt(this.get("ram")) * 1024 * 1024;
        },

        get_readable: function(key) {
          var parser = function(v) { return v }
          var getter = this.get;
          if (key == 'ram') {
            parser = synnefo.util.readablizeBytes
            getter = this.ram_to_bytes
          }
          if (key == 'disk') {
            parser = synnefo.util.readablizeBytes
            getter = this.disk_to_bytes
          }
          if (key == 'cpu') {
            parser = function(v) { return v + 'x' }
          }

          var val = getter.call(this, key);
          return parser(val);
        },

        quotas: function() {
          return {
            'cyclades.vm': 1,
            'cyclades.disk': this.disk_to_bytes(), 
            'cyclades.ram': this.ram_to_bytes(),
            'cyclades.cpu': this.get('cpu')
          }
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

    // Virtualmachine model
    models.VM = models.Model.extend({

        path: 'servers',
        has_status: true,
        proxy_attrs: {
          'busy': [
            ['status', 'state'], function() {
              return !_.contains(['ACTIVE', 'STOPPED'], this.get('status'));
            }
          ],
          'in_progress': [
            ['status', 'state'], function() {
              return this.in_transition();
            }
          ],
          'shared_to_me': [
            ['user_id', 'is_ghost'], function() {
              return !this.get('is_ghost') &&
                (this.get('user_id') != snf.user.current_username);
            }
          ]
        },

        storage_attrs: {
          'tenant_id': ['projects', 'project']
        },

        initialize: function(params) {
            var self = this;

            this.ports = new Backbone.FilteredCollection(undefined, {
              collection: synnefo.storage.ports,
              collectionFilter: function(m) {
                return self.id == m.get('device_id')
            }});

            this.volumes = new Backbone.FilteredCollection(undefined, {
              collection: synnefo.storage.volumes,
              collectionFilter: function(m) {
                return self.id == m.get('_vm_id');
            }});

            this.pending_firewalls = {};
            
            models.VM.__super__.initialize.apply(this, arguments);

            this.set({state: params.status || "UNKNOWN"});
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
            this.bind("change:task_state", _.bind(this.update_status, this));
            // force update of progress message
            this.update_status_message(true);
            
            // default values
            this.bind("change:state", _.bind(function(){
                if (this.state() == "DESTROY") { 
                    this.handle_destroy() 
                }
            }, this));

        },
        
        get_public_ips: function() {
          var ips = [];
          this.ports.filter(function(port) {
            if (port.get('network') && !port.get('network').get('is_public')) { return }
            if (!port.get("ips")) { return }
            port.get("ips").each(function(ip) {
              ips.push(ip);
            });
          });
          return ips;
        },

        has_public_ip: function() {
          return this.ports.filter(function(port) {
            return port.get("network") && 
                   port.get("network").get("is_public") && 
                   port.get("ips").length > 0;
          }).length > 0;
        },

        has_public_ipv6: function() {
          return this.has_ip_version("v6", true);
        },

        has_public_ipv4: function() {
          return this.has_ip_version("v4", true);
        },
        
        has_ip_version: function(ver, public) {
          var found = false;
          this.ports.each(function(port) {
            if (found) { return }
            if (public !== undefined) {
              if (port.get("network") && 
                  port.get("network").get("is_public") != public) {
                return
              }
            }
            port.get('ips').each(function(ip) {
              if (found) { return }
              if (ip.get("type") == ver) {
                found = true
              }
            })
          }, this)
          return found;
        },
        
        is_ext: function() {
            if (this.get('is_ghost')) { return undefined }
            var tpl = this.get_flavor().get('disk_template');
            return tpl.indexOf('ext_') == 0;
        },

        status: function(st) {
            if (!st) { return this.get("status")}
            return this.set({status:st});
        },
        
        update_status: function() {
            this.set_status(this.get('status'));
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
            var state = this.state_for_api_status(st);
            this.set({'state': state}, {silent: true});
            
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
            if (this.get('is_ghost')) { return }

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
            if (this.get('is_ghost')) { return }

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
            if ((!this.do_update_stats && !force) || this.updating_stats ||
               this.get('is_ghost')) {
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

        get_attachment: function(id) {
          var attachment = undefined;
          _.each(this.get("attachments"), function(a) {
            if (a.id == id) {
              attachment = a;
            }
          });
          return attachment
        },

        _set_stats: function(stats) {
            var silent = silent === undefined ? false : silent;
            // unavailable stats while building
            if (this.get("status") == "BUILD" ||
                this.get('status') == "DESTROY" ||
                this.get('is_ghost')) {
                this.stats_available = false;
            } else { this.stats_available = true; }

            this.set({stats: stats}, {silent:true});
            this.trigger("stats:update", stats);
        },

        unbind: function() {
            models.VM.__super__.unbind.apply(this, arguments);
        },
        
        can_start: function(flv, count_current) {
          if (!this.can_resize()) { return false; }
          var self = this;
          var get_quota = function(key) {
            if (!self.get('project')) { return false; }
            var quota = self.get('project').quotas.get(key);
            return quota && quota.get('available');
          }
          var flavor = flv || this.get_flavor();
          var vm_ram_current = 0, vm_cpu_current = 0;
          if (flv && this.is_active() || flv && count_current) {
            var current = this.get_flavor();
            vm_ram_current = current.ram_to_bytes();
            vm_cpu_current = parseInt(current.get('cpu'));
          }
          var vm_ram = flavor.ram_to_bytes();
          var vm_cpu = parseInt(flavor.get('cpu'));
          var available_cpu = get_quota('cyclades.cpu') + vm_cpu_current;
          var available_ram = get_quota('cyclades.ram') + vm_ram_current;
          if (vm_ram > available_ram || vm_cpu > available_cpu) { return false }
          return true
        },

        can_attach_volume: function() {
          return _.contains(["ACTIVE", "STOPPED"], this.get("status")) && 
                 !this.get('suspended')
        },

        can_connect: function() {
          if (!synnefo.config.hotplug_enabled && this.is_active()) { return false }
          return _.contains(["ACTIVE", "STOPPED"], this.get("status")) && 
                 !this.get('suspended')
        },

        can_disconnect: function() {
          return _.contains(["ACTIVE", "STOPPED"], this.get("status"))
        },

        can_resize: function() {
          return this.get('status') == 'STOPPED' && 
                                    !this.get('project').get('missing');
        },

        can_reassign: function() {
          return true;
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
          if (this.status_fetcher) {
            this.stats_fetcher.stop();
          }
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
        
        active_resources: function() {
          if (this.get("status") == "STOPPED") {
            return ["cyclades.vm", "cyclades.disk"]
          }
          return ["cyclades.vm", "cyclades.disk", "cyclades.cpu", 
                  "cyclades.ram"]
        },

        // machine is active
        is_active: function() {
            return models.VM.ACTIVE_STATES.indexOf(this.state()) > -1;
        },
        
        // machine is building 
        is_building: function() {
            return models.VM.BUILDING_STATES.indexOf(this.state()) > -1;
        },
        
        is_rebooting: function() {
            return this.state() == 'REBOOT';
        },

        in_error_state: function() {
            return this.state() === "ERROR"
        },

        // user can connect to machine
        is_connectable: function() {
            return models.VM.CONNECT_STATES.indexOf(this.state()) > -1;
        },
        
        remove_meta: function(key, complete, error) {
            var url = this.api_path() + "/metadata/" + key;
            this.api_call(url, "delete", undefined, complete, error);
        },

        save_meta: function(meta, complete, error) {
            var url = this.api_path() + "/metadata/" + meta.key;
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
                
            if (args.length > 0 && models.VM.STATES.indexOf(args[0]) > -1) {
                this.set({'state': args[0]});
            }

            return this.get('state');
        },
        
        // get the state that the api status corresponds to
        state_for_api_status: function(status) {
            return this.state_transition(this.state(), status);
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
            if (this.get('is_ghost')) { return undefined }
            if (callback == undefined) { callback = function(){} }
            var image = storage.images.get(this.get('image'));
            if (!image) {
                storage.images.update_unknown_id(this.get('image'), callback);
                return;
            }
            callback(image);
            return image;
        },
        
        // get flavor object
        get_flavor: function() {
            if (this.get('is_ghost')) { return undefined }
            var flv = storage.flavors.get(this.get('flavor'));
            if (!flv) {
                storage.flavors.update_unknown_id(this.get('flavor'));
                flv = storage.flavors.get(this.get('flavor'));
            }
            return flv;
        },

        get_resize_flavors: function() {
          var vm_flavor = this.get_flavor();
          var flavors = synnefo.storage.flavors.filter(function(f){
              return f.get('disk_template') ==
              vm_flavor.get('disk_template') && f.get('disk') ==
              vm_flavor.get('disk');
          });
          return flavors;
        },

        get_flavor_quotas: function() {
          if (this.get('is_ghost')) { return {} }
          var flavor = this.get_flavor();
          return {
            cpu: flavor.get('cpu'), 
            ram: flavor.get_ram_size(), 
            disk:flavor.get_disk_size()
          }
        },

        get_meta: function(key, deflt) {
            if (this.get('metadata') && this.get('metadata')) {
                if (!this.get('metadata')[key]) { return deflt }
                return _.escape(this.get('metadata')[key]);
            } else {
                return deflt;
            }
        },

        get_meta_keys: function() {
            if (this.get('metadata') && this.get('metadata')) {
                return _.keys(this.get('metadata'));
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
        
        get_hostname: function() {
          if (this.get('is_ghost')) { return 'Unknown FQDN' }
          return this.get_meta('hostname') || this.get('fqdn') || synnefo.config.no_fqdn_message;
        },

        // get actions that the user can execute
        // depending on the vm state/status
        get_available_actions: function() {
            if (this.get('suspended')) { return [] }
            return models.VM.AVAILABLE_ACTIONS[this.state()];
        },

        set_profile: function(profile, net_id) {
        },
        
        // call rename api
        rename: function(new_name) {
            //this.set({'name': new_name});
            var self = this;
            this.sync("update", this, {
                critical: true,
                data: {
                    'server': {
                        'name': new_name
                    }
                }, 
                success: _.bind(function(){
                    snf.api.trigger("call");
                    this.set({'name': new_name});
                }, this)
            });
        },
        
        get_console_url: function(data) {
            var url_params = {
                machine: this.get("name"),
                machine_hostname: this.get_hostname(),
                host: data.host,
                port: data.port,
                password: data.password
            }
            return synnefo.config.ui_console_url + '?' + $.param(url_params);
        },
        
        set_firewall: function(nic, value, success_cb, error_cb) {
          var self = this;
          var success = function() { self.require_reboot(); success_cb() }
          var error = function() { error_cb() }
          var data = {'nic': nic.id, 'profile': value, 'display': true};
          var url = this.url() + "/action";
          //var params = {skip_api_error: false, display: true};
          this.call('firewallProfile', success, error, data);
        },

        connect_floating_ip: function(ip, cb, error) {
          var self = this;
          var from_status = this.get('status');
          this.set({'status': 'CONNECTING'});
          synnefo.storage.ports.create({
            port: {
              network_id: ip.get('floating_network_id'),
              device_id: this.id,
              fixed_ips: [{'ip_address': ip.get('floating_ip_address')}]
            }
          }, {
            success: cb, 
            error: function() { error && error() },
            skip_api_error: false
          });
        },
        
        create_snapshot: function(snapshot_params, callback, error_cb) {
          var volume = this.get('volumes') && this.get('volumes').length ? 
                       this.get('volumes')[0] : undefined;
          var params = _.extend({
            'metadata': {},
            'volume_id': volume
          }, snapshot_params);

          snf.api.sync('create', undefined, {
              url: synnefo.config.api_urls.volume + '/snapshots/',
              data: JSON.stringify({snapshot:params}),
              success: callback, 
              error: error_cb,
              skip_api_error: false,
	      contentType: 'application/json'
          });
        },

        // action helper
        call: function(action_name, success, error, params) {
            var id_param = [this.id];
            
            params = params || {};
            success = success || function() {};
            error = error || function() {};

            var self = this;

            if (this.get('is_ghost')) { return }

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
                                         {reboot:{}}, // payload
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
                    this.__make_api_call(this.url() + "/action", "create", 
                                         {'console': {'type':'vnc-wss'}},
                                         function(data) {
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
                                             success.apply(this, arguments);
                                             synnefo.api.trigger("quotas:call", 20);
                                         },  
                                         error, 'destroy', params);
                    break;
                case 'reassign':
                    this.__make_api_call(this.get_action_url(), // vm actions url
                                         "create", // create so that sync later uses POST to make the call
                                         {reassign: {project:params.project_id}}, // payload
                                         function() {
                                             self.state('reassign');
                                             self.set({'tenant_id': params.project_id});
                                             success.apply(this, arguments);
                                             snf.api.trigger("call");
                                         },  
                                         error, 'reassign', params);
                    break;
                case 'resize':
                    this.__make_api_call(this.get_action_url(), // vm actions url
                                         "create", // create so that sync later uses POST to make the call
                                         {resize: {flavorRef:params.flavor}}, // payload
                                         function() {
                                             self.state('RESIZE');
                                             success.apply(this, arguments);
                                             snf.api.trigger("call");
                                         },  
                                         error, 'resize', params);
                    break;
                case 'destroy':
                    this.__make_api_call(this.url(), // vm actions url
                                         "delete", // create so that sync later uses POST to make the call
                                         undefined, // payload
                                         function() {
                                             // set state after successful call
                                             self.state('DESTROY');
                                             success.apply(this, arguments);
                                             synnefo.storage.quotas.get('cyclades.vm').decrease();

                                         },  
                                         error, 'destroy', params);
                    break;
                case 'firewallProfile':
                    this.__make_api_call(this.get_action_url(), // vm actions url
                                         "create",
                                         {firewallProfile:{nic:params.nic, profile:params.profile}}, // payload
                                         function() {
                                             success.apply(this, arguments);
                                             snf.api.trigger("call");
                                         },  
                                         error, 'start', params);
                    break;
                default:
                    throw "Invalid VM action ("+action_name+")";
            }
        },
        
        __make_api_call: function(url, method, data, success, error, action, 
                                  extra_params) {
            var self = this;
            error = error || function(){};
            success = success || function(){};

            var params = {
                url: url,
                data: data,
                success: function() { 
                  self.handle_action_succeed.apply(self, arguments); 
                  success.apply(this, arguments)
                },
                error: function() { 
                  self.handle_action_fail.apply(self, arguments);
                  error.apply(this, arguments)
                },
                error_params: { ns: "Machines actions", 
                                title: "'" + this.get("name") + "'" + " " + action + " failed", 
                                extra_details: {
                                  'Machine ID': this.id, 
                                  'URL': url, 
                                  'Action': action || "undefined" },
                                allow_reload: false
                              },
                display: false,
                critical: false
            }
            _.extend(params, extra_params);
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

        get_users: function() {
            var image;
            var users = [];
            try {
              var users = this.get_meta('users').split(" ");
            } catch (err) { users = null }
            if (!users) {
              image = this.get_image();
              if (image) {
                  users = image.get_created_users();
              }
            }
            return users;
        },

        get_connection_info: function(host_os, success, error) {
            var url = synnefo.config.ui_connect_url;
            var users = this.get_users();

            params = {
                ip_address: this.get_hostname(),
                hostname: this.get_hostname(),
                os: this.get_os(),
                host_os: host_os,
                ports: JSON.stringify(this.get('SNF:port_forwarding') || {}),
                srv: this.id
            }
            
            if (users.length) { 
                params['username'] = _.last(users)
            }

            url = url + "?" + $.param(params);

            var ajax = snf.api.sync("read", undefined, { url: url, 
                                                         error:error, 
                                                         success:success, 
                                                         handles_error:1});
        }
    });
    
    models.VM.ACTIONS = [
        'start',
        'shutdown',
        'reboot',
        'console',
        'destroy',
        'resize',
        'reassign',
        'snapshot'
    ]

    models.VM.TASK_STATE_STATUS_MAP = {
      'BUILDING': 'BUILD',
      'REBOOTING': 'REBOOT',
      'STOPPING': 'SHUTDOWN',
      'STARTING': 'START',
      'RESIZING': 'RESIZE',
      'REASSIGNING': 'REASSIGN',
      'CONNECTING': 'CONNECT',
      'DISCONNECTING': 'DISCONNECT',
      'UNKNOWN': 'UNKNOWN',
      'ATTACHING_VOLUME': 'ATTACH_VOLUME',
      'DETACHING_VOLUME': 'DETACH_VOLUME',
      'DESTROYING': 'DESTROY',
    }

    models.VM.AVAILABLE_ACTIONS = {
        'UNKNOWN'       : [],
        'BUILD'         : ['destroy'],
        'REBOOT'        : ['destroy'],
        'STOPPED'       : ['start', 'destroy', 'reassign', 'resize', 'snapshot'],
        'ACTIVE'        : ['shutdown', 'destroy', 'reboot', 'console', 'reassign', 'resize', 'snapshot'],
        'ERROR'         : ['destroy'],
        'DELETED'       : ['destroy'],
        'DESTROY'       : ['destroy'],
        'SHUTDOWN'      : ['destroy'],
        'START'         : ['destroy'],
        'CONNECT'       : ['destroy'],
        'DISCONNECT'    : ['destroy'],
        'DETACH_VOLUME' : ['destroy'],
        'ATTACH_VOLUME' : ['destroy'],
        'RESIZE'        : ['destroy'],
        'REASSIGN'      : ['destroy']
    }
    
    models.VM.AVAILABLE_ACTIONS_INACTIVE = {}

    // api status values
    models.VM.STATUSES = [
        'UNKNOWN',
        'BUILD',
        'REBOOT',
        'STOPPED',
        'ACTIVE',
        'ERROR',
        'DELETED',
        'REASSIGN',
        'RESIZE'
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
        'SHUTDOWN',
        'START',
        'CONNECT',
        'DISCONNECT',
        'FIREWALL',
        'DETACH_VOLUME',
        'ATTACH_VOLUME',
        'REASSIGN',
        'RESIZE'
    ]);
    
    models.VM.STATES_TRANSITIONS = {
        'DESTROY' : ['DELETED'],
        'SHUTDOWN': ['ERROR', 'STOPPED', 'DESTROY'],
        'STOPPED': ['ERROR', 'ACTIVE', 'DESTROY', 'RESIZE', 'REASSIGN'],
        'ACTIVE': ['ERROR', 'STOPPED', 'REBOOT', 'SHUTDOWN', 'DESTROY', 'REASSIGN'],
        'START': ['ERROR', 'ACTIVE', 'DESTROY'],
        'REBOOT': ['ERROR', 'ACTIVE', 'STOPPED', 'DESTROY'],
        'BUILD': ['ERROR', 'ACTIVE', 'DESTROY'],
        'RESIZE': ['ERROR', 'STOPPED'],
        'REASSIGN': ['ERROR', 'STOPPED', 'ACTIVE']
    }

    models.VM.TRANSITION_STATES = [
        'DESTROY',
        'SHUTDOWN',
        'START',
        'REBOOT',
        'BUILD',
        'RESIZE',
        'REASSIGN',
        'DISCONNECT',
        'CONNECT',
        'ATTACH_VOLUME',
        'DETACH_VOLUME'
    ]

    models.VM.ACTIVE_STATES = [
        'BUILD', 'REBOOT', 'ACTIVE',
        'SHUTDOWN', 'CONNECT', 'DISCONNECT'
    ]

    models.VM.BUILDING_STATES = [
        'BUILD'
    ]

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
            if (!id) {
              callback(this.get(id));
              return
            };
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
            var parsed = _.map(resp.images, _.bind(this.parse_meta, this));
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
            if (img.metadata && img.metadata && img.metadata[key]) {
                return _.escape(img.metadata[key]);
            }
            return undefined;
        },

        comparator: function(img) {
            var date = new Date(img.get('created_at'));
            return -img.get_sort_order("sortorder") || -date.getTime();
        },

        parse_meta: function(img) {
            _.each(this.meta_keys_as_attrs, _.bind(function(key){
                if (img[key]) { return };
                img[key] = this.get_meta_key(img, key) || "";
            }, this));
            return img;
        },

        active: function() {
            var active_states = ['available'];
            return this.filter(function(img){return img.get('status') == "available"});
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
        
        get_listing_sections: function() {
          return _.unique(_.filter(this.map(function(img) {
            return img.listing_section();
          }), function(r) { return r; }));
        },

        get_section_images: function(section) {
          return this.filter(function(img) {
            return (img.listing_section() == section);
          });
        },

        get_images_for_type: function(type, isSection) {
            if (isSection) {
              return this.get_section_images(type);
            }

            var method = 'get_{0}_images'.format(type.replace("-", "_"));
            if (this[method]) {
                return this[method]();
            }
            return this.active();
        },

        update_images_for_type: function(type, isSection, onStart, onComplete, onError, force_load) {
            var load = false;
            error = onError || function() {};
            function complete(collection) { 
                onComplete(collection.get_images_for_type(type, isSection)); 
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
                this.add({id:id, cpu:"Unknown", ram:"Unknown", disk:"Unknown", disk_template: "Unknown", name: "Unknown", status:"DELETED"})
            }, this), _.bind(function(flv) {
                if (!flv.flavor.status) { flv.flavor.status = "DELETED" };
                flv.flavor.cpu = flv.flavor['vcpus'];
                flv.flavor.disk_template = flv.flavor['SNF:disk_template'];
                this.add(flv.flavor);
            }, this));
        },

        parse: function (resp, xhr) {
            return _.map(resp.flavors, function(o) {
              o.cpu = o['vcpus'];
              o.disk_template = o['SNF:disk_template'];
              return o
            });
        },

        comparator: function(flv) {
            return flv.get("disk") * flv.get("cpu") * flv.get("ram");
        },
          
        unavailable_values_for_quotas: function(quotas, flavors, extra) {
            var flavors = flavors || this.active();
            var index = {cpu:[], disk:[], ram:[]};
            var extra = extra == undefined ? {cpu:0, disk:0, ram:0} : extra;
            
            _.each(flavors, function(el) {

                var disk_available = quotas['disk'] + extra.disk;
                var disk_size = el.get_disk_size();
                if (index.disk.indexOf(disk_size) == -1) {
                  var disk = el.disk_to_bytes();
                  if (disk > disk_available) {
                    index.disk.push(el.get('disk'));
                  }
                }
                
                var ram_available = quotas['ram'] + extra.ram * 1024 * 1024;
                var ram_size = el.get_ram_size();
                if (index.ram.indexOf(ram_size) == -1) {
                  var ram = el.ram_to_bytes();
                  if (ram > ram_available) {
                    index.ram.push(el.get('ram'))
                  }
                }

                var cpu = el.get('cpu');
                var cpu_available = quotas['cpu'] + extra.cpu;
                if (index.cpu.indexOf(cpu) == -1) {
                  if (cpu > cpu_available) {
                    index.cpu.push(el.get('cpu'))
                  }
                }
            });
            return index;
        },

        unavailable_values_for_image: function(img, flavors) {
            var flavors = flavors || this.active();
            var size = img.get_size();
            
            var index = {cpu:[], disk:[], ram:[]};

            _.each(this.active(), function(el) {
                var img_size = size;
                var flv_size = el.get_disk_size();
                if (flv_size < img_size) {
                    if (index.disk.indexOf(el.get("disk")) == -1) {
                        index.disk.push(el.get("disk"));
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
            var data = {'cpu': [], 'mem':[], 'disk':[], 'disk_template':[]};

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
                if (data.disk_template.indexOf(flv.get("disk_template")) == -1) {
                    data.disk_template.push(flv.get("disk_template"));
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

        append_ghost_servers: function(servers) {
          // Get ghost VMs from existing volumes
          synnefo.storage.volumes.map(function(volume) {
            var vol_vm_id = volume.get('_vm_id');

            if (!vol_vm_id || synnefo.storage.vms.get(vol_vm_id)) { return; }

            _vm = _.find(servers, function(e) {
              return (e.id == vol_vm_id);
            });

            if (!_vm) {
              servers.push({
                'id': vol_vm_id,
                'deleted': false,
                'is_ghost': true});
              }
          })

          // Get ghost VMs from existing ports
          synnefo.storage.ports.map(function(port) {
            var port_vm_id = port.get('device_id');

            if (!port_vm_id || synnefo.storage.vms.get(port_vm_id)) { return; }

            _vm = _.find(servers, function(e) {
              return e.id == port_vm_id;
            });

            if (!_vm) {
              servers.push({
              'id': port_vm_id,
              'deleted': false,
              'is_ghost': true});
            }
          });
        },

        parse: function (resp, xhr) {
            var data = resp.servers;

            data = _.map(data, function(vm) {
              vm.is_ghost = false;
              return vm;
            });

            this.append_ghost_servers(data);

            data = _.filter(_.map(data,
                                  _.bind(this.parse_vm_api_data, this)),
                                  function(v){return v});
            return data;
        },

        parse_vm_api_data: function(data) {
            var status;
            // do not add non existing DELETED entries
            if (data.status && data.status == "DELETED") {
                if (!this.get(data.id)) {
                    return false;
                }
            }
            
            if ('SNF:task_state' in data) { 
                data['task_state'] = data['SNF:task_state'];
                // Update machine state based on task_state value
                // Do not apply task_state logic when machine is in ERROR state.
                // In that case only update from task_state only if equals to
                // DESTROY
                if (data['task_state'] !== undefined) {
                    if (data['status'] != 'ERROR' && data['task_state'] != 'DESTROY') {
                      status = models.VM.TASK_STATE_STATUS_MAP[data['task_state']];
                      if (status) { data['status'] = status }
                    }
                }
            }

            // OS attribute
            if (this.has_meta(data)) {
                data['OS'] = data.metadata.OS || snf.config.unknown_os;
            }
            
            if (!data.diagnostics) {
                data.diagnostics = [];
            }

            // network metadata
            data['firewalls'] = {};
            data['fqdn'] = data['SNF:fqdn'];

            // if vm has no metadata, no metadata object
            // is in json response, reset it to force
            // value update
            if (!data['metadata']) {
                data['metadata'] = {};
            }
            
            // v2.0 API returns objects
            if (!data.is_ghost) {
              data.image_obj = data.image;
              data.image = data.image_obj.id;
              data.flavor_obj = data.flavor;
              data.flavor = data.flavor_obj.id;
            } else {
              data.image = undefined;
              data.flavor = undefined;
            }

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
            return vm_data.metadata && vm_data.metadata
        },

        has_addresses: function(vm_data) {
            return vm_data.metadata && vm_data.metadata
        },

        create: function (name, image, flavor, meta, project, extra, callback) {

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
            
            opts = {name: name, imageRef: image.id, flavorRef: flavor.id, 
                    metadata:meta, project: project.id}
            opts = _.extend(opts, extra);
            
            var cb = function(data) {
              synnefo.api.trigger("quota:update");
              callback(data);
            }

            this.api_call(this.path, "create", {'server': opts}, undefined, 
                          undefined, cb, {critical: true});
        },

        load_missing_images: function(callback) {
          var missing_ids = [];
          var resolved = 0;

          // fill missing_ids
          this.each(function(el) {
            var imgid = el.get("image");
            var existing = synnefo.storage.images.get(imgid);
            if (!existing && missing_ids.indexOf(imgid) == -1) {
              missing_ids.push(imgid);
            }
          });
          var check = function() {
            // once all missing ids where resolved continue calling the 
            // callback
            resolved++;
            if (resolved == missing_ids.length) {
              callback(missing_ids)
            }
          }
          if (missing_ids.length == 0) {
            callback(missing_ids);
            return;
          }
          // start resolving missing image ids
          _(missing_ids).each(function(imgid){
            synnefo.storage.images.update_unknown_id(imgid, check);
          });
        },

        get_connectable: function() {
            return storage.vms.filter(function(vm){
                return !vm.in_error_state() && !vm.is_building();
            });
        }
    })
    
    models.PublicKey = models.Model.extend({
        path: 'keys',
        api_type: 'userdata',
        detail: false,
        model_actions: {
          'remove': [['name'], function() {
            return true;
          }]
        },

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
        },

        rename: function(new_name) {
          //this.set({'name': new_name});
          var self = this;
          this.sync("update", this, {
            critical: true,
            data: {'name': new_name}, 
            success: _.bind(function(){
              snf.api.trigger("call");
              this.set({'name': new_name});
            }, this)
          });
        },

        do_remove: function() {
          this.actions.reset_pending();
          this.remove(function() {
            synnefo.storage.keys.fetch();
          });
        }
    })
    
    models._ActionsModel = models.Model.extend({
      defaults: { pending: null },
      actions: [],
      status: {
        INACTIVE: 0,
        PENDING: 1,
        CALLED: 2
      },

      initialize: function(attrs, opts) {
        models._ActionsModel.__super__.initialize.call(this, attrs);
        this.actions = opts.actions;
        this.model = opts.model;
        this.bind("change", function() {
          this.set({'pending': this.get_pending()});
        }, this);
        this.clear();
      },
      
      _in_status: function(st) {
        var actions = null;
        _.each(this.attributes, function(status, action){
          if (status == st) {
            if (!actions) {
              actions = []
            }
            actions.push(action);
          }
        });
        return actions;
      },

      get_pending: function() {
        return this._in_status(this.status.PENDING);
      },

      unset_pending_action: function(action) {
        var data = {};
        data[action] = this.status.INACTIVE;
        this.set(data);
        this.trigger("unset-pending", action);
      },

      set_pending_action: function(action, reset_pending) {
        reset_pending = reset_pending === undefined ? true : reset_pending;
        var data = {};
        data[action] = this.status.PENDING;
        if (reset_pending) {
          this.reset_pending();
        }
        this.set(data);
        this.trigger("set-pending", action);
      },
      
      reset_pending: function() {
        var data = {};
        _.each(this.actions, function(action) {
          data[action] = this.status.INACTIVE;
        }, this);
        this.set(data);
        this.trigger("reset-pending");
      }
    });

    models.PublicPool = models.Model.extend({});
    models.PublicPools = models.Collection.extend({
      model: models.PublicPool,
      path: 'os-floating-ip-pools',
      api_type: 'compute',
      noUpdate: true,

      parse: function(data) {
        return _.map(data.floating_ip_pools, function(pool) {
          pool.id = pool.name;
          return pool;
        });
      }
    });

    models.PublicKeys = models.Collection.extend({
        model: models.PublicKey,
        details: false,
        path: 'keys',
        api_type: 'userdata',
        noUpdate: true,
        updateEntries: true,

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
    });

  
    models.Quota = models.Model.extend({
        storage_attrs: {
          'project_id': ['projects', 'project']
        },

        initialize: function() {
            models.Quota.__super__.initialize.apply(this, arguments);
            this.bind("change", this.check, this);
            this.check();
        },
        
        check: function() {
            var usage, limit;
            usage = this.get('usage');
            limit = this.get('limit');
            if (usage >= limit) {
                this.trigger("available");
            } else {
                this.trigger("unavailable");
            }
        },

        increase: function(val) {
            if (val === undefined) { val = 1};
            this.set({'usage': this.get('usage') + val})
        },

        decrease: function(val) {
            if (val === undefined) { val = 1};
            this.set({'usage': this.get('usage') - val})
        },

        can_consume: function() {
            var usage, limit;
            usage = this.get('usage');
            limit = this.get('limit');
            if (usage >= limit) {
                return false
            } else {
                return true
            }
        },
        
        is_bytes: function() {
            return this.get('resource').get('unit') == 'bytes';
        },
        
        infinite: function(active) {
            var suffix = '';
            if (active) { suffix = '_active' }
            return this.get("limit" + suffix) >= snf.util.PRACTICALLY_INFINITE; 
        },

        get_available: function(active) {
            var suffix = '';
            if (active) { suffix = '_active'}
            var value = this.get('limit'+suffix) - this.get('usage'+suffix);
            if (active) {
              if (this.get('available') <= value) {
                value = this.get('available');
              }
            }
            if (value < 0) { return value }
            return value
        },

        get_readable: function(key, active, over_value) {
            if (key == 'available') {
                value = this.get_available(active);
            } else {
                value = this.get(key)
            }
            if (value <= 0) { value = 0 }

            value = parseInt(value);
            if (this.infinite()) { 
              return "Unlimited";
            }

            if (!this.is_bytes()) {
              if (over_value !== undefined) { return over_value + "" }
              return value + "";
            }
            
            value = over_value !== undefined ? over_value : value;
            return snf.util.readablizeBytes(value);
        }
    });
    
    models.Quotas = models.Collection.extend({
        model: models.Quota,
        api_type: 'accounts',
        path: 'quotas',
        supportIncUpdates: false,

        required_quota: {
          'vm': {
            'cyclades.vm': 1,
            'cyclades.ram': 1,
            'cyclades.cpu': 1,
            'cyclades.disk': 1
          },
          'network': {
            'cyclades.network.private': 1
          },
          'ip': {
            'cyclades.floating_ip': 1
          },
          'volume': {
            'cyclades.disk': 1
          }
        },

        parse: function(resp) {
            var parsed = [];
            _.each(resp, function(resources, uuid) {
              parsed = _.union(parsed, _.map(resources, function(value, key) {
                var quota_available = value.limit - value.usage || 0;
                var total_available = quota_available;
                var project_available = value.project_limit - value.project_usage || 0;
                var limit = value.limit;
                var usage = value.usage;
                
                var available = quota_available;
                var total_available = available;

                // priority to project limits
                if (project_available < available ) {
                  available = project_available;
                  limit = value.project_limit;
                  usage = value.project_usage;
                  total_available = available;
                }

                var available_active = available;

                // corresponding total quota
                var keysplit = key.split(".");
                var last_part = keysplit.pop();
                var activekey = keysplit.join(".") + "." + "total_" + last_part;
                var total = resp[uuid][activekey];
                if (total) {
                  total_available = total.limit - total.usage;
                  var total_project_available = total.project_limit - total.project_usage;
                  var total_limit = total.limit;
                  var total_usage = total.usage;
                  if (total_project_available < total_available) {
                    total_available = total_project_available;
                    total_limit = total.project_limit;
                    total_usage = total.project_usage;
                  }
                  if (total_available < available) {
                    available = total_available;
                    limit = total_limit;
                    usage = total_usage;
                  }
                }

                var limit_active = limit;
                var usage_active = usage;

                var id = uuid + ":" + key;
                if (available < 0) { available = 0 }
                return _.extend(value, {
                          'name': key, 
                          'id': id, 
                          'available': available,
                          'available_active': available_active,
                          'total_available': total_available,
                          'limit_active': limit_active,
                          'project_id': uuid,
                          'usage_active': usage_active,
                          'resource': snf.storage.resources.get(key)
                });
              }));
            });
            return parsed;
        },
        
        project_key: function(project, key) {
          return project + ":" + key;
        },

        get_by_id: function(k) {
          return this.filter(function(q) { return q.get('name') == k})[0]
        },

        get_available_for_vm: function(options) {
          var quotas = this;
          var key = 'available';
          var available_quota = {};
          _.each(['cyclades.ram', 'cyclades.cpu', 'cyclades.disk'], 
            function (key) {
              var value = quotas.get(key).get_available(true);
              available_quota[key.replace('cyclades.', '')] = value;
          });
          return available_quota;
        },
        
        can_create: function(type) {
          return this.get_available_projects(this.required_quota[type]).length > 0;
        },

        get_available_projects: function(quotas) {
          return synnefo.storage.projects.filter(function(project) {
            return project.quotas.can_fit(quotas);
          });
        },

        can_fit: function(quotas, total, _issues) {
          var issues = [];
          if (total === undefined) { total = false }
          _.each(quotas, function(value, key) {
            var q = this.get(key);
            if (!q) { issues.push(key); return }
            var quota = q.get('available_active');
            if (total) {
              quota = q.get('total_available');
            }
            if (quota < value) {
              issues.push(key);
            }
          }, this);
          if (_issues) { return issues }
          return issues.length === 0;
        }
    })

    models.Resource = models.Model.extend({
        api_type: 'accounts',
        path: 'resources'
    });

    models.Resources = models.Collection.extend({
        api_type: 'accounts',
        path: 'resources',
        model: models.Network,
        display_name_map: {
          'cyclades.vm': 'Machines',
          'cyclades.ram': 'Memory size',
          'cyclades.total_ram': 'Memory size (total)',
          'cyclades.cpu': 'CPUs',
          'cyclades.total_cpu': 'CPUs (total)',
          'cyclades.floating_ip': 'IP Addresses',
          'pithos.diskpace': 'Storage space',
          'cyclades.disk': 'Disk size',
          'cyclades.network.private': 'Private networks'
        },

        parse: function(resp) {
            return _.map(resp, function(value, key) {
                var display_name = this.display_name_map[key] || key;
                return _.extend(value, {
                  'name': key, 
                  'id': key,
                  'display_name': display_name
                });
            }, this);
        }
    });
    
    models.ProjectQuotas = models.Quotas.extend({});
    _.extend(models.ProjectQuotas.prototype, 
             Backbone.FilteredCollection.prototype);
    models.ProjectQuotas.prototype.get = function(key) {
      key = this.project_id + ":" + key;
      return models.ProjectQuotas.__super__.get.call(this, key);
    }

    models.Project = models.Model.extend({
        api_type: 'accounts',
        path: 'projects',

        initialize: function() {
          var self = this;
          this.quotas = new models.ProjectQuotas(undefined, {
            collection: synnefo.storage.quotas,
            collectionFilter: function(m) {
              return self.id == m.get('project_id')
          }});
          this.quotas.bind('change', function() {
            self.trigger('change:_quotas');
          });
          this.quotas.project_id = this.id;
          models.Project.__super__.initialize.apply(this, arguments);
        }
    });

    models.Projects = models.Collection.extend({
        api_type: 'accounts',
        path: 'projects',
        model: models.Project,
        supportIncUpdates: false,
        user_project_uuid: null,
        _resolving_missing: [],

        get: function(id) {
          var project = models.Projects.__super__.get.call(this, id);
          if (!project && id) {
            if (_.contains(this._resolving_missing, id)) { return }
            this._resolving_missing.push(id);
            var missing_project = {
              id: id, 
              name: '[missing project]',
              missing: true
            };
            this.add(missing_project);
            this.update_unknown_id(id);
            return this.get(id);
          }
          return project;
        },
        
        update_unknown_id: function(id) {
          this.api_call([this.path, id].join("/") , this.read_method, {
            _options:{
              async:false, 
              skip_api_error:true
            }}, undefined, 
          _.bind(function() {}, this), 
          _.bind(function(project, msg, xhr) {
            if (!project) { return }
            var existing = this.get(id);
            existing.set(project);
            existing.set({'missing': true});
            existing.set({'resolved': true});
          }, this));
        },

        url: function() {
          var args = Array.prototype.splice.call(arguments, 0);
          var url = models.Projects.__super__.url.apply(this, args);
          return url + "?mode=member";
        },

        parse: function(resp) {
          _.each(resp, function(project){
            if (project.system_project) {
              this.user_project_uuid = project.id;
            }
            if (project.id == synnefo.user.get_username()) {
              project.name = "System project"
            }
            // missing means the project exists in a relation to a resource
            // but does not appear in user projects list. Once the project
            // appears in projects list set missing flag to false.
            project.missing = false;
          }, this);
          return resp;
        },

        get_user_project: function() {
          return this.get(synnefo.user.current_username);
        },

        comparator: function(project) {
            if (project.get('system_project')) { return -100 }
            return project.get('name');
        }
    });
    
    // storage initialization
    snf.storage.images = new models.Images();
    snf.storage.flavors = new models.Flavors();
    snf.storage.vms = new models.VMS();
    snf.storage.keys = new models.PublicKeys();
    snf.storage.resources = new models.Resources();
    snf.storage.quotas = new models.Quotas();
    snf.storage.projects = new models.Projects();
    snf.storage.public_pools = new models.PublicPools();
    
    snf.storage.joined_projects = new Backbone.FilteredCollection(undefined, {
        collection: synnefo.storage.projects,
        collectionFilter: function(m) {
            return m.get && !m.get("missing");
        }
    });
})(this);
