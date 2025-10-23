"""
Test LM Studio Connection

Verify that the local Gemma 3 4B model is accessible via LM Studio API.
"""

import sys
from openai import OpenAI

def test_lm_studio_connection():
    """Test connection to LM Studio"""
    
    print("🔌 Testing LM Studio Connection...")
    print("=" * 60)
    
    # Initialize OpenAI client pointing to LM Studio
    client = OpenAI(
        base_url="http://localhost:1234/v1",
        api_key="not-needed"  # LM Studio doesn't require API key
    )
    
    try:
        # Test 1: List available models
        print("\n1️⃣ Checking available models...")
        models = client.models.list()
        print(f"   Available models: {[model.id for model in models.data]}")
        
        # Test 2: Simple completion
        print("\n2️⃣ Testing chat completion...")
        response = client.chat.completions.create(
            model="google/gemma-3-4b",  # Adjust if your model name is different
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Be concise."},
                {"role": "user", "content": "Say 'LM Studio connection successful!' if you receive this message."}
            ],
            temperature=0.7,
            max_tokens=50
        )
        
        answer = response.choices[0].message.content
        print(f"   Model response: {answer}")
        
        # Test 3: Trading-related query
        print("\n3️⃣ Testing trading sentiment analysis...")
        response = client.chat.completions.create(
            model="google/gemma-3-4b",
            messages=[
                {"role": "system", "content": "You are a financial analyst. Analyze sentiment and respond in JSON."},
                {"role": "user", "content": """Analyze this news headline and respond ONLY with JSON:
"Apple reports record quarterly earnings, beats analyst expectations by 15%"

Format: {"sentiment": "bullish|neutral|bearish", "confidence": 0-100, "reasoning": "brief explanation"}"""}
            ],
            temperature=0.3,  # Lower temperature for more consistent JSON
            max_tokens=150
        )
        
        answer = response.choices[0].message.content
        print(f"   Model response:\n{answer}")
        
        print("\n" + "=" * 60)
        print("✅ All tests passed! LM Studio is ready.")
        print("=" * 60)
        
        # Use assertions instead of return
        assert client is not None, "Client should be initialized"
        assert response is not None, "Response should be received"
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure LM Studio is running")
        print("2. Verify the local server is started (port 1234)")
        print("3. Check that google/gemma-3-4b model is loaded")
        print("4. Try accessing: http://localhost:1234/v1/models")
        print("=" * 60)
        raise  # Re-raise the exception for pytest to catch


if __name__ == "__main__":
    success = test_lm_studio_connection()
    sys.exit(0 if success else 1)
