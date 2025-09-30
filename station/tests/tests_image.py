import tempfile
import os
from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient, APITestCase
from station.models import Train, TrainType, Route, Journey, Station, Cargo


TRAIN_URL = reverse("station:train-list")
JOURNEY_URL = reverse("station:journey-list")


def train_detail_url(train_id):
    return reverse("station:train-detail", args=(train_id,))


def journey_detail_url(journey_id):
    return reverse("station:journey-detail", args=[journey_id])


def sample_train(**params):
    train_type = params.pop("train_type", None)
    if train_type is None:
        train_type = TrainType.objects.create(name=f"Type_{TrainType.objects.count() + 1}")

    defaults = {
        "name": "Test Train",
        "cargo_num": 5,
        "places_in_cargo": 50,
        "train_type": train_type,
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
        train_type = TrainType.objects.create(name=f"Type_{TrainType.objects.count() + 1}")
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

def detail_url(train_id):
    return reverse("station:train-detail", args=[train_id])

class TrainImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.train = sample_train()
        self.station = sample_station()
        self.route = sample_route()
        self.journey = sample_journey(train=self.train, route=self.route)

    def tearDown(self):
        if self.train.image:
            self.train.image.delete()

    def test_upload_image_to_train(self):
        """Test uploading an image to train"""
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
        """Test uploading an invalid image"""
        url = image_upload_url(self.train.id)
        res = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_train_list(self):
        """Test creating a train with an image"""
        url = TRAIN_URL

        train_type_obj = TrainType.objects.create(name="Type")

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)

            res = self.client.post(
                url,
                {
                    "name": "Name",
                    "cargo_num": 10,
                    "places_in_cargo": 50,
                    "train_type": train_type_obj.name,
                    "image": ntf,
                },
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        train = Train.objects.get(name="Name")
        self.assertTrue(train.image)
        self.assertTrue(os.path.exists(train.image.path))

    def test_image_url_is_shown_on_train_detail(self):
        url = image_upload_url(self.train.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(detail_url(self.train.id))

        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_train_list(self):
        url = image_upload_url(self.train.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")

        self.train.refresh_from_db()
        res = self.client.get(TRAIN_URL)

        # Якщо у тебе пагінація DRF, список може бути всередині 'results'
        data = res.data.get('results', res.data)

        self.assertGreater(len(data), 0, "Train list should not be empty")
        self.assertIn("image", data[0])
