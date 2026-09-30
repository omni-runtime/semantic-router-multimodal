# Build context is a clean prepare.py output. Build natively for each target.
ARG SR_BASE=ghcr.io/vllm-project/semantic-router/extproc@sha256:295a7da1ac432c950667083208a5a227e695efdc7b53502139d4c80c0b18b061
FROM ${SR_BASE} AS native
FROM golang@sha256:a02d35efc036053fdf0da8c15919276bf777a80cbfda6a35c5e9f087e652adfc AS builder
COPY --from=native /app/lib /native
WORKDIR /source
COPY . .
ENV CGO_ENABLED=1 CGO_LDFLAGS=-L/native LD_LIBRARY_PATH=/native
RUN bash tools/docker/check-native-abi.sh /native/libcandle_semantic_router.so /native/libonnx_semantic_router.so
WORKDIR /source/src/semantic-router
RUN go test ./pkg/llmprotocol ./pkg/protocolcodec ./pkg/selection ./pkg/decision ./pkg/catalog && \
    go test ./pkg/config ./pkg/configschema ./pkg/dsl && \
    go test ./pkg/extproc -run 'Test(NativeMLXVideo|NativeRealtime|NativeVideoBinding|NativeVideoSync|NativeChatOutput|NativeMultipart|NativeAudio|NativeImages|NativeSpeech|SpeechDispatch|SpeechChunks|SpeechProvider|RequireEntrypoint|SingleCandidate|CapabilitySelection|PrepareProviderDispatch)' && \
    go build -trimpath -o /out/router ./cmd
FROM native
COPY --from=builder /out/router /app/router-candle
COPY --from=builder /out/router /app/router-onnx
COPY --from=builder /out/router /app/router-openvino
COPY --from=builder /source/src/semantic-router/pkg/configschema/router-config-v0.3.schema.json /app/share/router-config-v0.3.schema.json
ENTRYPOINT ["/app/router-candle"]
