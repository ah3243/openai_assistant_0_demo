import time
from openai import OpenAI, OpenAIError

class OpenAIAssistant:
    """A class to interact with OpenAI's GPT model for creating and managing a chat session."""

    def __init__(self, name, instructions, model):
        """Initialize the assistant with a specific model, name, and instructions."""
        try:
            self.client = OpenAI()
            self.assistant = self.client.beta.assistants.create(
                name=name, 
                instructions=instructions, 
                model=model
            )
            self.assistant_id = self.assistant.id
        except OpenAIError as e:
            print(f"Error in initializing the assistant: {e}")
            raise

    def create_thread(self):
        """Create a new conversation thread and return its ID."""
        try:
            thread = self.client.beta.threads.create()
            return thread.id
        except OpenAIError as e:
            print(f"Error in creating thread: {e}")
            raise

    def send_message(self, thread_id, message):
        """Send a message to a specific thread."""
        try:
            self.client.beta.threads.messages.create(
                thread_id=thread_id, 
                role="user", 
                content=message
            )
        except OpenAIError as e:
            print(f"Error in sending message: {e}")
            raise

    def create_run(self, thread_id):
        """Create a run (a request for the assistant to process messages in a thread)."""
        try:
            return self.client.beta.threads.runs.create(
                thread_id=thread_id, 
                assistant_id=self.assistant_id
            )
        except OpenAIError as e:
            print(f"Error in creating run: {e}")
            raise

    def wait_on_run(self, run, thread_id):
        """Wait for a run to complete and return the updated run object."""
        while run.status in ["queued", "in_progress"]:
            try:
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id, 
                    run_id=run.id
                )
                time.sleep(0.5)
            except OpenAIError as e:
                print(f"Error in run retrieval: {e}")
                raise
        return run

    def get_responses(self, thread_id):
        """Retrieve all responses from a thread."""
        try:
            messages = self.client.beta.threads.messages.list(thread_id=thread_id)
            return [(msg.role, msg.content[0].text.value) for msg in messages]
        except OpenAIError as e:
            print(f"Error in retrieving responses: {e}")
            raise

    def get_latest_response(self, thread_id):
        """Retrieve the latest response from the assistant in a thread."""
        try:
            messages = self.client.beta.threads.messages.list(thread_id=thread_id)
            for msg in messages:
                if msg.role == 'assistant':
                    return msg.content[0].text.value
            return None
        except OpenAIError as e:
            print(f"Error in retrieving latest response: {e}")
            raise

    def chat(self):
        """Start a chat session, allowing user input and displaying assistant responses."""
        try:
            thread_id = self.create_thread()
        except OpenAIError:
            print("Failed to start chat due to thread creation error.")
            return

        while True:
            user_message = input("You: ")
            if user_message.lower() == 'exit':
                break

            try:
                self.send_message(thread_id, user_message)
                run = self.create_run(thread_id)
                self.wait_on_run(run, thread_id)
                latest_response = self.get_latest_response(thread_id)
                if latest_response:
                    print("Assistant:", latest_response)
            except OpenAIError:
                print("An error occurred during the chat session.")
                break

# Example usage
try:
    assistant = OpenAIAssistant("Math Tutor", "You are a personal math tutor. Answer questions briefly, in a sentence or less.", "gpt-4-1106-preview")
    assistant.chat()
except Exception as e:
    print(f"Failed to create assistant: {e}")
