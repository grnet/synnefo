// Copyright 2011 GRNET S.A. All rights reserved.
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

$(document).ready(function(){

    // shortcuts
    snf = synnefo;
    models = snf.models;
    util = snf.utils;
    views = snf.views;
    bb = Backbone;
    vms = snf.storage.vms;
    nets = snf.storage.networks;

    synnefo.config.api_urls = {
        'compute': '/api/v1.1', 
        'glance':'/images/v1.1'
    };

    module("VM Model")

    test("model change events", function(){
        expect(8);

        synnefo.storage.images.add({id:1,metadata:{values:{size:100}}});
        var v1 = new models.VM({'imageRef':1});
        v1.bind("change", function(){
            ok(1, "change event triggered")
            equals(v1.get("status"), "BUILD")
            equals(v1.get("state"), "BUILD_COPY")
        })
        v1.set({'status':'BUILD', 'progress':80, 'imageRef': 1});
        v1.unbind();

        v1.bind("change", function(){
            ok(1, "change event triggered")
            equals(v1.get("status"), "BUILD")
            equals(v1.get("state"), "DESTROY")
        })
        v1.set({'state':'DESTROY'});
        v1.unbind();

        v1.bind("change", function() {
            ok(1, "change event triggered")
            equals(v1.get("status"), "BUILD")
            equals(v1.get("state"), "BUILD_COPY")
        })
        v1.set({'status':'BUILD', 'progress':80, 'imageRef': 1});
        equals(v1.get("status"), "BUILD")
        equals(v1.get("state"), "DESTROY")
        v1.unbind();
    })

    test("model state transitions", function(){
        var vm = models.VM;
        
        var v1 = new vm();
        v1.set({status: 'BUILD_COPY'})
        equals(v1.get("state"), 'BUILD_COPY', "State is set");
        v1.set({status: 'DESTROY'})
        equals(v1.get("state"), 'DESTROY', "From buld to destroy");
        v1.set({status: 'BUILD'})
        equals(v1.get("state"), 'DESTROY', "Keep destroy state");

        v1 = new vm();
        v1.set({status: 'ACTIVE'})
        equals(v1.get("state"), 'ACTIVE', "State is set");

        v1.set({status: 'SHUTDOWN'})
        equals(v1.get("state"), 'SHUTDOWN', "From active to shutdown (should change)");

        v1.set({status: 'ACTIVE'})
        equals(v1.get("state"), 'SHUTDOWN', "From shutdown to active (should not change)");
        
        v1.set({status: 'STOPPED'})
        equals(v1.get("state"), 'STOPPED', "From shutdown to stopped (should change)");

        v1.set({status: 'ACTIVE'})
        equals(v1.get("state"), 'ACTIVE', "From stopped to active (should change)");
        v1.set({'status': 'STOPPED'})
        equals(v1.get('state'), 'STOPPED', "From shutdown to stopped should change");

        v1.set({'status': 'DESTROY'})
        equals(v1.get('state'), 'DESTROY', "From stopped to destory should set state to DESTROY");
        v1.set({'status': 'ACTIVE'})
        equals(v1.get('state'), 'DESTROY', "From destroy to active should keep state to DESTROY");
        v1.set({'status': 'REBOOT'})
        equals(v1.get('state'), 'DESTROY', "From destroy to active should keep state to DESTROY");
        v1.set({'status': 'DELETED'})
        equals(v1.get('state'), 'DELETED', "Destroy should be kept until DELETE or ERROR");

        v1 = new vm({status:'BUILD'});
        equals(v1.get('state'), 'BUILD', "new vm with build as initial status")
        equals(v1.get('status'), 'BUILD', "new vm with build as initial status")
        v1.set({status:'ACTIVE'})
        equals(v1.get('state'), 'ACTIVE', "active state has been set")
        equals(v1.get('status'), 'ACTIVE', "active status has been set")
    })


    test("building states", function(){
        synnefo.storage.images.add({id:1,metadata:{values:{size:100}}});
        var vm = models.VM;
        var v1 = new vm({'status':'BUILD','progress':0, 'imageRef':1});
        equals(v1.get('state'), 'BUILD_INIT', "progress 0 sets state to BUILD_INIT");
        equals(v1.get('status'), 'BUILD', "progress 0 sets status to BUILD");
        equals(v1.get('progress_message'), 'init', "message 'init'");
        v1.set({status:'BUILD', progress:50});
        equals(v1.get('state'), 'BUILD_COPY', "progress 50 sets state to BUILD_COPY");
        equals(v1.get('status'), 'BUILD', "progress 50 sets status to BUILD");
        equals(v1.get('progress_message'), '50.00 MB, 100.00 MB, 50', "message: 'final'");
        v1.set({status:'BUILD', progress:100});
        equals(v1.get('state'), 'BUILD_FINAL', "progress 100 sets state to BUILD_FINAL");
        equals(v1.get('status'), 'BUILD', "progress 100 sets status to BUILD");
        v1.set({status:'ACTIVE', progress:100});
        equals(v1.get('state'), 'ACTIVE', "ACTIVE set transition to ACTIVE");
        equals(v1.get('status'), 'ACTIVE', "ACTIVE set transition to ACTIVE");
        equals(v1.get('progress_message'), 'final', "message: 'final'");
    })

    test("active inactive states", function(){
    
        var vm = models.VM;
        var v1 = new vm();
        var v = {}
        var active = ['ACTIVE', 'BUILD', 'REBOOT'];
        for (v in active) {
            v = active[v];
            v1.set({status: v})
            equals(v1.is_active(), true, v + " status is active")
        }
        
        var v1 = new vm();
        var inactive = ['STOPPED', 'ERROR', 'UNKNOWN'];
        for (v in inactive) {
            v = inactive[v];
            v1.set({status: v})
            equals(v1.is_active(), false, v1.state() + " status is not active")
        }
    
    })

    test("transition event", function(){
        expect(9);

        var vm = new models.VM({status:'BUILD'});
        vm.bind("transition", function(data) {
            ok(true, "Transition triggered");
            equals(data.from, "BUILD")
            equals(data.to, "ACTIVE");
        })
        // trigger 1 time
        vm.set({status:'BUILD'});
        vm.set({status:'ACTIVE'});
        vm.unbind();
        
        // from build to active
        vm = new models.VM({status:'BUILD'});
        vm.bind("transition", function(data) {
            ok(true, "Transition triggered");
            equals(data.from, "BUILD")
            equals(data.to, "ACTIVE");
        })
        // trigger 1 time
        vm.set({status:'ACTIVE'});
        vm.unbind();

        // from active to shutdown
        vm = new models.VM({status:'SHUTDOWN'});
        vm.bind("transition", function(data) {
            ok(true, "Transition triggered");
            equals(data.from, "SHUTDOWN")
            equals(data.to, "STOPPED");
        })
        // trigger 1 time
        vm.set({status:'STOPPED'});
    })
    
    module("Collections");
        
    test("status model remove events", function(){
        vms.unbind();
        expect(1)

        vms.bind("change", function(){
            ok(-1, "change event should not get triggered");
        })

        vms.bind("remove", function(){
            ok(1, "remove event triggered")
        })

        var vm = new models.VM({id:1, status:"ACTIVE", name:"oldname"});
        vms.add(vm);
        
        // NO change/delete just DELETE event triggered
        vms.update([{id:1, status:"DELETED", name:"newname"}])
    });

    test("collection reset events", function() {
        expect(9);

        var testCollection = models.Collection.extend({
            url: '/testObject'
        });
        var collection = new testCollection();

        
        // reset on new entry after empty
        $.mockjax({
            url: '/testObject',
            responseTime: 50,
            responseText: [
                {id:1, attr1: 1, attr2: 2}
            ]
        }); 
        // THIS SHOULD NOT FIRE, since we force update method
        collection.bind("reset", function() {
            ok(1, "NOT EXPECTED: reset triggered on new entry while collection was empty");
        });
        collection.bind("add", function() {
            ok(1, "1: add triggered on new entry while collection was empty");
        });
        // THIS SHOULD NOT FIRE, model was added, not changed
        collection.bind("change", function() {
            ok(1, "NOT EXPECTED: change triggered on new entry while collection was empty");
        });
        collection.fetch({'async': false});
        equals(collection.length, 1, "2: collection contains 1 model");
        collection.unbind();
        $.mockjaxClear();
        
        // reset is called on change
        $.mockjax({
            url: '/testObject',
            responseTime: 50,
            responseText: [
                {id:1, attr1: 4, attr2: 2}
            ]
        });
        collection.bind("reset", function() {
            ok(1, "NOT EXPECTED: reset triggered on new entry while collection was empty");
        });
        collection.bind("add", function() {
            ok(1, "NOT EXPECTED: add triggered on new entry while collection was empty");
        });
        // THIS SHOULD NOT FIRE, model was added, not changed
        collection.bind("change", function() {
            ok(1, "3: change triggered on new entry while collection was empty");
        });
        collection.fetch({'async': false, refresh:true});
        equals(collection.length, 1, "4 collection contains 1 model");
        collection.unbind();
        $.mockjaxClear();

        // reset on second entry
        $.mockjax({
            url: '/testObject',
            responseTime: 50,
            responseText: [
                {id:1, attr1: 4, attr2: 2},
                {id:2, attr1: 1, attr2: 2}
            ]
        });
        collection.bind("reset", function() {
            ok(1, "NOT EXPECTED: reset triggered when new model arrived");
        })
        collection.bind("add", function() {
            ok(1, "5: add triggered when new model arrived");
        })
        collection.bind("change", function() {
            ok(1, "NOT EXPECTED: change triggered when new model arrived");
        }) 
        collection.fetch({async:false, refresh:true});
        equals(collection.length, 2, "6 new model added");
        collection.unbind();
        $.mockjaxClear();
        
        // reset does not remove
        $.mockjax({
            url: '/testObject',
            responseTime: 50,
            responseText: [
                {id:2, attr1: 1, attr2: 2}
            ]
        }); 
        collection.bind("reset", function() {
            ok(1, "NOT EXPECTED: reset triggered when model removed");
        })
        collection.bind("remove", function() {
            ok(1, "7: remove triggered when model removed");
        })
        collection.bind("change", function() {
            ok(1, "NOT EXPECTED: change triggered when model removed");
        })

        collection.fetch({async:false, refresh:true});
        equals(collection.length, 1, "8 one model removed");
        collection.unbind();
        $.mockjaxClear();

        // reset is not called on 304
        $.mockjax({
            url: '/testObject',
            responseTime: 50,
            status: 304,
            responseText: undefined
        }); 
        // NO event is triggered on 304
        collection.bind("reset", function() {
            ok(1, "WRONG: reset triggered on 304");
        });
        collection.bind("remove", function() {
            ok(1, "WRONG: remove triggered on 304");
        });
        collection.bind("change", function() {
            ok(1, "WRONG: remove triggered on 304");
        });
        collection.fetch({async:false, refresh:true});
        equals(collection.length, 1, "9 one model removed");
        collection.unbind();
        $.mockjaxClear();
    })


    module("network vm connections")
    test("network vm connections", function() {

        function _net(id, ip) {
            return {
                id: id,
                name: "net " + id,
                values:[{version:4, addr: ip}, {version:6, addr:ip}] 
            }
        }
        vms.add({id:1, name:"s1", linked_to_nets:[_net("p", "127")]});
        var vm = vms.at(0);
        
        nets.add({id:"p", nid:"p", name:"n1", linked_to:[1]});
        var n = nets.at(0);
    })

    module("images/flavors")
    test("Test DELETE state image retrieval", function() {
        snf.storage.images.reset();
        snf.storage.vms.reset();

        var images = snf.storage.images;
        var vms = snf.storage.vms;

        var img = images.add({name:"image 1", id:1}).last();
        var vm1 = vms.add({imageRef:1, name:"vm1"}).last();
        var vm2 = vms.add({imageRef:2, name:"vm2"}).last();
            
        equals(img, vm1.get_image());
        
        // reset is not called on 304
        $.mockjax({
            url: '/api/v1.1/images/2',
            responseTime: 50,
            status: 200,
            responseText: {image:{name:"image 2", id:2}}
        }); 
        
        
        equals(images.length, 1, "1 image exists");
        vm2.get_image();
        equals(images.get(2).get("name"), "image 2", "image data parsed");
        equals(images.length, 2);
    })

    test("Test DELETE state flavor retrieval", function() {
        snf.storage.flavors.reset();
        snf.storage.vms.reset();

        var flavors = snf.storage.flavors;
        var vms = snf.storage.vms;

        var flv = flavors.add({id:1, cpu:1, disk:1, ram:1024}).last();
        var vm1 = vms.add({flavorRef:1, name:"vm1"}).last();
        var vm2 = vms.add({flavorRef:2, name:"vm2"}).last();
            
        equals(flv, vm1.get_flavor());
        
        // reset is not called on 304
        $.mockjax({
            url: '/api/v1.1/flavors/2',
            responseTime: 50,
            status: 200,
            responseText: {flavor:{cpu:1, ram:2048, disk:100, id:2}}
        }); 
        
        
        equals(flavors.length, 1, "1 flavor exists");
        vm2.get_flavor();
        equals(flavors.get(2).get("ram"), 2048, "flavor data parsed");
        equals(flavors.length, 2);
    })

    test("actions list object", function(){
        var m = new models.Image();
        var l = new models.ParamsList(m, "actions");
        var count = 0;

        l.add("destroy");
        equals(l.has_action("destroy"), true);
        equals(l.contains("destroy"), true);

        l.add("destroy", 1, {});
        equals(l.has_action("destroy"), true);
        equals(l.contains("destroy", 1, {}), true);

        l.remove("destroy", 1, {});
        equals(l.contains("destroy", 1, {}), false);

        m.bind("change:actions", function() { count ++});
        l.add("destroy");
        
        equals(count, 0);
        l.add("destroy", 1, {});
        equals(count, 1);
    });

    module("update handlers")
    test("update handlers", function() {
        // this test is based on multiple timeouts
        // so the results might differ between different browsers
        // or browser load
        stop();

        var counter = 0;
        var cb = function() {
            counter++;
        }
        
        var opts = {
            callback:cb,
            interval: 10,
            fast: 5,
            increase: 5,
            max: 15,
            increase_after_calls: 3,
            initial_call: false
        }

        var h = new snf.api.updateHandler(opts);
        h.start();

        var add = $.browser.msie ? 8 : 0;

        window.setTimeout(function(){
            h.stop();
            start();
            // 4 calls, limit reached
            equals(counter, 4, "normal calls");
            equals(h.interval, opts.max, "limit reached");

            stop();
            h.start(false);
            h.faster();
            window.setTimeout(function(){
                // 11 calls, limit reached
                start();
                equals(counter, 11, "faster calls");
                equals(h.interval, opts.max, "limit reached");
                h.stop();
                stop();
                window.setTimeout(function(){
                    // no additional calls because we stopped it
                    start();
                    equals(counter, 11, "no additional calls")
                }, 50 + add)
            }, 50 + add)
        }, 43 + add)
    })
})
