#!/usr/bin/env python3
"""
discover_endpoints.py
----------------------
তোমার Tenda F6 রাউটারের আসল web API endpoint গুলো খুঁজে বের করার টুল।

রাউটারের মূল পেজ আর তার সাথে লোড হওয়া সব JavaScript ফাইল ডাউনলোড করে,
তার ভেতরে "goform/..." প্যাটার্নের সব endpoint নাম খুঁজে দেখায়।
এভাবে wifi_guard.py এ কোন endpoint বসাতে হবে সেটা বের করা যাবে।

ব্যবহার:
    python3 discover_endpoints.py
"""

import re
import sys
import requests
from urllib.parse import urljoin

ROUTER_IP = "192.168.0.1"
BASE_URL = f"http://{ROUTER_IP}"


def fetch(url):
    try:
        r = requests.get(url, timeout=6)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  [skip] {url} -> {e}")
        return ""


def main():
    print(f"[*] {BASE_URL} থেকে মূল পেজ আনা হচ্ছে...")
    html = fetch(BASE_URL + "/")
    if not html:
        print("[!] মূল পেজ আনা যায়নি। রাউটারের সাথে ওয়াইফাই কানেক্টেড কিনা চেক করো।")
        sys.exit(1)

    # সব <script src="..."> খুঁজে বের করা
    script_srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html)
    print(f"[*] {len(script_srcs)} টি script ফাইল পাওয়া গেছে।")

    all_js = html
    for src in script_srcs:
        full_url = urljoin(BASE_URL + "/", src)
        print(f"  -> ডাউনলোড হচ্ছে: {full_url}")
        js = fetch(full_url)
        all_js += "\n" + js

    # goform/xxx প্যাটার্ন খোঁজা
    endpoints = sorted(set(re.findall(r'goform/[A-Za-z0-9_]+', all_js)))
    # login সম্পর্কিত অন্য যেকোনো endpoint
    login_like = sorted(set(re.findall(r'["\'](/[A-Za-z0-9_/]*[Ll]ogin[A-Za-z0-9_/]*)["\']', all_js)))

    print("\n========== পাওয়া goform endpoint গুলো ==========")
    if endpoints:
        for e in endpoints:
            print(f"  {e}")
    else:
        print("  কিছু পাওয়া যায়নি (JS ফাইল obfuscated/encrypted হতে পারে)")

    print("\n========== Login-সম্পর্কিত endpoint ==========")
    if login_like:
        for e in login_like:
            print(f"  {e}")
    else:
        print("  কিছু পাওয়া যায়নি")

    print("\n[i] উপরের তালিকা থেকে device-list আর mac-filter/block সম্পর্কিত")
    print("    endpoint নাম দুটো (যেমন 'goform/GetSysStatus', 'goform/WifiMacFilter' ইত্যাদি)")
    print("    আমাকে কপি করে পাঠাও — আমি wifi_guard.py আপডেট করে দিব।")


if __name__ == "__main__":
    main()
