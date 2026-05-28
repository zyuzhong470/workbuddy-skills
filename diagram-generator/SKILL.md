---
name: diagram-generator
description: Generate Draw.io architecture diagrams, Mermaid diagrams, and Excalidraw sketches from structured specifications using the mcp-diagram-generator MCP server.
---

# Diagram Generator

Generate Draw.io architecture diagrams, Mermaid flowcharts/sequence/class/ER diagrams, and Excalidraw whiteboard sketches from structured JSON specifications using the `mcp-diagram-generator` MCP server.

---

## MCP Server Setup

Add one of the following configurations to your system settings (e.g., `mcp_config.json` or IDE configurations):

### Option A: Using NPM Remote Package (Recommended)
```json
{
  "mcpServers": {
    "diagram-generator": {
      "command": "npx",
      "args": ["-y", "mcp-diagram-generator"]
    }
  }
}
```

### Option B: Using Local Path
```json
{
  "mcpServers": {
    "diagram-generator": {
      "command": "node",
      "args": ["/your/path/to/mcp-diagram-generator/dist/index.js"]
    }
  }
}
```

---

## Core Workflow

1. **Select Format**: Choose the best target format among `drawio`, `mermaid`, and `excalidraw` based on your needs.
2. **Define Layout**: Specify `geometry` coordinates for precise placement (Note: coordinates for child elements inside containers must be relative to the top-left of their direct parent container). For automatic layout, set coordinates to `0` or omit them to trigger the generator's grid layout.
3. **Generate**: Call `generate_diagram` to render and save the file.

---

## Reference Guide (Read on-demand 🌟)

To ensure rendering quality, **you must read the following guides on-demand using `view_file`** before generating diagrams:

* 📘 **Format Selection Matrix** ➡️ [format-selection-guide.md](references/format-selection-guide.md)
  * Helps decide when to use Draw.io, Mermaid, or Excalidraw.
* 📘 **JSON Protocol & Schema Guide** ➡️ [json-schema-guide.md](references/json-schema-guide.md)
  * Contains the complete JSON schema and parameter templates for Mermaid flowcharts and sequence diagrams.
* 📘 **Network Topology & Auto-Layout Specs** ➡️ [topology-and-layout-spec.md](references/topology-and-layout-spec.md)
  * **For Network Diagrams**: Contains the 4-level nesting hierarchy (Environment ➡️ Datacenter ➡️ Zone ➡️ Device) and device color definitions.
  * **For Grid Layouts**: Contains Agent-specific mathematical layout formulas.
* 📘 **Network Topology Templates** ➡️ [network-topology-examples.md](references/network-topology-examples.md)
  * Provides complete JSON templates for nested network topologies.
* 📘 **Troubleshooting & Setup** ➡️ [setup-and-troubleshooting.md](references/setup-and-troubleshooting.md)
  * Read this file to troubleshoot errors such as `Schema Validation Error`, `Directory Not Found`, or `Wrong File Extension`.

---

## Best Practices

1. **Use Configuration Management**: Initialize paths with `init_config()` so you do not need to specify `output_path` in `generate_diagram`.
2. **Follow Naming & ID Standards**: Use descriptive prefixes (e.g., `env-`, `dc-`, `router-`) and ensure all element IDs are unique.
3. **Bind Edges to Parent Container**: For Draw.io diagrams, set the parent of an Edge to the shared Container ID when both source and target are inside that container, ensuring links move together with the container.
