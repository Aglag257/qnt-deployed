import os
from typing import TypedDict, Annotated
import operator
from langgraph.graph import StateGraph, END, START
from langchain_core.messages import HumanMessage, AIMessage, AnyMessage
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import PyPDFLoader

# -------------------
# Define State Schema
# -------------------
class SummaryState(TypedDict):
    pdf_path: str
    output_path: str
    pdf_text: str
    summary: str
    questions: str
    answers: str
    feedback: str
    messages: Annotated[list[AnyMessage], operator.add]

# -------------------
# Initialize LLM
# -------------------
llm = ChatOpenAI(model="gpt-4", temperature=0.2)

# -------------------
# Define Nodes
# -------------------
def read_article(state: SummaryState) -> dict:
    loader = PyPDFLoader(state["pdf_path"])
    pages = loader.load()
    text = "\n\n".join([p.page_content for p in pages])
    return {"pdf_text": text}

def generate_summary(state: SummaryState) -> dict:
    prompt = f"""
Διαβάστε το παρακάτω ελληνικό άρθρο και δημιουργήστε μία αρχική περίληψη με bullets. 
Κάθε bullet να αναφέρεται σε ένα βασικό σημείο του άρθρου:

{state['pdf_text']}
"""
    res = llm.invoke([HumanMessage(content=prompt)])
    return {"summary": res.content}

def generate_questions(state: SummaryState) -> dict:
    prompt = f"""
Διαβάστε το παρακάτω ελληνικό άρθρο και δημιουργήστε 5-7 ερωτήσεις που να ελέγχουν την κατανόηση των βασικών του σημείων:

{state['pdf_text']}
"""
    res = llm.invoke([HumanMessage(content=prompt)])
    return {"questions": res.content}

def answer_questions(state: SummaryState) -> dict:
    prompt = f"""
Έχοντας την παρακάτω περίληψη του άρθρου:

{state['summary']}

Απαντήστε στις ερωτήσεις:

{state['questions']}
"""
    res = llm.invoke([HumanMessage(content=prompt)])
    return {"answers": res.content}

def evaluate_answers(state: SummaryState) -> dict:
    prompt = f"""
Αξιολογήστε τις παρακάτω απαντήσεις βασισμένοι στο αρχικό άρθρο και δώστε σχόλια για το πώς μπορεί να βελτιωθεί η περίληψη ώστε να απαντώνται σωστά οι ερωτήσεις:

Άρθρο:
{state['pdf_text']}

Περίληψη:
{state['summary']}

Ερωτήσεις:
{state['questions']}

Απαντήσεις:
{state['answers']}
"""
    res = llm.invoke([HumanMessage(content=prompt)])
    return {"feedback": res.content}

def improve_summary(state: SummaryState) -> dict:
    prompt = f"""
Έχοντας την παρακάτω περίληψη:

{state['summary']}

Και τα εξής σχόλια αξιολόγησης:

{state['feedback']}

Βελτιώστε την περίληψη με βάση τα σχόλια. Η νέα περίληψη να είναι και πάλι σε μορφή bullets.
"""
    res = llm.invoke([HumanMessage(content=prompt)])
    return {"summary": res.content}

def save_to_file(state: SummaryState) -> dict:
    with open(state["output_path"], "w", encoding="utf-8") as f:
        f.write(state["summary"])
    return {"output_path": state["output_path"]}

# -------------------
# Build the Graph
# -------------------
graph = StateGraph(SummaryState)

# Add nodes
graph.add_node("read", read_article)
graph.add_node("summarize", generate_summary)
graph.add_node("ask", generate_questions)
graph.add_node("answer", answer_questions)
graph.add_node("evaluate", evaluate_answers)
graph.add_node("revise", improve_summary)
graph.add_node("save", save_to_file)

# Add edges
graph.set_entry_point("read")
graph.add_edge("read", "summarize")
graph.add_edge("read", "ask")
graph.add_edge("summarize", "answer")
graph.add_edge("ask", "answer")
graph.add_edge("summarize", "evaluate")
graph.add_edge("answer", "evaluate")
graph.add_edge("evaluate", "revise")
graph.add_edge("revise", "answer")  # loop

graph.add_edge("revise", "evaluate")
graph.add_edge("revise", "save")
graph.add_edge("save", END)

compiled_graph = graph.compile()

# -------------------
# Run Function
# -------------------
def summarize_greek_pdf(pdf_path: str, output_path: str, iterations: int = 5):
    state = {
        "pdf_path": pdf_path,
        "output_path": output_path,
        "messages": []
    }
    result = compiled_graph.invoke(state, config={"recursion_limit": iterations})
    print("Περίληψη αποθηκεύτηκε στο:", result["output_path"])

# Example usage
if __name__ == "__main__":
    summarize_greek_pdf("article.pdf", "summary.txt")
