# semantic-router-multimodal

[![CI](https://github.com/omni-runtime/semantic-router-multimodal/actions/workflows/ci.yml/badge.svg)](https://github.com/omni-runtime/semantic-router-multimodal/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

**Reproducible native multimodal protocol extensions for vLLM Semantic Router.**

[简体中文](README.zh-CN.md) · [Build guide](docs/building.md) ·
[Protocol examples](examples/README.md) · [Validation](docs/validation.md)

This repository maintains a checked patch set against a pinned upstream commit.
It extends the native Go task, capability, codec, catalog and ExtProc layers so
one SR/Envoy gateway can route text, images, audio, video and native sessions.
Deployment and operations live in the companion
[inference-stack](https://github.com/omni-runtime/inference-stack) repository.

It is an independent integration project, not an official vLLM distribution.

## Features

- [Native embedding routing](docs/native-embeddings.md): text batches and multimodal inputs, with vector-space, dimension and batch qualification.
- Native task/capability filtering before model selection, including the single-candidate case.
- Hard `auto` / `local-only` / `cloud-only` entrypoint and recipe enforcement.
- Native chat multimodal input/output and same-wire media preservation.
- Speech, images, diffusion audio, multipart ASR/translation/image editing, and video dispatch.
- Scoped Redis bindings for asynchronous video continuations.
- Native WebSocket handshake selection and same-session frame passthrough.
- **MLX-Serve H3 video**: typed native request, progress SSE and RGB8/PCM16 response preservation.
- Source verification, native CGO builds, ARM64 cross-build tooling and OCI provenance.

There is no additional Python inference proxy, automatic engine lifecycle, or
server-side multi-model business workflow. Envoy transports the request selected
by native SR. Model capabilities must match the concrete engine and weights.

## Source of truth

```text
upstream.lock.json + patches/series + patches/checksums.json
                         │
                         ▼
                isolated prepared checkout
                         │
                         ▼
          native tests → build → OCI artifact → gateway acceptance
```

The lock pins upstream commit `5aa0145eb16ddf7edcc40a87793f61260e8c5084` and schema
`v0.3`. A prepared checkout is an editing/build workspace, not another source of truth.

## Quick start: prepare and verify

Requires Python **3.12+** and Git. No GPU is needed to prepare the source.

```bash
git clone https://github.com/omni-runtime/semantic-router-multimodal.git
cd semantic-router-multimodal
python3 scripts/prepare.py --output .work/prepared
python3 scripts/verify-checkout.py .work/prepared
```

Preparation clones the locked upstream, verifies patch checksums and applies the
patches without modifying another checkout. To build a native Linux image on a
matching host:

```bash
docker build --platform linux/amd64 -f build/Dockerfile \
  -t semantic-router-multimodal:dev .work/prepared
```

Use `linux/arm64` on native ARM64 Linux, or the documented cross-build path. The
full build retains upstream native bindings and requires compatible native
libraries/ABI; a CGO-disabled build is not a supported router runtime.
See [building and artifact delivery](docs/building.md) for prerequisites,
CGO tests, OCI packaging and deployment-contract updates.

> **Preview source release:** `0.1.0-preview.11`. Historical image digests in
> `release.yaml` identify tested local OCI artifacts, **not public registry packages**.
> Build/import your own artifact and validate it before real deployment.

## Protocols and scope

| Area | Contract |
| --- | --- |
| Chat | Native multimodal content, tools/structured output and declared audio output |
| Speech, images, audio | Typed tasks and native parameter/response preservation |
| Multipart | ASR, translation, image editing and synchronous video |
| Async video | Concrete-instance bindings; create/query/content/delete |
| Realtime | Native handshake selection; one upstream connection per session |
| MLX video | `/v1/video/generations`; JSON/progress SSE; RGB8/PCM16 final media |

Cross-wire native-media translation is not implemented. Engine/model support,
configured capabilities and output limits determine what can run. H3 media must
be muxed by the client; it is not the asynchronous video-job protocol.
[Native MLX contract](docs/native-mlx-video.md) · [Request design](docs/design.md)

## Validation

Preview.10 passed **48 mock gateway cases on each of AMD64 and native ARM64**,
real text/cloud suites, and short H3 video generation before/after an MLX restart.
The [sanitized evidence](docs/validation.md) separates those recorded runs from
lightweight public CI and lists untested areas. It is not a universal hardware or
all-model compatibility guarantee.

## Repository guide

| Path | Purpose |
| --- | --- |
| `upstream.lock.json` | Pinned upstream source and toolchain metadata |
| `patches/` | Authoritative patch, checksums and maintenance/removal rules |
| `scripts/` | Prepare, verify, test, build and package commands |
| `build/` | Native Dockerfile and adaptable Kubernetes build manifests |
| `examples/` | Native router configuration and request fixtures |
| `validation/` | Sanitized acceptance and build artifact metadata |
| `release.yaml` | Companion-project deployment contract |

## Contributing, security and license

Read [CONTRIBUTING.md](CONTRIBUTING.md), [patch maintenance](patches/README.md)
and [community expectations](CODE_OF_CONDUCT.md). Report vulnerabilities through
[SECURITY.md](SECURITY.md).

[Apache-2.0](LICENSE). Upstream attribution is retained in [NOTICE](NOTICE) and
prepared sources. Native libraries, engines, base images and model weights retain
their own licenses; this repository does not distribute weights.

## Deployment configuration ownership

Configure deployment once in project A's `stack.yaml`, with credentials in its
referenced private dotenv file. This repository continues to own native source,
build locks and `release.yaml`; it does not need another copy of your host/model
settings. See [contract delivery to project A](docs/image-delivery.md#configure-deployment-in-project-a).

The embedding extension is included in [preview.11](release.yaml); its
[acceptance report](validation/preview.11.json) records native AMD64/ARM64 gateway
tests and real Qwen 2B/Ark embedding, chat and H3 checks.

Embedding acceptance: **39/39 mock gateway cases on each architecture**, **17/17
real embedding/chat cases**, **8/8 existing chat/vision cases**, and **3/3 H3
cases**. See [preview.11 evidence and limits](validation/preview.11.json).

## ALP extension ownership

Cloud ALP Function Calling is maintained separately in
[semantic-router-alp](https://github.com/omni-runtime/semantic-router-alp).
Use its locked composition to combine ALP and multimodal support in one SR image.
This repository owns the multimodal base; its release metadata describes that base only.
