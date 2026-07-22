from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from backend import urls as backend_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include((backend_urls.accounts_patterns, 'accounts'))),
    path('', include((backend_urls.dashboard_patterns, 'dashboard'))),
    path('inventory/', include((backend_urls.core_patterns, 'core'))),
    path('ops/', include((backend_urls.operations_patterns, 'operations'))),
    path('records/', include('records.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
