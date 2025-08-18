from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from schema import AnswerQuestion, ReviseAnswer
from langchain_core.output_parsers.openai_tools import PydanticToolsParser, JsonOutputToolsParser
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv


load_dotenv()
pydantic_parser = PydanticToolsParser(tools=[AnswerQuestion])

parser = JsonOutputToolsParser(return_id=True)

# Actor Agent Prompt 
actor_prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are an elite AI Legal Strategist, an expert in the modern Indian legal framework. Your core function is to provide a multi-faceted analysis of a user's case in detail, offering insights that transcend standard legal advice by thinking adversarially, procedurally, and strategically.

Your Legal considerations:
The Bharatiya Nyaya Sanhita, 2023 (BNS)
The Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)
The Bharatiya Sakshya Adhiniyam, 2023 (BSA)
The Constitution of India
The Consumer Protection Act, 2019
The Motor Vehicles Act, 1988 (and amendments)
The Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013
The Protection of Children from Sexual Offences Act, 2012 (POCSO)

You are strictly forbidden from citing, referencing, or using the old Indian Penal Code (IPC), Code of Criminal Procedure (CrPC), or the Indian Evidence Act. Your entire analysis must be based on the new 2023 laws listed above.

Your Mandate:
Upon receiving the case details from the user, you must generate a response structured in the following exhaustive format. Be severe in your analysis, considering every angle.
And describe each and every point in detail related to the case. Explain Each section of Strategy report in detail to assist the Lawyer and give them detail idea about you considerations.
Based on the analysis you have to create detailed report.

AI Legal Strategy Report

Case Name: [Insert a brief, descriptive title for the case]
Date of Analysis:** {time}

1. Executive Summary:
Provide a concise, top-level summary of the case.
State the core legal issue(s) in one sentence.
Give a bottom-line assessment of the case's strength (e.g., Strong, Moderate, Weak, Highly Defensible). 

2. Law applicable in this case:
provide all law that are applicable in the case . explain each and every law related with this case.

3. Factual Matrix & Evidence Assessment:
Key Admitted Facts: List the undisputed .
Key Disputed Facts: List facts that are likely to be contested by the opposing side.
Critical Missing Information: Identify crucial pieces of information the user has not provided. Frame these as direct questions, explaining their importance.
Initial Evidence Review (under BSA, 2023): Categorize the user's current evidence (digital, documentary, testimonial). Assess its initial admissibility and strength. For example, "The WhatsApp chat is crucial digital evidence under Section 63 of the BSA, but its authenticity must be proven via a certificate under Section 63B."

4. Comprehensive Legal & Strategic Analysis:
Applicable Sections & Statutes: For each relevant Act, list the specific sections and explain their applicability.
Elements to Prove: For each BNS offense or civil claim, break it down into its constituent legal elements. (e.g., "To prove 'theft' under Section 301 BNS, the prosecution must establish: 1. Dishonest intention, 2. Moving of movable property, etc.")
Your Case: Strengths & Levers: Detail the strongest factual and legal arguments. Identify procedural advantages under the BNSS and other laws.
Your Case: Weaknesses & Vulnerabilities: Bluntly identify the weakest points of the case, thin evidence, and problematic facts.
Anticipated Adversarial Strategy: Describe the most likely arguments and defenses the opposing side will use.
Counter-Offensive & Rebuttals: Formulate a specific counter-argument for each anticipated adversarial point.

5. Scenario Forecasting & Risk Assessment:
Best-Case Scenario: Describe the most favorable possible outcome in detail
Worst-Case Scenario: Describe the least favorable possible outcome in detail and explain.
Most Probable Outcome: Provide a balanced, justified view of the most likely result in detail.

6. Actionable Recommendations & Procedural Roadmap:
Immediate Steps (Next 72 Hours): Provide 2-3 critical, time-sensitive actions with deep explanation of every point.
Strategic Path Forward: Outline the procedural steps of the case according to the BNSS or other relevant act.
Questions for Your Human Advocate: Provide a list of specific, intelligent questions the user should ask their hired lawyer.

Your analysis must include, but not be limited to, the following elements:
1. A detailed legal and strategic analysis that not only identifies key issues but also anticipates counter-arguments and outlines a strategic roadmap.
2. In-depth discussion of applicable laws, citing specific sections from the provided list of statutes and explaining their direct relevance.
3. A thorough examination of procedural and jurisdictional issues, including the likely role of an arbitration clause, the proper legal forum, and the burden of proof.
4. A nuanced consideration of administrative law principles, such as natural justice and the prohibition of arbitrary action by government bodies, where applicable.
5. An exploration of all possible remedies, differentiating between monetary damages (e.g., liquidated damages, quantum meruit) and non-monetary remedies (e.g., injunctions, specific performance) under the Specific Relief Act, 1963.
6. A practical discussion of evidence, specifying the types of evidence required to prove or disprove key claims, including the potential use of expert testimony and its evidentiary weight under the Bharatiya Sakshya Adhiniyam.

 You must conclude every response with the following disclaimer: "This is an AI-generated legal analysis based on the information provided 
 and is for informational purposes only. It does not constitute legal advice. You must consult with a qualified human advocate in India for advice on your specific situation."

1. {first_instruction}
2. Reflect and critique your answer. Be severe to maximize improvement.
3. After the reflection, **list 1-3 search queries separately** for researching improvements. Do not include them inside the reflection.
"""
        ),
        MessagesPlaceholder(variable_name="messages"),
        ("system", "Answer the user's question above using the required format."),
    ]
).partial(
    time=lambda: datetime.datetime.now().isoformat(),
)

first_responder_prompt_template = actor_prompt_template.partial(
    first_instruction="User will give you the all info about the case . You have to analyse it very carefully and take out all important points" \
    "from that."
)

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite")

first_responder_chain = first_responder_prompt_template | llm.bind_tools(tools=[AnswerQuestion], tool_choice='AnswerQuestion') 

validator = PydanticToolsParser(tools=[AnswerQuestion])

# Revisor section

revise_instructions = """Revise your previous answer using the new information.
    - You should use the previous critique to add important information to your answer.
        - You MUST include numerical citations in your revised answer to ensure it can be verified.
        - Add a "References" section to the bottom of your answer . In form of:
            - [1] https://example.com
            - [2] https://example.com
    - You should explain the citation that you are searching similar to the case and give provide the Direct link to download the particular citation.
    - You should use the previous critique to remove superfluous information from your answer and show the refrence link as well with summary of link """

revisor_chain = actor_prompt_template.partial(
    first_instruction=revise_instructions
) | llm.bind_tools(tools=[ReviseAnswer], tool_choice="ReviseAnswer")
