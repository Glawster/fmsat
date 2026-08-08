# Additional Agent Instructions for organiseMyProjects

## Project-Specific Information

This file contains project-specific details for the **organiseMyProjects** repository. The master development guidelines live in `.github/agent-instructions.md` and take precedence over any conflicting guidance here or elsewhere in the repository. User-facing documentation begins in the root `README.md`, and developer documentation is in `documentation/developer.md`. The README must include a near-top Documentation section that links to every living guide in the repo so it remains the canonical entry point for all docs.

## Installation

```bash
pip install .
```

## Usage

### Create a new project
```bash
createProject myNewProject
```

### Update an existing project
```bash
# from anywhere
createProject myExistingProject --update

# or from within the project directory
createProject --update
```

### Run the GUI naming linter
```bash
# lint the whole project from its root
runLinter

# or specify a file or directory
runLinter <file_or_dir>
```

### Sync Agent instructions to other repos
```bash
# Preview what would change (dry-run, default)
python syncAgentInstructions.py

# Choose one repository from a numbered list
python syncAgentInstructions.py --repo

# Select one repository non-interactively
python syncAgentInstructions.py --repo Glawster/myRepository

# Actually push updates
GITHUB_TOKEN=<your-pat> python syncAgentInstructions.py --confirm

# Actually update one repository selected from the list
GITHUB_TOKEN=<your-pat> python syncAgentInstructions.py --repo --confirm

# Push updates, then create and merge conflict-free pull requests
GITHUB_TOKEN=<your-pat> python syncAgentInstructions.py --confirm --merge
```

The supplied token is stored with user-only permissions in
`~/.config/organiseMyProjects/syncAgentInstructions.json` for future runs.

## Requirements

- Python 3.10+
- Development tools: `black`, `pytest`, `pre-commit`

## Project Overview

**organiseMyProjects** is a Python toolkit for scaffolding new Python projects with predefined structure, logging, GUI naming conventions, and enforceable coding standards. It provides templates and tools to quickly create consistent, well-structured Python applications with Tkinter GUIs.

### Key Features
- 📁 Create full Python project scaffolds with `createProject`
- 🔄 Update existing projects with `createProject <name> --update`
- 🧪 Automatically include logging setup, dev tools, and layout
- 🧼 Run custom GUI naming linter with `runLinter`
- 🧰 Includes pre-commit support and code style guidelines
- 🤖 Includes AI coding agent instructions for generated projects

## Repository Structure

```
organiseMyProjects/
├── .github/
│   ├── agent-instructions.md           # Canonical master guidelines template
│   ├── copilot-instructions.md         # GitHub Copilot compatibility copy
│   ├── repositoryLayout.md             # Canonical project layout definition
│   ├── requirementsManagement.md       # Canonical requirements workflow
│   └── additional-instructions.md # Project-specific (this file, NOT template)
├── organiseMyProjects/                    # Main package
│   ├── __init__.py                       # [PACKAGE] Package initialization with public API
│   ├── createProject.py                   # [PACKAGE] Project scaffolding tool
│   ├── logUtils.py                       # [PACKAGE] Centralized logging utility
│   ├── globalVars.py                     # [TEMPLATE] Global constants
│   ├── HELP.md                           # [PACKAGE] GUI linter documentation
│   ├── guiNamingLinter.py                # [PACKAGE] Naming convention checker
│   ├── runLinter.py                      # [TEMPLATE + PACKAGE] Linter CLI interface
│   ├── baseFrame.py                      # [TEMPLATE] Base GUI framework
│   ├── frameTemplate.py                  # [TEMPLATE] Template for new frames
│   ├── statusFrame.py                    # [TEMPLATE] Status display utilities
│   ├── styleUtils.py                     # [TEMPLATE] GUI styling utilities
│   └── mainMenu.py                       # [TEMPLATE] Main menu framework
├── tests/                                 # Test suite (not distributed)
│   ├── test_CreateProject.py
│   ├── test_GuiNamingLinter.py
│   ├── test_RunLinter.py
│   ├── test_Integration.py
│   ├── test_LogUtils.py
│   ├── test_SyncAgentInstructions.py
│   └── conftest.py
├── documentation/                         # Project documentation
│   ├── developer.md                       # Developer guide
│   └── git.md                             # Git workflow guide
├── syncAgentInstructions.py               # Shared-instruction sync utility
├── setup.py                               # Package configuration
├── MANIFEST.in                            # Distribution files
└── pytest.ini                             # Test configuration
```

### File Categories

**[PACKAGE]** - Package utilities that remain in organiseMyProjects and are NOT copied to new projects:
- `createProject.py` - The scaffolding tool itself
- `logUtils.py` - Package-level logging utility (accessible via `from organiseMyProjects.logUtils import getLogger, thisApplication`)
- `HELP.md` - Documentation
- `guiNamingLinter.py` - Naming linter used by this repo and by installed downstream projects

**[TEMPLATE]** - Template files that are copied to new projects:
- `globalVars.py` - Global constants (copied to src/)
- `.github/agent-instructions.md` - Canonical development guidelines copied into generated projects
- `.github/copilot-instructions.md` - Identical compatibility copy for GitHub Copilot
- `.github/repositoryLayout.md` - Managed project layout definition synced at the same path
- `.github/requirementsManagement.md` - Managed requirements workflow synced at the same path
- `baseFrame.py`, `frameTemplate.py`, `statusFrame.py` - GUI framework
- `styleUtils.py` - GUI styling utilities
- `mainMenu.py` - Main menu framework

**[TEMPLATE + PACKAGE]** - Dual-purpose files that are both copied to new projects AND accessible from the package:
- `runLinter.py` - Linter CLI (copied to tests/, also runnable via package)

## Core Components

### createProject.py
- **Purpose**: Creates and updates Python project scaffolds
- **Key Functions**:
  - `createProject(projectName)` - Creates a new project structure
  - `updateProject(projectName)` - Updates existing project with latest templates
  - `_copy_if_newer(src, dest)` - Smart file copying with timestamp checking
  - `updateTextFile(src, dest, marker)` - Merges text files with section markers
- **Resource Access**: Uses `importlib.resources` with filesystem fallback

### guiNamingLinter.py
- **Purpose**: Enforces widget naming conventions via AST analysis for both Tkinter and Qt/PySide6 projects
- **Type**: PACKAGE UTILITY (kept in this repository/package and used by installed downstream projects)
- **Key Classes**:
  - `GuiNamingVisitor` - AST visitor for analyzing code
- **Key Functions**:
  - `lintFile(filepath)` - Lint a single Python file
  - `lintGuiNaming(target)` - Lint directory recursively
  - `detectFramework(content)` - Auto-detect GUI framework (Tkinter/Qt/None)
  - `isSnakeCase(name)` - Validate snake_case naming
- **Framework Detection**: Automatically detects framework from imports:
  - **Tkinter**: Detects `import tkinter` or `from tkinter`
  - **Qt**: Detects `from PySide6`, `from PyQt5`, or `from PyQt6`
- **Naming Rules**:
  - **Tkinter Projects**: Enforces prefix-based naming (btn*, lbl*, frm*, etc.) with camelCase
  - **Qt Projects**: Enforces snake_case naming (no prefix requirement)
  - **Mixed Projects**: Per-file framework detection (some files Tkinter, some Qt)
- **Usage**: 
  - From package: `python -m organiseMyProjects.guiNamingLinter <target>` or `from organiseMyProjects import lintFile`

### runLinter.py
- **Purpose**: CLI interface for the naming linter
- **Type**: TEMPLATE + PACKAGE (copied to new projects' tests/ directory AND accessible via package import)
- **Behavior**:
  - With targets: Lints specified files/directories
  - Without targets: Searches for src/, ui/, tests/ directories
  - Falls back to current directory if no project dirs found
  - Auto-detects framework per file
- **Usage**: 
  - In new projects: `python tests/runLinter.py [target]`
  - From package: `python -m organiseMyProjects.runLinter [target]` or `from organiseMyProjects import runLinter`

### logUtils.py
- **Purpose**: Package-level logging utility
- **Type**: PACKAGE UTILITY (NOT copied to new projects, but accessible via package import)
- **Key Functions**:
  - `setApplication(name, logDir=None)` - Set the active application context and create the log directory (`~/.local/state/<name>/` by default)
  - `getApplication()` - Return the active application name (raises `RuntimeError` if not set)
  - `getApplicationLogDir()` - Return the active application log directory (raises `RuntimeError` if not set)
  - `getLogger(name=None, logDir=None, includeConsole=False, dryRun=False)` - Return a logger adapter with semantic methods (`doing`, `done`, `info`, `value`, `action`)
  - `drawBox(message, logger=None)` - Print or log a formatted ASCII box
  - `cleanOldLogFiles(logDir, daysToKeep)` - Remove log files older than specified days
- **Usage**:
  - Entry point: `from organiseMyProjects.logUtils import getLogger, setApplication`
  - Helper modules: `from organiseMyProjects.logUtils import getLogger`
  - Example entry point setup:
    ```python
    thisApplication = Path(__file__).parent.name
    setApplication(thisApplication)
    logger = getLogger(includeConsole=True, dryRun=dryRun)
    ```

### globalVars.py
- **Purpose**: Global constants and configuration
- **Type**: TEMPLATE (copied to new projects' src/ directory)
- **Note**: Projects should customize these constants for their specific needs

## Package Distribution

### Distribution Strategy

The package contains two types of files:

1. **Package Utilities** - Stay in the organiseMyProjects package:
   - `createProject.py` - The tool that creates/updates projects
   - `logUtils.py` - Package-level logging (not distributed to projects)
   - `globalVars.py` - Package constants
   
2. **Template Files** - Copied to new projects via `createProject`:
   - `.github/agent-instructions.md` - Master Agent guidelines copied to the generated project's `.github/` directory
   - `guiNamingLinter.py` - Naming checker provided by the installed `organiseMyProjects` package
   - `runLinter.py` - Linter CLI for the project
   - GUI framework files: `baseFrame.py`, `frameTemplate.py`, `statusFrame.py`, `mainMenu.py`, `styleUtils.py`

### Technical Details
- Tests excluded from package via `setup.py` (not installed)
- Template files included via `MANIFEST.in`
- Uses `importlib.resources` for accessing packaged files
- Fallback to filesystem for development mode

### Entry Points
- `createProject` - Command to create/update projects
- `runLinter` - Command to run GUI naming linter

### Resource Access Pattern
```python
try:
    from importlib.resources import files
    template = files('organiseMyProjects') / 'template.py'
    content = template.read_text()
except (ImportError, FileNotFoundError):
    # Fallback for development mode
    template = Path(__file__).parent / 'template.py'
    content = template.read_text()
```

### Public API Usage Examples
```python
# Create and update projects
from organiseMyProjects import createProject, updateProject
createProject("myNewProject")
updateProject("myExistingProject")

# Run linter programmatically
from organiseMyProjects import lintFile, lintGuiNaming, runLinter
violations = lintFile("path/to/file.py")
lintGuiNaming("path/to/directory")
runLinter()  # CLI interface

# Use logging utility
from pathlib import Path
from organiseMyProjects.logUtils import getLogger, setApplication
thisApplication = Path(__file__).parent.name
setApplication(thisApplication)
logger = getLogger(includeConsole=True)
logger.doing("starting work")
```

## Development Workflow

### Setup
```bash
# Clone repository
git clone https://github.com/Glawster/organiseMyProjects.git
cd organiseMyProjects

# Install in development mode
pip install -e .

# Install dev dependencies
pip install pytest black
```

### Testing
```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_CreateProject.py

# Run with verbose output
python -m pytest -v

# Run with coverage
python -m pytest --cov=organiseMyProjects
```

### Linting and Formatting
```bash
# Format code
black organiseMyProjects/ tests/

# Run GUI naming linter
python -m organiseMyProjects.runLinter organiseMyProjects/
```

### Testing Project Creation
```bash
# Create a test project
createProject testProject

# Update an existing project
createProject testProject --update

# Or from within project directory
cd testProject
createProject --update
```

## Test Suite Details

### Test Organization
- `test_CreateProject.py` - Tests for project scaffolding
- `test_GuiNamingLinter.py` - Tests for linter logic
- `test_RunLinter.py` - Tests for the CLI interface
- `test_Integration.py` - Tests for end-to-end workflows
- `test_LogUtils.py` - Tests for logging utilities
- `test_SyncAgentInstructions.py` - Tests for agent-instruction syncing
- **Total**: 104 comprehensive tests

### Test Patterns
- Use `tmp_path` for temporary directories (automatic cleanup)
- Mock `lintGuiNaming` in CLI tests to avoid actual linting
- Change working directory for tests that depend on CWD
- Provide descriptive assertion messages for debugging

### Key Test Cases
- Project structure creation
- File timestamp handling
- Widget naming rule validation
- CLI argument parsing
- Package resource access
- Update functionality
- Error handling

## Code Review Checklist (Project-Specific)

Before submitting changes:
- [ ] All 104 tests pass: `python -m pytest`
- [ ] Code formatted: `black organiseMyProjects/ tests/`
- [ ] Linter passes: `runLinter organiseMyProjects/`
- [ ] Test project creation: `createProject testProject`
- [ ] Test project update: `createProject testProject --update`
- [ ] Package distribution works: `python setup.py sdist`
- [ ] Entry points work after install: `createProject --help`, `runLinter --help`
- [ ] Documentation updated for new features
- [ ] Backward compatibility maintained
- [ ] Cross-platform functionality verified (if possible)

## GUI Naming Linter Details

### Framework Detection

The linter automatically detects which GUI framework is used in each file:

- **Tkinter**: Detects `import tkinter` or `from tkinter` imports
- **Qt**: Detects `from PySide6`, `from PyQt5`, or `from PyQt6` imports
- **None**: Files without recognized GUI framework are skipped for widget validation

### Naming Rules by Framework

#### Tkinter Projects

**Widget Naming (STRICT prefix rules):**
- `ttk.Button` / `tk.Button` → `btnName` (e.g., `btnSave`, `btnCancel`)
- `ttk.Label` / `tk.Label` → `lblName` (e.g., `lblStatus`, `lblTitle`)
- `ttk.Entry` / `tk.Entry` → `entryName` (e.g., `entryUsername`, `entryPassword`)
- `ttk.Frame` / `tk.Frame` → `frmName` (e.g., `frmMain`, `frmSidebar`)
- `tk.Text` → `txtName` (e.g., `txtContent`, `txtLog`)
- `tk.Listbox` → `lstName` (e.g., `lstItems`, `lstFiles`)
- `ttk.Checkbutton` / `tk.Checkbutton` → `chkName` (e.g., `chkEnabled`, `chkRemember`)
- `ttk.Radiobutton` / `tk.Radiobutton` → `rdoName` (e.g., `rdoOption1`, `rdoOption2`)
- `ttk.Combobox` → `cmbName` (e.g., `cmbSelection`, `cmbCategory`)

**Naming Convention:**
- Use camelCase after prefix
- Private members use leading underscore: `_btnInternal`

**Example (Tkinter):**
```python
import tkinter as tk
from tkinter import ttk

class MainFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        
        # Valid Tkinter naming
        self.btnSave = ttk.Button(self, text="Save")
        self.lblStatus = ttk.Label(self, text="Ready")
        self.entryName = ttk.Entry(self)
        
        # Invalid - will be flagged by linter
        self.saveButton = ttk.Button(self)  # Missing 'btn' prefix
        self.status_label = ttk.Label(self)  # snake_case not allowed
```

#### Qt Projects

**Widget Naming (NO prefix requirement):**
- All Qt widgets (QPushButton, QLabel, QLineEdit, etc.) use snake_case
- No prefix requirement (e.g., `save_button`, not `btnSave`)
- Private members use leading underscore: `_internal_widget`

**Naming Convention:**
- Use snake_case for all widget names
- No prefix requirement
- Private members: `_private_widget`

**Example (Qt):**
```python
from PySide6.QtWidgets import QWidget, QPushButton, QLabel, QLineEdit

class MainWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Valid Qt naming
        self.save_button = QPushButton("Save")
        self.status_label = QLabel("Ready")
        self.name_input = QLineEdit()
        self._internal_widget = QWidget()  # Private member
        
        # Invalid - will be flagged by linter
        self.saveButton = QPushButton()  # camelCase not allowed
        self.btnSave = QPushButton()  # Tkinter-style not allowed
```

#### Mixed Projects

The linter supports projects with both Tkinter and Qt files:

```
project/
├── tkinter_ui.py      # Uses Tkinter rules (prefix-based)
└── qt_ui.py           # Uses Qt rules (snake_case)
```

Each file is analyzed independently based on its imports.

### Function Formatting Rules

**Both frameworks:**
- Methods longer than 4 lines should have a blank line after the `def` statement
- Short methods (≤4 lines) do not require blank line

```python
# Short method - no blank line needed
def shortMethod(self):
    return self.value

# Long method - blank line required after def
def longMethod(self):
    
    line1 = "test"
    line2 = "test"
    line3 = "test"
    line4 = "test"
    line5 = "test"
```

### Usage

```bash
# Lint current directory (auto-detect framework)
runLinter

# Lint specific file
runLinter path/to/file.py

# Lint directory
runLinter path/to/directory
```

### Qt Widget Types Supported

The linter recognizes these Qt widget types:
- QPushButton, QToolButton
- QLabel
- QLineEdit, QTextEdit, QPlainTextEdit
- QListWidget, QListView
- QComboBox
- QCheckBox, QRadioButton
- QWidget, QFrame, QGroupBox
- QTableWidget, QTableView, QTreeWidget, QTreeView
- QSpinBox, QDoubleSpinBox, QSlider, QProgressBar
- QTabWidget, QScrollArea, QSplitter, QStackedWidget

## Common Development Tasks

### Adding a New Template File
1. Add file to `organiseMyProjects/` directory
2. Update `MANIFEST.in` if needed
3. Update `createProject()` to copy the file
4. Add test in `test_CreateProject.py`
5. Update the root `README.md` with the file description

### Adding a New Widget Type to Linter
**For Tkinter widgets:**
1. Add naming rule to `namingRules` dict in `guiNamingLinter.py`
2. Add widget class to `widgetClasses` set
3. Add parametrized test cases in `test_GuiNamingLinter.py`
4. Update HELP.md and `.github/additional-instructions.md` (and `.github/agent-instructions.md` only if the change affects universal guidance)

**For Qt widgets:**
1. Add widget type to `qtWidgetTypes` set in `guiNamingLinter.py`
2. Add parametrized test cases in `test_GuiNamingLinter.py`
3. Update HELP.md and `.github/additional-instructions.md` (and `.github/agent-instructions.md` only if the change affects universal guidance)

### Modifying Project Structure
1. Update `createProject()` function
2. Update tests to verify new structure
3. Update the root `README.md` documentation
4. Consider backward compatibility for `updateProject()`

## Troubleshooting

### Tests Failing on Windows
- Check path separators (use `Path` from `pathlib`)
- Verify working directory changes in tests
- Check for platform-specific file handling

### Package Distribution Issues
- Verify `MANIFEST.in` includes all necessary files
- Check `setup.py` excludes tests properly
- Test with `python setup.py sdist` and inspect generated tarball

### Import Errors After Install
- Ensure entry points are correctly defined in `setup.py`
- Verify package name matches import statements
- Check that `__init__.py` files are present where needed

## Future Considerations

### Potential Enhancements
- Add more template variations (CLI-only, no-GUI, etc.)
- Support for other GUI frameworks (PyQt, wxPython)
- Configuration file for customizing generated projects
- Plugin system for custom linter rules
- Better handling of existing projects during updates

### Maintenance Notes
- Keep `.github/agent-instructions.md` as the master guideline and keep this file aligned with it
- Update this file for project-specific changes
- Maintain backward compatibility in `updateProject()`
- Keep test coverage above 90%
