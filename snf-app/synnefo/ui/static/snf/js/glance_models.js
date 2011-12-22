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

    models.GlanceImage = snf.models.Image.extend({
        api_type: 'glance',

        get_size: function() {
            return this.get('size') / 1024 / 1024;
        },

        get_readable_size: function() {
            return this.get('size') > 0 ? util.readablizeBytes(this.get('size')) : "unknown";
        },

        display_size: function() {
            return this.get_readable_size();
        }
    })

    models.GlanceImages = snf.models.Images.extend({
        model: models.GlanceImage,
        api_type: 'glance',
        type_selections: {'personal':'My images', 
                          'shared': 'Shared with me', 
                          'public': 'Public'},
        type_selections_order: ['system', 'personal', 'shared', 'public'],
        display_metadata: ['created_at', 'updated_at', 'filename', 'format', 
                            'size', 'status'],
        read_method: 'head',

        // custom glance api parser
        parse: function (resp, xhr) {
            if (_.isArray(resp)) {
                resp = {'images': {'values': resp }};
            }
            return models.GlanceImages.__super__.parse.call(this, resp, xhr);
        },

        _read_image_from_request: function(image, msg, xhr) {
            var img = {};
            img['metadata'] = {values:{}};

            var headers = snf.util.parseHeaders(xhr.getAllResponseHeaders().toLowerCase());

            _.each(headers, function(value, key) {
                if (key.indexOf("x-image-meta") == -1) {
                    return
                }

                if (key.indexOf("x-image-meta-property") == -1) {
                    img[key.replace("x-image-meta-","").replace(/-/g,"_")] = _.trim(value);
                } else {
                    img.metadata.values[key.replace('x-image-meta-property-',"").replace(/-/g,"_")] = _.trim(value);
                }
            
            })

            return img;
        },

        parse_meta: function(img) {
            if (img.properties) {
                img.metadata = {};
                img.metadata.values = img.properties;
            }
            
            img = models.GlanceImages.__super__.parse_meta.call(this, img);
            return img;
        },

        get_system_images: function() {
            return _.filter(this.active(), function(i){ return i.get_owner() == snf.config.system_images_owner })
        },

        get_personal_images: function() {
            return _.filter(this.active(), function(i) { return i.get_owner() == snf.user.username });
        },

        get_public_images: function() {
            return _.filter(this.active(), function(i){ return i.is_public() })
        },

        get_shared_images: function() {
            return _.filter(this.active(), function(i){ return i.get_owner() != snf.config.system_images_owner && 
                               i.get_owner() != snf.user.username &&
                               !i.is_public() })
        }

    })
        
    // replace images storage collection
    snf.glance.register = function() {
        // storage initialization
        snf.storage.glance = {};
        snf.storage.glance.images = new models.GlanceImages();

        // use glance images
        snf.storage.images = snf.storage.glance.images;
    }

})(this);

