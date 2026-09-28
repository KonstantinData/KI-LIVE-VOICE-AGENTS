import { useState, useRef, useEffect, useCallback } from "react";

/**
 * SpeakingAssistant
 * -----------------
 * A chat widget engineered to feel like the assistant is *speaking to you*.
 * The illusion is produced by four techniques, all independent of the model:
 *   1. Token streaming        -> reply appears word-by-word, not as a block
 *   2. Punctuation-aware pace  -> longer pause after . ! ?, short after ,
 *   3. Thinking indicator      -> animated dots BEFORE the stream starts
 *   4. Reactive avatar (orb)   -> visibly "alive" while speaking
 *
 * Swap point for production: replace `simulateReply` with a real streaming
 * endpoint (SSE / fetch ReadableStream) or, for a voice agent, drive the
 * `speaking` state from TTS audio events. See notes at the bottom.
 */

// --- Pacing config (tune this to change the "voice") ------------------------
const BASE_MS = 42;          // base delay per word
const JITTER_MS = 34;        // random jitter -> organic, non-mechanical rhythm
const PAUSE_SENTENCE = 260;  // extra pause after . ! ?
const PAUSE_COMMA = 120;     // extra pause after , ; :
const THINK_MS = 700;        // typing-indicator duration before streaming

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Canned replies stand in for a real API. In production this whole function
// is replaced by a streaming call (see notes at bottom of file).
const REPLIES = [
  "Klar, das kriegen wir hin. Erzähl mir kurz, was das Widget können soll – reiner Text-Chat oder soll später auch eine Stimme dranhängen?",
  "Gute Frage. Der Trick ist, die Antwort nicht am Stück zu rendern, sondern Wort für Wort. Genau das siehst du hier gerade passieren.",
  "Verstanden. Ich merke mir das für den Kontext – möchtest du, dass ich als Nächstes den Anschluss an eine echte API skizziere?",
];

export default function SpeakingAssistant() {
  const [messages, setMessages] = useState([
    { role: "assistant", text: "Hi Konstantin. Frag mich was – du siehst dann, wie die Antwort „gesprochen" wird." },
  ]);
  const [thinking, setThinking] = useState(false);
  const [streaming, setStreaming] = useState("");   // partial assistant text
  const [speaking, setSpeaking] = useState(false);  // drives the orb animation
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  const scrollRef = useRef(null);
  const replyIdx = useRef(0);

  // Keep the transcript pinned to the newest content.
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: 9e9, behavior: "smooth" });
  }, [messages, streaming, thinking]);

  /**
   * Streams `text` into the `streaming` buffer with speech-like timing.
   * The word loop + punctuation pauses are the core of the illusion.
   */
  const streamText = useCallback(async (text) => {
    setThinking(false);
    setSpeaking(true);
    const words = text.split(" ");
    let acc = "";
    for (let i = 0; i < words.length; i++) {
      const w = words[i];
      acc += (i === 0 ? "" : " ") + w;
      setStreaming(acc);

      let wait = BASE_MS + Math.random() * JITTER_MS;
      if (/[.!?]$/.test(w)) wait += PAUSE_SENTENCE;      // end of sentence
      else if (/[,;:]$/.test(w)) wait += PAUSE_COMMA;    // clause boundary
      await sleep(wait);
    }
    // Commit the finished message and reset the live buffer.
    setSpeaking(false);
    setStreaming("");
    setMessages((m) => [...m, { role: "assistant", text }]);
  }, []);

  const send = useCallback(async () => {
    const q = input.trim();
    if (!q || busy) return;
    setBusy(true);
    setInput("");
    setMessages((m) => [...m, { role: "user", text: q }]);

    // 3. Thinking indicator: the pause is a social signal, not dead time.
    setThinking(true);
    await sleep(THINK_MS);

    // --- SWAP POINT: real streaming API goes here (see notes) ---
    const reply = REPLIES[replyIdx.current % REPLIES.length];
    replyIdx.current += 1;
    await streamText(reply);
    // -----------------------------------------------------------

    setBusy(false);
  }, [input, busy, streamText]);

  return (
    <div className="sa-root">
      <style>{css}</style>

      <header className="sa-head">
        <Orb speaking={speaking} thinking={thinking} />
        <div className="sa-id">
          <span className="sa-name">Assistent</span>
          <span className="sa-state">
            {speaking ? "spricht …" : thinking ? "denkt nach …" : "online"}
          </span>
        </div>
        <VoiceBars active={speaking} />
      </header>

      <div className="sa-log" ref={scrollRef}>
        {messages.map((m, i) => (
          <Bubble key={i} role={m.role} text={m.text} />
        ))}

        {thinking && (
          <div className="sa-row assistant">
            <div className="sa-bubble assistant thinking">
              <Dots />
            </div>
          </div>
        )}

        {streaming && (
          <div className="sa-row assistant">
            <div className="sa-bubble assistant">
              {streaming}
              <span className="sa-caret" />
            </div>
          </div>
        )}
      </div>

      <div className="sa-input">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Nachricht schreiben …"
          disabled={busy}
        />
        <button onClick={send} disabled={busy || !input.trim()} aria-label="Senden">
          ↑
        </button>
      </div>
    </div>
  );
}

// --- Reactive avatar: idle "breathing" + active pulse while speaking --------
function Orb({ speaking, thinking }) {
  const state = speaking ? "speaking" : thinking ? "thinking" : "idle";
  return (
    <div className={`sa-orb ${state}`}>
      <div className="sa-orb-ring" />
      <div className="sa-orb-core" />
    </div>
  );
}

// Equalizer bars — reinforce the "speaking" metaphor, bridge to voice.
function VoiceBars({ active }) {
  return (
    <div className={`sa-bars ${active ? "on" : ""}`} aria-hidden>
      {[0, 1, 2, 3, 4].map((i) => (
        <span key={i} style={{ animationDelay: `${i * 90}ms` }} />
      ))}
    </div>
  );
}

function Dots() {
  return (
    <span className="sa-dots" aria-label="tippt">
      <span /><span /><span />
    </span>
  );
}

function Bubble({ role, text }) {
  return (
    <div className={`sa-row ${role}`}>
      <div className={`sa-bubble ${role}`}>{text}</div>
    </div>
  );
}

// --- Styles: dark surface so the glowing orb reads as "alive" ---------------
const css = `
.sa-root{--bg:#0F1420;--panel:#161C2A;--line:#232C3E;--user:#2A3350;
  --txt:#E6EAF2;--mut:#8A93A6;--a1:#5EEAD4;--a2:#A78BFA;
  display:flex;flex-direction:column;width:100%;max-width:440px;height:600px;
  margin:0 auto;background:var(--bg);border:1px solid var(--line);
  border-radius:20px;overflow:hidden;color:var(--txt);
  font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;}

.sa-head{display:flex;align-items:center;gap:12px;padding:14px 16px;
  border-bottom:1px solid var(--line);background:var(--panel);}
.sa-id{display:flex;flex-direction:column;line-height:1.3;flex:1;}
.sa-name{font-weight:600;font-size:14px;}
.sa-state{font-size:12px;color:var(--mut);}

/* Orb: layered gradient, always breathing, stronger pulse when speaking */
.sa-orb{position:relative;width:38px;height:38px;flex:0 0 auto;}
.sa-orb-core{position:absolute;inset:0;border-radius:50%;
  background:radial-gradient(circle at 30% 30%,var(--a1),var(--a2) 70%);
  box-shadow:0 0 14px -2px var(--a2);animation:breathe 3.6s ease-in-out infinite;}
.sa-orb-ring{position:absolute;inset:-4px;border-radius:50%;
  border:2px solid var(--a1);opacity:0;}
.sa-orb.speaking .sa-orb-core{animation:pulse .9s ease-in-out infinite;}
.sa-orb.speaking .sa-orb-ring{animation:ripple 1.2s ease-out infinite;}
.sa-orb.thinking .sa-orb-core{animation:breathe 1.4s ease-in-out infinite;}
@keyframes breathe{0%,100%{transform:scale(1)}50%{transform:scale(1.08)}}
@keyframes pulse{0%,100%{transform:scale(1);box-shadow:0 0 14px -2px var(--a2)}
  50%{transform:scale(1.16);box-shadow:0 0 24px 2px var(--a2)}}
@keyframes ripple{0%{opacity:.6;transform:scale(1)}100%{opacity:0;transform:scale(1.5)}}

/* Voice bars */
.sa-bars{display:flex;align-items:flex-end;gap:3px;height:20px;}
.sa-bars span{width:3px;height:4px;border-radius:2px;
  background:linear-gradient(var(--a1),var(--a2));opacity:.35;}
.sa-bars.on span{animation:eq .7s ease-in-out infinite;}
@keyframes eq{0%,100%{height:4px}50%{height:18px}}

/* Transcript */
.sa-log{flex:1;overflow-y:auto;padding:18px 16px;display:flex;
  flex-direction:column;gap:12px;}
.sa-row{display:flex;}
.sa-row.user{justify-content:flex-end;}
.sa-bubble{max-width:80%;padding:10px 14px;border-radius:16px;
  font-size:14px;line-height:1.5;white-space:pre-wrap;}
.sa-bubble.assistant{background:var(--panel);border:1px solid var(--line);
  border-bottom-left-radius:5px;}
.sa-bubble.user{background:var(--user);border-bottom-right-radius:5px;}
.sa-bubble.thinking{padding:14px 16px;}

/* Streaming caret — the "live typing" tell */
.sa-caret{display:inline-block;width:2px;height:1em;margin-left:2px;
  vertical-align:text-bottom;background:var(--a1);animation:blink 1s steps(1) infinite;}
@keyframes blink{50%{opacity:0}}

/* Typing dots */
.sa-dots{display:inline-flex;gap:4px;}
.sa-dots span{width:6px;height:6px;border-radius:50%;background:var(--mut);
  animation:dot 1.2s ease-in-out infinite;}
.sa-dots span:nth-child(2){animation-delay:.2s}
.sa-dots span:nth-child(3){animation-delay:.4s}
@keyframes dot{0%,60%,100%{opacity:.3;transform:translateY(0)}
  30%{opacity:1;transform:translateY(-4px)}}

/* Composer */
.sa-input{display:flex;gap:8px;padding:12px;border-top:1px solid var(--line);
  background:var(--panel);}
.sa-input input{flex:1;background:var(--bg);border:1px solid var(--line);
  border-radius:12px;padding:10px 14px;color:var(--txt);font-size:14px;outline:none;}
.sa-input input:focus{border-color:var(--a2);}
.sa-input button{width:40px;border:none;border-radius:12px;cursor:pointer;
  font-size:18px;color:#0F1420;background:linear-gradient(var(--a1),var(--a2));}
.sa-input button:disabled{opacity:.4;cursor:not-allowed;}

@media (prefers-reduced-motion:reduce){
  .sa-orb-core,.sa-orb-ring,.sa-bars span,.sa-caret,.sa-dots span{animation:none!important;}
}
`;

/* ---------------------------------------------------------------------------
 * WIRING TO A REAL BACKEND (replace the SWAP POINT in `send`):
 *
 * // Text streaming (SSE / fetch ReadableStream):
 * const res = await fetch("/api/chat", { method:"POST",
 *   body: JSON.stringify({ messages }) });
 * const reader = res.body.getReader();
 * const dec = new TextDecoder();
 * let acc = "";
 * setThinking(false); setSpeaking(true);
 * for(;;){
 *   const { value, done } = await reader.read();
 *   if (done) break;
 *   acc += dec.decode(value, { stream:true });
 *   setStreaming(acc);          // pacing now comes from the server's token rate
 * }
 * setSpeaking(false); setStreaming("");
 * setMessages(m => [...m, { role:"assistant", text: acc }]);
 *
 * // Voice agent (KEA): drive `speaking` from the TTS audio element instead
 * // of the word loop — audio.onplay => setSpeaking(true),
 * // audio.onended => setSpeaking(false). The orb + bars then react to the
 * // actual voice, and you can add real amplitude via an AnalyserNode.
 * ------------------------------------------------------------------------- */
