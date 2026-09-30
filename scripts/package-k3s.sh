#!/usr/bin/env bash
set -euo pipefail
cd /workspace
base_digest=sha256:295a7da1ac432c950667083208a5a227e695efdc7b53502139d4c80c0b18b061
base="ghcr.io/vllm-project/semantic-router/extproc@$base_digest"
mkdir -p dist
if [[ ! -f dist/base-amd64.oci.tar ]]; then
  /node/k3s ctr --address /run/k3s/containerd/containerd.sock --namespace k8s.io images export \
    --platform linux/amd64 dist/base-amd64.oci.tar.tmp "$base"
  mv dist/base-amd64.oci.tar.tmp dist/base-amd64.oci.tar
fi
patch_digest=$(python3 -c 'import json; print(json.load(open("patches/checksums.json"))["0001-native-multimodal.patch"])')
python3 -c 'import hashlib,json; p=json.load(open("patches/checksums.json"))["0001-native-multimodal.patch"]; b=json.load(open("dist/linux-amd64/build-inputs.json")); assert b["patch_digest"] == p; assert b["binary_digest"] == "sha256:"+hashlib.file_digest(open("dist/linux-amd64/router","rb"),"sha256").hexdigest()'
commit=$(python3 -c 'import json; print(json.load(open("upstream.lock.json"))["commit"])')
python3 scripts/package-oci.py --base dist/base-amd64.oci.tar --base-digest "$base_digest" \
  --binary dist/linux-amd64/router \
  --schema .work/upstream/src/semantic-router/pkg/configschema/router-config-v0.3.schema.json \
  --output dist/sr-linux-amd64.oci.tar --platform linux/amd64 \
  --reference "docker.io/inference-stack/semantic-router-multimodal:dev-${patch_digest:0:12}" \
  --commit "$commit" --patch-digest "$patch_digest"
/node/k3s ctr --address /run/k3s/containerd/containerd.sock --namespace k8s.io images import \
  --platform linux/amd64 --digests dist/sr-linux-amd64.oci.tar
# containerd 2.3's transfer importer retains the archive tag but does not add
# its repository@digest alias. Register that immutable reference explicitly.
tag=$(python3 -c 'import json; print(json.load(open("dist/sr-linux-amd64.oci.json"))["tag"])')
reference=$(python3 -c 'import json; print(json.load(open("dist/sr-linux-amd64.oci.json"))["reference"])')
/node/k3s ctr --address /run/k3s/containerd/containerd.sock --namespace k8s.io images tag --force "$tag" "$reference"
