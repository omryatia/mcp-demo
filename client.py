#!/usr/bin/env python3
"""
Simple MCP Client using FastMCP - Much cleaner!
"""

import asyncio
import json
import os
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv
from fastmcp import Client

# Load environment variables
load_dotenv()

class MCPClient:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        
    async def call_llm(self, message: str, tools_available: List[Dict], client: Client) -> str:
        """Call Groq LLM with tool support, fallback to pattern matching"""
        
        # Convert FastMCP tools to Groq format
        tools_schema = []
        for tool in tools_available:
            tools_schema.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool.get("inputSchema", {})
                }
            })
        
        # Try Groq if API key is available
        if self.groq_api_key and self.groq_api_key != "your_groq_key_here":
            try:
                return await self._call_groq(message, tools_schema, client)
            except Exception as e:
                print(f"🔄 Groq failed: {e}, using pattern matching...")
        
        # Fallback to simple pattern matching
        return await self._simple_weather_response(message, client)
    
    async def _call_groq(self, message: str, tools_schema: List[Dict], client: Client) -> str:
        """Call Groq API"""
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "llama3-8b-8192",  # Free Groq model
            "messages": [
                {
                    "role": "system", 
                    "content": "You are a helpful weather assistant. When users ask about weather, use the get_weather tool to get current conditions."
                },
                {"role": "user", "content": message}
            ],
            "tools": tools_schema,
            "max_tokens": 1000
        }
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30.0
        )
        response.raise_for_status()
        result = response.json()
        
        return await self._handle_tool_calls(result, data, headers, "https://api.groq.com/openai/v1/chat/completions", client)
    
    async def _handle_tool_calls(self, result: dict, data: dict, headers: dict, url: str, client: Client) -> str:
        """Handle tool calls for Groq API"""
        message_result = result["choices"][0]["message"]
        
        # Check if LLM wants to call a tool
        if message_result.get("tool_calls"):
            tool_call = message_result["tool_calls"][0]
            function_name = tool_call["function"]["name"]
            arguments = json.loads(tool_call["function"]["arguments"])
            
            print(f"🔧 Calling tool: {function_name} with {arguments}")
            
            # Call the MCP tool
            tool_result = await client.call_tool(function_name, arguments)
            tool_content = str(tool_result)
            
            print(f"📊 Tool result: {tool_content}")
            
            # Send tool result back to LLM
            data["messages"].extend([
                message_result,
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": tool_content
                }
            ])
            
            # Remove tools from follow-up call
            del data["tools"]
            
            response = requests.post(url, headers=headers, json=data, timeout=30.0)
            response.raise_for_status()
            result = response.json()
        
        return result["choices"][0]["message"]["content"]
    
    async def _simple_weather_response(self, message: str, client: Client) -> str:
        """Simple pattern matching fallback when Groq API doesn't work"""
        import re
        
        # Extract city name from message
        weather_patterns = [
            r"weather in ([^?]+)",
            r"weather for ([^?]+)", 
            r"how's.*weather.*in ([^?]+)",
            r"what's.*weather.*in ([^?]+)",
            r"weather.*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"
        ]
        
        city = None
        message_lower = message.lower().strip()
        
        for pattern in weather_patterns:
            match = re.search(pattern, message_lower)
            if match:
                city = match.group(1).strip()
                break
        
        if not city:
            return "I can help you get weather information! Please ask like 'What's the weather in [city name]?'"
        
        # Call weather tool directly
        try:
            print(f"🔧 Calling tool: get_weather with {{'city': '{city}'}}")
            tool_result = await client.call_tool("get_weather", {"city": city})
            
            # Parse result if it's a string
            if isinstance(tool_result, str):
                try:
                    weather_data = json.loads(tool_result)
                except:
                    weather_data = {"raw": tool_result}
            else:
                weather_data = tool_result
            
            # Format nice response
            if "error" in weather_data:
                return f"Sorry, I couldn't get weather data for {city}: {weather_data['error']}"
            
            return f"""Here's the current weather for {weather_data.get('city', city)}:

🌡️ Temperature: {weather_data.get('temperature', 'N/A')}
🤔 Feels like: {weather_data.get('feels_like', 'N/A')}
☁️ Conditions: {weather_data.get('description', 'N/A')}
💧 Humidity: {weather_data.get('humidity', 'N/A')}
💨 Wind: {weather_data.get('wind_speed', 'N/A')} {weather_data.get('wind_direction', '')}
👁️ Visibility: {weather_data.get('visibility', 'N/A')}
☀️ UV Index: {weather_data.get('uv_index', 'N/A')}"""
            
        except Exception as e:
            return f"Sorry, I had trouble getting the weather for {city}: {str(e)}"

    async def chat_loop(self):
        """Main chat loop with FastMCP"""
        print("🌟 FastMCP Demo Chat - Ask about weather in any city!")
        print("💡 Try: 'What's the weather in London?' or 'How's the weather in Tokyo?'")
        print("🔗 Connecting to FastMCP server...")
        print("🚪 Type 'quit' to exit\n")
        
        try:
            # Connect to FastMCP server using streamable-http transport
            async with Client("http://localhost:8000/mcp") as client:
                print("✅ Connected to FastMCP server")
                
                # List available tools
                tools = await client.list_tools()
                tools_info = [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema
                    }
                    for tool in tools
                ]
                
                print(f"🔧 Available tools: {[tool['name'] for tool in tools_info]}")
                print()
                
                while True:
                    try:
                        user_input = input("👤 You: ").strip()
                        
                        if user_input.lower() in ['quit', 'exit', 'bye']:
                            print("👋 Goodbye!")
                            break
                        
                        if not user_input:
                            continue
                        
                        print("🤖 Assistant: ", end="", flush=True)
                        
                        # Get LLM response
                        response = await self.call_llm(user_input, tools_info, client)
                        print(response)
                        print()
                        
                    except KeyboardInterrupt:
                        print("\n👋 Goodbye!")
                        break
                    except Exception as e:
                        print(f"❌ Error: {str(e)}")
                        
        except Exception as e:
            print(f"❌ Failed to connect to FastMCP server: {str(e)}")
            print("💡 Make sure the server is running: python server.py")
            print("💡 Server should be at: http://localhost:8000")

async def main():
    print("🤖 LLM Options:")
    print("   1. Groq (free with signup): https://console.groq.com")
    print("   2. Pattern matching fallback (no LLM needed)")
    print()
    
    groq_key = os.getenv("GROQ_API_KEY")
    
    if not groq_key or groq_key == "your_groq_key_here":
        print("ℹ️  No Groq API key found - using pattern matching fallback")
        print("💡 For smarter responses, get a free key from: https://console.groq.com")
        print("   - Sign up (free)")
        print("   - Get API key")
        print("   - Add to .env: GROQ_API_KEY=your_key_here")
        print()
    else:
        print("✅ Groq API key found - using Llama-3 for smart responses")
        print()
    
    print("✅ Weather API: Using free wttr.in (no signup needed!)")
    print()
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:8000", timeout=5.0)
        if response.status_code == 200:
            print("✅ FastMCP server is running")
        else:
            print("⚠️  FastMCP server responded but may have issues")
    except Exception:
        print("❌ FastMCP server not running. Please start it first:")
        print("   python server.py")
        print()
        return
    
    client = MCPClient()
    await client.chat_loop()

if __name__ == "__main__":
    asyncio.run(main())