/**
 * Copyright 2015 Solinea, Inc.
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
the jQuery dataTables plugin is documented at
http://datatables.net/reference/api/

instantiated on eventsBrowserPageView as:

    this.eventsBrowserTable = new EventsBrowserDataTableView({
        el: '.events-browser-table',
        chartTitle: 'Events Browser',
        infoIcon: 'fa-table',
        width: $('.events-browser-table').width()
    });

*/

var ApiBrowserDataTableView = DataTableBaseView.extend({

    instanceSpecificInit: function() {
        DataTableBaseView.__super__.instanceSpecificInit.apply(this, arguments);
        this.drawSearchTable('#reports-result-table', this.collection.toJSON());
    },

    update: function() {
        this.drawSearchTable('#reports-result-table', this.collection.toJSON());
    },

    // called in dataTableBaseView >
    // oTableParamGenerator
    addParams: function(options) {
        options.columnDefs = [
            {
                // [8] = 'id'
                "targets": [8],
                "visible": false,
                "searchable": true
            }
        ];
        return options;
    },

    preprocess: function(data) {

        /*
        strip object down to _id, _type, timestamp, and things in 'traits'
        and then flatten object before returning it to the dataPrep function
        */

        var self = this;
        var result = [];

        // strip away all but _id, _type, timestamp, and things in traits
        _.each(data, function(item) {
            var tempObj = {};
            tempObj.type = item.doc_type;
            tempObj.ip = item.client_ip;
            tempObj.component = item.component;
            tempObj.timestamp = item['@timestamp'];
            tempObj.uri = item.uri;
            tempObj.host = item.host;
            tempObj.type = item.type;
            tempObj.status = item.response_status;
            tempObj.length = item.response_length;
            tempObj.id = item.id;
            tempObj.response_time = item.response_time;

            result.push(tempObj);
        });

        // replace original data with stripped down dataset
        data = result;

        // reset result array
        result = [];

        // un-nest (flatten) objects
        _.each(data, function(item) {
            result.push(self.flattenObj(item));
        });

        // return flattened/stripped array of objects
        return result;
    },

    // keys will be pinned in ascending value order of key:value pair
    headingsToPin: {
        'timestamp': 0,
        'host': 1,
        'ip': 2,
        'uri': 3,
        'status': 4,
        'response_time': 5,
        'length': 6,
        'component': 7
    }
});
