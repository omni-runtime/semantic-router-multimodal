#!/usr/bin/env bash
set -euo pipefail
cd /workspace
patch_digest=$(python3 -c 'import json; print(json.load(open("patches/checksums.json"))["0001-native-multimodal.patch"])')
python3 -c 'import hashlib,json; p=json.load(open("patches/checksums.json"))["0001-native-multimodal.patch"]; b=json.load(open("dist/linux-arm64/build-inputs.json")); assert b["patch_digest"] == p; assert b["binary_digest"] == "sha256:"+hashlib.file_digest(open("dist/linux-arm64/router","rb"),"sha256").hexdigest()'
commit=$(python3 -c 'import json; print(json.load(open("upstream.lock.json"))["commit"])')
python3 scripts/package-oci.py --base dist/base-arm64.oci.tar \
  --base-digest sha256:295a7da1ac432c950667083208a5a227e695efdc7b53502139d4c80c0b18b061 \
  --binary dist/linux-arm64/router \
  --schema .work/upstream/src/semantic-router/pkg/configschema/router-config-v0.3.schema.json \
  --output dist/sr-linux-arm64.oci.tar --platform linux/arm64 \
  --reference "docker.io/inference-stack/semantic-router-multimodal:dev-${patch_digest:0:12}-arm64" \
  --commit "$commit" --patch-digest "$patch_digest" \
  --build-method cross-cgo-qemu-tests-plus-verified-oci-layer
# This is an OCI artifact, not native Docker acceptance or a registry push.
