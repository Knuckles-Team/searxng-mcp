# SearXNG - A2A | AG-UI | MCP

![PyPI - Version](https://img.shields.io/pypi/v/searxng-mcp)
![MCP Server](https://badge.mcpx.dev?type=server 'MCP Server')
![PyPI - Downloads](https://img.shields.io/pypi/dd/searxng-mcp)
![GitHub Repo stars](https://img.shields.io/github/stars/Knuckles-Team/searxng-mcp)
![GitHub forks](https://img.shields.io/github/forks/Knuckles-Team/searxng-mcp)
![GitHub contributors](https://img.shields.io/github/contributors/Knuckles-Team/searxng-mcp)
![PyPI - License](https://img.shields.io/pypi/l/searxng-mcp)
![GitHub](https://img.shields.io/github/license/Knuckles-Team/searxng-mcp)

![GitHub last commit (by committer)](https://img.shields.io/github/last-commit/Knuckles-Team/searxng-mcp)
![GitHub pull requests](https://img.shields.io/github/issues-pr/Knuckles-Team/searxng-mcp)
![GitHub closed pull requests](https://img.shields.io/github/issues-pr-closed/Knuckles-Team/searxng-mcp)
![GitHub issues](https://img.shields.io/github/issues/Knuckles-Team/searxng-mcp)

![GitHub top language](https://img.shields.io/github/languages/top/Knuckles-Team/searxng-mcp)
![GitHub language count](https://img.shields.io/github/languages/count/Knuckles-Team/searxng-mcp)
![GitHub repo size](https://img.shields.io/github/repo-size/Knuckles-Team/searxng-mcp)
![GitHub repo file count (file type)](https://img.shields.io/github/directory-file-count/Knuckles-Team/searxng-mcp)
![PyPI - Wheel](https://img.shields.io/pypi/wheel/searxng-mcp)
![PyPI - Implementation](https://img.shields.io/pypi/implementation/searxng-mcp)

*Version: 0.0.20*

## Overview

SearXNG MCP Server + A2A Server

It includes a Model Context Protocol (MCP) server and an out of the box Agent2Agent (A2A) agent

Perform privacy-respecting web searches using SearXNG through an MCP server!

This repository is actively maintained - Contributions are welcome!

### Supports:
- Privacy-respecting metasearch
- Customizable search parameters (language, time range, categories, engines)
- Safe search levels
- Pagination control
- Basic authentication support
- Random instance selection

## MCP

### MCP Tools

| Function Name | Description                                                                                                                            | Tag(s)   |
|:--------------|:---------------------------------------------------------------------------------------------------------------------------------------|:---------|
| `web_search`  | Perform web searches using SearXNG, a privacy-respecting metasearch engine. Returns relevant web content with customizable parameters. | `search` |


### Using as an MCP Server

The MCP Server can be run in two modes: `stdio` (for local testing) or `http` (for networked access). To start the server, use the following commands:

#### Run in stdio mode (default):
```bash
searxng-mcp --transport "stdio"
```

#### Run in HTTP mode:
```bash
searxng-mcp --transport "http"  --host "0.0.0.0"  --port "8000"
```

AI Prompt:
```text
Search for information about artificial intelligence
```

AI Response:
```text
Search completed successfully. Found 10 results for "artificial intelligence":

1. **What is Artificial Intelligence?**
   URL: https://example.com/ai
   Content: Artificial intelligence (AI) refers to the simulation of human intelligence in machines...

2. **AI Overview**
   URL: https://example.org/ai-overview
   Content: AI encompasses machine learning, deep learning, and more...
```

## A2A Agent

This package also includes an A2A agent server that can be used to interact with the SearXNG MCP server.

### Architecture:

```mermaid
---
config:
  layout: dagre
---
flowchart TB
 subgraph subGraph0["Agent Capabilities"]
        C["Agent"]
        B["A2A Server - Uvicorn/FastAPI"]
        D["MCP Tools"]
        F["Agent Skills"]
  end
    C --> D & F
    A["User Query"] --> B
    B --> C
    D --> E["Platform API"]

     C:::agent
     B:::server
     A:::server
    classDef server fill:#f9f,stroke:#333
    classDef agent fill:#bbf,stroke:#333,stroke-width:2px
    style B stroke:#000000,fill:#FFD600
    style D stroke:#000000,fill:#BBDEFB
    style F fill:#BBDEFB
    style A fill:#C8E6C9
    style subGraph0 fill:#FFF9C4
```

### Component Interaction Diagram

```mermaid
sequenceDiagram
    participant User
    participant Server as A2A Server
    participant Agent as Agent
    participant Skill as Agent Skills
    participant MCP as MCP Tools

    User->>Server: Send Query
    Server->>Agent: Invoke Agent
    Agent->>Skill: Analyze Skills Available
    Skill->>Agent: Provide Guidance on Next Steps
    Agent->>MCP: Invoke Tool
    MCP-->>Agent: Tool Response Returned
    Agent-->>Agent: Return Results Summarized
    Agent-->>Server: Final Response
    Server-->>User: Output
```

## Usage

### MCP CLI

| Short Flag | Long Flag                          | Description                                                                 |
|------------|------------------------------------|-----------------------------------------------------------------------------|
| -h         | --help                             | Display help information                                                    |
| -t         | --transport                        | Transport method: 'stdio', 'http', or 'sse' [legacy] (default: stdio)       |
| -s         | --host                             | Host address for HTTP transport (default: 0.0.0.0)                          |
| -p         | --port                             | Port number for HTTP transport (default: 8000)                              |
|            | --auth-type                        | Authentication type: 'none', 'static', 'jwt', 'oauth-proxy', 'oidc-proxy', 'remote-oauth' (default: none) |
|            | --token-jwks-uri                   | JWKS URI for JWT verification                                              |
|            | --token-issuer                     | Issuer for JWT verification                                                |
|            | --token-audience                   | Audience for JWT verification                                              |
|            | --oauth-upstream-auth-endpoint     | Upstream authorization endpoint for OAuth Proxy                             |
|            | --oauth-upstream-token-endpoint    | Upstream token endpoint for OAuth Proxy                                    |
|            | --oauth-upstream-client-id         | Upstream client ID for OAuth Proxy                                         |
|            | --oauth-upstream-client-secret     | Upstream client secret for OAuth Proxy                                     |
|            | --oauth-base-url                   | Base URL for OAuth Proxy                                                   |
|            | --oidc-config-url                  | OIDC configuration URL                                                     |
|            | --oidc-client-id                   | OIDC client ID                                                             |
|            | --oidc-client-secret               | OIDC client secret                                                         |
|            | --oidc-base-url                    | Base URL for OIDC Proxy                                                    |
|            | --remote-auth-servers              | Comma-separated list of authorization servers for Remote OAuth             |
|            | --remote-base-url                  | Base URL for Remote OAuth                                                  |
|            | --allowed-client-redirect-uris     | Comma-separated list of allowed client redirect URIs                       |
|            | --eunomia-type                     | Eunomia authorization type: 'none', 'embedded', 'remote' (default: none)   |
|            | --eunomia-policy-file              | Policy file for embedded Eunomia (default: mcp_policies.json)              |
|            | --eunomia-remote-url               | URL for remote Eunomia server                                              |


### A2A CLI
#### Endpoints
- **Web UI**: `http://localhost:8000/` (if enabled)
- **A2A**: `http://localhost:8000/a2a` (Discovery: `/a2a/.well-known/agent.json`)
- **AG-UI**: `http://localhost:8000/ag-ui` (POST)

| Short Flag | Long Flag         | Description                                                            |
|------------|-------------------|------------------------------------------------------------------------|
| -h         | --help            | Display help information                                               |
|            | --host            | Host to bind the server to (default: 0.0.0.0)                          |
|            | --port            | Port to bind the server to (default: 9000)                             |
|            | --reload          | Enable auto-reload                                                     |
|            | --provider        | LLM Provider: 'openai', 'anthropic', 'google', 'huggingface'           |
|            | --model-id        | LLM Model ID (default: qwen/qwen3-4b-2507)                                  |
|            | --base-url        | LLM Base URL (for OpenAI compatible providers)                         |
|            | --api-key         | LLM API Key                                                            |
|            | --mcp-url         | MCP Server URL (default: http://localhost:8000/mcp)                    |
|            | --web             | Enable Pydantic AI Web UI                                              | False (Env: ENABLE_WEB_UI) |


### Using as an MCP Server
The MCP Server can be run in two modes: `stdio` (for local testing) or `http` (for networked access). To start the server, use the following commands:

#### Run in stdio mode (default):
```bash
searxng-mcp --transport "stdio"
```

#### Run in HTTP mode:
```bash
searxng-mcp --transport "http"  --host "0.0.0.0"  --port "8000"
```

AI Prompt:
```text
Search for information about artificial intelligence
```

AI Response:
```text
Search completed successfully. Found 10 results for "artificial intelligence":

1. **What is Artificial Intelligence?**
   URL: https://example.com/ai
   Content: Artificial intelligence (AI) refers to the simulation of human intelligence in machines...

2. **AI Overview**
   URL: https://example.org/ai-overview
   Content: AI encompasses machine learning, deep learning, and more...
```

### Agentic AI
`searxng-mcp` is designed to be used by Agentic AI systems. It provides a set of tools that allow agents to search the web using SearXNG.

## Agent-to-Agent (A2A)

This package also includes an A2A agent server that can be used to interact with the SearXNG MCP server.

### CLI

| Argument          | Description                                                    | Default                        |
|-------------------|----------------------------------------------------------------|--------------------------------|
| `--host`          | Host to bind the server to                                     | `0.0.0.0`                      |
| `--port`          | Port to bind the server to                                     | `9000`                         |
| `--reload`        | Enable auto-reload                                             | `False`                        |
| `--provider`      | LLM Provider (openai, anthropic, google, huggingface)          | `openai`                       |
| `--model-id`      | LLM Model ID                                                   | `qwen/qwen3-4b-2507`                |
| `--base-url`      | LLM Base URL (for OpenAI compatible providers)                 | `http://ollama.arpa/v1`        |
| `--api-key`       | LLM API Key                                                    | `ollama`                       |
| `--mcp-url`       | MCP Server URL                                                 | `http://searxng-mcp:8000/mcp`  |
| `--allowed-tools` | List of allowed MCP tools                                      | `web_search`                   |

### Examples

#### Run A2A Server
```bash
searxng-agent --provider openai --model-id gpt-4 --api-key sk-... --mcp-url http://localhost:8000/mcp
```

#### Run with Docker
```bash
docker run -e CMD=searxng-agent -p 8000:8000 searxng-mcp
```

## Docker

### Build

```bash
docker build -t searxng-mcp .
```

### Run MCP Server

```bash
docker run -p 8000:8000 searxng-mcp
```

### Run A2A Server

```bash
docker run -e CMD=searxng-agent -p 8001:8001 searxng-mcp
```

### Deploy MCP Server as a Service

The ServiceNow MCP server can be deployed using Docker, with configurable authentication, middleware, and Eunomia authorization.

#### Using Docker Run

```bash
docker pull knucklessg1/searxng-mcp:latest

docker run -d \
  --name searxng-mcp \
  -p 8004:8004 \
  -e HOST=0.0.0.0 \
  -e PORT=8004 \
  -e TRANSPORT=http \
  -e AUTH_TYPE=none \
  -e EUNOMIA_TYPE=none \
  -e SEARXNG_URL=https://searxng.example.com \
  -e SEARXNG_USERNAME=user \
  -e SEARXNG_PASSWORD=pass \
  -e USE_RANDOM_INSTANCE=false \
  knucklessg1/searxng-mcp:latest
```

For advanced authentication (e.g., JWT, OAuth Proxy, OIDC Proxy, Remote OAuth) or Eunomia, add the relevant environment variables:

```bash
docker run -d \
  --name searxng-mcp \
  -p 8004:8004 \
  -e HOST=0.0.0.0 \
  -e PORT=8004 \
  -e TRANSPORT=http \
  -e AUTH_TYPE=oidc-proxy \
  -e OIDC_CONFIG_URL=https://provider.com/.well-known/openid-configuration \
  -e OIDC_CLIENT_ID=your-client-id \
  -e OIDC_CLIENT_SECRET=your-client-secret \
  -e OIDC_BASE_URL=https://your-server.com \
  -e ALLOWED_CLIENT_REDIRECT_URIS=http://localhost:*,https://*.example.com/* \
  -e EUNOMIA_TYPE=embedded \
  -e EUNOMIA_POLICY_FILE=/app/mcp_policies.json \
  -e SEARXNG_URL=https://searxng.example.com \
  -e SEARXNG_USERNAME=user \
  -e SEARXNG_PASSWORD=pass \
  -e USE_RANDOM_INSTANCE=false \
  knucklessg1/searxng-mcp:latest
```

#### Using Docker Compose

Create a `docker-compose.yml` file:

```yaml
services:
  searxng-mcp:
    image: knucklessg1/searxng-mcp:latest
    environment:
      - HOST=0.0.0.0
      - PORT=8004
      - TRANSPORT=http
      - AUTH_TYPE=none
      - EUNOMIA_TYPE=none
      - SEARXNG_URL=https://searxng.example.com
      - SEARXNG_USERNAME=user
      - SEARXNG_PASSWORD=pass
      - USE_RANDOM_INSTANCE=false
    ports:
      - 8004:8004
```

For advanced setups with authentication and Eunomia:

```yaml
services:
  searxng-mcp:
    image: knucklessg1/searxng-mcp:latest
    environment:
      - HOST=0.0.0.0
      - PORT=8004
      - TRANSPORT=http
      - AUTH_TYPE=oidc-proxy
      - OIDC_CONFIG_URL=https://provider.com/.well-known/openid-configuration
      - OIDC_CLIENT_ID=your-client-id
      - OIDC_CLIENT_SECRET=your-client-secret
      - OIDC_BASE_URL=https://your-server.com
      - ALLOWED_CLIENT_REDIRECT_URIS=http://localhost:*,https://*.example.com/*
      - EUNOMIA_TYPE=embedded
      - EUNOMIA_POLICY_FILE=/app/mcp_policies.json
      - SEARXNG_URL=https://searxng.example.com
      - SEARXNG_USERNAME=user
      - SEARXNG_PASSWORD=pass
      - USE_RANDOM_INSTANCE=false
    ports:
      - 8004:8004
    volumes:
      - ./mcp_policies.json:/app/mcp_policies.json
```

Run the service:

```bash
docker-compose up -d
```

#### Configure `mcp.json` for AI Integration

```json
{
  "mcpServers": {
    "searxng": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "searxng-mcp",
        "searxng-mcp"
      ],
      "env": {
        "SEARXNG_URL": "https://searxng.example.com",
        "SEARXNG_USERNAME": "user",
        "SEARXNG_PASSWORD": "pass",
        "USE_RANDOM_INSTANCE": "false"
      },
      "timeout": 300000
    }
  }
}
```

## Install Python Package

```bash
python -m pip install searxng-mcp
```
```bash
uv pip install searxng-mcp
```

## Repository Owners

<img width="100%" height="180em" src="https://github-readme-stats.vercel.app/api?username=Knucklessg1&show_icons=true&hide_border=true&&count_private=true&include_all_commits=true" />

![GitHub followers](https://img.shields.io/github/followers/Knucklessg1)
![GitHub User's stars](https://img.shields.io/github/stars/Knucklessg1)
