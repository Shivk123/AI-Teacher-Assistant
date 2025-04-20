from googleapiclient.discovery import build

def create_quiz_form(creds, quiz_data):
    service = build('forms', 'v1', credentials=creds)

    if not quiz_data:
        raise ValueError("Quiz data is empty or invalid. Cannot create form.")

    # Step 1: Create an empty form
    new_form = service.forms().create(body={"info": {"title": "AI Generated Quiz"}}).execute()

    # Step 2: Prepare questions
    requests = []
    for item in quiz_data:
        if "question" in item and "options" in item:
            requests.append({
                "createItem": {
                    "item": {
                        "title": item["question"],
                        "questionItem": {
                            "question": {
                                "choiceQuestion": {
                                    "options": [{"value": opt} for opt in item["options"]],
                                    "type": "RADIO"
                                }
                            }
                        }
                    },
                    "location": {"index": 0}
                }
            })

    if not requests:
        raise ValueError("No valid questions found in quiz data.")

    # Step 3: Push questions to form
    service.forms().batchUpdate(formId=new_form['formId'], body={"requests": requests}).execute()

    return new_form['responderUri']
