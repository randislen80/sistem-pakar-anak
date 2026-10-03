# Migrasi perluasan sistem: data anak, kode basis pengetahuan,
# status rekomendasi, dan informasi tambahan pada riwayat diagnosa.

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


STATUS_CHOICES = [
    ('sesuai', 'Sesuai'),
    ('perlu perhatian', 'Perlu Perhatian'),
    ('terlambat', 'Terlambat'),
    ('belum terlihat', 'Belum Terlihat'),
]


class Migration(migrations.Migration):

    dependencies = [
        ('expert', '0004_pesankontak'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # --- Domain perkembangan -------------------------------------------
        migrations.AlterModelOptions(
            name='domainperkembangan',
            options={
                'ordering': ['urutan', 'id'],
                'verbose_name': 'domain perkembangan',
                'verbose_name_plural': 'domain perkembangan',
            },
        ),
        migrations.AddField(
            model_name='domainperkembangan',
            name='kode',
            field=models.CharField(blank=True, help_text='Contoh: D01', max_length=10),
        ),
        migrations.AddField(
            model_name='domainperkembangan',
            name='deskripsi',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='domainperkembangan',
            name='urutan',
            field=models.PositiveSmallIntegerField(default=0),
        ),

        # --- Indikator -------------------------------------------------------
        migrations.AlterModelOptions(
            name='indikator',
            options={
                'ordering': ['domain__urutan', 'domain_id', 'urutan', 'id'],
                'verbose_name': 'indikator',
                'verbose_name_plural': 'indikator',
            },
        ),
        migrations.AddField(
            model_name='indikator',
            name='kode',
            field=models.CharField(blank=True, help_text='Contoh: G01', max_length=10),
        ),
        migrations.AddField(
            model_name='indikator',
            name='urutan',
            field=models.PositiveSmallIntegerField(default=0),
        ),

        # --- Rekomendasi -----------------------------------------------------
        migrations.AlterModelOptions(
            name='rekomendasi',
            options={
                'ordering': ['domain__urutan', 'domain_id', 'status', 'id'],
                'verbose_name': 'rekomendasi',
                'verbose_name_plural': 'rekomendasi',
            },
        ),
        migrations.AddField(
            model_name='rekomendasi',
            name='status',
            field=models.CharField(
                blank=True, choices=STATUS_CHOICES,
                help_text='Kosongkan agar berlaku untuk semua status yang belum Sesuai.',
                max_length=20,
            ),
        ),

        # --- Data anak -------------------------------------------------------
        migrations.CreateModel(
            name='Anak',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nama', models.CharField(max_length=100)),
                ('nomor_induk', models.CharField(blank=True, max_length=30)),
                ('jenis_kelamin', models.CharField(blank=True, choices=[('L', 'Laki-laki'), ('P', 'Perempuan')], max_length=1)),
                ('tanggal_lahir', models.DateField(blank=True, null=True)),
                ('kelompok', models.CharField(blank=True, choices=[('A', 'Kelompok A (4-5 tahun)'), ('B', 'Kelompok B (5-6 tahun)')], max_length=1)),
                ('nama_orang_tua', models.CharField(blank=True, max_length=100)),
                ('kontak_orang_tua', models.CharField(blank=True, max_length=30)),
                ('catatan', models.TextField(blank=True)),
                ('aktif', models.BooleanField(default=True, help_text='Hilangkan centang jika anak sudah lulus atau pindah.')),
                ('dibuat', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['nama'],
                'verbose_name': 'anak',
                'verbose_name_plural': 'data anak',
            },
        ),

        # --- Riwayat diagnosa ------------------------------------------------
        migrations.AlterModelOptions(
            name='riwayatdiagnosa',
            options={
                'ordering': ['-tanggal', '-id'],
                'verbose_name': 'riwayat diagnosa',
                'verbose_name_plural': 'riwayat diagnosa',
            },
        ),
        migrations.AddField(
            model_name='riwayatdiagnosa',
            name='anak',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name='riwayat', to='expert.anak',
            ),
        ),
        migrations.AlterField(
            model_name='riwayatdiagnosa',
            name='usia',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='riwayatdiagnosa',
            name='usia_bulan',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='riwayatdiagnosa',
            name='tanggal',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='riwayatdiagnosa',
            name='indikator_terpilih',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='riwayatdiagnosa',
            name='jejak',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='riwayatdiagnosa',
            name='kesimpulan',
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AddField(
            model_name='riwayatdiagnosa',
            name='rata_rata',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='riwayatdiagnosa',
            name='catatan',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='riwayatdiagnosa',
            name='pemeriksa',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='diagnosa', to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
