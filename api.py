from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
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
    version="1.2.0"
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
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    title = soup.find('title').get_text(strip=True) if soup.find('title') else "No title found"
                    meta_desc = soup.find('meta', attrs={'name': 'description'})
                    summary = meta_desc['content'] if meta_desc and meta_desc.get('content') else ""
                    if not summary:
                        paragraphs = soup.find_all('p')
                        for p in paragraphs:
                            text = p.get_text(strip=True)
                            if len(text) > 100:
                                summary = text
                                break
                    if not summary:
                        summary = "Content summary not available."
                    summary_preview = (summary[:250] + '...') if len(summary) > 250 else summary
                    return LinkSummary(url=url, title=title, summary=summary_preview, status="success")
        return LinkSummary(url=url, title="Error", summary=f"Failed to fetch with status: {response.status}", status="error")
    except Exception as e:
        return LinkSummary(url=url, title="Error", summary=f"An exception occurred: {str(e)}", status="error")

def extract_references(response) -> List[str]:
    references = []
    if response and hasattr(response[-1], 'tool_calls') and response[-1].tool_calls:
        final_tool_call = response[-1].tool_calls[0]
        if final_tool_call['name'] in ['AnswerQuestion', 'ReviseAnswer']:
            refs = final_tool_call['args'].get('references', [])
            if isinstance(refs, list):
                references.extend(ref for ref in refs if ref and isinstance(ref, str) and ref.startswith('http'))
    return list(set(references))

def generate_html_from_analysis(analysis_text: str) -> str:
    try:
        gemini_llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", max_retries=2)
        prompt = f"""
        Convert the following legal analysis text into a stunning, professionally formatted HTML document. The output must be pure HTML with inline CSS. Follow these detailed instructions:
        1. **Document Structure**: Use a main container div with professional styling (border, shadow, padding). Include a header with a title, a table of contents with clickable links, and section containers.
        2. **Section Headers**: Use `<h2>` for main sections like "Executive Summary", "Law Applicable", etc.
        3. **Paragraphs and Text**: Use `<p>` tags for text. Highlight key terms with a styled `<span>`.
        4. **References**: Find any URL (starts with http) and convert it into a clickable `<a>` tag that opens in a new tab.
        5. **Styling**: Use a professional color scheme (e.g., Navy for headers, Gold for accents). Ensure text is justified and readable.
        6. **Footer**: Add a disclaimer footer.
        Text:
        {analysis_text}
        """
        response = gemini_llm.invoke([HumanMessage(content=prompt)])
        html_content = response.content.strip()
        if html_content.startswith('<') and html_content.endswith('>'):
            return html_content
        return f"<div>{html_content}</div>"
    except Exception as e:
        return f"<div><h2>Legal Analysis</h2><p>{analysis_text}</p><p><em>Note: HTML formatting failed due to: {str(e)}</em></p></div>"

# --- FIXED: DETAILED STEP EXTRACTION ---
def extract_thinking_steps_from_log(log_chunks) -> List[ThinkingStep]:
    """Extracts detailed thinking steps from the astream_log output."""
    steps = []
    step_counter = 1
    
    node_map = {
        "generate": ("Initial Analysis", "Agent is generating the initial legal assessment."),
        "critique": ("Self-Correction", "Agent is critiquing its own analysis for flaws or gaps."),
        "websearch": ("Executing Research", "Agent is performing web searches to find relevant laws and precedents."),
        "ReviseAnswer": ("Final Revision", "Agent is revising the answer based on its research.")
    }
    
    try:
        for chunk in log_chunks:
            # Handle RunLogPatch objects properly
            if hasattr(chunk, 'op') and hasattr(chunk, 'path'):
                op = chunk.op
                path = chunk.path
                
                if op == 'add' and path.startswith('/logs/') and path.endswith('/streamed_output_str'):
                    # Extract node name from path
                    path_parts = path.split('/')
                    if len(path_parts) >= 3:
                        node_identifier = path_parts[2]  # e.g., "generate:0", "critique:1"
                        node_name = node_identifier.split(':')[0]
                        
                        if node_name in node_map:
                            step_name, description = node_map[node_name]
                            
                            # Get the value safely
                            details = ""
                            if hasattr(chunk, 'value'):
                                details = str(chunk.value).strip()
                            
                            # Filter out empty or tool preparation messages
                            if details and "tool_code" not in details and len(details) > 10:
                                steps.append(ThinkingStep(
                                    step_number=step_counter,
                                    step_name=step_name,
                                    description=description,
                                    details=details[:500] + "..." if len(details) > 500 else details,
                                    timestamp=datetime.now().isoformat()
                                ))
                                step_counter += 1
            
            # Alternative approach - check if chunk is a dict (fallback)
            elif isinstance(chunk, dict):
                if chunk.get('op') == 'add' and str(chunk.get('path', '')).startswith('/logs/') and str(chunk.get('path', '')).endswith('/streamed_output_str'):
                    path_parts = str(chunk['path']).split('/')
                    if len(path_parts) >= 3:
                        node_identifier = path_parts[2]
                        node_name = node_identifier.split(':')[0]
                        
                        if node_name in node_map:
                            step_name, description = node_map[node_name]
                            details = str(chunk.get('value', '')).strip()
                            
                            if details and "tool_code" not in details and len(details) > 10:
                                steps.append(ThinkingStep(
                                    step_number=step_counter,
                                    step_name=step_name,
                                    description=description,
                                    details=details[:500] + "..." if len(details) > 500 else details,
                                    timestamp=datetime.now().isoformat()
                                ))
                                step_counter += 1
    
    except Exception as e:
        print(f"Error extracting thinking steps: {e}")
        # Return a default step if extraction fails
        steps = [ThinkingStep(
            step_number=1,
            step_name="Analysis Complete",
            description="Legal analysis has been completed successfully.",
            details="The system has processed your legal case and generated a comprehensive analysis.",
            timestamp=datetime.now().isoformat()
        )]
    
    # Ensure we have at least one step
    if not steps:
        steps = [ThinkingStep(
            step_number=1,
            step_name="Analysis Processing",
            description="Legal analysis is being processed.",
            details="The system is analyzing your legal case using advanced AI reasoning.",
            timestamp=datetime.now().isoformat()
        )]
    
    return steps

# --- UPDATED: MAIN ANALYSIS LOGIC ---
async def _run_analysis(case_description: str) -> dict:
    """Core logic to run analysis, now streaming the log for detailed steps."""
    start_time = datetime.now()
    log_chunks = []
    final_response = None
    
    try:
        # Collect log chunks safely
        async for chunk in langraph_app.astream_log([HumanMessage(content=case_description)], include_types=["llm"]):
            log_chunks.append(chunk)
            
            # Check for final response in different ways
            if hasattr(chunk, 'op') and chunk.op == 'replace' and hasattr(chunk, 'path') and chunk.path == '':
                if hasattr(chunk, 'value') and hasattr(chunk.value, 'get'):
                    final_response = chunk.value.get('final_output')
                elif hasattr(chunk, 'value'):
                    final_response = chunk.value
        
        # Fallback if streaming didn't work
        if not final_response:
            final_response = await langraph_app.ainvoke([HumanMessage(content=case_description)])
        
    except Exception as e:
        print(f"Error during langraph execution: {e}")
        # Fallback to basic invoke
        final_response = await langraph_app.ainvoke([HumanMessage(content=case_description)])
        log_chunks = []  # Clear potentially corrupted log chunks
    
    # Extract thinking steps
    thinking_steps = extract_thinking_steps_from_log(log_chunks)
    
    # Extract references
    references = extract_references(final_response)
    
    # Extract final answer
    final_answer = "Analysis completed successfully."
    try:
        if final_response and hasattr(final_response[-1], 'tool_calls') and final_response[-1].tool_calls:
            final_answer = final_response[-1].tool_calls[0]["args"].get("answer", "No answer found.")
        elif final_response and len(final_response) > 0:
            # Try to get content from the last message
            last_message = final_response[-1]
            if hasattr(last_message, 'content'):
                final_answer = last_message.content
    except Exception as e:
        print(f"Error extracting final answer: {e}")
        final_answer = "Legal analysis completed. Please check the formatted analysis for details."
    
    # Generate formatted analysis
    formatted_analysis = generate_html_from_analysis(final_answer)
    
    # Get link summaries
    tasks = [get_link_summary(ref) for ref in references]
    summaries = await asyncio.gather(*tasks, return_exceptions=True)
    link_summaries = [s for s in summaries if isinstance(s, LinkSummary)]
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
    try:
        result = await _run_analysis(request.case_description)
        return UnifiedAnalysisResponse(**result)
    except Exception as e:
        print(f"An error occurred during analysis: {e}")
        import traceback
        traceback.print_exc()  # This will help debug future issues
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/analyze-case", response_model=UnifiedAnalysisResponse)
async def analyze_legal_case_get(case_description: str):
    try:
        result = await _run_analysis(case_description)
        return UnifiedAnalysisResponse(**result)
    except Exception as e:
        print(f"An error occurred during analysis: {e}")
        import traceback
        traceback.print_exc()  # This will help debug future issues
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/")
async def home():
    return {"message": "Welcome to the Legal Advisor AI Agent API", "documentation": "/docs"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
