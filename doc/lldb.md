# LLDB

## Connecting To the Target

```
(lldb) gdb-remote localhost:1234
```

## Modules and Symbols

To tell the debugger about the modules, where they are loaded and associated symbols.

**Note:** You can use `image` abbreviation instead of `target modules`.

### Add Module To the List

Add module to the target module list:

```
(lldb) target modules add -s test.pdb test.efi
```

Verify the symbols has been loaded:

```
(lldb) target modules list
[  0] 329320AD-9888-48A7-86EC-B514349A4F82-00000003 0x0000000180000000 C:\Projects\uefi\test.efi
      C:\Projects\uefi\test.pdb
```

or 

```
(lldb) target modules lookup -vn <SomeFunctionNameThatShouldHaveDebugInfo>
```

#### PDB Symbols

For modules built with Microsoft Visual C++.

On Windows LLDB should use DIA SDK to load PDB symbols. The LLDB needs to be launched from Visual Studio Developer Command prompt to set up the needed paths correctly. However there is currently [bug](https://github.com/llvm/llvm-project/issues/91060) that prevents loading the PDB symbols through DIA.

It is possible to use LLDB's native PDB loader with setting the `LLDB_USE_NATIVE_PDB_READER=1` environment variable before starting the debugger. This works on Linux too.

#### DWARF Symbols

ELF module needs to be built with the debug information (GCC `-g` switch). Then we only need sections of the intermediate ELF module with debug symbols loaded at the proper addresses. If the sections in the ELF file are properly aligned then only the `-slide` parameter needs to be calculated and specified for `target modules load`.

**Example**

Sections in the target EFI file have alignment of 0x1000. Section VAs are as follows:

section | VA
--------|-------
.text   | 0x1000
.rdata  | 0x7000
.data   | 0x8000
.bss    | 0x9000

Now we use `readelf` on the intermediate ELF module and we see that section addresses in the ELF file matches section VAs in the target EFI module.

Then we only need to calculate the `slide` parameter (see next). Since in this example the EFI module image base is zero, the `slide` parameter is equal to the actual load address.

**Notes and Tips**

* Use `dwarfdump` utility to troubleshoot DWARF symbol issues.
* EFI modules produced by iPXE are compiled without `-g` and linked with the `-S` option (strip debug symbols).

### Loading the Module

Telling the debugger where the module is loaded:

```
(lldb) target modules load -f test.efi -s 0
```

If the module is loaded at its preferred address the `slide` parameter (`-s`) is zero.

#### How To Obtain Load Address of a Module

If debugging a driver use `drivers` command in EFI Shell to retrieve the driver's handle and then print the handle information with `dh -v`.

If debugging an application print image load address at start of the program using the `EFI_LOADED_IMAGE_PROTOCOL`.

## Source Stepping

If source code of the application being debugged is in different location than it was at time of build, Set source map with `settings set target.source-map`. More details [here](https://werat.dev/blog/debugging-lldb-with-source-stepping/).

## Tips and Tricks

### Attaching the Debugger at Application Start

Insert endless loop in your application:

```c
volatile int quit = 0;

int main(int argc, char **argv)
{
    EFI_STATUS stat;
    EFI_LOADED_IMAGE_PROTOCOL *loaded_image;

    stat = efi_get_protocol(_efi_this_image_handle, &gEfiLoadedImageProtocolGuid, (void **)&loaded_image);
    if (EFI_ERROR(stat))
    {
        return stat;
    }

    efi_wprintf(L"Image has been loaded at %p\n", loaded_image->ImageBase);

    efi_wprintf(L"Now attach the debugger and set the 'quit' variable to a nonzero value...\n");

    while (!quit)
    {
    }

    ...
}
```

Once the debugger connects break into the target application (Ctrl+C) and set the `quit` variable to a non-zero value. Then resume the execution of the target.

```
(lldb) expression quit=1
(volatile int) $0 = 1
(lldb) continue
```

### Always Showing Disassembly

```
(lldb) set set stop-disassembly-display always
```

## Debugging the Debugger

Enable logging of various information.

```
(lldb) log list
(lldb) log enable gdb-remote packets
(lldb) log enable lldb all
```

## References

* [Debugging UEFI applications with GDB](https://wiki.osdev.org/Debugging_UEFI_applications_with_GDB)
* [Debugging Wine with LLDB and VSCode](https://werat.dev/blog/debugging-wine-with-lldb-and-vscode/)
* [Debugging LLDB with source stepping](https://werat.dev/blog/debugging-lldb-with-source-stepping/)
