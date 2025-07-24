# 🤖 WhatsApp Indonesia Document Extractor Bot

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

### Installation

1. **Clone Repository**
```bash
git clone https://github.com/classyid/wa-dokumen-extractor-bot.git
cd whatsapp-indonesia-doc-extractor
```

2. **Install Dependencies**
```bash
pip install asyncio aiohttp requests neonize thundra_io
```

3. **Setup Google Apps Script APIs**
- Deploy Google Apps Script untuk setiap jenis dokumen
- Update URL API di script:
```python
KTP_API_URL = "YOUR_GAS_DEPLOYMENT_URL"
KK_API_URL = "YOUR_GAS_DEPLOYMENT_URL"
IJAZAH_API_URL = "YOUR_GAS_DEPLOYMENT_URL" 
SIM_API_URL = "YOUR_GAS_DEPLOYMENT_URL"
```

4. **Run Bot**
```bash
python main.py
```

## 📱 Cara Penggunaan

### Commands Available

| Command | Fungsi | Contoh |
|---------|--------|---------|
| `ping` | Cek status bot | `ping` |
| `ktp` | Ekstrak data KTP | Reply gambar KTP dengan `ktp` |
| `kk` | Ekstrak data KK | Reply gambar KK dengan `kk` |
| `ijazah` | Ekstrak data Ijazah | Reply gambar Ijazah dengan `ijazah` |
| `sim` | Ekstrak data SIM | Reply gambar SIM dengan `sim` |
| `help` | Bantuan | `help` |

### Step by Step

1. **Kirim gambar dokumen** ke chat WhatsApp
2. **Reply gambar** dengan command yang sesuai (`ktp`, `kk`, `ijazah`, atau `sim`)
3. **Tunggu proses ekstraksi** (biasanya 5-10 detik)
4. **Terima hasil** dalam format yang rapi dengan emoji
5. **Optional**: Minta file export dengan `.txt` atau `.json`

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

- **Backend**: Python 3.7+ dengan asyncio
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

Anda dapat mengganti Google Apps Script dengan OCR service lain:

```python
# Ubah fungsi query_*_extractor sesuai API yang digunakan
async def query_ktp_extractor(media_bytes, mime_type, file_name):
    # Custom OCR implementation
    pass
```

## 🤝 Contributing

Kontribusi sangat welcome! Silakan:

1. Fork repository ini
2. Buat feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push ke branch (`git push origin feature/AmazingFeature`)
5. Buka Pull Request


## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.

## ⚠️ Disclaimer

- Bot ini untuk keperluan legal dan sah
- Penyalahgunaan data pribadi dapat dikenakan sanksi hukum
- Pastikan compliance dengan regulasi perlindungan data

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
