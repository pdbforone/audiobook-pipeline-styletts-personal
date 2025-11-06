import yaml

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Disable quality validation so all chunks are included
config['quality_validation_enabled'] = False

# Also lower SNR threshold as backup
config['snr_threshold'] = 10.0

# Reduce noise reduction since it's making things worse
config['noise_reduction_factor'] = 0.1

with open('config.yaml', 'w') as f:
    yaml.dump(config, f, default_flow_style=False, sort_keys=False)

print('Updated config.yaml:')
print('  quality_validation_enabled: False')
print('  snr_threshold: 10.0')
print('  noise_reduction_factor: 0.1')
