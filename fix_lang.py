with open('notion_push.py','r',encoding='utf-8') as f:
    c = f.read()
c = c.replace('"plaintext"', '"plain text"')
with open('notion_push.py','w',encoding='utf-8') as f:
    f.write(c)
print('Fixed plaintext -> plain text')
