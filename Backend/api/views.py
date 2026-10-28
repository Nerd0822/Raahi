from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import F
from datetime import date
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Plan, PlanItem, Profile
from .serializers import PlanItemSerializer, PlanSerializer


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
            user.profile_picture = picture
        user.save()

    return Response(_profile_json(user))


class PlanViewSet(viewsets.ModelViewSet):
    """A user's trips. Everyone only ever sees their own."""

    serializer_class = PlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Plan.objects.filter(user=self.request.user).order_by("-updated_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


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
    # ponytail: canned demo replies — swap this for the real AI service call
    # (check the PlaceInfo cache first, then hit the model) when it's wired.
    destination = (request.data.get("destination") or "your trip").strip()
    message = (request.data.get("message") or "").strip()
    reply = (
        f"Demo guide: noted '{message}' for {destination}. "
        "Real AI answers arrive here once the model is plugged in."
    )
    return Response({"reply": reply})
