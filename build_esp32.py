import subprocess, json, os

build_path = 'C:/echosphere v2.2/hardware/ESp32/build'
sdk_path = 'C:/Users/Harshith/AppData/Local/Arduino15/packages/esp32/tools/esp32-libs/3.3.12'
gxx = 'C:/Users/Harshith/AppData/Local/Arduino15/packages/esp32/tools/esp-x32/2601/bin/xtensa-esp32-elf-g++.exe'
esptool = 'C:/Users/Harshith/AppData/Local/Arduino15/packages/esp32/tools/esptool_py/5.3.1/esptool.exe'

# 0. Sync ESp32.ino and all header files to build/sketch
src_dir = 'C:/echosphere v2.2/hardware/ESp32'
sketch_dir = 'C:/echosphere v2.2/hardware/ESp32/build/sketch'
ino_file = f'{src_dir}/ESp32.ino'
cpp_target = f'{sketch_dir}/ESp32.ino.cpp'

with open(ino_file, 'r', encoding='utf-8') as f:
    ino_content = f.read()

with open(cpp_target, 'w', encoding='utf-8') as f:
    f.write('#line 1 "C:\\\\echosphere v2.2\\\\hardware\\\\ESp32\\\\ESp32.ino"\n' + ino_content)

# Sync all header files into build/sketch
import shutil
for fname in os.listdir(src_dir):
    if fname.endswith(('.h', '.hpp')):
        src_f = os.path.join(src_dir, fname)
        dst_f = os.path.join(sketch_dir, fname)
        shutil.copy2(src_f, dst_f)
        print(f'Synced header: {fname} -> build/sketch/{fname}')

# 1. Compile sketch
with open('c:/echosphere v2.2/hardware/esp32/build/compile_commands.json') as f:
    data = json.load(f)

for item in data:
    fpath = item.get('file', '')
    if 'ESp32.ino.cpp' in fpath:
        cmd = item.get('arguments', [])
        print('1. Compiling sketch object...')
        res = subprocess.run(cmd, capture_output=True, text=True, cwd='c:/echosphere v2.2')
        if res.returncode != 0:
            print('Compilation error:', res.stderr)
            exit(1)
        print('Sketch compilation successful!')
        break

# 2. Link
obj_files = []
for root, dirs, files in os.walk(os.path.join(build_path, 'sketch')):
    for f in files:
        if f.endswith('.o'): obj_files.append(os.path.join(root, f).replace('/', '\\\\'))
for root, dirs, files in os.walk(os.path.join(build_path, 'libraries')):
    for f in files:
        if f.endswith('.o'): obj_files.append(os.path.join(root, f).replace('/', '\\\\'))

archive_file = os.path.join(build_path, 'core', 'core.a').replace('/', '\\\\')
map_flag = f'-Wl,--Map={build_path}/ESp32.ino.map'
out_elf = f'{build_path}/ESp32.ino.elf'

link_cmd = [
    gxx,
    map_flag,
    f'-L{sdk_path}/lib',
    f'-L{sdk_path}/ld',
    f'-L{sdk_path}/qio_qspi',
    '-Wl,--wrap=esp_panic_handler',
    '-Wl,--wrap=esp_bt_mem_release',
    '-Wl,--wrap=esp_bt_controller_mem_release',
    '-Wl,--wrap=_ZN4chip11DeviceLayer8Internal10ESP32Utils13InitWiFiStackEv',
    '-Wl,--wrap=_Z21esp_matter_mem_callocjj',
    '-Wl,--wrap=_Z22esp_matter_mem_reallocPvj',
    '-Wl,--wrap=_Z19esp_matter_mem_freePv',
    f'@{sdk_path}/flags/ld_flags',
    f'@{sdk_path}/flags/ld_scripts',
    '-Wl,--start-group'
] + obj_files + [
    archive_file,
    f'@{sdk_path}/flags/ld_libs',
    '-Wl,--end-group',
    '-Wl,-EL',
    '-o', out_elf
]

print('2. Linking ELF...')
res = subprocess.run(link_cmd, capture_output=True, text=True)
if res.returncode != 0:
    print('Link error:', res.stderr)
    exit(1)
print(f'Link successful! ELF size: {os.path.getsize(out_elf)}')

# 3. Create BIN image with esptool
out_bin = f'{build_path}/ESp32.ino.bin'
bin_cmd = [
    esptool,
    '--chip', 'esp32',
    'elf2image',
    '--flash-mode', 'dio',
    '--flash-freq', '80m',
    '--flash-size', '4MB',
    '--elf-sha256-offset', '0xb0',
    '-o', out_bin,
    out_elf
]
print('3. Generating BIN image with esptool...')
res = subprocess.run(bin_cmd, capture_output=True, text=True)
if res.returncode != 0:
    print('Image error:', res.stderr)
    exit(1)
print(f'Successfully generated BIN: {out_bin} ({os.path.getsize(out_bin)} bytes)')
