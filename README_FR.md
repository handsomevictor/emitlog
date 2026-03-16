# emitlog

Logging structuré pour les microservices Python asyncio. Typé statiquement, zéro dépendance, prêt à l'emploi.

[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/downloads/)
[![mypy: strict](https://img.shields.io/badge/mypy-strict-brightgreen.svg)](https://mypy.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Zero dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)]()

```
10:23:45.123  INFO  api  user_login  user_id=42  ip=192.168.1.1  │  request_id=req-abc  service=api
```

[English →](README.md) | [中文文档 →](README_CN.md)

---

## Pourquoi emitlog ?

La plupart des bibliothèques de logging Python ont été conçues pour du code synchrone. Dès qu'on les utilise dans des microservices asyncio, on se heurte aux mêmes problèmes : les schémas de logs ne sont que des chaînes de caractères (un rename passe inaperçu jusqu'en prod), le `request_id` disparaît en traversant les frontières de coroutines car `threading.local` ne fonctionne pas là, et mypy ne peut rien vérifier puisque chaque appel `logger.info()` accepte `Any`.

emitlog traite les événements de log comme des dataclasses typées. Les champs sont déclarés statiquement, vérifiés par mypy et auto-complétés par l'IDE. La propagation de contexte repose sur `contextvars` — elle fonctionne correctement entre coroutines, y compris dans `asyncio.gather`, sans configuration particulière.

---

## Comparaison

| | stdlib logging | loguru | structlog | emitlog |
|---|---|---|---|---|
| Sortie structurée / JSON | ⚠️ via handler | ✅ | ✅ | ✅ |
| Schéma typé pour les événements | ❌ | ❌ | ❌ | ✅ |
| Compatible mypy `--strict` | ❌ | ❌ | ⚠️ partiel | ✅ |
| `await emit()` natif asyncio | ❌ | ❌ | ❌ | ✅ |
| Propagation via `contextvars` | ❌ | ❌ | ⚠️ manuel | ✅ intégré |
| Isolation de contexte dans `gather` | ❌ | ❌ | ❌ | ✅ automatique |
| Couleurs par champ dans le terminal | ❌ | ❌ | ❌ | ✅ |
| Couleurs selon plage de valeurs | ❌ | ❌ | ❌ | ✅ |
| Coloration inline par segment | ❌ | ❌ | ❌ | ✅ |
| Sampling intégré | ❌ | ❌ | ⚠️ plugin | ✅ |
| Sampling déterministe par entité | ❌ | ❌ | ❌ | ✅ |
| Zéro dépendance obligatoire | ✅ | ✅ | ❌ | ✅ |

loguru est excellent pour les scripts synchrones. Le pipeline de processeurs de structlog est très flexible. Aucun des deux ne propose de propagation de contexte asyncio native — c'est précisément ce que comble emitlog.

---

## Installation

```bash
pip install emitlog

# Optionnel : sérialisation JSON 3 à 5× plus rapide
pip install emitlog[fast]

# Optionnel : rendu terminal via rich
pip install emitlog[dev]
```

Python 3.13+ requis.

---

## Démarrage rapide

```python
import asyncio
import emitlog
from emitlog import event

@event(level="info")
class UserLogin:
    user_id: int
    ip: str

log = emitlog.get_logger(__name__)

async def main():
    await log.emit(UserLogin(user_id=42, ip="1.2.3.4"))

asyncio.run(main())
# Terminal (tty) :
# 10:23:45.123  INFO  __main__  user_login  user_id=42  ip=1.2.3.4
#
# Production / non-tty (JSON) :
# {"timestamp":"2024-01-15T10:23:45.123Z","level":"info","logger_name":"__main__","event_name":"user_login","user_id":42,"ip":"1.2.3.4"}
```

Aucune configuration nécessaire. emitlog détecte automatiquement le tty et choisit entre Pretty et JSON.

---

## Utilisation

### Événements typés

```python
from emitlog import event, field

@event(level="info")
class OrderCreated:
    order_id: str
    amount: float
    status: str = "pending"   # les valeurs par défaut fonctionnent normalement

@event(level="warning")
class RateLimitExceeded:
    user_id: int
    requests_per_minute: int

# C'est un dataclass ordinaire — dataclasses.asdict() etc. fonctionnent
await log.emit(OrderCreated(order_id="ord-123", amount=99.99))
```

Renommez un champ : toutes les utilisations cassent à la compilation mypy, pas à 3h du matin.

### Propagation de contexte

```python
async def handle_request(request_id: str):
    async with log.context(request_id=request_id, service="api"):
        await log.emit(UserLogin(user_id=1, ip="x"))
        # → contexte : {"request_id": "...", "service": "api"}

        async with log.context(service="db"):
            await log.emit(...)
            # → contexte : {"request_id": "...", "service": "db"}

        # le service "api" est automatiquement restauré ici

# Fonctionne correctement avec gather — pas de contamination croisée
await asyncio.gather(handle_request("req-1"), handle_request("req-2"))
```

Version synchrone :

```python
with log.context(job_id="batch-001"):
    log.emit_sync(OrderCreated(order_id="x", amount=0.0))
```

### Couleurs dans le terminal (3 couches)

**Couche 1 — couleur statique par champ**

```python
@event(level="info")
class OrderCreated:
    order_id: str  = field(color="cyan")
    amount:   float = field(color="bold green")
    status:   str  = field(color="yellow")
```

**Couche 2 — couleur selon la plage de valeurs**

```python
@event(level="info")
class HttpRequest:
    status_code: int = field(
        color_map=[
            (range(200, 300), "bold green"),
            (range(400, 500), "bold yellow"),
            (range(500, 600), "bold red"),
        ]
    )
    duration_ms: float = field(
        color_map=[
            (range(0,   100),   "green"),
            (range(100, 500),   "yellow"),
            (range(500, 99999), "bold red"),
        ]
    )
```

**Couche 3 — segments inline**

```python
from emitlog import colored, markup

msg = colored("SUCCESS", "bold green") + " déployé sur " + colored("prod", "bold red")
msg = markup("[bold green]SUCCESS[/bold green] déployé sur [bold red]prod[/bold red]")

# En JSON : texte brut, sans codes ANSI
```

### Sampling

```python
# Aléatoire à 1% — décision prise avant la sérialisation
@event(level="info", sample_rate=0.01)
class HealthCheckCalled:
    pass

# Déterministe par utilisateur — même user_id → même décision à chaque fois
@event(level="info", sample_rate=0.1, sample_by="user_id")
class ApiCalled:
    user_id: int
    endpoint: str
```

`sample_rate=1.0` (valeur par défaut) court-circuite entièrement le code de sampling — aucun surcoût.

### Configuration

```python
from emitlog.sinks import Stderr, AsyncFile
from emitlog.formatters import PrettyFormatter, ColorScheme, LevelColors

emitlog.configure(
    sinks=[
        Stderr(formatter=PrettyFormatter(
            colors=ColorScheme(
                levels=LevelColors(info="bold blue", error="bold white on red"),
                event_name="bold yellow",
            ),
        )),
        AsyncFile("app.log"),   # écriture asynchrone en arrière-plan
    ],
    level="info",
    capture_stdlib=True,   # intercepte les appels logging.getLogger() existants
)
```

Sélection automatique du formatter si aucun n'est spécifié :

| Sink | Condition | Formatter |
|---|---|---|
| `Stderr` | tty ou `EMITLOG_DEV=1` | `PrettyFormatter` |
| `Stderr` | sinon | `JsonFormatter` |
| `File` / `AsyncFile` | toujours | `JsonFormatter` |

Désactiver les couleurs (par ordre de priorité décroissant) :

```bash
NO_COLOR=1            # https://no-color.org
EMITLOG_NO_COLOR=1
# ou : PrettyFormatter(colorize=False)
```

### Sinks et formatters personnalisés

```python
from emitlog.sinks import BaseSink
from emitlog._record import LogRecord

class DatadogSink(BaseSink):
    async def write(self, record: LogRecord) -> None:
        payload = self._serialize(record)   # chaîne JSON fournie par BaseSink
        await send_to_datadog(payload)

    async def close(self) -> None:
        pass
```

```python
from emitlog.formatters import BaseFormatter

class CompactFormatter(BaseFormatter):
    def format(self, record: LogRecord) -> str:
        return f"{record.level.upper()} {record.event_name}"
```

### Compatibilité stdlib

```python
emitlog.configure(sinks=[...], capture_stdlib=True)

import logging
logging.getLogger("sqlalchemy").warning("requête lente")
# → event_name="stdlib_log", fields={"message": "requête lente", "logger": "sqlalchemy"}
```

---

## Structure de LogRecord

```python
@dataclass(frozen=True)
class LogRecord:
    timestamp:   str              # "2024-01-15T10:23:45.123Z"
    level:       str              # "debug" | "info" | "warning" | "error" | "critical"
    logger_name: str
    event_name:  str              # nom de classe → snake_case : UserLogin → "user_login"
    fields:      dict[str, Any]  # champs de l'événement, Span/SpanList en texte brut (JSON)
    raw_fields:  dict[str, Any]  # valeurs originales, Span/SpanList préservés (PrettyFormatter)
    context:     dict[str, Any]
```

Ordre des clés JSON : `timestamp → level → logger_name → event_name → **fields → **context`

---

## Référence des couleurs

```
Couleurs de base :  black  red  green  yellow  blue  magenta  cyan  white
Couleurs vives :    bright_black  bright_red  bright_green  ...  bright_white
Modificateurs :     bold  dim  italic  underline
Arrière-plan :      on black  on red  on green  ...  on white
Combinaisons :      "bold red"   "dim cyan"   "bold white on red"
```

---

## Exemples

```bash
uv run python examples/01_quickstart.py
uv run python examples/02_schema_events.py
uv run python examples/03_context.py
uv run python examples/04_sampling.py
uv run python examples/06_fastapi_integration.py
uv run python examples/08_colors_and_formatting.py
```

---

## Documentation

- [TUTORIAL.md](docs/TUTORIAL.md) — guide complet des fonctionnalités (en anglais)
- [TESTING.md](docs/TESTING.md) — lancer les tests en local
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — référence d'architecture (pour les contributeurs)

---

## Contribuer

```bash
git clone https://github.com/handsomevictor/emitlog
cd emitlog
uv sync --extra dev

uv run pytest tests/ -v
uv run mypy emitlog --strict
```

---

Licence MIT
