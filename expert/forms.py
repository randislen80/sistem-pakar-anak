from django import forms
from django.utils import timezone

from .models import Anak, Indikator, PesanKontak


def _tambah_kelas_bootstrap(form):
    """Memberi kelas Bootstrap pada semua widget agar tampilan seragam."""
    for field in form.fields.values():
        w = field.widget
        if isinstance(w, (forms.CheckboxInput, forms.CheckboxSelectMultiple, forms.RadioSelect)):
            continue
        kelas = "form-select" if isinstance(w, forms.Select) else "form-control"
        w.attrs["class"] = (w.attrs.get("class", "") + " " + kelas).strip()


class TanggalInput(forms.DateInput):
    input_type = "date"

    def __init__(self, attrs=None):
        super().__init__(attrs=attrs, format="%Y-%m-%d")


class AnakForm(forms.ModelForm):
    class Meta:
        model = Anak
        fields = [
            "nama", "nomor_induk", "jenis_kelamin", "tanggal_lahir", "kelompok",
            "nama_orang_tua", "kontak_orang_tua", "catatan", "aktif",
        ]
        labels = {
            "nama": "Nama lengkap anak",
            "nomor_induk": "Nomor induk (opsional)",
            "jenis_kelamin": "Jenis kelamin",
            "tanggal_lahir": "Tanggal lahir",
            "kelompok": "Kelompok",
            "nama_orang_tua": "Nama orang tua/wali",
            "kontak_orang_tua": "No. HP orang tua/wali",
            "catatan": "Catatan",
            "aktif": "Masih aktif bersekolah",
        }
        widgets = {
            "tanggal_lahir": TanggalInput(),
            "catatan": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tanggal_lahir"].required = True
        self.fields["jenis_kelamin"].required = True
        _tambah_kelas_bootstrap(self)
        self.fields["aktif"].widget.attrs["class"] = "form-check-input"

    def clean_nama(self):
        return " ".join(self.cleaned_data["nama"].split())

    def clean_tanggal_lahir(self):
        tgl = self.cleaned_data.get("tanggal_lahir")
        if tgl and tgl > timezone.localdate():
            raise forms.ValidationError("Tanggal lahir tidak boleh melewati hari ini.")
        return tgl


class DiagnosisForm(forms.Form):
    MODE = [("terdaftar", "Anak sudah terdaftar"), ("baru", "Anak baru")]

    mode = forms.ChoiceField(choices=MODE, initial="terdaftar", widget=forms.RadioSelect)
    anak = forms.ModelChoiceField(
        queryset=Anak.objects.filter(aktif=True), required=False,
        empty_label="-- Pilih nama anak --", label="Nama anak",
    )
    nama_baru = forms.CharField(max_length=100, required=False, label="Nama lengkap anak")
    jenis_kelamin_baru = forms.ChoiceField(
        choices=[("", "-- Pilih --")] + Anak.JENIS_KELAMIN, required=False, label="Jenis kelamin")
    tanggal_lahir_baru = forms.DateField(required=False, widget=TanggalInput(), label="Tanggal lahir")
    kelompok_baru = forms.ChoiceField(
        choices=[("", "-- Otomatis dari usia --")] + Anak.KELOMPOK, required=False, label="Kelompok")
    tanggal = forms.DateField(widget=TanggalInput(), label="Tanggal pengamatan")
    indikator = forms.ModelMultipleChoiceField(
        queryset=Indikator.objects.select_related("domain"), required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    catatan = forms.CharField(
        required=False, label="Catatan guru (opsional)",
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Misalnya: anak baru pulih dari sakit, kondisi saat pengamatan, dll."}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tanggal"].initial = timezone.localdate()
        _tambah_kelas_bootstrap(self)

    def clean_nama_baru(self):
        return " ".join((self.cleaned_data.get("nama_baru") or "").split())

    def clean(self):
        data = super().clean()
        hari_ini = timezone.localdate()
        tanggal = data.get("tanggal")
        if tanggal and tanggal > hari_ini:
            self.add_error("tanggal", "Tanggal pengamatan tidak boleh melewati hari ini.")

        if data.get("mode") == "baru":
            if not data.get("nama_baru"):
                self.add_error("nama_baru", "Isi nama anak baru.")
            lahir = data.get("tanggal_lahir_baru")
            if not lahir:
                self.add_error("tanggal_lahir_baru", "Isi tanggal lahir agar usia dapat dihitung.")
            elif lahir > hari_ini:
                self.add_error("tanggal_lahir_baru", "Tanggal lahir tidak boleh melewati hari ini.")
            elif tanggal and lahir > tanggal:
                self.add_error("tanggal_lahir_baru", "Tanggal lahir harus sebelum tanggal pengamatan.")
            if not data.get("jenis_kelamin_baru"):
                self.add_error("jenis_kelamin_baru", "Pilih jenis kelamin.")
        elif not data.get("anak"):
            self.add_error("anak", "Pilih anak yang akan didiagnosis, atau pilih \"Anak baru\".")
        return data


class KontakForm(forms.ModelForm):
    class Meta:
        model = PesanKontak
        fields = ["nama", "email", "handphone", "pesan"]
        labels = {"nama": "Nama", "email": "Email", "handphone": "No. HP", "pesan": "Pesan"}
        widgets = {"pesan": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["pesan"].required = True
        _tambah_kelas_bootstrap(self)

    def clean(self):
        data = super().clean()
        if not data.get("email") and not data.get("handphone"):
            raise forms.ValidationError("Isi email atau nomor HP agar kami dapat membalas pesan Anda.")
        return data
