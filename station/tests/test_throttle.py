from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.test import override_settings
from station.views import JourneyViewSet, TrainViewSet
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

TRAIN_URL = "/api/station/trains/"
JOURNEY_URL = "/api/station/journeys/"

@override_settings(REST_FRAMEWORK={
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"anon": "10/min", "user": "30/min"},
})
class ThrottlingTests(APITestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="testuser@example.com",
            password="testpassword"
        )

    def reset_throttles(self):
        AnonRateThrottle().cache.clear()
        UserRateThrottle().cache.clear()

    def test_train_anonymous_throttle(self):
        """Anonymous users: 10 requests/min"""
        self.reset_throttles()

        original_permissions = TrainViewSet.permission_classes
        TrainViewSet.permission_classes = [AllowAny]

        try:
            for _ in range(10):
                res = self.client.get(TRAIN_URL)
                self.assertEqual(res.status_code, status.HTTP_200_OK)

            res = self.client.get(TRAIN_URL)
            self.assertEqual(res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        finally:
            TrainViewSet.permission_classes = original_permissions

    def test_journey_anonymous_throttle(self):
        """Anonymous users: 10 requests/min"""
        self.reset_throttles()

        original_permissions = JourneyViewSet.permission_classes
        JourneyViewSet.permission_classes = [AllowAny]

        try:
            for _ in range(10):
                res = self.client.get(JOURNEY_URL)
                self.assertEqual(res.status_code, status.HTTP_200_OK)

            res = self.client.get(JOURNEY_URL)
            self.assertEqual(res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        finally:
            JourneyViewSet.permission_classes = original_permissions

    def test_train_authenticated_throttle(self):
        """Authenticated users: 30 requests/min"""
        self.reset_throttles()
        self.client.force_authenticate(self.user)

        for _ in range(30):
            res = self.client.get(TRAIN_URL)
            self.assertEqual(res.status_code, status.HTTP_200_OK)

        res = self.client.get(TRAIN_URL)
        self.assertEqual(res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


    def test_journey_authenticated_throttle(self):
        """Authenticated users: 30 requests/min"""
        self.reset_throttles()
        self.client.force_authenticate(self.user)

        for _ in range(30):
            res = self.client.get(JOURNEY_URL)
            self.assertEqual(res.status_code, status.HTTP_200_OK)

        res = self.client.get(JOURNEY_URL)
        self.assertEqual(res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
