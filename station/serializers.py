from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import (
    TrainType,
    Train,
    Station,
    Route,
    Journey,
    Crew,
    Ticket,
    Order,
)


class TrainTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = TrainType
        fields = ("id", "name")


class TrainSerializer(serializers.ModelSerializer):
    train_type = serializers.SlugRelatedField(
        slug_field="name",
        queryset=TrainType.objects.all()
    )

    class Meta:
        model = Train
        fields = (
            "id",
            "name",
            "cargo_num",
            "places_in_cargo",
            "train_type"
        )


class TrainImageSerializer(serializers.ModelSerializer):

    class Meta:
        model = Train
        fields = ("id", "image")


class TrainListSerializer(serializers.ModelSerializer):
    train_type = serializers.SlugRelatedField(
        slug_field="name", read_only=True
    )
    capacity = serializers.IntegerField(read_only=True)

    class Meta:
        model = Train
        fields = ("id", "name", "train_type", "capacity")


class TrainRetrieveSerializer(serializers.ModelSerializer):
    train_type = TrainTypeSerializer(read_only=True)
    capacity = serializers.IntegerField(read_only=True)

    class Meta:
        model = Train
        fields = ("id", "name", "cargo_num", "places_in_cargo", "train_type", "capacity")


class TrainImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Train
        fields = ("id", "image")


class StationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Station
        fields = ("id", "name", "latitude", "longitude")


class RouteSerializer(serializers.ModelSerializer):
    source = serializers.SlugRelatedField(
        slug_field="name",
        queryset=Station.objects.all()
    )
    destination = serializers.SlugRelatedField(
        slug_field="name",
        queryset=Station.objects.all()
    )

    class Meta:
        model = Route
        fields = (
            "id",
            "source",
            "destination",
            "distance"
        )

class CrewSerializer(serializers.ModelSerializer):

    class Meta:
        model = Crew
        fields = ("id", "first_name", "last_name")


class JourneySerializer(serializers.ModelSerializer):
    crews = CrewSerializer(many=True, read_only=True)

    class Meta:
        model = Journey
        fields = (
            "id",
            "route",
            "train",
            "departure_time",
            "arrival_time",
            "crews"
        )


class JourneyListSerializer(serializers.ModelSerializer):
    route_source = serializers.CharField(
        source="route.source.name",
        read_only=True
    )
    route_destination = serializers.CharField(
        source="route.destination.name",
        read_only=True
    )
    train_name = serializers.CharField(
        source="train.name",
        read_only=True
    )
    crew_full_names = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="full_name"
    )
    tickets_available = serializers.SerializerMethodField()
    crews = CrewSerializer(many=True, read_only=True)

    class Meta:
        model = Journey
        fields = (
            "id",
            "route",
            "route_source",
            "route_destination",
            "train",
            "train_name",
            "departure_time",
            "arrival_time",
            "crews",
            "crew_full_names",
            "tickets_available",
        )

    def get_tickets_available(self, obj):
        return obj.train.capacity - obj.tickets.count()


class JourneyRetrieveSerializer(serializers.ModelSerializer):
    route = RouteSerializer(read_only=True)
    train = TrainSerializer(read_only=True)
    crews = CrewSerializer(many=True, read_only=True)
    taken_seats = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="seat",
        source="tickets"
    )

    class Meta:
        model = Journey
        fields = (
            "id",
            "route",
            "train",
            "crews",
            "departure_time",
            "arrival_time",
            "taken_seats",
        )


class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ("id", "cargo", "seat", "journey", "order")

    def validate(self, attrs):
        Ticket.validate_position(
            attrs["seat"],
            attrs["journey"].train.places_in_cargo,
            field_name="seat",
            error_class=ValidationError
        )
        cargo_obj = attrs["cargo"]
        Ticket.validate_position(
            cargo_obj.number,
            attrs["journey"].train.cargo_num,
            field_name="cargo number",
            error_class=ValidationError
        )
        return attrs


class OrderSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(
        many=True,
        write_only=True,
        allow_empty=False
    )
    tickets_detail = TicketSerializer(
        many=True,
        read_only=True,
        source="tickets"
    )

    class Meta:
        model = Order
        fields = ("id", "created_at", "user", "tickets", "tickets_detail")

    def create(self, validated_data):
        with transaction.atomic():
            tickets_data = validated_data.pop("tickets")
            order = Order.objects.create(**validated_data)
            for ticket_data in tickets_data:
                Ticket.objects.create(order=order, **ticket_data)
            return order


class TicketListSerializer(TicketSerializer):
    journey = JourneyListSerializer(read_only=True)


class OrderListSerializer(OrderSerializer):
    tickets = TicketListSerializer(read_only=True, many=True)
