# semantic-router-multimodal

[English](README.md) · [构建指南](docs/building.md) · [协议样例](examples/README.md)

**可复现的 vLLM Semantic Router 原生多模态协议扩展。**

仓库用锁定的上游 commit＋补丁序列维护 Go 原生任务、能力、codec、catalog 和 ExtProc
扩展。配套 [inference-stack](https://github.com/omni-runtime/inference-stack) 负责部署和运维。
本项目是独立集成项目，不是 vLLM 官方发行版。

## 能力

- [原生 embedding 路由](docs/native-embeddings.md)：文本批量与多模态输入，向量空间、维度和批量上限校验。
- 选模前的任务能力、上下文与范围过滤，包括只有一个候选的场景。
- `auto`、`local-only`、`cloud-only` 入口；物理模型名不能绕过策略。
- Chat 多模态输入/输出，Speech、Images、音频生成，以及 multipart 媒体任务。
- 异步视频实例绑定、Redis 作用域和 TTL；原生 WebSocket 握手与同连接帧透传。
- MLX-Serve H3 原生视频参数、进度 SSE 与 RGB8/PCM16 结果透传。
- 源码一致性验证、原生 CGO 构建、ARM64 交叉构建和 OCI 产物元数据。

Envoy 执行转发，原生 SR 决定任务与模型；不增加 Python 请求代理、自动引擎启停或业务工作流。

## 准备源码

需要 Python 3.12+ 和 Git：

```bash
git clone https://github.com/omni-runtime/semantic-router-multimodal.git
cd semantic-router-multimodal
python3 scripts/prepare.py --output .work/prepared
python3 scripts/verify-checkout.py .work/prepared
```

权威来源为 `upstream.lock.json`、`patches/series` 和 `patches/checksums.json`。
准备目录只是隔离工作区；修改后必须导出补丁，再从新目录验证。构建示例：

```bash
docker build --platform linux/amd64 -f build/Dockerfile \
  -t semantic-router-multimodal:dev .work/prepared
```

完整运行时保留 CGO/native bindings，必须匹配 Linux 架构、glibc 和原生库 ABI。
详见[构建文档](docs/building.md)。无 CGO 的协议单测不能替代原生运行时验收。

## 发布与验证

当前为 **0.1.0-preview.11 源码预览版**。契约中的镜像摘要对应本地构建和导入的
验收产物，尚未推送公共镜像仓库；部署前需要自行构建、导入并验证镜像。

已记录 AMD64、原生 ARM64 各 48 项 mock 网关检查，以及真实文本/云端和 H3 短视频验证。
[公开摘要](docs/validation.md)保留测试范围及原始报告 SHA256，排除了内部机器信息和日志。
不将旧版本完整矩阵当成本次重跑结果，也不宣称已验证所有模型、视频长度和并发负载。

H3 使用 `/v1/video/generations`；结果是原生 JSON/SSE，包含 RGB8 画面和 PCM16 音轨，
由客户端封装成 MP4。详见[MLX 协议](docs/native-mlx-video.md)。

## 贡献、上游与许可

请阅读[贡献指南](CONTRIBUTING.md)、[补丁维护规则](patches/README.md)和
[安全报告方式](SECURITY.md)。代码采用 [Apache-2.0](LICENSE)，保留上游归属与声明，
见 [NOTICE](NOTICE)。模型权重、引擎、原生库与基础镜像保留各自许可证。

## 统一部署配置

实际主机、后端地址、模型与路由配置统一放在项目 A 的 `stack.yaml`，密钥由私有
`secrets.env` 提供。本仓库继续维护构建锁定和 `release.yaml`，A 通过契约导入命令
读取构建结果，无需在 A/B 两边手动修改同一套部署信息。
详见[交付与配置边界](docs/image-delivery.md#configure-deployment-in-project-a)。

Embedding 已接入本地 Qwen3-VL-Embedding-2B 与云端方舟豆包：两种架构各
39/39 项模拟后端验收、17/17 项真实 embedding/聊天、8/8 项原有聊天/视觉和
3/3 项 H3 回归通过。详见 [preview.11 验证记录](validation/preview.11.json)。
