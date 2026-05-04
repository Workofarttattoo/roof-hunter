"""
Unified QuLabInfinite MCP server.

This server exposes the curated high-confidence tools plus the full dynamic QuLab
capability graph discovered by the semantic cartographer.
"""
from __future__ import annotations

import importlib
import inspect
import json
import re
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from semantic_lattice_cartographer import LabCapability, LabNode, SemanticLatticeCartographer

# Curated core tool imports
from ech0_interface import ech0_analyze_material, ech0_design_selector
from ech0_invention_accelerator import ech0_quick_invention
from ech0_quantum_tools import ech0_filter_inventions, ech0_optimize_design
from materials_lab.qulab_ai_integration import (
    analyze_structure_with_provenance,
    batch_analyze_structures,
    get_materials_database_info,
)
from chemistry_lab.qulab_ai_integration import (
    analyze_molecule_with_provenance,
    batch_analyze_molecules,
    validate_smiles,
)
from chemistry_lab.molecular_dynamics import create_water_box
from physics_engine.physics_core import create_benchmark_simulation
from physics_engine.thermodynamics import get_element_properties
from qulab_ai.tools import calc


def _serialize_result(value: Any) -> Any:
    """Recursively coerce results to JSON-serializable values."""
    if hasattr(value, "tolist"):
        try:
            return value.tolist()
        except Exception:
            pass
    if isinstance(value, dict):
        return {str(k): _serialize_result(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize_result(v) for v in value]
    if hasattr(value, "__dict__"):
        return _serialize_result(vars(value))
    return value


@dataclass
class Tool:
    """Metadata for a callable tool."""

    name: str
    func: Callable[..., Any]
    description: str
    module: str
    cost_tokens: int = 0
    tags: List[str] = field(default_factory=list)
    parameter_schema: Optional[List[Dict[str, Any]]] = None
    is_real_algorithm: bool = True
    source: str = "curated"

    def to_dict(self) -> Dict[str, Any]:
        if self.parameter_schema is not None:
            parameters = self.parameter_schema
        else:
            signature = inspect.signature(self.func)
            parameters = [
                {
                    "name": param_name,
                    "kind": str(param.kind),
                    "default": None if param.default is inspect._empty else param.default,
                    "annotation": str(param.annotation),
                }
                for param_name, param in signature.parameters.items()
            ]
        return {
            "name": self.name,
            "module": self.module,
            "description": self.description,
            "cost_tokens": self.cost_tokens,
            "tags": self.tags,
            "is_real_algorithm": self.is_real_algorithm,
            "source": self.source,
            "parameters": parameters,
        }


class MaterialsDataset:
    """Load the freshest Materials Project expansion dataset (mp-*) records."""

    def __init__(self, dataset_path: Optional[Path] = None):
        self.dataset_path = dataset_path or Path(
            "materials_lab/data/materials_project_expansion.jsonl"
        )
        self.records: Dict[str, Dict[str, Any]] = {}
        self.latest_timestamp: Optional[str] = None
        self._load()

    def _load(self) -> None:
        if not self.dataset_path.exists():
            raise FileNotFoundError(
                f"Materials dataset not found at {self.dataset_path}. "
                "Please regenerate the expansion JSONL before starting the MCP server."
            )

        with self.dataset_path.open("r") as handle:
            for line in handle:
                record = json.loads(line)
                material_id = record.get("material_id") or record.get("mp_id")
                if not material_id:
                    continue
                self.records[material_id] = record
                acquired = record.get("provenance", {}).get("acquired_at")
                if acquired and (self.latest_timestamp is None or acquired > self.latest_timestamp):
                    self.latest_timestamp = acquired

    def summary(self) -> Dict[str, Any]:
        return {
            "dataset_path": str(self.dataset_path),
            "material_count": len(self.records),
            "latest_timestamp": self.latest_timestamp,
            "sample_ids": sorted(list(self.records.keys()))[:5],
        }

    def get_material(self, mp_id: str) -> Dict[str, Any]:
        try:
            return self.records[mp_id]
        except KeyError as exc:
            raise HTTPException(
                status_code=404,
                detail=f"Material '{mp_id}' not found in the freshest mp dataset",
            ) from exc


class PocketLabAssistant:
    """Lightweight on-site helper for notes + flash joule guidance."""

    def __init__(
        self,
        notes_path: Optional[Path] = None,
        runs_path: Optional[Path] = None,
        cookbook_path: Optional[Path] = None,
    ):
        self.notes_path = notes_path or Path("artifacts/pocket_lab_notes.jsonl")
        self.runs_path = runs_path or Path("artifacts/fjh_runbook.jsonl")
        self.cookbook_path = cookbook_path or Path("artifacts/materials_cookbook_notes.jsonl")
        self.notes_path.parent.mkdir(parents=True, exist_ok=True)
        self.runs_path.parent.mkdir(parents=True, exist_ok=True)
        self.cookbook_path.parent.mkdir(parents=True, exist_ok=True)

    def _read_jsonl(self, path: Path) -> List[Dict[str, Any]]:
        if not path.exists():
            return []
        items: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                raw = line.strip()
                if not raw:
                    continue
                try:
                    items.append(json.loads(raw))
                except Exception:
                    # Ignore malformed lines to keep field usage resilient.
                    continue
        return items

    def _append_jsonl(self, path: Path, entry: Dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")

    def _read_notes(self) -> List[Dict[str, Any]]:
        return self._read_jsonl(self.notes_path)

    def _read_runs(self) -> List[Dict[str, Any]]:
        return self._read_jsonl(self.runs_path)

    def _read_cookbook(self) -> List[Dict[str, Any]]:
        return self._read_jsonl(self.cookbook_path)

    def add_lab_note(
        self,
        note: str,
        tags: Optional[List[str]] = None,
        context: str = "flash_joule_reactor",
        priority: str = "normal",
    ) -> Dict[str, Any]:
        entry = {
            "id": f"note-{int(datetime.now(tz=timezone.utc).timestamp() * 1000)}",
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
            "context": context,
            "priority": priority,
            "tags": tags or [],
            "note": note,
        }
        self._append_jsonl(self.notes_path, entry)
        return {"saved": True, "entry": entry, "notes_path": str(self.notes_path)}

    def list_lab_notes(self, limit: int = 25, context: str = "flash_joule_reactor") -> Dict[str, Any]:
        notes = self._read_notes()
        if context:
            notes = [n for n in notes if n.get("context") == context]
        notes = list(reversed(notes))[: max(1, limit)]
        return {"count": len(notes), "items": notes, "notes_path": str(self.notes_path)}

    def search_lab_notes(self, query: str, limit: int = 25) -> Dict[str, Any]:
        q = query.lower().strip()
        notes = self._read_notes()
        matches: List[Dict[str, Any]] = []
        for note in reversed(notes):
            hay = " ".join(
                [
                    str(note.get("note", "")),
                    str(note.get("context", "")),
                    " ".join([str(t) for t in note.get("tags", [])]),
                ]
            ).lower()
            if q in hay:
                matches.append(note)
            if len(matches) >= max(1, limit):
                break
        return {"query": query, "count": len(matches), "items": matches}

    def add_cookbook_entry(
        self,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        source: str = "echo_materials_cookbook",
    ) -> Dict[str, Any]:
        entry = {
            "id": f"cookbook-{int(datetime.now(tz=timezone.utc).timestamp() * 1000)}",
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
            "title": title,
            "content": content,
            "tags": tags or [],
            "source": source,
        }
        self._append_jsonl(self.cookbook_path, entry)
        return {"saved": True, "entry": entry, "cookbook_path": str(self.cookbook_path)}

    def list_cookbook_entries(self, limit: int = 20) -> Dict[str, Any]:
        items = list(reversed(self._read_cookbook()))[: max(1, limit)]
        return {"count": len(items), "items": items, "cookbook_path": str(self.cookbook_path)}

    def log_fjh_run(
        self,
        run_id: str,
        ingredients: List[Dict[str, Any]],
        electrical_load_a: float,
        temperature_reached_c: float,
        pulse_time_ms: float,
        voltage_v: float = 450.0,
        pulse_count: int = 1,
        date: Optional[str] = None,
        time_local: Optional[str] = None,
        protocol_name: str = "FJH standard",
        notes: str = "",
    ) -> Dict[str, Any]:
        """
        Standardized FJH run protocol entry.

        Required standard fields:
        - ingredients list
        - date
        - time
        - electrical load
        - temperature reached
        - pulse time
        """
        if not ingredients:
            raise HTTPException(status_code=400, detail="ingredients must include at least one item")

        now = datetime.now(tz=timezone.utc)
        entry = {
            "id": f"fjh-{run_id}",
            "run_id": run_id,
            "logged_at_utc": now.isoformat(),
            "date": date or now.date().isoformat(),
            "time_local": time_local or now.strftime("%H:%M:%S"),
            "protocol_name": protocol_name,
            "ingredients": ingredients,
            "electrical": {
                "electrical_load_a": electrical_load_a,
                "voltage_v": voltage_v,
                "pulse_time_ms": pulse_time_ms,
                "pulse_count": pulse_count,
                "energy_estimate_j": round(voltage_v * electrical_load_a * (pulse_time_ms / 1000.0) * pulse_count, 3),
            },
            "temperature_reached_c": temperature_reached_c,
            "notes": notes,
        }
        self._append_jsonl(self.runs_path, entry)
        return {"saved": True, "entry": entry, "runbook_path": str(self.runs_path)}

    def list_fjh_runs(self, limit: int = 20) -> Dict[str, Any]:
        runs = list(reversed(self._read_runs()))[: max(1, limit)]
        return {"count": len(runs), "items": runs, "runbook_path": str(self.runs_path)}

    def search_fjh_runs(self, query: str, limit: int = 20) -> Dict[str, Any]:
        q = query.lower().strip()
        results: List[Dict[str, Any]] = []
        for run in reversed(self._read_runs()):
            ingredient_text = " ".join(
                [f"{item.get('name','')} {item.get('amount','')} {item.get('unit','')}" for item in run.get("ingredients", [])]
            )
            hay = " ".join(
                [
                    str(run.get("run_id", "")),
                    str(run.get("notes", "")),
                    str(run.get("protocol_name", "")),
                    ingredient_text,
                ]
            ).lower()
            if q in hay:
                results.append(run)
            if len(results) >= max(1, limit):
                break
        return {"query": query, "count": len(results), "items": results}

    def ask_fjh_assistant(self, question: str, limit_context: int = 6) -> Dict[str, Any]:
        """
        Practical Q&A for mixtures, electrical applied science, and troubleshooting.
        Uses cookbook entries + runbook + notes for grounded responses.
        """
        q = question.lower()
        notes = list(reversed(self._read_notes()))
        runs = list(reversed(self._read_runs()))
        cookbook = list(reversed(self._read_cookbook()))

        related_runs: List[Dict[str, Any]] = []
        related_notes: List[Dict[str, Any]] = []
        related_cookbook: List[Dict[str, Any]] = []

        def _matches(text: str, query: str) -> bool:
            return query in text.lower()

        keywords = [k for k in re.split(r"[^a-z0-9_]+", q) if len(k) >= 3][:12]
        for run in runs:
            hay = json.dumps(run, default=str).lower()
            if any(k in hay for k in keywords):
                related_runs.append(run)
            if len(related_runs) >= limit_context:
                break
        for note in notes:
            hay = json.dumps(note, default=str).lower()
            if any(k in hay for k in keywords):
                related_notes.append(note)
            if len(related_notes) >= limit_context:
                break
        for item in cookbook:
            hay = json.dumps(item, default=str).lower()
            if any(k in hay for k in keywords):
                related_cookbook.append(item)
            if len(related_cookbook) >= limit_context:
                break

        recommendations: List[str] = []
        if any(x in q for x in ["mixture", "mix", "feedstock", "blend"]):
            recommendations.extend(
                [
                    "Start with a binary mixture and one controlled variable change per run.",
                    "Track ingredient moisture and particle size explicitly; both drive resistance and heating profile.",
                    "Log conductivity before/after pulse to correlate feed composition with reactor response.",
                ]
            )
        if any(x in q for x in ["electrical", "load", "current", "voltage", "pulse"]):
            recommendations.extend(
                [
                    "Keep a fixed voltage window and sweep pulse time in small steps first.",
                    "Record load current and pulse time together; use them to estimate per-shot energy.",
                    "If arcing appears, reduce loop inductance and verify contact integrity before increasing energy.",
                ]
            )
        if any(x in q for x in ["trouble", "fault", "issue", "arcing", "overheat", "failure"]):
            recommendations.extend(
                [
                    "Run pre-fire gate: discharge verification, polarity check, balance resistors, precharge path.",
                    "Move to dummy-load pulses when behavior deviates; capture thermal + scope traces.",
                    "Treat unexplained contact heating as hardware fault until proven otherwise.",
                ]
            )
        if not recommendations:
            recommendations.append(
                "Use `pocket.log_fjh_run` for each run and ask again with run IDs/mixture terms for tighter guidance."
            )

        return {
            "question": question,
            "recommendations": recommendations[:8],
            "related_runs": related_runs,
            "related_notes": related_notes,
            "related_cookbook_entries": related_cookbook,
            "context_sizes": {
                "runs_total": len(runs),
                "notes_total": len(notes),
                "cookbook_total": len(cookbook),
            },
        }

    def flash_joule_advisor(self, mode: str = "pre_fire_gate") -> Dict[str, Any]:
        """Return compact, practical guardrails for FJR bench operation."""
        if mode == "pre_fire_gate":
            return {
                "mode": mode,
                "goal": "No-fire until all checks pass",
                "checklist": [
                    "Power locked out, capacitor bank meter-verified discharged.",
                    "Only pulse-rated capacitors installed; datasheet checked (ESR, pulse/surge, temp).",
                    "Correct polarity and series balancing resistors verified.",
                    "Precharge/inrush path verified; bypass relay/contactor sequencing tested.",
                    "Bleeder path + fuse + E-stop + insulated enclosure confirmed.",
                    "First shots on dummy load with low energy, then step-up while logging thermal/scope observations.",
                ],
            }
        if mode == "materials_focus":
            return {
                "mode": mode,
                "priority_workflow": [
                    "Capture feedstock batch, pre-treatment, and moisture.",
                    "Log pulse settings (V, pulse width, rep rate, shot count).",
                    "Record sample mass before/after, morphology notes, and conductivity changes.",
                    "Track observed failure signatures (arcing, overheating, contact wear).",
                    "Attach each run to an explicit hypothesis + next action.",
                ],
            }
        return {
            "mode": mode,
            "note": "Unknown mode. Supported modes: pre_fire_gate, materials_focus",
        }


class ToolRegistry:
    """Registry that maps tool names to callables and metadata."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def list_tools(self) -> List[Dict[str, Any]]:
        return [tool.to_dict() for tool in self._tools.values()]

    def cartography(self) -> Dict[str, List[Dict[str, Any]]]:
        mapped: Dict[str, List[Dict[str, Any]]] = {}
        for tool in self._tools.values():
            mapped.setdefault(tool.module, []).append(tool.to_dict())
        for module_tools in mapped.values():
            module_tools.sort(key=lambda entry: entry["name"])
        return mapped

    def call(self, tool_name: str, **kwargs: Any) -> Any:
        if tool_name not in self._tools:
            raise HTTPException(status_code=404, detail=f"Unknown tool '{tool_name}'")
        tool = self._tools[tool_name]
        return _serialize_result(tool.func(**kwargs))

    def count_by_source(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for tool in self._tools.values():
            counts[tool.source] = counts.get(tool.source, 0) + 1
        return counts


class DynamicLabExecutor:
    """Lazy loader/executor for cartographer-discovered lab capabilities."""

    def __init__(self, lab_directory: Path):
        self._cartographer = SemanticLatticeCartographer(str(lab_directory))
        self._cartographer.discover_labs()
        self._catalog: Dict[str, Tuple[str, LabNode, LabCapability]] = {}
        self._instances: Dict[str, Any] = {}
        self._build_catalog()

    def _build_catalog(self) -> None:
        for lab_name, node in self._cartographer.labs.items():
            for cap in node.capabilities:
                tool_name = f"{lab_name}.{cap.name}"
                self._catalog[tool_name] = (lab_name, node, cap)

    def catalog(self) -> Dict[str, Tuple[str, LabNode, LabCapability]]:
        return self._catalog

    def call(self, tool_name: str, **kwargs: Any) -> Any:
        if tool_name not in self._catalog:
            raise HTTPException(status_code=404, detail=f"Unknown dynamic tool '{tool_name}'")
        lab_name, node, _ = self._catalog[tool_name]
        _, func_name = tool_name.split(".", 1)
        func = self._resolve_callable(lab_name, node, func_name)
        try:
            return func(**kwargs)
        except TypeError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid params for {tool_name}: {exc}") from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"{tool_name} failed: {exc}") from exc

    def _load_module_and_default_instance(self, lab_name: str, node: LabNode) -> Tuple[Any, Any]:
        try:
            module = importlib.import_module(lab_name)
            if node.class_name and hasattr(module, node.class_name):
                cache_key = f"{lab_name}:{node.class_name}"
                if cache_key in self._instances:
                    return module, self._instances[cache_key]
                lab_class = getattr(module, node.class_name)
                instance = lab_class()
                self._instances[cache_key] = instance
            else:
                instance = module
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Unable to import {lab_name}: {exc}") from exc
        return module, instance

    def _resolve_callable(self, lab_name: str, node: LabNode, func_name: str) -> Callable[..., Any]:
        module, instance = self._load_module_and_default_instance(lab_name, node)
        if hasattr(instance, func_name):
            return getattr(instance, func_name)
        if hasattr(module, func_name):
            return getattr(module, func_name)

        # Fallback: search any class in module that defines the capability.
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and hasattr(attr, func_name):
                cache_key = f"{lab_name}:{attr_name}"
                if cache_key not in self._instances:
                    try:
                        self._instances[cache_key] = attr()
                    except Exception:
                        continue
                return getattr(self._instances[cache_key], func_name)

        raise HTTPException(
            status_code=404, detail=f"Function '{func_name}' not found in '{lab_name}'"
        )


class ToolInvocationRequest(BaseModel):
    tool: str
    params: Dict[str, Any] = {}


class ExperimentRecord(BaseModel):
    name: str
    path: str
    description: str
    entry_point: Optional[str] = None


def build_registry(materials_dataset: MaterialsDataset) -> ToolRegistry:
    registry = ToolRegistry()

    registry.register(
        Tool(
            name="materials.get_mp_material",
            func=materials_dataset.get_material,
            description="Return the freshest mp-* record from the Materials Project expansion dataset.",
            module="materials",
            tags=["materials", "database", "mp"],
            source="curated",
        )
    )
    registry.register(
        Tool(
            name="materials.analyze_structure",
            func=analyze_structure_with_provenance,
            description="Analyze a structure file with provenance tracking.",
            module="materials",
            source="curated",
        )
    )
    registry.register(
        Tool(
            name="materials.batch_analyze_structures",
            func=batch_analyze_structures,
            description="Analyze a batch of structure files.",
            module="materials",
            source="curated",
        )
    )
    registry.register(
        Tool(
            name="materials.database_info",
            func=get_materials_database_info,
            description="Get metadata about the materials database (coverage, fields, stats).",
            module="materials",
            source="curated",
        )
    )

    registry.register(
        Tool(
            name="chemistry.analyze_molecule",
            func=analyze_molecule_with_provenance,
            description="Analyze a molecule specified by SMILES, returning provenance-aware annotations.",
            module="chemistry",
            source="curated",
        )
    )
    registry.register(
        Tool(
            name="chemistry.batch_analyze_molecules",
            func=batch_analyze_molecules,
            description="Run batched molecule analysis for SMILES lists.",
            module="chemistry",
            source="curated",
        )
    )
    registry.register(
        Tool(
            name="chemistry.validate_smiles",
            func=validate_smiles,
            description="Validate SMILES syntax before downstream computations.",
            module="chemistry",
            source="curated",
        )
    )
    registry.register(
        Tool(
            name="chemistry.create_water_box",
            func=create_water_box,
            description="Create a water box for MD simulations with configurable size.",
            module="chemistry",
            tags=["md", "simulation"],
            source="curated",
        )
    )

    registry.register(
        Tool(
            name="physics.get_element_properties",
            func=get_element_properties,
            description="Return thermodynamic properties for an element symbol.",
            module="physics",
            source="curated",
        )
    )
    registry.register(
        Tool(
            name="physics.create_benchmark_simulation",
            func=create_benchmark_simulation,
            description="Create a physics benchmark scenario for downstream simulation runs.",
            module="physics",
            tags=["simulation"],
            source="curated",
        )
    )

    registry.register(
        Tool(
            name="ai.calc",
            func=calc,
            description="Lightweight calculator for quick numeric expressions.",
            module="ai",
            source="curated",
        )
    )

    registry.register(
        Tool(
            name="ech0.analyze_material",
            func=ech0_analyze_material,
            description="Run the Ech0 engine's material analysis pipeline.",
            module="ech0",
            cost_tokens=300,
            source="curated",
        )
    )
    registry.register(
        Tool(
            name="ech0.design_selector",
            func=ech0_design_selector,
            description="Select candidate material designs for a target application and budget.",
            module="ech0",
            cost_tokens=300,
            source="curated",
        )
    )
    registry.register(
        Tool(
            name="ech0.filter_inventions",
            func=ech0_filter_inventions,
            description="Filter and rank inventions discovered across lab runs.",
            module="ech0",
            cost_tokens=150,
            source="curated",
        )
    )
    registry.register(
        Tool(
            name="ech0.optimize_design",
            func=ech0_optimize_design,
            description="Optimize an invention or material design using Ech0 heuristics.",
            module="ech0",
            cost_tokens=300,
            source="curated",
        )
    )
    registry.register(
        Tool(
            name="ech0.quick_invention",
            func=ech0_quick_invention,
            description="Rapid invention generator for proofs of concept.",
            module="ech0",
            cost_tokens=500,
            source="curated",
        )
    )

    pocket = PocketLabAssistant()
    registry.register(
        Tool(
            name="pocket.add_lab_note",
            func=pocket.add_lab_note,
            description="Persist a timestamped lab note for the on-site pocket helper.",
            module="pocket",
            tags=["notes", "flash-joule", "logging"],
            source="curated",
        )
    )
    registry.register(
        Tool(
            name="pocket.list_lab_notes",
            func=pocket.list_lab_notes,
            description="List recent lab notes (defaults to flash_joule_reactor context).",
            module="pocket",
            tags=["notes", "history"],
            source="curated",
        )
    )
    registry.register(
        Tool(
            name="pocket.search_lab_notes",
            func=pocket.search_lab_notes,
            description="Search lab notes by keyword for quick recall at the bench.",
            module="pocket",
            tags=["notes", "search"],
            source="curated",
        )
    )
    registry.register(
        Tool(
            name="pocket.flash_joule_advisor",
            func=pocket.flash_joule_advisor,
            description="Return compact flash-joule safety/materials guidance for on-site use.",
            module="pocket",
            tags=["flash-joule", "safety", "materials"],
            source="curated",
        )
    )
    registry.register(
        Tool(
            name="pocket.log_fjh_run",
            func=pocket.log_fjh_run,
            description="Log a standardized FJH run protocol (ingredients/date/time/load/temp/pulse).",
            module="pocket",
            tags=["flash-joule", "runbook", "materials", "electrical"],
            source="curated",
        )
    )
    registry.register(
        Tool(
            name="pocket.list_fjh_runs",
            func=pocket.list_fjh_runs,
            description="List recent standardized FJH run entries.",
            module="pocket",
            tags=["flash-joule", "runbook", "history"],
            source="curated",
        )
    )
    registry.register(
        Tool(
            name="pocket.search_fjh_runs",
            func=pocket.search_fjh_runs,
            description="Search FJH runbook entries by mixture terms or troubleshooting keywords.",
            module="pocket",
            tags=["flash-joule", "runbook", "search"],
            source="curated",
        )
    )
    registry.register(
        Tool(
            name="pocket.add_cookbook_entry",
            func=pocket.add_cookbook_entry,
            description="Store Echo materials cookbook knowledge snippets for local Q&A grounding.",
            module="pocket",
            tags=["cookbook", "materials", "knowledge"],
            source="curated",
        )
    )
    registry.register(
        Tool(
            name="pocket.list_cookbook_entries",
            func=pocket.list_cookbook_entries,
            description="List saved materials cookbook entries.",
            module="pocket",
            tags=["cookbook", "materials", "knowledge"],
            source="curated",
        )
    )
    registry.register(
        Tool(
            name="pocket.ask_fjh_assistant",
            func=pocket.ask_fjh_assistant,
            description="Ask mixture/build troubleshooting questions grounded in cookbook + runbook + notes.",
            module="pocket",
            tags=["assistant", "flash-joule", "mixtures", "troubleshooting"],
            source="curated",
        )
    )

    return registry


def _dynamic_call_builder(dynamic_executor: DynamicLabExecutor, tool_name: str) -> Callable[..., Any]:
    def _call(**kwargs: Any) -> Any:
        return dynamic_executor.call(tool_name, **kwargs)

    return _call


def extend_registry_with_dynamic_tools(
    registry: ToolRegistry, dynamic_executor: DynamicLabExecutor
) -> int:
    added = 0
    for tool_name, (lab_name, _node, cap) in dynamic_executor.catalog().items():
        if tool_name in registry._tools:
            continue
        param_schema = [
            {
                "name": param_name,
                "kind": "POSITIONAL_OR_KEYWORD",
                "default": None,
                "annotation": str(param_type),
            }
            for param_name, param_type in cap.parameters.items()
        ]
        registry.register(
            Tool(
                name=tool_name,
                func=_dynamic_call_builder(dynamic_executor, tool_name),
                description=cap.docstring or f"Execute {tool_name}",
                module=lab_name,
                tags=cap.domain_keywords[:8],
                parameter_schema=param_schema,
                is_real_algorithm=cap.is_real_algorithm,
                source="dynamic",
            )
        )
        added += 1
    return added


EXPERIMENTS: List[ExperimentRecord] = [
    ExperimentRecord(
        name="oncology.demo_experiment",
        path="demo_experiment.py",
        description="Demonstration of calibrated tumor lab scenarios (chemo vs Ech0 protocol).",
    ),
    ExperimentRecord(
        name="materials.validation_suite",
        path="test_full_6_6m_materials.py",
        description="Automated validation harness for the expanded materials dataset.",
    ),
    ExperimentRecord(
        name="chemistry.expanded_database",
        path="test_expanded_database.py",
        description="Smoke tests that exercise the chemistry ingestion and validation stack.",
    ),
    ExperimentRecord(
        name="physics.benchmarks",
        path="physics_engine/physics_core.py",
        description="Core physics benchmark scenarios callable via the MCP API.",
        entry_point="create_benchmark_simulation",
    ),
]


app = FastAPI(title="QuLabInfinite MCP Server", version="2.0.0")
materials_dataset = MaterialsDataset()
registry = build_registry(materials_dataset)
dynamic_executor = DynamicLabExecutor(Path(__file__).parent)
dynamic_tools_added = extend_registry_with_dynamic_tools(registry, dynamic_executor)


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "materials_dataset": materials_dataset.summary(),
        "tool_count": len(registry.list_tools()),
        "tools_by_source": registry.count_by_source(),
        "dynamic_tools_added": dynamic_tools_added,
        "experiment_count": len(EXPERIMENTS),
    }


@app.get("/tools")
def list_tools() -> Dict[str, Any]:
    return {
        "tools": registry.list_tools(),
        "cartography": registry.cartography(),
        "experiments": [experiment.model_dump() for experiment in EXPERIMENTS],
        "stats": {
            "tool_count": len(registry.list_tools()),
            "tools_by_source": registry.count_by_source(),
            "dynamic_tools_added": dynamic_tools_added,
        },
    }


@app.post("/tools/call")
def call_tool(request: ToolInvocationRequest) -> Any:
    return registry.call(request.tool, **request.params)


@app.get("/map")
def map_everything() -> Dict[str, Any]:
    return {
        "cartography": registry.cartography(),
        "experiments": [experiment.model_dump() for experiment in EXPERIMENTS],
        "materials_dataset": materials_dataset.summary(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8102)
