import subprocess
import sys
import os

def apply_patch(patch_file, target_file):
    """Apply a unified diff patch to a target file."""
    if not os.path.exists(patch_file):
        print(f"Patch file not found: {patch_file}")
        return False
    if not os.path.exists(target_file):
        print(f"Target file not found: {target_file}")
        return False
    
    try:
        # Run patch from the repository root (current working directory)
        repo_root = os.getcwd()
        rel_patch = os.path.relpath(patch_file, repo_root)
        result = subprocess.run([
            "patch", "-p1", "-i", rel_patch
        ], capture_output=True, text=True, cwd=repo_root)
        
        if result.returncode == 0:
            print(f"Applied {patch_file} to {target_file}")
            return True
        else:
            print(f"Failed to apply {patch_file}: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error applying patch: {e}")
        return False

def main():
    patches_dir = ".github/workflows/patches"
    
    patches = [
        ("AccountListPage.patch", "HMCL/src/main/java/org/jackhuang/hmcl/ui/account/AccountListPage.java"),
        ("Accounts.patch", "HMCL/src/main/java/org/jackhuang/hmcl/setting/Accounts.java"),
    ]
    
    all_success = True
    for patch_file, target_file in patches:
        patch_path = os.path.join(patches_dir, patch_file)
        if not apply_patch(patch_path, target_file):
            all_success = False
    
    if not all_success:
        sys.exit(1)
    print("All patches applied successfully")

if __name__ == "__main__":
    main()
