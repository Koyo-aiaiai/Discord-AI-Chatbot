# Logic for Communication Between Components

This repository uses an eventbus structure to communicate between different components. Each component has a queue which gets content put in it on a certain event. Each service also publishes whatever their output data object is to the eventbus. Each service publishes and has a queue which is subscribed to the eventbus. When it detects message from event relating to the proper queue, the service triggers the stuff in the business logic layer.

## Dataflow Example

User -Discord Adapter-> Discord -UserMessage-> Behaviour -LLMInputMessage-> LLM -AIMessage-> Discord -DiscordAdapter-> User  

We have behaviour before LLM cuz this way the LLM can take into consideration of long it has been since the last response.
