// Copyright (C) 2010-2014 GRNET S.A.
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.
// 

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

function test() {
    utils.main().create_vm_view.show();   
}

TEST = test;
TEST = false;
