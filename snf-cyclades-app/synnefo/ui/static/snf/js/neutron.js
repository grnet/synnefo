;(function(root){
    // Neutron api models, collections, helpers
  
    // root
    var root = root;
    
    // setup namepsaces
    var snf = root.synnefo = root.synnefo || {};
    var snfmodels = snf.models = snf.models || {}
    var models = snfmodels.networks = snfmodels.networks || {};
    var storage = snf.storage = snf.storage || {};
    var util = snf.util = snf.util || {};

    // shortcuts
    var bb = root.Backbone;
    var slice = Array.prototype.slice

    // logging
    var logger = new snf.logging.logger("SNF-MODELS");
    var debug = _.bind(logger.debug, logger);
    
    // Neutron base model, extending existing synnefo model
    models.NetworkModel = snfmodels.Model.extend({
      api_type: 'network'
    });
    
    // Neutron base collection, common neutron collection params are shared
    models.NetworkCollection = snfmodels.Collection.extend({
      api_type: 'network',
      details: true,
      noUpdate: true,
      updateEntries: true,
      add_on_create: true
    });
  
    // Subnet model
    models.Subnet = models.NetworkModel.extend();
    
    // Subnet collection
    models.Subnets = models.NetworkCollection.extend({
      model: models.Subnet,
      details: false,
      path: 'subnets',
      parse: function(resp) {
        return resp.subnets
      }
    });
    
    // Network 
    models.Network = models.NetworkModel.extend({
      path: 'networks',

      parse: function(obj) {
        return obj.network;
      },

      // Available network actions.
      // connect: 
      model_actions: {
        'connect': [['status', 'is_public'], function() {
          //TODO: Also check network status
          return !this.is_public() && _.contains(['ACTIVE'], this.get('status'));
        }],
        'remove': [['status', 'is_public', 'ports'], function() {
          if (this.ports && this.ports.length) {
            return false
          }
          return !this.is_public() && _.contains(['ACTIVE'], this.get('status'));
        }]
      },

      proxy_attrs: {
        'is_public': [
          ['router:external', 'public'], function() {
            return this.get('router:external') || this.get('public')
          } 
        ],
        'is_floating': [
          ['SNF:floating_ip_pool'], function() {
            return this.get('SNF:floating_ip_pool')
          }
        ],
        'cidr': [
          ['subnet'], function() {
            var subnet = this.get('subnet');
            if (subnet && subnet.get('cidr')) {
              return subnet.get('cidr')
            } else {
              return undefined
            }
          }
        ],
        'ext_status': [
          ['status', 'cidr'], function(st) {
            if (this.get('ext_status') == 'REMOVING') {
              return 'REMOVING'
            }
            if (this.pending_connections) {
              return 'CONNECTING'
            } else if (this.pending_disconnects) {
              return 'DISCONNECTING'
            } else {
              return this.get('status')
            }
        }],
        'in_progress': [
          ['ext_status'], function() {
            return _.contains(['CONNECTING', 
                               'DISCONNECTING', 
                               'REMOVING'], 
                               this.get('ext_status'))
          }  
        ]
      },
      
      storage_attrs: {
        'subnets': ['subnets', 'subnet', function(model, attr) {
          var subnets = model.get(attr);
          if (subnets && subnets.length) { return subnets[0] }
        }]
      },

      // call rename api
      rename: function(new_name, cb) {
          this.sync("update", this, {
              critical: true,
              data: {
                  'network': {
                      'name': new_name
                  }
              }, 
              // do the rename after the method succeeds
              success: _.bind(function(){
                  //this.set({name: new_name});
                  snf.api.trigger("call");
              }, this),
              complete: cb || function() {}
          });
      },

      pending_connections: 0,
      pending_disconnects: 0,

      initialize: function() {
        var self = this;
        this.subnets = new Backbone.FilteredCollection(undefined, {
          collection: synnefo.storage.subnets,
          collectionFilter: function(m) {
            return self.id == m.get('network_id')
        }});
        this.ports = new Backbone.FilteredCollection(undefined, {
          collection: synnefo.storage.ports,
          collectionFilter: function(m) {
            return self.id == m.get('network_id')
          }
        });
        this.ports.network = this;
        this.ports.bind("reset", function() {
          this.pending_connections = 0;
          this.pending_disconnects = 0;
          this.update_connecting_status();
          this.update_actions();
        }, this);
        this.ports.bind("add", function() {
          this.pending_connections--;
          this.update_connecting_status();
          this.update_actions();
        }, this);
        this.ports.bind("remove", function() {
          this.pending_disconnects--;
          this.update_connecting_status();
          this.update_actions();
        }, this);
        this.set({ports: this.ports});

        this.connectable_vms = new Backbone.FilteredCollection(undefined, {
          collection: synnefo.storage.vms,
          collectionFilter: function(m) {
            return m.can_connect();
          }
        });
        models.Network.__super__.initialize.apply(this, arguments);
        this.update_actions();
      },
      
      update_actions: function() {
        if (this.ports.length) {
          this.set({can_remove: false})
        } else {
          this.set({can_remove: true})
        }
      },

      update_connecting_status: function() {
        if (this.pending_connections <= 0) {
          this.pending_connections = 0;
        }
        if (this.pending_disconnects <= 0) {
          this.pending_disconnects = 0;
        }
        this.trigger('change:status', this.get('status'));
      },

      get_nics: function() {
        return this.nics.models
      },

      is_public: function() {
        return this.get('router:external')
      },

      connect_vm: function(vm, cb) {
        var self = this;
        var data = {
          port: {
            network_id: this.id,
            device_id: vm.id
          }
        }

        this.pending_connections++;
        this.update_connecting_status();
        synnefo.storage.ports.create(data, {complete: cb});
      }
    });

    models.CombinedPublicNetwork = models.Network.extend({
      defaults: {
        'admin_state_up': true,
        'id': 'snf-combined-public-network',
        'name': 'Internet',
        'status': 'ACTIVE',
        'router:external': true,
        'shared': false,
        'rename_disabled': true,
        'subnets': []
      },
      
      initialize: function() {
        var self = this;
        this.ports = new Backbone.FilteredCollection(undefined, {
          collection: synnefo.storage.ports,
          collectionFilter: function(m) {
            return m.get('network') && m.get('network').get('is_public');
          }
        });
        this.set({ports: this.ports});
        this.floating_ips = synnefo.storage.floating_ips;
        this.set({floating_ips: this.floating_ips});

        this.available_floating_ips = new Backbone.FilteredCollection(undefined, {
          collection: synnefo.storage.floating_ips,
          collectionFilter: function(m) {
            return !m.get('port_id');
          }
        });
        this.set({available_floating_ips: this.available_floating_ips});
        models.Network.__super__.initialize.apply(this, arguments);
      },

    })

    models.Networks = models.NetworkCollection.extend({
      model: models.Network,
      path: 'networks',
      details: true,
      parse: function(resp) {
        return resp.networks
      },

      get_floating_ips_network: function() {
        return this.filter(function(n) { return n.get('is_public')})[1]
      },

      create: function (name, type, cidr, dhcp, callback) {
        var quota = synnefo.storage.quotas;
        var params = {network:{name:name}};
        var subnet_params = {subnet:{network_id:undefined}};
        if (!type) { throw "Network type cannot be empty"; }

        params.network.type = type;
        if (cidr) { subnet_params.subnet.cidr = cidr; }
        if (dhcp) { subnet_params.subnet.dhcp_enabled = dhcp; }
        if (dhcp === false) { subnet_params.subnet.dhcp_enabled = false; }
        
        var cb = function() {
          callback();
        }
        
        var complete = function() {};
        var error = function() { cb() };
        // on network create success, try to create the requested 
        // network subnet
        var success = function(resp) {
          var network = resp.network;
          subnet_params.subnet.network_id = network.id;
          synnefo.storage.subnets.create(subnet_params, {
            complete: function () { cb && cb() }
          });
          quota.get('cyclades.network.private').increase();
        }
        return this.api_call(this.path, "create", params, complete, error, success);
      }
    });
    
    // dummy model/collection
    models.FixedIP = models.NetworkModel.extend({
      storage_attrs: {
        'subnet_id': ['subnets', 'subnet']
      }
    });
    models.FixedIPs = models.NetworkCollection.extend({
      model: models.FixedIP
    });

    models.Port = models.NetworkModel.extend({
      path: 'ports',
      parse: function(obj) {
        return obj.port;
      },
      initialize: function() {
        models.Port.__super__.initialize.apply(this, arguments);
        var ips = new models.FixedIPs();
        this.set({'ips': ips});
        this.bind('change:fixed_ips', function() {
          var ips = this.get('ips');
          //var ips = _.map(ips, function(ip) { ip.id = ip.a})
          this.update_ips()
        }, this);
        this.update_ips();
        this.set({'pending_firewall': null});
      },
      
      update_ips: function() {
        var self = this;
        var ips = _.map(this.get('fixed_ips'), function(ip_obj) {
          var ip = _.clone(ip_obj);
          var type = "v4";
          if (ip.ip_address.indexOf(":") >= 0) {
            type = "v6";
          }
          ip.id = ip.ip_address;
          ip.type = type;
          ip.subnet_id = ip.subnet;
          ip.port_id = self.id;
          delete ip.subnet;
          return ip;
        });
        this.get('ips').update(ips, {removeMissing: true});
      },

      model_actions: {
        'disconnect': [['status', 'network', 'vm'], function() {
          var network = this.get('network');
          if ((!network || network.get('is_public')) && (network && !network.get('is_floating'))) {
            return false
          }
          var status_ok = _.contains(['DOWN', 'ACTIVE', 'CONNECTED'], 
                                     this.get('status'));
          var vm_status_ok = this.get('vm') && this.get('vm').can_connect();
          var vm_status = this.get('vm') && this.get('vm').get('status');
          return status_ok && vm_status_ok
        }]
      },

      storage_attrs: {
        'device_id': ['vms', 'vm'],
        'network_id': ['networks', 'network']
      },

      proxy_attrs: {
        'firewall_status': [
          ['vm'], function(vm) {
            var attachment = vm && vm.get_attachment(this.id);
            if (!attachment) { return "DISABLED" }
            return attachment.firewallProfile
          } 
        ],
        'ext_status': [
          ['status'], function() {
            if (_.contains(["DISCONNECTING"], this.get('ext_status'))) {
              return this.get("ext_status")
            }
            return this.get("status")
          }
        ],
        'in_progress': [
          ['ext_status', 'vm'], function() {
            return _.contains(["BUILD", "DISCONNECTING", "CONNECTING"], this.get("ext_status"))
          }
        ],
        'firewall_running': [
          ['firewall_status', 'pending_firewall'], function(status, pending) {
              var pending = this.get('pending_firewall');
              var status = this.get('firewall_status');
              if (!pending) { return false }
              if (status == pending) {
                this.set({'pending_firewall': null});
              }
              return status != pending;
          }
        ],
      },

      disconnect: function(cb) {
        var network = this.get('network');
        var vm = this.get('vm');
        network.pending_disconnects++;
        network.update_connecting_status();
        var success = _.bind(function() {
          if (vm) {
            vm.set({'status': 'DISCONNECTING'});
          }
          this.set({'status': 'DISCONNECTING'});
          cb();
        }, this);
        this.destroy({success: success, complete: cb, silent: true});
      }
    });

    models.Ports = models.NetworkCollection.extend({
      model: models.Port,
      path: 'ports',
      details: true,
      noUpdate: true,
      updateEntries: true,

      parse: function(data) {
        return data.ports;
      },

      comparator: function(m) {
          return parseInt(m.id);
      }
    });

    models.FloatingIP = models.NetworkModel.extend({
      path: 'floatingips',

      parse: function(obj) {
        return obj.floatingip;
      },

      storage_attrs: {
        'port_id': ['ports', 'port'],
        'floating_network_id': ['networks', 'network'],
      },

      model_actions: {
        'remove': [['status'], function() {
          var status_ok = _.contains(['DISCONNECTED'], this.get('status'))
          return status_ok
        }],
        'connect': [['status'], function() {
          var status_ok = _.contains(['DISCONNECTED'], this.get('status'))
          return status_ok
        }],
        'disconnect': [['status', 'port_id', 'port'], function() {
          var port = this.get('port');
          var vm = port && port.get('vm');
          if (!vm) { return false }
          if (vm && vm.get("task_state")) { return false }
          if (vm && vm.in_error_state()) { return false }
          var status_ok = _.contains(['ACTIVE', 'CONNECTED'], this.get('status'))
          var vm_status_ok = vm.can_disconnect();
          return status_ok && vm_status_ok;
        }]
      },

      proxy_attrs: {
        'ip': [
          ['floating_ip_adress'], function() {
            return this.get('floating_ip_address'); 
        }],

        'in_progress': [
          ['status'], function() {
            return _.contains(['CONNECTING', 'DISCONNECTING', 'REMOVING'], 
                              this.get('status'))
          }  
        ],

        'status': [
          ['port_id', 'port'], function() {
            var port_id = this.get('port_id');
            if (!port_id) {
              return 'DISCONNECTED'
            } else {
              var port = this.get('port');
              if (port) {
                var port_status = port.get('ext_status');
                if (port_status == "DISCONNECTING") {
                  return port_status
                }
                if (port_status == "CONNECTING") {
                  return port_status
                }
                return 'CONNECTED'
              }
              return 'CONNECTING'  
            }
          }
        ]
      },
      
      disconnect: function(cb) {
        this.get('port').disconnect(cb);
      }
    });

    models.FloatingIPs = models.NetworkCollection.extend({
      model: models.FloatingIP,
      details: false,
      path: 'floatingips',
      parse: function(resp) {
        return resp.floatingips;
      }
    });

    models.Router = models.NetworkModel.extend({
    });

    models.Routers = models.NetworkCollection.extend({
      model: models.Router,
      path: 'routers',
      parse: function(resp) {
        return resp.routers
      }
    });

    snf.storage.floating_ips = new models.FloatingIPs();
    snf.storage.routers = new models.Routers();
    snf.storage.networks = new models.Networks();
    snf.storage.ports = new models.Ports();
    snf.storage.subnets = new models.Subnets();

})(this);
