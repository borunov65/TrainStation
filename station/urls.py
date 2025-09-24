from django.urls import path, include
from station.views import TrainTypeViewSet, TrainViewSet, JourneyViewSet, OrderViewSet
from rest_framework import routers

app_name = "station"

router = routers.DefaultRouter()
router.register("trains", TrainViewSet)
router.register("journeys", JourneyViewSet)
router.register("train_types", TrainTypeViewSet)
router.register("orders", OrderViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
