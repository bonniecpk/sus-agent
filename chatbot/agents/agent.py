from google.adk.agents import Agent

root_agent = Agent(
    name="sus_agent",
    model="gemini-3-pro-preview",
    description="A helpful assistant agent.",
    instruction="You are a helpful assistant. Answer the user's questions clearly and concisely.",
)
