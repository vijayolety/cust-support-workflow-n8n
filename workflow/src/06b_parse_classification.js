// 06b - Parse Classification
// Strictly validates the classifier JSON and decides the route: support | non_support | escalate.
const ctx = $('05c - Build Classifier Prompt').first().json;
const cfg = $('00 - Config').first().json;
const resp = $input.first().json;
const threshold = Number(cfg.confidenceThreshold);
const sensitive = String(cfg.sensitiveIntents || '').split(',').map(s => s.trim().toLowerCase()).filter(Boolean);

const { classifierRequest, ...base } = ctx;

function fail(reason) {
  return [{ json: { ...base, classification: null, route: 'escalate', escalation_reason: reason, usage: resp.usage || null } }];
}

if (base.emptyBody && !String(base.subject || '').trim()) return fail('insufficient_content');

let parsed;
try {
  const content = resp && resp.choices && resp.choices[0] && resp.choices[0].message && resp.choices[0].message.content;
  parsed = typeof content === 'string' ? JSON.parse(content) : content;
} catch (e) {
  return fail('classifier_malformed_output');
}

const valid = parsed && typeof parsed === 'object'
  && ['support', 'non_support'].includes(parsed.category)
  && typeof parsed.confidence === 'number' && parsed.confidence >= 0 && parsed.confidence <= 1
  && typeof parsed.reason === 'string'
  && typeof parsed.requires_human === 'boolean'
  && typeof parsed.intent === 'string';
if (!valid) return fail('classifier_malformed_output');

const intent = parsed.intent.trim().toLowerCase();
const classification = {
  category: parsed.category,
  confidence: parsed.confidence,
  reason: parsed.reason,
  requires_human: parsed.requires_human,
  intent,
};

let route = 'escalate';
let escalation_reason = null;
if (sensitive.includes(intent)) {
  escalation_reason = 'sensitive_intent:' + intent;
} else if (parsed.requires_human || parsed.confidence < threshold) {
  escalation_reason = 'low_confidence_or_requires_human';
} else {
  route = parsed.category === 'support' ? 'support' : 'non_support';
}

const retrievalQuery = ((base.subject ? base.subject + '\n' : '') + (base.body || '')).slice(0, 2000);

return [{ json: { ...base, classification, route, escalation_reason, retrievalQuery, usage: resp.usage || null } }];
