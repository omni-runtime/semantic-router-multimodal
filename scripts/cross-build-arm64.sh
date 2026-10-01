#!/usr/bin/env bash
# Executed in the dedicated Kubernetes cross-build container, not on a host.
set -euo pipefail
cd /workspace
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0=/workspace/.work/upstream
python3 scripts/verify-checkout.py .work/upstream
mkdir -p dist/linux-arm64
# The locked Debian build image ships HTTP apt endpoints. Use their HTTPS
# equivalents and persist package archives across disposable build Pods.
sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources
mkdir -p /workspace/.work/apt-cache-arm64/partial
apt-get update
mapfile -t cross_packages < build/cross-dependencies.lock
apt-get -o Dir::Cache::archives=/workspace/.work/apt-cache-arm64 install --no-install-recommends -y "${cross_packages[@]}"
dpkg-query -W gcc-aarch64-linux-gnu gcc-14-aarch64-linux-gnu libc6-dev-arm64-cross qemu-user \
  > dist/linux-arm64/compiler-packages.txt
dpkg-query -W > dist/linux-arm64/all-build-packages.txt
native=/workspace/.work/native-arm64/rootfs
runner=/workspace/.work/native-arm64/qemu-run.sh
cat > "$runner" <<'RUNNER'
#!/usr/bin/env bash
set -euo pipefail
root=/workspace/.work/native-arm64/rootfs
exec qemu-aarch64 -L "$root" -E "LD_LIBRARY_PATH=$root/app/lib:$root/usr/lib64:$root/usr/lib" "$@"
RUNNER
chmod 755 "$runner"
export GOOS=linux GOARCH=arm64 CGO_ENABLED=1 CC=aarch64-linux-gnu-gcc
export CGO_LDFLAGS="-L$native/app/lib"
export GOPROXY=${GOPROXY:-https://goproxy.cn}
export GOMAXPROCS=${GOMAXPROCS:-3}
cd .work/upstream/src/semantic-router
go test -p 3 -exec "$runner" ./pkg/llmprotocol ./pkg/protocolcodec ./pkg/selection ./pkg/decision ./pkg/catalog -count=1
go test -p 3 -exec "$runner" ./pkg/config ./pkg/configschema ./pkg/dsl -count=1
go test -p 3 -exec "$runner" ./pkg/extproc -count=1 -run 'Test(NativeEmbeddings|NativeMLXVideo|NativeRealtime|NativeVideoBinding|NativeVideoSync|NativeChatOutput|NativeMultipart|NativeAudio|NativeImages|NativeSpeech|SpeechDispatch|SpeechChunks|SpeechProvider|RequireEntrypoint|SingleCandidate|CapabilitySelection|PrepareProviderDispatch|EntrypointRouting|ProcessBodyRoutingError)'
go build -p 3 -trimpath -o /workspace/dist/linux-arm64/router ./cmd
"$runner" /workspace/dist/linux-arm64/router --help > /workspace/dist/linux-arm64/runtime-help.txt 2>&1
cd /workspace
patch_digest=$(sha256sum patches/0001-native-multimodal.patch | cut -d ' ' -f 1)
binary_digest=$(sha256sum dist/linux-arm64/router | cut -d ' ' -f 1)
printf '{"patch_digest":"%s","binary_digest":"sha256:%s","execution":"qemu-user-emulated-tests; native target acceptance pending"}\n' \
  "$patch_digest" "$binary_digest" > dist/linux-arm64/build-inputs.json
sha256sum dist/linux-arm64/router
