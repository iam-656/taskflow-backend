import os
import json
import traceback
import re
from typing import List, Dict, Any
from groq import Groq
from .tools import tools_list, create_task_tool, list_tasks_tool
from .tool_utils import get_tool_definitions

# Configure API Key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Map function names to actual functions for execution
AVAILABLE_TOOLS = {
    "create_task_tool": create_task_tool,
    "list_tasks_tool": list_tasks_tool
}

def get_client():
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not configured.")
    return Groq(api_key=GROQ_API_KEY)

async def chat_with_gemini(message: str, history: List[Dict[str, str]] = [], context_id: str = "default"):
    """
    Chat with Groq using explicit Tool Emulation to avoid 400 API errors with 8B model.
    """
    if not GROQ_API_KEY:
        print("Error: GROQ_API_KEY is missing.")
        return "Groq API Key not configured. Please set GROQ_API_KEY in .env."

    try:
        client = get_client()
        
        # Parse context to find active workspace
        current_workspace_id = ""
        if context_id and context_id.startswith("workspace-"):
            current_workspace_id = context_id.replace("workspace-", "")

        # 1. Prepare Messages
        groq_messages = []
        
        # SYSTEM PROMPT: Explicitly instruct for JSON output, bypassing native tool definitions
        system_prompt = f"""You are TaskFlow AI, a helpful task management assistant.
You have access to these tools:
1. create_task_tool(title: str, description: str = "", priority: str = "medium", due_date: str = "", workspace_id: str = "")
2. list_tasks_tool(status: str = "")

To use a tool, you MUST strictly output a JSON object in this EXACT format and nothing else:
>>> {{\"tool\": \"create_task_tool\", \"args\": {{\"title\": \"Task Name\", \"priority\": \"medium\"}}}}

Context:
The user is currently viewing the list/context: "{context_id}".
"""

        if current_workspace_id:
            system_prompt += f"""
IMPORTANT: The user is in a specific Workspace (List) with ID: "{current_workspace_id}".
Unless the user explicitly says otherwise, you MUST pass "workspace_id": "{current_workspace_id}" when creating a task.
"""

        system_prompt += """
Example:
User: Create a task to buy milk
Assistant: >>> {"tool": "create_task_tool", "args": {"title": "Buy milk", "workspace_id": "..."}}

If no tool is needed, just reply normally.
"""
        groq_messages.append({"role": "system", "content": system_prompt})

        for msg in history:
            role = "user" if msg["role"] == "user" else "assistant"
            groq_messages.append({"role": role, "content": msg["content"]})
        
        groq_messages.append({"role": "user", "content": message})

        # 2. Call LLM (WITHOUT tools parameter to avoid API validation errors)
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=groq_messages,
            max_tokens=4096,
            temperature=0.1 # Lower temperature for more deterministic JSON
        )

        response_text = response.choices[0].message.content
        
        # 3. Manual Tool Detection
        # Check for the >>> JSON pattern
        match = re.search(r'>>>\s*({.*})', response_text, re.DOTALL)
        
        if match:
            json_str = match.group(1)
            try:
                tool_call = json.loads(json_str)
                function_name = tool_call.get("tool")
                function_args = tool_call.get("args", {})
                
                print(f"Executing emulated tool: {function_name} with args: {function_args}")
                
                function_to_call = AVAILABLE_TOOLS.get(function_name)
                if function_to_call:
                    try:
                        tool_result = function_to_call(**function_args)
                        # 4. Return result to model for final response (or just return result)
                        # Ideally, we feed the result back to generate a natural response.
                        
                        # Add the tool execution context to history
                        groq_messages.append({"role": "assistant", "content": response_text})
                        groq_messages.append({"role": "user", "content": f"Tool Output: {str(tool_result)}"})
                        
                        final_response = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=groq_messages
                        )
                        return final_response.choices[0].message.content
                        
                    except Exception as e:
                        return f"Error executing tool: {str(e)}"
                else:
                    return f"Error: Tool {function_name} not found."
            
            except json.JSONDecodeError:
                return f"Error parsing tool command: {response_text}"
        else:
            # Normal response
            return response_text

    except Exception as e:
        print(f"Groq API Error: {str(e)}")
        traceback.print_exc()
        return f"I'm sorry, I encountered an error interacting with the AI: {str(e)}"
