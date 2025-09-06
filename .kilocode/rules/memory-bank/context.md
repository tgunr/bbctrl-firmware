# BBCTRL Firmware - Context

## Current Work Focus
- Development version 2.1.0.dev
- Active maintenance and feature development
- Cross-platform CNC controller firmware

## Recent Changes
- Ongoing development with regular updates
- Support for various VFD spindle controllers
- Enhanced web interface with 3D visualization
- Improved camera integration and LCD support
- **✅ CAMotics ARM build V8 pointer compression issue RESOLVED**
  - Root cause: cbang expected V8 pointer compression enabled, system V8 has it disabled
  - Solution: Modified cbang config to not define V8_COMPRESS_POINTERS
  - Result: bbctrl starts successfully without V8 fatal errors
  - Repository sync: Both project and chroot use https://github.com/tgunr/CAMotics
  - **Debugging Process**: Systematic investigation involved checking V8 fatal error logs, comparing cbang configuration with system V8 settings, and testing configuration changes incrementally in the ARM chroot environment
  - **Lessons Learned**:
    - Configuration mismatches between build dependencies and runtime environments can cause silent failures in cross-compilation
    - Isolated build environments (chroot) are essential for reproducing and debugging ARM-specific issues
    - Documenting and verifying dependency configurations prevents future build failures
    - Incremental testing of configuration changes reduces debugging time and improves reliability

## Next Steps
- Continue development of new features
- Maintain compatibility with Raspberry Pi updates
- Expand support for additional CNC peripherals
- Improve documentation and user experience