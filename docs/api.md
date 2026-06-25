# API 说明

## GET /api/health

检查服务是否可用。

响应示例：

```json
{
  "status": "ok",
  "service": "smart-travel-companion"
}
```

## GET /api/profile/{user_id}

读取用户画像、历史行程和反馈记忆。

## POST /api/chat

提交一轮对话。后端会更新记忆、判断意图，并返回文本回复、行程、命中的记忆和主动提醒。

请求示例：

```json
{
  "user_id": "demo-user",
  "session_id": "optional-session-id",
  "message": "广州2天去小众景点，避开人多和商业化景点"
}
```

响应中的关键字段：

- `reply`：给用户看的自然语言回复。
- `itinerary`：结构化行程，包含每天的城市、主题、上午、下午、晚上、交通和天气提示。
- `memory_hits`：本次规划调用到的偏好、历史行程或反馈。
- `reminders`：系统主动生成的行前或行中提醒。
- `quick_actions`：前端可展示的下一步对话建议。

## WebSocket /ws/chat

消息格式与 `POST /api/chat` 一致，返回 `ChatResponse` JSON。当前版本按整条消息返回，后续可扩展为 token 流式响应。

## GET /api/llm/status

检查 Ollama/Qwen 和 DeepSeek 适配器状态。DeepSeek 默认读取 `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL` 和 `DEEPSEEK_MODEL`。
