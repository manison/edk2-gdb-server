# Prerequisites

## Target (debuggee)

* X86_64 system with COTS UEFI firmware
* Serial port
* [Debug agent](./debugagent.md) driver loaded

## Host (debugger)

* Linux machine with serial port
* edk2-gdb-server (this script)
  * Python3
  * _pyserial_ (not to be confused with _serial_) and _pefile_ packages installed (see [requirements.txt](../requirements.txt))
  * This script must run on Linux machine because of Python `poll` function inability to work with serial file descriptors  
* [lldb](./lldb.md) (running either on the same Linux machine or running on another (possibly Windows) machine and connected through TCP to the Linux machine that runs the edk2-gdb-server)

# Basic Setup

1. Connect the target and host machines with serial null modem cable

2. On the host system start the edk2-gdb-server

```sh
$ ./server.py
```

3. Power on the target system, load a UEFI shell a load the [debug agent](./debugagent.md)

```
FS0:\> load DebugAgentDxe.efi
```

4. Once the debug agent successfully connects to the edk2-gdb-server the target breaks and waits for next action

5. The edk2-gdb-server now accepts connections from the debugger, start the `lldb` and connect to the edk2-gdb-server

```sh
$ lldb
```

```
(lldb) gdb-remote localhost:1234
Process 1 stopped
* thread #1, stop reason = signal SIGTRAP
    frame #0: 0x000000005bb25d87
->  0x5bb25d87: movq   %rdi, %rcx
    0x5bb25d8a: callq  0x5bb247a0
    0x5bb25d8f: movq   %rsi, %rcx
    0x5bb25d92: movq   0x30(%rsp), %rbx
```

6. You can now resume the execution of target

```
(lldb) continue
```

or simply

```
(lldb) c
```

See [lldb](./lldb.md) for more debugging tips.
