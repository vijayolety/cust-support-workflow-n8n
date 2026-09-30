// 03b - Build Thread Context
// Keeps only a bounded number of recent prior messages (snippets), never the whole mailbox.
const norm = $('02 - Normalize Email').first().json;
const cfg = $('00 - Config').first().json;
const item = ($input.first() && $input.first().json) || {};
const max = Math.max(0, Number(cfg.maxThreadMessages) || 0);

const messages = Array.isArray(item.messages) ? item.messages : [];
const context = max === 0 ? [] : messages
  .filter(m => m && m.id !== norm.messageId)
  .slice(-max)
  .map(m => String(m.snippet || m.text || '').replace(/\s+/g, ' ').trim().slice(0, 300))
  .filter(Boolean);

return [{ json: { ...norm, threadContext: context, threadMessageCount: context.length } }];
