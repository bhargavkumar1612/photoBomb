---
description: Analyze staged changes and suggest a commit message
---
1. Check the repository status to identify staged files.
// turbo
2. Run `git diff --cached` to capture the staged changes.
3. Analyze the diff to understand the intent and scope of the changes (e.g., bug fix, feature, refactor).
4. Generate a commit message following the Conventional Commits specification:
   - **Type**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, etc.
   - **Scope** (optional): e.g., `auth`, `ui`, `api`.
   - **Subject**: Concise description (imperative mood, no period).
   - **Body**: Bullet points explaining *what* and *why* (not just *how*).
