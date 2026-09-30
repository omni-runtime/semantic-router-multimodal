# Native MLX-Serve H3 video

`api_format: mlx_video`, provider `mlx-serve`, catalog protocol `mlx/video@1`,
and wire format `mlx.video.v1` route `POST /v1/video/generations` through native
SR capability/recipe selection. This contract targets MLX-Serve 26.9.6 and the
MiniMax-H3 FL2VA pack. H3 runs on a macOS Metal host; the SR/Envoy gateway runs
in the Linux Kubernetes VM.

Requests accept `model`, `prompt`, `stream`, `width`, `height`, `num_frames`,
`steps`, `seed`, `turbo`, `fast`, `chain_windows`, `first_frame_image`,
`last_frame_image`, `preview`, `preview_frames`, and `preview_max_side`.
Keyframes must be base64 PNG/JPEG. Dimensions are multiples of 32, up to 2048;
steps are 1–1000, with a minimum of 4 for turbo. Chain windows are 1–6.
Unsupported fields, host-local LoRA paths, reference-partition inputs and chat
output budgets are rejected before backend dispatch. Model capability cards
must explicitly declare image input for keyframes and video/audio output.

The response is the engine's JSON containing base64 `rgb8` frames and
`pcm_s16le` audio. With `stream: true`, progress SSE ends in a `type: complete`
payload. SR preserves this wire; it does not create video jobs or transcode
media. The caller decodes/muxes frames and PCM using the returned frame count,
FPS and audio metadata. H3 may snap requested frames to its native temporal
ladder; callers must use the returned count.

`auto`, `local-only`, and `cloud-only` retain normal entrypoint/recipe rules.
Physical model names and client-supplied routing headers cannot bypass them.
Cross-wire projection into chat, speech or Omni video is rejected. Successful
native media responses bypass ExtProc body processing, keeping large video
payloads out of the router's buffered codec. Envoy applies an explicit
per-model timeout; service lifecycle remains an operator action in project A.

Upstream contract: https://github.com/ddalcu/mlx-serve/tree/v26.9.6
