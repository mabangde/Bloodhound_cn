import os
import re
import argparse
import json
import mmap
from pathlib import Path
try:
    import ijson.backends.python as ijson
except (ImportError, ModuleNotFoundError):
    print('Error: install the Python ijson module first')

VERSION = 1.1

def main(args):
    # Collect args
    path = args.path
    chunksize = args.chunksize

    # Create output directory if it doesn't exist
    out_dir = 'outs'
    os.makedirs(out_dir, exist_ok=True)

    # Fixed variables
    jsonformat = '{"data":[%s],"meta":%s}'

    # If the path is a directory, process all JSON files in it and its subdirectories
    if os.path.isdir(path):
        json_files = []
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith('.json'):
                    json_files.append(os.path.join(root, file))

        # Process each JSON file
        for file in json_files:
            process_json_file(file, chunksize, out_dir, jsonformat, args.verbose)

    # If the path is a single file, process that file
    elif os.path.isfile(path) and path.endswith('.json'):
        process_json_file(path, chunksize, out_dir, jsonformat, args.verbose)

    else:
        print('Error: The specified path is not a JSON file or directory.')

def process_json_file(file, chunksize, out_dir, jsonformat, verbose):
    # Fix non-ASCII characters in JSON file
    fix_non_ascii(file, verbose)

    print('[+] Opening file %s' % file)
    with open(file, 'rb') as js:
        # Obtain meta tag
        js.seek(-0x100, os.SEEK_END)
        lastbytes = str(js.read(0x100))
        if verbose:
            print(f"lastbytes: {lastbytes}")
        metatagstr = re.search('("meta":(\s+)?{.*})', lastbytes, re.IGNORECASE).group(1).replace('\\n', "")
        if verbose:
            print(metatagstr)
        metatag = json.loads('{' + metatagstr)

    # Open in text mode to parse
    with open(file, 'r', encoding='utf-8-sig', errors='replace') as js:
        items = ijson.items(js, 'data.item')

        endoflist = False
        i = 0
        while True:
            basename = Path(file).stem  # 获取文件名（不包含扩展名）
            outfile = os.path.join(out_dir, f'{basename}_%.4d.json' % i)

            # Get chunk
            chunks = []
            count = 0
            try:
                while True:
                    item = next(items)
                    chunks.append(json.dumps(item))

                    count += 1
                    if count == chunksize:
                        break
            except StopIteration:
                endoflist = True

            # Update meta tag
            metatag['meta']['count'] = count

            # Format and store
            print('[+] Writing %s' % outfile)
            with open(outfile, 'w', encoding='utf-8-sig', errors='replace') as jsout:
                jsout.write(jsonformat % (','.join(chunks), json.dumps(metatag['meta'])))

            i += 1

            if endoflist:
                break

def getargs():
    parser = argparse.ArgumentParser(
        description='Convert large BloodHound json to smaller chunks'
    )
    parser.add_argument('path', help='Path to a JSON file or directory containing JSON files to split')
    parser.add_argument('-c', '--chunksize', default=500, type=int, dest='chunksize', help='Number of items per outputted chunk')
    parser.add_argument('-v', '--verbose', action=argparse.BooleanOptionalAction, help='Show verbose output')

    return parser.parse_args()

def fix_non_ascii(file, verbose):
    crapbytes = []

    print('Locating non-ASCII characters in %s' % file)
    with open(file, 'r+b') as f:
        mem = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        offset = 0
        for byte in mem:
            obyte = ord(byte)
            if (obyte < 0x20 or obyte > 0x7e) and obyte not in (0x0a, 0x0d):
                crapbytes.append(offset)
                if verbose:
                    print("Found non-ASCII character at offset 0x%.8x" % offset)

            offset += 1

        mem.close()
    print('Found a total of %d non-ASCII characters' % len(crapbytes))

    print('Fixing non-ASCII characters in %s' % file)
    with open(file, 'r+b') as f:
        mem = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_WRITE)

        # Navigate to offset and write question mark
        for offset in crapbytes:
            if verbose:
                print("Writing '?' to offset 0x%.8x" % offset)
            mem.seek(offset)
            mem.write_byte(0x3f)

        mem.close()
    print('Fixed a total of %d non-ASCII characters' % len(crapbytes))

if __name__ == '__main__':
    print('ChopHound v%.2f ( https://github.com/bitsadmin/chophound/ )' % VERSION)
    main(getargs())
