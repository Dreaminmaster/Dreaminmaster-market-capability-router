# Publish to GitHub

The connected GitHub integration can edit existing repositories but cannot create a new repository. Create an empty repository first, preferably private during the design phase.

Recommended repository name:

```text
market-capability-router
```

Then run from this directory:

```bash
git remote add origin git@github.com:Dreaminmaster/market-capability-router.git
git push -u origin main
```

HTTPS alternative:

```bash
git remote add origin https://github.com/Dreaminmaster/market-capability-router.git
git push -u origin main
```

Do not initialize the GitHub repository with another README, license, or `.gitignore`, because this package already contains them.

After the push:

1. Check the GitHub Actions `CI` workflow.
2. Keep the repository private until the license and public-data policy are finalized.
3. Protect the `main` branch after the first stable release.
4. Let the coding Agent read `AGENTS.md` and `plan/task_list.md` before making changes.
