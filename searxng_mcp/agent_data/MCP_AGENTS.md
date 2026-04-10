# MCP_AGENTS.md - Dynamic Agent Registry

This file tracks the generated agents from MCP servers. You can manually modify the 'Tools' list to customize agent expertise.

## Agent Mapping Table

| Name | Description | System Prompt | Tools | Tag | Source MCP |
|------|-------------|---------------|-------|-----|------------|
| Searxng Search Specialist | Expert specialist for search domain tasks. | You are a Searxng Search specialist. Help users manage and interact with Search functionality using the available tools. | searxng-mcp_search_toolset | search | searxng-mcp |
| Searxng Misc Specialist | Expert specialist for misc domain tasks. | You are a Searxng Misc specialist. Help users manage and interact with Misc functionality using the available tools. | searxng-mcp_misc_toolset | misc | searxng-mcp |

## Tool Inventory Table

| Tool Name | Description | Tag | Source |
|-----------|-------------|-----|--------|
| searxng-mcp_search_toolset | Static hint toolset for search based on config env. | search | searxng-mcp |
| searxng-mcp_misc_toolset | Static hint toolset for misc based on config env. | misc | searxng-mcp |
