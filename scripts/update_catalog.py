#!/usr/bin/env python3
"""
Nuvizio Repository Catalog & Status Generator
Queries the GitHub API to update catalog.json, README.md, and profile/README.md.
"""

import json
import os
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

TOKEN = os.environ.get("GITHUB_TOKEN") or subprocess.run("gh auth token", shell=True, capture_output=True, text=True).stdout.strip()
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "nuvizio-catalog-updater"
}

def gh_api(endpoint):
    url = f"https://api.github.com/{endpoint.lstrip('/')}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

def fetch_repos():
    repos = []
    page = 1
    while True:
        data = gh_api(f"orgs/nuvizio/repos?per_page=100&page={page}")
        if not data:
            break
        repos.extend(data)
        if len(data) < 100:
            break
        page += 1
    return repos

def categorize(name, is_fork, desc):
    if not is_fork:
        return "Internal & Proprietary Systems"
    if name in ["leetcode", "project-based-learning", "public-apis", "OpenStock", "FinGPT"]:
        return "Reference, Learning & Finance"
    if name in ["LivePortrait", "LatentSync", "IMTalker", "Sonic", "digital-human-koubo", 
                "Audio2Face-3D-Samples", "gaussian-splatting", "Hunyuan3D-2", "SteadyDancer",
                "facefusion", "Wan2.2", "Wan2GP", "TurboDiffusion", "Pixelle-Video", 
                "frame-interpolation", "ECCV2022-RIFE", "DiffMorpher", "HeyGem", "SCAIL"]:
        return "Avatar: Visuals, 3D Human & Motion"
    if name in ["CosyVoice", "F5-TTS", "ChatTTS", "fish-speech", "GPT-SoVITS", "chatterbox", 
                "VoiceStudio", "whisper", "whisperX", "faster-whisper", "YuE", "YuEGP", 
                "ACE-Step", "DiffRhythm", "SongBloom"]:
        return "Avatar: Voice, Speech & Audio Customization"
    if name in ["docling", "readest", "pandoc", "tiptap", "PaddleOCR", "pretext", "lexbor", 
                "Scrapling", "html-ppt-skill", "frontend-slides", "html-anything", 
                "screenshot-to-code", "ui", "oil-ui", "impeccable", "book-ai"]:
        return "High-Fidelity Document & UI Systems"
    if name in ["LLMs-from-scratch", "llm-course", "build-your-own-x", "nanochat", "unsloth", 
                "vllm", "OpenHands", "hermes-agent", "paperclip", "claude-plugins-official", 
                "spec-kit", "andrej-karpathy-skills", "book-to-skill", "rea", "claw-code", "laya"]:
        return "Learning, Knowledge Hubs & AI Agents"
    return "Media Infrastructure & Compute Tooling"

def process_repo(r):
    name = r["name"]
    is_fork = r.get("fork", False)
    is_private = r.get("private", False)
    local_pushed = r.get("pushed_at")
    desc = r.get("description") or ""
    def_branch = r.get("default_branch", "main")
    
    cat = categorize(name, is_fork, desc)
    item = {
        "name": name,
        "is_fork": is_fork,
        "is_private": is_private,
        "category": cat,
        "description": desc,
        "local_pushed": local_pushed,
        "default_branch": def_branch,
        "upstream_parent": None,
        "upstream_pushed": None,
        "ahead_by": 0,
        "behind_by": 0,
        "sync_status": "Original" if not is_fork else "Unknown"
    }
    
    if is_fork:
        detail = gh_api(f"repos/nuvizio/{name}")
        if detail and detail.get("parent"):
            parent = detail["parent"]
            parent_full = parent["full_name"]
            parent_owner = parent["owner"]["login"]
            parent_branch = parent.get("default_branch", "main")
            item["upstream_parent"] = parent_full
            item["upstream_pushed"] = parent.get("pushed_at")
            
            comp = gh_api(f"repos/nuvizio/{name}/compare/{parent_owner}:{parent_branch}...{def_branch}")
            if comp:
                ahead = comp.get("ahead_by", 0)
                behind = comp.get("behind_by", 0)
                item["ahead_by"] = ahead
                item["behind_by"] = behind
                if ahead > 0 and behind > 0:
                    item["sync_status"] = f"Diverged (+{ahead} / -{behind})"
                elif ahead > 0:
                    item["sync_status"] = f"Custom (+{ahead} commits)"
                elif behind > 0:
                    item["sync_status"] = f"Behind (-{behind} commits)"
                else:
                    item["sync_status"] = "In Sync"
    return item

def format_date(iso_str):
    return iso_str[:10] if iso_str else "-"

def build_markdown(catalog, is_profile=False):
    categories_order = [
        "Internal & Proprietary Systems",
        "Avatar: Visuals, 3D Human & Motion",
        "Avatar: Voice, Speech & Audio Customization",
        "High-Fidelity Document & UI Systems",
        "Learning, Knowledge Hubs & AI Agents",
        "Media Infrastructure & Compute Tooling",
        "Reference, Learning & Finance"
    ]
    lines = []
    if is_profile:
        lines.append("# Welcome to Nuvizio 🌐\n")
        lines.append("> Engineering next-generation **Natural Human Avatars**, **Voice & Speech Customization**, **High-Fidelity Document Systems**, and **AI Learning & Agentic Hubs**.\n")
    else:
        lines.append("# Nuvizio Organization Repository Catalog 📚\n")
        lines.append("> Automated catalog tracking all repositories, domains, upstream sources, and synchronization statuses across the `nuvizio` organization.\n")

    lines.append(f"**Total Tracked Repositories:** {len(catalog)}  ")
    lines.append(f"**Last Catalog Audit:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  \n")
    
    lines.append("### 📊 Domain Distribution\n")
    lines.append("| Category | Repositories | Focus Areas |")
    lines.append("| :--- | :---: | :--- |")
    
    category_descriptions = {
        "Internal & Proprietary Systems": "Core platforms, proprietary engines (`mono-repo`, `go_comfy`, `virtual-human`, `UDE`), private APIs & services.",
        "Avatar: Visuals, 3D Human & Motion": "Talking heads, lip-sync (`LivePortrait`, `LatentSync`, `HeyGem`), 3D Gaussian Splatting, character motion (`SCAIL`).",
        "Avatar: Voice, Speech & Audio Customization": "Zero-shot voice cloning (`CosyVoice`, `F5-TTS`, `ChatTTS`), alignment (`whisperX`), music synthesis (`SongBloom`, `YuE`).",
        "High-Fidelity Document & UI Systems": "Document layout & parsing (`docling`, `PaddleOCR`), e-readers (`readest`, `book-ai`), headless editors (`tiptap`), agent UI.",
        "Learning, Knowledge Hubs & AI Agents": "Foundation architectures (`LLMs-from-scratch`), fast fine-tuning (`unsloth`, `vllm`), autonomous agents (`OpenHands`, `hermes-agent`).",
        "Media Infrastructure & Compute Tooling": "WebRTC realtime streaming (`livekit`, `mediasoup`), media processing (`FFmpeg`), diffusion engines (`ComfyUI`).",
        "Reference, Learning & Finance": "Financial LLMs (`FinGPT`, `OpenStock`), algorithmic references (`leetcode`, `project-based-learning`, `public-apis`)."
    }

    for cat in categories_order:
        count = sum(1 for r in catalog if r["category"] == cat)
        desc = category_descriptions.get(cat, "")
        lines.append(f"| **{cat}** | {count} | {desc} |")
        
    lines.append("\n---\n")

    for cat in categories_order:
        items = [r for r in catalog if r["category"] == cat]
        items.sort(key=lambda x: (not (x.get("ahead_by", 0) > 0), x["name"].lower()))
        lines.append(f"## {cat} ({len(items)})\n")
        
        if cat == "Internal & Proprietary Systems":
            lines.append("| Repository | Visibility | Last Active | Default Branch | Description |")
            lines.append("| :--- | :---: | :---: | :---: | :--- |")
            for item in items:
                name = item["name"]
                vis = "🔒 Private" if item["is_private"] else "🌐 Public"
                pushed = format_date(item["local_pushed"])
                branch = item["default_branch"]
                desc = (item["description"] or "-").replace("|", "/")
                lines.append(f"| [`nuvizio/{name}`](https://github.com/nuvizio/{name}) | {vis} | {pushed} | `{branch}` | {desc} |")
        else:
            lines.append("| Repository | Upstream Parent | Upstream Updated | Local Updated | Sync / Custom Status | Description |")
            lines.append("| :--- | :--- | :---: | :---: | :---: | :--- |")
            for item in items:
                name = item["name"]
                parent = item["upstream_parent"]
                parent_link = f"[{parent}](https://github.com/{parent})" if parent else "-"
                up_pushed = format_date(item["upstream_pushed"])
                loc_pushed = format_date(item["local_pushed"])
                status = item["sync_status"]
                if item.get("ahead_by", 0) > 0:
                    status = f"⭐ **Custom (+{item['ahead_by']})**"
                elif "Behind" in status:
                    status = f"⚠️ {status}"
                elif status == "In Sync":
                    status = "✅ In Sync"
                desc = (item["description"] or "-").replace("|", "/")
                lines.append(f"| [`{name}`](https://github.com/nuvizio/{name}) | {parent_link} | {up_pushed} | {loc_pushed} | {status} | {desc} |")
        lines.append("\n---\n")
    return "\n".join(lines)

def main():
    print("Fetching repositories...")
    repos = fetch_repos()
    print(f"Auditing {len(repos)} repositories...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        catalog = list(executor.map(process_repo, repos))
        
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    
    # Save catalog.json
    with open(os.path.join(root_dir, "catalog.json"), "w") as f:
        json.dump(catalog, f, indent=2)
        
    # Save root README.md
    with open(os.path.join(root_dir, "README.md"), "w") as f:
        f.write(build_markdown(catalog, is_profile=False))
        
    # Save profile/README.md
    os.makedirs(os.path.join(root_dir, "profile"), exist_ok=True)
    with open(os.path.join(root_dir, "profile", "README.md"), "w") as f:
        f.write(build_markdown(catalog, is_profile=True))
        
    print("Done updating catalog and documentation!")

if __name__ == "__main__":
    main()
