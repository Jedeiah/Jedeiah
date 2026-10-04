#!/usr/bin/env bash
# Roll the GitHub profile back to how it looked before the makeover.
#
# The whole makeover is delivered through the special profile repository
# Jedeiah/Jedeiah.  That repository did not exist beforehand and none of the
# profile fields were set, so both rollback paths are lossless:
#
#   ./tools/restore.sh --unpublish   make the repo private -> the README stops
#                                    rendering on the profile; repo, history and
#                                    the Action all survive.  Needs only `repo`.
#   ./tools/restore.sh --delete      delete the repo and re-clear every profile
#                                    field from the pre-makeover snapshot.
#                                    Needs the `delete_repo` scope:
#                                      gh auth refresh -s delete_repo
#
# Neither path touches any other repository.

set -euo pipefail

REPO="Jedeiah/Jedeiah"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() { sed -n '2,19p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 1; }

gh auth status >/dev/null 2>&1 || {
  echo "gh is not authenticated; run 'gh auth login' first." >&2
  exit 1
}

case "${1:-}" in
  --unpublish)
    echo "Making $REPO private (the profile README will stop rendering)…"
    gh repo edit "$REPO" --visibility private --accept-visibility-change-consequences
    echo "Done. Repo and history are intact — flip it back to public to re-publish."
    ;;

  --delete)
    scopes="$(gh auth status 2>&1 | grep -o "Token scopes:.*" || true)"
    if [[ "$scopes" != *delete_repo* ]]; then
      echo "This token lacks the delete_repo scope. Run:" >&2
      echo "    gh auth refresh -s delete_repo" >&2
      echo "…then re-run. (Or use --unpublish, which needs only the repo scope.)" >&2
      exit 1
    fi

    read -r -p "Delete $REPO permanently and clear the profile fields? [y/N] " reply
    [[ "$reply" == [yY] ]] || { echo "Aborted."; exit 1; }

    gh repo delete "$REPO" --yes
    echo "Deleted $REPO."

    # Clear every profile field exactly as captured before the makeover.
    # gh is invoked from Python so that empty values survive argument passing.
    python3 - "$HERE/profile-state.pre-makeover.json" <<'PY'
import json, subprocess, sys

state = json.load(open(sys.argv[1]))
fields = ("name", "bio", "company", "blog", "location", "twitter_username")
args = ["gh", "api", "--method", "PATCH", "/user"]
for field in fields:
    args += [f"--{field}", state.get(field) or ""]
subprocess.run(args, check=True)
print("cleared: " + ", ".join(fields))
PY
    echo "Profile restored to the pre-makeover snapshot."
    ;;

  *)
    usage
    ;;
esac
