# 上游能力核对（2026-09-29）

本地检查工作树：semantic-router、vllm、vllm-omni 均干净。SR 开发位于本项目
`.work/upstream` 隔离 checkout，不更改原仓库。

| 组件 | 锁定/观察版本 | 文档/API 注册 | 模型支持与链路实测 |
|---|---|---|---|
| SR | 5aa0145eb16ddf7edcc40a87793f61260e8c5084 | Chat/Responses/Anthropic、Images sink codec | 补丁后 K8s/amd64 与 Docker/arm64 的 SR＋Envoy 已实测 |
| vLLM 源码 | 31f2e70cd3e403aaa471fb7fe3d33a7207aaf3cc | Chat、多模态、ASR、Realtime 路径 | 注册路径不代表当前 Qwen3 支持所有任务 |
| Omni 源码 | 8a49c65bf9e477338173339540186577086d1cf4 | Chat、Speech、audio/generate、Images/edits、Videos、WebSocket | 每个接口依赖实际加载模型及配置 |
| K8s | v1.36.4+k3s1 / containerd 2.3.4 | 现有集群可访问 | 当前节点 Ready；报告在项目 A |
| Docker | Engine 29.5.2 / API 1.54 / linux-arm64 | 08:00 后实测 | 七组合 mock 781、真实云端 8、异步绑定 10 通过；本机 GPU/权重 blocked |
| Compose | 宿主 5.1.4，工具镜像 5.5.1 | 两个不同客户端 | 宿主归一化配置检查；工具版本完整七组合部署 |

历史部署 digest 只作为待核实来源，不能据此声称新镜像已测试：
SR 295a7da1ac432c950667083208a5a227e695efdc7b53502139d4c80c0b18b061；
Envoy 05ca04d64e3b899f73e64a9ff4a2cf0407bc8bba060cb579229421e125d74ca9；
Omni 6f8be103eaf0055448cf7578cfd621405fd669079d4361bd58896326b2bf722a。

## 原生与缺口

- [SR Router API](https://vllm-sr.ai/docs/api/router/) 与
  [协议矩阵](https://vllm-sr.ai/docs/installation/protocol-compatibility/)：以本地
  `pkg/protocolcodec` 为实施基线。ImagesCodec 已有后台图像生成转换，公开
  `/v1/images/generations` 在锁定版 header validator 仍被拒绝。
- [输入模态](https://vllm-sr.ai/docs/tutorials/signal/heuristic/input-modality/)：
  文档仍明确数据面 decoder 不接受 video 内容，配置枚举不能算视频正向支持。
- [Speech #3954](https://github.com/vllm-project/semantic-router/issues/3954) open；
  [#4081](https://github.com/vllm-project/semantic-router/pull/4081) 的 GitHub API
  新检查为 open、draft=true、merged=false，3 commits、6 files，head
  `4e689a731ecd4a79140098f2fec4ebdb055f68d1`。更新于 `2026-09-27T13:13:30Z`。
  已比历史增加 Speech IR 和能力测试，但没有 codec、ExtProc ingress/dispatch 或响应
  处理；未合并、未发布。本项目不将该 draft 直接当实现复用，补丁保留同义命名并
  自行补全请求/响应和集成测试。
- [#3183](https://github.com/vllm-project/semantic-router/issues/3183) 仍 open，
  标记 accepted/in-progress，不能据此宣称所有模态已交付。
- [vLLM serving](https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/)：
  API 注册与模型任务分开；Qwen3-0.6B 仅作文本验证。
- [Omni serving](https://docs.vllm.ai/projects/vllm-omni/en/latest/serving/)：
  `vllm_omni/entrypoints/openai/protocol/{audio,images,videos}.py` 是字段核对依据。
  Qwen3-TTS 只验证语音任务，不代表整个 Omni 生态。K8s 实际加载版本为 vLLM 0.28.0、Omni 0.28.0；Docker 本机引擎尚未加载。

## Docker 官方依据

[GPU 设备请求](https://docs.docker.com/compose/how-tos/gpu-support/)、
[contexts](https://docs.docker.com/engine/manage-resources/contexts/)、
[启动等待](https://docs.docker.com/compose/how-tos/startup-order/)、
[Desktop GPU](https://docs.docker.com/desktop/features/gpu/) 已查阅。
GPU devices 需要 capabilities，不能同时设置 count 和 device_ids。依赖需要
service_healthy，容器运行不等于模型可用。Desktop 官方 GPU 页面描述 Windows
WSL2 支持，不能由此推断 macOS CUDA 可用；以容器可见设备和镜像架构为准。

## 拟用方案与证据等级

原生 recipes/decisions/algorithms/provider binding 不重写；补齐媒体 codec、
任务能力和 ExtProc 传输边界。初次尝试 CGO_ENABLED=0 暴露上游不可编译的可选依赖，已放弃此构建路径，
未保留临时可选依赖修补。改用 K8s 构建 Pod、CGO_ENABLED=1 与锁定上游镜像中的
Candle/ORT/ML/NLP 原生库；库 SHA256 已与运行容器逐个匹配，ABI 检查已通过。
原生镜像要求 GLIBC_2.39，Bookworm 失败证据在 reports/kubernetes/kubernetes/native-build-01；
Trixie 构建镜像已锁定，协议/selection/decision 通过，ExtProc 发现的 415 错误映射已补齐并重测。
构建/单元/codec/ExtProc/真实 Envoy 集成分别出证据。

Docker 当前实测全部待执行；K8s 环境盘点不代表新链路通过。逐接口状态见 coverage.md。
