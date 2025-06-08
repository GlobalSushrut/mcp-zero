from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="mcp_zero",
    version="0.1.0",
    author="MCP-ZERO Team",
    author_email="team@mcp-zero.io",
    description="SDK for MCP-ZERO AI Agent Infrastructure",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mcp-zero/sdk",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
    install_requires=[
        "grpcio>=1.46.0,<2.0.0",
        "protobuf>=3.19.0,<4.0.0",
        "pyyaml>=6.0,<7.0",
        "click>=8.0.0,<9.0.0",
        "rich>=12.0.0,<13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "mcp-zero=mcp_zero.cli:main",
        ],
    },
)
