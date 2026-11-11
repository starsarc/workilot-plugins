# Workilot Plugins

[简体中文](#中文安装说明)

Connect Codex to Workilot through MCP to capture bugs, act on improvement suggestions,
execute ready work, and report results and workflow status.

This repository distributes plugins only. The Workilot API, web console, mobile app,
and their source history are maintained separately on GitArk. Installing the plugin
does not deploy the Workilot service.

## Install in Codex

Requires Codex with plugin support, Git, and Python 3.10 or later.

```bash
codex plugin marketplace add starsarc/workilot-plugins
codex plugin add workilot-mcp@workilot
```

Open a repository and ask Codex to connect to Workilot. The plugin opens Workilot in
your browser. Sign in, select an organization, and approve operation scopes. It then
verifies the MCP connection and stores the client-level Bearer token in Codex's MCP
configuration. No manual token creation, copying, or MCP setup command is needed.

Select a project for the current repository when prompted. The plugin saves only the
non-secret project identity in `.workilot/project.toml`. Other repositories using this
Codex installation reuse its client authorization and bind their own project.

### Offline installation

Download the versioned ZIP from the Workilot console, verify its SHA-256 checksum,
and extract it. In the extracted root, run:

```bash
codex plugin marketplace add .
codex plugin add workilot-mcp@workilot
```

Then connect Workilot from a repository as described above.

### Updates and troubleshooting

```bash
codex plugin marketplace upgrade workilot
codex plugin add workilot-mcp@workilot
```

If local plugin tools fail to start, check `python3 --version` (3.10+). For connection
errors, ask the plugin to diagnose the Workilot MCP connection. Never print the token
when diagnosing.

## 中文安装说明

Workilot 通过 MCP 连接 AI Agent，让 Bug、优化建议和项目任务进入自动化执行流程。
GitHub 仅分发插件；Workilot 服务仍由 GitArk 上的主项目维护。

在 Codex 中安装：

```bash
codex plugin marketplace add starsarc/workilot-plugins
codex plugin add workilot-mcp@workilot
```

打开一个仓库，在 Codex 中要求“连接 Workilot”。插件会打开浏览器，引导注册或登录、
选择组织并批准操作权限，然后自动验证 MCP 连接并将客户端级 Bearer Token 写入 Codex
的 MCP 配置。无需手动创建 Token、复制凭证或执行 MCP 配置命令。

按提示选择当前仓库绑定的项目。插件仅将项目 ID、key 和名称写入仓库的
`.workilot/project.toml`。这台 Codex 上的其他仓库可以复用客户端授权，并分别绑定项目。

更新插件：

```bash
codex plugin marketplace upgrade workilot
codex plugin add workilot-mcp@workilot
```

Python 3.10 或更高版本用于运行本地项目绑定工具。

## License

The plugin is distributed under the [MIT License](LICENSE).
