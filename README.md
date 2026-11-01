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

1. **Python 3.10+**，并安装依赖（macOS/Linux 上命令一般是 `python3`）：

   ```bash
   python -m pip install curl_cffi
   ```

2. **Node.js**（LTS 版即可，用于 `npx` 运行 mediawiki-mcp-server，首次启动自动下载）

> 支持 Windows / macOS / Linux；启动器会自动按平台选择 `npx` 的正确调用方式。

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

   > - Windows 上 `command` 建议写 Python 的完整路径，例如
   >   `"C:/Users/你的用户名/AppData/Local/Programs/Python/Python313/python.exe"`
   > - macOS / Linux 上通常写 `"python3"` 或完整路径（如 `"/usr/bin/python3"`），
   >   `args` 里的脚本路径按实际克隆位置填写（如 `"/Users/你/ff14-cnwiki-mcp/server.py"`）

3. 重启 MCP 客户端，即可让 AI 助手查询 FF14 维基，例如：
   - 「查一下灰机wiki上'究极神兵'的页面」
   - 「搜索所有标题以'幻想药'开头的页面」

## 给 AI Agent 的部署指令

如果你想让对方的 AI Agent 全自动完成部署，把下面这段提示词连同本仓库链接一起发给它即可：

```text
请帮我在本机部署这个 MCP 服务器：https://github.com/SelkieMoejun/ff14-cnwiki-mcp
它是一个查询 FF14 中文维基（灰机wiki）的只读 MCP，请按以下步骤执行，每步完成后向我汇报结果：

1. 【环境检测】先检测本机是否已安装 Python 3.10+ 和 Node.js：
   - 运行 python --version（Windows 上若无反应再试 py --version）和 node --version
   - 把检测结果明确告诉我。如果缺少其中任何一个，先询问我是否同意由你帮忙安装
     （Windows 可用 winget，macOS 可用 brew），得到我同意后再安装；如果我选择自己装，
     就停下来等我装好再继续。
2. 【克隆代码】环境齐全后，询问我想把代码放在哪个目录（可建议一个默认位置），
   然后执行 git clone https://github.com/SelkieMoejun/ff14-cnwiki-mcp.git
3. 【安装依赖】用第 1 步确认的 Python 执行：python -m pip install curl_cffi
4. 【写入配置】找到我正在使用的 MCP 客户端的配置文件（WorkBuddy 是
   ~/.workbuddy/mcp.json，Claude Desktop 是 claude_desktop_config.json；修改前先读
   出现有内容，只在 mcpServers 里新增、不要覆盖其他条目），加入：
   "ff14-wiki": { "command": "<Python 完整路径>", "args": ["<克隆目录>/server.py"], "timeout": 60000 }
   写完后把最终配置路径告诉我。
5. 【验收】提示我重启 MCP 客户端。重启后做一次连通性自检：调用 ff14-wiki 的
   search-page 工具搜索「陆行鸟」，能返回结果就是部署成功；失败则查看系统临时目录下的
   ff14-wiki-mcp-proxy.log 排查原因并向我说明。

注意：server.py 不需要也不应该被我手动常驻运行，它由 MCP 客户端按需通过 stdio 拉起。
```

> 提示：以上提示词对 WorkBuddy、Claude Code、Cursor 等具备命令执行能力的 Agent 均适用；
> 纯对话型 AI 无法执行命令，只能由人照 README 手动操作。

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
