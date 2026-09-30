#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
checkout=${1:-"$root/.work/prepared"}
arch=${2:-amd64}
case "$arch" in amd64|arm64) ;; *) echo "unsupported build target: $arch" >&2; exit 2;; esac
python3 "$root/scripts/verify-checkout.py" "$checkout"
mkdir -p "$root/dist/linux-$arch"
cd "$checkout/src/semantic-router"
CGO_ENABLED=1 GOOS=linux GOARCH="$arch" go build -trimpath -o "$root/dist/linux-$arch/router" ./cmd
echo "Built SR binary for linux/$arch with native bindings."
echo "This is not an image/deployment verification. Publish immutable image evidence before release."
