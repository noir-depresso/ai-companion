# #day 1
# import time

# from ollama import ResponseError, chat

# from config import MODEL_NAME, SYSTEM_PROMPT

# #a function that uses previous messages and returns a the LLM output
# def get_assistant_response(messages: list[dict[str, str]]) -> tuple[str, float]:
#     start_time = time.perf_counter()

#     response = chat(
#         model=MODEL_NAME,
#         messages=messages,
#         think=False,
#     )

#     elapsed_time = time.perf_counter() - start_time

#     return response.message.content, elapsed_time

# def main() -> None:
#     #sets up the original character card
#     messages: list[dict[str, str]] = [
#         {
#             "role": "system",
#             "content": SYSTEM_PROMPT,
#         }
#     ]

#     print(f"Running {MODEL_NAME}")
#     print("Type /exit to stop.\n")

#     #sets up the loop for conversatoin
#     while True:
#         #conditions to exit
#         try:
#             user_message = input("You: ").strip()
#         except (EOFError, KeyboardInterrupt):
#             print("\nGoodbye.")
#             break

#         if user_message.lower() == "/exit":
#             print("Goodbye.")
#             break

#         if not user_message:
#             print("Please enter a message.\n")
#             continue

#         #adds user input to the convsersation history
#         messages.append(
#             {
#                 "role": "user",
#                 "content": user_message,
#             }
#         )

#         #adds ai input to conversation history. but stops (and deletes the last user input) if error occurs
#         try:
#             assistant_message, elapsed_time = get_assistant_response(messages)
#         except ResponseError as error:
#             print(f"\nOllama error: {error}\n")
#             messages.pop()
#             continue
#         except ConnectionError:
#             print("\nCould not connect to Ollama.\n")
#             messages.pop()
#             continue

#         messages.append(
#             {
#                 "role": "assistant",
#                 "content": assistant_message,
#             }
#         )

#         print(f"\nRin: {assistant_message}\n")
#         print(f"[Response time: {elapsed_time:.2f} seconds]\n")

# #only runs main() if __name__ = "__main__" which is set only if this file is ran directly
# if __name__ == "__main__":
#     main()