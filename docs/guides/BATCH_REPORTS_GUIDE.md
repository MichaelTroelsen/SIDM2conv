# Batch Reports Guide - Conversion Cockpit

**Version**: 1.0.0
**Created**: 2026-01-01

Export professional HTML reports from Conversion Cockpit batch conversion results.

---

## 🚀 Quick Start

### Export from Conversion Cockpit GUI

1. **Run Batch Conversion**:
   - Launch Conversion Cockpit: `conversion-cockpit.bat`
   - Configure and run batch conversion
   - Wait for completion

2. **Export Report**:
   - Go to **Results** tab
   - Click **"Export HTML Report"** button
   - Choose save location
   - Click **Yes** to open report in browser

### Export from Python Code

```python
from pyscript.report_generator import generate_batch_report

# Sample results and summary
results = [...]  # List of result dictionaries
summary = {...}  # Summary statistics

# Generate report
generate_batch_report(
    results=results,
    summary=summary,
    output_path="batch_report.html"
)
```

---

## 📊 What's Included

The HTML report includes:

### 1. **Overview Section**
- Summary statistics dashboard
- 6 metric cards:
  - Total files processed
  - Passed conversions
  - Failed conversions
  - Warnings
  - Average accuracy
  - Total processing time
- Quick navigation sidebar

### 2. **Summary Statistics**
- Total files processed
- Successful conversions (count and percentage)
- Failed conversions
- Warnings
- Total processing time
- Average time per file

### 3. **Driver Breakdown**
- Usage statistics for each driver
- File counts and percentages
- Table sorted by usage frequency

### 4. **Accuracy Distribution**
- Accuracy ranges:
  - Perfect (99-100%)
  - High (90-99%)
  - Medium (70-90%)
  - Low (<70%)
- Statistics: Average, Min, Max
- File counts and percentages

### 5. **Performance Metrics**
- Total processing time
- Average time per file
- Fastest conversion (with filename)
- Slowest conversion (with filename)
- Throughput (files/second)

### 6. **File Details**
- Summary table (top 20 files)
- Failed/warnings shown first
- Expandable detailed view for each file:
  - Full file path
  - Driver used
  - Status (passed/failed/warning)
  - Steps completed
  - Accuracy percentage
  - Duration
  - Error messages (if any)
  - Output files list

---

## 🎨 Features

### Interactive Elements

- **Collapsible Sections**: Click headers to expand/collapse
- **Smooth Scrolling**: Sidebar navigation jumps to sections
- **Color-Coded Status**:
  - 🟢 Green: Passed
  - 🔴 Red: Failed
  - 🟡 Orange: Warning
  - 🔵 Blue: Info/Pending
- **Professional Styling**: Dark VS Code theme

### Data Export

- **Self-Contained HTML**: No external dependencies
- **Works Offline**: All assets embedded
- **Easy to Share**: Single file
- **Archive-Ready**: Perfect for long-term storage
- **Print-Friendly**: Optimized for printing

---

## 📖 Usage Examples

### Example 1: Export After Batch Conversion

```
1. Run batch conversion in Conversion Cockpit
2. Go to Results tab
3. Click "Export HTML Report"
4. Save as: batch_report_20260101_153045.html
5. Open report in browser
6. Navigate using sidebar
7. Expand file details to investigate failures
```

### Example 2: Programmatic Export

```python
from pyscript.conversion_executor import ConversionExecutor
from pyscript.pipeline_config import PipelineConfig
from pyscript.report_generator import generate_batch_report

# Setup executor
config = PipelineConfig()
executor = ConversionExecutor(config)

# Run conversions
executor.start_batch(["file1.sid", "file2.sid", "file3.sid"])
# ... wait for completion ...

# Export report
results_list = [executor._result_to_dict(r) for r in executor.results.values()]
summary = executor._get_summary()

generate_batch_report(
    results=results_list,
    summary=summary,
    output_path="my_batch_report.html"
)
```

### Example 3: Compare Multiple Batches

```bash
# Run batch 1 with driver11
python scripts/batch_convert.py --driver driver11
# Export report: batch_report_driver11.html

# Run batch 2 with laxity
python scripts/batch_convert.py --driver laxity
# Export report: batch_report_laxity.html

# Open both reports side-by-side to compare:
# - Accuracy differences
# - Performance differences
# - Success rates
```

---

## 🔍 Understanding the Report

### Status Indicators

- **✓ Passed**: Conversion completed successfully
- **✗ Failed**: Conversion failed (see error message)
- **⚠ Warning**: Completed with warnings (e.g., low accuracy)
- **○ Pending**: Not yet processed

### Accuracy Ranges

| Range | Description | Quality |
|-------|-------------|---------|
| 99-100% | Perfect | Excellent conversion |
| 90-99% | High | Good conversion |
| 70-90% | Medium | Acceptable with minor issues |
| <70% | Low | Poor conversion, review needed |

### Performance Metrics

- **Total Time**: Wall clock time for entire batch
- **Average Time**: Mean time per file
- **Fastest/Slowest**: Identify outliers
- **Throughput**: Processing speed (files/second)

### Driver Breakdown

Shows which drivers were used:
- **laxity**: Laxity NewPlayer v21 files (99.93% accuracy)
- **driver11**: SF2-exported files (100% accuracy)
- **np20**: NP20.G4 files (70-90% accuracy)
- **auto**: Automatic selection based on player detection

---

## 💡 Use Cases

### 1. **Quality Assurance**
- Review conversion accuracy across batches
- Identify problematic files
- Verify driver selection worked correctly

### 2. **Performance Analysis**
- Compare processing times
- Identify slow files for optimization
- Track throughput over time

### 3. **Documentation**
- Archive conversion results
- Share with collaborators
- Include in project documentation

### 4. **Troubleshooting**
- Filter by status (failed/warning first)
- Investigate error messages
- Review file-specific details

### 5. **Batch Comparison**
- Run same files with different drivers
- Compare accuracy and performance
- Validate driver improvements

---

## ⚙️ Technical Details

### Report Generation

The batch report uses:
- **HTMLComponents Library**: Professional UI components (`pyscript/html_components.py`)
- **Report Generator**: Batch report generation (`pyscript/report_generator.py`)
- **ConversionExecutor**: Results collection (`pyscript/conversion_executor.py`)

### Data Structure

**Results List** (per file):
```python
{
    "filename": str,           # Input file path
    "driver": str,             # Driver used (laxity, driver11, np20)
    "steps_completed": int,    # Steps completed
    "total_steps": int,        # Total steps
    "accuracy": float,         # Accuracy percentage (0-100)
    "status": str,             # passed, failed, warning, pending
    "error_message": str,      # Error details (if failed)
    "duration": float,         # Processing time (seconds)
    "output_files": List[str]  # Generated output files
}
```

**Summary Statistics**:
```python
{
    "total_files": int,        # Total files processed
    "passed": int,             # Successfully converted
    "failed": int,             # Failed conversions
    "warnings": int,           # Completed with warnings
    "avg_accuracy": float,     # Average accuracy (%)
    "duration": float,         # Total processing time (seconds)
    "pass_rate": float         # Success rate (%)
}
```

### HTML Structure

```
<container>
  <sidebar>
    - Navigation items
    - Summary stats
  </sidebar>
  <main-content>
    - Header
    - Overview stats grid (6 cards)
    - Summary section (collapsible)
    - Driver breakdown (collapsible)
    - Accuracy distribution (collapsible)
    - Performance metrics (collapsible)
    - File details (collapsible)
      - Summary table (top 20)
      - Per-file expandable sections
    - Footer
  </main-content>
</container>
```

---

## 🐛 Troubleshooting

### "No Results" Error

**Cause**: No conversion results available

**Solution**: Run a batch conversion first before exporting

### Report Generation Failed

**Cause**: Error creating HTML file

**Solution**:
- Check output directory exists and is writable
- Verify results data is valid
- Check console for error details

### Empty Sections

**Cause**: No data available for that section

**Solutions**:
- **No accuracy data**: Files didn't include accuracy metrics
- **No timing data**: Duration not recorded
- **No output files**: Files listed in results but not found

### File Paths Show Absolute Paths

**Cause**: Results contain full file paths

**Solution**: This is normal - report shows full paths for clarity

---

## 📚 See Also

- **Conversion Cockpit Guide**: `docs/CONVERSION_COCKPIT_USER_GUIDE.md`
- **HTML Components Library**: `docs/reference/HTML_COMPONENTS_LIBRARY.md`
- **SF2 HTML Export**: `docs/guides/SF2_HTML_EXPORT_GUIDE.md`
- **Validation Guide**: `docs/VALIDATION_GUIDE.md`

---

## 🎯 Next Steps

After exporting a batch report:

1. **Review Results**: Open HTML in browser
2. **Check Failed Files**: Expand failures to see errors
3. **Analyze Accuracy**: Review accuracy distribution
4. **Compare Performance**: Check timing metrics
5. **Archive Report**: Save HTML for long-term storage
6. **Share Report**: Send single HTML file to collaborators

---

## 💡 Tips

- **Export After Every Batch**: Create reports for all batch conversions
- **Use Descriptive Filenames**: Include date/time in report filename (e.g., `batch_report_20260101_153045.html`)
- **Archive Reports**: Keep reports for historical comparison
- **Compare Drivers**: Run same files with different drivers and compare reports
- **Investigate Failures**: Use file details section to debug issues
- **Track Performance**: Monitor throughput and timing trends
- **Share with Team**: HTML reports are perfect for sharing results

---

**End of Guide** - Happy batch converting! 🎵
