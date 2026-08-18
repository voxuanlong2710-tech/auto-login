import os
import csv
import urllib.request
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSklq1SDmWHjl2hYByILw-Nmd-kXaa3H69wiA29aYj2GUAarucHGOqTEvFO5WAwIfqyj_RuNVIgrnLt/pub?output=csv"
CRONJOB_API_KEY = os.environ["CRONJOB_API_KEY"]
CRONJOB_API_URL = "https://api.cron-job.org/jobs"

GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_PASS = os.environ.get("GMAIL_APP_PASSWORD", "")

JOB_IDS = {
    "1":  (7732771, 7732811),
    "2":  (7732828, 7732840),
    "3":  (7732852, 7732856),
    "4":  (7732873, 7732874),
    "5":  (7740025, 7740029),
    "6":  (7740116, 7740118),
    "7":  (7759114, 7759116),
    "8":  (7759141, 7759142),
    "9":  (7817111, 7817112),
    "10": (7817132, 7817133),
    "11": (7817152, 7817153),
    "12": (7817172, 7817173),
    "13": (7846330, 7846331),
    "14": (7846332, 7846333),
    "15": (7846334, 7846335),
    "16": (7846336, 7846337),
    "17": (7846338, 7846339),
    "18": (7846386, 7846387),
    "19": (7846388, 7846389),
    "20": (7846390, 7846391),
}

def fetch_schedule():
    with urllib.request.urlopen(SHEET_CSV_URL) as response:
        content = response.read().decode("utf-8")
    reader = csv.DictReader(content.splitlines())
    schedule = {}
    for row in reader:
        account = row["account"].strip()
        gio_bat = row["gio_bat"].strip()
        gio_tat = row["gio_tat"].strip()
        schedule[account] = (gio_bat, gio_tat)
    return schedule

def time_to_cron(time_str):
    """Chuyển HH:MM (giờ VN) sang cron UTC (trừ 7 giờ)"""
    h, m = map(int, time_str.split(":"))
    h_utc = (h - 7) % 24
    return f"{m} {h_utc} * * *"

def update_cronjob(job_id, cron_expression):
    """Gọi API cron-job.org để update giờ chạy"""
    parts = cron_expression.split()
    minute = int(parts[0])
    hour = int(parts[1])

    data = json.dumps({
        "job": {
            "schedule": {
                "timezone": "UTC",
                "expiresAt": 0,
                "hours": [hour],
                "mdays": [-1],
                "minutes": [minute],
                "months": [-1],
                "wdays": [-1]
            }
        }
    })

    req = urllib.request.Request(
        f"{CRONJOB_API_URL}/{job_id}",
        data=data.encode("utf-8"),
        method="PATCH",
        headers={
            "Authorization": f"Bearer {CRONJOB_API_KEY}",
            "Content-Type": "application/json"
        }
    )

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return True, result
    except urllib.error.HTTPError as e:
        return False, str(e)

def send_email(schedule, report):
    if not GMAIL_USER or not GMAIL_PASS:
        return

    success_count = sum(1 for r in report if r["bat_ok"] and r["tat_ok"])
    fail_count = len(report) - success_count
    subject = f"Update Schedule - {success_count*2}/{len(report)*2} thành công"

    rows = ""
    for r in report:
        bat_icon = "✅" if r["bat_ok"] else "❌"
        tat_icon = "✅" if r["tat_ok"] else "❌"
        rows += f"<tr><td>Account {r['account']}</td><td>{r['gio_bat']}</td><td>{bat_icon}</td><td>{r['gio_tat']}</td><td>{tat_icon}</td></tr>"

    body = f"""
<h2>Báo cáo Cập nhật Lịch 2Pink</h2>
<table border="1" cellpadding="6" cellspacing="0">
  <tr><td><b>Thời gian</b></td><td>{datetime.now().strftime("%d/%m/%Y %H:%M:%S")}</td></tr>
  <tr><td><b>Thành công</b></td><td>{success_count*2}/{len(report)*2} jobs</td></tr>
  <tr><td><b>Thất bại</b></td><td>{fail_count*2} jobs</td></tr>
</table>
<br>
<table border="1" cellpadding="6" cellspacing="0">
  <tr><th>Account</th><th>Giờ BẬT</th><th>BẬT</th><th>Giờ TẮT</th><th>TẮT</th></tr>
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

def main():
    print("📥 Đọc lịch từ Google Sheet...")
    schedule = fetch_schedule()
    print(f"✅ Đọc được {len(schedule)} accounts\n")

    report = []
    success_count = 0
    fail_count = 0

    for account, (gio_bat, gio_tat) in sorted(schedule.items(), key=lambda x: int(x[0])):
        if account not in JOB_IDS:
            print(f"⚠️ Account {account}: Không có Job ID, bỏ qua")
            continue

        job_bat, job_tat = JOB_IDS[account]
        cron_bat = time_to_cron(gio_bat)
        cron_tat = time_to_cron(gio_tat)

        print(f"📋 Account {account}: BẬT {gio_bat} | TẮT {gio_tat}")

        ok_bat, _ = update_cronjob(job_bat, cron_bat)
        ok_tat, _ = update_cronjob(job_tat, cron_tat)

        if ok_bat:
            print(f"  ✅ BẬT → {gio_bat} VN")
            success_count += 1
        else:
            print(f"  ❌ BẬT thất bại: {_}")
            fail_count += 1

        if ok_tat:
            print(f"  ✅ TẮT → {gio_tat} VN")
            success_count += 1
        else:
            print(f"  ❌ TẮT thất bại: {_}")
            fail_count += 1

        report.append({
            "account": account,
            "gio_bat": gio_bat,
            "gio_tat": gio_tat,
            "bat_ok": ok_bat,
            "tat_ok": ok_tat
        })

    print(f"\n🎉 Hoàn thành! {success_count} thành công, {fail_count} thất bại")
    send_email(schedule, report)

main()
