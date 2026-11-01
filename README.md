# ff14-cnwiki-mcp

让 AI 助手（WorkBuddy / Claude / 其他支持 MCP 的客户端）直接查询 **FF14 中文维基（灰机wiki，ff14.huijiwiki.com）** 的 MCP 服务器。

## 为什么需要它

灰机wiki 有 Cloudflare 人机验证，普通 HTTP 客户端（Node/axios 等）的 TLS 指纹会被 403 拦截，AI 助手直接联网抓取经常拿不到正文。本项目在本机起一个代理，用 `curl_cffi` 模拟 Chrome 浏览器指纹转发请求，再对接开源的 [mediawiki-mcp-server](https://www.npmjs.com/package/@professional-wiki/mediawiki-mcp-server) 提供标准 MCP 接口。

- **只读**：只能查询，不能修改维基（`config.json` 中 `readOnly: true`）
- **纯本地**：代理仅监听 `127.0.0.1`，不含任何账号密钥
- **自带缓存**：GET 请求缓存 5 分钟，减少重复请求

## 提供的工具（20 个）

| 分类 | 工具 |
|---|---|
| 搜索 | `search-page` 关键词搜索、`search-page-by-prefix` 标题前缀匹配 |
| 读页面 | `get-page`、`get-pages`（批量）、`get-revision`（历史版本）、`get-file` / `get-file-data` |
| 站点结构 | `get-category-members` 分类成员、`get-links-here` 链入页面、`get-site-info` |
| 语义查询 | `smw-query`、`smw-list-properties`（按属性批量查数据，如"所有 90 级装备"） |
| 其他 | `get-page-history`、`get-recent-changes`、`compare-pages`、`parse-wikitext` 等 |

## 安装要求

1. **Python 3.10+**，并安装依赖：

   ```bash
   python -m pip install curl_cffi
   ```

2. **Node.js**（LTS 版即可，用于 `npx` 运行 mediawiki-mcp-server，首次启动自动下载）

## 使用方法

1. 克隆本仓库：

   ```bash
   git clone https://github.com/SelkieMoejun/ff14-cnwiki-mcp.git
   ```

2. 在你的 MCP 客户端配置中加入（以 WorkBuddy / Claude Desktop 为例，编辑 `mcp.json`）：

   ```json
   {
     "mcpServers": {
       "ff14-wiki": {
         "command": "python",
         "args": ["C:/你的路径/ff14-cnwiki-mcp/server.py"],
         "timeout": 60000
       }
     }
   }
   ```

   > Windows 上 `command` 建议写 Python 的完整路径，例如
   > `"C:/Users/你的用户名/AppData/Local/Programs/Python/Python313/python.exe"`

3. 重启 MCP 客户端，即可让 AI 助手查询 FF14 维基，例如：
   - 「查一下灰机wiki上'究极神兵'的页面」
   - 「搜索所有标题以'幻想药'开头的页面」

## 工作原理

```
MCP 客户端
   │ stdio
   ▼
server.py（本启动器）
   ├─ 本地代理 127.0.0.1:8787（curl_cffi 模拟 Chrome 指纹 → 灰机wiki）
   └─ npx @professional-wiki/mediawiki-mcp-server（走代理访问站点 API）
```

## 环境变量（可选）

| 变量 | 默认值 | 说明 |
|---|---|---|
| `FF14_WIKI_TARGET` | `https://ff14.huijiwiki.com` | 目标站点，理论上也适用于其他灰机系维基 |
| `FF14_PROXY_PORT` | `8787` | 本地代理端口 |
| `FF14_WIKI_CONFIG` | `server.py` 同目录的 `config.json` | 维基站点配置文件路径 |
| `FF14_PROXY_ONLY` | 未设置 | 设为 `1` 时只起代理、不启动 MCP（调试用） |

日志写在系统临时目录：`%TEMP%\ff14-wiki-mcp-proxy.log`

## 免责声明

本项目仅用于个人学习查询，数据版权归灰机wiki及原编辑者所有。请控制查询频率，不要对站点造成压力。
