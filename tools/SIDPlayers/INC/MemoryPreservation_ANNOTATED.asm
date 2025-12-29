;==============================================================================
; MemoryPreservation.asm
; Annotated 6502 Assembly Disassembly
;==============================================================================
;
;
;==============================================================================
; MEMORY MAP
;==============================================================================
;==============================================================================
; SID REGISTER REFERENCE
;==============================================================================
; $D400-$D406   Voice 1 (Frequency, Pulse, Control, ADSR)
; $D407-$D40D   Voice 2 (Frequency, Pulse, Control, ADSR)
; $D40E-$D414   Voice 3 (Frequency, Pulse, Control, ADSR)
; $D415-$D416   Filter Cutoff (11-bit)
; $D417         Filter Resonance/Routing
; $D418         Volume/Filter Mode
;
;==============================================================================
; CODE
;==============================================================================

//; -----------------------------------------------------------------------------//; Configuration//; -----------------------------------------------------------------------------//; These addresses are identified as being modified during SID playback.//; The list should be defined in the SID-specific helper file (e.g., *-HelpfulData.asm)//; before including this file.//;//; Expected variables://;   SIDModifiedMemory - List of addresses modified during playback//;   SIDModifiedMemoryCount - Number of addresses in the list//; -----------------------------------------------------------------------------#importonce//; -----------------------------------------------------------------------------//; Data Storage//; -----------------------------------------------------------------------------//; Buffer to store the original values of modified memory locationsSIDMemoryBackup:    .fill SIDModifiedMemoryCount, $00//; -----------------------------------------------------------------------------//; BackupSIDMemory//; Saves the current state of all memory locations that will be modified//; during SID playback. Call this before playing the SID.//; //; Registers: Corrupts A//; -----------------------------------------------------------------------------BackupSIDMemory:    .for (var i = 0; i < SIDModifiedMemoryCount; i++) {        lda SIDModifiedMemory.get(i)  ; Load Accumulator
        sta SIDMemoryBackup + i  ; Store Accumulator
    }    rts  ; Return from Subroutine
//; -----------------------------------------------------------------------------//; RestoreSIDMemory//; Restores all memory locations to their state before SID playback.//; Call this after playing the SID to restore the original state.//; //; Registers: Corrupts A//; -----------------------------------------------------------------------------RestoreSIDMemory:    .for (var i = 0; i < SIDModifiedMemoryCount; i++) {        lda SIDMemoryBackup + i  ; Load Accumulator
        sta SIDModifiedMemory.get(i)  ; Store Accumulator
    }    rts  ; Return from Subroutine
//; -----------------------------------------------------------------------------//; Usage Example://; -----------------------------------------------------------------------------//; jsr BackupSIDMemory      ; Save current state//; jsr SIDPlay              ; Play music (modifies memory)//; jsr RestoreSIDMemory     ; Restore original state//; //; This allows us to://; 1. Play the music normally (first call)//; 2. Play it again with $01=$30 to read SID registers//; 3. Restore the state so the next frame plays correctly//; -----------------------------------------------------------------------------