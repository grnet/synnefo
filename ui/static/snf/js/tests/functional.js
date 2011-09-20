// shortcut helpers on global context
snf = synnefo;
vms = synnefo.storage.vms;
images = synnefo.storage.images;
flavors = synnefo.storage.flavors;
api = synnefo.api;
ui = synnefo.ui;

utils = {
    main: function() { return ui.main },
    current: function() { return ui.main.current_view }
}

function test_create_view() {
    utils.main().create_vm_view.show();   
}


TEST = test_create_view;
