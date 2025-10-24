# LM Studio Integration Upgrade

## What Changed

We've upgraded from using the OpenAI-compatible API to the **official LM Studio Python SDK** (`lmstudio-python`). This provides:

### ✨ New Features

1. **Automatic Model Loading** 🚀
   - No need to manually load models in LM Studio GUI
   - SDK automatically loads your configured model if not already in memory
   - Supports multiple model instances

2. **Better Error Handling** 🛡️
   - Native error messages from LM Studio
   - Health checking before queries
   - Graceful fallback if SDK unavailable

3. **Enhanced Monitoring** 📊
   - Prediction statistics (tokens, timing, stop reason)
   - Model information in responses
   - Better logging of model state

4. **Cleaner API** 🎯
   - Native `Chat` objects for conversation management
   - Streaming support with progress callbacks
   - Configuration parameters as proper Python objects

## Installation

### Step 1: Install the SDK

```bash
pip install lmstudio
```

Or update your entire environment:

```bash
pip install -r requirements.txt
```

### Step 2: Verify Installation

```bash
python -c "import lmstudio; print('✅ LM Studio SDK installed')"
```

## Usage

### Option A: Use New Enhanced Bridge (Recommended)

```python
from wawatrader.llm_bridge_v2 import LLMBridgeV2

# Initialize (automatically checks and loads model)
bridge = LLMBridgeV2()

# Check health
health = bridge.check_health()
print(f"Model loaded: {health['model_loaded']}")
print(f"Available: {health['available']}")

# Analyze market (same API as before)
analysis = bridge.analyze_market(
    symbol='AAPL',
    signals=signals_dict,
    news=news_list,
    current_position=position_dict
)
```

### Option B: Keep Using Legacy Bridge

The original `llm_bridge.py` still works with the OpenAI-compatible API. No changes needed if you prefer to keep using it.

## Key Differences

### Old Way (OpenAI-Compatible API)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="not-needed"
)

response = client.chat.completions.create(
    model="google/gemma-3-4b",
    messages=[...],
    temperature=0.7
)
```

**Issues:**
- ❌ Must manually load model in LM Studio GUI
- ❌ No automatic model checking
- ❌ Generic error messages
- ❌ Can't list or manage models programmatically

### New Way (Official SDK)

```python
import lmstudio as lms

# Automatically loads model if needed
model = lms.llm("google/gemma-3-4b")

# Create chat
chat = lms.Chat("You are a trading analyst")
chat.add_user_message("Analyze this...")

# Get response with stats
result = model.respond(chat, config={"temperature": 0.7})

print(result.content)
print(f"Tokens: {result.stats.predicted_tokens_count}")
print(f"Model: {result.model_info.display_name}")
```

**Benefits:**
- ✅ Automatic model loading
- ✅ Built-in health checking
- ✅ Rich metadata and statistics
- ✅ Model management APIs

## Migration Path

### For Existing Users

**Nothing breaks!** The new `llm_bridge_v2.py` coexists with the old one:

1. **Install SDK**: `pip install lmstudio`
2. **Test new bridge**: `python wawatrader/llm_bridge_v2.py`
3. **Switch when ready**: Update imports to use `LLMBridgeV2`

### Fallback Behavior

If the SDK isn't installed, `LLMBridgeV2` **automatically falls back** to the OpenAI-compatible client. You get:

- ✅ Same API (no code changes needed)
- ⚠️ Legacy features (manual model loading required)
- ⚠️ Less detailed error messages

## Configuration

No changes to `.env` file needed! Uses same settings:

```bash
LM_STUDIO_BASE_URL=http://localhost:1234/v1
LM_STUDIO_MODEL=google/gemma-3-4b
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=-1
```

## Advanced Features

### List Loaded Models

```python
import lmstudio as lms

loaded_models = lms.list_loaded_models("llm")
for model in loaded_models:
    print(f"- {model.identifier}")
```

### Load Multiple Instances

```python
import lmstudio as lms

model1 = lms.llm("google/gemma-3-4b")
model2 = lms.llm("qwen2.5-7b-instruct")

# Use different models for different tasks
conservative_analysis = model1.respond(chat1)
aggressive_analysis = model2.respond(chat2)
```

### Streaming Responses

```python
import lmstudio as lms

model = lms.llm()
for fragment in model.respond_stream("Analyze AAPL..."):
    print(fragment.content, end="", flush=True)
```

### Auto-Unload (TTL)

```python
import lmstudio as lms

# Automatically unload after 1 hour of inactivity
model = lms.llm("google/gemma-3-4b", ttl=3600)
```

## Troubleshooting

### "Import lmstudio could not be resolved"

```bash
# Solution: Install the SDK
pip install lmstudio
```

### "Model not found"

The SDK will **automatically load** the model. If it fails:

1. Check model is downloaded in LM Studio
2. Verify model name in settings
3. Check LM Studio server is running

```bash
# Check loaded models
python -c "import lmstudio as lms; print(lms.list_loaded_models())"
```

### "Connection refused"

LM Studio server must be running:

1. Open LM Studio app
2. Go to "Local Server" tab
3. Click "Start Server"
4. Verify: `curl http://localhost:1234/v1/models`

## Performance

The official SDK provides better performance insights:

```python
result = model.respond(chat)

# Timing metrics
print(f"Time to first token: {result.stats.time_to_first_token_sec:.2f}s")
print(f"Total tokens: {result.stats.predicted_tokens_count}")
print(f"Stop reason: {result.stats.stop_reason}")

# Model info
print(f"Model: {result.model_info.display_name}")
print(f"Context length: {result.model_info.context_length}")
```

## Testing

Test the new integration:

```bash
# Test health check
python wawatrader/llm_bridge_v2.py

# Run unit tests (coming soon)
pytest tests/test_llm_bridge_v2.py -v
```

## References

- [LM Studio Python SDK Docs](https://lmstudio.ai/docs/python)
- [GitHub: lmstudio-python](https://github.com/lmstudio-ai/lmstudio-python)
- [Chat Completions](https://lmstudio.ai/docs/python/llm-prediction/chat-completion)
- [Model Management](https://lmstudio.ai/docs/python/manage-models/loading)

## Next Steps

1. ✅ Install SDK: `pip install lmstudio`
2. ✅ Test: `python wawatrader/llm_bridge_v2.py`
3. ✅ Update imports in your code
4. ✅ Enjoy automatic model loading! 🎉

---

**Note**: Both bridges (`llm_bridge.py` and `llm_bridge_v2.py`) will coexist during the transition period. Choose which one works best for your workflow!
