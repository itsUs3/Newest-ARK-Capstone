"""GNN-style floor plan generation from boundary and centroid constraints.

This module replaces the earlier CSP room-order generator with a workflow inspired by
`Floor_Plan_Generation_using_GNNs`:
1) user boundary + front door + room centroids
2) graph construction
3) message-passing based width/height estimation
4) rendered layout image
"""

import base64
import io
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import matplotlib
import numpy as np
from matplotlib.patches import Rectangle

matplotlib.use("Agg")
import matplotlib.pyplot as plt


@dataclass
class FloorNode:
    node_id: int
    room_type: str
    centroid: Tuple[float, float]


class FloorplanGenerator:
    ROOM_EMBEDDINGS = {
        "living": 0,
        "room": 1,
        "kitchen": 2,
        "bathroom": 3,
    }

    TYPE_PRIORS = {
        "living": (9.0, 7.5),
        "room": (7.0, 6.0),
        "kitchen": (5.0, 4.5),
        "bathroom": (3.8, 3.0),
    }

    TYPE_COLORS = {
        "living": "#8B5CF6",
        "room": "#3B82F6",
        "kitchen": "#14B8A6",
        "bathroom": "#F59E0B",
    }

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.w1 = self.rng.normal(0, 0.15, (7, 16))
        self.w2 = self.rng.normal(0, 0.15, (16, 8))
        self.out = self.rng.normal(0, 0.10, (8, 2))

    def _parse_wkt_polygon(self, wkt: str) -> List[Tuple[float, float]]:
        if not wkt or "POLYGON" not in wkt.upper():
            raise ValueError("boundary_wkt/front_door_wkt must be POLYGON WKT")

        coords = re.findall(r"(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)", wkt)
        if len(coords) < 4:
            raise ValueError("Invalid WKT polygon: expected at least 4 points")

        points = [(float(x), float(y)) for x, y in coords]
        if points[0] != points[-1]:
            points.append(points[0])
        return points

    def _safe_centroids(self, centroids: List[List[float]], room_type: str, start_id: int) -> List[FloorNode]:
        nodes: List[FloorNode] = []
        for i, c in enumerate(centroids or []):
            if not isinstance(c, list) or len(c) != 2:
                continue
            try:
                x = float(c[0])
                y = float(c[1])
            except Exception:
                continue
            nodes.append(FloorNode(node_id=start_id + i, room_type=room_type, centroid=(x, y)))
        return nodes

    def _build_graph(self, nodes: List[FloorNode]) -> List[Tuple[int, int]]:
        if not nodes:
            return []

        edges = set()
        living_ids = [n.node_id for n in nodes if n.room_type == "living"]
        if living_ids:
            living = living_ids[0]
            for n in nodes:
                if n.node_id != living:
                    edges.add((living, n.node_id))
                    edges.add((n.node_id, living))

        for i in range(len(nodes)):
            dists = []
            xi, yi = nodes[i].centroid
            for j in range(len(nodes)):
                if i == j:
                    continue
                xj, yj = nodes[j].centroid
                d = (xi - xj) ** 2 + (yi - yj) ** 2
                dists.append((d, nodes[j].node_id))
            dists.sort(key=lambda x: x[0])
            for _, nbr in dists[:2]:
                edges.add((nodes[i].node_id, nbr))
                edges.add((nbr, nodes[i].node_id))

        return sorted(edges)

    def _normalize_centroids(self, nodes: List[FloorNode]) -> Dict[int, Tuple[float, float]]:
        xs = [n.centroid[0] for n in nodes]
        ys = [n.centroid[1] for n in nodes]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        dx = max(1e-6, max_x - min_x)
        dy = max(1e-6, max_y - min_y)

        out = {}
        for n in nodes:
            nx = (n.centroid[0] - min_x) / dx
            ny = (n.centroid[1] - min_y) / dy
            out[n.node_id] = (nx, ny)
        return out

    def _build_features(self, nodes: List[FloorNode], edges: List[Tuple[int, int]]) -> np.ndarray:
        node_index = {n.node_id: i for i, n in enumerate(nodes)}
        deg = np.zeros(len(nodes), dtype=float)
        for s, _ in edges:
            if s in node_index:
                deg[node_index[s]] += 1.0

        if len(deg) > 0 and deg.max() > 0:
            deg = deg / deg.max()

        norm_centroids = self._normalize_centroids(nodes)
        x = np.zeros((len(nodes), 7), dtype=float)
        for i, n in enumerate(nodes):
            type_idx = self.ROOM_EMBEDDINGS.get(n.room_type, 1)
            x[i, type_idx] = 1.0
            cx, cy = norm_centroids[n.node_id]
            x[i, 4] = cx
            x[i, 5] = cy
            x[i, 6] = deg[i]
        return x

    def _adjacency(self, nodes: List[FloorNode], edges: List[Tuple[int, int]]) -> np.ndarray:
        n = len(nodes)
        index = {node.node_id: i for i, node in enumerate(nodes)}
        a = np.eye(n, dtype=float)
        for s, t in edges:
            if s in index and t in index:
                a[index[s], index[t]] = 1.0

        d = a.sum(axis=1)
        d_inv = np.diag(1.0 / np.maximum(d, 1e-6))
        return d_inv @ a

    def _message_pass_predict(self, nodes: List[FloorNode], edges: List[Tuple[int, int]]) -> np.ndarray:
        x = self._build_features(nodes, edges)
        a = self._adjacency(nodes, edges)

        h1 = np.maximum(0.0, (a @ x) @ self.w1)
        h2 = np.maximum(0.0, (a @ h1) @ self.w2)
        raw = np.maximum(0.05, h2 @ self.out)

        wh = np.zeros((len(nodes), 2), dtype=float)
        for i, n in enumerate(nodes):
            pw, ph = self.TYPE_PRIORS.get(n.room_type, (6.0, 5.0))
            scale = 0.70 + float(np.clip(raw[i].mean(), 0.1, 1.0))
            wh[i, 0] = pw * scale
            wh[i, 1] = ph * scale
        return wh

    def _door_centroid(self, door_poly: List[Tuple[float, float]]) -> Tuple[float, float]:
        xs = [p[0] for p in door_poly[:-1]]
        ys = [p[1] for p in door_poly[:-1]]
        return (sum(xs) / max(1, len(xs)), sum(ys) / max(1, len(ys)))

    def _render_layout(
        self,
        boundary: List[Tuple[float, float]],
        door: List[Tuple[float, float]],
        nodes: List[FloorNode],
        edges: List[Tuple[int, int]],
        wh: np.ndarray,
    ) -> str:
        fig, ax = plt.subplots(figsize=(7, 7), dpi=140)

        bx = [p[0] for p in boundary]
        by = [p[1] for p in boundary]
        ax.plot(bx, by, color="#0f172a", linewidth=2.2)
        ax.fill(bx, by, color="#e2e8f0", alpha=0.08)

        dx = [p[0] for p in door]
        dy = [p[1] for p in door]
        ax.plot(dx, dy, color="#ef4444", linewidth=3)

        id_to_node = {n.node_id: n for n in nodes}
        for s, t in edges:
            if s not in id_to_node or t not in id_to_node:
                continue
            x1, y1 = id_to_node[s].centroid
            x2, y2 = id_to_node[t].centroid
            ax.plot([x1, x2], [y1, y2], color="#94a3b8", linewidth=0.8, alpha=0.5)

        for i, n in enumerate(nodes):
            cx, cy = n.centroid
            rw, rh = float(wh[i, 0]), float(wh[i, 1])
            rect = Rectangle(
                (cx - rw / 2.0, cy - rh / 2.0),
                rw,
                rh,
                facecolor=self.TYPE_COLORS.get(n.room_type, "#64748B"),
                edgecolor="#1e293b",
                linewidth=1.2,
                alpha=0.52,
            )
            ax.add_patch(rect)
            ax.text(
                cx,
                cy,
                f"{n.room_type}\n{rw:.1f}x{rh:.1f}",
                ha="center",
                va="center",
                fontsize=7,
                color="#0f172a",
                weight="bold",
            )

        ax.set_aspect("equal", adjustable="box")
        ax.set_title("GNN-based Floor Plan (Boundary + Centroids)", fontsize=11)
        ax.axis("off")

        buffer = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buffer, format="png", bbox_inches="tight", pad_inches=0.15)
        plt.close(fig)

        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def generate(
        self,
        boundary_wkt: str,
        front_door_wkt: str,
        room_centroids: List[List[float]],
        bathroom_centroids: List[List[float]],
        kitchen_centroids: List[List[float]],
    ) -> Dict[str, Any]:
        try:
            boundary = self._parse_wkt_polygon(boundary_wkt)
            door = self._parse_wkt_polygon(front_door_wkt)

            nodes: List[FloorNode] = []
            nodes.extend(self._safe_centroids(room_centroids, "room", start_id=len(nodes)))
            nodes.extend(self._safe_centroids(bathroom_centroids, "bathroom", start_id=len(nodes)))
            nodes.extend(self._safe_centroids(kitchen_centroids, "kitchen", start_id=len(nodes)))

            if nodes:
                living = FloorNode(node_id=len(nodes), room_type="living", centroid=self._door_centroid(door))
                nodes.insert(0, living)
                for idx, node in enumerate(nodes):
                    node.node_id = idx

            if not nodes:
                return {
                    "success": False,
                    "error": "No valid centroids supplied for rooms/bathrooms/kitchens",
                    "message": "Provide at least one centroid to generate a floor plan",
                }

            edges = self._build_graph(nodes)
            wh = self._message_pass_predict(nodes, edges)
            image_base64 = self._render_layout(boundary, door, nodes, edges, wh)

            out_nodes = []
            for i, n in enumerate(nodes):
                out_nodes.append(
                    {
                        "id": n.node_id,
                        "type": n.room_type,
                        "centroid": [float(n.centroid[0]), float(n.centroid[1])],
                        "predicted_width": round(float(wh[i, 0]), 3),
                        "predicted_height": round(float(wh[i, 1]), 3),
                    }
                )

            return {
                "success": True,
                "message": "Floor plan generated using GNN-style graph message passing",
                "image_base64": image_base64,
                "graph": {
                    "node_count": len(nodes),
                    "edge_count": len(edges),
                    "edges": [{"source": int(s), "target": int(t)} for s, t in edges],
                },
                "nodes": out_nodes,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to generate floor plan from the provided constraints",
            }
