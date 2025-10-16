# SearXNG MCP Server

![PyPI - Version](https://img.shields.io/pypi/v/searxng-mcp)
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

*Version: 0.0.2*

Perform privacy-respecting web searches using SearXNG through an MCP server!

This repository is actively maintained - Contributions are welcome!

### Supports:
- Privacy-respecting metasearch
- Customizable search parameters (language, time range, categories, engines)
- Safe search levels
- Pagination control
- Basic authentication support
- Random instance selection

<details>
  <summary><b>Usage:</b></summary>

### CLI
| Short Flag | Long Flag   | Description                                 |
|------------|-------------|---------------------------------------------|
| -h         | --help      | See usage                                   |
| -t         | --transport | Transport method: 'stdio', 'http', or 'sse' (default: stdio) |
| -s         | --host      | Host address for HTTP transport (default: 0.0.0.0) |
| -p         | --port      | Port number for HTTP transport (default: 8000) |

### Using as an MCP Server:

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

</details>

<details>
  <summary><b>Example:</b></summary>

### Use in CLI

```bash
searxng-mcp --transport http --host 0.0.0.0 --port 8000
```


### Use with AI

Deploy MCP Server as a Service
```bash
docker pull knucklessg1/searxng-mcp:latest
```

Modify the `compose.yml`

```yaml
services:
  searxng-mcp:
    image: knucklessg1/searxng-mcp:latest
    environment:
      - SEARXNG_URL=https://searxng.example.com
      - SEARXNG_USERNAME=user
      - SEARXNG_PASSWORD=pass
      - USE_RANDOM_INSTANCE=false
      - HOST=0.0.0.0
      - PORT=8000
    ports:
      - 8000:8000
```

Configure `mcp.json`

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

Run as a docker container:

```yaml
services:
  searxng-mcp:
    image: docker.io/knucklessg1/searxng-mcp:latest
    ports:
      - "8000:8000"
    environment:
      - HOST=0.0.0.0
      - PORT=8000
      - TRANSPORT=http
      - SEARXNG_URL=https://searxng.example.com
      - SEARXNG_USERNAME=user
      - SEARXNG_PASSWORD=pass
      - USE_RANDOM_INSTANCE=false
```

</details>

<details>
  <summary><b>Installation Instructions:</b></summary>

Install Python Package

```bash
python -m pip install searxng-mcp
```
```bash
uv pip install searxng-mcp
```

</details>

<details>
  <summary><b>Repository Owners:</b></summary>

<img width="100%" height="180em" src="https://github-readme-stats.vercel.app/api?username=Knucklessg1&show_icons=true&hide_border=true&&count_private=true&include_all_commits=true" />

![GitHub followers](https://img.shields.io/github/followers/Knucklessg1)
![GitHub User's stars](https://img.shields.io/github/stars/Knucklessg1)
</details>