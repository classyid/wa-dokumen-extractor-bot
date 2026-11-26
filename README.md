readme = """# 🤖 WhatsApp Indonesia Document Extractor Bot

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.7+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/WhatsApp-API-green.svg" alt="WhatsApp API">
  <img src="https://img.shields.io/badge/OCR-Google%20Apps%20Script-yellow.svg" alt="OCR Engine">
  <img src="https://img.shields.io/badge/License-MIT-red.svg" alt="License">
</p>

Bot WhatsApp pintar yang dapat mengekstrak data dari dokumen resmi Indonesia secara otomatis menggunakan teknologi OCR. Mendukung KTP, Kartu Keluarga, Ijazah, dan SIM dengan akurasi tinggi.

## ✨ Fitur Utama

- 🆔 **Ekstraksi KTP**: NIK, nama, alamat, dll
- 👨‍👩‍👧‍👦 **Ekstraksi Kartu Keluarga**: Data lengkap anggota keluarga
- 🎓 **Ekstraksi Ijazah**: Informasi pendidikan dan institusi
- 🚗 **Ekstraksi SIM**: Data pengemudi dan kendaraan
- 📄 **Export Files**: Hasil dalam format TXT dan JSON
- 🎨 **Rich Formatting**: Output cantik dengan emoji
- ⚡ **Real-time**: Proses dalam hitungan detik
- 🔒 **Privacy First**: Data tidak disimpan permanen

## 🚀 Quick Start

### Prerequisites

- Python 3.10+ recommended (check compatibility with the versions of Neonize and other dependencies you install)
- Git
- WhatsApp account for pairing the bot
- Google Apps Script deployments for the supported document types

### Installation

1. **Clone repository**
   ```bash
   git clone https://github.com/classyid/wa-dokumen-extractor-bot.git
   cd wa-dokumen-extractor-bot
   ```

2. **Create and activate a virtual environment**

   Windows:
   ```bash
   py -m venv .venv
   .venv\\Scripts\\activate
   ```

   macOS/Linux:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   python -m pip install --upgrade pip
   python -m pip install asyncio aiohttp requests neonize thundra_io
   ```

4. **Configure Google Apps Script APIs**

   Deploy Google Apps Script for each supported document type and update the API URLs in the project:
   ```python
   KTP_API_URL = "YOUR_GAS_DEPLOYMENT_URL"
   KK_API_URL = "YOUR_GAS_DEPLOYMENT_URL"
   IJAZAH_API_URL = "YOUR_GAS_DEPLOYMENT_URL"
   SIM_API_URL = "YOUR_GAS_DEPLOYMENT_URL"
   ```

   Replace each placeholder with the corresponding deployment URL. Do not commit real credentials, private deployment tokens, or personal document data.

5. **Run the bot**
   ```bash
   python main.py
   ```

### Troubleshooting installation

- If `cd` fails, make sure you enter the directory created by the clone command: `wa-dokumen-extractor-bot`.
- If installation fails, check your Python version and the dependency's compatibility requirements.
- Run commands from the activated virtual environment to avoid installing packages into a different Python environment.

## 📱 Cara Penggunaan

### Commands Available

| Command | Fungsi | Contoh |
|---------|--------|--------|
| `ping` | Cek status bot | `ping` |
| `ktp` | Ekstrak data KTP | Reply gambar KTP dengan `ktp` |
| `kk` | Ekstrak data KK | Reply gambar KK dengan `kk` |
| `ijazah` | Ekstrak data Ijazah | Reply gambar Ijazah dengan `ijazah` |
| `sim` | Ekstrak data SIM | Reply gambar SIM dengan `sim` |
| `help` | Bantuan | `help` |

### Step by Step

1. Kirim gambar dokumen ke chat WhatsApp.
2. Reply gambar dengan command yang sesuai (`ktp`, `kk`, `ijazah`, atau `sim`).
3. Tunggu proses ekstraksi.
4. Terima hasil dalam format yang rapi.
5. Optional: minta file export dengan `.txt` atau `.json`.

### Contoh Output KTP

```
🆔 HASIL EKSTRAKSI KTP 🆔
━━━━━━━━━━━━━━━━━━━━━━

📌 NIK: `3201234567890123`
👤 Nama: John Doe
🎂 TTL: Jakarta, 01-01-1990
⚧️ Jenis Kelamin: LAKI-LAKI
🩸 Golongan Darah: O

📍 DOMISILI 📍
🏠 Alamat: JL. Contoh No. 123
🏘️ RT/RW: 001/002
🏙️ Kel/Desa: Kelurahan Contoh
🌆 Kecamatan: Kecamatan Contoh

...
```

## 🏗️ Arsitektur

```
WhatsApp Message → Bot Detection → Media Download → OCR Processing → Data Formatting → Response
```

### Tech Stack

- **Backend**: Python dengan asyncio
- **WhatsApp API**: Neonize framework
- **OCR Engine**: Google Apps Script
- **Database**: SQLite untuk session management
- **Media Processing**: thundra_io + multiple fallback methods

## 🔧 Konfigurasi Lanjutan

### Environment Variables

```bash
# Optional configurations
LOG_LEVEL=DEBUG
TEMP_MEDIA_DIR=temp_media
DB_PATH=db.sqlite3
```

### Custom API Endpoints

Anda dapat mengganti Google Apps Script dengan OCR service lain dengan menyesuaikan fungsi `query_*_extractor` di source code.

## 🤝 Contributing

Kontribusi sangat welcome! Silakan:

1. Fork repository ini.
2. Buat feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit perubahan (`git commit -m 'Add some AmazingFeature'`).
4. Push ke branch fork Anda (`git push origin feature/AmazingFeature`).
5. Buka Pull Request.

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.

## ⚠️ Disclaimer

- Bot ini untuk keperluan legal dan sah.
- Penyalahgunaan data pribadi dapat dikenakan sanksi hukum.
- Pastikan compliance dengan regulasi perlindungan data.

## 🆘 Support

- 📧 **Email**: kontak@classy.id

## 🙏 Acknowledgments

- [Neonize](https://github.com/krypton-byte/neonize) - WhatsApp Web API framework
- [Thundra.io](https://github.com/thundra-io) - Media handling utilities
- Google Apps Script - OCR processing engine
- Indonesian Government - Document format standards

---

<p align="center">
  Made with ❤️ for Indonesian developers
</p>

<p align="center">
  <a href="#top">Back to top ⬆️</a>
</p>
"""
path = "/mnt/data/README_contribution.md"
with open(path, "w", encoding="utf-8") as f:
    f.write(readme)
print(path)
