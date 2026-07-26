#!/usr/bin/env python3
"""Gearbox V3 Preview — deterministic routing, observability and local learning.

Stdlib-only core used by the shell compatibility wrappers and Claude Code hooks.
The default mode is ``observe``: it predicts and records, but never changes the
active model or executes destructive actions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

# La biblioteca vive junto a este archivo, tanto en el repo como en la
# instalación (~/.claude/gearbox/gearboxlib). Se añade la carpeta propia al path
# para no depender de cómo se invoque el script.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gearboxlib import consent as gb_consent          # noqa: E402
from gearboxlib import capsule as gb_capsule          # noqa: E402
from gearboxlib import outbox as gb_outbox            # noqa: E402
from gearboxlib import priors as gb_priors            # noqa: E402
from gearboxlib import privacy as gb_privacy          # noqa: E402
from gearboxlib import transport as gb_transport      # noqa: E402
from gearboxlib.paths import ensure_private_dir, harden, install_salt  # noqa: E402

VERSION = "3.0.0-preview.2"
VALID_GEARS = ("auto", "G0", "G1", "G2", "G3", "G3.5", "G4", "G5")
DEFAULT_TASKS = {
    "auto": "auto",
    "G0": "rutina",
    "G1": "contenido",
    "G2": "ejecución",
    "G3": "planeación",
    "G3.5": "turno-profundo",
    "G4": "crítico",
    "G5": "arquitectura",
}
DEFAULT_ROUTES = {
    "G0": ("haiku", "low"),
    "G1": ("sonnet", "medium"),
    "G2": ("sonnet", "high"),
    "G3": ("opusplan", "high"),
    "G3.5": ("opus", "xhigh"),
    "G4": ("opus", "xhigh"),
    "G5": ("opus", "xhigh"),
}
PRIOR_SUCCESS = {
    "G0": 0.76,
    "G1": 0.80,
    "G2": 0.82,
    "G3": 0.83,
    "G3.5": 0.84,
    "G4": 0.88,
    "G5": 0.80,
}
GLOBAL_SKILLS = {
    "deep-research", "artifact-design", "update-config", "keybindings-help",
    "verify", "code-review", "simplify", "fewer-permission-prompts", "loop",
    "schedule", "claude-api", "run", "init", "review", "security-review",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def gb_dir() -> Path:
    return Path(os.environ.get("GEARBOX_HOME", Path.home() / ".claude" / "gearbox")).expanduser()


def skills_dir() -> Path:
    return Path(os.environ.get("GEARBOX_SKILLS_DIR", Path.home() / ".claude" / "skills")).expanduser()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def atomic_write_json(path: Path, value: Any) -> None:
    ensure_dir(path.parent)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(value, fh, ensure_ascii=False, separators=(",", ":"))
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    line = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def read_stdin_json() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def default_policy() -> dict[str, Any]:
    return {
        "version": 1,
        "mode": "observe",
        "privacy": {"store_prompt": False},
        "automation": {
            "min_confidence": 0.90,
            "min_samples": 100,
            "allowed_gears": ["G0", "G1", "G2"],
        },
        "human_gate_categories": [
            "security", "privacy", "payments", "production", "legal",
            "deletion", "irreversible",
        ],
    }


def load_policy() -> dict[str, Any]:
    policy = default_policy()
    custom = load_json(gb_dir() / "policy.json", {})
    if isinstance(custom, dict):
        for key, value in custom.items():
            if isinstance(value, dict) and isinstance(policy.get(key), dict):
                policy[key].update(value)
            else:
                policy[key] = value
    return policy


def state_path() -> Path:
    return gb_dir() / "state.json"


def load_state() -> dict[str, str]:
    state = load_json(state_path(), {})
    if not isinstance(state, dict):
        state = {}
    return {
        "gear": str(state.get("gear", "auto")),
        "task": str(state.get("task", "auto")),
        "effort": str(state.get("effort", "auto")),
        "model": str(state.get("model", "")),
    }


def write_state(gear: str, task: str, effort: str, model: str = "") -> dict[str, str]:
    if gear not in VALID_GEARS:
        raise ValueError(f"marcha inválida: {gear}")
    current = load_state()
    value = {
        "gear": gear,
        "task": task or DEFAULT_TASKS[gear],
        "effort": effort or "high",
        "model": model or current.get("model", ""),
    }
    atomic_write_json(state_path(), value)
    return value


MIGRATION_COLUMNS = (
    ("project_ref", "TEXT"),
    ("session_ref", "TEXT"),
    ("human_override", "INTEGER DEFAULT 0"),
    ("feedback_reason", "TEXT"),
    ("rating", "INTEGER"),
    ("latency_ms", "INTEGER"),
)


def db_connect() -> sqlite3.Connection:
    ensure_private_dir(gb_dir())
    conn = sqlite3.connect(gb_dir() / "gearbox.db")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS routing_events (
            task_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            session_id TEXT,
            project_id TEXT,
            prompt_hash TEXT,
            prompt_chars INTEGER NOT NULL,
            task_type TEXT NOT NULL,
            gear TEXT NOT NULL,
            model TEXT NOT NULL,
            effort TEXT NOT NULL,
            risk REAL NOT NULL,
            complexity REAL NOT NULL,
            ambiguity REAL NOT NULL,
            routing_confidence REAL NOT NULL,
            predicted_success REAL NOT NULL,
            human_gate INTEGER NOT NULL,
            reason TEXT NOT NULL,
            outcome TEXT,
            retrabajo INTEGER DEFAULT 0,
            actual_model TEXT,
            actual_effort TEXT,
            cost_usd REAL,
            updated_at TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_route_stats ON routing_events(task_type, gear, model, effort, outcome)"
    )
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(routing_events)")}
    for column, decl in MIGRATION_COLUMNS:
        if column not in existing:
            conn.execute(f"ALTER TABLE routing_events ADD COLUMN {column} {decl}")
    conn.commit()
    harden(gb_dir() / "gearbox.db")
    return conn


def scrub_legacy_identifiers() -> int:
    """Borra de la base local rutas, session_id y hashes de prompt heredados.

    La regla 6 de la misión prohíbe *almacenar* rutas locales, identificadores de
    sesión y hashes correlacionables de prompts. Las versiones anteriores sí los
    guardaban; esta función limpia esas columnas sin perder el aprendizaje (que
    vive en task_type/gear/model/effort/outcome).
    """
    try:
        with db_connect() as conn:
            cursor = conn.execute(
                """
                UPDATE routing_events
                SET session_id=NULL, project_id=NULL, prompt_hash=NULL
                WHERE session_id IS NOT NULL OR project_id IS NOT NULL OR prompt_hash IS NOT NULL
                """
            )
            conn.commit()
            return cursor.rowcount or 0
    except sqlite3.Error:
        return 0


@dataclass(frozen=True)
class Route:
    gear: str
    task_type: str
    model: str
    effort: str
    risk: float
    complexity: float
    ambiguity: float
    routing_confidence: float
    predicted_success: float
    human_gate: bool
    reason: str
    fallback: str
    matched_signals: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "gear": self.gear,
            "task_type": self.task_type,
            "model": self.model,
            "effort": self.effort,
            "risk": round(self.risk, 3),
            "complexity": round(self.complexity, 3),
            "ambiguity": round(self.ambiguity, 3),
            "routing_confidence": round(self.routing_confidence, 3),
            "predicted_success": round(self.predicted_success, 3),
            "human_gate": self.human_gate,
            "reason": self.reason,
            "fallback": self.fallback,
            "matched_signals": list(self.matched_signals),
        }


SIGNALS: dict[str, tuple[str, ...]] = {
    "security": (
        "seguridad", "security", "vulnerabilidad", "vulnerability", "secretos",
        "secrets", "oauth", "autenticación", "authentication", "cifrado", "encryption",
        "inyección", "injection", "pentest", "pii", "datos personales",
    ),
    "payments": (
        "pago", "pagos", "payment", "payments", "checkout", "facturación", "billing",
        "dinero", "money", "financiero", "financial",
    ),
    "production": (
        "producción", "production", "incidente", "incident", "caído", "outage",
        "hotfix", "rollback", "base de datos productiva", "production database",
    ),
    "legal": (
        "legal", "contrato", "contract", "compliance", "cumplimiento", "regulatorio",
        "regulatory", "impuesto", "tax",
    ),
    "deletion": (
        "eliminar datos", "delete data", "borrar datos", "drop table", "truncate",
        "destruir", "irreversible",
    ),
    "architecture": (
        "arquitectura", "architecture", "ecosistema", "ecosystem", "multi-repo",
        "varios repos", "infraestructura", "infrastructure", "blueprint", "tradeoff",
        "trade-off", "diseño de sistema", "system design", "graphos", "opengravity",
    ),
    "planning": (
        "plan", "planea", "planifica", "roadmap", "prp", "especificación", "specification",
        "por fases", "milestones", "estrategia de implementación",
    ),
    "content": (
        "copy", "contenido", "content", "redacta", "redacción", "linkedin", "seo",
        "caption", "artículo", "article", "landing page", "anuncio", "marketing",
    ),
    "routine": (
        "renombra", "rename", "formatea", "format", "lista archivos", "list files",
        "buscar referencias", "search references", "grep", "clasifica", "ordenar",
        "resumir logs", "read logs", "convertir formato",
    ),
    "research": (
        "investiga", "research", "triangula", "fuentes oficiales", "official sources",
        "compara fuentes", "literature review", "estado del arte",
    ),
    "debug": (
        "bug", "debug", "error", "falla", "failed", "stack trace", "traceback",
        "no funciona", "root cause", "causa raíz",
    ),
    "implementation": (
        "implementa", "implement", "crea", "build", "desarrolla", "develop", "fix",
        "corrige", "refactor", "deploy", "integra", "integrate", "migración", "migration",
    ),
}


def matched_categories(text: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for category, terms in SIGNALS.items():
        hits = [term for term in terms if term in text]
        if hits:
            found[category] = hits
    return found


def empirical_success(task_type: str, gear: str, model: str, effort: str, prior: float) -> tuple[float, int]:
    try:
        with db_connect() as conn:
            row = conn.execute(
                """
                SELECT
                    SUM(CASE WHEN outcome='accepted' THEN 1 ELSE 0 END) AS wins,
                    SUM(CASE WHEN outcome IN ('rejected','rework') THEN 1 ELSE 0 END) AS losses
                FROM routing_events
                WHERE task_type=? AND gear=? AND model=? AND effort=? AND outcome IS NOT NULL
                """,
                (task_type, gear, model, effort),
            ).fetchone()
        wins = int(row["wins"] or 0)
        losses = int(row["losses"] or 0)
        samples = wins + losses
        alpha = prior * 4.0 + wins
        beta = (1.0 - prior) * 4.0 + losses
        return alpha / (alpha + beta), samples
    except sqlite3.Error:
        return prior, 0


def classify(prompt: str, project: str = "") -> Route:
    text = normalize_text(f"{prompt} {project}")
    categories = matched_categories(text)
    signals = tuple(sorted(categories))

    high_risk = any(k in categories for k in ("security", "payments", "production", "legal", "deletion"))
    architecture = "architecture" in categories
    planning = "planning" in categories
    routine = "routine" in categories
    content = "content" in categories
    research = "research" in categories
    debug = "debug" in categories
    implementation = "implementation" in categories

    multi_scope = any(term in text for term in ("varios repos", "multi-repo", "ecosistema completo", "end to end", "extremo a extremo"))
    explicit_single_question = text.count("?") == 1 and not implementation
    vague_terms = sum(term in text for term in ("lo mejor", "todo", "completo", "como sea", "lo que haga falta", "próximo nivel"))

    complexity = 0.30
    complexity += 0.18 if implementation else 0
    complexity += 0.18 if debug else 0
    complexity += 0.22 if architecture else 0
    complexity += 0.12 if research else 0
    complexity += 0.15 if multi_scope else 0
    complexity += min(len(prompt) / 6000.0, 0.15)
    complexity = min(complexity, 1.0)

    ambiguity = 0.20 + min(vague_terms * 0.12, 0.36)
    ambiguity += 0.12 if architecture and not planning else 0
    ambiguity += 0.10 if len(prompt.strip()) < 35 else 0
    ambiguity = min(ambiguity, 1.0)

    risk = 0.15
    risk += 0.55 if high_risk else 0
    risk += 0.15 if architecture else 0
    risk += 0.10 if multi_scope else 0
    risk = min(risk, 1.0)

    if high_risk:
        gear, task_type, reason = "G4", "critical", "Riesgo alto: seguridad, dinero, producción, datos o cumplimiento"
    elif architecture and (multi_scope or ambiguity >= 0.55 or complexity >= 0.78):
        gear, task_type, reason = "G5", "architecture", "Arquitectura ambigua o de alcance sistémico/multi-repositorio"
    elif planning or (architecture and not implementation):
        gear, task_type, reason = "G3", "planning", "La tarea necesita separar planeación de ejecución"
    elif explicit_single_question and (research or complexity >= 0.62):
        gear, task_type, reason = "G3.5", "deep_analysis", "Pregunta aislada con análisis profundo o triangulación"
    elif routine and not high_risk:
        gear, task_type, reason = "G0", "routine", "Trabajo mecánico, reversible y verificable"
    elif content and not architecture:
        gear, task_type, reason = "G1", "content", "Producción o edición de contenido"
    else:
        gear = "G2"
        task_type = "debugging" if debug else "implementation"
        reason = "Ejecución con contrato razonablemente claro"

    model, effort = DEFAULT_ROUTES[gear]
    if gear == "G5" and high_risk:
        model, effort = "opus", "xhigh"

    matched_count = sum(len(v) for v in categories.values())
    routing_confidence = min(0.56 + matched_count * 0.045 + (0.08 if high_risk else 0), 0.96)
    if not categories:
        routing_confidence = 0.58

    prior = PRIOR_SUCCESS[gear]
    # Prior comunitario (si existe y es válido) sólo como punto de partida: pesa
    # menos conforme el usuario acumula evidencia propia. Nunca toca human_gate.
    community = None
    try:
        community = gb_priors.lookup(task_type, gear, gb_privacy.model_family(model), effort)
    except Exception:  # noqa: BLE001 — un prior corrupto jamás rompe la clasificación
        community = None
    _, samples = empirical_success(task_type, gear, model, effort, prior)
    blended = gb_priors.blended_prior(prior, community, samples)
    predicted_success, samples = empirical_success(task_type, gear, model, effort, blended)
    if samples < 5:
        predicted_success = (predicted_success + blended) / 2.0

    human_gate = high_risk or gear == "G5"
    fallback = {
        "G0": "escalar a G2 si la salida no es verificable",
        "G1": "subir esfuerzo si faltan matices o consistencia",
        "G2": "escalar a G3 si aparecen dependencias o alcance ambiguo",
        "G3": "volver a planear si falla el criterio de terminado",
        "G3.5": "convertir en G3 si la respuesta exige implementación",
        "G4": "detener y solicitar revisión humana ante evidencia insuficiente",
        "G5": "entregar blueprint; ejecutar después en G2/G3",
    }[gear]

    return Route(
        gear=gear,
        task_type=task_type,
        model=model,
        effort=effort,
        risk=risk,
        complexity=complexity,
        ambiguity=ambiguity,
        routing_confidence=routing_confidence,
        predicted_success=predicted_success,
        human_gate=human_gate,
        reason=reason,
        fallback=fallback,
        matched_signals=signals,
    )


def make_task_id(session_id: str, prompt: str) -> str:
    seed = f"{session_id}|{utc_now()}|{prompt}"
    return "gbx-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def record_prediction(route: Route, prompt: str, session_id: str = "", project_id: str = "") -> dict[str, Any]:
    """Registra la predicción SIN guardar ruta, sesión ni hash del prompt.

    De la ruta de proyecto y del id de sesión sólo se conserva un seudónimo
    HMAC con sal local (``project_ref``/``session_ref``): sirve para agrupar
    trabajo del mismo proyecto sin que la base contenga la ruta real, y no es
    correlacionable entre equipos porque la sal nunca sale de éste.
    """
    task_id = make_task_id(session_id, prompt)
    salt = install_salt()
    project_ref = gb_privacy.local_ref(salt, project_id)
    session_ref = gb_privacy.local_ref(salt, session_id)
    record = {
        "task_id": task_id,
        "created_at": utc_now(),
        "project_ref": project_ref,
        "session_ref": session_ref,
        "prompt_chars": len(prompt),
        **route.as_dict(),
    }
    atomic_write_json(gb_dir() / "last_prediction.json", record)
    harden(gb_dir() / "last_prediction.json")
    try:
        with db_connect() as conn:
            conn.execute(
                """
                INSERT INTO routing_events (
                    task_id, created_at, project_ref, session_ref, prompt_chars,
                    task_type, gear, model, effort, risk, complexity, ambiguity,
                    routing_confidence, predicted_success, human_gate, reason
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    task_id, record["created_at"], project_ref, session_ref,
                    record["prompt_chars"], route.task_type,
                    route.gear, route.model, route.effort, route.risk, route.complexity,
                    route.ambiguity, route.routing_confidence, route.predicted_success,
                    int(route.human_gate), route.reason,
                ),
            )
            conn.commit()
    except sqlite3.Error:
        append_jsonl(gb_dir() / "prediction-fallback.jsonl", record)
    return record


def prediction_context(record: dict[str, Any], mode: str) -> str:
    gate = "sí" if record.get("human_gate") else "no"
    return (
        "⚙ GEARBOX V3 PREDICTION\n"
        f"Modo: {mode} (no cambia el modelo automáticamente)\n"
        f"Marcha: {record['gear']} · {record['model']} · {record['effort']}\n"
        f"Tarea: {record['task_type']}\n"
        f"Confianza de routing: {record['routing_confidence']:.0%}\n"
        f"Éxito estimado: {record['predicted_success']:.0%} (prior/local, no garantía)\n"
        f"Riesgo: {record['risk']:.0%} · Gate humano: {gate}\n"
        f"Razón: {record['reason']}\n"
        f"Fallback: {record['fallback']}\n"
        f"Task ID: {record['task_id']}"
    )


def cmd_hook(_: argparse.Namespace) -> int:
    payload = read_stdin_json()
    prompt = str(payload.get("prompt", ""))
    if not prompt.strip():
        return 0
    session_id = str(payload.get("session_id", ""))
    project = str(payload.get("cwd", ""))
    route = classify(prompt, project)
    record = record_prediction(route, prompt, session_id, project)
    mode = str(load_policy().get("mode", "observe"))
    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": prediction_context(record, mode),
        }
    }
    print(json.dumps(output, ensure_ascii=False))
    return 0


def cmd_classify(args: argparse.Namespace) -> int:
    prompt = args.prompt if args.prompt is not None else sys.stdin.read()
    route = classify(prompt, args.project or "")
    value = route.as_dict()
    if args.record:
        value = record_prediction(route, prompt, args.session or "", args.project or "")
    print(json.dumps(value, ensure_ascii=False, indent=2))
    return 0


def log_event(action: str, gear: str, task: str, effort: str, model: str = "") -> None:
    record: dict[str, Any] = {
        "ts": utc_now(), "gear": gear, "task": task, "effort": effort, "action": action,
    }
    if model:
        record["model"] = model
    append_jsonl(gb_dir() / "events.jsonl", record)


def valid_skill(skill: str) -> bool:
    if skill == "ninguno":
        return True
    if not skill:
        return False
    return (skills_dir() / skill).is_dir() or skill in GLOBAL_SKILLS


def cmd_log(args: argparse.Namespace) -> int:
    mode = args.log_args[0] if args.log_args else "set"
    rest = args.log_args[1:]
    if mode == "decision":
        gear_actual = rest[0] if len(rest) > 0 else ""
        gear_rec = rest[1] if len(rest) > 1 else ""
        task = rest[2] if len(rest) > 2 else ""
        skill = rest[3] if len(rest) > 3 else ""
        doc = rest[4] if len(rest) > 4 else ""
        accion = rest[5] if len(rest) > 5 else ""
        if not accion:
            accion = "ejecutar" if gear_actual and gear_actual == gear_rec else "recomendar-cambio"
        if not valid_skill(skill):
            skill = "ninguno"
        model = os.environ.get("GEARBOX_MODEL", "") or load_state().get("model", "")
        append_jsonl(gb_dir() / "decisions.jsonl", {
            "ts": utc_now(), "model": model, "gear_actual": gear_actual,
            "gear_recomendada": gear_rec, "task": task, "skill": skill,
            "accion": accion, "doc": doc, "retrabajo": False,
        })
    elif mode == "retrabajo":
        task = rest[0] if rest else ""
        append_jsonl(gb_dir() / "decisions.jsonl", {
            "ts": utc_now(), "model": os.environ.get("GEARBOX_MODEL", ""),
            "gear_actual": "", "gear_recomendada": "", "task": task,
            "skill": "", "accion": "retrabajo", "doc": "", "retrabajo": True,
        })
    else:
        gear = rest[0] if len(rest) > 0 else "auto"
        task = rest[1] if len(rest) > 1 else "auto"
        effort = rest[2] if len(rest) > 2 else "auto"
        model = rest[3] if len(rest) > 3 else os.environ.get("GEARBOX_MODEL", "")
        log_event(mode, gear, task, effort, model)
    return 0


def cmd_set(args: argparse.Namespace) -> int:
    if args.gear not in VALID_GEARS:
        print(f'Gearbox — marcha inválida: "{args.gear}"', file=sys.stderr)
        print("Marchas válidas: " + " ".join(VALID_GEARS), file=sys.stderr)
        return 1
    task = args.task or DEFAULT_TASKS[args.gear]
    effort = args.effort or "high"
    model = args.model or os.environ.get("GEARBOX_MODEL", "")
    value = write_state(args.gear, task, effort, model)
    log_event("set", value["gear"], value["task"], value["effort"], value["model"])
    print(f"⚙ Gearbox: {value['gear']} · {value['task']} · {value['effort']}")
    return 0


def cmd_reset(_: argparse.Namespace) -> int:
    value = write_state("auto", "auto", "auto", "")
    log_event("reset", value["gear"], value["task"], value["effort"], value["model"])
    return 0


def model_gear(model: str, effort: str, state_gear: str) -> str:
    m = model.lower()
    if "fable" in m:
        return "G5"
    if "haiku" in m:
        return "G0"
    if "sonnet" in m:
        return "G1" if effort in ("low", "medium") else "G2"
    if "opus" in m:
        return state_gear if state_gear in ("G3", "G3.5", "G4") else "G4"
    return "G2" if state_gear == "auto" else state_gear


def percentage(value: Any) -> int | None:
    try:
        return max(0, min(100, int(float(value))))
    except (TypeError, ValueError):
        return None


def bar_for(pct: int) -> str:
    filled = max(0, min(5, round(pct / 20)))
    return "▓" * filled + "░" * (5 - filled)


def ansi_color(pct: int) -> str:
    return "31" if pct >= 80 else "33" if pct >= 50 else "32"


def cmd_statusline(_: argparse.Namespace) -> int:
    payload = read_stdin_json()
    model_obj = payload.get("model", {})
    model = str(model_obj.get("display_name", "?")) if isinstance(model_obj, dict) else "?"
    state = load_state()
    effort_obj = payload.get("effort", "")
    if isinstance(effort_obj, dict):
        effort = str(effort_obj.get("level", ""))
    else:
        effort = str(effort_obj or "")
    effort = effort or state.get("effort", "auto")
    if effort == "auto":
        effort = "high"

    actual_gear = model_gear(model, effort, state.get("gear", "auto"))
    gear_display = actual_gear
    suffixes: list[str] = []
    if state.get("gear") not in ("auto", actual_gear):
        gear_display += "*"
        suffixes.append(f"state={state['gear']}")

    prediction = load_json(gb_dir() / "last_prediction.json", {})
    task = state.get("task", "auto")
    if isinstance(prediction, dict) and prediction.get("task_type"):
        task = str(prediction["task_type"])
        pred_gear = str(prediction.get("gear", ""))
        conf = prediction.get("routing_confidence")
        if pred_gear and pred_gear != actual_gear:
            suffixes.append(f"pred={pred_gear} {float(conf):.0%}" if isinstance(conf, (int, float)) else f"pred={pred_gear}")
    elif task in ("", "auto"):
        task = DEFAULT_TASKS.get(actual_gear, "ejecución")

    prices = load_json(gb_dir() / "prices.json", {})
    key = next((k for k in ("fable", "haiku", "sonnet", "opus") if k in model.lower()), "")
    mult = ""
    try:
        rel = prices.get("models", {}).get(key, {}).get("relative")
        if rel is not None:
            mult = f" · ≈{rel}x"
    except AttributeError:
        pass

    cost = payload.get("cost", {})
    cost_value = cost.get("total_cost_usd") if isinstance(cost, dict) else None
    cost_str = ""
    try:
        if float(cost_value) > 0:
            cost_str = f" · ~${float(cost_value):.2f} est."
    except (TypeError, ValueError):
        pass

    rate_limits = payload.get("rate_limits", {})
    usage_parts: list[str] = []
    seven = None
    five = None
    if isinstance(rate_limits, dict):
        seven_obj = rate_limits.get("seven_day", {})
        five_obj = rate_limits.get("five_hour", {})
        seven = percentage(seven_obj.get("used_percentage")) if isinstance(seven_obj, dict) else None
        five = percentage(five_obj.get("used_percentage")) if isinstance(five_obj, dict) else None
    esc = "\033"
    if seven is not None:
        usage_parts.append(f"{esc}[{ansi_color(seven)}m{bar_for(seven)} {seven}% 7d{esc}[34m")
    if five is not None:
        usage_parts.append(f"{esc}[{ansi_color(five)}m{five}% 5h{esc}[34m")
    usage_str = "".join(f" · {part}" for part in usage_parts)
    if seven is not None and seven >= 80 and actual_gear in ("G4", "G5"):
        suffixes.append(f"⚠ 7d al {seven}% en marcha cara — considera bajar")

    line = f"⚙ {gear_display} · {model} · {effort} · {task}{mult}{cost_str}{usage_str}"
    suffix = " · ".join(suffixes)
    if suffix:
        sys.stdout.write(f"\033[34m{line}\033[0m\033[33m · {suffix}\033[0m")
    else:
        sys.stdout.write(f"\033[34m{line}\033[0m")
    return 0


FEEDBACK_REASONS = (
    "wrong_gear", "wrong_model", "insufficient_depth", "excessive_cost",
    "incorrect_result", "missing_source", "unnecessary_escalation",
    "needed_human_review", "other_local_only",
)
# Verbos aceptados y su traducción al modelo de datos. `wrong-route` es azúcar:
# el resultado fue rechazado porque el ruteo estuvo mal, y cuenta como override.
FEEDBACK_VERBS = {
    "accepted": ("accepted", None, False),
    "rejected": ("rejected", None, False),
    "rework": ("rework", None, False),
    "wrong-route": ("rejected", "wrong_gear", True),
}


def last_task_id() -> str:
    record = load_json(gb_dir() / "last_prediction.json", {})
    return str(record.get("task_id", "")) if isinstance(record, dict) else ""


def cmd_feedback(args: argparse.Namespace) -> int:
    task_id = getattr(args, "task_id", "")
    if task_id in ("last", ""):
        task_id = last_task_id()
        if not task_id:
            print("No hay predicción reciente que calificar.", file=sys.stderr)
            return 1

    verb = getattr(args, "outcome", None)
    rating = getattr(args, "rating", None)
    reason = getattr(args, "reason", None)

    if verb is None and rating is None and reason is None:
        print("Indica un resultado (accepted|rejected|rework|wrong-route), "
              "--rating 1-5 o --reason.", file=sys.stderr)
        return 1

    outcome = override = None
    verb_reason = None
    if verb is not None:
        if verb not in FEEDBACK_VERBS:
            print("Resultado válido: " + ", ".join(FEEDBACK_VERBS), file=sys.stderr)
            return 1
        outcome, verb_reason, override = FEEDBACK_VERBS[verb]

    if reason is not None and reason not in FEEDBACK_REASONS:
        print("Motivo válido: " + ", ".join(FEEDBACK_REASONS), file=sys.stderr)
        return 1
    reason = reason or verb_reason

    if rating is not None and not (1 <= int(rating) <= 5):
        print("El rating va de 1 a 5.", file=sys.stderr)
        return 1

    sets, values = [], []
    if outcome is not None:
        sets += ["outcome=?", "retrabajo=?"]
        values += [outcome, int(outcome == "rework")]
    if reason is not None:
        sets.append("feedback_reason=?")
        values.append(reason)
    if rating is not None:
        sets.append("rating=?")
        values.append(int(rating))
    if override:
        sets.append("human_override=?")
        values.append(1)
    sets.append("updated_at=?")
    values.append(utc_now())
    values.append(task_id)

    try:
        with db_connect() as conn:
            cursor = conn.execute(
                f"UPDATE routing_events SET {', '.join(sets)} WHERE task_id=?", values
            )
            conn.commit()
            if cursor.rowcount == 0:
                print(f"Task ID no encontrado: {task_id}", file=sys.stderr)
                return 1
    except sqlite3.Error as exc:
        print(f"No se pudo registrar feedback: {exc}", file=sys.stderr)
        return 1

    detail = outcome or ("rating " + str(rating) if rating is not None else reason)
    print(f"⚙ Feedback registrado: {task_id} → {detail}")
    if reason == "other_local_only":
        print("   (motivo 'other_local_only' se queda en este equipo: nunca se transmite)")
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    try:
        with db_connect() as conn:
            rows = conn.execute(
                """
                SELECT task_id, created_at, project_id, task_type, gear, model, effort,
                       routing_confidence, predicted_success, outcome
                FROM routing_events ORDER BY created_at DESC LIMIT ?
                """,
                (args.limit,),
            ).fetchall()
    except sqlite3.Error as exc:
        print(f"No se pudo leer el historial: {exc}", file=sys.stderr)
        return 1
    print(json.dumps([dict(row) for row in rows], ensure_ascii=False, indent=2))
    return 0


def cmd_doctor(_: argparse.Namespace) -> int:
    checks: list[tuple[str, bool, str]] = []
    checks.append(("python", sys.version_info >= (3, 9), sys.version.split()[0]))
    ensure_dir(gb_dir())
    state = load_state()
    checks.append(("state.json", state.get("gear") in VALID_GEARS, str(state_path())))
    policy = load_policy()
    checks.append(("policy", policy.get("mode") in ("observe", "advise", "assisted", "autonomous"), str(gb_dir() / "policy.json")))
    try:
        with db_connect() as conn:
            conn.execute("SELECT 1").fetchone()
        db_ok, db_detail = True, str(gb_dir() / "gearbox.db")
    except sqlite3.Error as exc:
        db_ok, db_detail = False, str(exc)
    checks.append(("sqlite", db_ok, db_detail))
    core = gb_dir() / "gearbox.py"
    checks.append(("core", core.exists() or Path(__file__).exists(), str(core)))

    for name, ok, detail in checks:
        print(f"{'✅' if ok else '❌'} {name}: {detail}")
    ok_all = all(ok for _, ok, _ in checks)
    print(f"Gearbox {VERSION}: {'saludable' if ok_all else 'requiere atención'}")
    return 0 if ok_all else 1


# ─────────────────────────────────────────────────────────────────────────────
# Telemetría (voluntaria, revocable, revisable)
# ─────────────────────────────────────────────────────────────────────────────
COMMUNITY_ENABLED_PATH = "community.json"


def community_enabled() -> bool:
    value = load_json(gb_dir() / COMMUNITY_ENABLED_PATH, {})
    return bool(value.get("enabled", True)) if isinstance(value, dict) else True


def endpoint_for(record: dict[str, Any]) -> str:
    env = (os.environ.get("GEARBOX_TELEMETRY_ENDPOINT") or "").strip()
    return env or str(record.get("endpoint") or "")


def _confirm(question: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    if not sys.stdin.isatty():
        print("Se requiere confirmación explícita. Repite con --yes si estás seguro.",
              file=sys.stderr)
        return False
    try:
        answer = input(f"{question} [escribe 'acepto' para continuar]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer == "acepto"


def cmd_telemetry(args: argparse.Namespace) -> int:
    action = args.action
    record = gb_consent.load()

    if action == "explain":
        print(gb_consent.EXPLAIN.format(mode=record["mode"], status=record["status"]))
        return 0

    if action == "status":
        stats = gb_outbox.stats()
        print(json.dumps({
            "mode": record["mode"],
            "consent_status": record["status"],
            "granted_at": record["granted_at"],
            "policy_version": record["policy_version"],
            "schema_version": record["schema_version"],
            "contributor_id": record["contributor_id"],
            "endpoint_configured": bool(endpoint_for(record)),
            "token_present": bool(os.environ.get("GEARBOX_TELEMETRY_TOKEN")),
            "outbox": stats,
            "community_priors": gb_priors.summary(),
            "community_priors_enabled": community_enabled(),
        }, ensure_ascii=False, indent=2))
        return 0

    if action == "enable":
        mode = args.mode
        if mode not in (gb_consent.MODE_COMMUNITY, gb_consent.MODE_SELF_HOSTED):
            print("Modos: community | self-hosted", file=sys.stderr)
            return 1
        if mode == gb_consent.MODE_SELF_HOSTED and not args.endpoint:
            print("self-hosted requiere --endpoint https://...", file=sys.stderr)
            return 1
        if args.endpoint:
            try:
                gb_transport.validate_endpoint(args.endpoint)
            except gb_transport.InsecureEndpoint as exc:
                print(f"Endpoint rechazado: {exc}", file=sys.stderr)
                return 1
        print(gb_consent.EXPLAIN.format(mode=record["mode"], status=record["status"]))
        if not _confirm("¿Activas el envío voluntario de métricas agregadas?", args.yes):
            print("Sin cambios: sigues en modo local.")
            return 1
        updated = gb_consent.grant(mode, source="cli", endpoint=args.endpoint)
        print(f"⚙ Telemetría activada en modo {updated['mode']}. "
              f"Revísala antes de enviar con: telemetry preview")
        return 0

    if action == "consent":
        if record["mode"] == gb_consent.MODE_LOCAL and record["status"] != gb_consent.STATUS_GRANTED:
            print("No hay modo de contribución elegido. Usa: telemetry enable community",
                  file=sys.stderr)
            return 1
        if not _confirm("¿Confirmas el consentimiento para contribuir?", args.yes):
            return 1
        gb_consent.grant(record["mode"], source="cli", endpoint=record.get("endpoint"))
        print("⚙ Consentimiento registrado.")
        return 0

    if action == "disable":
        gb_consent.disable()
        print("⚙ Envíos futuros detenidos. La cola local se conserva "
              "(usa `telemetry purge` para vaciarla o `revoke` para revocar).")
        return 0

    if action == "revoke":
        removed = gb_outbox.purge_all()
        marks = gb_capsule.clear_marks()
        gb_consent.revoke()
        print(json.dumps({
            "revoked": True,
            "queued_capsules_deleted": removed,
            "local_send_marks_cleared": marks,
            "contributor_id": None,
            "receipt": str(gb_consent.receipts_path()),
            "note": ("Si el colector ya recibió cápsulas, solicita su eliminación con el "
                     "contributor_id del comprobante: POST /v1/deletion-requests"),
        }, ensure_ascii=False, indent=2))
        return 0

    if action == "rotate-id":
        try:
            new_id = gb_consent.rotate_id()
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"⚙ Nuevo contributor_id: {new_id}")
        return 0

    if action == "purge":
        removed = gb_outbox.purge_all()
        print(f"⚙ Cola vaciada: {removed} paquetes eliminados.")
        return 0

    if action in ("preview", "export"):
        mode = record["mode"] if record["mode"] != gb_consent.MODE_LOCAL else gb_consent.MODE_COMMUNITY
        built, task_ids = gb_capsule.build(mode, client_version=VERSION)
        if action == "preview":
            print(gb_capsule.preview(built))
            print(f"\nEventos elegibles marcados al enviar: {len(task_ids)}")
            if record["status"] != gb_consent.STATUS_GRANTED:
                print("\n⚠ Vista previa únicamente: no hay consentimiento vigente, "
                      "nada se enviará.")
            return 0
        out = Path(args.out or (gb_dir() / "telemetry-export.json"))
        atomic_write_json(out, built, indent=2)
        print(f"⚙ Cápsula exportada a: {out}")
        return 0

    if action in ("send", "flush"):
        if not gb_consent.is_active():
            print("Sin consentimiento vigente: no se envía nada. "
                  "Usa `telemetry enable community` si deseas participar.", file=sys.stderr)
            return 1
        endpoint = endpoint_for(record)
        if not endpoint:
            print("No hay endpoint configurado (GEARBOX_TELEMETRY_ENDPOINT).", file=sys.stderr)
            return 1

        queued = 0
        if action == "send":
            built, task_ids = gb_capsule.build(record["mode"], client_version=VERSION)
            if not built["events"]:
                print("No hay eventos elegibles (necesitan feedback registrado).")
            else:
                try:
                    gb_outbox.enqueue(built, record["policy_version"])
                    gb_capsule.mark_sent(task_ids, built["capsule_id"])
                    queued = 1
                except gb_privacy.PrivacyViolation as exc:
                    print(f"❌ Bloqueado por el escáner de privacidad: {exc}", file=sys.stderr)
                    return 2
                except (ValueError, gb_outbox.PayloadTooLarge, gb_outbox.OutboxFull) as exc:
                    print(f"❌ No encolado: {exc}", file=sys.stderr)
                    return 2

        results = []
        for entry in gb_outbox.due():
            result = gb_transport.send(
                endpoint, gb_outbox.payload(entry),
                capsule_id=entry["capsule_id"],
                payload_sha256=entry["payload_sha256"],
                contributor_id=str(record.get("contributor_id") or ""),
            )
            if result.ok:
                gb_outbox.mark_sent(entry["capsule_id"])
            else:
                gb_outbox.mark_failed(entry["capsule_id"], result.code)
            results.append({"capsule_id": entry["capsule_id"], "ok": result.ok,
                            "code": result.code, "status": result.status})
        expired = gb_outbox.purge_expired()
        print(json.dumps({"queued": queued, "attempted": len(results),
                          "results": results, "expired_purged": expired},
                         ensure_ascii=False, indent=2))
        return 0 if all(r["ok"] for r in results) or not results else 1

    print(f"Acción desconocida: {action}", file=sys.stderr)
    return 1


def cmd_community(args: argparse.Namespace) -> int:
    action = args.action

    if action == "status":
        print(json.dumps({
            "enabled": community_enabled(),
            **gb_priors.summary(),
        }, ensure_ascii=False, indent=2))
        return 0

    if action == "disable":
        atomic_write_json(gb_dir() / COMMUNITY_ENABLED_PATH, {"enabled": False}, indent=2)
        print("⚙ Priors comunitarios desactivados. Gearbox usará sólo evidencia local.")
        return 0

    if action == "inspect":
        document = load_json(gb_priors.priors_path(), None)
        if not isinstance(document, dict):
            print("No hay priors comunitarios almacenados.", file=sys.stderr)
            return 1
        errors = gb_priors.validate(document, hmac_key=_priors_key())
        print(json.dumps(document, ensure_ascii=False, indent=2))
        print("\nValidación: " + ("✅ íntegro" if not errors else "❌ " + "; ".join(errors)))
        return 0 if not errors else 1

    if action == "update":
        raw = None
        if args.source:
            raw = load_json(Path(args.source), None)
            if raw is None:
                print(f"No pude leer priors desde {args.source}", file=sys.stderr)
                return 1
        else:
            url = args.url or os.environ.get("GEARBOX_PRIORS_URL", "")
            if not url:
                print("Indica --from ARCHIVO o --url https://... "
                      "(o define GEARBOX_PRIORS_URL).", file=sys.stderr)
                return 1
            try:
                gb_transport.validate_endpoint(url)
            except gb_transport.InsecureEndpoint as exc:
                print(f"URL rechazada: {exc}", file=sys.stderr)
                return 1
            import urllib.request

            try:
                request = urllib.request.Request(
                    url, headers={"User-Agent": gb_transport.USER_AGENT, "Accept": "application/json"}
                )
                with urllib.request.urlopen(request, timeout=gb_transport.TIMEOUT_SECONDS) as response:
                    raw = json.loads(response.read(1024 * 1024).decode("utf-8"))
            except Exception as exc:  # noqa: BLE001 — se reporta sin romper la instalación
                print(f"No se pudo descargar: {type(exc).__name__}", file=sys.stderr)
                return 1
        try:
            gb_priors.store(raw, hmac_key=_priors_key())
        except gb_priors.PriorsRejected as exc:
            print(f"❌ Priors rechazados (se conserva el último válido): {exc}", file=sys.stderr)
            return 1
        atomic_write_json(gb_dir() / COMMUNITY_ENABLED_PATH, {"enabled": True}, indent=2)
        print("⚙ Priors comunitarios actualizados y verificados.")
        return 0

    print(f"Acción desconocida: {action}", file=sys.stderr)
    return 1


def _priors_key() -> bytes | None:
    value = (os.environ.get("GEARBOX_PRIORS_HMAC_KEY") or "").strip()
    return value.encode("utf-8") if value else None


def cmd_privacy(args: argparse.Namespace) -> int:
    if args.action == "scrub-local":
        rows = scrub_legacy_identifiers()
        print(f"⚙ Identificadores heredados eliminados de {rows} filas locales.")
        return 0
    if args.action == "scan":
        target = Path(args.path)
        data = load_json(target, None)
        if data is None:
            print(f"No pude leer JSON en {target}", file=sys.stderr)
            return 1
        findings = gb_privacy.scan_object(data)
        for finding in findings:
            print(finding.describe())
        blockers = gb_privacy.blocking(findings)
        print(f"\n{len(findings)} hallazgos · {len(blockers)} bloqueantes")
        return 1 if blockers else 0
    print(f"Acción desconocida: {args.action}", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gearbox V3 predictive loop core")
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("hook").set_defaults(func=cmd_hook)

    p_class = sub.add_parser("classify")
    p_class.add_argument("--prompt")
    p_class.add_argument("--project", default="")
    p_class.add_argument("--session", default="")
    p_class.add_argument("--record", action="store_true")
    p_class.set_defaults(func=cmd_classify)

    p_set = sub.add_parser("set")
    p_set.add_argument("gear")
    p_set.add_argument("task", nargs="?")
    p_set.add_argument("effort", nargs="?")
    p_set.add_argument("model", nargs="?")
    p_set.set_defaults(func=cmd_set)

    sub.add_parser("reset").set_defaults(func=cmd_reset)
    sub.add_parser("statusline").set_defaults(func=cmd_statusline)

    p_log = sub.add_parser("log")
    p_log.add_argument("log_args", nargs=argparse.REMAINDER)
    p_log.set_defaults(func=cmd_log)

    p_feedback = sub.add_parser("feedback")
    p_feedback.add_argument("task_id", nargs="?", default="last",
                            help="task_id o 'last' para la predicción más reciente")
    p_feedback.add_argument("outcome", nargs="?",
                            help="accepted | rejected | rework | wrong-route")
    p_feedback.add_argument("--rating", type=int, help="1 a 5")
    p_feedback.add_argument("--reason", help=" | ".join(FEEDBACK_REASONS))
    p_feedback.set_defaults(func=cmd_feedback)

    p_history = sub.add_parser("history")
    p_history.add_argument("--limit", type=int, default=20)
    p_history.set_defaults(func=cmd_history)

    p_tel = sub.add_parser("telemetry", help="telemetría voluntaria y revocable")
    p_tel.add_argument("action", choices=[
        "status", "explain", "enable", "disable", "consent", "revoke",
        "preview", "export", "send", "flush", "purge", "rotate-id",
    ])
    p_tel.add_argument("mode", nargs="?", help="community | self-hosted (para enable)")
    p_tel.add_argument("--endpoint", help="URL HTTPS del colector (self-hosted)")
    p_tel.add_argument("--out", help="ruta del archivo exportado")
    p_tel.add_argument("--yes", action="store_true",
                       help="confirmación explícita en entornos no interactivos")
    p_tel.set_defaults(func=cmd_telemetry)

    p_com = sub.add_parser("community", help="priors comunitarios agregados")
    p_com.add_argument("action", choices=["status", "update", "inspect", "disable"])
    p_com.add_argument("--from", dest="source", help="archivo local con los priors")
    p_com.add_argument("--url", help="URL HTTPS del documento de priors")
    p_com.set_defaults(func=cmd_community)

    p_priv = sub.add_parser("privacy", help="utilidades de privacidad local")
    p_priv.add_argument("action", choices=["scrub-local", "scan"])
    p_priv.add_argument("path", nargs="?", help="archivo JSON a escanear")
    p_priv.set_defaults(func=cmd_privacy)

    sub.add_parser("doctor").set_defaults(func=cmd_doctor)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
