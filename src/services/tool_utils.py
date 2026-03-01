import inspect
from typing import get_type_hints, Callable, List, Dict, Any

def get_json_schema(func: Callable) -> Dict[str, Any]:
    """
    Generates a JSON schema for a given Python function for use with Groq/OpenAI tools.
    """
    type_hints = get_type_hints(func)
    signature = inspect.signature(func)
    docstring = func.__doc__
    
    # Parse docstring for description
    description = ""
    if docstring:
        description = docstring.split("\n")[0].strip() # Take the first line as description

    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }

    for name, param in signature.parameters.items():
        if name == "self":
            continue
            
        param_type = type_hints.get(name, str) # Default to str if not typed
        json_type = "string"
        if param_type == int:
            json_type = "integer"
        elif param_type == float:
            json_type = "number"
        elif param_type == bool:
            json_type = "boolean"
        elif param_type == list:
            json_type = "array"
        elif param_type == dict:
            json_type = "object"
            
        param_desc = ""
        # Basic docstring parsing to find arg descriptions (simple regex-like search)
        # This is a basic implementation.
        if docstring:
            lines = docstring.split("\n")
            for line in lines:
                if f"{name}:" in line or f"{name} (" in line:
                    param_desc = line.split(":", 1)[-1].strip()
                    break

        parameters["properties"][name] = {
            "type": json_type,
            "description": param_desc
        }
        
        if param.default == inspect.Parameter.empty:
            parameters["required"].append(name)

    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": description,
            "parameters": parameters
        }
    }

def get_tool_definitions(tools: List[Callable]) -> List[Dict[str, Any]]:
    return [get_json_schema(tool) for tool in tools]
