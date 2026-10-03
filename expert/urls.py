from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name="index"),

    # Diagnosis (forward chaining)
    path('diagnosis/', views.diagnosis, name="diagnosis"),

    # Riwayat / hasil diagnosis
    path('riwayat/', views.riwayat_list, name='riwayat_list'),
    path('riwayat/<int:pk>/', views.riwayat_detail, name='riwayat_detail'),
    path('riwayat/<int:pk>/pdf/', views.riwayat_pdf, name="riwayat_pdf"),
    path('riwayat/<int:pk>/hapus/', views.riwayat_hapus, name="riwayat_hapus"),

    # Data anak & perkembangan per anak
    path('anak/', views.anak_list, name='anak_list'),
    path('anak/tambah/', views.anak_tambah, name='anak_tambah'),
    path('anak/<int:pk>/', views.anak_detail, name='anak_detail'),
    path('anak/<int:pk>/ubah/', views.anak_ubah, name='anak_ubah'),
    path('anak/<int:pk>/hapus/', views.anak_hapus, name='anak_hapus'),
    path('anak/<int:pk>/pdf/', views.anak_pdf, name='anak_pdf'),

    # Statistik perkembangan
    path('statistik/', views.statistik, name='statistik'),
    path('statistik/excel/', views.statistik_excel, name='statistik_excel'),

    # Halaman umum
    path('basis-pengetahuan/', views.basis_pengetahuan, name='basis_pengetahuan'),
    path('galeri/', views.galeri, name="galeri"),
    path('kontak/', views.kontak, name='kontak'),

    # Login guru
    path('masuk/', auth_views.LoginView.as_view(template_name='registration/login.html',
                                                redirect_authenticated_user=True), name='masuk'),
    path('keluar/', views.keluar, name='keluar'),
]
