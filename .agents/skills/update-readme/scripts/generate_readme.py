#!/usr/bin/env python3
"""
Generate README.md from Jinja template with dynamic content.
This script is designed to be run during a release to update the README.md
with current release URLs and changelog content.
"""

import os
import sys
from pathlib import Path
import requests
from jinja2 import Environment, FileSystemLoader


def get_project_root():
    """Get the project root directory."""
    # Go up from .agents/skills/update-readme/scripts/ to project root
    return Path(__file__).parent.parent.parent.parent


def get_latest_release_info(owner, repo):
    """
    Fetch the latest GitHub release information.
    Returns dict with release data or None if failed.
    """
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Warning: Could not fetch release info: {e}")
        return None


def find_asset_url(release_data, asset_pattern):
    """Find asset URL matching pattern in release assets."""
    if not release_data or 'assets' not in release_data:
        return f"<!-- {asset_pattern} not found -->"
    
    for asset in release_data['assets']:
        if asset_pattern in asset['name'].lower():
            return asset['browser_download_url']
    
    return f"<!-- {asset_pattern} not found -->"


def get_changelog_content():
    """Read the CHANGELOG.md content."""
    project_root = get_project_root()
    changelog_path = project_root / "CHANGELOG.md"
    
    if changelog_path.exists():
        return changelog_path.read_text(encoding='utf-8')
    else:
        return "<!-- CHANGELOG.md not found -->"


def main():
    """Main function to generate README.md."""
    project_root = get_project_root()
    template_dir = project_root / ".agents" / "skills" / "update-readme" / "references"
    template_path = template_dir / "README.template.md"
    output_path = project_root / "README.md"
    
    # Check if template exists
    if not template_path.exists():
        print(f"Error: Template not found at {template_path}")
        sys.exit(1)
    
    # Get GitHub info (you may need to adjust owner/repo)
    # For now, using placeholder - you should update these values
    github_owner = "your-username"  # Update this
    github_repo = "arcfaces"        # Update this
    
    # Fetch latest release info
    print("Fetching latest release information...")
    release_data = get_latest_release_info(github_owner, github_repo)
    
    # Get template variables
    template_vars = {
        'github_whl_release_url': find_asset_url(release_data, '.whl'),
        'github_exe_release_url': find_asset_url(release_data, 'run_arcfaces.exe'),
        'changelog_content': get_changelog_content()
    }
    
    # Setup Jinja2 environment
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("README.template.md")
    
    # Render template
    print("Rendering template...")
    rendered_content = template.render(**template_vars)
    
    # Write to README.md
    output_path.write_text(rendered_content, encoding='utf-8')
    print(f"README.md generated successfully at {output_path}")
    
    # Print summary
    print("\nTemplate variables used:")
    for key, value in template_vars.items():
        # Truncate long content for display
        display_value = value[:100] + "..." if len(str(value)) > 100 else value
        print(f"  {key}: {display_value}")


if __name__ == "__main__":
    main()
