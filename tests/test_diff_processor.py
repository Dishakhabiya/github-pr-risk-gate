import pytest
from app.preprocessing.diff_processor import preprocess_diff


def test_normal_diff():
    raw_diff = (
        "diff --git a/app/main.py b/app/main.py\n"
        "index 1234567..89abcdef 100644\n"
        "--- a/app/main.py\n"
        "+++ b/app/main.py\n"
        "@@ -1,4 +1,5 @@\n"
        " def main():\n"
        "-    print('Hello World')\n"
        "+    print('Hello Risk Gate')\n"
        "+    return True\n"
    )
    result = preprocess_diff(raw_diff)

    assert result["files_changed"] == ["app/main.py"]
    assert result["num_added_lines"] == 2
    assert result["num_deleted_lines"] == 1
    assert len(result["added_lines"]) == 2
    assert len(result["deleted_lines"]) == 1
    assert "index 1234567..89abcdef" not in result["clean_diff"]
    assert "print('Hello Risk Gate')" in result["clean_diff"]


def test_added_lines():
    raw_diff = (
        "diff --git a/new_file.py b/new_file.py\n"
        "--- /dev/null\n"
        "+++ b/new_file.py\n"
        "@@ -0,0 +1,3 @@\n"
        "+line 1\n"
        "+line 2\n"
        "+line 3\n"
    )
    result = preprocess_diff(raw_diff)

    assert result["num_added_lines"] == 3
    assert result["num_deleted_lines"] == 0
    assert result["added_lines"] == ["+line 1", "+line 2", "+line 3"]
    assert result["deleted_lines"] == []


def test_deleted_lines():
    raw_diff = (
        "diff --git a/old_file.py b/old_file.py\n"
        "--- a/old_file.py\n"
        "+++ /dev/null\n"
        "@@ -1,2 +0,0 @@\n"
        "-old line 1\n"
        "-old line 2\n"
    )
    result = preprocess_diff(raw_diff)

    assert result["num_added_lines"] == 0
    assert result["num_deleted_lines"] == 2
    assert result["deleted_lines"] == ["-old line 1", "-old line 2"]


def test_multiple_files():
    raw_diff = (
        "diff --git a/file1.py b/file1.py\n"
        "--- a/file1.py\n"
        "+++ b/file1.py\n"
        "@@ -1,1 +1,1 @@\n"
        "-a\n"
        "+b\n"
        "diff --git a/file2.js b/file2.js\n"
        "--- a/file2.js\n"
        "+++ b/file2.js\n"
        "@@ -1,1 +1,1 @@\n"
        "-c\n"
        "+d\n"
        "diff --git a/docs/readme.md b/docs/readme.md\n"
        "--- a/docs/readme.md\n"
        "+++ b/docs/readme.md\n"
        "@@ -1,1 +1,2 @@\n"
        "+header\n"
    )
    result = preprocess_diff(raw_diff)

    assert result["files_changed"] == ["file1.py", "file2.js", "docs/readme.md"]
    assert result["num_added_lines"] == 3
    assert result["num_deleted_lines"] == 2


def test_empty_diff():
    res_empty_str = preprocess_diff("")
    assert res_empty_str["files_changed"] == []
    assert res_empty_str["num_added_lines"] == 0
    assert res_empty_str["num_deleted_lines"] == 0
    assert res_empty_str["clean_diff"] == ""

    res_none = preprocess_diff(None)
    assert res_none["files_changed"] == []
    assert res_none["num_added_lines"] == 0
    assert res_none["num_deleted_lines"] == 0


def test_binary_file():
    raw_diff = (
        "diff --git a/assets/logo.png b/assets/logo.png\n"
        "Binary files a/assets/logo.png and b/assets/logo.png differ\n"
    )
    result = preprocess_diff(raw_diff)

    assert result["files_changed"] == ["assets/logo.png"]
    assert result["binary_files"] == ["assets/logo.png"]
    assert result["num_added_lines"] == 0
    assert result["num_deleted_lines"] == 0
