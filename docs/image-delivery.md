# Image delivery

See [building and artifact delivery](building.md) for current instructions and
[validation](validation.md) for historical local OCI provenance. Public source
publication does not publish the referenced images to a registry.

## Configure deployment in project A

Project B owns the build and `release.yaml`. Hosts, backends, model bindings and
credentials are configured once in project A's `stack.yaml`. Do not maintain
machine-specific deployment settings in this repository's illustrative native
router configuration or build templates.

From the project A checkout, import the contract without rewriting it:

```bash
python scripts/configure.py import-release \
  --source ../semantic-router-multimodal/release.yaml \
  --output locks/router.local.yaml
```

Set `artifacts.release: ../../locks/router.local.yaml` in
`instances/<name>/stack.yaml`. Project A selects the image matching the gateway
platform and validates the required protocol/capability contract. The import
checks immutable image identifiers and preserves exact source bytes; it does not
publish the image or create new acceptance evidence. See project A's
[configuration guide](https://github.com/omni-runtime/inference-stack/blob/main/docs/configuration.md).
