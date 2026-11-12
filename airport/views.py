from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, mixins, pagination, status
from django.db.models import Prefetch
from django.db.models import F, Count
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.response import Response

import django_filters

from airport.models import (
    Airport,
    Route,
    AirplaneType,
    Airplane,
    Order,
    Flight,
    Crew,
)
from airport.serializers import (
    AirportSerializer,
    RouteSerializer,
    AirplaneTypeSerializer,
    AirplaneSerializer,
    OrderSerializer,
    FlightSerializer,
    CrewSerializer,
    RouteListSerializer,
    RouteDetailSerializer,
    AirplaneListSerializer,
    CrewListSerializer,
    FlightListSerializer,
    FlightDetailSerializer,
    OrderListSerializer,
    AirplaneTypeImageSerializer,
    CrewImageSerializer,
)

from airport.permissions import (
    IsAdminOrIfAuthenticatedReadOnly,
    IsAdminOrReadOnly
)


class Pagination(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class AirportViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    queryset = Airport.objects.all()
    serializer_class = AirportSerializer
    permission_classes = [IsAdminOrIfAuthenticatedReadOnly]


class RouteViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
    mixins.RetrieveModelMixin,
):
    queryset = Route.objects
    serializer_class = RouteSerializer
    permission_classes = [IsAdminOrIfAuthenticatedReadOnly]

    @staticmethod
    def _params_to_ints(qs):
        return [int(str_id) for str_id in qs.split(",")]

    def get_serializer_class(self):
        if self.action == "list":
            return RouteListSerializer

        if self.action == "retrieve":
            return RouteDetailSerializer

        return RouteSerializer

    def get_queryset(self):
        queryset = self.queryset

        source = self.request.query_params.get(
            "source_city",
            None
        )
        destination = self.request.query_params.get(
            "destination_city",
            None
        )

        if source:
            source = self._params_to_ints(source)
            queryset = queryset.filter(source__id__in=source)

        if destination:
            destination = self._params_to_ints(destination)
            queryset = queryset.filter(destination__id__in=destination)

        if self.action == "list":
            return queryset.select_related()

        return queryset.distinct()


class AirplaneTypeViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
    mixins.RetrieveModelMixin,
):
    queryset = AirplaneType.objects.all()
    serializer_class = AirplaneTypeSerializer
    permission_classes = [IsAdminOrIfAuthenticatedReadOnly]

    def get_serializer_class(self):
        if self.action == "upload_image":
            return AirplaneTypeImageSerializer

        return AirplaneTypeSerializer

    @action(
        methods=["POST"],
        detail=True,
        permission_classes=[permissions.IsAdminUser],
        url_path="upload-image",
    )
    def upload_image(self, request, pk=None):
        airplane_type = self.get_object()
        serializer = self.get_serializer(
            airplane_type,
            data=request.data
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class AirplaneViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Airplane.objects
    serializer_class = AirplaneSerializer
    permission_classes = [IsAdminOrIfAuthenticatedReadOnly]

    def get_serializer_class(self):
        if self.action == "list":
            return AirplaneListSerializer

        return AirplaneSerializer

    def get_queryset(self):
        queryset = self.queryset

        airplane_id = self.request.query_params.get("id", None)

        if airplane_id:
            ids = airplane_id.split(",")
            queryset = queryset.filter(id__in=ids)

        if self.action == "list":
            return queryset.select_related()

        return queryset.distinct()


class OrderViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    queryset = Order.objects
    serializer_class = OrderSerializer
    pagination_class = Pagination
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset.filter(
            user=self.request.user
        )

        if self.action == "list":
            return queryset.prefetch_related(
                "tickets__flight",
            )

        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer

        return OrderSerializer


class FlightFilter(django_filters.FilterSet):
    source = django_filters.CharFilter(
        field_name="route__source__closest_big_city",
        lookup_expr="icontains"
    )
    destination = django_filters.CharFilter(
        field_name="route__destination__closest_big_city",
        lookup_expr="icontains"
    )
    departure_time = django_filters.DateFromToRangeFilter()

    class Meta:
        model = Flight
        fields = [
            "source",
            "destination",
            "departure_time",
        ]


class FlightViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
    mixins.RetrieveModelMixin,
):
    queryset = Flight.objects
    serializer_class = FlightSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = FlightFilter
    pagination_class = Pagination
    permission_classes = [IsAdminOrReadOnly]

    def get_serializer_class(self):
        if self.action == "list":
            return FlightListSerializer

        if self.action == "retrieve":
            return FlightDetailSerializer

        return FlightSerializer

    def get_queryset(self):
        queryset = self.queryset

        if self.action == "list":
            return (
                queryset
                .select_related()
                .annotate(
                    available_seats=(
                            F("airplane__rows")
                            * F("airplane__seats_in_row")
                            - Count("tickets")
                    )
                )
            )

        if self.action == "retrieve":
            return queryset.select_related()

        return queryset


class CrewViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
    mixins.RetrieveModelMixin,
):
    queryset = Crew.objects
    serializer_class = CrewSerializer
    pagination_class = Pagination
    permission_classes = [IsAdminOrIfAuthenticatedReadOnly]

    @action(
        methods=["POST"],
        detail=True,
        permission_classes=[permissions.IsAdminUser],
        url_path="upload-image",
    )
    def upload_image(self, request, pk=None):
        crew_person = self.get_object()
        serializer = self.get_serializer(
            crew_person,
            data=request.data
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return CrewListSerializer

        if self.action == "upload_image":
            return CrewImageSerializer

        return CrewSerializer

    def get_queryset(self):
        queryset = self.queryset

        if self.action == "list":
            flight_qs = Flight.objects.select_related(
                "route",
                "route__source",
                "route__destination",
                "airplane",
                "airplane__airplane_type"
            )
            queryset = queryset.prefetch_related(
                Prefetch(
                    "flight",
                    queryset=flight_qs,
                    )
                )

        return queryset
