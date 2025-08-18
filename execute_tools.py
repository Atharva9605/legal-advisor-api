import json
from typing import List, Dict, Any
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage, HumanMessage
from langchain_tavily import TavilySearch
from dotenv import load_dotenv
load_dotenv()

# Configure TavilySearch with proper parameters based on documentation
tavily_tool = TavilySearch(
    max_results=5,
    topic="news",
    # Additional parameters for better search results
    search_depth="advanced",
    time_range="none"
)

def safe_json_serialize(obj):
    """Safely serialize objects to JSON, handling exceptions and non-serializable objects"""
    try:
        # Test if the object is JSON serializable
        json.dumps(obj)
        return obj
    except (TypeError, ValueError, AttributeError) as e:
        # If it's an exception object or non-serializable, convert to safe format
        if isinstance(obj, Exception):
            return {
                "error": True,
                "error_type": obj.__class__.__name__,
                "error_message": str(obj)
            }
        elif hasattr(obj, '__dict__'):
            try:
                # Try to convert object attributes to dictionary
                safe_dict = {}
                for key, value in obj.__dict__.items():
                    safe_dict[key] = safe_json_serialize(value)
                return safe_dict
            except:
                return {"error": True, "message": str(obj)}
        else:
            return {"error": True, "message": str(obj)}

# Function to execute search queries from AnswerQuestion tool calls
def execute_tools(state: List[BaseMessage]) -> List[BaseMessage]:
    last_ai_message: AIMessage = state[-1]
    
    # Extract tool calls from the AI message
    if not hasattr(last_ai_message, "tool_calls") or not last_ai_message.tool_calls:
        return []
    
    # Process the AnswerQuestion or ReviseAnswer tool calls to extract search queries
    tool_messages = []
    
    for tool_call in last_ai_message.tool_calls:
        if tool_call["name"] in ["AnswerQuestion", "ReviseAnswer"]:
            call_id = tool_call["id"]
            search_queries = tool_call["args"].get("search_queries", [])
            
            # Execute each search query using the tavily tool
            query_results = {}
            for query in search_queries:
                try:
                    print(f"Executing search query: {query}")  # Debug logging
                    result = tavily_tool.invoke(query)
                    
                    # Ensure result is JSON serializable
                    safe_result = safe_json_serialize(result)
                    query_results[query] = safe_result
                    
                except Exception as e:
                    print(f"Search failed for query '{query}': {str(e)}")  # Debug logging
                    query_results[query] = {
                        "error": True,
                        "error_type": e.__class__.__name__,
                        "error_message": str(e)
                    }
            
            try:
                # Safely serialize the entire query_results
                content = json.dumps(safe_json_serialize(query_results))
            except Exception as e:
                # Fallback if even safe serialization fails
                print(f"Failed to serialize query results: {str(e)}")
                content = json.dumps({
                    "error": True,
                    "message": "Failed to serialize search results",
                    "queries": list(search_queries)
                })
            
            # Create a tool message with the results
            tool_messages.append(
                ToolMessage(
                    content=content,
                    tool_call_id=call_id
                )
            )
    
    return tool_messages
