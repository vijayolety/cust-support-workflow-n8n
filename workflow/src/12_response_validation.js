// 12 - Response Validation (fail closed)
const ctx = $('10c - Build Generation Prompt').first().json;
const cfg = $('00 - Config').first().json;
const resp = $input.first().json;
const maxChars = Number(cfg.maxResponseChars) || 2500;

const { generationRequest, ...base } = ctx;
const failures = [];
let parsed = null;

try {
  const content = resp && resp.choices && resp.choices[0] && resp.choices[0].message && resp.choices[0].message.content;
  parsed = typeof content === 'string' ? JSON.parse(content) : content;
} catch (e) {
  failures.push('malformed_generation_output');
}

const reply = parsed && typeof parsed.response === 'string' ? parsed.response.trim() : '';

if (parsed) {
  if (typeof parsed.answerable !== 'boolean' || !Array.isArray(parsed.cited_source_ids)) failures.push('malformed_generation_output');
  else if (parsed.answerable !== true) failures.push('model_reported_unanswerable');
}
if (reply.length < 20) failures.push('empty_or_too_short');
if (reply.length > maxChars) failures.push('too_long');

// Grounding: must cite at least one accepted chunk and only accepted chunks.
const acceptedIds = base.retrieval.accepted.map(a => a.id);
const cited = parsed && Array.isArray(parsed.cited_source_ids) ? parsed.cited_source_ids : [];
if (cited.length === 0 || cited.some(id => !acceptedIds.includes(id))) failures.push('ungrounded_citations');

// Prompt / secret leakage and debug language.
const leak = /(system prompt|my instructions|pinecone|embedding|vector (search|store|index)|openai|chatgpt|as an ai( language model)?|\bsk-[A-Za-z0-9_-]{10,}|bearer\s+[A-Za-z0-9._-]{12,}|BEGIN [A-Z ]*PRIVATE KEY|<\/?(knowledge|customer_email|thread_context|chunk)>)/i;
if (leak.test(reply)) failures.push('prompt_or_secret_leakage');
if (/(\{\{|\}\}|\bundefined\b|\[object |\bTODO\b|\bNaN\b)/.test(reply)) failures.push('debug_language');

// Unsupported specifics: every URL and number in the reply must appear in the cited knowledge or the customer's email.
// Numbered-list markers ("1. ", "2) ") are formatting, not facts; source URLs/titles of cited chunks count as supported.
const citedChunks = base.retrieval.accepted.filter(a => cited.includes(a.id));
const citedText = citedChunks.map(a => a.text + ' ' + (a.source || '') + ' ' + (a.title || '')).join('\n') + '\n' + base.body + '\n' + base.subject + '\n' + (base.fromName || '') + '\n' + (base.from || '');
const norm = s => String(s).toLowerCase().replace(/(\d),(\d)/g, '$1$2');
const haystack = norm(citedText);
const replyNoMarkers = reply.replace(/^\s*(?:[-*•]\s*)?\(?\d{1,2}[.)]\s+/gm, '');
const urls = replyNoMarkers.match(/https?:\/\/[^\s)>\]]+/gi) || [];
const numbers = (replyNoMarkers.match(/(?<![A-Za-z0-9])\d+(?:[.,]\d+)*/g) || []).map(norm).map(n => n.replace(/[.,]+$/, ''));
const unsupported = [...urls.map(u => u.toLowerCase().replace(/[.,;]+$/, '')), ...numbers].filter(v => !haystack.includes(v));
if (unsupported.length) failures.push('unsupported_specifics(' + [...new Set(unsupported)].slice(0, 5).join(' | ') + ')');

// Recipient safety: reply goes to the original sender only, and never to ourselves or no-reply addresses.
const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
if (!emailRe.test(base.from || '') || base.from === base.mailbox || /(^|[._-])(no-?reply|donotreply|mailer-daemon|postmaster)([._-]|@)/i.test(base.from)) {
  failures.push('invalid_recipient');
}
if (!base.threadId || !base.messageId) failures.push('missing_thread_identifiers');

const passed = failures.length === 0;
return [{
  json: {
    ...base,
    validation: { passed, failures },
    replyText: passed ? reply : null,
    route: passed ? 'reply' : 'escalate',
    escalation_reason: passed ? null : 'validation_failed:' + [...new Set(failures)].join(','),
    generationUsage: resp.usage || null,
  },
}];
