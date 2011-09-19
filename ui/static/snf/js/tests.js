$(document).ready(function(){

    // shortcuts
    snf = synnefo;
    models = snf.models;
    util = snf.utils;
    views = snf.views;
    bb = Backbone;
    vms = snf.storage.vms;
    nets = snf.storage.networks;

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
        v1.set({'status': 'DELETE'})
        equals(v1.get('state'), 'DELETE', "Destroy should be kept until DELETE or ERROR");

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


    module("VM List view");
    test("test vm list views", function() {
        vms.unbind();
        expect(11);
        
        var api_mock = undefined;
        function mock_api(data) {
            if (api_mock != undefined) {
                $.mockjaxClear(api_mock)
            }

            api_mock = $.mockjax({
                url: '/api/v1.1/servers/detail*',
                responseTime: 1,
                responseText: {'servers':{'values':vms_data}}
            });
        }

        $("body").append('<div id="demo-vm-view"><div id="demo-vm-view-tpl"><div class="spinner"></div></div></div>');
        
        // create the test vms view
        // bind append calls when view 
        // or vm gets updated
        var DemoView = snf.views.VMListView.extend({
            id_tpl: 'demo-vm-{0}',
            view_id: "test",
            selectors: {
                'vms': '#demo-vm-view',
                'vm': '#demo-vm-{0}',
                'view': '#demo-vm-view',
                'tpl': '#demo-vm-view-tpl',
                'vm_cont_active': '#demo-vm-view',
                'vm_cont_terminated': '#demo-vm-view',
                'vm_spinner': '#demo-vm-{0} .spinner'
            },

            test: "initialize",
            post_add: function(vm) {},
            set_vm_handlers: function(vm) {},
            set_handlers: function() {},
            update_layout: function() {ok(1, "layout updated on '" + this.test + "'")},
            post_update_vm: function(vm) {ok(1, 'vm['+vm.id+'] updated on '+this.test+'')},
            post_remove_vm: function(vm) {ok(1, 'vm['+vm.id+'] removed on '+this.test+'')},
            update_details: function(vm) {}
        })

        
        // 1 call (only layout update
        var view = new DemoView();
        var vms_data = {};

        // initial fetch
        // 2 calls one for layout 1 for the first vm
        view.test = "initial fetch 1 new vm";
        vms_data = [{id:1, name:"server1", status:"ACTIVE"}];
        mock_api(vms_data);
        view.test = "initial fetch";
        vms.fetch({async:false, refresh:true, update:false});
        
        // 1 new vm 1 unchanged
        // 2 calls one for layout 1 for new vm
        view.test = "1 new vm 1 unchanged";
        vms_data = [{id:1, name:"server1", status:"ACTIVE"},
                    {id:2, name:"server2", status:"ACTIVE"}];
        mock_api(vms_data);
        vms.fetch({async:false});

        // 2 changed
        // 4 calls 2 for layout 2 for vms
        view.test = "2 existing changed";
        vms_data = [{id:1, name:"server141", status:"REBOOT"},
                    {id:2, name:"server2512", status:"REBOOT"}];
        mock_api(vms_data);
        vms.fetch({async:false});
        
        // 2 removed
        // 4 calls 2 for layout 2 for vms
        view.test = "2 vms removed";
        vms_data = [{id:1, name:"server141", status:"DELETED"},
                    {id:2, name:"server2512", status:"DELETED"}];
        mock_api(vms_data);
        vms.fetch({async:false});

        vms.unbind();
        delete view;
        $.mockjaxClear();
    });

    module("API errors");
    
    test("test api error", function(){
        expect(2);
        vms.unbind();
        
        var api_mock = undefined;
        function mock_api(data) {
            if (api_mock != undefined) {
                $.mockjaxClear(api_mock)
            }

            api_mock = $.mockjax({
                url: '/api/v1.1/servers/detail*',
                responseTime: 200,
                responseText: {'servers':{'values':data}}
            });
        }

        mock_api({});
        
        snf.api.bind("error", function() {ok(1,"error")});
        snf.api.bind("abort", function() {ok(1,"abort")});

        var a = snf.api.sync("read", {}, {url:"/api/v1.1/servers/detail"});
        a.abort();
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
})
