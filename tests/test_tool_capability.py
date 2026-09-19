import os
import dotenv
import groq

dotenv.load_dotenv()
client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_cpu_usage",
            "description": "Gets the current system CPU utilization percentage.",
            "parameters": {"type": "object", "properties": {}}
        }
    }
]

models_to_test = ["qwen/qwen3.8-27b", "groq/compound", "groq/compound-mini"]

for m in models_to_test:
    print(f"\nTesting model: {m}")
    try:
        response = client.chat.completions.create(
            model=m,
            messages=[
                {"role": "system", "content": "You are JARVIS, running locally on the user's computer. Use the tools provided."},
                {"role": "user", "content": "Check my CPU usage"}
            ],
            tools=tools,
            tool_choice="auto"
        )
        msg = response.choices[0].message
        if msg.tool_calls:
            print(f" [SUCCESS] Model {m} supports tool calling and successfully triggered a tool call: {msg.tool_calls[0].function.name}")
        else:
            print(f" [NO TOOL CALL] Model {m} responded with text instead of tool call: '{msg.content}'")
    except Exception as e:
        print(f" [ERROR] Model {m} failed: {e}")
