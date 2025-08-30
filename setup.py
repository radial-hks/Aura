#!/usr/bin/env python3
"""
Aura智能浏览器自动化系统 - 安装配置文件
"""

from setuptools import setup, find_packages
import os

# 读取README文件
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# 读取requirements文件
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

# 版本信息
VERSION = "1.0.0"

setup(
    name="aura-browser-automation",
    version=VERSION,
    author="Aura Team",
    author_email="team@aura-ai.com",
    description="智能浏览器自动化系统 - 通过自然语言指令操作浏览器",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/aura-ai/aura",
    project_urls={
        "Bug Tracker": "https://github.com/aura-ai/aura/issues",
        "Documentation": "https://docs.aura-ai.com",
        "Source Code": "https://github.com/aura-ai/aura",
    },
    packages=find_packages(include=["src", "src.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
            "black>=23.11.0",
            "isort>=5.12.0",
            "flake8>=6.1.0",
            "mypy>=1.7.1",
            "pre-commit>=3.6.0",
        ],
        "docs": [
            "mkdocs>=1.5.3",
            "mkdocs-material>=9.4.8",
            "mkdocstrings[python]>=0.24.0",
        ],
        "cloud": [
            "boto3>=1.34.0",
            "azure-storage-blob>=12.19.0",
            "google-cloud-storage>=2.10.0",
        ],
        "monitoring": [
            "prometheus-client>=0.19.0",
            "jaeger-client>=4.8.0",
            "sentry-sdk[fastapi]>=1.38.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "aura=main:main",
            "aura-cli=src.cli.interface:main",
            "aura-dev=scripts.dev:main",
            "aura-deploy=scripts.deploy:main",
        ],
    },
    include_package_data=True,
    package_data={
        "src": [
            "config/*.yaml",
            "config/*.json",
            "templates/*.html",
            "static/*",
        ],
    },
    zip_safe=False,
    keywords=[
        "browser automation",
        "web scraping",
        "artificial intelligence",
        "natural language processing",
        "playwright",
        "selenium",
        "rpa",
        "automation",
        "ai assistant",
    ],
)