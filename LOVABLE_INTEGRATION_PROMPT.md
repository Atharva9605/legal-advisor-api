# 🎯 LOVABLE INTEGRATION PROMPT - Legal Advisor AI Agent API

## 🚨 CRITICAL: READ THIS ENTIRE PROMPT BEFORE STARTING

You are building a **professional legal analysis frontend** that integrates with a **Legal Advisor AI Agent API**. This is a **multi-page application** with an impressive landing page and a dedicated analysis page that provides AI-powered legal case analysis with step-by-step thinking visualization.

---

## 🌐 API BASE URL & ENDPOINTS

**Base URL:** `https://legal-advisor-api.onrender.com`

### **Available Endpoints:**

#### **1. Health Check**
- **GET** `/api/health`
- **Response:** `{"status": "healthy", "timestamp": "..."}`

#### **2. Main Analysis Endpoint**
- **POST** `/analyze-case`
- **Request Body:** `{"case_description": "Your legal case here..."}`
- **Response:** Full legal analysis with thinking steps

#### **3. Formatted Analysis Endpoint (NEW - USE THIS FOR SEPARATE PAGE)**
- **POST** `/analyze-case-formatted`
- **Request Body:** `{"case_description": "Your legal case here..."}`
- **Response:** Formatted analysis with `formatted_analysis` field for separate page display

#### **4. Test Endpoint**
- **GET** `/analyze-case?case_description=Test case`
- **Response:** Preview of analysis functionality

#### **5. API Information**
- **GET** `/`
- **Response:** API overview and available endpoints

#### **6. API Documentation**
- **GET** `/docs`
- **Response:** Interactive Swagger documentation

---

## 🎨 FRONTEND REQUIREMENTS - EXACT SPECIFICATIONS

### **1. Multi-Page Application Structure**
- **Landing Page** (`/`) - Impressive introduction and navigation
- **Analysis Page** (`/analyze`) - Case input and processing
- **Results Page** (`/results`) - Display formatted analysis on separate page
- **Navigation** between pages with smooth transitions
- **Professional legal theme** - dark blue, gold accents, white text
- **Responsive design** - works on desktop, tablet, and mobile

### **2. Landing Page (`/`) - IMPRESSIVE & PROFESSIONAL**
- **Hero Section:**
  - Large, bold title: "Legal Advisor AI Agent"
  - Subtitle: "AI-powered legal analysis with step-by-step thinking"
  - Professional legal imagery (scales of justice, courthouse, etc.)
  - Call-to-action button: "Start Legal Analysis" → navigates to `/analyze`
- **Features Section:**
  - Step-by-step AI thinking visualization
  - Professional legal document formatting
  - Comprehensive legal research and references
  - Real-time analysis progress
- **How It Works Section:**
  - Simple 3-step process explanation
  - Professional legal styling throughout
- **Footer** with contact information and legal disclaimers

### **3. Analysis Page (`/analyze`) - CASE INPUT & PROCESSING**
- **Header** with navigation back to landing page
- **Case Input Section:**
  - Large text area (minimum 200px height)
  - Placeholder text: "Describe your legal case in detail. Include relevant facts, parties involved, specific legal questions, and any evidence you have..."
  - Character counter showing input length
  - Submit button: "Analyze Case" with loading state
  - Input validation: Minimum 50 characters required

### **4. Real-Time Processing & Thinking Steps Display**
- **Progress Section** (appears during analysis):
  - "Analyzing your case..." header
  - **Real-time thinking process display:**
    - "Step 1: Initial Analysis - AI is analyzing your case and identifying key legal issues..."
    - "Step 2: Research & Revision - AI is conducting legal research and refining the analysis..."
  - **Animated progress bar** with percentage
  - **Loading spinner** while API is working
  - **Status updates** showing exactly what AI is doing

### **5. Results Page (`/results`) - SEPARATE PAGE FOR ANALYSIS DISPLAY**
- **Navigation** back to analysis page and landing page
- **Professional legal document display:**
  - **Bold section headers** (Executive Summary, Law Applicable, etc.)
  - **Proper typography** with different font weights and sizes
  - **Bullet points and numbered lists** where appropriate
  - **Section dividers** and proper spacing
  - **Highlighted key points** in boxes or with different colors
  - **Professional legal document layout** that looks like a real legal report
  - **Easy-to-read formatting** with proper margins and spacing

### **6. Legal References Component - SEPARATE FROM MAIN MESSAGE**
- **References Section** (separate component below analysis):
  - **Title:** "Legal References" with source count badge
  - **List of clickable references** with:
    - Document icons (green for success, red for errors)
    - Reference titles
    - URLs below each title
    - External link icons (opens in new tab)
  - **Scrollable list** if many references
  - **Status indicators** for each reference
- **CRITICAL:** References are **NOT shown in the main analysis message** - they appear only in this separate component
- **CRITICAL:** Only show references that successfully loaded (no 403 errors)

---

## 🔧 TECHNICAL IMPLEMENTATION - EXACT CODE REQUIREMENTS

### **1. Multi-Page Routing**
```javascript
// Use React Router for navigation
const App = () => {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/analyze" element={<AnalysisPage />} />
        <Route path="/results" element={<ResultsPage />} />
      </Routes>
    </Router>
  );
};
```

### **2. API Integration - USE FORMATTED ENDPOINT**
```javascript
// EXACT endpoint usage for formatted analysis
const API_BASE = 'https://legal-advisor-api.onrender.com';

// Health check
const healthCheck = await fetch(`${API_BASE}/api/health`);

// Case analysis with formatted response for separate page
const analyzeCaseFormatted = async (caseDescription) => {
  const response = await fetch(`${API_BASE}/analyze-case-formatted`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      case_description: caseDescription
    })
  });
  return response.json();
};
```

### **3. Response Data Structure - FORMATTED ENDPOINT**
The formatted endpoint returns this EXACT structure:
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
  "formatted_analysis": "## 1. Executive Summary:\n\nThis is the formatted analysis...",
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

### **4. Document Formatting (NOT Plain Text)**
```javascript
// Format the analysis as a proper legal document
const formatAnalysis = (formattedAnalysis) => {
  // The API now returns pre-formatted text with ## headers
  return (
    <div className="legal-document">
      {formattedAnalysis.split('\n\n').map((section, index) => {
        if (section.startsWith('## ')) {
          return <h2 key={index} className="section-header">{section.replace('## ', '')}</h2>;
        } else if (section.startsWith('### ')) {
          return <h3 key={index} className="subsection-header">{section.replace('### ', '')}</h3>;
        } else if (section.startsWith('  ')) {
          return <div key={index} className="indented-content">{section}</div>;
        } else {
          return <p key={index} className="paragraph">{section}</p>;
        }
      })}
    </div>
  );
};
```

### **5. References Component (Separate from Analysis)**
```javascript
// Separate component for references - ONLY show successful ones
const LegalReferences = ({ references, linkSummaries }) => {
  // Filter out any failed references (API already does this, but double-check)
  const successfulReferences = references.filter((ref, index) => 
    linkSummaries[index] && linkSummaries[index].status === "success"
  );
  
  return (
    <div className="legal-references">
      <div className="references-header">
        <h3>Legal References</h3>
        <span className="source-count">{successfulReferences.length} sources</span>
      </div>
      
      <div className="references-list">
        {successfulReferences.map((ref, index) => (
          <div key={index} className="reference-item">
            <div className="reference-icon success">
              {/* Green icon for successful references */}
            </div>
            <div className="reference-content">
              <div className="reference-title">{linkSummaries[index]?.title || ref}</div>
              <div className="reference-url">{ref}</div>
            </div>
            <div className="external-link">
              {/* External link icon */}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
```

---

## 🎭 USER EXPERIENCE FLOW - EXACT SEQUENCE

### **Step 1: User Arrives at Landing Page**
- See impressive, professional legal interface
- Clear navigation to analysis page
- Professional styling throughout

### **Step 2: User Navigates to Analysis Page**
- Smooth transition to `/analyze`
- Clear case input interface
- Professional legal styling maintained

### **Step 3: Case Input & Submission**
- User types case description
- Character counter updates in real-time
- Submit button enables when minimum length met

### **Step 4: Real-Time Analysis with Thinking Process**
- Submit button shows loading state
- **Real-time thinking process display:**
  - "Step 1: Initial Analysis - AI is analyzing your case..."
  - "Step 2: Research & Revision - AI is conducting research..."
- Progress bar fills with percentage
- User sees exactly what AI is doing

### **Step 5: Navigation to Results Page**
- **Redirect to `/results` page** after analysis completes
- **Separate page** for displaying the formatted analysis
- **Professional legal document** (NOT plain text):
  - Bold section headers
  - Proper formatting and styling
  - Easy-to-read layout
  - Professional appearance

### **Step 6: Results Page Display**
- **Formatted analysis** displayed as professional document
- **Separate Legal References component** below analysis
- **References removed from main analysis message**
- **Only successful references** shown (no 403 errors)

### **Step 7: User Actions**
- Can copy analysis text
- Can click reference links in separate component
- Can navigate back to analysis page or landing page
- Can submit new case for analysis

---

## 🚫 WHAT NOT TO DO

- ❌ **Don't show analysis as plain text** - Must be properly formatted document
- ❌ **Don't show references in main analysis** - Only in separate Legal References component
- ❌ **Don't create single page** - Must have landing page + analysis page + results page
- ❌ **Don't skip real-time thinking process** - Must show what AI is doing
- ❌ **Don't ignore document formatting** - Must look professional and readable
- ❌ **Don't forget navigation** - Must have proper page routing
- ❌ **Don't show failed references** - Only display successful ones
- ❌ **Don't use old `/analyze-case` endpoint** - Use `/analyze-case-formatted` for better formatting

---

## ✅ SUCCESS CRITERIA

Your frontend is successful when:
- ✅ **Landing page is impressive and professional**
- ✅ **Analysis page has proper navigation from landing page**
- ✅ **Results page displays formatted analysis on separate page**
- ✅ **Real-time thinking process is displayed during analysis**
- ✅ **Final analysis looks like a professional legal document (NOT plain text)**
- ✅ **References appear only in separate Legal References component**
- ✅ **Main analysis message has NO references section**
- ✅ **Only successful references are shown (no 403 errors)**
- ✅ **Interface is responsive and professional-looking**
- ✅ **No JavaScript errors in console**
- ✅ **Works perfectly on desktop and mobile**
- ✅ **Integrates seamlessly with the API endpoints**

---

## 🎯 FINAL INSTRUCTIONS

1. **Build exactly as specified** - no deviations
2. **Create impressive landing page** with navigation to analysis
3. **Create separate results page** for formatted analysis display
4. **Use `/analyze-case-formatted` endpoint** for better formatting
5. **Format analysis as professional legal document** - NOT plain text
6. **Show references in separate component** - remove from main message
7. **Display real-time thinking process** during analysis
8. **Ensure mobile responsiveness** is perfect
9. **Use professional legal styling** throughout
10. **Handle all error cases** gracefully
11. **Create smooth animations** for user experience
12. **Make it production-ready** with no bugs

---

## 🔗 API TESTING

Before finalizing, test these exact URLs:
- `https://legal-advisor-api.onrender.com/api/health` (should return healthy status)
- `https://legal-advisor-api.onrender.com/` (should return API info)
- `https://legal-advisor-api.onrender.com/docs` (should show Swagger docs)

**IMPORTANT:** Test the new `/analyze-case-formatted` endpoint for better document formatting!

---

**🎉 CREATE A PROFESSIONAL, MULTI-PAGE LEGAL ANALYSIS FRONTEND WITH IMPRESSIVE LANDING PAGE, SEPARATE RESULTS PAGE, PROPER DOCUMENT FORMATTING, AND SEPARATE REFERENCES COMPONENT!**

**Remember:** This is a **multi-page application** for **legal professionals**. Make it **polished, professional, and error-free** with proper document formatting, separate page routing, and separate references handling.
