#!/usr/bin/env bash
set -euo pipefail
checkout=${1:-/workspace/.work/upstream}
native=${2:-/workspace/.work/native/lib}
# Source verification and Go's VCS stamping trust only this operator-prepared
# mount; do not change the host's Git configuration or disable VCS metadata.
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0="$checkout"
python3 /workspace/scripts/verify-checkout.py "$checkout"
cd "$checkout"
export CGO_ENABLED=1
export CGO_LDFLAGS="-L$native"
export LD_LIBRARY_PATH="$native"
export GOPROXY=${GOPROXY:-https://goproxy.cn}
export GOMAXPROCS=${GOMAXPROCS:-3}
patch_digest=$(sha256sum /workspace/patches/0001-native-multimodal.patch | cut -d ' ' -f 1)
grep -q "$patch_digest" /workspace/patches/checksums.json
bash tools/docker/check-native-abi.sh "$native/libcandle_semantic_router.so" "$native/libonnx_semantic_router.so"
cd src/semantic-router
go test -p 3 ./pkg/llmprotocol ./pkg/protocolcodec ./pkg/selection ./pkg/decision ./pkg/catalog -count=1
go test -p 3 ./pkg/config ./pkg/configschema ./pkg/dsl -count=1
go test -p 3 ./pkg/extproc -count=1 -run 'Test(NativeEmbeddings|NativeMLXVideo|NativeRealtime|NativeVideoBinding|NativeVideoSync|NativeChatOutput|NativeMultipart|NativeAudio|NativeImages|NativeSpeech|SpeechDispatch|SpeechChunks|SpeechProvider|RequireEntrypoint|SingleCandidate|CapabilitySelection|PrepareProviderDispatch|EntrypointRouting|ProcessBodyRoutingError)'
mkdir -p /workspace/dist/linux-amd64
go build -p 3 -trimpath -o /workspace/dist/linux-amd64/router ./cmd
sha256sum /workspace/dist/linux-amd64/router
binary_digest=$(sha256sum /workspace/dist/linux-amd64/router | cut -d ' ' -f 1)
printf '{"patch_digest":"%s","binary_digest":"sha256:%s"}\n' "$patch_digest" "$binary_digest" > /workspace/dist/linux-amd64/build-inputs.json
