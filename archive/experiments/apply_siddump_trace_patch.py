#!/usr/bin/env python3
"""
Automatically patch siddump source files to add memory tracing.
"""

import os
import sys

def patch_cpu_c():
    """Patch cpu.c to add memory read tracking."""
    print("Patching cpu.c...")

    with open('tools/cpu.c', 'r') as f:
        content = f.read()

    # Add includes and externs after the initial includes
    if 'extern int trace_enabled' not in content:
        includes = '''#include <stdio.h>
#include <stdlib.h>

// Memory trace globals (defined in siddump.c)
extern int trace_enabled;
extern int trace_frame;
extern FILE *trace_log;
'''
        content = content.replace(
            '#include <stdio.h>\n#include <stdlib.h>',
            includes
        )

    # Replace MEM macro
    if 'mem_read_tracked' not in content:
        tracked_function = '''
// Tracked memory read function
static inline unsigned char mem_read_tracked(unsigned short address)
{
  extern unsigned char mem[];
  extern unsigned short pc;
  unsigned char value = mem[address];

  // Log reads in music data range ($1800-$1C00) during first 10 frames
  if (trace_enabled && trace_log && trace_frame >= 0 && trace_frame < 10)
  {
    if (address >= 0x1800 && address < 0x1C00)
    {
      fprintf(trace_log, "F%02d PC:%04X -> [%04X]=%02X\\n",
              trace_frame, pc, address, value);
      fflush(trace_log);
    }
  }

  return value;
}

// Replace direct memory access with tracked version
#define MEM(address) mem_read_tracked(address)

/* Original:
'''
        content = content.replace(
            '#define MEM(address) (mem[address])',
            tracked_function + '#define MEM(address) (mem[address])\n*/'
        )

    with open('tools/cpu.c', 'w') as f:
        f.write(content)

    print("  cpu.c patched successfully")

def patch_cpu_h():
    """Patch cpu.h to add extern declarations."""
    print("Patching cpu.h...")

    with open('tools/cpu.h', 'r') as f:
        content = f.read()

    if 'extern int trace_enabled' not in content:
        # Find where to insert (after existing externs)
        insert_pos = content.find('extern unsigned char sp;')
        if insert_pos > 0:
            insert_pos = content.find('\n', insert_pos) + 1
            trace_externs = '''
// Memory trace externs
extern int trace_enabled;
extern int trace_frame;
extern FILE *trace_log;
'''
            content = content[:insert_pos] + trace_externs + content[insert_pos:]

    with open('tools/cpu.h', 'w') as f:
        f.write(content)

    print("  cpu.h patched successfully")

def patch_siddump_c():
    """Patch siddump.c to add trace option and globals."""
    print("Patching siddump.c...")

    with open('tools/siddump.c', 'r') as f:
        content = f.read()

    # Add globals after includes
    if 'int trace_enabled' not in content:
        globals_code = '''
// Memory trace globals
int trace_enabled = 0;
int trace_frame = -1;
FILE *trace_log = NULL;
'''
        # Insert after #include "cpu.h"
        content = content.replace(
            '#include "cpu.h"',
            '#include "cpu.h"\n' + globals_code
        )

    # Add -trace option parsing
    if 'strcmp(argv[c], "-trace")' not in content:
        # Find usage section and add before it
        usage_pos = content.find('printf("Usage:')
        if usage_pos > 0:
            # Find the beginning of that code block
            block_start = content.rfind('if', 0, usage_pos)
            trace_option = '''
  // Check for -trace option
  for (c = 1; c < argc; c++)
  {
    if (!strcmp(argv[c], "-trace"))
    {
      trace_log = fopen("siddump_trace.txt", "w");
      trace_enabled = 1;
      if (trace_log)
      {
        fprintf(trace_log, "SIDDUMP MEMORY TRACE\\n");
        fprintf(trace_log, "Format: Frame PC MemAddr Value\\n\\n");
      }
    }
  }

  '''
            content = content[:block_start] + trace_option + content[block_start:]

    # Add trace_frame assignment in play loop
    if 'trace_frame = ' not in content:
        # Find cpuexecute(playaddress)
        play_call = content.find('cpuexecute(playaddress)')
        if play_call > 0:
            # Add before it
            line_start = content.rfind('\n', 0, play_call) + 1
            trace_set = '''      trace_frame = frames;
'''
            content = content[:line_start] + trace_set + content[line_start:]

    # Add cleanup at end
    if 'if (trace_log)' not in content or content.count('if (trace_log)') < 2:
        # Add before final return 0
        return_pos = content.rfind('return 0;')
        if return_pos > 0:
            cleanup = '''
  if (trace_log)
  {
    fclose(trace_log);
  }

'''
            line_start = content.rfind('\n', 0, return_pos) + 1
            content = content[:line_start] + cleanup + content[line_start:]

    with open('tools/siddump.c', 'w') as f:
        f.write(content)

    print("  siddump.c patched successfully")

def main():
    print("=" * 60)
    print("SIDDUMP TRACE PATCHER")
    print("=" * 60)
    print()

    # Check if we're in the right directory
    if not os.path.exists('tools/siddump.c'):
        print("ERROR: tools/siddump.c not found!")
        print("Please run this script from the SIDM2 directory")
        return 1

    try:
        patch_cpu_c()
        patch_cpu_h()
        patch_siddump_c()

        print()
        print("=" * 60)
        print("SUCCESS!")
        print("=" * 60)
        print()
        print("All files patched successfully!")
        print()
        print("Next steps:")
        print("1. cd tools")
        print("2. gcc -o siddump_trace.exe siddump.c cpu.c -lm -O2")
        print("3. siddump_trace.exe -trace SID/file.sid -t1")
        print()

        return 0

    except Exception as e:
        print(f"\nERROR: {e}")
        print("\nSomething went wrong. Try manual patching instead.")
        print("See: tools/BUILD_SIDDUMP_TRACE.md")
        return 1

if __name__ == '__main__':
    sys.exit(main())
