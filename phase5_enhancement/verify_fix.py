"""
Phase 5 Clipping Fix Verification Script
Run this to verify the configuration changes are working properly.
"""

import yaml
from pathlib import Path

def verify_config():
    """Verify Phase 5 config.yaml has correct anti-clipping settings"""
    
    config_path = Path(__file__).parent / "config.yaml"
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    print("=" * 60)
    print("PHASE 5 CLIPPING FIX VERIFICATION")
    print("=" * 60)
    print()
    
    # Expected values
    expected = {
        'lufs_target': -18.0,
        'noise_reduction_factor': 0.3,
        'volume_norm_headroom': 0.3,
        'crossfade_duration': 0.2,
    }
    
    all_good = True
    
    for key, expected_val in expected.items():
        actual_val = config.get(key)
        status = "✅ PASS" if actual_val == expected_val else "❌ FAIL"
        
        if actual_val != expected_val:
            all_good = False
        
        print(f"{status} {key}:")
        print(f"    Expected: {expected_val}")
        print(f"    Actual:   {actual_val}")
        print()
    
    # Check additional settings
    print("Additional Settings:")
    print(f"  Sample Rate: {config.get('sample_rate')} Hz")
    print(f"  Volume Normalization: {config.get('enable_volume_normalization')}")
    print(f"  SNR Threshold: {config.get('snr_threshold')} dB")
    print()
    
    print("=" * 60)
    if all_good:
        print("✅ ALL CHECKS PASSED - Configuration is correct!")
        print()
        print("Next steps:")
        print("1. Test single chunk: poetry run python src/phase5_enhancement/main.py --chunk_id 0 --skip_concatenation")
        print("2. Listen to: processed/enhanced_0000.wav")
        print("3. Check for clipping: Should sound clean and natural")
    else:
        print("❌ CONFIGURATION ERRORS DETECTED")
        print()
        print("Please review config.yaml and fix the values above.")
    print("=" * 60)

if __name__ == "__main__":
    verify_config()
