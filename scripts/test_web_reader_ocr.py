#!/usr/bin/env python3
"""测试 /api/web-reader/ocr 接口（需先启动后端）"""
import json
import sys
import urllib.request

# 32x32 灰色 PNG（Qwen 要求宽高 >10px）
PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAIAAAD8GO2jAAAAM0lEQVR4nO3NMQEAMAyEwG+Uv/RKIEs2TgC8trk0p/U4WHCAHCAHyAFygBwgB8gBchDyAb49AcD7t0R0AAAAAElFTkSuQmCC"

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8081"
URL = f"{BASE}/api/web-reader/ocr"


def main():
    data = {"image": f"data:image/png;base64,{PNG_B64}"}
    req = urllib.request.Request(
        URL,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            out = json.loads(r.read().decode())
            print(json.dumps(out, ensure_ascii=False, indent=2))
            if out.get("success"):
                print("\n✅ OCR 接口正常")
            else:
                print("\n⚠️ OCR 返回失败:", out.get("error"))
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read().decode()[:500])
        sys.exit(1)
    except Exception as e:
        print("Error:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
