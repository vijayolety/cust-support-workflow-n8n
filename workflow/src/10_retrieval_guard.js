// 10 - Retrieval Guard
// Keeps only matches at/above the relevance threshold that carry usable text; caps to Top-K.
const ctx = $('06b - Parse Classification').first().json;
const cfg = $('00 - Config').first().json;
const resp = $input.first().json;
const topK = Number(cfg.topK);
const minScore = Number(cfg.minScore);
const textField = cfg.metadataTextField || 'text';

const matches = Array.isArray(resp && resp.matches) ? resp.matches : [];
const accepted = matches
  .filter(m => typeof m.score === 'number' && m.score >= minScore)
  .filter(m => m.metadata && typeof m.metadata[textField] === 'string' && m.metadata[textField].trim().length > 0)
  .sort((a, b) => b.score - a.score)
  .slice(0, topK)
  .map(m => ({
    id: m.id,
    score: m.score,
    title: m.metadata.title || m.metadata.doc_title || m.metadata.source || null,
    source: m.metadata.url || m.metadata.source_url || m.metadata.source || null,
    text: m.metadata[textField],
  }));

const grounded = accepted.length > 0;
return [{
  json: {
    ...ctx,
    retrieval: { topK, minScore, returned: matches.length, acceptedCount: accepted.length, accepted },
    grounded,
    escalation_reason: grounded ? null : 'no_relevant_context',
    route: grounded ? 'support' : 'escalate',
    embeddingUsage: ($('08 - Create Query Embedding').first().json || {}).usage || null,
  },
}];
