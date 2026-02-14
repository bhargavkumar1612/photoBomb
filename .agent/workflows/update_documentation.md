---
description: Check validity of documentation and update it with latest features/changes.
---

This workflow updates all project documentation to reflect the current state of the codebase, including the CHANGELOG.

## Steps

1. **Review Current Changes**
   - Check git status to see what files have been modified
   - Review recent commits to understand what has changed
   - Identify features, fixes, and refactoring that need documentation

2. **Update CHANGELOG.md**
   - Extract the last commit hash from the current CHANGELOG.md (first version, since newest is on top):
     ```bash
     # Get the last version's commit hash (first 8 chars in the first version header)
     LAST_COMMIT=$(grep -oP '(?<=\[)[a-f0-9]{8}(?=\]\[V)' CHANGELOG.md | head -1)
     ```
   - Run the changelog generator script in incremental mode:
     ```bash
     python3 scripts/generate_changelog.py --incremental --last-commit $LAST_COMMIT --output CHANGELOG.md
     ```
   - This will prepend new versions to CHANGELOG.md (newest on top), grouping every 20 commits since the last release
   - **Note**: The changelog is in reverse chronological order - newest versions appear first

3. **Update README.md**
   - Review the README for accuracy
   - Update feature lists if new features were added
   - Update installation/setup instructions if dependencies changed
   - Verify all links and references are still valid

4. **Update PROGRESS.md (if exists)**
   - Mark completed features as done
   - Update completion percentages
   - Add new planned features if discussed
   - Update milestone dates if applicable

5. **Update Architecture Documentation**
   - Check `docs/architecture/` for any files that need updates
   - Update system diagrams if architecture changed
   - Document new components or services
   - Update API documentation if endpoints changed

6. **Update Deployment Documentation**
   - Check `docs/deployment*.md` files
   - Update deployment steps if CI/CD changed
   - Document new environment variables
   - Update infrastructure requirements

7. **Verify Documentation Consistency**
   - Ensure all documentation files are consistent with each other
   - Check that version numbers match across files
   - Verify code examples still work
   - Test any commands or scripts mentioned in docs

8. **Review and Commit**
   - Review all documentation changes
   - Commit with a clear message like "docs: update documentation for [feature/version]"
   - Consider using the /commit_check workflow to generate a good commit message

## Notes

- The CHANGELOG is automatically generated from git commits in **reverse chronological order** (newest first)
- Each version in CHANGELOG represents ~20 commits and uses format: `[commit_id[:8]][Vx.x.x]`
- Always run the incremental changelog update to avoid regenerating the entire file
- New versions are prepended to the top of the file, maintaining reverse chronological order
- Documentation should be updated regularly, not just at release time
