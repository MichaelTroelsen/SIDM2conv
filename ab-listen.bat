@echo off
REM A/B Listening Pages - hear an original .sid against a SIDM2 conversion
REM
REM Builds one self-contained HTML page per pair that plays BOTH renders in
REM lock-step and swaps which one is audible, so the switch is gapless and
REM position-matched. Two files in a media player cannot be compared that way,
REM and a comparison that loses its place between clicks is a comparison of
REM two memories. Adds blind-test scoring, a sync-offset control, amplitude
REM envelopes (whole song + per voice) and a precomputed dual spectrogram.
REM
REM This is the human-in-the-loop companion to audio-tightness.bat: that tool
REM measures onset timing, this one lets a person CHECK a fidelity claim by ear.
REM
REM Usage:
REM   ab-listen.bat stage original.sid converted.sf2 --driver-init 0x1000 --driver-play 0x1003
REM   ab-listen.bat stage original.sid converted.sf2 --voices -t 60
REM   ab-listen.bat chips                          (measure the staged pairs)
REM   ab-listen.bat build --chips build\listen\chips.json --notes LISTENING.md
REM   ab-listen.bat serve
REM   ab-listen.bat build --embed Tune_Name        (self-contained, WAVs inlined)
REM
REM SERVE, don't open the file: the envelope overlay and the automatic sync
REM read both WAVs with fetch(), which no browser allows over file://. Audio
REM playback works either way. `build` also drops a double-clickable
REM build\listen\Listen.cmd that serves and opens the index.
REM
REM stage options:
REM   --name N                 Page name (default: the original's stem)
REM   -t, --seconds N          Render duration in seconds (default: 60)
REM   --subtune N              Subtune to render on both sides
REM   --driver-init/--driver-play  Override the .sf2's init/play addresses
REM                            (required for bin/-only native drivers)
REM   --voices                 Also render three solo stems per side. Forces
REM                            sidplayfp (the only renderer with a voice mute).
REM                            NOT clean isolation on every tune -- the page
REM                            says so beside the strips.
REM   --renderer {auto,vsid,sidplayfp}   ONE renderer is used for both sides.
REM
REM chips options (measures the staged WAVs -- renders NOTHING, so it is cheap
REM and can be re-run after any rebuild without re-staging):
REM   -o FILE                  Output path (default: build\listen\chips.json)
REM   --onset                  Also emit onset match + median offset. OPT-IN:
REM                            onset match is ORDINAL ONLY with no absolute
REM                            gate -- a 99.8%% register-exact build measured
REM                            64.7%% against an 85-91%% original-vs-itself
REM                            floor -- so it is meaningful only against a
REM                            baseline of the SAME tune, never as pass/fail.
REM   NOTE: no chip here is a score. Each carries a `blind` note saying what it
REM   cannot see, shown as a tooltip on the page, because WHICH feature is
REM   informative depends on the defect: A-weighted level is the strongest
REM   discriminator on a timing defect and pure noise on a pitch defect, where
REM   chroma fires instead. A null reading does not mean "clean".
REM
REM build options:
REM   --chips FILE.json        {tune: {label: value}} quoted in the page rail.
REM                            JSON, never a scraped Markdown table -- a scraper
REM                            that stops matching renders an empty rail, which
REM                            reads exactly like "nothing to report".
REM   --notes FILE.md          '## <tune>' headings with '- ' bullets
REM   --embed TUNE             One page with the audio inlined (~14 MB/minute
REM                            per side -- the practical ceiling)

setlocal

REM Check Python
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found in PATH
    echo.
    echo Please install Python 3.8+ or add to PATH
    exit /b 1
)

if "%~1"=="" (
    echo A/B Listening Pages - hear an original .sid against a SIDM2 conversion
    echo.
    echo Usage: ab-listen.bat {stage^|build^|serve} [options]
    echo.
    echo Examples:
    echo   ab-listen.bat stage original.sid converted.sf2 --driver-init 0x1000 --driver-play 0x1003
    echo   ab-listen.bat build --chips fidelity.json
    echo   ab-listen.bat serve
    echo.
    echo For detailed help: ab-listen.bat --help
    exit /b 1
)

python pyscript\abpage.py %*

endlocal
