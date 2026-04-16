import asyncio
import os
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root / "apps" / "api"))
from src.main_dependencies import get_llm_gateway

async def main():
    llm = get_llm_gateway()
    
    # Create a dummy payload large enough
    large_payload = [
        {"role": "user", "content": "Hello, please just say 'CONFIRMED'. Here is some padding text: " + "PADDING_DATA " * 15000}
    ]
    
    print(f"Payload char length: {len(large_payload[0]['content'])}")
    print("Calling LLM Gateway...")
    
    try:
        response = await llm.chat(large_payload, max_tokens=20000)
        print("Success! Got response:")
        print(response)
    except Exception as e:
        print("Error!")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())
