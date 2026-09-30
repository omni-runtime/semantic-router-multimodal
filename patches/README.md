# Patch maintenance

`series` and `checksums.json` identify the authoritative patch. The single patch
keeps the shared task, capability, codec, catalog and ExtProc contract atomic;
the isolated checkout is only an editing/build workspace. No patch changes an
engine or adds another request router. Upstream issue status was checked in
`docs/upstream-audit.md`; an open issue or draft PR is not released functionality.

| Area | Upstream relationship and reason | Regression / removal condition |
| --- | --- | --- |
| Speech | [#3954](https://github.com/vllm-project/semantic-router/issues/3954), [draft #4081](https://github.com/vllm-project/semantic-router/pull/4081): locked SR lacks complete native Speech dispatch | Speech task/capability, strict parameter preservation, WAV/SSE/error and no implicit Chat call pass against the replacement |
| Chat video and mixed output | [multimodal #3183](https://github.com/vllm-project/semantic-router/issues/3183): decoder lacks video content and native audio output preservation | Ordered mixed content, all input/output capability constraints, native JSON/SSE bytes and cancellation pass |
| Images / audio generation | #3183 is an umbrella issue, not an exact implementation PR; image sink exists but public ingress and native controls are incomplete | Native image parameters, file/b64/URL responses, separate diffusion audio task, errors and budget checks pass |
| Multipart ASR / translation / image editing | #3183 umbrella; no equivalent complete transport in locked SR | MIME/file/field preservation, task-specific constraints, size limits and native response formats pass |
| Sync / async video | #3183 umbrella; native protocol and continuation dispatch absent | MP4 passthrough, scoped instance binding, restart/storage failure/TTL behavior pass; migrate live binding records or drain jobs before removal |
| Realtime / speech stream | #3183 umbrella; header-only native task selection and upgrade handling absent | Exactly one native selection per handshake, declared capabilities, native frame hashes, same connection, cancellation/close/error cases pass |
| MLX-Serve H3 | Native MLX-Serve 26.9.6 video wire is distinct from chat and async video; no equivalent contract in the locked SR | Typed fields, keyframe bounds, hard capability/scope filtering, JSON/progress SSE and native RGB8/PCM16 passthrough pass against an upstream replacement |
| Shared strict routing / config | Existing recipes, decisions, algorithms and providers are retained; task filtering must also apply with one candidate | Single-candidate and preference-bypass checks, hard local/cloud isolation, generated catalog/schema round trips and upstream selection/decision tests pass |

For areas without a dedicated upstream issue/PR, this table explicitly names
the umbrella rather than inventing a tracker. Relevant source locations and
upstream engine contracts are in `docs/design.md` and the patched API docs.

To upgrade, prepare a new isolated checkout at the proposed upstream commit and
inspect each hunk. Drop only the functionality now supplied by upstream, then
regenerate public contracts and run `scripts/test.sh`, the native build, and the
same gateway fixture matrix. Compare request/response/task/session semantics,
not only API names or configuration acceptance. Keep prior release digests and
reports for rollback. Recompute the patch checksum and build both target
architectures; do not label an untested architecture accepted.

Release publication updates `release.yaml` only after actual gateway acceptance.
Project A consumes that contract and an immutable image, never this patch tree.
