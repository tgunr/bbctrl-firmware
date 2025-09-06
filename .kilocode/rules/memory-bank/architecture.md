# BBCTRL Firmware - Architecture

## System Architecture

The BBCTRL firmware follows a distributed architecture with three main components:

### AVR Microcontroller (Real-time Motion Control)
- **Location**: `src/avr/`
- **Language**: C
- **Purpose**: Handles real-time motion control and I/O operations
- **Key Files**:
  - `src/avr/src/main.c` - Main firmware loop
  - `src/avr/src/stepper.c` - Stepper motor control
  - `src/avr/src/motor.c` - Motor driver management
  - `src/avr/src/exec.c` - Motion execution
  - `src/avr/src/command.c` - Command processing
  - `src/avr/src/modbus.c` - Modbus communication
  - `src/avr/src/io.c` - Digital I/O handling

### Raspberry Pi Backend (Application Server)
- **Location**: `src/py/bbctrl/`
- **Language**: Python 3
- **Framework**: Tornado web server
- **Purpose**: Main application logic, web serving, file management
- **Key Files**:
  - `src/py/bbctrl/__init__.py` - Main entry point
  - `src/py/bbctrl/Web.py` - Web server and API handlers
  - `src/py/bbctrl/AVR.py` - AVR communication
  - `src/py/bbctrl/Mach.py` - Machine control logic
  - `src/py/bbctrl/Planner.py` - GCode planning and execution
  - `src/py/bbctrl/Config.py` - Configuration management
  - `src/py/bbctrl/FileSystem.py` - File operations

### Web Frontend (User Interface)
- **Location**: `src/js/`, `src/pug/`, `src/stylus/`
- **Language**: JavaScript, Pug templates, Stylus CSS
- **Framework**: Vue.js
- **Purpose**: Browser-based user interface
- **Key Files**:
  - `src/js/main.js` - Frontend entry point
  - `src/js/app.js` - Main Vue application
  - `src/pug/index.pug` - Main HTML template
  - `src/js/program.js` - GCode program handling
  - `src/js/path-viewer.js` - 3D visualization

## Source Code Paths
- **AVR Firmware**: `src/avr/src/`
- **Python Backend**: `src/py/bbctrl/`
- **JavaScript Frontend**: `src/js/`
- **Templates**: `src/pug/templates/`
- **Styles**: `src/stylus/`
- **Build Scripts**: `scripts/`
- **Configuration**: Root level files (Makefile, package.json, setup.py)

## Key Technical Decisions
- **Distributed Architecture**: Separates real-time motion control (AVR) from application logic (RPi)
- **Web-based UI**: Cross-platform accessibility without native applications
- **Modular Design**: Clean separation of concerns between components
- **Open Standards**: Uses standard protocols (HTTP, WebSocket, Modbus)
- **Cross-compilation**: ARM build support for Raspberry Pi deployment

## Design Patterns
- **Observer Pattern**: Event-driven communication between components
- **Command Pattern**: GCode command processing and queuing
- **Factory Pattern**: Dynamic component creation
- **MVC Pattern**: Separation of data, presentation, and control logic

## Component Relationships
- **AVR ↔ RPi**: Serial communication for real-time control
- **RPi ↔ Web**: WebSocket/SockJS for real-time updates
- **Web ↔ RPi**: REST API for configuration and file operations
- **AVR ↔ Peripherals**: Direct hardware interfaces (motors, I/O, Modbus)

## Critical Implementation Paths
- **Motion Control**: AVR main loop → command processing → stepper execution
- **GCode Execution**: File upload → planning → AVR command queue → motion
- **Web Interface**: Vue components → API calls → Python handlers → AVR communication
- **Configuration**: Web forms → validation → storage → runtime updates