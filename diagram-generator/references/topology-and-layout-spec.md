# Network Topology & Auto-Layout Specifications

This document defines visual standards for network topologies and provides mathematical auto-layout guidelines for Agent automatic generation.

---

## Network Topology Specifications

Network topology diagrams require a strict 4-level hierarchical structure when generated in `drawio` format:

```text
Environment (level="environment")
  └── Datacenter (level="datacenter")
        └── Zone (level="zone")
              └── Device (type="node")
```

### Style Conventions

* **Environment Container**: 
  * `fillColor`: `#e1d5e7`, `strokeColor`: `#9673a6` (purple style)
  * Default font size: `14` (Bold)
* **Datacenter Container**: 
  * `fillColor`: `#d5e8d4`, `strokeColor`: `#82b366` (green style)
  * Default font size: `12` (Bold)
* **Zone Container**: 
  * `fillColor`: `#fff2cc`, `strokeColor`: `#d6b656` (yellow style)
  * Default font size: `10` (Bold)
* **Device Nodes**: Colors are based on device classifications.

### Device Types & Styles

| deviceType | strokeColor | fillColor | strokeWidth | Description |
| :--- | :--- | :--- | :--- | :--- |
| **router** | `#607D8B` (blue-gray) | `none` | `2` | Router devices |
| **switch** | `#4CAF50` (green) | `none` | `2` | Switch devices |
| **firewall**| `#F44336` (red) | `none` | `2` | Security Firewall |
| **server**  | `#2196F3` (blue) | `none` | `2` | Backend servers |
| **pc**      | `#607D8B` (gray) | `none` | `2` | User PC clients |
| **database**| `#9C27B0` (purple) | `none` | `2` | Databases |
| **cloud**   | `#9E9E9E` (gray) | `none` | `2` | External cloud services |

---

## Auto-Layout & Coordinate Math Guide (Agent Guide)

When generating diagrams in **Draw.io** or **Excalidraw** formats, providing clean coordinates in `geometry` prevents node overlap. Use the following formulas to programmatically compute offsets:

### A. Horizontal Grid Flow
For sequential/parallel nodes, compute the $X$-axis dynamically while keeping $Y$ fixed:
$$X_i = X_{start} + i \times (Width_{node} + Gap_{horizontal})$$
* **Recommended Specs**:
  * Node Size ($Width \times Height$): `120` x `60`
  * Horizontal Gap ($Gap_{horizontal}$): `80` (use `120` for network topologies to leave edge space).

### B. Matrix Grid Layout
For matrix arrangements, place nodes in an $R$ row by $C$ column grid:
$$X_{col} = X_{start} + col \times (Width_{node} + Gap_{x})$$
$$Y_{row} = Y_{start} + row \times (Height_{node} + Gap_{y})$$
* For the $n$-th element (0-indexed):
  * $row = \lfloor n / C \rfloor$
  * $col = n \bmod C$

### C. Relative Coordinates in Nested Containers
* **Constraint**: Child elements inside any Container **must use coordinates relative to the top-left corner of their parent container**, not the absolute board space.
* **Layout Constraints**:
  * Ensure the parent container size is large enough: $Width_{parent} \ge Max(X_{child} + Width_{child}) + Padding_{right}$.
  * Leave `50` pixels at the top of the parent container for the title bar; child elements' relative $Y$-start should be $\ge 50$.
  * Default container padding ($Padding$): `20` pixels.
