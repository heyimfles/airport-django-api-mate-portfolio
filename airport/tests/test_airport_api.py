import tempfile
import os

from PIL import Image

from datetime import datetime

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

from airport.models import (
    AirplaneType,
    Airplane,
    Route,
    Airport,
    Flight,
    Crew,
)
from airport.serializers import (
    AirplaneListSerializer,
    CrewListSerializer,
)


AIRPLANE_LIST_URL = reverse("airport:airplane-list")
ORDER_LIST_URL = reverse("airport:order-list")
CREW_LIST_URL = reverse("airport:crew-list")
FLIGHT_LIST_URL = reverse("airport:flight-list")

def sample_airplane(**params):
    if ("airplane_type" in params
        and isinstance(params["airplane_type"], str)
    ):
        airplane_type = AirplaneType.objects.create(name=params["airplane_type"])
    else:
        airplane_type = AirplaneType.objects.create(name="Sample APT")

    params["airplane_type"] = airplane_type

    name = "Sample Airplane"
    if "name" in params:
        name = params["name"]

    defaults = {
        "name": name,
        "rows": 10,
        "seats_in_row": 5,
        "airplane_type": airplane_type,
    }

    defaults.update(params)

    return Airplane.objects.create(**defaults)

def sample_route(**params):
    if (
        "source_city" in params
        and isinstance(params["source_city"], str)
        and "source_ap_name" in params
        and isinstance(params["source_ap_name"], str)
    ):
        source_city = params["source_city"]
        source_ap_name = params["source_ap_name"]
    else:
        source_city = "Sample Source City"
        source_ap_name = "Sample Source Airport"

    if (
        "destination_city" in params
        and isinstance(params["destination_city"], str)
        and "destination_ap_name" in params
        and isinstance(params["destination_ap_name"], str)
    ):
        destination_city = params["destination_city"]
        destination_ap_name = params["destination_ap_name"]
    else:
        destination_city = "Sample Destination City"
        destination_ap_name = "Sample Destination Airport"

    source = Airport.objects.create(
        name=source_ap_name,
        closest_big_city=source_city,
    )
    destination = Airport.objects.create(
        name=destination_ap_name,
        closest_big_city=destination_city,
    )

    to_pop = [
        "source_city",
        "source_ap_name",
        "destination_city",
        "destination_ap_name",
    ]

    for p in to_pop:
        if p in params:
            params.pop(p)

    defaults = {
        "source": source,
        "destination": destination,
        "distance": 100,
    }

    defaults.update(params)
    return Route.objects.create(**defaults)

def sample_flight(**params):
    if (
        "route" in params
        and isinstance(params["route"], Route)
    ):
        route = params["route"]
    else:
        route = sample_route(**params)

    if (
        "airplane" in params
        and isinstance(params["airplane"], Airplane)
    ):
        airplane = params["airplane"]
    else:
        airplane = sample_airplane(**params)

    defaults = {
        "route": route,
        "airplane": airplane,
        "departure_time": datetime.now(),
        "arrival_time": datetime.now(),
    }

    defaults.update(params)
    return Flight.objects.create(**defaults)

def sample_crew(**params):
    defaults = {
        "first_name": "Name",
        "last_name": "Last Name",
    }

    defaults.update(params)
    return Crew.objects.create(**defaults)

def crew_detail_url(crew_member_id):
    return reverse(
        viewname="airport:crew-detail",
        args=[crew_member_id]
    )

def crew_image_upload_url(crew_member_id):
    return reverse(
        "airport:crew-upload-image",
        args=[crew_member_id]
    )


class UnauthenticatedAirportAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    """ everything except flight will have no access. """
    def test_auth_required(self):
        response = self.client.get(AIRPLANE_LIST_URL)
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    """ flight will be read only. """
    def test_read_only(self):
        response = self.client.get(FLIGHT_LIST_URL)
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        payload = {
            "departure_time": datetime.now(),
            "arrival_time": datetime.now()
        }
        response = self.client.post(FLIGHT_LIST_URL, payload)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )


class AuthenticatedAirportAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "test1password",
        )
        self.client.force_authenticate(user=self.user)

    """ everything other than order is read only. """
    def test_read_only_crew(self):
        payload = {
            "first_name": "John",
            "last_name": "Doe",
        }
        response = self.client.post(CREW_LIST_URL, payload)
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN
        )

    """ airplane list viewpoint working. """
    def test_list_airplanes(self):
        sample_airplane(name="AP1", airplane_type="APT1")
        sample_airplane(name="AP2", airplane_type="APT2")

        response = self.client.get(AIRPLANE_LIST_URL)

        airplanes = Airplane.objects.order_by("id")
        serializer = AirplaneListSerializer(
            airplanes,
            many=True
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )
        self.assertEqual(
            response.data,
            serializer.data
        )

    """ filtering by airplane ids. """
    def test_filter_airplanes(self):
        airplane1 = sample_airplane(name="AP1", airplane_type="APT1")
        airplane2 = sample_airplane(name="AP2", airplane_type="APT2")
        airplane3 = sample_airplane(name="AP3", airplane_type="APT3")

        response = self.client.get(
            AIRPLANE_LIST_URL,
            data={"id": f"{airplane1.id}, {airplane2.id}"}
        )

        serializer1 = AirplaneListSerializer(airplane1)
        serializer2 = AirplaneListSerializer(airplane2)
        serializer3 = AirplaneListSerializer(airplane3)

        self.assertIn(serializer1.data, response.data)
        self.assertIn(serializer2.data, response.data)
        self.assertNotIn(serializer3.data, response.data)

    """ filtering by source, destination and time. """
    def test_filter_flights(self):
        route1 = sample_route(
            source_city="Find this source",
            source_ap_name="SAPN1",
            destination_city="Find this destination",
            destination_ap_name="DAPN1"
        )
        route2 = sample_route(
            source_city="SSC2",
            source_ap_name="SAPN2",
            destination_city="Find this destination",
            destination_ap_name="DAPN2"
        )

        airplane = sample_airplane()

        flight1 = sample_flight(route=route1, airplane=airplane)
        flight2 = sample_flight(route=route2, airplane=airplane)

        """ this part is for source and destination. """
        response = self.client.get(
            FLIGHT_LIST_URL,
            data={
                "source": "source",
                "destination": "destination",
            }
        )

        self.assertIn(
            flight1.id,
            [item["id"] for item in response.data["results"]]
        )
        self.assertNotIn(
            flight2.id,
            [item["id"] for item in response.data["results"]]
        )

        """ this part is for destination only. """
        response = self.client.get(
            FLIGHT_LIST_URL,
            data={
                "destination": "destination",
            }
        )

        self.assertIn(
            flight1.id,
            [item["id"] for item in response.data["results"]]
        )
        self.assertIn(
            flight2.id,
            [item["id"] for item in response.data["results"]]
        )

        """ this part is for time"""
        response = self.client.get(
            FLIGHT_LIST_URL,
            data={
                "departure_time": str(datetime.now)
            }
        )

        self.assertIn(
            flight1.id,
            [item["id"] for item in response.data["results"]]
        )

    """ retrieve must work correctly. """
    def test_retrieve_crew(self):
        crew_member = sample_crew()
        url = crew_detail_url(crew_member.id)

        response = self.client.get(url)

        serializer = CrewListSerializer(crew_member)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )
        self.assertEqual(
            response.data,
            serializer.data
        )

    """ creating is forbidden, unless it is order waypoint. """
    def test_create(self):
        payload = {
            "first_name": "John",
            "last_name": "Doe",
        }

        response = self.client.post(CREW_LIST_URL, payload)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN
        )

        """ order creation. """
        flight = sample_flight()

        payload = {
            "user": self.user.id,
            "tickets": [
                {
                    "row": 1,
                    "seat": "A",
                    "flight": flight.id,
                }
            ]
        }

        response = self.client.post(
            ORDER_LIST_URL,
            payload,
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )


class AdminAirportAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com",
            "admin1password",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    """ admin can create new instances. """
    def test_create_airplane(self):
        airplane_type = AirplaneType.objects.create(
            name="Test APT",
        )

        payload = {
            "name": "Test Airplane",
            "rows": 10,
            "seats_in_row": 5,
            "airplane_type": airplane_type.id,
        }

        response = self.client.post(
            AIRPLANE_LIST_URL,
            payload,
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        sample_airplane()
        airplanes = Airplane.objects.all()
        self.assertEqual(airplanes.count(), 2)

    """ admin can upload new images. """
    def test_upload_image_crew(self):
        crew_member = sample_crew()
        url = crew_image_upload_url(crew_member.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as f:
            img = Image.new(mode="RGB", size=(10, 10))
            img.save(f, format="JPEG")
            f.seek(0)
            response = self.client.post(
                url,
                data={
                    "photo": f
                },
                format="multipart"
            )
        crew_member.refresh_from_db()

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )
        self.assertTrue(
            response.data["photo"]
        )
        self.assertTrue(
            os.path.exists(
                crew_member.photo.path
            )
        )

        """ the image should be on detail page """
        response = self.client.get(
            crew_detail_url(crew_member.id)
        )
        self.assertTrue(
            response.data["photo"]
        )

    """ uploading something other than image should not work. """
    def test_upload_image_bad_request(self):
        crew_member = sample_crew()
        url = crew_image_upload_url(crew_member.id)

        response = self.client.post(
            url,
            data={
                "photo": "not photo"
            },
            format="multipart"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )