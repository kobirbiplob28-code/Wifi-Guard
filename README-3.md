# WiFi Guard — Tenda F6 Access Control Tool

তোমার নিজের ওয়াইফাই নেটওয়ার্ক প্রোটেক্ট করার টুল — অচেনা ডিভাইস কানেক্ট হলে
রাউটারের MAC filter দিয়ে অটোমেটিক ব্লক করে দেয়।

## ধাপ ১ — Termux/Pydroid এ ইনস্টল করা

Termux এ:
```
pkg install python
pip install requests
```

Pydroid 3 এ: Pydroid এর নিজস্ব pip manager দিয়ে `requests` ইনস্টল করো (এটা সাধারণত
আগে থেকেই থাকে)।

## ধাপ ২ — Password বসানো

`wifi_guard.py` ফাইল খুলে এই লাইনটা খুঁজে বের করো:

```python
ROUTER_PASS = "CHANGE_ME"
```

`CHANGE_ME` এর জায়গায় তোমার রাউটারের admin panel password বসাও (192.168.0.1 এ
ব্রাউজার দিয়ে ঢুকলে যেটা দিয়ে লগইন করো)।

## ধাপ ৩ — এন্ডপয়েন্ট ভেরিফাই করা (গুরুত্বপূর্ণ)

Tenda F6 এর ঠিক কোন URL ব্যবহার করে device list আনে এবং MAC block করে, সেটা
firmware version ভেদে সামান্য আলাদা হতে পারে। তাই প্রথমে ভেরিফাই করে নাও:

1. ফোন/পিসির Chrome ব্রাউজারে যাও, `192.168.0.1` এ লগইন করো
2. Developer Tools (Chrome এ ⋮ মেনু > More tools > Developer tools, বা ডেস্কটপে F12) খুলে **Network** ট্যাবে যাও
3. রাউটারের admin panel এ "Connected Devices" বা "Device List" পেজে যাও — Network ট্যাবে যে request যায় (যেমন `getOnlineDevice` বা অন্য নাম) সেটা নোট করো
4. একইভাবে "MAC Filter / Access Control" পেজে গিয়ে কাউকে ব্লক করলে যে request যায় সেটাও নোট করো
5. `wifi_guard.py` এর `get_connected_devices()` আর `block_mac()` ফাংশনে থাকা URL গুলো (`/goform/getOnlineDevice`, `/goform/WifiMacFilterSet`) দরকার হলে ঠিক সেই অনুযায়ী বদলে দাও

আমাকে সেই actual endpoint/request details পাঠালে আমি script টা এক্সাক্টলি
তোমার রাউটারের জন্য ঠিক করে দিতে পারব।

## ধাপ ৪ — ব্যবহার

```bash
# প্রথমবার: নিজের সব ডিভাইস কানেক্ট রেখে ট্রাস্টেড লিস্ট বানাও
python3 wifi_guard.py --setup

# একবার scan করে দেখো কে কানেক্টেড, কে trusted/unknown
python3 wifi_guard.py --scan

# ক্রমাগত মনিটর করা শুরু করো — অচেনা কেউ এলে অটো ব্লক হবে
python3 wifi_guard.py --monitor
```

`--monitor` চালু রাখলে script প্রতি ২০ সেকেন্ডে scan করবে এবং trusted list
এ নেই এমন কোনো MAC পেলে সাথে সাথে ব্লক করে দিবে। সব activity
`wifi_guard.log` ফাইলে সেভ হবে।

## নতুন ডিভাইস trust করতে চাইলে

`trusted_devices.json` ফাইল খুলে `trusted_macs` লিস্টে নতুন MAC address
(বড় হাতের অক্ষরে, যেমন `"AA:BB:CC:DD:EE:FF"`) যোগ করে সেভ করো।
