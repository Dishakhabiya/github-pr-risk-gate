import re
from typing import Any, Dict, List, Optional


def preprocess_diff(diff: Optional[str]) -> Dict[str, Any]:
    """Preprocess raw git unified diff into structured data.

    Args:
        diff: Raw git diff string returned by GitHub API or git diff command.

    Returns:
        Dict containing:
            - clean_diff: Filtered diff string with metadata cleaned up.
            - files_changed: List of changed filenames.
            - added_lines: List of added code lines.
            - deleted_lines: List of deleted code lines.
            - num_added_lines: Total count of added lines.
            - num_deleted_lines: Total count of deleted lines.
            - binary_files: List of binary files detected in diff.
    """
    if not diff or not diff.strip():
        return {
            "clean_diff": "",
            "files_changed": [],
            "added_lines": [],
            "deleted_lines": [],
            "num_added_lines": 0,
            "num_deleted_lines": 0,
            "binary_files": [],
        }

    files_changed: List[str] = []
    binary_files: List[str] = []
    added_lines: List[str] = []
    deleted_lines: List[str] = []
    clean_diff_lines: List[str] = []

    lines = diff.splitlines()
    in_binary_patch = False

    for line in lines:
        # Check for binary file diff statements
        binary_match = re.search(r"Binary files (a/(\S+)|/dev/null) and (b/(\S+)|/dev/null) differ", line)
        if binary_match:
            # Extract filename from b/ or a/
            b_file = binary_match.group(4)
            a_file = binary_match.group(2)
            fname = b_file or a_file
            if fname and fname not in files_changed:
                files_changed.append(fname)
            if fname and fname not in binary_files:
                binary_files.append(fname)
            clean_diff_lines.append(f"Binary file {fname} changed")
            continue

        if line.startswith("GIT binary patch"):
            in_binary_patch = True
            clean_diff_lines.append("[Binary patch omitted]")
            continue

        if in_binary_patch:
            # Skip binary patch content lines until next file diff header
            if line.startswith("diff --git"):
                in_binary_patch = False
            else:
                continue

        # Check for file diff headers
        if line.startswith("diff --git"):
            # Extract filename from 'diff --git a/file b/file'
            match = re.search(r"diff --git a/(.+) b/(.+)", line)
            if match:
                fname = match.group(2)
                if fname not in files_changed:
                    files_changed.append(fname)
            clean_diff_lines.append(line)
            continue

        # Ignore noisy diff metadata lines
        if (
            line.startswith("index ")
            or line.startswith("new file mode ")
            or line.startswith("deleted file mode ")
            or line.startswith("old mode ")
            or line.startswith("new mode ")
            or line.startswith("similarity index ")
            or line.startswith("rename from ")
            or line.startswith("rename to ")
        ):
            continue

        # Capture file header markers (--- a/file and +++ b/file)
        if line.startswith("--- ") or line.startswith("+++ "):
            # Extract file path if not captured yet
            if line.startswith("--- a/") or line.startswith("+++ b/"):
                fname = line[6:].strip()
                if fname and fname != "/dev/null" and fname not in files_changed:
                    files_changed.append(fname)
            clean_diff_lines.append(line)
            continue

        # Capture chunk range header (e.g., @@ -1,5 +1,6 @@)
        if line.startswith("@@"):
            clean_diff_lines.append(line)
            continue

        # Added line
        if line.startswith("+"):
            added_lines.append(line)
            clean_diff_lines.append(line)
            continue

        # Deleted line
        if line.startswith("-"):
            deleted_lines.append(line)
            clean_diff_lines.append(line)
            continue

        # Unchanged / context line
        if line.startswith(" "):
            clean_diff_lines.append(line)
            continue

    return {
        "clean_diff": "\n".join(clean_diff_lines),
        "files_changed": files_changed,
        "added_lines": added_lines,
        "deleted_lines": deleted_lines,
        "num_added_lines": len(added_lines),
        "num_deleted_lines": len(deleted_lines),
        "binary_files": binary_files,
    }
