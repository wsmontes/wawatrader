# 🔑 Getting Your Alpaca API Keys

Quick guide to obtain your free Alpaca paper trading API keys.

## 📝 Step-by-Step Instructions

### 1. Sign Up for Alpaca

1. Go to [https://alpaca.markets/](https://alpaca.markets/)
2. Click **"Sign Up"** in the top right
3. Choose **"Paper Trading"** (free, no credit card needed)
4. Fill in your information:
   - Email address
   - Password
   - Name
   - Accept terms

### 2. Verify Email

1. Check your email for verification link
2. Click the verification link
3. Log in to Alpaca dashboard

### 3. Navigate to API Keys

1. After login, you'll see the dashboard
2. Look for **"Paper Trading"** section
3. Click on **"API Keys"** or navigate to:
   - **Your Paper Trading** → **API Keys**
   - Or go directly to: https://app.alpaca.markets/paper/dashboard/overview

### 4. Generate API Keys

1. Click **"Generate New Key"** button
2. You'll see two keys:
   - **API Key ID** (starts with `PK...`)
   - **Secret Key** (long alphanumeric string)

3. **⚠️ CRITICAL:** 
   - The **Secret Key** is shown ONLY ONCE
   - Copy BOTH keys immediately
   - Store them securely

### 5. Copy Keys to .env File

#### Option A: Use the Setup Script (Recommended)

```bash
cd /Users/wagnermontes/Documents/GitHub/_TESTS/WawaTrader
source venv/bin/activate
python scripts/setup_alpaca.py
```

The script will:
- ✅ Check if .env exists (create if needed)
- ✅ Prompt you for your keys
- ✅ Validate key format
- ✅ Update .env automatically
- ✅ Test the connection

#### Option B: Manual Configuration

```bash
# Copy template
cp .env.example .env

# Edit the file
nano .env
# or
code .env
```

Update these lines:
```bash
ALPACA_API_KEY=PK...your_actual_key_here...
ALPACA_SECRET_KEY=SK...your_actual_secret_here...
```

**Make sure:**
- No extra spaces around the `=` sign
- No quotes around the keys
- Keys are on a single line

### 6. Verify Configuration

Test your connection:

```bash
# Quick test
python wawatrader/alpaca_client.py

# Full test suite
python tests/test_alpaca.py
```

Expected output:
```
✅ Connected to Alpaca (Account: ...)
   Status: ACTIVE
   Buying Power: $100,000.00
```

---

## 🔒 Security Best Practices

### DO:
- ✅ Use **Paper Trading** keys (not live trading)
- ✅ Keep your `.env` file **private** (already in `.gitignore`)
- ✅ Regenerate keys if accidentally exposed
- ✅ Use different keys for different projects

### DON'T:
- ❌ Commit `.env` to git
- ❌ Share keys publicly
- ❌ Use live trading keys for testing
- ❌ Hard-code keys in source files

---

## 🐛 Troubleshooting

### "Invalid API key" error

**Problem:** API key not recognized

**Solutions:**
1. Verify you copied the full key (no truncation)
2. Check for extra spaces in .env file
3. Make sure you're using **Paper Trading** keys
4. API key should start with `PK...`
5. Secret key should be a long alphanumeric string
6. Try regenerating keys in Alpaca dashboard

### "Account not found" error

**Problem:** Using wrong API endpoint

**Solution:** Verify in `.env`:
```bash
ALPACA_BASE_URL=https://paper-api.alpaca.markets
# NOT: https://api.alpaca.markets (that's live trading)
```

### Secret key not showing

**Problem:** Secret key only shown once during generation

**Solution:**
1. Generate a new key pair
2. Immediately copy both keys
3. Old keys are automatically revoked

### Can't find API Keys page

**Navigation path:**
1. Log in to Alpaca
2. Look for "Paper Trading" section in left sidebar
3. Click "API Keys" under Paper Trading
4. Or use direct link: https://app.alpaca.markets/paper/dashboard/overview

---

## 💡 Pro Tips

### Test Connection First
Before building strategies, verify your connection:
```bash
python tests/test_alpaca.py
```

### Check Account Status
View your paper trading account anytime:
```bash
python wawatrader/alpaca_client.py
```

### View Examples
Learn common operations:
```bash
python examples/alpaca_examples.py
```

### Paper Trading Limits
Your paper account comes with:
- 💰 **$100,000** initial capital
- 📈 Real market data (15-min delayed quotes free)
- ♾️ Unlimited trades
- 🔄 Reset anytime from dashboard

---

## 📞 Need Help?

1. **Alpaca Support:** https://alpaca.markets/support
2. **Alpaca Docs:** https://alpaca.markets/docs/
3. **Project Setup:** See `SETUP.md`
4. **Examples:** See `examples/alpaca_examples.py`

---

## ⏭️ Next Steps

Once your keys are configured and tested:

1. ✅ **Task 2 Complete!** Alpaca API integrated
2. ⏭️ **Task 3:** Build technical indicators (RSI, MACD, etc.)
3. 🎯 **Task 4:** Create LLM translation bridge
4. 🚀 **Tasks 5+:** Build the full trading system

---

**Your keys are ready! Time to fetch some market data! 📊**
