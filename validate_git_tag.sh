readonly DOC="Checks that a specified tag for a git repo is derived from primary branch to be called when deploying to PROD
Usage: ${0} <tag>
Example: ${0} v1.0
"

if [ "$#" -ne 1 ]; then
    printf "%s\n" "${DOC}" >&2
    exit 1
fi

args=("$@")
TAG=${args[0]}

TAGGED_COMMIT=$(git rev-parse $TAG^{commit})

if git rev-list --first-parent main | grep $TAGGED_COMMIT >/dev/null; then
    echo "$TAG points to a commit reachable via first-parent from primary branch (main)"
else
    echo "$TAG does not point to a commit reachable via first-parent from primary branch (main)"
    exit 1
fi
