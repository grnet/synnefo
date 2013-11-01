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
      api_type: 'compute'
    });
    
    // Neutron base collection, common neutron collection params are shared
    models.NetworkCollection = snfmodels.Collection.extend({
      api_type: 'compute',
      details: true,
      noUpdate: true,
      updateEntries: true
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

      // Available network actions.
      // connect: 
      model_actions: {
        'connect': [['status', 'is_public'], function() {
          //TODO: Also check network status
          return !this.is_public() && _.contains(['ACTIVE'], this.get('status'));
        }],
        'remove': [['status', 'is_public'], function() {
          //TODO: Also check network status
          return !this.is_public() && _.contains(['ACTIVE'], this.get('status'));
        }]
      },

      proxy_attrs: {
        'is_public': [
          ['router:external', 'public'], function() {
            return this.get('router:external') || this.get('public')
          } 
        ],
        'ext_status': [
          ['status'], function(st) {
            if (this.pending_connections) {
              return 'CONNECTING'
            } else if (this.pending_disconnects) {
              return 'DISCONNECTING'
            } else {
              return st
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
        models.Network.__super__.initialize.apply(this, arguments);
        var self = this;
        this.subnets = new Backbone.FilteredCollection(undefined, {
          collection: synnefo.storage.subnets,
          collectionFilter: function(m) {
            return self.id == m.get('network_id')
          }
        });
        this.ports = new Backbone.FilteredCollection(undefined, {
          collection: synnefo.storage.ports,
          collectionFilter: function(m) {
            return self.id == m.get('network_id')
          }
        });
        this.ports.network = this;
        this.ports.bind("add", function() {
          this.pending_connections--;
          this.update_connecting_status();
        }, this);
        this.ports.bind("remove", function() {
          this.pending_disconnects--;
          this.update_connecting_status();
        }, this);
        this.set({ports: this.ports});
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

      pluggable_vms: function() {
        var vms = synnefo.storage.vms.models;
        // TODO: filter out vms
        return vms;
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
        'name': 'Public',
        'status': 'ACTIVE',
        'router:external': true,
        'shared': false,
        'rename_disabled': true
      },
      
      initialize: function() {
        models.Network.__super__.initialize.apply(this, arguments);
        var self = this;
        this.ports = new Backbone.FilteredCollection(undefined, {
          collection: synnefo.storage.ports,
          collectionFilter: function(m) {
            return m.get('network') && m.get('network').get('is_public');
          }
        });
        this.set({ports: this.ports});
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
        var params = { network: { name:name } };
        if (!type) { throw "Network type cannot be empty"; }

        params.network.type = type;
        if (cidr) { params.network.cidr = cidr; }
        if (dhcp) { params.network.dhcp = dhcp; }
        if (dhcp === false) { params.network.dhcp = false; }
        
        var cb = function() {
          callback();
          quota.get('cyclades.network.private').increase();
        }
        return this.api_call(this.path, "create", params, cb);
      }
    });

    models.Port = models.NetworkModel.extend({
      
      path: 'ports',

      initialize: function() {
        models.Port.__super__.initialize.apply(this, arguments);
        this.set({'pending_firewall': null});
      },
      
      model_actions: {
        'disconnect': [['status', 'network', 'vm'], function() {
          var network = this.get('network');
          if (!network || network.is_public()) {
            return false
          }
          var status_ok = _.contains(['DOWN', 'ACTIVE', 'CONNECTED'], 
                                     this.get('status'));
          var vm_status_ok = this.get('vm') && !this.get('vm').get('busy');
          return status_ok && vm_status_ok
        }]
      },

      storage_attrs: {
        'device_id': ['vms', 'vm'],
        'network_id': ['networks', 'network'],
      },

      proxy_attrs: {
        'firewall_status': [
          ['vm'], function(vm) {
            var attachment = vm && vm.get_attachment(this.id);
            if (!attachment) { return "DISABLED" }
            return attachment.firewallProfile
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

      set_firewall: function(value, callback, error, options) {
        // MOCK CALL
        window.setTimeout(_.bind(function() {
          var vm = this.get('vm');
          var attachments = [];
          attachments.push({id: this.id, firewallProfile: value});
          vm.set({attachments: attachments});
        }, this),  2000);
        window.setTimeout(_.bind(function() {
          callback();
        }), 300);
      },

      disconnect: function(cb) {
        var network = this.get('network');
        network.pending_disconnects++;
        network.update_connecting_status();
        this.destroy({complete: cb, silent: true});
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
        try {
          return parseInt(m.get('device_id'));
        } catch (err) {
          return 0
        }
      }
    });

    models.FloatingIP = models.NetworkModel.extend({
      path: 'floatingips',
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
        'disconnect': [['status'], function() {
          var status_ok = _.contains(['CONNECTED'], this.get('status'))
          return status_ok
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
            var val = this.get('port_id');
            if (!val) {
              return 'DISCONNECTED'
            } else {
              if (this.get('port')) {
                return 'CONNECTED'
              } else {
                return 'CONNECTING'
              }
            }
          }
        ]
      },

      disconnect: function(cb) {
        // MOCK
        var self = this;
        window.setTimeout(function() {
          cb()
        }, 2000);
        window.setTimeout(function() {
          self.set({port_id: undefined});
        }, 3000);
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
