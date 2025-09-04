# BBCTRL Firmware - Technologies

## Technologies Used

### Core Languages
- **C**: AVR microcontroller firmware for real-time motion control
- **Python 3**: Main application server and backend logic
- **JavaScript**: Web frontend user interface
- **HTML/Pug**: Template system for web interface
- **CSS/Stylus**: Styling for web interface

### Frameworks and Libraries

#### Python Backend
- **Tornado**: Asynchronous web framework for HTTP/WebSocket server
- **SockJS**: WebSocket communication library
- **PySerial**: Serial communication with AVR microcontroller
- **PyUDEV**: Linux device management
- **SMBus2**: I2C communication

#### JavaScript Frontend
- **Vue.js**: Reactive frontend framework
- **Three.js**: 3D visualization library
- **Chart.js**: Data visualization for charts
- **SockJS**: WebSocket client
- **Browserify**: JavaScript module bundler

#### Build Tools
- **Make**: Build system orchestration
- **Node.js**: JavaScript runtime for build tools
- **Browserify**: JavaScript bundling
- **Pug CLI**: Template compilation
- **Stylus**: CSS preprocessing
- **JSHint**: JavaScript linting

### Hardware Interfaces
- **AVR Toolchain**: GCC for AVR microcontroller compilation
- **ARM Toolchain**: Cross-compilation for Raspberry Pi
- **Serial Communication**: UART between RPi and AVR
- **I2C**: Inter-integrated circuit communication
- **SPI**: Serial peripheral interface
- **Modbus**: Industrial communication protocol

## Development Setup

### Prerequisites
- **Linux Development Environment**: Ubuntu/Debian recommended
- **AVR Toolchain**: `gcc-avr`, `avr-libc`, `avrdude`
- **ARM Toolchain**: For Raspberry Pi cross-compilation
- **Python 3**: With required packages
- **Node.js**: For JavaScript build tools
- **Git**: Version control

### Build Process
1. **AVR Firmware**: Compiled with AVR-GCC, programmed via avrdude
2. **Python Package**: Built with setuptools, installed via pip
3. **Web Assets**: JavaScript bundled with Browserify, templates compiled with Pug
4. **Cross-compilation**: CAMotics built for ARM architecture using chroot

### Development Workflow
- **Makefile**: Central build orchestration
- **Version Management**: Automated version bumping and tagging
- **Package Distribution**: Source distribution with setup.py
- **Testing**: Unit tests and integration testing

## Technical Constraints

### Real-time Requirements
- AVR microcontroller handles time-critical motion control
- Interrupt-driven I/O processing
- Precise timing for stepper motor control

### Resource Limitations
- AVR memory constraints (limited RAM/Flash)
- Raspberry Pi thermal management
- Network bandwidth for camera streaming

### Compatibility
- Cross-platform web interface (browsers)
- Multiple CNC machine configurations
- Various peripheral device support

## Dependencies

### Runtime Dependencies
- **Python Packages**: tornado, sockjs-tornado, pyserial, pyudev, smbus2
- **System Libraries**: Linux kernel modules, device drivers
- **Hardware**: Raspberry Pi, AVR microcontroller, stepper drivers

### Build Dependencies
- **AVR Tools**: gcc-avr, binutils-avr, avr-libc
- **ARM Tools**: gcc-arm-linux-gnueabihf
- **Node.js Packages**: browserify, pug-cli, stylus, jshint

## Tool Usage Patterns

### Version Control
- Git for source code management
- GitHub for repository hosting
- Release management with tags

### Documentation
- Markdown for documentation
- Inline code comments
- API documentation generation

### Testing
- Unit testing for Python components
- Integration testing for full system
- Manual testing for hardware interfaces

### Deployment
- Debian package generation
- Image creation for Raspberry Pi
- Firmware update mechanisms