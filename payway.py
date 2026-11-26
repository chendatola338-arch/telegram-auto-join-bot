import io
import time
import asyncio
import httpx
import qrcode
from typing import Optional, Dict, Any

try:
    from curl_cffi.requests import AsyncSession
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

API_BASE_URL = "https://payway.jlastore.com"

# Browser Headers ដើម្បីការពារកុំឱ្យ Cloudflare ចាប់ និង Block (403 Forbidden)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://payway.jlastore.com",
    "Referer": "https://payway.jlastore.com/",
}

async def create_payway_transaction(amount: float, aba_data_url: str, tran_id: Optional[str] = None) -> Dict[str, Any]:
    """
    បង្កើតប្រតិបត្តិការបង់ប្រាក់តាមរយៈ JLA Payway API (មានភ្ជាប់ Auto Retry និង Cloudflare Bypass)
    """
    if not tran_id:
        tran_id = f"tx_{int(time.time())}_{int(time.time() * 1000) % 1000}"

    url = f"{API_BASE_URL}/api/create-tran"
    payload = {
        "amount": f"{amount:.2f}",
        "aba_data": aba_data_url,
        "tran_id": tran_id
    }

    last_error = None
    for attempt in range(3):
        try:
            if HAS_CURL_CFFI:
                async with AsyncSession(impersonate="chrome120") as s:
                    response = await s.post(url, json=payload, headers=HEADERS, timeout=30)
                    if response.status_code == 200:
                        return response.json()
                    if response.status_code in (502, 503, 504, 429):
                        last_error = f"Server busy (Status {response.status_code})"
                        await asyncio.sleep(2.5)
                        continue
                    response.raise_for_status()
            else:
                async with httpx.AsyncClient(timeout=30.0, verify=False, headers=HEADERS) as client:
                    response = await client.post(url, json=payload)
                    if response.status_code == 200:
                        return response.json()
                    if response.status_code in (502, 503, 504, 429):
                        last_error = f"Server busy (Status {response.status_code})"
                        await asyncio.sleep(2.5)
                        continue
                    response.raise_for_status()
        except Exception as e:
            last_error = e
            await asyncio.sleep(2.5)

    raise Exception(f"Bank API Busy, please try again: {last_error}")

async def check_transaction_status(tran_id: str) -> Dict[str, Any]:
    """
    ពិនិត្យស្ថានភាពបង់ប្រាក់
    ត្រឡប់ទិន្នន័យពី Payway API: status.message == 'approved' ឬ data.action == 'approved'
    """
    url = f"{API_BASE_URL}/api/check-payment-status"
    payload = {
        "tran_id": tran_id
    }

    try:
        if HAS_CURL_CFFI:
            async with AsyncSession(impersonate="chrome120") as s:
                response = await s.post(url, json=payload, headers=HEADERS, timeout=20)
                if response.status_code == 200:
                    return response.json()
                return {}
        else:
            async with httpx.AsyncClient(timeout=20.0, verify=False, headers=HEADERS) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    return response.json()
                return {}
    except Exception:
        return {}

def is_approved(data: Dict[str, Any]) -> bool:
    """
    ផ្ទៀងផ្ទាត់ថាតើការបង់ប្រាក់ទទួលបានជោគជ័យ (Approved) ឬនៅ
    """
    if not data:
        return False
        
    status_obj = data.get("status", {})
    if isinstance(status_obj, dict) and status_obj.get("message") == "approved":
        return True

    data_obj = data.get("data", {})
    if isinstance(data_obj, dict) and data_obj.get("action") == "approved":
        return True

    return False

def generate_qr_code_image(qr_string: str, amount: float = 30.00, currency: str = "USD") -> io.BytesIO:
    """
    បង្កើតរូបភាព KHQR Code ស្អាតមានស៊ុម និង Logo តាមទម្រង់ផ្លូវការ (Official ABA / Bakong Template)
    """
    import os
    from PIL import Image, ImageDraw, ImageFont

    template_path = "khqr_template.png"
    logo_path = "bakong_logo.png"

    # បើមាន Template និង Logo ប្រើប្រាស់ Template
    if os.path.exists(template_path) and os.path.exists(logo_path):
        try:
            template = Image.open(template_path).convert("RGBA")

            # បង្កើត QR Code កម្រិតច្បាស់ខ្ពស់ (High error correction សម្រាប់ Logo កណ្តាល)
            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=0,
            )
            qr.add_data(qr_string)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")

            # Resize អោយត្រូវនឹងប្រអប់ស៊ុម (304x304)
            qr_img = qr_img.resize((304, 304), Image.Resampling.LANCZOS)

            # បញ្ចូល Bakong Logo នៅចំកណ្តាល QR
            logo = Image.open(logo_path).convert("RGBA")
            logo_pos = ((qr_img.width - logo.width) // 2, (qr_img.height - logo.height) // 2)
            qr_img.paste(logo, logo_pos, mask=logo)

            # បញ្ចូល QR ទៅក្នុងស៊ុម Template
            template.paste(qr_img, (218, 487), mask=qr_img)

            # សរសេរចំនួនទឹកប្រាក់
            draw = ImageDraw.Draw(template)
            draw.rectangle([215, 360, 480, 405], fill=(255, 255, 255))
            try:
                font_bold = ImageFont.truetype("segoeuib.ttf", 28)
                font_curr = ImageFont.truetype("segoeui.ttf", 20)
            except Exception:
                font_bold = ImageFont.load_default()
                font_curr = font_bold

            draw.text((218, 365), f"{amount:.2f}", fill="#0A0A0A", font=font_bold)
            draw.text((310, 372), f"{currency}", fill="#0A0A0A", font=font_curr)

            bio = io.BytesIO()
            template.convert("RGB").save(bio, format="JPEG", quality=95)
            bio.seek(0)
            return bio
        except Exception as e:
            pass

    # Fallback ករណីគ្មាន file template
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(qr_string)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#001F3F", back_color="white")
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    return bio
