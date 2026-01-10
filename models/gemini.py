from model import Model
from utils import normalize_args

from google import genai
from google.genai import types
import asyncio
import logging

def mcp_tools_to_gemini_tools(mcp_tools):
    """
    Convert the MCP tools obtained from list_tools() of a FastMCP client
    into the format required by Gemini (function_declarations).
    """
    function_declarations = []

    for t in mcp_tools:
        function_declarations.append({
            "name": t.name,
            "description": getattr(t, "description", "") or "",
            "parameters": getattr(t, "input_schema", {"type": "object", "properties": {}})
        })

    return [
        {
            "function_declarations": function_declarations
        }
    ]

class GeminiModel(Model):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def init(self):
        self.gemini = genai.client.Client(api_key=self.api_key)
        self.messages = [
            types.Content(
                role="user", parts=[types.Part(text=self.system)]
            )
        ]
    
    def init_tools(self, tools):
        super().init_tools(tools)
        self.available_tools = mcp_tools_to_gemini_tools(tools)
    
    def set_system(self, system_prompt):
        super().set_system(system_prompt)
        self.messages[0] = types.Content(
            role="user", parts=[types.Part(text=system_prompt)]
        )
    
    async def create_message(self):
        super().create_message()
        tries = 0
        while tries < self.max_tries:
            try:
                tries += 1

                response = await self.gemini.aio.models.generate_content(
                    model = self.name,
                    contents = self.messages,
                    config=types.GenerateContentConfig(
                        temperature=self.temperature,
                        max_output_tokens=self.max_tokens,
                        tools=[self.client.session],
                    )
                )

                return response

            except Exception as e:
                self.error_print(str(e))

            await asyncio.sleep(self.wait_seconds)

        self.error_print("Maximum number of attempts reached, please try again later")
    
    def get_role_message(self, role, content):
        return types.Content(role=role, parts=[types.Part(text=content)])
    
    async def process_query(self, query):
        """Process a query using a model and the available tools"""
        await self._examine_query(query)

        tool_use_detected = True
        # Interaction loop with the model
        while tool_use_detected:
            # Check if a summary is needed
            next_message = [{
                "role": "user",
                "content": query
            }]
            if self.check_summarize_needed(next_message):
                await self.summarize()
            # Request to the model
            self.response = await self.create_message()

            candidate = self.response.candidates[0]
            finish = candidate.finish_reason

            tool_use_detected = False

            if finish == "STOP":
                # The answer is complete; there are no tools to call
                text = candidate.content.parts[0].text
                self.messages.append(types.Content(
                    role="model", parts=[types.Part(text=text)]
                ))
                self.assistant_print(text)
            elif finish == "CALL_FUNCTION":
                tool_use_detected = True

                calls = []
                for part in candidate.content:
                    if hasattr(part, "function_call") and part.function_call:
                        calls.append(part.function_call)
                
                # Add a part for the model's intent anyway
                self.messages.append(types.Content(
                    role="model", parts=[types.Part(text=candidate.text or "")]
                ))


                # Process each tool call
                for fc in calls:
                    tool_name = fc.name
                    tool_args = normalize_args(fc.args)

                    # Call FastMCP
                    result = await self.client.call_tool(tool_name, tool_args)
                    tool_output = result.content[0].text

                    # Append the result as simple context for Gemini
                    self.messages.append(types.Content(
                        role="user", parts=[types.Part(text=tool_output)]
                    ))

    async def summarize(self):
        logging.debug("Started summarization")
        history = [
            types.Content(
                role="system", parts=[types.Part(text=self.model.summarizer_system_prompt)]
            ),
            types.Content(
                role="user", parts=[types.Part(text=f"{self.model.summarizer_user_prompt}{str(self.messages[1:-2])}")]
            )
        ]
        summarizer = await self.gemini.aio.models.generate_content(
            model=self.model.name,
            contents=history,
            config=types.GenerateContentConfig(
                max_output_tokens=self.model.summarizer_max_tokens,
                temperature=self.model.summarizer_temperature
            )
        )
        summary = summarizer.candidates[0].parts[0].text
        logging.debug(f"Summary produced:{summary}")
        new_messages = [
            types.Content(
                role="user", parts=[types.Part(text=self.system)]
            ),
            types.Content(
                role="system", parts=[types.Part(text=summary)]
            )
        ]
        new_messages.extend(self.messages[-2:])
        self.messages = new_messages
        logging.debug("Finished summarization")
    
    def get_messages(self):
        for msg in self.messages:
            if isinstance(msg, dict):
                yield types.Content(
                    role=msg["role"],
                    content=[types.Part(text=msg["content"])]
                )
            else:
                yield msg
    
    def set_messages(self, messages):
        self.messages = [
            types.Content(
                role="user", parts=[types.Part(text=self.system)]
            )
        ]
        for message in messages:
            self.messages.append(
                types.Content(
                    role=message["role"],
                    parts=[types.Part(text=message["content"])]
                )
            )