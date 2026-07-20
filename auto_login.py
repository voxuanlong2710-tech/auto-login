import asyncio
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from playwright.async_api import async_playwright

LOGIN_URL     = "https://2pink.org/"
DASHBOARD_URL = "https://2pink.org/dashboard/live-traffic"
USERNAME      = os.environ["USERNAME_2PINK"]
PASSWORD      = os.environ["PASSWORD_2PINK"]
ACTION        = os.environ.get("ACTION", "on")
ACCOUNT       = os.environ.get("ACCOUNT", "?")

GMAIL_USER    = os.environ.get("GMAIL_USER", "")
GMAIL_PASS    = os.environ.get("GMAIL_APP_PASSWORD", "")

MAX_RETRIES   = 3  # Số lần thử lại nếu thất bại

logs = []

def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    print(entry)
    logs.append(entry)

def send_email(success: bool):
    if not GMAIL_USER or not GMAIL_PASS:
        print("⚠️ Chưa cấu hình Gmail, bỏ qua gửi email.")
        return

    status = "✅ Thành công" if success else "❌ Thất bại"
    action_text = "BẬT" if ACTION == "on" else "TẮT"
    subject = f"Account {ACCOUNT} {action_text}"

    body = f"""
<h2>Báo cáo tự động</h2>
<table border="1" cellpadding="6" cellspacing="0">
  <tr><td><b>Tài khoản</b></td><td>Account {ACCOUNT}</td></tr>
  <tr><td><b>Hành động</b></td><td>{action_text}</td></tr>
  <tr><td><b>Trạng thái</b></td><td>{status}</td></tr>
  <tr><td><b>Thời gian</b></td><td>{datetime.now().strftime("%d/%m/%Y %H:%M:%S")}</td></tr>
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

async def attempt(p):
    """1 lần thử đăng nhập và toggle"""
    browser = await p.chromium.launch(headless=True)
    page = await browser.new_page()

    try:
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

        await page.goto(DASHBOARD_URL)
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        checkbox = page.locator("input[type='checkbox']").first
        checkbox_id = await checkbox.get_attribute("id")
        is_checked = await page.evaluate(f"document.getElementById('{checkbox_id}').checked")

        if ACTION == "on" and not is_checked:
            await page.evaluate(f"document.getElementById('{checkbox_id}').click()")
            await page.wait_for_timeout(1000)
            log("✅ Đã BẬT Active Domain!")
        elif ACTION == "off" and is_checked:
            await page.evaluate(f"document.getElementById('{checkbox_id}').click()")
            await page.wait_for_timeout(1000)
            log("✅ Đã TẮT Active Domain!")
        else:
            log(f"ℹ️ Active Domain đã ở trạng thái {'bật' if is_checked else 'tắt'} rồi, không cần thay đổi.")

        return True

    finally:
        await browser.close()

async def run():
    success = False

    async with async_playwright() as p:
        for i in range(1, MAX_RETRIES + 1):
            try:
                if i > 1:
                    log(f"🔄 Thử lại lần {i}/{MAX_RETRIES}...")
                    await asyncio.sleep(10)  # Chờ 10 giây trước khi thử lại

                success = await attempt(p)
                if success:
                    break

            except Exception as e:
                log(f"⚠️ Lần {i} thất bại: {e}")
                if i == MAX_RETRIES:
                    log("❌ Đã thử 3 lần, không thành công!")

    send_email(success)

asyncio.run(run())
