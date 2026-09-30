// 05 - Mark Processing
// Claims the message (state PROCESSING) BEFORE any AI call or reply. Re-checks to close the race window.
const it = $input.first().json;
const sd = $getWorkflowStaticData('global');
sd.processed = sd.processed || {};

if (it.duplicate) return [{ json: it }];

if (sd.processed[it.messageId]) {
  return [{ json: { ...it, duplicate: true, duplicateReason: 'already_' + String(sd.processed[it.messageId].state).toLowerCase() } }];
}

sd.processed[it.messageId] = { state: 'PROCESSING', threadId: it.threadId, at: new Date().toISOString() };

// Bound the state store size (drop oldest entries).
const keys = Object.keys(sd.processed);
if (keys.length > 5000) {
  keys.sort((a, b) => String(sd.processed[a].at).localeCompare(String(sd.processed[b].at)));
  for (const k of keys.slice(0, keys.length - 5000)) delete sd.processed[k];
}

return [{ json: { ...it, processingKey: it.messageId, processingState: 'PROCESSING' } }];
