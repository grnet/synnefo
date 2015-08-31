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
    
    models.Volume = snfmodels.Model.extend({
      path: 'volumes',
      api_type: 'volume',
      storage_attrs: {
        '_vm_id': ['vms', 'vm'],
        'tenant_id': ['projects', 'project']
      },

      proxy_attrs: { 
          '_status': [['vm', 'vm.state', 'vm.status', 'status'], function() {
              return this.get('status');
          }],
          'in_progress': [['status', 'vm', 'vm.status'], function() {
              var vm = this.get('vm');
              if (vm && vm.get('in_progress')) {
                  return true
              }
              return false;
          }],
          'ext': [['vm', 'volume_type'], function() {
              var vm = this.get('vm');
              if (!vm) { return false }
              var flavor = vm.get_flavor();
              var tpl = flavor.get('disk_template');
              return tpl.indexOf('ext_') === 0;
          }],
        'rename_disabled': [
          ['is_ghost', 'is_root'], function() {
            return this.get('is_ghost') || this.get('is_root');
          }
        ]
      },

      initialize: function() {
        var self = this;
        this.vms = new Backbone.FilteredCollection(undefined, {
          collection: synnefo.storage.vms,
          collectionFilter: function(m) {
            var devices = _.map(self.get('attachments'), 
                                function(a) { return a.server_id + '' });
            return _.contains(devices, m.id + '');
          }
        });
        
        models.Volume.__super__.initialize.apply(this, arguments);
        this.set({vm:this.vms.at(0)});
      },

      model_actions: {
        'snapshot': [['is_ghost', 'status', 'vm', 'ext'], function() {
            if (this.get('is_ghost')) { return false }
            if (!synnefo.config.snapshots_enabled) { return false }
            if (!this.get('ext')) { return false }
            var removing = this.get('status') == 'deleting';
            var creating = this.get('status') == 'creating';
            var vm = this.get('vm');
            return vm && vm.can_connect() && !removing && !creating;
        }],

        'remove': [['is_ghost', 'is_root', 'vm', 'ext'], function() {
            if (this.get('is_ghost')) { return false }
            var removing = this.get('status') == 'deleting';
            var creating = this.get('status') == 'creating';
            if (this.get('is_root')) { return false }
            var vm = this.get('vm');
            return vm && vm.can_connect() && !removing && !creating;
        }]
      },
      
      get_index: function() {
          var a = this.get("attachments");
          return a && a[0] && a[0].device_index;
      },

      reassign_to_project: function(project, success, cb) {
        var project_id = project.id ? project.id : project;
        var self = this;
        var _success = function() {
          success();
          self.set({'tenant_id': project_id});
        }

        synnefo.api.sync('create', this, {
          url: this.url() + '/action',
          success: _success,
          complete: cb,
          data: { 
            reassign: { 
              project: project_id 
            }
          }
        });
      },

      update_description: function(new_desc) {
          var self = this;
          this.sync("update", this, {
              critical: true,
              data: {
                  'volume': {
                      'display_description': new_desc
                  }
              }, 
              success: _.bind(function(){
                  snf.api.trigger("call");
                  this.set({'display_description': new_desc});
              }, this)
          });
      },

      rename: function(new_name) {
          //this.set({'name': new_name});
          var self = this;
          this.sync("update", this, {
              critical: true,
              data: {
                  'volume': {
                      'display_name': new_name
                  }
              }, 
              success: _.bind(function(){
                  snf.api.trigger("call");
                  this.set({'display_name': new_name});
              }, this)
          });
      },

      do_remove: function(succ, err) { return this.do_destroy(succ, err) },

      do_destroy: function(succ, err) {
        this.actions.reset_pending();
        this.destroy({
          success: _.bind(function() {
            synnefo.api.trigger("quotas:call", 10);
            this.set({status: 'deleting'});
            succ && succ();
          }, this),
          error: err || function() {},
          silent: true
        });
      },

    });
    
    models.Volumes = snfmodels.Collection.extend({
      model: models.Volume,
      path: 'volumes',
      api_type: 'volume',
      details: true,
      noUpdate: true,
      updateEntries: true,
      add_on_create: true,

      append_ghost_volumes: function(volumes) {
        // Get ghost volumes from existing VMs
        synnefo.storage.vms.map(function(vm) {
          var index = 0;
          _.map(vm.attributes.volumes, function (volume_id) {
            _vol = _.find(volumes, function(v) {
              return v.id == volume_id;
            });

            // Enable when using changes since
            // if (synnefo.storage.volumes.get(volume_id)) { return; }
            //
            if (!_vol) {
              volumes.push({
                'id': volume_id,
                'size': 0,
                'volume_type': vm.get_flavor().get_volume_type(),
                'status': 'un_use',
                'attachments': [{'server_id': vm.id,
                                 'device_index': index,
                                 'volume_id': volume_id}],
                                 'display_name': 'Unknown',
                                 'is_ghost': true,
              });
            }
            index = index + 1;
          });
        });
      },

      parse: function(resp) {
        var data = resp.volumes;

        data = _.map(data, function (v) { v.is_ghost = false; return v; });

        this.append_ghost_volumes(data);

        data = _.map(data, this.parse_volume_api_data);
        data = _.filter(_.map(data,
                              _.bind(this.parse_volume_api_data, this)),
          function(v){ return v });

        return data;
      },

      parse_volume_api_data: function(volume) {
        var attachments = volume.attachments || [];
        volume._vm_id = attachments.length > 0 ?
                            attachments[0].server_id : undefined;

        if (!volume.display_name) {
            volume.display_name = "Disk {0}".format(volume.id);
        }

        volume.is_root = false;
        if (attachments.length)  {
            volume._index = attachments[0].device_index;
            volume._index_set = true;
            if (volume._index == 0)  {
                    volume.display_name = "Boot disk";
                    volume.is_root = true;
            }
        } else {
            volume._index_set = false;
        }

        return volume;
      },

      comparator: function(m) {
          return m.get('_vm_id') + m.get('_index');
      },

      create: function(name, size, vm, project, source, description, 
                       extra, callback) {
        var volume = {
          'display_name': name,
          'display_description': description || null,
          'size': parseInt(size),
          'server_id': vm.id,
          'project': project.id,
          'metadata': {}
        }

        if (source && source.is_snapshot()) {
            volume.snapshot_id = source.get("id"); 
        } 

        if (source && !source.is_snapshot()) {
            volume.imageRef = source.get("id"); 
        } 

        var cb = function(data) {
          callback && callback(data);
        }

        this.api_call(this.path + "/", "create", {'volume': volume}, undefined, 
                      undefined, cb, {critical: true});
      }
    });

    snf.storage.volumes = new models.Volumes();
})(this);
