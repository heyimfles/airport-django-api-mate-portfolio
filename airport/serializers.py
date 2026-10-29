from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueTogetherValidator

from airport.models import (
    Airport,
    Route,
    AirplaneType,
    Airplane,
    Order,
    Flight,
    Crew,
    Ticket
)


class AirportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airport
        fields = (
            "id",
            "name",
            "closest_big_city"
        )


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = (
            "id",
            "source",
            "destination",
            "distance"
        )

    def validate(self, attrs):
        Route.validate_route(
            attrs["source"],
            attrs["destination"],
            serializers.ValidationError
        )
        return attrs


class RouteListSerializer(RouteSerializer):
    source_city = serializers.CharField(
        source="source.closest_big_city",
        read_only=True
    )
    destination_city = serializers.CharField(
        source="destination.closest_big_city",
        read_only=True
    )

    class Meta:
        model = Route
        fields = (
            "id",
            "source_city",
            "destination_city",
            "distance",
        )


class RouteDetailSerializer(RouteSerializer):
    source = AirportSerializer(many=False, read_only=True)
    destination = AirportSerializer(many=False, read_only=True)

    class Meta:
        model = Route
        fields = (
            "id",
            "source",
            "destination",
            "distance",
        )


class AirplaneTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AirplaneType
        fields = (
            "id",
            "name",
            "image",
        )


class AirplaneTypeImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AirplaneType
        fields = (
            "id",
            "image"
        )


class AirplaneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airplane
        fields = (
            "id",
            "name",
            "rows",
            "seats_in_row",
            "airplane_type",
        )


class AirplaneListSerializer(AirplaneSerializer):
    airplane_type = AirplaneTypeSerializer(
        many=False,
        read_only=False
    )

    class Meta:
        model = Airplane
        fields = (
            "id",
            "name",
            "rows",
            "seats_in_row",
            "seat_letters",
            "capacity",
            "airplane_type",
        )


class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = (
            "id",
            "row_seat_together",
            "flight",
        )
        validators = [
            UniqueTogetherValidator(
                queryset=Ticket.objects.all(),
                fields=["row", "seat", "flight"]
            )
        ]

    def validate(self, attrs):
        data = super(TicketSerializer, self).validate(attrs)
        Ticket.validate_ticket(
            attrs["row"],
            attrs["seat"],
            attrs["flight"].airplane,
            serializers.ValidationError
        )
        return data


class FlightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flight
        fields = (
            "id",
            "route",
            "airplane",
            "departure_time",
            "arrival_time",
        )


class FlightListSerializer(FlightSerializer):
    source = serializers.CharField(
        source="route.source.closest_big_city",
        read_only=True
    )
    destination = serializers.CharField(
        source="route.destination.closest_big_city",
        read_only=True
    )
    airplane_name = serializers.CharField(
        source="airplane.name",
        read_only=True
    )
    capacity = serializers.IntegerField(
        source="airplane.capacity",
        read_only=True
    )
    available_seats = serializers.IntegerField(
        read_only=True
    )

    class Meta:
        model = Flight
        fields = (
            "id",
            "source",
            "destination",
            "airplane_name",
            "departure_time",
            "arrival_time",
            "capacity",
            "available_seats",
        )


class FlightDetailSerializer(FlightSerializer):
    route = RouteListSerializer(
        read_only=True,
    )
    airplane = AirplaneListSerializer(
        read_only=True,
    )
    taken_seats = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="row_seat_together",
        source="tickets",
    )

    class Meta:
        model = Flight
        fields = (
            "id",
            "route",
            "airplane",
            "taken_seats",
            "departure_time",
            "arrival_time",
        )


class OrderSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(
        many=True,
        read_only=False,
        allow_empty=False,
    )

    class Meta:
        model = Order
        fields = (
            "id",
            "created_at",
            "tickets",
        )

    def create(self, validated_data):
        with transaction.atomic():
            tickets_data = validated_data.pop("tickets")
            order = Order.objects.create(**validated_data)

            for ticket_data in tickets_data:

                Ticket.objects.create(order=order, **ticket_data)

            return order


class TicketListSerializer(TicketSerializer):
    flight = FlightListSerializer(
        read_only=True
    )


class OrderListSerializer(OrderSerializer):
    tickets = TicketListSerializer(
        read_only=True,
        many=True,
    )


class CrewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crew
        fields = (
            "id",
            "first_name",
            "last_name",
            "flight",
            "photo",
        )


class CrewListSerializer(CrewSerializer):
    flight = FlightListSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = Crew
        fields = (
            "id",
            "full_name",
            "flight",
            "photo",
        )


class CrewImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crew
        fields = (
            "id",
            "photo",
        )
