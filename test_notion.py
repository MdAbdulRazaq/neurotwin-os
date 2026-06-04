import sys, urllib.request, json
token = sys.argv[1]
print(f"Token len: {len(token)}, starts: {token[:8]}")
req = urllib.request.Request(
    'https://api.notion.com/v1/users/me',
    headers={'Authorization': f'Bearer {token}', 'Notion-Version': '2022-06-28'},
    method='GET'
)
r = urllib.request.urlopen(req)
print(json.loads(r.read())['name'])
