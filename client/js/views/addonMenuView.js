/**
 * Copyright 2016 Solinea, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/*

instantiated in init.js as:
goldstone.addonMenuView = new AddonMenuView({});

if compliance and/or topology module installed, after login, localStorage will contain:
compliance: [{
    url_root: 'compliance'
}]
topology: [{
    url_root: 'topology'
}]

*/

var AddonMenuView = GoldstoneBaseView.extend({

    instanceSpecificInit: function() {
        this.generateAddonIconsAndRoute();
    },

    generateAddonIconsAndRoute: function() {
        var compliance = JSON.parse(localStorage.getItem('compliance'));
        var topology = JSON.parse(localStorage.getItem('topology'));

        if (compliance) {

            // render the compliance icon and set the routes
            $(".compliance-icon-container").html(this.complianceTemplate());
            this.generateRoutesPerAddon(compliance[0]);
        }

        if (topology) {

            // render the topology icon and set the routes
            $(".topology-icon-container").html(this.topologyTemplate());
            this.generateRoutesPerAddon(topology[0]);
        }

        // initialize tooltip connected to new menu item
        $('[data-toggle="tooltip"]').tooltip({
            trigger: 'hover'
        });
    },

    generateRoutesPerAddon: function(module) {
        var self = this;
        // if the module is installed this should be true
        if (goldstone[module.url_root]) {

            // for each sub-array in the array of 'routes' in
            // the addon's javascript file, do the following:
            _.each(goldstone[module.url_root].routes, function(route) {
                // pass along the route array
                // and the name of the addon
                // which is needed for
                // proper side-menu highlighting
                self.addNewRoute(route, module.url_root);
            });
        }

    },

    addNewRoute: function(routeToAdd, eventName) {
        /*
        .route will dynamically add a new route where the
        url is index 0 of the passed in route array, and
        eventName is the string to return via
        the router's on.route event.
        finally, the view to load is index 2 of the passed in route array.
        */

        goldstone.gsRouter.route(routeToAdd[0], eventName, function(passedValue) {

            // passedValue will be created by routes with /:foo
            // passed value = 'foo'
            if (passedValue) {
                this.switchView(routeToAdd[2], {
                    'passedValue': passedValue
                });
            } else {
                this.switchView(routeToAdd[2]);
            }
        });
    },

    topologyTemplate: _.template('' +
        '<a href="#topology">' +
        '<li class="topology-tab" data-toggle="tooltip" data-i18n-tooltip="Topology" data-placement="right" title="Topology">' +
        '<span class="btn-icon-block"><i class="icon topology">&nbsp;</i></span>' +
        '<span data-i18n="Topology" class="btn-txt i18n">Topology</span>' +
        '</li>' +
        '</a>'
    ),

    complianceTemplate: _.template('' +
        '<a href="#compliance/opentrail/manager/">' +
        '<li class="compliance-tab" data-toggle="tooltip" data-i18n-tooltip="Compliance" data-placement="right" title="Compliance">' +
        '<span class="btn-icon-block"><i class="icon compliance">&nbsp;</i></span>' +
        '<span class="btn-txt i18n" data-i18n="Compliance">Compliance</span>' +
        '</li>' +
        '</a>'
    )

});
