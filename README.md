# Elite Editor 🎞️

**ELITE EDITOR** is a professional desktop video editor built with Python, PySide6 (Qt Widgets), and MoviePy. It aims to provide a real, production-grade editing experience with a modern UI, signature-driven effect controls, real drag-and-drop, integrated preview and render pipelines, and AI-assisted features. **Status:** ⚙️ *Active development (dev)*

---

## Highlights ✨

- Real MoviePy-based effects and composition (no placeholders) 🎛️
- QGraphicsView-based timeline with draggable/resizable clips and snapping ✂️
- Signature-driven **Properties Panel** that auto-generates controls from MoviePy callables 🧩
- Low-res preview renderer (fast iterations) + subprocess renderer for full exports ⏱️
- Theming and persistent project format (.eep) for portability 💾
- Planned & partial AI integration using Gemini for timeline insights and generation 🧠

---

## Quick Start (Windows) 🚀

Prerequisites:

- Python 3.11+ (recommended)
- FFmpeg (installed and discoverable via PATH)

Clone the repo and prepare a Python virtual environment:

```powershell
git clone https://github.com/pro-grammer-SD/EliteEditor.git
cd EliteEditor
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Run the app:

```powershell
python run.py
```

If you see a splash and a window, the app is running — welcome! 🎉

---

## Development (for devs) 🛠️

This project is actively in development. Follow these steps to contribute or run locally:

1. Create a virtual environment and install dependencies (see Quick Start).
2. Use a code formatter and linter before committing (e.g. `black`, `ruff`).
3. Run the application from the repository root using `python run.py`.
4. Unit tests (when available):

```powershell
# Example (if tests exist)
pytest -q
```

Dev notes:

- Config, cache, and projects are stored under your user folder (e.g. `%USERPROFILE%/.eliteeditor/`).
- The bundled font is located at `font/font.ttf` and the app attempts to load it at startup.
- The main application entrypoint is `run.py`.

---

## Architecture & Key Files 🗂️

- `core/` — core data models, project & registry systems (MoviePy reflection, timeline markers)
- `ui/` — all Qt widgets (timeline view, panels, main window, style files)
- `rendering/` — preview & subprocess renderers
- `ai/` — Gemini integration scaffolding and AI helpers
- `timeline/` — timeline & clip models used by the UI
- `requirements.txt` — pinned Python dependencies

---

## Configuration & AI Key 🔑

- The app reads configuration from the project-specific files and a global config under `~/.eliteeditor`.
- To enable Gemini AI features, set an environment variable named `ELITE_EDITOR_GEMINI_API_KEY` or enter your key in the **Settings → AI** panel at runtime.

> Note: Gemini integration requires the official client and an enabled API key — the app will gracefully disable AI features if no key is present.

---

## Styling & Fonts 🎨

- The UI styling is loaded exclusively from `ui/style.qss` (or `ui/style_light.qss` for light theme). The stylesheet should be the single source of truth for look-and-feel.
- The bundled font is at `font/font.ttf`. The app attempts to load this font at startup; if it fails it falls back to the system default.

---

## Contributing ✍️

We welcome PRs and issues. Please follow these guidelines for contributions:

1. Open an issue describing the bug, enhancement, or feature idea.
2. Create a topic branch off `main` named like `feat/some-feature` or `fix/issue-xyz`.
3. Write tests for new behavior when applicable; keep changes focused.
4. Run linters and formatters, then open a PR and reference the issue.

Be civil and constructive — we prefer clear, respectful communication. 🤝

---

## Troubleshooting & Tips 🛟

- If the custom font doesn't appear, check the logs for font loading messages and confirm `font/font.ttf` exists.
- If styles appear missing, ensure `ui/style.qss` is present and readable; the app reads the QSS file at startup and applies it globally.
- For render/export issues, verify FFmpeg is installed and reachable via PATH.

---

## License & Code of Conduct 📜

This repository uses an open-source license (update as needed). Please include a short `LICENSE` file in the root.

We expect contributors to follow a respectful Code of Conduct.

---

## Contact & Support 📬

If you need help or want to request features, please open an issue on this repository. For quick dev questions, add a note to the issue and tag maintainers.

Thanks for checking out Elite Editor — contributions are welcome and appreciated! 🙏
