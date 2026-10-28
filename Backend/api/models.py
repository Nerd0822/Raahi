from django.db import models
from django.contrib.auth.models import AbstractUser


# Create your models here.
class Profile(AbstractUser):
    email = models.EmailField(unique=True)
    birth_date = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to="profiles/", null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)

    def __str__(self):
        return self.username


class Plan(models.Model):
    class Status(models.TextChoices):
        WISHLIST = "wishlist", "Wishlist"
        PLANNED = "planned", "Planned"
        DONE = "done", "Done"

    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="plans")
    title = models.CharField(max_length=200)
    destination = models.CharField(max_length=200)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.WISHLIST
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.destination})"


class PlanItem(models.Model):
    class Category(models.TextChoices):
        PLACE = "place", "Place"
        FOOD = "food", "Food"
        RESTAURANT = "restaurant", "Restaurant"
        TRANSPORT = "transport", "Transport"
        FLIGHT = "flight", "Flight"
        STAY = "stay", "Stay"
        OTHER = "other", "Other"

    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="items")
    category = models.CharField(max_length=20, choices=Category.choices)
    name = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    time = models.DateTimeField(null=True, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.category})"


class PlaceInfo(models.Model):
    """Shared AI-answer cache. One row per destination + category."""

    destination = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=PlanItem.Category.choices)
    data = models.JSONField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["destination", "category"],
                name="unique_destination_category",
            )
        ]

    def __str__(self):
        return f"{self.destination} / {self.category}"
