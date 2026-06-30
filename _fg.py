with open("E:\AI_Projects\Codex\无人机勘测服务器搭建\服务器端\gateway.py", "r", encoding="utf-8") as f:
    data = f.read()

old = "_cm = {chr(39)+chr(92)+chr(117)+chr(54)+chr(55)+chr(54)+chr(100)+chr(92)+chr(117)+chr(53)+chr(100)+chr(100)+chr(101)+chr(39)+': hangzhou, '+chr(39)+chr(92)+chr(117)+chr(55)+chr(101)+chr(99)+chr(100)+chr(92)+chr(117)+chr(53)+chr(49)+chr(55)+chr(52)+chr(39)+': shaoxing}'"
new = old[:-1] + ", " + chr(39)+chr(92)+chr(117)+chr(54)+chr(50)+chr(50)+chr(100)+chr(92)+chr(117)+chr(57)+chr(48)+chr(49)+chr(97)+chr(39)+": 'zhaotong'}"
