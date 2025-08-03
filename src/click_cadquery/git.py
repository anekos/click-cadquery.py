import subprocess


def version_number() -> int:
    result = subprocess.run(
        ["git", "log", "--oneline"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return len([line for line in result.stdout.split("\n") if line.strip() != ""])
    else:
        return 0
