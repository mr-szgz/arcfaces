#!/usr/bin/env python3
import os
import sys
import requests


def main():
    if len(sys.argv) != 4:
        print("usage: fetch_release_assets.py <owner> <repo> <tag>", file=sys.stderr)
        return 2

    owner, repo, tag = sys.argv[1:4]
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}"
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    for asset in data.get("assets", []):
        name = asset.get("name", "")
        dl = asset.get("browser_download_url", "")
        print(f"{name}\t{dl}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
