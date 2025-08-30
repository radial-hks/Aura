# Playwright MCP Bridge 浏览器扩展安装指南

## 概述

Playwright MCP Bridge 浏览器扩展允许您连接到现有的浏览器标签页，并利用已登录的会话和浏览器状态。这使得 AI 助手可以与您已经登录的网站进行交互，使用现有的 cookies、会话和浏览器状态，提供无缝体验，无需单独的身份验证或设置。

## 前置条件

- Chrome/Edge/Chromium 浏览器
- Node.js 18 或更新版本
- 已安装 `@playwright/mcp` 包

## 安装步骤

### 1. 下载扩展

从 GitHub 下载最新的 Chrome 扩展：

**下载链接**: https://github.com/microsoft/playwright-mcp/releases

1. 访问上述链接
2. 找到最新的 Release
3. 下载扩展文件（通常是 `.zip` 格式）
4. 解压下载的文件到本地目录

### 2. 加载 Chrome 扩展

1. 打开 Chrome 浏览器
2. 导航到 `chrome://extensions/`（对于 Edge 浏览器，使用 `edge://extensions/`）
3. 启用右上角的"开发者模式"（Developer mode）
4. 点击"加载已解压的扩展程序"（Load unpacked）
5. 选择解压后的扩展目录
6. 确认扩展已成功加载，您应该能在扩展列表中看到"Playwright MCP Bridge"

### 3. 配置 Playwright MCP 服务器

配置 Playwright MCP 服务器以使用扩展，通过在运行 MCP 服务器时传递 `--extension` 选项：

#### 标准配置

```json
{
  "mcpServers": {
    "playwright-extension": {
      "command": "npx",
      "args": [
        "@playwright/mcp@latest",
        "--extension"
      ]
    }
  }
}
```

#### Aura 项目配置

在 Aura 项目中，您可以通过 `MCPConfig` 类配置扩展模式：

```python
# 在 src/config/mcp_config.py 中
from src.config.mcp_config import MCPConfig
from src.core.mcp_manager import MCPManager

# 加载配置
config = MCPConfig()

# 启用 Playwright 扩展服务器
config.enable_server("playwright_extension")

# 创建 MCP 管理器
mcp_manager = MCPManager(config)

# 初始化并启用浏览器扩展模式
await mcp_manager.initialize()
await mcp_manager.enable_browser_extension_mode()
```

## 使用方法

### 浏览器标签页选择

当 LLM 首次与浏览器交互时，它会加载一个页面，您可以在其中选择 LLM 将连接到的浏览器标签页。这允许您控制 AI 助手在会话期间将与哪个特定页面进行交互。

### 基本使用流程

1. **启动浏览器并登录**：在您想要使用的配置文件中打开浏览器并登录到目标网站
2. **启动 MCP 服务器**：使用 `--extension` 标志启动 Playwright MCP 服务器
3. **选择标签页**：当 AI 助手请求浏览器访问时，选择要连接的标签页
4. **开始自动化**：AI 助手现在可以在已登录的会话中与网站进行交互

### 在 Aura 项目中使用

```python
from src.core.orchestrator import Orchestrator
from src.modules.site_explorer import SiteExplorer

# 创建 Orchestrator 实例
orchestrator = Orchestrator()

# 初始化 MCP
await orchestrator.initialize_mcp()

# 启用浏览器扩展模式
await orchestrator.enable_browser_extension_mode()

# 使用 SiteExplorer 进行扩展模式探索
site_explorer = SiteExplorer(mcp_manager=orchestrator.mcp_manager)
await site_explorer.enable_browser_extension_mode()

# 探索已登录的网站
site_model = await site_explorer.explore_with_extension(
    domain="example.com",
    target_tab_url="https://example.com/dashboard"
)
```

## 故障排除

### 常见问题

1. **扩展未显示连接状态**
   - 确保扩展已正确加载并启用
   - 检查浏览器控制台是否有错误信息
   - 重新启动浏览器并重新加载扩展

2. **MCP 服务器无法连接到浏览器**
   - 确认使用了 `--extension` 标志
   - 检查防火墙设置
   - 确保没有其他程序占用相关端口

3. **标签页选择页面未出现**
   - 刷新浏览器页面
   - 检查扩展权限设置
   - 尝试重新启动 MCP 服务器

### 调试步骤

1. **检查扩展状态**：
   ```bash
   # 在浏览器控制台中检查扩展状态
   chrome://extensions/
   ```

2. **验证 MCP 服务器配置**：
   ```bash
   npx @playwright/mcp@latest --extension --help
   ```

3. **查看连接日志**：
   ```python
   # 在 Aura 项目中启用调试日志
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

## 安全注意事项

- 扩展将访问您的浏览器标签页和会话信息
- 仅在受信任的环境中使用此功能
- 定期检查扩展权限和访问范围
- 在生产环境中使用时，考虑使用专用的浏览器配置文件

## 支持的功能

- ✅ 连接到现有浏览器标签页
- ✅ 利用已登录的会话状态
- ✅ 保持 cookies 和本地存储
- ✅ 支持 Chrome 和 Edge 浏览器
- ✅ 实时页面交互和自动化
- ✅ 截图和页面分析功能

## 更多资源

- [Playwright MCP 官方文档](https://github.com/microsoft/playwright-mcp)
- [MCP 协议规范](https://docs.agno.com/tools/mcp/mcp)
- [Aura 项目文档](../README.md)