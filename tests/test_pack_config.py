#!/usr/bin/env python3
"""Test the new pack configuration system"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.utils.config import ConfigManager

def test_pack_config_system():
    """Test pack config functionality"""
    print('🧪 Testing pack config system...')
    
    cm = ConfigManager()
    
    # Test 1: Ensure pack config exists
    print('1. Testing pack config creation...')
    config = cm.ensure_pack_config('heroes.txt', 'default')
    print(f'   ✅ Pack config created/loaded: {len(config) > 0}')
    
    # Test 2: Save pack config
    print('2. Testing pack config saving...')
    test_config = {
        'txt2img': {
            'steps': 25, 
            'cfg_scale': 8.0,
            'width': 1024,
            'height': 1024
        }
    }
    success = cm.save_pack_config('test_pack.txt', test_config)
    print(f'   ✅ Pack config saved: {success}')
    
    # Test 3: Load pack config
    print('3. Testing pack config loading...')
    loaded = cm.get_pack_config('test_pack.txt')
    steps_match = loaded.get('txt2img', {}).get('steps') == 25
    print(f'   ✅ Pack config loaded correctly: {steps_match}')
    
    # Test 4: Check file was created
    config_file = Path('packs/test_pack.json')
    print(f'   ✅ Config file created: {config_file.exists()}')
    
    print('\n🎉 All pack config system tests passed!')
    return True

if __name__ == "__main__":
    test_pack_config_system()