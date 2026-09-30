// 14 - Human Escalation
// Single convergence point for every "cannot safely answer" path. No customer-facing email is sent from here.
const cfg = $('00 - Config').first().json;
const norm = $('02 - Normalize Email').first().json;
const cur = $input.first().json || {};
const prev = $prevNode && $prevNode.name ? $prevNode.name : 'unknown';

let reason = cur.escalation_reason || null;
let reasonClass = 'policy';
let errorDetail = '';
if (cur.error) {
  errorDetail = String((cur.error && (cur.error.message || cur.error.description)) || cur.error || '').replace(/\s+/g, ' ').slice(0, 300);
}
if (!reason && cur.error) {
  const msg = errorDetail;
  const permanent = /(401|403|404|unauthori[sz]ed|forbidden|invalid.*(api key|credential|index)|not found)/i.test(msg);
  reasonClass = permanent ? 'permanent_config' : 'transient_exhausted';
  reason = (permanent ? 'permanent_error_at_' : 'provider_error_after_retries_at_') + prev.replace(/\s+/g, '_');
} else if (!reason) {
  reason = 'unspecified_escalation_from_' + prev.replace(/\s+/g, '_');
}
if (cur.error && reasonClass === 'policy') reasonClass = 'transient_exhausted';

const subject = String(norm.subject || '').slice(0, 120);
const link = 'https://mail.google.com/mail/u/0/#all/' + norm.threadId;
const notifyBody = [
  'A support email could not be answered automatically and needs human handling. No automated reply was sent.',
  '',
  'Reason: ' + reason,
  'Class: ' + reasonClass,
  'Stage: ' + prev,
  errorDetail ? 'Error detail: ' + errorDetail : null,
  'From: ' + norm.from,
  'Subject: ' + subject,
  'Message ID: ' + norm.messageId,
  'Thread ID: ' + norm.threadId,
  'Received: ' + norm.receivedAt,
  'Open thread: ' + link,
  'n8n execution: ' + $execution.id,
].filter(l => l !== null).join('\n');

return [{
  json: {
    messageId: norm.messageId,
    threadId: norm.threadId,
    escalation: { reason, reasonClass, stage: prev, at: new Date().toISOString(), destination: cfg.escalationEmail },
    escalationLabelId: cfg.escalationLabelId,
    escalationEmail: cfg.escalationEmail,
    notifySubject: '[Support Escalation] ' + subject,
    notifyBody,
  },
}];
