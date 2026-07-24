#!/usr/bin/env python3
"""
Apply custom patches to remove offline account login restriction.
This script is run after syncing with upstream/main.
"""

import re
import sys
from pathlib import Path


def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_file(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def patch_account_list_page(path: Path) -> int:
    content = read_file(path)
    original = content
    removed = 0

    # 1. Remove RESTRICTED field declaration
    def remove_restricted_field(text: str) -> tuple[str, int]:
        lines = text.splitlines(keepends=True)
        to_remove = set()
        for i, line in enumerate(lines):
            if "static final BooleanProperty RESTRICTED" in line:
                to_remove.add(i)
                # Remove trailing blank line
                if i + 1 < len(lines) and lines[i + 1].strip() == "":
                    to_remove.add(i + 1)
                new_lines = [l for idx, l in enumerate(lines) if idx not in to_remove]
                return "".join(new_lines), len(lines) - len(new_lines)
        return text, 0

    content, n = remove_restricted_field(content)
    removed += n

    # 2. Remove RESTRICTED holder field
    def remove_holder_field(text: str) -> tuple[str, int]:
        lines = text.splitlines(keepends=True)
        to_remove = set()
        for i, line in enumerate(lines):
            if "private static BooleanProperty.Listener<Boolean> holder" in line:
                to_remove.add(i)
                if i + 1 < len(lines) and lines[i + 1].strip() == "":
                    to_remove.add(i + 1)
                new_lines = [l for idx, l in enumerate(lines) if idx not in to_remove]
                return "".join(new_lines), len(lines) - len(new_lines)
        return text, 0

    content, n = remove_holder_field(content)
    removed += n

    # 3. Remove static block that initializes RESTRICTED
    def remove_static_block(text: str) -> tuple[str, int]:
        lines = text.splitlines(keepends=True)
        to_remove = set()
        static_start = None

        for i, line in enumerate(lines):
            if re.match(r"^\s*static\s*\{", line):
                # Check if this static block references RESTRICTED anywhere in the block
                brace_count = 0
                started = False
                for j in range(i, len(lines)):
                    if "{" in lines[j] or "}" in lines[j]:
                        started = True
                    brace_count += lines[j].count("{")
                    brace_count -= lines[j].count("}")
                    if started and brace_count == 0:
                        block_content = "".join(lines[i:j+1])
                        if "RESTRICTED" in block_content:
                            static_start = i
                            static_end = j
                        break
                if static_start is not None:
                    break

        if static_start is not None:
            for k in range(static_start, static_end + 1):
                to_remove.add(k)
            if static_end + 1 < len(lines) and lines[static_end + 1].strip() == "":
                to_remove.add(static_end + 1)
            new_lines = [l for idx, l in enumerate(lines) if idx not in to_remove]
            return "".join(new_lines), len(lines) - len(new_lines)
        return text, 0

    content, n = remove_static_block(content)
    removed += n

    # 4. Remove if/else block that checks RESTRICTED.get() in AccountListPageSkin
    def remove_restricted_if_else(text: str) -> tuple[str, int]:
        lines = text.splitlines(keepends=True)
        to_remove = set()

        # Find the "if (RESTRICTED.get())" line
        if_start = None
        for i, line in enumerate(lines):
            if "if (RESTRICTED.get())" in line and "{" in line:
                if_start = i
                break

        if if_start is not None:
            # Find the matching else
            else_start = None
            for i in range(if_start, len(lines)):
                if "} else {" in lines[i]:
                    else_start = i
                    break

            if else_start is not None:
                # Find the end of the entire if/else block
                brace_count = 0
                started = False
                for j in range(if_start, len(lines)):
                    if "{" in lines[j] or "}" in lines[j]:
                        started = True
                    brace_count += lines[j].count("{")
                    brace_count -= lines[j].count("}")
                    if started and brace_count == 0:
                        # Found the end of the if/else block
                        for k in range(if_start, j + 1):
                            to_remove.add(k)
                        # Remove trailing blank line
                        if j + 1 < len(lines) and lines[j + 1].strip() == "":
                            to_remove.add(j + 1)
                        new_lines = [l for idx, l in enumerate(lines) if idx not in to_remove]
                        return "".join(new_lines), len(lines) - len(new_lines)

        return text, 0

    content, n = remove_restricted_if_else(content)
    removed += n

    # 5. Clean up imports that are no longer needed
    def clean_imports(text: str) -> tuple[str, int]:
        lines = text.splitlines(keepends=True)
        to_remove = set()
        unused_imports = [
            "import javafx.beans.property.BooleanProperty;",
            "import javafx.beans.property.SimpleBooleanProperty;",
            "import javafx.beans.value.ChangeListener;",
            "import org.jackhuang.hmcl.util.i18n.LocaleUtils;",
        ]
        for i, line in enumerate(lines):
            if line.strip() in unused_imports:
                to_remove.add(i)
        if to_remove:
            new_lines = [l for idx, l in enumerate(lines) if idx not in to_remove]
            return "".join(new_lines), len(lines) - len(new_lines)
        return text, 0

    content, n = clean_imports(content)
    removed += n

    # 6. Fix the extra closing brace issue after if/else removal
    def fix_extra_brace(text: str) -> tuple[str, int]:
        lines = text.splitlines(keepends=True)
        # Look for pattern: ClassTitle title = ...; } }
        for i in range(len(lines) - 2):
            if "ClassTitle title = new ClassTitle" in lines[i] and lines[i+1].strip() == "}" and lines[i+2].strip() == "}":
                # Remove the extra closing brace
                new_lines = lines[:i+1] + lines[i+2:]
                return "".join(new_lines), 1
        return text, 0

    content, n = fix_extra_brace(content)
    removed += n

    # 7. Ensure the class has the correct number of closing braces
    def fix_class_closing_braces(text: str) -> tuple[str, int]:
        lines = text.splitlines(keepends=True)
        # Count opening and closing braces for the outer class
        open_braces = 0
        close_braces = 0
        for line in lines:
            open_braces += line.count("{")
            close_braces += line.count("}")
        # The file should have balanced braces
        if open_braces > close_braces:
            # Add missing closing braces at the end
            missing = open_braces - close_braces
            new_lines = lines + ["}\n"] * missing
            return "".join(new_lines), missing
        return text, 0

    content, n = fix_class_closing_braces(content)
    removed += n

    # 8. Remove unused holder field
    def remove_holder_field(text: str) -> tuple[str, int]:
        lines = text.splitlines(keepends=True)
        to_remove = set()
        for i, line in enumerate(lines):
            if "private ChangeListener<Boolean> holder;" in line:
                to_remove.add(i)
                if i + 1 < len(lines) and lines[i + 1].strip() == "":
                    to_remove.add(i + 1)
                new_lines = [l for idx, l in enumerate(lines) if idx not in to_remove]
                return "".join(new_lines), len(lines) - len(new_lines)
        return text, 0

    content, n = remove_holder_field(content)
    removed += n

    if content != original:
        write_file(path, content)
        print(f"Patched {path}: removed ~{removed} lines")
    else:
        print(f"No changes needed for {path}")
    return removed


def patch_accounts(path: Path) -> int:
    content = read_file(path)
    original = content
    removed = 0

    # Remove RESTRICTED field from Accounts.java
    def remove_restricted_field(text: str) -> tuple[str, int]:
        lines = text.splitlines(keepends=True)
        to_remove = set()
        for i, line in enumerate(lines):
            if "public static final BooleanProperty RESTRICTED" in line:
                to_remove.add(i)
                if i + 1 < len(lines) and lines[i + 1].strip() == "":
                    to_remove.add(i + 1)
                new_lines = [l for idx, l in enumerate(lines) if idx not in to_remove]
                return "".join(new_lines), len(lines) - len(new_lines)
        return text, 0

    content, n = remove_restricted_field(content)
    removed += n

    # Remove the if blocks that check enableOfflineAccountProperty
    def remove_offline_account_blocks(text: str) -> tuple[str, int]:
        lines = text.splitlines(keepends=True)
        to_remove = set()
        
        # Find all if blocks that check enableOfflineAccountProperty
        i = 0
        while i < len(lines):
            if "enableOfflineAccountProperty" in lines[i] and ".get()" in lines[i]:
                # Check if previous line has "if"
                if i > 0 and "if" in lines[i-1]:
                    if_start = i - 1
                    
                    # Check if this is a single-statement if (no braces) or a block
                    # Look ahead to find the end
                    brace_count = 0
                    started = False
                    found_brace = False
                    for j in range(if_start, len(lines)):
                        if "{" in lines[j]:
                            found_brace = True
                            started = True
                        if "{" in lines[j] or "}" in lines[j]:
                            started = True
                        brace_count += lines[j].count("{")
                        brace_count -= lines[j].count("}")
                        if started and brace_count == 0:
                            if found_brace:
                                # This is a block with braces
                                for k in range(if_start, j + 1):
                                    to_remove.add(k)
                                if j + 1 < len(lines) and lines[j + 1].strip() == "":
                                    to_remove.add(j + 1)
                            else:
                                # Single statement if - find the semicolon
                                for k in range(if_start, j + 1):
                                    to_remove.add(k)
                                if j + 1 < len(lines) and lines[j + 1].strip() == "":
                                    to_remove.add(j + 1)
                            i = j + 1
                            break
                    else:
                        i += 1
                else:
                    i += 1
            else:
                i += 1
        
        if to_remove:
            new_lines = [l for idx, l in enumerate(lines) if idx not in to_remove]
            return "".join(new_lines), len(lines) - len(new_lines)
        return text, 0

    content, n = remove_offline_account_blocks(content)
    removed += n

    # Clean up unused imports
    def clean_imports(text: str) -> tuple[str, int]:
        lines = text.splitlines(keepends=True)
        to_remove = set()
        unused_imports = [
            "import javafx.beans.property.BooleanProperty;",
            "import javafx.beans.property.SimpleBooleanProperty;",
            "import javafx.collections.ListChangeListener;",
            "import javafx.collections.Change;",
        ]
        for i, line in enumerate(lines):
            if line.strip() in unused_imports:
                to_remove.add(i)
        if to_remove:
            new_lines = [l for idx, l in enumerate(lines) if idx not in to_remove]
            return "".join(new_lines), len(lines) - len(new_lines)
        return text, 0

    content, n = clean_imports(content)
    removed += n

    if content != original:
        write_file(path, content)
        print(f"Patched {path}: removed ~{removed} lines")
    else:
        print(f"No changes needed for {path}")
    return removed


def patch_create_account_pane(path: Path) -> int:
    content = read_file(path)
    original = content
    removed = 0

    # Replace the entire if/else block that checks AccountListPage.RESTRICTED.get()
    # Original pattern:
    # if (factory == null) {
    #     if (AccountListPage.RESTRICTED.get()) {
    #         showMethodSwitcher = false;
    #         factory = Accounts.FACTORY_MICROSOFT;
    #     } else {
    #         showMethodSwitcher = true;
    #         String preferred = settings().preferredLoginTypeProperty().get();
    #         try {
    #             factory = Accounts.getAccountFactory(preferred);
    #         } catch (IllegalArgumentException e) {
    #             factory = Accounts.FACTORY_OFFLINE;
    #         }
    #     }
    # } else {
    #     showMethodSwitcher = false;
    # }
    #
    # Should become:
    # if (factory == null) {
    #     showMethodSwitcher = true;
    #     String preferred = settings().preferredLoginTypeProperty().get();
    #     try {
    #         factory = Accounts.getAccountFactory(preferred);
    #     } catch (IllegalArgumentException e) {
    #         factory = Accounts.FACTORY_OFFLINE;
    #     }
    # } else {
    #     showMethodSwitcher = false;
    # }

    def replace_restricted_block(text: str) -> tuple[str, int]:
        lines = text.splitlines(keepends=True)

        # Find the outer if (factory == null) block
        outer_if_start = None
        for i, line in enumerate(lines):
            if "if (factory == null)" in line and "{" in line:
                outer_if_start = i
                break

        if outer_if_start is None:
            return text, 0

        # Find the matching closing brace for the outer if/else
        brace_count = 0
        started = False
        outer_else_start = None
        outer_end = None

        for j in range(outer_if_start, len(lines)):
            if "{" in lines[j] or "}" in lines[j]:
                started = True
            brace_count += lines[j].count("{")
            brace_count -= lines[j].count("}")
            if started and brace_count == 0:
                outer_end = j
                break
            # Track the else position - only the outer else (at brace level 1)
            if outer_else_start is None and "} else {" in lines[j]:
                # Check if this is the outer else by looking at brace count before this line
                temp_brace_count = 0
                for k in range(outer_if_start, j):
                    temp_brace_count += lines[k].count("{")
                    temp_brace_count -= lines[k].count("}")
                # The outer else should be at brace level 1 (inside the outer if block)
                if temp_brace_count == 1:
                    outer_else_start = j

        if outer_end is None or outer_else_start is None:
            return text, 0

        # Find the inner if (AccountListPage.RESTRICTED.get()) block
        inner_if_start = None
        for i in range(outer_if_start + 1, outer_else_start):
            if "if (AccountListPage.RESTRICTED.get())" in lines[i] and "{" in lines[i]:
                inner_if_start = i
                break

        if inner_if_start is None:
            return text, 0

        # Find the inner else
        inner_else_start = None
        for i in range(inner_if_start, outer_else_start):
            if "} else {" in lines[i]:
                inner_else_start = i
                break

        if inner_else_start is None:
            return text, 0

        # Find the end of the inner if/else (should be just before outer_else_start)
        inner_brace_count = 0
        inner_started = False
        inner_end = None
        for j in range(inner_if_start, outer_else_start):
            if "{" in lines[j] or "}" in lines[j]:
                inner_started = True
            inner_brace_count += lines[j].count("{")
            inner_brace_count -= lines[j].count("}")
            if inner_started and inner_brace_count == 0:
                inner_end = j
                break

        if inner_end is None:
            return text, 0

        # Build new content:
        # 1. Lines before outer_if_start + 1 (up to and including "if (factory == null) {")
        # 2. The else branch content (lines inner_else_start+1 to inner_end-1)
        # 3. The outer else block
        # 4. Lines after outer_end

        new_content_lines = []
        new_content_lines.extend(lines[:outer_if_start + 1])  # Up to "if (factory == null) {"

        # Add the else branch content (without the inner if/else structure)
        for k in range(inner_else_start + 1, inner_end):
            new_content_lines.append(lines[k])

        # Add the outer else block
        new_content_lines.append("        } else {\n")
        new_content_lines.append("            showMethodSwitcher = false;\n")
        new_content_lines.append("        }\n")

        # Add lines after outer_end
        new_content_lines.extend(lines[outer_end + 1:])

        new_content = "".join(new_content_lines)
        removed = len(lines) - len(new_content_lines)
        return new_content, removed

    content, n = replace_restricted_block(content)
    removed += n

    # Clean up multiple consecutive blank lines (max 2)
    content = re.sub(r"\n{3,}", "\n\n", content)

    if content != original:
        write_file(path, content)
        print(f"Patched {path}: removed ~{removed} lines")
    else:
        print(f"No changes needed for {path}")
    return removed


def main():
    # Repo root is the current working directory (GitHub Actions checks out to /home/runner/work/HMCL/HMCL)
    repo_root = Path.cwd()
    account_list_page = repo_root / "HMCL/src/main/java/org/jackhuang/hmcl/ui/account/AccountListPage.java"
    accounts = repo_root / "HMCL/src/main/java/org/jackhuang/hmcl/setting/Accounts.java"
    create_account_pane = repo_root / "HMCL/src/main/java/org/jackhuang/hmcl/ui/account/CreateAccountPane.java"

    if not account_list_page.exists():
        print(f"ERROR: {account_list_page} not found")
        sys.exit(1)
    if not accounts.exists():
        print(f"ERROR: {accounts} not found")
        sys.exit(1)
    if not create_account_pane.exists():
        print(f"ERROR: {create_account_pane} not found")
        sys.exit(1)

    patch_account_list_page(account_list_page)
    patch_accounts(accounts)
    patch_create_account_pane(create_account_pane)
    print("All patches applied successfully")


if __name__ == "__main__":
    main()
