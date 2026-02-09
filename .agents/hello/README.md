# Hello World Test

Quick test to verify Ollama integration works correctly.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure Ollama is running:
```bash
ollama serve
```

3. Pull a model (if not already done):
```bash
ollama pull qwen
```

## Run Test

From the project root:
```bash
python src/tools/hello_world.py
```

## Expected Output

```
🌍 RotRL Hello World Test
==================================================
📄 Loading prompt from: ./.agents/hello/PROMPT.md
✅ Prompt loaded (XXX characters)

🤖 Calling Ollama (qwen) at http://localhost:11434...
✅ Response received: 'hello world'

🔍 Validating response...
✅ PASS: Response is exactly 'hello world'

==================================================
🎉 Hello World test PASSED!
```

## What This Tests

- ✅ Ollama connection and API
- ✅ Prompt loading from file
- ✅ Response parsing and validation
- ✅ Strict output matching

This is the foundation for more complex agent interactions.
