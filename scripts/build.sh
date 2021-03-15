#!/bin/sh

set -e

npm run build 1>&2

# Non-Git paths that should be included when deploying
echo "app/static"
echo "app/templates/govuk"
echo "app/content"
