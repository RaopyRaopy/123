# 智能旅行规划伴侣

记忆驱动的自由行规划工具。用户输入城市、天数、预算和偏好后，系统生成结构化行程，并联动天气、地图标点、附近美食和长期偏好记忆。

当前项目重点是两套规划模式：

- **规则模式**：默认模式。本地关键词和标签匹配，速度快，不依赖 LLM；仍会走天气、高德地图和附近美食。
- **Agent 模式**：LangChain + DeepSeek 工具调用，能结合预算、地点特性、偏好记忆生成更灵活的路线；速度较慢，失败时会自动重试并降级到规则模式。

## 核心功能

### 双模式规划

前端聊天页提供 `规则模式 / Agent 模式` 切换按钮，请求体也支持 `mode` 字段：

```json
{
  "message": "广州2天去小众景点，避开人多和商业化景点",
  "mode": "rules"
}
```

- `rules`：走 `app/services/planner.py` + `app/services/attractions.py`，根据城市、天数、关键词、避雷词进行本地排序。
- `agent`：走 `app/services/agent_planner.py`，调用 LangChain Agent、景点工具、天气工具和记忆工具。
- 不传 `mode` 时默认是 `rules`。
- `SMART_TRIP_USE_AGENT=1` 是旧配置思路，当前切换以页面按钮或请求体 `mode` 为准。

### 一天一个主景点

两种模式都约束为“每天一个主景点/片区”，但每天仍区分：

- 上午活动
- 下午活动
- 晚上活动
- 交通建议
- 天气提示

### 本地景点标签库

内置 10 个城市的标签化景点库。

### 天气和地图

- 天气：默认使用 Open-Meteo，无需 key；可选配置和风天气 `QWEATHER_API_KEY`。
- 地图：使用高德 JS API 展示地图。
- 地理编码：优先使用本地景点坐标，配置高德 key 后可调用高德 REST。
- 地图标点：标记每天的主景点，不再只标城市中心。

### 附近美食

每天主景点坐标确定后，会调用高德地图周边搜索。

### Agent 稳定性兜底

Agent 模式依赖模型结构化输出，因此有概率出现模型没有按格式收尾的情况。当前处理策略：

1. 第一次 Agent 输出不可解析时，自动重试一次。
2. 两次仍失败或接口异常时，自动用规则模式生成稳定行程。
3. 返回 `debug.agent_fallback = "rules"`，页面仍有行程，不会空白。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI + Uvicorn |
| 规则规划 | 本地城市/景点/标签库 |
| Agent | LangChain + LangChain OpenAI + DeepSeek |
| 天气 | Open-Meteo / 和风天气可选 |
| 地图 | 高德 JS API v2 + 高德 REST |
| 前端聊天页 | 原生 HTML/CSS/JavaScript |
| 前端介绍页 | React 19 + Vite |
| 存储 | JSON 文件，位于 `data/` |
| 通信 | HTTP REST + WebSocket |

## 本地运行

项目根目录双击：

```text
start-local-preview.bat
```

前端介绍页开发：

```powershell
npm install
npm run dev
```

构建介绍页：

```powershell
npm run build
```

