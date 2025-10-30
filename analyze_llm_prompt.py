#!/usr/bin/env python3
"""
Quick script to analyze LLM prompts from conversation logs.
"""
import json

# Get last 100 entries
with open('logs/llm_conversations_v2.jsonl') as f:
    lines = f.readlines()[-100:]

# Find MU entry (the one with $250 resistance but actual price $221)
print("Searching for MU entry with problematic $250 mention...")
for line in lines:
    try:
        entry = json.loads(line)
        if entry.get('symbol') == 'MU':
            prompt = entry.get('prompt', '')
            response = entry.get('response', '')
            
            print('=' * 80)
            print('SYMBOL: MU (actual price should be ~$221.91)')
            print('=' * 80)
            
            print('\n1. Checking if prompt contains actual MU price ($221):')
            if '221' in prompt:
                print('   ✅ YES - found "221" in prompt')
                # Find context
                idx = prompt.find('221')
                context = prompt[max(0,idx-80):idx+120]
                print(f'   Context: ...{context}...')
            else:
                print('   ❌ NO - price 221 not found in prompt!')
            
            print('\n2. Checking for hardcoded template price ($150.00):')
            if 'Price: $150.00' in prompt:
                print('   ❌ PROBLEM: Template price found!')
                idx = prompt.find('Price: $150.00')
                context = prompt[max(0,idx-80):idx+120]
                print(f'   Context: ...{context}...')
            else:
                print('   ✅ Good - no hardcoded $150 template')
            
            print('\n3. Checking LLM response for problematic $250 mention:')
            if '250' in response:
                print('   ⚠️  FOUND "$250" in LLM response!')
                idx = response.find('250')
                context = response[max(0,idx-80):idx+120]
                print(f'   Context: ...{context}...')
            
            print('\n4. Full TECHNICAL DATA section from prompt:')
            print('-' * 80)
            tech_start = prompt.find('📊 TECHNICAL DATA')
            if tech_start > 0:
                tech_section = prompt[tech_start:tech_start+1000]
                print(tech_section)
            else:
                print("   ❌ Technical section not found!")
            
            print('\n5. Full LLM Response:')
            print('-' * 80)
            print(response)
            
            break
    except Exception as e:
        continue
else:
    print("❌ No MU entry found in last 100 log entries")
