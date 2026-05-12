# A Comprehensive Guide to `uv`

`uv` is an extremely fast Python package and project manager written in Rust. It aims to replace `pip`, `pip-tools`, `pipx`, `poetry`, `pyenv`, and `virtualenv` with a single, unified tool.

This guide focuses on the default, zero-customization workflow of `uv`. The philosophy here is **minimal customization**: you only create code or modify config files manually when `uv`'s default behaviors cannot handle it. `uv` automates almost all the tedious setup.

Here is exactly what happens under the hood when you run the core `uv` commands in practice.

---

## 1. Project Initialization: `uv init`

Instead of manually creating folders, environments, and configuration files, you use `uv init`.

**The Command:**
```bash
uv init --name alphavi .
```

**What it actually does automatically:**
It immediately sets up a modern Python project structure in the current directory without asking any questions.

- **`pyproject.toml` is created:** It generates the modern standard configuration file with your project name, version, and dependencies list. No manual editing required.
- **`.python-version` is created:** It writes a tiny file (e.g., containing `3.14`) that locks the project to your currently active or latest Python version.
- **`main.py` is created:** It generates a boilerplate entry point script so you can immediately start running code.
- *(It does not yet download any dependencies or create heavy virtual environment folders).*

**Manual Customization Note:** Because we ran the basic `uv init` (instead of `uv init --package` or `uv init --app`), `uv` created a "flat" layout suitable for a simple script. To make this a publishable package, we **manually** had to:
1. Move our code into a `src/alphavi/` directory.
2. Manually add `[build-system]` and `[project.scripts]` to `pyproject.toml`.
*(Tip: In the future, running `uv init --package` automates even these steps!)*

---

## 2. Dependency Management: `uv add`

Instead of running `python -m venv .venv`, activating it, running `pip install flask`, and then running `pip freeze > requirements.txt` manually, `uv add` does it all in one step.

**The Command:**
```bash
uv add flask yt-dlp
```

**What it actually does automatically:**
1. **Creates a Virtual Environment:** It detects that `.venv` does not exist and automatically creates a fully isolated `.venv` folder in your project directory.
2. **Downloads and Links Packages:** It fetches `flask` and `yt-dlp` (and all their dependencies, like `werkzeug` and `jinja2`). Instead of storing massive copies of these libraries, it heavily utilizes hard links to a global cache, making installation almost instantaneous and saving disk space.
3. **Updates Configuration:** It automatically rewrites your `pyproject.toml` to include these new dependencies. **You do not need to edit `pyproject.toml` manually.**
4. **Creates `uv.lock`:** It generates a massive, strict lockfile (`uv.lock`) ensuring that every single sub-dependency is pinned to an exact cryptographic hash. This guarantees the project will run identically on any other machine.

---

## 3. Running Code: `uv run`

In standard Python workflows, running a script with a `src/` layout often fails with `ModuleNotFoundError` unless you manually "activate" your environment and install the package first. `uv` eliminates this entirely.

**The Command:**
```bash
uv run main.py
```

**What it actually does automatically:**
1. **Automatic Synchronization:** If you just cloned this project on a new computer, `uv run` automatically checks the `uv.lock` file. If the `.venv` is missing or out of date, it instantly downloads the correct Python version, creates the `.venv`, and installs all locked dependencies. You never have to run a separate "install" command first!
2. **Editable Installs for `src/` Layouts:** Because you have a `pyproject.toml` that defines a package, `uv` invisibly installs your project into the `.venv` in **"editable mode"**. This creates a link telling Python: *"Whenever someone imports `alphavi`, look inside the `src/alphavi` folder."* This is why your root `main.py` can successfully import from `src/` without errors.
3. **Environment Activation:** It invisibly and temporarily "activates" the isolated environment in the background.
4. **Execution:** It executes `main.py` securely within that environment. Your global system Python remains completely untouched.

**Idiomatic Module Execution (`__main__.py`)**
If your package is structured idiomatically with a `__main__.py` file (e.g., `src/alphavi/__main__.py`), `uv` natively supports executing the directory as a standard Python module. You can bypass standalone entry point scripts entirely and run:
```bash
uv run python -m alphavi
```
Because of the automatic editable install mentioned above, `uv run` seamlessly passes the command to Python, which natively locates and executes your package's `__main__.py` module.

---

## 4. Running Utilities: `uvx`

What if you want to run a tool like `ruff` (a code linter) or `httpie` (an API tester), but you **don't** want to add them to your `pyproject.toml` because they aren't required for the app itself?

**The Command:**
```bash
uvx ruff check
```

**What it actually does automatically:**
1. It creates a hidden, temporary virtual environment in the background.
2. It installs `ruff` into that temporary space.
3. It executes the `ruff check` command against your code.
4. It cleans up or isolates the environment, leaving your project dependencies and global system perfectly clean.

---

## 5. Automatic Dependency Inference

While `uv` requires explicit dependency declarations, you can easily replicate the behavior of tools like `pipreqs` without globally installing them or manually managing virtual environments.

**The Workflow:**
```bash
uvx pipreqs . --force
uv add -r requirements.txt
rm requirements.txt
```

**What it actually does automatically:**
1. **`uvx pipreqs . --force`**: Invisibly downloads `pipreqs` into a temporary space, scans your project code (e.g., `src/`) to find all third-party imports, generates a `requirements.txt` file, and cleans up the temporary environment.
2. **`uv add -r requirements.txt`**: Reads the generated list of discovered dependencies, resolves their exact versions, and officially registers them into your `pyproject.toml` and `uv.lock`.
3. **`rm requirements.txt`**: Deletes the temporary file, as your project is now natively managed by `uv`.

*(Note: If `pipreqs` includes OS-incompatible packages like `xattr` that fail to build on Windows, simply remove them from `requirements.txt` before running `uv add`).*

---

## 6. Building and Packaging: `uv build`

When you want to publish your project so others can install it, you need to build it. Best practice dictates using a `src/` layout (e.g., `src/alphavi/`), which prevents module import errors and ensures clean packaging. `uv` perfectly supports standard modern packaging out of the box.

**The Command:**
```bash
uv build
```

**What it actually does automatically:**
1. It reads the `[build-system]` defined in your `pyproject.toml` (by default, tools like `hatchling`).
2. It invisibly creates an isolated, temporary build environment, downloading the necessary build tools without polluting your project's main `.venv`.
3. It packages your code from the `src/` directory into standard distribution formats: a Source Distribution (`.tar.gz`) and a Binary Wheel (`.whl`).
4. It places these final, publishable artifacts into a automatically created `dist/` folder.

---

## 7. Disambiguation and Etymology: `uv`, `uvx`, `libuv`, and `uvw`

With all these short acronyms, it is easy to get confused. Here is exactly what each tool is, what the name stands for, and where it originated:

- **`libuv`**: A high-performance, asynchronous I/O library written in C that powers Node.js. It handles event loops, file system notifications, and networking.
  - **Name Origin**: The name originally had no specific meaning. However, because developers constantly asked what "uv" stood for, the creators playfully made up the backronym **"Unicorn Velociraptor"**, which even became the project's official mascot!

- **`uvw` (C++ Library)**: A modern, header-only C++ (C++17 or later) wrapper for `libuv`.
  - **Name Origin**: It stands simply for **"uv wrapper"**. It makes working with the low-level `libuv` C library much more idiomatic for C++ developers.

- **`uv` (Python Tool)**: The lightning-fast Python package and project manager by Astral that this guide covers.
  - **Name Origin**: The name fits Astral's celestial/space branding, evoking **Ultraviolet** (light beyond the visible spectrum) or **Universal** (referring to their goal of a universal lockfile). It was primarily chosen because it is incredibly short and fast to type. **Note: Despite the naming similarity, it has no direct relation to the `libuv` C library.**

- **`uvx` (Python Tool Runner)**: The command used alongside `uv` to temporarily execute standalone Python utilities.
  - **Name Origin**: The **"x"** stands for **"execute"** or **"executable"**. It follows the exact same naming convention as JavaScript's `npx` (Node Package Execute) or Python's `pipx`, appending an "x" to the base package manager (`uv`).

### Which one do you need?
- If you are managing Python dependencies, environments, or running Python scripts: **Stick with `uv` and `uvx`**.
- If you are writing low-level C++ programs and need an event-driven, non-blocking I/O loop: **Use `uvw`**. It is a fantastic library for high-concurrency networking or systems programming, but it won't help you install Python packages!

---

## Summary of the "Minimal Customization" Philosophy

- **Never create a `.venv` manually.** Let `uv` do it automatically when you run a command.
- **Never edit `requirements.txt` or manually edit `pyproject.toml` dependencies.** Use `uv add <package>` or `uv remove <package>`.
- **Never manually activate environments.** Just prefix your commands with `uv run`.
- **Never install utilities globally.** Use `uvx <tool>` to run them in temporary isolation.