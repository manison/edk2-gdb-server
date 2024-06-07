# UEFI Debug Agent

Debug agent driver is part of EDK2 (_SourceLevelDebugPkg_).

## Build Instructions

1. Setup EDK2 build environment as documented.
2. Set active platform in _Conf/target.txt_ (and check other parameters, e.g. `TARGET` and `TARGET_ARCH`)

```
ACTIVE_PLATFORM = SourceLevelDebugPkg/SourceLevelDebugPkg.dsc
```

3. Modify _SourceLevelDebugPkg\SourceLevelDebugPkg.dsc_ to suit your needs.

Downgrade the debug protocol to revision 0.3 since the edk2-gdb-server does not support data compression:

```ini
[PcdsFixedAtBuild]
gEfiSourceLevelDebugPkgTokenSpaceGuid.PcdTransferProtocolRevision|0x00000003
```

For debug output of the debug agent itself I added

```ini
[PcdsFixedAtBuild]
gEfiMdePkgTokenSpaceGuid.PcdDebugPropertyMask|0xFF
gEfiMdePkgTokenSpaceGuid.PcdDebugPrintErrorLevel|0x80000042

[LibraryClasses.common.DXE_DRIVER]
DebugLib|MdePkg/Library/UefiDebugLibConOut/UefiDebugLibConOut.inf
```

For serial communication I used SUNIX PCIe expansion card. This needed to be added:

```ini
[PcdsFixedAtBuild]
# The following is for SUNIX PCIe serial port expansion board.

# 4-byte structure for each PCI node in PcdSerialPciDeviceInfo
## PCI Serial Device Info. It is an array of Device, Function, and Power Management
#  information that describes the path that contains zero or more PCI to PCI bridges
#  followed by a PCI serial device.  Each array entry is 4-bytes in length.  The
#  first byte is the PCI Device Number, then second byte is the PCI Function Number,
#  and the last two bytes are the offset to the PCI power management capabilities
#  register used to manage the D0-D3 states.  If a PCI power management capabilities
#  register is not present, then the last two bytes in the offset is set to 0.  The
#  array is terminated by an array entry with a PCI Device Number of 0xFF.  For a
#  non-PCI fixed address serial device, such as an ISA serial device, the value is 0xFF.
#
# typedef struct {
#   UINT8     Device;
#   UINT8     Function;
#   UINT16    PowerManagementStatusAndControlRegister;
# } PCI_UART_DEVICE_INFO;
#
# Use EFI Shell `pci` command to find this address.
# Also if the device is on bus other than zero, the for loop variable in
# GetSerialRegisterBase in BaseSerialPortLib.c might need to be modified
# accordingly.
gEfiMdeModulePkgTokenSpaceGuid.PcdSerialPciDeviceInfo|{0x00, 0x00, 0x00, 0x00, 0xFF}

## UART clock frequency is for the baud rate configuration.
# Default 1843200
gEfiMdeModulePkgTokenSpaceGuid.PcdSerialClockRate|14745600

## Baud rate for the 16550 serial port.  Default is 115200 baud.
# @Prompt Baud rate for serial port.
# @ValidList  0x80000001 | 921600, 460800, 230400, 115200, 57600, 38400, 19200, 9600, 7200, 4800, 3600, 2400, 2000, 1800, 1200, 600, 300, 150, 134, 110, 75, 50
gEfiMdeModulePkgTokenSpaceGuid.PcdSerialBaudRate|9600
```

**Note:** I had to lower the baudrate because the default 115200 was quite unreliable. There were CRC errors, missing ACKs and similar sort of communication errors.

**Tip:** To enable agent trace output uncomment `DEBUG_AGENT_SETTING_PRINT_ERROR_LEVEL` request in _udkserver.py_.
