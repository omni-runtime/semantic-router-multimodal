#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
checkout=${1:-"$root/.work/prepared"}
python3 "$root/scripts/verify-checkout.py" "$checkout"
cd "$checkout/src/semantic-router"
export CGO_ENABLED=1
go test ./pkg/llmprotocol ./pkg/protocolcodec ./pkg/selection ./pkg/decision ./pkg/catalog -count=1
go test ./pkg/config ./pkg/configschema ./pkg/dsl -count=1
go test ./pkg/extproc -count=1 -run 'Test(NativeEmbeddings|NativeMLXVideo|NativeRealtime|NativeVideoBinding|NativeVideoSync|NativeChatOutput|NativeMultipart|NativeAudio|NativeImages|NativeSpeech|SpeechDispatch|SpeechChunks|SpeechProvider|RequireEntrypoint|SingleCandidate|CapabilitySelection|PrepareProviderDispatch|EntrypointRouting|ProcessBodyRoutingError)'
