---
description: Check validity of documentation and update it with latest features/changes.
---

This workflow guides you through checking the validity of the project's documentation and updating it to reflect the current state of the codebase. It also ensures the changelog is updated.

## Prerequisites
- Working knowledge of the current feature set and recent changes.

## Steps

1. **Identify Recent Changes**:
   - Review your recent conversation history and `git log` (if available/relevant) to identify new features, bug fixes, or architectural changes since the last documentation update.
   - Look for changes in `CHANGELOG.md` under [Unreleased] if it exists.

2. **Verify Feature Implementation**:
   - For every new feature identified, verify its existence and implementation state in the codebase using `find_by_name` or `view_file` (e.g., check for new API endpoints, UI components, migration files).
   - *Self-Correction*: Do not assume a feature mentioned in a plan is implemented. Always verify the code.

3. **Check Documentation Validity**:
   - Read `README.md`, `docs/PROGRESS.md` (or equivalent status doc), and `docs/architecture/system_architecture.md`.
   - Compare the documented state with your verified codebase state.
   - Note discrepancies (e.g., "Docs say feature X is planned, but code shows it's implemented", or "Docs describe architecture A, but code uses architecture B").

4. **Update Documentation**:
   - Update `README.md` to include new major features and update any outdated setup instructions.
   - Update `docs/PROGRESS.md`:
     - Mark completed items as Checked (✅).
     - Add newly implemented features to the list.
     - Move items from "Planned" to "Implemented" where appropriate.
   - Update Architecture Docs (`docs/architecture/*.md`):
     - If architectural patterns changed (e.g., Auth flow, Storage strategy), update the relevant sections and diagrams.

5. **Update Changelog**:
   - Open `CHANGELOG.md`.
   - Add a new entry under `[Unreleased]` (or a new version header if releasing) describing:
     - **Added**: New features.
     - **Changed**: Modifications to existing functionality.
     - **Deprecated/Removed**: Anything removed.
     - **Fixed**: Bug fixes.
   - Ensure specific, technical details are summarized clearly for developers.

6. **Final Review**:
   - Read through your changes to ensure consistency across all updated documents.
   - Verify that no "Planned" items are falsely marked as "Complete" without code verification.
