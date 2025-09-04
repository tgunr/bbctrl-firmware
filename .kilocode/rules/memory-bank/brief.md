# BBCTRL Firmware - Brief

## Project Purpose
BBCTRL (Buildbotics CNC Controller) is an open-source firmware for CNC (Computer Numerical Control) machines. It provides a complete motion control system that runs on Raspberry Pi hardware with AVR microcontroller for real-time motion control.

## Core Requirements
- **Real-time Motion Control**: 4-axis stepper motor control with precise positioning
- **GCode Execution**: Full GCode interpreter and executor with simulation capabilities
- **Web Interface**: Browser-based control interface with 3D visualization
- **Modular Architecture**: Separate AVR firmware for real-time tasks, Python backend, and JavaScript frontend
- **Extensible I/O**: Configurable digital I/O, Modbus communication, VFD spindle control
- **Safety Features**: Emergency stop handling, soft limits, motor fault detection

## Key Goals
- Provide a complete, open-source CNC controller solution
- Maintain real-time performance for precise motion control
- Offer intuitive web-based user interface
- Support various CNC machine configurations and peripherals
- Ensure safety and reliability in CNC operations

## Success Criteria
- Reliable 4-axis motion control with sub-millimeter precision
- Smooth GCode execution with lookahead planning
- Responsive web interface with real-time status updates
- Support for common CNC peripherals (VFD spindles, cameras, LCD displays)
- Stable operation under various load conditions

## Current Status
- Version 2.1.0.dev8 (development)
- Active development with regular updates
- Production-ready for many CNC applications
- Community-supported open-source project