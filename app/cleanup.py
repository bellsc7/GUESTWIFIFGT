import sqlite3
import requests
import os
from datetime import datetime

# --- การตั้งค่า (เหมือนเดิม) ---
FORTIGATE_IP = "10.210.1.1"
FORTIGATE_API_KEY = "Gbft0trcy98pQ54sHdNhsr35p3wbsc"
ACTIVE_GROUP = "Guest-Group"
# EXPIRED_GROUP = "Guest-expired" # ไม่ได้ใช้แล้วในเวอร์ชันนี้
DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'guests.db')

def remove_user_from_active_group(username):
    """ลบ user ออกจาก Guest-Group"""
    group_url = f"https://{FORTIGATE_IP}/api/v2/cmdb/user/group/{ACTIVE_GROUP}"
    headers = {"Authorization": f"Bearer {FORTIGATE_API_KEY}"}

    try:
        # 1. ดึงสมาชิกปัจจุบัน
        response_get = requests.get(group_url, headers=headers, verify=False)
        response_get.raise_for_status()
        current_members = response_get.json()["results"][0].get("member", [])
        member_names = [member.get("name") for member in current_members]

        # 2. ตรวจสอบว่า user อยู่ใน group หรือไม่
        if username not in member_names:
            print(f"[{datetime.now()}] User '{username}' not found in group '{ACTIVE_GROUP}'. No removal needed.")
            return True # ถือว่าสำเร็จ

        # 3. สร้างรายชื่อใหม่ที่ไม่มี user คนนี้
        new_member_list = [member for member in current_members if member.get("name") != username]

        # 4. อัปเดต Group บน FortiGate
        update_payload = {"member": new_member_list}
        response_put = requests.put(group_url, headers=headers, json=update_payload, verify=False)
        response_put.raise_for_status()

        if response_put.json().get("status") == "success":
            print(f"[{datetime.now()}] Successfully removed user '{username}' from group '{ACTIVE_GROUP}'.")
            return True
        else:
            print(f"[{datetime.now()}] Failed to update group '{ACTIVE_GROUP}'. Response: {response_put.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now()}] API error modifying group '{ACTIVE_GROUP}': {e}")
        return False


def cleanup_expired_users():
    """ค้นหาและนำ user ที่หมดอายุออกจาก Guest-Group และอัปเดตสถานะ DB"""
    print(f"[{datetime.now()}] Starting cleanup process...")
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT username FROM guests WHERE created_at <= datetime('now', '-12 hours') AND status = 'active'")
        expired_users = cursor.fetchall()

        if not expired_users:
            print(f"[{datetime.now()}] No active expired users found.")
            return

        print(f"[{datetime.now()}] Found {len(expired_users)} expired user(s) to process.")

        for user in expired_users:
            username_to_expire = user[0]

            # ทำแค่การลบออกจาก Active Group
            if remove_user_from_active_group(username_to_expire):
                cursor.execute("UPDATE guests SET status = 'expired' WHERE username = ?", (username_to_expire,))
                conn.commit()
                print(f"[{datetime.now()}] Successfully updated status for user '{username_to_expire}' to 'expired' in local DB.")
            else:
                print(f"[{datetime.now()}] Failed to remove user '{username_to_expire}' from FortiGate group. Will retry next time.")

    except sqlite3.Error as e:
        print(f"[{datetime.now()}] Database error: {e}")
    finally:
        if conn:
            conn.close()
    print(f"[{datetime.now()}] Cleanup process finished.")

if __name__ == '__main__':
    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
    cleanup_expired_users()