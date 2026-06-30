with open("app.py", "r", encoding="utf-8") as f:
    data = f.read()
data = data.replace("\r\n", "\n")

old_line5 = '        print("  5. (\u5408\u5e76\u81f34)\u67e5\u770b\u603b\u90e8\u670d\u52a1\u5668\u6570\u636e")'
data = data.replace(old_line5, "", 1)
print("Menu line 5 removed")

for old, new in [("  6. ","  5. "),("  7. ","  6. "),("  8. ","  7. "),("  9. ","  8. ")]:
    if old in data: data = data.replace(old, new, 1)
print("Menu 6-9 renumbered to 5-8")

old_h5 = '        elif choice == "5":\n            print("  (\u5df2\u5408\u5e76\u81f3\u83dc\u53544)"); _view_main()\n'
data = data.replace(old_h5, "", 1)
print("Choice 5 handler removed")

repl_h = [("== '6':","== '5':"),("== '7':","== '6':"),("== '8':","== '7':"),("== '9':","== '8':")]
for old, new in repl_h:
    idx = data.find(old)
    if idx >= 0:
        data = data[:idx] + new + data[idx+len(old):]
print("Handlers 6-9 renumbered to 5-8")

search_dup = '        elif choice == "8":\n            _data_management()'
first = data.find(search_dup)
second = data.find(search_dup, first + 1)
if second >= 0:
    data = data[:second] + data[second+len(search_dup):]
    print("Duplicate choice 8 handler removed")

with open("app.py", "w", encoding="utf-8") as f:
    f.write(data)

import py_compile
try:
    py_compile.compile("app.py", doraise=True)
    print("Syntax OK! Menu cleaned up.")
except py_compile.PyCompileError as e:
    print(f"Syntax ERROR: {e}")
