# 📋 Setup Instructions for WawaTrader

Follow these steps to get your LLM-powered trading system running.

## ✅ Prerequisites Checklist

Before starting, make sure you have:

- [ ] **macOS** (tested on Mac M4)
- [ ] **Python 3.10+** installed
- [ ] **LM Studio** installed and running
- [ ] **Gemma 3 4B** model loaded in LM Studio
- [ ] **Alpaca Markets** account (free paper trading)

---

## 🔧 Step 1: LM Studio Setup

### 1.1 Install LM Studio

1. Download from [https://lmstudio.ai/](https://lmstudio.ai/)
2. Install and launch LM Studio
3. Accept any permissions required

### 1.2 Load Gemma 3 4B Model

1. In LM Studio, click **"Search"** tab
2. Search for: `google/gemma-3-4b`
3. Download the model (will take a few minutes)
4. Wait for download to complete

### 1.3 Start Local Server

1. Click **"Local Server"** tab in LM Studio
2. Select `google/gemma-3-4b` from model dropdown
3. Click **"Start Server"**
4. Server should start on `http://localhost:1234`
5. Leave LM Studio running in the background

### 1.4 Verify Server is Running

```bash
# Test the API endpoint
curl http://localhost:1234/v1/models

# You should see: {"data": [{"id": "google/gemma-3-4b", ...}]}
```

---

## 💼 Step 2: Alpaca Markets Setup

### 2.1 Create Account

1. Go to [https://alpaca.markets/](https://alpaca.markets/)
2. Click **"Sign Up"**
3. Complete registration (email verification required)
4. Choose **"Paper Trading"** account (free, no credit card needed)

### 2.2 Get API Keys

1. Log in to Alpaca dashboard
2. Navigate to: **Your Paper Trading** → **API Keys**
3. Click **"Generate New Key"**
4. **IMPORTANT**: Copy both keys immediately (secret key shown only once)
   - API Key (starts with `PK...`)
   - Secret Key (starts with `SK...`)
5. Save these securely - you'll need them next

---

## 🐍 Step 3: Python Environment Setup

### 3.1 Navigate to Project

```bash
cd /Users/wagnermontes/Documents/GitHub/_TESTS/WawaTrader
```

### 3.2 Create Virtual Environment

```bash
# Create venv
python3 -m venv venv

# Activate venv
source venv/bin/activate  # macOS/Linux
```

You should see `(venv)` in your terminal prompt.

### 3.3 Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt

# This will install:
# - alpaca-trade-api (market data & trading)
# - pandas, numpy (data analysis)
# - openai (for LM Studio API)
# - and more...
```

Installation takes 2-3 minutes.

---

## ⚙️ Step 4: Configuration

### 4.1 Create Environment File

```bash
# Copy the template
cp .env.example .env
```

### 4.2 Edit Configuration

```bash
# Open in your favorite editor
nano .env
# or
code .env
# or
open -a TextEdit .env
```

### 4.3 Add Your API Keys

Update these lines in `.env`:

```bash
# Replace with YOUR Alpaca API keys
ALPACA_API_KEY=PK...your_actual_key_here...
ALPACA_SECRET_KEY=SK...your_actual_secret_here...

# LM Studio should work with defaults
LM_STUDIO_BASE_URL=http://localhost:1234/v1
LM_STUDIO_MODEL=google/gemma-3-4b
```

**⚠️ Security Warning:**
- Never commit `.env` to git
- Never share your API keys
- Keep your secret key secure

### 4.4 Verify Configuration

```bash
python config/settings.py
```

Expected output:
```
WawaTrader Configuration
============================================================
Settings(
  Alpaca: https://paper-api.alpaca.markets
  LM Studio: http://localhost:1234/v1 (google/gemma-3-4b)
  Risk: max_pos=0.1, max_loss=0.02
  Trading: tech=0.7, sent=0.3
)
============================================================
✅ Configuration is valid
```

---

## 🧪 Step 5: Test Everything

### 5.1 Test LM Studio Connection

```bash
python tests/test_lm_studio.py
```

Expected output:
```
🔌 Testing LM Studio Connection...
============================================================
1️⃣ Checking available models...
   Available models: ['google/gemma-3-4b']
2️⃣ Testing chat completion...
   Model response: LM Studio connection successful!
3️⃣ Testing trading sentiment analysis...
   Model response: {"sentiment": "bullish", "confidence": 95, ...}
============================================================
✅ All tests passed! LM Studio is ready.
```

### 5.2 Test Alpaca Connection (Coming Soon)

```bash
# This will be available after Task 2 is completed
python tests/test_alpaca.py
```

---

## 🚀 Step 6: Ready to Build

You've completed the setup! Your environment is now configured with:

✅ Python virtual environment  
✅ All dependencies installed  
✅ LM Studio running with Gemma 3 4B  
✅ Alpaca API keys configured  
✅ Configuration validated  

**Next steps:**
- Task 2: Build Alpaca API integration
- Task 3: Implement technical indicators
- Task 4: Create LLM translation bridge
- Continue through the development roadmap

---

## 🐛 Troubleshooting

### LM Studio Issues

**Problem:** "Connection refused" error
```bash
# Solution: Make sure LM Studio server is running
# 1. Open LM Studio
# 2. Go to "Local Server" tab
# 3. Click "Start Server"
# 4. Wait for "Server running on http://localhost:1234"
```

**Problem:** "Model not found"
```bash
# Solution: Check model name matches
curl http://localhost:1234/v1/models
# Update LM_STUDIO_MODEL in .env to match the exact model ID
```

### Alpaca Issues

**Problem:** "Invalid API key"
```bash
# Solution: Verify keys are correct
# 1. Check .env file has no extra spaces
# 2. Make sure you copied PAPER TRADING keys (not live trading)
# 3. Keys should start with PK... and SK...
# 4. Regenerate keys if necessary from Alpaca dashboard
```

**Problem:** "Account not found"
```bash
# Solution: Make sure you're using paper trading URL
# In .env:
ALPACA_BASE_URL=https://paper-api.alpaca.markets  # NOT api.alpaca.markets
```

### Python Issues

**Problem:** "Module not found" errors
```bash
# Solution: Make sure venv is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

**Problem:** "pydantic validation error"
```bash
# Solution: Check .env file exists and has all required values
# Make sure you copied .env.example to .env
cp .env.example .env
```

### General Issues

**Problem:** Port 1234 already in use
```bash
# Solution: Change LM Studio port
# In LM Studio → Server Settings → Port: 1235
# Then update .env:
LM_STUDIO_BASE_URL=http://localhost:1235/v1
```

**Problem:** Mac M4 performance issues
```bash
# Solution: Close other applications
# LM Studio uses Neural Engine - make sure:
# - No other LLMs running
# - Chrome/heavy apps closed for best performance
# - Activity Monitor: check CPU/Memory usage
```

---

## 📞 Need Help?

1. Check the main [README.md](README.md) for architecture details
2. Review error messages carefully
3. Check logs in `logs/wawatrader.log`
4. Verify all prerequisites are met

---

## ⏭️ What's Next?

Once setup is complete, you can:

1. **Learn the Architecture**: Read `README.md` for system design
2. **Run Tests**: Execute `pytest` to verify components
3. **Start Development**: Follow the todo list in order
4. **Backtest Strategies**: Test on historical data (no risk)
5. **Paper Trade**: Run with real market data (no real money)

**⚠️ Remember:** 
- Stay in paper trading for minimum 3-6 months
- Never use real money until thoroughly tested
- This is educational software, not financial advice

---

**Happy Trading! 🚀📈**
