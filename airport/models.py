import os
import uuid

from django.core.exceptions import ValidationError
from django.db import models
from string import ascii_uppercase
from django.utils.deconstruct import deconstructible

from django.utils.text import slugify

from user.models import User


@deconstructible
class MediaUrlPath:
    def __init__(self, model_folder, instance_name_field):
        self.model_folder = model_folder
        self.instance_name_field = instance_name_field

    def __call__(self, instance, filename):
        _, ext = os.path.splitext(filename)
        name = getattr(instance, self.instance_name_field)
        new_filename = f"{slugify(name)}-{uuid.uuid4()}{ext}"
        return os.path.join(
            "uploads",
            self.model_folder,
            new_filename
        )


class Airport(models.Model):
    name = models.CharField(max_length=255, unique=True)
    closest_big_city = models.CharField(max_length=255)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Route(models.Model):
    source = models.ForeignKey(
        Airport,
        on_delete=models.CASCADE,
        related_name="routes_source",
    )
    destination = models.ForeignKey(
        Airport,
        on_delete=models.CASCADE,
        related_name="routes_destination",
    )
    distance = models.IntegerField()

    @staticmethod
    def validate_route(source, destination, error_to_raise):
        if source.closest_big_city == destination.closest_big_city:
            raise error_to_raise(
                {
                    f"{source.closest_big_city} - "
                    f"{destination.closest_big_city}: "
                    f"the destination cannot be the same as source"
                }
            )

    def clean(self):
        Route.validate_route(
            self.source,
            self.destination,
            ValidationError
        )

    def save(
        self,
        *args,
        force_insert=False,
        force_update=False,
        using=None,
        update_fields=None,
    ):
        self.full_clean()
        return super(Route, self).save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )

    class Meta:
        ordering = [
            "source",
            "destination"
        ]

    def __str__(self):
        return (
            f"Route from {self.source.name} "
            f"to {self.destination.name}"
        )


class AirplaneType(models.Model):
    name = models.CharField(max_length=255, unique=True)
    image = models.ImageField(
        null=True,
        blank=True,
        upload_to=MediaUrlPath("airplane_type", "name")
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Airplane(models.Model):
    name = models.CharField(max_length=255, unique=True)
    rows = models.IntegerField()
    seats_in_row = models.IntegerField()
    airplane_type = models.ForeignKey(
        AirplaneType,
        on_delete=models.CASCADE,
        related_name="airplanes",
    )

    @property
    def capacity(self):
        return self.rows * self.seats_in_row

    @property
    def seat_letters(self):
        return ascii_uppercase[: self.seats_in_row]

    def __str__(self):
        return (
            f"{self.name} with capacity "
            f"of {self.capacity} seats"
        )


class Order(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="orders",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return str(self.created_at)


class Flight(models.Model):
    route = models.ForeignKey(
        Route,
        on_delete=models.CASCADE,
        related_name="flights",
    )
    airplane = models.ForeignKey(
        Airplane,
        on_delete=models.CASCADE,
        related_name="flights",
    )
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()

    @staticmethod
    def validate_at_later_dt(arrival_time, departure_time, error_to_raise):
        if arrival_time < departure_time:
            raise error_to_raise(
                "arrival_time must be later than departure_time"
            )

    def clean(self):
        Flight.validate_at_later_dt(
            self.arrival_time,
            self.departure_time,
            ValidationError
        )

    def save(
        self,
        *args,
        force_insert=False,
        force_update=False,
        using=None,
        update_fields=None,
    ):
        self.full_clean()
        return super(Flight, self).save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )

    class Meta:
        ordering = [
            "route",
            "-departure_time",
        ]

    def __str__(self):
        return (
            f"{self.route.source.name} - "
            f"{self.route.destination.name} "
            f"({str(self.departure_time)})"
        )


class Crew(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    flight = models.ManyToManyField(
        Flight,
        blank=True,
        related_name="crew"
    )
    photo = models.ImageField(
        null=True,
        blank=True,
        upload_to=MediaUrlPath("crew", "last_name")
    )

    class Meta:
        ordering = ["first_name", "last_name"]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.first_name + " " + self.last_name


class Ticket(models.Model):
    row = models.IntegerField()
    seat = models.CharField(max_length=1)
    flight = models.ForeignKey(
        Flight,
        on_delete=models.CASCADE,
        related_name="tickets",
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="tickets",
    )

    @property
    def row_seat_together(self):
        return f"{self.row}{self.seat}"

    @staticmethod
    def validate_ticket(
            row,
            seat,
            airplane,
            error_to_raise
    ):
        if not 1 <= row <= airplane.rows:
            raise error_to_raise(
                {"row": f"Row must be in range: 1, {airplane.rows}"}
            )
        if seat not in airplane.seat_letters:
            raise error_to_raise(
                {"seat": f"Seat must be one of: {airplane.seat_letters}"}
            )

    def clean(self):
        Ticket.validate_ticket(
            self.row,
            self.seat,
            self.flight.airplane,
            ValidationError
        )

    def save(
            self,
            *args,
            force_insert=False,
            force_update=False,
            using=None,
            update_fields=None,
    ):
        self.full_clean()
        return super(Ticket, self).save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )

    def __str__(self):
        return (
            f"{str(self.flight)} ({self.row}{self.seat})"
        )

    class Meta:
        ordering = ["row", "seat"]
        unique_together = ("row", "seat", "flight")
