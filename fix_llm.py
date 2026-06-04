f = '/app/app/core/llm_client.py'
lines = open(f).readlines()
out = []
i = 0
while i < len(lines):
    if 'data = resp.json()' in lines[i]:
        # Remove lines 174-187 (the old try/except block)
        # Skip until we find the closing of LLMResponse
        while i < len(lines) and 'latency_ms=0,' not in lines[i]:
            i += 1
        i += 2  # skip latency_ms and closing )
        # Insert new SSE parser
        out.append('        raw = resp.text.strip()\n')
        out.append('        text = ""\n')
        out.append('        input_tokens = 0\n')
        out.append('        output_tokens = 0\n')
        out.append('        model_name = self.model\n')
        out.append('        for line in raw.splitlines():\n')
        out.append('            if line.startswith("data:"):\n')
        out.append('                chunk = line[5:].strip()\n')
        out.append('                try:\n')
        out.append('                    evt = __import__("json").loads(chunk)\n')
        out.append('                    if evt.get("type") == "content_block_delta":\n')
        out.append('                        text += evt.get("delta", {}).get("text", "")\n')
        out.append('                    elif evt.get("type") == "message_start":\n')
        out.append('                        m = evt.get("message", {})\n')
        out.append('                        model_name = m.get("model", self.model)\n')
        out.append('                        input_tokens = m.get("usage", {}).get("input_tokens", 0)\n')
        out.append('                    elif evt.get("type") == "message_delta":\n')
        out.append('                        output_tokens = evt.get("usage", {}).get("output_tokens", 0)\n')
        out.append('                except Exception:\n')
        out.append('                    pass\n')
        out.append('        return LLMResponse(text=text, model=model_name, input_tokens=input_tokens, output_tokens=output_tokens, latency_ms=0)\n')
    else:
        out.append(lines[i])
        i += 1
open(f, 'w').writelines(out)
print('DONE - line count:', len(out))
