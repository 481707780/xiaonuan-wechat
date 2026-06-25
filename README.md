# 🌸 小暖 — AI 情感伴侣（风格注入版）

一个温暖、私密的 AI 对话伴侣，支持 **移动端 PWA** 和 **微信公众号**（小暖aini）两种方式对话。

## ✨ 最新特性：真实聊天风格注入

基于你的真实聊天数据分析，自动将以下内容注入到 AI 系统提示词中：

- **说话风格分析** — 简洁直接、口语化、真实情感表达
- **女生朋友真实回复范例** — 来自 5287 条真实对话的学习样本
- **个人聊天风格参考** — 来自 10514 条个人聊天记录的语调模仿
- **风格分析概要** — 平均句长、语气词偏好、幽默感程度等

每次对话时，AI 伴侣都会加载这些风格数据，让回复更自然、更像真人。

---

## 🚀 快速开始（3 步）

### 1. 安装依赖
`ash
cd soul-companion
pip install -r backend/requirements.txt
`

### 2. 配置 API Key
编辑 .env，填入你的 Key：
`env
OPENAI_API_KEY=sk-你的key
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
`

### 3. 启动
`ash
python run.py
# 浏览器打开 http://localhost:8000
`

---

## 📱 手机上使用（小暖aini 公众号）

关注微信公众号 **小暖aini**，直接发消息即可对话。

### 本地开发
- **同一 WiFi**：手机访问 http://172.25.152.54:8000
- **Cloudflare Tunnel**：cloudflared tunnel --url http://localhost:8000

---

## 💬 微信接入指南

### 前提条件
1. 已注册微信公众号 **小暖aini**（个人订阅号，免费）
2. 有一台带 HTTPS 的公网服务器

### 配置步骤
1. 公众号后台 → 设置与开发 → 基本配置
2. 服务器配置：
   - **URL**：https://你的域名/wechat
   - **Token**：与 .env 中 WECHAT_TOKEN 一致
   - 消息加解密方式：明文模式
3. 提交验证，通过后用户即可对话

---

## 📊 风格数据管理

| 接口 | 说明 |
|------|------|
| GET /wechat/style-status | 查看风格数据注入状态 |
| POST /wechat/style-reload | 重新加载风格数据 |
| GET /health | 健康检查（含风格注入状态） |

风格数据文件位于 data/ 目录：
- style_profile.json — 风格分析概要
- ll_female_replies.txt — 女生朋友真实回复样本
- my_chat_style.txt — 个人聊天风格参考

---

## 🛠 项目结构

`
soul-companion/
├── backend/app/
│   ├── main.py              # FastAPI 入口（含风格注入日志）
│   ├── config.py            # 配置（含伴侣人格 Prompt）
│   ├── routers/
│   │   ├── chat.py          # /api/chat 聊天接口
│   │   └── wechat.py        # /wechat 微信 Webhook（含风格管理接口）
│   └── services/
│       ├── companion.py     # AI 核心（动态注入风格数据）
│       ├── style_loader.py  # 风格数据加载与注入服务（新增）
│       └── session.py       # SQLite 会话持久化
├── data/                    # 风格数据文件（已注入）
│   ├── style_profile.json
│   ├── all_female_replies.txt
│   └── my_chat_style.txt
├── frontend/                # PWA 聊天界面
├── Dockerfile               # Docker 部署（含数据文件）
├── .env.example
├── run.py
└── README.md
`

## 🔧 API 接口

| 接口 | 说明 |
|------|------|
| POST /api/chat | 发送消息 |
| POST /api/chat/stream | 流式聊天（SSE） |
| POST /api/chat/clear | 清除历史 |
| GET /api/chat/history | 查对话记录 |
| GET /wechat | 微信服务器验证 |
| POST /wechat | 接收微信消息 |
| GET /wechat/style-status | 风格数据注入状态 |
| POST /wechat/style-reload | 重载风格数据 |
