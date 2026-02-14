#!/usr/bin/env python3
"""
Generate CHANGELOG.md from git commit history.
Groups commits into versions of 20 commits each.
"""
import subprocess
import sys
from typing import List, Tuple

def get_all_commits() -> List[Tuple[str, str]]:
    """Get all commits in reverse chronological order (oldest first)."""
    result = subprocess.run(
        ['git', 'log', '--oneline', '--reverse', '--all'],
        capture_output=True,
        text=True,
        check=True
    )
    commits = []
    for line in result.stdout.strip().split('\n'):
        if line:
            parts = line.split(' ', 1)
            commit_hash = parts[0]
            message = parts[1] if len(parts) > 1 else ''
            commits.append((commit_hash, message))
    return commits

def get_commits_since(last_commit_hash: str) -> List[Tuple[str, str]]:
    """Get commits since a specific commit hash."""
    result = subprocess.run(
        ['git', 'log', '--oneline', f'{last_commit_hash}..HEAD'],
        capture_output=True,
        text=True,
        check=True
    )
    commits = []
    for line in result.stdout.strip().split('\n'):
        if line:
            parts = line.split(' ', 1)
            commit_hash = parts[0]
            message = parts[1] if len(parts) > 1 else ''
            commits.append((commit_hash, message))
    return list(reversed(commits))  # Reverse to get oldest first

def group_commits(commits: List[Tuple[str, str]], group_size: int = 20) -> List[List[Tuple[str, str]]]:
    """Group commits into chunks of specified size."""
    groups = []
    for i in range(0, len(commits), group_size):
        groups.append(commits[i:i + group_size])
    return groups

def generate_changelog(output_file: str = 'CHANGELOG.md', incremental: bool = False, last_commit: str = None):
    """Generate the changelog file."""
    
    if incremental and last_commit:
        commits = get_commits_since(last_commit)
        if not commits:
            print("No new commits since last release.")
            return
        # Read existing changelog to get the last version number
        try:
            with open(output_file, 'r') as f:
                content = f.read()
                # Extract first version number (since newest is on top)
                import re
                versions = re.findall(r'\[V(\d+)\.(\d+)\.(\d+)\]', content)
                if versions:
                    last_major, last_minor, last_patch = map(int, versions[0])
                    start_version = (last_major, last_minor, last_patch + 1)
                else:
                    start_version = (0, 0, 0)
        except FileNotFoundError:
            start_version = (0, 0, 0)
    else:
        commits = get_all_commits()
        start_version = (0, 0, 0)
    
    groups = group_commits(commits, 20)
    
    # Reverse groups so newest is first
    groups = list(reversed(groups))
    
    changelog_content = []
    
    if not incremental:
        changelog_content.append("# CHANGELOG\n")
        changelog_content.append("This changelog is automatically generated from git commit history.\n")
        changelog_content.append("Each version represents approximately 20 commits.\n")
        changelog_content.append("Versions are listed in reverse chronological order (newest first).\n\n")
    
    # Calculate version numbers in reverse (newest gets highest number)
    total_versions = len(groups)
    
    for idx, group in enumerate(groups):
        # Calculate version number (newest first)
        if incremental:
            major, minor, patch = start_version
            version_num = (major, minor, patch + idx)
        else:
            version_num = (0, 0, total_versions - 1 - idx)
        
        # The last commit in the group determines the version ID
        last_commit_hash = group[-1][0]
        version_str = f"[{last_commit_hash[:8]}][V{version_num[0]}.{version_num[1]}.{version_num[2]}]"
        
        changelog_content.append(f"## {version_str}\n\n")
        
        # Categorize commits (reverse to show newest first within the version)
        features = []
        fixes = []
        chores = []
        refactors = []
        others = []
        
        for commit_hash, message in reversed(group):
            msg_lower = message.lower()
            if msg_lower.startswith('feat'):
                features.append(f"- {message}")
            elif msg_lower.startswith('fix'):
                fixes.append(f"- {message}")
            elif msg_lower.startswith('chore'):
                chores.append(f"- {message}")
            elif msg_lower.startswith('refactor'):
                refactors.append(f"- {message}")
            else:
                others.append(f"- {message}")
        
        # Write categorized commits
        if features:
            changelog_content.append("### Features\n")
            changelog_content.extend([f"{feat}\n" for feat in features])
            changelog_content.append("\n")
        
        if fixes:
            changelog_content.append("### Fixes\n")
            changelog_content.extend([f"{fix}\n" for fix in fixes])
            changelog_content.append("\n")
        
        if refactors:
            changelog_content.append("### Refactoring\n")
            changelog_content.extend([f"{ref}\n" for ref in refactors])
            changelog_content.append("\n")
        
        if chores:
            changelog_content.append("### Chores\n")
            changelog_content.extend([f"{chore}\n" for chore in chores])
            changelog_content.append("\n")
        
        if others:
            changelog_content.append("### Other Changes\n")
            changelog_content.extend([f"{other}\n" for other in others])
            changelog_content.append("\n")
    
    # Write to file
    if incremental and last_commit:
        # Prepend to existing file (new versions go on top)
        try:
            with open(output_file, 'r') as f:
                existing_content = f.read()
        except FileNotFoundError:
            existing_content = ""
        
        with open(output_file, 'w') as f:
            f.writelines(changelog_content)
            if existing_content:
                # Skip the header if it exists
                if existing_content.startswith("# CHANGELOG"):
                    lines = existing_content.split('\n')
                    # Find where versions start (after header)
                    for i, line in enumerate(lines):
                        if line.startswith('## ['):
                            f.write('\n'.join(lines[i:]))
                            break
                else:
                    f.write(existing_content)
        print(f"Prepended {len(groups)} new version(s) to {output_file}")
    else:
        # Write new file
        with open(output_file, 'w') as f:
            f.writelines(changelog_content)
        print(f"Generated {output_file} with {len(groups)} versions from {len(commits)} commits")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Generate changelog from git history')
    parser.add_argument('--incremental', action='store_true', help='Generate incremental changelog')
    parser.add_argument('--last-commit', type=str, help='Last commit hash for incremental generation')
    parser.add_argument('--output', type=str, default='CHANGELOG.md', help='Output file path')
    
    args = parser.parse_args()
    
    generate_changelog(
        output_file=args.output,
        incremental=args.incremental,
        last_commit=args.last_commit
    )
