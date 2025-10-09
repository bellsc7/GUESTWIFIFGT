import sqlite3
import requests
import os
from datetime import datetime

# --- การตั้งค่า (เหมือนเดิม) ---
FORTIGATE_IP = "10.210.1.1"
FORTIGATE_API_KEY = "Gbft0trcy98pQ54sHdNhsr35p3wbsc"
GUEST_USER_GROUP = "Guest-Group"
DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'guests.db')

def remove_user_from_group(username):
    # ... (ฟังก์ชันนี้เหมือนเดิมทุกประการ ไม่ต้องแก้ไข) ...
    group_url = f"https://{FORTIGATE_IP}/api/v2/cmdb/user/group/{GUEST_USER_GROUP}"
    headers = { "Authorization": f"Bearer {FORTIGATE_API_KEY}" }
    try:
        response_get = requests.get(group_url, headers=headers, verify=False)
        response_get.raise_for_status()
        current_members = response_get.json()["results"][0].get("member", [])
        new_member_list = [member for member in current_members if member.get("name") != username]
        if len(new_member_list) == len(current_members): return True
        update_payload = {"member": new_member_list}
        response_put = requests.put(group_url, headers=headers, json=update_payload, verify=False)
        response_put.raise_for_status()
        if response_put.json().get("status") == "success":
            print(f"[{datetime.now()}] Successfully removed user '{username}' from group '{GUEST_USER_GROUP}'.")
            return True
        else: return False
    except requests.exceptions.RequestException: return False

def cleanup_expired_users():
    """ค้นหาและอัปเดตสถานะ user ที่หมดอายุ (เกิน 12 ชั่วโมง)"""
    print(f"[{datetime.now()}] Starting cleanup process...")
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # --- ส่วนที่แก้ไข 1: ค้นหาเฉพาะ user ที่ status เป็น 'active' เท่านั้น ---
        cursor.execute("SELECT username FROM guests WHERE created_at <= datetime('now', '-12 hours') AND status = 'active'")
        expired_users = cursor.fetchall()

        if not expired_users:
            print(f"[{datetime.now()}] No active expired users found.")
            return

        print(f"[{datetime.now()}] Found {len(expired_users)} expired user(s) to process.")

        for user in expired_users:
            username_to_expire = user[0]

            if remove_user_from_group(username_to_expire):
                # --- ส่วนที่แก้ไข 2: เปลี่ยนจาก DELETE เป็น UPDATE ---
                cursor.execute("UPDATE guests SET status = 'expired' WHERE username = ?", (username_to_expire,))
                conn.commit()
                print(f"[{datetime.now()}] Successfully updated status for user '{username_to_expire}' to 'expired'.")

    except sqlite3.Error as e:
        print(f"[{datetime.now()}] Database error: {e}")
    finally:
        if conn:
            conn.close()
    print(f"[{datetime.now()}] Cleanup process finished.")

if __name__ == '__main__':
    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
    cleanup_expired_users()