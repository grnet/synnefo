// Copyright 2012 GRNET S.A. All rights reserved.
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

;(function(root){
    
    // Astakos client javascript lib
    // Requires jquery and jquery.cookie javascript libs
    //
    // Usage
    // -----
    // <script src="jquery.js"></script>
    // <script src="jquery.cookie.js"></script>
    // <script src="snf/auth.js"></script>
    //
    //  var astakos_config = {
    //        'login_url': '/im/login',
    //        'auth_url': '/im/authenticate',
    //        'cookie_name': '_pithos2_a',
    //        'logout_callback': function(client) {
    //            console.log("logging out");
    //            client.redirect_to_logout();
    //        }
    //
    //  var astakos_client = new snf.auth.AstakosClient(astakos_config);
    //  var user = astakos_client.get_user();
    //  if (!user) { astakos_client.redirect_to_login() };
    //  console.log(user.username, user.token);
    //

    var root = root;
    var snf = root.synnefo = root.synnefo || {};
    
    // init auth namespace
    snf.auth = {};
    
    snf.auth.AstakosClient = function(config) {
        this.config = $.extend(this.default_config, config);
    }

    snf.auth.AstakosClient.prototype.default_config = {
            'logout_url': '/im/logout',
            'login_url': '/im/login',
            'cookie_name': '_pithos2_a',
            'logout_callback': function(client) {
                client.redirect_to_logout();
            }
    }

    snf.auth.AstakosClient.prototype.delete_cookie = function() {
        $.cookie(this.config.cookie_name, null);
    }

    snf.auth.AstakosClient.prototype.redirect_to_logout = function() {
        window.location = this.config.logout_url + "?next=";
    }
    
    snf.auth.AstakosClient.prototype.redirect_to_login = function() {
        window.location = this.config.login_url + "?next=" + window.location.toString();
    }

    // delete cookie and redirect to logout
    // cookie removal can be forced by passing true as delete_cookie parameter
    snf.auth.AstakosClient.prototype.logout = function(delete_cookie) {
        var delete_cookie = delete_cookie == undefined ? false : delete_cookie;
        if (delete_cookie) {
            this.delete_cookie();
        }
        this.config.logout_callback(this);
    }

    snf.auth.AstakosClient.prototype.get_cookie_data = function() {
        var data = $.cookie(this.config.cookie_name);
        
        // remove " characters
        if (data) { return data.replace(/\"/g, "") }
        return data;
    }


    snf.auth.AstakosClient.prototype.logged_in = function() {
        return this.get_cookie_data() == null
    }

    // parse cookie data
    // astakos sets cookie data using the following pattern: <username>|<token>
    snf.auth.AstakosClient.prototype.parse_cookie_data = function(data) {
        return {
            'username': data.split("|")[0],
            'token': data.split("|")[1]
        }
    }
    
    // set username and token
    snf.auth.AstakosClient.prototype.get_user = function() {
        var data = this.get_cookie_data();
        if (!data) {
            return false;
        }
        var parsed_data = this.parse_cookie_data(data);
        return parsed_data;
    }
    
})(this);
