from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Admin Sistem Pakar Perkembangan Anak"
admin.site.site_title = "Admin Sistem Pakar"
admin.site.index_title = "Kelola basis pengetahuan dan data"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('expert.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
