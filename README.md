# Workilot Plugins

[简体中文](#中文安装说明)

**Turn tasks into action.** Connect AI agents to Workilot through MCP to capture
bugs, act on improvement suggestions, execute ready work, and report results and
workflow status.

This repository distributes plugins only. The Workilot API, web console, mobile
app, and their source history are maintained separately on GitArk. You need an
existing Workilot service; installing this plugin does not deploy that service.
Model inference, code execution, and scheduled runs are provided by the agent
client, with people involved in key decisions and result verification.

## Install in Codex

Requires a Codex version with `codex plugin` support, Git, and Python 3.10 or later.

### 1. Install from GitHub

```bash
codex plugin marketplace add starsarc/workilot-plugins
codex plugin add workilot-mcp@workilot
```

### 2. Connect your Workilot service

Create an Agent API key in the Workilot console's MCP Access page, with MCP scopes,
capabilities, and project access appropriate to your work. Make it available to
the **Codex process** as `WORKILOT_MCP_TOKEN`, then register your deployed endpoint:

```bash
codex mcp add workilot \
  --url "https://<workilot-host>/mcp" \
  --bearer-token-env-var WORKILOT_MCP_TOKEN
```

Replace the URL with your actual service address. The console provides a command
using its current address. Codex reads the token from the named environment
variable; the plugin does not store it. Do not paste the key into chat or commit
it to a repository. For desktop Codex, ensure the desktop process inherits this
variable; setting it only in a separate terminal does not update an already
running application.

### 3. Reload Codex and bind your repository

Restart or reload Codex, open your target repository, and ask:

> Use Workilot, bind this repository, and show pending tasks.

Select an authorized project when prompted. The plugin writes non-secret binding
metadata to `.workilot/project.toml`. It then uses that project for task discovery,
bug reports, execution results, and status updates. See the [plugin reference](workilot-mcp/README.md)
for included skills, permissions, and migration from AgentPilot.

### Offline installation

Download the versioned ZIP from your Workilot console, verify its SHA-256 checksum,
and extract it. In the extracted root (containing `.agents/` and `workilot-mcp/`), run:

```bash
codex plugin marketplace add .
codex plugin add workilot-mcp@workilot
```

Then follow steps 2 and 3 above. The offline package has the same plugin files as
the GitHub distribution.

### Updates and troubleshooting

Refresh the GitHub marketplace and install the current plugin, then reload Codex:

```bash
codex plugin marketplace upgrade workilot
codex plugin add workilot-mcp@workilot
```

If `codex plugin` is unavailable, update Codex to a version that supports plugins.
If local binding tools fail to start, check `python3 --version` (3.10+). For remote
connection errors, check the service URL, the Codex process environment, and the
Agent key's scopes and project authorization. Never print the token when diagnosing.

## 中文安装说明

Workilot 通过 MCP 连接 AI Agent，让 Bug、优化建议和项目任务进入自动化执行流程。
GitHub 仅分发插件；主服务和主项目源码保留在 GitArk。安装插件前需要有可访问的
Workilot 服务，插件本身不部署服务。

1. 准备支持 `codex plugin` 的 Codex、Git，以及 Python 3.10 或更高版本。
2. 在终端执行上方两条 GitHub 安装命令。
3. 在 Workilot 控制台的 MCP 接入页面创建 Agent API Key，配置所需 scope、能力和项目权限。
   将 Key 设为 **Codex 进程**可读取的 `WORKILOT_MCP_TOKEN` 环境变量，再执行上方
   `codex mcp add workilot` 命令，将示例 URL 替换为实际服务的 `/mcp` 地址。
   控制台也提供使用当前服务地址的可复制命令。不要把 Key 粘贴到聊天或提交到仓库。
   桌面版 Codex 必须继承该环境变量；在另一个终端设置变量不会改变已运行应用的环境。
4. 重新启动或重新加载 Codex，在目标仓库中输入：
   “使用 Workilot，绑定当前仓库并查看待办任务”。按提示选择一个已授权项目。
5. 绑定保存在 `.workilot/project.toml`，不包含 Token。之后可让 Agent 提交 Bug、
   处理待办、落实优化建议并回写结果和状态。模型调用、代码执行及定时运行由 Agent 客户端承担。

离线安装可在控制台下载 ZIP 和 SHA-256 校验文件，校验并解压后，在解压根目录运行
`codex plugin marketplace add .` 和 `codex plugin add workilot-mcp@workilot`，再完成连接和绑定。
更新 GitHub 插件时执行上方 Updates 中的命令，然后重新加载 Codex。

详细技能、项目绑定和旧配置迁移参见 [Workilot MCP](workilot-mcp/README.md)。

## License

The plugin is distributed under the [MIT License](LICENSE).
