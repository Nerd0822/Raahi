from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.routers import DefaultRouter
from django.urls import include, path
from . import views


class LoginView(TokenObtainPairView):
    serializer_class = views.EmailOrUsernameObtainSerializer


router = DefaultRouter()
router.register("plans", views.PlanViewSet, basename="plan")
router.register("plan-items", views.PlanItemViewSet, basename="plan-item")

urlpatterns = [
    path("home/", views.home, name="home"),
    path("auth/login/", LoginView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/register/", views.register, name="register"),
    path("auth/me/", views.me, name="me"),
    path("chat/", views.chat, name="chat"),
    path("", include(router.urls)),
]
