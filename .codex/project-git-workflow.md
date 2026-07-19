<!-- codex-project-git-workflow: initialized -->
<!-- initialized-at: 2026-07-20 03:30:40 +08:00 -->

# Codex Git Workflow

- Initialization status: initialized
- Project: 游戏原语 / Game Primitives
- Repository root: `D:\Articles\Game Primitives`
- Machine config: `.codex\project-git-workflow.json`
- Skill: `project-git-workflow`

Treat this document and the machine config as the source of truth for this repository's Codex git workflow. Do not replace them with generic defaults unless the user explicitly asks to reinitialize or update the policy.

## Global Wrappers

Run these from the repository root:

```powershell
C:\Users\Administrator\.codex\skills\project-git-workflow\scripts\git\Status.cmd
C:\Users\Administrator\.codex\skills\project-git-workflow\scripts\git\Validate.cmd
C:\Users\Administrator\.codex\skills\project-git-workflow\scripts\git\Commit.cmd -Message "commit message" -Paths path\to\file,other\file
C:\Users\Administrator\.codex\skills\project-git-workflow\scripts\git\CommitAndPush.cmd -Message "commit message" -Paths path\to\file,other\file
C:\Users\Administrator\.codex\skills\project-git-workflow\scripts\git\Push.cmd
C:\Users\Administrator\.codex\skills\project-git-workflow\scripts\git\Stash.cmd -StashMessage "reason"
C:\Users\Administrator\.codex\skills\project-git-workflow\scripts\git\StashPop.cmd
C:\Users\Administrator\.codex\skills\project-git-workflow\scripts\git\Ignore.cmd -Pattern build-output/
C:\Users\Administrator\.codex\skills\project-git-workflow\scripts\git\DiscardPaths.cmd -ConfirmDangerous -Paths path\to\file
```

## Status

```powershell
git status --short --branch
```

## Validation

Run this before commit or push:

```powershell
git diff --check
```

## Staging Policy

Stage selected files only. Inspect status before staging and preserve unrelated user changes unless the user explicitly asks to include them.

## Commit

Use the global wrapper's built-in Git commit after staging according to policy. Prefer concise conventional commit messages unless the user specifies another message.

## Push

```powershell
git push -u origin HEAD
```

## Docs And TODO

Update `README.md` or the relevant manuscript and research documents when project scope or structure changes.

## Safety And Branch Policy

Use `main`; never force-push; preserve research history and unrelated work.
