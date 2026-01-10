from model import Model

from anthropic import Anthropic
from fastmcp import McpError
import asyncio
import logging


def mcp_tools_to_anthropic_tools(mcp_tools):
    return [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in mcp_tools]

class AnthropicModel(Model):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = None

    def init(self):
        self.anthropic = Anthropic(api_key=self.api_key)
        self.messages = []

    def init_tools(self, tools):
        super().init_tools(tools)
        self.available_tools = mcp_tools_to_anthropic_tools(tools)
    
    def set_system(self, system_prompt):
        super().set_system(system_prompt)
    
    async def create_message(self):
        super().create_message()
        tries = 0
        while tries < self.max_tries:
            try:
                tries += 1
                return self.anthropic.messages.create(
                    model=self.name,
                    max_tokens=self.max_tokens,
                    messages=self.messages,
                    tools=self.available_tools,
                    system=self.system
                )
            except Exception as e:
                if e.body["error"]["message"] == "Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.":
                    self.error_print(f"You have no Anthropic credits. Purchase more to continue; a new attempt will be made in {self.model.wait_seconds} seconds")
                elif e.body["error"]["message"] == "Overloaded":
                    self.error_print(f"Anthropic's server is overloaded; a new attempt will be made in {self.model.wait_seconds} seconds")
                elif e.body["error"]["message"].startswith("This request would exceed your organization's"):
                    self.error_print(f"You have exceeded the requests-per-minute limit; a new attempt will be made in {self.model.wait_seconds} seconds")
                else:
                    if e.body is not None and "error" in e.body and "message" in e.body["error"]:
                        self.error_print(f"{e.body['error']['message']}")
                    else:
                        self.error_print(f"{e}")
            await asyncio.sleep(self.model.wait_seconds)
        self.error_print("Maximum number of attempts reached, please try again later")
    
    async def process_query(self, query):
        """Process a query using Claude and the available tools"""
        await self._examine_query(query)

        tool_use_detected = True
        # Interaction loop with Claude
        while tool_use_detected:
            # Check if summarization is needed
            next_message = [{
                "role": "user",
                "content": query
            }]
            if self.check_summarize_needed(next_message):
                await self.summarize()
            # Request to Claude
            self.response = await self.create_message()

            response_content = list(self.response.content)
            assistant_parts = []

            tool_use_detected = False

            while response_content:
                content = response_content.pop(0)  # Take the first element of the response

                if content.type == 'text':  # Assistant normal text
                    self.assistant_print(content.text)
                    assistant_parts.append(content)

                elif content.type == 'tool_use':  # Tool use
                    tool_use_detected = True
                    tool_name = content.name
                    tool_args = content.input
                    tool_id = content.id

                    # Save assistant message (testo + tool_use)
                    self.messages.append({
                        "role": "assistant",
                        "content": assistant_parts + [content]
                    })

                    result = None
                    while result is None:
                        try:
                            # Call the tool
                            result = await self.client.call_tool(tool_name, tool_args)
                        except McpError as e:
                            self.error_print(f"Error while calling tool {tool_name}: {str(e)}, a new attempt will be made in {self.model.wait_seconds} seconds")
                            await asyncio.sleep(self.model.wait_seconds)

                    # Add the tool_result right after
                    self.messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": result.content
                            }
                        ]
                    })

            # If there are no tools to call, exit the loop
            if not tool_use_detected:
                # Save the assistant's response
                self.messages.append({
                    "role": "assistant",
                    "content": assistant_parts
                })
    
    async def summarize(self):
        logging.debug("Started summarization")
        history = [{"role":"system", "content": self.summarizer_system_prompt},{"role": "user", "content": f"{self.summarizer_user_prompt}{str(self.messages[1:-2])}"}]
        summarizer = self.anthropic.messages.create(
            model=self.name,
            max_tokens=self.summarizer_max_tokens,
            messages=history
        )
        summary = summarizer.content
        logging.debug(f"Summary produced:{summary}")
        new_messages = [
        {
            "role": "system",
            "content": self.system
        },
        {
            "role": "system",
            "content": summary
        }]
        new_messages.extend(self.messages[-2:])
        self.messages = new_messages
        logging.debug("Finished summarization")