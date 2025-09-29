from django.contrib import admin
from .models import (
    TrainType,
    Train,
    Station,
    Route,
    Journey,
    Crew,
    Ticket,
    Order,
    Cargo,
)


class TicketInline(admin.TabularInline):
    model = Ticket
    extra = 1


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = (TicketInline,)


@admin.register(TrainType)
class TrainTypeAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Train)
class TrainAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "cargo_num", "places_in_cargo", "train_type")
    list_filter = ("train_type",)


@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "latitude", "longitude")
    search_fields = ("name",)


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("id", "source", "destination", "distance")
    list_filter = ("source", "destination")


@admin.register(Journey)
class JourneyAdmin(admin.ModelAdmin):
    list_display = ("id", "route", "train", "departure_time", "arrival_time")
    list_filter = ("train", "route", "departure_time")


@admin.register(Crew)
class CrewAdmin(admin.ModelAdmin):
    list_display = ("id", "first_name", "last_name")
    search_fields = ("first_name", "last_name")


@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    list_display = ("id", "train", "number", "cargo_type")
    list_filter = ("cargo_type", "train")
