#!/usr/bin/env python3

from pathlib import Path
import plistlib
import subprocess
import re
import csv

def app_uses_swift(path):
    libswiftPath = path / 'Frameworks' / 'libswiftCore.dylib'
    return libswiftPath.exists()

def is_executable(file_path):
    file_info = subprocess.run(["file", file_path], capture_output=True)
    return 'Mach-O' in str(file_info.stdout)

def find_executable_in(path):
    executables = [file for file in path.iterdir()
                   if is_executable(file)]
    return None if len(executables) == 0 else executables[0]

def class_dump(executable_path):
    header = str(subprocess.run(["class-dump", executable_path], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout)
    return re.findall("@interface ([\w_]+)\s?:\s?(\w+)", header)

def is_apple_class(class_tuple):
    prefixes = ["NS", "UI", "CA", "SCN", "SK", "CI", "AB", "ML", "GK", "AV"]
    for prefix in prefixes:
        pattern = re.compile(f'{prefix}[A-Z][a-z]+')
        if pattern.match(class_tuple[0]):
            return True
    return False

def percentage_classes_in_swift(classes):
    classes = [item for item in classes if not is_apple_class(item)]
    if len(classes) == 0: return 0.0
    swift_classes = [item for item in classes if item[0].startswith("_T")]
    return float(len(swift_classes)) / float(len(classes))
    
def analyze_app(path):
    results = {}
    infoPlistPath = path / 'Info.plist'
    with open(str(infoPlistPath.resolve()), 'rb') as infoPlistFile:
        infoPlist = plistlib.load(infoPlistFile)
    
    bundle_id = infoPlist['CFBundleIdentifier']
    app_name = infoPlist.get('CFBundleDisplayName', infoPlist.get('CFBundleName', infoPlist['CFBundleIdentifier']))
    print(f'analyzing {app_name} at {path.name}')
    results['app_name'] = app_name
    results['bundle_id'] = bundle_id
    results['sdk'] = infoPlist.get('DTSDKName')
    results['deployment_target'] = infoPlist.get('MinimumOSVersion')
    results['uses_swift'] = app_uses_swift(path)
    executable = find_executable_in(path)
    results['executable'] = executable.name
    classes = class_dump(executable)
    results['percentage_swift'] = percentage_classes_in_swift(classes)
    results['main_binary_uses_swift'] = results['percentage_swift'] > 0
    return results

apps = [path for path in Path.cwd().iterdir() if path.suffix == '.app']

with open('results.csv', mode='w', newline='') as csv_file:
    fieldnames = ['app_name', 'bundle_id', 'sdk', 'deployment_target', 'uses_swift', 'percentage_swift', 'main_binary_uses_swift', 'executable']
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()    
    writer.writerows(map(analyze_app, apps))
