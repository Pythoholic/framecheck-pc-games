from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import tkinter as tk
from tkinter import messagebox, ttk
from urllib.request import Request, urlopen
from urllib.parse import quote
from urllib.error import HTTPError
import webbrowser
from report_view import render


CORE_GAMES = [
    (2483190, "Forza Horizon 6"),
    (3764200, "Resident Evil Requiem"),
    (3321460, "Crimson Desert"),
    (3017860, "DOOM: The Dark Ages"),
    (1285190, "Borderlands 4"),
    (2807960, "Battlefield 6"),
    (2246340, "Monster Hunter Wilds"),
    (2947440, "SILENT HILL f"),
    (2677660, "Indiana Jones and the Great Circle"),
]
CORE_SNAPSHOT = {
    2483190: (
        "OS: Windows 10 22H2\nProcessor: Intel i5-8400 / AMD Ryzen 5 1600\nMemory: 16 GB RAM\nGraphics: NVIDIA GTX 1650 / AMD RX 6500 XT\nStorage: 167 GB available space\nAdditional Notes: SSD required.",
        "OS: Windows 10 22H2\nProcessor: Intel i5-12400F / AMD Ryzen 5 5600X\nMemory: 16 GB RAM\nGraphics: NVIDIA RTX 3060 Ti / AMD RX 6700 XT\nStorage: 167 GB available space\nAdditional Notes: SSD required.",
    ),
    3764200: (
        "OS: Windows 11\nProcessor: Intel i5-8500 / AMD Ryzen 5 3500\nMemory: 16 GB RAM\nGraphics: NVIDIA GTX 1660 6GB / AMD RX 5500 XT 8GB\nAdditional Notes: SSD required.",
        "OS: Windows 11\nProcessor: Intel i7-8700 / AMD Ryzen 5 5500\nMemory: 16 GB RAM\nGraphics: NVIDIA RTX 2060 Super 8GB / AMD RX 6600 8GB\nAdditional Notes: SSD required.",
    ),
    3321460: (
        "OS: Windows 10\nProcessor: Intel i5-8500 / AMD Ryzen 5 2600X\nMemory: 16 GB RAM\nGraphics: NVIDIA GTX 1060 / AMD RX 5500 XT\nStorage: 180 GB available space\nAdditional Notes: SSD required.",
        "OS: Windows 10\nProcessor: Intel i5-11600K / AMD Ryzen 5 5600\nMemory: 16 GB RAM\nGraphics: NVIDIA RTX 2080 / AMD RX 6700 XT\nStorage: 180 GB available space\nAdditional Notes: SSD required.",
    ),
    3017860: (
        "OS: Windows 10 / Windows 11\nProcessor: AMD Ryzen 7 3700X or better\nMemory: 16 GB RAM\nGraphics: NVIDIA RTX 2060 Super 8GB or better\nStorage: 100 GB available space\nAdditional Notes: NVMe SSD required.",
        "OS: Windows 10 / Windows 11\nProcessor: AMD Ryzen 7 5700X or better\nMemory: 32 GB RAM\nGraphics: NVIDIA RTX 3080 10GB or better\nStorage: 100 GB available space\nAdditional Notes: NVMe SSD required.",
    ),
    1285190: (
        "OS: Windows 10 / Windows 11\nProcessor: Intel i7-9700 / AMD Ryzen 7 2700X\nMemory: 16 GB RAM\nGraphics: NVIDIA RTX 2070 / AMD RX 5700 XT\nStorage: 100 GB available space\nAdditional Notes: SSD required; 8 GB VRAM required.",
        "OS: Windows 10 / Windows 11\nProcessor: Intel i7-12700 / AMD Ryzen 7 5800X\nMemory: 32 GB RAM\nGraphics: NVIDIA RTX 3080 / AMD RX 6800 XT\nStorage: 100 GB available space\nAdditional Notes: SSD required.",
    ),
    2807960: (
        "OS: Windows 10\nProcessor: Intel i5-8400 / AMD Ryzen 5 2600\nMemory: 16 GB RAM\nGraphics: NVIDIA RTX 2060 6GB / AMD RX 5600 XT\nStorage: 55 GB available space\nAdditional Notes: Secure Boot, TPM 2.0, HVCI and VBS required.",
        "OS: Windows 11\nProcessor: Intel i7-10700 / AMD Ryzen 7 3700X\nMemory: 16 GB RAM\nGraphics: NVIDIA RTX 3060 Ti 8GB / AMD RX 6700 XT\nStorage: 80 GB available space\nAdditional Notes: SSD; Secure Boot, TPM 2.0, HVCI and VBS required.",
    ),
    2246340: (
        "OS: Windows 10 / Windows 11\nProcessor: AMD Ryzen 5 3600\nMemory: 16 GB RAM\nGraphics: NVIDIA GTX 1660 6GB / AMD RX 5500 XT 8GB\nStorage: 75 GB available space\nAdditional Notes: SSD required.",
        "OS: Windows 10 / Windows 11\nProcessor: AMD Ryzen 5 3600\nMemory: 16 GB RAM\nGraphics: NVIDIA RTX 2060 Super 8GB / AMD RX 6600 8GB\nStorage: 75 GB available space\nAdditional Notes: SSD required.",
    ),
    2947440: (
        "OS: Windows 11\nProcessor: Intel i5-8400 / AMD Ryzen 5 2600\nMemory: 16 GB RAM\nGraphics: NVIDIA GTX 1070 Ti / AMD RX 5700\nStorage: 50 GB available space\nAdditional Notes: SSD recommended.",
        "OS: Windows 11\nProcessor: Intel i7-9700 / AMD Ryzen 5 5500\nMemory: 16 GB RAM\nGraphics: NVIDIA RTX 2080 / AMD RX 6800 XT\nStorage: 50 GB available space\nAdditional Notes: SSD required.",
    ),
    2677660: (
        "OS: Windows 10\nProcessor: Intel i7-10700K / AMD Ryzen 5 3600\nMemory: 16 GB RAM\nGraphics: NVIDIA RTX 2060 Super 8GB / AMD RX 6600 8GB\nStorage: 120 GB available space\nAdditional Notes: SSD and GPU hardware ray tracing required.",
        "OS: Windows 10\nProcessor: Intel i7-12700K / AMD Ryzen 7 7700\nMemory: 32 GB RAM\nGraphics: NVIDIA RTX 3080 Ti 12GB / AMD RX 7700 XT 12GB\nStorage: 120 GB available space\nAdditional Notes: SSD and GPU hardware ray tracing required.",
    ),
}
NON_GAME_APPS = {431960}  # Wallpaper Engine is classified as a game by the Store API.


class StoreUnavailableError(RuntimeError):
    pass

GPU_RANK = {
    "1050": 10, "1060": 20, "1070": 28, "1070 ti": 32, "1080": 35,
    "1650": 15, "1660": 25, "1660 super": 27, "2060": 30,
    "2060 super": 34, "2070": 38, "2080": 45, "2080 ti": 50,
    "3050": 28, "3060": 40, "3060 ti": 48, "3070": 55,
    "3070 ti": 59, "3080": 70, "3080 ti": 76, "3090": 80,
    "4060": 38, "4060 ti": 47, "4070": 63, "4070 super": 70,
    "4070 ti": 75, "4070 ti super": 79, "4080": 85,
    "4080 super": 88, "4090": 100,
    "5060": 42, "5060 ti": 52, "5070": 65, "5070 ti": 81,
    "5080": 90, "5090": 110,
}


class RequirementText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("br", "li", "p"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("li", "p"):
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)


def plain(value):
    p = RequirementText()
    p.feed(value or "")
    return "\n".join(line.strip() for line in "".join(p.parts).splitlines() if line.strip())


def field(text, label):
    m = re.search(r"^" + re.escape(label) + r":\s*(.+)$", text, re.I | re.M)
    return m.group(1).strip() if m else ""


def fetch_json(url):
    req = Request(url, headers={"User-Agent": "FrameCheck/1.0 (Windows desktop hardware report)", "Accept": "application/json", "Cache-Control": "no-cache"})
    with urlopen(req, timeout=16) as response:
        return json.load(response)


def scan_hardware():
    script = r'''$ErrorActionPreference='SilentlyContinue'; $o=[ordered]@{Computer=Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer,Model,TotalPhysicalMemory;InstalledMemory=(Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property Capacity -Sum).Sum;CPU=Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors;GPU=Get-CimInstance Win32_VideoController | Select-Object Name;OS=Get-CimInstance Win32_OperatingSystem | Select-Object Caption,OSArchitecture;Volumes=@(Get-Partition | Where-Object DriveLetter | ForEach-Object {$v=Get-Volume -DriveLetter $_.DriveLetter; $d=Get-Disk -Number $_.DiskNumber; $pd=Get-PhysicalDisk | Where-Object FriendlyName -eq $d.FriendlyName | Select-Object -First 1; [pscustomobject]@{Drive=$_.DriveLetter;Free=$v.SizeRemaining;Disk=$d.FriendlyName;Bus=$d.BusType;MediaType=$pd.MediaType}})}; $o | ConvertTo-Json -Depth 5 -Compress'''
    result = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True, timeout=25, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode or not result.stdout.strip():
        raise RuntimeError("Windows hardware scan failed: " + result.stderr.strip()[:300])
    info = json.loads(result.stdout)
    gpu = next((g["Name"] for g in as_list(info.get("GPU")) if "NVIDIA" in g.get("Name", "").upper()), "")
    if not gpu:
        gpu = as_list(info.get("GPU"))[0].get("Name", "Unknown GPU")
    info["SelectedGPU"] = gpu
    info["VRAMMiB"] = None
    try:
        smi = subprocess.run(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=8, creationflags=subprocess.CREATE_NO_WINDOW)
        info["VRAMMiB"] = int(smi.stdout.strip().splitlines()[0].strip())
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
        pass
    return info


def as_list(value):
    return value if isinstance(value, list) else ([value] if value else [])


def nvidia_model(text):
    m = re.search(r"(?:RTX|GTX)\s*(\d{4})(?:\s*(Ti|SUPER))?", text or "", re.I)
    if not m:
        return ""
    return (m.group(1) + (" " + m.group(2).lower() if m.group(2) else "")).lower()


def cpu_result(cpu, requirement):
    own = re.search(r"Ryzen\W*(\d)\W*(\d{4})", cpu or "", re.I)
    target = re.search(r"Ryzen\W*(\d)\W*(\d{4})", requirement or "", re.I)
    if own and target:
        own_gen, own_tier, own_model = int(own.group(2)[0]), int(own.group(1)), int(own.group(2))
        tgt_gen, tgt_tier, tgt_model = int(target.group(2)[0]), int(target.group(1)), int(target.group(2))
        if own_gen > tgt_gen and own_tier >= tgt_tier:
            return True
        if own_gen == tgt_gen:
            return own_tier >= tgt_tier and own_model >= tgt_model
        return None
    if "zen 3" in requirement.lower() and own and int(own.group(2)[0]) >= 5:
        return True
    if "zen 2" in requirement.lower() and own and int(own.group(2)[0]) >= 3:
        return True
    return None


def requested_vram(graphics, notes):
    combined = graphics + " " + notes
    matches = re.findall(r"(\d+(?:\.\d+)?)\s*GB\s*(?:dedicated\s*)?(?:V(?:ideo\s*)?RAM|VRAM)", combined, re.I)
    matches += re.findall(r"(?:VRAM|video memory)\s*(?:of|:|=|minimum|required)?\s*(\d+(?:\.\d+)?)\s*GB", combined, re.I)
    graphics_matches = re.findall(r"(?:RTX|GTX)\s*\d{4}(?:\s*(?:Ti|Super))?\s*\(?\s*(\d+)\s*GB", graphics, re.I)
    matches += graphics_matches
    return max(map(float, matches)) if matches else None


def ram_gb(text):
    m = re.search(r"(?:Memory|RAM):\s*(\d+)\s*GB", text, re.I)
    return int(m.group(1)) if m else None


def storage_gb(text):
    m = re.search(r"(?:Storage|Hard Drive):\s*(\d+)\s*GB", text, re.I)
    return int(m.group(1)) if m else None


def evaluate(info, requirements, appid):
    if not requirements:
        return []
    checks = []
    cpu_have = info["CPU"]["Name"].strip()
    cpu_need = field(requirements, "Processor")
    cpu_match = cpu_result(cpu_have, cpu_need) if cpu_need else None
    checks.append({"label": "Processor", "actual": cpu_have, "required": cpu_need or "Not stated", "status": "pass" if cpu_match is True else ("review" if cpu_need else "na")})

    gpu_have = info["SelectedGPU"]
    gpu_need = field(requirements, "Graphics") or field(requirements, "Graphics Card")
    have_model = nvidia_model(gpu_have)
    need_model = nvidia_model(gpu_need)
    if not gpu_need:
        gpu_status = "na"
    elif have_model in GPU_RANK and need_model in GPU_RANK:
        gpu_status = "pass" if GPU_RANK[have_model] >= GPU_RANK[need_model] else "fail"
    else:
        gpu_status = "review"
    checks.append({"label": "Graphics", "actual": gpu_have, "required": gpu_need or "Not stated", "status": gpu_status})

    vram_have = info.get("VRAMMiB")
    vram_need = requested_vram(gpu_need, field(requirements, "Additional Notes"))
    vram_status = "na" if vram_need is None else ("review" if vram_have is None else ("pass" if vram_have >= vram_need * 1000 else "fail"))
    checks.append({"label": "VRAM", "actual": f"{vram_have / 1024:.0f} GB" if vram_have else "Unknown", "required": f"{vram_need:g} GB" if vram_need else "Not stated", "status": vram_status})

    ram_need = ram_gb(requirements)
    ram_have = (info.get("InstalledMemory") or info["Computer"]["TotalPhysicalMemory"]) / 1024**3
    checks.append({"label": "Memory", "actual": f"{ram_have:.0f} GB", "required": f"{ram_need} GB" if ram_need else "Not stated", "status": "na" if ram_need is None else ("pass" if ram_have >= ram_need else "fail")})

    os_have = info["OS"]["Caption"]
    os_need = field(requirements, "OS")
    needs_10 = bool(re.search(r"Windows\W*10", os_need, re.I))
    needs_11 = bool(re.search(r"Windows\W*11", os_need, re.I))
    os_status = "na" if not os_need else ("pass" if ("Windows 11" in os_have and (needs_10 or needs_11)) or ("Windows 10" in os_have and needs_10) else "review")
    checks.append({"label": "Windows", "actual": os_have, "required": os_need or "Not stated", "status": os_status})

    space = storage_gb(requirements)
    volumes = as_list(info.get("Volumes"))
    disk_req = "NVMe SSD" if "NVME" in requirements.upper() else ("SSD" if "SSD" in requirements.upper() else "Any drive")
    if space is None:
        disk_status = "na"
    else:
        eligible = [v for v in volumes if (v.get("Free") or 0) >= space * 1_000_000_000]
        if disk_req == "NVMe SSD":
            eligible = [v for v in eligible if str(v.get("Bus", "")).upper() == "NVME"]
        elif disk_req == "SSD":
            eligible = [v for v in eligible if str(v.get("Bus", "")).upper() == "NVME" or str(v.get("MediaType", "")).upper() == "SSD"]
        disk_status = "pass" if eligible else "fail"
    drive_text = ", ".join(f'{v.get("Drive")}: {(v.get("Free") or 0)/1024**3:.0f} GiB' for v in volumes)
    checks.append({"label": "Storage", "actual": drive_text or "Unknown", "required": f"{space} GB · {disk_req}" if space else "Not stated", "status": disk_status})

    if appid == 2807960:
        checks.append({"label": "Launch checks", "actual": "Not verified", "required": "Secure Boot, TPM 2.0, HVCI and VBS", "status": "review"})
    return checks


def verdict_for(checks):
    if not checks:
        return "unavailable", "This tier has no published PC requirements."
    failed = [c["label"] for c in checks if c["status"] == "fail"]
    review = [c["label"] for c in checks if c["status"] == "review"]
    if failed:
        return "below", "Below the listed tier on " + ", ".join(failed) + ". Open the detail checks for the exact comparison."
    if review:
        return "review", "Hardware comparison needs review for " + ", ".join(review) + ". Open the detail checks for the source values."
    return "meets", "The listed hardware and storage checks pass. Actual FPS and game-specific launch settings are not measured."


def game_data(appid, fallback):
    payload = fetch_json(f"https://store.steampowered.com/api/appdetails?appids={appid}&l=english&cc=us")
    item = payload.get(str(appid), {})
    if not item.get("success"):
        raise StoreUnavailableError("Store listing unavailable")
    data = item.get("data", {})
    req = data.get("pc_requirements") or {}
    return {"id": appid, "name": data.get("name") or fallback, "type": data.get("type"), "release": (data.get("release_date") or {}).get("date") or "", "image": data.get("header_image") or "", "minimum": plain(req.get("minimum")), "recommended": plain(req.get("recommended")), "url": f"https://store.steampowered.com/app/{appid}/"}


def recent_ids():
    data = fetch_json("https://store.steampowered.com/api/featuredcategories/?cc=us&l=english")
    return [(int(x["id"]), x["name"]) for x in data.get("new_releases", {}).get("items", []) if x.get("id")]


def browse_metadata(appids):
    payload = {"ids": [{"appid": appid} for appid in appids], "context": {"country_code": "US"}, "data_request": {"include_basic_info": True, "include_assets": True}}
    url = "https://api.steampowered.com/IStoreBrowseService/GetItems/v1/?input_json=" + quote(json.dumps(payload, separators=(",", ":")))
    result = fetch_json(url)
    found = {}
    for item in result.get("response", {}).get("store_items", []):
        appid = item.get("appid")
        if not appid:
            continue
        assets = item.get("assets") or {}
        image_format = assets.get("asset_url_format") or ""
        capsule = assets.get("main_capsule") or ""
        image = "https://shared.akamai.steamstatic.com/store_item_assets/" + image_format.replace("${FILENAME}", capsule) if image_format and capsule else ""
        found[appid] = {"name": item.get("name") or str(appid), "image": image}
    return found


def cache_path():
    location = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "FrameCheck"
    location.mkdir(parents=True, exist_ok=True)
    return location / "requirements-cache.json"


def load_cache():
    try:
        data = json.loads(cache_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def fetch_cached_game(appid, name, cached, rate_limited):
    record = cached.get(str(appid))
    if rate_limited.is_set():
        if record and record.get("game"):
            return record["game"], "stale"
        raise RuntimeError("Steam store details are temporarily rate limited")
    try:
        return game_data(appid, name), "fresh"
    except HTTPError as ex:
        if ex.code in (403, 429):
            rate_limited.set()
        if record and record.get("game"):
            return record["game"], "stale"
        raise
    except Exception:
        if record and record.get("game"):
            return record["game"], "stale"
        raise


def chart_games():
    data = fetch_json("https://api.steampowered.com/ISteamChartsService/GetMostPlayedGames/v1/")
    return data.get("response", {}).get("ranks", [])[:100]


def start_lookup_server(info, games):
    allowed = {game["id"] for game in games}
    save_lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def send_result(self, code, result):
            body = json.dumps(result, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            match = re.fullmatch(r"/game/(\d+)", self.path)
            appid = int(match.group(1)) if match else 0
            if appid not in allowed:
                self.send_result(404, {"error": "Unknown game"})
                return
            try:
                game = game_data(appid, str(appid))
                game["freshness"] = "fresh"
                game["minimum_checks"] = evaluate(info, game.get("minimum", ""), appid)
                game["recommended_checks"] = evaluate(info, game.get("recommended", ""), appid)
                if game["recommended_checks"]:
                    game["verdict"], game["reason"] = verdict_for(game["recommended_checks"])
                elif game["minimum_checks"]:
                    result, reason = verdict_for(game["minimum_checks"])
                    game["verdict"] = "below" if result == "below" else "minimum"
                    game["reason"] = "No recommended tier is published. Minimum tier: " + reason
                else:
                    game["verdict"], game["reason"] = "unavailable", "No PC requirements were returned for this game."
                if game.get("minimum"):
                    with save_lock:
                        records = load_cache()
                        stored = {key: game.get(key) for key in ("id", "name", "type", "release", "image", "minimum", "recommended", "url")}
                        records[str(appid)] = {"fetched": time.time(), "game": stored}
                        cache_path().write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
                self.send_result(200, game)
            except Exception as ex:
                self.send_result(503, {"error": str(ex)[:150]})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def run_scan(status, live=False):
    status("Scanning hardware…")
    info = scan_hardware()
    errors = []
    catalog = {}
    for appid, name in CORE_GAMES:
        catalog[appid] = {"name": name, "categories": ["core"], "rank": None, "peak": None}

    status("Reading Steam's top played chart…")
    try:
        chart = chart_games()
        for row in chart:
            appid = int(row["appid"])
            entry = catalog.setdefault(appid, {"name": str(appid), "categories": [], "rank": None, "peak": None})
            entry["categories"].append("popular")
            entry["rank"] = row.get("rank")
            entry["peak"] = row.get("peak_in_game")
        metadata = browse_metadata([int(row["appid"]) for row in chart])
        for appid, item in metadata.items():
            catalog[appid]["name"] = item["name"]
            catalog[appid]["image"] = item["image"]
    except Exception as ex:
        errors.append("Top played chart: " + str(ex)[:100])

    status("Reading Steam's new releases…")
    try:
        for appid, name in recent_ids()[:10]:
            entry = catalog.setdefault(appid, {"name": name, "categories": [], "rank": None, "peak": None})
            if "new" not in entry["categories"]:
                entry["categories"].append("new")
    except Exception as ex:
        errors.append("New releases: " + str(ex)[:100])

    status(f"Fetching requirements for {len(catalog)} games…")
    games = []
    core_ids = {appid for appid, _ in CORE_GAMES}
    cached = load_cache()
    updated_cache = dict(cached)
    rate_limited = threading.Event()
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = {pool.submit(fetch_cached_game, appid, item["name"], cached, rate_limited): (appid, item) for appid, item in catalog.items()}
        for completed, future in enumerate(as_completed(jobs), 1):
            appid, item = jobs[future]
            if completed % 8 == 0 or completed == len(jobs):
                status(f"Checked {completed} of {len(jobs)} Steam listings…")
            try:
                game, freshness = future.result()
                game = dict(game)
                if freshness == "fresh":
                    updated_cache[str(appid)] = {"fetched": time.time(), "game": dict(game)}
            except Exception as ex:
                if isinstance(ex, StoreUnavailableError) and appid not in core_ids:
                    continue
                message = str(ex)
                if not rate_limited.is_set() or not any("rate limited" in issue.lower() for issue in errors):
                    errors.append(f'{item["name"]}: {message[:90]}')
                snapshot = CORE_SNAPSHOT.get(appid)
                freshness = "snapshot" if snapshot else "unavailable"
                game = {"id": appid, "name": item["name"], "type": "game", "release": "", "image": item.get("image", ""), "minimum": snapshot[0] if snapshot else "", "recommended": snapshot[1] if snapshot else "", "url": f"https://store.steampowered.com/app/{appid}/"}
            if appid in NON_GAME_APPS or (appid not in core_ids and game.get("type") != "game"):
                continue
            if not game.get("image"):
                game["image"] = item.get("image", "")
            game["categories"] = item["categories"]
            game["rank"] = item["rank"]
            game["peak"] = item["peak"]
            game["freshness"] = freshness
            game["minimum_checks"] = evaluate(info, game.get("minimum", ""), appid)
            game["recommended_checks"] = evaluate(info, game.get("recommended", ""), appid)
            if game["recommended_checks"]:
                game["verdict"], game["reason"] = verdict_for(game["recommended_checks"])
            elif game["minimum_checks"]:
                minimum_verdict, minimum_reason = verdict_for(game["minimum_checks"])
                game["verdict"] = "below" if minimum_verdict == "below" else "minimum"
                game["reason"] = "No recommended tier is published. Minimum tier: " + minimum_reason
            else:
                game["verdict"], game["reason"] = "unavailable", "No PC requirements were returned for this game."
            games.append(game)

    try:
        cache_path().write_text(json.dumps(updated_cache, ensure_ascii=False), encoding="utf-8")
    except OSError as ex:
        errors.append("Could not save requirements cache: " + str(ex)[:90])
    if not games:
        raise RuntimeError("No games were returned. Check your internet connection and try again.")
    games.sort(key=lambda g: (g["rank"] is None, g["rank"] or 999, 0 if "core" in g["categories"] else 1, g["name"].lower()))
    fresh_count = sum(game["freshness"] == "fresh" for game in games)
    fallback_count = sum(game["freshness"] in ("stale", "snapshot") for game in games)
    server = start_lookup_server(info, games) if live else None
    report = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent / "Game Readiness Report.html"
    report.write_text(render(info, games, errors, server.server_port if server else 0), encoding="utf-8")
    return report, len(games), errors, server, fresh_count, fallback_count


def main():
    root = tk.Tk()
    root.title("FrameCheck · PC Game Compatibility")
    root.geometry("490x330")
    root.resizable(False, False)
    root.configure(bg="#0d131a")
    title = tk.Label(root, text="FRAMECHECK", bg="#0d131a", fg="#c6f36a", font=("Segoe UI", 12, "bold"))
    title.pack(anchor="w", padx=28, pady=(24, 6))
    heading = tk.Label(root, text="Your PC. Game requirements.", bg="#0d131a", fg="#edf3f4", font=("Segoe UI", 20, "bold"))
    heading.pack(anchor="w", padx=28)
    description = tk.Label(root, text="Scan hardware, fetch current requirements, and create a report.", bg="#0d131a", fg="#9eafb8", font=("Segoe UI", 10))
    description.pack(anchor="w", padx=28, pady=(5, 20))
    status_text = tk.StringVar(value="Starting scan…")
    tk.Label(root, textvariable=status_text, bg="#0d131a", fg="#b9c8ce", font=("Segoe UI", 10), wraplength=425, justify="left", height=3).pack(anchor="w", padx=28)
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("FrameCheck.Horizontal.TProgressbar", troughcolor="#24313a", background="#c6f36a", borderwidth=0, thickness=6)
    progress = ttk.Progressbar(root, mode="indeterminate", style="FrameCheck.Horizontal.TProgressbar")
    progress.pack(fill="x", padx=28, pady=(8, 0))
    frame = tk.Frame(root, bg="#0d131a")
    frame.pack(anchor="w", padx=28, pady=18)
    scan_button = tk.Button(frame, text="Scanning…", bg="#24313a", fg="#9eafb8", disabledforeground="#9eafb8", activebackground="#d9ff90", bd=0, padx=17, pady=9, font=("Segoe UI", 10, "bold"), cursor="arrow", state="disabled")
    scan_button.pack(side="left")
    open_button = tk.Button(frame, text="Open report", bg="#19242c", fg="#71838d", disabledforeground="#71838d", activebackground="#334550", bd=0, padx=17, pady=9, font=("Segoe UI", 10), cursor="arrow", state="disabled")
    open_button.pack(side="left", padx=10)
    report_path = [None]
    lookup_server = [None]

    def status(message):
        root.after(0, status_text.set, message)

    def done(path, count, errors, server, fresh_count, fallback_count):
        progress.stop()
        progress.configure(mode="determinate", value=100)
        if lookup_server[0]:
            lookup_server[0].shutdown()
        lookup_server[0] = server
        report_path[0] = path
        summary = f"Report ready · {count} games · {fresh_count} fresh"
        if fallback_count:
            summary += f" · {fallback_count} fallback"
        if errors:
            summary += f" · {len(errors)} lookup issue{'s' if len(errors) != 1 else ''}"
        status_text.set(summary + ". Keep this window open for on-demand checks.")
        scan_button.config(state="normal", text="Scan again", bg="#c6f36a", fg="#17200e", cursor="hand2")
        open_button.config(state="normal", text="Open report", bg="#24313a", fg="#edf3f4", cursor="hand2")
        webbrowser.open(path.as_uri())

    def failed(error):
        progress.stop()
        progress.configure(mode="determinate", value=0)
        status_text.set("Scan failed. Check the error and try again.")
        scan_button.config(state="normal", text="Retry scan", bg="#c6f36a", fg="#17200e", cursor="hand2")
        if report_path[0]:
            open_button.config(state="normal", text="Open previous report", bg="#24313a", fg="#edf3f4", cursor="hand2")
        messagebox.showerror("FrameCheck", str(error))

    def start():
        status_text.set("Scanning hardware…")
        scan_button.config(state="disabled", text="Scanning…", bg="#24313a", fg="#9eafb8", cursor="arrow")
        open_button.config(state="disabled", bg="#19242c", fg="#71838d", cursor="arrow")
        progress.configure(mode="indeterminate", value=0)
        progress.start(12)
        def task():
            try:
                result = run_scan(status, live=True)
                root.after(0, done, *result)
            except Exception as ex:
                root.after(0, failed, ex)
        threading.Thread(target=task, daemon=True).start()

    scan_button.config(command=start)
    open_button.config(command=lambda: webbrowser.open(report_path[0].as_uri()) if report_path[0] else None)
    root.protocol("WM_DELETE_WINDOW", lambda: (lookup_server[0].shutdown() if lookup_server[0] else None, root.destroy()))
    root.after(0, start)
    root.mainloop()


if __name__ == "__main__":
    if os.getenv("FRAMECHECK_TEST_MODE") == "1":
        run_scan(lambda message: None)
    else:
        main()
