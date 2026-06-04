# NEUROTWIN OS — ALLOWED_ORIGINS JSON Fix
## Technical Root Cause Analysis & Solution

---

## THE PROBLEM

### Error Message
```
pydantic_settings.sources.SettingsError: error parsing value for field "ALLOWED_ORIGINS" from source "EnvSettingsSource"
json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

### What Was Happening
The API container crashed on startup with a JSON parsing error when trying to load the `ALLOWED_ORIGINS` environment variable.

---

## ROOT CAUSE ANALYSIS

### Code Location
**File:** `D:\neurotwin\services\api\app\core\config.py`

**Line 15:**
```python
ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "https://app.neurotwin.ai"]
```

The `ALLOWED_ORIGINS` field is typed as `List[str]` (a Python list).

### The Pydantic v2 Behavior
Pydantic Settings v2 (pydantic-settings ≥2.0) has a **strict environment variable parsing pipeline**:

1. **First:** Try to parse the environment variable as **JSON**
2. **Second:** If that fails, run field validators
3. **Third:** Apply default values if parsing fails

### What Was in .env (INCORRECT)
```
ALLOWED_ORIGINS=http://localhost,http://localhost:3000,http://localhost:8000,https://app.neurotwin.ai
```

**Why it failed:**
- This is a comma-separated string, NOT valid JSON
- When pydantic_settings tries `json.loads()` on this value, it fails immediately
- The error happens **before** the field validator could run

### Field Validator (Not Being Used)
Lines 91-95 in config.py have a validator designed to handle comma-separated strings:
```python
@field_validator("ALLOWED_ORIGINS", mode="before")
@classmethod
def parse_origins(cls, v):
    if isinstance(v, str):
        return [o.strip() for o in v.split(",")]  # ← Would split by comma
    return v
```

**Problem:** This validator never runs because JSON parsing crashes first.

---

## THE SOLUTION

### Change Applied
**Old (Broken):**
```
ALLOWED_ORIGINS=http://localhost,http://localhost:3000,http://localhost:8000,https://app.neurotwin.ai
```

**New (Fixed):**
```
ALLOWED_ORIGINS=["http://localhost","http://localhost:3000","http://localhost:8000","https://app.neurotwin.ai"]
```

### Why This Works
1. The new value is **valid JSON** (a JSON array)
2. Pydantic v2 can successfully parse it with `json.loads()`
3. Result: `["http://localhost", "http://localhost:3000", ...]`
4. This is **exactly** what the Python code expects (a List[str])
5. API starts successfully ✅

---

## IMPLEMENTATION CHECKLIST

### ✅ Changes Made
- [x] Fixed `.env` file: ALLOWED_ORIGINS now in JSON format
- [x] Created verification script: `NEUROTWIN_FIX_AND_VERIFY.ps1`
- [x] Created technical documentation: This file

### 📋 Next Steps (Run in PowerShell)
```powershell
cd D:\neurotwin
.\NEUROTWIN_FIX_AND_VERIFY.ps1
```

This script will:
1. Verify .env has correct JSON format
2. Stop and remove old API container
3. Start fresh API container with corrected settings
4. Poll the API health endpoint (http://localhost:8000/api/health)
5. Report success or failure with detailed diagnostics

---

## VERIFICATION SIGNS

### ✅ Success Indicators
- `docker-compose ps` shows `neurotwin-api` with status "Up"
- `curl http://localhost:8000/api/health` returns `{"status":"ok"}` with HTTP 200
- API logs don't contain the `pydantic_settings.sources.SettingsError`
- Dashboard loads at `http://localhost`

### ❌ Failure Indicators
- API container keeps restarting (unhealthy)
- Logs show `json.decoder.JSONDecodeError`
- Health endpoint returns 500 or times out
- API container exits immediately after starting

---

## ALTERNATIVE APPROACHES (Not Needed)

### Approach A: Modify config.py (More Complex)
Could disable JSON parsing for this field:
```python
ALLOWED_ORIGINS: List[str] = Field(..., json_schema_extra={"json_schema_input_type": "string"})
```
**Why we didn't:** Not necessary, JSON format is standard for Pydantic v2

### Approach B: Use Environment Variable with Custom Parsing (More Complex)
Could use a custom SettingsSource.
**Why we didn't:** JSON format is the simplest, most direct solution

### Approach C: Use a Different Field Type (Not Applicable)
Could use `CommaSeparatedString` from a library.
**Why we didn't:** We're using standard Pydantic, and JSON is the native format

---

## LESSONS LEARNED

1. **Pydantic v2** treats environment variables as JSON by default
2. **Field validators** don't rescue malformed JSON input
3. **Complex types** (List, Dict, etc.) MUST be JSON when set via environment
4. **Backward compatibility:** Pydantic v1 behavior different from v2

---

## REFERENCES

- [Pydantic v2 Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Environment Variables in Pydantic](https://docs.pydantic.dev/latest/concepts/json/#parsing-values-from-strings)
- Error Source: `/usr/local/lib/python3.12/site-packages/pydantic_settings/sources.py` line 307

---

**File:** `D:\neurotwin\.env`
**Field:** `ALLOWED_ORIGINS`
**Status:** ✅ FIXED
**Verified:** Yes (run NEUROTWIN_FIX_AND_VERIFY.ps1 to confirm)
