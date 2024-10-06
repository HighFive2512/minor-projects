from difflib import get_close_matches

def get_closest_match(question:str, kb: str) -> str | None:
    questions: list[str] = [q for q in kb]
    matches: list[str] = get_close_matches(question, questions, n=1, cutoff=0.6)


    if matches:
        return matches[0]

def start_chatbot(knowledgebase:dict) -> None:
    while True:
        uinput:str = input('You: ')

        best_match: str | None = get_closest_match(uinput, knowledgebase)
        response: str | None = knowledgebase.get(best_match)

        if response:
            print(f'Bot : {response}')
        else:
            print(f'Bot : I do not understand...')

def main() -> None:
    brain: dict[str,str] = {'hello': 'Hey there!',
                            'how are you?': 'I am good, thanks!',
                            'what time is it?': 'no idea'}
    start_chatbot(knowledgebase=brain)
if __name__ == '__main__':
    main()

