import time
from openai import OpenAI, OpenAIError


class OpenAIAssistant:
    def __init__(self, name, instructions, model, knowledge_files=None, auto_accept=False):
        self.client = OpenAI()
        
        self.name = name
        self.instructions = instructions
        self.model = model
        self.assistant_id = None
        self.knowledge_files = knowledge_files if knowledge_files is not None else []
        self.auto_accept = auto_accept

        self.manage_assistant()

    def assistant_exists(self, name):
        """Check if an assistant with the given name already exists."""
        assistants = self.client.beta.assistants.list()
        for assistant in assistants.data:
            if assistant.name == name:
                return assistant.id
        return None

    def create_assistant(self):
        """Create a new assistant, optionally with knowledge files."""
        try:
            file_ids = []
            if self.knowledge_files:
                file_ids = [self.upload_file(file_path) for file_path in self.knowledge_files]

            assistant = self.client.beta.assistants.create(
                name=self.name, 
                instructions=self.instructions, 
                model=self.model,
                tools=[{"type": "retrieval"}] if file_ids else [],
                file_ids=file_ids
            )
            return assistant.id
        except OpenAIError as e:
            print(f"Error in creating assistant: {e}")
            raise

    def modify_assistant(self, assistant_id):
        """Modify an existing assistant, optionally updating knowledge files."""
        try:
            file_ids = []

            if self.knowledge_files:
                file_ids = [self.upload_file(file_path) for file_path in self.knowledge_files]

            updated_assistant = self.client.beta.assistants.update(
                assistant_id,
                instructions=self.instructions,
                name=self.name,
                tools=[{"type": "retrieval"}] if file_ids else [],
                model=self.model,
                file_ids=file_ids
            )
            print("Assistant updated successfully:", updated_assistant)
        except Exception as e:
            print(f"Error in modifying assistant: {e}")
            raise

    def manage_assistant(self):
        """Manage the creation or modification of an assistant."""
        existing_id = self.assistant_exists(self.name)
        if existing_id:
            if self.auto_accept or input(f"An assistant named '{self.name}' exists. Modify it? (y/n): ").lower() in ['y', 'yes']:
                self.modify_assistant(existing_id)
                self.assistant_id = existing_id
            else:
                print("Please choose a new name for the assistant that doesn't conflict with an existing assistants name. These are your existing assistants:\n")
                self.list_assistants()
                return False
        else:
            self.assistant_id = self.create_assistant()
            print(f"Created a new assistant with ID: {self.assistant_id}")

            

    def list_assistants(self):
        """List all assistants."""
        try:
            assistants = self.client.beta.assistants.list()

            # print the names of the assistants
            for assistant in assistants.data:
                print(f"Assistant name: {assistant.name},                       Assistant ID: {assistant.id}")

            return assistants.data
        except OpenAIError as e:
            print(f"Error in listing assistants: {e}")
            raise

    def delete_assistants_by_name(self, names_to_delete):
        """Deletes assistants that have names specified in the names_to_delete list."""
        try:
            # List all assistants
            assistants = self.client.beta.assistants.list()

            for assistant in assistants.data:
                if assistant.name in names_to_delete:
                    self.client.beta.assistants.delete(assistant.id)
                    print(f"Deleted assistant: {assistant.name} (ID: {assistant.id})")

        except Exception as e:
            print(f"Error in deleting assistants: {e}")
            raise

    def list_files(self):
        """List all files."""
        try:
            files = self.client.files.list()
            file_details = []
            # Loop through and get the names of each file
            for file in files.data:
                file_id = file.id
                file_name = file.filename
                file_details.append((file_name, file_id))
                print(f"File name: {file_name}, File ID: {file_id}")
            return file_details
        except OpenAIError as e:
            print(f"Error in listing files: {e}")
            raise

    def delete_all_files(self):
        """Deletes all files uploaded for the assistant."""
        try:
            # List all files
            files = self.client.files.list()

            # Loop through each file and delete
            for file in files.data:
                file_id = file.id
                self.client.files.delete(file_id)
                print(f"Deleted file: {file_id}")

        except Exception as e:
            print(f"Error in deleting files: {e}")
            raise

    def upload_file(self, file_path):
        """Upload a file and return its ID, check if file exists and ask for replacement."""
        try:
            existing_files = self.list_files()
            file_name = file_path.split('/')[-1]

            for existing_file_name, existing_file_id in existing_files:
                if existing_file_name == file_name:
                    if self.auto_accept or input(f"A file named '{file_name}' already exists. Replace it? (y/n): ").lower() in ['y', 'yes']:
                        self.client.files.delete(existing_file_id)
                        print(f"Replaced file: {existing_file_name}")
                    else:
                        print(f"Using existing file: {existing_file_name}")
                        return existing_file_id

            file = self.client.files.create(
                file=open(file_path, "rb"),
                purpose="assistants",
            )
            return file.id
        except OpenAIError as e:
            print(f"Error in uploading file: {e}")
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


if __name__ == "__main__":
    # Example usage
    try:

        # name of the assistant
        assistant_name = "Document Helper"

        # instructions for the assistant
        assistant_instructions = "You are a helpful assistant who allows someone to interact with any attached knowledge. "

        # list of knowledge files to upload
        # knowledge_files = []
        knowledge_files = ["example_knowledge.txt"]

        # set to True to automatically accept assistant creation/modification
        auto_accept=False

        assistant = OpenAIAssistant(assistant_name, assistant_instructions, "gpt-4-1106-preview", knowledge_files=knowledge_files, auto_accept=auto_accept)

        if assistant.assistant_id is None:
            print("No assistant created, exiting.")
            exit()

        # ## deletes assistants with specific names if you have created duplicates. 
        # assistant.delete_assistants_by_name(["Document Helper", "Math Tutor"])
        
        # delete files 
        # assistant.delete_all_files()


        assistant.chat()
    except Exception as e:
        print(f"Failed to create assistant: {e}")

