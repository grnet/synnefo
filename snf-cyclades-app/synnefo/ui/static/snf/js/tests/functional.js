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
