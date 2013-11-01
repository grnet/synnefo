function _resolve_keypath(obj, keypath) {
  _obj = obj;
  _key = keypath;
  
  var map = [];
  
  keypath = keypath.replace(/^model\./, '');
  keypath = keypath.replace(/^item\./, '');

  _.each(keypath.split("."), function(key) {
    // key = vm, name
    var is_last = (keypath.indexOf(key) == (keypath.length-key.length))
    if (is_last) {
      map.push([_obj, key]);
      return;
    }

    map.push([_obj, key]);
    _key = key;
    _obj = _obj.get(key);
  });
  
  return map
}

COLLECTION_EVENTS = ['add', 'remove', 'update', 'reset']

_.extend(rivets.formatters, {

  prefix: function(value, prefix) {
    return prefix + value.toString();
  },
  
  collection_size: function(col) {
    return col.models.length;
  },

  collection_machines_size: function(col) {
    var items = {};
    col.each(function(m) {
      if (!items[m.get('device_id')]) {
        items[m.get('device_id')] = 1
      }
    });
    return _.keys(items).length
  },

  lower: function(value) {
    return value.toString().toLowerCase();
  },

  parenthesize: function(value) {
    return "({0})".format(value);
  },
  
  intEq: function(value, cmp) {
    return parseInt(value) == parseInt(cmp);
  }

});

_.extend(rivets.binders, {
  'collection-view': {
    block: true,
    bind: function(el) {
      if (this.bound) { return }
    },

    unbind: function(el) {
    },
    
    update: function(el, value) {
    },

    routine: function(el, value) {
      if (!value) {
        try {
          if (this.keypath) {
            value = this.view.models.model.get(this.keypath);
          } else {
            value = this.view.models.model;
          }
        } catch (err) {
          console.log("value error");
        }
      }

      if (!value || this._bind_value != value) {
        if (this.bound) {
          this._bind_view.hide();
          this.view.models.view.remove_view(this._bind_view);
          delete this._bind_view;
          delete this._bind_value;
        }
        this.bound = false;
      }
      
      if (!this.bound && value) {
        var specs = this.options.formatters[0].split(",");
        var cls_name = specs[0];
        var params = specs[1];
        var view_cls = synnefo.views[cls_name];
        var view_params = {collection: value};
        if (params) {
          _.extend(view_params, JSON.parse(params));
        }
        var view = this.view.models.view.create_view(view_cls, view_params);
        this.view.models.view.add_subview(view);
        view.show(true);
        this._bind_view = view;
        this._bind_value = value;

        this.bound = true;
        $(el).append(view.el);
      }
    }
  },
  'model-view': {
    block: true,
    bind: function(el) {
      if (this.bound) { return }
    },

    unbind: function(el) {
    },
    
    update: function(el, value) {
    },

    routine: function(el, value) {
      if (!value) {
        try {
          if (this.keypath) {
            value = this.view.models.model.get(this.keypath);
          } else {
            value = this.view.models.model;
          }
        } catch (err) {
          console.log("value error");
        }
      }

      if (!value || this._bind_value != value) {
        if (this.bound) {
          this._bind_view.hide();
          this.view.models.view.remove_view(this._bind_view);
          delete this._bind_view;
          delete this._bind_value;
        }
        this.bound = false;
      }
      
      if (!this.bound && value) {
        var specs = this.options.formatters[0].split(",");
        var cls_name = specs[0];
        var params = specs[1];
        var view_cls = synnefo.views[cls_name];
        var view_params = {model: value};
        if (params) {
          _.extend(view_params, JSON.parse(params));
        }
        var view = this.view.models.view.create_view(view_cls, view_params);
        this.view.models.view.add_subview(view);
        view.show(true);
        this._bind_view = view;
        this._bind_value = value;

        this.bound = true;
        $(el).append(view.el);
      }
    }
  }
});

rivets.configure({
  prefix: 'rv',
  preloadData: true,

  handler: function(target, event, binding) {
    var func = binding.model[binding.keypath];
    func.call(binding.model, binding.view.models.model, event);
  },

  adapter: {

    subscribe: function(root_obj, keypath, callback) {
      if (!(root_obj instanceof Backbone.Model) && 
          !(root_obj instanceof Backbone.Collection)) {
        return;
      }

      var bind_map = _resolve_keypath(root_obj, keypath);
      var last_key, last_obj;
      last_key = bind_map[0][1];
      last_obj = bind_map[0][0];

      // TODO: Clean up :)
      _.each(bind_map, function(data) {
        var obj, key;
        obj = data[0]; key = data[1];
        
        var collection = last_obj[key] || last_obj.get && last_obj.get(key);
        if (collection instanceof Backbone.Collection) {
          obj = collection;
          _.each(COLLECTION_EVENTS, function(e) {
            obj.bind(e, callback);
          });
          last_obj = obj;
          last_key = key;
          return;
        }

        if (!obj) {
          var cb = function() {
            obj.bind('change:' + key, callback);
          }
          function reg_handler(last_obj, lkey, obj, callback) {
            var last_key = lkey;
            var resolve_obj = function(model, value, key) {
              if (value) {
                last_obj.unbind('change:' + key, resolve_obj);
                delete last_obj['__pending_rivet_bind'];
              }
              var key = last_key;
            }
            last_obj.bind('change:' + last_key, resolve_obj);
          }
          last_obj.__pending_rivet_bind = [last_key, reg_handler];
          reg_handler(last_obj, last_key, obj, callback);
        } else {
          obj.bind('change:' + key, callback);
        }
        last_key = key;
        last_obj = obj;
      });
    },
    
    unsubscribe: function(obj, keypath, callback) {
      if (!(obj instanceof Backbone.Model) && 
          !(obj instanceof Backbone.Collection)) {
        return;
      }
      var bind_map = _resolve_keypath(obj, keypath);
      _.each(bind_map, function(data) {
        var obj, key;
        obj = data[0]; key = data[1];
        if (!obj) {
          return
        }
        if ('__pending_rivet_bind' in obj) {
          var opts = obj.__pending_rivet_bind;
          obj.unbind('change:'+opts[0], opts[1]);
        }
        if (obj instanceof Backbone.Collection) {
          _.each(COLLECTION_EVENTS, function(e) {
            obj.unbind(e, callback);
          });
        } else {
          obj.unbind('change:' + key, callback);
        }
      });
    },
    
    read: function(obj, keypath) {
      if (!(obj instanceof Backbone.Model) && !(obj instanceof Backbone.Collection)) {
        return;
      }
      var result;
      var bind_map = _resolve_keypath(obj, keypath);
      var last = _.last(bind_map);
      if (!last[0]) {
        return '';
      }
      result = last[0].get(last[1]);
      // array of models or collection ????
      //if (result instanceof Backbone.Collection) {
        //return result
      //}
      return result
    },
    
    publish: function(obj, keypath, value) {
      throw "Publish not available"
    },

  }
});
