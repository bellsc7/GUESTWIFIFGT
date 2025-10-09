# ใช้ Python base image
FROM python:3.9-slim

# ตั้งค่า working directory
WORKDIR /app

# คัดลอกไฟล์ requirements และติดตั้ง dependencies
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# คัดลอกไฟล์แอปพลิเคชันทั้งหมด
COPY ./app .

# บอก Docker ว่าแอปของเราจะรันบน port 5000
EXPOSE 5000

# คำสั่งสำหรับรันแอปพลิเคชัน
CMD ["python", "main.py"]