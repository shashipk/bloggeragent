# ADK Blogger Agent & Chat UI Codelab Guide

This project implements a **Deliberative/Planning Multi-Agent Blog-Writing System** using Google's **Agent Development Kit (ADK)** and Gemini in Python. It features two user interfaces:
1. **Standard ADK Web UI**: The official built-in graph UI that shows the execution traces of loops and agents.
2. **Premium Custom Chat UI**: A custom-designed, glassmorphic dark-mode web interface with real-time Server-Sent Events (SSE) streaming, Markdown rendering, syntax highlighting, and visual indicators tracking which sub-agent is currently executing.

---

## 1. Architecture Overview

Unlike a basic single-prompt LLM, this system utilizes a **deliberative planning loop** that mimics how human writers work:

```mermaid
graph TD
    User([User Prompt]) --> Coordinator[Blogger Coordinator Agent]
    Coordinator -->|Calls Planner Tool| PlannerLoop[Robust Blog Planner Loop]
    subgraph PlannerLoop [Robust Blog Planner Loop]
        Planner[BlogPlanner] -->|Generates Outline| OutlineChecker[OutlineValidationChecker]
        OutlineChecker -->|Validation Fails| Planner
        OutlineChecker -->|Validation Succeeds 'ok'| PlannerDone[Validated Outline]
    end
    PlannerDone --> Coordinator
    Coordinator -->|Calls Writer Tool| WriterLoop[Robust Blog Writer Loop]
    subgraph WriterLoop [Robust Blog Writer Loop]
        Writer[BlogWriter] -->|Drafts Article| PostChecker[BlogPostValidationChecker]
        PostChecker -->|Validation Fails| Writer
        PostChecker -->|Validation Succeeds 'ok'| WriterDone[Validated Article]
    end
    WriterDone --> Coordinator
    Coordinator -->|Generates Titles & Tweets| FinalOutput[Final Output to User]
```

- **Blogger (Coordinator)**: Receives the topic, dispatches the planning phase, passes the outline to the writing phase, and appends alternate titles and social media hooks.
- **BlogPlanner**: Generates a structured Markdown outline.
- **OutlineValidationChecker**: Ensures the outline meets structural parameters (title, intro, 4-6 sections, conclusion).
- **RobustBlogPlanner**: A `LoopAgent` that runs validation and retries outline planning up to 3 times on failure.
- **BlogWriter**: Produces the technical blog post in Markdown based on the outline.
- **BlogPostValidationChecker**: Reviews the post structure and technical clarity.
- **RobustBlogWriter**: A `LoopAgent` that retries writing up to 3 times on failure.

---

## 2. User Interfaces & Code Flow

This project implements two different ways to interface with the ADK Blogger Agent. Below is a detailed look at how they work and the corresponding code flows.

### Option A: Standard ADK Web UI
The Standard Web UI is provided out-of-the-box by the `google-adk` framework.
* **How it runs**: When you run `adk web` in your terminal, the ADK CLI starts its built-in FastAPI web server. It scans the current directory, finds the `root_agent` exposed in your package, and mounts it.
* **Flow**:
  1. The pre-built React/TypeScript frontend asks the server for the agent's definition.
  2. The UI renders the agent's hierarchical graph structure showing the connection between `Blogger`, `RobustBlogPlanner`, and `RobustBlogWriter`.
  3. During execution, it streams the full system execution logs and tool outputs, showing you exactly when checkers validate or trigger retries.

### Option B: Premium Custom Chat UI
The Premium Custom Chat UI uses a custom FastAPI backend (`main.py`) to stream events directly to a custom HTML/CSS/JS frontend (`static/index.html`) using **Server-Sent Events (SSE)**.

```mermaid
sequenceDiagram
    participant Browser as Custom Frontend (index.html)
    participant Server as FastAPI Backend (main.py)
    participant Runner as ADK InMemoryRunner
    participant Agent as ADK agent.py

    Browser->>Server: POST /api/chat {message: "..."}
    Note over Server: Creates InMemoryRunner(agent=root_agent)
    Server->>Runner: runner.run_async(new_message)
    
    loop Stream Agent Events
        Runner->>Agent: Execute step (e.g., BlogPlanner outlines)
        Agent-->>Runner: Yield Event
        Runner-->>Server: Yield Event
        Note over Server: Extract event text, author & status
        Server-->>Browser: Stream SSE "data: {JSON}\n\n"
        Note over Browser: JavaScript parses event<br/>1. Lights up active sub-agent in sidebar<br/>2. Appends text & renders Markdown (marked.js)
    end
    
    Server-->>Browser: Close Connection (Stream complete)
```

#### 1. Backend Event Streaming (`main.py`)
In `main.py`, we instantiate the ADK `InMemoryRunner` for our agent:
```python
runner = InMemoryRunner(agent=root_agent)
runner.auto_create_session = True
```
When `/api/chat` is hit, it starts `runner.run_async()` asynchronously. As the multi-agent system runs, the runner yields `Event` objects representing text output chunks and transitions. We serialize these events and stream them to the browser:
```python
async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=user_msg):
    data = {
        "author": event.author,      # Active agent name (e.g., "BlogPlanner", "BlogWriter")
        "text": text_content,        # Streamed text tokens
        "output": event.output,      # Final agent output payload
        "node_path": event.node_info.path if event.node_info else None
    }
    yield f"data: {json.dumps(data)}\n\n"
```

#### 2. Frontend Real-Time Client (`static/index.html`)
The frontend uses JavaScript to parse this real-time stream:
* **Streaming Consumer**: The browser uses `fetch()` and consumes the response stream using `response.body.getReader()`. It reads and decodes the stream chunk-by-chunk.
* **Sub-Agent Tracking**: When a chunk arrives with a new `data.author`, the script automatically selects the corresponding step in the sidebar (e.g. `step-BlogPlanner`, `step-BlogWriter`) and marks it `.active` (making it glow purple) or `.done` (making it green).
* **Live Markdown Rendering**: It appends new tokens to a cumulative text buffer and runs it through `marked.parse(fullText)` to generate HTML on the fly. It then triggers `Prism.highlightAllUnder(...)` to highlight python or bash code blocks in the article.

---

## 3. Local Setup & Installation

### Prerequisites
- Python 3.10 or higher.
- A Google AI Studio API Key. Get one at [Google AI Studio](https://aistudio.google.com/app/api-keys).

### Steps
1. **Clone or navigate to the directory**:
   ```bash
   cd bloggeragent
   ```

2. **Create and activate a Python virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Credentials**:
   Open the `.env` file in the root of the project and add your API key:
   ```env
   GOOGLE_API_KEY=your_gemini_api_key_here
   MODEL=gemini-3.5-flash
   ```

---

## 4. Running Locally

### Option A: Standard ADK Web UI
This runs the official ADK interactive web console.
```bash
adk web
```
- Open your browser to `http://127.0.0.1:8000` (if port 8000 is taken, use `adk web --port 8001`).
- Enter a topic like `How to build an AI agent using planning loops` and observe the visual execution graph showing the sub-agents and checkers running.

### Option B: Premium Custom Chat UI (Recommended)
This runs the custom-built glassmorphic web app with real-time SSE streaming.
```bash
python main.py
```
- Open your browser to `http://localhost:8080` (or the port shown in your terminal).
- Enter a topic and watch as the sidebar steps light up, showing which specialist agent (Planner, Checker, Writer) is active in real-time as text streams onto the page.

---

## 5. Deploying to Google Cloud Run

To deploy your agent to Google Cloud, you need a Google Cloud Project with billing enabled.

### 1. Install Google Cloud CLI (gcloud)

If you do not have the Google Cloud CLI (`gcloud`) installed on your machine, select one of the options below:

* **Option A: Using Homebrew (macOS)**
  ```bash
  brew install --cask google-cloud-sdk
  ```
  *(Restart your terminal session after installation)*

* **Option B: Using the Interactive Installer Script (macOS/Linux)**
  ```bash
  curl https://sdk.cloud.google.com | bash
  exec -l $SHELL
  gcloud init
  ```

* **Option C: Windows**
  Download and run the official [Google Cloud CLI Installer](https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe).

### 2. Authenticate with Google Cloud CLI
Once installed, log in to your Google Cloud account in your terminal:
```bash
gcloud auth login
gcloud auth list
```

### 3. Configure Your Cloud Project
Set your active project ID:
```bash
gcloud config set project <YOUR_PROJECT_ID>
```
Enable the required Cloud APIs:
```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com
```

### 4. Grant Permissions
Retrieve your project number:
```bash
gcloud projects describe <YOUR_PROJECT_ID> --format="value(projectNumber)"
```
Grant the Cloud Build builder role to the default compute service account:
```bash
gcloud projects add-iam-policy-binding <YOUR_PROJECT_ID> \
  --member="serviceAccount:<PROJECT_NUMBER>-compute@developer.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.builder"
```
Grant Vertex AI User permissions to the service account (allowing the Cloud Run instance to invoke Gemini without requiring an API key):
```bash
gcloud projects add-iam-policy-binding <YOUR_PROJECT_ID> \
  --member="serviceAccount:<PROJECT_NUMBER>-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

### 5. Deploying

> [!IMPORTANT]
> **Working Directory**: All deployment commands (`adk deploy` and `gcloud run deploy`) **MUST** be run from the root of the **`bloggeragent/`** directory. If you are in the workspace root, change directory first:
> ```bash
> cd bloggeragent
> ```

---

#### Understanding the Environment Tags (`--set-env-vars`)
When deploying services to Google Cloud Run, we pass custom environment variables to configure how the agent authenticates and communicates with Gemini models:
* `GOOGLE_GENAI_USE_VERTEXAI`: Set this to `TRUE` to tell the ADK SDK to run on Google Cloud Vertex AI infrastructure. This leverages the Cloud Run service account permissions automatically (meaning you do not need to expose your private API Key in the cloud configuration). Set it to `FALSE` if using the AI Studio Free Tier.
* `MODEL`: Specifies the Gemini model to invoke. We recommend `gemini-3.5-flash` or `gemini-1.5-pro` (the reasoning model).
* `GOOGLE_CLOUD_LOCATION`: Specifies the geographical location for Vertex AI API operations (e.g. `global` or `us-east1`).
* `GOOGLE_API_KEY`: *(Optional)* If Vertex AI is set to `FALSE` (billing-free option), pass your Google AI Studio API Key using this environment variable.

---

#### Option A: Deploy the Built-in ADK Web UI
Deploy the standard ADK container, which runs the default visual graph interface:

1. **Verify your active directory** is `bloggeragent/`:
   ```bash
   pwd
   # Should output: .../bloggeragent
   ```
2. **Execute the deployment command**:
   ```bash
   export PROJECT_ID="<YOUR_PROJECT_ID>"

   adk deploy cloud_run \
     --project=$PROJECT_ID \
     --region=us-east1 \
     --service_name=bloggeragent \
     --with_ui \
     . \
     -- \
     --set-env-vars GOOGLE_GENAI_USE_VERTEXAI=TRUE,MODEL=gemini-3.5-flash,GOOGLE_CLOUD_LOCATION=global
   ```
3. **Confirm deployment settings**:
   - When asked to create an Artifact Registry repository `cloud-run-source-deploy`, type `Y` and press **Enter**.
   - When asked to allow unauthenticated invocations to `bloggeragent`, type `y` and press **Enter** (this allows you to access the web URL publicly).
4. **Access the UI**: Once complete, copy the output URL to open the built-in graph UI in your browser.

---

#### Option B: Deploy the Custom Chat UI (Recommended)
Build and deploy the custom glassmorphic FastAPI interface using the provided `Dockerfile`:

1. **Verify your active directory** is `bloggeragent/`:
   ```bash
   pwd
   # Should output: .../bloggeragent
   ```
2. **Execute the gcloud run command**:
   ```bash
   gcloud run deploy bloggeragent-custom \
     --source . \
     --region=us-east1 \
     --allow-unauthenticated \
     --set-env-vars GOOGLE_GENAI_USE_VERTEXAI=TRUE,MODEL=gemini-3.5-flash,GOOGLE_CLOUD_LOCATION=global
   ```
   *(Note: The `--source .` flag compiles the project from your current directory, building it using the `Dockerfile`).*
3. **Access the Custom UI**: Once successful, open the resulting service URL to view your premium Glassmorphic Blogger Chat Interface!

---

## 6. Clean Up

To prevent ongoing charges, delete the deployed Cloud Run services and Artifact Registry repositories from your Google Cloud Console or terminal:

```bash
# Delete the custom UI service
gcloud run services delete bloggeragent-custom --region=us-east1 --quiet

# Delete the standard ADK service
gcloud run services delete bloggeragent --region=us-east1 --quiet

# Delete the built Artifact Registry repository
gcloud artifacts repositories delete cloud-run-source-deploy --location=us-east1 --quiet
```

---

## 7. Redeploying After Clean Up

If you have performed the clean-up steps and want to deploy the agent again in the future, you do not need to rewrite any code. Since all files remain saved locally on your machine, you can redeploy by following these steps:

1. **Open your terminal** and navigate to your local `bloggeragent/` directory:
   ```bash
   cd bloggeragent
   ```
2. **Re-authenticate and configure** your Google Cloud project (if you are in a new terminal session or active account session has expired):
   ```bash
   gcloud auth login
   gcloud config set project <YOUR_PROJECT_ID>
   ```
3. **Execute the deployment command** for whichever UI option you prefer:
   * **For the Custom Chat UI**:
     ```bash
     gcloud run deploy bloggeragent-custom \
       --source . \
       --region=us-east1 \
       --allow-unauthenticated \
       --set-env-vars GOOGLE_GENAI_USE_VERTEXAI=TRUE,MODEL=gemini-3.5-flash,GOOGLE_CLOUD_LOCATION=global
     ```
   * **For the Built-in ADK UI**:
     ```bash
     export PROJECT_ID="<YOUR_PROJECT_ID>"
     adk deploy cloud_run \
       --project=$PROJECT_ID \
       --region=us-east1 \
       --service_name=bloggeragent \
       --with_ui \
       . \
       -- \
       --set-env-vars GOOGLE_GENAI_USE_VERTEXAI=TRUE,MODEL=gemini-3.5-flash,GOOGLE_CLOUD_LOCATION=global
     ```
     *(Type `Y` to recreate the Artifact Registry repository and `y` to allow unauthenticated access when prompted)*

Google Cloud will automatically recreate the registry repository, compile a new container from your local files, spin up a new Cloud Run instance, and output a new service URL!
