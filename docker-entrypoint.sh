#!/bin/sh
# Detect the UID/GID of the workspace bind-mount, then drop privileges to
# match it before starting the server. This means files written into the
# workspace (decompile cache, progress notes) end up owned by the host user
# regardless of who they are, with zero host-side configuration.
set -eu

WORKSPACE="${ILSPY_WORKSPACE:-/workspace}"

if [ -d "$WORKSPACE" ]; then
    TARGET_UID=$(stat -c %u "$WORKSPACE")
    TARGET_GID=$(stat -c %g "$WORKSPACE")
else
    TARGET_UID=1000
    TARGET_GID=1000
fi

# If the mount is root-owned (e.g. Docker auto-created the directory because
# nothing was bind-mounted, or the user mounted a brand-new volume), fall back
# to a non-root default and take ownership so subsequent writes succeed.
if [ "$TARGET_UID" = "0" ]; then
    TARGET_UID=1000
    TARGET_GID=1000
    chown "$TARGET_UID:$TARGET_GID" "$WORKSPACE" 2>/dev/null || true
fi

exec setpriv \
    --reuid="$TARGET_UID" \
    --regid="$TARGET_GID" \
    --clear-groups \
    python3 -m ilspy_mcp
