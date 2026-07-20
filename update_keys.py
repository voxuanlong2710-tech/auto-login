import asyncio
import os
import csv
import random
import smtplib
import urllib.request
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from playwright.async_api import async_playwright

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTlV3fKG5HQjME5OYZ--vk7TMwaSkd_OZZMN4aMvEtLNx_wx7jCFhfu-L9eD74rXage674hucpO7dfR/pub?gid=0&single=true&output=csv"

LOGIN_URL = "https://2pink.org/"

USERNAME  = os.environ["USERNAME_2PINK"]
PASSWORD  = os.environ["PASSWORD_2PINK"]
ACCOUNT   = os.environ.get("ACCOUNT", "?")

GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_PASS = os.environ.get("GMAIL_APP_PASSWORD", "")

ACCOUNT_CONFIG = {
    "1":  (1,   5,  "https://2pink.org/dashboard/live-traffic/ivivucom-262112"),
    "2":  (6,   10, "https://2pink.org/dashboard/live-traffic/wwwivivucom-263440"),
    "3":  (11,  15, "https://2pink.org/dashboard/live-traffic/wwwivivucom-269699"),
    "4":  (16,  20, "https://2pink.org/dashboard/live-traffic/wwwivivucom-269704"),
    "5":  (21,  25, "https://2pink.org/dashboard/live-traffic/wwwivivucom-269705"),
    "6":  (26,  30, "https://2pink.org/dashboard/live-traffic/wwwivivucom-269707"),
    "7":  (31,  35, "https://2pink.org/dashboard/live-traffic/wwwivivucom-270385"),
    "8":  (36,  40, "https://2pink.org/dashboard/live-traffic/wwwivivucom-270386"),
    "9":  (41,  45, "https://2pink.org/dashboard/live-traffic/wwwivivucom-270767"),
    "10": (46,  50, "https://2pink.org/dashboard/live-traffic/wwwivivucom-270768"),
    "11": (51,  55, "https://2pink.org/dashboard/live-traffic/wwwivivucom-270766"),
    "12": (56,  60, "https://2pink.org/dashboard/live-traffic/wwwivivucom-270769"),
    "13": (61,  65, "https://2pink.org/dashboard/live-traffic/wwwivivucom-270955"),
    "14": (66,  70, "https://2pink.org/dashboard/live-traffic/wwwivivucom-270956"),
    "15": (71,  75, "https://2pink.org/dashboard/live-traffic/wwwivivucom-270958"),
    "16": (76,  80, "https://2pink.org/dashboard/live-traffic/wwwivivucom-270959"),
    "17": (81,  85, "https://2pink.org/dashboard/live-traffic/wwwivivucom-270960"),
    "18": (86,  90, "https://2pink.org/dashboard/live-traffic/wwwivivucom-270962"),
    "19": (91,  95, "https://2pink.org/dashboard/live-traffic/wwwivivucom-270964"),
    "20": (96, 100, "https://2pink.org/dashboard/live-traffic/wwwivivucom-270965"),
}

MAX_RETRIES = 3
logs = []

def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    print(entry)
    logs.append(entry)

def fetch_keywords(stt_from, stt_to):
    with urllib.request.urlopen(SHEET_CSV_URL) as response:
        content = response.read().decode("utf-8")
    reader = csv.DictReader(content.splitlines())
    keywords = []
    for row in reader:
        try:
            stt = int(row["stt"])
            if stt_from <= stt <= stt_to:
                keywords.append({
                    "stt": stt,
                    "key": row["Key"].strip(),
                    "url": row["url"].strip()
                })
        except:
            continue
    keywords.sort(key=lambda x: x["stt"])
    return keywords

def send_email(success: bool, keywords: list, account: str):
    if not GMAIL_USER or not GMAIL_PASS:
        return

    status = "✅ Thành công" if success else "❌ Thất bại"
    subject = f"Account {account} Cập nhật Key - {status}"

    rows = ""
    for kw in keywords:
        rows += f"<tr><td>{kw['stt']}</td><td>{kw['key']}</td><td>{kw['url']}</td></tr>"

    body = f"""
<h2>Báo cáo cập nhật keyword</h2>
<table border="1" cellpadding="6" cellspacing="0">
  <tr><td><b>Tài khoản</b></td><td>Account {account}</td></tr>
  <tr><td><b>Trạng thái</b></td><td>{status}</td></tr>
  <tr><td><b>Thời gian</b></td><td>{datetime.now().strftime("%d/%m/%Y %H:%M:%S")}</td></tr>
</table>
<h3>Danh sách keyword đã cập nhật:</h3>
<table border="1" cellpadding="6" cellspacing="0">
  <tr><th>STT</th><th>Key</th><th>URL</th></tr>
  {rows}
</table>
<h3>Chi tiết log:</h3>
<pre>{"<br>".join(logs)}</pre>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = GMAIL_USER
    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASS)
            server.sendmail(GMAIL_USER, GMAIL_USER, msg.as_string())
        print("📧 Đã gửi email báo cáo!")
    except Exception as e:
        print(f"⚠️ Lỗi gửi email: {e}")

async def update_one(page, dashboard_url, row_index, kw):
    log(f"🔄 [{row_index+1}/5] STT {kw['stt']}: {kw['key']}")

    # Reload dashboard trước mỗi lần để đảm bảo danh sách fresh
    await page.goto(dashboard_url)
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(2000)

    # Click vào link theo index
    links = page.locator("a[id*='ListView1'][id*='LinkButton1']")
    count = await links.count()
    log(f"🔍 Tìm thấy {count} links, click index {row_index}")
    await links.nth(row_index).click()
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(2000)

    # Điền keyword
    await page.fill("#ctl00_ContentPlaceHolder1_txtKeyWord", kw["key"])
    await page.wait_for_timeout(300)
    log(f"✏️ Keyword: {kw['key']}")

    # Điền URL
    await page.fill("#ctl00_ContentPlaceHolder1_txtStep1", kw["url"])
    await page.wait_for_timeout(300)
    log(f"🔗 URL: {kw['url']}")

    # Thời gian chờ random 25-115 giây
    rand_time1 = random.randint(25, 45)   # Click vào link
    rand_time2 = random.randint(25, 120)  # Click ngẫu nhiên 1
    rand_time3 = random.randint(25, 120)  # Click ngẫu nhiên 2
    rand_time4 = random.randint(25, 120)  # Click ngẫu nhiên 3
    await page.fill("#ctl00_ContentPlaceHolder1_txtWait1", str(rand_time1))
    await page.wait_for_timeout(300)
    await page.fill("#ctl00_ContentPlaceHolder1_txtWait2", str(rand_time2))
    await page.wait_for_timeout(300)
    await page.fill("#ctl00_ContentPlaceHolder1_txtWait3", str(rand_time3))
    await page.wait_for_timeout(300)
    await page.fill("#ctl00_ContentPlaceHolder1_txtWait4", str(rand_time4))
    await page.wait_for_timeout(300)
    log(f"⏱️ Click link: {rand_time1}s | Ngẫu nhiên: {rand_time2}s, {rand_time3}s, {rand_time4}s")

    # Bấm Cập nhật Url
    await page.click("#ctl00_ContentPlaceHolder1_btnUpdateUrl")
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(2000)

    log(f"✅ [{row_index+1}/5] Xong STT {kw['stt']}")

async def attempt(p, keywords, dashboard_url):
    browser = await p.chromium.launch(headless=True)
    page = await browser.new_page()

    try:
        # Đăng nhập
        await page.goto(LOGIN_URL)
        await page.wait_for_load_state("networkidle")
        await page.click("text=Đăng nhập", timeout=60000)
        await page.wait_for_timeout(2000)

        await page.fill("#ctl00_ContentPlaceHolder1_txtUserName", USERNAME)
        await page.fill("#ctl00_ContentPlaceHolder1_txtPass", PASSWORD)
        await page.click("#ctl00_ContentPlaceHolder1_btnDangNhap")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)
        log("✅ Đã đăng nhập!")

        # Cập nhật từng keyword — mỗi lần reload dashboard
        for i, kw in enumerate(keywords):
            await update_one(page, dashboard_url, i, kw)

        return True

    except Exception as e:
        log(f"❌ Lỗi: {e}")
        return False
    finally:
        await browser.close()

async def run():
    if ACCOUNT not in ACCOUNT_CONFIG:
        log(f"❌ Account {ACCOUNT} chưa được cấu hình!")
        return

    stt_from, stt_to, dashboard_url = ACCOUNT_CONFIG[ACCOUNT]
    log(f"📥 Đọc keywords STT {stt_from}-{stt_to} từ Google Sheet...")
    keywords = fetch_keywords(stt_from, stt_to)
    log(f"✅ Đọc được {len(keywords)} keywords")

    success = False
    async with async_playwright() as p:
        for i in range(1, MAX_RETRIES + 1):
            try:
                if i > 1:
                    log(f"🔄 Thử lại lần {i}/{MAX_RETRIES}...")
                    await asyncio.sleep(10)
                success = await attempt(p, keywords, dashboard_url)
                if success:
                    break
            except Exception as e:
                log(f"⚠️ Lần {i} thất bại: {e}")
                if i == MAX_RETRIES:
                    log("❌ Đã thử 3 lần, không thành công!")

    send_email(success, keywords, ACCOUNT)

asyncio.run(run())
