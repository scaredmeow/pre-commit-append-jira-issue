from __future__ import annotations
import argparse
import re
import subprocess
from typing import Sequence

def run_command(command: str) -> str:
    """Run a command and return its output
    If the command fails, return an empty string"""
    try:
        stdout: str = subprocess.check_output(command.split()).decode("utf-8").strip()
    except Exception:
        stdout = ""
    return stdout

def get_branch_name() -> str:
    # git rev-parse --abbrev-ref HEAD
    #   returns HEAD if in detached state
    # git symbolic-ref --short HEAD
    #   returns fatal: ref HEAD is not a symbolic ref if in detached state
    return run_command("git symbolic-ref --short HEAD")

def extract_jira_issue(content: str) -> str | None:
    project_key, issue_number = r"[A-Z]{2,}", r"[0-9]+"
    match = re.search(f"{project_key}-{issue_number}", content)
    if match:
        return match.group(0)
    return None

def get_commit_msg(commit_msg_filepath: str) -> str:
    """Get the commit message
    Ignore comment lines as those aren't included in the commit message
    """
    with open(commit_msg_filepath) as f:
        msg = ""
        for line in f:
            if not line.startswith("#"):
                msg += line
    return msg

def append_jira_issue(msg: str, issue: str) -> str:
    """
    Appends a Jira issue key to the commit message subject.

    This function intelligently inserts the Jira issue key based on whether
    the message already follows the conventional commit format.

    - If a conventional commit type is found (e.g., "feat:", "fix(api):"),
      it inserts the issue key after the type/scope.
      Example: "feat: new button" -> "feat: JIRA-123 new button"

    - If no conventional commit type is found, it prepends a default
      type 'chore' along with the issue key.
      Example: "Add new button" -> "chore: JIRA-123 Add new button"

    Args:
        msg: The original commit message.
        issue: The Jira issue key (e.g., "JIRA-123").

    Returns:
        The modified commit message.
    """
    # Split the message into the subject (first line) and the body.
    lines = msg.strip().split('\n', 1)
    subject = lines[0]
    body = f'\n\n{lines[1].strip()}' if len(lines) > 1 and lines[1].strip() else ''

    # Regex to detect conventional commit types (e.g., feat, fix, chore)
    # with an optional scope in parentheses.
    conv_commit_pattern = re.compile(
        r"^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)(\(.*\))?:"
    )

    match = conv_commit_pattern.match(subject)

    if match:
        # If a conventional commit type is found, insert the issue key
        # right after the colon.
        colon_index = subject.find(':')
        prefix = subject[:colon_index + 1]
        description = subject[colon_index + 1:].lstrip()
        new_subject = f"{prefix} {issue} {description}"
    else:
        # If no conventional commit type is found, prepend a default
        # 'chore' type and the issue key to the original subject.
        new_subject = f"chore: {issue} {subject}"

    # Reassemble and return the full commit message.
    return new_subject + body

def write_commit_msg(commit_msg_filepath: str, commit_msg: str) -> None:
    with open(commit_msg_filepath, "w") as f:
        f.write(commit_msg)

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("commit_msg_filepath", type=str)
    args = parser.parse_args(argv)

    git_branch_name = get_branch_name()
    branch_jira_issue = extract_jira_issue(git_branch_name)

    # If no jira issue in branch name, exit gracefully.
    if branch_jira_issue is None:
        return 0

    commit_msg = get_commit_msg(args.commit_msg_filepath)

    # Ignore merge requests, as they have their own format.
    if commit_msg.startswith("Merge "):
        return 0

    # Check if commit message already has a jira issue in it.
    commit_msg_jira_issue = extract_jira_issue(commit_msg)

    # If a jira issue is already in the commit message, do nothing.
    if commit_msg_jira_issue:
        return 0

    new_commit_msg = append_jira_issue(commit_msg, branch_jira_issue)
    write_commit_msg(args.commit_msg_filepath, new_commit_msg)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
