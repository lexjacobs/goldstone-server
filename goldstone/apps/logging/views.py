"""Logging app views."""
# Copyright 2014 - 2015 Solinea, Inc.
#
# Licensed under the Solinea Software License Agreement (goldstone),
# Version 1.0 (the "License"); you may not use this file except in compliance
# with the License. You may obtain a copy of the License at:
#
#     http://www.solinea.com/goldstone/LICENSE.pdf
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either expressed or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.conf import settings
import arrow
import six
import logging

from django.http import HttpResponse, Http404
from rest_framework import serializers, fields, pagination
from rest_framework.exceptions import NotFound
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.serializers import Serializer
from rest_framework.views import APIView

from goldstone.apps.core.serializers import IntervalField, ArrowCompatibleField
from goldstone.apps.logging.models import LogData
from .serializers import LoggingNodeSerializer
from rest_framework.response import Response
from goldstone.apps.core.views import NodeViewSet, ReadOnlyElasticViewSet

logger = logging.getLogger(__name__)


class LoggingNodeViewSet(NodeViewSet):

    serializer_class = LoggingNodeSerializer

    @staticmethod
    def get_request_time_range(params_dict):

        end_time = \
            arrow.get(params_dict['end_time']) if 'end_time' in params_dict \
            else arrow.utcnow()

        start_time = \
            arrow.get(params_dict['start_time']) \
            if 'start_time' in params_dict \
            else end_time.replace(
                minutes=(-1 * settings.LOGGING_NODE_LOGSTATS_LOOKBACK_MINUTES))

        return {'start_time': start_time, 'end_time': end_time}

    @staticmethod
    def _add_headers(response, time_range):
        """Add time logging to a response's header."""

        # pylint: disable=W0212
        response._headers['LogCountEnd'] = \
            ('LogCountEnd', time_range['end_time'].isoformat())
        response._headers['LogCountStart'] = \
            ('LogCountStart', time_range['start_time'].isoformat())

        return response

    def list(self, request, *args, **kwargs):

        time_range = self.get_request_time_range(request.QUERY_PARAMS.dict())
        instance = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(instance)

        serializer = self.get_pagination_serializer(page) if page is not None \
            else self.get_serializer(instance, many=True)

        serializer.context['start_time'] = time_range['start_time']
        serializer.context['end_time'] = time_range['end_time']

        return self._add_headers(Response(serializer.data), time_range)

    def retrieve(self, request, *args, **kwargs):

        time_range = self.get_request_time_range(request.QUERY_PARAMS.dict())

        serializer = self.serializer_class(
            self.get_object(),
            context={'start_time': time_range['start_time'],
                     'end_time': time_range['end_time']})

        return self._add_headers(Response(serializer.data), time_range)


class LogDataPagination(pagination.PageNumberPagination):

    def paginate_queryset(self, queryset, request, view=None):
        """
        Paginate a queryset if required, either returning a
        page object, or `None` if pagination is not configured for this view.
        """
        from django.core.paginator import InvalidPage, \
            Paginator as DjangoPaginator

        self._handle_backwards_compat(view)

        page_size = self.get_page_size(request)
        if not page_size:
            return None

        paginator = DjangoPaginator(queryset, page_size)
        page_number = request.query_params.get(self.page_query_param, 1)
        if page_number in self.last_page_strings:
            page_number = paginator.num_pages

        try:
            self.page = paginator.page(page_number)
            # we need to execute the query to resolve the page of objects
            self.page.object_list = self.page.object_list.execute()
        except InvalidPage as exc:
            msg = self.invalid_page_message.format(
                page_number=page_number, message=six.text_type(exc)
            )
            raise NotFound(msg)

        if paginator.count > 1 and self.template is not None:
            # The browsable API should display pagination controls.
            self.display_page_controls = True

        self.request = request
        return list(self.page)


class LogDataSerializer(Serializer):

    def to_representation(self, instance):
        return instance.to_dict()


class LogDataView(ListAPIView):
    """A view that handles requests for Logstash data."""

    validate_params = {}
    lookup_field = '_id'
    permission_classes = (AllowAny,)
    serializer_class = LogDataSerializer
    pagination_class = LogDataPagination

    class ParamValidator(serializers.Serializer):
        """An inner class that validates and deserializes the request context.
        """
        start = ArrowCompatibleField(
            required=False,
            allow_blank=True)
        end = ArrowCompatibleField(
            required=False,
            allow_blank=True)
        interval = IntervalField(
            required=False,
            allow_blank=True)
        hosts = serializers.ListField(
            child=serializers.CharField(),
            required=False)

    def get_queryset(self):
        logger.info("in get_queryset")
        return LogData.ranged_log_search(**self.validated_params)

    def get_object(self):

        queryset = self.get_queryset()

        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup = self.kwargs.get(lookup_url_kwarg, None)

        if lookup is not None:
            filter_kwargs = {self.lookup_field: lookup}

        queryset_result = queryset.filter(**filter_kwargs)[:1].execute()

        if queryset_result.count > 1:
            logger.warning("multiple objects with %s = %s, only returning "
                           "first one.", lookup_url_kwarg, lookup)

        if queryset_result.count > 0:
            return queryset_result.objects[0].get_object()
        else:
            raise Http404

    def _get_data(self, data):
        return LogData.ranged_log_search(**data)

    def get(self, request, *args, **kwargs):
        """Return a response to a GET request."""
        params = self.ParamValidator(data=request.query_params)
        params.is_valid(raise_exception=True)
        self.validated_params = params.to_internal_value(request.query_params)
        logger.info("iv = %s", self.validated_params)

        logger.info("data = %s", self.queryset)

        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

