#include <stdio.h>
#include <stdlib.h>

#define FN 0x80
#define FV 0x40
#define FB 0x10
#define FD 0x08
#define FI 0x04
#define FZ 0x02
#define FC 0x01

// Memory read tracking
extern int trace_reads;
extern int current_frame;
extern FILE *trace_file;

// Track memory reads in interesting regions (skip I/O and ROM)
static inline unsigned char tracked_read(unsigned short address, unsigned char *mem)
{
  unsigned char value = mem[address];

  // Only trace if enabled and address is in interesting range
  // Skip: zero page (0x00-0xFF), stack (0x100-0x1FF), I/O (0xD000+)
  if (trace_reads && trace_file &&
      address >= 0x1000 && address < 0xD000) {
    fprintf(trace_file, "R:%04X:%02X ", address, value);
  }

  return value;
}

#define MEM(address) (traced_read(address, mem))
#define LO() (MEM(pc))
#define HI() (MEM(pc+1))
#define FETCH() (MEM(pc++))
#define SETPC(newpc) (pc = (newpc))
#define PUSH(data) (mem[0x100 + (sp--)] = (data))
#define POP() (mem[0x100 + (++sp)])

#define IMMEDIATE() (LO())
#define ABSOLUTE() (LO() | (HI() << 8))
#define ABSOLUTEX() (((LO() | (HI() << 8)) + x) & 0xffff)
#define ABSOLUTEY() (((LO() | (HI() << 8)) + y) & 0xffff)
#define ZEROPAGE() (LO() & 0xff)
#define ZEROPAGEX() ((LO() + x) & 0xff)
#define ZEROPAGEY() ((LO() + y) & 0xff)
#define INDIRECTX() (MEM((LO() + x) & 0xff) | (MEM((LO() + x + 1) & 0xff) << 8))
#define INDIRECTY() (((MEM(LO()) | (MEM((LO() + 1) & 0xff) << 8)) + y) & 0xffff)
#define INDIRECTZP() (((MEM(LO()) | (MEM((LO() + 1) & 0xff) << 8)) + 0) & 0xffff)

#define WRITE(address)                  \
{                                       \
  /* cpuwritemap[(address) >> 6] = 1; */  \
}

#define EVALPAGECROSSING(baseaddr, realaddr) ((((baseaddr) ^ (realaddr)) & 0xff00) ? 1 : 0)
#define EVALPAGECROSSING_ABSOLUTEX() (EVALPAGECROSSING(ABSOLUTE(), ABSOLUTEX()))
#define EVALPAGECROSSING_ABSOLUTEY() (EVALPAGECROSSING(ABSOLUTE(), ABSOLUTEY()))
#define EVALPAGECROSSING_INDIRECTY() (EVALPAGECROSSING(INDIRECTZP(), INDIRECTY()))

#define BRANCH()                                          \
{                                                         \
  ++cpucycles;                                            \
  temp = FETCH();                                         \
  if (temp < 0x80)                                        \
  {                                                       \
    cpucycles += EVALPAGECROSSING(pc, pc + temp);         \
    SETPC(pc + temp);                                     \
  }                                                       \
  else                                                    \
  {                                                       \
    cpucycles += EVALPAGECROSSING(pc, pc + temp - 0x100); \
    SETPC(pc + temp - 0x100);                             \
  }                                                       \
}

#define SETFLAGS(data)                  \
{                                       \
  if (!(data))                          \
    flags = (flags & ~FN) | FZ;         \
  else                                  \
    flags = (flags & ~(FN|FZ)) |        \
    ((data) & FN);                      \
}

#define ASSIGNSETFLAGS(dest, data)      \
{                                       \
  dest = data;                          \
  if (!dest)                            \
    flags = (flags & ~FN) | FZ;         \
  else                                  \
    flags = (flags & ~(FN|FZ)) |        \
    (dest & FN);                        \
}

// Rest of CPU implementation continues...
// (The rest would be copied from cpu.c - this shows the key modification)

// Wrapper function to be called from other files
unsigned char traced_read(unsigned short address, unsigned char *mem)
{
  return tracked_read(address, mem);
}
