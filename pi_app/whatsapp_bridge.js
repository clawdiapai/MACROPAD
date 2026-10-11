const { default: makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
const pino = require('pino');
const qrcodeTerminal = require('qrcode-terminal');
const QRCode = require('qrcode');
const axios = require('axios');
const fs = require('fs');
const path = require('path');
const http = require('http');

const AUTH_DIR = path.join(__dirname, 'auth_info_baileys');
const CONFIG_PATH = path.join(__dirname, 'config.json');
const QR_STATUS_PATH = path.join(__dirname, 'qr_status.json');
const RECENT_CHATS_PATH = path.join(__dirname, 'recent_chats.json');

// Ensure directories exist
if (!fs.existsSync(AUTH_DIR)) {
  fs.mkdirSync(AUTH_DIR, { recursive: true });
}

// Strict validator for 1-on-1 Direct Chats
function isDirectChat(jid) {
  if (!jid || typeof jid !== 'string') return false;
  if (jid.includes('@g.us')) return false; // WhatsApp Group
  if (jid.includes('@broadcast')) return false; // Broadcast / Status
  if (jid.includes('@newsletter')) return false; // Channels
  if (jid.startsWith('name_') || jid.startsWith('contact_')) return false;
  return jid.endsWith('@s.whatsapp.net') || jid.endsWith('@lid');
}

// In-Memory LID <-> Phone Number Mapping Cache
const lidToPhoneMap = new Map();
const phoneToLidMap = new Map();

function loadLidMappings() {
  try {
    if (fs.existsSync(AUTH_DIR)) {
      const files = fs.readdirSync(AUTH_DIR);
      for (const f of files) {
        if (f.startsWith('lid-mapping-') && f.endsWith('_reverse.json')) {
          const lid = f.replace('lid-mapping-', '').replace('_reverse.json', '');
          try {
            const raw = fs.readFileSync(path.join(AUTH_DIR, f), 'utf8');
            const phone = JSON.parse(raw);
            if (phone) {
              const cleanPhone = String(phone).replace(/\D/g, '');
              lidToPhoneMap.set(lid, cleanPhone);
              phoneToLidMap.set(cleanPhone, lid);
            }
          } catch (e) {}
        }
      }
      console.log(`[LID MAPPINGS] Loaded ${lidToPhoneMap.size} LID-to-Phone translations.`);
    }
  } catch (e) {}
}

loadLidMappings();

function getPhoneNumber(jid) {
  if (!jid || typeof jid !== 'string') return "";
  const rawId = jid.split('@')[0].replace(/\D/g, '');
  if (jid.includes('@lid')) {
    if (lidToPhoneMap.has(rawId)) {
      return lidToPhoneMap.get(rawId);
    }
    // Also try reading on demand if dynamically written
    try {
      const p = path.join(AUTH_DIR, `lid-mapping-${rawId}_reverse.json`);
      if (fs.existsSync(p)) {
        const ph = JSON.parse(fs.readFileSync(p, 'utf8'));
        if (ph) {
          const cleanPh = String(ph).replace(/\D/g, '');
          lidToPhoneMap.set(rawId, cleanPh);
          return cleanPh;
        }
      }
    } catch (e) {}
  }
  return rawId;
}

// Load or initialize config
function loadConfig() {
  try {
    if (fs.existsSync(CONFIG_PATH)) {
      return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
    }
  } catch (e) {
    console.error('[CONFIG] Error reading config.json:', e.message);
  }
  return {
    vip_contacts: [
      { name: "Mom", phone: "", aliases: ["mom", "mamma", "mother"] },
      { name: "Dad", phone: "", aliases: ["dad", "papa", "father"] },
      { name: "Sister", phone: "", aliases: ["sister", "sis"] }
    ],
    trigger_keywords: ["!call", "!urgent", "!alert", "!ring", "call", "urgent", "🚨", "📞", "ring", "ok"],
    any_vip_message_triggers: false,
    incoming_call_triggers: true,
    dashboard_notify_url: "http://127.0.0.1:5000/api/notify",
    send_ack_reaction: false,
    ack_reaction_emoji: "✅",
    send_ack_reply: false,
    ack_reply_text: ""
  };
}

let config = loadConfig();

// Watch for runtime config edits
fs.watchFile(CONFIG_PATH, (curr, prev) => {
  console.log('[CONFIG] config.json reloaded dynamically');
  config = loadConfig();
});

// Update QR code status for web dashboard
async function updateQrState(qrString, isConnected, statusMsg) {
  let qrBase64 = null;
  if (qrString) {
    try {
      qrBase64 = await QRCode.toDataURL(qrString, { margin: 2, scale: 6 });
    } catch (e) {}
  }
  const statusObj = {
    connected: isConnected,
    status: statusMsg,
    qr_raw: qrString,
    qr_image: qrBase64,
    updated_at: new Date().toISOString()
  };
  try {
    fs.writeFileSync(QR_STATUS_PATH, JSON.stringify(statusObj, null, 2));
  } catch (e) {}
}

// Dispatch alert to MacroPad
async function dispatchToMacroPad(senderName, messageText, notifType = "call") {
  const payload = {
    title: notifType === "call" ? "Incoming Call" : "WhatsApp Alert",
    sender: senderName,
    body: messageText,
    app: "whatsapp",
    type: notifType,
    led_effect: notifType === "call" ? "call" : "message"
  };

  try {
    const res = await axios.post(config.dashboard_notify_url, payload, { timeout: 3000 });
    console.log(`[ALERT DISPATCHED] -> MacroPad: [${senderName}] "${messageText}" (Status: ${res.status})`);
  } catch (e) {
    console.error(`[ALERT ERROR] Could not reach Pi Dashboard API: ${e.message}`);
  }
}

// Keyword matching with word boundary support
function matchKeyword(text, keyword) {
  if (!text || !keyword) return false;
  const clean = text.toLowerCase().trim();
  const kw = keyword.toLowerCase().trim();
  if (!kw) return false;

  // Alphanumeric keywords (e.g. "ok", "call", "urgent") use boundary match
  if (/^[a-z0-9]+$/i.test(kw)) {
    const regex = new RegExp(`(^|[\\s.,!?;:])${kw}([\\s.,!?;:]|$)`, 'i');
    return regex.test(clean) || clean === kw;
  }

  // Symbol/emoji or special trigger keywords (e.g. "!call", "🚨", "📞")
  return clean.includes(kw);
}

// Check if a message sender or content matches triggers
function evaluateMessage(senderJid, pushName, text) {
  if (!isDirectChat(senderJid)) return { trigger: false };

  const cleanText = (text || "").toLowerCase().trim();
  const phone = getPhoneNumber(senderJid);
  const pName = (pushName || "").toLowerCase();

  let matchedContact = null;

  for (const contact of (config.vip_contacts || [])) {
    const contactPhone = (contact.phone || "").replace(/\D/g, '');
    const hasPhoneMatch = contactPhone && phone && (phone.includes(contactPhone) || contactPhone.includes(phone));
    const hasAliasMatch = (contact.aliases || []).some(alias => pName.includes(alias.toLowerCase()));

    if (hasPhoneMatch || hasAliasMatch) {
      matchedContact = contact;
      break;
    }
  }

  // Check trigger keywords
  const hasKeyword = (config.trigger_keywords || []).some(kw => matchKeyword(cleanText, kw));
  const senderDisplayName = matchedContact ? matchedContact.name : (pushName || (phone ? ("+" + phone) : "WhatsApp"));

  // Trigger conditions:
  // 1. Matched VIP contact and (any_vip_message_triggers or contains keyword)
  if (matchedContact) {
    if (config.any_vip_message_triggers || hasKeyword) {
      return { trigger: true, senderName: matchedContact.name, type: "call" };
    }
  }

  // 2. Any direct contact sending ANY configured trigger keyword (e.g. ok, !call, urgent)
  if (hasKeyword) {
    return { trigger: true, senderName: senderDisplayName, type: "call" };
  }

  return { trigger: false };
}

// In-Memory Contact & Recent Chats Tracking
const contactsMap = new Map(); // jid -> { name, phone }
const recentChatsMap = new Map(); // canonicalKey -> { jid, name, phone, last_msg, timestamp, time_str }

function persistRecentChats() {
  const sorted = Array.from(recentChatsMap.values())
    .filter(c => c && isDirectChat(c.jid))
    .sort((a, b) => b.timestamp - a.timestamp)
    .slice(0, 50);

  try {
    fs.writeFileSync(RECENT_CHATS_PATH, JSON.stringify(sorted, null, 2));
  } catch (e) {
    console.error('[RECENT CHATS] Error writing cache file:', e.message);
  }
}

// Load initial recent chats if file exists
try {
  if (fs.existsSync(RECENT_CHATS_PATH)) {
    const list = JSON.parse(fs.readFileSync(RECENT_CHATS_PATH, 'utf8'));
    list.forEach(c => {
      if (c && isDirectChat(c.jid)) {
        const realPhone = getPhoneNumber(c.jid);
        if (realPhone && /^\d+$/.test(realPhone) && !c.jid.startsWith(realPhone)) {
          c.phone = '+' + realPhone;
        }
        c.name = resolveContactName(c.jid, c.name);
        recentChatsMap.set(c.jid, c);
      }
    });
    console.log(`[RECENT CHATS] Loaded ${recentChatsMap.size} verified direct 1-on-1 chats.`);
    persistRecentChats();
  }
} catch (e) {
  console.error('[RECENT CHATS] Error reading cache file:', e.message);
}

function resolveContactName(jid, pushName) {
  const phone = getPhoneNumber(jid);

  // 1. Check if configured in VIP contacts
  for (const vip of (config.vip_contacts || [])) {
    const vipPhone = (vip.phone || '').replace(/\D/g, '');
    if (vipPhone && phone && (phone.includes(vipPhone) || vipPhone.includes(phone))) {
      return vip.name;
    }
  }

  // 2. Check contactsMap
  if (contactsMap.has(jid)) {
    const c = contactsMap.get(jid);
    if (c.name && !c.name.startsWith('+')) return c.name;
  }

  // 3. Check pushName
  if (pushName && pushName.trim() && !pushName.startsWith('+')) {
    return pushName.trim();
  }

  return phone ? ('+' + phone) : jid;
}

function processContact(c) {
  if (!c || !isDirectChat(c.id)) return;
  const jid = c.id;
  const phone = getPhoneNumber(jid);
  const name = c.name || c.notify || c.verifiedName || '';

  if (name) {
    contactsMap.set(jid, {
      jid,
      name,
      phone: phone ? ('+' + phone) : ''
    });
  }

  const canonicalKey = phone ? `${phone}@s.whatsapp.net` : jid;
  if (recentChatsMap.has(canonicalKey)) {
    const existing = recentChatsMap.get(canonicalKey);
    if (name && (!existing.name || existing.name.startsWith('+'))) {
      existing.name = name;
      recentChatsMap.set(canonicalKey, existing);
    }
  }
}

function processChat(chat) {
  if (!chat || !isDirectChat(chat.id)) return;
  const jid = chat.id;
  const phone = getPhoneNumber(jid);
  const resolvedName = resolveContactName(jid, chat.name);
  
  let ts = 1000;
  if (chat.conversationTimestamp) {
    const rawTs = Number(chat.conversationTimestamp);
    ts = rawTs > 10000000000 ? rawTs : rawTs * 1000;
  }

  const canonicalKey = phone ? `${phone}@s.whatsapp.net` : jid;
  const existing = recentChatsMap.get(canonicalKey) || {};

  recentChatsMap.set(canonicalKey, {
    jid: canonicalKey,
    name: resolvedName,
    phone: phone ? ('+' + phone) : '',
    last_msg: existing.last_msg || (chat.unreadCount ? `${chat.unreadCount} unread` : ''),
    timestamp: Math.max(ts, existing.timestamp || 0),
    time_str: new Date(Math.max(ts, existing.timestamp || 0)).toLocaleTimeString()
  });
}

function saveRecentChat(jid, name, lastMessage, msgTimestamp) {
  if (!isDirectChat(jid)) return;
  const phone = getPhoneNumber(jid);
  const resolvedName = resolveContactName(jid, name);

  let ts = Date.now();
  if (msgTimestamp) {
    const rawTs = Number(msgTimestamp);
    ts = rawTs > 10000000000 ? rawTs : rawTs * 1000;
  }

  const canonicalKey = phone ? `${phone}@s.whatsapp.net` : jid;
  const existing = recentChatsMap.get(canonicalKey) || {};

  recentChatsMap.set(canonicalKey, {
    jid: canonicalKey,
    name: resolvedName,
    phone: phone ? ('+' + phone) : '',
    last_msg: (lastMessage || existing.last_msg || '').substring(0, 60),
    timestamp: Math.max(ts, existing.timestamp || 0),
    time_str: new Date(Math.max(ts, existing.timestamp || 0)).toLocaleTimeString()
  });

  persistRecentChats();
}

function unwrapMessage(msg) {
  if (!msg || !msg.message) return null;
  let m = msg.message;
  if (m.ephemeralMessage) m = m.ephemeralMessage.message;
  if (m.viewOnceMessage) m = m.viewOnceMessage.message;
  if (m.viewOnceMessageV2) m = m.viewOnceMessageV2.message;
  if (m.documentWithCaptionMessage) m = m.documentWithCaptionMessage.message;
  return m;
}

function extractMessageText(msg) {
  const m = unwrapMessage(msg);
  if (!m) return "";
  return m.conversation ||
         m.extendedTextMessage?.text ||
         m.imageMessage?.caption ||
         m.videoMessage?.caption ||
         m.documentMessage?.caption ||
         m.reactionMessage?.text ||
         m.templateButtonReplyMessage?.selectedId ||
         m.buttonsResponseMessage?.selectedButtonId ||
         "";
}

let activeSock = null;
let lastTriggeredAlert = null;

// Start local IPC HTTP Server for MacroPad Ack Callbacks
const ipcServer = http.createServer(async (req, res) => {
  if (req.method === 'POST' && req.url === '/api/ack') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', async () => {
      let reacted = false;
      try {
        if (activeSock && lastTriggeredAlert && lastTriggeredAlert.key) {
          const ageMs = Date.now() - lastTriggeredAlert.timestamp;
          if (ageMs < 15 * 60 * 1000) { // within 15 minutes
            if (config.send_ack_reaction) {
              const reactionEmoji = config.ack_reaction_emoji || "✅";
              await activeSock.sendMessage(lastTriggeredAlert.remoteJid, {
                react: {
                  text: reactionEmoji,
                  key: lastTriggeredAlert.key
                }
              });
              console.log(`[WHATSAPP ACK] Successfully sent '${reactionEmoji}' reaction to ${lastTriggeredAlert.senderName}`);
              reacted = true;
            }

            if (config.send_ack_reply && config.ack_reply_text) {
              await activeSock.sendMessage(lastTriggeredAlert.remoteJid, {
                text: config.ack_reply_text
              }, { quoted: { key: lastTriggeredAlert.key, message: { conversation: lastTriggeredAlert.text || "" } } });
              console.log(`[WHATSAPP ACK] Successfully sent text reply to ${lastTriggeredAlert.senderName}`);
            }

            lastTriggeredAlert = null;
          }
        }
      } catch (err) {
        console.error(`[WHATSAPP ACK ERROR] Failed to send feedback:`, err.message);
      }
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'ok', reacted }));
    });
  } else {
    res.writeHead(404);
  }
});

ipcServer.listen(5001, '127.0.0.1', () => {
  console.log('[WHATSAPP BRIDGE] Ack Feedback IPC listening on 127.0.0.1:5001');
});

async function connectToWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
  const { version, isLatest } = await fetchLatestBaileysVersion();

  console.log(`[WHATSAPP] Initializing Baileys v${version.join('.')} (Latest: ${isLatest})...`);

  const sock = makeWASocket({
    version,
    auth: state,
    logger: pino({ level: 'silent' }),
    printQRInTerminal: false,
    browser: ['MacroPad Hub', 'Raspberry Pi', '1.0.0'],
    syncFullHistory: true
  });

  activeSock = sock;

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      console.log('\n======================================================');
      console.log('  SCAN THIS QR CODE IN WHATSAPP TO PAIR YOUR PI:');
      console.log('  WhatsApp -> Settings -> Linked Devices -> Link Device');
      console.log('======================================================\n');
      qrcodeTerminal.generate(qr, { small: true });
      await updateQrState(qr, false, 'Scan QR code in WhatsApp to link your Raspberry Pi');
    }

    if (connection === 'close') {
      const statusCode = (lastDisconnect?.error)?.output?.statusCode;
      const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
      console.log(`[WHATSAPP] Connection closed (${statusCode}). Reconnecting: ${shouldReconnect}`);
      await updateQrState(null, false, `Disconnected (${statusCode}). Reconnecting...`);

      if (shouldReconnect) {
        setTimeout(connectToWhatsApp, 3000);
      } else {
        console.log('[WHATSAPP] Logged out. Clearing credentials...');
        fs.rmSync(AUTH_DIR, { recursive: true, force: true });
        setTimeout(connectToWhatsApp, 2000);
      }
    } else if (connection === 'open') {
      console.log('======================================================');
      console.log('  🎉 WHATSAPP 24/7 MULTI-DEVICE BRIDGE CONNECTED!     ');
      console.log('======================================================');
      await updateQrState(null, true, 'Connected 24/7 as Linked Device');
      loadLidMappings();
      persistRecentChats();
    }
  });

  // History & Contacts Synchronization
  sock.ev.on('messaging-history.set', ({ chats, contacts, messages, isLatest, syncType }) => {
    console.log(`[WHATSAPP SYNC] Direct sync received: ${(chats||[]).length} chats, ${(contacts||[]).length} contacts, ${(messages||[]).length} messages`);
    loadLidMappings();

    if (Array.isArray(contacts)) {
      contacts.filter(c => c && isDirectChat(c.id)).forEach(processContact);
    }
    if (Array.isArray(chats)) {
      chats.filter(c => c && isDirectChat(c.id)).forEach(processChat);
    }
    if (Array.isArray(messages)) {
      messages.forEach(msg => {
        if (!msg || !msg.key) return;
        const senderJid = msg.key.remoteJid || "";
        if (!isDirectChat(senderJid)) return;
        const pushName = msg.pushName || "";
        const rawText = extractMessageText(msg);
        if (!rawText) return;
        const fromMe = Boolean(msg.key.fromMe);
        const displayText = fromMe ? `You: ${rawText}` : rawText;
        const msgTs = msg.messageTimestamp ? Number(msg.messageTimestamp) * 1000 : Date.now();
        saveRecentChat(senderJid, pushName, displayText, msgTs);
      });
    }
    persistRecentChats();
  });

  sock.ev.on('contacts.set', ({ contacts }) => {
    if (Array.isArray(contacts)) {
      contacts.filter(c => c && isDirectChat(c.id)).forEach(processContact);
      persistRecentChats();
    }
  });

  sock.ev.on('contacts.upsert', (contacts) => {
    if (Array.isArray(contacts)) {
      contacts.filter(c => c && isDirectChat(c.id)).forEach(processContact);
      persistRecentChats();
    }
  });

  sock.ev.on('contacts.update', (updates) => {
    if (Array.isArray(updates)) {
      updates.filter(c => c && isDirectChat(c.id)).forEach(processContact);
      persistRecentChats();
    }
  });

  sock.ev.on('chats.set', ({ chats }) => {
    if (Array.isArray(chats)) {
      chats.filter(c => c && isDirectChat(c.id)).forEach(processChat);
      persistRecentChats();
    }
  });

  sock.ev.on('chats.upsert', (chats) => {
    if (Array.isArray(chats)) {
      chats.filter(c => c && isDirectChat(c.id)).forEach(processChat);
      persistRecentChats();
    }
  });

  sock.ev.on('chats.update', (updates) => {
    if (Array.isArray(updates)) {
      updates.filter(c => c && isDirectChat(c.id)).forEach(processChat);
      persistRecentChats();
    }
  });

  // Handle incoming calls
  sock.ev.on('call', async (callEvents) => {
    if (!config.incoming_call_triggers) return;
    for (const c of callEvents) {
      if (c.status === 'offer') {
        const callerPhone = getPhoneNumber(c.from);
        const callerName = resolveContactName(c.from, null) || (callerPhone ? ('+' + callerPhone) : 'WhatsApp');
        console.log(`[CALL OFFER] Incoming WhatsApp call from: ${callerName} (${callerPhone || c.from})`);
        dispatchToMacroPad(callerName, "Incoming WhatsApp Call", "call");
      }
    }
  });

  // Handle live incoming AND outbound messages
  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    for (const msg of messages) {
      if (!msg.message) continue;

      const senderJid = msg.key.remoteJid || "";
      if (!isDirectChat(senderJid)) {
        // Strictly ignore all group messages (@g.us)
        continue;
      }

      const pushName = msg.pushName || "";
      const rawText = extractMessageText(msg);
      if (!rawText) continue;

      const fromMe = Boolean(msg.key.fromMe);
      const displayText = fromMe ? `You: ${rawText}` : rawText;
      const msgTs = msg.messageTimestamp ? Number(msg.messageTimestamp) * 1000 : Date.now();

      console.log(`[DM ${fromMe ? 'OUT' : 'IN'}] [${senderJid}] (${pushName || 'direct'}): ${displayText}`);

      saveRecentChat(senderJid, pushName, displayText, msgTs);

      // Trigger notification alerts on new live incoming messages
      if (type === 'notify' && !fromMe) {
        const evalResult = evaluateMessage(senderJid, pushName, rawText);
        if (evalResult.trigger) {
          console.log(`⚡ [TRIGGER MATCH] ${evalResult.senderName}: "${rawText}"`);
          lastTriggeredAlert = {
            remoteJid: senderJid,
            key: msg.key,
            senderName: evalResult.senderName,
            text: rawText,
            timestamp: Date.now()
          };
          dispatchToMacroPad(evalResult.senderName, rawText, evalResult.type);
        }
      }
    }
  });
}

connectToWhatsApp();
