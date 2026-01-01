# Validation Dashboard - User Guide

**Version**: 2.0.0 (Improved)
**Created**: 2026-01-01

Interactive validation dashboard with professional styling and enhanced search capabilities.

---

## 🚀 Quick Start

### Generate Dashboard

```bash
# Generate from latest validation run (Windows)
validation-dashboard.bat

# Generate from specific run (Windows)
validation-dashboard.bat --run 5

# Specify output location (Windows)
validation-dashboard.bat --output custom_dashboard.html

# Direct Python (cross-platform)
python scripts/generate_dashboard.py
python scripts/generate_dashboard.py --run 5 --output custom.html
```

### From Conversion Cockpit GUI

1. Run batch conversion with validation enabled
2. Go to **Results** tab
3. Click **"Generate & View Dashboard"**
4. Dashboard loads in embedded view (or opens in browser)

---

## 📊 Dashboard Sections

### 1. **Overview**
- Run information (ID, timestamp, driver)
- Navigation sidebar
- Summary statistics cards

### 2. **Statistics Grid**
Six metric cards showing:
- **Total Files**: Number of files validated
- **Passed**: Successfully validated files
- **Failed**: Failed validation files
- **Pass Rate**: Success percentage
- **Avg Accuracy**: Average overall accuracy
- **Step 1 Avg**: Average Step 1 accuracy

### 3. **Accuracy Trends**
Line chart showing accuracy across validation runs:
- X-axis: Run IDs (up to 20 most recent)
- Y-axis: Average accuracy (0-100%)
- Hover for exact values

### 4. **Results Table**
Comprehensive file-by-file results:
- File name
- Status (Pass/Fail)
- Overall accuracy (with visual bar)
- Step 1 accuracy (with visual bar)
- Step 2 accuracy (with visual bar)
- Step 3 accuracy (with visual bar)

**Features**:
- Failed files shown first
- Sorted by accuracy (lowest to highest)
- Hover row to highlight

---

## 🔍 Search & Filter

### Basic Search

Type in the search box to filter results by:
- **File name**: Partial match (e.g., "beast", "laxity")
- **Status**: "pass", "fail"
- **Any text**: Searches entire row content

```
Example searches:
- "beast" → Shows files with "beast" in name
- "fail" → Shows only failed files
- "pass" → Shows only passed files
```

### Advanced Search - Accuracy Ranges

Search by accuracy thresholds:

**Greater Than (`>`):**
```
>90   → Shows files with ANY accuracy > 90%
>95   → Shows files with ANY accuracy > 95%
>99   → Shows files with ANY accuracy > 99%
```

**Less Than (`<`):**
```
<70   → Shows files with ANY accuracy < 70%
<50   → Shows files with ANY accuracy < 50%
<90   → Shows files with ANY accuracy < 90%
```

**Use Cases**:
- Find low accuracy files: `<70`
- Find excellent results: `>95`
- Find borderline files: Search `>85`, then `<95`

---

## 🎨 Visual Elements

### Status Indicators

- **✓ PASS** (green): File passed validation
- **✗ FAIL** (red): File failed validation

### Accuracy Bars

Color-coded progress bars:
- **Green**: 90-100% (Excellent)
- **Orange**: 70-90% (Good)
- **Red**: 0-70% (Needs attention)

Visual width = accuracy percentage

### Color Scheme

- **Dark Theme**: Professional VS Code-inspired
- **Accent Colors**:
  - Teal: Primary highlights
  - Blue: Secondary elements
  - Green: Success indicators
  - Red: Error indicators
  - Orange: Warnings

---

## 🔧 Navigation

### Sidebar Navigation

Click any section to jump:
- **Overview**: Top of page
- **Statistics**: Metrics grid
- **Trends**: Chart section
- **Results**: File table

Smooth scrolling for better UX.

### Collapsible Sections

Click section headers to expand/collapse:
- Summary Statistics
- Driver Breakdown
- Accuracy Distribution
- Performance Metrics
- File Details

---

## 📈 Understanding Results

### Accuracy Metrics

**Overall Accuracy**:
- Percentage of frames matching expected output
- Most important metric
- 90%+ is excellent

**Step 1 Accuracy**:
- First validation step (usually frame-by-frame comparison)
- Indicates core conversion quality

**Step 2 Accuracy**:
- Second validation step
- Additional validation checks

**Step 3 Accuracy**:
- Third validation step
- Final validation checks

### Pass/Fail Criteria

**Pass**:
- All validation steps completed successfully
- Accuracies meet minimum thresholds
- No critical errors

**Fail**:
- One or more validation steps failed
- Accuracy below threshold
- Critical errors encountered

---

## 💡 Use Cases

### 1. **Quality Assurance**
```
Goal: Verify batch conversion quality
Steps:
1. Run batch conversion with validation
2. Generate dashboard
3. Check pass rate (should be >90%)
4. Review failed files
5. Search for low accuracy: <70
6. Investigate failures
```

### 2. **Regression Testing**
```
Goal: Compare accuracy over time
Steps:
1. Check Trends chart
2. Look for accuracy drops
3. Identify when regression occurred
4. Compare results between runs
```

### 3. **Driver Comparison**
```
Goal: Compare driver accuracy
Steps:
1. Run validation with driver A
2. Run validation with driver B
3. Generate dashboards for each
4. Compare accuracy metrics
5. Choose better driver
```

### 4. **Troubleshooting**
```
Goal: Debug conversion issues
Steps:
1. Search for specific file
2. Check accuracy breakdown
3. Review error messages
4. Identify problematic steps
5. Fix and re-validate
```

---

## 🛠️ Advanced Usage

### Comparing Multiple Runs

```bash
# Generate dashboard for run 5
python scripts/generate_dashboard.py --run 5 --output run5.html

# Generate dashboard for run 6
python scripts/generate_dashboard.py --run 6 --output run6.html

# Open both in browser tabs
# Compare side-by-side
```

### Filtering Results Programmatically

The dashboard HTML is self-contained. You can:
1. Open in browser
2. Use browser DevTools console
3. Filter programmatically:

```javascript
// Hide all rows with accuracy < 90%
document.querySelectorAll('.results-table tbody tr').forEach(row => {
    const accuracyText = row.textContent.match(/(\d+\.\d+)%/);
    if (accuracyText && parseFloat(accuracyText[1]) < 90) {
        row.style.display = 'none';
    }
});
```

### Exporting Data

**Copy Table to Spreadsheet**:
1. Select table rows
2. Copy (Ctrl+C)
3. Paste into Excel/Google Sheets

**Screenshot for Reports**:
1. Use browser screenshot tool
2. Capture entire page or specific section
3. Include in documentation

---

## 🐛 Troubleshooting

### Dashboard Not Generating

**Error**: "No validation runs found in database"

**Cause**: No validation data in database

**Solution**:
```bash
# Run validation first
python scripts/sid_to_sf2.py input.sid output.sf2 --validate

# Or use Conversion Cockpit with validation enabled
```

### Empty Trends Chart

**Cause**: Only one validation run in database

**Solution**: Run more validations. Trends require 2+ runs.

### Search Not Working

**Cause**: Browser JavaScript disabled

**Solution**: Enable JavaScript in browser settings

### Accuracy Bars Not Showing

**Cause**: CSS not loaded

**Solution**:
- Refresh page (F5)
- Clear browser cache
- Try different browser

---

## 📊 Example Workflow

### Weekly Quality Check

```bash
# Monday: Run full validation
python scripts/batch_convert.py --validate

# Generate dashboard
python scripts/generate_dashboard.py --output weekly_report_$(date +%Y%m%d).html

# Review results
1. Check pass rate (target: >95%)
2. Search for failures: "fail"
3. Search for low accuracy: <80
4. Document issues
5. Create fix tasks

# Friday: Re-validate after fixes
python scripts/batch_convert.py --validate

# Compare
python scripts/generate_dashboard.py --output weekly_final_$(date +%Y%m%d).html

# Verify improvements in Trends chart
```

---

## 🎯 Best Practices

### 1. **Regular Validation**
- Run validation after each major change
- Compare trends over time
- Set pass rate targets (e.g., >95%)

### 2. **Document Issues**
- Screenshot low accuracy files
- Note patterns in failures
- Track fixes applied

### 3. **Use Search Effectively**
- Start with broad searches
- Narrow down with accuracy ranges
- Combine file name + accuracy searches

### 4. **Archive Dashboards**
- Save HTML files with timestamps
- Keep for historical comparison
- Include in release documentation

### 5. **Share Results**
- HTML files work offline
- Easy to email to team
- No special software needed

---

## 📚 See Also

- **Validation Guide**: `docs/VALIDATION_GUIDE.md` - Complete validation documentation
- **Conversion Cockpit**: `docs/CONVERSION_COCKPIT_USER_GUIDE.md` - GUI tool guide
- **Batch Reports**: `docs/guides/BATCH_REPORTS_GUIDE.md` - Batch conversion reports
- **HTML Components**: `docs/reference/HTML_COMPONENTS_LIBRARY.md` - Styling reference

---

## 🆕 What's New in v2.0.0

**Improvements Over v1.0.0**:
- ✅ Professional dark VS Code theme
- ✅ HTMLComponents styling (consistent with other tools)
- ✅ Enhanced search with accuracy ranges
- ✅ Better mobile responsiveness
- ✅ Sidebar navigation with smooth scrolling
- ✅ Improved color scheme and accessibility
- ✅ Better Chart.js integration
- ✅ Faster rendering for large datasets

**Migration**:
No changes needed. Simply regenerate dashboard with new version.

---

## 💡 Tips & Tricks

1. **Quick Failure Review**: Type "fail" in search box
2. **Find Outliers**: Use `<50` or `>99` to find extremes
3. **Bookmark Dashboard**: Save frequently used dashboard URLs
4. **Print to PDF**: Use browser Print → Save as PDF for archiving
5. **Multi-Monitor**: Open multiple runs on different monitors
6. **Keyboard Navigation**: Tab through sections, Enter to expand/collapse
7. **Copy Results**: Select and copy table data for analysis
8. **Browser Zoom**: Ctrl+Plus/Minus to adjust text size

---

**End of Guide** - Master your validation analysis! 🎵
