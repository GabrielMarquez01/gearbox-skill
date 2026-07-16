# Referencias de README — repos top de herramientas de IA/CLI

> Investigación de patrones de presentación para la portada del repo `gearbox-skill`.
> Actualizado: 2026-07-15 22:56

## Repos estudiados

| Repo | Tipo | Por qué es referencia |
|---|---|---|
| [openai/codex](https://github.com/openai/codex) | CLI de agente de IA | Herramienta oficial de OpenAI, README minimalista orientado a acción |
| [google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli) | CLI de agente de IA | Herramienta oficial de Google, README con badges de CI y docs segmentadas |
| [sst/opencode](https://github.com/sst/opencode) | Agente de código open-source | Logo adaptativo a tema, badges honestos (npm, build, Discord) |
| [Aider-AI/aider](https://github.com/Aider-AI/aider) | Par-programación con IA | Badges con métricas reales, bloques de features, prueba social |
| [All-Hands-AI/OpenHands](https://github.com/All-Hands-AI/OpenHands) | Plataforma de agentes | Badge de estado ("beta") honesto, navegación por anclas, diagrama de arquitectura |

## Patrones compartidos (los que aplicamos)

### 1. Apertura: identidad visual + tagline en ≤5 segundos
- Todos abren con logo o banner centrado (`<div align="center">` / `<p align="center">`).
- Tagline de UNA línea inmediatamente después ("The open source AI coding agent" — opencode;
  "AI Pair Programming in Your Terminal" — aider).
- opencode usa `<picture>` con `prefers-color-scheme` para logo claro/oscuro (opcional, nice-to-have).

### 2. Badges: pocos, verdaderos, arriba
- gemini-cli: CI, versión, licencia, docs. opencode: Discord, npm, build. OpenHands: estado
  ("beta"), CI, versión, docs, comunidad.
- Patrón clave de OpenHands: **badge de estado honesto** — declarar "beta"/"experimental"
  en vez de aparentar madurez.
- Formato estándar: `https://img.shields.io/badge/...` con `style=flat-square` o `for-the-badge`.
- Ninguno inventa números: aider muestra estrellas/descargas porque son reales y automáticas
  (shields.io las calcula), no hardcodeadas.

### 3. Quick Start arriba, con rutas múltiples
- codex: la instalación ES la narrativa principal, con variantes por plataforma.
- gemini-cli y opencode: instalación inmediatamente después del banner, varios package managers.
- OpenHands: tres rutas (sin sandbox, Docker, desde fuente) con prerequisitos marcados.
- Lección: el lector decide en 30 segundos si puede probarlo; el detalle vive en docs enlazadas.

### 4. Navegación: anclas > tabla de contenidos formal
- Ninguno de los 5 usa un TOC clásico; usan barra de anclas (`<a href="#quickstart">` — OpenHands)
  o secciones con emoji-prefijo escaneables (gemini-cli).
- Docs largas se sacan del README y se enlazan segmentadas por categoría (gemini-cli: 20+ links
  agrupados en Getting Started / Core / Advanced / Troubleshooting).

### 5. Tablas para comparar, código para ejecutar
- OpenHands: tabla de 6 capacidades con links a docs. opencode: tabla de descargas por plataforma.
- Bloques de código con lenguaje declarado (```bash) en todos.

### 6. Colapsables para domar longitud
- codex: `<details>` para binarios por plataforma — la única info larga que no cabe en el flujo.
- Patrón: lo que el 80% no necesita leer, va colapsado (FAQ, matrices, variantes).

### 7. Diagramas donde hay arquitectura
- OpenHands incluye diagrama de arquitectura embebido. Los CLI simples (codex, gemini-cli) no
  lo necesitan. Lección: diagrama solo si el sistema tiene partes móviles — Gearbox EV6 las tiene
  (coordinador/ejecutor/auditor/motores), y GitHub renderiza mermaid nativo.

### 8. Cierre: contribuir + comunidad + licencia
- gemini-cli: link a CONTRIBUTING.md + footer con crédito ("Built with ❤️ by...").
- opencode: CTAs de comunidad (Discord/X) al final.
- Licencia clara al pie (Apache-2.0 en codex, referencias en gemini-cli).
- Callouts `> [!WARNING]` / `> [!NOTE]` nativos de GitHub para avisos (OpenHands).

## Anti-patrones observados (lo que evitamos)

- Muros de texto sin jerarquía (ninguno de los 5 los tiene; los READMEs malos sí).
- Badges decorativos falsos o métricas hardcodeadas.
- Prometer instalación de una línea que no está verificada.
- Duplicar la documentación técnica completa dentro del README en vez de enlazarla.

## Decisiones aplicadas al README de gearbox-skill

1. Banner EV6 arriba + tagline de una línea + 3 párrafos de contexto.
2. Badges verdaderos: Licencia MIT (existe en `LICENSE`), estado "experimental — en calibración"
   (honesto, patrón OpenHands), doc técnica, PRs bienvenidos.
3. Quick Start por capas: mono-motor (Claude Code, comando ya publicado en el repo) y
   multi-motor opcional (solo comandos verificados del doc EV6 §3.10).
4. Diagrama mermaid del organigrama de puestos (renderiza nativo en GitHub).
5. `<details>` para FAQ y comparativa de motores.
6. Índice con enlaces al doc técnico completo y sus secciones.
7. Sección de contribución centrada en replicar y reportar resultados (doc EV6 §10).
8. Footer con lema, crédito multi-motor y licencia.
