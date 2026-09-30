// 04 - Idempotency Check
// messageId is the primary idempotency key. Any existing state means "stop safely".
const it = $input.first().json;
const sd = $getWorkflowStaticData('global');
sd.processed = sd.processed || {};
const existing = sd.processed[it.messageId];

let duplicateReason = null;
if (existing) duplicateReason = 'already_' + String(existing.state).toLowerCase();
else if (it.fromSelf) duplicateReason = 'self_sender';
else if (it.isAutomated) duplicateReason = 'automated_sender';
else if (!it.messageId) duplicateReason = 'missing_message_id';

return [{
  json: {
    ...it,
    duplicate: duplicateReason !== null,
    duplicateReason,
    existingState: existing ? existing.state : null,
  },
}];
