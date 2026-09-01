# Harmless rejection-test inputs

Each string is a direct unit-test input to `_safe_member_path()` and must raise
`WorkspaceArchiveError`. No ZIP creation, restore, or filesystem write is
needed.

| Input | Expected result |
| --- | --- |
| `\Windows\Temp\owned` | Reject: rooted Windows path |
| `D:\owned` | Reject: drive-qualified Windows path |
| `D:/owned` | Reject: drive-qualified path using forward slashes |
| `D:owned` | Reject: drive-relative Windows path |
| `\\server\share\owned` | Reject: UNC path |
| `..\escape` | Reject: backslash traversal syntax |
| `../escape` | Reject: POSIX parent component |
| `/absolute` | Reject: POSIX absolute path |
| `projects//default/evidence.txt` | Reject: non-canonical separators |
| `projects/./default/evidence.txt` | Reject: non-canonical dot component |
