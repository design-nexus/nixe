#!/usr/bin/env bash
# Install the Nixe apps pinned in suite.toml: ./install.sh APP... | all
set -euo pipefail
RAW=https://raw.githubusercontent.com/design-nexus/nixe/main
here=""
[[ -n ${BASH_SOURCE[0]:-} && -f ${BASH_SOURCE[0]} ]] && here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ -n $here && -f $here/tools/install-suite.py ]]; then
  exec python3 "$here/tools/install-suite.py" "$@"
else
  work=$(mktemp -d)
  trap 'rm -rf "$work"' EXIT
  curl -fsSL "$RAW/tools/install-suite.py" > "$work/install.py"
  python3 "$work/install.py" "$@"
fi
