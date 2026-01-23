---
description: Analyze changes (staged first, then unstaged) and suggest a commit message
---
1. Run `git diff --cached` to check for staged changes.
2. **IF** there are staged changes:
   - Analyze the diff to understand the intent and scope.
   - Generate a commit message following Conventional Commits.
   - Stop here.
3. **ELSE** (if no staged changes):
   - Run `git diff` to capture unstaged changes.
   - Run `git status` to identify untracked files.
   - Analyze the changes.
   - Generate a commit message based on these changes (noting they are unstaged).
