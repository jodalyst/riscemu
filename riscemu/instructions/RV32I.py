"""
RiscEmu (c) 2021 Anton Lydike

SPDX-License-Identifier: MIT
"""

from .instruction_set import *
from ..CPU import UserModeCPU

from ..colors import FMT_DEBUG, FMT_NONE
from riscemu.types.exceptions import LaunchDebuggerException
from ..syscall import Syscall
from ..types import Instruction, Int32, UInt32


class RV32I(InstructionSet):
    """
    The RV32I instruction set. Some instructions are missing, such as
    fence, fence.i, rdcycle, rdcycleh, rdtime, rdtimeh, rdinstret, rdinstreth
    All atomic read/writes are also not implemented yet

    See https://maxvytech.com/images/RV32I-11-2018.pdf for a more detailed overview
    """

    def instruction_lb(self, ins: 'Instruction'):

        rd, addr = self.parse_mem_ins(ins)
        self.regs.set(rd, Int32.sign_extend(self.mmu.read(addr.unsigned_value, 1), 8))

    def instruction_lh(self, ins: 'Instruction'):
        rd, addr = self.parse_mem_ins(ins)
        self.regs.set(rd, Int32.sign_extend(self.mmu.read(addr.unsigned_value, 2), 16))

    def instruction_lw(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3) # this is how we teach it
        rd, addr = self.parse_mem_ins(ins)
        ASSERT_WORD_ALIGNED(addr.unsigned_value, "lw {}, {}({})".format(ins.get_reg(0), ins.get_imm(2), ins.get_reg(1)))
        self.regs.set(rd, Int32(self.mmu.read(addr.unsigned_value, 4)))

    def instruction_lbu(self, ins: 'Instruction'):
        rd, addr = self.parse_mem_ins(ins)
        self.regs.set(rd, Int32(self.mmu.read(addr.unsigned_value, 1)))

    def instruction_lhu(self, ins: 'Instruction'):
        rd, addr = self.parse_mem_ins(ins)
        self.regs.set(rd, Int32(self.mmu.read(addr.unsigned_value, 2)))

    def instruction_sb(self, ins: 'Instruction'):
        rd, addr = self.parse_mem_ins(ins)
        self.mmu.write(addr.unsigned_value, 1, self.regs.get(rd).to_bytes(1))

    def instruction_sh(self, ins: 'Instruction'):
        rd, addr = self.parse_mem_ins(ins)
        self.mmu.write(addr.unsigned_value, 2, self.regs.get(rd).to_bytes(2))

    def instruction_sw(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3) # this is how we do it
        rd, addr = self.parse_mem_ins(ins)
        ASSERT_WORD_ALIGNED(addr.unsigned_value, "sw {}, {}({})".format(ins.get_reg(0), ins.get_imm(2), ins.get_reg(1)))
        self.mmu.write(addr.unsigned_value, 4, self.regs.get(rd).to_bytes(4))

    def instruction_sll(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3)
        dst = ins.get_reg(0)
        src1 = ins.get_reg(1)
        src2 = ins.get_reg(2)
        self.regs.set(
            dst,
            self.regs.get(src1) << (self.regs.get(src2) & 0b11111)
        )

    def instruction_slli(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3)
        dst = ins.get_reg(0)
        src1 = ins.get_reg(1)
        imm = ins.get_imm(2)
        self.regs.set(
            dst,
            self.regs.get(src1) << (imm & 0b11111)
        )

    def instruction_srl(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3)
        dst = ins.get_reg(0)
        src1 = ins.get_reg(1)
        src2 = ins.get_reg(2)
        self.regs.set(
            dst,
            self.regs.get(src1).shift_right_logical(self.regs.get(src2) & 0b11111)
        )

    def instruction_srli(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3)
        dst = ins.get_reg(0)
        src1 = ins.get_reg(1)
        imm = ins.get_imm(2)
        self.regs.set(
            dst,
            self.regs.get(src1).shift_right_logical(imm & 0b11111)
        )

    def instruction_sra(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3)
        dst = ins.get_reg(0)
        src1 = ins.get_reg(1)
        src2 = ins.get_reg(2)
        self.regs.set(
            dst,
            Int32(self.regs.get(src1)) >> (self.regs.get(src2) & 0b11111)
        )

    def instruction_srai(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3)
        dst = ins.get_reg(0)
        src1 = ins.get_reg(1)
        imm = ins.get_imm(2)
        self.regs.set(
            dst,
            Int32(self.regs.get(src1)) >> (imm & 0b11111)
        )

    def instruction_add(self, ins: 'Instruction'):
        # FIXME: once configuration is figured out, add flag to support immediate arg in add instruction
        ASSERT_LEN(ins.args, 3)
        dst, rs1, rs2 = self.parse_rd_rs_rs(ins)

        self.regs.set(
            dst,
            rs1 + rs2
        )

    def instruction_addi(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3)
        dst, rs1, imm = self.parse_rd_rs_imm(ins)
        self.regs.set(
            dst,
            rs1 + imm
        )

    def instruction_sub(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3)
        dst, rs1, rs2 = self.parse_rd_rs_rs(ins)
        self.regs.set(
            dst,
            rs1 - rs2
        )

    def instruction_lui(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 2)
        ASSERT_IMM_LEN(ins.get_imm(1),20,False)
        reg = ins.get_reg(0)
        imm = UInt32(ins.get_imm(1) << 12)
        self.regs.set(reg, Int32(imm))

    def instruction_auipc(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 2)
        reg = ins.get_reg(0)
        imm = UInt32(ins.get_imm(1) << 12)
        self.regs.set(reg, imm.signed() + self.pc)

    def instruction_xor(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3)
        rd, rs1, rs2 = self.parse_rd_rs_rs(ins)
        self.regs.set(
            rd,
            rs1 ^ rs2
        )

    def instruction_xori(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3)
        rd, rs1, imm = self.parse_rd_rs_imm(ins)
        self.regs.set(
            rd,
            rs1 ^ imm
        )

    def instruction_or(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3)
        rd, rs1, rs2 = self.parse_rd_rs_rs(ins)
        self.regs.set(
            rd,
            rs1 | rs2
        )

    def instruction_ori(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3)
        rd, rs1, imm = self.parse_rd_rs_imm(ins)
        self.regs.set(
            rd,
            rs1 | imm
        )

    def instruction_and(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3)
        rd, rs1, rs2 = self.parse_rd_rs_rs(ins)
        self.regs.set(
            rd,
            rs1 & rs2
        )

    def instruction_andi(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3)
        rd, rs1, imm = self.parse_rd_rs_imm(ins)
        self.regs.set(
            rd,
            rs1 & imm
        )

    def instruction_slt(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3)
        rd, rs1, rs2 = self.parse_rd_rs_rs(ins)
        self.regs.set(
            rd,
            Int32(int(rs1 < rs2))
        )

    def instruction_slti(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3)
        rd, rs1, imm = self.parse_rd_rs_imm(ins)
        #print(f"rs1:{rs1} and imm: {imm}")
        self.regs.set(
            rd,
            Int32(int(rs1 < imm))
        )

    def instruction_sltu(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3)
        dst, rs1, rs2 = self.parse_rd_rs_rs(ins, signed=False)
        self.regs.set(
            dst,
            Int32(int(rs1 < rs2))
        )

    def instruction_sltiu(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3)
        dst, rs1, imm = self.parse_rd_rs_imm(ins, signed=False)
        #print(f"rs1:{rs1} and imm: {imm}")
        self.regs.set(
            dst,
            Int32(int(rs1 < imm))
        )

    def instruction_beq(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3)
        rs1, rs2, dst = self.parse_rs_rs_imm(ins)
        if rs1 == rs2:
            self.pc = dst.unsigned_value

    def instruction_bne(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3)
        rs1, rs2, dst = self.parse_rs_rs_imm(ins)
        if rs1 != rs2:
            self.pc = dst.unsigned_value

    def instruction_blt(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3)
        rs1, rs2, dst = self.parse_rs_rs_imm(ins)
        if rs1 < rs2:
            self.pc = dst.unsigned_value

    def instruction_bge(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3)
        rs1, rs2, dst = self.parse_rs_rs_imm(ins)
        if rs1 >= rs2:
            self.pc = dst.unsigned_value

    def instruction_bltu(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3)
        rs1, rs2, dst = self.parse_rs_rs_imm(ins, signed=False)
        if rs1 < rs2:
            self.pc = dst.unsigned_value

    def instruction_bgeu(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3)
        rs1, rs2, dst = self.parse_rs_rs_imm(ins, signed=False)
        if rs1 >= rs2:
            self.pc = dst.unsigned_value

    # technically deprecated
    def instruction_j(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 1)
        addr = ins.get_imm(0)
        self.pc = addr

    def instruction_jal(self, ins: 'Instruction'):
        reg = 'ra'  # default register is ra
        if len(ins.args) == 1:
            addr = ins.get_imm(0)
        else:
            ASSERT_LEN(ins.args, 2)
            reg = ins.get_reg(0)
            addr = ins.get_imm(1)
        self.regs.set(reg, Int32(self.pc))
        self.pc = addr

    # zero pseudo-ops:
    #beqz, bnez, bltz, bgez, bgtz, blez

    def instruction_beqz(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 2)
        rs1 = ins.get_reg(0)
        dst = ins.get_imm(1)
        if Int32(self.regs.get(rs1)) == 0:
            self.pc = dst

    def instruction_bnez(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 2)
        rs1 = ins.get_reg(0)
        dst = ins.get_imm(1)
        if Int32(self.regs.get(rs1)) != 0:
            self.pc = dst

    def instruction_bltz(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 2)
        rs1 = ins.get_reg(0)
        dst = ins.get_imm(1)
        if Int32(self.regs.get(rs1)) < 0:
            self.pc = dst

    def instruction_bgtz(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 2)
        rs1 = ins.get_reg(0)
        dst = ins.get_imm(1)
        if Int32(self.regs.get(rs1)) > 0:
            self.pc = dst

    def instruction_bgez(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 2)
        rs1 = ins.get_reg(0)
        dst = ins.get_imm(1)
        if Int32(self.regs.get(rs1)) >= 0:
            self.pc = dst

    def instruction_blez(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 2)
        rs1 = ins.get_reg(0)
        dst = ins.get_imm(1)
        if Int32(self.regs.get(rs1)) <= 0:
            self.pc = dst

    #pseudo instructions bgt ble bgtu bleu

    def instruction_bgt(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3)
        rs1, rs2, dst = self.parse_rs_rs_imm(ins)
        if rs1 > rs2:
            self.pc = dst.unsigned_value

    def instruction_ble(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3)
        rs1, rs2, dst = self.parse_rs_rs_imm(ins)
        if rs1 <= rs2:
            self.pc = dst.unsigned_value

    def instruction_bgtu(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3)
        rs1, rs2, dst = self.parse_rs_rs_imm(ins, signed=False)
        if rs1 > rs2:
            self.pc = dst.unsigned_value

    def instruction_bleu(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 3)
        rs1, rs2, dst = self.parse_rs_rs_imm(ins, signed=False)
        if rs1 <= rs2:
            self.pc = dst.unsigned_value

    #jds pseudo-op
    def instruction_call(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 1)
        addr = ins.get_imm(0)
        self.regs.set('ra', Int32(self.pc))
        self.pc = addr

    #jds pseudo-op
    def instruction_jr(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 1)
        reg = ins.get_reg(0)
        val = self.regs.get(reg)
        thing = val&(0xFFFFFFFE)
        #self.regs.set(reg, self.pc)
        self.pc = thing

    #modified by jds
    def instruction_jalr(self, ins: 'Instruction'):
        reg = 'ra'  # default register is ra
        if len(ins.args) == 1:
            addr = ins.get_reg(0)
            thing = self.regs.get(addr)
            addr = thing #&(0xFFFFFFFE)
        else:
            #ASSERT_LEN(ins.args, 2)
            reg, addr = self.parse_mem_ins(ins)
            #reg = ins.get_reg(0)
            #addr = ins.get_imm(1)
            #thing = self.regs.get(addr)
            #addr = addr&(0xFFFFFFFE)
            #reg = ins.get_reg(0)
            #addr = ins.get_imm(1)
        self.regs.set(reg, Int32(self.pc))
        self.pc = addr

    '''
    def instruction_jalr(self, ins: 'Instruction'):
        print(ins.args)
        ASSERT_LEN(ins.args, 2)
        reg = ins.get_reg(0)
        addr = ins.get_imm(1)
        self.regs.set(reg, Int32(self.pc))
        self.pc = addr
    '''

    def instruction_ret(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 0)
        self.pc = self.regs.get('ra').value

    def instruction_ecall(self, ins: 'Instruction'):
        self.instruction_scall(ins)

    def instruction_ebreak(self, ins: 'Instruction'):
        self.instruction_sbreak(ins)

    def instruction_scall(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 0)

        if not isinstance(self.cpu, UserModeCPU):
            # FIXME: add exception for syscall not supported or something
            raise

        syscall = Syscall(self.regs.get('utilreg'), self.cpu)
        self.cpu.syscall_int.handle_syscall(syscall)

    def instruction_sbreak(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 0)

        print(FMT_DEBUG + "Debug instruction encountered at 0x{:08X}".format(self.pc - 1) + FMT_NONE)
        raise LaunchDebuggerException()

    def instruction_nop(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 0)
        pass

    def instruction_li(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 2)
        reg = ins.get_reg(0)
        immediate = ins.get_imm(1)
        self.regs.set(reg, Int32(immediate))

    def instruction_la(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 2)
        reg = ins.get_reg(0)
        immediate = ins.get_imm(1)
        self.regs.set(reg, Int32(immediate))

    def instruction_mv(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 2)
        rd, rs = ins.get_reg(0), ins.get_reg(1)
        self.regs.set(rd, self.regs.get(rs))

    def instruction_neg(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 2)
        rd, rs = ins.get_reg(0), ins.get_reg(1)
        self.regs.set(rd, Int32(0)-self.regs.get(rs))

    def instruction_not(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 2)
        rd, rs = ins.get_reg(0), ins.get_reg(1)
        self.regs.set(rd, Int32(-1) ^ self.regs.get(rs))

    # Add instructions to start/stop state saving for catsoop debug
    def instruction_startlog(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 0)
        pass # nop
    
    def instruction_stoplog(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 0)
        pass # nop

    # Add instruction for catsoop debug breakpoint
    def instruction_csbreak(self, ins: 'Instruction'):
        ASSERT_LEN(ins.args, 0)
        pass # stuff happens on the js side