;(function(root){
    
    // root
    var root = root;
    
    // setup namepsaces
    var snf = root.synnefo = root.synnefo || {};
    var glance = snf.glance = snf.glance || {};
    var models = glance.models = glance.models || {}
    var storage = glance.storage = glance.storage || {};
    var util = snf.util = snf.util || {};

    // shortcuts
    var bb = root.Backbone;
    var slice = Array.prototype.slice

    // logging
    var logger = new snf.logging.logger("SNF-MODELS");
    var debug = _.bind(logger.debug, logger);

    
    models.Image = snf.models.Image.extend({
        //api_type: 'glance'
    })

    models.Images = snf.models.Images.extend({
        //api_type: 'glance'
        
        personal: function() {
            return _.filter(this.active(), function(i) { return i.get("serverRef") });
        }
    })
    
    // storage initialization
    snf.storage.glance = {};
    snf.storage.glance.images = new models.Images();

})(this);

