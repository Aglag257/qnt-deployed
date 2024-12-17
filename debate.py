import os
from openai import OpenAI
import requests
import streamlit as st


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

if not OPENAI_API_KEY or not TAVILY_API_KEY:
    raise ValueError("API keys not found. Set OPENAI_API_KEY and TAVILY_API_KEY as environment variables.")

client = OpenAI(api_key=OPENAI_API_KEY)

def openai_response(prompt):
    """Get response from OpenAI's API."""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=700,  # Increase this to 700 or more
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"

def tavily_search(query):
    """Fetch data from Tavily API."""
    url = f"https://api.tavily.ai/search?q={query}&key={TAVILY_API_KEY}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            results = response.json()
            return results.get("results", [])[0].get("snippet", "No relevant results found.")
        return "Error in Tavily API response."
    except Exception as e:
        return f"Error: {e}"

def generate_arguments(topic):
    """Generate initial arguments for both sides."""
    pro_prompt = f"Provide the strongest arguments supporting the following topic: '{topic}'. Do not include any introductions, preambles, or disclaimers. List arguments as bullet points or numbered points."
    con_prompt = f"Provide the strongest arguments against the following topic: '{topic}'. Do not include any introductions, preambles, or disclaimers. List arguments as bullet points or numbered points."

    pro_args = openai_response(pro_prompt)
    con_args = openai_response(con_prompt)

    return pro_args, con_args

def debate_round(pro_args, con_args, round_num):
    """Conduct a round of debate between agents."""
    print(f"\nRound {round_num}")
    print("Pro side arguments:")
    print(pro_args)

    print("\nCon side arguments:")
    print(con_args)

    pro_rebuttal_prompt = f"Here are the con side's arguments: {con_args}. Rebut them concisely."
    con_rebuttal_prompt = f"Here are the pro side's arguments: {pro_args}. Rebut them concisely."

    pro_rebuttal = openai_response(pro_rebuttal_prompt)
    con_rebuttal = openai_response(con_rebuttal_prompt)

    return pro_rebuttal, con_rebuttal

def conclude_debate(pro_args, con_args):
    """Summarize the debate and decide the winner."""
    conclusion_prompt = (
        f"Summarize the arguments and counterarguments presented for the topic. \n"
        f"Pro arguments: {pro_args}. \n"
        f"Con arguments: {con_args}. \n"
        "Determine which side presented stronger arguments based on logical reasoning, evidence, and persuasiveness."
    )
    return openai_response(conclusion_prompt)

if __name__ == "__main__":

    st.title("AI Debate System")

    # Input for debate topic
    topic = st.text_input("Enter the debate topic:")

    if topic:
        st.write(f"### Debate Topic: {topic}")
        st.write("---")

        # Generate initial arguments
        pro_args, con_args = generate_arguments(topic)

        # Split arguments safely into blocks (ensure no truncation)
        pro_args_list = pro_args.split("\n") if "\n" in pro_args else [pro_args]
        con_args_list = con_args.split("\n") if "\n" in con_args else [con_args]

        # Chat-like layout
        st.subheader("Round 1: Arguments")
        max_len = max(len(pro_args_list), len(con_args_list))
        for i in range(max_len):
            col1, col2 = st.columns(2)
            with col1:
                if i < len(pro_args_list) and pro_args_list[i].strip():
                    with st.chat_message("assistant"):
                        st.markdown(f"**Pro Side:** {pro_args_list[i]}")
            with col2:
                if i < len(con_args_list) and con_args_list[i].strip():
                    with st.chat_message("user"):
                        st.markdown(f"**Con Side:** {con_args_list[i]}")

        # Conduct multiple debate rounds
        num_rounds = 3
        for round_num in range(1, num_rounds + 1):
            st.subheader(f"Round {round_num}: Rebuttals")
            
            # Generate rebuttals
            pro_args, con_args = debate_round(pro_args, con_args, round_num)
            pro_args_list = pro_args.split("\n")
            con_args_list = con_args.split("\n")

            for pro, con in zip(pro_args_list, con_args_list):
                col1, col2 = st.columns(2)
                with col1:
                    if pro.strip():
                        with st.chat_message("assistant"):
                            st.markdown(f"**Pro Side Rebuttal:** {pro}")
                with col2:
                    if con.strip():
                        with st.chat_message("user"):
                            st.markdown(f"**Con Side Rebuttal:** {con}")

        # Display the conclusion
        result = conclude_debate(pro_args, con_args)
        st.subheader("Debate Conclusion:")
        st.write(result)
