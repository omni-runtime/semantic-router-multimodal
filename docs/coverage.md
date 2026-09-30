# Protocol coverage

Current implementation and limits are summarized in the [README](../README.md).
Recorded preview.10 acceptance is described in [validation](validation.md).

Supported native families include chat, speech, images, diffusion audio,
ASR/translation/image editing, synchronous/asynchronous video and native
WebSocket sessions. The MLX-specific contract is [documented separately](native-mlx-video.md).
Implementation presence, mock transport coverage and real-engine validation are
separate claims; consult the release contract and model capability cards.

Cross-wire native-media conversion, implicit multi-model workflows, async-video
listing, general model compatibility, long H3 video and load/throughput guarantees
are outside the current acceptance scope.
