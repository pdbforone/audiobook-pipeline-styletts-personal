import sys

# Read the file
with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the buggy section
old_text = '''                snr_post, rms_post, _, quality_good = validate_audio_quality(
                    enhanced, sr, config
                )
                if quality_good:'''

new_text = '''                snr_post, rms_post, _, quality_good = validate_audio_quality(
                    enhanced, sr, config
                )
                # FIXED: Always accept fallback audio if quality validation is disabled
                if quality_good or not config.quality_validation_enabled:'''

if old_text in content:
    content = content.replace(old_text, new_text)
    print('✓ Fixed fallback quality check')
    
    # Write back
    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('✓ Updated main.py')
else:
    print('ERROR: Could not find the code section to fix')
    sys.exit(1)
