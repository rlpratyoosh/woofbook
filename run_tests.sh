#!/usr/bin/env bash
set -e

SCRIPT_DIRECTORY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_ENVIRONMENT_PYTHON="$SCRIPT_DIRECTORY/env/bin/python"

if [ -n "$VIRTUAL_ENV" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
    PYTHON_EXECUTABLE="$VIRTUAL_ENV/bin/python"
elif [ -x "$LOCAL_ENVIRONMENT_PYTHON" ]; then
    PYTHON_EXECUTABLE="$LOCAL_ENVIRONMENT_PYTHON"
else
    PYTHON_EXECUTABLE="$(command -v python3)"
fi

exec "$PYTHON_EXECUTABLE" "$SCRIPT_DIRECTORY/run_tests.py" "$@"
