from django.urls import path, include
from rest_framework import routers

from airport.views import (
    AirportViewSet,
    RouteViewSet,
    AirplaneTypeViewSet,
    AirplaneViewSet,
    OrderViewSet,
    FlightViewSet,
    CrewViewSet,
)


router = routers.DefaultRouter()
router.register(
    "airport",
    AirportViewSet,
    basename="airport"
)
router.register(
    "route",
    RouteViewSet,
    basename="route"
)
router.register(
    "airplane_type",
    AirplaneTypeViewSet,
    basename="airplane_type"
)
router.register(
    "airplane",
    AirplaneViewSet,
    basename="airplane"
)
router.register(
    "order",
    OrderViewSet,
    basename="order"
)
router.register(
    "flight",
    FlightViewSet,
    basename="flight"
)
router.register(
    "crew",
    CrewViewSet,
    basename="crew"
)

urlpatterns = [
    path("", include(router.urls)),
]

app_name = "airport"
