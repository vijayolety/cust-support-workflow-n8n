"""Generates the importable n8n workflow JSON files from workflow/src/*.js.

Run: python workflow/tools/build.py
"""
import json
import os
import uuid

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
OUT = os.path.join(ROOT, "workflows")
os.makedirs(OUT, exist_ok=True)

VERSION = "v1.0"
CRED_GMAIL = {"gmailOAuth2": {"id": "REPLACE_ME", "name": "Gmail account (support mailbox)"}}
CRED_OPENAI = {"openAiApi": {"id": "REPLACE_ME", "name": "OpenAI account"}}
CRED_PINECONE = {"httpHeaderAuth": {"id": "REPLACE_ME", "name": "Pinecone API Key (Header Auth: Api-Key)"}}


def uid(seed):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "l180-support-" + seed))


def code(name):
    with open(os.path.join(SRC, name), encoding="utf-8") as f:
        return f.read()


nodes = []


def add(name, type_, params, pos, version=1, creds=None, **extra):
    n = {
        "parameters": params,
        "id": uid(name),
        "name": name,
        "type": type_,
        "typeVersion": version,
        "position": list(pos),
    }
    if creds:
        n["credentials"] = creds
    n.update(extra)
    nodes.append(n)
    return n


def code_node(name, file, pos, **extra):
    return add(name, "n8n-nodes-base.code", {"mode": "runOnceForAllItems", "jsCode": code(file)}, pos, 2, **extra)


def sticky(name, content, pos, w, h, color=4):
    add(name, "n8n-nodes-base.stickyNote", {"content": content, "height": h, "width": w, "color": color}, pos, 1)


def cond_bool(left, want_true):
    return {
        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
        "conditions": [{
            "id": uid("cond-" + left + str(want_true)),
            "leftValue": left,
            "rightValue": "",
            "operator": {"type": "boolean", "operation": "true" if want_true else "false", "singleValue": True},
        }],
        "combinator": "and",
    }


def if_node(name, left, want_true, pos):
    return add(name, "n8n-nodes-base.if", {"conditions": cond_bool(left, want_true), "options": {}}, pos, 2.2)


def cfg_assign(name, value, type_="string"):
    return {"id": uid("cfg-" + name), "name": name, "value": value, "type": type_}


def http_openai(name, url, body_expr, pos):
    return add(
        name, "n8n-nodes-base.httpRequest",
        {
            "method": "POST",
            "url": url,
            "authentication": "predefinedCredentialType",
            "nodeCredentialType": "openAiApi",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": body_expr,
            "options": {"timeout": 60000},
        },
        pos, 4.2, creds=CRED_OPENAI,
        retryOnFail=True, maxTries=3, waitBetweenTries=3000, onError="continueErrorOutput",
    )


# ---------------------------------------------------------------- layout
X = 240
Y0 = 300
YS = 220

# 01 Gmail Trigger
add(
    "01 - Gmail Trigger", "n8n-nodes-base.gmailTrigger",
    {
        "pollTimes": {"item": [{"mode": "everyMinute"}]},
        "simple": False,
        "filters": {"q": "in:inbox -from:me"},
        "options": {"downloadAttachments": False},
    },
    (0, Y0), 1.2, creds=CRED_GMAIL,
)

# 00 Config (all business thresholds / client-specific values in ONE place)
config_values = [
    cfg_assign("workflowVersion", VERSION),
    cfg_assign("mailbox", "support@example.com"),
    cfg_assign("classifierModel", "gpt-4o-mini"),
    cfg_assign("generationModel", "gpt-4o"),
    cfg_assign("embeddingModel", "text-embedding-3-small"),
    cfg_assign("confidenceThreshold", 0.8, "number"),
    cfg_assign("topK", 5, "number"),
    cfg_assign("minScore", 0.5, "number"),
    cfg_assign("pineconeIndexHost", "https://REPLACE-INDEX-HOST.svc.REPLACE-REGION.pinecone.io"),
    cfg_assign("pineconeNamespace", ""),
    cfg_assign("metadataTextField", "text"),
    cfg_assign("maxThreadMessages", 5, "number"),
    cfg_assign("maxResponseChars", 2500, "number"),
    cfg_assign("signature", "Customer Support Team"),
    cfg_assign("sensitiveIntents", "legal,refund,payment_dispute,security_incident,account_deletion"),
    cfg_assign("nonSupportAction", "label"),
    cfg_assign("nonSupportLabelId", "REPLACE_WITH_GMAIL_LABEL_ID_NON_SUPPORT"),
    cfg_assign("escalationLabelId", "REPLACE_WITH_GMAIL_LABEL_ID_ESCALATION"),
    cfg_assign("escalationEmail", "support-escalations@example.com"),
]
add("00 - Config", "n8n-nodes-base.set",
    {"assignments": {"assignments": config_values}, "includeOtherFields": True, "options": {}},
    (X, Y0), 3.4)

code_node("02 - Normalize Email", "02_normalize.js", (X * 2, Y0))

add("03 - Get Thread Context", "n8n-nodes-base.gmail",
    {"resource": "thread", "operation": "get", "threadId": "={{ $json.threadId }}", "simple": True, "options": {}},
    (X * 3, Y0), 2.1, creds=CRED_GMAIL, onError="continueRegularOutput", alwaysOutputData=True)

code_node("03b - Build Thread Context", "03b_thread_context.js", (X * 4, Y0))
code_node("04 - Idempotency Check", "04_idempotency_check.js", (X * 5, Y0))
code_node("05 - Mark Processing", "05_mark_processing.js", (X * 6, Y0))
if_node("05b - Proceed?", "={{ $json.duplicate }}", False, (X * 7, Y0))
code_node("05c - Build Classifier Prompt", "05c_build_classifier_prompt.js", (X * 8, Y0))

http_openai("06 - Classify Email", "https://api.openai.com/v1/chat/completions",
            "={{ JSON.stringify($json.classifierRequest) }}", (X * 9, Y0))
code_node("06b - Parse Classification", "06b_parse_classification.js", (X * 10, Y0))

# 07 Route (3-way)
def switch_rule(value):
    return {
        "conditions": {
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
            "conditions": [{
                "id": uid("route-" + value),
                "leftValue": "={{ $json.route }}",
                "rightValue": value,
                "operator": {"type": "string", "operation": "equals"},
            }],
            "combinator": "and",
        },
        "renameOutput": True,
        "outputKey": value,
    }


add("07 - Route Support?", "n8n-nodes-base.switch",
    {"rules": {"values": [switch_rule("support"), switch_rule("non_support"), switch_rule("escalate")]}, "options": {}},
    (X * 11, Y0), 3.2)

# Support path
Y1 = Y0 - YS
http_openai("08 - Create Query Embedding", "https://api.openai.com/v1/embeddings",
            "={{ JSON.stringify({ model: $('00 - Config').first().json.embeddingModel, input: $json.retrievalQuery }) }}",
            (X * 12, Y1))

add("09 - Pinecone Search", "n8n-nodes-base.httpRequest",
    {
        "method": "POST",
        "url": "={{ $('00 - Config').first().json.pineconeIndexHost.replace(/\\/$/, '') + '/query' }}",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "sendHeaders": True,
        "headerParameters": {"parameters": [{"name": "X-Pinecone-Api-Version", "value": "2024-07"}]},
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ vector: $json.data[0].embedding, topK: $('00 - Config').first().json.topK, namespace: $('00 - Config').first().json.pineconeNamespace, includeMetadata: true, includeValues: false }) }}",
        "options": {"timeout": 30000},
    },
    (X * 13, Y1), 4.2, creds=CRED_PINECONE,
    retryOnFail=True, maxTries=3, waitBetweenTries=3000, onError="continueErrorOutput")

code_node("10 - Retrieval Guard", "10_retrieval_guard.js", (X * 14, Y1))
if_node("10b - Grounded?", "={{ $json.grounded }}", True, (X * 15, Y1))
code_node("10c - Build Generation Prompt", "10c_build_generation_prompt.js", (X * 16, Y1))
http_openai("11 - Generate Response", "https://api.openai.com/v1/chat/completions",
            "={{ JSON.stringify($json.generationRequest) }}", (X * 17, Y1))
code_node("12 - Response Validation", "12_response_validation.js", (X * 18, Y1))
if_node("12b - Response Approved?", "={{ $json.validation.passed }}", True, (X * 19, Y1))

# Reply: no retries (a blind repeat could double-send); failure escalates.
add("13 - Gmail Reply", "n8n-nodes-base.gmail",
    {
        "resource": "message",
        "operation": "reply",
        "messageId": "={{ $json.messageId }}",
        "emailType": "text",
        "message": "={{ $json.replyText }}",
        "options": {"appendAttribution": False},
    },
    (X * 20, Y1), 2.1, creds=CRED_GMAIL, retryOnFail=False, onError="continueErrorOutput")

# Non-support path
Y2 = Y0 + YS
add("07b - Apply Non-Support Label", "n8n-nodes-base.gmail",
    {
        "resource": "message",
        "operation": "addLabels",
        "messageId": "={{ $json.messageId }}",
        "labelIds": "={{ [$('00 - Config').first().json.nonSupportLabelId] }}",
    },
    (X * 12, Y2), 2.1, creds=CRED_GMAIL, onError="continueRegularOutput")

# Escalation convergence
Y3 = Y0 + YS * 2
code_node("14 - Human Escalation", "14_human_escalation.js", (X * 14, Y3))
add("14b - Apply Escalation Label", "n8n-nodes-base.gmail",
    {
        "resource": "message",
        "operation": "addLabels",
        "messageId": "={{ $json.messageId }}",
        "labelIds": "={{ [$json.escalationLabelId] }}",
    },
    (X * 15, Y3), 2.1, creds=CRED_GMAIL, onError="continueRegularOutput")
add("14c - Notify Human", "n8n-nodes-base.gmail",
    {
        "resource": "message",
        "operation": "send",
        "sendTo": "={{ $('14 - Human Escalation').first().json.escalationEmail }}",
        "subject": "={{ $('14 - Human Escalation').first().json.notifySubject }}",
        "emailType": "text",
        "message": "={{ $('14 - Human Escalation').first().json.notifyBody }}",
        "options": {"appendAttribution": False},
    },
    (X * 16, Y3), 2.1, creds=CRED_GMAIL, onError="continueRegularOutput")

# Completion + audit
code_node("15 - Mark Complete", "15_mark_complete.js", (X * 21, Y0))
code_node("16 - Audit Metadata", "16_audit_metadata.js", (X * 22, Y0))

# Sticky notes
sticky("Note - Overview",
       "## AI Customer Support Email Automation " + VERSION + "\nGmail -> normalize -> dedupe -> classify -> RAG (Pinecone) -> generate -> validate -> threaded reply OR human escalation -> audit.\n\n**Fail closed:** any uncertainty escalates; no automated reply is sent.\n\nSee docs/setup-guide.md.",
       (-40, -160), 700, 240)
sticky("Note - Credentials",
       "## Credentials (n8n credential store only)\n- Gmail OAuth2 (scopes: gmail.readonly + gmail.modify + gmail.send; gmail.compose optional)\n- OpenAI API (openAiApi)\n- Pinecone: Header Auth credential, header name `Api-Key`\n\nNever paste keys into nodes, prompts or Code.",
       (X * 5 - 40, -160), 640, 240)
sticky("Note - Configuration",
       "## 00 - Config is the ONLY place for thresholds and client values\nOPEN DECISIONS (confirm before go-live): mailbox + trigger criteria, non-support action, escalation destination, Pinecone namespace/metadata schema, thread depth, production models + cost ceiling.\nDefaults: non-support = label only (no reply); escalation = label + Gmail notification.",
       (X - 40, Y0 + 120), 640, 240)
sticky("Note - Retries",
       "## Retry policy\nOpenAI + Pinecone HTTP nodes: 3 tries, 3s wait, then the error output routes to 14 - Human Escalation.\nGmail Reply: NO retry (could double-send); failure escalates.\nIdempotency state lives in workflow static data (active executions only).",
       (X * 9 - 40, -160), 640, 220)

# ---------------------------------------------------------------- connections
conns = {}


def link(a, b, out=0, dst_idx=0):
    outs = conns.setdefault(a, {"main": []})["main"]
    while len(outs) <= out:
        outs.append([])
    outs[out].append({"node": b, "type": "main", "index": dst_idx})


chain = [
    "01 - Gmail Trigger", "00 - Config", "02 - Normalize Email", "03 - Get Thread Context",
    "03b - Build Thread Context", "04 - Idempotency Check", "05 - Mark Processing", "05b - Proceed?",
]
for a, b in zip(chain, chain[1:]):
    link(a, b)
link("05b - Proceed?", "05c - Build Classifier Prompt", 0)   # true output of "duplicate == false"
link("05c - Build Classifier Prompt", "06 - Classify Email")
link("06 - Classify Email", "06b - Parse Classification", 0)
link("06 - Classify Email", "14 - Human Escalation", 1)       # error output
link("06b - Parse Classification", "07 - Route Support?")
link("07 - Route Support?", "08 - Create Query Embedding", 0)
link("07 - Route Support?", "07b - Apply Non-Support Label", 1)
link("07 - Route Support?", "14 - Human Escalation", 2)
link("07b - Apply Non-Support Label", "15 - Mark Complete")
link("08 - Create Query Embedding", "09 - Pinecone Search", 0)
link("08 - Create Query Embedding", "14 - Human Escalation", 1)
link("09 - Pinecone Search", "10 - Retrieval Guard", 0)
link("09 - Pinecone Search", "14 - Human Escalation", 1)
link("10 - Retrieval Guard", "10b - Grounded?")
link("10b - Grounded?", "10c - Build Generation Prompt", 0)
link("10b - Grounded?", "14 - Human Escalation", 1)
link("10c - Build Generation Prompt", "11 - Generate Response")
link("11 - Generate Response", "12 - Response Validation", 0)
link("11 - Generate Response", "14 - Human Escalation", 1)
link("12 - Response Validation", "12b - Response Approved?")
link("12b - Response Approved?", "13 - Gmail Reply", 0)
link("12b - Response Approved?", "14 - Human Escalation", 1)
link("13 - Gmail Reply", "15 - Mark Complete", 0)
link("13 - Gmail Reply", "14 - Human Escalation", 1)
link("14 - Human Escalation", "14b - Apply Escalation Label")
link("14b - Apply Escalation Label", "14c - Notify Human")
link("14c - Notify Human", "15 - Mark Complete")
link("15 - Mark Complete", "16 - Audit Metadata")

main = {
    "name": "AI Customer Support Email Automation " + VERSION,
    "nodes": nodes,
    "connections": conns,
    "active": False,
    "settings": {
        "executionOrder": "v1",
        "saveDataSuccessExecution": "none",
        "saveDataErrorExecution": "all",
        "saveManualExecutions": True,
        "executionTimeout": 300,
    },
    "pinData": {},
    "meta": {"templateCredsSetupCompleted": False},
    "tags": [],
}
with open(os.path.join(OUT, "support-email-automation-" + VERSION + ".json"), "w", encoding="utf-8") as f:
    json.dump(main, f, indent=2, ensure_ascii=False)

# ---------------------------------------------------------------- error workflow
nodes.clear()
conns2 = {}
add("E1 - Error Trigger", "n8n-nodes-base.errorTrigger", {}, (0, 200), 1)
add("E2 - Build Alert", "n8n-nodes-base.code", {
    "mode": "runOnceForAllItems",
    "jsCode": (
        "// Redacted alert: workflow/node/error class only. No email content.\n"
        "const e = $input.first().json;\n"
        "const cfg = $('E0 - Config').first().json;\n"
        "const msg = String((e.execution && e.execution.error && e.execution.error.message) || 'unknown error').slice(0, 300);\n"
        "const body = [\n"
        "  'An unhandled failure occurred in the support email automation. Some messages may be stuck in PROCESSING; see the recovery steps in the handover notes.',\n"
        "  '',\n"
        "  'Workflow: ' + (e.workflow && e.workflow.name),\n"
        "  'Execution ID: ' + (e.execution && e.execution.id),\n"
        "  'Failed node: ' + (e.execution && e.execution.lastNodeExecuted),\n"
        "  'Error: ' + msg,\n"
        "  'Execution URL: ' + (e.execution && e.execution.url),\n"
        "  'Time: ' + new Date().toISOString(),\n"
        "].join('\\n');\n"
        "return [{ json: { to: cfg.ownerEmail, subject: '[Support Automation ERROR] ' + (e.workflow && e.workflow.name), body } }];\n"
    ),
}, (X * 2, 200), 2)
add("E0 - Config", "n8n-nodes-base.set",
    {"assignments": {"assignments": [cfg_assign("ownerEmail", "automation-owner@example.com")]},
     "includeOtherFields": True, "options": {}},
    (X, 200), 3.4)
add("E3 - Notify Owner", "n8n-nodes-base.gmail",
    {"resource": "message", "operation": "send", "sendTo": "={{ $json.to }}", "subject": "={{ $json.subject }}",
     "emailType": "text", "message": "={{ $json.body }}", "options": {"appendAttribution": False}},
    (X * 3, 200), 2.1, creds=CRED_GMAIL)
for a, b in [("E1 - Error Trigger", "E0 - Config"), ("E0 - Config", "E2 - Build Alert"), ("E2 - Build Alert", "E3 - Notify Owner")]:
    conns2.setdefault(a, {"main": [[]]})["main"][0].append({"node": b, "type": "main", "index": 0})

err = {
    "name": "Support Email Automation - Error Handler " + VERSION,
    "nodes": nodes,
    "connections": conns2,
    "active": False,
    "settings": {"executionOrder": "v1"},
    "pinData": {},
    "meta": {"templateCredsSetupCompleted": False},
    "tags": [],
}
with open(os.path.join(OUT, "error-handler-" + VERSION + ".json"), "w", encoding="utf-8") as f:
    json.dump(err, f, indent=2, ensure_ascii=False)

print("Built workflows into", OUT)
