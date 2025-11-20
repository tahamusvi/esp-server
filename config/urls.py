from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularJSONAPIView,
)
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    path("monitor/", include("monitor.urls")),
    path("api-schema", SpectacularAPIView.as_view(), name="schema"),
    path("api-schema-json", SpectacularJSONAPIView.as_view(), name="schema"),
    path("", SpectacularSwaggerView.as_view(url_name="schema")),
    path("api-auth/", include("rest_framework.urls")),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),


]



if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
