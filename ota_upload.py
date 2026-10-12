import urllib.request
import os
import time

bin_path = r"c:\Users\Uzzo\Desktop\MACROPAD\build\MACROPAD.ino.bin"
if not os.path.exists(bin_path):
    print("Binary does not exist!")
    exit(1)

with open(bin_path, "rb") as f:
    bin_data = f.read()

print(f"Firmware binary size: {len(bin_data)} bytes")

boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="update"; filename="firmware.bin"\r\n'
    f"Content-Type: application/octet-stream\r\n\r\n"
).encode("utf-8") + bin_data + f"\r\n--{boundary}--\r\n".encode("utf-8")

req = urllib.request.Request(
    "http://192.168.1.58/update",
    data=body,
    headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(body)),
        "Connection": "close"
    }
)

try:
    print("Uploading firmware via HTTP OTA...")
    res = urllib.request.urlopen(req, timeout=45)
    print("HTTP OTA Response:", res.read().decode())
except Exception as e:
    print("OTA error:", e)
