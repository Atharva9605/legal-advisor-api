import json
from typing import List, Dict, Any
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage, HumanMessage
from langchain_tavily import TavilySearch
from dotenv import load_dotenv

load_dotenv()

# Configure TavilySearch with proper parameters based on documentation
tavily_tool = TavilySearch(
    max_results=5,
    topic="general",
    # Additional parameters for better search results
    search_depth="advanced",
    time_range="week"
)

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
                    result = tavily_tool.invoke(query)
                    query_results[query] = result
                except Exception as e:
                    query_results[query] = {"error": f"Search failed: {str(e)}"}
            
            # Create a tool message with the results
            tool_messages.append(
                ToolMessage(
                    content=json.dumps(query_results),
                    tool_call_id=call_id
                )
            )
    
    return tool_messages