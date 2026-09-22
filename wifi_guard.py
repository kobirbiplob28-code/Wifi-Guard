#!/usr/bin/env python3
"""
WiFi Guard - Tenda F6 Access Control Tool
-------------------------------------------
নিজের ওয়াইফাই নেটওয়ার্ক প্রোটেক্ট করার জন্য একটি defensive security tool।

কী করে:
  1. রাউটারে (Tenda F6, 192.168.0.1) কানেক্টেড সব ডিভাইসের তালিকা আনে
  2. trusted_devices.json ফাইলে থাকা MAC address এর সাথে compare করে
  3. অচেনা (untrusted) কোনো ডিভাইস পেলে সাথে সাথে রাউটারের MAC filter দিয়ে
     ব্লক করে দেয় এবং লগ ফাইলে/স্ক্রিনে জানায়

ব্যবহার:
    python3 wifi_guard.py --setup        # প্রথমবার ট্রাস্টেড ডিভাইস লিস্ট বানানো
    python3 wifi_guard.py --scan         # একবার scan করে দেখানো
    python3 wifi_guard.py --monitor      # ক্রমাগত মনিটর ও অটো-ব্লক করা
"""

import json
import time
import os
import sys
import argparse
from datetime import datetime

try:
    import requests
except ImportError:
    print("[!] 'requests' লাইব্রেরি নেই। ইনস্টল করো: pip install requests")
    sys.exit(1)

# ---------------- কনফিগারেশন ----------------
ROUTER_IP = "192.168.0.1"
ROUTER_USER = "admin"          # তোমার admin username (সাধারণত admin)
ROUTER_PASS = "CHANGE_ME"      # <-- এখানে তোমার রাউটার admin password বসাও

TRUSTED_FILE = os.path.join(os.path.dirname(__file__), "trusted_devices.json")
LOG_FILE = os.path.join(os.path.dirname(__file__), "wifi_guard.log")

SCAN_INTERVAL_SECONDS = 20  # কত সেকেন্ড পরপর scan করবে


# ---------------- লগিং ----------------
def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ---------------- Trusted device list ----------------
def load_trusted() -> set:
    if not os.path.exists(TRUSTED_FILE):
        return set()
    with open(TRUSTED_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return set(mac.upper() for mac in data.get("trusted_macs", []))


def save_trusted(mac_set: set):
    with open(TRUSTED_FILE, "w", encoding="utf-8") as f:
        json.dump({"trusted_macs": sorted(mac_set)}, f, indent=2, ensure_ascii=False)


# ---------------- Tenda router communication ----------------
class TendaRouter:
    """
    Tenda F6 (N300 সিরিজ) এর সাথে যোগাযোগের জন্য।
    F6 সাধারণত N301-এর মতো একই ধরনের /goform/ web API ব্যবহার করে।
    যদি এই এন্ডপয়েন্টগুলো কাজ না করে, ব্রাউজার থেকে রাউটারে লগইন করে
    Developer Tools > Network ট্যাবে গিয়ে আসল endpoint বের করে এখানে বসাতে হবে।
    """

    def __init__(self, ip: str, username: str, password: str):
        self.base_url = f"http://{ip}"
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.logged_in = False

    def login(self) -> bool:
        try:
            resp = self.session.post(
                f"{self.base_url}/login/Auth",
                data={"username": self.username, "password": self.password},
                timeout=5,
            )
            if resp.status_code == 200:
                self.logged_in = True
                return True
        except requests.RequestException as e:
            log(f"[ERROR] রাউটারে login করতে সমস্যা: {e}")
        return False

    def get_connected_devices(self):
        """
        রাউটারে বর্তমানে কানেক্টেড ডিভাইসের তালিকা আনে।
        Returns: list of dicts [{"mac": "...", "ip": "...", "name": "..."}]
        """
        try:
            resp = self.session.get(
                f"{self.base_url}/goform/getOnlineDevice",
                timeout=5,
            )
            resp.raise_for_status()
            data = resp.json()
            devices = []
            for d in data.get("list", data if isinstance(data, list) else []):
                devices.append({
                    "mac": d.get("mac", d.get("macAddr", "")).upper(),
                    "ip": d.get("ip", d.get("ipAddr", "")),
                    "name": d.get("name", d.get("hostname", "Unknown")),
                })
            return devices
        except Exception as e:
            log(f"[ERROR] ডিভাইস লিস্ট আনতে সমস্যা: {e}")
            return []

    def block_mac(self, mac: str) -> bool:
        """রাউটারের MAC filter দিয়ে দেওয়া MAC ব্লক করে।"""
        try:
            resp = self.session.post(
                f"{self.base_url}/goform/WifiMacFilterSet",
                data={"mac": mac, "action": "block"},
                timeout=5,
            )
            return resp.status_code == 200
        except Exception as e:
            log(f"[ERROR] {mac} ব্লক করতে সমস্যা: {e}")
            return False


# ---------------- Setup mode: প্রথমবার trusted list বানানো ----------------
def setup_trusted_list(router: TendaRouter):
    print("\n=== Trusted Device Setup ===")
    print("এখন তোমার নিজের সব ডিভাইস (ফোন, ল্যাপটপ ইত্যাদি) ওয়াইফাইতে কানেক্ট করে রাখো,")
    print("তারপর Enter চাপো — বর্তমানে কানেক্টেড সবাইকে 'trusted' হিসেবে সেভ করব।\n")
    input("রেডি হলে Enter চাপো...")

    if not router.login():
        print("[!] রাউটারে লগইন ব্যর্থ। ROUTER_PASS ঠিক আছে কিনা চেক করো।")
        return

    devices = router.get_connected_devices()
    if not devices:
        print("[!] কোনো ডিভাইস পাওয়া যায়নি। endpoint ঠিক আছে কিনা চেক করতে হতে পারে।")
        return

    print(f"\n{len(devices)} টি ডিভাইস পাওয়া গেছে:")
    for i, d in enumerate(devices, 1):
        print(f"  {i}. {d['name']} — MAC: {d['mac']} — IP: {d['ip']}")

    trusted = set(d["mac"] for d in devices)
    save_trusted(trusted)
    print(f"\n[✓] {len(trusted)} টি ডিভাইস trusted_devices.json এ সেভ হয়েছে।")


# ---------------- Scan mode: একবার দেখানো ----------------
def scan_once(router: TendaRouter):
    if not router.login():
        print("[!] রাউটারে লগইন ব্যর্থ।")
        return

    trusted = load_trusted()
    devices = router.get_connected_devices()

    print(f"\n{len(devices)} টি ডিভাইস বর্তমানে কানেক্টেড:\n")
    for d in devices:
        status = "✓ Trusted" if d["mac"] in trusted else "✗ UNKNOWN"
        print(f"  [{status}] {d['name']} — {d['mac']} — {d['ip']}")


# ---------------- Monitor mode: ক্রমাগত মনিটর + অটো-ব্লক ----------------
def monitor_loop(router: TendaRouter):
    trusted = load_trusted()
    if not trusted:
        print("[!] কোনো trusted device সেভ করা নেই। আগে --setup চালাও।")
        return

    log(f"মনিটরিং শুরু হলো। {len(trusted)} টি trusted device আছে।")
    blocked_already = set()

    while True:
        if not router.logged_in:
            router.login()

        devices = router.get_connected_devices()
        for d in devices:
            mac = d["mac"]
            if not mac:
                continue
            if mac not in trusted and mac not in blocked_already:
                log(f"[ALERT] অচেনা ডিভাইস পাওয়া গেছে: {d['name']} ({mac}, {d['ip']}) — ব্লক করা হচ্ছে...")
                if router.block_mac(mac):
                    log(f"[BLOCKED] {mac} সফলভাবে ব্লক করা হয়েছে।")
                    blocked_already.add(mac)
                else:
                    log(f"[FAILED] {mac} ব্লক করা যায়নি — router endpoint verify করো।")

        time.sleep(SCAN_INTERVAL_SECONDS)


# ---------------- Main ----------------
def main():
    parser = argparse.ArgumentParser(description="WiFi Guard - Tenda F6 Access Control")
    parser.add_argument("--setup", action="store_true", help="Trusted device list বানাও")
    parser.add_argument("--scan", action="store_true", help="একবার scan করো")
    parser.add_argument("--monitor", action="store_true", help="ক্রমাগত মনিটর ও অটো-ব্লক করো")
    args = parser.parse_args()

    if ROUTER_PASS == "CHANGE_ME":
        print("[!] প্রথমে script এর ভিতরে ROUTER_PASS বসাও (তোমার router admin password)।")
        sys.exit(1)

    router = TendaRouter(ROUTER_IP, ROUTER_USER, ROUTER_PASS)

    if args.setup:
        setup_trusted_list(router)
    elif args.scan:
        scan_once(router)
    elif args.monitor:
        monitor_loop(router)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
