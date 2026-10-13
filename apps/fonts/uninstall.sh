#!/usr/bin/env bash
# Remove fonts (--purge also removes its settings and data).
here=$(cd "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec "$here/../../uninstall.sh" fonts "$@"
