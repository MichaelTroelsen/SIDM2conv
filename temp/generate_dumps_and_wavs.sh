#!/bin/bash
# Generate siddump outputs and WAV files for all SIDSF2player pipeline files

echo "======================================================================"
echo "Generating Siddump Outputs and WAV Files"
echo "======================================================================"
echo ""

PIPELINE_DIR="output/SIDSF2player_Pipeline"
SIDSF2PLAYER_DIR="SIDSF2player"

# Counter
total=0
success_dumps=0
success_wavs=0

# Process each SID file
for sid in "$SIDSF2PLAYER_DIR"/*.sid; do
    basename=$(basename "$sid" .sid)
    total=$((total + 1))

    echo "[$total] Processing: $basename"
    echo "----------------------------------------------------------------------"

    # Paths
    orig_dir="$PIPELINE_DIR/$basename/Original"
    new_dir="$PIPELINE_DIR/$basename/New"

    # Create Original directory if it doesn't exist
    mkdir -p "$orig_dir"

    exported_sid="$new_dir/${basename}_exported.sid"
    orig_dump="$orig_dir/${basename}_original.dump"
    exp_dump="$new_dir/${basename}_exported.dump"
    orig_wav="$orig_dir/${basename}_original.wav"
    exp_wav="$new_dir/${basename}_exported.wav"

    # Siddump original
    echo "  [1/4] Siddump original SID..."
    if tools/siddump.exe "$sid" -t10 > "$orig_dump" 2>&1; then
        echo "        [OK] $orig_dump"
        success_dumps=$((success_dumps + 1))
    else
        echo "        [ERROR] Failed"
    fi

    # Siddump exported (if exists)
    if [ -f "$exported_sid" ]; then
        echo "  [2/4] Siddump exported SID..."
        if tools/siddump.exe "$exported_sid" -t10 > "$exp_dump" 2>&1; then
            echo "        [OK] $exp_dump"
            success_dumps=$((success_dumps + 1))
        else
            echo "        [ERROR] Failed"
        fi
    else
        echo "  [2/4] Skipping siddump (no exported SID)"
    fi

    # WAV original
    echo "  [3/4] Rendering original WAV..."
    if tools/SID2WAV.EXE "$sid" -o "$orig_wav" -t30 > /dev/null 2>&1; then
        echo "        [OK] $orig_wav"
        success_wavs=$((success_wavs + 1))
    else
        echo "        [ERROR] Failed"
    fi

    # WAV exported (if exists)
    if [ -f "$exported_sid" ]; then
        echo "  [4/4] Rendering exported WAV..."
        if tools/SID2WAV.EXE "$exported_sid" -o "$exp_wav" -t30 > /dev/null 2>&1; then
            echo "        [OK] $exp_wav"
            success_wavs=$((success_wavs + 1))
        else
            echo "        [ERROR] Failed"
        fi
    else
        echo "  [4/4] Skipping WAV (no exported SID)"
    fi

    echo ""
done

echo "======================================================================"
echo "SUMMARY"
echo "======================================================================"
echo "Total files processed: $total"
echo "Successful dumps: $success_dumps / $((total * 2))"
echo "Successful WAVs: $success_wavs / $((total * 2))"
echo "======================================================================"
