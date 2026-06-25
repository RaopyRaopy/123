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

例如“广州2天小众景点”在规则模式下会优先生成：

```text
D1 广州老城：恩宁路和永庆坊早茶 / 粤剧艺术博物馆和荔枝湾 / 西关小巷觅食
D2 沙面：沙面建筑群慢走 / 沿江西路和人民桥周边 / 珠江边散步
```

### 本地景点标签库

内置 10 个城市的标签化景点库：

```text
重庆、北京、上海、成都、杭州、西安、广州、桂林、苏州、长沙
```

标签包括：小众、商业、风景、自然、户外、历史文化、美食、夜景、亲子、网红、城市、室内、古镇、文创、免费、远郊。

规则模式会直接在 `app/services/attractions.py` 中做关键词和标签匹配，重点保证响应速度。

### 天气和地图

- 天气：默认使用 Open-Meteo，无需 key；可选配置和风天气 `QWEATHER_API_KEY`。
- 地图：使用高德 JS API 展示地图。
- 地理编码：优先使用本地景点坐标，配置高德 key 后可调用高德 REST。
- 地图标点：标记每天的主景点，不再只标城市中心。

### 附近美食

每天主景点坐标确定后，会调用高德地图周边搜索：

- 半径：3km
- 数量：前 5 个
- 关键词：美食、餐厅、小吃、特色菜

结果会展示在行程卡片和地图信息窗里。

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

## 项目结构

```text
app/
  main.py                   FastAPI 入口、模式选择、HTTP API、WebSocket
  models.py                 请求和响应模型，ChatRequest.mode 在这里定义
  services/
    planner.py              规则模式规划与行程调整
    agent_planner.py        LangChain Agent 模式、重试和规则兜底
    agent_tools.py          Agent 可调用工具和结构化输出模型
    attractions.py          城市景点库、标签匹配、本地景点坐标
    geo.py                  高德地理编码、3km 美食搜索
    weather.py              Open-Meteo / 和风天气服务
    memory.py               JSON 长期记忆
    llm.py                  DeepSeek / Ollama 状态检查与旧适配器
    config.py               环境变量加载
  static/
    index.html              聊天页
    app.js                  模式切换、WebSocket、地图渲染
    styles.css              聊天页样式
    landing/                React 介绍页构建产物
src/                         React 介绍页源码
data/                        用户记忆和聊天会话
tests/                       规则模式和 Agent 解析/重试测试
```

## 本地运行

### 推荐启动方式

项目根目录双击：

```text
start-local-preview.bat
```

这个脚本会固定使用项目内的虚拟环境：

```text
.venv\Scripts\python.exe
```

访问地址：

```text
http://127.0.0.1:8000
http://127.0.0.1:8000/chat
```

### 首次安装或依赖缺失

如果出现 `ModuleNotFoundError: No module named 'langchain'`，通常是 `.venv` 里没有安装 Agent 依赖。请在项目根目录执行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

安装后关闭旧的后端窗口，重新运行 `start-local-preview.bat`。

### 手动启动后端

不要直接用全局 `uvicorn`，否则可能出现“全局 Python 有包，但项目 `.venv` 没包”的环境错位。建议这样启动：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

开发时需要自动重载可以加：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

### 前端介绍页开发

```powershell
npm install
npm run dev
```

构建介绍页：

```powershell
npm run build
```

构建产物输出到 `app/static/landing/`，后端会直接托管。

## 环境配置

在项目根目录创建 `.env`，可参考 `.env.example`。

```text
# DeepSeek，Agent 模式需要
DEEPSEEK_API_KEY=你的 DeepSeek API Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
SMART_TRIP_USE_DEEPSEEK=1

# 高德地图，地图和附近美食需要
AMAP_API_KEY=你的高德 Web端 Key
AMAP_SECURITY_CODE=你的高德安全密钥

# 可选：如果 REST 和 JS 分开用不同 key
AMAP_REST_KEY=你的高德 REST Key

# 可选：和风天气
QWEATHER_API_KEY=你的和风天气 Key

# 可选：本地 Ollama 状态检查
SMART_TRIP_USE_OLLAMA=1
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:7b
```

说明：

- 规则模式不需要 DeepSeek key。
- Agent 模式需要 `DEEPSEEK_API_KEY`。
- 地图 JS 展示需要 `AMAP_API_KEY` 和必要的安全密钥。
- 附近美食优先读 `AMAP_REST_KEY`，没有时回退读 `AMAP_API_KEY`。

## API 端点

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/health` | GET | 服务健康检查 |
| `/api/chat` | POST | 对话式行程规划，支持 `mode: "rules" | "agent"` |
| `/ws/chat` | WebSocket | 实时双向通信，前端聊天页默认使用 |
| `/api/profile/{user_id}` | GET | 用户偏好与历史 |
| `/api/profile/{user_id}/preferences` | DELETE | 清除偏好记忆 |
| `/api/weather/{city}` | GET | 逐日天气预报 |
| `/api/llm/status` | GET | Ollama / DeepSeek 状态检查 |
| `/api/config/amap-key` | GET | 前端读取高德 JS key |

## 请求示例

规则模式：

```json
{
  "user_id": "demo-user",
  "session_id": "demo-session",
  "message": "广州2天去小众景点，避开人多和商业化景点",
  "mode": "rules"
}
```

Agent 模式：

```json
{
  "user_id": "demo-user",
  "session_id": "demo-session",
  "message": "广州2天去小众景点，避开人多和商业化景点，预算5000",
  "mode": "agent"
}
```

## 演示输入

```text
广州2天去小众景点，避开人多和商业化景点
广州2天去网红景点
今天广州下雨了，想改成室内活动
北京3天，预算5000，想看历史文化和安静街区
深圳2天去小众景点
```

其中 `深圳` 当前未收录，应返回“暂未收录”，不会推荐其他城市替代。

## 验证命令

项目 `.venv` 默认不一定安装 pytest，因此可直接用标准库测试：

```powershell
.\.venv\Scripts\python.exe -m compileall app tests
.\.venv\Scripts\python.exe -m unittest discover -s tests
node --check app\static\app.js
```

如果当前环境安装了 pytest，也可以运行：

```powershell
python -m pytest -q
```

## 常见问题

### Agent 模式报 `No module named 'langchain'`

你启动的是 `start-local-preview.bat`，它使用项目 `.venv`。把依赖装进 `.venv`：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

然后重启 `start-local-preview.bat`。

### Agent 偶尔无法回复

Agent 依赖模型按结构化格式返回。当前代码已加入一次自动重试，并在失败后降级到规则模式。可查看响应里的：

```text
debug.agent_failed
debug.agent_fallback
debug.agent_failure_reason
```

### 规则模式为什么也会请求天气和地图

这是当前设计：规则模式只是不走 LLM，但仍会获取天气、景点坐标、地图 marker 和高德 3km 附近美食。

### 地图或美食不显示

检查 `.env`：

```text
AMAP_API_KEY=...
AMAP_SECURITY_CODE=...
```

如果只配置了本地景点坐标但没有高德 key，后端仍能生成坐标，前端地图和附近美食可能不可用。

## 后续可完善

- 扩展更多城市和景点标签。
- 给天气和高德接口加缓存，减少重复请求。
- 前端展示 Agent 是否发生了规则兜底。
- 为 WebSocket 错误和地图渲染补充更多端到端测试。
