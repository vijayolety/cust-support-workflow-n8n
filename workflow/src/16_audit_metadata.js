// 16 - Audit Metadata
// Operational metadata only: IDs, statuses, decisions, timings. Email bodies are deliberately excluded.
const cfg = $('00 - Config').first().json;
const norm = $('02 - Normalize Email').first().json;
const done = $input.first().json;
const sd = $getWorkflowStaticData('global');

function safe(name) {
  try {
    const n = $(name);
    return n.isExecuted ? n.first().json : null;
  } catch (e) { return null; }
}

const cls = safe('06b - Parse Classification');
const ret = safe('10 - Retrieval Guard');
const val = safe('12 - Response Validation');
const esc = safe('14 - Human Escalation');

const record = {
  executionId: $execution.id,
  workflowVersion: cfg.workflowVersion,
  messageId: norm.messageId,
  threadId: norm.threadId,
  mailbox: norm.mailbox,
  receivedAt: norm.receivedAt,
  status: done.status,
  classification: cls && cls.classification ? {
    category: cls.classification.category,
    confidence: cls.classification.confidence,
    intent: cls.classification.intent,
    route: cls.route,
  } : null,
  retrieval: ret ? { topK: ret.retrieval.topK, returned: ret.retrieval.returned, accepted: ret.retrieval.acceptedCount, grounded: ret.grounded } : null,
  generation: val ? {
    model: cfg.generationModel,
    validationPassed: val.validation.passed,
    validationFailures: val.validation.failures,
    usage: val.generationUsage || null,
  } : null,
  replyStatus: done.status === 'REPLIED' ? 'sent' : 'not_sent',
  escalation: esc ? { reason: esc.escalation.reason, class: esc.escalation.reasonClass, stage: esc.escalation.stage, destination: esc.escalation.destination, at: esc.escalation.at } : null,
  maxRetryAttemptsConfigured: 3,
  latencyMs: Date.now() - norm.startedAt,
  completedAt: new Date().toISOString(),
};

sd.audit = sd.audit || [];
sd.audit.push(record);
if (sd.audit.length > 200) sd.audit = sd.audit.slice(-200);

console.log('AUDIT ' + JSON.stringify(record));
return [{ json: record }];
