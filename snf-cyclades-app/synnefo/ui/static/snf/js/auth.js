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
    //  var user = new snf.auth.AstakosClient(astakos_config);
    //  if (!user.get_token() { user.redirect_to_login() };
    //  console.log(user.get_username(), user.get_token());
    //

    var root = root;
    var snf = root.synnefo = root.synnefo || {};
    
    // init auth namespace
    snf.auth = {};
    
    snf.auth.AstakosClient = function(config) {
        this.config = $.extend(this.default_config, config);
        this.current_token = undefined;
        this.current_username = undefined;
        this.skip_redirects = config.skip_redirects === undefined ? false : 
                              config.skip_redirects;
      
        var self = this;
        this.updater = window.setInterval(function(){
          self.get_token();
          self.get_username();
        }, 10000);
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
      if (!this.skip_redirects) {
        $.cookie(this.config.cookie_name, null);
      }
    }

    snf.auth.AstakosClient.prototype.redirect_to_logout = function() {
      if (!this.skip_redirects) {
        window.location = this.config.logout_url + "?next=";
      }
    }
    
    snf.auth.AstakosClient.prototype.redirect_to_login = function() {
      if (!this.skip_redirects) {
        window.location = this.config.login_url + "?next=" + window.location.toString();
      }
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
    
    snf.auth.AstakosClient.prototype.extract_cookie_contents = function() {
        var data = this.get_cookie_data();
        if (!data) {
            return {};
        }
        return this.parse_cookie_data(data);
    }

    snf.auth.AstakosClient.prototype.get_token = function() {
      var newtoken;
      newtoken = this.extract_cookie_contents().token;
      if (newtoken === undefined || (newtoken != this.current_token && 
          this.current_token != undefined)) {
        this.redirect_to_login();
      }
      this.current_token = newtoken;
      return this.current_token;
    }

    snf.auth.AstakosClient.prototype.get_username = function() {
      var newusername;
      newusername = this.extract_cookie_contents().username;
      if (newusername === undefined || (newusername != this.current_username && 
          this.current_username != undefined)) {
        this.redirect_to_login();
      }
      this.current_username = newusername;
      return this.current_username;
    }
    
})(this);
