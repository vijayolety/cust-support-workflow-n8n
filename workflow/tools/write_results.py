import json, shutil, openpyxl, os
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src = os.path.join(root, "..", "Ignore", "4.n8n Customer Support QA Test Cases.xlsx")
dst = os.path.join(root, "tests", "QA Test Cases - Offline Results.xlsx")
shutil.copy(src, dst)
res = json.load(open(os.path.join(root, "tests", "results.json"), encoding="utf-8"))["results"]
live = {
 "TC-E2E-001": ("PASS (live)", "Live n8n Cloud run: support email -> grounded reply in original Gmail thread, same subject, no footer; node 15 status REPLIED."),
 "TC-RP-001": ("PASS (live)", "Screenshot: reply appears inside original conversation in real Gmail."),
 "TC-RP-003": ("PASS (live)", "Screenshot: thread keeps original subject."),
 "TC-GM-003": ("PASS (live)", "Reply landed in the source thread (threadId carried end to end)."),
 "TC-GEN-001": ("PASS (live)", "Reply matched the KB article (Settings > Security > Reset password, 24h link)."),
 "TC-GEN-003": ("PASS (live)", "One sample judged professional, concise, greeting + sign-off; broader manual review still advisable."),
 "TC-CL-001": ("PASS (live)", "Live classifier: category=support, confidence 0.90, routed to RAG (single sample)."),
 "TC-RAG-001": ("PASS (live)", "Live OpenAI embedding created and mapped to the Pinecone query."),
 "TC-RAG-002": ("PASS (live)", "Live Pinecone returned kb-reset-password (score 0.73) with text/title/url metadata."),
 "TC-RAG-005": ("PASS (live)", "Live: id/title/source preserved in Retrieval Guard output."),
 "TC-RAG-004": ("PASS (user-reported)", "User ran the Android-app question (not in KB): escalated, no reply. Live also showed no_relevant_context when score 0.73 < minScore 0.75."),
 "TC-GEN-002": ("PASS (user-reported)", "Unsupported question escalated without a guessed reply."),
 "TC-E2E-003": ("PASS (user-reported)", "Unsupported question: escalation notification + label, no reply."),
 "TC-CL-002": ("PASS (user-reported)", "Marketing email classified non-support; no reply."),
 "TC-E2E-002": ("PASS (user-reported)", "Non-support email followed configured label-only route; no reply."),
 "TC-RP-005": ("PASS (live)", "Escalated runs (Pinecone 401, no_relevant_context, validation failure) sent no customer reply; only escalation notification."),
 "TC-E2E-006": ("PASS (live)", "Observed live: Pinecone 401 (missing header) -> no generation, no reply, escalation email with reason permanent_config."),
 "TC-NFR-007": ("PASS (live)", "Both workflow JSON files imported into n8n Cloud with all nodes/connections intact; only credentials needed mapping."),
}
wb = openpyxl.load_workbook(dst)
ws = wb["Test Result"]
for row in ws.iter_rows(min_row=2):
    tc = row[0].value
    if tc in res:
        r = res[tc]
        if tc in live: r = {"status": live[tc][0], "evidence": live[tc][1] + " | Offline: " + str(r["evidence"])[:250]}
        row[4].value = "Claude (offline simulator)"
        row[5].value = "2026-09-30"
        row[6].value = r["status"]
        row[7].value = r["evidence"]
        row[9].value = "workflow/tests/results.md"
wb.save(dst)
print("saved", dst)
