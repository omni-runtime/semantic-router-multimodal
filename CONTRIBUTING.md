# Contributing

Thank you for contributing to semantic-router-multimodal. Please start with an issue for changes
that alter public protocols, deployment behavior, or the upstream patch boundary.
Small fixes can go directly to a pull request.

## Development

Use Python 3.12 or newer to prepare and verify the locked upstream checkout. Run `python scripts/validate-public.py`. For router changes, edit an isolated checkout, regenerate catalogs/schemas, export the patch with `scripts/export-patches.py --checkout PATH`, and run the native CGO tests in `scripts/test.sh` or `scripts/native-build.sh`. See [building](docs/building.md).

Keep each change focused. Explain the problem, the resulting behavior, tests
performed, and any limitation. Do not describe a mock test as a real-model test.
Include a regression test when fixing routing, protocol, credential, or lifecycle
behavior. Documentation-only changes do not require GPU tests.

## Architecture boundaries

- Envoy forwards requests; native Semantic Router performs task/capability and recipe selection.
- Python is an operator tool, never another request router or an implicit workflow engine.
- Do not weaken authentication or allow physical model names to bypass entrypoint policy.
- Engine start/stop and multi-step inference remain explicit operator/client actions.
- Preserve upstream attribution and the authoritative patch checksum.

## Commits and review

Sign off commits with `git commit -s` to certify the
[Developer Certificate of Origin](https://developercertificate.org/).
Use your own configured name and email. Contributions are under Apache-2.0.
Do not commit credentials, kubeconfigs, private addresses, raw production logs,
model weights, native libraries, or multi-gigabyte OCI archives.

Pull requests run lightweight source checks in GitHub Actions. Native builds,
GPU tests, and full gateway acceptance require the environments documented in
the project; maintainers must attach the corresponding evidence before changing
release acceptance claims.
