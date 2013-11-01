/*
The MIT License (MIT)

Copyright (c) 2013 Dmitriy Likhten

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
*/
/* version 1.1.0 */
(function(_, Backbone) {
  var defaultFilter = function() {return true;};
  /**
   * This represents a filtered collection. You can either pass a filter or
   * invoke setFilter(filter) to give a filter. The filter is identical to
   * that which is used for _.select(array, filter)
   *
   * false filter indicates no filtering.
   *
   * do not modify this collection directly via #add/#remove, modify the
   * underlying origModel.
   *
   * Events:
   *   add - something was added (via filter or trickling from underlying collection)
   *   remove - something was removed (via filter or trickling from underlying collection)
   *   reset - the whole thing was reset
   *   sort - same as reset, but via sort
   *   filter-complete - filtering is complete -- very useful if you want to trigger a re-draw
   *                                              of the whole collection
   */
  Backbone.FilteredCollection = Backbone.Collection.extend({
    collectionFilter: null
    ,defaultFilter: defaultFilter

    ,initialize: function(models, data) {
      if (models) throw "models cannot be set directly, unfortunately first argument is the models.";
      this.collection = data.collection;
      this.setFilter(data.collectionFilter);

      this.collection.bind("add",             this.addModel, this);
      this.collection.bind("remove",          this.removeModel, this);
      this.collection.bind("reset",           this.resetCollection, this);
      this.collection.bind("sort",            this.resortCollection, this);
      this.collection.bind("change",          this._modelChanged, this);
      this.collection.bind("filter-complete", this._filterComplete, this);
    }

    ,_reset: function(options) {
      Backbone.Collection.prototype._reset.call(this, options);
      this._mapping = [];
    }

    ,add: function() {
      throw "Do not invoke directly";
    }

    ,remove: function() {
      throw "Do not invoke directly";
    }

    ,reset: function() {
      throw "Do not invoke directly";
    }

    ,_modelChanged: function(model, collection, options){
      options || (options = {});

      var ownIndexOfModel = this.indexOf(model);
      if (this.collectionFilter(model)){
        // Model passed filter
        if (ownIndexOfModel < 0){
          // Model not found, add it
          var index = this.collection.indexOf(model);
          this._forceAddModel(model, {index: index});
        }
        // the model passes the filter and is already in the collection
        // therefore we want to indicate that the model has changed
        else {
          this.trigger("change", model, this);
        }
      } else {
        // Model did not pass filter
        if (ownIndexOfModel > -1){
          this._forceRemoveModel(model, {index: ownIndexOfModel});
        }
      }
      if (! options.silent) {
        this._filterComplete();
      }
    }

    ,resortCollection: function() {
      // note: we don't need to do any filter work since sort
      // implies nothing changed, only order
      var newModels = [];
      var newMapping = [];
      var models = this.models;
      _.each(this.collection.models, function(model, index) {
        if (models.indexOf(model) >= 0) {
          newModels.push(model);
          newMapping.push(index);
        }
      });
      this.models = newModels;
      this._mapping = newMapping;
      this.trigger("sort", this);
    }

    ,resetCollection: function() {
      this._mapping = [];
      this._reset();
      this.setFilter(undefined, {silent: true});
      this.trigger("reset", this);
    }

    // this is to synchronize where the element exists in the original model
    // to our _mappings array
    ,renumberMappings: function() {
      this._mapping = []
      var collection = this.collection;
      var mapping = this._mapping;

      _(this.models).each(function(model) {
        mapping.push(collection.indexOf(model));
      });
    }

    ,removeModel: function(model, colleciton, options) {
      var at = this._mapping.indexOf(options.index);
      console.log("requested remove", "options.index", options.index, 
                  "at", at, "model.id", model.id);
      if (at > -1) {
        this._forceRemoveModel(model, _.extend({index: at}, options));
      }
      this.renumberMappings();
    }

    // the options.index here is the index of the current model which we are removing
    ,_forceRemoveModel: function(model, options) {
      this._mapping.splice(options.index, 1);
      Backbone.Collection.prototype.remove.call(this, model, {silent: options.silent});
      if (! options.silent) {
        this.trigger("remove", model, this, {index: options.index})
      }
    }

    ,addModel: function(model, collection, options) {
      if (this.collectionFilter(model)) {
        this._forceAddModel(model, _.extend(options || {}, {index: (options && options.at) || collection.indexOf(model)}));
      }
      this.renumberMappings();
    }

    // the options.index here is the index of the original model which we are inserting
    ,_forceAddModel: function(model, options) {
      var desiredIndex = options.index;
      // determine where to add, look at mapping and find first object with the index
      // great than the one that we are given
      var addToIndex = _.sortedIndex(this._mapping, desiredIndex, function(origIndex) { return origIndex; });

      // add it there
      if (this.get(model.id)) { return }
      Backbone.Collection.prototype.add.call(this, model, {at: addToIndex, silent: options.silent});
      this._mapping.splice(addToIndex, 0, desiredIndex);
      if (! options.silent) {
        this.trigger("add", model, this, {index: addToIndex})
      }
    }

    ,setFilter: function(newFilter, options) {
      options || (options = {});
      if (newFilter === false) { newFilter = this.defaultFilter } // false = clear out filter
      this.collectionFilter = newFilter || this.collectionFilter || this.defaultFilter;

      // this assumes that the original collection was unmodified
      // without the use of add/remove/reset events. If it was, a
      // reset event must be thrown, or this object's .resetCollection
      // method must be invoked, or this will most likely fall out-of-sync

      // why HashMap lookup when you can get it off the stack
      var filter = this.collectionFilter;
      var mapping = this._mapping;

      // this is the option object to pass, it will be mutated on each
      // iteration
      var passthroughOption = _.extend({}, options);
      this.collection.each(function(model, index) {
        var foundIndex = mapping.indexOf(index);

        if (filter(model, index)) {
          // if already added, no touchy
          if (foundIndex == -1) {
            passthroughOption.index = index
            this._forceAddModel(model, passthroughOption);
          }
        }
        else {
          if (foundIndex > -1) {
            passthroughOption.index = foundIndex == -1 ? this.length : foundIndex;
            this._forceRemoveModel(model, passthroughOption);
          }
        }
      }, this);
      if (! options.silent) {
        this._filterComplete();
      }
    }

    ,_onModelEvent: function(event, model, collection, options) {
      // noop, this collection has no business dealing with events of the original model
      // they will be handled by the original normal collection and bubble up to here
    }

    ,_filterComplete: function() {
      this.trigger("filter-complete", this);
    }
  });
})(_, Backbone);
