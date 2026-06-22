// sidm2_sid_trace.zig
// Loads a Laxity NP21 SID .prg file, calls INIT then runs N frames,
// collecting all SID register writes per frame. Outputs CSV to stdout.
//
// Usage:
//   sidm2-sid-trace <file.prg> [frames]   (default: 5 frames)
//
// Build:  see build.zig entry for sidm2-sid-trace
// Output: frame, cycle, register_name, old_value, new_value

const std = @import("std");
const C64 = @import("zig64");
const flagz = @import("flagz");

// Addresses read from SID header (vary per file):
// init_addr = header bytes 10-11 (big-endian)
// play_addr = header bytes 12-13 (big-endian)
// For Laxity NP21 SID files, these point to tiny stubs.
// The actual player is dispatched from play_addr internally.

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const args = try std.process.argsAlloc(allocator);
    defer std.process.argsFree(allocator, args);

    if (args.len < 2) {
        std.debug.print(
            "Usage: {s} <file.prg> [frames] [init_hex] [play_hex] [subtune]\n",
            .{args[0]},
        );
        return;
    }

    const prg_path = args[1];
    const num_frames: u32 = if (args.len > 2)
        try std.fmt.parseInt(u32, args[2], 10)
    else
        5;

    var c64 = try C64.init(allocator, C64.Vic.Model.pal, 0x1000);
    defer c64.deinit(allocator);

    // Read INIT and PLAY addresses from the SID header embedded in the PRG.
    // SID header: first byte = $00 or 'P', varies. For PSID: magic at [0].
    // For our PRGs: 2-byte PRG header, then the music data starts.
    // The SID file's init/play addresses are stored in the original SID header,
    // not in the PRG. We accept them as CLI args or use defaults.
    //
    // For Laxity NP21 "Stinsens_Last_Night_of_89":
    //   SID header: init=$1000, play=$1006
    //   $1000: JMP $1692 (actual init, sets flag bytes)
    //   $1003: JMP $169B (enable-player stub)
    //   $1006: The real per-frame play entry

    const init_addr: u16 = if (args.len > 3)
        try std.fmt.parseInt(u16, args[3], 16)
    else
        0x1000;

    const play_addr: u16 = if (args.len > 4)
        try std.fmt.parseInt(u16, args[4], 16)
    else
        0x1003;

    // Optional subtune (PSID convention: passed in A to INIT). Default 0.
    const subtune: u8 = if (args.len > 5)
        try std.fmt.parseInt(u8, args[5], 10)
    else
        0;

    const load_addr = try c64.loadPrg(allocator, prg_path, false);
    std.debug.print("Loaded: {s} @ ${X:04}\n", .{ prg_path, load_addr });

    // Show entry points
    std.debug.print("Mem[${X:04}]: ", .{init_addr});
    var i: u16 = 0;
    while (i < 6) : (i += 1)
        std.debug.print("{X:02} ", .{c64.cpu.readByte(init_addr + i)});
    std.debug.print("  (INIT)\n", .{});
    std.debug.print("Mem[${X:04}]: ", .{play_addr});
    i = 0;
    while (i < 6) : (i += 1)
        std.debug.print("{X:02} ", .{c64.cpu.readByte(play_addr + i)});
    std.debug.print("  (PLAY)\n", .{});

    // play=$0000 (PSID convention): INIT installs its own IRQ — for these Galway
    // tunes a RASTER IRQ at the hardware vector $FFFE ($01=$35 banks the KERNAL
    // out) — and INIT never RTSes (it CLIs and spins waiting for the IRQ, so
    // c64.call(init) would hang). Run INIT bounded until the vector is installed,
    // then drive each frame by invoking the handler exactly as a 6502 IRQ would.
    if (play_addr == 0) {
        std.debug.print("play=$0000: bounded INIT @ ${X:04} (subtune {d}), deriving IRQ from $FFFE\n",
            .{ init_addr, subtune });
        c64.cpu.status = 0x00;
        c64.cpu.psToFlags();
        c64.cpu.sp = 0xFF;
        c64.cpu.a = subtune;
        c64.cpu.pc = init_addr;
        const fffe0: u16 = c64.cpu.readWord(0xFFFE);
        const cinv0: u16 = c64.cpu.readWord(0x0314);
        var installed = false;
        var post: u32 = 0;
        var g: u32 = 0;
        while (g < 2_000_000) : (g += 1) {
            _ = c64.cpu.runStep();
            if (!installed) {
                const hv: u16 = c64.cpu.readWord(0xFFFE);
                const cv: u16 = c64.cpu.readWord(0x0314);
                if ((hv != fffe0 and hv != 0) or (cv != cinv0 and cv != 0)) installed = true;
            } else {
                post += 1;
                if (post > 40000) break; // let INIT finish setup after install
            }
        }
        // Handler is at the hardware vector ($FFFE) when the player banks out the
        // KERNAL ($01=$35), else at the KERNAL IRQ vector CINV ($0314).
        const hv: u16 = c64.cpu.readWord(0xFFFE);
        const handler: u16 = if (hv != fffe0 and hv != 0) hv else c64.cpu.readWord(0x0314);
        std.debug.print("INIT installed IRQ handler @ ${X:04} ($01=${X:02})\n",
            .{ handler, c64.cpu.readByte(0x0001) });
        // RTS sentinel in RAM under the banked-out KERNAL ($FFF0 is unused here):
        // the handler's RTI returns here -> RTS @ sp==$FF -> runStep halts the frame.
        c64.cpu.writeByte(0x60, 0xFFF0);

        std.debug.print("frame,cycle,register,old_val,new_val\n", .{});
        var frame: u32 = 0;
        while (frame < num_frames) : (frame += 1) {
            // Simulate a 6502 IRQ entry: push return PC ($FFF0) then status.
            c64.cpu.writeByte(0xFF, 0x01FF); // PCH
            c64.cpu.writeByte(0xF0, 0x01FE); // PCL
            c64.cpu.writeByte(0x24, 0x01FD); // status (I + unused set)
            c64.cpu.sp = 0xFC;
            c64.cpu.pc = handler;
            c64.cpu.flags.i = 1;
            c64.sid.ext_reg_written = false;
            // Run the handler (raster ack + JSR play + restore + RTI) until it
            // RTIs to $FFF0 -> RTS @ sp==$FF -> halt; print each SID write. A
            // safety cap aborts the frame if a quirky handler never returns
            // cleanly, so the tracer can never hang (a normal frame is <20k cycles).
            var steps: u32 = 0;
            var ran_away = false;
            while (c64.cpu.runStep() != 0) {
                steps += 1;
                if (steps > 25000) { // ~3.5x a normal frame; a runaway handler aborts
                    ran_away = true;
                    break;
                }
                if (c64.sid.last_change) |ch| {
                    std.debug.print("{d},{d},{s},${X:02},${X:02}\n", .{
                        frame, ch.cycle, @tagName(ch.meaning), ch.old_value, ch.new_value,
                    });
                }
            }
            if (ran_away) {
                // Handler never returned cleanly (unusual banking/exit) — abort the
                // whole trace fast rather than grinding 50k steps per frame.
                std.debug.print("ABORT: IRQ handler ran away at frame {d}\n", .{frame});
                break;
            }
            std.debug.print("--- Frame {d} ---\n", .{frame});
        }
        return;
    }

    // Call INIT with the subtune number in A (PSID convention).
    std.debug.print("Calling INIT @ ${X:04} (subtune {d})...\n", .{ init_addr, subtune });
    c64.cpu.a = subtune;
    c64.call(init_addr);
    std.debug.print("INIT done. SID regs:\n", .{});
    c64.sid.printRegisters();
    std.debug.print("Running {d} frames via PLAY @ ${X:04}...\n", .{ num_frames, play_addr });

    // CSV header to stderr (stdout may not be easily accessible in Zig 0.15)
    std.debug.print("frame,cycle,register,old_val,new_val\n", .{});

    // Run frames, tracing SID writes each time PLAY is called
    var frame: u32 = 0;
    while (frame < num_frames) : (frame += 1) {
        const changes = try c64.callSidTrace(play_addr, allocator);
        defer allocator.free(changes);

        for (changes) |ch| {
            std.debug.print("{d},{d},{s},${X:02},${X:02}\n", .{
                frame,
                ch.cycle,
                @tagName(ch.meaning),
                ch.old_value,
                ch.new_value,
            });
        }
        std.debug.print("--- Frame {d}: {d} SID changes ---\n", .{ frame, changes.len });
    }
}
