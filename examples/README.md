# Native media request examples

These requests target an operator-deployed SR + Envoy gateway. Set `GATEWAY_URL`
and `GATEWAY_TOKEN` in your private shell; model aliases in requests are public
recipes, not concrete model bypasses. No example starts a model or calls another
model implicitly. Configure only capabilities that the loaded model actually has.

| Request fixture | Task | Verified transport |
| --- | --- | --- |
| chat-text.json | Text → text | JSON, SSE |
| chat-vision.json | Image + text → text | JSON, SSE |
| chat-audio.json | Audio + text → text | Native Chat |
| chat-video.json | Video + text → text | Native Chat |
| chat-mixed-output.json | Image + audio + text → text/audio | Native Chat JSON/SSE |
| speech.json | Given text → speech | WAV, PCM/SSE |
| images.json | Text → image | JSON base64/URL, native file |
| audio-generate.json | Text → generated audio | Native audio file |
| transcription.multipart.json | Audio → transcription | JSON/text/subtitle/SSE |
| translation.multipart.json | Audio → translated text | JSON/text/subtitle/SSE |
| image-edit.multipart.json | Image + text → edited image | Native multipart response |
| video-sync.multipart.json | Media + text → video | MP4 stream |
| video-create.multipart.json | Create a video job | Native job JSON, bound continuation |

The `.multipart.json` files are **client fixture descriptions**, not a JSON API
accepted by the backend. The client below turns them into native MIME parts.
Replace `example.invalid` reference URLs with media reachable by the selected
engine. SR preserves references; it does not download them. The WAV and MP4 assets
are valid synthetic transport fixtures and do not prove model understanding.

```sh
curl --fail-with-body "$GATEWAY_URL/v1/chat/completions" \
  -H "Authorization: Bearer $GATEWAY_TOKEN" -H 'Content-Type: application/json' \
  --data-binary @requests/chat-vision.json
python3 send-multipart.py requests/transcription.multipart.json > transcript.json
python3 send-multipart.py requests/video-sync.multipart.json > output.mp4
python3 send-multipart.py requests/video-create.multipart.json > task.json
```

Use the returned opaque task `id` in `GET /v1/videos/{id}`,
`GET /v1/videos/{id}/content`, or `DELETE /v1/videos/{id}` with the same caller
credential. These operations restore their original binding and never run a new
selection algorithm. Asynchronous tasks require the optional Redis binding store;
see the patched `website/docs/api/native-video-tasks.md` and release status.

For an image description followed by spoken output, the caller first reads the
Chat response and explicitly places its text in a second Speech request. Sending
only the first request does not cause TTS. A single model's native mixed Chat
output uses `modalities` and is separately represented by its own fixture.

Detailed mock/real/platform status is in `release.yaml` and `docs/coverage.md`.
WebSocket handshake, native text/binary frames, two utterances, cancellation,
backend disconnect and errors have separate mock acceptance evidence.

Native WebSocket client (consult `release.yaml` for acceptance):

```sh
python3 websocket_client.py speech --model local-only --text 'Hello.' > speech.wav
python3 websocket_client.py realtime --model auto --audio input-16khz-mono.pcm
```

The client reads the selected native model from the 101 handshake, then sends
native engine session frames. `input-16khz-mono.pcm` must be raw signed PCM16,
not a WAV container. `--audio-output` requests an audio-capable realtime candidate.
Events go to stderr and native binary speech bytes go to stdout. The script is a
caller example; it never runs a second model implicitly. Browser clients cannot
read the custom handshake model header; see the native realtime API document.
