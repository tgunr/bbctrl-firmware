from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama.llms import OllamaLLM
# Set up the prompt template
template = """Question: {question}
Answer: Provide a clear, concise explanation in plain language."""
prompt = ChatPromptTemplate.from_template(template)
# Initialize the LLM
model = OllamaLLM(model="llama3.2")
# Combine prompt and model
chain = prompt | model
# Function to process questions
def answer_question(question):
    response = chain.invoke({"question": question})
    return response
# Test the bot
if __name__ == "__main__":
    question = "What is machine learning?"
    response = answer_question(question)
    print(f"Question: {question}")
    print(f"Answer: {response}")
