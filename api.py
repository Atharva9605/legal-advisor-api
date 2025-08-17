from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime
from langchain_core.messages import HumanMessage
from reflexion_graph import app as langraph_app  # Your LangGraph agent
import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Legal Advisor AI Agent API",
    description="AI-powered legal analysis with step-by-step thinking and link summaries",
    version="1.1.0" # Version updated
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models ---
class LegalCaseRequest(BaseModel):
    case_description: str
    user_id: Optional[str] = None

class LinkSummary(BaseModel):
    url: str
    title: str
    summary: str
    status: str

class ThinkingStep(BaseModel):
    step_number: int
    step_name: str
    description: str
    details: str
    timestamp: str

class LegalAnalysisResponse(BaseModel):
    case_name: str
    analysis_date: str
    thinking_steps: List[ThinkingStep]
    # This field will contain plain text or HTML, depending on the endpoint called
    analysis_content: str 
    references: List[str]
    link_summaries: List[LinkSummary]
    total_steps: int
    processing_time: float

# --- Helper Functions ---
async def get_link_summary(url: str) -> Optional[LinkSummary]:
    """Asynchronously fetches and summarizes a URL."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    title = soup.find('title').get_text(strip=True) if soup.find('title') else "No title found"
                    
                    # Try to get meta description first
                    meta_desc = soup.find('meta', attrs={'name': 'description'})
                    summary = meta_desc['content'] if meta_desc and meta_desc.get('content') else ""
                    
                    # If no meta description, fallback to the first long paragraph
                    if not summary:
                        paragraphs = soup.find_all('p')
                        for p in paragraphs:
                            text = p.get_text(strip=True)
                            if len(text) > 100: # Find a reasonably long paragraph
                                summary = text
                                break
                    
                    if not summary:
                        summary = "Content summary not available."

                    # Truncate summary to a reasonable length
                    summary_preview = (summary[:250] + '...') if len(summary) > 250 else summary

                    return LinkSummary(url=url, title=title, summary=summary_preview, status="success")
        return LinkSummary(url=url, title="Error", summary=f"Failed to fetch with status: {response.status}", status="error")
    except Exception as e:
        return LinkSummary(url=url, title="Error", summary=f"An exception occurred: {str(e)}", status="error")

def extract_thinking_steps(response_messages) -> List[ThinkingStep]:
    """Extracts the agent's thinking steps from the LangGraph response."""
    steps = []
    step_counter = 1
    for message in response_messages:
        if not hasattr(message, 'tool_calls') or not message.tool_calls:
            continue
        for tool_call in message.tool_calls:
            step_name = "Initial Analysis"
            description = "AI analyzes the case and provides initial legal assessment"
            if tool_call['name'] == 'ReviseAnswer':
                step_name = "Research & Revision"
                description = "AI revises the analysis based on critique and research"
            
            details = f"Action: {tool_call['name']}. Queries: {len(tool_call['args'].get('search_queries', []))}."
            steps.append(ThinkingStep(
                step_number=step_counter,
                step_name=step_name,
                description=description,
                details=details,
                timestamp=datetime.now().isoformat()
            ))
            step_counter += 1
    return steps

def extract_references(response) -> List[str]:
    """Extracts web links from the final tool call in the response."""
    references = []
    # The final answer and references are in the last message's tool call
    if response and hasattr(response[-1], 'tool_calls') and response[-1].tool_calls:
        # Assuming the last tool call contains the final answer and references
        final_tool_call = response[-1].tool_calls[0]
        if final_tool_call['name'] in ['AnswerQuestion', 'ReviseAnswer']:
            refs = final_tool_call['args'].get('references', [])
            if isinstance(refs, list):
                references.extend(ref for ref in refs if ref and isinstance(ref, str) and ref.startswith('http'))
    return list(set(references)) # Return unique references

async def _run_analysis(case_description: str) -> dict:
    """Core logic to run analysis, shared by endpoints."""
    start_time = datetime.now()
    
    # --- 1. Invoke the LangGraph Agent (now returns HTML) ---
    # Using ainvoke for non-blocking IO
    response = await langraph_app.ainvoke([HumanMessage(content=case_description)])
    
    # --- 2. Extract Data from Response ---
    thinking_steps = extract_thinking_steps(response)
    references = extract_references(response)
    
    final_answer = ""
    if response and hasattr(response[-1], 'tool_calls') and response[-1].tool_calls:
        final_answer = response[-1].tool_calls[0]["args"].get("answer", "No answer found.")
        
    # --- 3. Asynchronously Summarize Links ---
    tasks = [get_link_summary(ref) for ref in references]
    summaries = await asyncio.gather(*tasks)
    link_summaries = [s for s in summaries if s] # Filter out potential Nones
    
    # Keep only references that were successfully summarized
    successful_references = [s.url for s in link_summaries if s.status == "success"]
    
    processing_time = (datetime.now() - start_time).total_seconds()
    
    return {
        "case_name": f"Case Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "analysis_date": datetime.now().isoformat(),
        "thinking_steps": thinking_steps,
        "analysis_content": final_answer, # This content is now HTML
        "references": successful_references,
        "link_summaries": link_summaries,
        "total_steps": len(thinking_steps),
        "processing_time": processing_time
    }

# --- API Endpoints ---
@app.post("/analyze-case", response_model=LegalAnalysisResponse)
async def analyze_legal_case(request: LegalCaseRequest):
    """
    Analyzes a legal case and returns the analysis as formatted HTML content.
    """
    try:
        result = await _run_analysis(request.case_description)
        return LegalAnalysisResponse(**result)
    except Exception as e:
        # Log the full error for debugging
        print(f"An error occurred during analysis: {e}") 
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/")
async def home():
    """Home endpoint providing API information."""
    return {
        "message": "Welcome to the Legal Advisor AI Agent API",
        "documentation": "/docs"
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
