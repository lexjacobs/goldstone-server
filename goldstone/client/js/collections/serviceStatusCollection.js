/**
 * Copyright 2014 Solinea, Inc.
 *
 * Licensed under the Solinea Software License Agreement (goldstone),
 * Version 1.0 (the "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at:
 *
 *     http://www.solinea.com/goldstone/LICENSE.pdf
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * Author: Alex Jacobs
 */

var ServiceStatusCollection = Backbone.Collection.extend({

    defaults: {},

    parse: function(data) {
        var nextUrl;
        if (data.next && data.next !== null) {
            var dp = data.next;
            nextUrl = dp.slice(dp.indexOf('/core'));
            this.fetch({
                url: nextUrl,
                remove: false
            });
        }
        return data.results;
    },

    model: ServiceStatusModel,

    initialize: function(options) {
        this.options = options || {};
        this.defaults = _.clone(this.defaults);
        this.defaults.nodeName = options.nodeName;
        this.retrieveData();
    },

    retrieveData: function() {
        var self = this;

        var twentyAgo = (+new Date() - (1000 * 60 * 20));

        this.url = "/core/reports?name__prefix=os.service&node__prefix=" +
            this.defaults.nodeName + "&page_size=300" +
            "&timestamp__gte=" + twentyAgo;

        this.fetch();
    }
});
