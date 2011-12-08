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
        api_type: 'glance'

    })

    models.Images = snf.models.Images.extend({
        api_type: 'glance',
        type_selections: {'personal':'My images', 
                          'shared': 'Shared with me', 
                          'public': 'Public'},
        type_selections_order: ['system', 'personal', 'shared', 'public'],
        display_metadata: ['created_at', 'updated_at'],

        parse_meta: function(img) {
            if (img.properties) {
                img.metadata = {};
                img.metadata.values = img.properties;
            }
            
            img = models.Images.__super__.parse_meta.call(this, img);
            return img;
        },
        
        get_system_images: function() {
            return this.filter(function(i){ return i.get_owner() == snf.config.system_images_owner })
        },

        get_personal_images: function() {
            return this.filter(function(i) { return i.get_owner() == snf.user.username });
        },

        get_public_images: function() {
            return this.filter(function(i){ return i.is_public() })
        },

        get_shared_images: function() {
            return this.filter(function(i){ return i.get_owner() != snf.config.system_images_owner && 
                               i.get_owner() != snf.user.username &&
                               !i.is_public() })
        }
    })
    
    // storage initialization
    snf.storage.glance = {};
    snf.storage.glance.images = new models.Images();

    // use glance images
    snf.storage.images = snf.storage.glance.images;

})(this);

