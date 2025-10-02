import pathlib
import uuid
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.text import slugify
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.conf import settings


class TrainType(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


def train_image_path(instance: "Train", filename: str) -> pathlib.Path:
    filename = (
        f"{slugify(instance.name)}-{uuid.uuid4()}" + pathlib.Path(filename).suffix
    )
    return pathlib.Path("upload/trains/") / pathlib.Path(filename)


class Train(models.Model):
    name = models.CharField(max_length=255, blank=True, null=True)
    cargo_num = models.IntegerField(validators=[MinValueValidator(1)])
    places_in_cargo = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(160)]
    )
    train_type = models.ForeignKey("TrainType", on_delete=models.CASCADE)
    image = models.ImageField(null=True, upload_to=train_image_path)

    class Meta:
        verbose_name_plural = "trains"
        ordering = ["name"]

    @property
    def capacity(self):
        return self.cargo_num * self.places_in_cargo

    @property
    def is_small(self):
        return self.capacity <= 1000

    def __str__(self):
        return f"{self.name or 'Unnamed train'} (id={self.id})"


class Cargo(models.Model):
    train = models.ForeignKey("Train", on_delete=models.CASCADE, related_name="cargos")
    number = models.PositiveIntegerField()
    cargo_type = models.CharField(max_length=255)

    class Meta:
        unique_together = ("train", "number")
        ordering = ["train", "number"]

    def __str__(self):
        return f"Cargo {self.number} ({self.cargo_type}) of {self.train}"


@receiver([post_save, post_delete], sender=Cargo)
def update_cargo_num(sender, instance, **kwargs):
    train = instance.train
    cargo_count = train.cargos.count()
    if train.cargo_num != cargo_count:
        train.cargo_num = cargo_count
        train.save(update_fields=["cargo_num"])


class Station(models.Model):
    name = models.CharField(max_length=255, unique=True)
    latitude = models.DecimalField(
        max_digits=8, decimal_places=6,
        validators=[MinValueValidator(-90.0), MaxValueValidator(90.0)]
    )

    longitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        validators=[MinValueValidator(-180.0), MaxValueValidator(180.0)]
    )

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return (f"Station: {self.name} (id = {self.id}, "
                f"{self.latitude}, {self.longitude})")


class Route(models.Model):
    source = models.ForeignKey(
        "Station",
        on_delete=models.CASCADE,
        related_name="routes_from"
    )
    destination = models.ForeignKey(
        "Station",
        on_delete=models.CASCADE,
        related_name="routes_to"
    )
    distance = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=~models.Q(source=models.F("destination")),
                name="prevent_same_station"
            ),
            models.UniqueConstraint(
                fields=["source", "destination"],
                name="unique_route"
            )
        ]
        indexes = [
            models.Index(fields=["source", "destination"]),
            models.Index(fields=["distance"]),
        ]

    def __str__(self):
        return f"Route: {self.source} - {self.destination} ({self.distance} km)"


class Crew(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.full_name


class Journey(models.Model):
    route = models.ForeignKey("Route", on_delete=models.CASCADE)
    train = models.ForeignKey("Train", on_delete=models.CASCADE)
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    crews = models.ManyToManyField("Crew", related_name="journeys")

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(arrival_time__gt=models.F("departure_time")),
                name="arrival_after_departure"
            )
        ]
        ordering = ["departure_time"]

    def clean(self):
        if self.arrival_time <= self.departure_time:
            raise ValidationError("Arrival time must be later than departure time.")

    def __str__(self):
        return f"{self.route} | {self.departure_time} → {self.arrival_time}"


class Order(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.id} ({self.user}) at {self.created_at:%Y-%m-%d %H:%M}"


class Ticket(models.Model):
    cargo = models.ForeignKey("Cargo", on_delete=models.CASCADE, related_name="tickets")
    seat = models.IntegerField()
    journey = models.ForeignKey(
        "Journey",
        on_delete=models.CASCADE,
        related_name="tickets"
    )
    order = models.ForeignKey("Order", on_delete=models.CASCADE, related_name="tickets")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["seat", "cargo", "journey"],
                name="unique_ticket_position"
            )
        ]
        ordering = ("cargo", "seat")

    def __str__(self):
        return (f"{self.journey} - "
                f"Cargo {self.cargo.number} ({self.cargo.cargo_type}), "
                f"seat {self.seat}")

    @staticmethod
    def validate_position(value: int, max_value: int, field_name: str, error_class):
        if not (1 <= value <= max_value):
            raise error_class(
                {
                    field_name:
                        f"{field_name} must be in range [1, {max_value}], not {value}"
                }
            )

    def clean(self):
        Ticket.validate_position(
            self.seat, self.journey.train.places_in_cargo, "seat", ValidationError
        )
        Ticket.validate_position(
            self.cargo.number,
            self.journey.train.cargo_num,
            "cargo number", ValidationError
        )

    def save(
        self,
        force_insert=False,
        force_update=False,
        using=None,
        update_fields=None,
    ):
        self.full_clean()
        return super(Ticket, self).save(
            force_insert, force_update, using, update_fields
        )
