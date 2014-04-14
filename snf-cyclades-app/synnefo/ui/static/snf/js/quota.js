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
    
    // Astakos quotas lib
    // Requires jquery and jquery.cookie javascript libs
    //
    // Usage
    // -----
    // <script src="jquery.js"></script>
    // <script src="backbone.js"></script>
    // <script src="snf/quota.js"></script>
    // 
    // var quotas = new snf.quota.Quota();
    // var quotas = new snf.quota.Quota();
    // $.ajax({
    //        url: '/userquota',
    //        async: false,
    //        method: 'POST',
    //        success: function(data) {
    //           quotas.load(data);
    //        }
    //    })
    //
    // var vms_limit = quotas.get_limit("cyclades.vm");
    // var networks_usage = quotas.get_usage("cyclades.network.private");
    //

    var root = root;
    var snf = root.synnefo = root.synnefo || {};
    var bb = root.Backbone;
    var _ = root._;
    
    // init quota namespace
    snf.quota = {};
    
    snf.quota.Quota = function(defaultns) {
        if (defaultns == undefined) { defaultns = "" }
        this.ns = defaultns;
        this.data = {};
    }

    _.extend(snf.quota.Quota.prototype, bb.Events, {

      load: function(resp) {
        this.data = {};
        _.each(resp, function(q) {
          if (this.data[q.name]) {
            _.extend(this.data[q.name], q)
          } else {
            this.data[q.name] = q;
          }

          q.maxValue = parseInt(q.maxValue);
          q.currValue = parseInt(q.currValue);
          this.update_exceeded(q.name, true);
        }, this);
      },
    
      get_key: function(key) {
        if (key.indexOf(".") == -1) {
          return this.ns + "." + key;
        }
        return key;
      },
      
      get: function(key) {
        if (this.get_key(key) in this.data) {
          return this.data[this.get_key(key)]
        }
        return {}
      },

      update_exceeded: function(key, silent) {
        if (silent === undefined) { silent = false; }
        
        var q = this.get(key);
        var oldexceeded = q.exceeded;
        q.exceeded = this.exceeded(key);
        if (q.exceeded != oldexceeded) {
          key = this.get_key(key);
          this.trigger("quota.changed", key, this);
          this.trigger(key + ".quota.changed", this);
          if (q.exceeded) { this.trigger("quota.reached", this)}
          if (!q.exceeded) { this.trigger("quota.free", this)}
          if (q.exceeded) { this.trigger(key + ".quota.reached", this)}
          if (!q.exceeded) { this.trigger(key + ".quota.free", this)}
        }
      },

      update_usage: function(key, value) {
        this.get(key).currValue = parseInt(value);
        this.update_exceeded(key);
      },

      update_limit: function(key, value) {
        this.get(key).maxValue = parseInt(value);
        this.update_exceeded(key);
      },

      get_usage: function(key) {
        return parseInt(this.get(key).currValue);
      },

      get_limit: function(key) {
        return parseInt(this.get(key).maxValue);
      },

      is_bytes: function(key) {
        return this.get(key).unit == "bytes";
      },

      get_available: function(key) {
        return this.get_limit(key) - this.get_usage(key)
      },
      
      exceeded: function(key) {
        return this.get_usage(key) >= this.get_limit(key);
      },

      can_consume: function(key, value) {
        return (this.get_available(key) - parseInt(value)) >= 0
      },

      get_available_readable: function(key) {
        var value;
        if (this.is_bytes(key)) {
          var value = this.get_available(key);
          if (!value) { return 0 }
          return snf.util.readablizeBytes(value);
        } else {
          return this.get_available(key);
        }
      }

    });

})(this);

