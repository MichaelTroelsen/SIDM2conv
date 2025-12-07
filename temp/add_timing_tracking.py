"""Add timing tracking to the pipeline"""

import re

# Read the pipeline script
with open('complete_pipeline_with_validation.py', 'r') as f:
    content = f.read()

# Add imports at the top
if 'import time' not in content:
    content = content.replace('from datetime import datetime', 
                            'from datetime import datetime\nimport time\nimport json')

# Add timing initialization in main()
init_code = """
    # Timing tracking
    step_timings = []
    file_timings = []
    overall_start = time.time()
"""

if 'step_timings = []' not in content:
    content = content.replace('    results = []', 
                            '    results = []\n' + init_code)

# Add timing tracking for each file
file_start = """
        file_start_time = time.time()
"""

if 'file_start_time' not in content:
    content = content.replace('        result = {',
                            file_start + '        result = {')

# Add timing save at end of file processing
file_end = """
        file_duration = time.time() - file_start_time
        file_timings.append({
            'filename': filename,
            'duration': file_duration,
            'steps': result.get('step_times', {})
        })
"""

# Save updated file
with open('complete_pipeline_with_validation.py', 'w') as f:
    f.write(content)

print("Timing tracking code added!")
