# agent_adk_matias_silvera — Asistente de gastos personales

Agente de IA construido con **Python** y **Google Agent Development Kit (ADK)** que ayuda a llevar el control de gastos personales. No es un chatbot que solo genera texto: el agente interpreta el pedido del usuario, **decide qué herramienta usar**, la ejecuta contra una base de datos SQLite y arma la respuesta a partir del resultado real.

- **Framework:** Google ADK
- **Modelo:** `gpt-oss:120b-cloud` servido por Ollama, integrado a ADK mediante **LiteLLM** (`ollama_chat/gpt-oss:120b-cloud`)
- **Persistencia:** SQLite (`gastos.db`, se crea sola al primer uso)
- **Idioma del agente:** español

## Instrucciones del agente

Definidas en `gastos_agent/agent.py`:

- **Rol:** asistente de finanzas personales.
- **Objetivo:** registrar, consultar, resumir y eliminar gastos usando siempre las herramientas (nunca inventa datos).
- **Restricciones:** no da asesoramiento financiero/de inversión; no adivina montos ni ids; pide confirmación antes de eliminar; rechaza temas ajenos a la gestión de gastos.
- **Comportamiento:** pide los datos que faltan, convierte fechas relativas ("ayer", "este mes") a `AAAA-MM-DD`, explica los errores en lenguaje simple y avisa cuando un resultado viene vacío.

## Herramientas

| Herramienta | Responsabilidad | Validaciones |
|---|---|---|
| `registrar_gasto(monto, categoria, descripcion, fecha=None)` | **Escritura:** guarda un gasto nuevo | monto numérico y > 0 (rechaza texto, NaN, negativos), categoría no vacía, fecha `AAAA-MM-DD` y no futura |
| `listar_gastos(categoria=None, desde=None, hasta=None, limite=20)` | **Consulta:** devuelve gastos con filtros | fechas válidas, `desde <= hasta`, límite 1–100; si no hay resultados devuelve lista vacía con mensaje |
| `resumen_gastos(desde=None, hasta=None)` | **Agregación:** total, desglose por categoría y categoría con más gasto | fechas válidas y rango coherente; sin datos devuelve total 0 con mensaje |
| `eliminar_gasto(id_gasto)` | **Borrado:** elimina un gasto por id | id entero positivo; id inexistente devuelve error controlado |

Todas devuelven `{"status": "success" | "error", ...}`, de modo que el agente puede detectar fallos y explicárselos al usuario.

## Estructura

```
agent_adk_matias_silvera/
├── gastos_agent/
│   ├── __init__.py
│   ├── agent.py         # definición del agente (modelo, instrucciones, tools)
│   ├── tools.py         # las 4 herramientas con su validación
│   ├── db.py            # conexión y esquema SQLite
│   └── .env.example     # variables de entorno
├── tests/test_tools.py  # pruebas unitarias (pytest)
├── requirements.txt
└── README.md
```

## Requisitos

- Python 3.10+ (probado con 3.13)
- [Ollama](https://ollama.com) instalado y en ejecución
- Cuenta de Ollama para usar modelos cloud

## Instalación

```bash
git clone https://github.com/<usuario>/agent_adk_matias_silvera.git
cd agent_adk_matias_silvera

python -m venv .venv
source .venv/bin/activate            # en Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Modelo (una sola vez)
ollama signin
ollama pull gpt-oss:120b-cloud

# Configuración
cp gastos_agent/.env.example gastos_agent/.env
```

## Uso

### Interfaz web de ADK

Desde la **raíz del repositorio**:

```bash
adk web
```

Abrir http://localhost:8000, elegir **`gastos_agent`** en el selector de la izquierda y chatear. En la pestaña de eventos se ve cada llamada a herramienta (argumentos y respuesta). Si el puerto 8000 está ocupado: `adk web --port 8765`.

### Terminal

```bash
adk run gastos_agent
```

### Ejemplos de prompts

| Prompt | Herramienta que elige el agente |
|---|---|
| "Gasté 3500 en comida, almuerzo con amigos" | `registrar_gasto` |
| "Gasté 1200 en transporte ayer" | `registrar_gasto` (fecha de ayer) |
| "¿Qué gasté en comida este mes?" | `listar_gastos` (con filtros) |
| "¿Cuánto gasté en total y por categoría?" | `resumen_gastos` |
| "Borrá el gasto 2" | `listar_gastos` → confirmación → `eliminar_gasto` |

### Manejo de errores y casos límite

| Prompt | Resultado |
|---|---|
| "Gasté -50 en ocio" | el agente rechaza el monto y pide uno válido |
| "Borrá el gasto 99" | informa que no existe ese id |
| "Mostrame mis gastos de salud" (sin datos) | informa que no hay gastos de esa categoría |
| "Gasté 100 en comida el 31/02" | informa que la fecha es inválida y pide `AAAA-MM-DD` |

## Tests

```bash
python -m pytest
```

Cubren casos válidos, argumentos inválidos (montos, fechas, ids, límites) y resultados vacíos. Usan una base de datos temporal (variable `GASTOS_DB`), no tocan `gastos.db`.

## Autor

Matías Silvera
