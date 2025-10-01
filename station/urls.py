from django.urls import path, include
from station.views import (
    TrainTypeViewSet,
    TrainViewSet,
    JourneyViewSet,
    OrderViewSet,
    CrewViewSet,
    TicketViewSet,
    RouteViewSet,
    StationViewSet,
    CargoViewSet
)
from rest_framework import routers

app_name = "station"

router = routers.DefaultRouter()
router.register("train_types", TrainTypeViewSet)
router.register("trains", TrainViewSet)
router.register("crews", CrewViewSet)
router.register("cargos", CargoViewSet)
router.register("stations", StationViewSet)
router.register("routes", RouteViewSet)
router.register("journeys", JourneyViewSet)
router.register("orders", OrderViewSet)
router.register("tickets", TicketViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
