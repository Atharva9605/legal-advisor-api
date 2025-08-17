from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime
from langchain_core.messages import HumanMessage
from reflexion_graph import app as langraph_app
from langchain_google_genai import ChatGoogleGenerativeAI
import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Legal Advisor AI Agent API",
    description="AI-powered legal analysis with step-by-step thinking and link summaries",
    version="1.1.0"
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

def generate_html_from_analysis(analysis_text: str) -> str:
    """Convert legal analysis text into a beautifully formatted HTML document."""
    gemini_llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", max_retries=2)
    prompt = f"""
    Convert the following legal analysis text into a stunning, professionally formatted HTML document designed for a legal report. The output must be pure HTML with inline CSS for styling, ensuring no external files (CSS/JavaScript) are required. Follow these detailed instructions:

    1. **Document Structure**:
        - Wrap the entire content in a `<div class="report-container">` with inline styles: `max-width: 900px; margin: 0 auto; padding: 25px; background-color: #ffffff; border: 3px solid #003087; border-radius: 12px; box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15); font-family: 'Times New Roman', serif;`.
        - Include a **legal document header** with a title, date, and horizontal rule.
        - Add a **table of contents** `<div class="toc">` with `<a>` links to each section.

    2. **Section Headers**:
        - Use `<h2 class="section-header">` for section titles (e.g., "1. Executive Summary", "2. Law Applicable") with appropriate styles and an anchor tag for the TOC link.

    3. **Paragraphs and Text**:
        - Use `<p class="paragraph">` for text with justified alignment and good line-height.
        - Highlight key terms with a styled `<span class="key-term">`.
        - Use `<strong>` for emphasis.

    4. **Lists and Tables**:
        - Style `<ul>` and `<li>` for legal points.
        - Format data into a clean `<table class="evidence-table">`.

    5. **Footnotes and References**:
        - **In the references section, find any text that is a URL (starts with http:// or https://) and convert it into a clickable link. For example, transform the text `https://www.example.com/doc.pdf` into `<a href="https://www.example.com/doc.pdf" target="_blank">https://www.example.com/doc.pdf</a>`. Use `target="_blank"` to open the link in a new tab.**

    6. **Footer**:
        - Add a footer `<div class="report-footer">` with a standard disclaimer.

    7. **Styling**:
        - Use a professional color scheme: Navy (#003087) for headers, Gold (#d4af37) for accents, and grays for text.

    Text:
    {analysis_text}
    """
    response = gemini_llm.invoke([HumanMessage(content=prompt)])
    html_content = response.content.strip()
    if html_content.startswith('<') and html_content.endswith('>'):
        return html_content
    return f"<div>{html_content}</div>"  # Fallback wrapper

# --- Main Analysis Logic ---
async def _run_analysis(case_description: str) -> dict:
    """Core logic to run analysis, shared by endpoints."""
    start_time = datetime.now()
    
    # --- 1. Invoke the LangGraph Agent ---
    response = await langraph_app.ainvoke([HumanMessage(content=case_description)])
    
    # --- 2. Extract Data from Response ---
    thinking_steps = extract_thinking_steps(response)
    references = extract_references(response)
    
    final_answer = ""
    if response and hasattr(response[-1], 'tool_calls') and response[-1].tool_calls:
        final_answer = response[-1].tool_calls[0]["args"].get("answer", "No answer found.")
        
    # --- 3. Generate Formatted HTML ---
    formatted_analysis = generate_html_from_analysis(final_answer)
        
    # --- 4. Asynchronously Summarize Links ---
    tasks = [get_link_summary(ref) for ref in references]
    summaries = await asyncio.gather(*tasks)
    link_summaries = [s for s in summaries if s]
    
    successful_references = [s.url for s in link_summaries if s.status == "success"]
    
    processing_time = (datetime.now() - start_time).total_seconds()
    
    return {
        "case_name": f"Case Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "analysis_date": datetime.now().isoformat(),
        "thinking_steps": thinking_steps,
        "final_answer": final_answer,
        "formatted_analysis": formatted_analysis,
        "references": successful_references,
        "link_summaries": link_summaries,
        "total_steps": len(thinking_steps),
        "processing_time": processing_time
    }

# --- API Endpoints ---
@app.post("/analyze-case", response_model=UnifiedAnalysisResponse)
async def analyze_legal_case_post(request: LegalCaseRequest):
    """
    Analyzes a legal case from a POST request and returns a unified response.
    """
    try:
        result = await _run_analysis(request.case_description)
        return UnifiedAnalysisResponse(**result)
    except Exception as e:
        print(f"An error occurred during analysis: {e}") 
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/analyze-case", response_model=UnifiedAnalysisResponse)
async def analyze_legal_case_get(case_description: str):
    """
    Analyzes a legal case from a GET request query parameter.
    """
    try:
        result = await _run_analysis(case_description)
        return UnifiedAnalysisResponse(**result)
    except Exception as e:
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
