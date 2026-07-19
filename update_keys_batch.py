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

logs = []
results = []

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

def send_summary_email(results: list):
    if not GMAIL_USER or not GMAIL_PASS:
        return

    total = len(results)
    success_count = sum(1 for r in results if r["success"])
    subject = f"Batch Update Keys - {success_count}/{total} thành công"

    rows = ""
    for r in results:
        status = "✅" if r["success"] else "❌"
        rows += f"<tr><td>{r['account']}</td><td>{status}</td><td>{r['keywords']}</td></tr>"

    body = f"""
<h2>Báo cáo Batch Cập nhật Keyword</h2>
<table border="1" cellpadding="6" cellspacing="0">
  <tr><td><b>Tổng account</b></td><td>{total}</td></tr>
  <tr><td><b>Thành công</b></td><td>{success_count}</td></tr>
  <tr><td><b>Thất bại</b></td><td>{total - success_count}</td></tr>
  <tr><td><b>Thời gian</b></td><td>{datetime.now().strftime("%d/%m/%Y %H:%M:%S")}</td></tr>
</table>
<h3>Chi tiết từng account:</h3>
<table border="1" cellpadding="6" cellspacing="0">
  <tr><th>Account</th><th>Trạng thái</th><th>Keywords</th></tr>
  {rows}
</table>
<h3>Log đầy đủ:</h3>
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
        print("📧 Đã gửi email tổng hợp!")
    except Exception as e:
        print(f"⚠️ Lỗi gửi email: {e}")

async def update_one(page, row_index, kw):
    links = page.locator("a[id*='ListView1'][id*='LinkButton1']")
    await links.nth(row_index).click()
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(2000)

    await page.fill("#ctl00_ContentPlaceHolder1_txtKeyWord", kw["key"])
    await page.wait_for_timeout(300)
    await page.fill("#ctl00_ContentPlaceHolder1_txtStep1", kw["url"])
    await page.wait_for_timeout(300)

    rand_time = random.randint(25, 115)
    await page.fill("#ctl00_ContentPlaceHolder1_txtWait1", str(rand_time))
    await page.wait_for_timeout(300)

    await page.click("#ctl00_ContentPlaceHolder1_btnUpdateUrl")
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(2000)

    log(f"  ✅ STT {kw['stt']}: {kw['key']} | {rand_time}s")

async def process_account(p, account):
    stt_from, stt_to, dashboard_url = ACCOUNT_CONFIG[account]
    username = os.environ.get(f"USERNAME_2PINK_{account}", "")
    password = os.environ.get(f"PASSWORD_2PINK_{account}", "")

    if not username or not password:
        log(f"❌ Account {account}: Chưa có credentials!")
        return False, []

    log(f"\n{'='*40}")
    log(f"📋 Account {account} - STT {stt_from}-{stt_to}")

    keywords = fetch_keywords(stt_from, stt_to)

    for attempt in range(1, 4):
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            if attempt > 1:
                log(f"🔄 Account {account} - Thử lại lần {attempt}/3...")
                await asyncio.sleep(10)

            await page.goto(LOGIN_URL)
            await page.wait_for_load_state("networkidle")
            await page.click("text=Đăng nhập", timeout=60000)
            await page.wait_for_timeout(2000)

            await page.fill("#ctl00_ContentPlaceHolder1_txtUserName", username)
            await page.fill("#ctl00_ContentPlaceHolder1_txtPass", password)
            await page.click("#ctl00_ContentPlaceHolder1_btnDangNhap")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)

            await page.goto(dashboard_url)
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)
            log(f"✅ Account {account} - Đã vào dashboard!")

            for j, kw in enumerate(keywords):
                await update_one(page, j, kw)

            log(f"✅ Account {account} - Hoàn thành!")
            return True, keywords

        except Exception as e:
            log(f"⚠️ Account {account} lần {attempt}: {e}")
        finally:
            await browser.close()

    log(f"❌ Account {account} thất bại sau 3 lần!")
    return False, keywords

async def run():
    accounts_str = os.environ.get("ACCOUNTS", "1")
    accounts = [a.strip() for a in accounts_str.split(",")]

    log(f"🚀 Batch chạy {len(accounts)} accounts: {', '.join(accounts)}")

    async with async_playwright() as p:
        for acc in accounts:
            success, keywords = await process_account(p, acc)
            kw_summary = ", ".join([kw["key"] for kw in keywords]) if keywords else "-"
            results.append({
                "account": f"Account {acc}",
                "success": success,
                "keywords": kw_summary
            })

    send_summary_email(results)

asyncio.run(run())
