# LLM Generator - Troubleshooting Guide

## Common Issues and Solutions

### 1. Generation Issues

#### Issue: Code contains line numbers

**Symptom:**
```
   1|from fastapi import FastAPI
   2|app = FastAPI()
```
Causes `IndentationError` when running.

**Cause:** LLM outputs code with embedded line numbers.

**Solution:** Already handled automatically by `_clean_line_numbers()` in code_agent.py. If still occurring:
1. Check the SYSTEM_PROMPT includes instruction to not output line numbers
2. Ensure `generate_file()` calls `_clean_line_numbers(code)` after generation

---

#### Issue: JSON files are single-line

**Symptom:**
```json
{"name":"calendar","version":"1.0.0","description":"..."}
```

**Cause:** LLM outputs compact JSON without formatting.

**Solution:**
1. `reflect_on_file()` detects single-line JSON and adds `JSON_FORMAT` issue
2. `fix_issues()` reformats with `json.dumps(data, indent=2)`
3. Check SYSTEM_PROMPT emphasizes proper JSON formatting

---

#### Issue: tsconfig.node.json always fails

**Symptom:** Repeated syntax errors or invalid JSON in tsconfig.node.json

**Cause:** LLM may output Python dict syntax or malformed JSON.

**Solution:**
1. Special handling added in `generate_file()` for tsconfig files
2. Uses explicit format instructions:
```
CRITICAL tsconfig.node.json REQUIREMENTS:
- Output VALID JSON only, NOT Python dict
- Use DOUBLE QUOTES (") for ALL strings
- Use lowercase: null, true, false
- NO trailing commas
```

---

#### Issue: Code truncated mid-generation

**Symptom:** File ends with incomplete function, missing closing brackets.

**Cause:** LLM max_tokens limit reached.

**Solution:**
1. `_detect_truncation()` checks for unbalanced brackets
2. `_ensure_complete_code()` prompts LLM to continue
3. Increase `max_tokens` in config (current: 128000)

---

#### Issue: Infinite regeneration loop

**Symptom:** Same file keeps regenerating, log shows repeated syntax errors.

**Cause:** LLM reflection reports errors that don't exist (false positive).

**Solution:**
1. Trust automated `syntax_check` over LLM analysis
2. Filter in `reflect_on_file()`:
```python
if "SYNTAX" in issue and automated_syntax_passed:
    continue  # Ignore LLM's false positive
```

---

### 2. Import Errors

#### Issue: ModuleNotFoundError: No module named 'calendar_api'

**Symptom:** Server fails to start with import error.

**Cause:** Using absolute imports (`from calendar_api.database`) when running from within the package directory.

**Solution:**
1. Convert to relative imports: `from .database import ...`
2. Generator's `fix_issues()` handles this automatically
3. Ensure backend tests run from correct directory

---

#### Issue: Missing __init__.py files

**Symptom:** Package imports fail.

**Cause:** LLM forgot to generate __init__.py.

**Solution:**
1. `_get_phase_spec("backend")` explicitly includes __init__.py files
2. `verify_planned_files()` checks for missing files
3. Generator creates missing __init__.py in fix phase

---

### 3. Runtime Testing Issues

#### Issue: Port already in use

**Symptom:** `Address already in use: 8008`

**Cause:** Previous test left server running.

**Solution:**
1. `_run_backend_tests()` now kills existing processes on port:
```python
lsof_output = subprocess.check_output(["lsof", "-i", ":8008", "-t"])
for pid in lsof_output.strip().split('\n'):
    subprocess.run(["kill", "-9", pid])
```

---

#### Issue: Python command not found

**Symptom:** Server can't start, `python` not found.

**Cause:** Different systems use `python` vs `python3` vs conda python.

**Solution:**
1. Use `sys.executable` instead of hardcoded `python`:
```python
command = f"{sys.executable} -m uvicorn main:app --port 8008"
```

---

#### Issue: Tests pass but VERIFY PASS shows with errors

**Symptom:** Server tests fail but phase marked as pass.

**Cause:** Verification events emitted before tests complete.

**Solution:**
1. Only emit `VERIFICATION_PASS` when `result.issues` is empty
2. Ensure test results are added to issues list

---

### 4. File/Path Issues

#### Issue: read_file fails with "File not found"

**Symptom:** Agent tries to read non-existent file.

**Cause:** Agent used partial path like "database.py" instead of "calendar_api/database.py".

**Solution:**
1. `_resolve_file_path()` searches for file in generated directories
2. Returns correct full path
3. `list_generated()` shows actual file paths

---

#### Issue: grep returns too many results

**Symptom:** grep with `path='.'` searches entire directory.

**Cause:** Agent not specifying specific path.

**Solution:**
1. Encourage specific paths in prompts
2. Limit grep results
3. Use `_smart_truncate_file()` for large outputs

---

### 5. Memory/Checkpoint Issues

#### Issue: Generation doesn't resume correctly

**Symptom:** Files regenerated despite checkpoint showing complete.

**Cause:** File content invalid (e.g., truncated) but marked complete.

**Solution:**
1. `is_file_complete()` validates actual content:
   - JSON: `json.loads()` succeeds
   - Python: `compile()` succeeds
2. Invalid files are marked for regeneration

---

#### Issue: Memory not persisting across runs

**Symptom:** Agent doesn't learn from previous runs.

**Solution:**
1. Check memory save/load in main.py:
```python
orchestrator.save_memory(memory_file)
# On resume:
orchestrator.load_memory(memory_file)
```

---

### 6. API/Network Issues

#### Issue: OpenAI API error: max_tokens too large

**Symptom:** `max_tokens is too large: 160000`

**Cause:** Model doesn't support requested token count.

**Solution:**
1. GPT-5.1 supports max 128000 completion tokens
2. Set `max_tokens=128000` in config

---

#### Issue: API rate limiting

**Symptom:** Generation slows down or fails intermittently.

**Solution:**
1. Add retry logic with exponential backoff
2. Reduce parallel API calls
3. Use checkpointing to resume on failure

---

## Debugging Tips

### Enable Verbose Logging

```bash
python -m llm_generator.main --name test --description "test" --verbose
```

### Watch Real-time Log

```bash
tail -f generated/calendar_realtime.log
```

### Check Specific Tool Calls

Look for `TOOL:` entries in realtime log:
```
[21:22:45] 🔧 TOOL: grep pattern='APIRouter' path='.'
[21:22:45] ✅ TOOL RESULT: success, found 5 matches
```

### Inspect Checkpoint

```bash
cat generated/calendar/.checkpoint.json | python -m json.tool
```

### Test Individual Components

```python
# Test syntax check
from llm_generator.tools.code_tools import SyntaxCheckTool
tool = SyntaxCheckTool()
result = await tool.execute(code="def foo(): pass", language="python")
print(result)
```

### Force Regeneration

Delete checkpoint to start fresh:
```bash
rm generated/calendar/.checkpoint.json
```

Or delete specific file to regenerate:
```bash
rm generated/calendar/calendar_api/main.py
```

## Log File Locations

| File | Purpose |
|------|---------|
| `{name}_realtime.log` | Human-readable event stream |
| `{name}_generation.log` | JSON event log |
| `.checkpoint.json` | Progress state |
| `memory.json` | Persisted agent memory |

## Getting Help

1. Check the logs first - most issues are visible there
2. Look for specific error patterns in this guide
3. Enable `--verbose` for more detail
4. Check if the issue was already fixed in a later iteration

