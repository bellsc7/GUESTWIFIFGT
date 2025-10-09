import os
import sqlite3
import requests
import random
import string
from flask import Flask, render_template, request, redirect, url_for, g

# --- การตั้งค่า ---
FORTIGATE_IP = "10.210.1.1"
FORTIGATE_API_KEY = "Gbft0trcy98pQ54sHdNhsr35p3wbsc"
GUEST_USER_GROUP = "Guest-Group"
DATABASE = 'guests.db'

app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- ฟังก์ชันจัดการฐานข้อมูล SQLite ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS guests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fullname TEXT NOT NULL,
                citizen_id TEXT NOT NULL UNIQUE,
                mobile_no TEXT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                created_at DATETIME DEFAULT (datetime('now', 'localtime')),
                status TEXT NOT NULL DEFAULT 'active'
            )
        ''')
        db.commit()

# --- ฟังก์ชันสำหรับคุยกับ FortiGate API (เวอร์ชัน 2 ขั้นตอน) ---
def create_fortigate_user(username, password, fullname):
    base_url = f"https://{FORTIGATE_IP}/api/v2/cmdb"
    headers = {
        "Authorization": f"Bearer {FORTIGATE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # ขั้นตอนที่ 1: สร้าง User
    user_creation_url = f"{base_url}/user/local/"
    user_payload = {"name": username, "passwd": password, "type": "password", "status": "enable"}
    try:
        response_user = requests.post(user_creation_url, headers=headers, json=user_payload, verify=False)
        response_user.raise_for_status()
        if response_user.json().get("status") != "success":
            return False, f"User Creation Error: {response_user.text}"
    except requests.exceptions.RequestException as e:
        return False, str(e)

    # ขั้นตอนที่ 2: เพิ่ม User เข้า Group
    group_edit_url = f"{base_url}/user/group/{GUEST_USER_GROUP}"
    try:
        response_get_group = requests.get(group_edit_url, headers=headers, verify=False)
        response_get_group.raise_for_status()
        existing_members = response_get_group.json()["results"][0].get("member", [])
        
        new_member = {"name": username}
        if new_member not in existing_members:
            existing_members.append(new_member)
            
        group_payload = {"member": existing_members}
        response_group = requests.put(group_edit_url, headers=headers, json=group_payload, verify=False)
        response_group.raise_for_status()

        if response_group.json().get("status") == "success":
            return True, "User created and added to group."
        else:
            return False, f"Group Update Error: {response_group.text}"
    except requests.exceptions.RequestException as e:
        return False, str(e)

# --- Routes ของ Web App ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form['fullname']
        citizen_id = request.form['citizen_id']
        mobile_no = request.form.get('mobile_no', '')

        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))

        success, message = create_fortigate_user(username, password, fullname)
        
        if success:
            try:
                db = get_db()
                cursor = db.cursor()
                cursor.execute(
                    "INSERT INTO guests (fullname, citizen_id, mobile_no, username, password, status) VALUES (?, ?, ?, ?, ?, ?)",
                    (fullname, citizen_id, mobile_no, username, password, 'active')
                )
                db.commit()
                return render_template('registered.html', 
                                       username=username, 
                                       password=password)
            except sqlite3.IntegrityError:
                return "Error: This ID is already registered.", 400
            except Exception as e:
                return f"Database Error: {e}", 500
        else:
            return f"Error creating FortiGate user: {message}", 500
            
    return render_template('register.html')

if __name__ == '__main__':
    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
    init_db()
    app.run(host='0.0.0.0', port=5000)