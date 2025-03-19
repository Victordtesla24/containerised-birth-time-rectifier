import os
print('SWISSEPH_PATH:', os.environ.get('SWISSEPH_PATH'))
print('EPHE_PATH exists:', os.path.exists(os.environ.get('SWISSEPH_PATH', '')))

for path in ['/app/ephemeris', '/usr/share/swisseph/ephe']:
    print(f'Path {path} exists: {os.path.exists(path)}')
    if os.path.exists(path):
        print('Contents:', os.listdir(path))
