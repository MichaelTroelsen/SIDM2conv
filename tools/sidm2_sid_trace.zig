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
        // FIX: the old code printed "installed" and proceeded unconditionally, even
        // when `installed` never became true and `handler` resolved to an invalid
        // $0000 — producing a fake "0 writes" trace indistinguishable from a real
        // silent tune. This happens for players whose INIT polls a RAM flag that only
        // its own IRQ handler sets (a self-test handshake) — this bounded-INIT
        // emulation never delivers a real interrupt (zig64's runStep has no
        // autonomous VIC/CIA interrupt controller — only c64.call-style explicit
        // dispatch), so that flag can never be set and INIT spins forever. Detect
        // this and fail loudly instead of silently faking success.
        // An IRQ handler must live in code space. $0000-$01FF is zero page +
        // the stack: a "handler" there is always a mis-read of an uninitialized
        // or stale vector, never a real entry point (e.g. LFT/A_Mind_Is_Born
        // resolves $0031). Treat it as unresolved rather than trace garbage.
        if (!installed or handler < 0x0200) {
            std.debug.print(
                "FAILED: self-installing IRQ vector never resolved after {d} steps (installed={}, handler=${X:04}). " ++
                "This player's INIT likely waits on its own IRQ firing as a handshake before finishing setup; " ++
                "this tracer has no autonomous VIC/CIA interrupt delivery so that can never happen here. " ++
                "Not a 0-write tune — untraceable with this tool.\n",
                .{ g, installed, handler },
            );
            std.process.exit(1);
        }
        std.debug.print("INIT installed IRQ handler @ ${X:04} ($01=${X:02})\n",
            .{ handler, c64.cpu.readByte(0x0001) });
        // RTS sentinel in RAM under the banked-out KERNAL ($FFF0 is unused here):
        // the handler's RTI returns here -> RTS @ sp==$FF -> runStep halts the frame.
        c64.cpu.writeByte(0x60, 0xFFF0);

        std.debug.print("frame,cycle,register,old_val,new_val\n", .{});
        var total_writes: u64 = 0;
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
                    total_writes += 1;
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
        // A resolved handler that drives ZERO SID writes is not evidence of a
        // silent tune — it means the IRQ emulation never actually reached the
        // player (stale/wrong vector, banking the sentinel can't survive, or a
        // handshake this tracer can't satisfy). Emitting an empty CSV here is
        // indistinguishable from a real silent trace and has silently passed
        // consumers that compare traces for equality. Fail loudly instead.
        if (total_writes == 0) {
            std.debug.print(
                "FAILED: IRQ handler @ ${X:04} produced 0 SID writes over {d} frames. " ++
                "The handler resolved but never drove the SID — the vector is likely stale/wrong, " ++
                "or this player needs interrupt delivery this tracer cannot provide. " ++
                "This is NOT a verified silent tune — treat as untraceable.\n",
                .{ handler, num_frames },
            );
            std.process.exit(1);
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
    var total_writes: u64 = 0;
    var frame: u32 = 0;
    while (frame < num_frames) : (frame += 1) {
        const changes = try c64.callSidTrace(play_addr, allocator);
        defer allocator.free(changes);

        total_writes += changes.len;
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
    // Same honest-failure rule as the IRQ path: a PLAY routine that writes no
    // SID register at all over the whole window means we never reached the real
    // player (wrong play address, a wrapper we mis-entered, or an INIT that did
    // not complete). Never let that masquerade as a valid empty trace.
    if (total_writes == 0) {
        std.debug.print(
            "FAILED: PLAY @ ${X:04} produced 0 SID writes over {d} frames. " ++
            "Wrong play address, an unhandled wrapper, or INIT did not complete. " ++
            "This is NOT a verified silent tune — treat as untraceable.\n",
            .{ play_addr, num_frames },
        );
        std.process.exit(1);
    }
}
