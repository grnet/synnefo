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
            var unknown_title = snf.config.image_deleted_size_title || "(none)";
            if (this.is_deleted()) { return unknown_title }
            return this.get('size') > 0 ? util.readablizeBytes(this.get('size')) : unknown_title;
        },

        get_meta: function(key) {
            // check for lowercase keys too since glance image meta are set 
            // via http headers
            var val = models.GlanceImage.__super__.get_meta.call(this, key)
            if (val == null) {
                val = models.GlanceImage.__super__.get_meta.call(this, 
                                                                 key.toLowerCase())
            }
            return val;
        },

        get_owner: function() {
            return this.get('owner') || 'Unknown';
        },


        display_size: function() {
            return this.get_readable_size();
        },

        display_users: function() {
            try {
              return this.get_meta('users').split(' ').join(", ");
            } catch(err) { console.log(err); return ''}
        }
        
    })

    models.GlanceImages = snf.models.Images.extend({
        model: models.GlanceImage,
        api_type: 'glance',

        type_selections: {'personal':'My images', 
                          'shared': 'Shared with me', 
                          'public': 'Public'},
        type_selections_order: ['system', 'personal', 'shared', 'public'],
        display_metadata: ['size', 'users', 'osfamily', 'status', 'created_at', 'updated_at', 
            'filename', 'format', 'root_partition'],
        meta_labels: {'OS':'OS', 'osfamily':'OS Family', 'GUI':'GUI'},
        display_extra_metadata: true,
        read_method: 'head',

        // custom glance api parser
        parse: function (resp, xhr) {
            if (_.isArray(resp)) {
              resp = {'images': resp };
            }
            return models.GlanceImages.__super__.parse.call(this, resp, xhr);
        },

        _read_image_from_request: function(image, msg, xhr) {
            var img = {};
            img['metadata'] = {};

            var headers = snf.util.parseHeaders(xhr.getAllResponseHeaders().toLowerCase());

            _.each(headers, function(value, key) {
                if (key.indexOf("x-image-meta") == -1) {
                    return
                }

                if (key.indexOf("x-image-meta-property") == -1) {
                    img[key.replace("x-image-meta-","").replace(/-/g,"_")] = _.trim(value);
                } else {
                    img.metadata[key.replace('x-image-meta-property-',"").replace(/-/g,"_")] = _.trim(value);
                }
            
            })

            return img;
        },

        parse_meta: function(img) {
            if (img.properties) {
                img.metadata = {};
                img.metadata = img.properties;
            } else {
                if (!img.metadata) {
                    img.metadata = {};
                }
            }

            // fixes plankton regression (returns lowercase meta keys)
            if (img.metadata.os && !img.metadata.OS) {
                img.metadata.OS = img.metadata.os;
            }

            img = models.GlanceImages.__super__.parse_meta.call(this, img);
            return img;
        },

        get_system_images: function() {
            return _.filter(this.active(), function(i) { 
                return _.include(_.keys(snf.config.system_images_owners), 
                                 i.get_owner());
            })
        },

        get_personal_images: function() {
            return _.filter(this.active(), function(i) { 
                return i.get_owner_uuid() == snf.user.get_username();
            });
        },

        get_public_images: function() {
            return _.filter(this.active(), function(i){ return i.is_public() })
        },

        get_shared_images: function() {
            return _.filter(this.active(), function(i){ 
                return !_.include(_.keys(snf.config.system_images_owners), 
                                  i.get_owner()) && 
                               i.get_owner_uuid() != snf.user.get_username() &&
                               !i.is_public();
            });
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

