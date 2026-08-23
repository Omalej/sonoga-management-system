path = 'sonoga_hms/settings.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
brace_depth = 0

for line in lines:
    if not skip and 'DATABASES' in line and '=' in line:
        skip = True
        new_lines.append("DATABASES = {\n")
        new_lines.append("    'default': {\n")
        new_lines.append("        'ENGINE': 'django.db.backends.sqlite3',\n")
        new_lines.append("        'NAME': BASE_DIR / 'db.sqlite3',\n")
        new_lines.append("    }\n")
        new_lines.append("}\n")
        brace_depth = line.count('{') - line.count('}')
        if brace_depth <= 0:
            skip = False
        continue

    if skip:
        brace_depth += line.count('{') - line.count('}')
        if brace_depth <= 0:
            skip = False
        continue

    new_lines.append(line)

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Settings successfully reset and fixed!")
