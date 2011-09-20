// shortcut helpers on global context
snf = synnefo;
vms = synnefo.storage.vms;
images = synnefo.storage.images;
flavors = synnefo.storage.flavors;
api = synnefo.api;
ui = synnefo.ui;
models = synnefo.models;

SERVERS_CREATED = 0;
utils = {
    main: function() { return ui.main },
    current: function() { return ui.main.current_view },
    nets: function() { return ui.main.views['networks']},
    
    rnd: function (lst) {
        var i = Math.floor((lst.length)*Math.random());
        return lst[i];
    },

    rvms: function(count, st, data) {
        while (count) {
            utils.rvm(st, data)
            count--;
        }
    },

    // random vm
    rvm: function(st, data) {
        if (!data) { data = {} };
        if (st) { data['status'] = st };

        var s = new models.VM();
        s.set(_.extend({
            'name': "server " + (SERVERS_CREATED + 1),
            'created': "2011-08-31T12:38:05.183738+00:00",
            'flavorRef': utils.rnd([1,2,3,4,5,6,7,8,9,10,11,12,13,14]),
            'imageRef': utils.rnd([1,2,3,4]),
            'progress': 100,
            'status': utils.rnd(['BUILD', 'ACTIVE', 'ERROR']),
            'updated': '2011-08-31T12:38:14.746141+00:00',
            'metadata': {'values':{ 'OS': utils.rnd(["debian", "fedora", "windows"])}},
            'id': vms.length + 100
        }, data));

        SERVERS_CREATED++;
        vms.add(s);
        return s;
    }

}

function test_create_view() {
    utils.main().create_vm_view.show();   
}

function test_nets_border() {
    utils.rvms(1);

    //vms.each(function(vm) {
        //utils.nets().network_views['public'].create_vm(vm);
        //utils.nets().network_views[2].create_vm(vm);
    //})
    utils.nets().network_views['public'].create_vm(vms.at(0));
    utils.nets().network_views[2].create_vm(vms.at(0));

    utils.nets().network_views['public'].$(".cont-toggler").click();
    utils.nets().network_views[2].vms_list.show();
    $(window).trigger("resize");
}


TEST = test_nets_border;
TEST = false;
