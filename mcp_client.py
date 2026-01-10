from fastmcp import Client
from fastmcp.client.logging import LogMessage

class MCPClient:
    def __init__(self, model):
        self.client = None
        self.model = model
        self.assistant_print = model.assistant_print
        self.system_print = model.system_print
        self.error_print = model.error_print


    def get_client(self):
        if self.client==None:
            async def _log_handler(msg: LogMessage):
                if msg.level == "error":
                    self.error_print(msg.data.get("msg"))
                else:
                    self.system_print(msg.data.get("msg"))  
            self.client = Client(self.model.url, log_handler=_log_handler)
            self.model.client = self.client
        return self.client

    async def init(self):
        tools = await self.get_client().list_tools()
        self.system_print("Available tools: " + ", ".join([tool.name for tool in tools]))
        prompts = await self.get_client().list_prompts()
        self.system_print("Available prompts: " + ", ".join([prompt.name for prompt in prompts]))

        self.model.init_tools(tools)

        self.available_prompts = [{
            "name": prompt.name,
            "description": prompt.description
        } for prompt in prompts]

        if len(self.available_prompts)!=0:
            prompts = "\n".join([f"/{prompt['name']} - {prompt['description']}" for prompt in self.available_prompts])
            self.model.set_system(self.model.system + "\nThe following commands are available: " + prompts)

    async def process_query(self, query):
        await self.model.process_query(query)