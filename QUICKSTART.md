# 🚀 Quick Start Guide

**Get WawaTrader running in 10 minutes!**

## ⚡ Super Quick Setup

```bash
# 1. Navigate to project
cd /Users/wagnermontes/Documents/GitHub/_TESTS/WawaTrader

# 2. Activate virtual environment
source venv/bin/activate

# 3. Create and configure .env
cp .env.example .env
# Edit .env and add your Alpaca API keys

# 4. Test everything
python tests/test_lm_studio.py
```

## ✅ Current Status

### Task 1: Project Setup ✅ COMPLETED

**What's been built:**

```
WawaTrader/
├── 📦 Core Files
│   ├── requirements.txt       ✅ All dependencies defined
│   ├── setup.py              ✅ Package configuration
│   ├── .env.example          ✅ Configuration template
│   ├── .gitignore            ✅ Git ignore rules
│   ├── README.md             ✅ Full documentation
│   └── SETUP.md              ✅ Setup instructions
│
├── ⚙️ Configuration
│   ├── config/__init__.py    ✅ Config exports
│   └── config/settings.py    ✅ Settings management
│
├── 🤖 Main Package
│   └── wawatrader/__init__.py ✅ Package structure
│
├── 🧪 Tests
│   ├── tests/__init__.py     ✅ Test package
│   └── tests/test_lm_studio.py ✅ LM Studio tests
│
└── 🐍 Virtual Environment
    └── venv/                  ✅ Python 3.12 + all packages
```

**What's working:**

- ✅ Python virtual environment created
- ✅ All dependencies installed (35+ packages)
- ✅ Configuration management system
- ✅ LM Studio connection verified
- ✅ Gemma 3 4B model responding correctly
- ✅ JSON response parsing working
- ✅ Project structure established

## 🎯 What You Can Do Now

### 1. Verify LM Studio

```bash
python tests/test_lm_studio.py
```

Expected: All 3 tests pass ✅

### 2. Check Configuration

```bash
python config/settings.py
```

Expected: Configuration loads successfully

### 3. Test Sentiment Analysis

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:1234/v1", api_key="not-needed")

response = client.chat.completions.create(
    model="google/gemma-3-4b",
    messages=[
        {"role": "system", "content": "You are a financial analyst."},
        {"role": "user", "content": "Is this bullish or bearish: 'Stock drops 20% on earnings miss'"}
    ],
    temperature=0.7
)

print(response.choices[0].message.content)
```

## 📋 Next Tasks

### Ready to Build:

**Task 2: Alpaca API Integration** ⏭️ NEXT
- Connect to Alpaca paper trading
- Fetch market data
- Test account access

**Task 3: Technical Indicators**
- Build RSI, MACD, SMA, etc.
- Pure NumPy/Pandas calculations
- Unit tests for accuracy

**Task 4: LLM Translation Bridge**
- Format numbers → text for LLM
- Parse LLM responses → structured data
- Validation and error handling

## 🛠️ Development Workflow

```bash
# Always activate venv first
source venv/bin/activate

# Make sure LM Studio is running
# Check: http://localhost:1234/v1/models

# Run tests
pytest tests/

# Check configuration
python config/settings.py

# When you're done
deactivate
```

## 📊 System Architecture Reminder

```
User Request
    ↓
[Market Data] → [Technical Indicators (NumPy/Pandas)]
    ↓                        ↓
[Format as Text]    [Calculate RSI, MACD, etc.]
    ↓                        ↓
[LLM Interprets] ← [Numerical Results]
    ↓                        ↓
[Parse Response]    [Combine Signals 70/30]
    ↓                        ↓
[Validate]          [Apply Risk Rules]
    ↓                        ↓
[Execute Trade on Alpaca Paper Account]
    ↓
[LLM Explains Decision]
```

## ⚠️ Important Reminders

1. **LM Studio must be running** on port 1234
2. **Always use paper trading** - never real money
3. **Alpaca keys** go in `.env` file (not committed to git)
4. **Virtual environment** must be activated for all Python commands
5. **Test thoroughly** before any trading execution

## 🔥 Performance Notes (Mac M4)

Your Mac M4 is perfect for this:
- **Neural Engine** accelerates Gemma 3 inference
- **Unified Memory** allows fast data transfer
- **Expected latency:**
  - Technical indicators: < 1ms
  - LLM inference: 50-200ms
  - Total decision cycle: 200-500ms

This is fast enough for:
- ✅ Daily trading strategies
- ✅ Swing trading
- ✅ Intraday positions
- ❌ High-frequency trading (requires < 10ms)

## 💡 Tips

**Faster LLM responses:**
```python
# Use lower max_tokens for simple queries
response = client.chat.completions.create(
    model="google/gemma-3-4b",
    messages=[...],
    max_tokens=50,  # Instead of -1 (unlimited)
    temperature=0.3  # Lower = more consistent
)
```

**Better JSON responses:**
```python
# Be explicit in prompts
messages=[
    {"role": "system", "content": "Respond ONLY with valid JSON. No markdown."},
    {"role": "user", "content": "Format: {\"sentiment\": \"bullish\", \"confidence\": 85}"}
]
```

## 📞 Support

- **Documentation**: See `README.md` for full details
- **Setup Help**: See `SETUP.md` for step-by-step guide
- **Architecture**: See `README.md` → Architecture section
- **Troubleshooting**: See `SETUP.md` → Troubleshooting section

## ✨ Ready to Continue?

Task 1 is complete! When you're ready:

```bash
# Say the word and I'll start building Task 2: Alpaca API Integration
# This will add:
# - Alpaca client connection
# - Market data fetching
# - Account information utilities
# - Integration tests
```

**Current completion: 1/15 tasks (6.7%) ✅**

---

**Remember:** This is a learning project. Take time to understand each component. Don't rush to live trading!

🎯 **Goal**: Build a robust, transparent, testable trading system.  
⏰ **Timeline**: Minimum 3-6 months paper trading before any real money consideration.  
💰 **Cost**: $0 (everything is free for paper trading)

**Let's build something amazing! 🚀**
