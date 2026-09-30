// 02 - Normalize Email
// Normalizes the Gmail Trigger payload (raw/parsed format) into a stable contract.
const cfg = $('00 - Config').first().json;
const j = $input.first().json;

function parseOne(x) {
  if (!x) return { address: '', name: '' };
  if (x.value && x.value[0]) {
    return { address: String(x.value[0].address || '').trim().toLowerCase(), name: String(x.value[0].name || '').trim() };
  }
  const s = typeof x === 'string' ? x : (x.text || '');
  const m = s.match(/^\s*"?([^"<]*?)"?\s*<([^>]+)>\s*$/);
  if (m) return { address: m[2].trim().toLowerCase(), name: m[1].trim() };
  return { address: s.trim().toLowerCase(), name: '' };
}

function parseList(x) {
  if (!x) return [];
  if (x.value) return x.value.map(v => String(v.address || '').trim().toLowerCase()).filter(Boolean);
  const s = typeof x === 'string' ? x : (x.text || '');
  return s.split(',').map(p => parseOne(p).address).filter(Boolean);
}

function htmlToText(html) {
  return String(html || '')
    .replace(/<(script|style|head|title)[\s\S]*?<\/\1>/gi, ' ')
    .replace(/<!--[\s\S]*?-->/g, ' ')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/(p|div|li|tr|h[1-6])>/gi, '\n')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'");
}

function stripQuotedReply(text) {
  const lines = String(text).split(/\r?\n/);
  const out = [];
  for (const line of lines) {
    if (/^\s*On .{5,120}wrote:\s*$/i.test(line)) break;
    if (/^\s*-{2,}\s*Original Message\s*-{2,}/i.test(line)) break;
    if (/^\s*>/.test(line)) continue;
    out.push(line);
  }
  return out.join('\n');
}

const rawText = j.text && String(j.text).trim() ? String(j.text) : htmlToText(j.html || j.textAsHtml || '');
let body = stripQuotedReply(rawText)
  .replace(/[​-‍﻿]/g, '')
  .replace(/[ \t]+/g, ' ')
  .replace(/\n{3,}/g, '\n\n')
  .trim();
if (body.length > 6000) body = body.slice(0, 6000);

const from = parseOne(j.from || j.From);
const to = parseList(j.to || j.To);
const subject = String(j.subject || j.Subject || '').trim();
const headers = j.headers || {};
const autoSubmitted = String(headers['auto-submitted'] || '').toLowerCase();
const precedence = String(headers['precedence'] || '').toLowerCase();
const isAutomated = (autoSubmitted !== '' && autoSubmitted !== 'no') || ['bulk', 'junk', 'auto_reply'].includes(precedence);
const mailbox = String(cfg.mailbox || '').toLowerCase();

let receivedAt = null;
if (j.date) { const d = new Date(j.date); if (!isNaN(d)) receivedAt = d.toISOString(); }
if (!receivedAt && j.internalDate) receivedAt = new Date(Number(j.internalDate)).toISOString();
if (!receivedAt) receivedAt = new Date().toISOString();

return [{
  json: {
    messageId: j.id || '',
    rfcMessageId: j.messageId || '',
    threadId: j.threadId || '',
    from: from.address,
    fromName: from.name,
    to,
    subject,
    body,
    receivedAt,
    mailbox,
    emptyBody: body.length === 0,
    fromSelf: mailbox !== '' && from.address === mailbox,
    isAutomated,
    startedAt: Date.now(),
  },
}];
