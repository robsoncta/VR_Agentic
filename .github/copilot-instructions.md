# Copilot Instructions for VR_Agentic

## Project Overview
This project automates the monthly calculation and purchase of VR/VA (Vale Refeição/Vale Alimentação) for employees, consolidating multiple Excel sources and applying complex business rules. The main output is a single consolidated CSV/Excel file for supplier use.

## Architecture & Data Flow
- **Data Sources:** All input files are in `data/` (e.g., `ATIVOS.xlsx`, `DESLIGADOS.xlsx`, etc.).
- **Core Logic:**
  - `vr_agent/agent.py`: Main entry point, orchestrates loading, consolidation, and output.
  - `vr_agent/rules.py`: Implements normalization, sanitization, and consolidation rules (`compute_layout`, `validate`).
  - `vr_agent/io_utils.py`: Handles reading/writing Excel files.
- **Output:** Final file is saved to `data/output/consolidado.csv` or `.xlsx`.

## Key Patterns & Conventions
- **DataFrame-centric:** All transformations use Pandas DataFrames. Column names are normalized to uppercase and stripped of whitespace.
- **Business Rules:** See `agent.py` and `rules.py` for detailed consolidation logic (e.g., exclusions, proportional calculations for admissions/dismissals, VR value by union/state).
- **Logging:** Uses Python `logging` for progress and error reporting. Prefer `logger.info`/`logger.warning` over print.
- **Environment:**
  - Requires `.env` file for API keys and config (see `README.md`).
  - External dependencies: `google-adk`, `agentops`, `langfuse`, `pandas`, `openpyxl`.

## Developer Workflows
- **Setup:**
  - Create and activate a Python 3.10+ virtual environment.
  - Install dependencies: `pip install -r requirements.txt`
  - Add `.env` file with required keys.
- **Run (CLI):**
  - Main agent logic is invoked via FastAPI (`uvicorn app.main:app --reload`) or ADK Web (`adk web --port 8000`).
- **Debug/Test:**
  - Use logging output for debugging.
  - Validate output structure with `validate()` from `rules.py`.

## Integration Points
- **Google ADK:** Used for agent orchestration (`Agent` class in `agent.py`).
- **ADK Web:** Optional web interface for agent interaction.

## Examples
- To add a new business rule, update `compute_layout` in `rules.py` and ensure it is reflected in the agent's instruction string in `agent.py`.
- To support a new input file, add its loader in `load_bases()` in `agent.py` and update the consolidation logic.

## References
- See `README.md` and `readme.txt` for setup, environment, and workflow details.
- Key files: `vr_agent/agent.py`, `vr_agent/rules.py`, `vr_agent/io_utils.py`, `requirements.txt`, `data/`

---
If any conventions or workflows are unclear, please ask for clarification or provide feedback to improve these instructions.
