// Copyright 2013 GRNET S.A. All rights reserved.
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

