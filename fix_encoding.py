# PowerPack Character Fix Script
import os

file_path = r'POWERPACK_R2\BO_POWERPACK_R2M1\PC_APP\powerpack_controller.py'

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace all broken characters
    replacements = {
        'âŒ': '[ERROR]',
        'âœ…': '[OK]',
        'âšª': '[INFO]',
        'ðŸ"§': '[DEBUG]',
        'ðŸ"¡': '[INFO]',
        'ðŸ"Œ': '[INFO]',
        'ðŸ"‹': '[VERSION]',
        'ðŸ"Š': '[INFO]',
        'âš ï¸': '[WARN]',
        'âš': '[WARN]',
        'ï¸': '',
    }
    
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Successfully fixed encoding issues in {file_path}")
    print(f"File size: {len(content)} characters")
    
except Exception as e:
    print(f"Error: {e}")

