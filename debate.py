import os
from openai import OpenAI
import requests

def load_api_keys(filename="api_keys.txt"):
    api_keys = {}
    try:
        with open(filename, "r") as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    api_keys[key] = value
    except FileNotFoundError:
        print(f"Error: {filename} not found. Ensure your API keys are in this file.")
    return api_keys

api_keys = load_api_keys()
OPENAI_API_KEY = api_keys.get("OPENAI_API_KEY")
TAVILY_API_KEY = api_keys.get("TAVILY_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

def openai_response(prompt):
    """Get response from OpenAI's API."""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a helpful assistant."},
                     {"role": "user", "content": prompt}],
            max_tokens=300,
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
    pro_prompt = f"You are an AI debater supporting the topic: {topic}. Provide your strongest arguments."
    con_prompt = f"You are an AI debater opposing the topic: {topic}. Provide your strongest arguments."

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
    print("Welcome to the AI Debate System!")
    topic = input("Enter the debate topic: ")

    # Generate initial arguments
    pro_args, con_args = generate_arguments(topic)

    # Conduct multiple debate rounds
    num_rounds = 3
    for round_num in range(1, num_rounds + 1):
        pro_args, con_args = debate_round(pro_args, con_args, round_num)

    # Summarize and conclude the debate
    result = conclude_debate(pro_args, con_args)
    print("\nDebate Conclusion:")
    print(result)
