# Embedding request routing

Source and artifacts are recorded in `release.yaml` (preview.11). The
[acceptance report](../validation/preview.11.json) records 39 native gateway cases
per architecture, plus real Qwen 2B/Ark embedding and chat/H3 regression checks.
Historical preview.10 full-media evidence is preserved separately.

The public operation is `POST /v1/embeddings`. Envoy authenticates the caller,
native SR validates the request and chooses a declared embedding backend, and
Envoy forwards the request and response. Embedding requests do not become Chat
Completions requests and do not enable SR's internal semantic classifiers.

The existing `auto`, `local-only`, and `cloud-only` entrypoints retain their scope.
Only models declaring the embedding task and the concrete input capabilities can
be selected. Cloud and local are deployment scopes, not separate wire protocols.

## Input and output contract

- OpenAI text embedding input: one string, a nonempty string batch, one token-ID
  sequence, or a batch of token-ID sequences. A backend must explicitly support
  token input before receiving it. Preserve item order and batch boundaries.
- Multimodal embedding uses the vLLM `messages` extension, separate from `input`.
  Supported input modalities must be declared by the model. Do not interpret
  arbitrary vendor fields as interchangeable multimodal contracts.
- Preserve `dimensions`, `encoding_format` (`float` or `base64`), and `user`.
  Reject unsupported fields, streaming, empty input, mixed batch types, invalid
  dimensions, and conflicting input forms before dispatch.
- Same-wire responses, usage, indices, backend errors, and rate-limit headers
  pass through. Ark responses receive only the container conversion described
  below; vectors never become Chat messages or change their values.

## Vector-space isolation

Model configuration declares an embedding space, default/supported dimensions,
and batch limit. A space identifies weights/revision, tokenizer and processor,
pooling, normalization, and relevant precision choices. Equal vector length alone
does not establish compatibility. Quantized variants have distinct space IDs
unless an operator has validated interoperability for the actual application.

The optional request field `embedding_space` constrains native selection and is
consumed by SR. It is not forwarded to an OpenAI backend. If a recipe contains
multiple compatible spaces and the caller does not choose one, fail explicitly
instead of changing the vector space according to candidate order. No implicit
cross-space fallback, model substitution, or retry is introduced.

Dimension and batch limits are checked before model selection. Context limits
apply to each item, not the sum of a batch. The selected space is exposed in a
response header so clients can record the vector identity with their index.

## Project A and deployment

Project A's `stack.yaml` owns backend URL, scope, authentication references,
model identity, embedding constraints, and host runtime settings. Credentials
remain in the private dotenv file. Public examples contain no fleet addresses.

On Apple Silicon, a host embedding engine exposes the same authenticated HTTP
operation to the K8s gateway. It loads the actual embedding checkpoint, performs
the model's prescribed last-token pooling and normalization, and limits batch,
input size, and concurrency. It is a model engine, not a second router. The
existing video and text engines keep their own endpoints and weights.

Real deployment requires measured memory headroom with the existing H3 workload.
If the requested checkpoint cannot coexist safely, the operator chooses a
quantized variant, a smaller checkpoint, or an explicit scheduling policy before
weights are downloaded and the service is started.

## Validation

Protocol tests cover batch fidelity, native input forms, dimensions, encoding,
malformed input, and task isolation. Native SR integration covers local/cloud
scope, vector-space conflicts, model capabilities, forged routing headers,
authentication, and backend error passthrough. Real model checks cover finite
vectors, dimensionality, normalization, repeatability, text/image retrieval, and
memory usage. Existing Chat and H3 requests are regression checked after rollout.

Cloud acceptance requires a real embedding model and credentials. A successful
mock route or a Chat-only cloud model is not cloud embedding acceptance.

References: [Qwen model card](https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B),
[vLLM embedding API](https://docs.vllm.ai/en/stable/models/pooling_models/embed/),
[MLX Embeddings](https://github.com/Blaizzy/mlx-embeddings).

## Ark multimodal backend

`api_format: ark_embeddings` and `provider: volcengine-ark` select the native Ark
codec. Configure the provider base URL ending in `/api/v3`; SR uses the
`/embeddings/multimodal` operation. Clients continue to call `/v1/embeddings`.
One text input or one joint text/image `messages` sample becomes one Ark content
array. Independent text batches and token IDs are rejected, never fused.
System text maps to Ark `instructions`; unsupported `user`, video, sparse and
multi-vector options are rejected. The adapter preserves post-policy text.

Ark's response `data` object becomes a single indexed element in `data[]`.
Embedding numbers/base64, model/request identity, nested modality token usage,
provider HTTP status and errors retain their values. Conversion happens only at
the native transport boundary; generation response plugins do not process vectors.

For `doubao-embedding-vision-251215`, declare default dimensions 2048,
`min_dimensions: 1024`, `allowed_dimensions: [1024, 2048]`, and
`max_batch_size: 1`. These are discrete dimensions; the router excludes 1536.
`embedding.image_token_estimate` optionally replaces the generic per-image
admission reserve for a bounded engine image processor. It is not an exact
usage count. The Qwen host deployment uses a 1024-token estimate with a
262144-pixel resize cap and an independent 4096-token engine guard.

The two embedding models have distinct space IDs, even at equal dimensions.
Use `local-only`, `cloud-only`, or an explicit `embedding_space` with `auto`.
Keep model revision, preprocessing and query/corpus instruction conventions
consistent within an application index.

[Ark protocol and instruction guide](https://docs.volcengine.com/docs/ark/vectorization?lang=zh).
