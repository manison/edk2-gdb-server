#!/usr/bin/env python3

"""
"""

import udkserver
import gdbserver
import collections
import logging
import select
import serial
#import signal
#import sys
import io
import socket
import ctypes
import pefile
#import macholib
import xml.etree.ElementTree

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

#### This should be generated from the packaged gdb xmls eventually
# can be viewed in a running gdb with maint remote-registers
registers = {
    'rax': udkserver.Register.SOFT_DEBUGGER_REGISTER_AX,
    'rbx': udkserver.Register.SOFT_DEBUGGER_REGISTER_BX,
    'rcx': udkserver.Register.SOFT_DEBUGGER_REGISTER_CX,
    'rdx': udkserver.Register.SOFT_DEBUGGER_REGISTER_DX,
    'rsi': udkserver.Register.SOFT_DEBUGGER_REGISTER_SI,
    'rdi': udkserver.Register.SOFT_DEBUGGER_REGISTER_DI,
    'rbp': udkserver.Register.SOFT_DEBUGGER_REGISTER_BP,
    'rsp': udkserver.Register.SOFT_DEBUGGER_REGISTER_SP,

    'r8':  udkserver.Register.SOFT_DEBUGGER_REGISTER_R8,
    'r9':  udkserver.Register.SOFT_DEBUGGER_REGISTER_R9,
    'r10': udkserver.Register.SOFT_DEBUGGER_REGISTER_R10,
    'r11': udkserver.Register.SOFT_DEBUGGER_REGISTER_R11,
    'r12': udkserver.Register.SOFT_DEBUGGER_REGISTER_R12,
    'r13': udkserver.Register.SOFT_DEBUGGER_REGISTER_R13,
    'r14': udkserver.Register.SOFT_DEBUGGER_REGISTER_R14,
    'r15': udkserver.Register.SOFT_DEBUGGER_REGISTER_R15,

    'rip': udkserver.Register.SOFT_DEBUGGER_REGISTER_EIP,
    'eflags': udkserver.Register.SOFT_DEBUGGER_REGISTER_EFLAGS,

    'cs': udkserver.Register.SOFT_DEBUGGER_REGISTER_CS,
    'ss': udkserver.Register.SOFT_DEBUGGER_REGISTER_SS,
    'ds': udkserver.Register.SOFT_DEBUGGER_REGISTER_DS,
    'es': udkserver.Register.SOFT_DEBUGGER_REGISTER_ES,
    'fs': udkserver.Register.SOFT_DEBUGGER_REGISTER_FS,
    'gs': udkserver.Register.SOFT_DEBUGGER_REGISTER_GS,

    'st0': udkserver.Register.SOFT_DEBUGGER_REGISTER_ST0,
    'st1': udkserver.Register.SOFT_DEBUGGER_REGISTER_ST1,
    'st2': udkserver.Register.SOFT_DEBUGGER_REGISTER_ST2,
    'st3': udkserver.Register.SOFT_DEBUGGER_REGISTER_ST3,
    'st4': udkserver.Register.SOFT_DEBUGGER_REGISTER_ST4,
    'st5': udkserver.Register.SOFT_DEBUGGER_REGISTER_ST5,
    'st6': udkserver.Register.SOFT_DEBUGGER_REGISTER_ST6,
    'st7': udkserver.Register.SOFT_DEBUGGER_REGISTER_ST7,

    'fctrl': udkserver.Register.SOFT_DEBUGGER_REGISTER_FP_FCW,
    'fstat': udkserver.Register.SOFT_DEBUGGER_REGISTER_FP_FSW,
    'ftag': udkserver.Register.SOFT_DEBUGGER_REGISTER_FP_FTW,
    'fiseg': udkserver.Register.SOFT_DEBUGGER_REGISTER_FP_CS,
    'fioff': udkserver.Register.SOFT_DEBUGGER_REGISTER_FP_EIP,
    'foseg': udkserver.Register.SOFT_DEBUGGER_REGISTER_FP_DS,
    'fooff': udkserver.Register.SOFT_DEBUGGER_REGISTER_FP_DATAOFFSET,
    'fop': udkserver.Register.SOFT_DEBUGGER_REGISTER_FP_OPCODE,

    'xmm0': udkserver.Register.SOFT_DEBUGGER_REGISTER_XMM0,
    'xmm1': udkserver.Register.SOFT_DEBUGGER_REGISTER_XMM1,
    'xmm2': udkserver.Register.SOFT_DEBUGGER_REGISTER_XMM2,
    'xmm3': udkserver.Register.SOFT_DEBUGGER_REGISTER_XMM3,
    'xmm4': udkserver.Register.SOFT_DEBUGGER_REGISTER_XMM4,
    'xmm5': udkserver.Register.SOFT_DEBUGGER_REGISTER_XMM5,
    'xmm6': udkserver.Register.SOFT_DEBUGGER_REGISTER_XMM6,
    'xmm7': udkserver.Register.SOFT_DEBUGGER_REGISTER_XMM7,
    'xmm8': udkserver.Register.SOFT_DEBUGGER_REGISTER_XMM8,
    'xmm9': udkserver.Register.SOFT_DEBUGGER_REGISTER_XMM9,
    'xmm10': udkserver.Register.SOFT_DEBUGGER_REGISTER_XMM10,
    'xmm11': udkserver.Register.SOFT_DEBUGGER_REGISTER_XMM11,
    'xmm12': udkserver.Register.SOFT_DEBUGGER_REGISTER_XMM12,
    'xmm13': udkserver.Register.SOFT_DEBUGGER_REGISTER_XMM13,
    'xmm14': udkserver.Register.SOFT_DEBUGGER_REGISTER_XMM14,
    'xmm15': udkserver.Register.SOFT_DEBUGGER_REGISTER_XMM15,
}

class LoadedImageProtocol(ctypes.Structure):
    _fields_ = [('revision', ctypes.c_uint32),
                ('parent_handle', ctypes.c_uint64),
                ('system_table', ctypes.c_uint64),
                ('device_handle', ctypes.c_uint64),
                ('file_path', ctypes.c_uint64),
                ('reserved', ctypes.c_uint64),
                ('load_options_size', ctypes.c_uint32),
                ('load_options', ctypes.c_uint64),
                ('image_base', ctypes.c_uint64),
                ('image_size', ctypes.c_uint64),
                ('image_code_type', ctypes.c_uint8),
                ('image_data_type', ctypes.c_uint8),
                ('image_unload', ctypes.c_uint64)]


class PeCoffLoaderImageContext(ctypes.Structure):
    _pdb_name = None
    _fields_ = [('image_addr', ctypes.c_ulonglong),
                ('image_size', ctypes.c_ulonglong),
                ('destination_address', ctypes.c_ulonglong),
                ('entrypoint', ctypes.c_ulonglong),
                ('image_read', ctypes.c_ulonglong),
                ('handle', ctypes.c_ulonglong),
                ('fixup_data', ctypes.c_ulonglong),
                ('section_alignment', ctypes.c_ulong),
                ('pe_coff_header_offset', ctypes.c_ulong),
                ('debug_directory_entry_rva', ctypes.c_ulong),
                ('code_view', ctypes.c_ulonglong),
                ('pdb_pointer', ctypes.c_ulonglong),
                ('size_of_headers', ctypes.c_ulonglong),
                ('image_code_memory_type', ctypes.c_ulong),
                ('image_data_memory_type', ctypes.c_ulong),
                ('image_error', ctypes.c_ulong),
                ('fixup_data_size', ctypes.c_ulonglong),
                ('machine', ctypes.c_ushort),
                ('image_type', ctypes.c_ushort),
                ('relocations_stripped', ctypes.c_bool),
                ('is_te_image', ctypes.c_bool),
                ('hii_resource_data', ctypes.c_uint64),
                ]

    @property
    def pdb_name(self):
        return self._pdb_name

    @pdb_name.setter
    def pdb_name(self, pdb_name):
        self._pdb_name = pdb_name

class GUID(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('Data1', ctypes.c_uint32),
                ('Data2', ctypes.c_uint16),
                ('Data3', ctypes.c_uint16),
                ('Data4', ctypes.c_uint8 * 8)]

class CodeViewRSDSEntry(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('Signature', ctypes.c_char * 4),
                ('GUID', GUID),
                ('Age', ctypes.c_uint32)]

class LoadedImagePrivateData(ctypes.Structure):
    _fields_ = [('signature', ctypes.c_uint64),
                ('handle', ctypes.c_uint64),
                ('type', ctypes.c_uint64),
                ('started', ctypes.c_uint8),
                ('entrypoint', ctypes.c_uint64),
                ('info', LoadedImageProtocol),
                ('loaded_image_device_path', ctypes.c_uint64),
                ('image_base_page', ctypes.c_uint64),
                ('number_of_pages', ctypes.c_uint64),
                ('fixup_data', ctypes.c_uint64),
                ('tpl', ctypes.c_uint64),
                ('status', ctypes.c_uint64),
                ('exit_data_size', ctypes.c_uint64),
                ('exit_data', ctypes.c_uint64),
                ('jump_context', ctypes.c_uint64),
                ('machine', ctypes.c_uint16),
                ('ebc', ctypes.c_uint64),
                ('runtime_data', ctypes.c_uint64),
                ('image_context', PeCoffLoaderImageContext)]

class UdkGdbStub(gdbserver.GdbHostStub):
    def __init__(self, rsp, udk):
        super(UdkGdbStub, self).__init__(rsp)
        self.udk = udk

        #### UDK Extensions
        self.udk_extension_handlers = collections.defaultdict(dict)
        self.add_general_query_handler(b'UdkExtension', self.udk_extension)

        #### General UDK Extensions
        self.add_udk_extension_handlers(b'arch', self.udk_extension_arch)
        self.add_udk_extension_handlers(b'checkexpat', self.udk_extension_checkexpat)
        self.add_udk_extension_handlers(b'exception', self.udk_extension_exception)
        self.add_udk_extension_handlers(b'symbol', self.udk_extension_symbol)

        #### Loaded Modules UDK Extension
        self.add_udk_extension_handlers(b'fmodules', self.udk_extension_fmodules)
        self.add_udk_extension_handlers(b'smodules', self.udk_extension_smodules)

        self.add_feature(b'qXfer:features:read', True)
        self.add_feature(b'qXfer:libraries:read', True)

        self.reset()
        self.udk.connect(self)

    def reset(self):
        """Reset
        Called when the UDK Target Reboots to re-initialize any transient GDB state
        """
        logger.warn("target reset()")
        target = xml.etree.ElementTree.Element('target', version='1.0')
        architecture = xml.etree.ElementTree.SubElement(target, 'architecture')
        architecture.text = self.architecture
        target_xml = xml.etree.ElementTree.tostring(target, encoding='utf-8', method='xml')

        self.set_xml(b'features', b'target.xml', target_xml)

        self.libraries_xml = xml.etree.ElementTree.Element('library-list')
        self.set_xml(b'libraries', b'', xml.etree.ElementTree.tostring(self.libraries_xml, encoding='utf-8', method='xml'))
        for i, breakpoint in enumerate(self.breakpoints):
            if breakpoint.state == gdbserver.BreakpointState.BP_ACTIVE:
                breakpoint.state = gdbserver.BreakpointState.BP_SET
                breakpoint.first_byte = None
            elif breakpoint.state == gdbserver.BreakpointState.BP_REMOVED:
                del self.breakpoints[i]

    def add_library(self, library, segment, sections = None):
        """Add Library
        Called when the target loads shared library that should be recorded for GDB.
        """
        library = xml.etree.ElementTree.SubElement(self.libraries_xml, 'library', name = library)
        if not sections:
            xml.etree.ElementTree.SubElement(library, 'segment', address='0x{0:x}'.format(segment))
        else:
            for section in sections:
                xml.etree.ElementTree.SubElement(library, 'section', address='0x{0:x}'.format(section.address))
        self.set_xml(b'libraries', b'', xml.etree.ElementTree.tostring(self.libraries_xml, encoding='utf-8', method='xml'))

    def ensure_breakpoints(self):
        for i, breakpoint in enumerate(self.breakpoints):
            if breakpoint.state == gdbserver.BreakpointState.BP_SET:
                first_byte = self.udk.read_memory(breakpoint.address, 1, 1)
                if first_byte != b'\xcc':
                    breakpoint.first_byte = first_byte

                breakpoint.state = gdbserver.BreakpointState.BP_ACTIVE
                self.udk.write_memory(breakpoint.address, 1, 1, b'\xcc')
            elif breakpoint.state == gdbserver.BreakpointState.BP_ACTIVE:
                first_byte = self.udk.read_memory(breakpoint.address, 1, 1)
                if first_byte != b'\xcc':
                    logger.warn("breakpoint marked active but no deployed")
                breakpoint.state = gdbserver.BreakpointState.BP_SET
            elif breakpoint.state == gdbserver.BreakpointState.BP_REMOVED:
                first_byte = self.udk.read_memory(breakpoint.address, 1, 1)
                if first_byte != b'\xcc':
                    logger.warn("breakpoint marked removed but not active")
                elif breakpoint.first_byte:
                    self.udk.write_memory(breakpoint.address, 1, 1, breakpoint.first_byte)
                logger.warn("breakpoint marked removed but not active")
                del self.breakpoints[i]

    ##### GDB Target Stub Side
    ### Called by GDB to request the target continue execution
    def continue_execution_impl(self, address = None):
        self.ensure_breakpoints()
        self.udk.go()

    def continue_execution_with_signal_impl(self, signal, addr):
        if signal == 9:
            self.udk.reset()
            return True

        self.ensure_breakpoints()
        self.udk.go()

    def disconnect_impl(self):
        self.udk.detach()
        return False

    ### Called by GDB to request the break cause from the target
    def halt_reason_impl(self):
        return self.udk.handle_break_cause()

    def insert_breakpoint_impl(self, index, address, kind):
        logger.info("adding breakpoint: index: {}, address: {}".format(index, address))
        for breakpoint in self.breakpoints:
            if breakpoint.address == address:
                return
        breakpoint = gdbserver.Breakpoint(address)
        breakpoint.state = gdbserver.BreakpointState.BP_SET
        self.breakpoints.append(breakpoint)

    def remove_breakpoint_impl(self, index, address, kind):
        logger.info("removing breakpoint: index: {}, address: {}".format(index, address))
        for breakpoint in self.breakpoints:
            if breakpoint.address == address:
                breakpoint.state = gdbserver.BreakpointState.BP_REMOVED
        self.ensure_breakpoints()

    ### Called by GDB to request memory from the target
    def read_memory_impl(self, address, size):
        return self.udk.read_memory(address, 1, size)

    ### Called by GDB to request a single register from the target
    def read_register_impl(self, register):
        return self.udk.read_register(registers[register])

    ### Called by GDB to read the register state from the target
    def read_registers_impl(self, defaults):
        registers = self.udk.read_registers()
        registers['rip'] = registers['eip']
        registers['fctrl'] = registers['fcw']
        registers['fstat'] = registers['fcw']
        registers['ftag'] = registers['ftw']
        registers['fiseg'] = registers['fcs']
        registers['fioff'] = registers['fpu_ip']
        registers['foseg'] = registers['fds']
        registers['fooff'] = registers['fpu_dp']
        registers['st0'] = registers['st0mm0']
        registers['st1'] = registers['st1mm1']
        registers['st2'] = registers['st2mm2']
        registers['st3'] = registers['st3mm3']
        registers['st4'] = registers['st4mm4']
        registers['st5'] = registers['st5mm5']
        registers['st6'] = registers['st6mm6']
        registers['st7'] = registers['st7mm7']
        return registers

    ### Called by GDB to halt the target from running
    def send_break_impl(self):
        self.udk.halt()
        return self.udk.handle_break_cause()

    ### Called by GDB to request the target step a single instruction
    def step_instruction_impl(self):
        self.ensure_breakpoints()
        self.udk.single_stepping()
        return self.udk.handle_break_cause()

    ### Called by GDB to request the target step a single instruction
    def step_instruction_with_signal_impl(self, signal, addr):
        if signal == 9:
            self.udk.reset()
        self.ensure_breakpoints()
        self.udk.single_stepping()
        return self.udk.handle_break_cause()

    ### Called by GDB to write memory on the target
    def write_memory_impl(self, address, size, data):
        return self.udk.write_memory(address, 1, size, data)

    def write_register_impl(self, register_name, value):
        return self.udk.write_register(registers[register_name], value)

    #### GDB Protocol Extensions for UDK
    ###
    def add_udk_extension_handlers(self, command, handler):
        self.udk_extension_handlers[command] = handler

    def udk_extension(self, args):
        cmd = args
        args = None
        if b':' in cmd:
            cmd, args = cmd.split(b':', 2)

        try:
            self.udk_extension_handlers[cmd](args)
        except KeyError:
            self.rsp.send_packet(b'')

    def udk_extension_arch(self, args):
        self.rsp.send_packet(b'use64')

    def udk_extension_exception(self, args):
        (vector, error_code) = self.udk.get_exception()
        msg = '{0:x};{1:x}'.format(vector, error_code)
        self.rsp.send_packet(msg.encode('utf-8'))

    def udk_extension_next_module(self):
        try:
            first = next(self.libraries_iter)
            msg = '0x{0:x};0x{1:x};{2}'.format(first['image_context'].entrypoint,
                                               first['image_context'].image_addr,
                                               first['pdb_name'])
            self.rsp.send_packet(msg.encode('utf-8'))
        except StopIteration:
            self.rsp.send_packet(b'l')
            del self.libraries_iter
        except AttributeError:
            self.rsp.send_packet(b'l')

    def udk_extension_fmodules(self, args):
        self.libraries_iter = iter(self.udk.libraries)
        self.udk_extension_next_module()

    def udk_extension_smodules(self, args):
        if not hasattr(self, 'libraries_iter'):
            self.rsp.send_packet(b'E99')

        self.udk_extension_next_module()

    def udk_extension_symbol(self, args):
        address = int(args, 0)
        (pdb_name, image_addr, sections) = self.udk.symbol(address)
        if pdb_name is None:
            self.rsp.send_packet(b'E91')
            return

        msg = '{0};0x{1:x}'.format(pdb_name.decode('utf-8'), image_addr)
        text_sections = []
        for section in sections:
            text_sections.append('{0}=0x{1:x}'.format(section['name'].decode('utf-8'), section['address']))
        msg = msg + ';' + ';'.join(text_sections)
#        logger.debug(msg)
        self.rsp.send_packet(msg.encode('utf-8'))

    def udk_extension_checkexpat(self, args):
        if args == b'start':
            self.rsp.send_packet(b'OK')
        else:
            self.rsp.send_packet(b'E91')

class UdkStub(udkserver.UdkTargetStub):
    def __init__(self, target, server):
        super(UdkStub, self).__init__(target)
        self.images = {}
        self.server = server
        self.libraries = []
        self.gdb = None

    def connect(self, gdb):
        self.gdb = gdb
        for library in self.libraries:
            self.gdb.add_library(library['pdb_name'], library['text_section'], library['sections'])

    def search_image(self, address):
        image_search_start = address & 0xfffffffffffff000;
        image_search_end = image_search_start - 0x80000
        if image_search_end < 0:
            image_search_end = 0

        image_search = image_search_start
        # Max go back 512K
        while image_search > image_search_end:
            header = self.read_memory(image_search, 1, 2)
            if header == b'VZ' or header == b'MZ':
#                logger.debug(str(header))
                return image_search
            image_search = image_search - 0x1000
        return None

    def obtain_image(self, image_address):
        peheader = self.read_memory(image_address, 1, 0x600)
        pe = pefile.PE(data = peheader, fast_load = True)
        directory_index = pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_DEBUG']
        dir_entry = pe.OPTIONAL_HEADER.DATA_DIRECTORY[directory_index]
        peheader += b'\0' * (dir_entry.VirtualAddress - 0x600)
        peheader += self.read_memory(image_address + dir_entry.VirtualAddress, 1, dir_entry.Size)
        return peheader

    def symbol(self, address):
        image_address = self.search_image(address)
        if image_address is None:
            return (None, None, None)

        if not image_address in self.images:
            self.images[image_address] = self.obtain_image(image_address)

        image_data = self.images[image_address]

#        logger.debug('found PE32 image signature at: 0x{0:x}'.format(image_address))
        pdb_name = b''
        sections = []
        try:
            pe = pefile.PE(data = image_data, fast_load = True)
            pe.parse_data_directories(pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_DEBUG'])
#            logger.debug(pe.dump_info())
            for pesection in pe.sections:
                sections.append({'name': pesection.Name.strip(b'\x00'),
                                 'address': pesection.VirtualAddress + pe.OPTIONAL_HEADER.ImageBase})

            try:
                for entry in pe.DIRECTORY_ENTRY_DEBUG:
                    if entry.struct.Type == 2: # IMAGE TYPE CODEVIEW
                        off = entry.struct.PointerToRawData
                        size = entry.struct.SizeOfData
                        data = image_data[off:off+size]

                        cv = CodeViewRSDSEntry.from_buffer_copy(data)
                        if (cv.Signature == b'MTOC'):
                            pdb_name = data[20:].strip(b'\x00')
                        elif (cv.Signature == b'RSDS'):
                            pdb_name = data[24:].strip(b'\x00')
                        else:
                            logger.warn('Unknown debug signature {0:s}'.format(cv.Signature))
            except AttributeError:
                pdb_name = b'NoDebugData'
                pass

        except pefile.PEFormatError:
            pass
        return (pdb_name, image_address, sections)

    ##### UDK Host Side
    def handle_init_break(self, packet):
        super(UdkStub, self).handle_init_break(packet)
        self.server.start_socket()

    ### Called by UDK Server when memory is ready on the target
    def handle_memory_ready_impl(self):
        self.libraries = []
        self.images = {}
#        self.server.start_socket()
        if self.gdb:
            self.gdb.reset()

    ### Called by UDK Server when memory is ready on the target
    def handle_break_point_impl(self):
        (cause, nr) = self.handle_break_cause()
        try:
            self.gdb.rsp.send_stop_reply_packet(cause, nr)
        except AttributeError:
            pass

    ### Called to generate a response when the target is stopped at a SW breakpoint
    def handle_break_cause_sw_breakpoint_impl(self, stop_address):
        logger.debug('swbreak caused stop at address 0x{0:x}'.format(stop_address))
        return (5, {b'swbreak': b''})

    ### Called to generate a response when the target is stopped at a SW breakpoint
    def handle_break_cause_hw_breakpoint_impl(self, stop_address):
        return (5, {b'hwbreak': b''})

    ### Called to generate a response when the target is stopped due to image loading
    def handle_break_cause_image_load_impl(self, pdb_name_addr, image_context_addr):
        loaded_image_private_data_addr = image_context_addr - LoadedImagePrivateData.image_context.offset;
        loaded_image_private_data_buffer = self.read_memory(loaded_image_private_data_addr, 1, 512)
        loaded_image_private_data = LoadedImagePrivateData.from_buffer_copy(loaded_image_private_data_buffer)

        image_context = loaded_image_private_data.image_context

#        logger.debug('signature: 0x{0:x}'.format(loaded_image_private_data.signature))
        if loaded_image_private_data.signature == 0x6972646c:
            logger.debug('EDK_LOADED_IMAGE_PRIVATE_DATA:')
            logger.info('signature: 0x{0:x} entrypoint: 0x{1:x}, image_base_page: 0x{2:x}, number_of_pages: 0x{3:x}'
                .format(loaded_image_private_data.signature,
                        loaded_image_private_data.entrypoint,
                        loaded_image_private_data.image_base_page,
                        loaded_image_private_data.number_of_pages))

            logger.debug('EFI_LOADED_IMAGE_PROTOCOL:')
            logger.info('revision: 0x{0:x} image_base: 0x{1:x}, image_size: 0x{2:x}'
                .format(loaded_image_private_data.info.revision,
                        loaded_image_private_data.info.image_base,
                        loaded_image_private_data.info.image_size))

            if image_context.image_addr == 0x0:
                image_context.image_addr = loaded_image_private_data.info.image_base

            if image_context.image_size == 0x0:
                image_context.image_size = loaded_image_private_data.info.image_size

            if image_context.entrypoint == 0x0:
                image_context.entrypoint = loaded_image_private_data.entrypoint

        pdb_name = self.read_null_terminated_string(pdb_name_addr)
        if pdb_name.endswith('.dll'):
           pdb_name = pdb_name[:-4]
        if not pdb_name.endswith('.dll'):
            pdb_name += '.dll'


        logger.info('module {0} loaded at address 0x{1:x} with size 0x{2:x}'.format(pdb_name, image_context.image_addr, image_context.image_size))

        ### Get .text offset:
        # When specifying a segment address, GDB uses segment relocation code.
        # Whereas a PE32 has only a single segment, a Mach-O binary has 2 segments:
        # .text and .data. So, gdb expects the segment address to be the address of
        # the .text segment.
        offset = 0
        sections = []
        peheader = self.read_memory(image_context.image_addr, 1, 1024)
        try:
            pe = pefile.PE(data = peheader)
            for pesection in pe.sections:
                if pesection.Name.strip(b'\x00') == b'.text':
                    offset = pesection.VirtualAddress

#                section = gdbserver.Section(pesection.Name.strip(b'\x00'),
#                                            pesection.VirtualAddress + image_context.image_addr,
#                                            pesection.Misc_VirtualSize)
#                if section.name == b'.text' or \
#                   section.name == b'.data':
#                    sections.append(section)
#
#                logger.info('module {0} section {1!s} loaded at address 0x{2:x} with size 0x{3:x}'.format(pdb_name, section.name, image_context.image_addr + section.address, section.length))
        except pefile.PEFormatError:
            pass

        self.libraries.append({'pdb_name': pdb_name,
                               'image_context': image_context,
                               'text_section': image_context.image_addr + offset,
                               'sections': sections})
        if self.gdb:
            self.gdb.add_library(pdb_name, image_context.image_addr + offset, sections)

        return (5, {b'library': b''})

    def handle_break_cause_stepping_impl(self, stop_address):
        return (5, {})

    ### Called by UDK Server when a SW breakpoint occurs on the target
    def handle_break_cause_exception_impl(self, stop_addres, vector, data):
        return (4, {})


class UdkGdbServer():
    def __init__(self, serial_name = '/dev/cu.usbmodem357', host = '0.0.0.0', port = 1234):
        self._serial_name = serial_name
        self._serial = None

        self._host = host
        self._port = port
        self._socket = None

        self._poll = select.poll()
        self._poll_handlers = {}

        self.udk = None

    def add_poll_fd(self, fd, handler):
        self._poll.register(fd, select.POLLIN)
        self._poll_handlers[fd] = handler

    def remove_poll_fd(self, fd):
        self._poll.unregister(fd)
        del self._poll_handlers[fd]

    def start_serial(self):
        ### Initialize the Serial port
        self._serial = serial.Serial(self._serial_name)
        self._serial.reset_input_buffer()
        self._serial.reset_output_buffer()
        self.udk = udkserver.UdkTarget(self._serial, UdkStub, self)
        self.add_poll_fd(self._serial.fileno(), self.udk.command_communication)

    def socket_handler(self):
        self.connection, self.remote_addr = self._socket.accept()
        self.gdb = gdbserver.GdbRemoteSerialProtocol(self.connection.makefile('rwb', buffering = 0), UdkGdbStub, self.udk.stub)
        self.add_poll_fd(self.connection.fileno(), self.gdb.command_communication)
        logger.info("Received a connection from {}".format(self.remote_addr))

    def start_socket(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((self._host, self._port))
        self._socket.listen(0)
        self.add_poll_fd(self._socket.fileno(), self.socket_handler)
        logger.info("Listening on {}:{} for connections".format(self._host, self._port))

    def run(self):
#        def signal_handler(signal, frame):
#            sys.exit(0)

        self.start_serial()

#        signal.signal(signal.SIGINT, signal_handler)
#        signal.pause()

        while True:
            for (fd, event) in self._poll.poll():
                if event & (select.POLLHUP | select.POLLERR | select.POLLNVAL):
                    self.remove_poll_fd(fd)
                    self.gdb = None
                    continue

                elif not event & select.POLLIN:
                    logger.error("unknown poll event occurred {}".format(str(event)))
                    raise Exception

                if fd not in self._poll_handlers:
                    raise Exception("unknown fd raised poll event")

                try:
                    status = self._poll_handlers[fd]()
                    if status is False:
                        logger.warning("Disconnected handler.")
                        self.remove_poll_fd(fd)
                except udkserver.AbortError:
                    pass

if __name__ == "__main__":
    udk_gdb_server = UdkGdbServer()
    udk_gdb_server.run()
