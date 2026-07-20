import os
import csv
import urllib.request
import urllib.parse
import json

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSklq1SDmWHjl2hYByILw-Nmd-kXaa3H69wiA29aYj2GUAarucHGOqTEvFO5WAwIfqyj_RuNVIgrnLt/pub?output=csv"
CRONJOB_API_KEY = os.environ["CRONJOB_API_KEY"]
CRONJOB_API_URL = "https://api.cron-job.org/jobs"

# Job ID mapping: account -> (job_id_bat, job_id_tat)
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
    """Đọc lịch từ Google Sheet"""
    with urllib.request.urlopen(SHEET_CSV_URL) as response:
        content = response.read().decode("utf-8")
    reader = csv.DictReader(content.splitlines())
    schedule = {}
    for row in reader:
        account = row["account"].strip()
        gio_bat = row["gio_bat"].strip()  # format HH:MM
        gio_tat = row["gio_tat"].strip()  # format HH:MM
        schedule[account] = (gio_bat, gio_tat)
    return schedule

def time_to_cron(time_str):
    """Chuyển HH:MM (giờ VN) sang cron UTC (trừ 7 giờ)"""
    h, m = map(int, time_str.split(":"))
    h_utc = (h - 7) % 24
    return f"{m} {h_utc} * * *"

def update_cronjob(job_id, cron_expression):
    """Gọi API cron-job.org để update giờ chạy"""
    url = f"{CRONJOB_API_URL}/{job_id}"
    data = json.dumps({
        "job": {
            "schedule": {
                "timezone": "UTC",
                "expiresAt": 0,
                "hours": [-1],
                "mdays": [-1],
                "minutes": [-1],
                "months": [-1],
                "wdays": [-1]
            }
        }
    })

    # Parse cron để lấy minute và hour
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
        url,
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

def main():
    print("📥 Đọc lịch từ Google Sheet...")
    schedule = fetch_schedule()
    print(f"✅ Đọc được {len(schedule)} accounts\n")

    success_count = 0
    fail_count = 0

    for account, (gio_bat, gio_tat) in sorted(schedule.items(), key=lambda x: int(x[0])):
        if account not in JOB_IDS:
            print(f"⚠️ Account {account}: Không có Job ID, bỏ qua")
            continue

        job_bat, job_tat = JOB_IDS[account]
        cron_bat = time_to_cron(gio_bat)
        cron_tat = time_to_cron(gio_tat)

        print(f"📋 Account {account}: BẬT {gio_bat} ({cron_bat}) | TẮT {gio_tat} ({cron_tat})")

        # Update job BẬT
        ok, _ = update_cronjob(job_bat, cron_bat)
        if ok:
            print(f"  ✅ BẬT → {gio_bat} VN")
            success_count += 1
        else:
            print(f"  ❌ BẬT thất bại: {_}")
            fail_count += 1

        # Update job TẮT
        ok, _ = update_cronjob(job_tat, cron_tat)
        if ok:
            print(f"  ✅ TẮT → {gio_tat} VN")
            success_count += 1
        else:
            print(f"  ❌ TẮT thất bại: {_}")
            fail_count += 1

    print(f"\n🎉 Hoàn thành! {success_count} thành công, {fail_count} thất bại")

main()
