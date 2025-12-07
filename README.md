# UE5 Macro Automation System

A comprehensive Python-based macro automation system for Unreal Engine 5 that enables programmatic control of the editor through recording, playback, and batch operations.

## Features

### Core System
- **Macro Recorder**: Capture and replay editor actions with support for multiple action types
- **Command Queue**: Priority-based queue with dependency resolution and cancellation support
- **Task Executor**: Synchronous and asynchronous task execution with retry logic
- **Rollback Manager**: Full undo/redo support with transaction-based operations

### Macro Operations
- Asset import with auto-LOD generation (FBX, OBJ)
- Automated material assignment based on naming conventions
- Bulk texture import and material instance creation
- Static mesh collision generation
- Level organization (grouping, renaming, hierarchy management)
- Automated lighting build and quality settings
- Asset validation and cleanup routines

### Pre-built Templates
- **Import Tree Assets**: Batch import foliage with collision, materials, and folder organization
- **Optimize Scene**: Merge actors, combine meshes, check for errors
- **Setup Environment**: 7 lighting presets (outdoor sunny, sunset, overcast, indoor office, dramatic, studio, night)
- **Batch Rename**: Smart renaming with prefix/suffix, regex, sequential numbering
- **Export Selected**: Batch export to FBX, OBJ, glTF formats

### Control Interface
- Qt-based GUI panel that docks inside Unreal Editor
- Macro library with save/load functionality (JSON format)
- Hotkey support for triggering macros
- Macro editor with syntax highlighting
- Progress bars and logging for long operations

### Bonus Features
- REST API for external control and automation
- Watch folder automation for automatic macro triggering
- External tool integration (Blender, Substance)
- Performance profiling for macro execution

## Requirements

- Unreal Engine 5.3+ (tested and expected to work on 5.6/5.7)
- Python 3.9+
- PySide6 (Qt for Python)
- aiohttp (for REST API)
- watchdog (for folder monitoring)

## Engine Version Support

This macro system is designed against Unreal Engine 5.3+ and uses core editor scripting APIs that have been stable across UE 5.0–5.7. The system relies on the following Unreal Python modules:

**Core Editor Libraries:**
- `unreal.EditorLevelLibrary` - Level actor management, spawning, selection, lighting builds
- `unreal.EditorAssetLibrary` - Asset operations (rename, delete, duplicate, save, list)
- `unreal.EditorUtilityLibrary` - Selection and content browser utilities
- `unreal.EditorLoadingAndSavingUtils` - Map loading and package saving

**Asset Tools:**
- `unreal.AssetToolsHelpers` - Asset import/export operations
- `unreal.AssetRegistryHelpers` - Asset registry queries
- `unreal.StaticMeshEditorSubsystem` - Collision and mesh editing

**Types and Enums:**
- Core types: `Vector`, `Rotator`, `LinearColor`, `StaticMesh`, `Texture2D`
- Actor types: `DirectionalLight`, `PointLight`, `SpotLight`, `PostProcessVolume`, `ExponentialHeightFog`
- Enums: `LightingBuildQuality`, `CollisionTraceFlag`, `ScriptingCollisionShapeType`, `AttachmentRule`

These APIs are part of the "Editor Scripting Utilities" plugin and have remained stable across UE 5.x releases.

**Required Plugins (must be enabled in your project):**
- Editor Scripting Utilities
- Python Editor Script Plugin

**Caveats for UE 5.6/5.7:**
- Static mesh and collision operations require the editor to be fully initialized with a level loaded
- `GameUserSettings` quality changes may only affect PIE sessions, not editor viewports
- Lighting build behavior depends on your project's lighting system (Lumen vs baked)
- In World Partition projects, `get_all_level_actors()` behavior depends on loaded cells/layers

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/kaydenn-k/ue5-macro-automation.git
cd ue5-macro-automation
```

### 2. Install Dependencies

Using Poetry (recommended):

```bash
poetry install
```

Or using pip:

```bash
pip install -e .
```

### 3. Configure Unreal Engine

Copy the plugin files to your Unreal Engine project:

```bash
cp -r src/ue5_macro_automation /path/to/your/project/Plugins/
```

Enable the plugin in your project settings.

### 4. Configure Python Path

Add the following to your Unreal Engine Python initialization:

```python
import sys
sys.path.append("/path/to/ue5-macro-automation/src")
```

## Quick Start for Unreal Engine 5

### 1. Install Python Dependencies into Unreal's Python

Unreal Engine 5 uses its own embedded Python interpreter. You need to install the required packages into Unreal's Python environment.

**Important:** Replace `UE_5.x` with your installed version (e.g., `UE_5.6` or `UE_5.7`).

**Windows:**
```bash
# Example for UE 5.7 (adjust version number to match your installation)
"C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\ThirdParty\Python3\Win64\python.exe" -m pip install PySide6 aiohttp watchdog pydantic
```

**macOS:**
```bash
# Replace UE_5.x with your version (e.g., UE_5.6, UE_5.7)
"/Users/Shared/Epic Games/UE_5.x/Engine/Binaries/ThirdParty/Python3/Mac/bin/python3" -m pip install PySide6 aiohttp watchdog pydantic
```

**Linux:**
```bash
# Replace UE_5.x with your version (e.g., UE_5.6, UE_5.7)
"/opt/UnrealEngine/UE_5.x/Engine/Binaries/ThirdParty/Python3/Linux/bin/python3" -m pip install PySide6 aiohttp watchdog pydantic
```

**Note:** The exact path may vary based on your installation. Check your Epic Games Launcher or installation directory to find the correct path.

### 2. Copy the Package to Your UE5 Project

Copy the `src` folder to your Unreal project's Scripts directory:

```bash
# Create the Scripts directory if it doesn't exist
mkdir -p <YourProject>/Scripts

# Copy the package
cp -r /path/to/ue5-macro-automation/src <YourProject>/Scripts/ue5_macro_automation
```

Your project structure should look like:
```
YourProject/
├── Content/
├── Scripts/
│   └── ue5_macro_automation/
│       ├── __init__.py
│       ├── core/
│       ├── macros/
│       ├── ui/
│       ├── templates/
│       ├── api/
│       └── utils/
└── YourProject.uproject
```

### 3. Minimal Python Console Snippet

Open the Unreal Editor Python console (Window > Developer Tools > Output Log, then switch to Python) and run:

```python
import sys
sys.path.insert(0, r"<YourProject>/Scripts")

import ue5_macro_automation
from ue5_macro_automation.ui.main_panel import MacroAutomationPanel
from ue5_macro_automation.templates.import_tree_assets import ImportTreeAssetsTemplate, TreeImportConfig

panel = MacroAutomationPanel()
panel.show()

template = ImportTreeAssetsTemplate()
config = TreeImportConfig(
    source_directory="C:/Assets/Trees",
    destination="/Game/Environment/Trees",
    generate_collision=True,
    auto_lod=True,
    lod_count=3,
    material_conventions={
        "bark": "/Game/Materials/M_TreeBark",
        "leaf": "/Game/Materials/M_TreeLeaves",
    }
)
result = template.execute(config)
print(f"Import complete: {result.success}, imported {result.imported_count} assets")
```

## Quick Start

### Basic Usage

```python
from src.core.macro_engine import MacroEngine

engine = MacroEngine()
engine.initialize()

engine.start_recording("My First Macro")

engine.stop_recording()

engine.execute_macro("My First Macro")

engine.shutdown()
```

### Recording a Macro

```python
from src.core.macro_engine import MacroEngine
from src.core.macro_recorder import ActionType

engine = MacroEngine()
engine.initialize()

engine.start_recording("Import Assets Macro")

engine.recorder.record_import("/path/to/model.fbx", "/Game/Meshes")
engine.recorder.record_material_assign("/Game/Meshes/Model", "/Game/Materials/M_Default")
engine.recorder.record_command("stat fps")

macro = engine.stop_recording()

engine.recorder.save_macro("/path/to/macro.json", macro)
```

### Using Templates

```python
from src.templates.import_tree_assets import ImportTreeAssetsTemplate, TreeImportConfig

template = ImportTreeAssetsTemplate()

config = TreeImportConfig(
    source_directory="/path/to/assets",
    destination="/Game/Environment/Trees",
    generate_collision=True,
    auto_lod=True,
)

result = template.execute(config)

if result.success:
    print(f"Imported {result.imported_count} assets")
```

### Using the REST API

Start the API server:

```python
from src.api.rest_server import MacroAPIServer

server = MacroAPIServer(host="127.0.0.1", port=8080)
server.start()
```

Then use HTTP requests to control macros:

```bash
curl http://localhost:8080/api/macros

curl -X POST http://localhost:8080/api/macros/MyMacro/execute

curl -X POST http://localhost:8080/api/recording/start \
  -H "Content-Type: application/json" \
  -d '{"name": "New Recording"}'
```

### Watch Folder Automation

```python
from src.api.watch_folder import WatchFolderAutomation

watcher = WatchFolderAutomation()

watcher.add_watch(
    "/path/to/watch",
    "ImportTreeAssets",
    patterns=["*.fbx", "*.obj"],
)

watcher.start()
```

## Configuration

### Macro Library Location

By default, macros are stored in:

```
~/.ue5_macro_automation/macros/
```

You can change this by setting the `UE5_MACRO_LIBRARY_PATH` environment variable.

### Hotkey Configuration

Hotkeys are stored in:

```
~/.ue5_macro_automation/hotkeys.json
```

Example configuration:

```json
{
  "Ctrl+Shift+1": "ImportTreeAssets",
  "Ctrl+Shift+2": "OptimizeScene",
  "Ctrl+Shift+3": "BatchRename"
}
```

### REST API Configuration

```python
server = MacroAPIServer(
    host="0.0.0.0",
    port=8080,
)
```

## GUI Usage

### Launching the Panel

```python
from src.ui.main_panel import MacroAutomationPanel

panel = MacroAutomationPanel()
panel.show()
```

### Panel Features

The main panel includes tabs for macro library management, macro editor with syntax highlighting, template execution, and settings configuration. The macro library tab displays all saved macros with options to execute, edit, duplicate, or delete them. The editor tab provides a full-featured code editor for creating and modifying macros with JSON syntax highlighting. The templates tab offers quick access to pre-built automation templates with configurable parameters. The settings tab allows customization of hotkeys, API settings, and watch folder configurations.

## API Reference

### MacroEngine

The central coordinator for all macro operations.

```python
engine = MacroEngine()
engine.initialize()
engine.start_recording(name: str)
engine.stop_recording() -> Macro
engine.execute_macro(name: str, context: dict = None) -> MacroResult
engine.queue_command(name: str, action: Callable) -> str
engine.undo() -> bool
engine.redo() -> bool
engine.shutdown()
```

### CommandQueue

Priority-based command queue with dependency resolution.

```python
queue = CommandQueue()
queue.enqueue(command: Command)
queue.enqueue_batch(commands: List[Command])
queue.process_next() -> CommandResult
queue.process_all() -> List[CommandResult]
queue.cancel(command_id: str) -> bool
queue.get_status(command_id: str) -> CommandStatus
```

### MacroRecorder

Records and replays editor actions.

```python
recorder = MacroRecorder()
recorder.start_recording(name: str)
recorder.record_action(action: RecordedAction)
recorder.record_import(source: str, destination: str)
recorder.record_spawn(actor_class: str, location: tuple)
recorder.record_material_assign(mesh_path: str, material_path: str)
recorder.stop_recording() -> Macro
recorder.replay(macro: Macro, dry_run: bool = False) -> ReplayResult
recorder.save_macro(path: str, macro: Macro) -> bool
recorder.load_macro(path: str) -> Macro
```

### REST API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check |
| GET | /status | System status |
| GET | /api/macros | List all macros |
| GET | /api/macros/{name} | Get macro details |
| POST | /api/macros | Create macro |
| DELETE | /api/macros/{name} | Delete macro |
| POST | /api/macros/{name}/execute | Execute macro |
| POST | /api/recording/start | Start recording |
| POST | /api/recording/stop | Stop recording |
| GET | /api/recording/status | Recording status |
| GET | /api/templates | List templates |
| POST | /api/templates/{name}/execute | Execute template |
| POST | /api/undo | Undo last action |
| POST | /api/redo | Redo last undone action |

## Testing

Run the test suite:

```bash
poetry run pytest
```

Run with coverage:

```bash
poetry run pytest --cov=src --cov-report=html
```

Run specific test modules:

```bash
poetry run pytest tests/core/test_command_queue.py
poetry run pytest tests/api/test_rest_server.py
```

## Project Structure

```
ue5-macro-automation/
├── src/
│   ├── core/
│   │   ├── command_queue.py
│   │   ├── task_executor.py
│   │   ├── macro_recorder.py
│   │   ├── macro_engine.py
│   │   └── rollback.py
│   ├── macros/
│   │   ├── asset_import.py
│   │   ├── material_ops.py
│   │   ├── collision_ops.py
│   │   ├── level_ops.py
│   │   ├── lighting_ops.py
│   │   └── validation.py
│   ├── ui/
│   │   ├── main_panel.py
│   │   ├── macro_library.py
│   │   ├── macro_editor.py
│   │   ├── progress_widget.py
│   │   ├── log_widget.py
│   │   ├── hotkey_manager.py
│   │   └── action_dialog.py
│   ├── templates/
│   │   ├── import_tree_assets.py
│   │   ├── optimize_scene.py
│   │   ├── setup_environment.py
│   │   ├── batch_rename.py
│   │   └── export_selected.py
│   ├── api/
│   │   ├── rest_server.py
│   │   ├── watch_folder.py
│   │   └── external_tools.py
│   └── utils/
│       ├── file_utils.py
│       ├── logging_utils.py
│       ├── unreal_helpers.py
│       └── profiler.py
├── tests/
│   ├── core/
│   ├── macros/
│   ├── ui/
│   ├── templates/
│   └── api/
├── examples/
├── config/
├── docs/
├── pyproject.toml
└── README.md
```

## Contributing

Contributions are welcome. Please ensure all tests pass before submitting a pull request. Follow the existing code style and add tests for new functionality.

## License

MIT License
