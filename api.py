from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import json
import re
from datetime import datetime

# Import existing agent components
from reflexion_graph import app as langraph_app
from langchain_core.messages import HumanMessage
import requests
from bs4 import BeautifulSoup
import aiohttp

# Initialize FastAPI app
app = FastAPI(
    title="Legal Advisor AI Agent API",
    description="AI-powered legal analysis with step-by-step thinking and link summaries",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
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
    final_answer: str
    references: List[str]
    link_summaries: List[LinkSummary]
    total_steps: int
    processing_time: float

# Web scraping function for link summaries
async def get_link_summary(url: str) -> LinkSummary:
    """Extract title and summary from a webpage for tooltip display"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extract title
                    title = soup.find('title')
                    title_text = title.get_text().strip() if title else "No title found"
                    
                    # Extract meta description or first paragraph
                    meta_desc = soup.find('meta', attrs={'name': 'description'})
                    if meta_desc and meta_desc.get('content'):
                        summary = meta_desc['content'][:200] + "..." if len(meta_desc['content']) > 200 else meta_desc['content']
                    else:
                        # Try to get first meaningful paragraph
                        paragraphs = soup.find_all('p')
                        summary = ""
                        for p in paragraphs:
                            text = p.get_text().strip()
                            if len(text) > 50:  # Skip very short paragraphs
                                summary = text[:200] + "..." if len(text) > 200 else text
                                break
                        
                        if not summary:
                            summary = "Content summary not available"
                    
                    return LinkSummary(
                        url=url,
                        title=title_text,
                        summary=summary,
                        status="success"
                    )
                else:
                    return LinkSummary(
                        url=url,
                        title="Error",
                        summary=f"Failed to load page (Status: {response.status})",
                        status="error"
                    )
    except Exception as e:
        return LinkSummary(
            url=url,
            title="Error",
            summary=f"Failed to load page: {str(e)}",
            status="error"
        )

def extract_thinking_steps(response_messages) -> List[ThinkingStep]:
    """Extract thinking steps from the Langraph response"""
    steps = []
    step_counter = 1
    
    for i, message in enumerate(response_messages):
        if hasattr(message, 'tool_calls') and message.tool_calls:
            for tool_call in message.tool_calls:
                if tool_call['name'] == 'AnswerQuestion':
                    # First responder step
                    steps.append(ThinkingStep(
                        step_number=step_counter,
                        step_name="Initial Analysis",
                        description="AI analyzes the case and provides initial legal assessment",
                        details=f"Generated initial answer with {len(tool_call['args'].get('search_queries', []))} search queries",
                        timestamp=datetime.now().isoformat()
                    ))
                    step_counter += 1
                    
                elif tool_call['name'] == 'ReviseAnswer':
                    # Revision step
                    steps.append(ThinkingStep(
                        step_number=step_counter,
                        step_name="Research & Revision",
                        description="AI researches additional information and revises the answer",
                        details=f"Revised answer with {len(tool_call['args'].get('references', []))} references",
                        timestamp=datetime.now().isoformat()
                    ))
                    step_counter += 1
    
    return steps

def extract_references(response_messages) -> List[str]:
    """Extract reference links from the response"""
    references = []
    
    for message in response_messages:
        if hasattr(message, 'tool_calls') and message.tool_calls:
            for tool_call in message.tool_calls:
                if tool_call['name'] == 'ReviseAnswer':
                    refs = tool_call['args'].get('references', [])
                    references.extend(refs)
    
    # Also look for URLs in the content
    for message in response_messages:
        if hasattr(message, 'content') and message.content:
            # Simple URL extraction regex
            urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', message.content)
            references.extend(urls)
    
    return list(set(references))  # Remove duplicates

@app.post("/analyze-case", response_model=LegalAnalysisResponse)
async def analyze_legal_case(request: LegalCaseRequest):
    """Analyze a legal case using the AI agent"""
    start_time = datetime.now()
    
    try:
        # Invoke the Langraph agent
        response = langraph_app.invoke(request.case_description)
        
        # Extract thinking steps
        thinking_steps = extract_thinking_steps(response)
        
        # Extract references
        references = extract_references(response)
        
        # Get final answer from the last message
        final_answer = ""
        if response and hasattr(response[-1], 'tool_calls') and response[-1].tool_calls:
            final_answer = response[-1].tool_calls[0]["args"].get("answer", "")
        
        # Generate link summaries for tooltips
        link_summaries = []
        for ref in references:
            if ref.startswith(('http://', 'https://')):
                summary = await get_link_summary(ref)
                link_summaries.append(summary)
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return LegalAnalysisResponse(
            case_name=f"Case Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            analysis_date=datetime.now().isoformat(),
            thinking_steps=thinking_steps,
            final_answer=final_answer,
            references=references,
            link_summaries=link_summaries,
            total_steps=len(thinking_steps),
            processing_time=processing_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/analyze-case")
async def analyze_legal_case_get(case_description: str = "Test case for API verification"):
    """GET endpoint for testing the analyze-case functionality"""
    try:
        # Create a request object for the POST endpoint
        request = LegalCaseRequest(case_description=case_description)
        
        # Call the POST endpoint logic
        start_time = datetime.now()
        
        # Invoke the Langraph agent
        response = langraph_app.invoke(request.case_description)
        
        # Extract thinking steps
        thinking_steps = extract_thinking_steps(response)
        
        # Extract references
        references = extract_references(response)
        
        # Get final answer from the last message
        final_answer = ""
        if response and hasattr(response[-1], 'tool_calls') and response[-1].tool_calls:
            final_answer = response[-1].tool_calls[0]["args"].get("answer", "")
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "message": "GET endpoint working - use POST for full functionality",
            "case_description": case_description,
            "final_answer_preview": final_answer[:200] + "..." if len(final_answer) > 200 else final_answer,
            "processing_time": processing_time,
            "note": "This is a test endpoint. Use POST /analyze-case with JSON body for full analysis."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/test")
async def test_endpoint():
    """Simple test endpoint to verify API is working"""
    return {
        "message": "API is working!",
        "endpoints": {
            "POST /analyze-case": "Submit legal case for analysis",
            "GET /analyze-case": "Test endpoint with query parameter",
            "GET /api/health": "Health check",
            "GET /docs": "API documentation"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/")
async def home(request: Request):
    """Serve the main API information"""
    return {
        "message": "Legal Advisor AI Agent API",
        "description": "AI-powered legal analysis with step-by-step thinking and link summaries",
        "endpoints": {
            "POST /analyze-case": "Submit legal case for analysis",
            "GET /analyze-case": "Test endpoint with query parameter",
            "GET /api/health": "Health check",
            "GET /docs": "API documentation"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
