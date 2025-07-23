import asyncio
import logging
import os
import sys
import traceback
import base64
import json
import aiohttp
import requests
import tempfile
from neonize.aioze.client import ClientFactory, NewAClient
from neonize.events import (
    ConnectedEv,
    MessageEv,
)
from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import Message
from neonize.utils import log

# Tambahkan import dari thundra_io
from thundra_io.utils import get_message_type, get_user_id
from thundra_io.types import MediaMessageType
from thundra_io.storage.file import File

sys.path.insert(0, os.getcwd())

# Konfigurasi logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
log.setLevel(logging.DEBUG)

# API Extractor configurations
KTP_API_URL = "https://github.com/classyid/ktp-extraction-api"  # Ganti dengan ID_DEPLOYMENT yang sesuai
KK_API_URL = "https://github.com/classyid/kk-extractor-api"  # Ganti dengan ID_DEPLOYMENT yang sesuai
IJAZAH_API_URL = "https://github.com/classyid/ijazah-extractor-api"  # Ganti dengan ID_DEPLOYMENT yang sesuai
SIM_API_URL = "https://github.com/classyid/sim-extractor-api"  # Ganti dengan ID_DEPLOYMENT yang sesuai


# Setup client
client_factory = ClientFactory("db.sqlite3")
os.makedirs("temp_media", exist_ok=True)

# Load existing sessions
sessions = client_factory.get_all_devices()
for device in sessions:
    client_factory.new_client(device.JID)

# Helper function untuk mendapatkan pesan yang dikutip dan jenisnya
async def get_quoted_message_info(message):
    has_quoted = False
    quoted_message = None
    quoted_type = None
    
    try:
        # Check untuk extended text message
        if (hasattr(message.Message, 'extendedTextMessage') and 
            hasattr(message.Message.extendedTextMessage, 'contextInfo') and
            hasattr(message.Message.extendedTextMessage.contextInfo, 'quotedMessage')):
            
            quoted_message = message.Message.extendedTextMessage.contextInfo.quotedMessage
            has_quoted = True
            
            # Coba gunakan thundra_io untuk deteksi tipe
            try:
                msg_type = get_message_type(quoted_message)
                if isinstance(msg_type, MediaMessageType):
                    quoted_type = msg_type.__class__.__name__.lower().replace('message', '')
                    log.info(f"Detected quoted {quoted_type} message using thundra_io")
            except Exception as e:
                log.error(f"Error using thundra_io for type detection: {e}")
            
            # Fallback ke metode deteksi lama jika thundra_io gagal
            if not quoted_type:
                if hasattr(quoted_message, 'videoMessage'):
                    quoted_type = "video"
                    log.info("Detected quoted video message")
                elif hasattr(quoted_message, 'audioMessage'):
                    quoted_type = "audio"
                    log.info("Detected quoted audio message")
                elif hasattr(quoted_message, 'imageMessage'):
                    quoted_type = "image"
                    log.info("Detected quoted image message")
                elif hasattr(quoted_message, 'documentMessage'):
                    quoted_type = "document"
                    log.info("Detected quoted document message")
                else:
                    log.info("Unknown quoted message type")
                    # Log atribut
                    for attr in dir(quoted_message):
                        if not attr.startswith('_'):
                            log.info(f"Quoted message has attribute: {attr}")
    
    except Exception as e:
        log.error(f"Error in get_quoted_message_info: {e}")
        log.error(traceback.format_exc())
    
    return has_quoted, quoted_message, quoted_type

# Fungsi download langsung dari URL jika tersedia
async def download_from_url(url):
    try:
        log.info(f"Downloading from URL: {url}")
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            log.info(f"Successfully downloaded {len(response.content)} bytes from URL")
            return response.content
        else:
            log.error(f"Failed to download from URL: status code {response.status_code}")
            return None
    except Exception as e:
        log.error(f"Error downloading from URL: {e}")
        log.error(traceback.format_exc())
        return None

# Fungsi untuk mengunduh media (image)
async def download_media(client, quoted_message, quoted_type):
    try:
        log.info(f"Starting download process for {quoted_type}")
        
        # Hanya fokus pada image untuk Extractor
        if quoted_type != "image":
            log.info(f"Media type {quoted_type} not supported for extraction, only images are supported")
            return None, None, None
            
        # Metode 1: Coba menggunakan thundra_io
        try:
            log.info("Trying thundra_io approach for image")
            msg_type = get_message_type(quoted_message)
            
            if isinstance(msg_type, MediaMessageType):
                # Buat File object dari message
                file_obj = File.from_message(msg_type)
                
                # Jika file_obj memiliki method get_content, gunakan
                if hasattr(file_obj, 'get_content') and callable(file_obj.get_content):
                    media_bytes = file_obj.get_content()
                    
                    # Set default extension dan mime_type
                    extension = ".jpg"
                    mime_type = "image/jpeg"
                    
                    # Coba dapatkan mime_type dari file_obj jika ada
                    if hasattr(file_obj, 'mime_type'):
                        mime_type = file_obj.mime_type
                    
                    # Coba dapatkan extension dari file_obj jika ada
                    if hasattr(file_obj, 'get_extension') and callable(file_obj.get_extension):
                        ext = file_obj.get_extension()
                        if ext:
                            extension = ext
                    
                    if media_bytes and len(media_bytes) > 0:
                        temp_path = f"temp_media/image_thundra_{os.urandom(4).hex()}{extension}"
                        with open(temp_path, 'wb') as f:
                            f.write(media_bytes)
                        log.info(f"Successfully downloaded image using thundra_io: {len(media_bytes)} bytes")
                        return media_bytes, mime_type, temp_path
                else:
                    log.warning("thundra_io File object doesn't have get_content method")
            else:
                log.warning("thundra_io did not detect a media message type")
        except Exception as e:
            log.error(f"Error in thundra_io approach: {e}")
            log.error(traceback.format_exc())
        
        # Metode 2: Gunakan metode standar
        media_obj = None
        message = Message()
        mime_type = None
        extension = None
        
        if hasattr(quoted_message, 'imageMessage'):
            media_obj = quoted_message.imageMessage
            message.imageMessage.CopyFrom(media_obj)
            mime_type = getattr(media_obj, 'mimetype', "image/jpeg")
            extension = ".jpg"
        else:
            log.error("Image message attribute not found")
            return None, None, None

        # Debug: Print all attributes of media_obj
        log.info("Media object attributes for image:")
        for attr in dir(media_obj):
            if not attr.startswith('_'):
                try:
                    val = getattr(media_obj, attr)
                    log.info(f"{attr}: {val}")
                except Exception as e:
                    log.info(f"{attr}: Error retrieving value - {e}")

        # Metode 2a: Gunakan download_any
        try:
            log.info("Trying download_any for image")
            media_bytes = await client.download_any(message)
            
            if media_bytes and len(media_bytes) > 0:
                temp_path = f"temp_media/image_{os.urandom(4).hex()}{extension}"
                with open(temp_path, 'wb') as f:
                    f.write(media_bytes)
                log.info(f"Successfully downloaded image using download_any: {len(media_bytes)} bytes")
                return media_bytes, mime_type, temp_path
            else:
                log.warning("download_any returned empty data for image")
        except Exception as e:
            log.error(f"Error in download_any: {e}")
            log.error(traceback.format_exc())

        # Metode 2b: Coba melalui URL langsung
        url = None
        if hasattr(media_obj, 'URL'):
            url = media_obj.URL
        elif hasattr(media_obj, 'url'):
            url = media_obj.url
        
        if url:
            log.info("Trying URL download for image")
            media_bytes = await download_from_url(url)
            if media_bytes and len(media_bytes) > 0:
                temp_path = f"temp_media/image_url_{os.urandom(4).hex()}{extension}"
                with open(temp_path, 'wb') as f:
                    f.write(media_bytes)
                log.info(f"Successfully downloaded image from URL: {len(media_bytes)} bytes")
                return media_bytes, mime_type, temp_path
            else:
                log.warning("URL download returned empty data for image")

        # Metode 3: Khusus untuk gambar, coba ekstrak dari thumbnail
        if hasattr(media_obj, 'JPEGThumbnail') and media_obj.JPEGThumbnail:
            log.info("Trying to extract image from JPEGThumbnail")
            thumbnail_bytes = media_obj.JPEGThumbnail
            temp_path = f"temp_media/image_thumbnail_{os.urandom(4).hex()}.jpg"
            with open(temp_path, 'wb') as f:
                f.write(thumbnail_bytes)
            log.info(f"Successfully extracted thumbnail: {len(thumbnail_bytes)} bytes")
            return thumbnail_bytes, "image/jpeg", temp_path

        log.error("All download methods failed for image")
        return None, None, None

    except Exception as e:
        log.error(f"Error in download_media: {e}")
        log.error(traceback.format_exc())
        return None, None, None

# Fungsi untuk mengirim gambar KTP ke API Extractor
async def query_ktp_extractor(media_bytes, mime_type, file_name):
    try:
        log.info(f"Sending image to KTP Extractor API, type: {mime_type}, size: {len(media_bytes)} bytes")
        
        # Encode media as base64
        media_b64 = base64.b64encode(media_bytes).decode('utf-8')
        
        # Prepare payload
        payload = {
            "action": "process-ktp",
            "fileData": media_b64,
            "fileName": file_name,
            "mimeType": mime_type
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        log.info("Sending request to KTP Extractor API...")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(KTP_API_URL, json=payload, headers=headers) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    try:
                        response_json = json.loads(response_text)
                        log.info("Successfully got response from KTP Extractor API")
                        return response_json
                    except json.JSONDecodeError as e:
                        log.error(f"Error parsing JSON response: {e}")
                        return {"status": "error", "message": f"Error parsing JSON response: {str(e)}", "code": 500}
                else:
                    log.error(f"KTP Extractor API error: {response_text}")
                    return {"status": "error", "message": f"Error dari KTP Extractor API: Status {response.status}.", "code": response.status}
    except Exception as e:
        log.error(f"Exception in query_ktp_extractor: {e}")
        log.error(traceback.format_exc())
        return {"status": "error", "message": f"Error: {str(e)}", "code": 500}

# Fungsi untuk mengirim gambar KK ke API Extractor
async def query_kk_extractor(media_bytes, mime_type, file_name):
    try:
        log.info(f"Sending image to KK Extractor API, type: {mime_type}, size: {len(media_bytes)} bytes")
        
        # Encode media as base64
        media_b64 = base64.b64encode(media_bytes).decode('utf-8')
        
        # Prepare payload
        payload = {
            "action": "process-kk",
            "fileData": media_b64,
            "fileName": file_name,
            "mimeType": mime_type
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        log.info("Sending request to KK Extractor API...")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(KK_API_URL, json=payload, headers=headers) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    try:
                        response_json = json.loads(response_text)
                        log.info("Successfully got response from KK Extractor API")
                        return response_json
                    except json.JSONDecodeError as e:
                        log.error(f"Error parsing JSON response: {e}")
                        return {"status": "error", "message": f"Error parsing JSON response: {str(e)}", "code": 500}
                else:
                    log.error(f"KK Extractor API error: {response_text}")
                    return {"status": "error", "message": f"Error dari KK Extractor API: Status {response.status}.", "code": response.status}
    except Exception as e:
        log.error(f"Exception in query_kk_extractor: {e}")
        log.error(traceback.format_exc())
        return {"status": "error", "message": f"Error: {str(e)}", "code": 500}

# Fungsi untuk memformat data KTP untuk ditampilkan di WhatsApp
def format_ktp_response(response):
    try:
        if response["status"] == "error":
            return f"❌ Error: {response['message']} (Code: {response['code']})"
            
        if response["status"] == "success":
            data = response["data"]
            analysis = data["analysis"]
            parsed = analysis["parsed"]
            
            if parsed["status"] == "not_ktp":
                return "❌ Dokumen yang dikirim bukan merupakan KTP."
                
            if parsed["status"] == "success":
                result = (
                    "🆔 *HASIL EKSTRAKSI KTP* 🆔\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"📌 *NIK:* `{parsed.get('nik', 'Tidak terdeteksi')}`\n"
                    f"👤 *Nama:* {parsed.get('nama', 'Tidak terdeteksi')}\n"
                    f"🎂 *TTL:* {parsed.get('tempat_tanggal_lahir', 'Tidak terdeteksi')}\n"
                    f"⚧️ *Jenis Kelamin:* {parsed.get('jenis_kelamin', 'Tidak terdeteksi')}\n"
                    f"🩸 *Golongan Darah:* {parsed.get('golongan_darah', 'Tidak terdeteksi')}\n\n"
                    "📍 *DOMISILI* 📍\n"
                    f"🏠 *Alamat:* {parsed.get('alamat', 'Tidak terdeteksi')}\n"
                    f"🏘️ *RT/RW:* {parsed.get('rt_rw', 'Tidak terdeteksi')}\n"
                    f"🏙️ *Kel/Desa:* {parsed.get('kel_desa', 'Tidak terdeteksi')}\n"
                    f"🌆 *Kecamatan:* {parsed.get('kecamatan', 'Tidak terdeteksi')}\n\n"
                    "ℹ️ *INFORMASI LAINNYA* ℹ️\n"
                    f"🕌 *Agama:* {parsed.get('agama', 'Tidak terdeteksi')}\n"
                    f"💍 *Status Perkawinan:* {parsed.get('status_perkawinan', 'Tidak terdeteksi')}\n"
                    f"💼 *Pekerjaan:* {parsed.get('pekerjaan', 'Tidak terdeteksi')}\n"
                    f"🌐 *Kewarganegaraan:* {parsed.get('kewarganegaraan', 'Tidak terdeteksi')}\n"
                    f"⏱️ *Berlaku Hingga:* {parsed.get('berlaku_hingga', 'Tidak terdeteksi')}\n"
                    f"📅 *Dikeluarkan di:* {parsed.get('dikeluarkan_di', 'Tidak terdeteksi')}\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "⚠️ *PERHATIAN:* _Gunakan informasi ini hanya untuk keperluan yang sah dan legal. Penyalahgunaan data pribadi dapat dikenakan sanksi hukum._"
                )
                return result
                
        return "❌ Format respons tidak dikenal"
    except Exception as e:
        log.error(f"Error formatting KTP response: {e}")
        log.error(traceback.format_exc())
        return f"❌ Error saat memformat respons: {str(e)}"


# Fungsi untuk memformat data KK untuk ditampilkan di WhatsApp
def format_kk_response(response):
    try:
        if response["status"] == "error":
            return f"❌ Error: {response['message']} (Code: {response['code']})"
            
        if response["status"] == "success":
            data = response["data"]
            analysis = data["analysis"]
            parsed = analysis["parsed"]
            
            if parsed["status"] == "not_kk":
                return "❌ Dokumen yang dikirim bukan merupakan Kartu Keluarga."
                
            if parsed["status"] == "success":
                # Format data kepala keluarga
                kepala_keluarga = parsed.get('kepala_keluarga', {})
                
                result = (
                    "👨‍👩‍👧‍👦 *HASIL EKSTRAKSI KARTU KELUARGA* 👨‍👩‍👧‍👦\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"📝 *Nomor KK:* `{parsed.get('nomor_kk', 'Tidak terdeteksi')}`\n"
                    f"🔢 *Kode Keluarga:* {parsed.get('kode_keluarga', 'Tidak terdeteksi')}\n\n"
                    "👑 *DATA KEPALA KELUARGA* 👑\n"
                    f"👤 *Nama:* {kepala_keluarga.get('nama', 'Tidak terdeteksi')}\n"
                    f"🆔 *NIK:* `{kepala_keluarga.get('nik', 'Tidak terdeteksi')}`\n"
                    f"📍 *Alamat:* {kepala_keluarga.get('alamat', 'Tidak terdeteksi')}\n"
                    f"🏘️ *RT/RW:* {kepala_keluarga.get('rt_rw', 'Tidak terdeteksi')}\n"
                    f"🏙️ *Desa/Kelurahan:* {kepala_keluarga.get('desa_kelurahan', 'Tidak terdeteksi')}\n"
                    f"🌆 *Kecamatan:* {kepala_keluarga.get('kecamatan', 'Tidak terdeteksi')}\n"
                    f"🏢 *Kabupaten/Kota:* {kepala_keluarga.get('kabupaten_kota', 'Tidak terdeteksi')}\n"
                    f"📮 *Kode Pos:* {kepala_keluarga.get('kode_pos', 'Tidak terdeteksi')}\n"
                    f"🌏 *Provinsi:* {kepala_keluarga.get('provinsi', 'Tidak terdeteksi')}\n"
                )
                
                # Format data anggota keluarga
                anggota_keluarga = parsed.get('anggota_keluarga', [])
                if anggota_keluarga:
                    result += "\n👨‍👩‍👧‍👦 *ANGGOTA KELUARGA* 👨‍👩‍👧‍👦\n"
                    for i, anggota in enumerate(anggota_keluarga, 1):
                        # Tentukan emoji untuk hubungan keluarga
                        status_hubungan = next((s for s in parsed.get('status_hubungan', []) if s.get('nama') == anggota.get('nama')), {})
                        hubungan = status_hubungan.get('hubungan_keluarga', '').lower() if status_hubungan else ''
                        
                        emoji = "👤"
                        if "kepala" in hubungan:
                            emoji = "👨‍💼" if anggota.get('jenis_kelamin', '').lower() == "laki-laki" else "👩‍💼"
                        elif "suami" in hubungan:
                            emoji = "👨"
                        elif "istri" in hubungan:
                            emoji = "👩"
                        elif "anak" in hubungan:
                            emoji = "👦" if anggota.get('jenis_kelamin', '').lower() == "laki-laki" else "👧"
                        
                        result += (
                            f"{emoji} *{i}. {anggota.get('nama', 'Tidak terdeteksi')}*\n"
                            f"   🆔 NIK: `{anggota.get('nik', 'Tidak terdeteksi')}`\n"
                            f"   ⚧️ Jenis Kelamin: {anggota.get('jenis_kelamin', 'Tidak terdeteksi')}\n"
                            f"   🎂 TTL: {anggota.get('tempat_lahir', 'Tidak terdeteksi')}, {anggota.get('tanggal_lahir', 'Tidak terdeteksi')}\n"
                            f"   🕌 Agama: {anggota.get('agama', 'Tidak terdeteksi')}\n"
                            f"   🎓 Pendidikan: {anggota.get('pendidikan', 'Tidak terdeteksi')}\n"
                            f"   💼 Pekerjaan: {anggota.get('pekerjaan', 'Tidak terdeteksi')}\n"
                        )
                            
                        # Tambahkan info status hubungan
                        if status_hubungan:
                            result += (
                                f"   💍 Status Pernikahan: {status_hubungan.get('status_pernikahan', 'Tidak terdeteksi')}\n"
                                f"   👨‍👩‍👧‍👦 Hubungan Keluarga: {status_hubungan.get('hubungan_keluarga', 'Tidak terdeteksi')}\n"
                                f"   🌐 Kewarganegaraan: {status_hubungan.get('kewarganegaraan', 'Tidak terdeteksi')}\n"
                            )
                            
                        # Tambahkan info orang tua
                        orang_tua = next((o for o in parsed.get('orang_tua', []) if o.get('nama') == anggota.get('nama')), {})
                        if orang_tua:
                            result += (
                                f"   👨‍👩 Orang Tua:\n"
                                f"   ┣ 👨 Ayah: {orang_tua.get('ayah', 'Tidak terdeteksi')}\n"
                                f"   ┗ 👩 Ibu: {orang_tua.get('ibu', 'Tidak terdeteksi')}\n"
                            )
                            
                        if i < len(anggota_keluarga):
                            result += "\n"
                else:
                    result += "\n👥 *Anggota Keluarga:* Tidak terdeteksi\n"
                
                # Tambahkan tanggal penerbitan
                if parsed.get('tanggal_penerbitan'):
                    result += f"\n📅 *Tanggal Penerbitan:* {parsed.get('tanggal_penerbitan')}\n"
                
                # Tambahkan catatan penting
                result += (
                    "\n━━━━━━━━━━━━━━━━━━━━━━\n"
                    "⚠️ *PERHATIAN:* _Gunakan informasi ini hanya untuk keperluan yang sah dan legal. Penyalahgunaan data pribadi dapat dikenakan sanksi hukum._"
                )
                
                return result
                
        return "❌ Format respons tidak dikenal"
    except Exception as e:
        log.error(f"Error formatting KK response: {e}")
        log.error(traceback.format_exc())
        return f"❌ Error saat memformat respons: {str(e)}"


# Fungsi untuk mengirim gambar Ijazah ke API Extractor
async def query_ijazah_extractor(media_bytes, mime_type, file_name):
    try:
        log.info(f"Sending image to Ijazah Extractor API, type: {mime_type}, size: {len(media_bytes)} bytes")
        
        # Encode media as base64
        media_b64 = base64.b64encode(media_bytes).decode('utf-8')
        
        # Prepare payload
        payload = {
            "action": "process-ijazah",
            "fileData": media_b64,
            "fileName": file_name,
            "mimeType": mime_type
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        log.info("Sending request to Ijazah Extractor API...")
        log.info(f"API URL: {IJAZAH_API_URL}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(IJAZAH_API_URL, json=payload, headers=headers) as response:
                response_text = await response.text()
                
                # Log the raw response for debugging
                log.info(f"Raw response status: {response.status}")
                log.info(f"Raw response headers: {response.headers}")
                # Log first 500 chars of response text to avoid flooding logs
                log.info(f"Raw response text (first 500 chars): {response_text[:500]}")
                
                if response.status == 200:
                    try:
                        response_json = json.loads(response_text)
                        log.info("Successfully got response from Ijazah Extractor API")
                        return response_json
                    except json.JSONDecodeError as e:
                        log.error(f"Error parsing JSON response: {e}")
                        log.error(f"Response text: {response_text}")
                        return {"status": "error", "message": f"Error parsing JSON response: {str(e)}", "code": 500}
                else:
                    log.error(f"Ijazah Extractor API error: {response_text}")
                    return {"status": "error", "message": f"Error dari Ijazah Extractor API: Status {response.status}.", "code": response.status}
    except Exception as e:
        log.error(f"Exception in query_ijazah_extractor: {e}")
        log.error(traceback.format_exc())
        return {"status": "error", "message": f"Error: {str(e)}", "code": 500}
        
        
# Fungsi untuk memformat data Ijazah untuk ditampilkan di WhatsApp
def format_ijazah_response(response):
    try:
        if response["status"] == "error":
            return f"❌ Error: {response['message']} (Code: {response['code']})"
            
        if response["status"] == "success":
            data = response["data"]
            analysis = data["analysis"]
            parsed = analysis["parsed"]
            
            if parsed["status"] == "not_ijazah":
                return "❌ Dokumen yang dikirim bukan merupakan Ijazah pendidikan."
                
            if parsed["status"] == "success":
                # Tentukan emoji berdasarkan jenis ijazah
                jenis_ijazah = parsed.get('jenis_ijazah', '').upper()
                ijazah_emoji = "🎓"
                
                if "SD" in jenis_ijazah:
                    ijazah_emoji = "🏫"
                elif "SMP" in jenis_ijazah:
                    ijazah_emoji = "🏫"
                elif "SMA" in jenis_ijazah or "SMK" in jenis_ijazah:
                    ijazah_emoji = "🏫"
                elif "D" in jenis_ijazah:
                    ijazah_emoji = "🎓"
                elif "S1" in jenis_ijazah:
                    ijazah_emoji = "🎓"
                elif "S2" in jenis_ijazah:
                    ijazah_emoji = "🎓"
                elif "S3" in jenis_ijazah:
                    ijazah_emoji = "🎓"
                
                result = (
                    f"{ijazah_emoji} *HASIL EKSTRAKSI IJAZAH* {ijazah_emoji}\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"🏆 *Jenis Ijazah:* {parsed.get('jenis_ijazah', 'Tidak terdeteksi')}\n"
                    f"🏛️ *Kementerian Penerbit:* {parsed.get('kementerian_penerbit', 'Tidak terdeteksi')}\n\n"
                    "🏫 *INSTITUSI PENDIDIKAN* 🏫\n"
                    f"📍 *Nama Institusi:* {parsed.get('nama_institusi', 'Tidak terdeteksi')}\n"
                    f"📊 *Akreditasi:* {parsed.get('akreditasi', 'Tidak terdeteksi')}\n"
                    f"🎯 *Program Studi/Jurusan:* {parsed.get('program_studi_jurusan', 'Tidak terdeteksi')}\n"
                    f"🏛️ *Institusi Asal:* {parsed.get('institusi_asal', 'Tidak terdeteksi')}\n\n"
                    "👤 *INFORMASI PEMILIK* 👤\n"
                    f"📝 *Nama Peserta Didik:* {parsed.get('nama_peserta_didik', 'Tidak terdeteksi')}\n"
                    f"🎂 *TTL:* {parsed.get('tempat_tanggal_lahir', 'Tidak terdeteksi')}\n"
                    f"👨‍👩‍👧‍👦 *Nama Orang Tua:* {parsed.get('nama_orang_tua', 'Tidak terdeteksi')}\n"
                    f"🔢 *Nomor Induk:* {parsed.get('nomor_induk', 'Tidak terdeteksi')}\n\n"
                    "📑 *INFORMASI DOKUMEN* 📑\n"
                    f"📅 *Tanggal Penerbitan:* {parsed.get('tanggal_penerbitan', 'Tidak terdeteksi')}\n"
                    f"✒️ *Pejabat Pengesah:* {parsed.get('pejabat_pengesah', 'Tidak terdeteksi')}\n"
                    f"🆔 *Nomor Identitas Pejabat:* {parsed.get('nomor_identitas_pejabat', 'Tidak terdeteksi')}\n"
                    f"📊 *Nomor Seri:* {parsed.get('nomor_seri', 'Tidak terdeteksi')}\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "⚠️ *PERHATIAN:* _Gunakan informasi ini hanya untuk keperluan yang sah dan legal. Penyalahgunaan data dapat dikenakan sanksi hukum._"
                )
                return result
                
        return "❌ Format respons tidak dikenal"
    except Exception as e:
        log.error(f"Error formatting Ijazah response: {e}")
        log.error(traceback.format_exc())
        return f"❌ Error saat memformat respons: {str(e)}"
        
# Fungsi untuk mengirim gambar SIM ke API Extractor
async def query_sim_extractor(media_bytes, mime_type, file_name):
    try:
        log.info(f"Sending image to SIM Extractor API, type: {mime_type}, size: {len(media_bytes)} bytes")
        
        # Encode media as base64
        media_b64 = base64.b64encode(media_bytes).decode('utf-8')
        
        # Prepare payload
        payload = {
            "action": "process-sim",
            "fileData": media_b64,
            "fileName": file_name,
            "mimeType": mime_type
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        log.info("Sending request to SIM Extractor API...")
        log.info(f"API URL: {SIM_API_URL}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(SIM_API_URL, json=payload, headers=headers) as response:
                response_text = await response.text()
                
                # Log the raw response for debugging
                log.info(f"Raw response status: {response.status}")
                log.info(f"Raw response headers: {response.headers}")
                # Log first 500 chars of response text to avoid flooding logs
                log.info(f"Raw response text (first 500 chars): {response_text[:500]}")
                
                if response.status == 200:
                    try:
                        response_json = json.loads(response_text)
                        log.info("Successfully got response from SIM Extractor API")
                        return response_json
                    except json.JSONDecodeError as e:
                        log.error(f"Error parsing JSON response: {e}")
                        log.error(f"Response text: {response_text}")
                        return {"status": "error", "message": f"Error parsing JSON response: {str(e)}", "code": 500}
                else:
                    log.error(f"SIM Extractor API error: {response_text}")
                    return {"status": "error", "message": f"Error dari SIM Extractor API: Status {response.status}.", "code": response.status}
    except Exception as e:
        log.error(f"Exception in query_sim_extractor: {e}")
        log.error(traceback.format_exc())
        return {"status": "error", "message": f"Error: {str(e)}", "code": 500}

async def handle_document_extraction(client, chat, has_quoted, quoted_message, quoted_type, doc_type, file_format, text):
    """
    Menangani ekstraksi dokumen dengan opsi format file
    
    Args:
        client: NewAClient instance
        chat: Chat ID
        has_quoted: Boolean apakah pesan memiliki quote
        quoted_message: Message yang dikutip
        quoted_type: Tipe pesan yang dikutip
        doc_type: Tipe dokumen (ktp, kk, ijazah, sim)
        file_format: Format file untuk hasil (txt, json, atau None untuk tanpa file)
        text: Teks pesan asli
    """
    if not has_quoted or quoted_type != "image":
        await client.send_message(chat, f"❌ Silakan reply pesan gambar {doc_type.upper()} dengan perintah '{text}'")
        return
        
    await client.send_message(chat, f"📷 Mengunduh gambar {doc_type.upper()}...")
    
    try:
        # Download gambar
        media_bytes, mime_type, temp_path = await download_media(client, quoted_message, quoted_type)
        
        if not media_bytes:
            await client.send_message(chat, "❌ Gagal mengunduh gambar")
            return
            
        # Kirim ke API ekstraksi sesuai jenis dokumen
        await client.send_message(chat, f"🔍 Mengekstrak data {doc_type.upper()}...")
        
        file_name = os.path.basename(temp_path)
        
        if doc_type.lower() == 'ktp':
            response = await query_ktp_extractor(media_bytes, mime_type, file_name)
            formatted_response = format_ktp_response(response)
        elif doc_type.lower() == 'kk':
            response = await query_kk_extractor(media_bytes, mime_type, file_name)
            formatted_response = format_kk_response(response)
        elif doc_type.lower() == 'ijazah':
            response = await query_ijazah_extractor(media_bytes, mime_type, file_name)
            formatted_response = format_ijazah_response(response)
        elif doc_type.lower() == 'sim':
            response = await query_sim_extractor(media_bytes, mime_type, file_name)
            formatted_response = format_sim_response(response)
        else:
            await client.send_message(chat, f"❌ Tipe dokumen '{doc_type}' tidak dikenal")
            return
        
        # Kirim hasil ekstraksi dalam format chatting
        await client.send_message(chat, formatted_response)
        
        # Jika diminta format file, buat dan kirim filenya
        if file_format:
            await create_and_send_extraction_file(client, chat, response, doc_type, file_format)
            
    except Exception as e:
        log.error(f"Error in {doc_type} extraction: {e}")
        log.error(traceback.format_exc())
        await client.send_message(chat, f"❌ Error saat memproses {doc_type.upper()}: {str(e)}")


# Fungsi untuk memformat data SIM untuk ditampilkan di WhatsApp
def format_sim_response(response):
    try:
        if response["status"] == "error":
            return f"❌ Error: {response['message']} (Code: {response['code']})"
            
        if response["status"] == "success":
            data = response["data"]
            analysis = data["analysis"]
            parsed = analysis["parsed"]
            
            if parsed["status"] == "not_sim":
                return "❌ Dokumen yang dikirim bukan merupakan Surat Izin Mengemudi (SIM)."
                
            if parsed["status"] == "success":
                # Tentukan emoji untuk golongan SIM
                golongan_sim = parsed.get('golongan_sim', 'X')
                sim_emoji = "🚘"
                
                if "A" in golongan_sim:
                    sim_emoji = "🚗"  # Mobil penumpang
                elif "B" in golongan_sim:
                    sim_emoji = "🚐"  # Mobil barang/orang
                elif "C" in golongan_sim:
                    sim_emoji = "🏍️"  # Motor
                elif "D" in golongan_sim:
                    sim_emoji = "🚜"  # Traktor
                
                result = (
                    f"{sim_emoji} *HASIL EKSTRAKSI SIM* {sim_emoji}\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"🎫 *Nomor SIM:* `{parsed.get('nomor_sim', 'Tidak terdeteksi')}`\n"
                    f"🚦 *Golongan SIM:* {parsed.get('golongan_sim', 'Tidak terdeteksi')}\n\n"
                    "👤 *DATA PEMILIK* 👤\n"
                    f"📝 *Nama:* {parsed.get('nama', 'Tidak terdeteksi')}\n"
                    f"🎂 *TTL:* {parsed.get('tempat_tanggal_lahir', 'Tidak terdeteksi')}\n"
                    f"⚧️ *Jenis Kelamin:* {parsed.get('jenis_kelamin', 'Tidak terdeteksi')}\n"
                    f"🩸 *Golongan Darah:* {parsed.get('golongan_darah', 'Tidak terdeteksi')}\n"
                    f"📏 *Tinggi:* {parsed.get('tinggi', 'Tidak terdeteksi')}\n"
                    f"💼 *Pekerjaan:* {parsed.get('pekerjaan', 'Tidak terdeteksi')}\n\n"
                    "📍 *ALAMAT* 📍\n"
                    f"🏠 *Alamat:* {parsed.get('alamat', 'Tidak terdeteksi')}\n"
                    f"🏘️ *RT/RW:* {parsed.get('rt_rw', 'Tidak terdeteksi')}\n"
                )
                
                # Tambahkan desa/kelurahan jika ada
                if parsed.get('desa_kelurahan'):
                    result += f"🏙️ *Desa/Kelurahan:* {parsed.get('desa_kelurahan')}\n"
                
                # Tambahkan kecamatan jika ada
                if parsed.get('kecamatan'):
                    result += f"🌆 *Kecamatan:* {parsed.get('kecamatan')}\n"
                
                # Tambahkan kota jika ada
                if parsed.get('kota'):
                    result += f"🏢 *Kota:* {parsed.get('kota')}\n"
                    
                # Informasi dokumen
                result += (
                    f"\n📄 *INFORMASI DOKUMEN* 📄\n"
                    f"⏱️ *Berlaku Hingga:* {parsed.get('berlaku_hingga', 'Tidak terdeteksi')}\n"
                    f"📍 *Dikeluarkan di:* {parsed.get('dikeluarkan_di', 'Tidak terdeteksi')}\n"
                )
                
                # Tambahkan instansi penerbit jika ada
                if parsed.get('instansi_penerbit'):
                    result += f"🏛️ *Instansi Penerbit:* {parsed.get('instansi_penerbit')}\n"
                
                # Tambahkan peringatan
                result += (
                    "\n━━━━━━━━━━━━━━━━━━━━━━\n"
                    "⚠️ *PERHATIAN:* _Gunakan informasi ini hanya untuk keperluan yang sah dan legal. Penyalahgunaan data pribadi dapat dikenakan sanksi hukum._"
                )
                
                return result
                
        return "❌ Format respons tidak dikenal"
    except Exception as e:
        log.error(f"Error formatting SIM response: {e}")
        log.error(traceback.format_exc())
        return f"❌ Error saat memformat respons: {str(e)}"

# Fungsi utilitas untuk membuat file hasil ekstraksi dan mengirimkannya (dengan nama sesuai pemilik)

# Fungsi utilitas untuk membuat file hasil ekstraksi (dengan perbaikan nama file)

async def create_and_send_extraction_file(client, chat, data, doc_type, format_type):
    """
    Membuat file hasil ekstraksi dalam format txt atau json dan mengirimkannya
    dengan nama file yang menyertakan nama pemilik dokumen
    
    Args:
        client: NewAClient instance
        chat: Chat ID tujuan
        data: Data hasil ekstraksi yang akan disimpan ke file
        doc_type: Jenis dokumen (ktp, kk, ijazah, sim)
        format_type: Format file yang diinginkan (txt atau json)
    """
    try:
        # Siapkan timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Default nama jika tidak ditemukan
        owner_name = "Untitled"
        
        # PERBAIKAN: Cek dan dapatkan nama pemilik dokumen dengan lebih teliti
        if isinstance(data, dict) and "data" in data and "analysis" in data["data"] and "parsed" in data["data"]["analysis"]:
            parsed_data = data["data"]["analysis"]["parsed"]
            
            # Pastikan status success dan cek nama berdasarkan jenis dokumen
            if parsed_data.get("status") == "success":
                if doc_type.lower() == "ktp" and "nama" in parsed_data:
                    owner_name = parsed_data["nama"]
                    log.info(f"Extracted KTP owner name: {owner_name}")
                    
                elif doc_type.lower() == "kk" and "kepala_keluarga" in parsed_data:
                    if isinstance(parsed_data["kepala_keluarga"], dict) and "nama" in parsed_data["kepala_keluarga"]:
                        owner_name = parsed_data["kepala_keluarga"]["nama"]
                        log.info(f"Extracted KK owner name: {owner_name}")
                    
                elif doc_type.lower() == "ijazah" and "nama_peserta_didik" in parsed_data:
                    owner_name = parsed_data["nama_peserta_didik"]
                    log.info(f"Extracted Ijazah owner name: {owner_name}")
                    
                elif doc_type.lower() == "sim" and "nama" in parsed_data:
                    owner_name = parsed_data["nama"]
                    log.info(f"Extracted SIM owner name: {owner_name}")
        
        # Bersihkan nama untuk digunakan dalam nama file (hapus karakter tidak valid)
        import re
        clean_name = re.sub(r'[\\/*?:"<>|]', "", owner_name).strip()
        clean_name = clean_name.replace(' ', '_')
        
        # PERBAIKAN: Logging lebih detail untuk debugging nama file
        log.info(f"Original owner name: {owner_name}")
        log.info(f"Cleaned name for filename: {clean_name}")
        
        # Jika nama kosong setelah dibersihkan, gunakan "Untitled"
        if not clean_name:
            clean_name = "Untitled"
            log.info("Using 'Untitled' as name is empty after cleaning")
        
        if format_type.lower() == 'json':
            # Buat konten file JSON
            import json
            
            # Pastikan kita memiliki data yang benar untuk JSON
            if isinstance(data, dict) and "data" in data and "analysis" in data["data"] and "parsed" in data["data"]["analysis"]:
                # Ambil hanya bagian parsed dari data untuk file JSON
                json_data = data["data"]["analysis"]["parsed"]
                
                # PERBAIKAN: Pastikan nama file menggunakan clean_name
                file_path = f"temp_media/{doc_type}_{clean_name}_{timestamp}.json"
                log.info(f"Creating JSON file: {file_path}")
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)
                
                # Kirim file
                caption = f"Hasil ekstraksi {doc_type.upper()} - {owner_name} (JSON)"
                await client.send_document(chat, file_path, caption)
                
                # Beri tahu pengguna
                await client.send_message(chat, f"✅ File JSON hasil ekstraksi {doc_type.upper()} untuk {owner_name} telah dikirim.")
                return True
            else:
                await client.send_message(chat, "❌ Format data tidak valid untuk konversi ke JSON.")
                return False
                
        elif format_type.lower() == 'txt':
            # Buat konten file TXT
            # Gunakan fungsi format yang sudah ada untuk membuat konten yang rapi
            
            if doc_type.lower() == 'ktp':
                formatted_content = format_ktp_response(data).replace('*', '').replace('_', '')
            elif doc_type.lower() == 'kk':
                formatted_content = format_kk_response(data).replace('*', '').replace('_', '')
            elif doc_type.lower() == 'ijazah':
                formatted_content = format_ijazah_response(data).replace('*', '').replace('_', '')
            elif doc_type.lower() == 'sim':
                formatted_content = format_sim_response(data).replace('*', '').replace('_', '')
            else:
                await client.send_message(chat, f"❌ Jenis dokumen '{doc_type}' tidak dikenal.")
                return False
            
            # Hilangkan emoji dari teks untuk file txt
            import re
            emoji_pattern = re.compile("["
                                       u"\U0001F600-\U0001F64F"  # emoticons
                                       u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                                       u"\U0001F680-\U0001F6FF"  # transport & map symbols
                                       u"\U0001F700-\U0001F77F"  # alchemical symbols
                                       u"\U0001F780-\U0001F7FF"  # Geometric Shapes
                                       u"\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
                                       u"\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
                                       u"\U0001FA00-\U0001FA6F"  # Chess Symbols
                                       u"\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
                                       u"\U00002702-\U000027B0"  # Dingbats
                                       u"\U000024C2-\U0001F251" 
                                       "]+", flags=re.UNICODE)
            
            clean_content = emoji_pattern.sub(r'', formatted_content)
            
            # Bersihkan format dan tag lainnya
            clean_content = clean_content.replace('`', '').replace('┣', '-').replace('┗', '-')
            
            # Tambahkan nama pemilik dan info dokumen di header
            header = f"Dokumen: {doc_type.upper()}\n"
            header += f"Nama: {owner_name}\n"
            header += f"Diekstrak pada: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}\n"
            header += "=" * 40 + "\n\n"
            
            # PERBAIKAN: Pastikan nama file menggunakan clean_name
            file_path = f"temp_media/{doc_type}_{clean_name}_{timestamp}.txt"
            log.info(f"Creating TXT file: {file_path}")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(header + clean_content)
            
            # Kirim file
            caption = f"Hasil ekstraksi {doc_type.upper()} - {owner_name} (TXT)"
            await client.send_document(chat, file_path, caption)
            
            # Beri tahu pengguna
            await client.send_message(chat, f"✅ File TXT hasil ekstraksi {doc_type.upper()} untuk {owner_name} telah dikirim.")
            return True
            
        else:
            await client.send_message(chat, f"❌ Format file '{format_type}' tidak didukung. Gunakan 'txt' atau 'json'.")
            return False
            
    except Exception as e:
        log.error(f"Error creating extraction file: {e}")
        log.error(traceback.format_exc())
        await client.send_message(chat, f"❌ Error saat membuat file: {str(e)}")
        return False     
        
@client_factory.event(ConnectedEv)
async def on_connected(_: NewAClient, __: ConnectedEv):
    log.info("⚡ WhatsApp terhubung")

@client_factory.event(MessageEv)
async def on_message(client: NewAClient, message: MessageEv):
    await handle_message(client, message)

async def handle_message(client, message):
    try:
        chat = message.Info.MessageSource.Chat
        
        # Extract text content
        if hasattr(message.Message, 'conversation') and message.Message.conversation:
            text = message.Message.conversation
        elif hasattr(message.Message, 'extendedTextMessage') and message.Message.extendedTextMessage.text:
            text = message.Message.extendedTextMessage.text
        else:
            text = ""
        
        # Get quoted message if any
        has_quoted, quoted_message, quoted_type = await get_quoted_message_info(message)
        
        # Handle commands
        if text.lower() == "ping":
            await client.reply_message("pong", message)
            
        elif text.lower() == "debug":
            if has_quoted:
                # Debug quoted message
                info = f"Debug untuk pesan {quoted_type}:\n"
                
                if quoted_type == "image":
                    # Cetak atribut-atribut image yang penting
                    imgmsg = quoted_message.imageMessage
                    info += "== IMAGE MESSAGE INFO ==\n"
                    for attr in ['URL', 'url', 'mimetype', 'fileLength', 'height', 'width', 'mediaKey', 'caption', 'JPEGThumbnail', 'directPath']:
                        if hasattr(imgmsg, attr):
                            val = getattr(imgmsg, attr)
                            if isinstance(val, (str, int, float, bool)):
                                info += f"{attr}: {val}\n"
                            else:
                                info += f"{attr}: (binary present)\n"
                        else:
                            info += f"{attr}: not present\n"
                
                # Tambahkan info dari thundra_io jika tersedia
                try:
                    msg_type = get_message_type(quoted_message)
                    if isinstance(msg_type, MediaMessageType):
                        info += "\n== THUNDRA_IO INFO ==\n"
                        info += f"MediaMessageType: {msg_type.__class__.__name__}\n"
                        
                        # Coba dapatkan info dari File object
                        try:
                            file_obj = File.from_message(msg_type)
                            info += "File object attributes:\n"
                            
                            # Periksa semua atribut yang mungkin dimiliki
                            for attr_name in dir(file_obj):
                                if not attr_name.startswith('_') and not callable(getattr(file_obj, attr_name)):
                                    try:
                                        attr_value = getattr(file_obj, attr_name)
                                        if isinstance(attr_value, (str, int, float, bool)):
                                            info += f"  {attr_name}: {attr_value}\n"
                                        else:
                                            info += f"  {attr_name}: (complex object)\n"
                                    except Exception as e:
                                        info += f"  {attr_name}: Error getting value: {str(e)}\n"
                            
                            # Periksa metode yang mungkin berguna
                            info += "Available methods:\n"
                            for method_name in ['get_content', 'get_extension', 'get_mime_type']:
                                if hasattr(file_obj, method_name) and callable(getattr(file_obj, method_name)):
                                    info += f"  {method_name}: Available\n"
                                else:
                                    info += f"  {method_name}: Not available\n"
                        except Exception as e:
                            info += f"Error creating File object: {str(e)}\n"
                    else:
                        info += "\nNot a MediaMessageType according to thundra_io\n"
                except Exception as e:
                    info += f"\nError using thundra_io: {str(e)}\n"
                
                await client.send_message(chat, info)
            else:
                await client.send_message(chat, message.__str__())
        elif text.lower() == "ptk" or text.lower() == "ptk.txt" or text.lower() == "ptk.json":
            file_format = None
            if text.lower().endswith('.txt'):
                file_format = 'txt'
            elif text.lower().endswith('.json'):
                file_format = 'json'
                
            await handle_document_extraction(client, chat, has_quoted, quoted_message, quoted_type, 
                                           'ktp', file_format, text)
        # Command untuk ekstrak KTP
        elif text.lower() == "ktp":
            if has_quoted and quoted_type == "image":
                await client.send_message(chat, "📷 Mengunduh gambar KTP...")
                
                try:
                    # Download gambar
                    media_bytes, mime_type, temp_path = await download_media(client, quoted_message, quoted_type)
                    
                    if media_bytes:
                        # Kirim ke API ekstraksi KTP
                        await client.send_message(chat, "🔍 Mengekstrak data KTP...")
                        
                        file_name = os.path.basename(temp_path)
                        response = await query_ktp_extractor(media_bytes, mime_type, file_name)
                        
                        # Format dan kirim respons
                        formatted_response = format_ktp_response(response)
                        await client.send_message(chat, formatted_response)
                    else:
                        await client.send_message(chat, "❌ Gagal mengunduh gambar")
                        
                except Exception as e:
                    log.error(f"Error in KTP extraction: {e}")
                    log.error(traceback.format_exc())
                    await client.send_message(chat, f"❌ Error saat memproses KTP: {str(e)}")
            else:
                await client.send_message(chat, "❌ Silakan reply pesan gambar KTP dengan perintah 'ktp'")

        # Command untuk ekstrak KK (Kartu Keluarga)
        elif text.lower() == "kk":
            if has_quoted and quoted_type == "image":
                await client.send_message(chat, "📷 Mengunduh gambar Kartu Keluarga...")
                
                try:
                    # Download gambar
                    media_bytes, mime_type, temp_path = await download_media(client, quoted_message, quoted_type)
                    
                    if media_bytes:
                        # Kirim ke API ekstraksi KK
                        await client.send_message(chat, "🔍 Mengekstrak data Kartu Keluarga...")
                        
                        file_name = os.path.basename(temp_path)
                        response = await query_kk_extractor(media_bytes, mime_type, file_name)
                        
                        # Format dan kirim respons
                        formatted_response = format_kk_response(response)
                        await client.send_message(chat, formatted_response)
                    else:
                        await client.send_message(chat, "❌ Gagal mengunduh gambar")
                        
                except Exception as e:
                    log.error(f"Error in KK extraction: {e}")
                    log.error(traceback.format_exc())
                    await client.send_message(chat, f"❌ Error saat memproses Kartu Keluarga: {str(e)}")
            else:
                await client.send_message(chat, "❌ Silakan reply pesan gambar Kartu Keluarga dengan perintah 'kk'")
        
        # Command untuk ekstrak SIM
        elif text.lower() == "sim":
            if has_quoted and quoted_type == "image":
                await client.send_message(chat, "📷 Mengunduh gambar SIM...")
                
                try:
                    # Download gambar
                    media_bytes, mime_type, temp_path = await download_media(client, quoted_message, quoted_type)
                    
                    if media_bytes:
                        # Kirim ke API ekstraksi SIM
                        await client.send_message(chat, "🔍 Mengekstrak data SIM...")
                        
                        file_name = os.path.basename(temp_path)
                        response = await query_sim_extractor(media_bytes, mime_type, file_name)
                        
                        # Format dan kirim respons
                        formatted_response = format_sim_response(response)
                        await client.send_message(chat, formatted_response)
                    else:
                        await client.send_message(chat, "❌ Gagal mengunduh gambar")
                        
                except Exception as e:
                    log.error(f"Error in SIM extraction: {e}")
                    log.error(traceback.format_exc())
                    await client.send_message(chat, f"❌ Error saat memproses SIM: {str(e)}")
            else:
                await client.send_message(chat, "❌ Silakan reply pesan gambar SIM dengan perintah 'sim'")

        
        # Command untuk ekstrak Ijazah
        elif text.lower() == "ijazah":
            if has_quoted and quoted_type == "image":
                await client.send_message(chat, "📷 Mengunduh gambar Ijazah...")
                
                try:
                    # Download gambar
                    media_bytes, mime_type, temp_path = await download_media(client, quoted_message, quoted_type)
                    
                    if media_bytes:
                        # Kirim ke API ekstraksi Ijazah
                        await client.send_message(chat, "🔍 Mengekstrak data Ijazah...")
                        
                        file_name = os.path.basename(temp_path)
                        response = await query_ijazah_extractor(media_bytes, mime_type, file_name)
                        
                        # Format dan kirim respons
                        formatted_response = format_ijazah_response(response)
                        await client.send_message(chat, formatted_response)
                    else:
                        await client.send_message(chat, "❌ Gagal mengunduh gambar")
                        
                except Exception as e:
                    log.error(f"Error in Ijazah extraction: {e}")
                    log.error(traceback.format_exc())
                    await client.send_message(chat, f"❌ Error saat memproses Ijazah: {str(e)}")
            else:
                await client.send_message(chat, "❌ Silakan reply pesan gambar Ijazah dengan perintah 'ijazah'")

        elif text.lower() == "help":
            help_text = """
*WhatsApp Dokumen Extractor Bot*

*Perintah:*
- `ping` - Cek apakah bot aktif
- `debug` - Menampilkan detail pesan (reply ke media untuk melihat attributnya)
- `ktp` - Ekstrak data dari gambar KTP (reply ke gambar KTP)
- `kk` - Ekstrak data dari gambar Kartu Keluarga (reply ke gambar KK)
- `ijazah` - Ekstrak data dari gambar Ijazah (reply ke gambar Ijazah)
- `sim` - Ekstrak data dari gambar SIM (reply ke gambar SIM)
- `help` - Tampilkan bantuan ini

*Contoh:*
> Reply gambar KTP dengan pesan "ktp"
> Reply gambar Kartu Keluarga dengan pesan "kk"
> Reply gambar Ijazah dengan pesan "ijazah" 
> Reply gambar SIM dengan pesan "sim"
> Tunggu proses ekstraksi selesai
> Data dokumen akan ditampilkan secara lengkap
"""
            await client.send_message(chat, help_text)
            
    except Exception as e:
        log.error(f"Error in message handler: {e}")
        log.error(traceback.format_exc())

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(client_factory.run())
