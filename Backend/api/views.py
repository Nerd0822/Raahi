import logging
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation

from PIL import Image, UnidentifiedImageError
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .llm import LLMError, LLMNotConfigured, chat_reply, generate_itinerary
from .models import Plan, PlanItem, Profile
from .serializers import PlanItemSerializer, PlanSerializer

logger = logging.getLogger(__name__)


class EmailOrUsernameObtainSerializer(TokenObtainPairSerializer):
    """Accepts either email or username as the identifier.

    If the identifier matches a stored email, it is remapped to that
    account's username before the default (password-checking) flow runs.
    """

    def validate(self, attrs):
        ident = (attrs.get(self.username_field) or "").strip()
        m = Profile.objects.filter(email__iexact=ident).only("username").first()
        if m:
            attrs[self.username_field] = m.username
        return super().validate(attrs)


@api_view(["GET"])
def home(request):
    return Response({"message": "hello from backend"})


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    email = request.data.get("email", "").strip().lower()
    password = request.data.get("password", "")

    if not email or not password:
        return Response(
            {"email": ["Email and password are required."]},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if Profile.objects.filter(email=email).exists():
        return Response(
            {"email": ["That email is already registered."]},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        validate_password(password)
    except ValidationError as e:
        return Response({"password": e.messages}, status=status.HTTP_400_BAD_REQUEST)

    user = Profile.objects.create_user(email=email, username=email, password=password)
    refresh = RefreshToken.for_user(user)
    return Response(
        {"access": str(refresh.access_token), "refresh": str(refresh)},
        status=status.HTTP_201_CREATED,
    )


def _profile_json(user):
    return {
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "bio": user.bio,
        "birth_date": user.birth_date.isoformat() if user.birth_date else None,
        "date_joined": user.date_joined.isoformat(),
        "profile_picture": user.profile_picture.url if user.profile_picture else None,
    }


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user

    if request.method == "PATCH":
        data = request.data
        if "first_name" in data:
            user.first_name = str(data.get("first_name") or "").strip()[:150]
        if "bio" in data:
            bio = str(data.get("bio") or "").strip()
            if len(bio) > 500:
                return Response(
                    {"bio": ["Keep the bio under 500 characters."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.bio = bio
        if "birth_date" in data:
            raw = str(data.get("birth_date") or "").strip()
            if not raw:
                user.birth_date = None
            else:
                try:
                    user.birth_date = date.fromisoformat(raw)
                except ValueError:
                    return Response(
                        {"birth_date": ["Use the YYYY-MM-DD format."]},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
        picture = request.FILES.get("profile_picture")
        remove_picture = str(
            request.data.get("remove_profile_picture") or ""
        ).lower() in {"1", "true", "on"}
        old_picture = user.profile_picture if user.profile_picture else None
        old_name = old_picture.name if old_picture else ""
        old_storage = old_picture.storage if old_picture else None

        if picture:
            if not (picture.content_type or "").startswith("image/"):
                return Response(
                    {"profile_picture": ["Upload an image file."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if picture.size > 2 * 1024 * 1024:
                return Response(
                    {"profile_picture": ["Image must be under 2 MB."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                with Image.open(picture) as image:
                    image.verify()
            except (UnidentifiedImageError, OSError):
                return Response(
                    {"profile_picture": ["That file is not a readable image."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            picture.seek(0)
            user.profile_picture = picture
        elif remove_picture:
            user.profile_picture = None

        user.save()
        new_name = user.profile_picture.name if user.profile_picture else ""
        if old_storage and old_name and old_name != new_name:
            old_storage.delete(old_name)

    return Response(_profile_json(user))


CATEGORIES = {value for value, _ in PlanItem.Category.choices}


def _clip(value, limit):
    return str(value or "").strip()[:limit]


def _clock(value):
    try:
        return datetime.strptime(_clip(value, 5), "%H:%M").time()
    except ValueError:
        return None


def _cost(value):
    if value in (None, ""):
        return None
    try:
        amount = Decimal(str(value).replace(",", "").replace("₹", "").strip())
    except (InvalidOperation, ValueError):
        return None
    return amount if amount >= 0 else None


def _generated_plan(user, prompt, start_date, data):
    """Validate model output and save it as a Plan with PlanItems.

    Raises LLMError when the payload has no usable days, so the view can turn
    that into a 502 instead of saving an empty trip.
    """
    raw_days = data.get("days")
    if not isinstance(raw_days, list):
        raise LLMError("model returned no days")

    days = []
    for raw_day in raw_days[:14]:
        if not isinstance(raw_day, dict):
            continue
        items = []
        for raw in raw_day.get("items") or []:
            if not isinstance(raw, dict):
                continue
            name = _clip(raw.get("name"), 200)
            if not name:
                continue
            clock = _clock(raw.get("time"))
            items.append(
                {
                    "category": (
                        raw.get("category")
                        if raw.get("category") in CATEGORIES
                        else PlanItem.Category.OTHER
                    ),
                    "name": name,
                    "notes": _clip(raw.get("notes"), 1000),
                    "clock": clock,
                    "time_label": clock.strftime("%H:%M") if clock else "",
                    "cost": _cost(raw.get("cost")),
                }
            )
            if len(items) == 8:
                break
        if items:
            days.append({"title": _clip(raw_day.get("title"), 200), "items": items})

    if not days:
        raise LLMError("model returned no usable stops")

    destination = _clip(data.get("destination"), 200)
    if not destination:
        destination = _clip(prompt.split(",")[0], 200) or "Your trip"
    title = _clip(data.get("title"), 200) or f"Trip to {destination}"
    summary = _clip(data.get("summary"), 1000)
    end_date = start_date + timedelta(days=len(days) - 1) if start_date else None

    with transaction.atomic():
        plan = Plan.objects.create(
            user=user,
            title=title,
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            status=Plan.Status.PLANNED,
            notes=summary,
        )
        PlanItem.objects.bulk_create(
            [
                PlanItem(
                    plan=plan,
                    category=item["category"],
                    name=item["name"],
                    notes=item["notes"],
                    time=(
                        timezone.make_aware(
                            datetime.combine(
                                start_date + timedelta(days=day_number - 1),
                                item["clock"],
                            )
                        )
                        if start_date and item["clock"]
                        else None
                    ),
                    cost=item["cost"],
                    details={
                        "day": day_number,
                        "day_title": day["title"],
                        "time": item["time_label"],
                    },
                )
                for day_number, day in enumerate(days, start=1)
                for item in day["items"]
            ]
        )
    return plan


class PlanViewSet(viewsets.ModelViewSet):
    """A user's trips. Everyone only ever sees their own."""

    serializer_class = PlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Plan.objects.filter(user=self.request.user).order_by("-updated_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["post"])
    def generate(self, request):
        """Turn a free-text request into a saved plan with day-by-day stops."""
        prompt = (request.data.get("prompt") or "").strip()
        if not prompt:
            return Response(
                {"prompt": ["Tell us where you want to go."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(prompt) > 1000:
            return Response(
                {"prompt": ["Keep the request under 1000 characters."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        start = None
        raw_start = request.data.get("start_date")
        if raw_start:
            try:
                start = date.fromisoformat(str(raw_start))
            except ValueError:
                return Response(
                    {"start_date": ["Use the YYYY-MM-DD format."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            itinerary = generate_itinerary(prompt, start.isoformat() if start else "")
            plan = _generated_plan(request.user, prompt, start, itinerary)
        except LLMNotConfigured:
            return Response(
                {"detail": "The AI planner isn't connected yet."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except LLMError as exc:
            # ponytail: one blocking call per plan, no streaming/retries yet.
            logger.warning("LLM itinerary failed: %s", exc)
            return Response(
                {"detail": "The AI planner couldn't finish that trip. Try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            PlanSerializer(plan, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )


class PlanItemViewSet(viewsets.ModelViewSet):
    """Stops inside a trip. `?plan=<id>` narrows the list to one trip."""

    serializer_class = PlanItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = PlanItem.objects.filter(plan__user=self.request.user)
        plan = self.request.query_params.get("plan")
        if plan:
            qs = qs.filter(plan_id=plan)
        return qs.order_by(F("time").asc(nulls_last=True), "created_at")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def chat(request):
    destination = (request.data.get("destination") or "").strip()
    message = (request.data.get("message") or "").strip()
    if not message:
        return Response(
            {"message": ["Type a message first."]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        reply = chat_reply(message, destination)
    except LLMNotConfigured:
        return Response(
            {"detail": "The AI guide isn't connected yet."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except LLMError as exc:
        # ponytail: single blocking HTTP call, no retries/streaming yet; add
        # them when chat latency or provider flakiness becomes a real problem.
        logger.warning("LLM chat failed: %s", exc)
        return Response(
            {"detail": "The AI guide is unavailable right now."},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    return Response({"reply": reply})
