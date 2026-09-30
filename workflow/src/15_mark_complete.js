// 15 - Mark Complete
// Persists the terminal state. Status is derived from the node that fed this one.
const norm = $('02 - Normalize Email').first().json;
const sd = $getWorkflowStaticData('global');
sd.processed = sd.processed || {};
const prev = $prevNode && $prevNode.name ? $prevNode.name : '';

let status = 'ESCALATED';
if (prev.startsWith('13')) status = 'REPLIED';
else if (prev.startsWith('07b')) status = 'NON_SUPPORT';

sd.processed[norm.messageId] = { state: status, threadId: norm.threadId, at: new Date().toISOString() };

return [{ json: { messageId: norm.messageId, threadId: norm.threadId, status } }];
