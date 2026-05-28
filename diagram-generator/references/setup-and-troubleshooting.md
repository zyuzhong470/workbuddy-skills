# MCP Server Setup & Troubleshooting

This document guide you through setup, configuration, and troubleshooting for the `mcp-diagram-generator` MCP server.

---

## MCP Server Invocation Options

When invoking the `generate_diagram` tool, you can customize how and where the output files are saved using the `output_path` and `filename` parameters:

### Option A: Use defaults (Recommended)
Leave both `output_path` and `filename` empty. The server will automatically determine the directory based on the selected format and generate a timestamped filename based on the diagram's title (e.g., if the `title` is `Production Environment`, it will generate `Production-Environment-2026-05-24.drawio` inside `diagrams/drawio/`).
```json
{
  "diagram_spec": { ... }
}
```

### Option B: Specify custom path
Provide a fully custom relative or absolute path in the `output_path` parameter to save the diagram exactly where you need it:
```json
{
  "diagram_spec": { ... },
  "output_path": "custom/path/to/diagram.drawio"
}
```

### Option C: Provide filename only
Provide a `filename` without a directory path. The server will save the file to the default folder for that format (e.g., `diagrams/drawio/my-diagram.drawio`):
```json
{
  "diagram_spec": { ... },
  "filename": "my-diagram.drawio"
}
```

---

## Editing Existing Diagrams

To modify or update an existing diagram:
1. **Read the existing file** to understand its current layout and structure.
2. **Parse** the diagram (e.g., inspect the XML for Draw.io or JSON/Markdown codeblocks).
3. **Modify** the JSON specification based on the user's change request.
4. **Generate** the new diagram using the modified JSON (overwriting the existing file or creating a new version as requested).

---

## Troubleshooting & Error Handling

### 1. Invalid JSON Schema
If the MCP server returns a schema validation error:
* Check [json-schema-guide.md](json-schema-guide.md) to ensure correct fields.
* Verify all required fields (e.g., `id`, `type`, `name`, `source`, `target`) are present.
* Ensure all elements have unique `id` values.
* Check container hierarchy parent-child references.

### 2. Directory Not Found
* **Behavior**: The server automatically creates target directories if they do not exist.
* **Troubleshooting**: If you still encounter folder access errors:
  1. Verify write permissions for the project workspace directory.
  2. Query config state with `get_config()` to check actual mapped paths.
  3. Reinitialize the default structure using `init_config()`.

### 3. Wrong File Extension
The server automatically appends the correct extension based on the selected format:
* `drawio` ➡️ `.drawio`
* `mermaid` ➡️ `.md` (Markdown embedded code block)
* `excalidraw` ➡️ `.excalidraw`
* **Note**: You do not need to specify the extension in the `filename` parameter; the server handles it automatically.

### 4. Nested Container Issues (Network Topology)
* Verify that the `level` field matches the structural hierarchy (`environment` ➡️ `datacenter` ➡️ `zone`).
* Check that child elements have their `parent` container IDs set correctly.
* Ensure that geometry coordinates of child elements are specified relative to their parent container.
