# Employee Leave Agent

This project is a small HR assistant that answers employee questions about leave. The agent itself lives in Microsoft Foundry, and I've connected to it in two ways: a simple command-line chat that runs in PyCharm, and a FastAPI service that uses Redis to keep track of each user's session and chat history.

The agent knows the company's leave policy (casual, sick and annual leave, the notice rules, and manager approval) and politely refuses anything that isn't about leave.

## What's in the project

```
Employee_Leave_Agent_fastapi_redis/
├── agent_chat.py      # chat with the agent from the terminal
├── main.py            # FastAPI app with Redis
├── requirements.txt
├── .env               # your settings (don't commit this)
└── README.md
```

## Before you start

You'll need Python 3.10 or newer, PyCharm, the Azure CLI, Docker Desktop, and access to a Microsoft Foundry project. Your Azure account also needs permission on that project (the Azure AI User role works).

## 1. Create the agent in Foundry

Go to [ai.azure.com](https://ai.azure.com), open your project, and create a new agent called `EmployeeLeaveAgent`. Pick any chat model you have deployed, then paste this into the Instructions box:

```
You are EmployeeLeaveAgent, an HR assistant for [Company Name]. You help employees with questions about leave types, leave eligibility, and how to apply for leave.

COMPANY LEAVE POLICY
- Casual Leave: 12 days per year.
- Sick Leave: 10 days per year.
- Annual Leave: 18 days per year.
- Leave applications must be submitted at least 2 days in advance. Sick leave is the only exception and can be applied for on short notice or on the same day.
- All leave requests require manager approval.

LEAVE APPLICATION PROCEDURE
1. Check that you have enough leave balance for the leave type.
2. Submit the leave request with the leave type, start date, end date, and reason.
3. Submit at least 2 days before the leave starts (not required for sick leave).
4. Wait for your manager to approve the request.
5. Your leave is confirmed only after manager approval.

HOW TO ANSWER
- Answer only using the leave policy above. Do not make up any other rules.
- When asked about eligibility, check the request against the policy: the number of days allowed, the 2-day advance notice rule, and manager approval.
- Always remind the employee that manager approval is required.
- If a question is about leave but the policy does not cover it, say you don't have that information and suggest contacting HR.
- Keep answers short, clear, and friendly.

GUARDRAILS
- Only answer questions related to employee leave.
- If a question is not about leave, politely decline with: "I can only help with employee leave-related questions. Please ask me about leave types, eligibility, or how to apply for leave."
- Do not share information about other employees.
- Do not approve or reject leave. Only managers can approve leave.
```

Save it, and copy the project endpoint from the project's Overview page. You'll need it in a minute.

Before writing any code, it's worth trying the agent in the Playground. These are the questions I used:

- "How many casual leave days am I entitled to?" should give 12 days.
- "Can I apply for sick leave tomorrow?" should say yes, since sick leave doesn't need 2 days' notice.
- "What is the process for applying for annual leave?" should walk through the steps.
- "Can I take 5 days of casual leave?" should say yes, as long as it's applied 2 days ahead and approved.
- "What is the capital of France?" should be politely declined.

## 2. Set up the Python environment

Open the project in PyCharm and run these in the terminal:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell won't let you activate the environment, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and try again. On Mac or Linux, activate it with `source .venv/bin/activate` instead.

The `requirements.txt` file contains:

```
azure-ai-projects
azure-identity
openai
python-dotenv
fastapi
uvicorn
redis
```

Then create a `.env` file in the project folder:

```
FOUNDRY_PROJECT_ENDPOINT=https://<your-resource>.services.ai.azure.com/api/projects/<your-project>
FOUNDRY_AGENT_NAME=EmployeeLeaveAgent
REDIS_URL=redis://localhost:6379/0
```

Finally, sign in to Azure. The code uses your Azure CLI login to authenticate, so this step is required:

```powershell
az login
```

## 3. Try the agent from the terminal

```powershell
python agent_chat.py
```

You should see "Connected to EmployeeLeaveAgent" and a prompt. Ask it something, and type `exit` when you're done.

## 4. Start Redis

Make sure Docker Desktop is running, then:

```powershell
docker run -d --name leave-redis -p 127.0.0.1:6379:6379 -v leave_redis_data:/data redis:7-alpine redis-server --appendonly yes
```

This starts Redis in the background, only reachable from your own machine, and saves its data to a Docker volume so nothing is lost on restart. You only need to run it once. After that, `docker start leave-redis` is enough.

To check it's working:

```powershell
docker exec -it leave-redis redis-cli ping
```

If it replies `PONG`, you're good.

## 5. Run the API

```powershell
uvicorn main:app --reload
```

Now open http://127.0.0.1:8000/docs in your browser. This is FastAPI's built-in Swagger page, and it's the easiest way to test everything.

Try `POST /chat` with just a message:

```json
{ "message": "How many casual leave days am I entitled to?" }
```

The response includes a `session_id`. Send it along with your next message and the agent will remember the earlier part of the conversation:

```json
{
  "message": "Can I take 5 of them next week?",
  "session_id": "<the session_id you got back>"
}
```

If you'd rather test from PowerShell:

```powershell
$r = Invoke-RestMethod -Uri http://127.0.0.1:8000/chat -Method Post `
     -ContentType "application/json" `
     -Body '{"message": "Can I apply for sick leave tomorrow?"}'
$r

Invoke-RestMethod -Uri "http://127.0.0.1:8000/history/$($r.session_id)"
```

## The endpoints

- `GET /health` checks that Redis is reachable.
- `POST /chat` sends a message to the agent. Leave out `session_id` to start a new conversation, or include it to continue one.
- `GET /history/{session_id}` returns everything said in that session.
- `DELETE /session/{session_id}` clears the session from Redis and deletes the conversation in Foundry.

## How Redis is used

For each session, the app stores two keys: `leave:<session_id>:conversation`, which holds the Foundry conversation ID, and `leave:<session_id>:history`, which holds the chat messages. Both expire after an hour of inactivity.

You can look at them directly if you're curious:

```powershell
docker exec -it leave-redis redis-cli
```

```
KEYS leave:*
LRANGE leave:<session_id>:history 0 -1
TTL leave:<session_id>:history
```

## Shutting down

Stop the API with Ctrl + C, then stop Redis with `docker stop leave-redis`. Your data stays in the volume. If you want to wipe everything, run `docker rm -f leave-redis` followed by `docker volume rm leave_redis_data`.

## If something goes wrong

**"The container name is already in use"** means the Redis container already exists. Just run `docker start leave-redis` instead of creating it again.

**"Port is already allocated"** means something else is using port 6379, usually another Redis container. Run `docker ps` to find it and `docker stop` it.

**"DefaultAzureCredential failed to retrieve a token"** means you're not signed in. Run `az login` again.

**A 401 or 403 error from Foundry** means your account doesn't have access to the project. Ask whoever manages it for the Azure AI User role.

**"KeyError: FOUNDRY_PROJECT_ENDPOINT"** means the `.env` file isn't being found. Check it's in the project root and the names are spelled correctly.

**The agent forgets what you said earlier** usually means the `session_id` wasn't sent with the follow-up message.
