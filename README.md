# Legal Advisor AI Agent API

A FastAPI-based API that converts your Langraph-based AI Legal Agent into a web service with step-by-step thinking visualization and link summaries.

## Features

- **AI Legal Analysis**: Integrates with your existing Langraph agent
- **Step-by-Step Thinking**: Shows the AI's reasoning process
- **Clickable References**: All links in responses are clickable
- **Link Summaries**: Hover tooltips show webpage content summaries
- **Real-time Processing**: Async processing with progress tracking

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables**:
   Create a `.env` file with:
   ```
   GOOGLE_API_KEY=your_google_api_key
   TAVILY_API_KEY=your_tavily_api_key
   ```

3. **Run the API**:
   ```bash
   python api.py
   ```

4. **Access the API**:
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - Health Check: http://localhost:8000/api/health

## API Endpoints

### POST /analyze-case
Analyzes a legal case using the AI agent.

**Request Body**:
```json
{
  "case_description": "Your legal case description here...",
  "user_id": "optional_user_id"
}
```

**Response**:
```json
{
  "case_name": "Case Analysis - 2025-08-17 11:40",
  "analysis_date": "2025-08-17T11:40:00.000Z",
  "thinking_steps": [
    {
      "step_number": 1,
      "step_name": "Initial Analysis",
      "description": "AI analyzes the case and provides initial legal assessment",
      "details": "Generated initial answer with 3 search queries",
      "timestamp": "2025-08-17T11:40:00.000Z"
    }
  ],
  "final_answer": "The AI's final legal analysis...",
  "references": ["https://example.com", "https://legal.org"],
  "link_summaries": [
    {
      "url": "https://example.com",
      "title": "Example Legal Resource",
      "summary": "This webpage contains information about...",
      "status": "success"
    }
  ],
  "total_steps": 2,
  "processing_time": 15.5
}
```

## Frontend Integration

The API is designed to work with frontend frameworks. Key features for frontend developers:

- **CORS enabled** for cross-origin requests
- **Real-time progress** through thinking steps
- **Clickable links** with hover summaries
- **Structured responses** for easy UI rendering

## Architecture

- **FastAPI**: Modern, fast web framework
- **Langraph**: AI agent orchestration
- **Async Processing**: Non-blocking operations
- **Web Scraping**: Automatic link summarization
- **Pydantic Models**: Type-safe data validation
