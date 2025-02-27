"""
RiscEmu (c) 2021-2022 Anton Lydike

SPDX-License-Identifier: MIT

This file contains the CPU logic (not the individual instruction sets). See instructions/instruction_set.py for more info
on them.
"""
import typing
from typing import List, Type

import riscemu
from .config import RunConfig
from .MMU import MMU
from .colors import FMT_CPU, FMT_NONE, FMT_ERROR
from .debug import launch_debug_session
from .types.exceptions import RiscemuBaseException, LaunchDebuggerException, StackOverflowException
from .syscall import SyscallInterface, get_syscall_symbols
from .types import CPU, ProgramLoader, Int32, BinaryDataMemorySection
from .parser import AssemblyFileLoader

if typing.TYPE_CHECKING:
    from .instructions.instruction_set import InstructionSet


class UserModeCPU(CPU):
    """
    This class represents a single CPU. It holds references to it's mmu, registers and syscall interrupt handler.

    It is initialized with a configuration and a list of instruction sets.
    """

    def __init__(self, instruction_sets: List[Type['riscemu.InstructionSet']], conf: RunConfig):
        """
        Creates a CPU instance.

        :param instruction_sets: A list of instruction set classes. These must inherit from the InstructionSet class
        """
        # setup CPU states
        super().__init__(MMU(), instruction_sets, conf)

        self.exit_code = 0

        # setup syscall interface
        self.syscall_int = SyscallInterface()

        # add global syscall symbols, but don't overwrite any user-defined symbols
        syscall_symbols = get_syscall_symbols()
        syscall_symbols.update(self.mmu.global_symbols)
        self.mmu.global_symbols.update(syscall_symbols)

    def step(self, verbose=False):
        """
        Execute a single instruction, then return.
        """
        if self.halted:
            print(FMT_CPU + "[CPU] Program exited with code {}".format(self.exit_code) + FMT_NONE)
            return

        launch_debugger = False

        try:
            if self.regs.get('sp') < self.conf.stack_size - 4096:
                raise StackOverflowException("You have run out of space on the stack. This is likely due to infinite recursion or improper stack discipline.")
            self.cycle += 1
            ins = self.mmu.read_ins(self.pc)
            if verbose:
                print(FMT_CPU + "   Running 0x{:08X}:{} {}".format(self.pc, FMT_NONE, ins))
            self.pc += self.INS_XLEN
            self.run_instruction(ins)
        except RiscemuBaseException as ex:
            if isinstance(ex, LaunchDebuggerException):
                # if the debugger is active, raise the exception to
                if self.debugger_active:
                    raise ex

                print(FMT_CPU + '[CPU] Debugger launch requested!' + FMT_NONE)
                launch_debugger = True
            else:
                print(ex.message())
                ex.print_stacktrace()
                print(FMT_CPU + '[CPU] Halting due to exception!' + FMT_NONE)
                self.halted = True

        if launch_debugger:
            launch_debug_session(self)

    def run(self, verbose=False):
        while not self.halted:
            self.step(verbose)

        if self.conf.verbosity > 0:
            print(FMT_CPU + "[CPU] Program exited with code {}".format(self.exit_code) + FMT_NONE)

    def setup_stack(self, stack_size=1024 * 4) -> bool:
        """
        Create program stack and populate stack pointer
        :param stack_size: the size of the required stack, defaults to 4Kib
        :return:
        """
        stack_sec = BinaryDataMemorySection(
            bytearray(stack_size),
            '.stack',
            None,  # FIXME: why does a binary data memory section require a context?
            '',
            0
        )
        if not self.mmu.load_section(stack_sec, fixed_position=False):
            print(FMT_ERROR + "[CPU] Could not insert stack section!" + FMT_NONE)
            return False

        self.regs.set('sp', Int32(stack_sec.base + stack_sec.size))

        if self.conf.verbosity > 1:
            print(FMT_CPU + "[CPU] Created stack of size {} at 0x{:x}".format(
                stack_size, stack_sec.base
            ) + FMT_NONE)

        #ABSOLUTELY NOT STACK!
        gpio_sec = BinaryDataMemorySection(
            bytearray(200),
            '.gpio',
            None,  # FIXME: why does a binary data memory section require a context?
            '',
            0x60004000
        )
        io_sec = BinaryDataMemorySection(
            bytearray(200),
            '.io',
            None,  # FIXME: why does a binary data memory section require a context?
            '',
            0x60009000
        )
        if not self.mmu.load_section(gpio_sec, fixed_position=True):
            print(FMT_ERROR + "[CPU] Could not insert gpio section!" + FMT_NONE)
            return False
        if not self.mmu.load_section(io_sec, fixed_position=True):
            print(FMT_ERROR + "[CPU] Could not insert io section!" + FMT_NONE)
            return False

        return True

    @classmethod
    def get_loaders(cls) -> typing.Iterable[Type[ProgramLoader]]:
        return [AssemblyFileLoader]
