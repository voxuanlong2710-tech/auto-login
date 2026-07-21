import asyncio
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from playwright.async_api import async_playwright

LOGIN_URL = "https://2pink.org/"

GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_PASS = os.environ.get("GMAIL_APP_PASSWORD", "")

ACCOUNT_CONFIG = {
    "1":  "https://2pink.org/dashboard/live-traffic/ivivucom-262112",
    "2":  "https://2pink.org/dashboard/live-traffic/wwwivivucom-263440",
    "3":  "https://2pink.org/dashboard/live-traffic/wwwivivucom-269699",
    "4":  "https://2pink.org/dashboard/live-traffic/wwwivivucom-269704",
    "5":  "https://2pink.org/dashboard/live-traffic/wwwivivucom-269705",
    "6":  "https://2pink.org/dashboard/live-traffic/wwwivivucom-269707",
    "7":  "https://2pink.org/dashboard/live-traffic/wwwivivucom-270385",
    "8":  "https://2pink.org/dashboard/live-traffic/wwwivivucom-270386",
    "9":  "https://2pink.org/dashboard/live-traffic/wwwivivucom-270767",
    "10": "https://2pink.org/dashboard/live-traffic/wwwivivucom-270768",
    "11": "https://2pink.org/dashboard/live-traffic/wwwivivucom-270766",
    "12": "https://2pink.org/dashboard/live-traffic/wwwivivucom-270769",
    "13": "https://2pink.org/dashboard/live-traffic/wwwivivucom-270955",
    "14": "https://2pink.org/dashboard/live-traffic/wwwivivucom-270956",
    "15": "https://2pink.org/dashboard/live-traffic/wwwivivucom-270958",
    "16": "https://2pink.org/dashboard/live-traffic/wwwivivucom-270959",
    "17": "https://2pink.org/dashboard/live-traffic/wwwivivucom-270960",
    "18": "https://2pink.org/dashboard/live-traffic/wwwivivucom-270962",
    "19": "https://2pink.org/dashboard/live-traffic/wwwivivucom-270964",
    "20": "https://2pink.org/dashboard/live-traffic/wwwivivucom-270965",
}

MAX_RETRIES = 3

def send_email(results: list):
    if not GMAIL_USER or not GMAIL_PASS:
        return

    on_count = sum(1 for r in results if r["status"] == "ON")
    off_count = sum(1 for r in results if r["status"] == "OFF")
    error_count = sum(1 for r in results if r["status"] == "ERROR")

    subject = f"Check Status - {on_count} ON | {off_count} OFF | {error_count} Lỗi"

    rows = ""
    for r in results:
        if r["status"] == "ON":
            icon = "🟢"
        elif r["status"] == "OFF":
            icon = "🔴"
        else:
            icon = "⚠️"
        retry_note = f" (thành công sau {r['attempts']} lần)" if r["attempts"] > 1 and r["status"] != "ERROR" else ""
        rows += f"<tr><td>Account {r['account']}</td><td>{icon} {r['status']}{retry_note}</td></tr>"

    body = f"""
<h2>Báo cáo trạng thái 2Pink</h2>
<table border="1" cellpadding="6" cellspacing="0">
  <tr><td><b>Thời gian check</b></td><td>{datetime.now().strftime("%d/%m/%Y %H:%M:%S")}</td></tr>
  <tr><td><b>🟢 ON</b></td><td>{on_count} acc</td></tr>
  <tr><td><b>🔴 OFF</b></td><td>{off_count} acc</td></tr>
  <tr><td><b>⚠️ Lỗi</b></td><td>{error_count} acc</td></tr>
</table>
<br>
<table border="1" cellpadding="6" cellspacing="0">
  <tr><th>Tài khoản</th><th>Trạng thái</th></tr>
  {rows}
</table>
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

async def check_once(p, account):
    """Thử check 1 lần"""
    username = os.environ.get(f"USERNAME_2PINK_{account}", "")
    password = os.environ.get(f"PASSWORD_2PINK_{account}", "")
    dashboard_url = ACCOUNT_CONFIG[account]

    browser = await p.chromium.launch(headless=True)
    page = await browser.new_page()

    try:
        await page.goto(LOGIN_URL, timeout=60000)
        await page.wait_for_timeout(3000)
        await page.click("text=Đăng nhập", timeout=60000)
        await page.wait_for_timeout(2000)

        await page.fill("#ctl00_ContentPlaceHolder1_txtUserName", username)
        await page.fill("#ctl00_ContentPlaceHolder1_txtPass", password)
        await page.click("#ctl00_ContentPlaceHolder1_btnDangNhap")
        await page.wait_for_timeout(3000)

        await page.goto(dashboard_url, timeout=60000)
        await page.wait_for_timeout(3000)

        # Đọc trạng thái toggle
        checkbox = page.locator("input[type='checkbox']").first
        checkbox_id = await checkbox.get_attribute("id")
        is_checked = await page.evaluate(f"document.getElementById('{checkbox_id}').checked")

        return "ON" if is_checked else "OFF"

    finally:
        await browser.close()

async def check_account(p, account):
    """Check với retry tự động tối đa 3 lần"""
    username = os.environ.get(f"USERNAME_2PINK_{account}", "")
    password = os.environ.get(f"PASSWORD_2PINK_{account}", "")

    if not username or not password:
        print(f"⚠️ Account {account}: Chưa có credentials!")
        return {"account": account, "status": "ERROR", "attempts": 0}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if attempt > 1:
                print(f"  🔄 Account {account} - Retry lần {attempt}/{MAX_RETRIES}...")
                await asyncio.sleep(10)

            status = await check_once(p, account)
            icon = "🟢" if status == "ON" else "🔴"
            print(f"{icon} Account {account}: {status}" + (f" (lần {attempt})" if attempt > 1 else ""))
            return {"account": account, "status": status, "attempts": attempt}

        except Exception as e:
            print(f"  ⚠️ Account {account} lần {attempt}: {e}")

    print(f"❌ Account {account}: Thất bại sau {MAX_RETRIES} lần!")
    return {"account": account, "status": "ERROR", "attempts": MAX_RETRIES}

async def run():
    print(f"🔍 Bắt đầu check {len(ACCOUNT_CONFIG)} accounts...\n")
    results = []

    async with async_playwright() as p:
        for account in sorted(ACCOUNT_CONFIG.keys(), key=lambda x: int(x)):
            result = await check_account(p, account)
            results.append(result)

    on_count = sum(1 for r in results if r["status"] == "ON")
    off_count = sum(1 for r in results if r["status"] == "OFF")
    error_count = sum(1 for r in results if r["status"] == "ERROR")
    print(f"\n📊 Tổng kết: 🟢 {on_count} ON | 🔴 {off_count} OFF | ⚠️ {error_count} Lỗi")

    send_email(results)

asyncio.run(run())
