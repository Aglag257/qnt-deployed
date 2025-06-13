import os
from langraph import Graph, Node
from langraph.llms import ChatOpenAI
from langraph.connectors import PDFConnector

# Greek-language multi-agent summarization system using LangGraph

# Initialize LLM client (use GPT-4)
llm = ChatOpenAI(model_name="gpt-4", temperature=0.2)

# Connector to read PDF articles
pdf_reader = PDFConnector()

# Node: Διαβάζει το PDF και επιστρέφει το πλήρες κείμενο
read_article = Node(
    name="read_article",
    llm=llm,
    prompt="""
Διαβάστε το πλήρες κείμενο του άρθρου από το PDF στον μονοπάτι {{pdf_path}} και επιστρέψτε μόνο το κείμενο χωρίς σχόλια.
""",
    inputs=["pdf_path"]
)

# Node: Πρώτη περίληψη σε bullets
first_summary = Node(
    name="first_summary",
    llm=llm,
    prompt="""
Έχοντας το πλήρες κείμενο του άρθρου:
"""
"""
1) Δημιουργήστε μια αρχική περίληψη σε μορφή bullets στα Ελληνικά.
2) Κάθε bullet πρέπει να καλύπτει ένα κύριο σημείο του άρθρου.
""",
    inputs=["read_article.output"]
)

# Node: Δημιουργία ερωτήσεων κατανόησης
question_generator = Node(
    name="question_generator",
    llm=llm,
    prompt="""
Έχοντας το πλήρες κείμενο του άρθρου:
"""
"""
1) Δημιουργήστε 5-7 ερωτήσεις πολλαπλής επιλογής ή ανοικτού τύπου που ελέγχουν την κατανόηση των κύριων σημείων.
2) Παρουσιάστε τις ερωτήσεις στα Ελληνικά.
""",
    inputs=["read_article.output"]
)

# Node: Απάντηση στις ερωτήσεις με βάση την περίληψη
answer_questions = Node(
    name="answer_questions",
    llm=llm,
    prompt="""
Έχοντας την αρχική περίληψη:
{{first_summary.output}}

και τις ερωτήσεις:
{{question_generator.output}}

Απαντήστε σε κάθε ερώτηση χρησιμοποιώντας μόνο την περίληψη.
""",
    inputs=["first_summary.output", "question_generator.output"]
)

# Node: Αξιολόγηση απαντήσεων και feedback για τη βελτίωση της περίληψης
evaluate_answers = Node(
    name="evaluate_answers",
    llm=llm,
    prompt="""
Έχοντας την αρχική περίληψη:
{{first_summary.output}}

τις ερωτήσεις:
{{question_generator.output}}

και τις απαντήσεις:
{{answer_questions.output}}

1) Εντοπίστε λάθη ή ελλείψεις στις απαντήσεις.
2) Δώστε ανατροφοδότηση στον κόμβο της περίληψης για το πώς να βελτιώσει τα bullets ώστε να μην υπάρχουν λάθη.
Παρουσιάστε σχόλια στα Ελληνικά.
""",
    inputs=["first_summary.output", "question_generator.output", "answer_questions.output"]
)

# Node: Ενημέρωση περίληψης βάσει feedback
update_summary = Node(
    name="update_summary",
    llm=llm,
    prompt="""
Έχοντας το αρχικό κείμενο:
{{read_article.output}}

την αρχική περίληψη:
{{first_summary.output}}

και τα σχόλια:
{{evaluate_answers.output}}

Δημιουργήστε μια βελτιωμένη περίληψη σε bullets στα Ελληνικά.
""",
    inputs=["read_article.output", "first_summary.output", "evaluate_answers.output"]
)

# Node: Αποθήκευση τελικής περίληψης σε αρχείο .txt
save_summary = Node(
    name="save_summary",
    llm=llm,
    prompt="""
Έχοντας την τελική περίληψη:
{{final_summary.output}}

Αποθηκεύστε την περίληψη στο αρχείο {{output_path}}.
Επιστρέψτε το μονοπάτι του αρχείου.
""",
    inputs=["final_summary.output", "output_path"]
)

# Build graph and connect nodes

g = Graph()

# Add nodes
nodes = [read_article, first_summary, question_generator, answer_questions, evaluate_answers, update_summary, save_summary]
for node in nodes:
    g.add_node(node)

# Define edges and loop until no errors or max iterations

# First pass

g.add_edge("read_article", "first_summary")
g.add_edge("read_article", "question_generator")
g.add_edge("first_summary", "answer_questions")
g.add_edge("question_generator", "answer_questions")
g.add_edge("first_summary", "evaluate_answers")
g.add_edge("question_generator", "evaluate_answers")
g.add_edge("answer_questions", "evaluate_answers")
g.add_edge("read_article", "update_summary")
g.add_edge("first_summary", "update_summary")
g.add_edge("evaluate_answers", "update_summary")

g.add_edge("update_summary", "question_generator")
g.add_edge("update_summary", "answer_questions")

g.add_edge("update_summary", "evaluate_answers")

g.add_edge("update_summary", "save_summary")

# Function to run iterative refinement

def summarize_pdf(pdf_path: str, output_txt: str, max_iters: int = 5):
    # Initial inputs
    data = {"pdf_path": pdf_path, "output_path": output_txt}
    # Run graph with iteration
    outputs = g.run(data, iterations=max_iters)
    return outputs.get("save_summary")

# Example usage
if __name__ == "__main__":
    input_pdf = "article.pdf"
    output_txt = "summary.txt"
    path = summarize_pdf(input_pdf, output_txt)
    print(f"Η περίληψη αποθηκεύτηκε στο: {path}")
