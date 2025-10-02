import tempfile
import os
from PIL import Image
from django.db import IntegrityError
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient, APITestCase
from station.models import Train, TrainType, Route, Journey, Station, Cargo
from station.serializers import (
    TrainListSerializer,
    TrainRetrieveSerializer,
    JourneyListSerializer,
    JourneyRetrieveSerializer,
)

TRAIN_URL = reverse("station:train-list")
JOURNEY_URL = reverse("station:journey-list")


def train_detail_url(train_id):
    return reverse("station:train-detail", args=(train_id,))


def journey_detail_url(journey_id):
    return reverse("station:journey-detail", args=[journey_id])


def sample_train(**params) -> Train:
    defaults = {
        "name": "Podillia",
        "cargo_num": 8,
        "places_in_cargo": 30,
    }
    defaults.update(params)
    return Train.objects.create(**defaults)


def sample_station(name=None, latitude=50.0, longitude=30.0):
    from uuid import uuid4
    if not name:
        name = f"Station_{uuid4().hex[:6]}"
    return Station.objects.create(name=name, latitude=latitude, longitude=longitude)


def sample_route(**params):
    defaults = {
        "source": params.pop("source", sample_station()),
        "destination": params.pop("destination", sample_station()),
        "distance": params.pop("distance", 500)
    }
    defaults.update(params)
    return Route.objects.create(**defaults)


def sample_journey(**params):
    route = params.pop("route", sample_route())
    train = params.pop("train", None)

    if train is None:
        train_type = TrainType.objects.create(
            name=f"Type_{TrainType.objects.count() + 1}"
        )
        train = sample_train(train_type=train_type)

    defaults = {
        "route": route,
        "train": train,
        "departure_time": "2025-01-01T10:00:00Z",
        "arrival_time": "2025-01-01T15:00:00Z",
    }
    defaults.update(params)

    return Journey.objects.create(**defaults)


def image_upload_url(train_id):
    return reverse("station:train-upload-image", args=[train_id])


class TrainImageUploadTests(APITestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_superuser(
            "admin@test.com",
            "password123"
        )
        self.client.force_authenticate(self.admin_user)

        self.train_type = TrainType.objects.create(name="default")
        self.train = Train.objects.create(
            name="Tavria",
            cargo_num=8,
            places_in_cargo=30,
            train_type=self.train_type,
        )

    def tearDown(self):
        if self.train.image:
            if os.path.exists(self.train.image.path):
                os.remove(self.train.image.path)

    def test_upload_image_successful(self):
        url = image_upload_url(self.train.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")

        self.train.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.train.image.path))

    def test_upload_image_bad_request(self):
        url = image_upload_url(self.train.id)
        res = self.client.post(url, {"image": "notimage"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_image_forbidden_for_non_admin(self):
        user = get_user_model().objects.create_user(
            "user@test.com",
            "testpass"
        )
        self.client.force_authenticate(user)
        url = image_upload_url(self.train.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class UnauthenticatedTrainApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(TRAIN_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedTrainApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test", password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_trains_list(self):
        train_type_1 = TrainType.objects.create(name="fast")
        train_type_2 = TrainType.objects.create(name="night")
        sample_train(train_type=train_type_1)
        sample_train(train_type=train_type_2)

        res = self.client.get(TRAIN_URL)
        trains = Train.objects.all().order_by("id")
        serializer = TrainListSerializer(trains, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_filter_trains_by_train_types(self):
        train_type_default = TrainType.objects.create(name="default")
        train_type_1 = TrainType.objects.create(name="fast")
        train_type_2 = TrainType.objects.create(name="night")

        train_without_train_type = sample_train(train_type=train_type_default)
        train_with_train_type_1 = sample_train(name="Podillia", train_type=train_type_1)
        train_with_train_type_2 = sample_train(name="Tavria", train_type=train_type_2)

        res = self.client.get(
            TRAIN_URL, {"train_type": f"{train_type_1.id},{train_type_2.id}"}
        )

        serializer_without_train_type = TrainListSerializer(train_without_train_type)
        serializer_train_type_1 = TrainListSerializer(train_with_train_type_1)
        serializer_train_type_2 = TrainListSerializer(train_with_train_type_2)

        self.assertIn(serializer_train_type_1.data, res.data["results"])
        self.assertIn(serializer_train_type_2.data, res.data["results"])
        self.assertNotIn(serializer_without_train_type.data, res.data["results"])

    def test_retrieve_train_detail(self):
        train_type = TrainType.objects.create(name="fast")
        train = sample_train(train_type=train_type)

        url = train_detail_url(train.id)

        res = self.client.get(url)

        serializer = TrainRetrieveSerializer(train)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_train_forbidden(self):
        payload = {
            "name": "Tavria",
            "cargo_num": 8,
            "places_in_cargo": 30,
            "train_type": "fast"
        }

        res = self.client.post(TRAIN_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_train_invalid_cargo_num(self):
        res = self.client.get(TRAIN_URL, {"cargo_num": "abc"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_train_invalid_places_in_cargo(self):
        res = self.client.get(TRAIN_URL, {"places_in_cargo": "abc"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_journey_list(self):
        train_type_1 = TrainType.objects.create(name="fast")
        train_type_2 = TrainType.objects.create(name="night")

        train_1 = sample_train(name="Tavria", train_type=train_type_1)
        train_2 = sample_train(name="Podillia", train_type=train_type_2)

        route_1 = sample_route()
        route_2 = sample_route()

        sample_journey(route=route_1, train=train_1)
        sample_journey(route=route_2, train=train_2)

        res = self.client.get(JOURNEY_URL)
        journeys = Journey.objects.all().order_by("id")
        serializer = JourneyListSerializer(journeys, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_filter_journeys_by_trains_and_by_routes(self):
        train_type_default = TrainType.objects.create(name="default")
        train_type_1 = TrainType.objects.create(name="fast")
        train_type_2 = TrainType.objects.create(name="night")

        train_default = sample_train(name="default", train_type=train_type_default)
        train_1 = sample_train(name="Tavria", train_type=train_type_1)
        train_2 = sample_train(name="Podillia", train_type=train_type_2)

        route_default = sample_route()
        route_1 = sample_route()
        route_2 = sample_route()

        journey_without_train = sample_journey(route=route_1, train=train_default)
        journey_without_route = sample_journey(route=route_default, train=train_1)
        journey_1 = sample_journey(route=route_1, train=train_1)
        journey_2 = sample_journey(route=route_2, train=train_2)

        res = self.client.get(
            JOURNEY_URL, {
                "train": f"{train_1.id},{train_2.id}",
                "route": f"{route_1.id},{route_2.id}"
            }
        )

        serializer_journey_without_train = JourneyListSerializer(journey_without_train)
        serializer_journey_without_route = JourneyListSerializer(journey_without_route)
        serializer_journey_1 = JourneyListSerializer(journey_1)
        serializer_journey_2 = JourneyListSerializer(journey_2)

        self.assertIn(serializer_journey_1.data, res.data["results"])
        self.assertIn(serializer_journey_2.data, res.data["results"])
        self.assertNotIn(serializer_journey_without_train.data, res.data["results"])
        self.assertNotIn(serializer_journey_without_route.data, res.data["results"])

    def test_retrieve_journey_detail(self):
        train_type = TrainType.objects.create(name="default")

        route = sample_route()
        train = sample_train(train_type=train_type)
        journey = sample_journey(route=route, train=train)

        url = journey_detail_url(journey.id)
        res = self.client.get(url)

        serializer = JourneyRetrieveSerializer(journey)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_journey_forbidden(self):
        train_type = TrainType.objects.create(name="default")
        route = sample_route()
        train = sample_train(train_type=train_type)

        payload = {
            "route": route.id,
            "train": train.id,
            "departure_time": "2025-01-01T10:00:00Z",
            "arrival_time": "2025-01-01T15:00:00Z",
        }

        res = self.client.post(JOURNEY_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminTrainTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.test",
            password="testpassword",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_train(self):
        TrainType.objects.create(name="fast")
        payload = {
            "name": "Tavria",
            "cargo_num": 8,
            "places_in_cargo": 30,
            "train_type": "fast"
        }

        res = self.client.post(TRAIN_URL, payload)

        train = Train.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(train.train_type.name, payload["train_type"])

        for key in ["name", "cargo_num", "places_in_cargo"]:
            self.assertEqual(payload[key], getattr(train, key))

    def test_delete_train_not_allowed(self):
        train_type_default = TrainType.objects.create(name="default")
        train = sample_train(train_type=train_type_default)
        url = train_detail_url(train.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_create_journey(self):
        train_type = TrainType.objects.create(name="default")
        route = sample_route()
        train = sample_train(train_type=train_type)

        payload = {
            "route": route.id,
            "train": train.id,
            "departure_time": "2025-01-01T10:00:00Z",
            "arrival_time": "2025-01-01T15:00:00Z",
        }

        res = self.client.post(JOURNEY_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        journey = Journey.objects.get(id=res.data["id"])

        self.assertEqual(journey.route.id, payload["route"])
        self.assertEqual(journey.train.id, payload["train"])
        self.assertEqual(
            journey.departure_time.isoformat().replace("+00:00", "Z"),
            payload["departure_time"]
        )
        self.assertEqual(
            journey.arrival_time.isoformat().replace("+00:00", "Z"),
            payload["arrival_time"]
        )

    def test_delete_journey_not_allowed(self):
        train_type_default = TrainType.objects.create(name="default")
        train = sample_train(train_type=train_type_default)
        route_default = sample_route()
        journey = sample_journey(route=route_default, train=train)
        url = journey_detail_url(journey.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class CargoModelTests(TestCase):
    def setUp(self):
        self.train_type = TrainType.objects.create(name="fast")
        self.train = Train.objects.create(
            name="Tavria",
            cargo_num=0,
            places_in_cargo=50,
            train_type=self.train_type,
        )

    def test_create_cargo_with_type(self):
        cargo = Cargo.objects.create(train=self.train, number=1, cargo_type="coal")
        self.assertEqual(cargo.cargo_type, "coal")
        self.assertEqual(cargo.train, self.train)

    def test_cargo_num_auto_update_on_create_and_delete(self):
        Cargo.objects.create(train=self.train, number=1, cargo_type="coal")
        Cargo.objects.create(train=self.train, number=2, cargo_type="wood")

        self.train.refresh_from_db()
        self.assertEqual(self.train.cargo_num, 2)

        Cargo.objects.get(number=1, train=self.train).delete()
        self.train.refresh_from_db()
        self.assertEqual(self.train.cargo_num, 1)

    def test_unique_cargo_number_per_train(self):
        Cargo.objects.create(train=self.train, number=1, cargo_type="coal")
        with self.assertRaises(IntegrityError):
            Cargo.objects.create(train=self.train, number=1, cargo_type="wood")
