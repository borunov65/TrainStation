from rest_framework.decorators import action
from rest_framework import viewsets, status, mixins
from django.db.models import Count, F
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.viewsets import GenericViewSet
from rest_framework.exceptions import ValidationError

from station.models import TrainType, Train, Journey, Order
from station.serializers import (
    TrainTypeSerializer,
    TrainSerializer,
    TrainListSerializer,
    TrainRetrieveSerializer,
    TrainImageSerializer,
    JourneySerializer,
    JourneyListSerializer,
    JourneyRetrieveSerializer,
    OrderSerializer,
    OrderListSerializer,
)


class TrainTypeViewSet(viewsets.ModelViewSet):
    queryset = TrainType.objects.all()
    serializer_class = TrainTypeSerializer


class TrainViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = Train.objects.all()
    serializer_class = TrainSerializer

    @staticmethod
    def _params_to_ints(query_string):
        return [int(str_id) for str_id in query_string.split(",")]

    def get_serializer_class(self):
        if self.action == "list":
            return TrainListSerializer
        elif self.action == "retrieve":
            return TrainRetrieveSerializer
        elif self.action == "upload_image":
            return TrainImageSerializer
        return TrainSerializer

    def get_queryset(self):
        queryset = self.queryset

        train_type = self.request.query_params.get("train_type")
        cargo_num = self.request.query_params.get("cargo_num")
        places_in_cargo = self.request.query_params.get("places_in_cargo")

        if train_type:
            train_type = self._params_to_ints(train_type)
            queryset = queryset.filter(train_type__id__in=train_type)

        if cargo_num:
            if not cargo_num.isdigit():
                raise ValidationError({"cargo_num": "cargo_num must be an integer"})
            queryset = queryset.filter(cargo_num=int(cargo_num))

        if places_in_cargo:
            if not places_in_cargo.isdigit():
                raise ValidationError({"places_in_cargo": "places_in_cargo must be an integer"})
            queryset = queryset.filter(places_in_cargo=int(places_in_cargo))

        if self.action in ("list", "retrieve"):
            return queryset.select_related("train_type")

        return queryset.distinct()

    @action(
        methods=["POST"],
        detail=True,
        permission_classes=[IsAdminUser],
        url_path="upload-image",
    )
    def upload_image(self, request, pk=None):
        train = self.get_object()
        serializer = self.get_serializer(train, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="train_type",
                type={"type": "array", "items": {"type": "number"}},
                description="Filter by train_type id (ex. ?train_type=2,3)",
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class JourneyViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = Journey.objects.all().select_related()

    def get_serializer_class(self):
        if self.action == "list":
            return JourneyListSerializer
        elif self.action == "retrieve":
            return JourneyRetrieveSerializer
        return JourneySerializer

    def get_queryset(self):
        queryset = self.queryset
        if self.action == "list":
            queryset = queryset.select_related("train", "route").annotate(
                tickets_available=F("train__cargo_num") * F("train__places_in_cargo") - Count("tickets")
            )

        train_ids = self.request.query_params.get("train")
        if train_ids:
            train_ids = [int(i) for i in train_ids.split(",")]
            queryset = queryset.filter(train__id__in=train_ids)

        route_ids = self.request.query_params.get("route")
        if route_ids:
            route_ids = [int(i) for i in route_ids.split(",")]
            queryset = queryset.filter(route__id__in=route_ids)

        elif self.action == "retrieve":
            queryset = queryset.select_related("train", "route")
        return queryset.order_by("id")


class OrderSetPagination(PageNumberPagination):
    page_size = 3
    page_size_query_param = "page_size"
    max_page_size = 20


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    pagination_class = OrderSetPagination

    def get_queryset(self):
        queryset = self.queryset.filter(user=self.request.user)

        if self.action == "list":
            queryset = queryset.prefetch_related("tickets__journey__train")

        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_serializer_class(self):
        serializer = self.serializer_class

        if self.action == "list":
            serializer = OrderListSerializer

        return serializer
