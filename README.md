# Aura - 智能浏览器自动化系统

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](#)
[![Coverage](https://img.shields.io/badge/coverage-85%25-yellow.svg)](#)

> 🚀 基于多MCP服务器协作的智能浏览器自动化系统，通过自然语言指令实现复杂的网页操作任务

## ✨ 核心特性

- 🧠 **智能任务理解**: 基于大语言模型的自然语言指令解析
- 🔗 **多MCP协作**: 支持多个MCP服务器协同工作，扩展系统能力
- 🎯 **精准操作**: 结合计算机视觉和DOM分析的元素定位
- 🛡️ **安全可靠**: 内置风险评估和策略控制机制
- 📊 **全程监控**: 完整的执行过程记录和回放功能
- 🔄 **自我进化**: 基于执行结果的技能库自动优化

## 🚀 快速开始

### 环境要求

- Python 3.9+
- Node.js 16+ (用于Playwright)
- 8GB+ RAM
- 支持的操作系统: Windows, macOS, Linux

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/aura-ai/aura.git
cd aura

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 安装浏览器
playwright install chromium

# 5. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入必要的配置

# 6. 启动系统
python main.py
```

### 基本使用

```python
from src.core.orchestrator import Orchestrator

# 创建orchestrator实例
orchestrator = Orchestrator()

# 执行任务
result = await orchestrator.execute_task(
    instruction="打开百度，搜索'人工智能'，点击第一个结果",
    context={"target_url": "https://www.baidu.com"}
)

print(f"任务状态: {result.status}")
print(f"执行结果: {result.message}")
```

## 📚 文档导航

### 🏗️ 架构设计
- [系统概览](docs/system-overview.md) - 项目愿景、架构图和核心组件
- [架构决策记录](docs/architecture-decisions.md) - 关键技术决策和设计原则
- [技术规范](docs/technical-specifications.md) - 详细的技术实现规范

### 🔧 开发指南
- [开发指南](docs/development-guide.md) - 环境搭建、开发流程和最佳实践
- [API参考](docs/api-reference.md) - 完整的API接口文档
- [测试指南](docs/testing-guide.md) - 测试策略、工具和示例

### 🚀 部署运维
- [部署指南](docs/deployment-guide.md) - 开发、测试、生产环境部署
- [监控运维](docs/deployment-guide.md#监控和日志) - 系统监控和故障排查

### 📖 其他文档
- [Playwright MCP扩展设置](docs/playwright_mcp_extension_setup.md) - MCP服务器配置

## 🏗️ 项目结构

```
aura/
├── src/                    # 核心源代码
│   ├── core/              # 核心模块
│   │   ├── orchestrator.py    # 任务编排器
│   │   ├── action_graph.py    # 动作图引擎
│   │   ├── mcp_manager.py     # MCP服务器管理
│   │   └── policy_engine.py   # 策略引擎
│   ├── modules/           # 功能模块
│   │   ├── skill_library.py   # 技能库
│   │   ├── site_explorer.py   # 站点探索
│   │   └── command_parser.py  # 指令解析
│   ├── api/               # API接口
│   ├── cli/               # 命令行界面
│   └── utils/             # 工具函数
├── docs/                   # 项目文档
├── tests/                  # 测试代码
├── config/                 # 配置文件
├── examples/               # 示例代码
├── scripts/                # 部署脚本
└── tools/                  # 开发工具
```

## 🤝 参与贡献

我们欢迎所有形式的贡献！请查看 [开发指南](docs/development-guide.md#贡献指南) 了解详细信息。

### 贡献流程

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [Playwright](https://playwright.dev/) - 现代化的浏览器自动化框架
- [MCP Protocol](https://modelcontextprotocol.io/) - 模型上下文协议
- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的Python Web框架

## 📞 联系我们

- 项目主页: [https://github.com/aura-ai/aura](https://github.com/aura-ai/aura)
- 问题反馈: [Issues](https://github.com/aura-ai/aura/issues)
- 讨论交流: [Discussions](https://github.com/aura-ai/aura/discussions)

---

<div align="center">
  <sub>Built with ❤️ by the Aura Team</sub>
</div>