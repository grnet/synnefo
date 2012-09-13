Cloudbar
========

Cloudbar is a project to provide common navigation user experience
between services that share common authentication mechanism and user
entries but get deployed on different domains and may not share
common frontend themes/templates.

The project consists of a javascript file which once imported in a
html page handles the automatic creation and styling of a bar that
is placed on top of the page (first body element absolutely
positioned on top). Since the addition of the bar may break the
current layout of the site once imported the script tries to load an
additional css located in the same url as the script itself named by
the ``CLOUDBAR_ACTIVE_SERVICE`` configuration and prefixed by *service_* so 
that css changes can be applied without touching the page native styles.

The bar contains links to the refered services application urls, and
depending on if the user is authenticated links to account pages
(login, change profile, logout etc.).

To identify if a user is authenticated the script checks of a
specific cookie which can be configured using ``CLOUDBAR_COOKIE_NAME`` setting
contains valid data which should match the following format::
    
    <username or email>|<authentication token>


Usage
-----

Each page that wants to display the navigation bar should:

    - Include one of the latest jquery builds.
    - Set the ``CLOUDBAR_COOKIE_NAME`` variable containing info about the username
      and the authentication status of the current visitor of the page.
    - Set the ``CLOUDBAR_ACTIVE_SERVICE`` to the id of the service the current
      page refers to so that script cat set the appropriate active styles to
      the services menu for services ids see ``SERVICES_LINK`` object in 
      cloudbar.js. Use special **accounts** value to set account menu as the
      active link.
    - Set the ``CLOUDBAR_LOCATION`` to the url where bar files are served from.
    - Include the servicesbar.js script.


Example
*******

.. codeblock:: javascript
    
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.4.2/jquery.min.js"></script>
    <script>
        var CLOUDBAR_COOKIE_NAME = '_pithos2_a';
        var CLOUDBAR_ACTIVE_SERVICE = 'cloud';
        var CLOUDBAR_LOCATION = "https://accounts.cloud.grnet.gr/cloudbar/";

        $(document).ready(function(){
            $.getScript(CLOUDBAR_LOC + 'cloudbar.js');
        })
    </script>


Build styles
------------

Cloudbar uses `less-css <http://www.lesscss.org>`_ for css styles
definitions. To build the less file you need the bootstrap less files
available on 
`bootstrap github repository <https://github.com/twitter/bootstrap/>`.

You can build the styles using the following command::

    $ lessc --include-path=<path/to/bootstrap> cloudbar.less > cloudbar.css

