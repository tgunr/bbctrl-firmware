# G-code Processing Architecture in BBCtrl Firmware

This document explains how G-code is interpreted, processed, and executed in the BBCtrl firmware system, including command queuing mechanisms and overload handling.

## Overview

The BBCtrl system uses a multi-stage pipeline for G-code processing that ensures real-time motion control while maintaining system stability:

```
G-code File → Python Planner → Command Queue → AVR → Motors
```

## 1. G-code Interpretation and Processing Pipeline

### High-Level Architecture

The system separates G-code processing into distinct layers:

- **Python Layer**: High-level planning, trajectory generation, and command orchestration
- **Communication Layer**: Serial communication and flow control between Python and AVR
- **AVR Layer**: Real-time command execution and motor control

### Stage 1: G-code Parsing and Planning (Python Layer)

#### File Loading and Parsing

The [`Planner`](../src/py/bbctrl/Planner.py) class handles G-code interpretation:

1. **File Loading**: G-code files are loaded through `planner.load()`
2. **Camotics Integration**: Uses the Camotics library for actual G-code parsing and trajectory planning
3. **Motion Planning**: Converts G-code commands into motion blocks with:
   - Target positions for each axis
   - Velocity and acceleration profiles
   - S-curve timing calculations
   - Spindle speed synchronization

#### Command Encoding

The `_encode()` method converts planning blocks into AVR-compatible commands:

- **Line moves**: Become `Cmd.line()` commands with target positions and timing arrays
- **Speed changes**: Become `Cmd.speed()` commands for spindle control
- **Tool changes**: Handled via configurable G-code macros
- **Dwells**: Become `Cmd.dwell()` commands for timed pauses

#### Configuration Management

The planner applies system configuration including:

```python
cfg = {
    'default-units': 'METRIC' if state.get('metric') else 'IMPERIAL',
    'max-vel': state.get_axis_vector('vm', 1000),
    'max-accel': state.get_axis_vector('am', 1000000),
    'max-jerk': state.get_axis_vector('jm', 1000000),
    'junction-accel': config.get('junction-accel'),
}
```

### Stage 2: Command Queuing (Python Layer)

#### Command Queue Management

The [`CommandQueue`](../src/py/bbctrl/CommandQueue.py) class manages command synchronization:

```python
def enqueue(self, id, cb, *args, **kwargs):
    self.lastEnqueueID = id
    self.q.append([id, cb, args, kwargs])
    self._release()
```

Key features:
- Each command gets a unique 16-bit ID for tracking
- Callbacks are synchronized with AVR execution completion
- Commands are released when the AVR reports completion via the `id` variable

#### Synchronization Mechanism

The queue uses a release mechanism to ensure proper timing:

```python
def release(self, id):
    if id and not util.id16_less(self.releaseID, id):
        self.log.debug('id out of order %d <= %d' % (id, self.releaseID))
    self.releaseID = id
    self._release()
```

### Stage 3: Communication Layer

#### Serial Communication

The [`Comm`](../src/py/bbctrl/Comm.py) class manages AVR communication:

```python
def queue_command(self, cmd):
    self.queue.append(cmd)
    self.flush()
```

Communication characteristics:
- High-speed serial communication (up to 921600 baud)
- Hardware flow control (RTS/CTS) for buffer management
- Non-blocking I/O with proper error handling

#### Flow Control

The communication layer implements several flow control mechanisms:
- Command queuing to prevent buffer overflow
- Periodic polling for new commands from the planner
- Graceful handling of communication errors

## 2. AVR Command Processing

### Command Reception

#### Serial Input Processing

Commands arrive via USART and are processed in `command_callback()`:

```c
bool command_callback() {
  static char *block = 0;
  if (!block) block = usart_readline();
  if (!block) return false; // No command
  
  // Process command based on type
  status = _dispatch(block);
}
```

#### Command Classification

Commands are defined in [`command.def`](../src/avr/src/command.def) and classified as:

**Synchronous Commands** (queued for real-time execution):
- `'l'` line: Motion commands with S-curve timing profiles
- `'d'` dwell: Timed pauses in execution
- `'s'` seek: Homing and probing moves
- `'a'` set_axis: Axis position setting
- `'p'` speed: Spindle speed control

**Asynchronous Commands** (immediate execution):
- `'j'` jog: Manual jogging operations
- `'S'` stop: Emergency stop
- `'F'` flush: Clear command queue
- `'E'` estop: Emergency stop with alarm state

### Command Queue (AVR Layer)

#### Synchronous Queue Implementation

Critical motion commands use a ring buffer implementation:

```c
void command_push(char code, void *_data) {
  uint8_t *data = (uint8_t *)_data;
  unsigned size = _size(code);
  
  // Ensure buffer space is available
  ESTOP_ASSERT(size < sync_q_space(), STAT_Q_OVERRUN);
  
  // Queue command and data
  sync_q_push(code);
  for (unsigned i = 0; i < size; i++) sync_q_push(*data++);
  
  ATOMIC_BLOCK(ATOMIC_RESTORESTATE) cmd.count++;
}
```

#### Buffer Management Strategy

The queue implements several safety mechanisms:
- Fixed-size ring buffer with overflow protection
- Atomic operations for thread safety
- Command rejection when buffer is full
- Buffer space validation before command acceptance

## 3. Motion Execution

### Real-time Execution Engine

#### Command Execution Loop

The execution engine is called from the stepper interrupt at 1ms intervals:

```c
stat_t exec_next() {
  // Handle holding state
  if (state_get() == STATE_HOLDING) return STAT_NOP;
  
  // Try to execute next command
  if (!ex.cb && !command_exec()) return STAT_NOP; // Queue empty
  if (!ex.cb) return STAT_AGAIN; // Non-exec command
  
  return ex.cb(); // Execute motion callback
}
```

#### Command Dequeuing

Commands are dequeued and executed by `command_exec()`:

```c
bool command_exec() {
  if (!cmd.count) {
    cmd.last_empty = rtc_get_time();
    state_idle();
    return false;
  }
  
  // Wait for minimum queue depth on restart
  if (cmd.count < EXEC_FILL_TARGET &&
      !rtc_expired(cmd.last_empty + EXEC_DELAY)) return false;
  
  uint8_t *data = command_next();
  state_running();
  _exec_cb((char)*data, data + 1);
  return true;
}
```

### Motion Control Pipeline

#### Line Command Execution

Motion commands go through `command_line_exec()`:

1. **S-curve Profile Setup**: Configures acceleration profiles for smooth motion
2. **Stepper Preparation**: `st_prep_line()` prepares individual motor moves
3. **Real-time Execution**: Stepper interrupt generates step pulses with precise timing

#### Stepper Control

The stepper system implements:
- Precise timing control using hardware timers
- S-curve acceleration profiles for smooth motion
- Power management for spindle synchronization
- Coordinated multi-axis motion

## 4. AVR Overload Handling

### Buffer Management and Flow Control

#### Command Rejection Strategy

When the synchronous queue approaches capacity:

```c
// Check buffer space before accepting commands
if (state_is_resuming() || sync_q_space() <= _size(*block))
  return false; // Wait - insufficient buffer space
```

#### Serial Flow Control

Hardware flow control prevents receiver buffer overflow:

```c
// RTS/CTS flow control in USART interrupt
if (rx_buf_space() < SERIAL_CTS_THRESH)
  OUTSET_PIN(SERIAL_CTS_PIN); // CTS Hi (disable transmission)
```

### Overload Response Mechanisms

#### Graceful Degradation

1. **Command Buffering**: New commands wait for buffer space rather than being lost
2. **Motion Continuity**: Queued commands continue executing during overload
3. **Flow Control**: Hardware-level flow control prevents data loss

#### Emergency Responses

1. **Emergency Stop**: Immediate queue flush and motion halt
2. **State Management**: Controlled transitions between execution states
3. **Hard Reset**: Available for critical error recovery
4. **Watchdog Protection**: Prevents system lockup

#### Buffer Fill Strategy

The system implements intelligent buffer management:

```c
// Maintain minimum queue depth for smooth motion
if (cmd.count < EXEC_FILL_TARGET &&
    !rtc_expired(cmd.last_empty + EXEC_DELAY)) 
  return false; // Wait for more commands
```

## 5. Performance Characteristics

### Timing Specifications

- **Stepper Interrupt**: 1ms interval (250Hz base timer with 4x subdivision)
- **Command Processing**: Non-blocking execution in main loop
- **Serial Communication**: Up to 1Mbps baud rate with hardware flow control
- **Queue Depth**: Maintains smooth motion with look-ahead buffering

### Buffer Sizes

- **Synchronous Queue**: ~1024 bytes for motion commands
- **USART Buffers**: 1024 bytes each for transmit and receive
- **Command Processing**: Real-time execution with 1ms granularity

### System States

The system manages several execution states:
- `STATE_READY`: Idle, ready for commands
- `STATE_RUNNING`: Actively executing motion
- `STATE_STOPPING`: Controlled deceleration to stop
- `STATE_HOLDING`: Paused, maintaining position
- `STATE_ESTOPPED`: Emergency stop state
- `STATE_JOGGING`: Manual jogging mode

## 6. Error Handling and Recovery

### Error Detection

The system implements comprehensive error detection:
- Buffer overflow protection with `ESTOP_ASSERT()`
- Communication error handling with retry mechanisms
- Motion limit checking and soft limit enforcement
- Emergency stop monitoring

### Recovery Mechanisms

1. **Soft Recovery**: State transitions and queue management
2. **Hard Recovery**: System reset and re-initialization
3. **Emergency Procedures**: Immediate motion halt and alarm state
4. **Watchdog Recovery**: Automatic restart on system lockup

## Conclusion

The BBCtrl G-code processing architecture provides a robust, real-time motion control system with:

- **Separation of Concerns**: High-level planning in Python, real-time execution in AVR
- **Robust Queuing**: Multi-level buffering with overflow protection
- **Flow Control**: Hardware and software mechanisms prevent data loss
- **Error Handling**: Comprehensive error detection and recovery
- **Real-time Performance**: Deterministic execution with precise timing control

This architecture ensures reliable operation even under heavy computational loads while maintaining the precise timing requirements of CNC motion control.