from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import json
import re
from datetime import datetime
from langchain_core.messages import HumanMessage
from reflexion_graph import app as langraph_app
from langchain_google_genai import ChatGoogleGenerativeAI
import requests
from bs4 import BeautifulSoup
import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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

class UnifiedAnalysisResponse(BaseModel):
    case_name: str
    analysis_date: str
    thinking_steps: List[ThinkingStep]
    final_answer: str
    formatted_analysis: str
    references: List[str]
    link_summaries: List[LinkSummary]
    total_steps: int
    processing_time: float

# Web scraping function
async def get_link_summary(url: str) -> Optional[LinkSummary]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    title = soup.find('title').get_text().strip() if soup.find('title') else "No title found"
                    meta_desc = soup.find('meta', attrs={'name': 'description'})
                    summary = meta_desc['content'][:200] + "..." if meta_desc and meta_desc.get('content') and len(meta_desc['content']) > 200 else (meta_desc['content'] if meta_desc else "")
                    if not summary:
                        paragraphs = soup.find_all('p')
                        for p in paragraphs:
                            text = p.get_text().strip()
                            if len(text) > 50:
                                summary = text[:200] + "..." if len(text) > 200 else text
                                break
                        if not summary:
                            summary = "Content summary not available"
                    return LinkSummary(url=url, title=title, summary=summary, status="success")
                return None
    except Exception:
        return None

# Extract thinking steps
def extract_thinking_steps(response_messages) -> List[ThinkingStep]:
    steps = []
    step_counter = 1
    for i, message in enumerate(response_messages):
        if hasattr(message, 'tool_calls') and message.tool_calls:
            for tool_call in message.tool_calls:
                if tool_call['name'] == 'AnswerQuestion':
                    steps.append(ThinkingStep(
                        step_number=step_counter,
                        step_name="Initial Analysis",
                        description="AI analyzes the case and provides initial legal assessment",
                        details=f"Generated initial answer with {len(tool_call['args'].get('search_queries', []))} search queries",
                        timestamp=datetime.now().isoformat()
                    ))
                    step_counter += 1
                elif tool_call['name'] == 'ReviseAnswer':
                    steps.append(ThinkingStep(
                        step_number=step_counter,
                        step_name="Research & Revision",
                        description="AI revises the analysis based on critique",
                        details=f"Revised with {len(tool_call['args'].get('search_queries', []))} new queries",
                        timestamp=datetime.now().isoformat()
                    ))
                    step_counter += 1
    return steps

# Extract references
def extract_references(response) -> List[str]:
    references = []
    if response and hasattr(response[-1], 'tool_calls') and response[-1].tool_calls:
        for tool_call in response[-1].tool_calls:
            if tool_call['name'] == 'ReviseAnswer':
                references.extend(tool_call['args'].get('references', []))
    return [ref for ref in references if ref.startswith(('http://', 'https://'))]

# Generate HTML with gemini-2.0-flash
def generate_html_from_analysis(analysis_text: str) -> str:
    """Convert plain text analysis to HTML using gemini-2.0-flash."""
    gemini_llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", max_retries=2)
    prompt = f"""
    Convert the following legal analysis text into a well-formatted HTML document suitable for a professional legal report. Use appropriate HTML tags:
    - Use <h1> for the case name, <h2> for section headers, <p> for paragraphs.
    - Use <strong> for bold text (replace **text** with <strong>text</strong>).
    - Use <ul><li> for bullet points (replace - with <li> and group with <ul>).
    - Ensure proper nesting and structure.
    - Do not include external CSS or JavaScript; return pure HTML.

    Text:
    {analysis_text}
    """
    response = gemini_llm.invoke([HumanMessage(content=prompt)])
    html_content = response.content.strip()
    if html_content.startswith('<') and html_content.endswith('>'):
        return html_content
    return f"<div>{html_content}</div>"  # Fallback wrapper if Gemini returns plain text

# Unified analysis endpoint
@app.post("/analyze-case")
@app.get("/analyze-case")
async def analyze_legal_case(request: LegalCaseRequest = None, case_description: str = "Test case for API verification"):
    start_time = datetime.now()
    try:
        # Determine case description based on request type
        if request:
            desc = request.case_description
        else:
            desc = case_description

        # Invoke the Langraph agent
        response = langraph_app.invoke([HumanMessage(content=desc)])
        
        # Extract thinking steps and references
        thinking_steps = extract_thinking_steps(response)
        references = extract_references(response)
        
        # Get final answer from the last message
        final_answer = ""
        if response and hasattr(response[-1], 'tool_calls') and response[-1].tool_calls:
            final_answer = response[-1].tool_calls[0]["args"].get("answer", "")
        
        # Generate HTML-formatted analysis
        formatted_analysis = generate_html_from_analysis(final_answer)
        
        # Generate link summaries for successful references
        link_summaries = []
        successful_references = []
        tasks = [get_link_summary(ref) for ref in references if ref.startswith(('http://', 'https://'))]
        summaries = await asyncio.gather(*tasks)
        for summary in summaries:
            if summary:
                link_summaries.append(summary)
                successful_references.append(summary.url)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return UnifiedAnalysisResponse(
            case_name=f"Case Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            analysis_date=datetime.now().isoformat(),
            thinking_steps=thinking_steps,
            final_answer=final_answer,
            formatted_analysis=formatted_analysis,
            references=successful_references,
            link_summaries=link_summaries,
            total_steps=len(thinking_steps),
            processing_time=processing_time
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

# Other endpoints
@app.get("/test")
async def test_endpoint():
    return {
        "message": "API is working!",
        "endpoints": {
            "POST /analyze-case": "Submit legal case for analysis (returns both raw and formatted analysis)",
            "GET /analyze-case": "Test endpoint with query parameter",
            "GET /api/health": "Health check",
            "GET /docs": "API documentation"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/")
async def home(request: Request):
    return {
        "message": "Legal Advisor AI Agent API",
        "description": "AI-powered legal analysis with step-by-step thinking and link summaries",
        "endpoints": {
            "POST /analyze-case": "Submit legal case for analysis (returns both raw and formatted analysis)",
            "GET /analyze-case": "Test endpoint with query parameter",
            "GET /api/health": "Health check",
            "GET /docs": "API documentation"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/debug")
async def debug():
    return {"message": "API is running", "endpoints": [route.path for route in app.routes]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
