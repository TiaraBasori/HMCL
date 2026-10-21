import os
import subprocess
import sys

# Fork patches are applied to a *pristine upstream tree* (see release-build.yml).
# Never run this against an already-patched tree: the patches are plain unified diffs
# and will fail (or double-apply) rather than merge.

PATCHES = [
    ("AccountListPage.patch", "HMCL/src/main/java/org/jackhuang/hmcl/ui/account/AccountListPage.java"),
    ("Accounts.patch", "HMCL/src/main/java/org/jackhuang/hmcl/setting/Accounts.java"),
    ("CreateAccountPane.patch", "HMCL/src/main/java/org/jackhuang/hmcl/ui/account/CreateAccountPane.java"),
    ("MainPage.patch", "HMCL/src/main/java/org/jackhuang/hmcl/ui/main/MainPage.java"),
    ("IntegrityChecker.patch", "HMCL/src/main/java/org/jackhuang/hmcl/upgrade/IntegrityChecker.java"),
    ("Version.patch", "HMCL/build.gradle.kts"),
    ("VersionsPage.patch", "HMCL/src/main/java/org/jackhuang/hmcl/ui/download/VersionsPage.java"),
    ("DownloadListPage.patch", "HMCL/src/main/java/org/jackhuang/hmcl/ui/instances/DownloadListPage.java"),
]

PATCHES_DIR = ".github/workflows/patches"


def run_patch(patch_file, dry_run):
    cmd = ["patch", "-p1"]
    if dry_run:
        cmd.append("--dry-run")
    cmd += ["--batch", "-i", patch_file]
    return subprocess.run(cmd, capture_output=True, text=True)


def main():
    missing = []
    for patch_file, target_file in PATCHES:
        for path in (os.path.join(PATCHES_DIR, patch_file), target_file):
            if not os.path.exists(path):
                missing.append(path)
    if missing:
        print("Missing files:\n  " + "\n  ".join(missing), file=sys.stderr)
        return 1

    # Pre-check every patch before touching the tree, so a stale patch never leaves
    # the workspace half-patched.
    failed = []
    for patch_file, _ in PATCHES:
        result = run_patch(os.path.join(PATCHES_DIR, patch_file), True)
        if result.returncode != 0:
            failed.append((patch_file, (result.stdout + result.stderr).strip()))
    if failed:
        print("Fork patches no longer apply to upstream. Regenerate them against a pristine "
              "upstream tree (see .github/workflows/patches/gen_download_patches.py for the pattern):",
              file=sys.stderr)
        for patch_file, output in failed:
            print(f"\n=== {patch_file}\n{output}", file=sys.stderr)
        return 1

    for patch_file, _ in PATCHES:
        result = run_patch(os.path.join(PATCHES_DIR, patch_file), False)
        if result.returncode != 0:
            print(f"Failed to apply {patch_file}:\n{result.stdout}{result.stderr}", file=sys.stderr)
            return 1
        print(f"Applied {patch_file}")

    print("All patches applied successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
