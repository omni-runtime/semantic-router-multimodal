# 多模态请求设计

状态：完整范围实施中；已验证子集以 preview 发布。完整范围见 coverage.md；拒绝能力不代表正向支持。

客户端每次新推理进入 Envoy，由 ExtProc 调用 SR。SR 的入口解析产生
`llmprotocol.Request`，原生 signals → decisions → selection 选择候选，
provider binding/codec 编码请求，Envoy 执行实际 HTTP 转发。

```text
客户端 ──HTTP/SSE/WebSocket──> Envoy ──HTTP──> 被 SR 选中的模型后端
                              │   ▲
                              │   │ ExtProc 请求/响应控制
                              ▼   │
                       SR 协议、能力、规则、选模
```

项目不新增独立代理、分类器或业务工作流。图片理解后 TTS 是调用方发起的两次请求，
各有独立 request_id。只发第一次请求不会生成第二次推理。Omni 内部模型 stages 仍由引擎负责。

## 任务与传输

Chat 保留上游中立 IR、tools、结构化输出和 SSE；补齐已知的多模态内容解析缺口。
Speech 作为独立 wire format，`speech_generation` 与 `audio_output` 分开；结构化
`input` 直接变成中立文本供原生 signals 使用，voice/format/speed 等保存在 Speech
任务字段，不构造伪 Chat HTTP 请求。图像生成沿用 Images codec 并补齐公开入口；
图像编辑、ASR 的 multipart 需保留文件和各任务参数，并施加有界输入限制。

模型能力归属于 model card；协议传输能力归属于 codec。不能根据 vLLM/Omni 名称
推断任务能力。候选能力与上下文过滤在选模算法之前发生，只有一个候选同样检查。
`model` 是公开 recipe 名或受约束偏好，`provider_model_id` 是后端请求中的真实模型 ID，
`endpoint`/`base_url` 是网络绑定，`api_format` 是线协议，不表示推理引擎。

## 上游落点

| 阶段 | 上游文件/目录 | 改动目的 |
|---|---|---|
| HTTP 入口识别 | pkg/extproc/processor_req_header_endpoints.go | 识别 Speech、Images 和后续媒体入口 |
| 输入校验 | pkg/extproc/processor_req_header_validation.go | Method/Content-Type/路径检查 |
| 中立任务 | pkg/llmprotocol | 独立任务参数、输入输出与传输能力 |
| codec | pkg/protocolcodec | 严格解析，保留参数，按目标模型编码 |
| 候选检查 | pkg/extproc/selection_capabilities.go、pkg/selection | 复用原生能力约束和算法 |
| 路由与 provider | pkg/extproc/processor_protocol_contract.go 等 | 选择后的 URL、模型、鉴权编码 |
| 响应 | pkg/extproc/processor_res_header.go、processor_res_body*.go | 二进制/流式透传及协议转换 |
| 配置 | pkg/config、pkg/configschema | 原生 schema 与生成物同步 |

公开入口只开放配置中的 auto/local-only/cloud-only recipes。具体后端别名不能直接
跳过决策；local-only recipe 只含本地 refs，cloud-only 只含云端 refs，默认关闭故障
回退和业务重试。客户端内部路由头在入口去除，路由目的地只能由本次 SR 决策生成。

## 响应、流与状态

同协议媒体响应由 Envoy 受控透传，保留状态码、Content-Type、二进制字节及错误。
不把音频当 Chat JSON 解码。请求限制、路由超时、后端超时分别配置；流开始后不重放。
SSE 检查结束标志、后端中断和客户端取消。长音视频响应不在 SR 完整缓冲。

异步视频创建先决策，再将任务 ID 与 provider/model/endpoint 绑定；查询/下载/删除
进入 SR 的状态分发，不能重新选模。绑定需带租户与 TTL，跨副本采用共享存储。
实时 WebSocket 在握手时按协议与模型能力选路，会话期间 Envoy 保持同一上游连接；
不能声称 ExtProc 可检查每个 WebSocket 帧。帧协议、断连和取消需独立验收。

这两类状态功能是完整目标的一部分，只有完成实现及对应测试后才进入 release 能力。
不支持的端点/字段明确报错，状态报告不得把报错计为接口通过。

异步视频的具体实现复用上游 `contextcompression.RecoveryStore` 的 Redis 后端、
有界总容量、租户 scope 与 TTL，使用独立 `vsr:media-binding:v1:` namespace，
不复用压缩内容记录、不新增队列或工作流服务。创建仍经原生选模，随后保存逻辑模型、
具体 endpoint/provider、实例声明、recipe 指纹和引擎任务 ID。对外返回随机任务 ID；
后续 GET/DELETE 只恢复并核对绑定，沿 provider 的路径/鉴权逻辑分发，不运行选模。
绑定以入口已验证的 Authorization 摘要隔离；凭据原文不进入状态或日志。

每个有状态 backend 必须显式声明单个实例或共享任务存储的稳定身份。项目 A 的本地
视频服务限制单副本；多个副本以独立 backend/逻辑别名登记，不能经负载均衡 Service
随机访问副本。配置/实例身份改变、TTL 到期、Redis 不可用均拒绝恢复，不选其他模型。
仅有界任务 JSON 进入响应缓冲；下载仍由 Envoy 分块透传。创建前检查存储，创建后
保存失败明确报错；无法证明创建结果时不重放，也不偷偷取消已创建的引擎任务。

## 交付与升级

权威修改来源是锁定 commit + patches/series。`.work/upstream` 仅为隔离工作树；
prepare 从干净 commit 应用 patch，test 测协议与路由，build 产出相同 SR 行为的目标
架构镜像。项目 A 只消费 release 契约和镜像，不复制源码。

## Multipart 媒体入口实施设计

转录、翻译和图片编辑分别使用独立 task/capability 与 wire format。codec 接收真实
Content-Type/boundary，解析有界 multipart，而非将文件包装成 Chat HTTP 请求。
文件进入中立媒体内容，表单参数保留在类型明确的 multipart operation 中；未知字段、
重复的单值字段、错误文件数量、非法枚举/数值在入口拒绝。上下文检查仍对音频输入与
显式文字输出预算生效；图片编辑与图片生成一样使用非 token 输出预算。

`Engine.DecodeHTTPRequestForMutation` 在原有 codec 边界增加 HTTP 元数据入口；
只有实现该接口的 codec 使用 Content-Type。普通 JSON codec 行为不变。Envelope
保存有界 MIME boundary，选模后 codec 重建 multipart、替换 provider model ID，
ExtProc 同时更新 Content-Type 和 Content-Length。不保存上传文件到磁盘，不读取
用户文件名指向的本地路径。客户端和 mock 后端用文件与字段摘要验证保真。

同协议 ASR 文本/JSON/字幕/SSE、图片编辑结果及错误走原生媒体响应透传，不引入业务
重试或第二次推理。Envoy 请求体上限为 16 MiB；大于此限制明确失败，响应保持分块。
流式长音频上传和跨协议 multipart 转换不由这个有界 HTTP 上传契约暗示支持。

## 原生 WebSocket 实现边界

`llmprotocol.RealtimeSession` 与两个 codec 描述握手中的协议、音频输入和输出要求；
`processor_realtime_transport.go` 验证 GET/Upgrade/版本/key/查询参数，再复用
`routeSemanticRequest` 的信号、决策、算法和 provider 编码。Realtime 会话是原生
路由事实，空请求体不绕过决策，也不伪造 Chat prompt。普通 Chat 或 Speech 候选
缺少 realtime/对应任务能力时被剔除。公开 recipe 只在握手选择，协议错误明确拒绝。

最终 ExtProc 响应设置 request/response body NONE，Envoy 原生升级后固定同一上游
TCP 连接；SR 不查看或重写帧。每个协议的 session model 必须与握手选中模型匹配，
由原生引擎校验。原生客户端读取 `x-vsr-realtime-provider-model` 后构造 session
配置；浏览器 WebSocket API 不能读取该自定义响应头，需预先配置相容的引擎别名。
SR 查询约束不会传到引擎，仅保留编码后的 native model。断连结束会话，重连执行
新的能力判断与决策；无隐式重试、跨模型恢复或状态迁移。

HTTP body 插件和多模型 looper 无法表示升级后帧语义，因此明确拒绝。帧协议、
帧内 token 上限、生成参数及用量由引擎负责；SR 只对声明的握手任务做能力检查。
原生实时协议不等同于任意供应商 Realtime API。实现文档及配置见补丁中的
`website/docs/api/native-realtime.md`；测试按 WebSocket 连接独立比对帧和关闭状态。
