import subprocess


def version_number() -> int:
    result = subprocess.run(
        ["git", "log", "--oneline"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return len([line for line in result.stdout.split("\n") if line.strip() != ""])
    else:
        return 0


def branch_name() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    else:
        return "unknown"
