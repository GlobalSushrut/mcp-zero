#!/usr/bin/env python3
"""
MCP-ZERO SDK
-----------
Python SDK for interacting with the MCP-ZERO AI agent infrastructure.
Designed for minimal resource usage and 100+ year sustainability.
"""

import os
from setuptools import setup, find_packages

# Load README as long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Load version from version.py
about = {}
with open(os.path.join("mcp_zero", "version.py"), "r", encoding="utf-8") as f:
    exec(f.read(), about)

setup(
    name="mcp-zero",
    version=about["__version__"],
    author="MCP-ZERO Team",
    author_email="support@mcp-zero.org",
    description="Minimal Computing Protocol - ZERO for sustainable AI agents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mcp-zero/sdk",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.0,<3.0.0",
        "cryptography>=3.4.0,<4.0.0",
        "pyyaml>=5.4.0,<6.0.0",
        "wasmtime>=0.35.0,<1.0.0",  # For plugin sandboxing
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "black>=21.5b2",
            "isort>=5.9.1",
            "mypy>=0.812",
        ],
        "monitoring": [
            "psutil>=5.8.0",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    keywords="ai, agents, mcp, protocol, minimal computing",
    project_urls={
        "Documentation": "https://docs.mcp-zero.org",
        "Bug Reports": "https://github.com/mcp-zero/sdk/issues",
        "Source": "https://github.com/mcp-zero/sdk",
    },
)
