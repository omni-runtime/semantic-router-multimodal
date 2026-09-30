# Building and delivering the router

## Source preparation

Python 3.12+ and Git are required. `upstream.lock.json` pins the upstream commit
and Go toolchain baseline. `prepare.py` creates a new directory; it never resets
an existing checkout. Use `--source /path/to/upstream-clone` for an existing clone,
or omit it to clone the public upstream. Every patch checksum is checked first.

```bash
python3 scripts/prepare.py --output .work/prepared
python3 scripts/verify-checkout.py .work/prepared
```

The verifier compares the worktree with locked upstream plus patches using a
temporary Git index. It does not modify your real index or reset HEAD.

## Native image build

Use a Linux Docker engine on the target architecture. The pinned base supplies
native libraries; the pinned Go builder must satisfy their ABI requirements.

```bash
docker build --platform linux/amd64 -f build/Dockerfile \
  -t semantic-router-multimodal:dev .work/prepared
```

On native ARM64 choose `linux/arm64`. Emulated builds are not native-runtime
acceptance. The Dockerfile checks native ABI, runs the affected Go package tests
and targeted ExtProc cases, builds the router, and installs the generated schema.
Image/model downloads can be substantial; no model weights are part of this repo.

`CGO_ENABLED=1` and the native library search paths are required for a complete
router runtime. A build with missing native classifiers is not equivalent. Native
libraries and container base layers keep their upstream licenses.

## Kubernetes/native and cross-build tooling

`build/k8s/` contains operator templates. Replace `gpu-node`, `/srv/semantic-router-multimodal`,
resource limits and optional GOPROXY values for your build environment. Some
packaging Pods mount the node containerd socket and K3s executable to export/import
images. Use them only on an explicitly authorized build node; remove those Pods
after collecting artifacts. They are not business-serving manifests.

The native script expects the repository mounted at `/workspace`, a prepared
checkout (default `.work/upstream`) and matching libraries in `.work/native/lib`:

```bash
bash /workspace/scripts/native-build.sh /workspace/.work/upstream /workspace/.work/native/lib
```

ARM64 cross builds use `scripts/cross-build-arm64.sh`, locked Debian packages,
a native ARM64 base rootfs and QEMU package tests. See
`build/k8s/cross-build-arm64.yaml` and `build/cross-dependencies.lock`.
The cross-build proves selected package behavior under QEMU; deployment still
requires native ARM64 gateway acceptance.

## OCI packaging and release acceptance

`scripts/package-oci.py --help` describes the generic packager. It verifies the
base descriptor/layer hashes, inserts the native binary and schema, and writes an
OCI archive plus JSON metadata. The K3s wrappers add platform and source checks,
import the archive, and register the immutable image alias. `dist/` is ignored.

A locally built image is not a published registry package. Either import the OCI
archive into every target node or push an image to a registry you control. Record
the actual digest, architecture, upstream commit, patch hash and binary hash.
Update the companion project's local release contract to that exact artifact.

Acceptance progresses from `built-unit-tested` to `tested-with-mock`, then to
`tested-with-real-backend` only with corresponding evidence. Candidate testing
must explicitly use mock backends. Do not transfer historical acceptance claims
to a newly built or changed binary. The checked-in preview.10 image digests are
historical local artifacts, not promised public pull URLs.

## Editing the patch

Modify an isolated prepared checkout, follow its nearest upstream `AGENTS.md`,
regenerate affected catalogs/schemas, and run relevant native tests. Then export:

```bash
python3 scripts/export-patches.py --checkout .work/prepared
python3 scripts/prepare.py --output .work/verify-new
python3 scripts/verify-checkout.py .work/verify-new
```

Run `scripts/test.sh` only with native libraries available. Lightweight CI also
runs the pure protocol packages without CGO; that subset is not full runtime
validation. See [patch maintenance](../patches/README.md) for upstream/removal rules.
